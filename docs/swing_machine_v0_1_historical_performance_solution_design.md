# Swing Machine v0.1 historical performance solution design

Date: 2026-05-07
Baseline: `swing_machine_v0_1`
Status: implementation-ready design

## Purpose

Define how to measure whether `swing_machine_v0_1` has historical profitability and robustness worth taking toward paper trading.

This design covers `SWING-V01-143` through `SWING-V01-149`.

## Gating rule

Do not implement or run historical performance qualification until mechanical readiness is complete or explicitly accepted.

Historical performance must measure the frozen baseline. It must not optimize parameters or introduce strategy variants.

## Target architecture

New module:

- `performance.py`
  - Equity metrics.
  - Trade metrics.
  - Drawdowns.
  - Benchmark comparison.
  - Concentration metrics.
  - Cost sensitivity.
  - Regime/period breakdowns.
  - Performance decision engine.

Runtime CLI additions:

- `run-historical-performance-qualification`
- `compare-performance-providers`

Report outputs under:

- `reports/swing_machine_v0_1/historical_performance_<RUN_ID>/`

## New CLI commands

### `run-historical-performance-qualification`

Proposed signature:

```bash
.venv/bin/swingmachine run-historical-performance-qualification \
  --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml \
  --config swing_trading_bot_config_template_v2.yaml \
  --mechanical-readiness reports/.../mechanical_readiness_<RUN_ID>.json \
  --output-dir reports/swing_machine_v0_1/historical_performance_<RUN_ID> \
  --benchmark-symbol SPY \
  --initial-equity 100000
```

Required behaviour:

- Refuse to run if mechanical readiness is `BLOCK`.
- Warn or refuse if mechanical readiness is missing depending on strict mode.
- Run the existing stateful backtest with the explicit baseline config.
- Emit performance artifacts.
- Do not tune strategy parameters.
- Do not execute paper/live orders.

### `compare-performance-providers`

Proposed signature:

```bash
.venv/bin/swingmachine compare-performance-providers \
  --left-performance reports/.../alpaca_performance/historical_performance_summary.json \
  --right-performance reports/.../huggingface_performance/historical_performance_summary.json \
  --output reports/swing_machine_v0_1/provider_performance_comparison_<RUN_ID>.json
```

Required behaviour:

- Compare return, drawdown, trade count, symbols, setup ids, and missing data effects.
- Report provider drift.
- Do not hide differences.

## Typed contracts

### HistoricalPerformanceSummary

Fields:

- `baseline_id: str`
- `run_id: str`
- `panel_id: str`
- `manifest_path: str`
- `config_hash: str`
- `generated_at: datetime`
- `status: ReviewStatus`
- `decision: Literal["PASS_FOR_PAPER_CONSIDERATION", "WARN_RESEARCH_REQUIRED", "BLOCK_PAPER_TRADING"]`
- `initial_equity: float`
- `final_equity: float`
- `total_return: float`
- `cagr: float | None`
- `annualized_volatility: float | None`
- `sharpe_ratio: float | None`
- `sortino_ratio: float | None`
- `max_drawdown: float`
- `calmar_ratio: float | None`
- `trade_count: int`
- `benchmark_symbol: str | None`
- `benchmark_total_return: float | None`
- `excess_return_vs_benchmark: float | None`
- `blockers: tuple[str, ...]`
- `warnings: tuple[str, ...]`

### HistoricalEquityCurvePoint

Fields:

- `session_date: date`
- `equity: float`
- `cash: float`
- `open_positions: int`
- `pending_entries: int`
- `strategy_return: float | None`
- `benchmark_equity: float | None`
- `benchmark_return: float | None`
- `drawdown: float`

### HistoricalTradeMetrics

Fields:

- `trade_count: int`
- `winning_trade_count: int`
- `losing_trade_count: int`
- `win_rate: float | None`
- `average_win: float | None`
- `average_loss: float | None`
- `median_win: float | None`
- `median_loss: float | None`
- `largest_win: float | None`
- `largest_loss: float | None`
- `profit_factor: float | None`
- `expectancy_per_trade: float | None`
- `average_bars_held: float | None`
- `median_bars_held: float | None`
- `consecutive_wins_max: int`
- `consecutive_losses_max: int`
- `exit_reason_counts: dict[str, int]`

### HistoricalDrawdownRecord

Fields:

- `drawdown_id: str`
- `start_date: date`
- `trough_date: date`
- `recovery_date: date | None`
- `max_drawdown: float`
- `duration_sessions: int`
- `recovered: bool`

### HistoricalBenchmarkComparison

Fields:

- `benchmark_symbol: str`
- `start_date: date`
- `end_date: date`
- `strategy_total_return: float`
- `benchmark_total_return: float`
- `excess_return: float`
- `strategy_max_drawdown: float`
- `benchmark_max_drawdown: float`
- `strategy_volatility: float | None`
- `benchmark_volatility: float | None`
- `strategy_sharpe: float | None`
- `benchmark_sharpe: float | None`
- `status: ReviewStatus`
- `warnings: tuple[str, ...]`

### HistoricalConcentrationReport

Fields:

- `max_open_positions: int`
- `average_open_positions: float`
- `max_gross_exposure: float`
- `average_gross_exposure: float`
- `max_sector_exposure: dict[str, float]`
- `symbol_trade_counts: dict[str, int]`
- `sector_trade_counts: dict[str, int]`
- `top_symbol_trade_share: float | None`
- `top_sector_trade_share: float | None`
- `warnings: tuple[str, ...]`

### HistoricalCostSensitivityReport

Fields:

- `scenarios: tuple[HistoricalCostScenarioResult, ...]`
- `base_scenario_id: str`
- `worst_case_total_return: float | None`
- `edge_survives_high_cost: bool | None`
- `warnings: tuple[str, ...]`

### HistoricalCostScenarioResult

Fields:

- `scenario_id: str`
- `description: str`
- `total_return: float`
- `max_drawdown: float`
- `trade_count: int`
- `profit_factor: float | None`
- `expectancy_per_trade: float | None`

### HistoricalBreakdownReport

Fields:

- `breakdown_type: Literal["month", "quarter", "regime", "sector", "setup_type", "ranking_bucket"]`
- `rows: tuple[HistoricalBreakdownRow, ...]`

### HistoricalBreakdownRow

Fields:

- `bucket: str`
- `start_date: date | None`
- `end_date: date | None`
- `trade_count: int`
- `total_return: float | None`
- `net_pnl: float | None`
- `win_rate: float | None`
- `profit_factor: float | None`
- `max_drawdown: float | None`
- `low_sample_warning: bool`

### ProviderPerformanceComparison

Fields:

- `comparison_id: str`
- `left_provider: str`
- `right_provider: str`
- `status: ReviewStatus`
- `left_total_return: float`
- `right_total_return: float`
- `return_difference: float`
- `left_trade_count: int`
- `right_trade_count: int`
- `shared_trade_count: int`
- `left_only_trade_count: int`
- `right_only_trade_count: int`
- `max_drawdown_difference: float`
- `differences: tuple[ProviderPerformanceDifference, ...]`
- `warnings: tuple[str, ...]`

## Metric formulas

### Daily/session return

For equity curve point `i`:

```text
return_i = equity_i / equity_{i-1} - 1
```

First point return is `null`.

### Total return

```text
total_return = final_equity / initial_equity - 1
```

### CAGR

If elapsed calendar days >= 365:

```text
cagr = (final_equity / initial_equity) ** (365.25 / elapsed_days) - 1
```

Otherwise `null` with warning `PERIOD_TOO_SHORT_FOR_CAGR`.

### Annualized volatility

Use session returns standard deviation:

```text
annualized_volatility = std(session_returns) * sqrt(252)
```

Require at least 30 non-null returns. Otherwise `null`.

### Sharpe

Use zero risk-free rate initially:

```text
sharpe = mean(session_returns) / std(session_returns) * sqrt(252)
```

If std is zero or sample insufficient, `null`.

### Sortino

Use downside returns below zero:

```text
sortino = mean(session_returns) / std(min(return, 0)) * sqrt(252)
```

Require sufficient downside sample. Otherwise `null`.

### Drawdown

```text
running_peak = max(equity_0 ... equity_i)
drawdown_i = equity_i / running_peak - 1
max_drawdown = min(drawdown_i)
```

Drawdown records start when drawdown first goes below zero and recover when equity reaches prior peak.

### Profit factor

```text
profit_factor = sum(winning net pnl) / abs(sum(losing net pnl))
```

If no losing trades and at least one winner, use `null` plus warning `NO_LOSING_TRADES_PROFIT_FACTOR_UNBOUNDED`.

### Expectancy

```text
expectancy = average(net_pnl per trade)
```

Also include expectancy as return per trade if practical.

## Benchmark alignment

Inputs:

- Benchmark symbol selected from manifest panel if available.
- If not available, validated external benchmark file must be declared.

Rules:

- Use same start/end sessions as strategy equity curve.
- Use first available benchmark close on or after start session.
- Use last available benchmark close on or before end session.
- Missing benchmark coverage is a blocker unless benchmark comparison is explicitly disabled.

Benchmark equity:

```text
benchmark_units = initial_equity / benchmark_start_close
benchmark_equity_i = benchmark_units * benchmark_close_i
```

## Cost sensitivity design

Initial scenarios:

1. `configured_base`: current config costs.
2. `zero_cost`: remove transaction cost/friction for upper bound.
3. `high_cost`: double transaction costs.
4. `high_slippage`: increase spread/slippage assumptions if supported by config.

If the current backtest cannot rerun costs without config mutation, implement scenario configs as explicit copied config objects with changed execution-cost fields. Do not use `.env`.

## Performance decision framework

### PASS_FOR_PAPER_CONSIDERATION

Suggested minimums:

- Total return positive after base costs.
- Benchmark comparison not materially worse, or justified by lower drawdown/exposure.
- Max drawdown acceptable versus return.
- Trade count sufficient for a preliminary read.
- Profit factor above 1.
- Expectancy positive.
- No severe concentration warning.
- High-cost scenario does not completely destroy the edge.

Exact numeric thresholds should be explicit config/report parameters, not hidden constants.

### WARN_RESEARCH_REQUIRED

Any of:

- Positive but weak return.
- Too few trades.
- Profitable only in one regime/sector/window.
- Cost-sensitive edge.
- Benchmark outperforms but strategy has other possible merit.
- Provider comparison unavailable.

### BLOCK_PAPER_TRADING

Any of:

- Negative total return after costs.
- Large unacceptable drawdown.
- Profit factor below 1.
- Expectancy negative.
- Severe concentration.
- Benchmark clearly superior with similar or lower risk.
- Provider comparison shows unstable results.
- Mechanical readiness is not passed or accepted.

## Output artifacts

Directory:

```text
reports/swing_machine_v0_1/historical_performance_<RUN_ID>/
```

Files:

- `historical_performance_summary.json`
- `historical_equity_curve.json`
- `historical_trade_metrics.json`
- `historical_trade_list.json`
- `historical_drawdowns.json`
- `historical_benchmark_comparison.json`
- `historical_concentration_report.json`
- `historical_cost_sensitivity.json`
- `historical_breakdown_month.json`
- `historical_breakdown_quarter.json`
- `historical_breakdown_regime.json`
- `historical_breakdown_sector.json`
- `historical_breakdown_setup_type.json`
- `historical_breakdown_ranking_bucket.json`
- `historical_performance_manifest.json`
- `historical_performance_review.md`

## Build sequence

1. Add performance metric contracts.
2. Implement equity/drawdown/trade metric calculations with fixtures.
3. Implement benchmark comparison.
4. Implement concentration report.
5. Implement cost sensitivity scenarios.
6. Implement breakdown reports.
7. Add CLI command to run full qualification.
8. Run broad Alpaca performance qualification.
9. Add Hugging Face/provider comparison if compatible.
10. Produce performance decision packet.

## Test plan

Unit tests:

- Equity return calculations.
- CAGR short/long period handling.
- Volatility/Sharpe insufficient sample handling.
- Drawdown record extraction.
- Win/loss/profit-factor calculations.
- Consecutive win/loss calculations.
- Benchmark alignment.
- Concentration warnings.
- Cost scenario comparisons.

Contract tests:

- All performance contracts serialize to JSON.
- Invalid metric values fail where appropriate.

Smoke tests:

- Tiny fixture performance report writes all artifacts.
- Missing mechanical readiness blocks or warns as configured.

Qualification tests:

- Broad Alpaca performance run.
- Provider comparison run when Hugging Face panel is qualified.

## Acceptance for historical performance phase

The phase is complete when:

- Performance artifacts are produced from the mechanically ready baseline.
- Benchmark comparison exists.
- Cost sensitivity exists.
- Breakdown reports exist.
- Provider robustness is completed or explicitly blocked by data incompatibility.
- Final performance packet gives one of the defined decisions.
- No paper execution is performed as part of the performance run.
