from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

import yaml

from swingmachine.enums import (
    AssetType,
    BenchmarkRealizedVolSeries,
    BenchmarkTrendSeries,
    BrokerName,
    ChartOHLCSeries,
    ExecutionOHLCSeries,
    NormalizationMethod,
    OpeningPrintReference,
    OrderType,
    PatternType,
    RealizedVolMethod,
    RegimeExitMode,
    RegimeState,
    ReturnCloseSeries,
    SessionType,
    SourceUniverse,
    SubmissionTiming,
    TrendQualityFormula,
)
from swingmachine.modeling import (
    ImmutableModel,
    NonNegativeFloat,
    NonNegativeInt,
    Percent,
    PositiveFloat,
    PositiveInt,
)


class StrategySection(ImmutableModel):
    id: str
    version: str
    description: str
    timeframe: str
    signal_session: SessionType
    scan_schedule: str
    order_schedule: str
    long_only: bool
    pyramiding_allowed: bool


class CanonicalPriceSeriesConfig(ImmutableModel):
    chart_ohlc: ChartOHLCSeries
    return_close: ReturnCloseSeries
    execution_ohlc: ExecutionOHLCSeries


class CorporateActionsConfig(ImmutableModel):
    adjust_for_splits: bool
    adjust_chart_ohlc_for_dividends: bool
    include_cash_dividends_in_return_index: bool
    total_return_index_base_value: PositiveFloat


class MissingInputPolicyConfig(ImmutableModel):
    fail_closed_on_missing_regime_inputs: bool
    fail_closed_on_missing_corporate_actions: bool


class DataSection(ImmutableModel):
    canonical_price_series: CanonicalPriceSeriesConfig
    corporate_actions: CorporateActionsConfig
    missing_input_policy: MissingInputPolicyConfig


class UniverseSection(ImmutableModel):
    asset_types: tuple[AssetType, ...]
    min_history_days: PositiveInt
    min_price: PositiveFloat
    min_avg_daily_dollar_volume_20: PositiveFloat
    exclude_leveraged_etfs: bool
    exclude_inverse_etfs: bool
    allowed_exchanges: tuple[str, ...]
    allowed_symbols: tuple[str, ...]
    blocked_symbols: tuple[str, ...]


class BreadthSection(ImmutableModel):
    enabled: bool
    source_universe: SourceUniverse
    include_etfs: bool
    min_constituents: PositiveInt
    ma_window_days: PositiveInt


class RealizedVolConfig(ImmutableModel):
    lookback_days: PositiveInt
    method: RealizedVolMethod
    caution_threshold: PositiveFloat
    risk_off_threshold: PositiveFloat


class BreadthThresholdsConfig(ImmutableModel):
    risk_on_min_pct_above_ma200: Percent
    risk_off_min_pct_above_ma200: Percent


class PanicReboundConfig(ImmutableModel):
    enabled: bool
    drawdown_lookback_days: PositiveInt
    panic_decline_threshold: float
    rebound_window_days: PositiveInt
    rebound_return_threshold: PositiveFloat
    panic_realized_vol_threshold: PositiveFloat


class RegimeActionConfig(ImmutableModel):
    entry_enabled: bool
    size_multiplier: NonNegativeFloat
    min_candidate_score_percentile: Percent
    min_trend_quality: Percent


class RegimeActionsConfig(ImmutableModel):
    RISK_ON: RegimeActionConfig
    CAUTION: RegimeActionConfig
    RISK_OFF: RegimeActionConfig
    PANIC_REBOUND: RegimeActionConfig


class RegimeSection(ImmutableModel):
    benchmark_symbol: str
    benchmark_trend_series: BenchmarkTrendSeries
    benchmark_realized_vol_series: BenchmarkRealizedVolSeries
    ma_window_days: PositiveInt
    ma200_slope_lookback_days: PositiveInt
    caution_min_distance_above_ma200: NonNegativeFloat
    realized_vol: RealizedVolConfig
    breadth_thresholds: BreadthThresholdsConfig
    panic_rebound: PanicReboundConfig
    actions: RegimeActionsConfig


class TrendQualityComponentsConfig(ImmutableModel):
    ma20_over_ma50_weight: Percent
    ma50_over_ma200_weight: Percent
    ma50_slope_pct20_weight: Percent
    ma200_slope_pct20_weight: Percent


class TrendQualityLevelsConfig(ImmutableModel):
    ma20_over_ma50: PositiveFloat
    ma50_over_ma200: PositiveFloat
    ma50_slope_pct20: PositiveFloat
    ma200_slope_pct20: PositiveFloat


class TrendQualityConfig(ImmutableModel):
    formula: TrendQualityFormula
    components: TrendQualityComponentsConfig
    full_score_levels: TrendQualityLevelsConfig


class RankingWeightsConfig(ImmutableModel):
    mom_252_21: float
    ret_126: float
    rs_vs_benchmark_126: float
    proximity_52w_high: float
    trend_quality: float


class RankingSection(ImmutableModel):
    normalization: NormalizationMethod
    winsorize_lower_percentile: Percent
    winsorize_upper_percentile: Percent
    return_series: ReturnCloseSeries
    relative_strength_lookback_days: PositiveInt
    momentum_skip_days: NonNegativeInt
    trend_quality: TrendQualityConfig
    weights: RankingWeightsConfig


class FiltersSection(ImmutableModel):
    require_close_above_ma50: bool
    require_ma50_above_ma200: bool
    require_positive_ma200_slope: bool
    max_distance_from_52w_high: Percent


class RangeCompressionRatioConfig(ImmutableModel):
    numerator_atr_window: PositiveInt
    denominator_atr_window: PositiveInt


class FeaturesSection(ImmutableModel):
    moving_averages: tuple[PositiveInt, ...]
    atr_windows: tuple[PositiveInt, ...]
    high_lookback_days_for_52w: PositiveInt
    pullback_anchor_lookback_days: PositiveInt
    range_compression_ratio: RangeCompressionRatioConfig


class RelativeStrengthAccelerationPairConfig(ImmutableModel):
    short_window: PositiveInt
    long_window: PositiveInt


class BenchmarkRelativeFeaturesSection(ImmutableModel):
    compute: bool
    influence_strategy_behavior: bool
    benchmark_symbol: str
    relative_strength_windows: tuple[PositiveInt, ...]
    acceleration_pairs: tuple[RelativeStrengthAccelerationPairConfig, ...]
    drawdown_window: PositiveInt
    rebound_window: PositiveInt


class SharedRequirementsConfig(ImmutableModel):
    max_distance_from_52w_high: Percent
    require_close_above_ma50: bool
    require_ma50_above_ma200: bool
    require_positive_ma200_slope: bool


class PullbackSetupConfig(ImmutableModel):
    min_days: PositiveInt
    max_days: PositiveInt
    max_depth_atr: PositiveFloat
    max_range_compression_ratio: PositiveFloat
    support_buffer_atr: NonNegativeFloat
    require_volume_dry_up: bool
    max_setup_volume_ratio: PositiveFloat


class TightBaseSetupConfig(ImmutableModel):
    min_days: PositiveInt
    max_days: PositiveInt
    max_base_range_atr: PositiveFloat
    max_base_drift_pct: Percent
    max_range_compression_ratio: PositiveFloat


class SetupRegistryConfig(ImmutableModel):
    persist_spent_setups: bool
    disallow_reuse_of_spent_setup_id: bool


class SetupSection(ImmutableModel):
    pattern_priority: tuple[PatternType, ...]
    shared_requirements: SharedRequirementsConfig
    pullback: PullbackSetupConfig
    tight_base: TightBaseSetupConfig
    setup_registry: SetupRegistryConfig


class EntrySection(ImmutableModel):
    order_type: OrderType
    entry_buffer_atr: PositiveFloat
    max_gap_above_trigger_atr: PositiveFloat
    order_expiry_sessions: PositiveInt
    use_regular_session_only: bool
    enable_extended_hours: bool
    one_pending_entry_per_symbol: bool
    submission_timing: SubmissionTiming
    opening_print_reference: OpeningPrintReference
    cancel_unfilled_order_if_open_above_limit: bool


class RiskSection(ImmutableModel):
    risk_per_trade_pct_equity: Percent
    max_position_pct_equity: Percent
    max_sector_pct_equity: Percent
    max_portfolio_heat_pct_equity: Percent
    max_new_risk_per_day_pct_equity: Percent
    portfolio_vol_target_annualized: PositiveFloat


class TrailingStopsConfig(ImmutableModel):
    enabled: bool
    activate_after_gain_atr: PositiveFloat
    trailing_atr_multiple: PositiveFloat
    risk_off_trailing_atr_multiple: PositiveFloat


class TimeStopConfig(ImmutableModel):
    enabled: bool
    max_bars_without_progress: PositiveInt
    min_progress_after_n_bars_atr: NonNegativeFloat


class StopsSection(ImmutableModel):
    initial_stop_mode: str
    stop_atr_multiple: PositiveFloat
    setup_low_buffer_atr: NonNegativeFloat
    trailing: TrailingStopsConfig
    time_stop: TimeStopConfig


class ExitsSection(ImmutableModel):
    profit_target_enabled: bool
    allow_partial_scale_out: bool
    earnings_exit_lead_regular_closes: PositiveInt
    earnings_exit_execution: str
    regime_exit_mode: RegimeExitMode


class EventsSection(ImmutableModel):
    earnings_filter_enabled: bool
    min_regular_closes_before_earnings_for_new_entry: PositiveInt
    unknown_earnings_session_policy: str
    allow_holding_through_earnings: bool
    use_eps_surprise_overlay: bool
    use_transcript_nlp_overlay: bool


class ExecutionSection(ImmutableModel):
    broker: BrokerName
    use_synthetic_brackets: bool
    deduplicate_order_intents: bool
    max_pending_orders_per_symbol: PositiveInt
    max_open_positions_per_symbol: PositiveInt
    cancel_stale_entries_before_new_submit: bool
    rate_limit_guard_enabled: bool
    reconcile_positions_every_minutes: PositiveInt
    reconcile_orders_every_minutes: PositiveInt


class MonitoringSection(ImmutableModel):
    enable_stale_data_checks: bool
    max_data_age_seconds: PositiveInt
    enable_slippage_alerts: bool
    slippage_alert_bps: NonNegativeFloat
    enable_drawdown_kill_switch: bool
    daily_drawdown_kill_switch_pct: Percent
    enable_reconciliation_kill_switch: bool
    enable_broker_health_kill_switch: bool


class SignalPriceSourcesConfig(ImmutableModel):
    chart_features: str
    return_features: str
    execution_model: str


class BacktestSection(ImmutableModel):
    signal_price_sources: SignalPriceSourcesConfig
    include_splits: bool
    include_cash_dividends: bool
    include_delistings: bool
    include_spread_model: bool
    include_market_impact_model: bool
    include_fx_cost_model: bool
    include_spent_setup_logic: bool
    walk_forward_enabled: bool
    pbo_analysis_enabled: bool


class StrategyRuntimeConfig(ImmutableModel):
    strategy: StrategySection
    data: DataSection
    universe: UniverseSection
    breadth: BreadthSection
    regime: RegimeSection
    ranking: RankingSection
    filters: FiltersSection
    features: FeaturesSection
    benchmark_relative_features: BenchmarkRelativeFeaturesSection
    setup: SetupSection
    entry: EntrySection
    risk: RiskSection
    stops: StopsSection
    exits: ExitsSection
    events: EventsSection
    execution: ExecutionSection
    monitoring: MonitoringSection
    backtest: BacktestSection

    def regime_action(self, state: RegimeState) -> RegimeActionConfig:
        return cast(RegimeActionConfig, getattr(self.regime.actions, state.value))

    def config_hash(self) -> str:
        payload = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_strategy_config(path: str | Path) -> StrategyRuntimeConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at root of {config_path}")

    return StrategyRuntimeConfig.model_validate(data)
