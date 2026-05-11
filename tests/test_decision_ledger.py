from __future__ import annotations

import json
from pathlib import Path

from swingmachine.decision_ledger import (
    build_decision_ledger_report,
    write_decision_ledger_report_json,
)
from swingmachine.enums import ReviewStatus


def test_decision_ledger_links_lifecycle_order_and_position_snapshots(
    tmp_path: Path,
) -> None:
    manifest_path = _write_lifecycle_artifacts(tmp_path)
    output_path = tmp_path / "decision_ledger.json"

    report = build_decision_ledger_report(
        lifecycle_artifact_manifest_path=manifest_path,
        scanner_material_decisions_path=tmp_path / "scanner_material_decisions.json",
    )
    written_path = write_decision_ledger_report_json(report, output_path)

    assert written_path == output_path
    assert report.status is ReviewStatus.PASS
    assert report.row_count == 2
    assert report.accepted_setup_count == 1
    assert report.rejected_candidate_count == 1
    assert report.missing_link_count == 0
    row = next(row for row in report.rows if row.symbol == "AAA")
    assert row.symbol == "AAA"
    assert row.signal_id == "signal-1"
    assert row.risk_plan_id == "risk-1"
    assert row.order_plan_id == "order-1"
    assert row.order_intent_id == "intent-1"
    assert row.position_id == "position-1"
    assert row.entry_submitted
    assert row.entry_filled
    assert row.trade_closed
    assert row.missing_links == ()
    rejected = next(row for row in report.rows if row.symbol == "BBB")
    assert rejected.decision == "REJECTED_CANDIDATE"
    assert rejected.reason_codes == ("score.too_low",)
    assert rejected.lifecycle_state == "REJECTED"
    assert rejected.missing_links == ()


def _write_lifecycle_artifacts(tmp_path: Path) -> Path:
    _write_json(
        tmp_path / "portfolio_lifecycle_transitions.json",
        {
            "panel_id": "panel-1",
            "transitions": [
                {
                    "transition_id": "t1",
                    "symbol": "AAA",
                    "setup_id": "setup-1",
                    "session_date": "2026-01-02",
                    "trigger": "ENTRY_SUBMITTED",
                    "to_state": "PENDING_ENTRY",
                    "reason_codes": ["ENTRY"],
                },
                {
                    "transition_id": "t2",
                    "symbol": "AAA",
                    "setup_id": "setup-1",
                    "session_date": "2026-01-03",
                    "trigger": "ENTRY_FILLED",
                    "to_state": "ACTIVE",
                    "reason_codes": ["ENTRY"],
                },
                {
                    "transition_id": "t3",
                    "symbol": "AAA",
                    "setup_id": "setup-1",
                    "session_date": "2026-01-10",
                    "trigger": "EXIT_FILLED",
                    "to_state": "CLOSED",
                    "reason_codes": ["TRAIL_STOP"],
                },
            ],
        },
    )
    _write_json(
        tmp_path / "portfolio_lifecycle_pending_orders.json",
        {
            "panel_id": "panel-1",
            "pending_orders": [
                {
                    "symbol": "AAA",
                    "setup_id": "setup-1",
                    "session_date": "2026-01-02",
                    "order_intent_id": "intent-1",
                }
            ],
        },
    )
    _write_json(
        tmp_path / "portfolio_lifecycle_positions.json",
        {
            "panel_id": "panel-1",
            "positions": [
                {
                    "symbol": "AAA",
                    "setup_id": "setup-1",
                    "session_date": "2026-01-10",
                    "order_intent_id": "intent-1",
                    "position_id": "position-1",
                    "state": "CLOSED",
                }
            ],
        },
    )
    _write_json(
        tmp_path / "portfolio_lifecycle_replay_summary.json",
        {
            "panel_id": "panel-1",
            "status": "PASS",
            "entry_submitted_count": 1,
        },
    )
    _write_json(
        tmp_path / "scanner_material_decisions.json",
        {
            "panel_id": "panel-1",
            "status": "PASS",
            "sessions": [
                {
                    "signal_session": "2026-01-02",
                    "accepted_setup_symbols": ["AAA"],
                    "material_decision_rows": [
                        {
                            "symbol": "AAA",
                            "signal_session": "2026-01-02",
                            "next_session": "2026-01-03",
                            "setup_id": "setup-1",
                            "decision": "ACCEPTED_SETUP",
                            "reason_codes": ["ACCEPTED_SETUP"],
                            "candidate_id": "candidate-1",
                            "candidate_score_pct": 1.0,
                            "rank": 1,
                            "signal_id": "signal-1",
                            "risk_plan_id": "risk-1",
                            "order_plan_id": "order-1",
                        },
                        {
                            "symbol": "BBB",
                            "signal_session": "2026-01-02",
                            "next_session": "2026-01-03",
                            "setup_id": None,
                            "decision": "REJECTED_CANDIDATE",
                            "reason_codes": ["score.too_low"],
                            "candidate_id": "candidate-2",
                            "candidate_score_pct": 0.2,
                            "rank": 2,
                            "signal_id": None,
                            "risk_plan_id": None,
                            "order_plan_id": None,
                        },
                    ],
                }
            ],
        },
    )
    manifest_path = tmp_path / "portfolio_lifecycle_artifact_manifest.json"
    _write_json(
        manifest_path,
        {
            "panel_id": "panel-1",
            "run_id": "run-1",
            "output_dir": str(tmp_path),
            "lifecycle_transitions_path": str(tmp_path / "portfolio_lifecycle_transitions.json"),
            "lifecycle_pending_orders_path": str(
                tmp_path / "portfolio_lifecycle_pending_orders.json"
            ),
            "lifecycle_positions_path": str(tmp_path / "portfolio_lifecycle_positions.json"),
            "lifecycle_replay_summary_path": str(
                tmp_path / "portfolio_lifecycle_replay_summary.json"
            ),
        },
    )
    return manifest_path


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
