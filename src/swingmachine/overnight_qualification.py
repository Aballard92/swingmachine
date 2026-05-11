"""Overnight-safe qualification helpers for the swing v0.1 baseline.

These helpers consolidate already-generated evidence and run guarded checks that do
not execute broker, paper, live, or full qualification paths.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml
from pydantic import Field

from swingmachine.baseline import (
    BASELINE_ID,
    build_baseline_qualification_checklist,
    build_swing_baseline_manifest_from_profile_alias,
    load_swing_selected_qualification_plan,
)
from swingmachine.baseline_readiness import (
    evaluate_serious_full_run_freeze_readiness,
    write_freeze_readiness_decision_json,
)
from swingmachine.data_contracts import (
    validate_corporate_actions_data,
    validate_earnings_events_data,
    validate_historical_ohlcv_data,
    validate_symbol_reference_data,
)
from swingmachine.modeling import ImmutableModel, NonNegativeInt

PRIMARY_DATA_SOURCE = "trading212_alpaca"
DECLARED_QUALIFICATION_PANEL = (
    "SPY",
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "GOOGL",
    "TSLA",
    "AMD",
    "NFLX",
    "AVGO",
    "QCOM",
    "INTC",
    "JPM",
    "XOM",
    "QQQ",
)
EXCLUDED_SYMBOLS = ("ORCL", "CRM", "BAC", "CVX")


class OvernightEvidenceArtifact(ImmutableModel):
    artifact_id: str
    path: str
    exists: bool
    passed: bool | None = None
    summary: tuple[str, ...] = Field(default_factory=tuple)


class OvernightQualificationEvidenceSummary(ImmutableModel):
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    generated_at: datetime
    primary_data_source: str
    declared_panel_symbols: tuple[str, ...]
    excluded_symbols: tuple[str, ...]
    artifacts: tuple[OvernightEvidenceArtifact, ...]
    primary_source_coverage_passed: bool
    data_input_gate_passed: bool
    selected_period_preflight_passed: bool
    selected_period_smoke_passed: bool
    dry_run_safety_passed: bool
    provider_drift_passed: bool
    serious_full_run_allowed: Literal[False] = False
    blockers: tuple[str, ...]


class DraftBaselineManifestBundle(ImmutableModel):
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    generated_at: datetime
    manifest_path: str
    checklist_path: str
    freeze_readiness_path: str
    serious_full_run_allowed: bool
    freeze_decision: str
    blockers: tuple[str, ...]


class SelectedPeriodSmokePeriodResult(ImmutableModel):
    period_id: str
    passed: bool
    ohlcv_rows: NonNegativeInt
    symbol_count: NonNegativeInt
    total_session_count: NonNegativeInt
    qualification_session_count: NonNegativeInt
    minimum_session_count: NonNegativeInt
    maximum_symbol_count: NonNegativeInt
    blockers: tuple[str, ...] = Field(default_factory=tuple)


class SelectedPeriodDataSmokeReport(ImmutableModel):
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    generated_at: datetime
    input_plan_path: str
    selected_period_plan_path: str
    execution_mode: Literal["DRY_RUN_REPLAY_ONLY"] = "DRY_RUN_REPLAY_ONLY"
    broker_execution_allowed: Literal[False] = False
    passed: bool
    periods: tuple[SelectedPeriodSmokePeriodResult, ...]
    blockers: tuple[str, ...]


class DryRunSafetyReport(ImmutableModel):
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    generated_at: datetime
    selected_period_plan_path: str
    profile_alias_path: str
    execution_mode: Literal["DRY_RUN_REPLAY_ONLY"]
    serious_full_run_policy: Literal["PROHIBITED_UNTIL_QUALIFIED"]
    broker_execution_allowed: Literal[False] = False
    live_order_actions_allowed: Literal[False] = False
    paper_order_actions_allowed: Literal[False] = False
    serious_full_run_allowed: bool
    freeze_decision: str
    passed: bool
    blockers: tuple[str, ...]
    evidence: tuple[str, ...]


def build_overnight_qualification_evidence_summary(
    report_root: str | Path = "reports/swing_machine_v0_1",
) -> OvernightQualificationEvidenceSummary:
    root = Path(report_root)
    artifact_specs = (
        ("alpaca_source_inspection", root / "trading212_alpaca_source_inspection.json"),
        ("hf_source_inspection", root / "trading212_huggingface_source_inspection.json"),
        ("alpaca_source_coverage", root / "trading212_alpaca_source_coverage.json"),
        ("hf_source_coverage", root / "trading212_huggingface_source_coverage.json"),
        ("alpaca_export", root / "trading212_alpaca_selected_period_export.json"),
        ("hf_export", root / "trading212_huggingface_selected_period_export.json"),
        ("provider_panel_drift", root / "trading212_provider_panel_drift_report.json"),
        ("alpaca_data_input_preflight", root / "trading212_alpaca_data_input_preflight.json"),
        ("hf_data_input_preflight", root / "trading212_huggingface_data_input_preflight.json"),
        (
            "alpaca_selected_period_preflight",
            root / "trading212_alpaca_selected_period_preflight.json",
        ),
        ("selected_period_data_smoke", root / "selected_period_data_smoke_report.json"),
        (
            "selected_period_dry_run_safety",
            root / "selected_period_dry_run_safety_report.json",
        ),
    )
    artifacts = tuple(_artifact_summary(artifact_id, path) for artifact_id, path in artifact_specs)
    primary_source_coverage_passed = _artifact_passed(
        root / "trading212_alpaca_source_coverage.json"
    )
    data_input_gate_passed = _artifact_passed(
        root / "trading212_alpaca_data_input_preflight.json"
    )
    selected_period_preflight_passed = _artifact_passed(
        root / "trading212_alpaca_selected_period_preflight.json"
    )
    selected_period_smoke_passed = _artifact_passed(
        root / "selected_period_data_smoke_report.json"
    )
    dry_run_safety_passed = _artifact_passed(
        root / "selected_period_dry_run_safety_report.json"
    )
    provider_drift_passed = _artifact_passed(root / "trading212_provider_panel_drift_report.json")
    blockers = []
    if not primary_source_coverage_passed:
        blockers.append("alpaca_source_coverage_missing_selected_period_windows")
    if not data_input_gate_passed:
        blockers.append("alpaca_data_input_gate_not_passed")
    if not selected_period_preflight_passed:
        blockers.append("alpaca_selected_period_preflight_not_passed")
    if not selected_period_smoke_passed:
        blockers.append("selected_period_data_smoke_not_passed")
    if not dry_run_safety_passed:
        blockers.append("selected_period_dry_run_safety_not_passed")
    if not provider_drift_passed:
        blockers.append("provider_panel_drift_not_resolved_hf_comparison_only")
    blockers.append("serious_full_run_still_requires_parity_smoke_dry_run_freeze_review")
    return OvernightQualificationEvidenceSummary(
        generated_at=datetime.now(UTC),
        primary_data_source=PRIMARY_DATA_SOURCE,
        declared_panel_symbols=DECLARED_QUALIFICATION_PANEL,
        excluded_symbols=EXCLUDED_SYMBOLS,
        artifacts=artifacts,
        primary_source_coverage_passed=primary_source_coverage_passed,
        data_input_gate_passed=data_input_gate_passed,
        selected_period_preflight_passed=selected_period_preflight_passed,
        selected_period_smoke_passed=selected_period_smoke_passed,
        dry_run_safety_passed=dry_run_safety_passed,
        provider_drift_passed=provider_drift_passed,
        blockers=tuple(blockers),
    )


def write_draft_baseline_manifest_bundle(
    output_root: str | Path = "reports/swing_machine_v0_1",
    *,
    profile_alias_path: str | Path = "config/swing_machine_v0_1_profile.yaml",
    selected_period_plan_path: str | Path = "config/swing_machine_v0_1_selected_periods.yaml",
) -> DraftBaselineManifestBundle:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    manifest = build_swing_baseline_manifest_from_profile_alias(
        profile_alias_path,
        satisfied_check_ids=(
            "explicit_baseline_profile",
            "data_contract",
            "typed_candidate_signal_contracts",
            "risk_order_lifecycle_contracts",
            "reporting_package",
        ),
        blocked_check_ids=(
            "research_runtime_parity",
            "selected_period_replay",
            "operator_review_pass",
            "freeze_review",
        ),
    )
    checklist = build_baseline_qualification_checklist(manifest)
    selected_period_plan = load_swing_selected_qualification_plan(selected_period_plan_path)
    freeze_readiness = evaluate_serious_full_run_freeze_readiness(
        manifest,
        selected_period_plan=selected_period_plan,
        parity_reports=(),
        operator_approved=False,
    )
    manifest_path = root / "draft_baseline_manifest.json"
    checklist_path = root / "draft_qualification_checklist.json"
    freeze_path = root / "draft_freeze_readiness.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")
    checklist_path.write_text(checklist.model_dump_json(indent=2) + "\n", encoding="utf-8")
    write_freeze_readiness_decision_json(freeze_readiness, freeze_path)
    return DraftBaselineManifestBundle(
        generated_at=datetime.now(UTC),
        manifest_path=manifest_path.as_posix(),
        checklist_path=checklist_path.as_posix(),
        freeze_readiness_path=freeze_path.as_posix(),
        serious_full_run_allowed=freeze_readiness.serious_full_run_allowed,
        freeze_decision=freeze_readiness.decision,
        blockers=tuple(blocker.code for blocker in freeze_readiness.blockers),
    )


def run_selected_period_data_smoke(
    input_plan_path: str | Path = (
        "reports/swing_machine_v0_1/trading212_alpaca_data_input_plan.json"
    ),
) -> SelectedPeriodDataSmokeReport:
    input_path = Path(input_plan_path)
    input_plan = _load_mapping(input_path)
    selected_period_plan_path = Path(str(input_plan["selected_period_plan_path"]))
    selected_period_plan = load_swing_selected_qualification_plan(selected_period_plan_path)
    period_requirements = {period.period_id: period for period in selected_period_plan.periods}
    results: list[SelectedPeriodSmokePeriodResult] = []
    blockers: list[str] = []
    for period in input_plan.get("periods", []):
        result = _smoke_period(period, period_requirements[str(period["period_id"])])
        results.append(result)
        blockers.extend(result.blockers)
    return SelectedPeriodDataSmokeReport(
        generated_at=datetime.now(UTC),
        input_plan_path=input_path.as_posix(),
        selected_period_plan_path=selected_period_plan_path.as_posix(),
        passed=not blockers,
        periods=tuple(results),
        blockers=tuple(blockers),
    )


def check_selected_period_dry_run_safety(
    selected_period_plan_path: str | Path = "config/swing_machine_v0_1_selected_periods.yaml",
    *,
    profile_alias_path: str | Path = "config/swing_machine_v0_1_profile.yaml",
) -> DryRunSafetyReport:
    selected_period_plan = load_swing_selected_qualification_plan(selected_period_plan_path)
    manifest = build_swing_baseline_manifest_from_profile_alias(profile_alias_path)
    freeze_readiness = evaluate_serious_full_run_freeze_readiness(
        manifest,
        selected_period_plan=selected_period_plan,
        parity_reports=(),
        operator_approved=False,
    )
    blockers = []
    if selected_period_plan.run_policy != "DRY_RUN_REPLAY_ONLY":
        blockers.append(f"run_policy_not_dry_run:{selected_period_plan.run_policy}")
    if selected_period_plan.serious_full_run_policy != "PROHIBITED_UNTIL_QUALIFIED":
        blockers.append(
            f"serious_full_run_policy_not_prohibited:{selected_period_plan.serious_full_run_policy}"
        )
    if manifest.hidden_environment_strategy_behavior_allowed:
        blockers.append("hidden_environment_strategy_behavior_allowed")
    if freeze_readiness.serious_full_run_allowed:
        blockers.append("freeze_readiness_unexpectedly_allows_serious_full_run")
    return DryRunSafetyReport(
        generated_at=datetime.now(UTC),
        selected_period_plan_path=Path(selected_period_plan_path).as_posix(),
        profile_alias_path=Path(profile_alias_path).as_posix(),
        execution_mode=selected_period_plan.run_policy,
        serious_full_run_policy=selected_period_plan.serious_full_run_policy,
        serious_full_run_allowed=freeze_readiness.serious_full_run_allowed,
        freeze_decision=freeze_readiness.decision,
        passed=not blockers,
        blockers=tuple(blockers),
        evidence=(
            "broker_execution_allowed:false",
            "live_order_actions_allowed:false",
            "paper_order_actions_allowed:false",
            f"freeze_blockers:{','.join(blocker.code for blocker in freeze_readiness.blockers)}",
        ),
    )


def write_json_report(report: Any, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(report, "model_dump_json"):
        payload = report.model_dump_json(indent=2)
    else:
        payload = json.dumps(report, indent=2, sort_keys=True)
    path.write_text(payload + "\n", encoding="utf-8")
    return path


def _artifact_summary(artifact_id: str, path: Path) -> OvernightEvidenceArtifact:
    if not path.exists():
        return OvernightEvidenceArtifact(
            artifact_id=artifact_id,
            path=path.as_posix(),
            exists=False,
        )
    payload = _load_mapping(path)
    summary = _summary_lines(payload)
    return OvernightEvidenceArtifact(
        artifact_id=artifact_id,
        path=path.as_posix(),
        exists=True,
        passed=_extract_passed(payload),
        summary=summary,
    )


def _artifact_passed(path: Path) -> bool:
    if not path.exists():
        return False
    return _extract_passed(_load_mapping(path)) is True


def _load_mapping(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if raw.lstrip().startswith("{"):
        payload = json.loads(raw)
    else:
        payload = yaml.safe_load(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {path}")
    return payload


def _extract_passed(payload: dict[str, Any]) -> bool | None:
    passed = payload.get("passed")
    if isinstance(passed, bool):
        return passed
    decision = payload.get("decision")
    if decision == "ALLOW":
        return True
    if decision == "BLOCK":
        return False
    return None


def _summary_lines(payload: dict[str, Any]) -> tuple[str, ...]:
    lines: list[str] = []
    for key in (
        "provider",
        "passed",
        "checked_rows",
        "covered_rows",
        "missing_rows",
        "blocker_count",
        "decision",
    ):
        if key in payload:
            lines.append(f"{key}:{payload[key]}")
    if "periods" in payload and isinstance(payload["periods"], list):
        lines.append(f"period_count:{len(payload['periods'])}")
    blockers = payload.get("blockers")
    if isinstance(blockers, list):
        lines.append(f"blockers:{len(blockers)}")
    return tuple(lines)


def _smoke_period(
    period_payload: dict[str, Any],
    requirement: Any,
) -> SelectedPeriodSmokePeriodResult:
    period_id = str(period_payload["period_id"])
    blockers: list[str] = []
    ohlcv = _read_panel_frame(Path(period_payload["ohlcv_path"]))
    symbols = _read_panel_frame(Path(period_payload["symbol_reference_path"]))
    corporate_actions = _read_panel_frame(Path(period_payload["corporate_actions_path"]))
    earnings_events = _read_panel_frame(Path(period_payload["earnings_events_path"]))
    _validate_or_block(blockers, period_id, "ohlcv", validate_historical_ohlcv_data, ohlcv)
    _validate_or_block(
        blockers,
        period_id,
        "symbol_reference",
        validate_symbol_reference_data,
        symbols,
    )
    _validate_or_block(
        blockers,
        period_id,
        "corporate_actions",
        validate_corporate_actions_data,
        corporate_actions,
    )
    _validate_or_block(
        blockers,
        period_id,
        "earnings_events",
        validate_earnings_events_data,
        earnings_events,
    )
    ohlcv_dates = pd.to_datetime(ohlcv["session_date"]).dt.date if not ohlcv.empty else []
    qualification_mask = (
        (pd.Series(ohlcv_dates) >= requirement.start_date)
        & (pd.Series(ohlcv_dates) <= requirement.end_date)
        if len(ohlcv_dates)
        else pd.Series(dtype=bool)
    )
    qualification_rows = ohlcv.loc[qualification_mask.to_numpy()] if len(ohlcv_dates) else ohlcv
    qualification_session_count = (
        int(qualification_rows["session_date"].nunique()) if not qualification_rows.empty else 0
    )
    symbol_count = int(symbols["symbol"].nunique()) if "symbol" in symbols else 0
    if qualification_session_count < requirement.minimum_session_count:
        blockers.append(
            f"{period_id}:minimum_session_count_not_met:{qualification_session_count}"
        )
    if symbol_count > requirement.maximum_symbol_count:
        blockers.append(f"{period_id}:maximum_symbol_count_exceeded:{symbol_count}")
    return SelectedPeriodSmokePeriodResult(
        period_id=period_id,
        passed=not blockers,
        ohlcv_rows=len(ohlcv),
        symbol_count=symbol_count,
        total_session_count=int(ohlcv["session_date"].nunique()) if not ohlcv.empty else 0,
        qualification_session_count=qualification_session_count,
        minimum_session_count=requirement.minimum_session_count,
        maximum_symbol_count=requirement.maximum_symbol_count,
        blockers=tuple(blockers),
    )


def _read_panel_frame(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _validate_or_block(
    blockers: list[str],
    period_id: str,
    artifact_id: str,
    validator: Any,
    frame: pd.DataFrame,
) -> None:
    try:
        validator(frame)
    except Exception as exc:  # noqa: BLE001 - report validator failure as smoke blocker
        blockers.append(f"{period_id}:{artifact_id}_contract_failed:{exc}")


__all__ = [
    "DraftBaselineManifestBundle",
    "DryRunSafetyReport",
    "OvernightEvidenceArtifact",
    "OvernightQualificationEvidenceSummary",
    "SelectedPeriodDataSmokeReport",
    "SelectedPeriodSmokePeriodResult",
    "build_overnight_qualification_evidence_summary",
    "check_selected_period_dry_run_safety",
    "run_selected_period_data_smoke",
    "write_draft_baseline_manifest_bundle",
    "write_json_report",
]
