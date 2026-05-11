from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field

from swingmachine.baseline import BASELINE_ID, load_swing_selected_qualification_plan
from swingmachine.modeling import ImmutableModel, NonNegativeInt

GLOBAL_REQUIRED_EVIDENCE_ARTIFACTS: tuple[str, ...] = (
    "selected_period_data_input_preflight.json",
    "selected_period_manifest_build_summary.json",
    "selected_period_preflight.json",
)

PERIOD_REQUIRED_EVIDENCE_ARTIFACTS: tuple[str, ...] = (
    "manifest.yaml",
    "baseline_report_package.json",
    "freeze_readiness.json",
    "replay_summary.json",
    "stage_counts.json",
    "material_decisions.json",
    "decision_traces.json",
    "reconciliation_summary.json",
    "baseline_parity_report.json",
)

EvidenceScope = Literal["global", "period"]


class SwingQualificationEvidenceItem(ImmutableModel):
    artifact_id: str
    scope: EvidenceScope
    artifact_name: str
    path: str
    required: bool = True
    present: bool
    period_id: str | None = None


class SwingQualificationEvidenceIndex(ImmutableModel):
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    generated_at: datetime
    evidence_root: str
    selected_period_plan_path: str
    period_ids: tuple[str, ...]
    artifact_count: NonNegativeInt
    required_artifact_count: NonNegativeInt
    present_required_count: NonNegativeInt
    missing_required_count: NonNegativeInt
    all_required_present: bool
    artifacts: tuple[SwingQualificationEvidenceItem, ...] = Field(default_factory=tuple)

    @property
    def missing_required_artifact_ids(self) -> tuple[str, ...]:
        return tuple(
            artifact.artifact_id
            for artifact in self.artifacts
            if artifact.required and not artifact.present
        )


def build_qualification_evidence_index(
    evidence_root: str | Path,
    *,
    selected_period_plan_path: str | Path,
    generated_at: datetime | None = None,
) -> SwingQualificationEvidenceIndex:
    root = Path(evidence_root)
    selected_plan_path = Path(selected_period_plan_path)
    selected_plan = load_swing_selected_qualification_plan(selected_plan_path)
    artifacts = [
        _global_artifact(root, artifact_name)
        for artifact_name in GLOBAL_REQUIRED_EVIDENCE_ARTIFACTS
    ]
    for period in selected_plan.periods:
        period_root = root / period.period_id
        artifacts.extend(
            _period_artifact(period_root, period.period_id, artifact_name)
            for artifact_name in PERIOD_REQUIRED_EVIDENCE_ARTIFACTS
        )
    required_artifacts = tuple(artifact for artifact in artifacts if artifact.required)
    present_required_count = sum(1 for artifact in required_artifacts if artifact.present)
    missing_required_count = len(required_artifacts) - present_required_count
    return SwingQualificationEvidenceIndex(
        generated_at=generated_at or datetime.now(UTC),
        evidence_root=str(root),
        selected_period_plan_path=str(selected_plan_path),
        period_ids=tuple(period.period_id for period in selected_plan.periods),
        artifact_count=len(artifacts),
        required_artifact_count=len(required_artifacts),
        present_required_count=present_required_count,
        missing_required_count=missing_required_count,
        all_required_present=missing_required_count == 0,
        artifacts=tuple(artifacts),
    )


def write_qualification_evidence_index_json(
    index: SwingQualificationEvidenceIndex,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(index.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output_path


def _global_artifact(root: Path, artifact_name: str) -> SwingQualificationEvidenceItem:
    path = root / artifact_name
    return SwingQualificationEvidenceItem(
        artifact_id=f"global:{artifact_name}",
        scope="global",
        artifact_name=artifact_name,
        path=str(path),
        present=path.exists(),
    )


def _period_artifact(
    period_root: Path,
    period_id: str,
    artifact_name: str,
) -> SwingQualificationEvidenceItem:
    path = period_root / artifact_name
    return SwingQualificationEvidenceItem(
        artifact_id=f"period:{period_id}:{artifact_name}",
        scope="period",
        period_id=period_id,
        artifact_name=artifact_name,
        path=str(path),
        present=path.exists(),
    )


__all__ = [
    "GLOBAL_REQUIRED_EVIDENCE_ARTIFACTS",
    "PERIOD_REQUIRED_EVIDENCE_ARTIFACTS",
    "EvidenceScope",
    "SwingQualificationEvidenceIndex",
    "SwingQualificationEvidenceItem",
    "build_qualification_evidence_index",
    "write_qualification_evidence_index_json",
]
