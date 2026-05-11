from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from swingmachine.qualification_evidence import (
    GLOBAL_REQUIRED_EVIDENCE_ARTIFACTS,
    PERIOD_REQUIRED_EVIDENCE_ARTIFACTS,
    build_qualification_evidence_index,
    write_qualification_evidence_index_json,
)

SELECTED_PERIOD_PLAN_PATH = "config/swing_machine_v0_1_selected_periods.yaml"
PERIOD_IDS = (
    "smoke_recent_5_sessions",
    "recent_medium_replay_window",
    "historical_contract_stability_window",
)


def test_qualification_evidence_index_reports_missing_required_artifacts(
    tmp_path: Path,
) -> None:
    index = build_qualification_evidence_index(
        tmp_path,
        selected_period_plan_path=SELECTED_PERIOD_PLAN_PATH,
        generated_at=datetime(2026, 5, 5, 18, 0, tzinfo=UTC),
    )
    output_path = write_qualification_evidence_index_json(
        index,
        tmp_path / "qualification_evidence_index.json",
    )

    assert index.all_required_present is False
    assert index.period_ids == PERIOD_IDS
    assert index.required_artifact_count == 30
    assert index.present_required_count == 0
    assert index.missing_required_count == 30
    assert "global:selected_period_preflight.json" in index.missing_required_artifact_ids
    assert output_path.read_text(encoding="utf-8").startswith("{\n")


def test_qualification_evidence_index_passes_when_required_artifacts_exist(
    tmp_path: Path,
) -> None:
    for artifact_name in GLOBAL_REQUIRED_EVIDENCE_ARTIFACTS:
        (tmp_path / artifact_name).write_text("{}\n", encoding="utf-8")
    for period_id in PERIOD_IDS:
        period_root = tmp_path / period_id
        period_root.mkdir()
        for artifact_name in PERIOD_REQUIRED_EVIDENCE_ARTIFACTS:
            (period_root / artifact_name).write_text("{}\n", encoding="utf-8")

    index = build_qualification_evidence_index(
        tmp_path,
        selected_period_plan_path=SELECTED_PERIOD_PLAN_PATH,
    )

    assert index.all_required_present is True
    assert index.required_artifact_count == 30
    assert index.present_required_count == 30
    assert index.missing_required_count == 0
    assert index.missing_required_artifact_ids == ()
