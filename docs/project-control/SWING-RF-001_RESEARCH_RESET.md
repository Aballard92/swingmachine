# SWING-RF-001 — Evidence-led offline research reset

Date: 2026-09-07. Repository: `Aballard92/swingmachine`.
Sponsor authority: current conversation, requesting a fresh strategy review,
research, implementation and testing, with Codex leading the work.

## Authority and scope

This instruction supersedes the previous prohibition on starting further offline
strategy research for this campaign. It does not retroactively accept the XR-001
audit, invalidate past results, or grant trading authority. Codex owns the current
research design and implementation under the sponsor's new mandate. No GitHub
issue was requested; this local task contract records the authorised work.

Allowed edits: new offline research modules under `src/swingmachine/`, focused
tests, scripts, explicit research configurations, project-control status and new
evidence under `reports/research_reset/`. Existing source data is read-only.
Checks: focused unit/integration tests and local historical experiments.
Prohibited: broker/runtime/order paths, paper/live trading, account/API/provider
commands, paid acquisition, secrets, existing evidence rewrites, external repo
mutations, staging, commits, pushes, issues, PRs and deployment. No package
installation is assumed. Existing frozen holdouts remain protected.

## Research decision before outcomes

Keep the daily decision cadence, explicit risk budgets, portfolio accounting and
determinism. Challenge the many overlapping ranking/setup filters, next-session
fill assumptions, narrow population, missing event semantics and incomplete
source lineage. Do not carry forward a positive-median-trade requirement: a
positively skewed trend strategy can have negative median trades and positive
expectancy. Assess net portfolio performance and its uncertainty instead.

Initial scope assumption: liquid US equities/ETFs, long-only, unlevered, USD
research account, approximately 2–20-session holding periods. Account size and
costs are research scenarios, not the sponsor's actual balance or broker terms.

Freeze three primary hypotheses with no parameter sweep:

1. `momentum`: positive 126-to-21-session momentum, close above its 200-session
   mean, select the top 20% of eligible names, hold at most 20 sessions.
2. `breakout`: close exceeds the previous 20-session high and its 200-session
   mean, hold at most 20 sessions.
3. `reversal`: close lies at least 1.5 ATR below its 20-session mean while above
   its 200-session mean, hold at most five sessions.

Common primary rules: decide only after the completed regular session; idealized
next-session open entry with adverse costs; stop two signal ATR below signal close;
target adjusted for assumed costs to supply twice the planned net initial risk;
reject gaps that destroy the
minimum 2:1 net planned reward/risk; no pyramiding; 0.3% planned equity risk per
trade; 8% name cap; 2% portfolio heat; 1% new daily risk; 20% sector cap; no
leverage. Unknown sectors share one conservative bucket. Stops may lose more
than planned risk on gaps. Earnings knowledge must be explicit; unknown events
are not silently treated as no event. Risk and cash are shared across positions.

The target-bearing primary experiment deliberately differs from the old
targetless trailing baseline. It does not establish that fixed targets are
optimal. A later preregistered exit ablation may test trailing exits; it counts
as another trial and cannot silently replace a losing primary result.

The daily research fill uses the observed open for gap admission and sizing. This
is an idealized execution bound, not a claim that an auction order can be
submitted after its fill price is known. Promotion requires a precommitted auction
order model or a delayed, executable intraday entry model using minute data and
appropriate spread/impact evidence. Source models and broker order support must
be matched before any research/runtime parity claim.

Costs: 5, 10 and 20 basis points per side, including assumed spread/slippage/fees;
not calibrated broker estimates. FX and tax are not modeled, and this blocks
account-specific performance claims. Compare with cash and SPY under matched
dates/cost conventions, and report market exposure so beta is not called alpha.

## Data admission and temporal protection

The locally discovered acquisition manifest describes 102 selected logical
instruments, XNAS.ITCH one-minute raw prices and definitions, 2019–2023.
This is metadata evidence, not a verified current raw-data inventory. Nasdaq
venue OHLCV is not consolidated US volume or guaranteed primary-exchange open.
No Trading212 strategy outcomes may be used to choose Swing parameters.

Freeze a source manifest with hashes before calculating any strategy return.
Require stable instrument mapping, official session calendar (including early
closes), regular-session aggregation, valid unique OHLCV, split and dividend
semantics, point-in-time availability and explicit population limitations.
Never impute a missing held-position price from the entry price or silently drop
delistings. Stop and report incomplete accounting instead.

The old Swing holdout is 2020-12-04 through 2025-12-10; the prior cross-repo audit
also identifies a protected Trading212 2023 holdout. These dates remain closed
to strategy outcomes here. A new provider does not create independent dates.
Any currently accessible pre-holdout data can support exploratory development,
not a fresh out-of-sample or profitability claim. Do not invent a new validation
window inside a protected period. Outcome execution requires a separate,
explicit temporal plan whose boundaries do not intersect protected windows.

## Promotion criteria and stopping rules

Mechanical test success is not evidence of edge. Real-data research is admissible
only after the source and temporal checks pass. Save all trials, including
failures, with source/config/code hashes. Keep candidate selection separate from
evaluation, purge overlapping positions across boundaries and use an embargo at
least as long as maximum holding duration. Reusing validation after revisions
turns it into development data.

Before promotion, require positive net expectancy under stressed costs, positive
portfolio-level excess over an exposure-matched baseline, acceptable drawdown,
calendar-block uncertainty estimates corrected for the family search, sufficient
independent periods, stability across regimes and symbols, and no dependence on
one name or a few outliers. Exact promotion thresholds must be frozen when a
qualified population and unexposed evaluation period are established. No current
candidate can be promoted by this initial infrastructure task.

Autonomy is a later engineering qualification: same decision/risk engine in
research and execution; persistent idempotent intents; broker reconciliation;
protective order recovery; independent limits and kill switch; event and stale
data controls; full audit trail; supervised forward observation before capital.
An LLM can propose research and explain results, but cannot rewrite a deployed
strategy or bypass deterministic risk limits.

## Acceptance and reporting

- Source-backed review of current strategies and new corpus suitability.
- Explicit hypotheses and source/temporal limits recorded before outcomes.
- Executable isolated research components with meaningful adversarial tests.
- Real-data results only if actual inputs pass admission; otherwise an exact
  blocker, with synthetic mechanical tests clearly identified.
- Durable findings, commands/results, inspected/changed files, limitations and
  final git status. No profitable or autonomous-ready claim without evidence.

Initial git state: `main`, HEAD `23efab1`; no tracked modifications or staged
files; pre-existing untracked XR-001 audit, preserved unchanged.
