from __future__ import annotations

import json

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
from swingmachine.enums import SymbolLifecycleState
from tests.fixtures.lifecycle_artifacts import (
    lifecycle_artifact_package_fixture,
    lifecycle_replay_summary_fixture,
    lifecycle_session_state_fixture,
    lifecycle_transition_fixtures,
)


def test_lifecycle_fixture_package_is_json_serializable() -> None:
    package = lifecycle_artifact_package_fixture()

    payload = {
        "summary": package.summary.model_dump(mode="json"),
        "session_states": [
            state.model_dump(mode="json") for state in package.session_states
        ],
        "transitions": [
            transition.model_dump(mode="json") for transition in package.transitions
        ],
        "positions": [
            position.model_dump(mode="json") for position in package.positions
        ],
        "pending_orders": [
            pending_order.model_dump(mode="json")
            for pending_order in package.pending_orders
        ],
        "exposure": [
            exposure.model_dump(mode="json") for exposure in package.exposure
        ],
        "reconciliation": package.reconciliation.model_dump(mode="json"),
        "manifest": package.manifest.model_dump(mode="json"),
    }

    json.dumps(payload)

    assert payload["summary"]["processed_session_count"] == 2
    assert payload["session_states"][0]["blocked_reason_counts"]["PORTFOLIO_HEAT"] == 1
    assert payload["manifest"]["lifecycle_parity_report_path"].endswith(
        "portfolio_lifecycle_parity_report.json"
    )


def test_lifecycle_fixture_package_round_trips_through_contracts() -> None:
    package = lifecycle_artifact_package_fixture()

    summary = HistoricalPortfolioLifecycleReplaySummary.model_validate(
        package.summary.model_dump(mode="json")
    )
    session_states = tuple(
        HistoricalPortfolioLifecycleSessionState.model_validate(
            state.model_dump(mode="json")
        )
        for state in package.session_states
    )
    transitions = tuple(
        HistoricalPortfolioLifecycleTransition.model_validate(
            transition.model_dump(mode="json")
        )
        for transition in package.transitions
    )
    positions = tuple(
        HistoricalPortfolioLifecyclePositionSnapshot.model_validate(
            position.model_dump(mode="json")
        )
        for position in package.positions
    )
    pending_orders = tuple(
        HistoricalPortfolioLifecyclePendingOrderSnapshot.model_validate(
            pending_order.model_dump(mode="json")
        )
        for pending_order in package.pending_orders
    )
    exposure = tuple(
        HistoricalPortfolioLifecycleExposureSnapshot.model_validate(
            exposure_snapshot.model_dump(mode="json")
        )
        for exposure_snapshot in package.exposure
    )
    reconciliation = HistoricalPortfolioLifecycleReconciliation.model_validate(
        package.reconciliation.model_dump(mode="json")
    )
    manifest = HistoricalPortfolioLifecycleArtifactManifest.model_validate(
        package.manifest.model_dump(mode="json")
    )

    assert summary.transition_count == len(transitions)
    assert len(session_states) == 1
    assert len(positions) == summary.position_snapshot_count
    assert len(pending_orders) == summary.pending_order_snapshot_count
    assert len(exposure) == summary.exposure_snapshot_count
    assert reconciliation.difference_count == 0
    assert manifest.lifecycle_replay_summary_path.endswith(
        "portfolio_lifecycle_replay_summary.json"
    )


def test_lifecycle_transition_fixtures_cover_core_outcomes() -> None:
    transitions = lifecycle_transition_fixtures()
    state_pairs = {(transition.from_state, transition.to_state) for transition in transitions}
    triggers = {transition.trigger for transition in transitions}
    reason_codes = {
        reason_code
        for transition in transitions
        for reason_code in transition.reason_codes
    }

    assert (
        SymbolLifecycleState.ARMED,
        SymbolLifecycleState.PENDING_ENTRY,
    ) in state_pairs
    assert (
        SymbolLifecycleState.PENDING_ENTRY,
        SymbolLifecycleState.ACTIVE,
    ) in state_pairs
    assert (
        SymbolLifecycleState.ACTIVE,
        SymbolLifecycleState.EXIT_PENDING,
    ) in state_pairs
    assert "PORTFOLIO_GATE_BLOCKED" in triggers
    assert "PORTFOLIO_HEAT" in reason_codes


def test_lifecycle_fixture_builders_support_state_variants() -> None:
    session_state = lifecycle_session_state_fixture(
        open_position_count=2,
        pending_entry_count=0,
        exit_pending_count=2,
    )
    summary = lifecycle_replay_summary_fixture()

    assert session_state.exit_pending_count == session_state.open_position_count
    assert summary.final_equity > summary.initial_equity
