from __future__ import annotations

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from swingmachine.contracts import (
    FeatureSnapshot,
    HistoricalPortfolioLifecycleArtifactManifest,
    HistoricalPortfolioLifecycleExposureSnapshot,
    HistoricalPortfolioLifecyclePendingOrderSnapshot,
    HistoricalPortfolioLifecyclePositionSnapshot,
    HistoricalPortfolioLifecycleReconciliation,
    HistoricalPortfolioLifecycleReplaySummary,
    HistoricalPortfolioLifecycleSessionState,
    HistoricalPortfolioLifecycleTransition,
    HistoricalScannerReplayArtifactManifest,
    HistoricalScannerReplayDensityMetrics,
    HistoricalScannerReplaySessionResult,
    HistoricalScannerReplaySummary,
    OrderIntent,
    SymbolDailyBar,
)
from swingmachine.enums import (
    EarningsEventSession,
    OrderIntentStatus,
    OrderReason,
    OrderSide,
    OrderType,
    PatternType,
    ReviewStatus,
    SessionType,
    SymbolLifecycleState,
)


def test_symbol_daily_bar_parses_contract_fields() -> None:
    bar = SymbolDailyBar(
        symbol="AAPL",
        session_date=date(2026, 4, 23),
        session_type=SessionType.REGULAR,
        raw_open=180.0,
        raw_high=182.5,
        raw_low=179.4,
        raw_close=181.8,
        raw_volume=12_500_000,
        split_adj_open=180.0,
        split_adj_high=182.5,
        split_adj_low=179.4,
        split_adj_close=181.8,
        split_adj_volume=12_500_000,
        cash_dividend_per_share=0.0,
        split_ratio=1.0,
        tr_close_index=143.2,
        currency="USD",
        exchange="NASDAQ",
        is_tradable=True,
    )

    assert bar.symbol == "AAPL"
    assert bar.session_type is SessionType.REGULAR


def test_feature_snapshot_supports_earnings_timing_fields() -> None:
    snapshot = FeatureSnapshot(
        symbol="MSFT",
        session_date=date(2026, 4, 23),
        ret_21=0.04,
        ret_63=0.12,
        ret_126=0.21,
        ret_252=0.33,
        mom_252_21=0.26,
        rs_vs_benchmark_126=0.08,
        ma20=412.0,
        ma50=405.0,
        ma200=360.0,
        ma50_slope_pct20=0.03,
        ma200_slope_pct20=0.02,
        atr_14=6.5,
        atr_5=5.8,
        atr_20=7.1,
        atr_pct=0.016,
        range_compression_ratio=0.81,
        dist_to_52w_high=0.04,
        pullback_days=6,
        pullback_depth_atr=1.2,
        volume_ratio_20=0.84,
        trend_quality=0.72,
        candidate_score_raw=1.83,
        candidate_score_pct=0.93,
        effective_candidate_score_threshold_pct=0.9,
        effective_min_trend_quality=0.6,
        pattern_type=PatternType.TIGHT_BASE,
        setup_id="setup-1",
        setup_start_date=date(2026, 4, 14),
        setup_end_date=date(2026, 4, 23),
        setup_high=415.0,
        setup_low=401.0,
        setup_high_date=date(2026, 4, 18),
        setup_low_date=date(2026, 4, 21),
        setup_valid=True,
        earnings_event_session=EarningsEventSession.POST_CLOSE,
        regular_closes_until_earnings_event=2,
    )

    assert snapshot.pattern_type is PatternType.TIGHT_BASE
    assert snapshot.regular_closes_until_earnings_event == 2


def test_order_intent_accepts_string_enums() -> None:
    intent = OrderIntent.model_validate(
        {
            "intent_id": "intent-1",
            "dedupe_key": "dedupe-1",
            "strategy_id": "RF_TPC_V2",
            "config_hash": "abc123",
            "symbol": "NVDA",
            "setup_id": "setup-1",
            "side": "BUY",
            "reason": "ENTRY",
            "order_type": "STOP_LIMIT",
            "quantity": 10,
            "stop_price": 101.5,
            "limit_price": 103.0,
            "created_at": datetime(2026, 4, 23, 16, 30),
            "expires_at": datetime(2026, 4, 24, 16, 0),
            "broker_order_id": None,
        }
    )

    assert intent.side is OrderSide.BUY
    assert intent.reason is OrderReason.ENTRY
    assert intent.order_type is OrderType.STOP_LIMIT


def test_historical_scanner_replay_contracts_capture_density() -> None:
    density = HistoricalScannerReplayDensityMetrics(
        decision_trace_count=32,
        candidate_count=12,
        accepted_setup_count=3,
        rejected_decision_count=20,
        signal_count=3,
        risk_plan_count=3,
        order_plan_count=3,
        backtest_event_count=4,
        shadow_proposal_count=3,
        paper_submission_count=3,
        reason_counts={"NO_PATTERN_VALID": 9},
    )
    session = HistoricalScannerReplaySessionResult(
        panel_id="panel-1",
        signal_session=date(2025, 7, 30),
        next_session=date(2025, 7, 31),
        status=ReviewStatus.PASS,
        validation_status=ReviewStatus.PASS,
        reconciliation_status=ReviewStatus.PASS,
        symbol_count=16,
        density=density,
        accepted_setup_symbols=("AAPL", "AMZN"),
    )
    summary = HistoricalScannerReplaySummary(
        panel_id="panel-1",
        manifest_path="manifest.yaml",
        config_hash="abc123",
        status=ReviewStatus.PASS,
        started_at=datetime(2026, 5, 6, 12, 0),
        completed_at=datetime(2026, 5, 6, 12, 30),
        replay_start_session=date(2025, 7, 1),
        replay_end_session=date(2025, 7, 31),
        eligible_signal_session_count=21,
        processed_signal_session_count=20,
        total_decision_traces=320,
        total_candidates=120,
        total_setups=18,
        total_rejections=302,
        sessions_with_setups=8,
        sessions_without_setups=12,
        average_candidates_per_session=6.0,
        average_setups_per_session=0.9,
        max_setups_per_session=3,
        parity_difference_count=0,
        session_results=(session,),
    )
    artifact_manifest = HistoricalScannerReplayArtifactManifest(
        panel_id="panel-1",
        run_id="run-1",
        output_dir="reports/run-1",
        scanner_replay_summary_path="reports/run-1/scanner_replay_summary.json",
        scanner_session_results_path="reports/run-1/scanner_session_results.json",
        scanner_decision_density_path="reports/run-1/scanner_decision_density.json",
        scanner_rejection_reasons_path="reports/run-1/scanner_rejection_reasons.json",
        scanner_material_decisions_path="reports/run-1/scanner_material_decisions.json",
        scanner_baseline_report_package_path=(
            "reports/run-1/scanner_baseline_report_package.json"
        ),
        scanner_parity_report_path="reports/run-1/scanner_parity_report.json",
    )

    assert summary.session_results[0].density.reason_counts["NO_PATTERN_VALID"] == 9
    assert summary.processed_signal_session_count == 20
    assert artifact_manifest.scanner_parity_report_path is not None


def test_historical_portfolio_lifecycle_contracts_capture_state() -> None:
    session_state = HistoricalPortfolioLifecycleSessionState(
        session_date=date(2025, 7, 30),
        cash=95_000.0,
        equity=101_250.0,
        open_position_count=2,
        pending_entry_count=1,
        exit_pending_count=1,
        portfolio_heat=0.024,
        daily_new_risk=0.01,
        sector_exposure={"Technology": 0.18},
        candidate_count=16,
        setup_count=3,
        entry_submitted_count=2,
        entry_filled_count=1,
        entry_cancelled_count=1,
        exit_submitted_count=1,
        exit_filled_count=0,
        stop_updated_count=2,
        blocked_reason_counts={"PORTFOLIO_HEAT": 1},
    )
    transition = HistoricalPortfolioLifecycleTransition(
        transition_id="transition-1",
        symbol="AAPL",
        session_date=date(2025, 7, 30),
        from_state=SymbolLifecycleState.PENDING_ENTRY,
        to_state=SymbolLifecycleState.ACTIVE,
        trigger="ENTRY_FILL",
        setup_id="setup-1",
        order_intent_id="intent-1",
        position_id="position-1",
        reason_codes=("ENTRY_TRIGGER_TOUCHED",),
        evidence={"fill_price": 101.25},
        config_hash="abc123",
    )
    position = HistoricalPortfolioLifecyclePositionSnapshot(
        position_id="position-1",
        symbol="AAPL",
        session_date=date(2025, 7, 30),
        state=SymbolLifecycleState.ACTIVE,
        quantity=10,
        entry_price=100.0,
        market_price=101.25,
        initial_stop=94.0,
        current_stop=96.5,
        highest_high_since_entry=103.0,
        unrealized_pnl=12.5,
        unrealized_pnl_pct=0.0125,
        risk_amount=60.0,
        sector="Technology",
        setup_id="setup-1",
        order_intent_id="intent-1",
        opened_session=date(2025, 7, 30),
    )
    pending_order = HistoricalPortfolioLifecyclePendingOrderSnapshot(
        order_intent_id="intent-2",
        symbol="MSFT",
        session_date=date(2025, 7, 30),
        status=OrderIntentStatus.ACTIVE,
        side=OrderSide.BUY,
        order_type=OrderType.STOP_LIMIT,
        quantity=5,
        stop_price=412.0,
        limit_price=416.0,
        setup_id="setup-2",
        evidence={"source": "fixture"},
    )
    exposure = HistoricalPortfolioLifecycleExposureSnapshot(
        session_date=date(2025, 7, 30),
        equity=101_250.0,
        cash=95_000.0,
        gross_exposure=6_250.0,
        net_exposure=6_250.0,
        portfolio_heat=0.024,
        daily_new_risk=0.01,
        open_position_count=2,
        pending_entry_count=1,
        sector_exposure={"Technology": 0.18},
        symbol_exposure={"AAPL": 0.06},
    )

    assert session_state.blocked_reason_counts["PORTFOLIO_HEAT"] == 1
    assert transition.to_state is SymbolLifecycleState.ACTIVE
    assert position.current_stop == 96.5
    assert pending_order.status is OrderIntentStatus.ACTIVE
    assert exposure.symbol_exposure["AAPL"] == 0.06


def test_historical_portfolio_lifecycle_rejects_impossible_exit_pending_count() -> None:
    with pytest.raises(ValidationError, match="exit_pending_count"):
        HistoricalPortfolioLifecycleSessionState(
            session_date=date(2025, 7, 30),
            cash=95_000.0,
            equity=101_250.0,
            open_position_count=1,
            pending_entry_count=0,
            exit_pending_count=2,
            portfolio_heat=0.024,
            daily_new_risk=0.01,
            candidate_count=16,
            setup_count=3,
            entry_submitted_count=2,
            entry_filled_count=1,
            entry_cancelled_count=1,
            exit_submitted_count=1,
            exit_filled_count=0,
            stop_updated_count=2,
        )


def test_historical_portfolio_lifecycle_summary_and_manifest_are_explicit() -> None:
    reconciliation = HistoricalPortfolioLifecycleReconciliation(
        status=ReviewStatus.PASS,
        checked_at=datetime(2026, 5, 6, 18, 0),
        session_count=20,
        transition_count=14,
        position_snapshot_count=8,
        pending_order_snapshot_count=6,
        exposure_snapshot_count=20,
        difference_count=0,
        reason_counts={"OK": 20},
    )
    summary = HistoricalPortfolioLifecycleReplaySummary(
        panel_id="panel-1",
        manifest_path="manifest.yaml",
        config_hash="abc123",
        status=ReviewStatus.PASS,
        started_at=datetime(2026, 5, 6, 17, 0),
        completed_at=datetime(2026, 5, 6, 18, 0),
        replay_start_session=date(2025, 7, 1),
        replay_end_session=date(2025, 7, 31),
        initial_equity=100_000.0,
        final_equity=101_250.0,
        final_cash=95_000.0,
        processed_session_count=20,
        transition_count=reconciliation.transition_count,
        position_snapshot_count=reconciliation.position_snapshot_count,
        pending_order_snapshot_count=reconciliation.pending_order_snapshot_count,
        exposure_snapshot_count=reconciliation.exposure_snapshot_count,
        entry_submitted_count=6,
        entry_filled_count=3,
        entry_cancelled_count=2,
        exit_submitted_count=1,
        exit_filled_count=1,
        max_open_position_count=3,
        max_pending_entry_count=2,
        max_portfolio_heat=0.045,
        reconciliation_status=reconciliation.status,
        parity_difference_count=0,
    )
    artifact_manifest = HistoricalPortfolioLifecycleArtifactManifest(
        panel_id="panel-1",
        run_id="run-1",
        output_dir="reports/run-1",
        lifecycle_replay_summary_path="reports/run-1/portfolio_lifecycle_replay_summary.json",
        lifecycle_session_states_path="reports/run-1/portfolio_lifecycle_session_states.json",
        lifecycle_transitions_path="reports/run-1/portfolio_lifecycle_transitions.json",
        lifecycle_positions_path="reports/run-1/portfolio_lifecycle_positions.json",
        lifecycle_pending_orders_path="reports/run-1/portfolio_lifecycle_pending_orders.json",
        lifecycle_exposure_path="reports/run-1/portfolio_lifecycle_exposure.json",
        lifecycle_reconciliation_path="reports/run-1/portfolio_lifecycle_reconciliation.json",
        lifecycle_baseline_package_path="reports/run-1/portfolio_lifecycle_baseline_package.json",
        lifecycle_artifact_manifest_path="reports/run-1/portfolio_lifecycle_artifact_manifest.json",
        lifecycle_parity_report_path="reports/run-1/portfolio_lifecycle_parity_report.json",
    )

    assert summary.reconciliation_status is ReviewStatus.PASS
    assert summary.parity_difference_count == 0
    assert artifact_manifest.lifecycle_parity_report_path is not None
