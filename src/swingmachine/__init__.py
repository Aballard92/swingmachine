"""Swingmachine package."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__version__ = "0.1.0"

_EXPORTS: dict[str, tuple[str, str]] = {
    "BrokerAdapter": ("swingmachine.broker", "BrokerAdapter"),
    "MonitoringService": ("swingmachine.monitoring", "MonitoringService"),
    "PaperBrokerAdapter": ("swingmachine.broker", "PaperBrokerAdapter"),
    "OrderIntentService": ("swingmachine.order_intents", "OrderIntentService"),
    "OrderStateMachine": ("swingmachine.order_state_machine", "OrderStateMachine"),
    "OperatorReviewThresholds": (
        "swingmachine.contracts",
        "OperatorReviewThresholds",
    ),
    "PaperShadowAuditService": (
        "swingmachine.paper_shadow_audit",
        "PaperShadowAuditService",
    ),
    "PortfolioManager": ("swingmachine.portfolio_manager", "PortfolioManager"),
    "ReconciliationService": (
        "swingmachine.reconciliation",
        "ReconciliationService",
    ),
    "ShadowReviewService": ("swingmachine.shadow_reviews", "ShadowReviewService"),
    "StrategyRuntimeConfig": ("swingmachine.config", "StrategyRuntimeConfig"),
    "TradingRuntime": ("swingmachine.runtime", "TradingRuntime"),
    "apply_execution_cost": ("swingmachine.execution_model", "apply_execution_cost"),
    "apply_config_overrides": ("swingmachine.research", "apply_config_overrides"),
    "adverse_slippage_bps": ("swingmachine.monitoring", "adverse_slippage_bps"),
    "backtest_result_fingerprint": (
        "swingmachine.research",
        "backtest_result_fingerprint",
    ),
    "build_paper_shadow_audit_service": (
        "swingmachine.runtime",
        "build_paper_shadow_audit_service",
    ),
    "build_historical_performance_report": (
        "swingmachine.performance",
        "build_historical_performance_report",
    ),
    "build_historical_data_quality_report": (
        "swingmachine.data_quality",
        "build_historical_data_quality_report",
    ),
    "build_feature_outcome_attribution_dataset": (
        "swingmachine.feature_outcomes",
        "build_feature_outcome_attribution_dataset",
    ),
    "build_accepted_vs_near_miss_report": (
        "swingmachine.feature_outcomes",
        "build_accepted_vs_near_miss_report",
    ),
    "build_feature_snapshot_bucket_report": (
        "swingmachine.feature_outcomes",
        "build_feature_snapshot_bucket_report",
    ),
    "build_accepted_excess_distribution_report": (
        "swingmachine.feature_outcomes",
        "build_accepted_excess_distribution_report",
    ),
    "build_traded_lifecycle_decomposition_report": (
        "swingmachine.feature_outcomes",
        "build_traded_lifecycle_decomposition_report",
    ),
    "build_exit_path_diagnostic_report": (
        "swingmachine.feature_outcomes",
        "build_exit_path_diagnostic_report",
    ),
    "build_pattern_specific_benchmark_diagnostic_report": (
        "swingmachine.feature_outcomes",
        "build_pattern_specific_benchmark_diagnostic_report",
    ),
    "build_provider_performance_comparison_report": (
        "swingmachine.performance",
        "build_provider_performance_comparison_report",
    ),
    "build_operator_review_report_service": (
        "swingmachine.runtime",
        "build_operator_review_report_service",
    ),
    "build_rolling_audit_report_service": (
        "swingmachine.runtime",
        "build_rolling_audit_report_service",
    ),
    "build_runtime": ("swingmachine.runtime", "build_runtime"),
    "build_runtime_run_history": (
        "swingmachine.runtime",
        "build_runtime_run_history",
    ),
    "build_canonical_price_frame": (
        "swingmachine.canonical",
        "build_canonical_price_frame",
    ),
    "build_walk_forward_windows": (
        "swingmachine.research",
        "build_walk_forward_windows",
    ),
    "candidate_ranking_fingerprint": (
        "swingmachine.research",
        "candidate_ranking_fingerprint",
    ),
    "build_setup_snapshot": ("swingmachine.entries", "build_setup_snapshot"),
    "build_setup_snapshots": ("swingmachine.entries", "build_setup_snapshots"),
    "classify_regimes": ("swingmachine.regime", "classify_regimes"),
    "compute_breadth_by_session": (
        "swingmachine.regime",
        "compute_breadth_by_session",
    ),
    "compute_core_features": ("swingmachine.features", "compute_core_features"),
    "compute_regime_inputs": ("swingmachine.regime", "compute_regime_inputs"),
    "compute_regime_snapshots": ("swingmachine.regime", "compute_regime_snapshots"),
    "compute_updated_stop": ("swingmachine.exits", "compute_updated_stop"),
    "compute_universe_eligibility": (
        "swingmachine.signals",
        "compute_universe_eligibility",
    ),
    "classify_symbol_state": ("swingmachine.lifecycle", "classify_symbol_state"),
    "paper_shadow_alignment_stats": (
        "swingmachine.analytics",
        "paper_shadow_alignment_stats",
    ),
    "paper_shadow_audit_to_frame": (
        "swingmachine.analytics",
        "paper_shadow_audit_to_frame",
    ),
    "paper_shadow_regime_stats": (
        "swingmachine.analytics",
        "paper_shadow_regime_stats",
    ),
    "shadow_fill_comparisons_to_frame": (
        "swingmachine.analytics",
        "shadow_fill_comparisons_to_frame",
    ),
    "shadow_fill_regime_stats": (
        "swingmachine.analytics",
        "shadow_fill_regime_stats",
    ),
    "shadow_fill_status_stats": (
        "swingmachine.analytics",
        "shadow_fill_status_stats",
    ),
    "detect_setups": ("swingmachine.signals", "detect_setups"),
    "duplicate_entry_submission_keys": (
        "swingmachine.research",
        "duplicate_entry_submission_keys",
    ),
    "earnings_exit_triggered": ("swingmachine.exits", "earnings_exit_triggered"),
    "execution_cost_bps": ("swingmachine.execution_model", "execution_cost_bps"),
    "evaluate_exit_position": ("swingmachine.exits", "evaluate_exit_position"),
    "evaluate_pending_entry": ("swingmachine.lifecycle", "evaluate_pending_entry"),
    "compare_next_session_shadow_fills": (
        "swingmachine.shadow",
        "compare_next_session_shadow_fills",
    ),
    "compare_runtime_cycle_shadow_fills": (
        "swingmachine.shadow",
        "compare_runtime_cycle_shadow_fills",
    ),
    "create_database_engine": ("swingmachine.storage", "create_database_engine"),
    "create_session_factory": ("swingmachine.storage", "create_session_factory"),
    "create_sqlite_engine": ("swingmachine.storage", "create_sqlite_engine"),
    "initialize_database": ("swingmachine.storage", "initialize_database"),
    "load_market_data_frame": ("swingmachine.runtime", "load_market_data_frame"),
    "load_benchmark_price_rows_from_manifest": (
        "swingmachine.performance",
        "load_benchmark_price_rows_from_manifest",
    ),
    "load_strategy_config": ("swingmachine.config", "load_strategy_config"),
    "load_runtime_cycle_input": ("swingmachine.runtime", "load_runtime_cycle_input"),
    "load_runtime_cycle_result": (
        "swingmachine.runtime",
        "load_runtime_cycle_result",
    ),
    "validate_next_session_market_data": (
        "swingmachine.data_contracts",
        "validate_next_session_market_data",
    ),
    "validate_symbol_reference_data": (
        "swingmachine.data_contracts",
        "validate_symbol_reference_data",
    ),
    "validate_corporate_actions_data": (
        "swingmachine.data_contracts",
        "validate_corporate_actions_data",
    ),
    "validate_earnings_events_data": (
        "swingmachine.data_contracts",
        "validate_earnings_events_data",
    ),
    "make_entry_order_intent": ("swingmachine.entries", "make_entry_order_intent"),
    "pending_entry_expired": ("swingmachine.lifecycle", "pending_entry_expired"),
    "plan_entry": ("swingmachine.entries", "plan_entry"),
    "portfolio_heat": ("swingmachine.entries", "portfolio_heat"),
    "reserved_position_from_plan": (
        "swingmachine.portfolio_manager",
        "reserved_position_from_plan",
    ),
    "progress_atr": ("swingmachine.exits", "progress_atr"),
    "regime_segmented_trade_stats": (
        "swingmachine.analytics",
        "regime_segmented_trade_stats",
    ),
    "RollingAuditReportService": (
        "swingmachine.reporting",
        "RollingAuditReportService",
    ),
    "OperatorReviewReportService": (
        "swingmachine.reporting",
        "OperatorReviewReportService",
    ),
    "RuntimeEventType": ("swingmachine.enums", "RuntimeEventType"),
    "RuntimeRunHistory": ("swingmachine.run_history", "RuntimeRunHistory"),
    "ReviewStatus": ("swingmachine.enums", "ReviewStatus"),
    "repeated_backtest_is_identical": (
        "swingmachine.research",
        "repeated_backtest_is_identical",
    ),
    "repeated_candidate_ranking_is_identical": (
        "swingmachine.research",
        "repeated_candidate_ranking_is_identical",
    ),
    "render_operator_review_html": (
        "swingmachine.review_rendering",
        "render_operator_review_html",
    ),
    "resolve_post_cancel_state": (
        "swingmachine.lifecycle",
        "resolve_post_cancel_state",
    ),
    "run_parameter_sweep": ("swingmachine.research", "run_parameter_sweep"),
    "run_backtest": ("swingmachine.backtest", "run_backtest"),
    "run_walk_forward_study": ("swingmachine.research", "run_walk_forward_study"),
    "score_candidates": ("swingmachine.signals", "score_candidates"),
    "sector_gross_exposure": ("swingmachine.entries", "sector_gross_exposure"),
    "setup_can_be_armed": ("swingmachine.lifecycle", "setup_can_be_armed"),
    "simulate_entry_fill": ("swingmachine.execution_model", "simulate_entry_fill"),
    "simulate_stop_fill": ("swingmachine.execution_model", "simulate_stop_fill"),
    "summarize_paper_shadow_audit": (
        "swingmachine.analytics",
        "summarize_paper_shadow_audit",
    ),
    "summarize_backtest": ("swingmachine.analytics", "summarize_backtest"),
    "summarize_shadow_fill_comparisons": (
        "swingmachine.analytics",
        "summarize_shadow_fill_comparisons",
    ),
    "time_stop_triggered": ("swingmachine.exits", "time_stop_triggered"),
    "trades_to_frame": ("swingmachine.analytics", "trades_to_frame"),
    "trailing_is_active": ("swingmachine.exits", "trailing_is_active"),
    "write_runtime_cycle_result": (
        "swingmachine.runtime",
        "write_runtime_cycle_result",
    ),
    "write_historical_performance_report": (
        "swingmachine.performance",
        "write_historical_performance_report",
    ),
    "write_provider_performance_comparison_report": (
        "swingmachine.performance",
        "write_provider_performance_comparison_report",
    ),
    "write_shadow_fill_comparison_batch": (
        "swingmachine.runtime",
        "write_shadow_fill_comparison_batch",
    ),
}

__all__ = [*_EXPORTS.keys(), "__version__"]


def __getattr__(name: str) -> Any:
    if name == "__version__":
        return __version__
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    module = import_module(module_name)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(__all__)
