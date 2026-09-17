# SwingMachine research reset: findings and delivery evidence

7 September 2026 · SWING-RF-001 · Local, uncommitted work.

## Decision

Keep the daily swing-trading objective and the existing risk/contract foundations.
Do not build an autonomous trader around the inherited strategy unchanged. Its
complexity exceeds its demonstrated edge, and important data and execution
assumptions remain unqualified. The correct replacement is a simpler, falsifiable
research process feeding a deterministic execution system. No profitable strategy
has been established by this work.

The sponsor's new mandate authorises further offline research, implementation and
tests. It does not erase earlier losses or turn a fresh provider into fresh market
history. Historical paper/live and holdout restrictions remain preserved.

## What the review found

### The ranking partly counts the same information twice

`features.py` calculates 126-session relative strength as the stock return minus
the common benchmark return. `signals.py` then separately cross-sectionally
standardizes stock return and relative strength. With aligned observations and
the same benchmark, subtracting a common constant does not change the winsorized
z-score. The configured 20% return weight and 20% relative-strength weight
therefore act like a combined 40% weight on the same signal, not two independent
sources of evidence. Different missing histories can complicate the equivalence;
they do not establish an independent predictor.

The ranking also includes longer momentum, proximity to the annual high and trend
quality, while eligibility/setup rules repeat moving-average and annual-high
conditions. That may reduce trade count without adding useful information.
Any retained filter should demonstrate incremental value through preregistered
removal comparisons, not be justified by its intuitive chart appearance.

### Some inherited acceptance rules are poorly matched to trend following

SWING-PC-006 required a positive median realised R. A trend system can legitimately
lose on more than half its trades while occasional larger winners produce positive
expectancy. Negative median R is diagnostic, not a universal rejection criterion.
This does not rescue H1: concentration, limited independent observations and
unestablished benchmark-relative performance still matter. Past failed gates remain
recorded; the new programme changes the future evaluation design prospectively.

A nominal 2:1 target is likewise a trade-plan constraint, not evidence of positive
expectancy. Net expectancy depends on win probability, realised payoff, gaps and
costs. The new primary experiments retain explicit target/RR discipline, but a
later separately recorded exit comparison may assess whether capping winners
damages momentum. No such exit optimisation has been run.

### Missing information can be mistaken for safe conditions

`signals.py` permits earnings when the earnings distance is absent/NaN.
`exits.py` does not trigger an earnings exit for an unknown event distance.
`backtest.py` values a missing held-position bar at the entry fill price in its
equity and position snapshot helpers. Those are dangerous defaults for trustworthy
multi-session research: unknown events are not no events, and entry price is not
the current mark or a delisting outcome.

The new isolated engine rejects unknown entry-event knowledge and stops when a
held-position price is absent. It models split changes and cash-dividend accrual,
reports remaining open positions, and reconciles equity to closed and unrealised
P&L. Existing legacy runtime and backtest behavior has not been silently changed.

### Execution still needs a demonstrably tradable model

Daily OHLC cannot establish the intraday ordering of an entry, stop and target.
The old stop-limit approximation does not prove that a price was available after
the trigger, or that a broker could obtain the reference fill. Full-day volume
also cannot establish opening-auction capacity or contemporaneous spread.

The new daily simulator deliberately chooses the stop first when both stop and
target are touched, charges adverse costs and handles overnight gaps. Its
open-contingent sizing remains an idealized research bound. A live-compatible
version must either precommit a supported auction order and quantity or use a
delayed intraday entry with observable prices. The Databento minute bars can help
test that sequence; quotes, venue and broker behavior still matter.

## What the Databento data now supports

The acquisition documents describe XNAS.ITCH one-minute raw bars and instrument
definitions for 102 selected logical instruments, 2019–2023. I found the copied
raw corpus under the September import, not at the obsolete Vault mount.

- File census: **242 DBN/Zstandard objects**, **1,050,245,245 bytes**.
- Complete pre-holdout custody check: **92 files**, **379,902,473 bytes**, all
  matching recorded provider sizes and SHA-256 hashes.
- **150 later files were deferred without reading their price/definition
  contents.** Their names/sizes are inventory metadata, not holdout outcomes.
- The initial inherited research inventory covered a smaller subset: 35 verified
  files and 51 deferred. The full provider census above supersedes that subset as
  the scope of the custody finding; both receipts are retained.

Two samples were fixed before profiling: January 2019 and August 2020, core-101.

| Structural measure | January 2019 | August 2020 |
| --- | ---: | ---: |
| Decoded minute bars | 895,486 | 981,608 |
| Observed mapped symbols | 101 | 101 |
| Dates with weekday 09:30–16:00 New York bars | 21 | 21 |
| Bars within that clock window | 815,435 | 818,578 |
| Malformed OHLC | 0 | 0 |
| Duplicate timestamp/instrument pairs | 0 | 0 |
| Unmapped records | 0 | 0 |
| Out-of-order records | 0 | 0 |

These **1,877,094 sampled bars** pass the implemented structural checks. This is
not a full-corpus quality pass. The older structural qualification records 133
malformed bars across its broader scope; the clean samples do not overturn that
finding. The narrow local decoder supports the observed DBN-v1 layout and was
tested with binary fixtures; official-SDK parity has not been established.

Data limitations that materially change the research:

1. **Selected population.** One hundred chosen stocks plus two ETFs are not a
   point-in-time broad-market universe. Results can describe this selected basket;
   they cannot prove general stock-selection performance or remove survivorship
   bias.
2. **Single venue.** XNAS.ITCH is Nasdaq venue activity, including activity in
   securities listed elsewhere. It is not consolidated market volume or a
   guaranteed primary-exchange opening price.
3. **Raw prices.** Bars and definitions do not provide complete split, dividend,
   spinoff, delisting and event treatment for multi-session portfolios. Complete
   action and earnings inputs were not established in this corpus. No such data
   was found in this checkout's `data/` or `prepared_data/` (both absent).
4. **Sessions.** Clock filtering in the sample audit is not official calendar
   qualification. A daily adapter must handle holidays and early closes, session
   completeness and the distinction between venue opens and official opens.
5. **History independence.** The inherited Swing holdout spans 4 December 2020
   through 10 December 2025; the earlier Trading212 audit also protects 2023.
   Different data on these dates is not a new independent holdout. No protected
   outcomes were calculated here.

Databento documents that its daily aggregates use UTC dates, so exchange-session
daily data may need aggregation from finer bars. Its adjustment-factor and
corporate-action products are separate inputs with event/update semantics.
See [OHLCV documentation](https://databento.com/docs/schemas-and-data-formats/ohlcv)
and [adjustment-factor specifications](https://databento.com/docs/venues-and-datasets/adjustment-factors).

## Which hypotheses deserve testing

The initial programme contains three explicit, deliberately simple hypotheses:

- **Momentum:** long positive medium-term momentum above the long-term trend;
  rank eligible names and hold for at most 20 sessions.
- **Breakout:** long a completed close above the prior 20-session high, with a
  long-term trend condition; hold for at most 20 sessions.
- **Reversal:** buy a sufficiently large short-term decline within a positive
  long-term trend; hold for at most five sessions.

These are research candidates, not established working strategies. Evidence for
momentum is stronger at medium horizons than for this exact short swing rule.
The published time-series momentum study covers 58 futures/forward instruments
and a 12-month signal; it does not validate a five-day stock trade. The broader
equity momentum literature supports investigating continuation, not importing a
headline return estimate. [Moskowitz, Ooi and Pedersen](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum),
[Asness et al.](https://www.aqr.com/insights/research/journal-article/fact-fiction-and-momentum-investing?aqrPDF=1).

Short-term reversal has an economic rationale in compensation for providing
liquidity, with strong variation across market conditions. That makes costs and
adverse event selection central. The new reversal rule is an inference to test,
not a replication of the paper. [Nagel, Evaporating Liquidity](https://www.nber.org/papers/w17653).

Post-earnings drift needs historical announcement timing and expectations; pairs
and short strategies need borrow/funding and hedge mechanics; complex machine
learning increases the opportunity to fit noise. None is the first implementation
lane with the presently established inputs. They can be reconsidered when their
data and operational assumptions are demonstrable.

## What a dependable autonomous machine should do

Its ordinary day should be quiet and deterministic: reconcile holdings and
protective orders, validate data freshness and corporate actions, update features
after the official close, create ranked trade/no-trade decisions, allocate account
risk, persist inert intents, submit only under an approved execution mode, then
reconcile every acknowledgement and fill. Overnight/event exposure and cash are
account-level concerns, not independent decisions made by each signal.

The target design has six independently testable parts:

1. **Data custody:** stable security identity; point-in-time eligibility and
   events; immutable source hashes; official sessions; explicit adjusted versus
   raw calculations; no silent exclusion of failed securities.
2. **Research:** economic hypotheses, small initial family set, complete trial
   ledger, protected evaluation, purged boundaries, cost/capacity sensitivity,
   calendar-block uncertainty and negative controls.
3. **Portfolio decisions:** expected net advantage, position/name/sector limits,
   aggregate heat, correlation stress, gap risk, cash and pending-order
   reservations. Taking no trade is a normal successful outcome.
4. **Execution:** the same strategy/risk logic as research; idempotent intent IDs;
   precommitted order semantics; partial-fill/cancel/reject recovery; broker-native
   protection where supported; reconnect reconciliation; no duplicate orders.
5. **Independent controls:** stale-data and broker-disagreement stops, loss and
   exposure limits, kill switch, restart recovery and operator intervention.
   Strategy code must not be able to disable its own account limits.
6. **Review:** expected-versus-realized fills, rejection causes, trade attribution,
   concentration and changing distributions. Changes are researched and versioned,
   not improvised by an LLM during live trading.

Historical testing must be followed by executable replay, supervised forward
observation, and separately authorised staged deployment. Automatic self-rewriting
of live strategies is not part of this design. Unlimited ideas do not justify
unrecorded repeated selection: the backtest-overfitting literature shows why the
search process itself changes confidence. [Bailey et al.](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).

## Implemented and tested now

New `research_reset.py` provides three signal families, explicit target-bearing
plans, next-session timing, conservative daily stop/target handling, costs,
shared cash/risk/sector limits, split and dividend accounting, open-position
reporting and a matched-date passive SPY comparison. Passive SPY is a full-exposure
hurdle, not a risk-matched alpha estimate. Cash yield is assumed zero; account FX,
tax and actual broker fees are not inferred.

New `databento_audit.py` verifies copied source custody and profiles narrowly
supported DBN-v1 minute files without network access or package installation.
`run_research_reset.py` freezes source/config/code hashes before experiment
outcomes, requires explicit data admission, protects the inherited holdout,
separates warmup and evaluation, retains failed runs and writes nine fixed trials.
It does not perform parameter optimization, statistical promotion or broker work.

Synthetic tests exercise known accounting and execution cases and all three
families at 5/10/20 bps per side. Their profits are intentionally not presented as
investment evidence. The stored fixture run is reproducible and explicitly
labelled `SYNTHETIC_FIXTURE`. A source manifest is an adapter contract, not proof
that its assertions are true; historical use requires actual supporting data QA.

## Outstanding work and next action

The review, initial implementation and mechanical testing are complete. The wider
objective—establishing a profitable strategy and qualifying an autonomous bot—is
**not complete**. No historical candidate comparison, walk-forward evaluation,
uncertainty estimate or profitability claim has been produced under this reset.

The next dependency is a research-grade daily source with documented corporate
actions, earnings knowledge, security population and official sessions, plus a
non-overlapping evaluation plan. The discovered raw corpus is useful input to
that work but does not satisfy those requirements alone. If the sponsor's new
data includes additional reference/event files or a broader corpus, its location
is the outstanding input. Paid acquisition and protected-date reuse are not
silently inferred. Implementing a source adapter against unknown event semantics
would only disguise the gap.

Once those inputs exist, run the frozen family set on development data; assess
net return, risk, exposure, drawdown, concentration and stressed costs; freeze the
survivor and its executable entry model; then run the untouched evaluation once.
If no family survives, the correct result remains no selected strategy.

## Delivery record

Repository identity: `/home/alexballard92/swingmachine`, origin
`https://github.com/Aballard92/swingmachine.git`, `main`, starting HEAD `23efab1`.
Starting state: no staged or dirty tracked files; only the pre-existing untracked
XR-001 audit. That audit is preserved unchanged.

Inspected: AGENTS and DeliveryOS controls; product/current-state/architecture/
workflow/backlog/handoff and research-design documents; strategy config;
`signals.py`, `features.py`, `entries.py`, `exits.py`, `execution_model.py`,
`backtest.py`, `lifecycle.py`, `mps_hypothesis_screen.py` and related file surfaces;
Databento acquisition/custody/structural metadata and declared raw samples;
official Databento format documentation and primary research cited above.

Changed files: new research module, audit module, CLI, JSON config, three focused
test modules, this findings document and the research-reset contract; status
annotations in current state, backlog and restart handoff. Existing application
and broker/runtime files were not edited. New generated evidence is confined to
`reports/research_reset/20260907/` (ignored by Git).

Validation commands and exact final results are saved in the companion delivery
receipt. The focused legacy strategy tests passed (21 tests, one existing NumPy
datetime deprecation warning). Full repository tests, type checks, provider APIs,
historical strategy outcomes, holdouts and trading commands were not run. Full
application dependencies are not installed in this checkout; existing Python and
test tools from the local Trading212 environment were used without changing that
environment or importing Trading212 application code.

No staging, commit, branch, push, issue, PR, deployment or broker operation was
performed. Recommended next action: supply or identify the missing reference/event
inputs and an independent evaluation period, then continue the frozen research
programme rather than tune the inherited strategy to selected data.
