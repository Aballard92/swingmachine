from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from swingmachine.enums import (
    AlertSeverity,
    BrokerOrderStatus,
    EarningsEventSession,
    MonitoringAlertType,
    OrderIntentStatus,
    OrderReason,
    OrderSide,
    OrderType,
    PaperShadowAlignmentStatus,
    PatternType,
    PendingEntryCancelReason,
    RegimeState,
    ReviewStatus,
    RuntimeMode,
    SessionType,
    ShadowFillStatus,
    SymbolLifecycleState,
)
from swingmachine.modeling import (
    ImmutableModel,
    NonNegativeFloat,
    NonNegativeInt,
    Percent,
    PositiveFloat,
    PositiveInt,
)


class SymbolDailyBar(ImmutableModel):
    symbol: str
    session_date: date
    session_type: SessionType

    raw_open: PositiveFloat
    raw_high: PositiveFloat
    raw_low: PositiveFloat
    raw_close: PositiveFloat
    raw_volume: NonNegativeFloat

    split_adj_open: PositiveFloat
    split_adj_high: PositiveFloat
    split_adj_low: PositiveFloat
    split_adj_close: PositiveFloat
    split_adj_volume: NonNegativeFloat

    cash_dividend_per_share: NonNegativeFloat
    split_ratio: PositiveFloat
    tr_close_index: PositiveFloat

    currency: str
    exchange: str
    is_tradable: bool


class FeatureSnapshot(ImmutableModel):
    symbol: str
    session_date: date

    ret_21: float
    ret_63: float
    ret_126: float
    ret_252: float
    mom_252_21: float
    rs_vs_benchmark_126: float

    ma20: PositiveFloat
    ma50: PositiveFloat
    ma200: PositiveFloat
    ma50_slope_pct20: float
    ma200_slope_pct20: float

    atr_14: PositiveFloat
    atr_5: PositiveFloat
    atr_20: PositiveFloat
    atr_pct: NonNegativeFloat
    range_compression_ratio: NonNegativeFloat

    dist_to_52w_high: Percent
    pullback_days: NonNegativeInt
    pullback_depth_atr: NonNegativeFloat
    volume_ratio_20: NonNegativeFloat
    trend_quality: Percent

    candidate_score_raw: float
    candidate_score_pct: Percent
    effective_candidate_score_threshold_pct: Percent
    effective_min_trend_quality: Percent

    pattern_type: PatternType | None
    setup_id: str | None
    setup_start_date: date | None
    setup_end_date: date | None
    setup_high: PositiveFloat | None
    setup_low: PositiveFloat | None
    setup_high_date: date | None
    setup_low_date: date | None
    setup_valid: bool

    earnings_event_session: EarningsEventSession | None
    regular_closes_until_earnings_event: NonNegativeInt | None


class RegimeSnapshot(ImmutableModel):
    session_date: date
    benchmark_symbol: str

    benchmark_close: PositiveFloat
    benchmark_ma200: PositiveFloat
    benchmark_ma200_slope_pct20: float
    benchmark_dist_above_ma200: float

    realized_vol_20: NonNegativeFloat
    breadth_pct_above_ma200: Percent | None
    panic_drawdown_126: float
    rebound_return_20: float

    regime_state: RegimeState
    entry_enabled: bool
    size_multiplier: NonNegativeFloat
    min_candidate_score_percentile: Percent
    min_trend_quality: Percent


class SetupSnapshot(ImmutableModel):
    symbol: str
    session_date: date
    pattern_type: PatternType
    setup_id: str
    setup_start_date: date
    setup_end_date: date
    setup_high: PositiveFloat
    setup_low: PositiveFloat
    setup_high_date: date
    setup_low_date: date
    entry_trigger: PositiveFloat
    entry_limit: PositiveFloat
    initial_stop: PositiveFloat
    per_share_risk: PositiveFloat
    spent: bool


class OrderIntent(ImmutableModel):
    intent_id: str
    dedupe_key: str
    strategy_id: str
    config_hash: str

    symbol: str
    setup_id: str | None
    side: OrderSide
    reason: OrderReason
    order_type: OrderType

    quantity: PositiveFloat
    stop_price: PositiveFloat | None
    limit_price: PositiveFloat | None

    created_at: datetime
    expires_at: datetime | None
    broker_order_id: str | None


class CanonicalSnapshotHashRecord(ImmutableModel):
    symbol: str
    session_date: date
    snapshot_hash: str
    recorded_at: datetime


class OrderIntentSubmissionResult(ImmutableModel):
    accepted: bool
    reason: str | None = None
    intent: OrderIntent | None = None
    existing_intent_id: str | None = None


class RestartRecoveryState(ImmutableModel):
    pending_entry_intents: tuple[OrderIntent, ...] = Field(default_factory=tuple)
    spent_setup_ids: tuple[str, ...] = Field(default_factory=tuple)


class BrokerOrderSnapshot(ImmutableModel):
    broker_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: PositiveFloat
    stop_price: PositiveFloat | None = None
    limit_price: PositiveFloat | None = None
    status: BrokerOrderStatus
    created_at: datetime | None = None


class BrokerSubmitResult(ImmutableModel):
    accepted: bool
    reused_existing: bool
    order: BrokerOrderSnapshot | None = None
    reason: str | None = None


class BrokerCancelResult(ImmutableModel):
    cancelled: bool
    order: BrokerOrderSnapshot | None = None
    reason: str | None = None


class ReconciliationResult(ImmutableModel):
    matched_intent_ids: tuple[str, ...] = Field(default_factory=tuple)
    recovered_intent_ids: tuple[str, ...] = Field(default_factory=tuple)
    terminalized_intent_ids: tuple[str, ...] = Field(default_factory=tuple)
    unmatched_broker_order_ids: tuple[str, ...] = Field(default_factory=tuple)
    ambiguous_intent_ids: tuple[str, ...] = Field(default_factory=tuple)
    missing_broker_order_intent_ids: tuple[str, ...] = Field(default_factory=tuple)


class MonitoringAlert(ImmutableModel):
    alert_type: MonitoringAlertType
    severity: AlertSeverity
    message: str
    triggered_at: datetime
    kill_switch_active: bool
    symbol: str | None = None
    broker_order_id: str | None = None
    metric_value: float | None = None
    threshold_value: float | None = None


class MonitoringReport(ImmutableModel):
    alerts: tuple[MonitoringAlert, ...] = Field(default_factory=tuple)
    kill_switch_active: bool


class OrderStateSynchronization(ImmutableModel):
    recovery_state: RestartRecoveryState
    reconciliation_result: ReconciliationResult
    monitoring_report: MonitoringReport


class PendingEntryCheck(ImmutableModel):
    official_open_next: PositiveFloat | None = None
    regular_sessions_elapsed: NonNegativeInt = 0
    regime_state: RegimeState | None = None
    earnings_window_breached: bool = False
    shared_setup_preconditions_pass: bool = True
    intent_invalidated: bool = False
    fill_confirmed: bool = False
    hard_eligible_after_cancel: bool = True
    candidate_eligible_after_cancel: bool = False


class PositionSnapshot(ImmutableModel):
    symbol: str
    quantity: PositiveFloat
    average_price: PositiveFloat
    market_price: PositiveFloat
    unrealized_pnl: float
    sector: str | None = None


class PortfolioSnapshot(ImmutableModel):
    as_of: datetime
    equity: PositiveFloat
    cash: NonNegativeFloat
    positions: tuple[PositionSnapshot, ...] = Field(default_factory=tuple)


class ProtectedPosition(ImmutableModel):
    symbol: str
    quantity: PositiveFloat
    entry_reference_price: PositiveFloat
    protective_stop: PositiveFloat
    sector: str | None = None


class HistoricalPortfolioLifecyclePositionSnapshot(ImmutableModel):
    position_id: str
    symbol: str
    session_date: date
    state: SymbolLifecycleState
    quantity: PositiveFloat
    entry_price: PositiveFloat
    market_price: PositiveFloat
    initial_stop: PositiveFloat
    current_stop: PositiveFloat
    highest_high_since_entry: PositiveFloat
    unrealized_pnl: float
    unrealized_pnl_pct: float
    risk_amount: NonNegativeFloat
    sector: str | None = None
    setup_id: str | None = None
    order_intent_id: str | None = None
    opened_session: date | None = None
    planned_exit_session: date | None = None


class HistoricalPortfolioLifecyclePendingOrderSnapshot(ImmutableModel):
    order_intent_id: str
    symbol: str
    session_date: date
    status: OrderIntentStatus
    side: OrderSide
    order_type: OrderType
    quantity: PositiveFloat
    stop_price: PositiveFloat | None = None
    limit_price: PositiveFloat | None = None
    setup_id: str | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None
    cancel_reason: PendingEntryCancelReason | str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class HistoricalPortfolioLifecycleExposureSnapshot(ImmutableModel):
    session_date: date
    equity: PositiveFloat
    cash: NonNegativeFloat
    gross_exposure: NonNegativeFloat
    net_exposure: float
    portfolio_heat: NonNegativeFloat
    daily_new_risk: NonNegativeFloat
    open_position_count: NonNegativeInt
    pending_entry_count: NonNegativeInt
    sector_exposure: dict[str, NonNegativeFloat] = Field(default_factory=dict)
    symbol_exposure: dict[str, NonNegativeFloat] = Field(default_factory=dict)


class HistoricalPortfolioLifecycleTransition(ImmutableModel):
    transition_id: str
    symbol: str
    session_date: date
    from_state: SymbolLifecycleState
    to_state: SymbolLifecycleState
    trigger: str
    config_hash: str
    setup_id: str | None = None
    order_intent_id: str | None = None
    position_id: str | None = None
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    evidence: dict[str, Any] = Field(default_factory=dict)


class HistoricalTradeLedgerRow(ImmutableModel):
    trade_id: str
    symbol: str
    setup_id: str
    position_id: str
    entry_signal_date: date
    entry_fill_date: date
    exit_fill_date: date
    entry_reference_price: PositiveFloat
    entry_fill_price: PositiveFloat
    exit_reference_price: PositiveFloat
    exit_fill_price: PositiveFloat
    quantity: PositiveInt
    entry_regime_state: RegimeState
    exit_regime_state: RegimeState
    exit_reason: OrderReason
    bars_held: NonNegativeInt
    initial_stop: PositiveFloat
    final_stop: PositiveFloat
    entry_transaction_cost: NonNegativeFloat
    exit_transaction_cost: NonNegativeFloat
    total_transaction_cost: NonNegativeFloat
    gross_pnl: float
    gross_return: float
    net_pnl: float
    net_return: float
    sector: str | None = None
    source: str = "BACKTEST_TRADE"


class HistoricalPortfolioLifecycleSessionState(ImmutableModel):
    session_date: date
    cash: NonNegativeFloat
    equity: PositiveFloat
    open_position_count: NonNegativeInt
    pending_entry_count: NonNegativeInt
    exit_pending_count: NonNegativeInt
    portfolio_heat: NonNegativeFloat
    daily_new_risk: NonNegativeFloat
    sector_exposure: dict[str, NonNegativeFloat] = Field(default_factory=dict)
    candidate_count: NonNegativeInt
    setup_count: NonNegativeInt
    entry_submitted_count: NonNegativeInt
    entry_filled_count: NonNegativeInt
    entry_cancelled_count: NonNegativeInt
    exit_submitted_count: NonNegativeInt
    exit_filled_count: NonNegativeInt
    stop_updated_count: NonNegativeInt
    blocked_reason_counts: dict[str, NonNegativeInt] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _exit_pending_requires_active_position(
        self,
    ) -> HistoricalPortfolioLifecycleSessionState:
        if self.exit_pending_count > self.open_position_count:
            msg = "exit_pending_count cannot exceed open_position_count"
            raise ValueError(msg)
        return self


class HistoricalPortfolioLifecycleReconciliation(ImmutableModel):
    status: ReviewStatus
    checked_at: datetime
    session_count: NonNegativeInt
    transition_count: NonNegativeInt
    position_snapshot_count: NonNegativeInt
    pending_order_snapshot_count: NonNegativeInt
    exposure_snapshot_count: NonNegativeInt
    difference_count: NonNegativeInt = 0
    reason_counts: dict[str, NonNegativeInt] = Field(default_factory=dict)
    failures: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class HistoricalPortfolioLifecycleReplaySummary(ImmutableModel):
    panel_id: str
    manifest_path: str
    config_hash: str
    status: ReviewStatus
    started_at: datetime
    completed_at: datetime | None = None
    replay_start_session: date
    replay_end_session: date
    initial_equity: PositiveFloat
    final_equity: PositiveFloat
    final_cash: NonNegativeFloat
    processed_session_count: NonNegativeInt
    transition_count: NonNegativeInt
    position_snapshot_count: NonNegativeInt
    pending_order_snapshot_count: NonNegativeInt
    exposure_snapshot_count: NonNegativeInt
    entry_submitted_count: NonNegativeInt
    entry_filled_count: NonNegativeInt
    entry_cancelled_count: NonNegativeInt
    exit_submitted_count: NonNegativeInt
    exit_filled_count: NonNegativeInt
    max_open_position_count: NonNegativeInt
    max_pending_entry_count: NonNegativeInt
    max_portfolio_heat: NonNegativeFloat
    reconciliation_status: ReviewStatus
    parity_difference_count: NonNegativeInt | None = None


class HistoricalPortfolioLifecycleArtifactManifest(ImmutableModel):
    panel_id: str
    run_id: str
    output_dir: str
    lifecycle_replay_summary_path: str
    lifecycle_session_states_path: str
    lifecycle_transitions_path: str
    lifecycle_positions_path: str
    lifecycle_trade_ledger_path: str | None = None
    lifecycle_pending_orders_path: str
    lifecycle_exposure_path: str
    lifecycle_reconciliation_path: str
    lifecycle_baseline_package_path: str
    lifecycle_artifact_manifest_path: str
    lifecycle_parity_report_path: str | None = None


class EntryPlan(ImmutableModel):
    setup: SetupSnapshot
    approved: bool
    reject_reasons: tuple[str, ...] = Field(default_factory=tuple)
    quantity: NonNegativeInt
    base_risk_budget: NonNegativeFloat
    regime_risk_budget: NonNegativeFloat
    effective_risk_budget: NonNegativeFloat
    shares_from_risk: NonNegativeInt
    shares_from_notional: NonNegativeInt
    projected_portfolio_heat: NonNegativeFloat
    projected_daily_new_risk: NonNegativeFloat
    projected_sector_gross_exposure: NonNegativeFloat
    order_intent: OrderIntent | None


class PortfolioEntryBatch(ImmutableModel):
    plans: tuple[EntryPlan, ...] = Field(default_factory=tuple)
    approved_count: NonNegativeInt
    rejected_count: NonNegativeInt
    batch_new_risk_amount: NonNegativeFloat
    projected_portfolio_heat: NonNegativeFloat
    projected_daily_new_risk: NonNegativeFloat


class EntrySubmissionOutcome(ImmutableModel):
    symbol: str
    setup_id: str
    approved: bool
    submitted: bool
    intent_id: str | None = None
    broker_order_id: str | None = None
    reused_existing_broker_order: bool = False
    reject_reasons: tuple[str, ...] = Field(default_factory=tuple)


class EntrySubmissionBatch(ImmutableModel):
    synchronization: OrderStateSynchronization
    portfolio_batch: PortfolioEntryBatch
    blocked_spent_setup_ids: tuple[str, ...] = Field(default_factory=tuple)
    submissions: tuple[EntrySubmissionOutcome, ...] = Field(default_factory=tuple)


class ShadowSubmissionOutcome(ImmutableModel):
    symbol: str
    setup_id: str
    approved: bool
    would_submit: bool
    intent_id: str | None = None
    hypothetical_intent: OrderIntent | None = None
    reject_reasons: tuple[str, ...] = Field(default_factory=tuple)


class ShadowEntryBatch(ImmutableModel):
    as_of: datetime
    regime_state: RegimeState
    synchronization: OrderStateSynchronization
    portfolio_batch: PortfolioEntryBatch
    blocked_spent_setup_ids: tuple[str, ...] = Field(default_factory=tuple)
    proposals: tuple[ShadowSubmissionOutcome, ...] = Field(default_factory=tuple)


class ShadowFillComparison(ImmutableModel):
    snapshot_id: str | None = None
    symbol: str
    setup_id: str
    intent_id: str
    recorded_at: datetime | None = None
    source_as_of: datetime | None = None
    source_regime_state: RegimeState | None = None
    session_date: date | None = None
    status: ShadowFillStatus
    would_fill: bool
    would_remain_pending: bool
    would_mark_setup_spent: bool
    official_open: PositiveFloat | None = None
    reference_price: PositiveFloat | None = None
    hypothetical_fill_price: PositiveFloat | None = None
    transaction_cost: NonNegativeFloat | None = None
    total_cost_bps: NonNegativeFloat | None = None
    slippage_alert: MonitoringAlert | None = None
    detail: str | None = None


class ShadowFillComparisonBatch(ImmutableModel):
    source_mode: RuntimeMode
    source_as_of: datetime | None = None
    source_regime_state: RegimeState | None = None
    source_proposal_count: NonNegativeInt
    compared_proposal_count: NonNegativeInt
    skipped_proposal_count: NonNegativeInt
    comparisons: tuple[ShadowFillComparison, ...] = Field(default_factory=tuple)
    alerts: tuple[MonitoringAlert, ...] = Field(default_factory=tuple)
    filled_count: NonNegativeInt
    unfilled_count: NonNegativeInt
    cancelled_count: NonNegativeInt
    missing_market_data_count: NonNegativeInt


class PaperShadowAuditRecord(ImmutableModel):
    snapshot_id: str | None = None
    snapshot_batch_id: str | None = None
    recorded_at: datetime | None = None
    intent_id: str
    symbol: str
    setup_id: str | None = None
    created_at: datetime | None = None
    source_as_of: datetime | None = None
    source_regime_state: RegimeState | None = None
    alignment_status: PaperShadowAlignmentStatus
    paper_intent_present: bool
    paper_intent_status: OrderIntentStatus | None = None
    broker_order_id: str | None = None
    paper_broker_status: BrokerOrderStatus | None = None
    paper_filled: bool
    shadow_present: bool
    shadow_status: ShadowFillStatus | None = None
    shadow_would_fill: bool | None = None
    shadow_session_date: date | None = None
    shadow_hypothetical_fill_price: PositiveFloat | None = None
    shadow_total_cost_bps: NonNegativeFloat | None = None
    shadow_slippage_alert_triggered: bool


class RollingAuditWindow(ImmutableModel):
    label: str
    lookback_days: PositiveInt
    date_from: date
    date_to: date


class RollingAuditWindowReport(ImmutableModel):
    window: RollingAuditWindow
    shadow_review: dict[str, Any] = Field(default_factory=dict)
    paper_shadow_audit: dict[str, Any] = Field(default_factory=dict)
    recent_divergences: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    recent_shadow_alerts: tuple[dict[str, Any], ...] = Field(default_factory=tuple)


class RollingAuditReport(ImmutableModel):
    generated_at: datetime
    as_of_date: date
    symbol: str | None = None
    regime_state: RegimeState | None = None
    windows: tuple[RollingAuditWindowReport, ...] = Field(default_factory=tuple)


class OperatorReviewThresholds(ImmutableModel):
    min_alignment_rate: Percent = 0.95
    max_divergent_count: NonNegativeInt = 0
    max_shadow_slippage_alert_rate: Percent = 0.0
    max_missing_market_data_count: NonNegativeInt = 0
    require_runtime_runs: bool = True
    require_decision_events: bool = True
    require_shadow_snapshots: bool = True
    require_paper_shadow_audit_snapshots: bool = True


class OperatorReviewCheck(ImmutableModel):
    status: ReviewStatus
    category: str
    message: str
    observed: float | int | str | bool | None = None
    threshold: float | int | str | bool | None = None
    window: str | None = None


class OperatorReviewReport(ImmutableModel):
    generated_at: datetime
    as_of_date: date
    symbol: str | None = None
    regime_state: RegimeState | None = None
    review_status: ReviewStatus = ReviewStatus.PASS
    review_thresholds: OperatorReviewThresholds = Field(default_factory=OperatorReviewThresholds)
    review_checks: tuple[OperatorReviewCheck, ...] = Field(default_factory=tuple)
    lookback_days: tuple[PositiveInt, ...] = Field(default_factory=tuple)
    rolling_audit: RollingAuditReport
    runtime_runs: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    runtime_events: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    decision_events: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    shadow_comparison_snapshots: dict[str, Any] = Field(default_factory=dict)
    paper_shadow_audit_snapshots: dict[str, Any] = Field(default_factory=dict)
    replay_artifacts: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    recent_divergences: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    recent_shadow_alerts: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    review_exceptions: tuple[dict[str, Any], ...] = Field(default_factory=tuple)


class HistoricalPanelFileSpec(ImmutableModel):
    path: str
    format: str = "csv"
    row_count: NonNegativeInt | None = None
    sha256: str | None = None


class HistoricalPanelFiles(ImmutableModel):
    ohlcv: HistoricalPanelFileSpec
    symbol_reference: HistoricalPanelFileSpec
    corporate_actions: HistoricalPanelFileSpec
    earnings_events: HistoricalPanelFileSpec
    features: HistoricalPanelFileSpec | None = None


HistoricalFeatureCoverageScope = Literal["all_ohlcv", "tradable_reference"]


class HistoricalPanelManifest(ImmutableModel):
    panel_id: str
    schema_version: str
    created_at: datetime
    description: str | None = None
    base_path: str | None = None
    calendar: str
    timezone: str
    start_session: date
    end_session: date
    feature_start_session: date | None = None
    replay_start_session: date | None = None
    replay_end_session: date | None = None
    feature_coverage_scope: HistoricalFeatureCoverageScope = "all_ohlcv"
    expected_symbol_count: NonNegativeInt | None = None
    expected_session_count: NonNegativeInt | None = None
    files: HistoricalPanelFiles


class HistoricalPanelValidationIssue(ImmutableModel):
    code: str
    message: str
    file_key: str | None = None
    path: str | None = None
    field: str | None = None
    symbol: str | None = None
    session_date: date | None = None


class HistoricalPanelFileSummary(ImmutableModel):
    file_key: str
    path: str
    row_count: NonNegativeInt
    symbol_count: NonNegativeInt
    start_session: date | None = None
    end_session: date | None = None


class HistoricalPanelValidationResult(ImmutableModel):
    panel_id: str
    manifest_path: str
    status: ReviewStatus
    errors: tuple[HistoricalPanelValidationIssue, ...] = Field(default_factory=tuple)
    warnings: tuple[HistoricalPanelValidationIssue, ...] = Field(default_factory=tuple)
    file_summaries: tuple[HistoricalPanelFileSummary, ...] = Field(default_factory=tuple)
    symbol_count: NonNegativeInt
    session_count: NonNegativeInt
    start_session: date | None = None
    end_session: date | None = None
    validated_at: datetime


class HistoricalReplayProofResult(ImmutableModel):
    panel_id: str
    manifest_path: str
    status: ReviewStatus
    validation: HistoricalPanelValidationResult
    signal_session: date | None = None
    next_session: date | None = None
    setup_ids: tuple[str, ...] = Field(default_factory=tuple)
    setup_symbols: tuple[str, ...] = Field(default_factory=tuple)
    backtest_event_types: tuple[str, ...] = Field(default_factory=tuple)
    shadow_status_counts: dict[str, NonNegativeInt] = Field(default_factory=dict)
    audit_alignment_counts: dict[str, NonNegativeInt] = Field(default_factory=dict)
    stage_summaries: tuple[dict[str, Any], ...] = Field(default_factory=tuple)


class HistoricalReplayDecisionTrace(ImmutableModel):
    panel_id: str
    symbol: str
    session_date: date
    decision: str
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    setup_id: str | None = None
    pattern_type: str | None = None
    universe_eligible: bool | None = None
    rankable: bool | None = None
    is_candidate: bool | None = None
    setup_valid: bool | None = None
    candidate_score_pct: float | None = None
    candidate_score_threshold_pct: float | None = None
    trend_quality: float | None = None
    min_trend_quality: float | None = None


class HistoricalReplayReconciliationCheck(ImmutableModel):
    name: str
    status: ReviewStatus
    observed: int | float | str | bool | None = None
    expected: int | float | str | bool | None = None
    detail: str | None = None


class HistoricalReplayReconciliationSummary(ImmutableModel):
    status: ReviewStatus
    counts: dict[str, NonNegativeInt] = Field(default_factory=dict)
    checks: tuple[HistoricalReplayReconciliationCheck, ...] = Field(default_factory=tuple)


class HistoricalReplayRunResult(ImmutableModel):
    panel_id: str
    manifest_path: str
    config_hash: str
    status: ReviewStatus
    validation: HistoricalPanelValidationResult
    started_at: datetime
    completed_at: datetime
    signal_session: date | None = None
    next_session: date | None = None
    feature_adapter: str = "proof_derived_from_ohlcv_v1"
    setup_ids: tuple[str, ...] = Field(default_factory=tuple)
    setup_symbols: tuple[str, ...] = Field(default_factory=tuple)
    backtest_event_types: tuple[str, ...] = Field(default_factory=tuple)
    shadow_status_counts: dict[str, NonNegativeInt] = Field(default_factory=dict)
    audit_alignment_counts: dict[str, NonNegativeInt] = Field(default_factory=dict)
    decision_traces: tuple[HistoricalReplayDecisionTrace, ...] = Field(default_factory=tuple)
    reconciliation: HistoricalReplayReconciliationSummary | None = None
    stage_summaries: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    baseline_candidates: tuple[Any, ...] = Field(default_factory=tuple)
    baseline_signals: tuple[Any, ...] = Field(default_factory=tuple)
    baseline_risk_plans: tuple[Any, ...] = Field(default_factory=tuple)
    baseline_order_plans: tuple[Any, ...] = Field(default_factory=tuple)


class HistoricalScannerReplayDensityMetrics(ImmutableModel):
    decision_trace_count: NonNegativeInt = 0
    candidate_count: NonNegativeInt = 0
    accepted_setup_count: NonNegativeInt = 0
    rejected_decision_count: NonNegativeInt = 0
    signal_count: NonNegativeInt = 0
    risk_plan_count: NonNegativeInt = 0
    order_plan_count: NonNegativeInt = 0
    backtest_event_count: NonNegativeInt = 0
    shadow_proposal_count: NonNegativeInt = 0
    paper_submission_count: NonNegativeInt = 0
    reason_counts: dict[str, NonNegativeInt] = Field(default_factory=dict)


class HistoricalScannerReplaySessionResult(ImmutableModel):
    panel_id: str
    signal_session: date
    next_session: date
    status: ReviewStatus
    validation_status: ReviewStatus
    reconciliation_status: ReviewStatus
    symbol_count: NonNegativeInt
    density: HistoricalScannerReplayDensityMetrics
    accepted_setup_symbols: tuple[str, ...] = Field(default_factory=tuple)
    skipped: bool = False
    skip_reason: str | None = None
    material_decision_rows: tuple[dict[str, Any], ...] = Field(default_factory=tuple)


class HistoricalScannerReplayStateSnapshot(ImmutableModel):
    signal_session: date
    open_position_count: NonNegativeInt = 0
    pending_entry_count: NonNegativeInt = 0
    spent_setup_count: NonNegativeInt = 0
    open_symbols: tuple[str, ...] = Field(default_factory=tuple)
    pending_symbols: tuple[str, ...] = Field(default_factory=tuple)
    spent_setup_ids: tuple[str, ...] = Field(default_factory=tuple)


class HistoricalScannerReplaySummary(ImmutableModel):
    panel_id: str
    manifest_path: str
    config_hash: str
    status: ReviewStatus
    started_at: datetime
    completed_at: datetime
    replay_start_session: date
    replay_end_session: date
    eligible_signal_session_count: NonNegativeInt
    processed_signal_session_count: NonNegativeInt
    skipped_session_count: NonNegativeInt = 0
    total_decision_traces: NonNegativeInt = 0
    total_candidates: NonNegativeInt = 0
    total_setups: NonNegativeInt = 0
    total_rejections: NonNegativeInt = 0
    sessions_with_setups: NonNegativeInt = 0
    sessions_without_setups: NonNegativeInt = 0
    average_candidates_per_session: NonNegativeFloat = 0.0
    average_setups_per_session: NonNegativeFloat = 0.0
    max_setups_per_session: NonNegativeInt = 0
    parity_difference_count: NonNegativeInt | None = None
    session_results: tuple[HistoricalScannerReplaySessionResult, ...] = Field(
        default_factory=tuple
    )


class HistoricalScannerReplayArtifactManifest(ImmutableModel):
    panel_id: str
    run_id: str
    output_dir: str
    scanner_replay_summary_path: str
    scanner_session_results_path: str
    scanner_decision_density_path: str
    scanner_rejection_reasons_path: str
    scanner_material_decisions_path: str
    scanner_baseline_report_package_path: str
    scanner_parity_report_path: str | None = None
    scanner_runtime_database_path: str | None = None


class ManagedPosition(ImmutableModel):
    symbol: str
    quantity: PositiveFloat
    entry_fill_price: PositiveFloat
    atr_at_entry: PositiveFloat
    current_stop: PositiveFloat
    highest_high_since_entry: PositiveFloat
    bars_since_entry: NonNegativeInt
    regular_closes_until_earnings_event: NonNegativeInt | None = None


class ExitEvaluation(ImmutableModel):
    symbol: str
    current_stop: PositiveFloat
    updated_stop: PositiveFloat
    trailing_active: bool
    effective_trailing_multiple: PositiveFloat | None
    progress_atr: NonNegativeFloat
    time_stop_triggered: bool
    earnings_exit_triggered: bool
    should_submit_exit_intent: bool
    discretionary_exit_reasons: tuple[OrderReason, ...] = Field(default_factory=tuple)


class PendingEntryEvaluation(ImmutableModel):
    symbol: str
    setup_id: str | None
    should_cancel: bool
    cancel_reasons: tuple[PendingEntryCancelReason, ...] = Field(default_factory=tuple)
    expired: bool
    mark_setup_spent: bool
    next_state: SymbolLifecycleState


class PendingEntryAction(ImmutableModel):
    intent_id: str
    symbol: str
    setup_id: str | None = None
    evaluation: PendingEntryEvaluation
    broker_cancelled: bool
    broker_cancel_reason: str | None = None
    terminal_status: OrderIntentStatus | None = None
    setup_marked_spent: bool


class PendingEntryBatchResult(ImmutableModel):
    synchronization: OrderStateSynchronization
    actions: tuple[PendingEntryAction, ...] = Field(default_factory=tuple)


class RuntimeCycleInput(ImmutableModel):
    as_of: datetime
    regime_state: RegimeState
    equity: PositiveFloat
    expires_at: datetime | None = None
    last_data_at: datetime | None = None
    day_start_equity: PositiveFloat | None = None
    current_equity: NonNegativeFloat | None = None
    broker_available: bool = True
    setups: tuple[SetupSnapshot, ...] = Field(default_factory=tuple)
    pending_entry_checks: dict[str, PendingEntryCheck] = Field(default_factory=dict)
    open_positions: tuple[ProtectedPosition, ...] = Field(default_factory=tuple)
    submitted_today_risk_amount: NonNegativeFloat = 0.0
    sector_by_symbol: dict[str, str | None] = Field(default_factory=dict)
    vol_target_size_multiplier: NonNegativeFloat | None = None


class RuntimeCycleResult(ImmutableModel):
    mode: RuntimeMode
    pending_entry_batch: PendingEntryBatchResult | None = None
    paper_entry_batch: EntrySubmissionBatch | None = None
    shadow_entry_batch: ShadowEntryBatch | None = None


class BacktestEvent(ImmutableModel):
    session_date: date
    symbol: str
    event_type: str
    setup_id: str | None = None
    state: SymbolLifecycleState | None = None
    order_reason: OrderReason | None = None
    detail: str | None = None


class BacktestTrade(ImmutableModel):
    symbol: str
    setup_id: str
    entry_signal_date: date
    entry_fill_date: date
    entry_reference_price: PositiveFloat
    entry_fill_price: PositiveFloat
    exit_fill_date: date
    exit_reference_price: PositiveFloat
    exit_fill_price: PositiveFloat
    quantity: PositiveInt
    entry_regime_state: RegimeState
    exit_regime_state: RegimeState
    exit_reason: OrderReason
    bars_held: NonNegativeInt
    initial_stop: PositiveFloat
    final_stop: PositiveFloat
    entry_transaction_cost: NonNegativeFloat
    exit_transaction_cost: NonNegativeFloat
    total_transaction_cost: NonNegativeFloat
    gross_pnl: float
    gross_return: float
    net_pnl: float
    net_return: float
    sector: str | None = None


class BacktestEquityPoint(ImmutableModel):
    session_date: date
    equity: NonNegativeFloat
    cash: float
    open_positions: NonNegativeInt
    pending_entries: NonNegativeInt


class BacktestResult(ImmutableModel):
    initial_equity: PositiveFloat
    final_equity: NonNegativeFloat
    trades: tuple[BacktestTrade, ...] = Field(default_factory=tuple)
    equity_curve: tuple[BacktestEquityPoint, ...] = Field(default_factory=tuple)
    events: tuple[BacktestEvent, ...] = Field(default_factory=tuple)
    spent_setup_ids: tuple[str, ...] = Field(default_factory=tuple)
    pending_order_snapshots: tuple[
        HistoricalPortfolioLifecyclePendingOrderSnapshot, ...
    ] = Field(default_factory=tuple)
    position_snapshots: tuple[
        HistoricalPortfolioLifecyclePositionSnapshot, ...
    ] = Field(default_factory=tuple)


class HistoricalEquityCurvePoint(ImmutableModel):
    session_date: date
    equity: NonNegativeFloat
    cash: float
    open_position_count: NonNegativeInt
    pending_entry_count: NonNegativeInt
    daily_return: float | None = None
    cumulative_return: float
    running_peak_equity: NonNegativeFloat
    drawdown: float
    portfolio_heat: NonNegativeFloat = 0.0
    daily_new_risk: NonNegativeFloat = 0.0


class HistoricalDrawdownRecord(ImmutableModel):
    start_date: date
    trough_date: date
    recovery_date: date | None = None
    peak_equity: NonNegativeFloat
    trough_equity: NonNegativeFloat
    drawdown: float
    duration_sessions: NonNegativeInt
    recovered: bool


class HistoricalTradeMetrics(ImmutableModel):
    closed_trade_count: NonNegativeInt
    winning_trade_count: NonNegativeInt
    losing_trade_count: NonNegativeInt
    win_rate: Percent | None = None
    gross_pnl: float
    net_pnl: float
    average_net_pnl: float | None = None
    average_net_return: float | None = None
    median_net_return: float | None = None
    best_net_return: float | None = None
    worst_net_return: float | None = None
    profit_factor: NonNegativeFloat | None = None
    expectancy: float | None = None
    average_bars_held: NonNegativeFloat | None = None
    total_transaction_cost: NonNegativeFloat = 0.0
    source: str
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class HistoricalBenchmarkComparison(ImmutableModel):
    benchmark_symbol: str
    start_date: date
    end_date: date
    benchmark_start_close: PositiveFloat
    benchmark_end_close: PositiveFloat
    strategy_total_return: float
    benchmark_total_return: float
    excess_return: float
    strategy_max_drawdown: float
    benchmark_max_drawdown: float
    daily_return_correlation: float | None = None


class HistoricalConcentrationReport(ImmutableModel):
    max_open_position_count: NonNegativeInt
    max_pending_entry_count: NonNegativeInt
    max_portfolio_heat: NonNegativeFloat
    max_daily_new_risk: NonNegativeFloat
    max_single_sector_exposure_pct_equity: NonNegativeFloat | None = None
    max_single_sector_exposure_sector: str | None = None
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class HistoricalCostScenarioResult(ImmutableModel):
    scenario_id: str
    additional_cost_bps: NonNegativeFloat
    estimated_total_additional_cost: NonNegativeFloat
    estimated_final_equity: NonNegativeFloat
    estimated_total_return: float
    delta_vs_base_equity: float
    delta_vs_base_return: float


class HistoricalCostSensitivityReport(ImmutableModel):
    cost_source: str
    base_total_transaction_cost: NonNegativeFloat
    base_final_equity: NonNegativeFloat
    base_total_return: float
    estimated_turnover: NonNegativeFloat = 0.0
    scenarios: tuple[HistoricalCostScenarioResult, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class HistoricalBreakdownBucketMetrics(ImmutableModel):
    trade_count: NonNegativeInt
    winning_trade_count: NonNegativeInt
    losing_trade_count: NonNegativeInt
    win_rate: Percent | None = None
    gross_pnl: float
    net_pnl: float
    average_net_return: float | None = None
    total_transaction_cost: NonNegativeFloat


class HistoricalBreakdownReport(ImmutableModel):
    monthly_returns: dict[str, float] = Field(default_factory=dict)
    yearly_returns: dict[str, float] = Field(default_factory=dict)
    by_entry_regime: dict[str, HistoricalBreakdownBucketMetrics] = Field(
        default_factory=dict
    )
    by_exit_reason: dict[str, HistoricalBreakdownBucketMetrics] = Field(default_factory=dict)
    by_sector: dict[str, HistoricalBreakdownBucketMetrics] = Field(default_factory=dict)
    by_setup_type: dict[str, HistoricalBreakdownBucketMetrics] = Field(default_factory=dict)
    by_ranking_bucket: dict[str, HistoricalBreakdownBucketMetrics] = Field(
        default_factory=dict
    )
    missing_breakdowns: tuple[str, ...] = Field(default_factory=tuple)


class HistoricalPerformanceSummary(ImmutableModel):
    panel_id: str
    run_id: str
    generated_at: datetime
    source_artifact_dir: str
    status: ReviewStatus
    start_date: date
    end_date: date
    session_count: PositiveInt
    initial_equity: PositiveFloat
    final_equity: NonNegativeFloat
    total_return: float
    cagr: float | None = None
    annualized_volatility: NonNegativeFloat | None = None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    max_drawdown: float
    max_drawdown_start_date: date | None = None
    max_drawdown_trough_date: date | None = None
    max_drawdown_recovery_date: date | None = None
    trade_metrics: HistoricalTradeMetrics
    concentration: HistoricalConcentrationReport
    cost_sensitivity: HistoricalCostSensitivityReport
    benchmark_comparison: HistoricalBenchmarkComparison | None = None
    breakdown: HistoricalBreakdownReport
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class HistoricalPerformanceReport(ImmutableModel):
    summary: HistoricalPerformanceSummary
    equity_curve: tuple[HistoricalEquityCurvePoint, ...]
    drawdown_records: tuple[HistoricalDrawdownRecord, ...] = Field(default_factory=tuple)


class ProviderPerformanceLeg(ImmutableModel):
    provider: str
    summary_path: str
    panel_id: str
    status: ReviewStatus
    start_date: date
    end_date: date
    session_count: PositiveInt
    total_return: float
    max_drawdown: float
    closed_trade_count: NonNegativeInt
    net_pnl: float
    benchmark_total_return: float | None = None
    excess_return: float | None = None
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class ProviderPerformanceComparisonReport(ImmutableModel):
    comparison_id: str
    generated_at: datetime
    status: ReviewStatus
    left: ProviderPerformanceLeg
    right: ProviderPerformanceLeg
    total_return_delta: float
    max_drawdown_delta: float
    closed_trade_count_delta: int
    net_pnl_delta: float
    excess_return_delta: float | None = None
    blockers: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class MechanicalReadinessEvidence(ImmutableModel):
    evidence_id: str
    evidence_type: str
    path: str
    status: ReviewStatus
    run_id: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)


class MechanicalReadinessCheck(ImmutableModel):
    check_id: str
    category: str
    status: ReviewStatus
    observed: Any = None
    expected: Any = None
    severity: Literal["INFO", "WARNING", "BLOCKER"]
    message: str


class MechanicalReadinessDecision(ImmutableModel):
    baseline_id: str
    run_id: str
    generated_at: datetime
    status: ReviewStatus
    decision: Literal["PASS", "WARN", "BLOCK"]
    profile_alias_path: str
    manifest_path: str
    config_hash: str | None = None
    evidence: tuple[MechanicalReadinessEvidence, ...] = Field(default_factory=tuple)
    checks: tuple[MechanicalReadinessCheck, ...] = Field(default_factory=tuple)
    blockers: tuple[str, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    next_required_actions: tuple[str, ...] = Field(default_factory=tuple)


class LookaheadAuditViolation(ImmutableModel):
    code: str
    symbol: str | None = None
    session_date: date | None = None
    field: str | None = None
    observed: Any = None
    expected: Any = None
    message: str


class LookaheadAuditReport(ImmutableModel):
    panel_id: str
    manifest_path: str
    status: ReviewStatus
    checked_at: datetime
    feature_window_check: ReviewStatus
    symbol_reference_check: ReviewStatus
    earnings_timing_check: ReviewStatus
    session_order_check: ReviewStatus
    violations: tuple[LookaheadAuditViolation, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class HistoricalDataQualityIssue(ImmutableModel):
    code: str
    severity: Literal["INFO", "WARNING", "BLOCKER"]
    symbol: str | None = None
    session_date: date | None = None
    field: str | None = None
    observed: Any = None
    expected: Any = None
    message: str


class HistoricalDataQualitySymbolSummary(ImmutableModel):
    symbol: str
    ohlcv_row_count: NonNegativeInt
    first_session: date | None = None
    last_session: date | None = None
    missing_session_count: NonNegativeInt = 0
    duplicate_ohlcv_row_count: NonNegativeInt = 0
    invalid_ohlc_row_count: NonNegativeInt = 0
    negative_volume_row_count: NonNegativeInt = 0
    zero_volume_row_count: NonNegativeInt = 0
    feature_row_count: NonNegativeInt = 0
    missing_feature_session_count: NonNegativeInt = 0


class HistoricalDataQualityReport(ImmutableModel):
    panel_id: str
    manifest_path: str
    status: ReviewStatus
    checked_at: datetime
    calendar: str
    source_start_session: date | None = None
    source_end_session: date | None = None
    replay_start_session: date | None = None
    replay_end_session: date | None = None
    symbol_count: NonNegativeInt
    session_count: NonNegativeInt
    ohlcv_row_count: NonNegativeInt
    feature_row_count: NonNegativeInt = 0
    coverage_check: ReviewStatus
    duplicate_check: ReviewStatus
    price_volume_check: ReviewStatus
    benchmark_coverage_check: ReviewStatus
    survivorship_check: ReviewStatus
    benchmark_symbol: str | None = None
    issues: tuple[HistoricalDataQualityIssue, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)
    symbol_summaries: tuple[HistoricalDataQualitySymbolSummary, ...] = Field(
        default_factory=tuple
    )


class FeatureOutcomeAttributionRow(ImmutableModel):
    panel_id: str
    symbol: str
    signal_session: date
    next_session: date | None = None
    candidate_id: str | None = None
    setup_id: str | None = None
    signal_id: str | None = None
    risk_plan_id: str | None = None
    order_plan_id: str | None = None
    decision: str
    pattern_type: str | None = None
    candidate_score_pct: float | None = None
    rank: NonNegativeInt | None = None
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    rejection_reasons: tuple[str, ...] = Field(default_factory=tuple)
    traded: bool = False
    trade_id: str | None = None
    entry_fill_date: date | None = None
    exit_fill_date: date | None = None
    exit_reason: str | None = None
    bars_held: NonNegativeInt | None = None
    net_pnl: float | None = None
    net_return: float | None = None
    forward_close_returns: dict[str, float | None] = Field(default_factory=dict)
    benchmark_forward_close_returns: dict[str, float | None] = Field(default_factory=dict)
    forward_close_excess_returns: dict[str, float | None] = Field(default_factory=dict)
    feature_snapshot: dict[str, Any] = Field(default_factory=dict)


class FeatureOutcomeAttributionSummary(ImmutableModel):
    panel_id: str
    generated_at: datetime
    source_scanner_material_decisions_path: str
    source_lifecycle_trade_ledger_path: str | None = None
    source_manifest_path: str
    source_feature_snapshot_path: str | None = None
    benchmark_symbol: str | None = None
    feature_snapshot_fields: tuple[str, ...] = Field(default_factory=tuple)
    row_count: NonNegativeInt
    accepted_count: NonNegativeInt
    rejected_count: NonNegativeInt
    traded_count: NonNegativeInt
    forward_windows: tuple[PositiveInt, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class FeatureOutcomeAttributionDataset(ImmutableModel):
    summary: FeatureOutcomeAttributionSummary
    rows: tuple[FeatureOutcomeAttributionRow, ...] = Field(default_factory=tuple)


class FeatureOutcomeSubsetMetrics(ImmutableModel):
    row_count: NonNegativeInt
    average_forward_returns: dict[str, float | None] = Field(default_factory=dict)
    median_forward_returns: dict[str, float | None] = Field(default_factory=dict)
    positive_forward_return_rates: dict[str, float | None] = Field(default_factory=dict)
    average_forward_excess_returns: dict[str, float | None] = Field(default_factory=dict)
    median_forward_excess_returns: dict[str, float | None] = Field(default_factory=dict)
    positive_forward_excess_return_rates: dict[str, float | None] = Field(
        default_factory=dict
    )
    trade_count: NonNegativeInt = 0
    winning_trade_count: NonNegativeInt = 0
    losing_trade_count: NonNegativeInt = 0
    trade_win_rate: Percent | None = None
    net_pnl: float | None = None
    average_net_pnl: float | None = None
    average_net_return: float | None = None
    median_net_return: float | None = None


class FeatureOutcomeBucketMetrics(ImmutableModel):
    bucket_id: str
    row_count: NonNegativeInt
    accepted_count: NonNegativeInt
    rejected_count: NonNegativeInt
    traded_count: NonNegativeInt
    sample_grade: Literal["ROBUST", "EXPLORATORY", "INSUFFICIENT"]
    sample_warnings: tuple[str, ...] = Field(default_factory=tuple)
    average_forward_returns: dict[str, float | None] = Field(default_factory=dict)
    median_forward_returns: dict[str, float | None] = Field(default_factory=dict)
    positive_forward_return_rates: dict[str, float | None] = Field(default_factory=dict)
    average_forward_excess_returns: dict[str, float | None] = Field(default_factory=dict)
    median_forward_excess_returns: dict[str, float | None] = Field(default_factory=dict)
    positive_forward_excess_return_rates: dict[str, float | None] = Field(
        default_factory=dict
    )
    accepted_only: FeatureOutcomeSubsetMetrics
    traded_only: FeatureOutcomeSubsetMetrics


class AcceptedVersusNearMissReport(ImmutableModel):
    report_id: str
    generated_at: datetime
    status: ReviewStatus
    source_dataset_path: str
    row_count: NonNegativeInt
    near_miss_definition: str
    accepted: FeatureOutcomeBucketMetrics
    rejected: FeatureOutcomeBucketMetrics
    near_miss: FeatureOutcomeBucketMetrics
    by_score_bucket: dict[str, FeatureOutcomeBucketMetrics] = Field(default_factory=dict)
    by_rejection_reason: dict[str, FeatureOutcomeBucketMetrics] = Field(default_factory=dict)
    conclusion: str
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class FeatureSnapshotBucketReport(ImmutableModel):
    report_id: str
    generated_at: datetime
    status: ReviewStatus
    source_dataset_path: str
    row_count: NonNegativeInt
    bucket_fields: tuple[str, ...] = Field(default_factory=tuple)
    sample_guardrails: dict[str, NonNegativeInt] = Field(default_factory=dict)
    by_feature_bucket: dict[str, dict[str, FeatureOutcomeBucketMetrics]] = Field(
        default_factory=dict
    )
    conclusion: str
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class FeatureOutcomeDistributionMetrics(ImmutableModel):
    population_id: str
    window: PositiveInt
    row_count: NonNegativeInt
    observed_count: NonNegativeInt
    mean: float | None = None
    median: float | None = None
    p10: float | None = None
    p25: float | None = None
    p75: float | None = None
    p90: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    positive_rate: Percent | None = None


class AcceptedCandidateExcessDistributionReport(ImmutableModel):
    report_id: str
    generated_at: datetime
    status: ReviewStatus
    source_dataset_path: str
    near_miss_definition: str
    populations: dict[str, dict[str, FeatureOutcomeDistributionMetrics]] = Field(
        default_factory=dict
    )
    conclusion: str
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class TradedLifecycleGroupMetrics(ImmutableModel):
    group_id: str
    trade_count: NonNegativeInt
    symbol_count: NonNegativeInt
    setup_count: NonNegativeInt
    winning_trade_count: NonNegativeInt
    losing_trade_count: NonNegativeInt
    win_rate: Percent | None = None
    net_pnl: float
    average_net_pnl: float | None = None
    average_net_return: float | None = None
    median_net_return: float | None = None
    average_bars_held: NonNegativeFloat | None = None
    exit_reason_counts: dict[str, NonNegativeInt] = Field(default_factory=dict)
    average_forward_excess_returns: dict[str, float | None] = Field(default_factory=dict)
    positive_forward_excess_return_rates: dict[str, float | None] = Field(
        default_factory=dict
    )


class TradedLifecycleOutcomeDecompositionReport(ImmutableModel):
    report_id: str
    generated_at: datetime
    status: ReviewStatus
    source_dataset_path: str
    trade_count: NonNegativeInt
    overall: TradedLifecycleGroupMetrics
    by_setup_type: dict[str, TradedLifecycleGroupMetrics] = Field(default_factory=dict)
    by_exit_reason: dict[str, TradedLifecycleGroupMetrics] = Field(default_factory=dict)
    by_bars_held_bucket: dict[str, TradedLifecycleGroupMetrics] = Field(
        default_factory=dict
    )
    by_feature_bucket: dict[str, dict[str, TradedLifecycleGroupMetrics]] = Field(
        default_factory=dict
    )
    conclusion: str
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class ExitPathTradeDiagnostic(ImmutableModel):
    trade_id: str | None = None
    symbol: str
    setup_id: str | None = None
    pattern_type: str | None = None
    exit_reason: str | None = None
    bars_held: NonNegativeInt | None = None
    net_pnl: float | None = None
    net_return: float | None = None
    winner: bool
    post_exit_forward_returns: dict[str, float | None] = Field(default_factory=dict)
    post_exit_benchmark_returns: dict[str, float | None] = Field(default_factory=dict)
    post_exit_excess_returns: dict[str, float | None] = Field(default_factory=dict)
    diagnostic_flags: tuple[str, ...] = Field(default_factory=tuple)


class ExitPathDiagnosticReport(ImmutableModel):
    report_id: str
    generated_at: datetime
    status: ReviewStatus
    source_dataset_path: str
    source_manifest_path: str
    benchmark_symbol: str | None = None
    trade_count: NonNegativeInt
    winner_count: NonNegativeInt
    loser_count: NonNegativeInt
    exit_reason_counts: dict[str, NonNegativeInt] = Field(default_factory=dict)
    diagnostic_flag_counts: dict[str, NonNegativeInt] = Field(default_factory=dict)
    trades: tuple[ExitPathTradeDiagnostic, ...] = Field(default_factory=tuple)
    conclusion: str
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class PatternSpecificBenchmarkDiagnostic(ImmutableModel):
    pattern_type: str
    row_count: NonNegativeInt
    accepted_count: NonNegativeInt
    rejected_count: NonNegativeInt
    traded_count: NonNegativeInt
    sample_grade: Literal["ROBUST", "EXPLORATORY", "INSUFFICIENT"]
    sample_warnings: tuple[str, ...] = Field(default_factory=tuple)
    all_rows: FeatureOutcomeBucketMetrics
    accepted_only: FeatureOutcomeSubsetMetrics
    rejected_only: FeatureOutcomeSubsetMetrics
    traded_lifecycle: TradedLifecycleGroupMetrics
    exit_reason_counts: dict[str, NonNegativeInt] = Field(default_factory=dict)
    recommendation: str
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class PatternSpecificBenchmarkDiagnosticReport(ImmutableModel):
    report_id: str
    generated_at: datetime
    status: ReviewStatus
    source_dataset_path: str
    benchmark_symbol: str | None = None
    row_count: NonNegativeInt
    pattern_count: NonNegativeInt
    sample_guardrails: dict[str, NonNegativeInt] = Field(default_factory=dict)
    patterns: dict[str, PatternSpecificBenchmarkDiagnostic] = Field(default_factory=dict)
    conclusion: str
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class DecisionLedgerRow(ImmutableModel):
    ledger_id: str
    panel_id: str
    symbol: str
    signal_session: date | None = None
    next_session: date | None = None
    setup_id: str | None = None
    decision: str
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    candidate_score_pct: float | None = None
    rank: NonNegativeInt | None = None
    signal_id: str | None = None
    risk_plan_id: str | None = None
    order_plan_id: str | None = None
    order_intent_id: str | None = None
    position_id: str | None = None
    lifecycle_state: str | None = None
    entry_submitted: bool = False
    entry_filled: bool = False
    entry_cancelled: bool = False
    exit_submitted: bool = False
    exit_filled: bool = False
    trade_closed: bool = False
    missing_links: tuple[str, ...] = Field(default_factory=tuple)


class DecisionLedgerReport(ImmutableModel):
    panel_id: str
    run_id: str
    status: ReviewStatus
    generated_at: datetime
    row_count: NonNegativeInt
    accepted_setup_count: NonNegativeInt
    rejected_candidate_count: NonNegativeInt
    missing_link_count: NonNegativeInt
    rows: tuple[DecisionLedgerRow, ...] = Field(default_factory=tuple)
    warnings: tuple[str, ...] = Field(default_factory=tuple)


class WalkForwardWindow(ImmutableModel):
    window_index: NonNegativeInt
    train_start_date: date
    train_end_date: date
    test_start_date: date
    test_end_date: date
    train_sessions: PositiveInt
    test_sessions: PositiveInt
    anchored: bool


class WalkForwardWindowResult(ImmutableModel):
    window: WalkForwardWindow
    config_hash: str
    train_candidate_fingerprint: str | None = None
    test_candidate_fingerprint: str | None = None
    backtest_fingerprint: str
    trade_count: NonNegativeInt
    final_equity: NonNegativeFloat
    gross_pnl: float
    net_pnl: float
    max_drawdown: float


class ParameterSweepRun(ImmutableModel):
    run_index: NonNegativeInt
    overrides: dict[str, object] = Field(default_factory=dict)
    config_hash: str
    backtest_fingerprint: str
    trade_count: NonNegativeInt
    final_equity: NonNegativeFloat
    gross_pnl: float
    net_pnl: float
    max_drawdown: float
