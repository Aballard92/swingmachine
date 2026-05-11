from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from swingmachine.contracts import (
    MechanicalReadinessCheck,
    MechanicalReadinessDecision,
    MechanicalReadinessEvidence,
)
from swingmachine.data_contracts import validate_historical_panel_manifest
from swingmachine.enums import ReviewStatus

DEFAULT_REPORT_ROOT = Path("reports/swing_machine_v0_1")
DEFAULT_BASELINE_ID = "swing_machine_v0_1"


_REQUIRED_EVIDENCE_SPECS = (
    (
        "scanner_qualification",
        ("historical_broad_scanner_qualification_summary_*.json",),
        "scanner broad qualification status must be PASS",
    ),
    (
        "scanner_parity",
        ("historical_broad_scanner_parity_report_*.json",),
        "scanner research/runtime parity must pass with zero differences",
    ),
    (
        "lifecycle_qualification",
        ("historical_broad_lifecycle_qualification_summary_*.json",),
        "lifecycle broad qualification status must be PASS",
    ),
    (
        "lifecycle_parity",
        ("historical_broad_lifecycle_parity_report_*.json",),
        "lifecycle research/runtime parity must pass with zero differences",
    ),
    (
        "full_test_gate",
        ("pre_paper_test_gate_*/pre_paper_test_gate_summary.json",),
        "full pre-paper ruff/pytest gate must pass",
    ),
    (
        "dry_run_safety",
        ("first_paper_preflight_*.json", "selected_period_dry_run_safety_report.json"),
        "dry-run safety report must pass",
    ),
)

_FUTURE_MECHANICAL_EVIDENCE = (
    (
        "lookahead_audit",
        "lookahead audit must pass before mechanical readiness can be final",
        "SWING-V01-138",
    ),
    (
        "decision_ledger",
        "decision ledger must exist before mechanical readiness can be final",
        "SWING-V01-139",
    ),
    (
        "risk_portfolio_adversarial_tests",
        "risk/portfolio adversarial coverage must pass",
        "SWING-V01-140",
    ),
    (
        "exit_lifecycle_adversarial_tests",
        "exit lifecycle adversarial coverage must pass",
        "SWING-V01-141",
    ),
)


def build_mechanical_readiness_report(
    *,
    profile_alias_path: str | Path = Path("config/swing_machine_v0_1_profile.yaml"),
    manifest_path: str | Path = Path(
        "data/qualification_manifests/trading212/alpaca_historical_broad/"
        "historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml"
    ),
    report_root: str | Path = DEFAULT_REPORT_ROOT,
    output_run_id: str | None = None,
    scanner_summary_path: str | Path | None = None,
    scanner_parity_path: str | Path | None = None,
    lifecycle_summary_path: str | Path | None = None,
    lifecycle_parity_path: str | Path | None = None,
    pre_paper_gate_path: str | Path | None = None,
    dry_run_safety_path: str | Path | None = None,
    lookahead_audit_path: str | Path | None = None,
    decision_ledger_path: str | Path | None = None,
    risk_portfolio_evidence_path: str | Path | None = None,
    exit_lifecycle_evidence_path: str | Path | None = None,
) -> MechanicalReadinessDecision:
    generated_at = datetime.utcnow()
    run_id = output_run_id or generated_at.strftime("%Y%m%dT%H%M%SZ")
    profile_alias_path = Path(profile_alias_path)
    manifest_path = Path(manifest_path)
    report_root = Path(report_root)

    evidence: list[MechanicalReadinessEvidence] = []
    checks: list[MechanicalReadinessCheck] = []
    config_hash = None

    profile_evidence, profile_check, profile_config_hash = _profile_alias_evidence(
        profile_alias_path
    )
    evidence.append(profile_evidence)
    checks.append(profile_check)
    config_hash = profile_config_hash

    manifest_evidence, manifest_check = _manifest_evidence(manifest_path)
    evidence.append(manifest_evidence)
    checks.append(manifest_check)

    explicit_paths = {
        "scanner_qualification": scanner_summary_path,
        "scanner_parity": scanner_parity_path,
        "lifecycle_qualification": lifecycle_summary_path,
        "lifecycle_parity": lifecycle_parity_path,
        "full_test_gate": pre_paper_gate_path,
        "dry_run_safety": dry_run_safety_path,
    }
    for evidence_type, patterns, message in _REQUIRED_EVIDENCE_SPECS:
        evidence_path = _explicit_or_latest_path(
            explicit_paths[evidence_type],
            report_root=report_root,
            patterns=patterns,
        )
        item, check = _json_artifact_evidence(evidence_type, evidence_path, message)
        evidence.append(item)
        checks.append(check)

    future_paths = {
        "lookahead_audit": lookahead_audit_path
        or _explicit_or_latest_path(
            None,
            report_root=report_root,
            patterns=("lookahead_audit_*.json", "lookahead_audit.json"),
        ),
        "decision_ledger": decision_ledger_path
        or _explicit_or_latest_path(
            None,
            report_root=report_root,
            patterns=("decision_ledger_*.json", "decision_ledger.json"),
        ),
        "risk_portfolio_adversarial_tests": risk_portfolio_evidence_path
        or _explicit_or_latest_path(
            None,
            report_root=report_root,
            patterns=(
                "risk_portfolio_adversarial_tests_*.json",
                "risk_portfolio_adversarial_tests.json",
            ),
        ),
        "exit_lifecycle_adversarial_tests": exit_lifecycle_evidence_path
        or _explicit_or_latest_path(
            None,
            report_root=report_root,
            patterns=(
                "exit_lifecycle_adversarial_tests_*.json",
                "exit_lifecycle_adversarial_tests.json",
            ),
        ),
    }
    for evidence_type, message, action_id in _FUTURE_MECHANICAL_EVIDENCE:
        item, check = _future_evidence(
            evidence_type,
            future_paths[evidence_type],
            message=message,
            action_id=action_id,
        )
        evidence.append(item)
        checks.append(check)

    blockers = tuple(
        check.check_id
        for check in checks
        if check.status is ReviewStatus.FAIL and check.severity == "BLOCKER"
    )
    warnings = tuple(
        check.check_id
        for check in checks
        if check.status is ReviewStatus.WARN or check.severity == "WARNING"
    )
    decision = "BLOCK" if blockers else "WARN" if warnings else "PASS"
    status = (
        ReviewStatus.FAIL
        if decision == "BLOCK"
        else ReviewStatus.WARN
        if decision == "WARN"
        else ReviewStatus.PASS
    )
    next_required_actions = _next_required_actions(checks)
    return MechanicalReadinessDecision(
        baseline_id=DEFAULT_BASELINE_ID,
        run_id=run_id,
        generated_at=generated_at,
        status=status,
        decision=decision,
        profile_alias_path=str(profile_alias_path),
        manifest_path=str(manifest_path),
        config_hash=config_hash,
        evidence=tuple(evidence),
        checks=tuple(checks),
        blockers=blockers,
        warnings=warnings,
        next_required_actions=next_required_actions,
    )


def write_mechanical_readiness_report_json(
    report: MechanicalReadinessDecision,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output_path


def write_mechanical_readiness_report_markdown(
    report: MechanicalReadinessDecision,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_mechanical_readiness_markdown(report), encoding="utf-8")
    return output_path


def render_mechanical_readiness_markdown(report: MechanicalReadinessDecision) -> str:
    lines = [
        "# Swing Machine v0.1 mechanical readiness report",
        "",
        f"Run ID: `{report.run_id}`",
        f"Generated at: `{report.generated_at.isoformat()}Z`",
        f"Decision: `{report.decision}`",
        f"Status: `{report.status.value}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{blocker}`" for blocker in report.blockers] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{warning}`" for warning in report.warnings] or ["- None"])
    lines.extend(["", "## Checks", ""])
    for check in report.checks:
        lines.append(
            f"- `{check.check_id}`: `{check.status.value}` "
            f"({check.severity}) - {check.message}"
        )
    lines.extend(["", "## Next required actions", ""])
    lines.extend(
        [f"- `{action}`" for action in report.next_required_actions]
        or ["- None"]
    )
    lines.append("")
    return "\n".join(lines)


def _profile_alias_evidence(
    profile_alias_path: Path,
) -> tuple[MechanicalReadinessEvidence, MechanicalReadinessCheck, str | None]:
    if not profile_alias_path.exists():
        return (
            _missing_evidence("profile_alias", profile_alias_path),
            _check(
                "profile_alias_present",
                "config",
                ReviewStatus.FAIL,
                observed="missing",
                expected="present",
                severity="BLOCKER",
                message="profile alias file must exist",
            ),
            None,
        )
    payload = yaml.safe_load(profile_alias_path.read_text(encoding="utf-8")) or {}
    expected_baseline = payload.get("baseline_id")
    status = ReviewStatus.PASS if expected_baseline == DEFAULT_BASELINE_ID else ReviewStatus.FAIL
    return (
        MechanicalReadinessEvidence(
            evidence_id="profile_alias",
            evidence_type="profile_alias",
            path=str(profile_alias_path),
            status=status,
            run_id=None,
            summary=payload,
        ),
        _check(
            "profile_alias_baseline_id",
            "config",
            status,
            observed=expected_baseline,
            expected=DEFAULT_BASELINE_ID,
            severity="BLOCKER",
            message="profile alias must target swing_machine_v0_1",
        ),
        payload.get("config_hash"),
    )


def _manifest_evidence(
    manifest_path: Path,
) -> tuple[MechanicalReadinessEvidence, MechanicalReadinessCheck]:
    if not manifest_path.exists():
        return (
            _missing_evidence("historical_manifest", manifest_path),
            _check(
                "historical_manifest_present",
                "data",
                ReviewStatus.FAIL,
                observed="missing",
                expected="present",
                severity="BLOCKER",
                message="historical panel manifest must exist",
            ),
        )
    validation = validate_historical_panel_manifest(manifest_path)
    summary = validation.model_dump(mode="json")
    return (
        MechanicalReadinessEvidence(
            evidence_id="historical_manifest",
            evidence_type="historical_manifest",
            path=str(manifest_path),
            status=validation.status,
            run_id=None,
            summary=summary,
        ),
        _check(
            "historical_manifest_validation",
            "data",
            validation.status,
            observed=validation.status.value,
            expected=ReviewStatus.PASS.value,
            severity="BLOCKER",
            message="historical panel manifest validation must pass",
        ),
    )


def _json_artifact_evidence(
    evidence_type: str,
    path: Path | None,
    message: str,
) -> tuple[MechanicalReadinessEvidence, MechanicalReadinessCheck]:
    if path is None or not path.exists():
        return (
            _missing_evidence(evidence_type, path),
            _check(
                f"{evidence_type}_present",
                "qualification",
                ReviewStatus.FAIL,
                observed="missing",
                expected="present",
                severity="BLOCKER",
                message=message,
            ),
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    status = _artifact_status(evidence_type, payload)
    return (
        MechanicalReadinessEvidence(
            evidence_id=evidence_type,
            evidence_type=evidence_type,
            path=str(path),
            status=status,
            run_id=str(payload.get("run_id")) if payload.get("run_id") else None,
            summary=payload,
        ),
        _check(
            f"{evidence_type}_clean",
            "qualification",
            status,
            observed=_artifact_observed_value(evidence_type, payload),
            expected="PASS_OR_ZERO_DIFFERENCES",
            severity="BLOCKER",
            message=message,
        ),
    )


def _future_evidence(
    evidence_type: str,
    path: str | Path | None,
    *,
    message: str,
    action_id: str,
) -> tuple[MechanicalReadinessEvidence, MechanicalReadinessCheck]:
    evidence_path = None if path is None else Path(path)
    if evidence_path is None or not evidence_path.exists():
        return (
            _missing_evidence(evidence_type, evidence_path),
            _check(
                f"{evidence_type}_complete",
                "mechanical_readiness",
                ReviewStatus.FAIL,
                observed="not_implemented",
                expected="PASS",
                severity="BLOCKER",
                message=message,
            ),
        )
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    status = _artifact_status(evidence_type, payload)
    check_message = message if status is ReviewStatus.PASS else f"{message}; implement {action_id}"
    return (
        MechanicalReadinessEvidence(
            evidence_id=evidence_type,
            evidence_type=evidence_type,
            path=str(evidence_path),
            status=status,
            run_id=str(payload.get("run_id")) if payload.get("run_id") else None,
            summary=payload,
        ),
        _check(
            f"{evidence_type}_complete",
            "mechanical_readiness",
            status,
            observed=_artifact_observed_value(evidence_type, payload),
            expected="PASS",
            severity="BLOCKER",
            message=check_message,
        ),
    )


def _artifact_status(evidence_type: str, payload: dict[str, Any]) -> ReviewStatus:
    if evidence_type.endswith("parity"):
        return (
            ReviewStatus.PASS
            if payload.get("passed") is True and int(payload.get("difference_count", 1)) == 0
            else ReviewStatus.FAIL
        )
    if payload.get("passed") is True:
        return ReviewStatus.PASS
    status = payload.get("status") or payload.get("decision")
    if status in {"PASS", ReviewStatus.PASS.value}:
        return ReviewStatus.PASS
    if status in {"WARN", "WARN_OR_FAIL", ReviewStatus.WARN.value}:
        return ReviewStatus.WARN
    return ReviewStatus.FAIL


def _artifact_observed_value(evidence_type: str, payload: dict[str, Any]) -> Any:
    if evidence_type.endswith("parity"):
        return {
            "passed": payload.get("passed"),
            "difference_count": payload.get("difference_count"),
        }
    if "passed" in payload:
        return payload.get("passed")
    return payload.get("status") or payload.get("decision")


def _explicit_or_latest_path(
    explicit_path: str | Path | None,
    *,
    report_root: Path,
    patterns: tuple[str, ...],
) -> Path | None:
    if explicit_path is not None:
        return Path(explicit_path)
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(report_root.glob(pattern))
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: str(path))[-1]


def _missing_evidence(
    evidence_type: str,
    path: Path | None,
) -> MechanicalReadinessEvidence:
    return MechanicalReadinessEvidence(
        evidence_id=evidence_type,
        evidence_type=evidence_type,
        path="" if path is None else str(path),
        status=ReviewStatus.FAIL,
        run_id=None,
        summary={"missing": True},
    )


def _check(
    check_id: str,
    category: str,
    status: ReviewStatus,
    *,
    observed: Any,
    expected: Any,
    severity: str,
    message: str,
) -> MechanicalReadinessCheck:
    return MechanicalReadinessCheck(
        check_id=check_id,
        category=category,
        status=status,
        observed=observed,
        expected=expected,
        severity=severity,  # type: ignore[arg-type]
        message=message,
    )


def _next_required_actions(
    checks: list[MechanicalReadinessCheck],
) -> tuple[str, ...]:
    actions = []
    for check in checks:
        if check.status is ReviewStatus.PASS:
            continue
        if check.check_id.startswith("lookahead_audit"):
            actions.append(
                "SWING-V01-151"
                if check.status is ReviewStatus.WARN
                else "SWING-V01-138"
            )
        elif check.check_id.startswith("decision_ledger"):
            actions.append(
                "SWING-V01-152"
                if check.status is ReviewStatus.WARN
                else "SWING-V01-139"
            )
        elif check.check_id.startswith("risk_portfolio"):
            actions.append("SWING-V01-140")
        elif check.check_id.startswith("exit_lifecycle"):
            actions.append("SWING-V01-141")
        else:
            actions.append(check.check_id)
    return tuple(dict.fromkeys(actions))
