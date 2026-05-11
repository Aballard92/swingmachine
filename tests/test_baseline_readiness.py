from __future__ import annotations

from datetime import UTC, datetime

from swingmachine.baseline import (
    build_swing_baseline_manifest_from_profile_alias,
    load_swing_selected_qualification_plan,
    required_qualification_check_ids,
)
from swingmachine.baseline_parity import compare_baseline_report_packages
from swingmachine.baseline_readiness import (
    evaluate_serious_full_run_freeze_readiness,
    preflight_selected_qualification_plan,
    write_freeze_readiness_decision_json,
    write_selected_qualification_preflight_json,
)
from swingmachine.baseline_reporting import build_baseline_report_package

PROFILE_ALIAS_PATH = "config/swing_machine_v0_1_profile.yaml"
SELECTED_PERIOD_PLAN_PATH = "config/swing_machine_v0_1_selected_periods.yaml"


def _selected_period_plan():
    return load_swing_selected_qualification_plan(SELECTED_PERIOD_PLAN_PATH)


def _passing_parity_report(manifest):
    research_package = build_baseline_report_package(
        manifest,
        generated_at=datetime(2026, 5, 5, 15, 0, tzinfo=UTC),
    )
    runtime_package = build_baseline_report_package(
        manifest,
        generated_at=datetime(2026, 5, 5, 16, 0, tzinfo=UTC),
    )
    return compare_baseline_report_packages(research_package, runtime_package)


def test_current_baseline_freeze_readiness_blocks_serious_full_run(tmp_path) -> None:
    manifest = build_swing_baseline_manifest_from_profile_alias(PROFILE_ALIAS_PATH)

    decision = evaluate_serious_full_run_freeze_readiness(
        manifest,
        selected_period_plan=_selected_period_plan(),
        parity_reports=(_passing_parity_report(manifest),),
        operator_approved=False,
        evaluated_at=datetime(2026, 5, 5, 17, 0, tzinfo=UTC),
    )
    decision_path = write_freeze_readiness_decision_json(
        decision,
        tmp_path / "freeze_readiness.json",
    )

    assert decision.decision == "BLOCK"
    assert decision.serious_full_run_allowed is False
    assert decision.blocker_count >= 2
    assert {
        "manifest_checks_incomplete",
        "operator_approval_missing",
    } <= {blocker.code for blocker in decision.blockers}
    assert decision_path.read_text(encoding="utf-8").startswith("{\n")


def test_freeze_readiness_allows_only_when_all_gates_are_satisfied() -> None:
    manifest = build_swing_baseline_manifest_from_profile_alias(
        PROFILE_ALIAS_PATH,
        satisfied_check_ids=required_qualification_check_ids(),
    )

    decision = evaluate_serious_full_run_freeze_readiness(
        manifest,
        selected_period_plan=_selected_period_plan(),
        parity_reports=(_passing_parity_report(manifest),),
        operator_approved=True,
    )

    assert decision.decision == "ALLOW"
    assert decision.serious_full_run_allowed is True
    assert decision.blocker_count == 0
    assert decision.blockers == ()


def test_freeze_readiness_blocks_failed_parity_evidence() -> None:
    manifest = build_swing_baseline_manifest_from_profile_alias(
        PROFILE_ALIAS_PATH,
        satisfied_check_ids=required_qualification_check_ids(),
    )
    passing_report = _passing_parity_report(manifest)
    failed_report = passing_report.model_copy(
        update={
            "comparison_id": "failed-selected-period",
            "passed": False,
            "difference_count": 1,
        }
    )

    decision = evaluate_serious_full_run_freeze_readiness(
        manifest,
        selected_period_plan=_selected_period_plan(),
        parity_reports=(failed_report,),
        operator_approved=True,
    )

    assert decision.decision == "BLOCK"
    assert (
        "parity_evidence_failed",
        ("failed-selected-period",),
    ) in {(blocker.code, blocker.evidence) for blocker in decision.blockers}


def test_selected_period_preflight_blocks_without_data_manifests(tmp_path) -> None:
    result = preflight_selected_qualification_plan(SELECTED_PERIOD_PLAN_PATH)
    result_path = write_selected_qualification_preflight_json(
        result,
        tmp_path / "selected_period_preflight.json",
    )

    assert result.passed is False
    assert result.blocker_count == 1
    assert result.blockers[0].code == "data_manifest_missing"
    assert result.period_ids == (
        "smoke_recent_5_sessions",
        "recent_medium_replay_window",
        "historical_contract_stability_window",
    )
    assert "baseline_report_package.json" in result.required_artifacts
    assert result_path.read_text(encoding="utf-8").startswith("{\n")


def test_selected_period_preflight_passes_with_declared_data_manifests(tmp_path) -> None:
    plan = _selected_period_plan()
    data_manifest_by_period = {}
    for period in plan.periods:
        manifest_path = tmp_path / period.period_id / "manifest.yaml"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text("panel_id: placeholder\n", encoding="utf-8")
        data_manifest_by_period[period.period_id] = manifest_path

    result = preflight_selected_qualification_plan(
        SELECTED_PERIOD_PLAN_PATH,
        data_manifest_by_period=data_manifest_by_period,
    )

    assert result.passed is True
    assert result.blocker_count == 0
    assert result.blockers == ()
