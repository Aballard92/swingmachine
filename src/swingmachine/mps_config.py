from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import model_validator

from swingmachine.modeling import (
    ImmutableModel,
    NonNegativeFloat,
    Percent,
    PositiveFloat,
    PositiveInt,
)


class MpsStrategyConfig(ImmutableModel):
    name: Literal["MPS_1"]
    description: str
    bar_frequency: Literal["1d"]
    direction: Literal["long_only"]
    signal_time: Literal["official_close"]
    execution_time: Literal["next_session_open"]
    pyramiding: Literal[False]


class MpsUniverseConfig(ImmutableModel):
    exchanges: tuple[str, ...]
    security_types: tuple[Literal["common_stock"], ...]
    excluded_types: tuple[str, ...]
    country_of_primary_listing: Literal["US"]
    minimum_price: PositiveFloat
    minimum_market_cap: PositiveFloat
    median_dollar_volume_period: PositiveInt
    minimum_median_dollar_volume: PositiveFloat
    minimum_history_sessions: PositiveInt


class MpsSmaPeriods(ImmutableModel):
    short: PositiveInt
    intermediate: PositiveInt
    long: PositiveInt


class MpsAtrConfig(ImmutableModel):
    period: PositiveInt
    method: Literal["wilder"]


class MpsMomentumLeg(ImmutableModel):
    start_lag: PositiveInt
    end_lag: PositiveInt
    weight: Percent

    @model_validator(mode="after")
    def validate_lags(self) -> MpsMomentumLeg:
        if self.start_lag <= self.end_lag:
            raise ValueError("momentum start_lag must exceed end_lag")
        return self


class MpsMomentumConfig(ImmutableModel):
    legs: tuple[MpsMomentumLeg, ...]
    enter_percentile: Percent
    hold_percentile: Percent

    @model_validator(mode="after")
    def validate_momentum(self) -> MpsMomentumConfig:
        if abs(sum(leg.weight for leg in self.legs) - 1.0) > 1e-12:
            raise ValueError("momentum leg weights must sum to 1")
        if self.hold_percentile >= self.enter_percentile:
            raise ValueError("hold percentile must be below enter percentile")
        return self


class MpsFeaturesConfig(ImmutableModel):
    sma_periods: MpsSmaPeriods
    long_sma_slope_lookback: PositiveInt
    atr: MpsAtrConfig
    momentum: MpsMomentumConfig


class MpsTrendConfig(ImmutableModel):
    require_close_above_sma50: bool
    require_sma50_above_sma200: bool
    require_rising_sma200: bool


class MpsPullbackConfig(ImmutableModel):
    peak_lookback_sessions: PositiveInt
    sma_touch_period: PositiveInt
    sma_touch_lookback_sessions: PositiveInt
    minimum_depth_atr: NonNegativeFloat
    maximum_depth_atr: PositiveFloat
    require_close_above_prior_high: bool
    minimum_close_location_value: Percent
    require_close_above_sma50: bool

    @model_validator(mode="after")
    def validate_depth(self) -> MpsPullbackConfig:
        if self.minimum_depth_atr >= self.maximum_depth_atr:
            raise ValueError("minimum pullback depth must be below maximum")
        return self


class MpsEntryConfig(ImmutableModel):
    order_type: Literal["opening_auction_market"]
    signal_valid_sessions: PositiveInt
    maximum_absolute_gap_atr: PositiveFloat
    no_pyramiding: Literal[True]


class MpsInitialStopConfig(ImmutableModel):
    swing_low_lookback_sessions: PositiveInt
    structure_buffer_atr: NonNegativeFloat
    minimum_volatility_distance_atr: PositiveFloat
    maximum_risk_distance_atr: PositiveFloat
    maximum_risk_distance_fraction: Percent


class MpsTrailingStopConfig(ImmutableModel):
    activation_r: PositiveFloat
    distance_atr: PositiveFloat
    reference_price: Literal["highest_close"]
    never_loosen: Literal[True]
    activate_next_session: Literal[True]


class MpsExitsConfig(ImmutableModel):
    momentum_hold_percentile: Percent
    close_below_sma_period: PositiveInt
    failure_check_after_sessions: PositiveInt
    failure_minimum_mfe_r: NonNegativeFloat
    failure_requires_close_at_or_below_entry: bool
    maximum_holding_sessions: PositiveInt
    fixed_profit_target: None


class MpsRiskConfig(ImmutableModel):
    base_risk_fraction_per_trade: Percent
    maximum_positions: PositiveInt
    maximum_gross_exposure: Percent
    maximum_position_notional_fraction: Percent
    maximum_portfolio_heat: Percent
    maximum_sector_notional_fraction: Percent
    maximum_sector_heat: Percent
    maximum_adv_participation: Percent
    post_fill_risk_tolerance: PositiveFloat
    allow_leverage: Literal[False]


class MpsMarketRegimeConfig(ImmutableModel):
    benchmark: str
    sma_period: PositiveInt
    below_sma_multiplier: Percent
    realised_volatility_period: PositiveInt
    annualisation_sessions: PositiveInt
    target_annualised_volatility: PositiveFloat
    minimum_multiplier: Percent
    maximum_multiplier: Percent
    allow_volatility_leverage: Literal[False]

    @model_validator(mode="after")
    def validate_bounds(self) -> MpsMarketRegimeConfig:
        if self.minimum_multiplier > self.maximum_multiplier:
            raise ValueError("minimum regime multiplier exceeds maximum")
        return self


class MpsEarningsConfig(ImmutableModel):
    enabled: bool
    avoid_entries_within_sessions: PositiveInt
    exit_before_event: bool
    require_point_in_time_calendar: bool


class MpsExecutionConfig(ImmutableModel):
    baseline_one_way_cost_bps: NonNegativeFloat
    stress_one_way_cost_bps: tuple[NonNegativeFloat, ...]
    gap_through_stop_fill: Literal["opening_price"]
    intraday_stop_fill: Literal["stop_price"]
    apply_adverse_slippage: bool
    partial_fills_enabled: Literal[False]


class MpsDrawdownConfig(ImmutableModel):
    half_risk_drawdown: Percent
    stop_new_entries_drawdown: Percent
    recovery_drawdown: Percent
    clean_sessions_before_recovery: PositiveInt


class MpsLoggingConfig(ImmutableModel):
    write_daily_equity: bool
    write_positions: bool
    write_orders: bool
    write_fills: bool
    write_rejected_orders: bool
    write_feature_snapshot: bool
    write_decision_reasons: bool
    write_data_version_hash: bool


class MpsConfig(ImmutableModel):
    strategy: MpsStrategyConfig
    universe: MpsUniverseConfig
    features: MpsFeaturesConfig
    trend: MpsTrendConfig
    pullback: MpsPullbackConfig
    entry: MpsEntryConfig
    initial_stop: MpsInitialStopConfig
    trailing_stop: MpsTrailingStopConfig
    exits: MpsExitsConfig
    risk: MpsRiskConfig
    market_regime: MpsMarketRegimeConfig
    earnings: MpsEarningsConfig
    execution: MpsExecutionConfig
    drawdown_controls: MpsDrawdownConfig
    logging: MpsLoggingConfig

    def config_hash(self) -> str:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_mps_config(path: str | Path = "config/mps_1.yaml") -> MpsConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError("MPS configuration root must be a mapping")
    return MpsConfig.model_validate(payload)
