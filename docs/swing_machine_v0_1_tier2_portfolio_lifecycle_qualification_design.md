# Swing Machine v0.1 Tier 2 portfolio/lifecycle qualification design

Date: 2026-05-06
Baseline: `swing_machine_v0_1`
Status: design decision complete, implementation not started

## Decision

Tier 2 portfolio/lifecycle simulation qualification is required before any paper/live runtime move.

The broad Tier 1 scanner-density qualification is now passed, but it is deliberately stateless. It proves that the machine can scan every eligible historical signal session and produce dense candidate/setup/rejection evidence with research/runtime parity. It does not prove multi-day portfolio state evolution.

Paper trading should remain deferred until Tier 2 qualification and a thorough pre-paper test suite both pass.

## Current qualified evidence

The current qualification stack is:

- Selected-session historical replay: passed.
- Broad selected-session serious offline replay: passed.
- Broad scanner-density replay: passed.
- Scanner research/runtime parity: passed with zero differences.
- Unit/contract certification: passed in focused shards.
- Operator evidence approval: recorded.

The remaining gap is stateful multi-day lifecycle qualification.

## Existing code that Tier 2 should build on

The repository already has useful stateful machinery:

- `src/swingmachine/backtest.py`
  - Carries cash, active positions, pending entries, exit pending state, equity curve, trades, events, and spent setup IDs.
  - Uses `simulate_entry_fill` and `simulate_stop_fill` from the execution model.
  - Uses `evaluate_exit_position` for trailing stop, time stop, and earnings exit decisions.
  - Uses `evaluate_pending_entry` and `classify_symbol_state` for entry lifecycle state.

- `src/swingmachine/lifecycle.py`
  - Defines symbol state classification.
  - Handles pending entry expiry/cancellation logic.
  - Handles post-cancel state resolution.
  - Guards impossible state combinations such as active plus pending entry.

- `src/swingmachine/exits.py`
  - Defines trailing stop activation/update.
  - Defines time-stop and earnings-exit triggers.
  - Produces exit evaluation decisions.

- `src/swingmachine/replay.py`
  - Now has selected-session replay, scanner-density replay, and scanner parity.
  - Tier 2 should not overload scanner-density semantics. It should add a portfolio/lifecycle qualification path.

## Tier 2 purpose

Tier 2 should answer:

- Can the swing machine evolve pending orders, active positions, stops, exits, cash, equity, and portfolio constraints across a historical replay window?
- Can it explain each lifecycle transition?
- Can research and runtime-compatible paths reproduce the same lifecycle outputs?
- Can the system produce enough evidence to justify a controlled paper-trading trial later?

## Non-goals

Tier 2 should not optimize strategy performance.

Tier 2 should not introduce new strategy variants.

Tier 2 should not execute live trading, real broker orders, production deployment actions, or destructive database changes.

Tier 2 should not use `.env` to change strategy behaviour.

Tier 2 should not replace the existing selected-session replay or scanner-density paths.

## Target command

Recommended command name:

```bash
run-historical-portfolio-lifecycle-replay
```

The command should be offline and artifact-only.

Required inputs:

- Historical panel manifest.
- Explicit baseline config/profile.
- Output directory.
- Initial equity.
- Optional selected-period plan reference for reporting.

Required safety behaviour:

- Default local SQLite database under the output directory only.
- No broker adapters that submit real orders.
- No production database writes.
- No live/paper runtime execution mode.
- Non-zero exit on validation or reconciliation failure.

## Target simulation semantics

Tier 2 should use a broad manifest replay window and process sessions in chronological order.

For each session:

- Compute candidate/setup state from the prepared/detected frame.
- Manage pending entry intents from earlier sessions.
- Simulate next-session fills using historical OHLCV.
- Create active positions for filled entries.
- Update stops and highest-high progress for active positions.
- Evaluate stop exits, time exits, earnings exits, and invalidation exits.
- Update cash/equity.
- Record portfolio heat and sector exposure.
- Track spent setup IDs to prevent hidden setup reuse.
- Emit lifecycle events and state snapshots.

## Required typed outputs

Add or extend typed contracts for:

- `HistoricalPortfolioLifecycleReplaySummary`
- `HistoricalPortfolioLifecycleSessionState`
- `HistoricalPortfolioLifecycleTransition`
- `HistoricalPortfolioLifecyclePositionSnapshot`
- `HistoricalPortfolioLifecyclePendingOrderSnapshot`
- `HistoricalPortfolioLifecycleExposureSnapshot`
- `HistoricalPortfolioLifecycleReconciliation`
- `HistoricalPortfolioLifecycleArtifactManifest`

Minimum lifecycle transition fields:

- `transition_id`
- `symbol`
- `session_date`
- `from_state`
- `to_state`
- `trigger`
- `setup_id`
- `order_intent_id`
- `position_id`
- `reason_codes`
- `evidence`
- `config_hash`

Minimum session state fields:

- `session_date`
- `cash`
- `equity`
- `open_position_count`
- `pending_entry_count`
- `exit_pending_count`
- `portfolio_heat`
- `daily_new_risk`
- `sector_exposure`
- `candidate_count`
- `setup_count`
- `entry_submitted_count`
- `entry_filled_count`
- `entry_cancelled_count`
- `exit_submitted_count`
- `exit_filled_count`
- `stop_updated_count`
- `blocked_reason_counts`

## Required artifacts

A Tier 2 run should emit:

- `portfolio_lifecycle_replay_summary.json`
- `portfolio_lifecycle_session_states.json`
- `portfolio_lifecycle_transitions.json`
- `portfolio_lifecycle_positions.json`
- `portfolio_lifecycle_pending_orders.json`
- `portfolio_lifecycle_exposure.json`
- `portfolio_lifecycle_reconciliation.json`
- `portfolio_lifecycle_baseline_package.json`
- `portfolio_lifecycle_artifact_manifest.json`
- `portfolio_lifecycle_parity_report.json` when paired lanes are compared

## Reconciliation checks

Tier 2 must reconcile:

- Pending entries plus active positions never coexist for the same symbol unless explicitly supported later.
- Exit pending never exists without an active position.
- Cash plus marked-to-market positions equals reported equity within tolerance.
- Filled entries create active positions exactly once.
- Cancelled pending entries mark setup IDs spent where configured.
- Closed positions create exactly one trade record.
- Stop exits, time exits, and earnings exits have explicit transition reasons.
- Exposure snapshots match positions and pending plans.
- Portfolio heat and sector exposure do not silently exceed configured constraints.
- Research/runtime-compatible lifecycle outputs match under parity.

## Testing policy before paper trading

The user explicitly accepts long test runs before paper trading. Therefore the pre-paper gate should be thorough rather than artificially constrained to 30 minutes.

Minimum pre-paper test gate:

- Full `ruff check` over source/tests.
- Full `pytest` suite, not only focused shards.
- Selected-session replay tests.
- Scanner-density tests.
- Portfolio/lifecycle simulation tests after Tier 2 exists.
- Broad historical selected-session replay evidence remains clean.
- Broad scanner-density qualification remains clean.
- Tier 2 broad portfolio/lifecycle qualification passes.
- Research/runtime parity passes for scanner and lifecycle packages.
- Dry-run safety report remains clean.
- Freeze/readiness artifact is rebuilt after Tier 2 evidence.

Recommended execution policy:

- Use long but bounded timeouts, for example 4 hours for the full pre-paper gate.
- Run expensive historical qualifications sequentially, not in parallel.
- Store all outputs under `reports/swing_machine_v0_1/` with run IDs.
- Treat any timeout as a blocker requiring either optimization or explicit operator acceptance.

## Paper-trading gate

Paper trading should remain blocked until all are true:

- Tier 2 design is implemented.
- Tier 2 broad historical lifecycle qualification passes.
- Tier 2 research/runtime-compatible parity passes.
- Full pre-paper test gate passes.
- Safety checks prove no live trading or real broker orders are triggered by qualification commands.
- Operator explicitly approves a paper-trading trial.
- A separate paper-trading runbook exists with kill switch, output paths, rollback/stop criteria, and monitoring expectations.

## Implementation sequence

1. Add Tier 2 lifecycle replay contracts.
2. Add lifecycle artifact schema tests.
3. Extract state snapshots from existing `run_backtest` outputs where sufficient.
4. Add a first lifecycle qualification builder over `BacktestResult`.
5. Emit lifecycle session states, transitions, positions, pending-order snapshots, and exposure snapshots.
6. Add lifecycle reconciliation checks.
7. Add lifecycle parity report.
8. Add guarded offline CLI `run-historical-portfolio-lifecycle-replay`.
9. Run fixture lifecycle qualification.
10. Run broad historical lifecycle qualification.
11. Run full pre-paper test gate.
12. Rebuild readiness and produce a paper-trading review packet.

## Current recommendation

Proceed with Tier 2 implementation next, starting with typed contracts and artifact schemas.

Do not move to paper trading yet.
