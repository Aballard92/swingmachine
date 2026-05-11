# SWING-PC-001 - PULLBACK Fill/Lifecycle Research Design

Status: `DESIGN_READY_FOR_REVIEW`
Scope: documentation-only

## 1. Purpose

This packet designs the next offline research lane before any new SwingMachine profile is built. It defines what deeper PULLBACK fill/lifecycle replay must prove or disprove, what evidence the future diagnostic should produce, and where the lane must stop.

The long-term product vision remains an autonomous swing-trading bot that can research, identify, execute, monitor, exit, and manage account-level risk. The current repo phase is not that execution phase. Current work is offline research and qualification only.

## 2. Current Contradiction To Resolve

- PULLBACK traded outcomes appear positive in the latest lifecycle evidence.
- All accepted PULLBACK evidence remains negative as a group on 20-session SPY-excess return.
- The traded PULLBACK sample is too small to justify building a revised profile.
- No revised baseline candidate is selected.
- Paper trading is blocked, live trading is prohibited, and serious full qualification is blocked until a revised baseline candidate is selected for offline qualification.
- TIGHT_BASE is out of scope for this lane and should remain isolated unless explicitly redesigned and re-qualified later.

This contradiction means the next useful question is not "build PULLBACK-only?" It is "is the positive traded PULLBACK subset caused by repeatable fill/lifecycle selection, or by sample noise?"

## 3. Research Questions

The future diagnostic must answer:

1. Are traded PULLBACK outcomes positive because of genuine fill/lifecycle selection, or just sample noise?
2. What separates traded PULLBACK candidates from untraded accepted PULLBACK candidates?
3. Are entry and fill rules filtering toward better outcomes, worse outcomes, or no meaningful difference?
4. Are exits, stops, targets, hold duration, or lifecycle transitions helping or damaging expectancy?
5. Does PULLBACK show benchmark-relative edge after realistic costs and slippage?
6. Is the apparent PULLBACK edge stable across symbols, dates, provider coverage, and market context?
7. What minimum sample size is required before paper-readiness can be reconsidered?

## 4. Required Evidence

Before any implementation result can support another profile design, the diagnostic must provide:

| Evidence | Required detail |
| --- | --- |
| Candidate counts | Total PULLBACK candidates by window, symbol, and date bucket. |
| Accepted vs traded counts | Accepted PULLBACK rows, traded rows, untraded accepted rows, and trade conversion rate. |
| Filled vs unfilled counts | Filled, unfilled, expired, cancelled, blocked, or otherwise non-executed accepted candidates where artifacts allow. |
| Win/loss rate | Traded lifecycle win rate and candidate forward-return hit rates. |
| Average R | Mean realized R for traded lifecycle rows, plus forward-return proxy R where possible. |
| Median R | Median realized R and median forward-return proxy R to reduce outlier dependence. |
| Max drawdown | Trade-level and aggregate drawdown, including adverse excursion if available. |
| Cost/slippage sensitivity | Results under base costs and stressed costs, at minimum 10, 25, and 50 bps. |
| Benchmark-relative return | Raw return and SPY-excess or appropriate benchmark-excess return over relevant forward windows. |
| Outcome by hold duration | Results grouped by bars held and planned versus actual holding path. |
| Outcome by entry/fill type | Results by entry trigger, fill status, fill delay, fill price relationship, and non-fill reason where available. |
| Outcome by stop/target behaviour | Results by stop hit, target hit, time exit, invalidation, trailing behaviour, and lifecycle transition path. |
| Provider coverage limitations | Alpaca/Hugging Face or other provider coverage gaps, drift, and non-like-for-like windows. |
| Sample-size confidence limits | Explicit confidence warning when counts are too small, concentrated, or dominated by one symbol/date cluster. |

## 5. Proposed Offline Diagnostic Report

A later implementation task should produce an offline-only diagnostic report. It must not change strategy logic, configs, profiles, paper paths, live paths, broker paths, data, migrations, or generated reports outside its own new output directory.

Expected output files:

- `reports/swing_machine_v0_1/pullback_fill_lifecycle_research_<timestamp>/pullback_fill_lifecycle_research.md`
- `reports/swing_machine_v0_1/pullback_fill_lifecycle_research_<timestamp>/pullback_fill_lifecycle_research.json`

Expected report sections:

1. Executive status: `GO`, `NO_GO`, or `INCONCLUSIVE`.
2. Source artifacts and data coverage.
3. Population summary.
4. Accepted versus traded comparison.
5. Filled versus unfilled comparison.
6. Entry/fill rule attribution.
7. Exit/stop/target/hold-duration attribution.
8. Benchmark-relative outcome analysis.
9. Cost/slippage sensitivity.
10. Provider coverage and drift notes.
11. Sample-size and concentration warnings.
12. GO/NO-GO/INCONCLUSIVE decision table.
13. Stop-condition table.
14. Recommended next task.
15. Gate status confirming paper/live/broker actions remain blocked.

Expected core columns:

| Column group | Example fields |
| --- | --- |
| Identity | `symbol`, `setup_date`, `pattern`, `provider`, `source_window` |
| Candidate state | `candidate_id`, `accepted`, `accepted_reason`, `candidate_score`, `feature_bucket` |
| Fill state | `entry_type`, `planned_entry`, `filled`, `fill_date`, `fill_price`, `non_fill_reason` |
| Lifecycle state | `exit_date`, `exit_reason`, `bars_held`, `stop_hit`, `target_hit`, `transition_path` |
| Outcome | `net_pnl`, `net_return`, `r_multiple`, `max_drawdown`, `max_adverse_excursion` |
| Benchmark | `spy_return`, `benchmark_excess_return`, `forward_5d`, `forward_10d`, `forward_20d`, `forward_40d` |
| Costs | `base_result`, `stress_10bps`, `stress_25bps`, `stress_50bps` |
| Confidence | `sample_count`, `symbol_concentration`, `date_cluster`, `provider_limitation_flag` |

Minimum metrics:

- accepted count
- traded count
- fill count
- non-fill count
- trade conversion rate
- win rate
- average R
- median R
- net PnL
- median net return
- max drawdown
- SPY-excess return mean and median
- cost-stressed PnL/return
- outcomes by hold-duration bucket
- outcomes by entry/fill type
- outcomes by stop/target behaviour

## 6. Future Diagnostic Acceptance Criteria

### GO

The future diagnostic can recommend designing a revised offline candidate profile only if:

- PULLBACK traded or fill-selected rows show positive benchmark-relative expectancy after costs/slippage.
- The effect is not limited to the original tiny traded sample.
- Traded or fill-selected rows materially outperform untraded accepted PULLBACK rows.
- Positive results are not dominated by one symbol, one date cluster, or one exit-path anomaly.
- Entry/fill and lifecycle mechanics explain the separation well enough to design a profile without guessing.
- Provider limitations are explicitly documented and accepted as research limitations.

GO does not authorize paper trading. It only authorizes a docs-only revised offline candidate profile design task.

### NO-GO

The diagnostic should reject or park PULLBACK if:

- Accepted PULLBACK remains benchmark-relative negative and fill/lifecycle selection does not explain a durable positive subset.
- Positive lifecycle evidence remains confined to too few trades.
- Costs/slippage erase the apparent edge.
- Exits, stops, targets, or hold duration are damaging expectancy.
- Results depend on stale, non-like-for-like, or provider-fragile evidence.
- The lane cannot distinguish candidate quality from fill selection or lifecycle behaviour.

### INCONCLUSIVE

The diagnostic should return INCONCLUSIVE if:

- Evidence is directionally interesting but sample size remains too small.
- Order/fill artifacts are insufficient to classify filled versus unfilled candidates reliably.
- Provider coverage is too incomplete for a stable conclusion.
- Results require additional historical windows or a broader hypothesis search before profile design.

## 7. Stop Conditions

Stop pursuing PULLBACK as the next profile lane if:

- The next diagnostic cannot expand evidence beyond the existing small traded subset.
- Traded and fill-selected candidates do not outperform untraded accepted candidates.
- Benchmark-relative returns remain negative after costs.
- Risk-adjusted returns are driven by one outlier winner or one symbol/date cluster.
- Provider drift materially changes the conclusion.
- The diagnostic requires profile/config changes before it can answer the offline question.
- The work starts drifting into profile-building, paper trading, live trading, or broker execution.

## 8. Risks And Assumptions

- Small sample risk: the current positive traded PULLBACK evidence may be noise.
- Provider drift risk: Alpaca and Hugging Face coverage may not produce like-for-like conclusions.
- Stale report risk: generated reports are numerous and older paper-readiness docs are not current authority.
- Overfitting risk: selecting filters after seeing four positive trades could create a non-repeatable profile.
- Benchmark-relative underperformance risk: absolute gains are insufficient if SPY-excess evidence remains weak.
- Accidental profile-building risk: this lane must not silently create or alter a revised strategy profile.
- Artifact availability assumption: current offline reports expose enough candidate, fill, and lifecycle fields to classify traded versus untraded accepted PULLBACK rows; missing fields must be reported, not inferred.

## 9. Recommended Next Task

After this document is reviewed and accepted, the next Codex task should be:

`SWING-PC-002 - Implement offline-only PULLBACK fill/lifecycle diagnostic report`

That task should build the diagnostic report described above using existing offline artifacts only, with focused tests for metric calculation and population splitting. It must not build a revised profile or run paper/live/broker commands.

## Gate Confirmation

- No paper trading is authorized by this design.
- No live trading is authorized by this design.
- No broker command is authorized by this design.
- No strategy profile build is authorized by this design.
- No app code, strategy config, data, generated report, broker/runtime path, or migration change is required for this design.
