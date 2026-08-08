# Swing Machine v0.1 paper-trading review packet

> **Historical and superseded.** The later research and sample-size evidence
> blocks paper trading. This packet grants no current authority. Read
> `docs/project-control/02_CURRENT_STATE.md` and
> `docs/project-control/04_DECISION_LOG.md` first.

Date: 2026-05-07
Baseline: `swing_machine_v0_1`
Status: engineering gates passed; paper trading requires explicit operator approval of the exact command

## Decision

The engineering evidence gate for considering a controlled paper-trading trial is now passed.

Do not start paper trading automatically. Paper trading remains an operator action that requires explicit approval of the exact command, runtime profile, database/output paths, account/broker mode, kill-switch state, and rollback/stop criteria.

## Current evidence summary

### Tier 2 lifecycle state export

Completed items:

- `SWING-V01-131`: exported full backtest lifecycle state for Tier 2 snapshots.
- `SWING-V01-132`: repaired local console-script entry point.

Result:

- `BacktestResult` now exports real pending-order snapshots.
- `BacktestResult` now exports real active/open position snapshots.
- Tier 2 artifacts now consume those snapshots directly.
- The previous lifecycle warning `PENDING_ORDER_DETAILS_NOT_AVAILABLE_FROM_BACKTEST_RESULT` is resolved.
- `.venv/bin/swingmachine` now exists and exposes `run-historical-portfolio-lifecycle-replay`.

### Broad historical lifecycle qualification

Run ID: `20260507T065158Z`

Artifacts:

- Research output: `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T065158Z/`
- Runtime-compatible output: `reports/swing_machine_v0_1/lifecycle_broad_runtime_20260507T065158Z/`
- Parity report: `reports/swing_machine_v0_1/historical_broad_lifecycle_parity_report_20260507T065158Z.json`
- Qualification summary: `reports/swing_machine_v0_1/historical_broad_lifecycle_qualification_summary_20260507T065158Z.json`

Result:

- Overall status: `PASS`.
- Research status: `PASS`.
- Runtime-compatible status: `PASS`.
- Parity passed: `true`.
- Parity difference count: `0`.
- Processed sessions: `634`.
- Lifecycle transitions: `490`.
- Pending-order snapshots: `712`.
- Position snapshots: `1080`.
- Reconciliation failures: none.
- Reconciliation warnings: none.

### Full pre-paper test gate

Run ID: `20260507T072058Z`

Artifacts:

- Summary: `reports/swing_machine_v0_1/pre_paper_test_gate_20260507T072058Z/pre_paper_test_gate_summary.json`
- Ruff log: `reports/swing_machine_v0_1/pre_paper_test_gate_20260507T072058Z/ruff_check.log`
- Pytest log: `reports/swing_machine_v0_1/pre_paper_test_gate_20260507T072058Z/pytest.log`

Result:

- Full ruff: passed.
- Full pytest: `246 passed in 1364.99s`.

## Earlier supporting evidence

Already completed before the final Tier 2 pass:

- Selected-session historical replay: passed.
- Broad selected-session serious offline replay: passed.
- Broad scanner-density replay: passed.
- Scanner research/runtime parity: passed with zero differences.
- Historical freeze engineering evidence: approved.
- Dry-run safety evidence: previously clean.
- Full pre-paper gate after initial Tier 2 work: passed, then rerun again after lifecycle-state export.

## Paper-trading readiness assessment

The system is now in a condition where a controlled paper-trading trial can be considered.

This is not approval to run paper trading by default.

Required before paper runtime starts:

1. Operator approves the exact paper-trading command.
2. Operator confirms runtime profile/config path.
3. Operator confirms database/output paths.
4. Operator confirms account/broker mode is paper-only.
5. Operator confirms kill-switch and stop criteria.
6. Operator confirms monitoring/reporting expectations for the first paper run.
7. Operator confirms that no live broker order path is enabled.

## Allowed now

Allowed with normal engineering caution:

- Offline replay and qualification reruns.
- Paper-trading runbook preparation.
- Paper-trading dry-run/preflight command checks.
- Final operator approval packet for the first controlled paper trial.

Allowed only after explicit operator approval:

- Controlled paper-trading trial.

Still prohibited:

- Live trading.
- Real broker orders.
- Production deployment actions.
- Destructive database changes.
- Any `.env`-controlled hidden strategy behaviour.

## Recommendation

Proceed next with a paper-trading runbook and command preflight, not immediate execution.

The next work should define the exact command, runtime profile, database paths, report paths, expected outputs, stop criteria, and first-run observation checklist. Once that is reviewed, the operator can approve or reject the actual paper-trading command.
