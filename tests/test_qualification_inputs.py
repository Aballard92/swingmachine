from __future__ import annotations

from pathlib import Path

import yaml

from swingmachine.qualification_inputs import (
    DATA_INPUT_PLAN_VERSION,
    build_selected_period_data_input_plan_from_root,
    load_selected_period_data_input_plan,
    preflight_selected_period_data_inputs,
    write_selected_period_data_input_plan_yaml,
    write_selected_period_data_input_preflight_json,
)

SELECTED_PERIOD_PLAN_PATH = Path("config/swing_machine_v0_1_selected_periods.yaml").resolve()
PERIOD_IDS = (
    "smoke_recent_5_sessions",
    "recent_medium_replay_window",
    "historical_contract_stability_window",
)


def _write_data_input_plan(
    path: Path,
    *,
    period_paths: dict[str, dict[str, Path]],
) -> None:
    payload = {
        "baseline_id": "swing_machine_v0_1",
        "plan_version": DATA_INPUT_PLAN_VERSION,
        "selected_period_plan_path": str(SELECTED_PERIOD_PLAN_PATH),
        "periods": [
            {
                "period_id": period_id,
                "ohlcv_path": str(paths["ohlcv"]),
                "symbol_reference_path": str(paths["symbol_reference"]),
                "corporate_actions_path": str(paths["corporate_actions"]),
                "earnings_events_path": str(paths["earnings_events"]),
                "features_path": str(paths["features"]),
            }
            for period_id, paths in period_paths.items()
        ],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _period_paths(tmp_path: Path, period_id: str) -> dict[str, Path]:
    period_dir = tmp_path / period_id
    return {
        "ohlcv": period_dir / "ohlcv.csv",
        "symbol_reference": period_dir / "symbol_reference.csv",
        "corporate_actions": period_dir / "corporate_actions.csv",
        "earnings_events": period_dir / "earnings_events.csv",
        "features": period_dir / "features.csv",
    }


def test_selected_period_data_input_preflight_blocks_missing_sources(tmp_path: Path) -> None:
    input_plan_path = tmp_path / "data_inputs.yaml"
    _write_data_input_plan(
        input_plan_path,
        period_paths={
            "smoke_recent_5_sessions": _period_paths(tmp_path, "smoke_recent_5_sessions")
        },
    )

    result = preflight_selected_period_data_inputs(input_plan_path)
    result_path = write_selected_period_data_input_preflight_json(
        result,
        tmp_path / "data_input_preflight.json",
    )

    assert result.passed is False
    assert {blocker.code for blocker in result.blockers} == {
        "selected_period_plan_period_missing",
        "source_file_missing",
    }
    assert result.expected_period_ids == PERIOD_IDS
    assert result.supplied_period_ids == ("smoke_recent_5_sessions",)
    assert result_path.read_text(encoding="utf-8").startswith("{\n")


def test_selected_period_data_input_preflight_passes_existing_sources(tmp_path: Path) -> None:
    all_period_paths = {period_id: _period_paths(tmp_path, period_id) for period_id in PERIOD_IDS}
    for paths in all_period_paths.values():
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("placeholder\n", encoding="utf-8")
    input_plan_path = tmp_path / "data_inputs.yaml"
    _write_data_input_plan(input_plan_path, period_paths=all_period_paths)

    result = preflight_selected_period_data_inputs(input_plan_path)

    assert result.passed is True
    assert result.blocker_count == 0
    assert result.blockers == ()
    assert result.expected_period_ids == PERIOD_IDS
    assert result.supplied_period_ids == PERIOD_IDS


def test_selected_period_data_input_plan_builder_uses_data_root(tmp_path: Path) -> None:
    data_root = tmp_path / "qualification"
    for period_id in PERIOD_IDS:
        paths = _period_paths(data_root, period_id)
        for file_key, path in paths.items():
            if file_key == "features":
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("placeholder\n", encoding="utf-8")
    output_path = tmp_path / "generated_data_inputs.yaml"

    plan = build_selected_period_data_input_plan_from_root(
        data_root,
        selected_period_plan_path=SELECTED_PERIOD_PLAN_PATH,
    )
    write_selected_period_data_input_plan_yaml(plan, output_path)
    loaded = load_selected_period_data_input_plan(output_path)
    result = preflight_selected_period_data_inputs(output_path)

    assert loaded.selected_period_plan_path == str(SELECTED_PERIOD_PLAN_PATH)
    assert loaded.periods[0].ohlcv_path.endswith("smoke_recent_5_sessions/ohlcv.csv")
    assert loaded.periods[0].features_path is None
    assert result.passed is True
