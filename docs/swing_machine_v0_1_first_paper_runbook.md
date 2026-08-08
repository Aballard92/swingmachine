# Swing Machine v0.1 first controlled paper-trading runbook

> **Historical and superseded.** Paper trading is currently blocked. This
> runbook is retained for provenance and does not authorise preparation or
> execution of any paper, broker, API, or runtime command. Current authority is
> under `docs/project-control/`.

Date: 2026-05-07
Baseline: `swing_machine_v0_1`
Status: runbook prepared, paper execution not approved or executed

## Decision

Do not execute paper trading automatically.

Engineering gates now support considering a controlled paper-trading trial, but the first paper run must be explicitly approved by the operator after reviewing this runbook and the exact command.

## Current engineering evidence

Latest clean lifecycle qualification:

- Run ID: `20260507T065158Z`
- Summary: `reports/swing_machine_v0_1/historical_broad_lifecycle_qualification_summary_20260507T065158Z.json`
- Status: `PASS`
- Research status: `PASS`
- Runtime-compatible status: `PASS`
- Parity difference count: `0`
- Processed sessions: `634`
- Lifecycle transitions: `490`
- Pending-order snapshots: `712`
- Position snapshots: `1080`
- Reconciliation warnings: none
- Reconciliation failures: none

Latest full pre-paper test gate:

- Run ID: `20260507T072058Z`
- Summary: `reports/swing_machine_v0_1/pre_paper_test_gate_20260507T072058Z/pre_paper_test_gate_summary.json`
- Full ruff: passed
- Full pytest: `246 passed in 1364.99s`

First paper preflight performed for this runbook:

- Output: `reports/swing_machine_v0_1/first_paper_preflight_20260507T075235Z.json`
- Preflight command: `.venv/bin/swingmachine check-selected-period-dry-run-safety --output reports/swing_machine_v0_1/first_paper_preflight_20260507T075235Z.json`
- Result: `passed: true`
- Execution mode: `DRY_RUN_REPLAY_ONLY`
- Broker execution allowed: `false`
- Live order actions allowed: `false`
- Paper order actions allowed: `false`

## Important scope clarification

The available runtime command for paper execution is `run-cycle`.

`run-cycle` executes one provided `RuntimeCycleInput` file. It is not, by itself, an autonomous live scheduler or scanner. The first paper run therefore requires a reviewed cycle input file.

The first paper trial should be a single controlled cycle, not an unattended multi-day service.

## Required files for first paper trial

Create a run directory before execution:

```bash
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)
RUN_DIR="reports/swing_machine_v0_1/first_paper_trial_${RUN_ID}"
mkdir -p "$RUN_DIR"
```

Required files inside the run directory:

- `cycle_input.yaml`: reviewed `RuntimeCycleInput` for the cycle.
- `shadow_preview.json`: shadow-mode preview output.
- `paper_cycle_output.json`: paper-mode output, only after approval.
- `paper_runtime.db`: local SQLite runtime database for the trial.
- `operator_approval.txt`: explicit operator approval record.
- `post_run_review.md`: immediate post-run notes.

## Cycle input requirements

The `cycle_input.yaml` must be reviewed before paper execution.

Required fields:

- `as_of`
- `regime_state`
- `equity`
- `last_data_at`
- `expires_at`
- `setups`
- `sector_by_symbol` where sector exposure is relevant

Required checks:

- `mode` must not be in the input file; mode is controlled by the command.
- `regime_state` must be explicit.
- `equity` must be explicit and realistic for the paper account simulation.
- Each setup must have explicit `symbol`, `session_date`, `pattern_type`, `setup_id`, `setup_start_date`, `setup_end_date`, `setup_high`, `setup_low`, `setup_high_date`, `setup_low_date`, `entry_trigger`, `entry_limit`, `initial_stop`, `per_share_risk`, and `spent`.
- No setup should be included unless it is explainable from the latest reviewed signal package.
- No hidden `.env` strategy behaviour may be required.

## Mandatory shadow preview command

Before paper mode, run shadow mode against the exact same input.

```bash
.venv/bin/swingmachine run-cycle \
  --mode SHADOW \
  --config swing_trading_bot_config_template_v2.yaml \
  --database-url "sqlite+pysqlite:///${RUN_DIR}/paper_runtime.db" \
  --input "${RUN_DIR}/cycle_input.yaml" \
  --output "${RUN_DIR}/shadow_preview.json"
```

Shadow preview acceptance criteria:

- Command exits successfully.
- Output mode is `SHADOW`.
- No paper order batch is present.
- Proposed entries match the reviewed setups.
- Any rejected entries have explicit reject reasons.
- No kill switch or monitoring alert blocks the cycle.
- Operator reviews `shadow_preview.json` before paper mode.

## Exact paper command requiring approval

Paper execution command, not approved yet:

```bash
.venv/bin/swingmachine run-cycle \
  --mode PAPER \
  --config swing_trading_bot_config_template_v2.yaml \
  --database-url "sqlite+pysqlite:///${RUN_DIR}/paper_runtime.db" \
  --input "${RUN_DIR}/cycle_input.yaml" \
  --output "${RUN_DIR}/paper_cycle_output.json"
```

This command must not be run until the operator explicitly approves it.

## Operator approval checklist

Before running paper mode, confirm:

- The exact `RUN_DIR` is known.
- The exact `cycle_input.yaml` has been reviewed.
- The shadow preview has been reviewed.
- The command uses `--mode PAPER`, not any live mode.
- The config path is `swing_trading_bot_config_template_v2.yaml` unless explicitly changed.
- The database URL points to the local run directory.
- No external broker credential or live adapter is needed.
- The expected maximum new risk is acceptable.
- The expected number of submitted paper entries is acceptable.
- Stop criteria are understood.
- Post-run review will be completed immediately.

Approval record format:

```text
Approved by: <operator>
Approved at: <UTC timestamp>
Run directory: <RUN_DIR>
Cycle input sha256: <sha256>
Shadow preview reviewed: yes/no
Approved command: <exact command>
Notes: <operator notes>
```

## Stop criteria

Stop and do not continue if any of the following occurs:

- Shadow preview differs from expected reviewed setups.
- Paper output contains an unexpected symbol.
- Paper output contains unexpected quantity, stop, limit, or risk sizing.
- Any monitoring alert or kill-switch condition appears.
- Runtime writes outside the run directory unexpectedly.
- Any code path attempts live broker execution.
- Any exception occurs during paper execution.

## Immediate post-run review

After paper mode, inspect and record:

- Submitted paper entries.
- Rejected paper entries and reasons.
- Pending entry intents stored in the local database.
- Paper broker open orders in the local database.
- Runtime output JSON.
- Any monitoring alerts.
- Any mismatch versus shadow preview.

Create:

```bash
${RUN_DIR}/post_run_review.md
```

Minimum review fields:

- Run ID
- Command executed
- Output file
- Database path
- Submitted count
- Rejected count
- Symbols submitted
- Risk summary
- Alerts
- Deviations from shadow preview
- Decision: continue monitoring / stop / rollback / investigate

## Prohibited actions

Still prohibited:

- Live trading.
- Real broker orders.
- Production deployment actions.
- Destructive database changes.
- Unattended multi-cycle paper operation.
- Any `.env`-controlled hidden strategy behaviour.

## Recommendation

Next step is not paper execution.

Next step is to prepare a specific `cycle_input.yaml`, run the mandatory shadow preview, and ask the operator to approve or reject the exact paper command.
