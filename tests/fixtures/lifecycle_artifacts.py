from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from swingmachine.contracts import (
    HistoricalPortfolioLifecycleArtifactManifest,
    HistoricalPortfolioLifecycleExposureSnapshot,
    HistoricalPortfolioLifecyclePendingOrderSnapshot,
    HistoricalPortfolioLifecyclePositionSnapshot,
    HistoricalPortfolioLifecycleReconciliation,
    HistoricalPortfolioLifecycleReplaySummary,
    HistoricalPortfolioLifecycleSessionState,
    HistoricalPortfolioLifecycleTransition,
)
from swingmachine.enums import (
    OrderIntentStatus,
    OrderSide,
    OrderType,
    ReviewStatus,
    SymbolLifecycleState,
)

FIXTURE_PANEL_ID = "panel-tier2-fixture"
FIXTURE_RUN_ID = "tier2-fixture-run"
FIXTURE_CONFIG_HASH = "tier2-config-hash"
FIXTURE_MANIFEST_PATH = "tests/fixtures/historical_panel/manifest.yaml"
FIXTURE_OUTPUT_DIR = "reports/swing_machine_v0_1/tier2_fixture_run"
FIXTURE_SESSION = date(2025, 7, 30)
FIXTURE_NEXT_SESSION = date(2025, 7, 31)
FIXTURE_STARTED_AT = datetime(2026, 5, 6, 17, 0)
FIXTURE_COMPLETED_AT = datetime(2026, 5, 6, 17, 5)


@dataclass(frozen=True)
class HistoricalPortfolioLifecycleFixturePackage:
    summary: HistoricalPortfolioLifecycleReplaySummary
    session_states: tuple[HistoricalPortfolioLifecycleSessionState, ...]
    transitions: tuple[HistoricalPortfolioLifecycleTransition, ...]
    positions: tuple[HistoricalPortfolioLifecyclePositionSnapshot, ...]
    pending_orders: tuple[HistoricalPortfolioLifecyclePendingOrderSnapshot, ...]
    exposure: tuple[HistoricalPortfolioLifecycleExposureSnapshot, ...]
    reconciliation: HistoricalPortfolioLifecycleReconciliation
    manifest: HistoricalPortfolioLifecycleArtifactManifest


def lifecycle_session_state_fixture(
    *,
    session_date: date = FIXTURE_SESSION,
    open_position_count: int = 1,
    pending_entry_count: int = 1,
    exit_pending_count: int = 0,
) -> HistoricalPortfolioLifecycleSessionState:
    return HistoricalPortfolioLifecycleSessionState(
        session_date=session_date,
        cash=97_500.0,
        equity=101_250.0,
        open_position_count=open_position_count,
        pending_entry_count=pending_entry_count,
        exit_pending_count=exit_pending_count,
        portfolio_heat=0.0275,
        daily_new_risk=0.01,
        sector_exposure={"Technology": 0.22},
        candidate_count=16,
        setup_count=3,
        entry_submitted_count=2,
        entry_filled_count=1,
        entry_cancelled_count=1,
        exit_submitted_count=0,
        exit_filled_count=0,
        stop_updated_count=1,
        blocked_reason_counts={"PORTFOLIO_HEAT": 1},
    )


def lifecycle_transition_fixtures() -> tuple[HistoricalPortfolioLifecycleTransition, ...]:
    return (
        HistoricalPortfolioLifecycleTransition(
            transition_id="transition-armed-to-pending",
            symbol="AAPL",
            session_date=FIXTURE_SESSION,
            from_state=SymbolLifecycleState.ARMED,
            to_state=SymbolLifecycleState.PENDING_ENTRY,
            trigger="ORDER_INTENT_CREATED",
            setup_id="setup-aapl-1",
            order_intent_id="intent-aapl-1",
            reason_codes=("SETUP_ACCEPTED",),
            evidence={"entry_trigger": 101.0, "entry_limit": 103.0},
            config_hash=FIXTURE_CONFIG_HASH,
        ),
        HistoricalPortfolioLifecycleTransition(
            transition_id="transition-pending-to-active",
            symbol="AAPL",
            session_date=FIXTURE_NEXT_SESSION,
            from_state=SymbolLifecycleState.PENDING_ENTRY,
            to_state=SymbolLifecycleState.ACTIVE,
            trigger="ENTRY_FILL",
            setup_id="setup-aapl-1",
            order_intent_id="intent-aapl-1",
            position_id="position-aapl-1",
            reason_codes=("ENTRY_TRIGGER_TOUCHED",),
            evidence={"fill_price": 101.25},
            config_hash=FIXTURE_CONFIG_HASH,
        ),
        HistoricalPortfolioLifecycleTransition(
            transition_id="transition-active-to-exit-pending",
            symbol="AAPL",
            session_date=FIXTURE_NEXT_SESSION,
            from_state=SymbolLifecycleState.ACTIVE,
            to_state=SymbolLifecycleState.EXIT_PENDING,
            trigger="TRAIL_STOP_EXIT_DECIDED",
            setup_id="setup-aapl-1",
            order_intent_id="exit-intent-aapl-1",
            position_id="position-aapl-1",
            reason_codes=("TRAILING_STOP_BREACHED",),
            evidence={"current_stop": 97.0},
            config_hash=FIXTURE_CONFIG_HASH,
        ),
        HistoricalPortfolioLifecycleTransition(
            transition_id="transition-active-blocked",
            symbol="MSFT",
            session_date=FIXTURE_SESSION,
            from_state=SymbolLifecycleState.CANDIDATE,
            to_state=SymbolLifecycleState.CANDIDATE,
            trigger="PORTFOLIO_GATE_BLOCKED",
            setup_id="setup-msft-1",
            reason_codes=("PORTFOLIO_HEAT",),
            evidence={"portfolio_heat_after_entry": 0.08},
            config_hash=FIXTURE_CONFIG_HASH,
        ),
    )


def lifecycle_position_snapshot_fixture() -> HistoricalPortfolioLifecyclePositionSnapshot:
    return HistoricalPortfolioLifecyclePositionSnapshot(
        position_id="position-aapl-1",
        symbol="AAPL",
        session_date=FIXTURE_NEXT_SESSION,
        state=SymbolLifecycleState.ACTIVE,
        quantity=10,
        entry_price=101.25,
        market_price=103.0,
        initial_stop=94.0,
        current_stop=97.0,
        highest_high_since_entry=104.0,
        unrealized_pnl=17.5,
        unrealized_pnl_pct=0.0173,
        risk_amount=72.5,
        sector="Technology",
        setup_id="setup-aapl-1",
        order_intent_id="intent-aapl-1",
        opened_session=FIXTURE_NEXT_SESSION,
    )


def lifecycle_pending_order_snapshot_fixture() -> (
    HistoricalPortfolioLifecyclePendingOrderSnapshot
):
    return HistoricalPortfolioLifecyclePendingOrderSnapshot(
        order_intent_id="intent-msft-1",
        symbol="MSFT",
        session_date=FIXTURE_SESSION,
        status=OrderIntentStatus.ACTIVE,
        side=OrderSide.BUY,
        order_type=OrderType.STOP_LIMIT,
        quantity=5,
        stop_price=412.0,
        limit_price=416.0,
        setup_id="setup-msft-1",
        created_at=FIXTURE_STARTED_AT,
        expires_at=FIXTURE_COMPLETED_AT,
        evidence={"source": "tier2_fixture"},
    )


def lifecycle_exposure_snapshot_fixture() -> HistoricalPortfolioLifecycleExposureSnapshot:
    return HistoricalPortfolioLifecycleExposureSnapshot(
        session_date=FIXTURE_NEXT_SESSION,
        equity=101_250.0,
        cash=97_500.0,
        gross_exposure=3_750.0,
        net_exposure=3_750.0,
        portfolio_heat=0.0275,
        daily_new_risk=0.01,
        open_position_count=1,
        pending_entry_count=1,
        sector_exposure={"Technology": 0.22},
        symbol_exposure={"AAPL": 0.0102, "MSFT": 0.0205},
    )


def lifecycle_reconciliation_fixture(
    *,
    status: ReviewStatus = ReviewStatus.PASS,
) -> HistoricalPortfolioLifecycleReconciliation:
    return HistoricalPortfolioLifecycleReconciliation(
        status=status,
        checked_at=FIXTURE_COMPLETED_AT,
        session_count=2,
        transition_count=4,
        position_snapshot_count=1,
        pending_order_snapshot_count=1,
        exposure_snapshot_count=1,
        difference_count=0,
        reason_counts={"OK": 2},
    )


def lifecycle_replay_summary_fixture(
    *,
    reconciliation_status: ReviewStatus = ReviewStatus.PASS,
) -> HistoricalPortfolioLifecycleReplaySummary:
    return HistoricalPortfolioLifecycleReplaySummary(
        panel_id=FIXTURE_PANEL_ID,
        manifest_path=FIXTURE_MANIFEST_PATH,
        config_hash=FIXTURE_CONFIG_HASH,
        status=ReviewStatus.PASS,
        started_at=FIXTURE_STARTED_AT,
        completed_at=FIXTURE_COMPLETED_AT,
        replay_start_session=FIXTURE_SESSION,
        replay_end_session=FIXTURE_NEXT_SESSION,
        initial_equity=100_000.0,
        final_equity=101_250.0,
        final_cash=97_500.0,
        processed_session_count=2,
        transition_count=4,
        position_snapshot_count=1,
        pending_order_snapshot_count=1,
        exposure_snapshot_count=1,
        entry_submitted_count=2,
        entry_filled_count=1,
        entry_cancelled_count=1,
        exit_submitted_count=1,
        exit_filled_count=0,
        max_open_position_count=1,
        max_pending_entry_count=1,
        max_portfolio_heat=0.0275,
        reconciliation_status=reconciliation_status,
        parity_difference_count=0,
    )


def lifecycle_artifact_manifest_fixture() -> (
    HistoricalPortfolioLifecycleArtifactManifest
):
    return HistoricalPortfolioLifecycleArtifactManifest(
        panel_id=FIXTURE_PANEL_ID,
        run_id=FIXTURE_RUN_ID,
        output_dir=FIXTURE_OUTPUT_DIR,
        lifecycle_replay_summary_path=(
            f"{FIXTURE_OUTPUT_DIR}/portfolio_lifecycle_replay_summary.json"
        ),
        lifecycle_session_states_path=(
            f"{FIXTURE_OUTPUT_DIR}/portfolio_lifecycle_session_states.json"
        ),
        lifecycle_transitions_path=(
            f"{FIXTURE_OUTPUT_DIR}/portfolio_lifecycle_transitions.json"
        ),
        lifecycle_positions_path=(
            f"{FIXTURE_OUTPUT_DIR}/portfolio_lifecycle_positions.json"
        ),
        lifecycle_pending_orders_path=(
            f"{FIXTURE_OUTPUT_DIR}/portfolio_lifecycle_pending_orders.json"
        ),
        lifecycle_exposure_path=(
            f"{FIXTURE_OUTPUT_DIR}/portfolio_lifecycle_exposure.json"
        ),
        lifecycle_reconciliation_path=(
            f"{FIXTURE_OUTPUT_DIR}/portfolio_lifecycle_reconciliation.json"
        ),
        lifecycle_baseline_package_path=(
            f"{FIXTURE_OUTPUT_DIR}/portfolio_lifecycle_baseline_package.json"
        ),
        lifecycle_artifact_manifest_path=(
            f"{FIXTURE_OUTPUT_DIR}/portfolio_lifecycle_artifact_manifest.json"
        ),
        lifecycle_parity_report_path=(
            f"{FIXTURE_OUTPUT_DIR}/portfolio_lifecycle_parity_report.json"
        ),
    )


def lifecycle_artifact_package_fixture() -> (
    HistoricalPortfolioLifecycleFixturePackage
):
    return HistoricalPortfolioLifecycleFixturePackage(
        summary=lifecycle_replay_summary_fixture(),
        session_states=(lifecycle_session_state_fixture(),),
        transitions=lifecycle_transition_fixtures(),
        positions=(lifecycle_position_snapshot_fixture(),),
        pending_orders=(lifecycle_pending_order_snapshot_fixture(),),
        exposure=(lifecycle_exposure_snapshot_fixture(),),
        reconciliation=lifecycle_reconciliation_fixture(),
        manifest=lifecycle_artifact_manifest_fixture(),
    )
