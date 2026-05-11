from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, model_validator

from swingmachine.baseline import (
    BASELINE_ID,
    load_swing_selected_qualification_plan,
)
from swingmachine.modeling import ImmutableModel, NonNegativeInt

DATA_INPUT_PLAN_VERSION = "swing_machine_v0_1_data_input_plan_v1"

SourceDataInputBlockerCode = Literal[
    "selected_period_plan_period_missing",
    "source_period_unexpected",
    "source_period_duplicate",
    "source_file_missing",
]


class SwingSelectedPeriodDataInputFiles(ImmutableModel):
    period_id: str
    ohlcv_path: str
    symbol_reference_path: str
    corporate_actions_path: str
    earnings_events_path: str
    features_path: str | None = None

    def source_paths(self) -> tuple[tuple[str, str], ...]:
        paths = [
            ("ohlcv", self.ohlcv_path),
            ("symbol_reference", self.symbol_reference_path),
            ("corporate_actions", self.corporate_actions_path),
            ("earnings_events", self.earnings_events_path),
        ]
        if self.features_path is not None:
            paths.append(("features", self.features_path))
        return tuple(paths)


class SwingSelectedPeriodDataInputPlan(ImmutableModel):
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    plan_version: Literal["swing_machine_v0_1_data_input_plan_v1"] = DATA_INPUT_PLAN_VERSION
    selected_period_plan_path: str
    periods: tuple[SwingSelectedPeriodDataInputFiles, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _period_ids_are_unique(self):
        period_ids = [period.period_id for period in self.periods]
        if len(period_ids) != len(set(period_ids)):
            raise ValueError("selected-period data input period ids must be unique")
        return self


class SwingSelectedPeriodDataInputPreflightBlocker(ImmutableModel):
    code: SourceDataInputBlockerCode
    message: str
    period_id: str | None = None
    file_key: str | None = None
    path: str | None = None


class SwingSelectedPeriodDataInputPreflightResult(ImmutableModel):
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    plan_version: Literal["swing_machine_v0_1_data_input_plan_v1"] = DATA_INPUT_PLAN_VERSION
    input_plan_path: str
    selected_period_plan_path: str
    passed: bool
    blocker_count: NonNegativeInt
    blockers: tuple[SwingSelectedPeriodDataInputPreflightBlocker, ...] = Field(
        default_factory=tuple
    )
    expected_period_ids: tuple[str, ...]
    supplied_period_ids: tuple[str, ...]
    evidence: tuple[str, ...] = Field(default_factory=tuple)


def load_selected_period_data_input_plan(path: str | Path) -> SwingSelectedPeriodDataInputPlan:
    input_plan_path = Path(path)
    with input_plan_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at root of {input_plan_path}")
    return SwingSelectedPeriodDataInputPlan.model_validate(data)


def build_selected_period_data_input_plan_from_root(
    data_root: str | Path,
    *,
    selected_period_plan_path: str | Path,
) -> SwingSelectedPeriodDataInputPlan:
    root = Path(data_root).resolve()
    selected_plan_path = Path(selected_period_plan_path).resolve()
    selected_plan = load_swing_selected_qualification_plan(selected_plan_path)
    periods = []
    for period in selected_plan.periods:
        period_dir = root / period.period_id
        features_path = _preferred_source_path(period_dir, "features")
        periods.append(
            SwingSelectedPeriodDataInputFiles(
                period_id=period.period_id,
                ohlcv_path=str(_preferred_source_path(period_dir, "ohlcv")),
                symbol_reference_path=str(_preferred_source_path(period_dir, "symbol_reference")),
                corporate_actions_path=str(_preferred_source_path(period_dir, "corporate_actions")),
                earnings_events_path=str(_preferred_source_path(period_dir, "earnings_events")),
                features_path=None if not features_path.exists() else str(features_path),
            )
        )
    return SwingSelectedPeriodDataInputPlan(
        selected_period_plan_path=str(selected_plan_path),
        periods=tuple(periods),
    )


def write_selected_period_data_input_plan_yaml(
    plan: SwingSelectedPeriodDataInputPlan,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(plan.model_dump(mode="json", exclude_none=True), sort_keys=False),
        encoding="utf-8",
    )
    return output_path


def preflight_selected_period_data_inputs(
    input_plan_path: str | Path,
    *,
    selected_period_plan_path: str | Path | None = None,
) -> SwingSelectedPeriodDataInputPreflightResult:
    input_path = Path(input_plan_path)
    input_plan = load_selected_period_data_input_plan(input_path)
    selected_plan_path = _resolve_selected_period_plan_path(
        input_path,
        input_plan,
        selected_period_plan_path,
    )
    selected_plan = load_swing_selected_qualification_plan(selected_plan_path)
    expected_period_ids = tuple(period.period_id for period in selected_plan.periods)
    supplied_period_ids = tuple(period.period_id for period in input_plan.periods)
    blockers: list[SwingSelectedPeriodDataInputPreflightBlocker] = []

    supplied = {period.period_id: period for period in input_plan.periods}
    for period_id in expected_period_ids:
        if period_id not in supplied:
            blockers.append(
                SwingSelectedPeriodDataInputPreflightBlocker(
                    code="selected_period_plan_period_missing",
                    message="Selected-period source input plan does not supply this period.",
                    period_id=period_id,
                )
            )
    for period_id in supplied_period_ids:
        if period_id not in set(expected_period_ids):
            blockers.append(
                SwingSelectedPeriodDataInputPreflightBlocker(
                    code="source_period_unexpected",
                    message="Selected-period source input plan supplies an unexpected period.",
                    period_id=period_id,
                )
            )
    for period in input_plan.periods:
        for file_key, source_path in period.source_paths():
            resolved = _resolve_source_path(input_path, source_path)
            if not resolved.exists():
                blockers.append(
                    SwingSelectedPeriodDataInputPreflightBlocker(
                        code="source_file_missing",
                        message="Selected-period source file does not exist.",
                        period_id=period.period_id,
                        file_key=file_key,
                        path=str(resolved),
                    )
                )
    return SwingSelectedPeriodDataInputPreflightResult(
        input_plan_path=input_path.as_posix(),
        selected_period_plan_path=selected_plan_path.as_posix(),
        passed=not blockers,
        blocker_count=len(blockers),
        blockers=tuple(blockers),
        expected_period_ids=expected_period_ids,
        supplied_period_ids=supplied_period_ids,
        evidence=(
            f"expected_period_count:{len(expected_period_ids)}",
            f"supplied_period_count:{len(supplied_period_ids)}",
        ),
    )


def write_selected_period_data_input_preflight_json(
    result: SwingSelectedPeriodDataInputPreflightResult,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output_path


def _resolve_selected_period_plan_path(
    input_plan_path: Path,
    input_plan: SwingSelectedPeriodDataInputPlan,
    override_path: str | Path | None,
) -> Path:
    selected_plan_path = Path(override_path or input_plan.selected_period_plan_path)
    if not selected_plan_path.is_absolute():
        selected_plan_path = input_plan_path.parent / selected_plan_path
    return selected_plan_path.resolve()


def _resolve_source_path(input_plan_path: Path, source_path: str) -> Path:
    path = Path(source_path)
    if not path.is_absolute():
        path = input_plan_path.parent / path
    return path.resolve()


def _preferred_source_path(period_dir: Path, stem: str) -> Path:
    parquet_path = period_dir / f"{stem}.parquet"
    if parquet_path.exists():
        return parquet_path
    csv_path = period_dir / f"{stem}.csv"
    if csv_path.exists():
        return csv_path
    return parquet_path


__all__ = [
    "DATA_INPUT_PLAN_VERSION",
    "SourceDataInputBlockerCode",
    "SwingSelectedPeriodDataInputFiles",
    "SwingSelectedPeriodDataInputPlan",
    "SwingSelectedPeriodDataInputPreflightBlocker",
    "SwingSelectedPeriodDataInputPreflightResult",
    "build_selected_period_data_input_plan_from_root",
    "load_selected_period_data_input_plan",
    "preflight_selected_period_data_inputs",
    "write_selected_period_data_input_plan_yaml",
    "write_selected_period_data_input_preflight_json",
]
