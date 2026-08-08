# Swing Machine v0.1 Benchmark-Relative Feature Design

Date: 2026-05-07

Status: design complete; implementation not enabled in strategy behavior.

Paper/live status: blocked.

## Why this design exists

The frozen broad baseline and the first `PULLBACK`-only revision failed paper-trading qualification because they did not prove benchmark-relative edge.

The accepted-versus-near-miss report shows that accepted candidates have some forward-return separation versus scored rejected near-misses:

- Accepted rows: 51.
- Near-miss rows: 585.
- Accepted average 20-session forward close return: 1.0460%.
- Near-miss average 20-session forward close return: 0.5414%.
- Accepted 20-session positive-rate: 54.90%.
- Near-miss 20-session positive-rate: 49.33%.

That is useful evidence, but it does not yet translate into benchmark-beating lifecycle performance. The next feature work should therefore focus on making the candidate model explicitly benchmark-relative and regime-aware before any new profile is promoted.

## Current implementation state

Current feature layer:

- `src/swingmachine/features.py` computes `rs_vs_benchmark_126` when a benchmark total-return close index is provided.
- `src/swingmachine/features.py` computes trend, momentum, pullback, ATR, range compression, volume, and distance-to-52-week-high fields.
- `src/swingmachine/regime.py` computes benchmark-level trend, distance above MA200, realized volatility, panic/rebound state, and breadth-aware regime state.
- `src/swingmachine/signals.py` includes `rs_vs_benchmark_126` in the cross-sectional score.
- `src/swingmachine/signals.py` uses regime-derived score and trend thresholds.

Current gap:

- The candidate score has only one benchmark-relative feature, `rs_vs_benchmark_126`.
- There is no short/intermediate relative-strength stack.
- Regime state changes thresholds, but candidate rows do not carry a richer benchmark-regime feature snapshot for research attribution.
- There is no explicit feature explaining whether a candidate is outperforming SPY during the exact intended swing holding horizon.
- Existing performance reports compare final strategy return to SPY, but signal features do not yet directly optimise for benchmark-relative opportunity quality.

## Design principles

1. Compute features first, gate later.
2. Keep all new behavior disabled until evidence supports promotion.
3. Do not add `.env` strategy controls.
4. Keep research/runtime feature definitions shared.
5. Preserve the frozen baseline config and behavior.
6. Use attribution reports to prove that new features separate outcomes before running revised profiles.
7. Compare all revised candidates to SPY, frozen baseline, and PULLBACK-only.

## Target feature groups

### 1. Multi-window relative strength versus benchmark

Add candidate-level fields:

- `rs_vs_benchmark_20`
- `rs_vs_benchmark_50`
- `rs_vs_benchmark_100`
- `rs_vs_benchmark_126`

Definition:

`symbol_return_N - benchmark_return_N` over the same session-aligned total-return close series.

Purpose:

- `20`: intended swing-horizon momentum confirmation.
- `50`: intermediate momentum confirmation.
- `100` and `126`: trend persistence and existing baseline continuity.

### 2. Relative-strength acceleration

Add candidate-level fields:

- `rs_acceleration_20_vs_100`
- `rs_acceleration_50_vs_126`

Definition:

- `rs_acceleration_20_vs_100 = rs_vs_benchmark_20 - rs_vs_benchmark_100`
- `rs_acceleration_50_vs_126 = rs_vs_benchmark_50 - rs_vs_benchmark_126`

Purpose:

Detect symbols whose relative strength is improving, not only already strong.

### 3. Benchmark regime snapshot on candidate rows

Carry the existing regime context into attribution-ready candidate rows:

- `benchmark_dist_above_ma200`
- `benchmark_ma200_slope_pct20`
- `benchmark_realized_vol_20`
- `benchmark_regime_state`
- `benchmark_breadth_pct_above_ma200`

Purpose:

Allow outcome attribution by market backdrop and prevent hidden coupling between signals and external regime logic.

### 4. Benchmark-relative drawdown and recovery quality

Add candidate-level fields:

- `symbol_drawdown_63`
- `benchmark_drawdown_63`
- `relative_drawdown_63`
- `relative_rebound_20`

Definitions:

- `symbol_drawdown_63 = close / rolling_63_session_high - 1`
- `benchmark_drawdown_63 = benchmark_close / benchmark_rolling_63_session_high - 1`
- `relative_drawdown_63 = symbol_drawdown_63 - benchmark_drawdown_63`
- `relative_rebound_20 = symbol_return_20 - benchmark_return_20`

Purpose:

Distinguish resilient pullbacks from market-wide weakness.

### 5. Candidate outcome attribution fields

Extend future attribution datasets to include:

- All new benchmark-relative fields.
- Score-bucket membership.
- Regime bucket.
- Forward excess returns versus SPY for 1, 5, 10, and 20 sessions.

Purpose:

The next research question should become: do accepted candidates outperform near-misses in excess-return terms, not just raw forward returns?

## Config/profile design

New feature computation fields should be configured explicitly under a future profile section such as:

```yaml
benchmark_relative_features:
  enabled: false
  benchmark_symbol: SPY
  relative_strength_windows: [20, 50, 100, 126]
  acceleration_pairs:
    - short_window: 20
      long_window: 100
    - short_window: 50
      long_window: 126
  drawdown_window: 63
  rebound_window: 20
```

Initial implementation should compute and report these fields, but not change eligibility, scoring, ranking, risk, or exits.

Only after attribution evidence is positive should a separate explicit revision profile enable any scoring or gating use.

## Scoring and gating non-change

This design does not immediately change:

- `rankable` hard gates.
- Candidate score weights.
- Pattern priority.
- PULLBACK or TIGHT_BASE setup logic.
- Risk sizing.
- Portfolio constraints.
- Entry or exit lifecycle.

Any future scoring/gating use must be a separate backlog item with tests and offline qualification.

## Research acceptance criteria

Before a revised profile can use these features:

- Feature formulas have unit tests.
- Feature output is present in both research and runtime candidate snapshots.
- Feature/outcome attribution includes raw and excess forward returns.
- Accepted candidates show better excess-return separation than near-misses.
- Score buckets show monotonic or defensible outcome separation.
- Provider comparison remains acceptable on the matched window.
- Broad Alpaca data-quality warnings are carried into interpretation.

## Build sequence

1. Add explicit config contract for benchmark-relative feature computation, default disabled for behavior.
2. Implement feature formulas in `features.py` with unit tests.
3. Extend prepared feature manifests and data contracts to include new optional fields.
4. Extend feature/outcome attribution to include forward excess returns versus SPY.
5. Build benchmark/regime bucket research reports.
6. Produce a controlled candidate-selection packet before creating any new revision profile.
7. Only then run a revised offline profile comparison.

## Non-goals

- No paper trading.
- No live trading.
- No hidden environment-driven strategy behavior.
- No threshold search against the broad slice.
- No immediate promotion of benchmark-relative scoring.
- No replacement of lifecycle/risk/exits in this feature design task.
