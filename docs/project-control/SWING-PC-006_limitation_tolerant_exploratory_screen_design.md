# SWING-PC-006 - Limitation-Tolerant Exploratory Screen Design

Status: `COMPLETED_NO_FAMILY_PASSES_DISCOVERY`
Accepted by: Alex, `Proceed`, 2026-07-29
Predecessor: `SWING-PC-005A`
Maximum evidence grade: `EXPLORATORY_ABSOLUTE_RETURN_RESEARCH_WITH_ACCEPTED_LIMITATIONS`

## 1. Goal

Run one honest, bounded H1/H2 exploratory screen without requiring another user
account, API key, quota, large database, or Vault transfer.

The `SWING-PC-005A` strategy outcomes and holdout were never opened. This revised
design therefore retains the same hypotheses and temporal partitions while
replacing the qualification-grade corporate-action and benchmark requirements
that stopped Gate 0.

## 2. Authority

Allowed:

- inspect the existing fixed MPS panel and current source/control code;
- acquire exactly one account-free SPY daily dataset;
- store it under local SwingMachine staging and pin its SHA-256;
- compare its overlapping dates with the existing local Alpaca SPY series;
- implement the common-lifecycle exploratory accounting described below;
- add focused tests;
- execute the sequential screen exactly once;
- write one JSON/Markdown report packet and update current project control.

Prohibited:

- another account, API key, authenticated API, quota-bearing source, database,
  repository-scale dataset, or Vault access;
- another candidate family, threshold change, parameter optimization, sweep, or
  result-driven exclusion;
- config/profile changes, serious qualification, paper/live trading,
  broker/runtime/deployment actions, package installation, or secret access;
- Git staging, commit, push, PR, issue, or comment actions;
- a second screen execution or outcome-driven implementation revision.

## 3. Fixed Strategy And Panel

The following identities remain fixed:

| Item | SHA-256 |
| --- | --- |
| MPS summary | `7cf6dd26d7fc0b1ddde13bcfa284c48b969988c638efc112fa31519adcd722c1` |
| Computed features | `3da1df73028a4cb8c67d75cc99f9583bf98562ea1941d111ab6b920b8b2ea731` |
| Feature input | `664c4c5664851f58a5d3d6a0ba116bce44a2c4106830c0663749a918ea028251` |
| MPS config file | `738b0a47c36bf60796bebd343575363cb7730f5b505f1f0cd7cc8ca831566d3c` |
| Parsed config | `a5fa802cc769fbce8f69996a6f2501fc1629df441565faa19551f2b6987b873f` |

The panel remains `PARTIAL_RESEARCH_ONLY`. The halt state remains
`ASSUMED_FALSE_NO_POINT_IN_TIME_SOURCE`.

Candidate families remain:

- H1: `B1_MOMENTUM_TREND`;
- H2: `B3_MOMENTUM_BREAKOUT`;
- B0: `B0_RANK_ONLY`, diagnostic control only.

All three use the same entry, next-open execution, sizing, costs, stops, trailing
stop, momentum exit, trend exit, failure exit, maximum hold, portfolio limits,
and drawdown controls. The entry mask is the only family difference.

## 4. Single Benchmark Acquisition

Primary allowed file:

`https://stooq.com/q/d/l/?s=spy.us&i=d&d1=20080102&d2=20251210`

The first retrieval returned a 796-byte JavaScript verification document rather
than CSV data, SHA-256
`54f1f005853d9e7053acfbd7182f892e2ddaee23118632aba39de0313e4c578c`.
No browser-verification bypass, scripted proof-of-work, or retry is allowed.

Because this was a transport failure before any market data or strategy outcome
was read, the only allowed fallback is one unauthenticated Yahoo chart response:

`https://query1.finance.yahoo.com/v8/finance/chart/SPY?period1=1199232000&period2=1765497600&interval=1d&events=div%2Csplits&includeAdjustedClose=true`

The response returned HTTP 429 before any file was written. No second
benchmark-data source or retry is allowed.

Required properties:

- a valid Stooq CSV or the single valid Yahoo JSON fallback;
- symbol SPY;
- daily OHLCV;
- adjusted close for benchmark total-return outcomes;
- coverage includes 2008-01-02 through 2025-12-10;
- no duplicate dates, non-positive prices, or invalid OHLC;
- SHA-256 recorded before strategy outcomes.

Account-free validation uses the existing local Alpaca SPY file:

`data/qualification_sources/trading212/alpaca/historical_broad_2024_06_to_2025_07_v0_1/historical_ohlcv.csv`

The benchmark gate requires:

- at least 600 overlapping sessions;
- daily close-return correlation at least 0.999;
- median absolute daily-return difference no more than 5 bps;
- 99th-percentile absolute daily-return difference no more than 50 bps.

Both account-free transports failed before market data was acquired. Under Alex's
standing instruction to use the best evidence already available rather than open
more accounts or data hunts, the screen is therefore downgraded to absolute-return
exploratory evidence:

- no SPY or market-relative metric is calculated;
- no benchmark-relative claim is permitted;
- every former SPY-excess threshold is replaced by the corresponding positive
  absolute net-return threshold;
- daily bootstrap evidence uses portfolio net returns rather than SPY excess;
- no further network request is allowed.

## 5. Accepted Corporate-Action Limitations

### Splits

Use the panel's explicit effective-date split factor. Adjust the held quantity,
entry price, stops, and per-share risk consistently. Total position cost and
total initial risk remain invariant.

### Dividends

Accrue `div_cash * held_quantity` on the ex-date only for positions held entering
that session. The receivable:

- is not spendable for new entries;
- is excluded from sizing cash and interim portfolio equity;
- is added to economic PnL and cash only when the trade closes.

This is deliberately conservative about reinvestment and does not claim to model
payment-date cash timing.

### Unresolved delistings

A position reaching a terminal `is_delisted` row is closed at that session's raw
close and tagged `UNRESOLVED_DELISTING_LAST_CLOSE`.

Every gate is evaluated under both:

- `LAST_CLOSE`: the recorded last-close proceeds;
- `TOTAL_LOSS`: the same trade receives zero exit proceeds.

Accrued pre-terminal dividends remain in both cases. A family passes only if both
scenarios pass. No unresolved terminal trade may be dropped.

## 6. Return Conventions

- Trade return: economic net PnL divided by entry cash cost.
- Daily portfolio returns: consecutive reported account-equity changes.
- Total-loss equity curves subtract terminal last-close proceeds from the
  terminal date onward.
- Costs: 5, 10, 20, and 50 bps one way, rerun through the same engine.

## 7. Temporal Lock

The accepted plan and canonical identity remain unchanged:

`6f7146d5901c4c41418c2726a30e3c4ff83a4dfe099b1aa9a3a225972c37dcdb`

- discovery: 2008-01-02 through 2016-01-04;
- validation 1: 2016-02-18 through 2018-02-15;
- validation 2: 2018-02-16 through 2020-02-19;
- unused buffer: 2020-02-20 through 2020-12-03;
- untouched holdout: 2020-12-04 through 2025-12-10.

Gate 1 is calculated before Gate 2. The holdout is read only if at least one
candidate passes Gate 2. The unused buffer is never used.

## 8. Sequential Gates

The `SWING-PC-005` thresholds remain controlling.

Gate 1 requires, in both delisting scenarios:

- at least 20 completed trades and four traded securities;
- positive mean and median realised R at 5 bps;
- positive mean net trade return at 20 bps;
- maximum drawdown no worse than -12%;
- no security above 35% or calendar year above 40% of trades;
- positive net PnL after removing every security in turn;
- no critical metric unavailable.

Gate 2 requires, in both scenarios:

- at least three trades per validation window and 15 pooled;
- positive pooled mean and median realised R;
- positive pooled mean net trade return at 20 bps;
- positive compounded net return in both windows;
- maximum drawdown in each window no worse than -12%;
- positive pooled leave-one-security-out result;
- DSR status `OK` and probability at least 0.95 using two candidate trials;
- PBO status `OK` and value below 0.50 across H1, H2, and B0.

Gate 3 requires, in both scenarios:

- at least 30 completed trades across the study and ten in holdout;
- at least five traded securities overall and three in holdout;
- no security above 35%;
- positive holdout mean and median realised R;
- positive holdout mean net trade return at 20 bps;
- positive daily net return mean and positive fixed bootstrap lower bound;
- maximum drawdown no worse than -12%;
- positive leave-one-security-out and leave-one-year-out net PnL;
- no one year above 40% or exit reason above 70% of holdout trades.

If both families pass Gate 3, H1 remains preferred unless the paired daily
holdout return difference `H2 - H1` has a positive mean and positive 95%
block-bootstrap lower bound.

## 9. Outcomes

- `STOP_BENCHMARK_VALIDATION_FAILED`
- `NO_FAMILY_PASSES_DISCOVERY`
- `STOP_WALK_FORWARD_NOT_STABLE`
- `INCONCLUSIVE_ABSOLUTE_ONLY_SCREEN`
- `H1_ABSOLUTE_ONLY_EXPLORATORY_PASS`
- `H2_ABSOLUTE_ONLY_EXPLORATORY_PASS`

No outcome authorizes a strategy profile, qualification, paper trading, live
trading, or another data-acquisition lane.

## 10. Infrastructure Recovery Record

The first execution attempt used output identity
`limitation_tolerant_screen_20260729T184316Z`. Crostini restarted at
2026-07-29 19:50:38 Europe/London while discovery was still running. The process
was terminated before the output directory or any report was created; no gate
decision or strategy result was exposed.

A recovery execution using the unchanged preregistered strategy, thresholds,
partitions, source hashes, and code is allowed under the same authorization. This
is an infrastructure retry, not another analytical iteration. The interrupted
identity remains recorded and must not be represented as a completed screen.

## 11. Final Result

Completed report:
`reports/swing_machine_v0_1/limitation_tolerant_screen_20260729T194422Z/`

Outcome: `NO_FAMILY_PASSES_DISCOVERY`.

- H1 completed 68 total-loss-scenario trades at 5 bps across seven securities.
  Net PnL was +3,510.02 and mean realised R was +0.1746, but median realised R
  was -0.2530 and one security supplied 61.76% of trades. H1 therefore failed
  the preregistered median and concentration gates.
- H2 completed 29 trades across only three securities. Net PnL was -509.92,
  mean realised R was -0.0805, median realised R was -0.2354, and one security
  supplied 79.31% of trades. H2 also failed its 20-bps return and
  leave-one-security-out gates.
- No terminal-position trade occurred in discovery, so `LAST_CLOSE` and
  `TOTAL_LOSS` produced the same gate decision.
- Gate 2 was not opened.
- The holdout remained unopened.

No candidate family was selected. The authorization is consumed.
