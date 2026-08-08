from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from swingmachine.pullback_diagnostic import (
    PullbackDiagnosticInputPaths,
    build_pullback_fill_lifecycle_diagnostic,
    write_pullback_fill_lifecycle_diagnostic,
)


def test_pullback_diagnostic_classifies_fill_states_and_missing_fields(
    tmp_path: Path,
) -> None:
    paths = _write_input_artifacts(tmp_path)

    report = build_pullback_fill_lifecycle_diagnostic(
        input_paths=paths,
        generated_at=datetime(2026, 5, 11, 12, 0, tzinfo=UTC),
    )

    assert report["verdict"]["verdict"] == "INCONCLUSIVE"
    assert report["populations"]["all_accepted_pullback"]["row_count"] == 4
    assert report["populations"]["traded_accepted_pullback"]["row_count"] == 1
    assert report["populations"]["untraded_accepted_pullback"]["row_count"] == 3
    assert report["fill_classification"]["counts"] == {
        "FILLED": 1,
        "NOT_SUBMITTED_EXISTING_SYMBOL_LIFECYCLE": 1,
        "UNFILLED_CANCELLED": 1,
        "UNKNOWN_NO_ORDER_EVIDENCE": 1,
    }
    assert report["fill_classification"]["submitted_count"] == 2
    assert report["fill_classification"]["submitted_fill_rate"] == 0.5
    assert report["fill_classification"][
        "not_submitted_existing_symbol_lifecycle_count"
    ] == 1
    assert report["fill_classification"]["unknown_count"] == 1
    filled = report["candidate_rows"][0]
    assert filled["entry_fill_price"] == 103.0
    assert filled["fill_delay_sessions"] == 1
    assert filled["stop_hit"] is True
    assert filled["target_hit"] is None
    overlap = report["candidate_rows"][2]
    assert (
        overlap["fill_classification"]
        == "NOT_SUBMITTED_EXISTING_SYMBOL_LIFECYCLE"
    )
    assert overlap["scanner_order_plan_present"] is True
    assert overlap["overlapping_symbol_lifecycles"] == [
        {
            "end_date": "2026-01-10",
            "setup_id": "setup-filled",
            "source_kinds": ["pending_order", "trade", "transition"],
            "start_date": "2026-01-01",
            "state_at_candidate": "OPEN_POSITION",
        }
    ]
    assert (
        report["candidate_rows"][3]["fill_classification"]
        == "UNKNOWN_NO_ORDER_EVIDENCE"
    )
    missing = {row["field"]: row["status"] for row in report["missing_unavailable_fields"]}
    assert missing["target_hit"] == "NOT_FOUND"
    assert missing["r_multiple"] == "DERIVED_PARTIAL"
    assert missing["forward_40d"] == "NOT_FOUND"
    assert missing["filled"] == "PARTIAL_DERIVED"
    assert set(report["source_artifact_sha256"]) == set(report["source_artifacts"])


def test_pullback_diagnostic_writer_outputs_json_and_markdown(tmp_path: Path) -> None:
    paths = _write_input_artifacts(tmp_path)
    report = build_pullback_fill_lifecycle_diagnostic(
        input_paths=paths,
        generated_at=datetime(2026, 5, 11, 12, 0, tzinfo=UTC),
    )

    written = write_pullback_fill_lifecycle_diagnostic(report, tmp_path / "diagnostic")

    assert set(written) == {"json", "markdown"}
    payload = json.loads(Path(written["json"]).read_text())
    markdown = Path(written["markdown"]).read_text()
    assert payload["report_id"] == "pullback_fill_lifecycle_diagnostic_20260511T120000Z"
    assert "PULLBACK Fill/Lifecycle Diagnostic Report" in markdown
    assert "Verdict: `INCONCLUSIVE`" in markdown
    assert "20-Session Benchmark Excess By Lifecycle Classification" in markdown
    assert "Source | Path | SHA-256" in markdown
    assert "`target_hit`" in markdown


def _write_input_artifacts(tmp_path: Path) -> PullbackDiagnosticInputPaths:
    attribution = tmp_path / "feature_outcome_attribution_dataset.json"
    scanner = tmp_path / "scanner_material_decisions.json"
    trade_ledger = tmp_path / "portfolio_lifecycle_trade_ledger.json"
    pending_orders = tmp_path / "portfolio_lifecycle_pending_orders.json"
    transitions = tmp_path / "portfolio_lifecycle_transitions.json"
    root_cause = tmp_path / "root_cause.json"
    traded_lifecycle = tmp_path / "traded_lifecycle.json"
    pattern_benchmark = tmp_path / "pattern_benchmark.json"
    cost_slippage = tmp_path / "cost_slippage.json"
    provider = tmp_path / "provider.json"
    null_denominator = tmp_path / "null_denominator.json"
    feature_stability = tmp_path / "feature_stability.json"

    attribution.write_text(
        json.dumps(
            {
                "summary": {"panel_id": "unit"},
                "rows": [
                    _attribution_row(
                        symbol="AAA",
                        setup_id="setup-filled",
                        traded=True,
                        net_pnl=120.0,
                        net_return=0.10,
                        excess_20=0.05,
                    ),
                    _attribution_row(
                        symbol="BBB",
                        setup_id="setup-cancelled",
                        traded=False,
                        net_pnl=None,
                        net_return=None,
                        excess_20=-0.04,
                    ),
                    _attribution_row(
                        symbol="AAA",
                        setup_id="setup-overlap",
                        signal_session="2026-01-04",
                        traded=False,
                        net_pnl=None,
                        net_return=None,
                        excess_20=-0.03,
                    ),
                    _attribution_row(
                        symbol="CCC",
                        setup_id="setup-unknown",
                        traded=False,
                        net_pnl=None,
                        net_return=None,
                        excess_20=-0.02,
                    ),
                    _attribution_row(
                        symbol="DDD",
                        setup_id="setup-tight",
                        pattern_type="TIGHT_BASE",
                        traded=True,
                        net_pnl=-50.0,
                        net_return=-0.05,
                        excess_20=-0.02,
                    ),
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    scanner.write_text(
        json.dumps(
            {
                "sessions": [
                    {
                        "material_decision_rows": [
                            {
                                "setup_id": setup_id,
                                "order_plan_id": f"order-plan-{setup_id}",
                                "risk_plan_id": f"risk-plan-{setup_id}",
                                "reason_codes": ["SETUP_VALID"],
                            }
                            for setup_id in (
                                "setup-filled",
                                "setup-cancelled",
                                "setup-overlap",
                                "setup-unknown",
                            )
                        ]
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    trade_ledger.write_text(
        json.dumps(
            {
                "trades": [
                    {
                        "symbol": "AAA",
                        "setup_id": "setup-filled",
                        "trade_id": "trade-1",
                        "entry_signal_date": "2026-01-01",
                        "entry_fill_date": "2026-01-03",
                        "entry_fill_price": 103.0,
                        "entry_reference_price": 102.0,
                        "exit_fill_date": "2026-01-10",
                        "exit_reason": "INITIAL_STOP",
                        "bars_held": 5,
                        "initial_stop": 99.0,
                        "final_stop": 100.0,
                        "quantity": 10,
                        "net_pnl": 120.0,
                        "net_return": 0.10,
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    pending_orders.write_text(
        json.dumps(
            {
                "pending_orders": [
                    {
                        "symbol": "AAA",
                        "setup_id": "setup-filled",
                        "status": "FILLED",
                        "order_type": "STOP_LIMIT",
                        "session_date": "2026-01-03",
                    },
                    {
                        "symbol": "BBB",
                        "setup_id": "setup-cancelled",
                        "status": "CANCELLED",
                        "order_type": "STOP_LIMIT",
                        "cancel_reason": "EXPIRED",
                        "session_date": "2026-01-04",
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    transitions.write_text(
        json.dumps(
            {
                "transitions": [
                    {
                        "symbol": "AAA",
                        "setup_id": "setup-filled",
                        "session_date": "2026-01-03",
                        "from_state": "PENDING_ENTRY",
                        "to_state": "ACTIVE",
                        "trigger": "ENTRY_FILLED",
                        "reason_codes": [],
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    root_cause.write_text(
        json.dumps(
            {
                "status": "WARN",
                "conclusion": "UNIT",
                "recommendation": "DEEPER_REPLAY_ONLY_DO_NOT_BUILD_PROFILE_YET",
                "flags": ["traded_sample_too_small"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    traded_lifecycle.write_text(
        json.dumps({"status": "WARN", "conclusion": "UNIT", "trade_count": 1})
        + "\n",
        encoding="utf-8",
    )
    pattern_benchmark.write_text(
        json.dumps(
            {
                "status": "WARN",
                "conclusion": "UNIT",
                "patterns": {
                    "PULLBACK": {
                        "recommendation": "MIXED_PATTERN_EVIDENCE_REQUIRES_DEEPER_RESEARCH",
                        "sample_grade": "INSUFFICIENT",
                    }
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    cost_slippage.write_text(
        json.dumps(
            {
                "status": "WARN",
                "conclusion": "UNIT",
                "scenario_extra_round_trip_cost_bps": [0, 10, 25, 50],
                "by_pattern": {
                    "PULLBACK": {
                        "scenario_metrics": {
                            "0": {"net_pnl": 120.0, "win_rate": 1.0},
                            "50": {"net_pnl": 100.0, "win_rate": 1.0},
                        }
                    }
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    provider.write_text(
        json.dumps({"status": "WARN", "decision": "UNIT", "scope": "contract only"})
        + "\n",
        encoding="utf-8",
    )
    null_denominator.write_text(
        json.dumps({"status": "PASS", "conclusion": "UNIT", "report_id": "null"})
        + "\n",
        encoding="utf-8",
    )
    feature_stability.write_text(
        json.dumps({"status": "WARN", "conclusion": "UNIT", "report_id": "feature"})
        + "\n",
        encoding="utf-8",
    )

    return PullbackDiagnosticInputPaths(
        attribution_dataset=attribution,
        scanner_material_decisions=scanner,
        lifecycle_trade_ledger=trade_ledger,
        lifecycle_pending_orders=pending_orders,
        lifecycle_transitions=transitions,
        root_cause_report=root_cause,
        traded_lifecycle_report=traded_lifecycle,
        pattern_benchmark_report=pattern_benchmark,
        cost_slippage_report=cost_slippage,
        provider_comparison_report=provider,
        null_denominator_report=null_denominator,
        feature_stability_report=feature_stability,
    )


def _attribution_row(
    *,
    symbol: str,
    setup_id: str,
    traded: bool,
    net_pnl: float | None,
    net_return: float | None,
    excess_20: float,
    pattern_type: str = "PULLBACK",
    signal_session: str = "2026-01-01",
) -> dict[str, object]:
    return {
        "panel_id": "unit",
        "symbol": symbol,
        "signal_session": signal_session,
        "next_session": "2026-01-02",
        "candidate_id": f"candidate-{setup_id}",
        "setup_id": setup_id,
        "decision": "ACCEPTED_SETUP",
        "pattern_type": pattern_type,
        "reason_codes": ["SETUP_VALID"],
        "rejection_reasons": [],
        "traded": traded,
        "trade_id": "trade-1" if traded else None,
        "entry_fill_date": "2026-01-03" if traded else None,
        "exit_fill_date": "2026-01-10" if traded else None,
        "exit_reason": "INITIAL_STOP" if traded else None,
        "bars_held": 5 if traded else None,
        "net_pnl": net_pnl,
        "net_return": net_return,
        "forward_close_returns": {"20": 0.01},
        "benchmark_forward_close_returns": {"20": 0.02},
        "forward_close_excess_returns": {"20": excess_20},
        "feature_snapshot": {"rs_vs_benchmark_20": 0.1},
    }
