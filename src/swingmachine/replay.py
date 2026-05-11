from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import pandas as pd

from swingmachine.backtest import run_backtest
from swingmachine.baseline import (
    build_swing_baseline_manifest,
    load_swing_selected_qualification_plan,
)
from swingmachine.baseline_parity import (
    SwingBaselineParityDifference,
    SwingBaselineParityReport,
)
from swingmachine.baseline_readiness import (
    evaluate_serious_full_run_freeze_readiness,
    write_freeze_readiness_decision_json,
)
from swingmachine.baseline_reporting import (
    build_baseline_report_package,
    write_baseline_report_package_json,
)
from swingmachine.config import StrategyRuntimeConfig
from swingmachine.contracts import (
    BacktestResult,
    HistoricalPortfolioLifecycleArtifactManifest,
    HistoricalPortfolioLifecycleExposureSnapshot,
    HistoricalPortfolioLifecyclePendingOrderSnapshot,
    HistoricalPortfolioLifecyclePositionSnapshot,
    HistoricalPortfolioLifecycleReconciliation,
    HistoricalPortfolioLifecycleReplaySummary,
    HistoricalPortfolioLifecycleSessionState,
    HistoricalPortfolioLifecycleTransition,
    HistoricalReplayDecisionTrace,
    HistoricalReplayProofResult,
    HistoricalReplayReconciliationCheck,
    HistoricalReplayReconciliationSummary,
    HistoricalReplayRunResult,
    HistoricalScannerReplayArtifactManifest,
    HistoricalScannerReplayDensityMetrics,
    HistoricalScannerReplaySessionResult,
    HistoricalScannerReplaySummary,
    HistoricalTradeLedgerRow,
    RuntimeCycleInput,
)
from swingmachine.data_contracts import (
    HistoricalPanelData,
    active_symbol_reference_rows,
    expected_feature_coverage_rows,
    load_historical_panel_data,
    symbol_reference_rows_for_sessions,
    validate_historical_panel_manifest,
)
from swingmachine.entries import build_setup_snapshots
from swingmachine.enums import RegimeState, ReviewStatus, RuntimeMode, SymbolLifecycleState
from swingmachine.portfolio_manager import PortfolioManager
from swingmachine.runtime import (
    build_paper_shadow_audit_service,
    build_runtime,
    build_shadow_review_service,
)
from swingmachine.shadow import compare_runtime_cycle_shadow_fills
from swingmachine.signals import detect_setups, score_candidates
from swingmachine.swing_adapters import (
    swing_candidates_from_scored_frame,
    swing_order_plan_from_entry_plan,
    swing_risk_plan_from_entry_plan,
    swing_signal_from_setup_snapshot,
)
from swingmachine.swing_contracts import SwingOrderPlan, SwingRiskPlan, SwingSignal


@dataclass(frozen=True)
class _SelectedReplaySessionWindow:
    sessions: tuple[date, ...]
    signal_session: date
    next_session: date


@dataclass(frozen=True)
class _SelectedSessionReplayContext:
    signal_session: date
    next_session: date
    feature_panel: pd.DataFrame
    feature_adapter: str
    regime_frame: pd.DataFrame
    scored: pd.DataFrame
    detected: pd.DataFrame
    decision_traces: tuple[HistoricalReplayDecisionTrace, ...]
    setups: tuple[Any, ...]
    replay_detected: pd.DataFrame
    replay_regime_frame: pd.DataFrame
    cycle_input: RuntimeCycleInput
    baseline_candidates: tuple[Any, ...]
    baseline_signals: tuple[Any, ...]
    baseline_risk_plans: tuple[Any, ...]
    baseline_order_plans: tuple[Any, ...]


@dataclass(frozen=True)
class HistoricalPortfolioLifecycleArtifactPackage:
    summary: HistoricalPortfolioLifecycleReplaySummary
    session_states: tuple[HistoricalPortfolioLifecycleSessionState, ...]
    transitions: tuple[HistoricalPortfolioLifecycleTransition, ...]
    positions: tuple[HistoricalPortfolioLifecyclePositionSnapshot, ...]
    trade_ledger: tuple[HistoricalTradeLedgerRow, ...]
    pending_orders: tuple[HistoricalPortfolioLifecyclePendingOrderSnapshot, ...]
    exposure: tuple[HistoricalPortfolioLifecycleExposureSnapshot, ...]
    reconciliation: HistoricalPortfolioLifecycleReconciliation
    manifest: HistoricalPortfolioLifecycleArtifactManifest


def run_tiny_manifest_replay_proof(
    manifest_path: str | Path,
    config: StrategyRuntimeConfig,
    *,
    database_url: str,
    initial_equity: float = 100_000.0,
) -> HistoricalReplayProofResult:
    """Run a deterministic replay proof from a validated historical panel manifest.

    This is deliberately a machinery proof, not a strategy-performance baseline.
    It uses the manifest as a hard precondition, derives a deterministic proof
    feature panel from the tiny prepared OHLCV/reference data, then exercises the
    existing score, setup, backtest, shadow, paper, and audit paths.
    """

    replay = run_historical_manifest_replay(
        manifest_path,
        config,
        database_url=database_url,
        output_dir=None,
        initial_equity=initial_equity,
    )
    return HistoricalReplayProofResult(
        panel_id=replay.panel_id,
        manifest_path=replay.manifest_path,
        status=replay.status,
        validation=replay.validation,
        signal_session=replay.signal_session,
        next_session=replay.next_session,
        setup_ids=replay.setup_ids,
        setup_symbols=replay.setup_symbols,
        backtest_event_types=replay.backtest_event_types,
        shadow_status_counts=replay.shadow_status_counts,
        audit_alignment_counts=replay.audit_alignment_counts,
        stage_summaries=replay.stage_summaries,
    )


def build_historical_portfolio_lifecycle_artifact_package(
    backtest_result: BacktestResult,
    *,
    panel_id: str,
    manifest_path: str | Path,
    config_hash: str,
    output_dir: str | Path,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> HistoricalPortfolioLifecycleArtifactPackage:
    """Build Tier 2 portfolio/lifecycle artifacts from existing backtest outputs.

    This is an offline artifact conversion layer. It does not re-simulate
    entries, exits, or broker activity. The current backtest result exposes
    events, closed trades, and equity points, so any unavailable lifecycle detail
    is surfaced as a reconciliation warning rather than reconstructed from
    hidden assumptions.
    """

    started_at = started_at or datetime.utcnow()
    completed_at = completed_at or datetime.utcnow()
    output_path = Path(output_dir)
    event_counts_by_session = _lifecycle_event_counts_by_session(backtest_result)
    session_states = _lifecycle_session_states_from_backtest(
        backtest_result,
        event_counts_by_session,
    )
    transitions = _lifecycle_transitions_from_backtest_events(
        backtest_result,
        config_hash=config_hash,
    )
    positions = (
        *backtest_result.position_snapshots,
        *_lifecycle_position_snapshots_from_backtest_trades(backtest_result),
    )
    trade_ledger = _trade_ledger_rows_from_backtest_trades(backtest_result)
    pending_orders = backtest_result.pending_order_snapshots
    exposure = _lifecycle_exposure_from_backtest_equity(backtest_result)
    reconciliation = _lifecycle_reconciliation_from_artifacts(
        backtest_result=backtest_result,
        session_states=session_states,
        transitions=transitions,
        positions=positions,
        pending_orders=pending_orders,
        exposure=exposure,
        checked_at=completed_at,
    )
    summary = _lifecycle_replay_summary_from_artifacts(
        backtest_result=backtest_result,
        panel_id=panel_id,
        manifest_path=manifest_path,
        config_hash=config_hash,
        started_at=started_at,
        completed_at=completed_at,
        session_states=session_states,
        transitions=transitions,
        positions=positions,
        pending_orders=pending_orders,
        exposure=exposure,
        reconciliation=reconciliation,
    )
    manifest = _lifecycle_artifact_manifest(
        panel_id=panel_id,
        run_id=f"portfolio_lifecycle:{panel_id}:{completed_at.isoformat()}",
        output_dir=output_path,
    )
    return HistoricalPortfolioLifecycleArtifactPackage(
        summary=summary,
        session_states=session_states,
        transitions=transitions,
        positions=positions,
        trade_ledger=trade_ledger,
        pending_orders=pending_orders,
        exposure=exposure,
        reconciliation=reconciliation,
        manifest=manifest,
    )


def write_historical_portfolio_lifecycle_artifacts(
    backtest_result: BacktestResult,
    output_dir: str | Path,
    *,
    panel_id: str,
    manifest_path: str | Path,
    config_hash: str,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> HistoricalPortfolioLifecycleArtifactManifest:
    """Write Tier 2 portfolio/lifecycle artifacts from a backtest result."""

    output_path = Path(output_dir)
    package = build_historical_portfolio_lifecycle_artifact_package(
        backtest_result,
        panel_id=panel_id,
        manifest_path=manifest_path,
        config_hash=config_hash,
        output_dir=output_path,
        started_at=started_at,
        completed_at=completed_at,
    )
    _write_historical_portfolio_lifecycle_artifact_package(package)
    return package.manifest


def run_historical_portfolio_lifecycle_replay(
    manifest_path: str | Path,
    config: StrategyRuntimeConfig,
    *,
    output_dir: str | Path | None = None,
    initial_equity: float = 100_000.0,
) -> HistoricalPortfolioLifecycleArtifactPackage:
    """Run an offline Tier 2 portfolio/lifecycle replay over a manifest.

    This path is artifact-only. It loads historical data, builds deterministic
    features/setups through the same research pipeline as the scanner replay,
    runs the existing stateful backtest, and emits lifecycle artifacts. It does
    not build runtime broker adapters or submit paper/live orders.
    """

    started_at = datetime.utcnow()
    manifest_path = Path(manifest_path)
    validation = validate_historical_panel_manifest(manifest_path)
    if validation.status is ReviewStatus.FAIL:
        raise ValueError("Cannot run lifecycle replay for a failing historical panel manifest")
    if initial_equity <= 0:
        raise ValueError("initial_equity must be positive")

    panel_data = load_historical_panel_data(manifest_path)
    feature_panel, _feature_adapter = _feature_panel_for_replay(panel_data)
    regime_frame = _build_proof_regime_frame(feature_panel, config)
    scored = score_candidates(feature_panel, regime_frame, config)
    detected = detect_setups(scored, config)
    backtest_result = run_backtest(
        detected,
        regime_frame,
        config,
        initial_equity=initial_equity,
    )
    package = build_historical_portfolio_lifecycle_artifact_package(
        backtest_result,
        panel_id=panel_data.manifest.panel_id,
        manifest_path=manifest_path,
        config_hash=config.config_hash(),
        output_dir=output_dir or "in_memory_portfolio_lifecycle_replay",
        started_at=started_at,
        completed_at=datetime.utcnow(),
    )
    if output_dir is not None:
        _write_historical_portfolio_lifecycle_artifact_package(package)
    return package


def _write_historical_portfolio_lifecycle_artifact_package(
    package: HistoricalPortfolioLifecycleArtifactPackage,
) -> None:
    output_path = Path(package.manifest.output_dir)
    _write_json(
        output_path / "portfolio_lifecycle_replay_summary.json",
        package.summary.model_dump(mode="json"),
    )
    _write_json(
        output_path / "portfolio_lifecycle_session_states.json",
        {
            "panel_id": package.summary.panel_id,
            "session_states": [
                state.model_dump(mode="json") for state in package.session_states
            ],
        },
    )
    _write_json(
        output_path / "portfolio_lifecycle_transitions.json",
        {
            "panel_id": package.summary.panel_id,
            "transitions": [
                transition.model_dump(mode="json")
                for transition in package.transitions
            ],
        },
    )
    _write_json(
        output_path / "portfolio_lifecycle_positions.json",
        {
            "panel_id": package.summary.panel_id,
            "positions": [
                position.model_dump(mode="json") for position in package.positions
            ],
        },
    )
    _write_json(
        output_path / "portfolio_lifecycle_trade_ledger.json",
        {
            "panel_id": package.summary.panel_id,
            "trades": [trade.model_dump(mode="json") for trade in package.trade_ledger],
        },
    )
    _write_json(
        output_path / "portfolio_lifecycle_pending_orders.json",
        {
            "panel_id": package.summary.panel_id,
            "pending_orders": [
                pending_order.model_dump(mode="json")
                for pending_order in package.pending_orders
            ],
        },
    )
    _write_json(
        output_path / "portfolio_lifecycle_exposure.json",
        {
            "panel_id": package.summary.panel_id,
            "exposure": [
                exposure.model_dump(mode="json") for exposure in package.exposure
            ],
        },
    )
    _write_json(
        output_path / "portfolio_lifecycle_reconciliation.json",
        package.reconciliation.model_dump(mode="json"),
    )
    _write_json(
        output_path / "portfolio_lifecycle_baseline_package.json",
        {
            "baseline_id": "swing_machine_v0_1",
            "package_type": "portfolio_lifecycle_v1",
            "panel_id": package.summary.panel_id,
            "status": package.summary.status.value,
            "summary": package.summary.model_dump(mode="json"),
            "reconciliation": package.reconciliation.model_dump(mode="json"),
            "trade_ledger_count": len(package.trade_ledger),
        },
    )
    _write_json(
        output_path / "portfolio_lifecycle_artifact_manifest.json",
        package.manifest.model_dump(mode="json"),
    )


def _lifecycle_event_counts_by_session(
    backtest_result: BacktestResult,
) -> dict[date, Counter[str]]:
    counts: dict[date, Counter[str]] = {}
    for event in backtest_result.events:
        counts.setdefault(event.session_date, Counter()).update((event.event_type,))
    return counts


def _lifecycle_session_states_from_backtest(
    backtest_result: BacktestResult,
    event_counts_by_session: dict[date, Counter[str]],
) -> tuple[HistoricalPortfolioLifecycleSessionState, ...]:
    states: list[HistoricalPortfolioLifecycleSessionState] = []
    events_by_session: dict[date, list[Any]] = {}
    for event in backtest_result.events:
        events_by_session.setdefault(event.session_date, []).append(event)

    for point in backtest_result.equity_curve:
        event_counts = event_counts_by_session.get(point.session_date, Counter())
        setup_ids = {
            event.setup_id
            for event in events_by_session.get(point.session_date, [])
            if event.setup_id is not None
        }
        states.append(
            HistoricalPortfolioLifecycleSessionState(
                session_date=point.session_date,
                cash=point.cash,
                equity=max(point.equity, 0.01),
                open_position_count=point.open_positions,
                pending_entry_count=point.pending_entries,
                exit_pending_count=min(
                    event_counts.get("EXIT_SUBMITTED", 0),
                    point.open_positions,
                ),
                portfolio_heat=0.0,
                daily_new_risk=0.0,
                sector_exposure={},
                candidate_count=len(setup_ids),
                setup_count=len(setup_ids),
                entry_submitted_count=event_counts.get("ENTRY_SUBMITTED", 0),
                entry_filled_count=event_counts.get("ENTRY_FILLED", 0),
                entry_cancelled_count=event_counts.get("ENTRY_CANCELLED", 0),
                exit_submitted_count=event_counts.get("EXIT_SUBMITTED", 0),
                exit_filled_count=event_counts.get("EXIT_FILLED", 0),
                stop_updated_count=0,
                blocked_reason_counts={},
            )
        )
    return tuple(states)


def _lifecycle_transitions_from_backtest_events(
    backtest_result: BacktestResult,
    *,
    config_hash: str,
) -> tuple[HistoricalPortfolioLifecycleTransition, ...]:
    transitions: list[HistoricalPortfolioLifecycleTransition] = []
    for index, event in enumerate(backtest_result.events, start=1):
        from_state, to_state = _lifecycle_transition_states(event)
        transitions.append(
            HistoricalPortfolioLifecycleTransition(
                transition_id=(
                    f"{event.session_date.isoformat()}:{event.symbol}:"
                    f"{event.event_type}:{index}"
                ),
                symbol=event.symbol,
                session_date=event.session_date,
                from_state=from_state,
                to_state=to_state,
                trigger=event.event_type,
                setup_id=event.setup_id,
                order_intent_id=None,
                position_id=None,
                reason_codes=_lifecycle_event_reason_codes(event),
                evidence={
                    "event_type": event.event_type,
                    "detail": event.detail,
                    "order_reason": None
                    if event.order_reason is None
                    else event.order_reason.value,
                },
                config_hash=config_hash,
            )
        )
    return tuple(transitions)


def _lifecycle_transition_states(event: Any) -> tuple[SymbolLifecycleState, SymbolLifecycleState]:
    if event.event_type == "ENTRY_SUBMITTED":
        return SymbolLifecycleState.ARMED, SymbolLifecycleState.PENDING_ENTRY
    if event.event_type == "ENTRY_FILLED":
        return SymbolLifecycleState.PENDING_ENTRY, SymbolLifecycleState.ACTIVE
    if event.event_type == "ENTRY_CANCELLED":
        return (
            SymbolLifecycleState.PENDING_ENTRY,
            event.state or SymbolLifecycleState.CANDIDATE,
        )
    if event.event_type == "EXIT_SUBMITTED":
        return SymbolLifecycleState.ACTIVE, SymbolLifecycleState.EXIT_PENDING
    if event.event_type == "EXIT_FILLED":
        return SymbolLifecycleState.EXIT_PENDING, SymbolLifecycleState.CLOSED
    state = event.state or SymbolLifecycleState.INELIGIBLE
    return state, state


def _lifecycle_event_reason_codes(event: Any) -> tuple[str, ...]:
    if event.detail:
        return tuple(reason for reason in str(event.detail).split("|") if reason)
    if event.order_reason is not None:
        return (event.order_reason.value,)
    return (event.event_type,)


def _lifecycle_position_snapshots_from_backtest_trades(
    backtest_result: BacktestResult,
) -> tuple[HistoricalPortfolioLifecyclePositionSnapshot, ...]:
    positions: list[HistoricalPortfolioLifecyclePositionSnapshot] = []
    for index, trade in enumerate(backtest_result.trades, start=1):
        position_id = (
            f"{trade.symbol}:{trade.setup_id}:"
            f"{trade.entry_fill_date.isoformat()}:{index}"
        )
        positions.append(
            HistoricalPortfolioLifecyclePositionSnapshot(
                position_id=position_id,
                symbol=trade.symbol,
                session_date=trade.exit_fill_date,
                state=SymbolLifecycleState.CLOSED,
                quantity=trade.quantity,
                entry_price=trade.entry_fill_price,
                market_price=trade.exit_fill_price,
                initial_stop=trade.initial_stop,
                current_stop=trade.final_stop,
                highest_high_since_entry=max(
                    trade.entry_reference_price,
                    trade.exit_reference_price,
                    trade.exit_fill_price,
                ),
                unrealized_pnl=0.0,
                unrealized_pnl_pct=0.0,
                risk_amount=max(
                    (trade.entry_fill_price - trade.initial_stop) * trade.quantity,
                    0.0,
                ),
                sector=trade.sector,
                setup_id=trade.setup_id,
                order_intent_id=None,
                opened_session=trade.entry_fill_date,
                planned_exit_session=trade.exit_fill_date,
            )
        )
    return tuple(positions)


def _trade_ledger_rows_from_backtest_trades(
    backtest_result: BacktestResult,
) -> tuple[HistoricalTradeLedgerRow, ...]:
    rows: list[HistoricalTradeLedgerRow] = []
    for index, trade in enumerate(backtest_result.trades, start=1):
        position_id = (
            f"{trade.symbol}:{trade.setup_id}:"
            f"{trade.entry_fill_date.isoformat()}:{index}"
        )
        trade_id = f"{trade.symbol}:{trade.setup_id}:{trade.exit_fill_date.isoformat()}:{index}"
        rows.append(
            HistoricalTradeLedgerRow(
                trade_id=trade_id,
                symbol=trade.symbol,
                setup_id=trade.setup_id,
                position_id=position_id,
                entry_signal_date=trade.entry_signal_date,
                entry_fill_date=trade.entry_fill_date,
                exit_fill_date=trade.exit_fill_date,
                entry_reference_price=trade.entry_reference_price,
                entry_fill_price=trade.entry_fill_price,
                exit_reference_price=trade.exit_reference_price,
                exit_fill_price=trade.exit_fill_price,
                quantity=trade.quantity,
                entry_regime_state=trade.entry_regime_state,
                exit_regime_state=trade.exit_regime_state,
                exit_reason=trade.exit_reason,
                bars_held=trade.bars_held,
                initial_stop=trade.initial_stop,
                final_stop=trade.final_stop,
                entry_transaction_cost=trade.entry_transaction_cost,
                exit_transaction_cost=trade.exit_transaction_cost,
                total_transaction_cost=trade.total_transaction_cost,
                gross_pnl=trade.gross_pnl,
                gross_return=trade.gross_return,
                net_pnl=trade.net_pnl,
                net_return=trade.net_return,
                sector=trade.sector,
            )
        )
    return tuple(rows)


def _lifecycle_exposure_from_backtest_equity(
    backtest_result: BacktestResult,
) -> tuple[HistoricalPortfolioLifecycleExposureSnapshot, ...]:
    exposure: list[HistoricalPortfolioLifecycleExposureSnapshot] = []
    for point in backtest_result.equity_curve:
        marked_exposure = point.equity - point.cash
        exposure.append(
            HistoricalPortfolioLifecycleExposureSnapshot(
                session_date=point.session_date,
                equity=max(point.equity, 0.01),
                cash=max(point.cash, 0.0),
                gross_exposure=max(marked_exposure, 0.0),
                net_exposure=marked_exposure,
                portfolio_heat=0.0,
                daily_new_risk=0.0,
                open_position_count=point.open_positions,
                pending_entry_count=point.pending_entries,
                sector_exposure={},
                symbol_exposure={},
            )
        )
    return tuple(exposure)


def _lifecycle_reconciliation_from_artifacts(
    *,
    backtest_result: BacktestResult,
    session_states: tuple[HistoricalPortfolioLifecycleSessionState, ...],
    transitions: tuple[HistoricalPortfolioLifecycleTransition, ...],
    positions: tuple[HistoricalPortfolioLifecyclePositionSnapshot, ...],
    pending_orders: tuple[HistoricalPortfolioLifecyclePendingOrderSnapshot, ...],
    exposure: tuple[HistoricalPortfolioLifecycleExposureSnapshot, ...],
    checked_at: datetime,
) -> HistoricalPortfolioLifecycleReconciliation:
    event_counts = Counter(event.event_type for event in backtest_result.events)
    warnings: list[str] = []
    failures: list[str] = []
    if not session_states:
        failures.append("NO_EQUITY_CURVE_SESSION_STATES")
    if len(session_states) != len(exposure):
        failures.append("SESSION_STATE_EXPOSURE_COUNT_MISMATCH")
    if len(transitions) != len(backtest_result.events):
        failures.append("TRANSITION_EVENT_COUNT_MISMATCH")
    closed_position_snapshot_count = sum(
        1 for position in positions if position.state is SymbolLifecycleState.CLOSED
    )
    if closed_position_snapshot_count != len(backtest_result.trades):
        failures.append("CLOSED_POSITION_TRADE_COUNT_MISMATCH")
    if event_counts.get("EXIT_FILLED", 0) != len(backtest_result.trades):
        failures.append("EXIT_FILLED_TRADE_COUNT_MISMATCH")
    if event_counts.get("ENTRY_FILLED", 0) > event_counts.get("ENTRY_SUBMITTED", 0):
        failures.append("ENTRY_FILL_WITHOUT_SUBMISSION")
    if event_counts.get("ENTRY_CANCELLED", 0) > event_counts.get("ENTRY_SUBMITTED", 0):
        failures.append("ENTRY_CANCEL_WITHOUT_SUBMISSION")
    failures.extend(
        _lifecycle_session_exposure_mismatches(
            session_states=session_states,
            exposure=exposure,
        )
    )
    failures.extend(_lifecycle_transition_mismatches(transitions))
    if event_counts.get("ENTRY_SUBMITTED", 0) and not pending_orders:
        warnings.append("PENDING_ORDER_DETAILS_NOT_AVAILABLE_FROM_BACKTEST_RESULT")
    has_open_position_snapshots = any(
        position.state in {SymbolLifecycleState.ACTIVE, SymbolLifecycleState.EXIT_PENDING}
        for position in positions
    )
    if (
        any(point.open_positions > 0 for point in backtest_result.equity_curve)
        and not has_open_position_snapshots
    ):
        warnings.append("OPEN_POSITION_DETAILS_LIMITED_TO_CLOSED_TRADES")
    status = (
        ReviewStatus.FAIL
        if failures
        else ReviewStatus.WARN
        if warnings
        else ReviewStatus.PASS
    )
    reason_counts = Counter({"OK": len(session_states)})
    reason_counts.update(warnings)
    reason_counts.update(failures)
    return HistoricalPortfolioLifecycleReconciliation(
        status=status,
        checked_at=checked_at,
        session_count=len(session_states),
        transition_count=len(transitions),
        position_snapshot_count=len(positions),
        pending_order_snapshot_count=len(pending_orders),
        exposure_snapshot_count=len(exposure),
        difference_count=len(failures),
        reason_counts=dict(reason_counts),
        failures=tuple(failures),
        warnings=tuple(warnings),
    )


def _lifecycle_session_exposure_mismatches(
    *,
    session_states: tuple[HistoricalPortfolioLifecycleSessionState, ...],
    exposure: tuple[HistoricalPortfolioLifecycleExposureSnapshot, ...],
) -> list[str]:
    failures: list[str] = []
    exposure_by_session = {snapshot.session_date: snapshot for snapshot in exposure}
    for state in session_states:
        exposure_snapshot = exposure_by_session.get(state.session_date)
        if exposure_snapshot is None:
            failures.append("SESSION_EXPOSURE_MISSING")
            continue
        if abs(float(state.equity) - float(exposure_snapshot.equity)) > 0.01:
            failures.append("SESSION_EXPOSURE_EQUITY_MISMATCH")
        if abs(float(state.cash) - float(exposure_snapshot.cash)) > 0.01:
            failures.append("SESSION_EXPOSURE_CASH_MISMATCH")
        if state.open_position_count != exposure_snapshot.open_position_count:
            failures.append("SESSION_EXPOSURE_OPEN_POSITION_COUNT_MISMATCH")
        if state.pending_entry_count != exposure_snapshot.pending_entry_count:
            failures.append("SESSION_EXPOSURE_PENDING_ENTRY_COUNT_MISMATCH")
    return failures


def _lifecycle_transition_mismatches(
    transitions: tuple[HistoricalPortfolioLifecycleTransition, ...],
) -> list[str]:
    failures: list[str] = []
    for transition in transitions:
        if transition.to_state is SymbolLifecycleState.EXIT_PENDING and (
            not transition.reason_codes
        ):
            failures.append("EXIT_PENDING_TRANSITION_MISSING_REASON")
        if transition.to_state is SymbolLifecycleState.CLOSED and (
            not transition.reason_codes
        ):
            failures.append("CLOSED_TRANSITION_MISSING_REASON")
        if transition.from_state is transition.to_state and not transition.reason_codes:
            failures.append("NOOP_TRANSITION_MISSING_REASON")
    return failures


def _lifecycle_replay_summary_from_artifacts(
    *,
    backtest_result: BacktestResult,
    panel_id: str,
    manifest_path: str | Path,
    config_hash: str,
    started_at: datetime,
    completed_at: datetime,
    session_states: tuple[HistoricalPortfolioLifecycleSessionState, ...],
    transitions: tuple[HistoricalPortfolioLifecycleTransition, ...],
    positions: tuple[HistoricalPortfolioLifecyclePositionSnapshot, ...],
    pending_orders: tuple[HistoricalPortfolioLifecyclePendingOrderSnapshot, ...],
    exposure: tuple[HistoricalPortfolioLifecycleExposureSnapshot, ...],
    reconciliation: HistoricalPortfolioLifecycleReconciliation,
) -> HistoricalPortfolioLifecycleReplaySummary:
    event_counts = Counter(event.event_type for event in backtest_result.events)
    replay_start_session = (
        session_states[0].session_date if session_states else started_at.date()
    )
    replay_end_session = (
        session_states[-1].session_date if session_states else completed_at.date()
    )
    return HistoricalPortfolioLifecycleReplaySummary(
        panel_id=panel_id,
        manifest_path=str(manifest_path),
        config_hash=config_hash,
        status=reconciliation.status,
        started_at=started_at,
        completed_at=completed_at,
        replay_start_session=replay_start_session,
        replay_end_session=replay_end_session,
        initial_equity=max(backtest_result.initial_equity, 0.01),
        final_equity=max(backtest_result.final_equity, 0.01),
        final_cash=max(backtest_result.equity_curve[-1].cash, 0.0)
        if backtest_result.equity_curve
        else max(backtest_result.initial_equity, 0.0),
        processed_session_count=len(session_states),
        transition_count=len(transitions),
        position_snapshot_count=len(positions),
        pending_order_snapshot_count=len(pending_orders),
        exposure_snapshot_count=len(exposure),
        entry_submitted_count=event_counts.get("ENTRY_SUBMITTED", 0),
        entry_filled_count=event_counts.get("ENTRY_FILLED", 0),
        entry_cancelled_count=event_counts.get("ENTRY_CANCELLED", 0),
        exit_submitted_count=event_counts.get("EXIT_SUBMITTED", 0),
        exit_filled_count=event_counts.get("EXIT_FILLED", 0),
        max_open_position_count=max(
            (state.open_position_count for state in session_states),
            default=0,
        ),
        max_pending_entry_count=max(
            (state.pending_entry_count for state in session_states),
            default=0,
        ),
        max_portfolio_heat=max(
            (state.portfolio_heat for state in session_states),
            default=0.0,
        ),
        reconciliation_status=reconciliation.status,
        parity_difference_count=None,
    )


def _lifecycle_artifact_manifest(
    *,
    panel_id: str,
    run_id: str,
    output_dir: Path,
) -> HistoricalPortfolioLifecycleArtifactManifest:
    return HistoricalPortfolioLifecycleArtifactManifest(
        panel_id=panel_id,
        run_id=run_id,
        output_dir=str(output_dir),
        lifecycle_replay_summary_path=str(
            output_dir / "portfolio_lifecycle_replay_summary.json"
        ),
        lifecycle_session_states_path=str(
            output_dir / "portfolio_lifecycle_session_states.json"
        ),
        lifecycle_transitions_path=str(
            output_dir / "portfolio_lifecycle_transitions.json"
        ),
        lifecycle_positions_path=str(output_dir / "portfolio_lifecycle_positions.json"),
        lifecycle_trade_ledger_path=str(
            output_dir / "portfolio_lifecycle_trade_ledger.json"
        ),
        lifecycle_pending_orders_path=str(
            output_dir / "portfolio_lifecycle_pending_orders.json"
        ),
        lifecycle_exposure_path=str(output_dir / "portfolio_lifecycle_exposure.json"),
        lifecycle_reconciliation_path=str(
            output_dir / "portfolio_lifecycle_reconciliation.json"
        ),
        lifecycle_baseline_package_path=str(
            output_dir / "portfolio_lifecycle_baseline_package.json"
        ),
        lifecycle_artifact_manifest_path=str(
            output_dir / "portfolio_lifecycle_artifact_manifest.json"
        ),
        lifecycle_parity_report_path=None,
    )


def run_historical_manifest_replay(
    manifest_path: str | Path,
    config: StrategyRuntimeConfig,
    *,
    database_url: str,
    output_dir: str | Path | None = None,
    initial_equity: float = 100_000.0,
    baseline_config_path: str | Path | None = None,
    selected_period_plan_path: str | Path | None = None,
) -> HistoricalReplayRunResult:
    """Run manifest-backed historical replay and optionally write JSON artifacts.

    This generalizes the tiny proof into a reusable replay service. If a manifest
    declares a validated prepared feature panel, replay uses that panel; otherwise
    it falls back to deterministic proof-derived features from OHLCV/reference data.
    This is machinery validation rather than strategy-performance baselining.
    """

    started_at = datetime.utcnow()
    result = _execute_historical_manifest_replay(
        manifest_path,
        config,
        database_url=database_url,
        initial_equity=initial_equity,
        started_at=started_at,
    )
    if output_dir is None:
        return result

    output_path = Path(output_dir)
    artifact_paths = _replay_artifact_paths(
        output_path,
        include_failure=result.status is ReviewStatus.FAIL,
    )
    result = result.model_copy(update={"artifact_paths": artifact_paths})
    _write_replay_artifacts(
        result,
        output_path,
        config=config,
        config_path=baseline_config_path or "runtime-provided-strategy-config",
        selected_period_plan_path=selected_period_plan_path,
    )
    return result


def run_historical_scanner_replay(
    manifest_path: str | Path,
    config: StrategyRuntimeConfig,
    *,
    output_dir: str | Path | None = None,
    initial_equity: float = 100_000.0,
) -> HistoricalScannerReplaySummary:
    """Run a stateless multi-session scanner-density replay over a manifest.

    This is a Tier 1 scanner qualification path. It scans every eligible
    signal/next-session pair inside the manifest replay window and emits density
    metrics only. It does not submit broker orders and does not carry portfolio
    lifecycle state between sessions.
    """

    started_at = datetime.utcnow()
    manifest_path = Path(manifest_path)
    validation = validate_historical_panel_manifest(manifest_path)
    if validation.status is ReviewStatus.FAIL:
        raise ValueError("Cannot run scanner replay for a failing historical panel manifest")

    panel_data = load_historical_panel_data(manifest_path)
    sessions = tuple(_replay_sessions(panel_data))
    if len(sessions) < 2:
        raise ValueError("At least two replay sessions are required for scanner replay")

    feature_panel, _feature_adapter = _feature_panel_for_replay(panel_data)
    regime_frame = _build_proof_regime_frame(feature_panel, config)
    scored = score_candidates(feature_panel, regime_frame, config)
    detected = detect_setups(scored, config)
    detected_for_scanner = detected.copy()
    detected_for_scanner["_scanner_session_date"] = pd.to_datetime(
        detected_for_scanner["session_date"],
        errors="raise",
    ).dt.date
    detected_by_session = {
        session: group.drop(columns=["_scanner_session_date"]).sort_values("symbol")
        for session, group in detected_for_scanner.groupby("_scanner_session_date", sort=False)
    }

    session_results: list[HistoricalScannerReplaySessionResult] = []
    for signal_session, next_session in zip(sessions, sessions[1:], strict=False):
        feature_precondition_failure = _prepared_feature_precondition_failure(
            panel_data=panel_data,
            feature_panel=feature_panel,
            signal_session=signal_session,
        )
        if feature_precondition_failure is not None:
            session_results.append(
                _skipped_scanner_session_result(
                    panel_id=panel_data.manifest.panel_id,
                    signal_session=signal_session,
                    next_session=next_session,
                    symbol_count=_signal_session_symbol_count(feature_panel, signal_session),
                    skip_reason=feature_precondition_failure,
                )
            )
            continue

        session_results.append(
            _scanner_session_result_from_signal_rows(
                panel_id=panel_data.manifest.panel_id,
                signal_rows=detected_by_session.get(signal_session, detected.iloc[0:0]),
                signal_session=signal_session,
                next_session=next_session,
                config=config,
            )
        )
    summary = _build_scanner_replay_summary(
        panel_id=panel_data.manifest.panel_id,
        manifest_path=manifest_path,
        config_hash=config.config_hash(),
        started_at=started_at,
        completed_at=datetime.utcnow(),
        replay_start_session=sessions[0],
        replay_end_session=sessions[-1],
        session_results=tuple(session_results),
    )
    if output_dir is not None:
        write_historical_scanner_replay_artifacts(summary, Path(output_dir))
    return summary


def _scanner_session_result_from_signal_rows(
    *,
    panel_id: str,
    signal_rows: pd.DataFrame,
    signal_session: date,
    next_session: date,
    config: StrategyRuntimeConfig,
) -> HistoricalScannerReplaySessionResult:
    decision_traces = _build_decision_traces_from_signal_rows(
        panel_id=panel_id,
        signal_rows=signal_rows,
        signal_session=signal_session,
        config=config,
    )
    setup_rows = signal_rows.loc[signal_rows["setup_valid"]]
    reason_counts = Counter(
        reason for trace in decision_traces for reason in trace.reason_codes
    )
    accepted_setup_symbols = tuple(str(symbol) for symbol in setup_rows["symbol"])
    accepted_setup_count = len(setup_rows)
    density = HistoricalScannerReplayDensityMetrics(
        decision_trace_count=len(decision_traces),
        candidate_count=len(signal_rows),
        accepted_setup_count=accepted_setup_count,
        rejected_decision_count=sum(
            1 for trace in decision_traces if trace.decision != "ACCEPTED_SETUP"
        ),
        signal_count=accepted_setup_count,
        risk_plan_count=accepted_setup_count,
        order_plan_count=accepted_setup_count,
        reason_counts=dict(reason_counts),
    )
    return HistoricalScannerReplaySessionResult(
        panel_id=panel_id,
        signal_session=signal_session,
        next_session=next_session,
        status=ReviewStatus.PASS,
        validation_status=ReviewStatus.PASS,
        reconciliation_status=ReviewStatus.PASS,
        symbol_count=len(signal_rows),
        density=density,
        accepted_setup_symbols=accepted_setup_symbols,
        material_decision_rows=_scanner_material_decision_rows_from_traces(
            decision_traces,
            next_session=next_session,
            config=config,
        ),
    )



def write_historical_scanner_replay_artifacts(
    summary: HistoricalScannerReplaySummary,
    output_dir: Path,
) -> HistoricalScannerReplayArtifactManifest:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_manifest = HistoricalScannerReplayArtifactManifest(
        panel_id=summary.panel_id,
        run_id=f"scanner:{summary.panel_id}:{summary.completed_at.isoformat()}",
        output_dir=str(output_dir),
        scanner_replay_summary_path=str(output_dir / "scanner_replay_summary.json"),
        scanner_session_results_path=str(output_dir / "scanner_session_results.json"),
        scanner_decision_density_path=str(output_dir / "scanner_decision_density.json"),
        scanner_rejection_reasons_path=str(output_dir / "scanner_rejection_reasons.json"),
        scanner_material_decisions_path=str(output_dir / "scanner_material_decisions.json"),
        scanner_baseline_report_package_path=str(
            output_dir / "scanner_baseline_report_package.json"
        ),
        scanner_runtime_database_path=None,
    )
    _write_json(
        output_dir / "scanner_replay_summary.json",
        summary.model_dump(mode="json", exclude={"session_results"}),
    )
    _write_json(
        output_dir / "scanner_session_results.json",
        {
            "panel_id": summary.panel_id,
            "session_results": [
                result.model_dump(mode="json") for result in summary.session_results
            ],
        },
    )
    _write_json(output_dir / "scanner_decision_density.json", _scanner_density_payload(summary))
    _write_json(
        output_dir / "scanner_rejection_reasons.json",
        _scanner_rejection_reason_payload(summary),
    )
    _write_json(
        output_dir / "scanner_material_decisions.json",
        _scanner_material_decisions_payload(summary),
    )
    _write_json(
        output_dir / "scanner_baseline_report_package.json",
        {
            "baseline_id": "swing_machine_v0_1",
            "panel_id": summary.panel_id,
            "status": summary.status.value,
            "package_type": "scanner_density_v1",
            "summary": summary.model_dump(mode="json", exclude={"session_results"}),
        },
    )
    _write_json(
        output_dir / "scanner_artifact_manifest.json",
        artifact_manifest.model_dump(mode="json"),
    )
    return artifact_manifest

def compare_historical_scanner_replay_output_dirs(
    research_output_dir: str | Path,
    runtime_output_dir: str | Path,
    *,
    comparison_id: str | None = None,
) -> SwingBaselineParityReport:
    research_dir = Path(research_output_dir)
    runtime_dir = Path(runtime_output_dir)
    differences: list[SwingBaselineParityDifference] = []
    for artifact_name in _scanner_parity_artifact_names():
        research_path = research_dir / artifact_name
        runtime_path = runtime_dir / artifact_name
        artifact_id = artifact_name.removesuffix(".json")
        if not research_path.exists():
            differences.append(
                _scanner_parity_difference(
                    artifact_id,
                    "__missing__",
                    None,
                    str(research_path),
                )
            )
            continue
        if not runtime_path.exists():
            differences.append(
                _scanner_parity_difference(
                    artifact_id,
                    "__missing__",
                    str(runtime_path),
                    None,
                )
            )
            continue
        research_payload = _normalise_scanner_parity_payload(
            artifact_name,
            json.loads(research_path.read_text(encoding="utf-8")),
        )
        runtime_payload = _normalise_scanner_parity_payload(
            artifact_name,
            json.loads(runtime_path.read_text(encoding="utf-8")),
        )
        differences.extend(
            _compare_scanner_payloads(
                artifact_id,
                research_payload,
                runtime_payload,
            )
        )

    return SwingBaselineParityReport(
        comparison_id=comparison_id
        or f"scanner_parity:{research_dir.name}:{runtime_dir.name}",
        research_package_id=f"scanner_output:{research_dir}",
        runtime_package_id=f"scanner_output:{runtime_dir}",
        passed=not differences,
        difference_count=len(differences),
        differences=tuple(differences),
    )


def compare_historical_portfolio_lifecycle_output_dirs(
    research_output_dir: str | Path,
    runtime_output_dir: str | Path,
    *,
    comparison_id: str | None = None,
) -> SwingBaselineParityReport:
    research_dir = Path(research_output_dir)
    runtime_dir = Path(runtime_output_dir)
    differences: list[SwingBaselineParityDifference] = []
    for artifact_name in _lifecycle_parity_artifact_names():
        research_path = research_dir / artifact_name
        runtime_path = runtime_dir / artifact_name
        artifact_id = artifact_name.removesuffix(".json")
        if not research_path.exists():
            differences.append(
                _lifecycle_parity_difference(
                    artifact_id,
                    "__missing__",
                    None,
                    str(research_path),
                )
            )
            continue
        if not runtime_path.exists():
            differences.append(
                _lifecycle_parity_difference(
                    artifact_id,
                    "__missing__",
                    str(runtime_path),
                    None,
                )
            )
            continue
        research_payload = _normalise_lifecycle_parity_payload(
            artifact_name,
            json.loads(research_path.read_text(encoding="utf-8")),
        )
        runtime_payload = _normalise_lifecycle_parity_payload(
            artifact_name,
            json.loads(runtime_path.read_text(encoding="utf-8")),
        )
        differences.extend(
            _compare_lifecycle_payloads(
                artifact_id,
                research_payload,
                runtime_payload,
            )
        )

    return SwingBaselineParityReport(
        comparison_id=comparison_id
        or f"portfolio_lifecycle_parity:{research_dir.name}:{runtime_dir.name}",
        research_package_id=f"portfolio_lifecycle_output:{research_dir}",
        runtime_package_id=f"portfolio_lifecycle_output:{runtime_dir}",
        passed=not differences,
        difference_count=len(differences),
        differences=tuple(differences),
    )


def write_historical_scanner_parity_report_json(
    report: SwingBaselineParityReport,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output_path


def write_historical_portfolio_lifecycle_parity_report_json(
    report: SwingBaselineParityReport,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output_path


def historical_replay_run_metrics(
    result: HistoricalReplayRunResult,
) -> dict[str, object]:
    return {
        "panel_id": result.panel_id,
        "status": result.status.value,
        "validation_status": result.validation.status.value,
        "validation_error_count": len(result.validation.errors),
        "validation_warning_count": len(result.validation.warnings),
        "setup_count": len(result.setup_ids),
        "feature_adapter": result.feature_adapter,
        "decision_trace_count": len(result.decision_traces),
        "rejected_decision_count": sum(
            1 for trace in result.decision_traces if trace.decision != "ACCEPTED_SETUP"
        ),
        "reconciliation_status": None
        if result.reconciliation is None
        else result.reconciliation.status.value,
        "backtest_event_count": len(result.backtest_event_types),
        "shadow_status_counts": result.shadow_status_counts,
        "audit_alignment_counts": result.audit_alignment_counts,
    }


def _execute_historical_manifest_replay(
    manifest_path: str | Path,
    config: StrategyRuntimeConfig,
    *,
    database_url: str,
    initial_equity: float,
    started_at: datetime,
) -> HistoricalReplayRunResult:
    manifest_path = Path(manifest_path)
    validation = validate_historical_panel_manifest(manifest_path)
    if validation.status is ReviewStatus.FAIL:
        return HistoricalReplayRunResult(
            panel_id=validation.panel_id,
            manifest_path=str(manifest_path),
            config_hash=config.config_hash(),
            status=ReviewStatus.FAIL,
            validation=validation,
            started_at=started_at,
            completed_at=datetime.utcnow(),
            reconciliation=_failed_reconciliation("VALIDATION_FAILED"),
            stage_summaries=(
                _stage_summary(
                    "validation",
                    ReviewStatus.FAIL,
                    error_count=len(validation.errors),
                    warning_count=len(validation.warnings),
                ),
            ),
        )

    panel_data = load_historical_panel_data(manifest_path)
    session_window = _selected_replay_session_window(panel_data)
    if session_window is None:
        sessions = _replay_sessions(panel_data)
        return HistoricalReplayRunResult(
            panel_id=panel_data.manifest.panel_id,
            manifest_path=str(manifest_path),
            config_hash=config.config_hash(),
            status=ReviewStatus.FAIL,
            validation=validation,
            started_at=started_at,
            completed_at=datetime.utcnow(),
            reconciliation=_failed_reconciliation("AT_LEAST_TWO_SESSIONS_REQUIRED"),
            stage_summaries=(
                _stage_summary(
                    "validation",
                    validation.status,
                    error_count=len(validation.errors),
                    warning_count=len(validation.warnings),
                ),
                _stage_summary(
                    "session_selection",
                    ReviewStatus.FAIL,
                    session_count=len(sessions),
                    reason="AT_LEAST_TWO_SESSIONS_REQUIRED",
                ),
            ),
        )

    signal_session = session_window.signal_session
    next_session = session_window.next_session
    feature_panel, feature_adapter = _feature_panel_for_replay(panel_data)
    feature_precondition_failure = _prepared_feature_precondition_failure(
        panel_data=panel_data,
        feature_panel=feature_panel,
        signal_session=signal_session,
    )
    if feature_precondition_failure is not None:
        return HistoricalReplayRunResult(
            panel_id=panel_data.manifest.panel_id,
            manifest_path=str(manifest_path),
            config_hash=config.config_hash(),
            status=ReviewStatus.FAIL,
            validation=validation,
            started_at=started_at,
            completed_at=datetime.utcnow(),
            signal_session=signal_session,
            next_session=next_session,
            feature_adapter=feature_adapter,
            reconciliation=_failed_reconciliation(feature_precondition_failure),
            stage_summaries=(
                _stage_summary(
                    "validation",
                    validation.status,
                    error_count=len(validation.errors),
                    warning_count=len(validation.warnings),
                ),
                _stage_summary(
                    "feature_adapter",
                    ReviewStatus.FAIL,
                    adapter=feature_adapter,
                    row_count=len(feature_panel),
                    reason=feature_precondition_failure,
                ),
            ),
        )

    context = _build_selected_session_replay_context(
        panel_data=panel_data,
        config=config,
        signal_session=signal_session,
        next_session=next_session,
        initial_equity=initial_equity,
        feature_panel=feature_panel,
        feature_adapter=feature_adapter,
    )

    if not context.setups:
        return HistoricalReplayRunResult(
            panel_id=panel_data.manifest.panel_id,
            manifest_path=str(manifest_path),
            config_hash=config.config_hash(),
            status=ReviewStatus.FAIL,
            validation=validation,
            started_at=started_at,
            completed_at=datetime.utcnow(),
            signal_session=signal_session,
            next_session=next_session,
            feature_adapter=context.feature_adapter,
            decision_traces=context.decision_traces,
            reconciliation=_failed_reconciliation("NO_VALID_SETUPS_FOR_SIGNAL_SESSION"),
            stage_summaries=(
                _stage_summary(
                    "validation",
                    validation.status,
                    error_count=len(validation.errors),
                    warning_count=len(validation.warnings),
                ),
                _stage_summary(
                    "feature_adapter",
                    ReviewStatus.PASS,
                    adapter=context.feature_adapter,
                    row_count=len(context.feature_panel),
                ),
                _stage_summary(
                    "setup_detection",
                    ReviewStatus.FAIL,
                    setup_count=0,
                    reason="NO_VALID_SETUPS_FOR_SIGNAL_SESSION",
                ),
            ),
        )

    backtest_result = run_backtest(
        context.replay_detected,
        context.replay_regime_frame,
        config,
        initial_equity=initial_equity,
    )

    runtime = build_runtime(config, database_url=database_url)
    shadow_result = runtime.run_cycle(context.cycle_input, mode=RuntimeMode.SHADOW)
    next_session_market_data = _next_session_market_data(panel_data.ohlcv, next_session)
    comparison_batch = compare_runtime_cycle_shadow_fills(
        shadow_result,
        next_session_market_data,
        config,
    )
    build_shadow_review_service(database_url=database_url).record_comparison_batch(comparison_batch)
    paper_result = runtime.run_cycle(context.cycle_input, mode=RuntimeMode.PAPER)
    audit_records = build_paper_shadow_audit_service(database_url=database_url).load_records()

    shadow_status_counts = Counter(
        comparison.status.value for comparison in comparison_batch.comparisons
    )
    audit_alignment_counts = Counter(record.alignment_status.value for record in audit_records)
    setup_ids = tuple(setup.setup_id for setup in context.setups)
    setup_symbols = tuple(setup.symbol for setup in context.setups)
    backtest_event_types = tuple(event.event_type for event in backtest_result.events)
    reconciliation = _build_reconciliation_summary(
        setup_count=len(context.setups),
        backtest_event_types=backtest_event_types,
        shadow_proposal_count=(
            0
            if shadow_result.shadow_entry_batch is None
            else len(shadow_result.shadow_entry_batch.proposals)
        ),
        shadow_compared_count=comparison_batch.compared_proposal_count,
        shadow_filled_count=comparison_batch.filled_count,
        paper_submission_count=(
            0
            if paper_result.paper_entry_batch is None
            else sum(
                1
                for submission in paper_result.paper_entry_batch.submissions
                if submission.submitted
            )
        ),
        audit_record_count=len(audit_records),
    )
    replay_status = _combine_replay_status(validation.status, reconciliation.status)

    return HistoricalReplayRunResult(
        panel_id=panel_data.manifest.panel_id,
        manifest_path=str(manifest_path),
        config_hash=config.config_hash(),
        status=replay_status,
        validation=validation,
        started_at=started_at,
        completed_at=datetime.utcnow(),
        signal_session=signal_session,
        next_session=next_session,
        feature_adapter=context.feature_adapter,
        setup_ids=setup_ids,
        setup_symbols=setup_symbols,
        backtest_event_types=backtest_event_types,
        shadow_status_counts=dict(shadow_status_counts),
        audit_alignment_counts=dict(audit_alignment_counts),
        decision_traces=context.decision_traces,
        reconciliation=reconciliation,
        baseline_candidates=context.baseline_candidates,
        baseline_signals=context.baseline_signals,
        baseline_risk_plans=context.baseline_risk_plans,
        baseline_order_plans=context.baseline_order_plans,
        stage_summaries=(
            _stage_summary(
                "validation",
                validation.status,
                error_count=len(validation.errors),
                warning_count=len(validation.warnings),
            ),
            _stage_summary(
                "setup_detection",
                ReviewStatus.PASS,
                setup_count=len(context.setups),
                setup_symbols=",".join(setup_symbols),
            ),
            _stage_summary(
                "feature_adapter",
                ReviewStatus.PASS,
                adapter=context.feature_adapter,
                row_count=len(context.feature_panel),
            ),
            _stage_summary(
                "backtest",
                ReviewStatus.PASS,
                event_count=len(backtest_result.events),
                event_types=",".join(backtest_event_types),
            ),
            _stage_summary(
                "shadow_comparison",
                ReviewStatus.PASS,
                comparison_count=len(comparison_batch.comparisons),
                filled_count=comparison_batch.filled_count,
                missing_market_data_count=comparison_batch.missing_market_data_count,
            ),
            _stage_summary(
                "paper_shadow_audit",
                ReviewStatus.PASS,
                audit_record_count=len(audit_records),
            ),
            _stage_summary(
                "reconciliation",
                reconciliation.status,
                check_count=len(reconciliation.checks),
            ),
        ),
    )


def _stage_summary(
    stage: str,
    status: ReviewStatus,
    **values: int | float | str,
) -> dict[str, int | float | str]:
    return {"stage": stage, "status": status.value, **values}


def _replay_artifact_paths(output_dir: Path, *, include_failure: bool) -> dict[str, str]:
    artifact_paths = {
        "validation_summary": output_dir / "validation_summary.json",
        "replay_summary": output_dir / "replay_summary.json",
        "stage_counts": output_dir / "stage_counts.json",
        "material_decisions": output_dir / "material_decisions.json",
        "decision_traces": output_dir / "decision_traces.json",
        "reconciliation_summary": output_dir / "reconciliation_summary.json",
        "baseline_report_package": output_dir / "baseline_report_package.json",
        "freeze_readiness": output_dir / "freeze_readiness.json",
    }
    if include_failure:
        artifact_paths["failure_summary"] = output_dir / "failure_summary.json"
    return {key: str(path) for key, path in artifact_paths.items()}


def _write_replay_artifacts(
    result: HistoricalReplayRunResult,
    output_dir: Path,
    *,
    config: StrategyRuntimeConfig,
    config_path: str | Path,
    selected_period_plan_path: str | Path | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "validation_summary.json", result.validation.model_dump(mode="json"))
    _write_json(output_dir / "replay_summary.json", _replay_summary_payload(result))
    _write_json(output_dir / "stage_counts.json", _stage_counts_payload(result))
    _write_json(output_dir / "material_decisions.json", _material_decisions_payload(result))
    _write_json(output_dir / "decision_traces.json", _decision_traces_payload(result))
    _write_json(
        output_dir / "reconciliation_summary.json",
        _reconciliation_summary_payload(result),
    )
    if result.status is ReviewStatus.FAIL:
        _write_json(output_dir / "failure_summary.json", _failure_summary_payload(result))
    manifest = build_swing_baseline_manifest(
        config,
        config_path,
        created_at=result.completed_at,
        satisfied_check_ids=_baseline_satisfied_check_ids_for_replay(result),
        blocked_check_ids=_baseline_blocked_check_ids_for_replay(result),
    )
    package = build_baseline_report_package(
        manifest,
        generated_at=result.completed_at,
        candidates=result.baseline_candidates,
        signals=result.baseline_signals,
        risk_plans=result.baseline_risk_plans,
        order_plans=result.baseline_order_plans,
    )
    write_baseline_report_package_json(package, output_dir / "baseline_report_package.json")
    selected_period_plan = (
        None
        if selected_period_plan_path is None
        else load_swing_selected_qualification_plan(selected_period_plan_path)
    )
    freeze_decision = evaluate_serious_full_run_freeze_readiness(
        manifest,
        selected_period_plan=selected_period_plan,
        parity_reports=(),
        operator_approved=False,
        evaluated_at=result.completed_at,
    )
    write_freeze_readiness_decision_json(freeze_decision, output_dir / "freeze_readiness.json")


def _baseline_candidates_for_replay(
    scored: pd.DataFrame,
    config: StrategyRuntimeConfig,
    signal_session: date,
):
    signal_scored = scored.copy()
    signal_scored["session_date"] = pd.to_datetime(signal_scored["session_date"])
    signal_scored = signal_scored.loc[signal_scored["session_date"].dt.date == signal_session]
    return swing_candidates_from_scored_frame(signal_scored, config)


def _baseline_signals_for_replay(
    setups,
    candidates,
    config: StrategyRuntimeConfig,
    *,
    regime_state: RegimeState,
) -> tuple[SwingSignal, ...]:
    candidate_by_symbol = {
        candidate.symbol: candidate
        for candidate in candidates
        if candidate.quality_score is not None
    }
    signals: list[SwingSignal] = []
    for setup in setups:
        candidate = candidate_by_symbol.get(setup.symbol)
        if candidate is None or candidate.quality_score is None:
            continue
        signals.append(
            swing_signal_from_setup_snapshot(
                setup,
                config,
                candidate_id=candidate.candidate_id,
                quality_score=candidate.quality_score,
                regime_state=regime_state,
            )
        )
    return tuple(signals)


def _baseline_risk_order_plans_for_replay(
    entry_plans,
    signals: tuple[SwingSignal, ...],
    config: StrategyRuntimeConfig,
) -> tuple[tuple[SwingRiskPlan, ...], tuple[SwingOrderPlan, ...]]:
    signal_by_setup_id = {
        signal.setup_id: signal for signal in signals if signal.setup_id is not None
    }
    risk_plans: list[SwingRiskPlan] = []
    order_plans: list[SwingOrderPlan] = []
    for entry_plan in entry_plans:
        signal = signal_by_setup_id.get(entry_plan.setup.setup_id)
        if signal is None:
            continue
        risk_plan = swing_risk_plan_from_entry_plan(
            entry_plan,
            config,
            signal_id=signal.signal_id,
        )
        risk_plans.append(risk_plan)
        order_plans.append(
            swing_order_plan_from_entry_plan(
                entry_plan,
                config,
                signal_id=signal.signal_id,
                risk_plan_id=risk_plan.risk_plan_id,
            )
        )
    return tuple(risk_plans), tuple(order_plans)


def _build_selected_session_replay_context(
    *,
    panel_data: HistoricalPanelData,
    config: StrategyRuntimeConfig,
    signal_session: date,
    next_session: date,
    initial_equity: float,
    feature_panel: pd.DataFrame | None = None,
    feature_adapter: str | None = None,
    regime_frame: pd.DataFrame | None = None,
    scored: pd.DataFrame | None = None,
    detected: pd.DataFrame | None = None,
) -> _SelectedSessionReplayContext:
    if feature_panel is None or feature_adapter is None:
        feature_panel, feature_adapter = _feature_panel_for_replay(panel_data)

    if regime_frame is None:
        regime_frame = _build_proof_regime_frame(feature_panel, config)
    if scored is None:
        scored = score_candidates(feature_panel, regime_frame, config)
    if detected is None:
        detected = detect_setups(scored, config)
    decision_traces = _build_decision_traces(
        panel_id=panel_data.manifest.panel_id,
        detected=detected,
        signal_session=signal_session,
        config=config,
    )
    setup_rows = detected.loc[
        (detected["session_date"].dt.date == signal_session) & detected["setup_valid"]
    ]
    setups = tuple(build_setup_snapshots(setup_rows, config))
    replay_detected = _replay_decision_window_frame(detected, signal_session, next_session)
    replay_regime_frame = _replay_decision_window_frame(
        regime_frame,
        signal_session,
        next_session,
    )
    cycle_input = RuntimeCycleInput(
        as_of=datetime.combine(signal_session, time(16, 5)),
        regime_state=RegimeState.RISK_ON,
        equity=initial_equity,
        last_data_at=datetime.combine(signal_session, time(16, 4)),
        expires_at=datetime.combine(next_session, time(16, 0)),
        setups=setups,
        sector_by_symbol=_sector_by_symbol(panel_data, signal_session),
    )
    baseline_candidates = _baseline_candidates_for_replay(scored, config, signal_session)
    baseline_signals = _baseline_signals_for_replay(
        setups,
        baseline_candidates,
        config,
        regime_state=cycle_input.regime_state,
    )
    baseline_entry_batch = PortfolioManager(config).plan_ranked_entries(
        setups,
        regime_state=cycle_input.regime_state,
        equity=cycle_input.equity,
        pending_symbols=(),
        open_positions=(),
        submitted_today_risk_amount=0.0,
        sector_by_symbol=cycle_input.sector_by_symbol,
        created_at=cycle_input.as_of,
        expires_at=cycle_input.expires_at,
    )
    baseline_risk_plans, baseline_order_plans = _baseline_risk_order_plans_for_replay(
        baseline_entry_batch.plans,
        baseline_signals,
        config,
    )

    return _SelectedSessionReplayContext(
        signal_session=signal_session,
        next_session=next_session,
        feature_panel=feature_panel,
        feature_adapter=feature_adapter,
        regime_frame=regime_frame,
        scored=scored,
        detected=detected,
        decision_traces=decision_traces,
        setups=setups,
        replay_detected=replay_detected,
        replay_regime_frame=replay_regime_frame,
        cycle_input=cycle_input,
        baseline_candidates=baseline_candidates,
        baseline_signals=baseline_signals,
        baseline_risk_plans=baseline_risk_plans,
        baseline_order_plans=baseline_order_plans,
    )


def _scanner_session_result_from_context(
    *,
    panel_id: str,
    context: _SelectedSessionReplayContext,
) -> HistoricalScannerReplaySessionResult:
    reason_counts = Counter(
        reason for trace in context.decision_traces for reason in trace.reason_codes
    )
    density = HistoricalScannerReplayDensityMetrics(
        decision_trace_count=len(context.decision_traces),
        candidate_count=len(context.baseline_candidates),
        accepted_setup_count=len(context.setups),
        rejected_decision_count=sum(
            1 for trace in context.decision_traces if trace.decision != "ACCEPTED_SETUP"
        ),
        signal_count=len(context.baseline_signals),
        risk_plan_count=len(context.baseline_risk_plans),
        order_plan_count=len(context.baseline_order_plans),
        reason_counts=dict(reason_counts),
    )
    return HistoricalScannerReplaySessionResult(
        panel_id=panel_id,
        signal_session=context.signal_session,
        next_session=context.next_session,
        status=ReviewStatus.PASS,
        validation_status=ReviewStatus.PASS,
        reconciliation_status=ReviewStatus.PASS,
        symbol_count=len(context.decision_traces),
        density=density,
        accepted_setup_symbols=tuple(setup.symbol for setup in context.setups),
        material_decision_rows=_scanner_material_decision_rows_from_context(context),
    )


def _skipped_scanner_session_result(
    *,
    panel_id: str,
    signal_session: date,
    next_session: date,
    symbol_count: int,
    skip_reason: str,
) -> HistoricalScannerReplaySessionResult:
    return HistoricalScannerReplaySessionResult(
        panel_id=panel_id,
        signal_session=signal_session,
        next_session=next_session,
        status=ReviewStatus.FAIL,
        validation_status=ReviewStatus.FAIL,
        reconciliation_status=ReviewStatus.FAIL,
        symbol_count=symbol_count,
        density=HistoricalScannerReplayDensityMetrics(),
        skipped=True,
        skip_reason=skip_reason,
    )


def _build_scanner_replay_summary(
    *,
    panel_id: str,
    manifest_path: Path,
    config_hash: str,
    started_at: datetime,
    completed_at: datetime,
    replay_start_session: date,
    replay_end_session: date,
    session_results: tuple[HistoricalScannerReplaySessionResult, ...],
) -> HistoricalScannerReplaySummary:
    processed_results = tuple(result for result in session_results if not result.skipped)
    skipped_session_count = len(session_results) - len(processed_results)
    total_candidates = sum(result.density.candidate_count for result in processed_results)
    total_setups = sum(result.density.accepted_setup_count for result in processed_results)
    total_decision_traces = sum(
        result.density.decision_trace_count for result in processed_results
    )
    total_rejections = sum(
        result.density.rejected_decision_count for result in processed_results
    )
    sessions_with_setups = sum(
        1 for result in processed_results if result.density.accepted_setup_count > 0
    )
    sessions_without_setups = len(processed_results) - sessions_with_setups
    processed_count = len(processed_results)
    status = ReviewStatus.FAIL if skipped_session_count else ReviewStatus.PASS
    return HistoricalScannerReplaySummary(
        panel_id=panel_id,
        manifest_path=str(manifest_path),
        config_hash=config_hash,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        replay_start_session=replay_start_session,
        replay_end_session=replay_end_session,
        eligible_signal_session_count=len(session_results),
        processed_signal_session_count=processed_count,
        skipped_session_count=skipped_session_count,
        total_decision_traces=total_decision_traces,
        total_candidates=total_candidates,
        total_setups=total_setups,
        total_rejections=total_rejections,
        sessions_with_setups=sessions_with_setups,
        sessions_without_setups=sessions_without_setups,
        average_candidates_per_session=(
            0.0 if processed_count == 0 else total_candidates / processed_count
        ),
        average_setups_per_session=(
            0.0 if processed_count == 0 else total_setups / processed_count
        ),
        max_setups_per_session=max(
            (result.density.accepted_setup_count for result in processed_results),
            default=0,
        ),
        session_results=session_results,
    )


def _signal_session_symbol_count(frame: pd.DataFrame, signal_session: date) -> int:
    sessions = pd.to_datetime(frame["session_date"], errors="raise").dt.date
    return int(frame.loc[sessions == signal_session, "symbol"].nunique())


def _scanner_density_payload(summary: HistoricalScannerReplaySummary) -> dict[str, Any]:
    return {
        "panel_id": summary.panel_id,
        "status": summary.status.value,
        "eligible_signal_session_count": summary.eligible_signal_session_count,
        "processed_signal_session_count": summary.processed_signal_session_count,
        "skipped_session_count": summary.skipped_session_count,
        "total_decision_traces": summary.total_decision_traces,
        "total_candidates": summary.total_candidates,
        "total_setups": summary.total_setups,
        "total_rejections": summary.total_rejections,
        "sessions_with_setups": summary.sessions_with_setups,
        "sessions_without_setups": summary.sessions_without_setups,
        "average_candidates_per_session": summary.average_candidates_per_session,
        "average_setups_per_session": summary.average_setups_per_session,
        "max_setups_per_session": summary.max_setups_per_session,
        "sessions": [
            {
                "signal_session": result.signal_session.isoformat(),
                "next_session": result.next_session.isoformat(),
                "candidate_count": result.density.candidate_count,
                "accepted_setup_count": result.density.accepted_setup_count,
                "rejected_decision_count": result.density.rejected_decision_count,
                "decision_trace_count": result.density.decision_trace_count,
                "skipped": result.skipped,
                "skip_reason": result.skip_reason,
            }
            for result in summary.session_results
        ],
    }


def _scanner_rejection_reason_payload(
    summary: HistoricalScannerReplaySummary,
) -> dict[str, Any]:
    aggregate = Counter()
    sessions = []
    for result in summary.session_results:
        aggregate.update(result.density.reason_counts)
        sessions.append(
            {
                "signal_session": result.signal_session.isoformat(),
                "reason_counts": result.density.reason_counts,
                "skipped": result.skipped,
                "skip_reason": result.skip_reason,
            }
        )
    return {
        "panel_id": summary.panel_id,
        "aggregate_reason_counts": dict(aggregate),
        "sessions": sessions,
    }


def _scanner_material_decisions_payload(
    summary: HistoricalScannerReplaySummary,
) -> dict[str, Any]:
    return {
        "panel_id": summary.panel_id,
        "status": summary.status.value,
        "sessions": [
            {
                "signal_session": result.signal_session.isoformat(),
                "next_session": result.next_session.isoformat(),
                "accepted_setup_symbols": list(result.accepted_setup_symbols),
                "accepted_setup_count": result.density.accepted_setup_count,
                "signal_count": result.density.signal_count,
                "risk_plan_count": result.density.risk_plan_count,
                "order_plan_count": result.density.order_plan_count,
                "material_decision_rows": list(result.material_decision_rows),
                "skipped": result.skipped,
                "skip_reason": result.skip_reason,
            }
            for result in summary.session_results
        ],
    }


def _scanner_material_decision_rows_from_context(
    context: _SelectedSessionReplayContext,
) -> tuple[dict[str, Any], ...]:
    candidate_by_symbol = {
        candidate.symbol: candidate for candidate in context.baseline_candidates
    }
    signal_by_setup_id = {
        signal.setup_id: signal
        for signal in context.baseline_signals
        if signal.setup_id is not None
    }
    risk_by_signal_id = {
        risk.signal_id: risk for risk in context.baseline_risk_plans
    }
    order_by_risk_plan_id = {
        order.risk_plan_id: order for order in context.baseline_order_plans
    }
    rows = []
    for trace in context.decision_traces:
        candidate = candidate_by_symbol.get(trace.symbol)
        signal = signal_by_setup_id.get(trace.setup_id or "")
        risk_plan = None if signal is None else risk_by_signal_id.get(signal.signal_id)
        order_plan = None if risk_plan is None else order_by_risk_plan_id.get(
            risk_plan.risk_plan_id
        )
        rows.append(
            _scanner_material_decision_row(
                trace,
                next_session=context.next_session,
                candidate=candidate,
                signal=signal,
                risk_plan=risk_plan,
                order_plan=order_plan,
            )
        )
    return tuple(rows)


def _scanner_material_decision_rows_from_traces(
    decision_traces: (
        tuple[HistoricalReplayDecisionTrace, ...] | list[HistoricalReplayDecisionTrace]
    ),
    *,
    next_session: date,
    config: StrategyRuntimeConfig,
) -> tuple[dict[str, Any], ...]:
    return tuple(
        _scanner_material_decision_row(trace, next_session=next_session, config=config)
        for trace in decision_traces
    )


def _scanner_material_decision_row(
    trace: HistoricalReplayDecisionTrace,
    *,
    next_session: date,
    candidate=None,
    signal=None,
    risk_plan=None,
    order_plan=None,
    config: StrategyRuntimeConfig | None = None,
) -> dict[str, Any]:
    accepted = trace.decision == "ACCEPTED_SETUP"
    candidate_id = None if candidate is None else candidate.candidate_id
    signal_id = None if signal is None else signal.signal_id
    risk_plan_id = None if risk_plan is None else risk_plan.risk_plan_id
    order_plan_id = None if order_plan is None else order_plan.order_plan_id
    if config is not None:
        candidate_id = candidate_id or (
            f"candidate:{config.strategy.id}:{trace.symbol}:{trace.session_date.isoformat()}"
        )
        if accepted and trace.setup_id is not None:
            signal_id = signal_id or (
                f"signal:{config.strategy.id}:{trace.symbol}:"
                f"{trace.session_date.isoformat()}:{trace.setup_id}"
            )
            risk_plan_id = risk_plan_id or (
                f"risk_plan:{config.strategy.id}:{trace.symbol}:"
                f"{trace.session_date.isoformat()}:{trace.setup_id}"
            )
            order_plan_id = order_plan_id or (
                f"order_plan:{config.strategy.id}:{trace.symbol}:"
                f"{trace.session_date.isoformat()}:{trace.setup_id}"
            )
    return {
        "panel_id": trace.panel_id,
        "symbol": trace.symbol,
        "signal_session": trace.session_date.isoformat(),
        "next_session": next_session.isoformat(),
        "setup_id": trace.setup_id,
        "decision": trace.decision,
        "reason_codes": list(trace.reason_codes),
        "candidate_id": candidate_id,
        "pattern_type": trace.pattern_type,
        "candidate_score_pct": trace.candidate_score_pct,
        "rank": _optional_nested_value(candidate, "ranking", "rank"),
        "signal_id": signal_id,
        "risk_plan_id": risk_plan_id,
        "order_plan_id": order_plan_id,
        "candidate_rejection_reasons": _rejection_reason_codes(candidate),
        "signal_rejection_reasons": _rejection_reason_codes(signal),
        "risk_rejection_reasons": _rejection_reason_codes(risk_plan),
        "order_rejection_reasons": _rejection_reason_codes(order_plan),
    }


def _optional_nested_value(item, *attributes: str):
    current = item
    for attribute in attributes:
        if current is None:
            return None
        current = getattr(current, attribute, None)
    return current


def _rejection_reason_codes(item) -> list[str]:
    if item is None:
        return []
    return [
        str(getattr(reason, "code", reason))
        for reason in getattr(item, "rejection_reasons", ())
    ]


def _scanner_parity_artifact_names() -> tuple[str, ...]:
    return (
        "scanner_replay_summary.json",
        "scanner_session_results.json",
        "scanner_decision_density.json",
        "scanner_rejection_reasons.json",
        "scanner_material_decisions.json",
        "scanner_baseline_report_package.json",
    )


def _lifecycle_parity_artifact_names() -> tuple[str, ...]:
    return (
        "portfolio_lifecycle_replay_summary.json",
        "portfolio_lifecycle_session_states.json",
        "portfolio_lifecycle_transitions.json",
        "portfolio_lifecycle_positions.json",
        "portfolio_lifecycle_pending_orders.json",
        "portfolio_lifecycle_exposure.json",
        "portfolio_lifecycle_reconciliation.json",
        "portfolio_lifecycle_baseline_package.json",
    )


def _normalise_scanner_parity_payload(artifact_name: str, payload: Any) -> Any:
    if isinstance(payload, dict):
        return {
            key: _normalise_scanner_parity_payload(artifact_name, value)
            for key, value in payload.items()
            if key not in _scanner_parity_ignored_fields(artifact_name)
        }
    if isinstance(payload, list):
        return [
            _normalise_scanner_parity_payload(artifact_name, value)
            for value in payload
        ]
    return payload


def _scanner_parity_ignored_fields(artifact_name: str) -> set[str]:
    ignored = {"started_at", "completed_at"}
    if artifact_name == "scanner_artifact_manifest.json":
        ignored |= {"run_id", "output_dir"}
    return ignored


def _normalise_lifecycle_parity_payload(artifact_name: str, payload: Any) -> Any:
    if isinstance(payload, dict):
        return {
            key: _normalise_lifecycle_parity_payload(artifact_name, value)
            for key, value in payload.items()
            if key not in _lifecycle_parity_ignored_fields(artifact_name)
        }
    if isinstance(payload, list):
        return [
            _normalise_lifecycle_parity_payload(artifact_name, value)
            for value in payload
        ]
    return payload


def _lifecycle_parity_ignored_fields(artifact_name: str) -> set[str]:
    ignored = {
        "started_at",
        "completed_at",
        "checked_at",
        "run_id",
        "output_dir",
        "lifecycle_replay_summary_path",
        "lifecycle_session_states_path",
        "lifecycle_transitions_path",
        "lifecycle_positions_path",
        "lifecycle_pending_orders_path",
        "lifecycle_exposure_path",
        "lifecycle_reconciliation_path",
        "lifecycle_baseline_package_path",
        "lifecycle_artifact_manifest_path",
        "lifecycle_parity_report_path",
    }
    if artifact_name == "portfolio_lifecycle_baseline_package.json":
        ignored |= {"package_id", "generated_at"}
    return ignored


def _compare_scanner_payloads(
    artifact_id: str,
    research_value: Any,
    runtime_value: Any,
    *,
    path: str = "",
) -> tuple[SwingBaselineParityDifference, ...]:
    differences: list[SwingBaselineParityDifference] = []
    if isinstance(research_value, dict) and isinstance(runtime_value, dict):
        for key in sorted(set(research_value) | set(runtime_value)):
            child_path = key if not path else f"{path}.{key}"
            if key not in research_value:
                differences.append(
                    _scanner_parity_difference(
                        artifact_id,
                        child_path,
                        None,
                        runtime_value[key],
                    )
                )
            elif key not in runtime_value:
                differences.append(
                    _scanner_parity_difference(
                        artifact_id,
                        child_path,
                        research_value[key],
                        None,
                    )
                )
            else:
                differences.extend(
                    _compare_scanner_payloads(
                        artifact_id,
                        research_value[key],
                        runtime_value[key],
                        path=child_path,
                    )
                )
        return tuple(differences)
    if isinstance(research_value, list) and isinstance(runtime_value, list):
        for index in range(max(len(research_value), len(runtime_value))):
            child_path = f"{path}[{index}]"
            if index >= len(research_value):
                differences.append(
                    _scanner_parity_difference(
                        artifact_id,
                        child_path,
                        None,
                        runtime_value[index],
                    )
                )
            elif index >= len(runtime_value):
                differences.append(
                    _scanner_parity_difference(
                        artifact_id,
                        child_path,
                        research_value[index],
                        None,
                    )
                )
            else:
                differences.extend(
                    _compare_scanner_payloads(
                        artifact_id,
                        research_value[index],
                        runtime_value[index],
                        path=child_path,
                    )
                )
        return tuple(differences)
    if research_value != runtime_value:
        return (
            _scanner_parity_difference(
                artifact_id,
                path,
                research_value,
                runtime_value,
            ),
        )
    return ()


def _compare_lifecycle_payloads(
    artifact_id: str,
    research_value: Any,
    runtime_value: Any,
    *,
    path: str = "",
) -> tuple[SwingBaselineParityDifference, ...]:
    differences: list[SwingBaselineParityDifference] = []
    if isinstance(research_value, dict) and isinstance(runtime_value, dict):
        for key in sorted(set(research_value) | set(runtime_value)):
            child_path = key if not path else f"{path}.{key}"
            if key not in research_value:
                differences.append(
                    _lifecycle_parity_difference(
                        artifact_id,
                        child_path,
                        None,
                        runtime_value[key],
                    )
                )
            elif key not in runtime_value:
                differences.append(
                    _lifecycle_parity_difference(
                        artifact_id,
                        child_path,
                        research_value[key],
                        None,
                    )
                )
            else:
                differences.extend(
                    _compare_lifecycle_payloads(
                        artifact_id,
                        research_value[key],
                        runtime_value[key],
                        path=child_path,
                    )
                )
        return tuple(differences)
    if isinstance(research_value, list) and isinstance(runtime_value, list):
        for index in range(max(len(research_value), len(runtime_value))):
            child_path = f"{path}[{index}]"
            if index >= len(research_value):
                differences.append(
                    _lifecycle_parity_difference(
                        artifact_id,
                        child_path,
                        None,
                        runtime_value[index],
                    )
                )
            elif index >= len(runtime_value):
                differences.append(
                    _lifecycle_parity_difference(
                        artifact_id,
                        child_path,
                        research_value[index],
                        None,
                    )
                )
            else:
                differences.extend(
                    _compare_lifecycle_payloads(
                        artifact_id,
                        research_value[index],
                        runtime_value[index],
                        path=child_path,
                    )
                )
        return tuple(differences)
    if research_value != runtime_value:
        return (
            _lifecycle_parity_difference(
                artifact_id,
                path,
                research_value,
                runtime_value,
            ),
        )
    return ()


def _scanner_parity_difference(
    artifact_id: str,
    field_path: str,
    research_value: Any,
    runtime_value: Any,
) -> SwingBaselineParityDifference:
    return SwingBaselineParityDifference(
        artifact_type="scanner_replay",
        artifact_id=artifact_id,
        field_path=field_path,
        research_value=research_value,
        runtime_value=runtime_value,
    )


def _lifecycle_parity_difference(
    artifact_id: str,
    field_path: str,
    research_value: Any,
    runtime_value: Any,
) -> SwingBaselineParityDifference:
    return SwingBaselineParityDifference(
        artifact_type="portfolio_lifecycle_replay",
        artifact_id=artifact_id,
        field_path=field_path,
        research_value=research_value,
        runtime_value=runtime_value,
    )


def _baseline_satisfied_check_ids_for_replay(result: HistoricalReplayRunResult) -> tuple[str, ...]:
    satisfied = ["explicit_baseline_profile"]
    if result.validation.status is ReviewStatus.PASS:
        satisfied.append("data_contract")
    return tuple(satisfied)


def _baseline_blocked_check_ids_for_replay(result: HistoricalReplayRunResult) -> tuple[str, ...]:
    if result.validation.status is ReviewStatus.FAIL:
        return ("data_contract",)
    return ()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")


def _replay_summary_payload(result: HistoricalReplayRunResult) -> dict[str, Any]:
    return {
        "panel_id": result.panel_id,
        "manifest_path": result.manifest_path,
        "config_hash": result.config_hash,
        "status": result.status.value,
        "validation_status": result.validation.status.value,
        "started_at": result.started_at.isoformat(),
        "completed_at": result.completed_at.isoformat(),
        "signal_session": None
        if result.signal_session is None
        else result.signal_session.isoformat(),
        "next_session": None if result.next_session is None else result.next_session.isoformat(),
        "feature_adapter": result.feature_adapter,
        "artifact_paths": result.artifact_paths,
        "metrics": historical_replay_run_metrics(result),
    }


def _stage_counts_payload(result: HistoricalReplayRunResult) -> dict[str, Any]:
    return {
        "panel_id": result.panel_id,
        "status": result.status.value,
        "stages": list(result.stage_summaries),
    }


def _material_decisions_payload(result: HistoricalReplayRunResult) -> dict[str, Any]:
    return {
        "panel_id": result.panel_id,
        "status": result.status.value,
        "signal_session": None
        if result.signal_session is None
        else result.signal_session.isoformat(),
        "next_session": None if result.next_session is None else result.next_session.isoformat(),
        "setup_ids": list(result.setup_ids),
        "setup_symbols": list(result.setup_symbols),
        "backtest_event_types": list(result.backtest_event_types),
        "shadow_status_counts": result.shadow_status_counts,
        "audit_alignment_counts": result.audit_alignment_counts,
    }


def _decision_traces_payload(result: HistoricalReplayRunResult) -> dict[str, Any]:
    return {
        "panel_id": result.panel_id,
        "status": result.status.value,
        "signal_session": None
        if result.signal_session is None
        else result.signal_session.isoformat(),
        "traces": [trace.model_dump(mode="json") for trace in result.decision_traces],
    }


def _reconciliation_summary_payload(result: HistoricalReplayRunResult) -> dict[str, Any]:
    if result.reconciliation is None:
        return {
            "panel_id": result.panel_id,
            "status": ReviewStatus.FAIL.value,
            "counts": {},
            "checks": [],
        }
    return {
        "panel_id": result.panel_id,
        **result.reconciliation.model_dump(mode="json"),
    }


def _failure_summary_payload(result: HistoricalReplayRunResult) -> dict[str, Any]:
    failing_stage = next(
        (
            stage
            for stage in result.stage_summaries
            if stage.get("status") == ReviewStatus.FAIL.value
        ),
        None,
    )
    return {
        "panel_id": result.panel_id,
        "status": result.status.value,
        "failure_stage": None if failing_stage is None else failing_stage.get("stage"),
        "failure_detail": failing_stage,
        "validation_errors": [issue.model_dump(mode="json") for issue in result.validation.errors],
        "validation_warnings": [
            issue.model_dump(mode="json") for issue in result.validation.warnings
        ],
    }


def _build_decision_traces(
    *,
    panel_id: str,
    detected: pd.DataFrame,
    signal_session: date,
    config: StrategyRuntimeConfig,
) -> tuple[HistoricalReplayDecisionTrace, ...]:
    signal_rows = detected.loc[
        pd.to_datetime(detected["session_date"]).dt.date == signal_session
    ].sort_values("symbol")
    return _build_decision_traces_from_signal_rows(
        panel_id=panel_id,
        signal_rows=signal_rows,
        signal_session=signal_session,
        config=config,
    )


def _build_decision_traces_from_signal_rows(
    *,
    panel_id: str,
    signal_rows: pd.DataFrame,
    signal_session: date,
    config: StrategyRuntimeConfig,
) -> tuple[HistoricalReplayDecisionTrace, ...]:
    traces: list[HistoricalReplayDecisionTrace] = []
    for _, row in signal_rows.iterrows():
        setup_valid = _optional_bool(row, "setup_valid")
        decision = "ACCEPTED_SETUP" if setup_valid else "REJECTED"
        traces.append(
            HistoricalReplayDecisionTrace(
                panel_id=panel_id,
                symbol=str(row["symbol"]),
                session_date=signal_session,
                decision=decision,
                reason_codes=_decision_reason_codes(row, config),
                setup_id=_optional_str(row, "setup_id"),
                pattern_type=_optional_str(row, "pattern_type"),
                universe_eligible=_optional_bool(row, "universe_eligible"),
                rankable=_optional_bool(row, "rankable"),
                is_candidate=_optional_bool(row, "is_candidate"),
                setup_valid=setup_valid,
                candidate_score_pct=_optional_float(row, "candidate_score_pct"),
                candidate_score_threshold_pct=_optional_float(
                    row,
                    "effective_candidate_score_threshold_pct",
                ),
                trend_quality=_optional_float(row, "trend_quality"),
                min_trend_quality=_optional_float(row, "effective_min_trend_quality"),
            )
        )
    return tuple(traces)


def _decision_reason_codes(
    row: pd.Series,
    config: StrategyRuntimeConfig,
) -> tuple[str, ...]:
    if _optional_bool(row, "setup_valid"):
        return ("SETUP_VALID",)

    reasons: list[str] = []
    if _optional_bool(row, "universe_eligible") is False:
        reasons.append("UNIVERSE_INELIGIBLE")
    if _optional_bool(row, "entry_enabled") is False:
        reasons.append("REGIME_ENTRY_DISABLED")

    if (
        _optional_float(row, "split_adj_close") is not None
        and _optional_float(row, "ma50") is not None
    ):
        if float(row["split_adj_close"]) <= float(row["ma50"]):
            reasons.append("PRICE_NOT_ABOVE_MA50")
    if _optional_float(row, "ma50") is not None and _optional_float(row, "ma200") is not None:
        if float(row["ma50"]) <= float(row["ma200"]):
            reasons.append("MA50_NOT_ABOVE_MA200")
    ma200_slope = _optional_float(row, "ma200_slope_pct20")
    if ma200_slope is not None and ma200_slope <= 0.0:
        reasons.append("MA200_SLOPE_NOT_POSITIVE")
    dist_to_high = _optional_float(row, "dist_to_52w_high")
    if (
        dist_to_high is not None
        and dist_to_high > config.setup.shared_requirements.max_distance_from_52w_high
    ):
        reasons.append("TOO_FAR_FROM_52W_HIGH")

    earnings_distance = _optional_float(row, "regular_closes_until_earnings_event")
    if (
        earnings_distance is not None
        and earnings_distance <= config.events.min_regular_closes_before_earnings_for_new_entry
    ):
        reasons.append("EARNINGS_WINDOW_TOO_CLOSE")

    score = _optional_float(row, "candidate_score_pct")
    score_threshold = _optional_float(row, "effective_candidate_score_threshold_pct")
    if score is None:
        reasons.append("CANDIDATE_SCORE_UNAVAILABLE")
    elif score_threshold is not None and score < score_threshold:
        reasons.append("CANDIDATE_SCORE_BELOW_THRESHOLD")

    trend_quality = _optional_float(row, "trend_quality")
    min_trend_quality = _optional_float(row, "effective_min_trend_quality")
    if trend_quality is None:
        reasons.append("TREND_QUALITY_UNAVAILABLE")
    elif min_trend_quality is not None and trend_quality < min_trend_quality:
        reasons.append("TREND_QUALITY_BELOW_THRESHOLD")

    if _optional_bool(row, "is_candidate") and not (
        _optional_bool(row, "pullback_valid") or _optional_bool(row, "tight_base_valid")
    ):
        reasons.append("NO_PATTERN_VALID")

    return tuple(dict.fromkeys(reasons or ["UNKNOWN_REJECTION"]))


def _build_reconciliation_summary(
    *,
    setup_count: int,
    backtest_event_types: tuple[str, ...],
    shadow_proposal_count: int,
    shadow_compared_count: int,
    shadow_filled_count: int,
    paper_submission_count: int,
    audit_record_count: int,
) -> HistoricalReplayReconciliationSummary:
    counts = {
        "setup_count": setup_count,
        "backtest_entry_submitted_count": backtest_event_types.count("ENTRY_SUBMITTED"),
        "backtest_entry_filled_count": backtest_event_types.count("ENTRY_FILLED"),
        "shadow_proposal_count": shadow_proposal_count,
        "shadow_compared_count": shadow_compared_count,
        "shadow_filled_count": shadow_filled_count,
        "paper_submission_count": paper_submission_count,
        "audit_record_count": audit_record_count,
    }
    checks = (
        _count_check(
            "setup_to_backtest_submission_count",
            observed=counts["backtest_entry_submitted_count"],
            expected=setup_count,
        ),
        _count_check(
            "setup_to_shadow_proposal_count",
            observed=shadow_proposal_count,
            expected=setup_count,
        ),
        _count_check(
            "shadow_proposal_to_comparison_count",
            observed=shadow_compared_count,
            expected=shadow_proposal_count,
        ),
        _count_check(
            "setup_to_paper_submission_count",
            observed=paper_submission_count,
            expected=setup_count,
        ),
        _count_check(
            "shadow_comparison_to_audit_record_count",
            observed=audit_record_count,
            expected=shadow_compared_count,
        ),
        _count_check(
            "backtest_fill_to_shadow_fill_count",
            observed=shadow_filled_count,
            expected=counts["backtest_entry_filled_count"],
        ),
    )
    status = (
        ReviewStatus.FAIL
        if any(check.status is ReviewStatus.FAIL for check in checks)
        else ReviewStatus.PASS
    )
    return HistoricalReplayReconciliationSummary(status=status, counts=counts, checks=checks)


def _count_check(
    name: str,
    *,
    observed: int,
    expected: int,
) -> HistoricalReplayReconciliationCheck:
    status = ReviewStatus.PASS if observed == expected else ReviewStatus.FAIL
    return HistoricalReplayReconciliationCheck(
        name=name,
        status=status,
        observed=observed,
        expected=expected,
    )


def _failed_reconciliation(reason: str) -> HistoricalReplayReconciliationSummary:
    return HistoricalReplayReconciliationSummary(
        status=ReviewStatus.FAIL,
        counts={},
        checks=(
            HistoricalReplayReconciliationCheck(
                name="replay_precondition",
                status=ReviewStatus.FAIL,
                observed=reason,
                expected="READY_TO_REPLAY",
            ),
        ),
    )


def _combine_replay_status(
    validation_status: ReviewStatus,
    reconciliation_status: ReviewStatus,
) -> ReviewStatus:
    if ReviewStatus.FAIL in {validation_status, reconciliation_status}:
        return ReviewStatus.FAIL
    if ReviewStatus.WARN in {validation_status, reconciliation_status}:
        return ReviewStatus.WARN
    return ReviewStatus.PASS


def _optional_bool(row: pd.Series, column: str) -> bool | None:
    if column not in row.index or pd.isna(row[column]):
        return None
    return bool(row[column])


def _optional_float(row: pd.Series, column: str) -> float | None:
    if column not in row.index or pd.isna(row[column]):
        return None
    return float(row[column])


def _optional_str(row: pd.Series, column: str) -> str | None:
    if column not in row.index or pd.isna(row[column]):
        return None
    value = str(row[column])
    return value if value else None


def _ordered_sessions(ohlcv: pd.DataFrame) -> list[date]:
    sessions = pd.to_datetime(ohlcv["session_date"], errors="raise").dt.date
    return sorted(set(sessions))


def _replay_sessions(panel_data: HistoricalPanelData) -> list[date]:
    sessions = _ordered_sessions(panel_data.ohlcv)
    if not sessions:
        return []
    start_session = panel_data.manifest.replay_start_session or sessions[0]
    end_session = panel_data.manifest.replay_end_session or sessions[-1]
    return [
        session
        for session in sessions
        if start_session <= session <= end_session
    ]


def _selected_replay_session_window(
    panel_data: HistoricalPanelData,
) -> _SelectedReplaySessionWindow | None:
    sessions = tuple(_replay_sessions(panel_data))
    if len(sessions) < 2:
        return None
    return _SelectedReplaySessionWindow(
        sessions=sessions,
        signal_session=sessions[-2],
        next_session=sessions[-1],
    )


def _replay_decision_window_frame(
    frame: pd.DataFrame,
    signal_session: date,
    next_session: date,
) -> pd.DataFrame:
    sessions = pd.to_datetime(frame["session_date"], errors="raise").dt.date
    return frame.loc[(sessions >= signal_session) & (sessions <= next_session)].copy()


def _build_proof_regime_frame(
    feature_panel: pd.DataFrame,
    config: StrategyRuntimeConfig,
) -> pd.DataFrame:
    action = config.regime_action(RegimeState.RISK_ON)
    sessions = _ordered_sessions(feature_panel)
    return pd.DataFrame(
        {
            "session_date": pd.to_datetime(sessions),
            "regime_state": [RegimeState.RISK_ON.value] * len(sessions),
            "entry_enabled": [True] * len(sessions),
            "min_candidate_score_percentile": [action.min_candidate_score_percentile]
            * len(sessions),
            "min_trend_quality": [action.min_trend_quality] * len(sessions),
        }
    )


def _feature_panel_for_replay(panel_data: HistoricalPanelData) -> tuple[pd.DataFrame, str]:
    if panel_data.features is not None:
        return panel_data.features.copy(), "prepared_features_v1"
    return _build_proof_feature_panel(panel_data), "proof_derived_from_ohlcv_v1"


def _prepared_feature_precondition_failure(
    *,
    panel_data: HistoricalPanelData,
    feature_panel: pd.DataFrame,
    signal_session: date,
) -> str | None:
    if panel_data.features is None:
        return None

    feature_start_session = (
        panel_data.manifest.feature_start_session or panel_data.manifest.start_session
    )
    if signal_session < feature_start_session:
        return "SIGNAL_SESSION_BEFORE_FEATURE_START"

    expected_symbols = _expected_feature_symbols_for_signal(panel_data, signal_session)
    if not expected_symbols:
        return None

    signal_feature_rows = feature_panel.loc[
        pd.to_datetime(feature_panel["session_date"]).dt.date == signal_session
    ]
    if signal_feature_rows.empty:
        return "PREPARED_FEATURES_MISSING_SIGNAL_SESSION"

    feature_symbols = set(signal_feature_rows["symbol"].astype(str))
    if expected_symbols - feature_symbols:
        return "PREPARED_FEATURES_MISSING_SIGNAL_SYMBOLS"

    return None


def _expected_feature_symbols_for_signal(
    panel_data: HistoricalPanelData,
    signal_session: date,
) -> set[str]:
    expected_rows = expected_feature_coverage_rows(
        ohlcv=panel_data.ohlcv,
        reference=panel_data.symbol_reference,
        feature_start_session=signal_session,
        feature_coverage_scope=panel_data.manifest.feature_coverage_scope,
    )
    signal_rows = expected_rows.loc[
        pd.to_datetime(expected_rows["session_date"]).dt.date == signal_session
    ]
    return set(signal_rows["symbol"].astype(str))


def _build_proof_feature_panel(panel_data: HistoricalPanelData) -> pd.DataFrame:
    ohlcv = panel_data.ohlcv.copy()
    ohlcv["session_date"] = pd.to_datetime(ohlcv["session_date"], errors="raise")
    reference = panel_data.symbol_reference[
        [
            "symbol",
            "asset_type",
            "sector",
            "exchange",
            "currency",
            "is_tradable",
            "effective_start_session",
            "effective_end_session",
            "tradable_start_session",
            "tradable_end_session",
        ]
    ].copy()
    panel = symbol_reference_rows_for_sessions(symbol_sessions=ohlcv, reference=reference)
    panel = panel.sort_values(["symbol", "session_date"]).reset_index(drop=True)

    symbols = sorted(str(symbol) for symbol in panel["symbol"].unique())
    symbol_rank = {symbol: len(symbols) - index for index, symbol in enumerate(symbols)}
    symbol_count = max(len(symbols), 1)
    frames = []

    for symbol, group in panel.groupby("symbol", sort=True):
        group = group.copy().reset_index(drop=True)
        closes = group["raw_close"].astype(float)
        highs = group["raw_high"].astype(float)
        lows = group["raw_low"].astype(float)
        bias = symbol_rank[str(symbol)] / symbol_count

        group["split_adj_close"] = closes
        group["split_adj_high"] = highs
        group["split_adj_low"] = lows
        group["ma50"] = closes * 0.96
        group["ma200"] = closes * 0.87
        group["ma200_slope_pct20"] = 0.02
        group["dist_to_52w_high"] = 0.04
        group["mom_252_21"] = 0.20 + bias
        group["ret_126"] = 0.15 + bias
        group["rs_vs_benchmark_126"] = 0.08 + bias
        group["trend_quality"] = 0.70 if bias >= 1.0 else 0.50
        group["atr_14"] = (closes * 0.02).clip(lower=1.0)
        group["range_compression_ratio"] = 0.75
        group["pullback_days"] = group.index.astype(float)
        group["pullback_depth_atr"] = ((highs.cummax() - closes) / group["atr_14"]).clip(lower=0.0)
        group["anchor_high_date"] = group["session_date"].iloc[0]
        group["volume_ratio_20"] = 0.80
        group["regular_closes_until_earnings_event"] = 10
        group["history_days"] = 300 + group.index
        group["avg_daily_dollar_volume_20"] = (closes * group["raw_volume"].astype(float)).clip(
            lower=25_000_000.0
        )
        frames.append(group)

    return pd.concat(frames, ignore_index=True)


def _sector_by_symbol(
    panel_data: HistoricalPanelData,
    signal_session: date,
) -> dict[str, str | None]:
    active_reference = active_symbol_reference_rows(
        panel_data.symbol_reference,
        signal_session,
    )
    return {str(row["symbol"]): str(row["sector"]) for _, row in active_reference.iterrows()}


def _next_session_market_data(ohlcv: pd.DataFrame, next_session: date) -> pd.DataFrame:
    market_data = ohlcv.loc[pd.to_datetime(ohlcv["session_date"]).dt.date == next_session].copy()
    return market_data[
        [
            "symbol",
            "session_date",
            "raw_open",
            "raw_high",
            "raw_low",
            "raw_close",
            "raw_volume",
        ]
    ].reset_index(drop=True)
