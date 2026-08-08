# Swing Machine v0.1 mechanical readiness completion design

Date: 2026-05-07
Baseline: `swing_machine_v0_1`
Status: design/backlog checkpoint, not implementation approval

## Executive position

The swing machine is much more mechanically ready than when the review began, but it is not yet at the standard required for serious paper trading or historical performance qualification.

Current strengths:

- Explicit baseline profile and strategy config exist.
- Historical data manifests and validation exist.
- Scanner-density replay exists.
- Stateful lifecycle replay exists.
- Tier 2 lifecycle artifacts now include pending-order and position snapshots.
- Research/runtime-compatible lifecycle parity is clean on the broad historical panel.
- Full test suite currently passes.
- Paper runbook exists but has not been executed.

Remaining mechanical gap:

- We have not yet frozen a final engine contract and readiness checklist.
- Runtime cycle input is still manually assembled rather than produced by a controlled signal-to-cycle package builder.
- Paper run workflow is not yet fully preflighted end-to-end with a real reviewed cycle input.
- Data provenance, feature availability, and lookahead-bias guards need stronger formal evidence before performance qualification.
- Order/risk/lifecycle explainability exists in pieces, but not as one unified end-to-end decision ledger.
- Observability for first paper-like cycles is not yet at operator-grade standard.
- Qualification gates exist, but are not yet bundled into one repeatable command/report that says `MECHANICALLY_READY` or `BLOCKED`.

## Target mechanical standard

The target is not merely that tests pass. The target is that another engineer/operator can look at one readiness packet and understand:

- What data was used.
- What config/profile was active.
- What symbols were eligible.
- What features were available at each decision point.
- Why each candidate was accepted or rejected.
- How entries were ranked.
- How risk was sized.
- What order would be planned.
- How pending entries, fills, cancels, positions, stops, exits, and cash/equity evolved.
- Whether research/runtime-compatible paths matched.
- Whether any live/paper broker path could be reached accidentally.
- Whether the engine is fit for historical profitability qualification.

## Mechanical readiness categories

### 1. Data integrity and provenance

Required state:

- Every historical run references a manifest.
- Manifest files include source identity, date range, row counts, hashes, replay window, feature coverage scope, and provider notes.
- Feature rows must be point-in-time compatible with the signal session.
- Symbol reference/tradability windows must be enforced.
- Corporate actions, split adjustment, and earnings availability assumptions must be explicit.

Remaining work:

- Add a mechanical readiness report section summarising data provenance and point-in-time checks.
- Add explicit lookahead-bias checks for features and session windows.
- Add a data contract fingerprint into performance/lifecycle reports.

### 2. Config and profile control

Required state:

- Strategy behaviour must come from explicit config/profile files.
- `.env` may only control infrastructure such as credentials, paths, and safe operational switches.
- Every run must record config hash, config path, profile alias, and baseline id.

Remaining work:

- Add a config lock/readiness report proving no strategy behaviour is pulled from `.env`.
- Add a single active baseline manifest package for the latest qualified engine.

### 3. Candidate and signal generation

Required state:

- Candidate generation must be deterministic.
- Rejection reasons must be complete.
- Scoring/ranking must be deterministic and explainable.
- Scanner-density replay must produce sufficient decision breadth.

Current evidence:

- Broad scanner qualification previously passed with zero parity differences.
- Candidate/setup/rejection density exists.

Remaining work:

- Bundle scanner evidence into the final mechanical readiness report.
- Add a top-N reviewed candidate ledger for a representative run.

### 4. Risk and portfolio mechanics

Required state:

- Risk per trade must be explicit.
- Daily new risk and portfolio heat must be tracked.
- Sector exposure and symbol duplication must be guarded.
- Rejected entries must explain risk/portfolio blocks.

Remaining work:

- Add a risk/portfolio audit report derived from lifecycle artifacts.
- Add tests for portfolio heat, sector cap, duplicate symbol, and pending/open conflict behaviour across lifecycle replay.

### 5. Order planning and lifecycle mechanics

Required state:

- Entry intents, pending orders, fills, cancellations, active positions, stop updates, exits, and closed trades must be represented as typed artifacts.
- Lifecycle transitions must reconcile with equity, cash, pending orders, positions, and trades.

Current evidence:

- Broad lifecycle run `20260507T065158Z` passed.
- It produced 712 pending-order snapshots and 1080 position snapshots.
- Reconciliation warnings and failures were zero.

Remaining work:

- Add an end-to-end lifecycle decision ledger that joins candidate, signal, risk plan, order plan, transition, position, and trade evidence by symbol/setup/session.
- Add additional adversarial fixture tests for expiry, cancellation, stop hit, time exit, earnings exit, and portfolio block scenarios.

### 6. Runtime and paper safety

Required state:

- Paper mode must be explicit.
- Shadow preview must precede paper execution.
- Local database/output paths must be explicit.
- Live trading must remain unreachable.
- First paper cycle must be a single reviewed cycle, not an unattended scheduler.

Remaining work:

- Build first paper `cycle_input.yaml` package.
- Run shadow preview only.
- Review shadow preview against expected setups.
- Require operator approval before `--mode PAPER`.

### 7. Observability and reporting

Required state:

- Every qualification run should emit a report package with config, data, candidates, rejections, signals, risk, orders, lifecycle, parity, tests, and blockers.
- Operator should not need to inspect raw JSON manually to decide readiness.

Remaining work:

- Build a consolidated `mechanical_readiness_report.json` and human-readable markdown summary.
- Add readiness decision values: `PASS`, `WARN`, `BLOCK`.
- Include residual risks and required approvals.

### 8. Test and qualification gate

Required state:

- Full ruff and full pytest pass.
- Broad scanner parity passes.
- Broad lifecycle parity passes.
- Dry-run safety passes.
- First-cycle shadow preview passes before any paper action.

Remaining work:

- Create one repeatable mechanical readiness gate that indexes the latest evidence and returns a single readiness decision.
- Re-run after any code/config change before performance qualification or paper execution.

## Mechanical readiness definition of done

The engine can be called mechanically ready when all are true:

- Data manifest validation passes.
- Lookahead-bias checks pass.
- Explicit config/profile lock passes.
- Scanner-density broad qualification passes.
- Lifecycle broad qualification passes.
- Candidate/signal/risk/order/lifecycle ledger is complete.
- Risk/portfolio audit passes.
- Full test gate passes.
- Dry-run safety passes.
- First shadow preview package can be produced and reviewed.
- Mechanical readiness report says `PASS`.
- Paper/live execution remains operator-gated.

## Recommendation

Do not move to historical profitability qualification until the remaining mechanical readiness items are closed or explicitly accepted as non-blocking.

The most important next step is to create the consolidated mechanical readiness report and close lifecycle/risk adversarial fixture coverage. That gives us confidence that any later profitability result is measuring the intended engine, not an accidental implementation artifact.
