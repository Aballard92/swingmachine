# Swing machine v0.1 qualification mini-plan

## Purpose

This mini-plan groups the remaining work into qualification workstreams so the project does not fall back into isolated item-by-item implementation.

The baseline scaffolding, typed contracts, report package, preflight command, readiness gate, and manifest builder now exist. The remaining blocker is qualification evidence, starting with real selected-period data manifests.

## Current decision

Serious full run remains prohibited.

The next execution gate is not strategy tuning and not a full run. It is selected-period data readiness.

## Workstream A: data readiness and manifests

Objective: produce real historical panel manifests for the selected periods in `config/swing_machine_v0_1_selected_periods.yaml`.

Required outputs:

- Manifest for `smoke_recent_5_sessions`.
- Manifest for `recent_medium_replay_window`.
- Manifest for `historical_contract_stability_window`.
- Data provenance/custody note explaining source files, preparation assumptions, adjustment basis, and any known gaps.

Entry criteria:

- Prepared OHLCV, symbol reference, corporate action, earnings event, and optional feature files exist for each selected period.
- Files are explicitly local or explicitly supplied by the operator.
- No live broker, production database, or real order path is involved.

Exit criteria:

- All three manifests are built through `build-historical-panel-manifest` or manually reviewed against the same contract.
- Manifest validation passes or each failure is recorded as a blocker.

## Workstream B: selected-period preflight

Objective: prove selected-period data readiness before any replay execution.

Required outputs:

- `reports/swing_machine_v0_1/selected_period_preflight.json` from the real manifests.
- Blocker list if preflight fails.

Entry criteria:

- Workstream A has produced three manifest paths.

Exit criteria:

- Preflight exits `0`.
- The preflight artifact has `passed=true` and `blocker_count=0`.

## Workstream C: dry-run replay qualification evidence

Objective: run only bounded dry-run/replay qualification after preflight passes.

Required outputs per period:

- `baseline_report_package.json`.
- `freeze_readiness.json`.
- `replay_summary.json`.
- `stage_counts.json`.
- `material_decisions.json`.
- `decision_traces.json`.
- `reconciliation_summary.json`.

Entry criteria:

- Workstream B has passed.
- Output directories are explicit and separated by period.
- Runtime remains dry-run/replay-only.

Exit criteria:

- Smoke period evidence is reviewed before running medium/historical windows.
- Medium and historical periods only proceed if smoke evidence is mechanically clean.

## Workstream D: parity and evidence consolidation

Objective: compare research/runtime-compatible packages and collect a reviewable evidence bundle.

Required outputs:

- `baseline_parity_report.json` per selected comparison.
- Consolidated qualification evidence index.
- Explicit list of pass/fail/blocker decisions.

Entry criteria:

- Workstream C has produced baseline report packages.

Exit criteria:

- Parity reports pass, or differences are field-level and logged as blockers.
- Evidence index links every manifest, replay package, parity report, and readiness decision.

## Workstream E: freeze readiness and operator decision

Objective: decide whether `swing_machine_v0_1` can be frozen for serious full-run consideration.

Required outputs:

- Freeze-readiness decision artifact.
- Operator freeze approval or explicit refusal.
- Serious full run decision record.

Entry criteria:

- Workstream D has passed or blockers are explicitly accepted as non-promotional.
- Every mandatory manifest/checklist item is satisfied.

Exit criteria:

- Serious full run remains prohibited, or is conditionally allowed with explicit operator approval and evidence.

## Do not do yet

- Do not run a serious full run.
- Do not run live trading.
- Do not submit real broker orders.
- Do not promote or freeze the baseline without selected-period evidence.
- Do not treat the tiny fixture panel as selected-period qualification evidence.

## Immediate next decision point

Before running anything else, choose where real selected-period prepared files will come from:

1. Existing local prepared files: provide paths and build manifests.
2. New local data preparation: create a separate data-prep task before manifest building.
3. No data available yet: keep qualification blocked and continue only with offline tooling/docs.
