from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from swingmachine.config import StrategyRuntimeConfig
from swingmachine.enums import AssetType, RegimeState

REQUIRED_BENCHMARK_COLUMNS = ("session_date", "split_adj_close", "tr_close_index")
REQUIRED_BREADTH_COLUMNS = ("session_date", "split_adj_close", "ma200")


def _validate_columns(frame: pd.DataFrame, required: Sequence[str]) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Missing required columns: {missing_str}")


def _ordered_frame(frame: pd.DataFrame, required: Sequence[str]) -> pd.DataFrame:
    _validate_columns(frame, required)
    ordered = frame.copy()
    ordered["session_date"] = pd.to_datetime(ordered["session_date"])
    ordered = ordered.sort_values("session_date").reset_index(drop=True)
    return ordered


def compute_regime_inputs(
    benchmark_frame: pd.DataFrame,
    config: StrategyRuntimeConfig,
) -> pd.DataFrame:
    ordered = _ordered_frame(benchmark_frame, REQUIRED_BENCHMARK_COLUMNS)

    ma_window = config.regime.ma_window_days
    slope_lookback = config.regime.ma200_slope_lookback_days
    realized_vol_lookback = config.regime.realized_vol.lookback_days
    panic_lookback = config.regime.panic_rebound.drawdown_lookback_days
    rebound_window = config.regime.panic_rebound.rebound_window_days

    result = ordered[["session_date"]].copy()
    result["benchmark_symbol"] = config.regime.benchmark_symbol
    result["benchmark_close"] = ordered["split_adj_close"].astype(float)
    result["benchmark_ma200"] = (
        result["benchmark_close"]
        .rolling(
            window=ma_window,
            min_periods=ma_window,
        )
        .mean()
    )
    result["benchmark_ma200_slope_pct20"] = (
        result["benchmark_ma200"] / result["benchmark_ma200"].shift(slope_lookback) - 1.0
    )
    result["benchmark_dist_above_ma200"] = (
        result["benchmark_close"] / result["benchmark_ma200"] - 1.0
    )

    tr_close = ordered["tr_close_index"].astype(float)
    log_returns = np.log(tr_close / tr_close.shift(1))
    result["realized_vol_20"] = log_returns.rolling(
        window=realized_vol_lookback,
        min_periods=realized_vol_lookback,
    ).std(ddof=1) * np.sqrt(252.0)

    result["panic_drawdown_126"] = (
        result["benchmark_close"]
        / result["benchmark_close"]
        .rolling(
            window=panic_lookback,
            min_periods=panic_lookback,
        )
        .max()
        - 1.0
    )
    result["rebound_return_20"] = (
        result["benchmark_close"] / result["benchmark_close"].shift(rebound_window) - 1.0
    )
    return result


def compute_breadth_by_session(
    panel: pd.DataFrame,
    config: StrategyRuntimeConfig,
) -> pd.DataFrame:
    ordered = _ordered_frame(panel, REQUIRED_BREADTH_COLUMNS)
    breadth = ordered.copy()

    valid = breadth["split_adj_close"].notna() & breadth["ma200"].notna()
    if "asset_type" in breadth.columns and not config.breadth.include_etfs:
        valid &= breadth["asset_type"] != AssetType.ETF.value
        valid &= breadth["asset_type"] != AssetType.ETF

    filtered = breadth.loc[valid].copy()
    filtered["above_ma200"] = filtered["split_adj_close"] > filtered["ma200"]

    grouped = filtered.groupby("session_date", sort=True)
    summary = grouped["above_ma200"].agg(["sum", "count"]).reset_index()
    summary = summary.rename(
        columns={
            "sum": "breadth_above_ma200_count",
            "count": "breadth_constituents",
        }
    )
    summary["breadth_pct_above_ma200"] = (
        summary["breadth_above_ma200_count"] / summary["breadth_constituents"]
    )
    return summary


def classify_regimes(
    regime_inputs: pd.DataFrame,
    config: StrategyRuntimeConfig,
    *,
    breadth_by_session: pd.DataFrame | None = None,
) -> pd.DataFrame:
    ordered = _ordered_frame(
        regime_inputs,
        (
            "session_date",
            "benchmark_symbol",
            "benchmark_close",
            "benchmark_ma200",
            "benchmark_ma200_slope_pct20",
            "benchmark_dist_above_ma200",
            "realized_vol_20",
            "panic_drawdown_126",
            "rebound_return_20",
        ),
    )

    result = ordered.copy()
    if breadth_by_session is not None:
        breadth = breadth_by_session.copy()
        breadth["session_date"] = pd.to_datetime(breadth["session_date"])
        result = result.merge(breadth, on="session_date", how="left")
    else:
        result["breadth_constituents"] = np.nan
        result["breadth_pct_above_ma200"] = np.nan

    breadth_enabled = config.breadth.enabled
    breadth_missing = pd.Series(False, index=result.index)
    if breadth_enabled:
        breadth_missing = (
            result["breadth_pct_above_ma200"].isna()
            | result["breadth_constituents"].isna()
            | (result["breadth_constituents"] < config.breadth.min_constituents)
        )

    panic = pd.Series(False, index=result.index)
    if config.regime.panic_rebound.enabled:
        panic = (
            (result["panic_drawdown_126"] <= config.regime.panic_rebound.panic_decline_threshold)
            & (result["rebound_return_20"] >= config.regime.panic_rebound.rebound_return_threshold)
            & (
                result["realized_vol_20"]
                >= config.regime.panic_rebound.panic_realized_vol_threshold
            )
        )

    risk_off = (
        (result["benchmark_close"] < result["benchmark_ma200"])
        | (result["benchmark_ma200_slope_pct20"] <= 0.0)
        | (result["realized_vol_20"] >= config.regime.realized_vol.risk_off_threshold)
    )
    if breadth_enabled:
        risk_off |= (
            result["breadth_pct_above_ma200"]
            < config.regime.breadth_thresholds.risk_off_min_pct_above_ma200
        )
        risk_off |= breadth_missing
    risk_off &= ~panic

    caution = (
        result["benchmark_dist_above_ma200"] < config.regime.caution_min_distance_above_ma200
    ) | (result["realized_vol_20"] >= config.regime.realized_vol.caution_threshold)
    if breadth_enabled:
        caution |= (
            result["breadth_pct_above_ma200"]
            < config.regime.breadth_thresholds.risk_on_min_pct_above_ma200
        )
    caution &= ~panic & ~risk_off

    states = np.full(len(result), RegimeState.RISK_ON.value, dtype=object)
    states[caution.to_numpy()] = RegimeState.CAUTION.value
    states[risk_off.to_numpy()] = RegimeState.RISK_OFF.value
    states[panic.to_numpy()] = RegimeState.PANIC_REBOUND.value
    result["regime_state"] = states

    actions = {
        state.value: config.regime_action(state)
        for state in (
            RegimeState.RISK_ON,
            RegimeState.CAUTION,
            RegimeState.RISK_OFF,
            RegimeState.PANIC_REBOUND,
        )
    }
    result["entry_enabled"] = result["regime_state"].map(lambda state: actions[state].entry_enabled)
    result["size_multiplier"] = result["regime_state"].map(
        lambda state: actions[state].size_multiplier
    )
    result["min_candidate_score_percentile"] = result["regime_state"].map(
        lambda state: actions[state].min_candidate_score_percentile
    )
    result["min_trend_quality"] = result["regime_state"].map(
        lambda state: actions[state].min_trend_quality
    )

    return result


def compute_regime_snapshots(
    benchmark_frame: pd.DataFrame,
    config: StrategyRuntimeConfig,
    *,
    breadth_by_session: pd.DataFrame | None = None,
) -> pd.DataFrame:
    inputs = compute_regime_inputs(benchmark_frame, config)
    return classify_regimes(inputs, config, breadth_by_session=breadth_by_session)
