# SWING-RF-004 — Execution implementation design

Date: 7 September 2026. Status: offline execution core and active CLI integration
implemented and verified on synthetic inputs. No historical outcomes have been
run under this design. Broker/execution-source qualification remains separate.

## Chosen order timing

Daily signals and ranking are formed after the prior completed session. New-entry
decisions use the first five completed minutes of the next regular session, with
fresh observations required for candidates and held-position valuation. For a
09:30 open the decision is at 09:35, with one additional minute of latency before
orders become eligible at 09:36. Orders expire at 09:45 (15 minutes after opening).
Missing observations disable the affected decision; no next-bar price is consulted
to choose quantity, price or whether to submit.

Each entry is a fixed-quantity buy limit with explicit protective stop and target
intent. The buy limit preserves at least the existing configured 2R after the
declared per-side costs; round the maximum permitted entry down to the price tick.
Reject an observed price already through the protective stop. Later gap moves can
still produce adverse fills/losses: they cannot retrospectively cancel the order
as if the gap had been known when it was submitted.

Reserve cash, per-name/sector exposure and risk across the whole ordered batch.
Release reservations only on fills, acknowledgement of cancellation/rejection or
expiry. Never finance an earlier order with a later exit. Entry quantity stays
fixed; later volume may constrain fills but cannot rewrite the earlier intent.

## Fill and lifecycle requirements to implement

Replay one-minute trade bars with explicit fill intervals, not claimed tick-exact
execution times. Limit touches alone do not guarantee fills; require trade-through
for passive fills. Apply a declared per-minute participation ceiling across buys
and sells for the same instrument. Partial fills leave explicit remaining quantity.
Stop triggers cancel remaining entry quantity and persist until the position exits.
Gap stops use the available market price; an ambiguous stop/target interval uses
the conservative stop ordering and reports the ambiguity. Quote/queue uncertainty
must remain visible; bar volume is not proof of available liquidity.

The protective-order protocol needs actual broker capability/recovery qualification
in RF-009. The offline state machine must model fill/activation sequencing and
remaining exposure explicitly; it must not assume an unavailable broker feature
has already been approved or infer live readiness from abstract order types.

Scheduled holding-period exits are committed at the preceding close. Proceeds
remain unsettled until a declared settlement calendar permits reuse. The historical
2019–2020 design uses two settlement days; future periods need their own explicit
convention. Splits adjust quantities/price levels before the effective open; cash
distribution entitlements accrue only to prior holders and become cash on the
retained payment date. Unsupported fractional/cash-in-lieu or terminal-distribution
terms block reconciliation. Closed, partially exited and open positions must all
reconcile against settled cash, unsettled proceeds, receivables and market value.

Risk sizing uses the existing explicit risk/name/sector/heat limits. Add an explicit
drawdown circuit breaker that stops new entries without erasing existing exposure.
The final numerical policy and its cost/participation assumptions must be frozen
with RF-005 before historical testing.

## Required adversarial evidence

- Perturb every price/volume after submission; the earlier order remains identical.
- Orders cannot fill before their activation time or after expiry/cancellation.
- Shared reservations and partial fills never overspend cash or planned risk.
- Stop/target ambiguity, gap-through entry/stop, missing minutes and zero capacity
  leave conservative, explicit outcomes; no artificial guaranteed liquidation.
- Future exit proceeds and unpaid dividends cannot fund new orders.
- Splits, dividend payments and partial exits reconcile through final marked equity.
- The active research command uses this model; the old daily open-contingent
  simulator remains only an explicitly labelled mechanical fixture if retained.

## Sources checked

[FINRA order types](https://www.finra.org/investors/investing/investment-products/stocks/order-types)
supports the distinction between limit-price protection and execution certainty.
[FINRA Rule 5350](https://www.finra.org/rules-guidance/rulebooks/finra-rules/5350)
defines transaction-triggered stop behaviour.
[SEC settlement transition statement](https://www.sec.gov/newsroom/press-releases/2024-62)
records the change from T+2 to T+1 on 28 May 2024. These establish conventions,
not the performance or account capability of a particular implementation.

## Implemented interface and precise conventions

`research_execution.py` separates frozen `OrderIntent` values from mutable order
state and holdings. `start_session`, `on_minute` and `finish_session` require a
contiguous completed-minute clock. The replay adapter traverses the complete
exchange calendar and resolves instrument identities at the observation time.
Entry/sector/earnings context is selected at the decision time; current-session
daily closes never determine an earlier entry quantity or permission.

`config/research_execution_v1.json` makes the initial mechanics explicit: five
opening minutes, one-minute latency, expiry after 15 opening minutes, 0.1% of
reported minute volume, $0.01 order ticks, two settlement days and a 10% drawdown
entry halt. These assumptions are code/test inputs; RF-005 must bind them into
the pre-historical evaluation freeze. The halt is latched at entry decisions and
session closes, with no automatic reset inside a run.

The limit is the tick-rounded minimum of the observed opening-window close and
the maximum price preserving 2R after the configured all-in costs. All-in costs
are charged once on filled notional, separately from the gross fill price.
Passive buys and target sells require trade-through, not a touch. Marketable buy
fills receive at most the limit and can use a lower interval open. A passive
entry-bar high may precede the entry, so same-bar target credit is withheld.
An entry-bar stop is processed after the buy, using the remaining capacity; if
none remains, stop exposure persists to the next observation. This assumes an
atomic contingent protective facility, explicitly unqualified for a real broker.
The same adverse ordering applies when an already partially filled entry receives
more fills: the later intrabar low cannot retroactively cancel an eligible buy.
Any interval receiving additional entry fills receives no target-high credit for
that position because the ordering is unresolved. Pre-existing market exits
already committed before the interval retain priority.

Stops cancel the unfilled entry balance. Client cancellation requests have a
separate latency-delayed acknowledgement; intervening fills remain possible.
Explicit simulated broker rejection releases only the unfilled reservation.
Previously committed holding-period market exits execute before later intrabar
extrema. A triggered unfilled stop remains a market-exit intent and can suffer a
worse price in the next observed interval.

Settlement dates are a separate provenance-bearing input. The engine does not
silently treat the NYSE exchange calendar as a clearing calendar. Cash proceeds
are unavailable until their declared maturity; distribution receivables are
unavailable until the supplied payment date. The current fixtures explicitly use
artificial settlement dates, not an assertion of actual historical clearing dates.
Splits preserve cost basis and action entitlements; unsupported fractional shares
or cash-in-lieu terms fail closed. Amended stop prices round down and targets round
up to the declared tick; any extra planned risk from rounding stays in portfolio
heat. Partial and open positions are retained in the
terminal account rather than sold at an invented boundary fill.

The active `simulate` command now requires `--minute-manifest` and
`--settlement-calendar`; `--execution-policy` defaults to the explicit v1 file.
It rebuilds daily bars from those minutes/references and compares every bar with
the admitted signal inputs before creating strategy engines. Source, policy,
settlement and implementation hashes are written before synthetic trial execution.
The earlier engine is accessible only as `simulate-daily-fixture` for labelled
legacy regression coverage. Historical replay remains blocked while RF-003
qualification and the RF-005 numerical evaluation protocol are incomplete.

## Verification and handoff

The final execution/replay suite passes **30 tests**, including the additional
partial-entry/stop ordering regression. The preceding full focused suite passed
162 tests; the 133 pre-existing reset/source/adapter/calendar/reader tests were
unchanged by the final execution correction. Ruff check/format and whitespace
checks pass. The active CLI's ten-session nine-trial fixture repeats identically.

The retained longer fixture contains 24,960 artificial minute rows, 1,560 daily
bars, 260 artificial sessions and a 200-session warmup. Its **nine 60-session
trials** generate 158 intents, 474 buy fills and 253 sell fills. Every checked buy
obeys its activation/expiry interval and limit; no entry reservation remains at
the end. Maximum absolute accounting residual is **5.10e-11 currency units**.
These are synthetic mechanical checks, not evidence for selecting a strategy.

Artifacts are under `reports/research_reset/SWING-RF-003_005/execution_v1/`:
`input/`, `daily/`, `replay_final/`, `execution_acceptance.json` and
`delivery_receipt.json`. The earlier `replay/` was explicitly terminated after
the partial-entry sequencing issue was identified; it is superseded and is not
accepted evidence. No existing report or source data was overwritten.

```bash
python3 scripts/run_research_reset.py simulate \
  --manifest reports/research_reset/SWING-RF-003_005/execution_v1/daily/daily_manifest.json \
  --minute-manifest reports/research_reset/SWING-RF-003_005/execution_v1/input/build_manifest.json \
  --settlement-calendar reports/research_reset/SWING-RF-003_005/execution_v1/input/settlement_calendar.json \
  --execution-policy config/research_execution_v1.json \
  --plan config/research_reset_v1.json \
  --output reports/research_reset/SWING-RF-003_005/new_executable_replay
```

RF-005 numerical gates, paired benchmarks and block/multiplicity calculations
are next. Calendar-only verification finds 483 covered sessions from 2 January
2019 through 30 November 2020, leaving 283 after the 200-session warmup (first
evaluation date 17 October 2019). Those are coverage counts, not qualified or
independent evaluation observations. Historical clearing dates, reference quality,
fill/quote assumptions and source qualification remain explicit dependencies.
The full three-objective goal stays active.
