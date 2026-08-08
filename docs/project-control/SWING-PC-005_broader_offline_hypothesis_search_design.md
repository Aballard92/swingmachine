# SWING-PC-005 - Broader Offline Hypothesis Search Design

Status: `ACCEPTED_GATE_0_STOPPED`
Authorization: `AUTHORISE_SWING_PC_005_BROADER_OFFLINE_HYPOTHESIS_SEARCH_DESIGN_V1`
Design date: `2026-07-29`
Accepted: `ACCEPT_SWING_PC_005_DESIGN_V1`
Execution authority: `AUTHORISE_SWING_PC_005A_ONE_BOUNDED_OFFLINE_SCREEN_V1`
Execution result: `STOP_SOURCE_OR_TEMPORALITY_INVALID`

## 1. Purpose

Define one bounded, preregistered offline search for a new SwingMachine research
hypothesis after PULLBACK was parked `INCONCLUSIVE`.

This design identified the only two candidate families, fixed the data and
validation contract before results were seen, defined minimum-sample and
robustness gates, and stated where work must stop. It was accepted before the
single bounded execution. That execution stopped at Gate 0 without calculating a
strategy outcome or opening discovery, walk-forward validation, or holdout.

Execution packet:
`reports/swing_machine_v0_1/broader_offline_hypothesis_screen_20260729T171017Z/`

## 2. Authority And Exclusions

Original design authority:

- Inspect existing offline artifacts and code.
- Create and review this design.

The later exact `SWING-PC-005A` authority allowed one minimal implementation,
focused checks, one sequential offline execution, one report packet, and current
project-control updates. That authority is consumed.

Never authorized:

- Bypass Gate 0 or calculate strategy outcomes after a source-gate failure.
- Run a sweep or open the holdout out of sequence.
- Change config, profiles, data, or runtime state.
- Acquire another dataset, account, API key, database, repository, or Vault copy.
- Install packages.
- Build a strategy profile.
- Run serious qualification, paper trading, live trading, broker/API/runtime, or
  deployment actions.
- Stage, commit, push, open a PR, or update GitHub.

Explicit strategy exclusions:

- PULLBACK remains `PARKED_INCONCLUSIVE`.
- MPS variants `B2_MOMENTUM_PULLBACK` and `B4_FULL_MPS1` are excluded.
- TIGHT_BASE remains isolated and is excluded.
- No renamed or cosmetically altered PULLBACK/TIGHT_BASE hypothesis is allowed.
- Earnings/event hypotheses are excluded because the point-in-time earnings
  calendar adapter is unavailable and disabled.
- Short selling, leverage, pyramiding, intraday data, and forced trades are
  excluded.

## 3. Fixed Evidence Foundation

### Primary research panel

| Item | Fixed evidence |
| --- | --- |
| Summary | `/home/alexballard92/.local/share/swingmachine-data-staging/mps-feature-ready-001/mps_feature_ready_summary.json` |
| Summary SHA-256 | `7cf6dd26d7fc0b1ddde13bcfa284c48b969988c638efc112fa31519adcd722c1` |
| Computed feature panel | `/home/alexballard92/.local/share/swingmachine-data-staging/mps-feature-ready-001/mps_computed_features.parquet` |
| Feature panel SHA-256 | `3da1df73028a4cb8c67d75cc99f9583bf98562ea1941d111ab6b920b8b2ea731` |
| Feature input panel | `/home/alexballard92/.local/share/swingmachine-data-staging/mps-feature-ready-001/mps_feature_input_panel.parquet` |
| Feature input SHA-256 | `664c4c5664851f58a5d3d6a0ba116bce44a2c4106830c0663749a918ea028251` |
| Coverage | 2008-01-02 through 2025-12-10 |
| Raw rows | 208,240 |
| Existing `eligible_universe` rows | 23,951 |
| Symbols with existing eligible rows | 25 |
| Data decision | `PARTIAL_RESEARCH_ONLY`; `qualification_usable=false` |

The panel exposes the fields needed for the two hypotheses: adjusted OHLCV,
SMA20/50/200, ATR20, 6- and 12-month momentum, cross-sectional momentum rank,
20-day average dollar volume, prior 20-day high, trend qualification, shares,
market cap, exchange, listing country, sector/reference state, tradability, and
corporate-action inputs.

### Fixed research configuration

| Item | Identity |
| --- | --- |
| Config | `config/mps_1.yaml` |
| File SHA-256 | `738b0a47c36bf60796bebd343575363cb7730f5b505f1f0cd7cc8ca831566d3c` |
| Parsed config hash | `a5fa802cc769fbce8f69996a6f2501fc1629df441565faa19551f2b6987b873f` |

Fixed behaviors relevant to this design:

- official-close signal;
- next-session-open entry;
- no pyramiding;
- momentum entry percentile 0.90;
- momentum hold percentile 0.70;
- maximum holding period 30 sessions;
- baseline adverse cost 5 bps one way;
- stress costs 10, 20, and 50 bps one way;
- maximum eight positions and no leverage;
- half risk at 8% drawdown and stop new entries at 12% drawdown.

No threshold or config value may be optimized in the first search.

### Existing implementation capability

The following local files demonstrate that a later bounded implementation can use
one deterministic engine, but they are not durable evidence while uncommitted:

| File | Current local SHA-256 |
| --- | --- |
| `src/swingmachine/mps_features.py` | `8df2bb97730eebc05e2b6d553f7c1c0a86ec77f1748562100f107d5fbf2050d1` |
| `src/swingmachine/mps_signals.py` | `1940d1cdc8c6e42e0b664a2b6b3f985033d93fef293833b6d8d48faef37edc15` |
| `src/swingmachine/mps_backtest.py` | `5a6d63ca650b7ea4bd73947e6d85ef3e5d683ab5530147ffb367e0dadbd1a09b` |
| `src/swingmachine/mps_validation.py` | `8558bff50ede3063dd1ba46d53e0a1a849f364665510c8e761c7077af97d929c` |

The execution packet records the exact source/config hashes it inspected. It does
not imply that current uncommitted files are already a GitHub baseline.

The current backtest branches B1 and B3 into different end-of-day exit policies.
They must not be compared unchanged as though entry mask were the only difference.
A run reaching strategy outcomes would have needed to decouple the preregistered
entry masks from one common fixed lifecycle policy and test that equality
explicitly. Gate 0 stopped before that code path was required.

### Secondary context only

The earlier benchmark-relative attribution panel contains 4,640 rows across 16
symbols from 2024-06 through 2025-07, with SHA-256
`dc7b96ef1fa10776be8f7af7bc54cf76375eed4c19ac426360e7e084e19e7622`.
It may be used to confirm formula definitions and benchmark fields, but it must not
be merged with the MPS panel or used as an additional optimization population.

## 4. Data Limitation Policy

The historical limitation acceptance in
`10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md` remains controlling.

Before any later screen:

- verify every fixed input hash;
- use security identity rather than ticker alone;
- require classification eligibility, shares availability, valid market cap,
  exchange/listing eligibility, tradability, sector availability for portfolio
  caps, sufficient history, and a next-session bar;
- preserve unavailable fields and masks;
- use only information whose `available_at` is no later than the decision time;
- use total-return-adjusted history for features and benchmark outcomes;
- report the halt-state limitation
  `ASSUMED_FALSE_NO_POINT_IN_TIME_SOURCE` prominently;
- keep every result `PARTIAL_RESEARCH_ONLY`;
- stop rather than impute if the bounded screen needs unavailable metadata.

Passing this search cannot make the panel qualification-usable. It can authorize,
at most, a docs-only candidate-hypothesis definition for later review.

## 5. Preregistered Hypothesis Families

Only two candidate families are allowed. A third family, parameter sweep, or
post-result threshold change invalidates the search.

### H1 - Momentum Trend Continuation

Signal-mask mapping: `B1_MOMENTUM_TREND`.

Predeclared thesis:

> Among fail-closed eligible US common stocks, the highest cross-sectional
> 6-/12-month momentum names that also satisfy the fixed long-term trend structure
> will continue to outperform SPY over their controlled swing lifecycle after
> costs.

Fixed entry mask:

- fail-closed research eligibility;
- `momentum_rank >= 0.90`;
- `trend_qualified == true`.

No PULLBACK, tight-base, rebound, compression, or discretionary candlestick
condition may be added.

### H2 - Momentum Breakout Continuation

Signal-mask mapping: `B3_MOMENTUM_BREAKOUT`.

Predeclared thesis:

> Requiring a new 20-session closing high within the same fixed momentum/trend
> population improves benchmark-relative swing expectancy enough to justify the
> lower trade count.

Fixed entry mask:

- all H1 conditions;
- `close > prior_high20`.

H2 is intentionally nested inside H1. It may be preferred over H1 only if the
paired daily net holdout return difference `H2 - H1` is positive with a positive
95% block-bootstrap lower bound; a higher point estimate alone is insufficient.

### Non-candidate control

`B0_RANK_ONLY` is a fixed diagnostic control. It measures whether the trend and
breakout conditions add value over momentum rank alone. It cannot be selected as a
candidate in this ticket.

## 6. Independent Opportunity And Execution Contract

- Signal at official close; earliest entry is next session open.
- One security may have at most one pending entry or open position.
- Repeated daily signals while pending or held are not new opportunities.
- The primary sample unit is a completed lifecycle trade.
- Unfilled/cancelled entries remain part of conversion and opportunity analysis,
  but do not inflate the completed-trade count.
- Corporate actions, delistings, missing next-session bars, gaps through stops,
  transaction costs, and rejected orders must remain explicit.
- No forced trades or resampling to reach a minimum count.
- H1, H2, and B0 must use the same execution, exit, risk, cost, portfolio, and
  temporal engine so the only candidate-family difference is the entry mask.
- The common lifecycle is the fixed MPS stop, momentum-deterioration, trend-failure,
  failure-exit, maximum-hold, trailing-stop, and risk policy. A family must not
  receive a different exit because of its current enum branch.

## 7. Frozen Temporal Validation

The temporal plan must be created once from the ordered panel sessions using the
existing `freeze_temporal_plan` contract:

- untouched holdout: the longer of the most recent five trading years or 25% of
  available sessions;
- development minimum: eight trading years;
- anchored walk-forward validation windows: two years;
- step: two years;
- embargo between development and validation: 30 sessions;
- holdout remains unopened until all development and walk-forward decisions are
  frozen.

The date-only plan was frozen during design without reading outcomes:

| Partition | Dates | Sessions |
| --- | --- | ---: |
| Full panel calendar | 2008-01-02 to 2025-12-10 | 4,515 |
| Initial discovery span | 2008-01-02 to 2016-01-04 | included in anchored development |
| Embargo 1 | 2016-01-05 to 2016-02-17 | 30 |
| Validation 1 | 2016-02-18 to 2018-02-15 | 504 |
| Anchored development 2 | 2008-01-02 to 2018-01-03 | included past observations only |
| Embargo 2 | 2018-01-04 to 2018-02-15 | 30 |
| Validation 2 | 2018-02-16 to 2020-02-19 | 504 |
| Unused pre-holdout buffer | 2020-02-20 to 2020-12-03 | excluded from selection |
| Untouched holdout | 2020-12-04 to 2025-12-10 | 1,260 |

Canonical date-plan SHA-256:
`6f7146d5901c4c41418c2726a30e3c4ff83a4dfe099b1aa9a3a225972c37dcdb`.

Gate 1 uses only the initial discovery span. Gate 2 uses the two unique validation
spans; observations already seen as validation never become new sample units.
The unused pre-holdout buffer is not available for repair or tuning.

The execution reproduced these exact boundaries and retained the accepted hash
before stopping at Gate 0. No family outcome was calculated. A failed discovery
or walk-forward gate would likewise have ended the task without opening the
holdout.

Sample counts use unique completed trades in mutually exclusive calendar
evaluation periods. Repeated expanding-window development runs and the same trade
appearing in more than one diagnostic view never increase the sample count.

## 8. Metrics Fixed Before Search

Every family and the B0 control must report:

- raw signals, independent submitted entries, fills, cancellations/rejections,
  completed trades, and fill rate;
- completed trades by symbol, calendar year, validation window, regime state, and
  exit reason;
- gross and net PnL, compounded return, CAGR, annualized volatility, Sharpe,
  maximum drawdown, recovery duration, exposure, and turnover;
- win rate, mean/median trade return, mean/median realised R, profit factor,
  average hold, MFE, and MAE;
- duration-matched SPY return and net benchmark-excess return per trade;
- daily net portfolio return and daily SPY-excess return;
- cost stress at 5, 10, 20, and 50 bps one way;
- leave-one-symbol-out and leave-one-calendar-year-out sensitivity;
- 95% block-bootstrap confidence interval using 2,000 samples, 20-session blocks,
  and seed 1;
- deflated Sharpe ratio using exactly two candidate-family trials;
- probability of backtest overfitting across H1, H2, and B0 where the diagnostic
  has sufficient observations;
- every insufficient-data diagnostic without substitution or inference.

## 9. Multiple-Testing And Anti-Overfitting Rules

- Candidate trial count is exactly two: H1 and H2.
- B0 is a control and must not become a candidate.
- No grid search, Bayesian optimization, genetic search, feature mining, threshold
  adjustment, alternative exit, or extra family.
- No result-driven symbol, year, sector, regime, or exit exclusion.
- No peeking at the holdout to repair a failed development result.
- The parsed config hash and all source hashes are frozen.
- Any correction to a calculation defect requires invalidating the affected run
  and regenerating the complete packet with a new identity.
- Both passing families default to the simpler H1 unless H2 passes its predefined
  incremental-return gate.

## 10. Sequential Gates

### Gate 0 - source and temporality

All must pass:

- fixed hashes match;
- schema and uniqueness checks pass;
- decision-time availability checks pass;
- eligibility and missing-data masks are applied fail closed;
- benchmark and corporate-action semantics are reproducible;
- temporal plan is frozen before outcomes;
- no prohibited source or action is used.

Failure outcome: `STOP_SOURCE_OR_TEMPORALITY_INVALID`.

### Gate 1 - development screening

For a family to enter walk-forward validation:

- at least 20 independent completed development trades;
- at least four traded symbols;
- positive mean and median net realised R at baseline costs;
- positive mean duration-matched SPY-excess return at 20 bps one-way stress;
- maximum drawdown no worse than -12%;
- no one symbol contributes more than 35% of completed trades;
- no one calendar year contributes more than 40% of completed trades;
- positive net result after removing each symbol in turn;
- no critical metric is unavailable.

Failure of both families ends the search without opening the holdout.

### Gate 2 - anchored walk-forward validation

For a family to unlock the holdout:

- at least three completed independent trades in every validation window and at
  least 15 across the pooled validation windows;
- positive pooled mean and median net realised R;
- positive pooled duration-matched SPY-excess return at 20 bps stress;
- positive compounded net return in both validation windows;
- no validation window breaches -12% maximum drawdown;
- leave-one-symbol-out pooled net result remains positive;
- deflated Sharpe diagnostic status is `OK` with probability at least 0.95;
- probability-of-backtest-overfitting diagnostic across H1, H2, and B0 is `OK`
  and below 0.50;
- an `INSUFFICIENT_DATA` robustness diagnostic fails Gate 2 rather than becoming a
  pass.

Failure outcome: `STOP_WALK_FORWARD_NOT_STABLE`.

### Gate 3 - untouched holdout

The minimum research-screening floor is:

- at least 30 independent completed trades across the full study;
- at least 10 completed holdout trades;
- at least five traded symbols overall and three in holdout;
- no symbol above 35% of full or holdout trades.

The holdout must also show:

- positive mean and median net realised R;
- positive mean duration-matched SPY-excess return at 20 bps stress;
- positive daily net SPY-excess mean;
- positive lower bound of the fixed 95% block-bootstrap interval for daily net
  SPY-excess return;
- maximum drawdown no worse than -12%;
- positive result after removing each holdout symbol in turn;
- no dependence on one year, regime, or exit path;
- no unresolved integrity or calculation warning.

Thirty trades is a research-screening floor, not paper-readiness evidence.

## 11. Decision Outcomes

| Outcome | Meaning | Authority |
| --- | --- | --- |
| `NO_FAMILY_PASSES` | Both families fail before or on holdout. Park both and stop. | No further strategy work. |
| `INCONCLUSIVE_DATA_LIMITATION` | Required metrics or minimum samples cannot be established from the fixed panel. | Preserve limitation; do not acquire data by inference. |
| `H1_RESEARCH_SCREEN_PASS` | H1 passes every gate and H2 does not establish robust incremental benefit. | Docs-only H1 candidate-hypothesis definition may be proposed. |
| `H2_RESEARCH_SCREEN_PASS` | H2 passes every gate and its incremental holdout lower bound versus H1 is positive. | Docs-only H2 candidate-hypothesis definition may be proposed. |

No outcome authorizes a profile build, serious qualification, paper/live trading,
broker actions, deployment, or further acquisition.

## 12. Stop Conditions

Stop immediately if:

- a fixed hash or schema differs;
- the fail-closed eligibility mask cannot be reproduced;
- available-at, adjustment, identity, delisting, or benchmark semantics are
  unresolved for a required calculation;
- both families fail Gate 1 or Gate 2;
- the holdout minimum sample is not met;
- a result needs parameter tuning, a third family, selective exclusions, or a
  revised exit to appear positive;
- PULLBACK or TIGHT_BASE logic enters the candidate search;
- a new dataset, API, package, Vault action, profile, or runtime action appears
  necessary;
- work exceeds one implementation and report iteration.

## 13. SWING-PC-005A Execution Result

`SWING-PC-005A - Implement one bounded broader offline hypothesis screen`

The ticket was authorized once and executed once. Gate 0 passed the fixed hashes,
parsed config, schema/uniqueness, decision-time availability, fail-closed mask,
frozen temporal boundaries, and prohibited-action checks.

Gate 0 failed:

- no frozen SPY benchmark exists in the accepted source set;
- all 974 dividend events lack payment dates;
- 81 terminal delisted rows exist without delisting return or cash-terms fields.

Required outcome: `STOP_SOURCE_OR_TEMPORALITY_INVALID`.

No H1, H2, or B0 result was calculated. Gate 1, Gate 2, and the holdout remained
unopened. The common-lifecycle backtest extension was not implemented because the
accepted sequential design required an immediate source-gate stop.

Design acceptance string:

`ACCEPT_SWING_PC_005_DESIGN_V1`

Separate implementation authorization, only after design acceptance:

`AUTHORISE_SWING_PC_005A_ONE_BOUNDED_OFFLINE_SCREEN_V1`

## 14. Gate Confirmation

- PULLBACK: `PARKED_INCONCLUSIVE`
- TIGHT_BASE: `ISOLATED`
- Revised profile: `NOT_AUTHORIZED`
- Serious full qualification: `BLOCKED_NO_SELECTED_CANDIDATE`
- Paper trading: `BLOCKED`
- Live trading: `PROHIBITED`
- Broker/API/runtime actions: `NOT_AUTHORIZED`
- Data acquisition: `STOPPED`
- `SWING-PC-005`: `ACCEPTED`
- `SWING-PC-005A`: `COMPLETED_GATE_0_STOP`
- Gate 1: `NOT_OPENED`
- Gate 2: `NOT_OPENED`
- Untouched holdout: `UNOPENED`

The accepted ticket is closed at its preregistered stop condition. It authorizes
no further implementation, data acquisition, strategy work, or trading action.
