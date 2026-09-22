# SwingMachine research and autonomy backlog

Updated: 8 September 2026. Owner: Codex under the sponsor's research-reset mandate.
Repository: `Aballard92/swingmachine`. Sponsor remains the final decision-maker.

## Outcome and delivery rules

Establish whether a simple, executable daily swing strategy has repeatable net
advantage, then qualify the machinery needed to operate it. A valid outcome is
no qualifying strategy. Profitability is an evidence question, not a delivery promise.

The sponsor accepted the reset direction and requested a backlog, elaborated tasks
and immediate work. This backlog is the local delivery record; creating GitHub
issues, commits, branches or PRs is not authorised. Offline code, config, tests,
documentation and new research evidence are authorised within the reset scope.
Existing source files/evidence are read-only. No provider/API/account/broker,
paper/live, deployment, package installation or protected-holdout access is inferred.

Work one acceptance boundary at a time. Start independent offline work when its
inputs are available; report exact missing inputs without inventing completeness.
Do not demand repeated approval for work already covered by the sponsor mandate.
Promotions depend on evidence; external actions retain their explicit gates.

## Ordered delivery queue

| Task | Deliverable | Dependency | Status |
| --- | --- | --- | --- |
| SWING-RF-001 | Strategy review, corpus custody audit and mechanical prototype | None | Delivered as research foundation; no strategy qualified |
| SWING-RF-002 | Source catalogue, input contract and executable preflight | RF-001 | Delivered; real inputs remain unqualified |
| SWING-RF-003 | Qualified daily data adapter and reference joins | RF-002; source inputs | In progress: adapter, Trading212 calendar/reader adopted; historical qualification open |
| SWING-RF-004 | Executable entry/exit model and portfolio accounting | RF-001; minute fixtures; RF-003 for real parity | Offline core and active CLI implemented; synthetic qualification passed |
| SWING-RF-005 | Frozen experiment, evaluation and promotion protocol | RF-002; RF-003 coverage; RF-004 execution assumptions | Numerical freeze and calculators verified; independent date assignments open |
| SWING-RF-006 | First fixed discovery campaign | RF-003, RF-004, RF-005 | Waiting on inputs |
| SWING-RF-007 | Independent evaluation and robustness decision | RF-006 survivor; unexposed evaluation data | Conditional |
| SWING-RF-008 | Production-quality deterministic decision/risk core | RF-004 contracts; RF-007 selected candidate for strategy integration | Conditional; pure control fixtures can proceed earlier |
| SWING-RF-009 | Execution recovery and broker integration qualification | RF-008; selected broker/account requirements | Offline design/fixtures only until exact broker authority |
| SWING-RF-010 | Forward observation and staged operation | RF-007, RF-009; sponsor approval | Trading/deployment gates closed |

## SWING-RF-002 — Establish and enforce research input readiness

**Goal:** replace vague data blockers with a reproducible, inspectable source
contract and a preflight that runs before strategy evaluation.

**Scope:** `src/swingmachine/research_source.py`, research reset CLI, focused tests,
a research-source example config, this backlog/current-state/handoff/decision
documents, and new `reports/research_reset/SWING-RF-002/` evidence. No legacy
strategy or broker/runtime edits; no source data rewrites or old evidence updates.

**Work:** catalogue known local raw, definition and reference candidates; distinguish
instrument definitions from corporate actions and intraday admission from daily
qualification. Define the daily JSON bundle, required evidence roles, dates,
adjustment convention, benchmark, eligibility, event knowledge and source hashes.
Validate every row, duplicate key, session, benchmark and configuration before
creating strategy outcomes. Protect dates before opening bar files. For historical
inputs require scoped, hashed local references instead of a generic string.
Structural admission must not claim that evidence documents prove economic edge.

**Acceptance:** a valid synthetic source passes; invalid/incomplete sources return
stable, actionable reasons; protected dates stop before bar reads; altered hashes,
duplicate/non-finite data, absent benchmark, missing sessions and unsupported
historical evidence fail before outcomes; all existing mechanical fixtures still
pass. Publish a local readiness assessment of the actual available corpus without
opening protected price data. A blocked data assessment is a completed diagnostic,
not successful data qualification.

**Checks/evidence:** unit and CLI integration tests; focused lint/format checks;
source catalogue, command receipt and final git status. No external commands.

**Delivery:** [SWING-RF-002_INPUT_CONTRACT_AND_READINESS.md](SWING-RF-002_INPUT_CONTRACT_AND_READINESS.md).
The shared CLI preflight, source contract/template and actual local catalogue are
implemented. Synthetic admission passes; the incomplete real-input template reports
nine blockers without a price read. RF-003 takes the data/reference joins next;
RF-004's executable-order fixtures are independently available work.

## SWING-RF-003 — Build an auditable daily source bundle

**Goal:** transform the authorised minute corpus into the daily and reference
inputs actually consumed by research.

**Work:** stream declared, hashed source files; resolve time-varying instrument
identity; join an authoritative exchange calendar with DST/holidays/early closes;
aggregate regular-session raw OHLCV with explicit venue/open semantics. Join
effective splits, distributions, cash entitlements, earnings knowledge and security
eligibility as known at decision time. Keep raw execution prices separate from
adjusted feature/return series. Record missingness and action/identity uncertainty
without selecting rows using future return or next-bar availability. Preserve
delisted and missing held instruments as explicit unresolved accounting states.

**Allowed surfaces:** new offline source adapters, versioned schemas/examples,
tests and newly generated research bundles. Original DBN files and other repos
remain unchanged. No acquisition or unsupported corporate-action inference.

**Acceptance:** hand-calculated daily OHLCV fixtures match; DST/early-close and
symbol-change cases pass; raw/adjusted purposes and availability timestamps are
reconstructable; every emitted field has lineage; full missingness coverage is
reported. Compare the narrow DBN reader against an available official decoder
before using it for price-based claims. Selected-universe limitations stay visible.
Real bundle admission requires the reference sources, not placeholder booleans.

**Checkpoint:** [RF-003 adapter implementation](SWING-RF-003_DAILY_ADAPTER.md).
The streamed minute reader, session aggregation, six reference-table joins,
price/reference lineage and `build-daily` command are implemented. Twenty-eight
adapter/CLI tests and all 64 earlier focused regressions pass. A 3,120-minute
synthetic bundle produces 1,560 admitted synthetic daily bars. Official decoder
parity and real source qualification remain open; this task is not marked complete.

**Subsequent Trading212 adoption:** the newer September worktree supplies a pinned
official-source calendar and isolated byte reader. These are adopted with local
independent calendar verification, source-month guarding, bounded reader
conformance and 133 passing focused tests. See
[adoption record](SWING-RF-003_TRADING212_ADOPTION.md). Its five-year sparsity veto,
intraday admissions and unresolved discontinuities are not swing reference facts.

**Checks:** adversarial calendar/action/mapping fixtures; deterministic replay;
small non-holdout real sample, then the authorised development interval. Missing
reference sources block real admission while fixture implementation proceeds.

## SWING-RF-004 — Make simulated fills and risk executable

**Goal:** remove the prototype's idealized open-contingent fill/sizing assumption.

**Work:** choose and document either precommitted supported auction orders or a
delayed intraday entry after the required observations exist. Freeze quantities
and reserve cash/heat at the actual decision time. Model gap-through stops,
entry/stop/target sequencing, participation, partial fills, order expiry and
cancel/reject paths. Use minute/quote evidence where available; where path is
ambiguous, report conservative bounds. Reconcile split/dividend effects, carried
positions, costs, realized/unrealized returns and period-end treatment.

**Allowed surfaces:** isolated research execution/risk modules, explicit config,
tests and evidence. No broker orders or live implementation activation.

**Acceptance:** perturbing later prices/volume never changes an earlier order;
orders cannot spend future exit proceeds; simultaneous intents share reservations;
stops may lose beyond planned R on gaps; fills obey the chosen order semantics;
ledger and equity reconcile. Expose limits of bars without quotes.

**Checks:** hand-audited minute scenarios, metamorphic timing tests, ledger
invariants, identical decision fixtures across replay and the future inert adapter.

**Implementation direction:** [RF-004 execution design](SWING-RF-004_EXECUTION_DESIGN.md).
The active `simulate` command now uses the fixed-quantity minute engine after
five completed opening minutes. Partial fills, cancel acknowledgements,
adverse entry/stop ordering, settlement and dividend accounting are implemented.
Thirty final execution/replay tests pass, alongside the 133 existing focused
regressions. The retained nine-trial, 60-session synthetic replay reconciles with
158 intents and 727 fills. Real source/broker execution qualification is separate;
The subsequent RF-005 integrated implementation passes all 186 focused research
tests and fixes signal planning at a common 10 bps across cost cases.

## SWING-RF-005 — Freeze the experiment and success criteria

**Goal:** specify what would support or kill a candidate before viewing results.

**Checkpoint:** [numerical freeze and evidence](SWING-RF-005_EVALUATION_FREEZE.md)
binds the plan/policy/calendar and all nine trials. Funded SPY, lagged exposure,
sample/economic gates, PnL attribution and joint stationary-block inference are
implemented and tested. The exposure audit distinguishes prior strategy research
from price-quality and input-only audits. Development has 283 calendar sessions
after warmup; independent validation/final dates remain unassigned. This is still
an open acceptance item. No historical strategy campaign or candidate is enabled.

**Work:** freeze the initial momentum/breakout/reversal family set and the existing
three cost scenarios; specify cash and full-exposure SPY hurdles plus a precisely
defined exposure/risk comparison. Set an explicit development, purged validation
and final evaluation calendar with at least a maximum-hold-length embargo. Record
past exposure: reused evaluation becomes development, and a provider change is
not independent history. Set trial accounting, block resampling, multiplicity,
sample adequacy, concentration, drawdown and net expectancy requirements. Freeze
numerical gates against the actual covered period and declared risk budget, not
after inspecting winners. Negative median trade R is diagnostic, not a universal
failure rule. Any parameter/exit ablation is a separate recorded trial.

**Allowed surfaces:** project-control design, explicit experiment config, pure
validation/statistical helpers and tests. No outcome inspection during design.

**Acceptance:** every promotion/rejection can be calculated from the frozen spec;
no ambiguous denominator, cash-rate, exposure, cost or partition-end rule; fake
IID trade assumptions are not used for overlapping positions. Protected windows
remain closed unless the sponsor changes their exact authority. Lack of a usable
independent period is reported, not concealed by relabeling dates.

## SWING-RF-006 — Execute the first discovery campaign

**Goal:** determine whether any primary hypothesis warrants independent testing.

**Work:** freeze sources/config/code and trial ledger; run the exact family/cost
matrix once on development; publish portfolio curves, trade/activity counts,
drawdowns, expectancy, turnover/exposure, cash/SPY differences and concentration.
Attribute results by predeclared year/regime/name without retroactive exclusions.
Record failed runs and resume deterministically without changing trials.

**Acceptance:** all attempted trials are accounted for, cash/positions reconcile,
sources and consumed inputs reconstruct results, cost effects are explained, and
the candidate/no-candidate decision follows RF-005. No hindsight rescue of failures.

**Allowed surfaces/checks:** offline campaign scripts/config, output bundles,
reconciliation and repeatability checks. No holdout, paper/live or broker access.

## SWING-RF-007 — Challenge the survivor independently

**Goal:** distinguish a repeatable effect from lucky development results.

**Work:** lock the survivor before evaluation; execute the preregistered independent
period; calculate calendar-block uncertainty and selection-aware statistics;
check stressed costs, delayed entries, regime changes, leave-one-name-out and
outlier sensitivity. Report time exposure, effective observations and population
limits. Keep robustness diagnostics separate from tuning a new candidate.

**Acceptance:** a clear pass, fail or inconclusive decision against RF-005; no
claims based solely on positive historical P&L or one symbol; any revisions
consume new development trials and require unexposed evaluation evidence.

**Allowed surfaces/checks:** offline frozen evaluation and statistical evidence.
Requires suitable dates and exact authority for any previously protected window.

## SWING-RF-008 — Qualify the deterministic decision and risk core

**Goal:** make the selected strategy operable without weakening account controls.

**Work:** share strategy features/outcome contracts across research and execution;
produce explicit trade/no-trade/reject/blocked outputs with target/RR and lineage;
centralize name/sector/correlation/heat/cash/pending limits; enforce stale-input,
event, drawdown and kill-switch behavior outside strategy policy. Specify a
versioned state/recovery model and create fault-injection fixtures.

**Acceptance:** deterministic decision parity, no duplicated or unreserved risk,
no forced trade, no strategy override of account limits, recoverable state and
complete audit trace. Changing a model/config changes its identity.

**Allowed surfaces:** pure core/adapters/tests; actual runtime wiring requires a
separate scoped activation task. A risk-engine test pass is not paper readiness.

## SWING-RF-009 — Qualify execution and recovery

**Goal:** demonstrate correct order lifecycle behavior through failures.

**Work:** specify account/broker capabilities and currency/fees; use inert order
adapters and broker fixtures for acknowledgements, duplicates, partial fills,
rejections, cancellations, disconnects and restarts; reconcile positions, cash,
open orders and protective stops. Define monitoring, operator intervention and
shutdown/restart procedures; rehearse failures offline.

**Acceptance:** idempotent intents, no unexplained broker/local disagreement, no
unhandled protection gap and complete failure recovery evidence. Broker-specific
capabilities/limits are verified before integration is promoted.

**Permission boundary:** this backlog authorises offline design/tests only. Any
provider/broker/account/API read or operation needs the exact applicable approval.

## SWING-RF-010 — Observe forward, then consider staged operation

**Goal:** validate behavior against newly arriving conditions before risking capital.

**Work:** prepare a concrete forward observation plan and review criteria; compare
expected versus observed data/fills; monitor slippage, rejection, drift, exposure
and risk compliance. Propose separately reviewed paper and limited-capital stages
with explicit stop conditions and rollback instructions.

**Acceptance:** sponsor receives an executable, reviewable plan backed by RF-007
and RF-009 evidence. Forward observations cannot be fabricated by replay. Paper,
live, deployment and capital allocation remain blocked until exact approval.

## First working increment and open inputs

RF-002 and the RF-003–005 implementation mechanics are delivered. The next
increment must address real reference/decoder qualification or independent date
coverage. Do not keep rerunning the same raw-data audit or synthetic strategy
matrix to imply progress on profitability.

External inputs still unknown: additional corpus/reference file locations;
authoritative corporate actions/earnings/session data; independent date coverage;
eventual account, broker, capital, currency and loss budget. Use the current
long-only, unlevered USD research assumptions until a material dependency needs
the sponsor's answer; never infer live authority from those defaults.

Each completed task reports outcome, pre-existing state, inspected/changed files,
commands and exact results, skipped checks, acceptance status, risks/unknowns,
next action and final git status. Future task scopes are elaborated before edits.
