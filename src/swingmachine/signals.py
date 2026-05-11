from __future__ import annotations

import hashlib
from collections.abc import Sequence

import numpy as np
import pandas as pd

from swingmachine.config import StrategyRuntimeConfig
from swingmachine.enums import AssetType, PatternType

REQUIRED_PANEL_COLUMNS = (
    "symbol",
    "session_date",
    "split_adj_close",
    "split_adj_high",
    "split_adj_low",
    "raw_volume",
    "ma50",
    "ma200",
    "ma200_slope_pct20",
    "dist_to_52w_high",
    "mom_252_21",
    "ret_126",
    "rs_vs_benchmark_126",
    "trend_quality",
)

REQUIRED_REGIME_COLUMNS = (
    "session_date",
    "regime_state",
    "entry_enabled",
    "min_candidate_score_percentile",
    "min_trend_quality",
)
REGIME_CONTEXT_COLUMNS = (
    "regime_state",
    "entry_enabled",
    "size_multiplier",
    "min_candidate_score_percentile",
    "min_trend_quality",
)


def _validate_columns(frame: pd.DataFrame, required: Sequence[str]) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Missing required columns: {missing_str}")


def _ordered_panel(frame: pd.DataFrame) -> pd.DataFrame:
    _validate_columns(frame, REQUIRED_PANEL_COLUMNS)
    ordered = frame.copy()
    ordered["session_date"] = pd.to_datetime(ordered["session_date"])
    ordered = ordered.sort_values(["symbol", "session_date"]).reset_index(drop=True)
    return ordered


def _merge_regime_context(
    panel: pd.DataFrame,
    regime_frame: pd.DataFrame,
) -> pd.DataFrame:
    _validate_columns(regime_frame, REQUIRED_REGIME_COLUMNS)
    panel = panel.drop(
        columns=[column for column in REGIME_CONTEXT_COLUMNS if column in panel.columns],
    )
    regime = regime_frame.copy()
    regime["session_date"] = pd.to_datetime(regime["session_date"])
    return panel.merge(regime, on="session_date", how="left")


def _compute_avg_daily_dollar_volume_20(panel: pd.DataFrame) -> pd.Series:
    if "avg_daily_dollar_volume_20" in panel.columns:
        return panel["avg_daily_dollar_volume_20"].astype(float)

    if "raw_close" not in panel.columns:
        raise ValueError(
            "avg_daily_dollar_volume_20 is missing and cannot be derived without raw_close"
        )

    dollar_volume = panel["raw_close"].astype(float) * panel["raw_volume"].astype(float)
    return (
        dollar_volume.groupby(panel["symbol"])
        .rolling(window=20, min_periods=20)
        .mean()
        .reset_index(level=0, drop=True)
    )


def compute_universe_eligibility(
    panel: pd.DataFrame,
    config: StrategyRuntimeConfig,
) -> pd.DataFrame:
    ordered = _ordered_panel(panel)
    result = ordered.copy()
    if "history_days" in result.columns:
        result["history_days"] = result["history_days"].astype(int)
    else:
        result["history_days"] = result.groupby("symbol").cumcount() + 1
    result["avg_daily_dollar_volume_20"] = _compute_avg_daily_dollar_volume_20(result)

    eligible = (
        (result["history_days"] >= config.universe.min_history_days)
        & (result["split_adj_close"] >= config.universe.min_price)
        & (result["avg_daily_dollar_volume_20"] >= config.universe.min_avg_daily_dollar_volume_20)
        & ~result["symbol"].isin(config.universe.blocked_symbols)
    )

    if "asset_type" in result.columns:
        allowed_asset_types = {asset_type.value for asset_type in config.universe.asset_types}
        eligible &= result["asset_type"].astype(str).isin(allowed_asset_types)
        if not config.breadth.include_etfs and config.universe.exclude_inverse_etfs:
            eligible &= (
                result["asset_type"]
                .astype(str)
                .isin({AssetType.COMMON_STOCK.value, AssetType.ETF.value})
            )

    if config.universe.allowed_exchanges and "exchange" in result.columns:
        eligible &= result["exchange"].astype(str).isin(config.universe.allowed_exchanges)

    if "is_tradable" in result.columns:
        eligible &= result["is_tradable"].astype(bool)
    if "is_halted" in result.columns:
        eligible &= ~result["is_halted"].astype(bool)
    if "session_type" in result.columns:
        eligible &= result["session_type"].astype(str) == "REGULAR"

    result["universe_eligible"] = eligible
    return result


def _winsorized_zscore(
    session: pd.DataFrame,
    column: str,
    *,
    lower: float,
    upper: float,
) -> pd.Series:
    values = session[column].astype(float)
    valid = values.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=session.index, dtype=float)

    clipped = values.clip(lower=valid.quantile(lower), upper=valid.quantile(upper))
    std = clipped.std(ddof=0)
    if np.isnan(std) or std == 0.0:
        return pd.Series(0.0, index=session.index, dtype=float)
    mean = clipped.mean()
    return (clipped - mean) / std


def score_candidates(
    panel: pd.DataFrame,
    regime_frame: pd.DataFrame,
    config: StrategyRuntimeConfig,
) -> pd.DataFrame:
    eligible = compute_universe_eligibility(panel, config)
    merged = _merge_regime_context(eligible, regime_frame)

    earnings_distance = merged.get("regular_closes_until_earnings_event")
    if earnings_distance is None:
        earnings_ok = pd.Series(True, index=merged.index)
    else:
        earnings_ok = earnings_distance.isna() | (
            earnings_distance.astype(float)
            > config.events.min_regular_closes_before_earnings_for_new_entry
        )

    merged["rankable"] = (
        merged["universe_eligible"].fillna(False)
        & (merged["split_adj_close"] > merged["ma50"])
        & (merged["ma50"] > merged["ma200"])
        & (merged["ma200_slope_pct20"] > 0.0)
        & (merged["dist_to_52w_high"] <= config.filters.max_distance_from_52w_high)
        & merged["entry_enabled"].fillna(False)
        & earnings_ok
    )

    merged["candidate_score_raw"] = np.nan
    merged["candidate_score_pct"] = np.nan

    lower = config.ranking.winsorize_lower_percentile
    upper = config.ranking.winsorize_upper_percentile
    weights = config.ranking.weights

    for _, session in merged.groupby("session_date", sort=True):
        rankable = session.loc[session["rankable"]]
        if rankable.empty:
            continue

        z_mom = _winsorized_zscore(rankable, "mom_252_21", lower=lower, upper=upper)
        z_ret = _winsorized_zscore(rankable, "ret_126", lower=lower, upper=upper)
        z_rs = _winsorized_zscore(rankable, "rs_vs_benchmark_126", lower=lower, upper=upper)
        session_for_distance = rankable.assign(
            proximity_52w_high=1.0 - rankable["dist_to_52w_high"].astype(float)
        )
        z_proximity = _winsorized_zscore(
            session_for_distance,
            "proximity_52w_high",
            lower=lower,
            upper=upper,
        )
        z_trend = _winsorized_zscore(rankable, "trend_quality", lower=lower, upper=upper)

        raw = (
            weights.mom_252_21 * z_mom
            + weights.ret_126 * z_ret
            + weights.rs_vs_benchmark_126 * z_rs
            + weights.proximity_52w_high * z_proximity
            + weights.trend_quality * z_trend
        )
        pct = raw.rank(method="average", pct=True)

        merged.loc[rankable.index, "candidate_score_raw"] = raw
        merged.loc[rankable.index, "candidate_score_pct"] = pct

    merged["effective_candidate_score_threshold_pct"] = merged["min_candidate_score_percentile"]
    merged["effective_min_trend_quality"] = merged["min_trend_quality"]
    merged["is_candidate"] = (
        merged["rankable"]
        & (merged["candidate_score_pct"] >= merged["effective_candidate_score_threshold_pct"])
        & (merged["trend_quality"] >= merged["effective_min_trend_quality"])
    )
    return merged


def _most_recent_matching_date(
    window: pd.DataFrame,
    *,
    column: str,
    value: float,
) -> pd.Timestamp:
    matches = np.isclose(window[column].to_numpy(dtype=float), value, equal_nan=False)
    if not matches.any():
        raise ValueError(f"No rows match {column}={value}")
    return pd.Timestamp(window.loc[matches, "session_date"].iloc[-1])


def _setup_id(
    *,
    symbol: str,
    pattern_type: PatternType,
    setup_start_date: pd.Timestamp,
    setup_end_date: pd.Timestamp,
    setup_high_date: pd.Timestamp,
    setup_low_date: pd.Timestamp,
) -> str:
    payload = "|".join(
        [
            symbol,
            pattern_type.value,
            setup_start_date.date().isoformat(),
            setup_end_date.date().isoformat(),
            setup_high_date.date().isoformat(),
            setup_low_date.date().isoformat(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def detect_setups(
    panel: pd.DataFrame,
    config: StrategyRuntimeConfig,
) -> pd.DataFrame:
    required = REQUIRED_PANEL_COLUMNS + (
        "atr_14",
        "range_compression_ratio",
        "pullback_days",
        "pullback_depth_atr",
        "anchor_high_date",
        "is_candidate",
        "entry_enabled",
    )
    _validate_columns(panel, required)

    ordered = panel.copy()
    ordered["session_date"] = pd.to_datetime(ordered["session_date"])
    ordered["anchor_high_date"] = pd.to_datetime(ordered["anchor_high_date"])
    ordered = ordered.sort_values(["symbol", "session_date"]).reset_index(drop=True)

    out = ordered.copy()
    out["setup_valid"] = False
    out["pattern_type"] = None
    out["setup_id"] = None
    out["setup_start_date"] = pd.NaT
    out["setup_end_date"] = pd.NaT
    out["setup_high"] = np.nan
    out["setup_low"] = np.nan
    out["setup_high_date"] = pd.NaT
    out["setup_low_date"] = pd.NaT
    out["pullback_valid"] = False
    out["tight_base_valid"] = False

    min_closes_before_earnings = config.events.min_regular_closes_before_earnings_for_new_entry

    for _, group in out.groupby("symbol", sort=False):
        group = group.sort_values("session_date")
        session_to_pos = {
            pd.Timestamp(session_date): position
            for position, session_date in enumerate(group["session_date"])
        }

        for position, row in group.iterrows():
            earnings_distance = row.get("regular_closes_until_earnings_event")
            earnings_ok = pd.isna(earnings_distance) or float(earnings_distance) > float(
                min_closes_before_earnings
            )
            shared_preconditions = (
                bool(row["is_candidate"])
                and bool(row["entry_enabled"])
                and (row["split_adj_close"] > row["ma50"])
                and (row["ma50"] > row["ma200"])
                and (row["ma200_slope_pct20"] > 0.0)
                and (
                    row["dist_to_52w_high"]
                    <= config.setup.shared_requirements.max_distance_from_52w_high
                )
                and earnings_ok
            )
            if not shared_preconditions:
                continue

            row_pos = session_to_pos[pd.Timestamp(row["session_date"])]
            pullback_setup: dict[str, object] | None = None
            tight_base_setup: dict[str, object] | None = None

            anchor_date = (
                pd.Timestamp(row["anchor_high_date"]) if pd.notna(row["anchor_high_date"]) else None
            )
            if (
                anchor_date is not None
                and anchor_date in session_to_pos
                and config.setup.pullback.min_days
                <= float(row["pullback_days"])
                <= config.setup.pullback.max_days
                and row["pullback_depth_atr"] <= config.setup.pullback.max_depth_atr
                and row["range_compression_ratio"]
                <= config.setup.pullback.max_range_compression_ratio
            ):
                start_pos = session_to_pos[anchor_date]
                if start_pos <= row_pos:
                    window = group.iloc[start_pos : row_pos + 1]
                    support_ok = window["split_adj_low"].min() >= (
                        row["ma50"] - config.setup.pullback.support_buffer_atr * row["atr_14"]
                    )
                    dry_up_ok = True
                    if config.setup.pullback.require_volume_dry_up:
                        volume_sma_20 = (
                            row["raw_volume"] / row["volume_ratio_20"]
                            if "volume_ratio_20" in row.index
                            and row["volume_ratio_20"] not in (0, np.nan)
                            else np.nan
                        )
                        dry_up_ok = (
                            pd.notna(volume_sma_20)
                            and window["raw_volume"].mean() / volume_sma_20
                            <= config.setup.pullback.max_setup_volume_ratio
                        )

                    if support_ok and dry_up_ok:
                        setup_high = float(window["split_adj_high"].max())
                        setup_low = float(window["split_adj_low"].min())
                        setup_high_date = _most_recent_matching_date(
                            window,
                            column="split_adj_high",
                            value=setup_high,
                        )
                        setup_low_date = _most_recent_matching_date(
                            window,
                            column="split_adj_low",
                            value=setup_low,
                        )
                        pullback_setup = {
                            "pattern_type": PatternType.PULLBACK,
                            "setup_start_date": anchor_date,
                            "setup_end_date": pd.Timestamp(row["session_date"]),
                            "setup_high": setup_high,
                            "setup_low": setup_low,
                            "setup_high_date": setup_high_date,
                            "setup_low_date": setup_low_date,
                        }

            for window_length in range(
                config.setup.tight_base.min_days,
                config.setup.tight_base.max_days + 1,
            ):
                if row_pos + 1 < window_length:
                    continue
                window = group.iloc[row_pos - window_length + 1 : row_pos + 1]
                base_range_atr = (
                    window["split_adj_high"].max() - window["split_adj_low"].min()
                ) / row["atr_14"]
                base_return_abs = abs(
                    row["split_adj_close"] / window.iloc[0]["split_adj_close"] - 1.0
                )
                valid = (
                    base_range_atr <= config.setup.tight_base.max_base_range_atr
                    and base_return_abs <= config.setup.tight_base.max_base_drift_pct
                    and row["range_compression_ratio"]
                    <= config.setup.tight_base.max_range_compression_ratio
                )
                if not valid:
                    continue

                setup_high = float(window["split_adj_high"].max())
                setup_low = float(window["split_adj_low"].min())
                tight_base_setup = {
                    "pattern_type": PatternType.TIGHT_BASE,
                    "setup_start_date": pd.Timestamp(window.iloc[0]["session_date"]),
                    "setup_end_date": pd.Timestamp(row["session_date"]),
                    "setup_high": setup_high,
                    "setup_low": setup_low,
                    "setup_high_date": _most_recent_matching_date(
                        window,
                        column="split_adj_high",
                        value=setup_high,
                    ),
                    "setup_low_date": _most_recent_matching_date(
                        window,
                        column="split_adj_low",
                        value=setup_low,
                    ),
                }

            out.loc[position, "pullback_valid"] = pullback_setup is not None
            out.loc[position, "tight_base_valid"] = tight_base_setup is not None

            chosen_setup = None
            for pattern_type in config.setup.pattern_priority:
                if pattern_type is PatternType.TIGHT_BASE and tight_base_setup is not None:
                    chosen_setup = tight_base_setup
                    break
                if pattern_type is PatternType.PULLBACK and pullback_setup is not None:
                    chosen_setup = pullback_setup
                    break

            if chosen_setup is None:
                continue

            out.loc[position, "setup_valid"] = True
            out.loc[position, "pattern_type"] = chosen_setup["pattern_type"].value
            out.loc[position, "setup_start_date"] = chosen_setup["setup_start_date"]
            out.loc[position, "setup_end_date"] = chosen_setup["setup_end_date"]
            out.loc[position, "setup_high"] = chosen_setup["setup_high"]
            out.loc[position, "setup_low"] = chosen_setup["setup_low"]
            out.loc[position, "setup_high_date"] = chosen_setup["setup_high_date"]
            out.loc[position, "setup_low_date"] = chosen_setup["setup_low_date"]
            out.loc[position, "setup_id"] = _setup_id(
                symbol=str(row["symbol"]),
                pattern_type=chosen_setup["pattern_type"],
                setup_start_date=chosen_setup["setup_start_date"],
                setup_end_date=chosen_setup["setup_end_date"],
                setup_high_date=chosen_setup["setup_high_date"],
                setup_low_date=chosen_setup["setup_low_date"],
            )

    return out
