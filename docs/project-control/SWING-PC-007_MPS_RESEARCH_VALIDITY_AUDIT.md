# SWING-PC-007 MPS Research Validity Recovery Audit

Status: `COMPLETE_INVALID_FOR_STRATEGY_SELECTION`

Execution base: `d399d96f5813f5a184fbb4854fb537a2010328a4`

Issue: `#17`

## Executive decision

`SWING-PC-006` evidence verdict: `INVALID_FOR_STRATEGY_SELECTION`

H1/H2 evidence status: `NOT_VALIDLY_TESTED`

The July report remains authentic evidence of what the preserved machinery
reported for its special cohort. It is not valid evidence for selecting or
rejecting a general US momentum, trend, or breakout family. The discovery
population was expressly built for machinery validation from recently delisted
securities missing from a prior price archive, not representative strategy
discovery. In addition, deterministic reproductions confirm that carried
positions can ignore an intraday stop and that open positions at a partition end
affect equity metrics without entering trade-level metrics.

The price-series implementation is contract-aligned. Provenance binds the report,
data, config, temporal plan, run identity, generation time, holdout status, and
network/provider status, but omits the Git commit, dirty state, and code/build
identity. The result is therefore bindable as a preserved run artifact but not to
an exact source revision.

No impact magnitude or direction is inferred. Gate 2 and the frozen holdout remain
unopened. No strategy is promoted.

## Scope and method

This was a read-only validity audit of current source/tests/config and exact
restored historical evidence. Two deterministic reproductions were created only
under `/tmp`; source, tests, config, data, reports, runtime state, and Trading212
were not modified.

Evidence authorities, in order:

1. Current `main` at the execution base above.
2. Exact `SWING-PC-006` JSON/Markdown restored under the preserved pre-alignment
   repository.
3. Hash-matched research inputs restored under
   `/home/alexballard92/.local/share/swingmachine-data-staging/`.
4. The accepted evidence hash index and current project-control record.

## Finding summary

| Finding ID | Audit area | Status | Severity | Evidence | Effect | Impact direction | Fix authorised |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `POP-001` | population | `CONFIRMED` | `CRITICAL` | `build_mps_tiingo_queue.py:63-130`; queue SHA-256 `ff4bec9d57e2d1fbd19cdc0d32c9d4ded00e4bf30c343ff0adbdcdd2901caee0`; feature summary; report discovery block | Discovery ranks and outcomes describe a specially selected delisted/missing-price cohort, not a representative US strategy population. | `UNKNOWN` | `NO` |
| `STOP-001` | stop | `CONFIRMED` | `CRITICAL` | `mps_backtest.py:217-230`; `mps_execution.py:42-57`; `/tmp` reproduction SHA-256 `45f5dd2bed86c2b2843c9405f0334884a314f739cf093e4b50039ac642a4bb33` | Valid carried-position `STOP_INTRADAY` fills are ignored; holding period, exits, equity, capital availability, risk and all downstream metrics may be affected. | `UNKNOWN` | `NO` |
| `PRICE-001` | price series | `REJECTED` | `LOW` | Tiingo panel builder; feature-ready builder; `mps_features.py:31-111,183-208`; provider cross-check | The suspected price-series drift is not present: raw and total-return roles are separated as designed. | `KNOWN` — no defect found | `NO` |
| `PART-001` | partition | `CONFIRMED` | `HIGH` | `mps_backtest.py:455-500`; `mps_limitation_screen.py:140-247`; `/tmp` reproduction | Boundary-open positions enter equity returns/drawdown but not completed-trade, PnL/R, concentration, or leave-one-out metrics. | `UNKNOWN` | `NO` |
| `PROV-001` | provenance | `CONFIRMED` | `MEDIUM` | Exact report and evidence-index hashes; report `source_preflight`; runner metadata | Run artifact and inputs are bindable, but exact code/dirty/build identity is not. | `UNKNOWN` | `NO` |

## Audit 1 — discovery-population suitability

### Lineage

The source lineage is:

`source lifecycle inventory -> Tiingo queue -> raw/provider-adjusted Tiingo panel -> shares/classification/reference joins -> feature-ready panel -> MPS features -> eligible universe -> within-cohort momentum ranks -> SWING-PC-006 discovery report`

The queue builder requires a delisting date, eligible exchange, Stock asset type,
absence from the prior price archive, a delisting date in the target interval,
and a unique Tiingo ticker/end-date lifecycle match. Accepted rows receive
`DELISTED_MISSING_PRICE_EXACT_TICKER_AND_END_DATE`. The candidates are ordered by
`most_recent_delisting_then_ticker_descending`, limited to 500, and the queue
explicitly records `strategy_selection_use: false`.

This uses future lifecycle/delisting information to construct the cohort. It is a
delisted-security/missing-archive sample, not a point-in-time broad US population.
No separate representative population is merged before feature construction or
ranking.

The full feature panel contains 208,240 rows across 82 securities. Only 23,951
rows across 25 securities ever pass all eligibility gates. Inside the discovery
partition, the panel has 62,166 rows across 39 available securities but only
3,861 eligible rows across eight securities: BERY, BLUE, JWN, MRC, PDCO, SPR,
VRNT, and WBA. Momentum percentiles are calculated only among eligible rows in
this cohort on each session (`mps_features.py:163-179`). The report confirms eight
eligible discovery securities; H1 completed trades in seven and H2 in three.

### Suitability classification

| Use | Classification | Reason |
| --- | --- | --- |
| Machinery validation | `SUITABLE` | This is the panel's explicit purpose and it exercises lifecycle/data machinery. |
| Delisted-security stress testing | `SUITABLE_WITH_LIMITATIONS` | The selection intentionally emphasizes delisted securities, although unresolved outcome/reference limitations remain. |
| H1/H2 cohort diagnostic | `POPULATION_SUITABLE_ONLY` | It can describe these masks within this cohort, but the confirmed engine defects invalidate the resulting performance evidence. |
| General US swing-strategy discovery | `UNSUITABLE` | The cohort is future-selected, narrow, and non-representative. |
| Programme-level momentum/trend/breakout family rejection | `UNSUITABLE` | Within-cohort ranks and outcomes cannot support general family rejection. |

Conclusion: `POP-001 CONFIRMED`.

## Audit 2 — carried-position intraday stop

`simulate_sell_stop` correctly returns:

- `STOP_GAP` when open is at or below the stop;
- `STOP_INTRADAY` when open is above the stop and low reaches the stop; and
- `STOP_NOT_REACHED` otherwise.

For positions carried into a session, `run_mps_backtest` calls this function at
lines 221-227 but closes the position only when `reason_code == "STOP_GAP"` at
lines 228-230. A valid `STOP_INTRADAY` result is discarded. A later loop processes
all stop types only for positions whose `entry_session` equals the current session
(`mps_backtest.py:391-404`). Existing tests cover same-session intraday stops but
not the carried-position case.

Deterministic reproduction:

- prior-session position with active stop `95.0`;
- next open `100.0`, low `94.0`, with no competing exit;
- direct simulator result: filled `true`, `STOP_INTRADAY`, reference `95.0`;
- actual backtest result: zero completed trades, zero exit events, final position
  count one.

Required conclusion: `CONFIRMED_DEFECT`.

Potentially affected outputs include exit reason/date/price, completed trades,
realised R, trade returns, holding period, MFE/MAE, cash, exposure, equity,
drawdown, Sharpe, fill capacity, later entries, concentration, and gate outcomes.
Impact magnitude and direction are unknown without a separately authorised repair
and rerun.

## Audit 3 — price-series contract

The Tiingo panel builder stores source `open/high/low/close/volume` in
`tradable_prices.parquet` and provider `adjOpen/adjHigh/adjLow/adjClose/adjVolume`
in a separate provider-adjusted panel. The feature-ready builder carries the raw
fields forward unchanged and constructs a causal total-return index from raw
close, cash distributions, and split factors. Its provider-adjusted close is used
as a cross-check, not substituted into execution/chart OHLC.

| Calculation | Actual series |
| --- | --- |
| SMA20/50/200 and SMA200 slope | Raw close |
| ATR | Raw high, low, and prior raw close |
| Peak/recent high | Raw high |
| Pullback depth | Raw high, raw close, raw ATR |
| SMA touch | Raw low versus raw-close SMA20 |
| Trend qualification | Raw close and raw-close SMAs |
| Swing low and structure stop | Raw low and raw ATR |
| Momentum | Causal total-return-adjusted close |
| Entry, stop, and mark-to-market | Raw OHLC |
| Market regime SMA | Raw benchmark close |
| Market regime volatility | Total-return-adjusted benchmark close |

The feature summary records a passing provider total-return cross-check: 208,158
comparable returns, no unexplained mismatches, and two SCPH rounding-explained
mismatches.

Required conclusion: `CONTRACT_ALIGNED`.

## Audit 4 — partition-end open-position accounting

Each `run_stage` call slices one partition and starts a new backtest ledger. The
backtest has no partition-final liquidation. On the final session it marks open
positions to raw close and writes their unrealised value into the equity curve.
It returns only completed trades; open positions and pending exits are not carried
to the next independently reset partition.

`aggregate_metrics` derives compounded return, Sharpe, and drawdown from the
equity curve, while completed trades, net trade PnL, R, win rate, concentration,
and leave-one-out metrics use only `result.trades`.

Deterministic reproduction:

- a position enters on the partition's final session and remains open;
- final position count: one;
- completed trade count: zero;
- initial cash: `100000.0`;
- final marked equity: `100287.1`;
- unrealised equity change included in portfolio metrics: `287.1`;
- trade metrics: zero completed trades and net PnL `0`, with R,
  concentration, and leave-one-security-out all null.

Required conclusion: `CONFIRMED_PARTITION_END_METRIC_MISMATCH`.

The issue can affect return/drawdown/Sharpe versus trade-gate comparability and
removes boundary-open positions from completed-trade and robustness metrics.
Impact direction is unknown.

## Audit 5 — report/code/config/data provenance

The exact preserved report identities match the accepted evidence index:

- JSON SHA-256: `e1ae5e0293d2ab50e630cfb9dc139fdfc61affdf6c7b470d13e2ca703f43a21a`;
- Markdown SHA-256: `751b1a9a08cd05ecb3f8d2a2ccda434070cf2223eb8b62774845dd60c4fdceca`.

| Provenance field | Status |
| --- | --- |
| Run/task identity | Bound: `SWING-PC-006` and timestamped output path |
| Generation timestamp | Bound: `2026-07-29T20:24:02.530956+00:00` |
| Config file and parsed config | Bound by SHA-256 and parsed hash |
| Computed features, feature input, summary, corporate actions | Bound by expected/actual SHA-256 equality |
| Temporal partitions/date plan | Bound by accepted date-plan hash and exact-boundary check |
| Holdout status | Bound: `holdout_opened: false` |
| Network/provider status | Bound: Stooq verification HTML hash and Yahoo HTTP 429/no file |
| Report identity | Bound by accepted evidence-index hashes |
| Git commit | Missing |
| Dirty/staged/untracked state | Missing |
| Source-code/build identity | Missing |

The report is conclusively the accepted July artifact and binds its declared
inputs. Its fields align with the preserved runner. Because no code revision or
dirty-state identity is embedded, the exact executable source cannot be proven
cryptographically from the report alone.

Required conclusion: `PROVENANCE_INCOMPLETE_BUT_RESULT_BINDABLE`.

## Product consequences

| Proposed action | Decision | Reason |
| --- | --- | --- |
| Programme-level momentum-family rejection from `SWING-PC-006` | `REJECT` | Population is unsuitable and mechanics are invalid. |
| Open Gate 2 | `REJECT` | Discovery evidence is invalid for strategy selection. |
| Open frozen holdout | `REJECT` | Discovery did not validly pass and holdout remains protected. |
| Tune H1/H2 | `REJECT` | Tuning against invalid evidence would compound bias. |
| Select revised baseline | `REJECT` | No valid selection evidence exists. |
| Acquire new data | `REJECT` | This audit grants no acquisition and does not establish the five-part exception. |
| Paper trading | `REJECT` | Existing research and safety gates remain closed. |
| Live trading | `REJECT` | Live trading remains prohibited. |

## Checks and preserved boundaries

Required focused tests:

```text
.venv/bin/python -m pytest tests/test_mps_backtest.py tests/test_mps_limitation_screen.py tests/test_mps_strategy.py -q -p no:cacheprovider
19 passed in 2.52s
```

These passing tests do not reject `STOP-001` or `PART-001`; the exact cases are
not covered.

No existing tracked file was modified. No source/test/config/data/report,
DeliveryOS, Trading212, provider/API, Gate 2, holdout, broker, paper, live,
runtime, database, secret, or generated state surface was changed.

## Exactly one recommended next task

Authorise one bounded repair ticket for the carried-position intraday-stop defect
only: make the carried-position loop execute a valid `STOP_INTRADAY` result and
add an exact regression test. Do not rerun `SWING-PC-006`, change thresholds,
open another partition, or infer any economic result as part of that repair.
