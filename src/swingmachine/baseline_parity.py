from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field

from swingmachine.baseline_reporting import SwingBaselineReportPackage
from swingmachine.modeling import ImmutableModel, NonNegativeInt


class SwingBaselineParityDifference(ImmutableModel):
    artifact_type: str
    artifact_id: str
    field_path: str
    research_value: Any = None
    runtime_value: Any = None


class SwingBaselineParityReport(ImmutableModel):
    comparison_id: str
    research_package_id: str
    runtime_package_id: str
    passed: bool
    difference_count: NonNegativeInt
    differences: tuple[SwingBaselineParityDifference, ...] = Field(default_factory=tuple)


def compare_baseline_report_packages(
    research_package: SwingBaselineReportPackage,
    runtime_package: SwingBaselineReportPackage,
    *,
    comparison_id: str | None = None,
) -> SwingBaselineParityReport:
    differences: list[SwingBaselineParityDifference] = []
    differences.extend(_compare_manifest_identity(research_package, runtime_package))
    differences.extend(_compare_summary(research_package, runtime_package))
    differences.extend(_compare_artifact_collections(research_package, runtime_package))
    return SwingBaselineParityReport(
        comparison_id=comparison_id
        or (
            "baseline_parity:"
            f"{research_package.manifest.baseline_id}:"
            f"{research_package.manifest.config_hash[:12]}"
        ),
        research_package_id=research_package.package_id,
        runtime_package_id=runtime_package.package_id,
        passed=not differences,
        difference_count=len(differences),
        differences=tuple(differences),
    )


def load_baseline_report_package_json(path: str | Path) -> SwingBaselineReportPackage:
    package_path = Path(path)
    return SwingBaselineReportPackage.model_validate_json(package_path.read_text(encoding="utf-8"))


def compare_baseline_report_package_files(
    research_package_path: str | Path,
    runtime_package_path: str | Path,
    *,
    comparison_id: str | None = None,
) -> SwingBaselineParityReport:
    return compare_baseline_report_packages(
        load_baseline_report_package_json(research_package_path),
        load_baseline_report_package_json(runtime_package_path),
        comparison_id=comparison_id,
    )


def write_baseline_parity_report_json(
    report: SwingBaselineParityReport,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output_path


def _compare_manifest_identity(
    research_package: SwingBaselineReportPackage,
    runtime_package: SwingBaselineReportPackage,
) -> tuple[SwingBaselineParityDifference, ...]:
    research = research_package.manifest
    runtime = runtime_package.manifest
    fields = (
        "baseline_id",
        "contract_version",
        "data_contract_version",
        "strategy_id",
        "strategy_version",
        "config_hash",
        "serious_full_run_allowed",
    )
    return tuple(
        _difference(
            "manifest",
            research.baseline_id,
            field,
            getattr(research, field),
            getattr(runtime, field),
        )
        for field in fields
        if getattr(research, field) != getattr(runtime, field)
    )


def _compare_summary(
    research_package: SwingBaselineReportPackage,
    runtime_package: SwingBaselineReportPackage,
) -> tuple[SwingBaselineParityDifference, ...]:
    research = research_package.summary.model_dump(mode="json")
    runtime = runtime_package.summary.model_dump(mode="json")
    return tuple(_compare_payloads("summary", "summary", research, runtime))


def _compare_artifact_collections(
    research_package: SwingBaselineReportPackage,
    runtime_package: SwingBaselineReportPackage,
) -> tuple[SwingBaselineParityDifference, ...]:
    differences: list[SwingBaselineParityDifference] = []
    for artifact_type, id_attr, collection_attr in _artifact_collection_specs():
        research_items = _items_by_id(getattr(research_package, collection_attr), id_attr)
        runtime_items = _items_by_id(getattr(runtime_package, collection_attr), id_attr)
        for artifact_id in sorted(set(research_items) | set(runtime_items)):
            research_item = research_items.get(artifact_id)
            runtime_item = runtime_items.get(artifact_id)
            if research_item is None:
                differences.append(
                    _difference(artifact_type, artifact_id, "__missing__", None, "present")
                )
                continue
            if runtime_item is None:
                differences.append(
                    _difference(artifact_type, artifact_id, "__missing__", "present", None)
                )
                continue
            differences.extend(
                _compare_payloads(
                    artifact_type,
                    artifact_id,
                    research_item.model_dump(mode="json"),
                    runtime_item.model_dump(mode="json"),
                )
            )
    return tuple(differences)


def _artifact_collection_specs() -> tuple[tuple[str, str, str], ...]:
    return (
        ("feature_snapshot", "feature_snapshot_id", "feature_snapshots"),
        ("universe_member", "member_id", "universe_members"),
        ("candidate", "candidate_id", "candidates"),
        ("signal", "signal_id", "signals"),
        ("risk_plan", "risk_plan_id", "risk_plans"),
        ("order_plan", "order_plan_id", "order_plans"),
        ("lifecycle_transition", "transition_id", "lifecycle_transitions"),
        ("exit_decision", "exit_decision_id", "exit_decisions"),
    )


def _items_by_id(items: tuple[Any, ...], id_attr: str) -> dict[str, Any]:
    return {str(getattr(item, id_attr)): item for item in items}


def _compare_payloads(
    artifact_type: str,
    artifact_id: str,
    research_value: Any,
    runtime_value: Any,
    *,
    path: str = "",
) -> tuple[SwingBaselineParityDifference, ...]:
    differences: list[SwingBaselineParityDifference] = []
    if isinstance(research_value, dict) and isinstance(runtime_value, dict):
        for key in sorted(set(research_value) | set(runtime_value)):
            child_path = key if not path else f"{path}.{key}"
            if key not in research_value:
                differences.append(
                    _difference(artifact_type, artifact_id, child_path, None, runtime_value[key])
                )
            elif key not in runtime_value:
                differences.append(
                    _difference(artifact_type, artifact_id, child_path, research_value[key], None)
                )
            else:
                differences.extend(
                    _compare_payloads(
                        artifact_type,
                        artifact_id,
                        research_value[key],
                        runtime_value[key],
                        path=child_path,
                    )
                )
        return tuple(differences)
    if isinstance(research_value, list) and isinstance(runtime_value, list):
        for index in range(max(len(research_value), len(runtime_value))):
            child_path = f"{path}[{index}]"
            if index >= len(research_value):
                differences.append(
                    _difference(artifact_type, artifact_id, child_path, None, runtime_value[index])
                )
            elif index >= len(runtime_value):
                differences.append(
                    _difference(artifact_type, artifact_id, child_path, research_value[index], None)
                )
            else:
                differences.extend(
                    _compare_payloads(
                        artifact_type,
                        artifact_id,
                        research_value[index],
                        runtime_value[index],
                        path=child_path,
                    )
                )
        return tuple(differences)
    if research_value != runtime_value:
        return (_difference(artifact_type, artifact_id, path, research_value, runtime_value),)
    return ()


def _difference(
    artifact_type: str,
    artifact_id: str,
    field_path: str,
    research_value: Any,
    runtime_value: Any,
) -> SwingBaselineParityDifference:
    return SwingBaselineParityDifference(
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        field_path=field_path,
        research_value=research_value,
        runtime_value=runtime_value,
    )


__all__ = [
    "SwingBaselineParityDifference",
    "SwingBaselineParityReport",
    "compare_baseline_report_packages",
    "compare_baseline_report_package_files",
    "load_baseline_report_package_json",
    "write_baseline_parity_report_json",
]
