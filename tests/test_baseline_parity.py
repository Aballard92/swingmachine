from __future__ import annotations

import json
from datetime import UTC, date, datetime

from swingmachine.baseline import build_swing_baseline_manifest_from_profile_alias
from swingmachine.baseline_parity import (
    compare_baseline_report_package_files,
    compare_baseline_report_packages,
    write_baseline_parity_report_json,
)
from swingmachine.baseline_reporting import (
    build_baseline_report_package,
    write_baseline_report_package_json,
)
from swingmachine.enums import RegimeState
from swingmachine.replay import (
    compare_historical_portfolio_lifecycle_output_dirs,
    compare_historical_scanner_replay_output_dirs,
    write_historical_portfolio_lifecycle_parity_report_json,
    write_historical_scanner_parity_report_json,
)
from swingmachine.swing_contracts import SwingCandidate, SwingRankingResult, build_quality_score

PROFILE_ALIAS_PATH = "config/swing_machine_v0_1_profile.yaml"


def _manifest():
    return build_swing_baseline_manifest_from_profile_alias(PROFILE_ALIAS_PATH)


def _candidate(*, score_percentile: float = 1.0) -> SwingCandidate:
    score = build_quality_score(score_raw=1.0, score_percentile=score_percentile)
    return SwingCandidate(
        candidate_id="candidate:RF_TPC_V2:AAA:2026-04-23",
        strategy_id="RF_TPC_V2",
        config_hash=_manifest().config_hash,
        symbol="AAA",
        session_date=date(2026, 4, 23),
        regime_state=RegimeState.RISK_ON,
        eligible=True,
        quality_score=score,
        ranking=SwingRankingResult(
            rank=1,
            score=score,
            trend_quality=0.8,
            dist_to_52w_high=0.01,
            tie_break_symbol="AAA",
        ),
    )


def test_baseline_parity_passes_for_equivalent_packages_with_different_package_metadata() -> None:
    manifest = _manifest()
    research_package = build_baseline_report_package(
        manifest,
        generated_at=datetime(2026, 5, 5, 15, 0, tzinfo=UTC),
        candidates=(_candidate(),),
    )
    runtime_package = build_baseline_report_package(
        manifest,
        generated_at=datetime(2026, 5, 5, 16, 0, tzinfo=UTC),
        candidates=(_candidate(),),
    )

    report = compare_baseline_report_packages(research_package, runtime_package)

    assert report.passed is True
    assert report.difference_count == 0
    assert report.differences == ()


def test_baseline_parity_reports_field_level_candidate_difference() -> None:
    manifest = _manifest()
    research_package = build_baseline_report_package(manifest, candidates=(_candidate(),))
    runtime_package = build_baseline_report_package(
        manifest,
        candidates=(_candidate(score_percentile=0.9),),
    )

    report = compare_baseline_report_packages(research_package, runtime_package)

    assert report.passed is False
    assert report.difference_count > 0
    assert (
        "candidate",
        "candidate:RF_TPC_V2:AAA:2026-04-23",
        "quality_score.score_percentile",
    ) in {
        (difference.artifact_type, difference.artifact_id, difference.field_path)
        for difference in report.differences
    }


def test_baseline_parity_reports_missing_candidate() -> None:
    manifest = _manifest()
    research_package = build_baseline_report_package(manifest, candidates=(_candidate(),))
    runtime_package = build_baseline_report_package(manifest)

    report = compare_baseline_report_packages(research_package, runtime_package)

    assert report.passed is False
    assert (
        "candidate",
        "candidate:RF_TPC_V2:AAA:2026-04-23",
        "__missing__",
    ) in {
        (difference.artifact_type, difference.artifact_id, difference.field_path)
        for difference in report.differences
    }


def test_baseline_parity_reports_manifest_config_hash_difference() -> None:
    manifest = _manifest()
    research_package = build_baseline_report_package(manifest)
    runtime_manifest = manifest.model_copy(update={"config_hash": "different-config-hash"})
    runtime_package = build_baseline_report_package(runtime_manifest)

    report = compare_baseline_report_packages(research_package, runtime_package)

    assert report.passed is False
    assert (
        "manifest",
        "swing_machine_v0_1",
        "config_hash",
    ) in {
        (difference.artifact_type, difference.artifact_id, difference.field_path)
        for difference in report.differences
    }


def test_baseline_parity_compares_written_research_and_runtime_packages(tmp_path) -> None:
    manifest = _manifest()
    research_package_path = write_baseline_report_package_json(
        build_baseline_report_package(
            manifest,
            generated_at=datetime(2026, 5, 5, 15, 0, tzinfo=UTC),
            candidates=(_candidate(),),
        ),
        tmp_path / "research" / "baseline_report_package.json",
    )
    runtime_package_path = write_baseline_report_package_json(
        build_baseline_report_package(
            manifest,
            generated_at=datetime(2026, 5, 5, 16, 0, tzinfo=UTC),
            candidates=(_candidate(),),
        ),
        tmp_path / "runtime" / "baseline_report_package.json",
    )

    report = compare_baseline_report_package_files(
        research_package_path,
        runtime_package_path,
        comparison_id="selected-period-smoke",
    )
    report_path = write_baseline_parity_report_json(
        report,
        tmp_path / "baseline_parity_report.json",
    )

    assert report.passed is True
    assert report.difference_count == 0
    assert report.comparison_id == "selected-period-smoke"
    assert report_path.read_text(encoding="utf-8").startswith("{\n")


def test_scanner_parity_compares_density_artifacts_ignoring_timestamps(tmp_path) -> None:
    research_dir = tmp_path / "research"
    runtime_dir = tmp_path / "runtime"
    research_dir.mkdir()
    runtime_dir.mkdir()
    artifacts = {
        "scanner_replay_summary.json": {
            "panel_id": "panel-1",
            "status": "PASS",
            "started_at": "2026-05-06T10:00:00",
            "completed_at": "2026-05-06T10:01:00",
            "processed_signal_session_count": 2,
            "total_setups": 1,
        },
        "scanner_session_results.json": {
            "panel_id": "panel-1",
            "session_results": [
                {
                    "signal_session": "2026-04-23",
                    "next_session": "2026-04-24",
                    "density": {"accepted_setup_count": 1},
                }
            ],
        },
        "scanner_decision_density.json": {
            "panel_id": "panel-1",
            "total_decision_traces": 4,
            "sessions": [{"signal_session": "2026-04-23", "accepted_setup_count": 1}],
        },
        "scanner_rejection_reasons.json": {
            "panel_id": "panel-1",
            "aggregate_reason_counts": {"NO_PATTERN_VALID": 1},
        },
        "scanner_material_decisions.json": {
            "panel_id": "panel-1",
            "sessions": [{"signal_session": "2026-04-23", "accepted_setup_symbols": ["AAA"]}],
        },
        "scanner_baseline_report_package.json": {
            "baseline_id": "swing_machine_v0_1",
            "summary": {
                "started_at": "2026-05-06T10:00:00",
                "completed_at": "2026-05-06T10:01:00",
                "total_setups": 1,
            },
        },
    }
    for artifact_name, payload in artifacts.items():
        write_json = json.dumps(payload, indent=2) + "\n"
        (research_dir / artifact_name).write_text(write_json, encoding="utf-8")
        runtime_payload = payload | {}
        if artifact_name == "scanner_replay_summary.json":
            runtime_payload = payload | {
                "started_at": "2026-05-06T11:00:00",
                "completed_at": "2026-05-06T11:01:00",
            }
        (runtime_dir / artifact_name).write_text(
            json.dumps(runtime_payload, indent=2) + "\n",
            encoding="utf-8",
        )

    report = compare_historical_scanner_replay_output_dirs(
        research_dir,
        runtime_dir,
        comparison_id="scanner-smoke",
    )
    report_path = write_historical_scanner_parity_report_json(
        report,
        tmp_path / "scanner_parity_report.json",
    )

    assert report.passed is True
    assert report.difference_count == 0
    assert report_path.read_text(encoding="utf-8").startswith("{\n")

    changed = artifacts["scanner_decision_density.json"] | {"total_decision_traces": 5}
    (runtime_dir / "scanner_decision_density.json").write_text(
        json.dumps(changed, indent=2) + "\n",
        encoding="utf-8",
    )
    changed_report = compare_historical_scanner_replay_output_dirs(research_dir, runtime_dir)

    assert changed_report.passed is False
    assert (
        "scanner_replay",
        "scanner_decision_density",
        "total_decision_traces",
    ) in {
        (difference.artifact_type, difference.artifact_id, difference.field_path)
        for difference in changed_report.differences
    }


def test_lifecycle_parity_compares_artifacts_ignoring_run_metadata(tmp_path) -> None:
    research_dir = tmp_path / "research_lifecycle"
    runtime_dir = tmp_path / "runtime_lifecycle"
    research_dir.mkdir()
    runtime_dir.mkdir()
    artifacts = {
        "portfolio_lifecycle_replay_summary.json": {
            "panel_id": "panel-1",
            "status": "WARN",
            "started_at": "2026-05-06T10:00:00",
            "completed_at": "2026-05-06T10:01:00",
            "processed_session_count": 2,
            "transition_count": 1,
        },
        "portfolio_lifecycle_session_states.json": {
            "panel_id": "panel-1",
            "session_states": [
                {
                    "session_date": "2026-04-23",
                    "equity": 100000.0,
                    "open_position_count": 0,
                }
            ],
        },
        "portfolio_lifecycle_transitions.json": {
            "panel_id": "panel-1",
            "transitions": [
                {
                    "transition_id": "transition-1",
                    "symbol": "AAA",
                    "trigger": "ENTRY_SUBMITTED",
                }
            ],
        },
        "portfolio_lifecycle_positions.json": {
            "panel_id": "panel-1",
            "positions": [],
        },
        "portfolio_lifecycle_pending_orders.json": {
            "panel_id": "panel-1",
            "pending_orders": [],
        },
        "portfolio_lifecycle_exposure.json": {
            "panel_id": "panel-1",
            "exposure": [{"session_date": "2026-04-23", "equity": 100000.0}],
        },
        "portfolio_lifecycle_reconciliation.json": {
            "status": "WARN",
            "checked_at": "2026-05-06T10:01:00",
            "difference_count": 0,
            "warnings": ["PENDING_ORDER_DETAILS_NOT_AVAILABLE_FROM_BACKTEST_RESULT"],
        },
        "portfolio_lifecycle_baseline_package.json": {
            "baseline_id": "swing_machine_v0_1",
            "package_type": "portfolio_lifecycle_v1",
            "summary": {
                "started_at": "2026-05-06T10:00:00",
                "completed_at": "2026-05-06T10:01:00",
                "transition_count": 1,
            },
        },
    }
    for artifact_name, payload in artifacts.items():
        (research_dir / artifact_name).write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        runtime_payload = payload | {}
        if artifact_name == "portfolio_lifecycle_replay_summary.json":
            runtime_payload = payload | {
                "started_at": "2026-05-06T11:00:00",
                "completed_at": "2026-05-06T11:01:00",
            }
        if artifact_name == "portfolio_lifecycle_reconciliation.json":
            runtime_payload = payload | {
                "checked_at": "2026-05-06T11:01:00",
            }
        (runtime_dir / artifact_name).write_text(
            json.dumps(runtime_payload, indent=2) + "\n",
            encoding="utf-8",
        )

    report = compare_historical_portfolio_lifecycle_output_dirs(
        research_dir,
        runtime_dir,
        comparison_id="lifecycle-smoke",
    )
    report_path = write_historical_portfolio_lifecycle_parity_report_json(
        report,
        tmp_path / "lifecycle_parity_report.json",
    )

    assert report.passed is True
    assert report.difference_count == 0
    assert report_path.read_text(encoding="utf-8").startswith("{\n")

    changed = artifacts["portfolio_lifecycle_transitions.json"] | {
        "transitions": [
            {
                "transition_id": "transition-1",
                "symbol": "AAA",
                "trigger": "ENTRY_FILLED",
            }
        ]
    }
    (runtime_dir / "portfolio_lifecycle_transitions.json").write_text(
        json.dumps(changed, indent=2) + "\n",
        encoding="utf-8",
    )
    changed_report = compare_historical_portfolio_lifecycle_output_dirs(
        research_dir,
        runtime_dir,
    )

    assert changed_report.passed is False
    assert (
        "portfolio_lifecycle_replay",
        "portfolio_lifecycle_transitions",
        "transitions[0].trigger",
    ) in {
        (difference.artifact_type, difference.artifact_id, difference.field_path)
        for difference in changed_report.differences
    }
