# Swing Machine v0.1 decision-density review

Date: 2026-05-06
Run ID: `20260506T124131Z`
Baseline: `swing_machine_v0_1`
Diagnostic artifact: `reports/swing_machine_v0_1/historical_broad_decision_density_diagnostics_20260506T124131Z.json`

## Question

Why did the broad historical serious offline run span 2024-06-03 to 2025-07-31 but emit only 16 decision traces and 2 setups?

## Finding

The current `run-historical-replay` path is a selected-session machinery replay, not a dense day-by-day scanner replay.

It uses the full historical panel as feature/lookback input, but it selects only one signal session and one next execution session for material decisions:

- Signal session: `2025-07-30`
- Next execution/fill session: `2025-07-31`
- Active symbol rows on signal session: 16
- Decision traces emitted: 16
- Valid setups emitted: 2

## Evidence

The broad manifest contains:

- Full panel start: `2023-01-20`
- Full panel end: `2025-07-31`
- Replay start: `2024-06-03`
- Replay end: `2025-07-31`
- Full panel sessions: 634
- Replay-window sessions: 291
- Symbols: 16
- OHLCV rows: 10,144

The replay summary contains:

- `signal_session`: `2025-07-30`
- `next_session`: `2025-07-31`
- `decision_trace_count`: 16
- `setup_count`: 2
- `rejected_decision_count`: 14
- `validation_status`: `PASS`
- `reconciliation_status`: `PASS`

The baseline package contains:

- `candidate_count`: 16
- `signal_count`: 2
- `risk_plan_count`: 2
- `order_plan_count`: 2

The parity report passed with zero differences.

## Root cause

The replay implementation does this:

- Loads and validates the whole manifest-backed historical panel.
- Applies the manifest replay window to get replay sessions.
- Chooses `sessions[-2]` as the signal session.
- Chooses `sessions[-1]` as the next execution/fill session.
- Scores/detects setups over the full feature panel.
- Builds decision traces only for the selected signal session.
- Builds candidates only for the selected signal session.
- Builds setups, signals, risk plans, order plans, shadow/paper cycle inputs, backtest reconciliation, and audit evidence only for that selected signal session plus next session.

That explains the exact count:

- 16 traces = one trace per active symbol on `2025-07-30`.
- 2 setups = AAPL and AMZN were valid setups on `2025-07-30`.

## Qualification meaning

The broad run is valid evidence for:

- Historical panel loading and validation.
- Feature/lookback availability across a broad panel.
- Selected-session candidate/signal/risk/order package generation.
- Shadow/paper audit machinery in offline replay mode.
- Research/runtime-compatible package parity.
- Dry-run safety around an offline replay path.

The broad run is not valid evidence for:

- Day-by-day historical scanning across all 291 replay sessions.
- Multi-day portfolio state evolution across the whole historical window.
- Session-by-session candidate density, rejection density, setup frequency, or exposure evolution.
- Paper/live runtime readiness.

## Recommendation

Keep the selected-session replay path unchanged because it is now useful, deterministic, and qualified.

Add a separate multi-session scanner qualification mode that iterates the replay window day by day and emits density metrics. This should be a new command/path, not a mutation of `run-historical-replay` semantics.

## Implementation follow-up

`SWING-V01-114` added scanner replay contracts after this review. The next implementation slice is `SWING-V01-115`, which should extract reusable selected-session internals while preserving the existing `run-historical-replay` command semantics.
