from __future__ import annotations

import pandas as pd

from swingmachine.mps_config import MpsConfig
from swingmachine.mps_contracts import MpsCandidate, MpsPosition, MpsVariant


def variant_signal_mask(
    features: pd.DataFrame, variant: MpsVariant, config: MpsConfig
) -> pd.Series:
    momentum = features["momentum_rank"] >= config.features.momentum.enter_percentile
    trend = features["trend_qualified"].astype(bool)
    pullback = (
        features["pullback_depth_atr"].between(
            config.pullback.minimum_depth_atr,
            config.pullback.maximum_depth_atr,
            inclusive="both",
        )
        & features["recent_sma20_touch"].astype(bool)
        & features["close_above_prior_high"].astype(bool)
        & (features["close_location_value"] >= config.pullback.minimum_close_location_value)
        & (features["close"] > features["sma50"])
    )
    breakout = features["close"] > features["prior_high20"]
    base = features["eligible_universe"].astype(bool) & momentum
    if variant is MpsVariant.B0_RANK_ONLY:
        return base
    if variant is MpsVariant.B1_MOMENTUM_TREND:
        return base & trend
    if variant in (MpsVariant.B2_MOMENTUM_PULLBACK, MpsVariant.B4_FULL_MPS1):
        return base & trend & pullback
    if variant is MpsVariant.B3_MOMENTUM_BREAKOUT:
        return base & trend & breakout
    raise ValueError(f"unsupported MPS variant {variant}")


def select_candidates(
    session_features: pd.DataFrame,
    variant: MpsVariant,
    config: MpsConfig,
    *,
    held_security_ids: frozenset[str] = frozenset(),
) -> tuple[MpsCandidate, ...]:
    matches = session_features.loc[variant_signal_mask(session_features, variant, config)].copy()
    matches = matches.loc[~matches["security_id"].isin(held_security_ids)]
    matches = matches.sort_values(
        ["momentum_rank", "adv20_dollars", "ticker"],
        ascending=[False, False, True],
        kind="mergesort",
    )
    return tuple(
        MpsCandidate(
            security_id=str(row.security_id),
            ticker=str(row.ticker),
            signal_session=pd.Timestamp(row.session_date).date(),
            variant=variant,
            momentum_rank=float(row.momentum_rank),
            adv20_dollars=float(row.adv20_dollars),
            structure_stop=None if pd.isna(row.structure_stop) else float(row.structure_stop),
            signal_close=float(row.close),
            signal_atr20=None if pd.isna(row.atr20) else float(row.atr20),
            sector=str(row.sector),
        )
        for row in matches.itertuples(index=False)
    )


def exit_reason(
    position: MpsPosition,
    row: pd.Series,
    config: MpsConfig,
) -> str | None:
    if float(row["momentum_rank"]) < config.exits.momentum_hold_percentile:
        return "MOMENTUM_DETERIORATION"
    if float(row["close"]) < float(row["sma50"]):
        return "TREND_FAILURE"
    mfe_r = (
        position.maximum_high_since_entry - position.entry_price
    ) / position.initial_risk_per_share
    if (
        position.holding_sessions >= config.exits.failure_check_after_sessions
        and mfe_r < config.exits.failure_minimum_mfe_r
        and float(row["close"]) <= position.entry_price
    ):
        return "FAILURE_EXIT"
    if position.holding_sessions >= config.exits.maximum_holding_sessions:
        return "MAX_HOLDING_EXIT"
    return None


def updated_trailing_stop(
    position: MpsPosition, close: float, atr20: float, config: MpsConfig
) -> float:
    activation = (
        position.entry_price + config.trailing_stop.activation_r * position.initial_risk_per_share
    )
    if close < activation:
        return position.active_stop
    highest_close = max(position.highest_close_since_entry, close)
    candidate = highest_close - config.trailing_stop.distance_atr * atr20
    return max(position.active_stop, candidate)
