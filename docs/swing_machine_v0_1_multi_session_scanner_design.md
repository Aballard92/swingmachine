# Swing Machine v0.1 multi-session scanner qualification design

Date: 2026-05-06
Baseline: `swing_machine_v0_1`
Status: design ready, implementation not started

## Purpose

Add a true multi-session historical scanner qualification mode for `swing_machine_v0_1` before any paper/live runtime move.

The existing selected-session replay proves that a single signal session can produce deterministic candidates, signals, risk plans, order plans, shadow/paper audit evidence, and research/runtime-compatible parity. It does not prove that the machine scans every historical session in a broad window.

## Design decision

Create a new scanner replay path rather than changing `run-historical-replay`.

Reason:

- The existing replay path is qualified and deterministic.
- Existing selected-period artifacts depend on its selected-session semantics.
- Scanner semantics have different output volume, runtime cost, state handling, and qualification criteria.
- A new path avoids corrupting the approved freeze evidence.

Recommended command name:

```bash
run-historical-scanner-replay
```

## Target behaviour

For a manifest with `replay_start_session` and `replay_end_session`, the scanner replay should:

- Load and validate the full historical panel once.
- Build or load feature definitions once where safe.
- Determine ordered replay sessions inside the manifest replay window.
- Iterate each eligible signal session where a following execution session exists.
- For each signal session, use the next replay session as the execution/fill session.
- Score candidates for the signal session.
- Detect setups for the signal session.
- Build candidate, signal, risk-plan, and order-plan artifacts for that session.
- Run offline backtest/shadow/paper comparison for that session without broker execution.
- Track lifecycle state across sessions if the mode is promoted from scanner-density to portfolio simulation.
- Emit per-session and aggregate decision-density metrics.

## Initial mode boundaries

Build this in two tiers.

Tier 1: scanner-density qualification

- Stateless per-session scan.
- No portfolio carry-forward across sessions beyond per-session planning constraints.
- No live/paper broker execution.
- Main outputs are decision density, setup density, rejection density, and package parity.
- Suitable as the next safe implementation step.

Tier 2: portfolio/lifecycle simulation

- Carries open positions, pending orders, exits, stops, targets, and time exits across sessions.
- Requires stronger lifecycle contracts and more careful reconciliation.
- Should not be built until Tier 1 passes.

## Core contracts

Add typed contracts when implementing:

- `HistoricalScannerReplaySessionResult`
- `HistoricalScannerReplaySummary`
- `HistoricalScannerReplayDensityMetrics`
- `HistoricalScannerReplayStateSnapshot`
- `HistoricalScannerReplayArtifactManifest`

Minimum session-result fields:

- `panel_id`
- `signal_session`
- `next_session`
- `symbol_count`
- `decision_trace_count`
- `candidate_count`
- `accepted_setup_count`
- `rejected_decision_count`
- `signal_count`
- `risk_plan_count`
- `order_plan_count`
- `backtest_event_count`
- `shadow_proposal_count`
- `paper_submission_count`
- `validation_status`
- `reconciliation_status`
- `status`
- `reason_counts`

Minimum aggregate fields:

- `eligible_signal_session_count`
- `processed_signal_session_count`
- `skipped_session_count`
- `total_decision_traces`
- `total_candidates`
- `total_setups`
- `total_rejections`
- `sessions_with_setups`
- `sessions_without_setups`
- `average_candidates_per_session`
- `average_setups_per_session`
- `max_setups_per_session`
- `parity_difference_count`
- `status`

## Artifacts

A scanner replay run should emit:

- `scanner_replay_summary.json`
- `scanner_session_results.json`
- `scanner_decision_density.json`
- `scanner_rejection_reasons.json`
- `scanner_material_decisions.json`
- `scanner_baseline_report_package.json`
- `scanner_parity_report.json` when paired lanes are compared
- `scanner_runtime_events.db` or equivalent local SQLite output under the report directory

## Research/runtime parity

Scanner parity should compare aggregate and per-session outputs between research and runtime-compatible lanes.

At minimum compare:

- Processed signal sessions.
- Candidate counts by session.
- Setup counts by session.
- Accepted setup symbols by session.
- Rejection reason counts by session.
- Risk/order plan counts by session.
- Aggregate density metrics.
- Baseline package schema/version/config hash.

## Safety controls

The scanner replay must remain offline:

- No live trading.
- No real broker orders.
- No production deployment.
- No destructive database changes.
- Output must be written under an explicit report directory.
- Database URL must default to a local SQLite DB under the output directory.
- Any command that could use live/paper broker execution must require a separate explicit approval path and must not be part of this scanner command.

## Acceptance criteria for Tier 1

- A broad manifest with 291 replay sessions produces materially more than one signal session of decision-density output.
- Per-session output count equals `replay_window_session_count - 1`, excluding documented skipped sessions.
- Every processed session has symbol-level decision traces or an explicit skip reason.
- Aggregate density metrics are emitted.
- Research/runtime-compatible scanner parity passes with zero material differences on the broad historical manifest.
- Existing `run-historical-replay` selected-session tests/artifacts remain unchanged.

## Proposed implementation sequence

1. Add scanner replay contracts.
2. Extract reusable selected-session replay internals without changing public selected-session behaviour.
3. Add a scanner session iterator over manifest replay sessions.
4. Emit per-session density results without portfolio carry-forward.
5. Add scanner summary and artifact writer.
6. Add runtime CLI command `run-historical-scanner-replay`.
7. Add focused contract/unit tests for scanner session counts and artifact schema.
8. Run broad scanner replay in research and runtime-compatible lanes.
9. Generate scanner parity report.
10. Decide whether Tier 2 portfolio/lifecycle simulation is required before paper/live runtime.

## Current recommendation

Implement Tier 1 next. Do not move to paper/live runtime until Tier 1 scanner-density qualification passes and the operator reviews the decision-density report.

## Implementation progress

`SWING-V01-115` extracted selected-session replay internals into reusable private helpers while preserving `run-historical-replay` behaviour. The next implementation slice is `SWING-V01-116`, the Tier 1 stateless scanner iterator and density artifact writer.

`SWING-V01-116` and `SWING-V01-117` implemented the Tier 1 scanner iterator, density artifacts, and guarded offline CLI. The next design item to implement is `SWING-V01-118`, scanner research/runtime-compatible parity.
