# Swing Machine v0.1 Post-Qualification Research Plan

## Status

Date: 2026-05-07

Current paper/live status: blocked.

Current serious-run status: offline historical research only.

This document exists because the frozen `swing_machine_v0_1` baseline and the first controlled `PULLBACK`-only revision are mechanically usable but do not yet prove market edge.

## Current evidence summary

The frozen broad historical baseline completed the scanner, lifecycle, attributed performance, provider-comparison, and qualification packet stages.

Key result:

- Frozen baseline total return: -0.0872%.
- Frozen baseline SPY benchmark return: 21.6229%.
- Frozen baseline excess return: -21.7101%.
- Frozen baseline closed trades: 9.
- Frozen baseline paper decision: blocked.

Pattern attribution:

- `PULLBACK`: 4 closed trades, 3 winners, net PnL 633.99.
- `TIGHT_BASE`: 5 closed trades, 0 winners, net PnL -721.16.

The controlled `PULLBACK`-only revision improved the frozen baseline but still failed benchmark and confidence requirements.

Key result:

- PULLBACK-only total return: 0.0448%.
- PULLBACK-only SPY benchmark return: 21.6229%.
- PULLBACK-only excess return: -21.5781%.
- PULLBACK-only closed trades: 6.
- PULLBACK-only paper decision: blocked.

## Interpretation

The engine is much closer to mechanically complete than it was at the start of the programme, but edge is not proven.

The current problem is no longer mainly missing contracts, lifecycle plumbing, or reporting. The current problem is that the baseline signal model is not producing enough benchmark-relative return or enough trade evidence to justify paper trading.

This means the next workstream should be research-governed alpha development, not paper execution.

## Research principles

1. Keep the frozen baseline unchanged.
2. Treat every revised profile as a named offline candidate.
3. Do not tune thresholds by repeated broad-slice backtest iteration.
4. Separate mechanical bugs from weak strategy hypotheses.
5. Compare every candidate to SPY and to the frozen baseline.
6. Require enough trades to make the evidence useful.
7. Use provider comparison where data coverage allows it.
8. Record rejected hypotheses and why they were rejected.
9. Do not promote anything to paper unless qualification evidence changes materially.

## Primary research questions

1. Is the low trade count caused by overly narrow candidate generation, overly restrictive gates, or limited historical data coverage?
2. Are accepted signals materially better than rejected near-miss candidates?
3. Are current features explaining future returns, or only describing chart shapes?
4. Does the strategy need benchmark-relative regime filters before it can compete with buy-and-hold SPY?
5. Does `PULLBACK` contain a real signal that can be widened safely without weakening quality?
6. Is `TIGHT_BASE` structurally weak, or does it need a materially different entry/exit model?
7. Do exits and risk rules truncate winners or allow avoidable losers?
8. Are data-provider differences small enough across the intended broad window?

## Immediate research tranche

### 1. Broad Hugging Face data feasibility

Goal: determine whether the Hugging Face dataset can support the same broad Alpaca historical window used for the failed baseline qualification.

Output:

- Data coverage report.
- Candidate matching symbol/date universe.
- Decision on whether to build a matching broad Hugging Face manifest.

### 2. Historical data quality and survivorship audit

Goal: identify whether current historical inputs create misleading evidence.

Check:

- Missing bars by symbol/date.
- Duplicate bars.
- Suspicious zero volume rows.
- Corporate-action adjusted price consistency where available.
- Symbol coverage gaps.
- Benchmark coverage alignment.

### 3. Feature outcome attribution dataset

Goal: create a reusable offline research table connecting candidate features to later realized outcomes.

Required rows:

- Candidate identity.
- Pattern type.
- Feature snapshot.
- Eligibility result.
- Rejection reasons.
- Quality score.
- Rank.
- Planned risk.
- Forward return windows.
- Lifecycle outcome if traded.

### 4. Accepted versus near-miss analysis

Goal: determine whether eligibility gates and scoring separate better candidates from worse candidates.

Output:

- Accepted candidate forward-return distribution.
- Rejected near-miss forward-return distribution.
- Gate-by-gate rejection analysis.
- Score-decile outcome analysis.

### 5. Benchmark-relative and regime-feature design

Goal: define features that measure whether a candidate is strong relative to SPY and its own recent behavior.

Examples:

- Relative strength versus SPY over 20, 50, and 100 bars.
- Trend regime of SPY.
- Candidate volatility regime.
- Breakout/pullback quality relative to prior range.
- Volume confirmation relative to recent symbol history.

### 6. Controlled candidate selection packet

Goal: choose one or two defensible revised candidates only after the above evidence exists.

The selection packet must state:

- Hypothesis.
- Evidence supporting it.
- Exact profile/config changes.
- Acceptance gates.
- Rejection gates.
- Why it is not an ad hoc curve-fit.

## Candidate promotion gates

A revised candidate cannot move to paper unless all of these are true:

- Scanner replay passes.
- Lifecycle replay passes.
- Attributed performance report passes.
- Benchmark comparison is materially improved.
- Trade count is high enough to support a useful conclusion.
- Provider comparison passes where matching data exists.
- No hidden `.env` strategy behavior is introduced.
- Decision packet explicitly recommends paper as the next controlled step.

## Current non-goals

- No live trading.
- No paper trading.
- No broker integration changes.
- No threshold grid search against the broad qualification slice.
- No promotion of `PULLBACK`-only based only on slight positive return.
- No resurrection of `TIGHT_BASE` without a defensible evidence packet.

## Near-term decision rule

If broad Hugging Face data cannot cover the same historical window, continue using Alpaca broad data for primary research and use Hugging Face only for matched shorter-window contract checks.

If feature/outcome attribution shows no meaningful separation between accepted and rejected candidates, stop revising thresholds and redesign the signal features before running new profile variants.

If a revised candidate improves return but still materially underperforms SPY, keep paper trading blocked.
