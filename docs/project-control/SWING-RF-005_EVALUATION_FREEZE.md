# SWING-RF-005 — Pre-historical evaluation protocol v1

Design frozen: 7 September 2026. Implementation and synthetic verification
completed: 8 September 2026. No historical reset outcomes preceded this freeze.
Historical execution is still unavailable. This is part of the existing RF-003–005 local contract; no
provider/broker/runtime, protected-price, paper/live or GitHub action is included.

## Decisions fixed before results

The experiment contains momentum, breakout and reversal, each at 5, 10 and 20 bps
per filled side: nine declared discovery trials. Only 10 bps is the selection
case; 5 bps is diagnostic and 20 bps is a required stress case. Signal stop/target
geometry is planned at the **same 10 bps** for every scenario. Actual sizing,
limit/RR admissibility and cash costs use the scenario cost, so fill paths can
still differ. This explicit planning-cost convention supersedes the RF-004
fixture's scenario-dependent target geometry; the earlier evidence is preserved.
No cost case, exit variant, universe change or parameter ablation can be added
silently. Such work needs a new version and trial record before outcomes.

The current source calendar covers 483 permitted sessions, 2 January 2019 through
30 November 2020. The first 200 sessions are warmup. Development is therefore
**17 October 2019–30 November 2020**, 283 sessions, subject to reference/source
qualification. Validation and final-test dates are **unassigned**. Each requires
at least 252 separately authorised sessions, with a 20-session embargo between
scored partitions. A provider change does not make previously used history
independent. T212's touched development history and Swing's prior research are
recorded as exposure; the complete prior search count is unknown. Current-matrix
statistics do not retroactively correct that unknown search.

## Benchmarks, denominators and accounting

- Cash earns zero in every account and comparison; no assumed interest credit.
- The funded SPY buy-and-hold benchmark uses the same initial capital, cost case,
  minute clock, opening observations, latency, participation cap and expiring
  fixed buy limit. It targets full investment once, on the first scored session.
  It does not add stops, targets, holding-period exits or reinvest distributions.
  Unfilled quantity and residual cash remain visible; below 95% of the intended
  shares filled is insufficient benchmark evidence. Shares are integral; splits
  and dividends follow the explicit action/payment facts.
- A frictionless exposure diagnostic earns `w[t-1] * SPY_total_return[t]`, where
  `w[t-1]` is the strategy's prior-close market value divided by prior-close
  equity. The first scored weight is zero because each partition starts in cash.
  SPY total return is `split_ratio * (close + dividend) / prior_close - 1` using
  the final warmup close for the first denominator. This is an analytical
  reference, not an asserted executable rebalancing strategy or causal alpha.
- Daily account return is `equity[t] / equity[t-1] - 1`; initial capital supplies
  the first denominator. Arithmetic means are used for inference; compounded
  return is reported separately. Annualised Sharpe uses 252 and sample standard
  deviation with zero cash rate. Zero variance yields no Sharpe, not infinity.
- Drawdown is the largest peak-to-current equity decline, including initial
  capital. Cost basis includes entry costs; proceeds deduct sell costs once.
  Marked positions, unsettled proceeds and unpaid receivables remain in equity.
  The boundary is not a fabricated liquidation. Each scored partition starts
  flat with identical capital; an earlier partition's orders/positions never
  cross an embargo. Feature warmup can precede scoring but cannot contain future
  observations. Missing independent partitions prevent advancement.
- Mean/median trade R use fully closed lifecycles: net PnL including accrued
  entitlements divided by summed intent risk for shares actually filled. Partial
  and open lifecycle PnL remains in portfolio returns and symbol attribution.
  Median R is diagnostic. It is not an automatic failure when expectancy passes.

## Numerical gates

The thresholds below are precommitted engineering/research policy, not values
estimated from historical performance or guarantees of profitability.

| Gate | Base 10 bps | Stress 20 bps |
| --- | --- | --- |
| Scored sessions | At least 252 | At least 252 |
| Fully closed lifecycles | At least 60 | At least 60 |
| Distinct filled symbols | At least 10 | At least 10 |
| Sessions with closing market exposure | At least 126 | At least 126 |
| Distinct 20-session entry cohorts | At least 12 | At least 12 |
| SPY intended share fill fraction | At least 95% | At least 95% |
| Maximum absolute accounting residual | At most 1e-6 of initial capital | Same |
| Compounded net return | Strictly positive | Strictly positive |
| Mean closed-trade R | At least 0.10 | At least 0 |
| Annualised Sharpe | At least 0.75 and at least funded SPY Sharpe | Reported |
| Maximum drawdown magnitude | At most 10% | At most 12% |
| Largest positive symbol contribution | At most 35% of total positive symbol PnL | Same |
| Largest positive calendar-quarter contribution | At most 60% of total positive quarter PnL | Same |
| Net PnL less best symbol / best quarter contribution | Both strictly positive | Both strictly positive |
| Simultaneous lower bounds versus cash and exposure diagnostic | Both strictly positive under each block length | Reported |

Entry cohorts are integer session-index groups `index // 20`, anchored at the
first scored date. They count temporal spread, not independent observations.
Positive-contribution fractions aggregate signed PnL by symbol or quarter before
taking positive components; the denominator is the sum of those positive group
values. Removing the best group is contribution subtraction, not a counterfactual
portfolio rerun. Undefined denominators are insufficient evidence, not passes.

## Dependence and search correction

Use stationary circular-block resampling with geometric expected lengths of
20 and 40 sessions, 9,999 replicates each, seed 20260907 plus block length. The
same block draws apply jointly to all nine cost/family trials and their two mean
differentials (cash and exposure): 18 series. Center each series on its observed
mean. Each replicate records the maximum resampled centered mean across the
entire matrix. The 95th-percentile maximum supplies one simultaneous one-sided
critical value in daily-return units. A series' lower bound is its observed mean
minus that value; adjusted tail probabilities use the finite-simulation
`(1 + exceedances) / (9999 + 1)` convention. No individual-trade IID bootstrap is
used. Both block-length checks must pass; do not choose the favorable length.

This is an unstudentised joint max-mean bootstrap, with a least-favourable
zero-mean centering. It is conservative for lower-volatility series and depends
on stationary/weak-dependence approximations. It is not a calibrated guarantee
through structural regime changes or a repair for unrecorded earlier research.
Insufficient samples retain descriptive metrics but cannot advance a candidate.

The method follows the block-resampling construction of
[Politis and Romano (1994)](https://www.tandfonline.com/doi/abs/10.1080/01621459.1994.10476870)
and the joint search correction described by
[White (2000), sections 2b–2c](https://users.ssc.wisc.edu/~behansen/718/White2000.pdf).
[Bailey and López de Prado (2014)](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf)
reinforces the need to account for selection and track-record length; this v1
does not label its bootstrap a Deflated Sharpe Ratio or claim to implement DSR.

## Decisions and remaining gates

Every family reports its base and stress gates, with failures separated from
insufficient evidence. A synthetic run can only validate mechanics. A historical
development pass could justify a **candidate for independent evaluation**, never
paper/live readiness. If several families pass, rank by the worse of the two
base-cost exposure lower bounds, then base Sharpe, then family name. Freeze that
single candidate before new evaluation. Validation and final evaluation must
repeat the unchanged numerical criteria and benchmark definitions; their missing
date assignments and exact release authority remain open acceptance items.

The implementation must bind the full plan/policy hashes, ledger, code and data
receipt before features/outcomes; reject omitted, duplicate or additional trials;
verify identical scored dates and denominations; and retain machine-readable
reasons. No candidate is selected by this numerical-design document.

## Implementation and exposure evidence

The versioned [spec](../../config/research_evaluation_v1.json) has byte SHA-256
`b633422a2914a9c31bede5f398b24b85b4c13405d24b323f2e5ca7652bec7526`.
The loader verifies that identity and the pinned plan, execution policy and
calendar. `freeze-evaluation` emits the complete ledger, numerical spec, code
identities and partition readiness while reading zero prices and constructing
zero strategies. Active `simulate` records all nine attempts before replay,
completed result hashes or aborted dispositions, and the evaluation output.
Historical replay remains explicitly blocked; passing caller flags cannot turn
this v1 freeze into historical-execution or paper/live authority.

New evidence is retained under
`reports/research_reset/SWING-RF-003_005/evaluation_v1/`:

- `final_freeze/evaluation_freeze.json`: verified final metadata-only freeze.
- `replay_final/`: integrated nine-trial synthetic run, pre-outcome freeze,
  attempted/completed ledgers, orders/fills, funded benchmarks and evaluation.
- `evaluation_acceptance.json`: result-hash verification and mechanics summary.
- `exposure_audit.json`: dated exposure categories and source-control hashes.
- `delivery_receipt.json`: commands, results, files, acceptance and git state.

The earlier `initial_freeze/` is a preserved development checkpoint; final code
identity is in `final_freeze/` and `replay_final/`. Earlier RF-004 evidence also
remains intact, using its then-current planning convention.

The exposure audit records Swing PC-006's discovery dates and its still-unopened
Gate 2, without equating planned validation dates to executed outcomes. Trading212
declares 2019 warmup, 2020–2021 development/touched, 2022 validation and 2023
outcome-prohibited. Its V3 evidence is input-only; the former campaign's complete
outcome exposure was not reconstructed here. Swing reset's fixed January 2019
and August 2020 price-quality audits examined 1,877,094 records; later January
reader conformance reread 895,486. Those checks calculated no historical strategy
outcomes. Calendar metadata and synthetic fixtures are separate exposure types.
No protected prices or additional historical prices were read for RF-005.

## Validation assessment

**Engineering assessment: verified for synthetic research mechanics. Market
evidence assessment: insufficient for strategy qualification.** The Data Analytics
validation workflow was applied to denominators, comparison alignment, attribution,
temporal independence and the stated decision boundary.

All **186 focused research tests passed in 532.15 seconds** on final code. The
eight changed Python/test surfaces also pass Ruff lint and format checks; tracked
changes pass `git diff --check`. Tests cover exact return/R/drawdown calculations,
partial/open PnL reconciliation, split/dividend benchmark accounting, identical
denominations/dates, lagged exposure, empty/undefined metrics, insufficient data,
cost-invariant signal geometry and post-freeze mutations. Bootstrap calculations
match explicit sampled-index expansion; correlated duplicate series preserve
dependence and serial clusters retain calendar dependence. Synthetic, incomplete,
omitted, duplicate or additional trial evidence cannot silently advance.

An initial unit-test run had 22 passes and one failed assertion: a perfectly
alternating 40-session cycle did not meet the test's assumed twofold standard-error
inflation versus IID resampling. The test fixture was corrected to persistent
80-session clusters; its long-lag behavior now matches the property being tested.
The production bootstrap and frozen numerical criteria were not changed in
response to that test. The final 186-test run includes the corrected case.

The retained integrated run uses the existing artificial 260-session source:
200 warmup and 60 scored sessions. All nine trials complete; all nine recorded
result hashes verify. There are 311 intents and 480 fills under the common planning
convention. Maximum absolute account residual is `5.820766091346741e-11`; maximum
evaluation residual as a fraction of initial capital is `6.002665031701326e-16`.
Both 9,999-replicate checks run over the full 18-series matrix. Each family is
`INCONCLUSIVE`, and the candidate is null. The benchmark fills only about 24.8%
of intended shares under fixture capacity, below the frozen 95% requirement.
Session/name/trade/cohort adequacy also fails. The fixture was not altered to
manufacture a numerical pass; synthetic returns are not presented as market edge.

Remaining acceptance items are real source/reference and official decoder
qualification plus independent validation/final date assignment. Fill capacity,
intrabar ordering, clearing dates and broker protection remain explicit assumptions
until independently qualified. Unknown earlier searches and regime changes limit
the statistical interpretation even after numerical checks pass. No historical,
provider, broker, runtime, paper/live or deployment test was run; the full legacy
application suite was not rerun because changes are isolated to offline research.

Reproduce the retained freeze with a new, empty output directory:

```bash
python3 scripts/run_research_reset.py freeze-evaluation \
  --plan config/research_reset_v1.json \
  --execution-policy config/research_execution_v1.json \
  --evaluation-spec config/research_evaluation_v1.json \
  --output <new-output-directory>
```

The delivery receipt records the exact integrated replay and pytest commands.
All work is local and uncommitted; four pre-existing modified control files and
all pre-existing untracked reset files are preserved. No staged changes exist.
