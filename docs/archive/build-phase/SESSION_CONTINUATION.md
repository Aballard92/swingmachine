# Swingmachine Session Continuation

Saved on: 2026-04-29, Europe/London
Workspace: `/home/alexballard92/swingmachine`

## Current Intent

We are still in design/build phase for `swingmachine`. Do not start live trading work or broker-specific live integration. The current broker scope is paper/shadow/audit only.

## Current Build State

Latest completed hardening pass added:

- Alembic migrations:
  - `migrations/versions/0001_initial_schema.py`
  - `migrations/versions/0002_runtime_events.py`
  - `migrations/versions/0003_shadow_comparison_snapshots.py`
  - `migrations/versions/0004_paper_shadow_audit_snapshots.py`
- Runtime command history and append-only artifact/decision event ledger:
  - `runtime_runs`
  - `runtime_events`
  - CLI commands: `list-run-history`, `list-run-events`
  - Decision events: `PENDING_ENTRY_ACTION_DECIDED`, `PAPER_ENTRY_SUBMISSION_DECIDED`, `SHADOW_ENTRY_PROPOSAL_DECIDED`, `SHADOW_FILL_COMPARISON_RECORDED`
- Shadow comparison persistence:
  - `shadow_fill_comparisons` keeps latest comparison per intent
  - `shadow_fill_comparison_snapshots` keeps immutable repeated-review history
  - CLI command: `summarize-shadow-comparison-snapshots`
  - Snapshot summary rows include `snapshot_id` and `recorded_at`
- Paper-shadow audit persistence:
  - `paper_shadow_audit_snapshots` keeps immutable audit-review history
  - CLI command: `summarize-paper-shadow-audit-snapshots`
  - Audit summary rows include `snapshot_id`, `snapshot_batch_id`, and `recorded_at`
- Composed local review report:
  - Contract: `OperatorReviewReport`
  - Service: `OperatorReviewReportService`
  - CLI command: `run-review-report`
  - Combines rolling audit windows, runtime runs/events, decision events, shadow snapshot summaries, paper-shadow audit snapshot summaries, recent divergences, recent shadow alerts, and derived review exceptions.
  - Supports JSON/YAML and static HTML output via `--format`.
  - Includes threshold-driven `review_status`, `review_thresholds`, and `review_checks`.
  - Persists structured review metrics to `runtime_runs.metrics` and the `REVIEW_REPORT_WRITTEN` event payload via `operator_review_run_metrics`, including status/category counts, non-pass checks, and per-window audit metrics.
  - Review scenario tests assert threshold breaches are visible in both JSON payloads and rendered HTML.
  - CLI command `summarize-review-run-trends` summarizes repeated `run-review-report` metrics into status counts, non-pass category counts, run summaries, and per-window metric trends.
- Build planning:
  - `docs/SOLUTION_DESIGN_AND_DELIVERY_ROADMAP.md` is now the control document
    for solution design, workstreams, delivery batches, dependencies, acceptance
    criteria, decision logging, and what not to build yet.
  - `docs/BUILD_ROADMAP.md` and `docs/BUILD_PLAN.md` are short indexes into
    that program.
  - `docs/HISTORICAL_PANEL_REQUIREMENTS.md` elaborates the next requirements:
    read a panel, reject bad data, replay deterministically, explain decisions,
    and reconcile stages without premature strategy-performance baselining.
- Historical panel manifest validation:
  - Contracts: `HistoricalPanelManifest`, `HistoricalPanelValidationResult`,
    `HistoricalPanelValidationIssue`, and related file summary/spec models.
  - Validator: `validate_historical_panel_manifest`.
  - Fixture: `tests/fixtures/historical_panel/manifest.yaml`.
  - Focused tests cover valid panel, missing file, missing required column,
    duplicate symbol/session, invalid OHLC, unknown earnings session, unknown
    corporate-action symbol, and manifest count mismatch.
- Tiny manifest-backed replay proof:
  - Contract: `HistoricalReplayProofResult`.
  - API: `run_tiny_manifest_replay_proof`.
  - Consumes `validate_historical_panel_manifest` as a hard precondition.
  - Derives deterministic proof-only feature inputs from the tiny prepared
    panel, then exercises setup detection, backtest events, shadow comparison,
    paper submission, and paper-shadow audit alignment.
  - Focused tests prove repeated proof runs produce the same material decisions
    and invalid panels are refused before replay.
- Review scenario fixtures:
  - `tests/fixtures/review_scenarios.py`
  - `examples/review_scenarios/README.md`
  - Multi-symbol, multi-session histories exercise `PASS`, `WARN`, and `FAIL` review outputs through runtime, shadow comparison, paper broker, audit snapshots, and run history.
- Prepared data validators:
  - next-session market data
  - symbol reference data
  - corporate actions
  - earnings events
- Local operator docs:
  - `.env.example`
  - `docs/OPERATING_RUNBOOK.md`
  - `PASS`, `WARN`, and `FAIL` operator responses are documented for design/build review.
- CI now runs:
  - `ruff check .`
  - `mypy --config-file mypy_core.ini`
  - `pytest -q`
- Handover docs are current:
  - `docs/archive/build-phase/BUILD_HANDOVER_AND_AUDIT.md`
  - `docs/archive/build-phase/BUILD_HANDOVER_SUMMARY.json`

## Latest Validation

Last verified:

- `./.venv/bin/python -m compileall src/swingmachine/contracts.py src/swingmachine/data_contracts.py tests/test_data_contracts.py` passed
- `./.venv/bin/pytest -q tests/test_data_contracts.py` passed after historical panel validator: `17 passed in 42.69s`
- `./.venv/bin/pytest -q tests/test_data_contracts.py tests/test_replay_workflow.py` passed after historical panel validator: `18 passed in 79.50s`
- `./.venv/bin/python -m compileall src/swingmachine/contracts.py src/swingmachine/data_contracts.py src/swingmachine/replay.py tests/test_data_contracts.py tests/test_replay_workflow.py` passed after tiny replay proof
- `./.venv/bin/pytest -q tests/test_data_contracts.py tests/test_replay_workflow.py` passed after tiny replay proof: `20 passed in 172.65s`
- `./.venv/bin/ruff check .` passed after tiny replay proof
- `./.venv/bin/mypy --config-file mypy_core.ini --show-error-codes` passed after tiny replay proof: `Success: no issues found in 7 source files`
- `./.venv/bin/ruff check .` passed after historical panel validator
- `./.venv/bin/mypy --config-file mypy_core.ini --show-error-codes` passed after historical panel validator: `Success: no issues found in 7 source files`
- `./.venv/bin/python -m json.tool docs/archive/build-phase/BUILD_HANDOVER_SUMMARY.json` passed after historical panel validator
- `./.venv/bin/python -m compileall src tests` passed
- `./.venv/bin/python -m compileall src/swingmachine/runtime.py src/swingmachine/enums.py tests/test_runtime.py` passed
- `./.venv/bin/ruff check .` passed
- `./.venv/bin/mypy --config-file mypy_core.ini --show-error-codes` passed: `Success: no issues found in 7 source files`
- `./.venv/bin/pytest -q tests/test_reporting.py` passed after threshold status addition: `6 passed in 233.81s`
- `./.venv/bin/pytest -q tests/test_reporting.py::test_multi_session_review_scenarios_exercise_pass_warn_fail` passed: `3 passed in 90.40s`
- `./.venv/bin/pytest -q tests/test_reporting.py::test_multi_session_review_scenarios_exercise_pass_warn_fail` passed after structured review metrics: `3 passed in 85.25s`
- `./.venv/bin/pytest -q tests/test_reporting.py::test_multi_session_review_scenarios_exercise_pass_warn_fail` passed after JSON/HTML threshold-breach checks: `3 passed in 169.17s`
- `./.venv/bin/pytest -q tests/test_reporting.py::test_run_review_report_cli_writes_operator_review_file` passed after structured review run/event metrics: `1 passed in 124.69s`
- `./.venv/bin/pytest -q tests/test_reporting.py` passed after structured review run/event metrics: `9 passed in 242.95s`
- `./.venv/bin/pytest -q tests/test_reporting.py` passed after JSON/HTML threshold-breach checks: `9 passed in 274.95s`
- `./.venv/bin/pytest -q tests/test_runtime.py::test_runtime_cli_summarizes_review_run_trends` passed: `1 passed in 99.66s`
- `./.venv/bin/pytest -q tests/test_reporting.py` passed after review scenario fixtures: `9 passed in 186.21s`
- `./.venv/bin/pytest -q tests/test_runtime.py tests/test_reporting.py` passed: `9 passed in 385.82s`
- `./.venv/bin/python -m json.tool docs/archive/build-phase/BUILD_HANDOVER_SUMMARY.json` passed
- `./.venv/bin/pytest -q tests/test_reporting.py::test_run_review_report_cli_writes_operator_review_html` passed: `1 passed in 138.51s`
- `./.venv/bin/pytest -q tests/test_paper_shadow_audit.py tests/test_migrations.py` passed: `4 passed in 289.20s`
- `./.venv/bin/pytest -q tests/test_runtime.py` passed: `5 passed in 205.51s`
- `./.venv/bin/pytest -q tests/test_shadow_reviews.py` passed: `4 passed in 212.13s`
- `./.venv/bin/pytest -q tests/test_shadow_reviews.py tests/test_migrations.py` previously passed before snapshot-review CLI addition: `4 passed in 159.33s`
- `./.venv/bin/pytest -q tests/test_shadow_reviews.py tests/test_migrations.py tests/test_replay_workflow.py` previously passed before snapshot-review CLI addition: `5 passed in 292.72s`
- `./.venv/bin/pytest -q` passed before the latest review-report patch: `98 passed in 834.28s`
- `./.venv/bin/mypy --show-error-codes` still fails with `25` known strict typing errors in 7 existing pandas/backtest/signal-heavy files

## Git/Repo Caveat

The parent git repo at `/home/alexballard92` still sees `swingmachine/` as untracked:

```bash
git -C /home/alexballard92 status --short -- swingmachine
# ?? swingmachine/
```

Do not rely on `git diff` inside this workspace as the source of truth. Inspect files directly.

## Strong Next Moves

1. Follow `docs/SOLUTION_DESIGN_AND_DELIVERY_ROADMAP.md`: design grouped delivery batches before coding, state non-goals, group implementation/tests/docs together, and record validation.
2. Continue Batch 1 by promoting the tiny manifest-backed replay proof toward a general historical replay runner with run-scoped artifacts.
3. Keep replay focused on machinery: deterministic decisions, explainable artifacts, and stage consistency. Do not add return baselining.
4. Use `summarize-review-run-trends` only after replay/review artifacts exist across a meaningful sample.
5. Keep expanding typed coverage beyond the current seven-file core check without making full pandas-heavy mypy blocking yet.
6. Keep external observability and live execution deferred until local replay/review evidence is stronger.

## Useful Resume Commands

```bash
cd /home/alexballard92/swingmachine
./.venv/bin/python -m swingmachine --help
./.venv/bin/python -m swingmachine run-paper-shadow-audit \
  --input examples/runtime_cycle_input.yaml \
  --market-data examples/next_session_market_data.csv \
  --output-dir output/demo-paper-shadow \
  --database-url sqlite+pysqlite:///./swingmachine_runtime.db
./.venv/bin/python -m swingmachine list-run-events \
  --output output/run_events.json \
  --database-url sqlite+pysqlite:///./swingmachine_runtime.db
./.venv/bin/python -m swingmachine summarize-review-run-trends \
  --output output/review_run_trends.json \
  --database-url sqlite+pysqlite:///./swingmachine_runtime.db
./.venv/bin/python -m swingmachine summarize-shadow-comparison-snapshots \
  --output output/shadow_snapshot_summary.json \
  --database-url sqlite+pysqlite:///./swingmachine_runtime.db
./.venv/bin/python -m swingmachine summarize-paper-shadow-audit-snapshots \
  --output output/paper_shadow_audit_snapshot_summary.json \
  --database-url sqlite+pysqlite:///./swingmachine_runtime.db
./.venv/bin/python -m swingmachine run-review-report \
  --output output/operator_review.json \
  --database-url sqlite+pysqlite:///./swingmachine_runtime.db
./.venv/bin/python -m swingmachine run-review-report \
  --output output/operator_review.html \
  --format html \
  --database-url sqlite+pysqlite:///./swingmachine_runtime.db
./.venv/bin/python -m swingmachine run-review-report \
  --output output/operator_review_experiment.html \
  --format html \
  --min-alignment-rate 0.90 \
  --max-divergent-count 1 \
  --max-shadow-slippage-alert-rate 0.05 \
  --database-url sqlite+pysqlite:///./swingmachine_runtime.db
```

Planning reference:

```bash
sed -n '1,260p' docs/SOLUTION_DESIGN_AND_DELIVERY_ROADMAP.md
sed -n '1,260p' docs/BUILD_ROADMAP.md
sed -n '1,260p' docs/HISTORICAL_PANEL_REQUIREMENTS.md
sed -n '1,140p' docs/BUILD_PLAN.md
```
