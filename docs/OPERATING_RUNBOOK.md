# Swingmachine Local Operating Runbook

> **Historical capability reference.** Paper/runtime operation is currently
> blocked unless an exact human-authorised task names the command and state
> changes. This runbook is not current operational authority.

This runbook is for the current design/build phase. It covers local paper,
shadow, audit, and recovery workflows only. It is not a live trading runbook.

## Scope

- Runtime mode is local `PAPER` and `SHADOW`.
- Market data and runtime inputs are prepared files supplied by the operator.
- SQLite is the local persistence layer.
- Alembic exists for schema evolution, but the local runtime still creates
  missing tables with SQLAlchemy `create_all`.
- No broker credentials, live order routing, scheduler, alert transport, or
  production deployment is configured in this repo.

## Local Setup

```bash
python -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[dev]"
```

Optional shell defaults:

```bash
set -a
. ./.env.example
set +a
```

## Database Setup

For a fresh local database:

```bash
./.venv/bin/alembic upgrade head
```

The runtime also calls `initialize_database(engine)` and creates missing tables
for local use. For handoff and schema review, prefer the Alembic path.

Rollback a disposable local database:

```bash
./.venv/bin/alembic downgrade base
rm -f swingmachine_runtime.db
```

Only remove a database after preserving any output or history you still need.

## Daily Paper/Shadow/Audit Workflow

```bash
./.venv/bin/python -m swingmachine run-paper-shadow-audit \
  --input "${SWINGMACHINE_RUNTIME_INPUT:-examples/runtime_cycle_input.yaml}" \
  --market-data "${SWINGMACHINE_NEXT_SESSION_MARKET_DATA:-examples/next_session_market_data.csv}" \
  --output-dir "${SWINGMACHINE_OUTPUT_DIR:-output/demo-paper-shadow}" \
  --database-url "${SWINGMACHINE_DATABASE_URL:-sqlite+pysqlite:///./swingmachine_runtime.db}"
```

Expected artifacts:

- `shadow_result.json`
- `shadow_comparison.json`
- `paper_result.json`
- `shadow_summary.json`
- `paper_shadow_audit_summary.json`
- `audit_report_<date>.json`
- `audit_report_latest.json`
- `workflow_summary.json`

## Historical Panel Validation

Historical panel manifest validation is available as a Python API. It validates
prepared panel structure before replay work begins: OHLCV, symbol reference,
corporate actions, earnings events, optional replay-ready features, file paths,
optional SHA-256 checksums, session range, `feature_start_session`, expected
counts, and cross-file symbol consistency. If a feature file is declared, missing
feature rows are only allowed before `feature_start_session`; coverage gaps from
that session onward are validation failures. The default `feature_coverage_scope`
is `all_ohlcv`; use `tradable_reference` when raw OHLCV intentionally includes
symbols outside the replay universe and `symbol_reference.is_tradable` should
define feature coverage. `symbol_reference` may also include
`tradable_start_session` and `tradable_end_session` to make that coverage
date-aware. For point-in-time reference changes, `symbol_reference` may include
multiple rows for a symbol with `effective_start_session` and
`effective_end_session`; those effective windows must not overlap, and every
OHLCV symbol/session must have exactly one active reference row. Prepared feature
rows must carry metadata that matches that active reference row for
`asset_type`, `sector`, `exchange`, and `is_tradable`.

This is machinery validation only. Do not use it to baseline returns, tune
parameters, or claim strategy readiness.

Tiny fixture:

```text
tests/fixtures/historical_panel/manifest.yaml
```

Python validation entry point:

```python
from swingmachine.data_contracts import validate_historical_panel_manifest

result = validate_historical_panel_manifest("tests/fixtures/historical_panel/manifest.yaml")
```

`result.status` is `PASS`, `WARN`, or `FAIL`. Inspect `result.errors`,
`result.warnings`, and `result.file_summaries` before using a panel as replay
input.

The tiny fixture also runs through the manifest-backed replay path. It consumes
the validator as a hard precondition. When a manifest includes `files.features`,
replay uses those validated prepared features; otherwise it falls back to the
deterministic proof-derived feature adapter. It exercises setup detection,
backtest event generation, shadow comparison, paper submission, and audit
alignment on the prepared panel. It deliberately does not report return metrics
as progression criteria.

CLI replay entry point:

```bash
./.venv/bin/python -m swingmachine run-historical-replay \
  --manifest tests/fixtures/historical_panel/manifest.yaml \
  --output-dir output/historical-replay-proof
```

Expected replay artifacts:

- `validation_summary.json`
- `replay_summary.json`
- `stage_counts.json`
- `material_decisions.json`
- `decision_traces.json`
- `reconciliation_summary.json`
- `workflow_summary.json`
- `failure_summary.json` when the panel cannot replay

Python proof API:

```python
from swingmachine.config import load_strategy_config
from swingmachine.replay import run_tiny_manifest_replay_proof

config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
proof = run_tiny_manifest_replay_proof(
    "tests/fixtures/historical_panel/manifest.yaml",
    config,
    database_url="sqlite+pysqlite:///./swingmachine_replay_proof.db",
)
```

See `docs/HISTORICAL_PANEL_REQUIREMENTS.md` for the exact requirements and
non-goals.

## Inspecting History

Command-level run history:

```bash
./.venv/bin/python -m swingmachine list-run-history \
  --output output/run_history.json \
  --database-url "${SWINGMACHINE_DATABASE_URL:-sqlite+pysqlite:///./swingmachine_runtime.db}"
```

Append-only runtime event ledger. This includes workflow artifact events plus
per-symbol/per-intent decision events for paper submissions, shadow proposals, shadow
fill comparisons, and pending-entry actions when present:

```bash
./.venv/bin/python -m swingmachine list-run-events \
  --output output/run_events.json \
  --database-url "${SWINGMACHINE_DATABASE_URL:-sqlite+pysqlite:///./swingmachine_runtime.db}"
```

Repeated review trend summary. This filters `runtime_runs` to
`run-review-report` rows and summarizes status counts, non-pass categories, and
per-window alignment/divergence/missing-data/slippage metrics:

```bash
./.venv/bin/python -m swingmachine summarize-review-run-trends \
  --output output/review_run_trends.json \
  --database-url "${SWINGMACHINE_DATABASE_URL:-sqlite+pysqlite:///./swingmachine_runtime.db}"
```

Shadow fill comparisons keep both latest state and append-only review history:
`shadow_fill_comparisons` is the current row per intent, while
`shadow_fill_comparison_snapshots` records each comparison batch review.

Review latest shadow comparison state:

```bash
./.venv/bin/python -m swingmachine summarize-shadow-fills \
  --output output/shadow_latest_summary.json \
  --database-url "${SWINGMACHINE_DATABASE_URL:-sqlite+pysqlite:///./swingmachine_runtime.db}"
```

Review the append-only comparison snapshot history. Rows include `snapshot_id`
and `recorded_at` so repeated reviews can be distinguished from the current
latest row:

```bash
./.venv/bin/python -m swingmachine summarize-shadow-comparison-snapshots \
  --output output/shadow_snapshot_summary.json \
  --database-url "${SWINGMACHINE_DATABASE_URL:-sqlite+pysqlite:///./swingmachine_runtime.db}"
```

Paper-shadow audit summaries now write immutable audit-review snapshots into
`paper_shadow_audit_snapshots`. The `paper_shadow_audit_summary.json` artifact
includes `snapshot_batch_id`; use it to review exactly what was captured for
that audit run:

```bash
./.venv/bin/python -m swingmachine summarize-paper-shadow-audit-snapshots \
  --snapshot-batch-id "<snapshot_batch_id from paper_shadow_audit_summary.json>" \
  --output output/paper_shadow_audit_snapshot_summary.json \
  --database-url "${SWINGMACHINE_DATABASE_URL:-sqlite+pysqlite:///./swingmachine_runtime.db}"
```

For a single local review artifact, compose the rolling audit report, latest run
history, decision events, immutable shadow snapshots, immutable paper-shadow
audit snapshots, recent divergences, shadow alerts, and derived review
exceptions:

```bash
./.venv/bin/python -m swingmachine run-review-report \
  --output output/operator_review.json \
  --database-url "${SWINGMACHINE_DATABASE_URL:-sqlite+pysqlite:///./swingmachine_runtime.db}"
```

For human review, render the same payload as static HTML:

```bash
./.venv/bin/python -m swingmachine run-review-report \
  --output output/operator_review.html \
  --format html \
  --database-url "${SWINGMACHINE_DATABASE_URL:-sqlite+pysqlite:///./swingmachine_runtime.db}"
```

Review status is threshold-driven. The report includes:

- `review_status`: overall `PASS`, `WARN`, or `FAIL`.
- `review_thresholds`: the criteria used to evaluate the run.
- `review_checks`: individual traceability, snapshot, alignment, divergence,
  missing-data, and slippage checks.

To include historical replay evidence, pass the replay output directory. The
review report will add replay status, validation, decision-trace, and
reconciliation checks:

```bash
./.venv/bin/python -m swingmachine run-review-report \
  --output output/operator_review_with_replay.json \
  --database-url "${SWINGMACHINE_DATABASE_URL:-sqlite+pysqlite:///./swingmachine_runtime.db}" \
  --replay-output-dir output/historical-replay-proof
```

The same command records structured review metrics to `runtime_runs.metrics` and
the `REVIEW_REPORT_WRITTEN` runtime event payload. Key fields include:

- `review_check_status_counts` and `review_check_category_status_counts`
- `non_pass_review_checks`
- `rolling_window_metrics` and `latest_window_metrics`
- `shadow_snapshot_comparison_count`
- `paper_shadow_audit_snapshot_record_count`

Default thresholds are strict because this is still design/build:

- `--min-alignment-rate 0.95`
- `--max-divergent-count 0`
- `--max-shadow-slippage-alert-rate 0.0`
- `--max-missing-market-data-count 0`

Operator response:

- `PASS`: archive the JSON or HTML report with the run history. Continue
  paper/shadow review, but do not expand scope unless the same criteria pass
  repeatedly across the intended sample.
- `WARN`: pause scope expansion. Inspect `non_pass_review_checks`,
  `review_exceptions`, recent divergences, recent shadow alerts, and the
  decision events for the affected windows. Record the cause and rerun after
  the data, threshold, or workflow issue is understood.
- `FAIL`: treat the review as invalid for progression. Do not use the result to
  justify broader paper/shadow scope. Fix the failing input, snapshot, or
  traceability condition, keep the failed artifact for audit, and rerun into a
  new output path.

Relax thresholds only for a named experiment and keep the generated report:

```bash
./.venv/bin/python -m swingmachine run-review-report \
  --output output/operator_review_experiment.html \
  --format html \
  --min-alignment-rate 0.90 \
  --max-divergent-count 1 \
  --max-shadow-slippage-alert-rate 0.05 \
  --database-url "${SWINGMACHINE_DATABASE_URL:-sqlite+pysqlite:///./swingmachine_runtime.db}"
```

Filter events for one run:

```bash
./.venv/bin/python -m swingmachine list-run-events \
  --run-id "<run_id from workflow_summary.json>" \
  --output output/run_events_for_run.json \
  --database-url "${SWINGMACHINE_DATABASE_URL:-sqlite+pysqlite:///./swingmachine_runtime.db}"
```

## Recovery From Interrupted Local Runs

1. Check whether `workflow_summary.json` exists in the output directory.
2. Inspect `run_history.json` and `run_events.json`.
3. If no successful `run-paper-shadow-audit` row exists, keep the partial
   output directory for debugging and rerun into a new output directory.
4. If a run row exists but expected files are missing, treat the run as
   incomplete and rerun into a new output directory.
5. Do not manually edit the SQLite state unless you are intentionally testing a
   recovery path.

## Quality Gates

```bash
./.venv/bin/python -m compileall src tests
./.venv/bin/ruff check .
./.venv/bin/mypy --config-file mypy_core.ini
./.venv/bin/pytest -q
```

Full strict mypy is still a backlog item:

```bash
./.venv/bin/mypy --show-error-codes
```

The blocking `mypy_core.ini` gate currently covers the typed runtime core:
`modeling.py`, `enums.py`, `config.py`, `contracts.py`, `storage.py`,
`run_history.py`, and `runtime.py`.

## Current Production Non-Goals

- No live broker adapter.
- No broker credentials or secrets handling.
- No scheduler, queue, service manager, or deployment target.
- No external logging, metrics, live dashboards, or alert delivery.
- No production market-data ingestion or point-in-time reference master.
