from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator

from swingmachine.baseline import (
    BASELINE_ID,
    SwingBaselineManifest,
    SwingBaselineQualificationChecklist,
    build_baseline_qualification_checklist,
    build_swing_baseline_manifest_from_profile_alias,
)
from swingmachine.modeling import ImmutableModel, NonNegativeInt
from swingmachine.swing_contracts import (
    SwingCandidate,
    SwingExitDecision,
    SwingFeatureSnapshotRecord,
    SwingLifecycleTransition,
    SwingOrderPlan,
    SwingRiskPlan,
    SwingSignal,
    SwingUniverseMember,
)


class SwingBaselineReportPackageSummary(ImmutableModel):
    feature_snapshot_count: NonNegativeInt = 0
    universe_member_count: NonNegativeInt = 0
    candidate_count: NonNegativeInt = 0
    signal_count: NonNegativeInt = 0
    risk_plan_count: NonNegativeInt = 0
    order_plan_count: NonNegativeInt = 0
    lifecycle_transition_count: NonNegativeInt = 0
    exit_decision_count: NonNegativeInt = 0
    serious_full_run_allowed: bool


class SwingBaselineReportPackage(ImmutableModel):
    package_id: str
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    generated_at: datetime
    manifest: SwingBaselineManifest
    qualification_checklist: SwingBaselineQualificationChecklist
    feature_snapshots: tuple[SwingFeatureSnapshotRecord, ...] = Field(default_factory=tuple)
    universe_members: tuple[SwingUniverseMember, ...] = Field(default_factory=tuple)
    candidates: tuple[SwingCandidate, ...] = Field(default_factory=tuple)
    signals: tuple[SwingSignal, ...] = Field(default_factory=tuple)
    risk_plans: tuple[SwingRiskPlan, ...] = Field(default_factory=tuple)
    order_plans: tuple[SwingOrderPlan, ...] = Field(default_factory=tuple)
    lifecycle_transitions: tuple[SwingLifecycleTransition, ...] = Field(default_factory=tuple)
    exit_decisions: tuple[SwingExitDecision, ...] = Field(default_factory=tuple)
    summary: SwingBaselineReportPackageSummary

    @model_validator(mode="after")
    def _package_is_consistent(self) -> Self:
        if self.manifest.baseline_id != self.baseline_id:
            raise ValueError("report package baseline_id must match manifest baseline_id")
        if self.qualification_checklist.baseline_id != self.baseline_id:
            raise ValueError("report package baseline_id must match checklist baseline_id")
        if self.qualification_checklist.config_hash != self.manifest.config_hash:
            raise ValueError("checklist config_hash must match manifest config_hash")
        self._validate_artifact_metadata()
        self._validate_summary()
        return self

    def _validate_artifact_metadata(self) -> None:
        artifacts = (
            *self.feature_snapshots,
            *self.universe_members,
            *self.candidates,
            *self.signals,
            *self.risk_plans,
            *self.order_plans,
            *self.lifecycle_transitions,
            *self.exit_decisions,
        )
        for artifact in artifacts:
            if artifact.baseline_id != self.baseline_id:
                raise ValueError("artifact baseline_id must match report package baseline_id")
            config_hash = getattr(artifact, "config_hash", None)
            if config_hash is not None and config_hash != self.manifest.config_hash:
                raise ValueError("artifact config_hash must match manifest config_hash")

    def _validate_summary(self) -> None:
        expected = _summary_for_package(
            feature_snapshots=self.feature_snapshots,
            universe_members=self.universe_members,
            candidates=self.candidates,
            signals=self.signals,
            risk_plans=self.risk_plans,
            order_plans=self.order_plans,
            lifecycle_transitions=self.lifecycle_transitions,
            exit_decisions=self.exit_decisions,
            serious_full_run_allowed=self.manifest.serious_full_run_allowed,
        )
        if self.summary != expected:
            raise ValueError("report package summary must match contained artifacts")


def build_baseline_report_package(
    manifest: SwingBaselineManifest,
    *,
    qualification_checklist: SwingBaselineQualificationChecklist | None = None,
    generated_at: datetime | None = None,
    feature_snapshots: tuple[SwingFeatureSnapshotRecord, ...] = (),
    universe_members: tuple[SwingUniverseMember, ...] = (),
    candidates: tuple[SwingCandidate, ...] = (),
    signals: tuple[SwingSignal, ...] = (),
    risk_plans: tuple[SwingRiskPlan, ...] = (),
    order_plans: tuple[SwingOrderPlan, ...] = (),
    lifecycle_transitions: tuple[SwingLifecycleTransition, ...] = (),
    exit_decisions: tuple[SwingExitDecision, ...] = (),
) -> SwingBaselineReportPackage:
    package_generated_at = generated_at or datetime.now(UTC)
    checklist = qualification_checklist or build_baseline_qualification_checklist(
        manifest,
        generated_at=package_generated_at,
    )
    summary = _summary_for_package(
        feature_snapshots=feature_snapshots,
        universe_members=universe_members,
        candidates=candidates,
        signals=signals,
        risk_plans=risk_plans,
        order_plans=order_plans,
        lifecycle_transitions=lifecycle_transitions,
        exit_decisions=exit_decisions,
        serious_full_run_allowed=manifest.serious_full_run_allowed,
    )
    return SwingBaselineReportPackage(
        package_id=_package_id(manifest, package_generated_at),
        generated_at=package_generated_at,
        manifest=manifest,
        qualification_checklist=checklist,
        feature_snapshots=feature_snapshots,
        universe_members=universe_members,
        candidates=candidates,
        signals=signals,
        risk_plans=risk_plans,
        order_plans=order_plans,
        lifecycle_transitions=lifecycle_transitions,
        exit_decisions=exit_decisions,
        summary=summary,
    )


def build_baseline_report_package_from_profile_alias(
    profile_alias_path: str | Path,
    *,
    generated_at: datetime | None = None,
    satisfied_check_ids: tuple[str, ...] = (),
    blocked_check_ids: tuple[str, ...] = (),
) -> SwingBaselineReportPackage:
    package_generated_at = generated_at or datetime.now(UTC)
    manifest = build_swing_baseline_manifest_from_profile_alias(
        profile_alias_path,
        created_at=package_generated_at,
        satisfied_check_ids=satisfied_check_ids,
        blocked_check_ids=blocked_check_ids,
    )
    return build_baseline_report_package(
        manifest,
        generated_at=package_generated_at,
    )


def write_baseline_report_package_from_profile_alias(
    profile_alias_path: str | Path,
    output_path: str | Path,
    *,
    generated_at: datetime | None = None,
    satisfied_check_ids: tuple[str, ...] = (),
    blocked_check_ids: tuple[str, ...] = (),
) -> Path:
    package = build_baseline_report_package_from_profile_alias(
        profile_alias_path,
        generated_at=generated_at,
        satisfied_check_ids=satisfied_check_ids,
        blocked_check_ids=blocked_check_ids,
    )
    return write_baseline_report_package_json(package, output_path)


def write_baseline_report_package_json(
    package: SwingBaselineReportPackage,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(package.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output_path


def _summary_for_package(
    *,
    feature_snapshots: tuple[SwingFeatureSnapshotRecord, ...],
    universe_members: tuple[SwingUniverseMember, ...],
    candidates: tuple[SwingCandidate, ...],
    signals: tuple[SwingSignal, ...],
    risk_plans: tuple[SwingRiskPlan, ...],
    order_plans: tuple[SwingOrderPlan, ...],
    lifecycle_transitions: tuple[SwingLifecycleTransition, ...],
    exit_decisions: tuple[SwingExitDecision, ...],
    serious_full_run_allowed: bool,
) -> SwingBaselineReportPackageSummary:
    return SwingBaselineReportPackageSummary(
        feature_snapshot_count=len(feature_snapshots),
        universe_member_count=len(universe_members),
        candidate_count=len(candidates),
        signal_count=len(signals),
        risk_plan_count=len(risk_plans),
        order_plan_count=len(order_plans),
        lifecycle_transition_count=len(lifecycle_transitions),
        exit_decision_count=len(exit_decisions),
        serious_full_run_allowed=serious_full_run_allowed,
    )


def _package_id(manifest: SwingBaselineManifest, generated_at: datetime) -> str:
    generated = generated_at.isoformat().replace("+00:00", "Z")
    return f"baseline_report_package:{manifest.baseline_id}:{manifest.config_hash[:12]}:{generated}"


__all__ = [
    "SwingBaselineReportPackage",
    "SwingBaselineReportPackageSummary",
    "build_baseline_report_package",
    "build_baseline_report_package_from_profile_alias",
    "write_baseline_report_package_from_profile_alias",
    "write_baseline_report_package_json",
]
