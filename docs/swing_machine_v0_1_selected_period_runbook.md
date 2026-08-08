# Swing machine v0.1 selected-period qualification runbook

## Status

Selected-period qualification is currently blocked.

The repository only contains the tiny fixture manifest at `tests/fixtures/historical_panel/manifest.yaml`. That fixture is useful for machinery tests, but it is not accepted as real selected-period qualification evidence.

Serious full run remains prohibited until the selected-period data manifests exist, preflight passes, parity evidence passes, and freeze readiness allows promotion.

## Required prepared files per selected period

For each selected-period ID in `config/swing_machine_v0_1_selected_periods.yaml`, prepare explicit point-in-time-safe files:

- `ohlcv`: historical OHLCV panel, CSV or Parquet.
- `symbol_reference`: symbol reference/universe metadata, CSV or Parquet.
- `corporate_actions`: corporate action file, CSV or Parquet.
- `earnings_events`: earnings event file, CSV or Parquet.
- `features`: optional prepared feature file, CSV or Parquet.

The manifest builder does not fetch data, infer missing rows, run replay, submit orders, or write runtime databases.

## Build a period manifest

Use the Typer app through Python when the console script is not installed in the venv:

```bash
./.venv/bin/python -c 'from swingmachine.runtime import main; main()' \
  build-historical-panel-manifest \
  --output data/qualification/smoke_recent_5_sessions/manifest.yaml \
  --panel-id smoke_recent_5_sessions \
  --ohlcv data/qualification/smoke_recent_5_sessions/ohlcv.parquet \
  --symbol-reference data/qualification/smoke_recent_5_sessions/symbol_reference.parquet \
  --corporate-actions data/qualification/smoke_recent_5_sessions/corporate_actions.parquet \
  --earnings-events data/qualification/smoke_recent_5_sessions/earnings_events.parquet \
  --features data/qualification/smoke_recent_5_sessions/features.parquet \
  --description 'Swing v0.1 selected-period smoke window'
```

Repeat for:

- `smoke_recent_5_sessions`
- `recent_medium_replay_window`
- `historical_contract_stability_window`

## Run selected-period preflight

```bash
./.venv/bin/python -c 'from swingmachine.runtime import main; main()' \
  preflight-selected-period-qualification \
  --plan config/swing_machine_v0_1_selected_periods.yaml \
  --output reports/swing_machine_v0_1/selected_period_preflight.json \
  --data-manifest smoke_recent_5_sessions=data/qualification/smoke_recent_5_sessions/manifest.yaml \
  --data-manifest recent_medium_replay_window=data/qualification/recent_medium_replay_window/manifest.yaml \
  --data-manifest historical_contract_stability_window=data/qualification/historical_contract_stability_window/manifest.yaml
```

Expected behavior:

- Exit code `0`: preflight passed, so selected-period dry-run replay can be considered next.
- Exit code `1`: preflight blocked; inspect `reports/swing_machine_v0_1/selected_period_preflight.json`.

## Safety boundary

Do not run selected-period dry-run replay unless preflight passes.

Do not run any serious full run unless freeze readiness allows it and operator approval is recorded.

## Preflight selected-period source inputs before building manifests

Before building manifests, create a concrete data input plan from the example:

`config/swing_machine_v0_1_selected_period_data_inputs.example.yaml`

Replace the example paths with the real prepared source files for all three selected periods.

Then run:

```bash
./.venv/bin/python -c 'from swingmachine.runtime import main; main()' \
  preflight-selected-period-data-inputs \
  --input-plan config/swing_machine_v0_1_selected_period_data_inputs.example.yaml \
  --output reports/swing_machine_v0_1/selected_period_data_input_preflight.json
```

Expected behavior:

- Exit code `0`: source files exist for every selected period; manifest building can proceed.
- Exit code `1`: source inputs are blocked; inspect `reports/swing_machine_v0_1/selected_period_data_input_preflight.json`.

The current repository state is expected to block here because the example source paths do not exist yet.

## Generate a source input plan from a qualification data root

If prepared files are arranged as `data/qualification/<period_id>/`, generate the data input plan instead of editing every path manually:

```bash
./.venv/bin/python -c 'from swingmachine.runtime import main; main()' \
  build-selected-period-data-input-plan \
  --data-root data/qualification \
  --output config/swing_machine_v0_1_selected_period_data_inputs.yaml \
  --selected-period-plan config/swing_machine_v0_1_selected_periods.yaml
```

The command prefers `.parquet` files when present and falls back to `.csv`. `features` are included only when a `features.parquet` or `features.csv` file exists for the period.

## Build all selected-period manifests after source input preflight passes

After `preflight-selected-period-data-inputs` exits `0`, build all selected-period manifests in one batch:

```bash
./.venv/bin/python -c 'from swingmachine.runtime import main; main()' \
  build-selected-period-manifests \
  --input-plan config/swing_machine_v0_1_selected_period_data_inputs.yaml \
  --output-root data/qualification_manifests \
  --summary-output reports/swing_machine_v0_1/selected_period_manifest_build_summary.json
```

Then run selected-period manifest preflight with the generated manifest paths:

```bash
./.venv/bin/python -c 'from swingmachine.runtime import main; main()' \
  preflight-selected-period-qualification \
  --plan config/swing_machine_v0_1_selected_periods.yaml \
  --output reports/swing_machine_v0_1/selected_period_preflight.json \
  --data-manifest smoke_recent_5_sessions=data/qualification_manifests/smoke_recent_5_sessions/manifest.yaml \
  --data-manifest recent_medium_replay_window=data/qualification_manifests/recent_medium_replay_window/manifest.yaml \
  --data-manifest historical_contract_stability_window=data/qualification_manifests/historical_contract_stability_window/manifest.yaml
```
