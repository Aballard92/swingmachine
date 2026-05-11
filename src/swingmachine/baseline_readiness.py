from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field

from swingmachine.baseline import (
    BASELINE_ID,
    SwingBaselineManifest,
    SwingSelectedQualificationPlan,
    load_swing_selected_qualification_plan,
    resolve_profile_alias_strategy_config_path,
    resolve_selected_qualification_profile_alias_path,
)
from swingmachine.baseline_parity import SwingBaselineParityReport
from swingmachine.modeling import ImmutableModel, NonNegativeInt

FreezeReadinessBlockerCode = Literal[
    "manifest_checks_incomplete",
    "selected_period_plan_missing",
    "selected_period_plan_mismatch",
    "parity_evidence_missing",
    "parity_evidence_failed",
    "operator_approval_missing",
]

SelectedQualificationPreflightBlockerCode = Literal[
    "profile_alias_missing",
    "strategy_config_missing",
    "required_artifacts_incomplete",
    "data_manifest_missing",
]


class SwingBaselineFreezeReadinessBlocker(ImmutableModel):
    code: FreezeReadinessBlockerCode
    message: str
    evidence: tuple[str, ...] = Field(default_factory=tuple)


class SwingBaselineFreezeReadinessDecision(ImmutableModel):
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    evaluated_at: datetime
    config_hash: str
    decision: Literal["ALLOW", "BLOCK"]
    serious_full_run_allowed: bool
    blocker_count: NonNegativeInt
    blockers: tuple[SwingBaselineFreezeReadinessBlocker, ...] = Field(default_factory=tuple)
    evidence: tuple[str, ...] = Field(default_factory=tuple)


class SwingSelectedQualificationPreflightBlocker(ImmutableModel):
    code: SelectedQualificationPreflightBlockerCode
    message: str
    evidence: tuple[str, ...] = Field(default_factory=tuple)


class SwingSelectedQualificationPreflightResult(ImmutableModel):
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    plan_version: str
    plan_path: str
    passed: bool
    blocker_count: NonNegativeInt
    blockers: tuple[SwingSelectedQualificationPreflightBlocker, ...] = Field(
        default_factory=tuple
    )
    period_ids: tuple[str, ...]
    required_artifacts: tuple[str, ...]
    evidence: tuple[str, ...] = Field(default_factory=tuple)


def evaluate_serious_full_run_freeze_readiness(
    manifest: SwingBaselineManifest,
    *,
    selected_period_plan: SwingSelectedQualificationPlan | None = None,
    parity_reports: tuple[SwingBaselineParityReport, ...] = (),
    operator_approved: bool = False,
    evaluated_at: datetime | None = None,
) -> SwingBaselineFreezeReadinessDecision:
    blockers: list[SwingBaselineFreezeReadinessBlocker] = []
    blockers.extend(_manifest_blockers(manifest))
    blockers.extend(_selected_period_plan_blockers(manifest, selected_period_plan))
    blockers.extend(_parity_report_blockers(parity_reports))
    if not operator_approved:
        blockers.append(
            SwingBaselineFreezeReadinessBlocker(
                code="operator_approval_missing",
                message="Operator freeze approval has not been recorded.",
            )
        )
    serious_full_run_allowed = not blockers
    return SwingBaselineFreezeReadinessDecision(
        evaluated_at=evaluated_at or datetime.now(UTC),
        config_hash=manifest.config_hash,
        decision="ALLOW" if serious_full_run_allowed else "BLOCK",
        serious_full_run_allowed=serious_full_run_allowed,
        blocker_count=len(blockers),
        blockers=tuple(blockers),
        evidence=_freeze_evidence(manifest, selected_period_plan, parity_reports),
    )


def preflight_selected_qualification_plan(
    plan_path: str | Path,
    *,
    data_manifest_by_period: Mapping[str, str | Path] | None = None,
    required_artifacts: tuple[str, ...] = (
        "baseline_report_package.json",
        "baseline_parity_report.json",
        "freeze_readiness.json",
    ),
) -> SwingSelectedQualificationPreflightResult:
    plan_file = Path(plan_path)
    plan = load_swing_selected_qualification_plan(plan_file)
    blockers: list[SwingSelectedQualificationPreflightBlocker] = []
    profile_alias_path = resolve_selected_qualification_profile_alias_path(plan_file)
    if not profile_alias_path.exists():
        blockers.append(
            SwingSelectedQualificationPreflightBlocker(
                code="profile_alias_missing",
                message="Selected-period profile alias path does not exist.",
                evidence=(str(profile_alias_path),),
            )
        )
    else:
        strategy_config_path = resolve_profile_alias_strategy_config_path(profile_alias_path)
        if not strategy_config_path.exists():
            blockers.append(
                SwingSelectedQualificationPreflightBlocker(
                    code="strategy_config_missing",
                    message="Selected-period strategy config path does not exist.",
                    evidence=(str(strategy_config_path),),
                )
            )
    missing_artifacts = tuple(
        artifact for artifact in required_artifacts if artifact not in plan.required_artifacts
    )
    if missing_artifacts:
        blockers.append(
            SwingSelectedQualificationPreflightBlocker(
                code="required_artifacts_incomplete",
                message="Selected-period plan does not declare every required artifact.",
                evidence=missing_artifacts,
            )
        )
    data_manifest_by_period = data_manifest_by_period or {}
    missing_period_manifests: list[str] = []
    for period in plan.periods:
        manifest_path = data_manifest_by_period.get(period.period_id)
        if manifest_path is None:
            missing_period_manifests.append(f"{period.period_id}:not_provided")
            continue
        if not Path(manifest_path).exists():
            missing_period_manifests.append(f"{period.period_id}:{manifest_path}")
    if missing_period_manifests:
        blockers.append(
            SwingSelectedQualificationPreflightBlocker(
                code="data_manifest_missing",
                message="Selected-period data manifests are missing or not provided.",
                evidence=tuple(missing_period_manifests),
            )
        )
    return SwingSelectedQualificationPreflightResult(
        plan_version=plan.plan_version,
        plan_path=plan_file.as_posix(),
        passed=not blockers,
        blocker_count=len(blockers),
        blockers=tuple(blockers),
        period_ids=tuple(period.period_id for period in plan.periods),
        required_artifacts=plan.required_artifacts,
        evidence=(
            f"profile_alias_path:{profile_alias_path}",
            f"run_policy:{plan.run_policy}",
            f"serious_full_run_policy:{plan.serious_full_run_policy}",
        ),
    )


def write_selected_qualification_preflight_json(
    result: SwingSelectedQualificationPreflightResult,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output_path


def write_freeze_readiness_decision_json(
    decision: SwingBaselineFreezeReadinessDecision,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(decision.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output_path


def _manifest_blockers(
    manifest: SwingBaselineManifest,
) -> tuple[SwingBaselineFreezeReadinessBlocker, ...]:
    outstanding = tuple(
        check.check_id for check in manifest.qualification_checks if check.status != "satisfied"
    )
    if not outstanding and manifest.serious_full_run_allowed:
        return ()
    return (
        SwingBaselineFreezeReadinessBlocker(
            code="manifest_checks_incomplete",
            message="The baseline manifest does not satisfy every required qualification check.",
            evidence=outstanding,
        ),
    )


def _selected_period_plan_blockers(
    manifest: SwingBaselineManifest,
    selected_period_plan: SwingSelectedQualificationPlan | None,
) -> tuple[SwingBaselineFreezeReadinessBlocker, ...]:
    if selected_period_plan is None:
        return (
            SwingBaselineFreezeReadinessBlocker(
                code="selected_period_plan_missing",
                message="No selected-period qualification plan was provided.",
            ),
        )
    evidence: list[str] = []
    if selected_period_plan.baseline_id != manifest.baseline_id:
        evidence.append(f"baseline_id:{selected_period_plan.baseline_id}")
    if selected_period_plan.required_data_contract_version != manifest.data_contract_version:
        evidence.append(
            "required_data_contract_version:"
            f"{selected_period_plan.required_data_contract_version}"
        )
    if selected_period_plan.run_policy != "DRY_RUN_REPLAY_ONLY":
        evidence.append(f"run_policy:{selected_period_plan.run_policy}")
    if selected_period_plan.serious_full_run_policy != "PROHIBITED_UNTIL_QUALIFIED":
        evidence.append(f"serious_full_run_policy:{selected_period_plan.serious_full_run_policy}")
    if not evidence:
        return ()
    return (
        SwingBaselineFreezeReadinessBlocker(
            code="selected_period_plan_mismatch",
            message="Selected-period qualification plan does not match the manifest or policy.",
            evidence=tuple(evidence),
        ),
    )


def _parity_report_blockers(
    parity_reports: tuple[SwingBaselineParityReport, ...],
) -> tuple[SwingBaselineFreezeReadinessBlocker, ...]:
    if not parity_reports:
        return (
            SwingBaselineFreezeReadinessBlocker(
                code="parity_evidence_missing",
                message="No research/runtime parity evidence was provided.",
            ),
        )
    failed = tuple(report.comparison_id for report in parity_reports if not report.passed)
    if not failed:
        return ()
    return (
        SwingBaselineFreezeReadinessBlocker(
            code="parity_evidence_failed",
            message="One or more research/runtime parity reports failed.",
            evidence=failed,
        ),
    )


def _freeze_evidence(
    manifest: SwingBaselineManifest,
    selected_period_plan: SwingSelectedQualificationPlan | None,
    parity_reports: tuple[SwingBaselineParityReport, ...],
) -> tuple[str, ...]:
    evidence = [
        f"manifest_config_hash:{manifest.config_hash}",
        f"manifest_serious_full_run_allowed:{manifest.serious_full_run_allowed}",
    ]
    if selected_period_plan is not None:
        evidence.append(f"selected_period_count:{len(selected_period_plan.periods)}")
    evidence.append(f"parity_report_count:{len(parity_reports)}")
    return tuple(evidence)


__all__ = [
    "FreezeReadinessBlockerCode",
    "SelectedQualificationPreflightBlockerCode",
    "SwingBaselineFreezeReadinessBlocker",
    "SwingBaselineFreezeReadinessDecision",
    "SwingSelectedQualificationPreflightBlocker",
    "SwingSelectedQualificationPreflightResult",
    "evaluate_serious_full_run_freeze_readiness",
    "preflight_selected_qualification_plan",
    "write_freeze_readiness_decision_json",
    "write_selected_qualification_preflight_json",
]
