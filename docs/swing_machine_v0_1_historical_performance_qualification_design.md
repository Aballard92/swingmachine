# Swing Machine v0.1 historical performance qualification design

Date: 2026-05-07
Baseline: `swing_machine_v0_1`
Status: design/backlog checkpoint, not implementation approval

## Executive position

Historical performance qualification has not yet been completed.

The current evidence proves mechanical determinism and lifecycle reconciliation. It does not prove profitability, robustness, benchmark superiority, or market edge.

Historical performance qualification should start only after the mechanical readiness gate is complete or explicitly accepted.

## Purpose

The purpose is to answer whether `swing_machine_v0_1` has enough historical merit to justify controlled paper trading and further research.

It should not optimize the strategy yet.

It should measure the current baseline honestly.

## Required questions

The qualification must answer:

- Did the strategy make money historically?
- Did it outperform a simple benchmark over the same period?
- Did it outperform after transaction costs and realistic slippage?
- Was profitability concentrated in one regime, period, symbol, or sector?
- Was trade count sufficient to support a meaningful conclusion?
- Were drawdowns tolerable?
- Was return worth the exposure and turnover?
- Did the system behave as expected during losing periods?
- Does the result justify paper trading, more research, or rejection?

## Required inputs

Required inputs:

- Qualified historical panel manifest.
- Explicit baseline profile/config.
- Mechanical readiness report with `PASS` or accepted residual warnings.
- Stateful backtest output.
- Lifecycle artifact package.
- Benchmark series for the same dates.
- Cost/slippage assumptions.

Data sources under consideration:

- Trading212 repo Alpaca historical data.
- Trading212 repo Hugging Face historical data.

The first pass should use the already-qualified Alpaca broad manifest because it has passed mechanical lifecycle qualification. Hugging Face data should be used as a provider robustness comparison after the first performance report exists.

## Required metrics

Core performance metrics:

- Initial equity.
- Final equity.
- Total return.
- CAGR where period length supports it.
- Annualized volatility.
- Sharpe ratio.
- Sortino ratio where downside sample is sufficient.
- Max drawdown.
- Calmar ratio.
- Exposure-adjusted return.
- Benchmark total return.
- Excess return versus benchmark.
- Tracking of cash drag.

Trade metrics:

- Trade count.
- Win rate.
- Loss rate.
- Average win.
- Average loss.
- Median win.
- Median loss.
- Profit factor.
- Expectancy per trade.
- Average bars held.
- Median bars held.
- Largest win.
- Largest loss.
- Consecutive wins/losses.
- Stop exit count.
- Time exit count.
- Earnings exit count.
- Trail exit count.

Risk/concentration metrics:

- Max open positions.
- Average open positions.
- Average exposure.
- Max exposure.
- Portfolio heat distribution.
- Sector concentration.
- Symbol concentration.
- Monthly/quarterly return distribution.
- Drawdown duration.
- Turnover.

Robustness metrics:

- Performance by market regime.
- Performance by calendar period.
- Performance by sector.
- Performance by setup type.
- Performance by ranking bucket.
- Cost/slippage sensitivity.
- Provider comparison where available.

## Benchmark design

Minimum benchmark comparison:

- Buy-and-hold benchmark over the same replay period.
- Same initial equity.
- Same date window.
- Same currency assumption.

Preferred benchmark symbols:

- SPY where available for US broad equity exposure.
- QQQ as secondary technology/growth comparison if available.
- Cash baseline at zero return for sanity.

If benchmark data is missing from the manifest, benchmark availability should be a blocker or explicitly sourced from a validated provider file.

## Cost and slippage design

The first report should include:

- Base configured transaction costs.
- Zero-cost sensitivity.
- Higher-cost sensitivity.
- Higher-slippage sensitivity.

The goal is not to tune costs but to understand whether the edge disappears under plausible friction.

## Regime and period breakdown

Breakdowns should include:

- Full period.
- Calendar month.
- Calendar quarter.
- Risk-on sessions.
- Caution sessions.
- Risk-off sessions.
- High-volatility windows if regime data supports it.

Each breakdown should report returns, drawdowns, trade count, win rate, and expectancy.

## Provider robustness design

The first qualification should run on the currently mechanically qualified Alpaca broad panel.

Then run a comparison against the Hugging Face panel if compatible data contracts exist.

Provider comparison should answer:

- Are returns directionally similar?
- Are trades materially different?
- Are missing bars or adjusted prices causing decision changes?
- Are candidate/ranking/lifecycle results stable enough?

Provider mismatch should be treated as a data-quality finding, not a strategy optimization opportunity.

## Output artifacts

Required artifacts:

- `historical_performance_summary.json`
- `historical_equity_curve.json`
- `historical_trade_metrics.json`
- `historical_trade_list.json`
- `historical_drawdowns.json`
- `historical_benchmark_comparison.json`
- `historical_regime_breakdown.json`
- `historical_period_breakdown.json`
- `historical_concentration_report.json`
- `historical_cost_sensitivity.json`
- `historical_performance_manifest.json`
- `historical_performance_review.md`

## Pass/warn/block framework

A performance report should not use a simplistic pass/fail based only on profit.

Suggested decision values:

- `PASS_FOR_PAPER_CONSIDERATION`: profitable after costs, acceptable drawdown, adequate trade count, no obvious concentration failure.
- `WARN_RESEARCH_REQUIRED`: mechanically valid but performance is weak, concentrated, sample too small, or sensitive to costs.
- `BLOCK_PAPER_TRADING`: unprofitable, unacceptable drawdown, benchmark materially better, too few trades, severe concentration, or data/provider instability.

## Non-goals

Do not optimize parameters.

Do not add strategy variants.

Do not overfit on the historical period.

Do not select only winning windows.

Do not treat paper trading as a substitute for this report.

## Recommendation

Historical performance qualification should be the next major phase after mechanical readiness closure.

It should start with an honest broad Alpaca performance report, then extend to Hugging Face/provider robustness if compatible.
