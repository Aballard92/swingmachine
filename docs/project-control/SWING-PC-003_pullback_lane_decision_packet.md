# SWING-PC-003 - PULLBACK Lane Decision Packet

Status: `ACCEPTED_OPTION_A_PARK_PULLBACK`
Decision date: `2026-07-29`
Scope: documentation-only

## Decision Outcome

Alex accepted Option A on 2026-07-29 using the decision:

`ACCEPT_SWING_PC_003_OPTION_A_PARK_PULLBACK_V1`

Final lane state: `PARKED_INCONCLUSIVE`.

Option B and `SWING-PC-003A` are `NOT_AUTHORIZED`.

## 1. Decision Record

Options considered:

- `OPTION_A_PARK_PULLBACK` - park PULLBACK as the next profile lane.
- `OPTION_B_ONE_BOUNDED_ROBUSTNESS_APPENDIX` - authorize one final
  existing-artifact-only robustness appendix before parking or rejecting the lane.

Accepted outcome: `OPTION_A_PARK_PULLBACK`.

Parking is not a claim that PULLBACK can never work. It means the current evidence
does not justify further PULLBACK-specific delivery, profile design, serious
qualification, or trading action. The evidence remains available for future review
if a separately authorized research lane produces genuinely new independent
evidence.

## 2. Controlling Evidence

Primary report:
`reports/swing_machine_v0_1/pullback_fill_lifecycle_diagnostic_20260729T130830Z/`

Evidence identities:

- JSON SHA-256:
  `59cc627d6b73ca1137b7bc40b4043f957f1f92faaba564f8f18efc6917d2862f`
- Markdown SHA-256:
  `c57e0eb632248430c8a982865e360457444d88f5b4d8c991154399a832435203`

Current facts:

| Fact | Result |
| --- | ---: |
| Raw accepted PULLBACK observations | 27 |
| Submitted accepted lifecycles | 10 |
| Filled lifecycles | 4 |
| Cancelled lifecycles | 6 |
| Submitted fill rate | 40% |
| Repeated same-symbol observations during an existing lifecycle | 17 |
| Remaining unexplained no-order observations | 0 |
| Filled symbols | 1 (`NFLX`) |
| All-accepted 20-session SPY-excess mean | -2.4352% |
| Filled 20-session SPY-excess mean | +0.7578% |
| Filled 20-session SPY-excess median | -1.8988% |
| Cancelled 20-session SPY-excess mean | -0.2870% |
| Repeated-observation 20-session SPY-excess mean | -3.9448% |
| Diagnostic verdict | `INCONCLUSIVE` |

The 17 repeated observations are now explained through dated same-symbol lifecycle
overlap. Six occurred while an entry was pending and eleven while a position was
open. This resolves the historical no-order ambiguity but does not increase the
four-trade filled sample.

## 3. Original Gate Reconciliation

The controlling criteria come from
`SWING-PC-001_pullback_fill_lifecycle_research_design.md`.

### GO criteria

| Criterion | Result | Reason |
| --- | --- | --- |
| Positive benchmark-relative expectancy after costs | `PARTIAL` | Filled mean is positive and cost-stressed PnL remains positive, but the filled median 20-session excess is negative and benchmark/cost evidence is not a larger independent sample. |
| Effect extends beyond the original tiny traded sample | `FAIL` | The filled population remains the same four trades. |
| Filled rows materially outperform untraded accepted rows | `DIRECTIONAL_PASS` | Filled mean 20-session excess is +0.7578% versus -2.9906% for untraded accepted rows. |
| Result is not dominated by one symbol/date cluster | `FAIL` | Every filled trade is NFLX; NFLX is 15 of 27 accepted observations. |
| Lifecycle mechanics explain the separation | `PARTIAL_PASS` | Existing-lifecycle suppression explains all 17 no-order rows, but four fills versus six cancellations cannot establish a durable selection effect. |
| Provider limitations documented and accepted | `PASS_AS_LIMITATION` | The limitations and acquisition stop condition are controlled by `10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md`. |

No profile-design GO is available.

### Stop conditions

| Stop condition | Result |
| --- | --- |
| Diagnostic cannot expand evidence beyond the existing small traded subset | `TRIGGERED` |
| Positive evidence is driven by one symbol/date concentration | `TRIGGERED` |
| Work would require profile/config changes to answer the question | `NOT_TRIGGERED`; such changes remain prohibited |
| Work drifts into profile, paper, live, or broker action | `NOT_TRIGGERED`; all gates remained closed |

The first two stop conditions are sufficient to stop treating PULLBACK as the next
profile lane.

## 4. Option Comparison

| Dimension | Option A - Park PULLBACK | Option B - One robustness appendix |
| --- | --- | --- |
| New independent fills | None claimed | Cannot create any |
| New data/API/Vault work | None | Prohibited |
| Expected information gain | High enough for resource allocation: acknowledges current limit | Low: can quantify fragility but cannot close sample or symbol concentration |
| Overfitting risk | Low | Higher because the same four observed trades are repeatedly sliced |
| Alignment with original stop conditions | Direct | Exception requiring explicit Product Owner choice |
| Profile/paper/live authority | None | None |
| Recommended | Yes | No |

## 5. Accepted Option A - Park PULLBACK

Accepted effects:

- Set the PULLBACK next-profile lane to `PARKED_INCONCLUSIVE`.
- Preserve the current report and source hashes as the closing evidence packet.
- Do not build or revise a PULLBACK profile.
- Do not run serious qualification, paper trading, live trading, or broker actions.
- Do not reopen provider or historical-data acquisition for PULLBACK.
- Allow PULLBACK to re-enter only if a separately authorized broader research lane
  produces genuinely new independent evidence, not another slice of the same four
  trades.
- The next possible task becomes a docs-only broader hypothesis-search design;
  that task is not authorized by this packet.

Exact acceptance string:

`ACCEPT_SWING_PC_003_OPTION_A_PARK_PULLBACK_V1`

## 6. Option B - One Bounded Robustness Appendix - Not Selected

This option was not selected and is not authorized. Its retained specification
records the considered alternative; it does not provide implementation authority.

Proposed ticket: `SWING-PC-003A - PULLBACK opportunity-level robustness appendix`

Allowed inputs:

- Only the source artifacts and SHA-256 identities already embedded in
  `pullback_fill_lifecycle_diagnostic_20260729T130830Z`.
- Existing repo code required to reproduce the diagnostic.

Allowed changes:

- `src/swingmachine/pullback_diagnostic.py`
- `tests/test_pullback_diagnostic.py`
- One new timestamped report directory under
  `reports/swing_machine_v0_1/pullback_opportunity_robustness_<timestamp>/`
- A result update to current project-control documents.

Required analysis:

- Collapse repeated accepted observations into their ten submitted lifecycle
  anchors without double counting.
- Compare the four filled and six cancelled lifecycles on predefined 5-, 10-, and
  20-session benchmark-excess outcomes.
- Report exact small-sample intervals or permutation results without converting
  them into proof.
- Run leave-one-trade-out sensitivity for the four filled trades.
- Report symbol and date concentration explicitly.
- Preserve costs, provider limitations, missing fields, and all existing gate
  statuses.

Hard bounds:

- No external network, API, broker, runtime, Vault, or database action.
- No new dataset, account, API key, repository hunt, package, or broad download.
- No strategy/config/profile change.
- No more than one implementation/report iteration.
- Stop immediately after the report and focused tests, regardless of outcome.

Acceptance for any continued PULLBACK research would require all of:

1. filled-minus-cancelled 20-session benchmark excess is positive in both mean and
   median;
2. leave-one-trade-out filled expectancy remains positive in every case;
3. the result is not dependent on a single exit path or date cluster; and
4. the packet identifies genuinely new independent evidence that could close the
   one-symbol/four-trade blocker.

The fourth condition cannot be satisfied from the current fixed artifacts. Option B
therefore cannot authorize a profile; its maximum useful result is a more formal
parking decision.

Historical alternative authorization string, retained for audit only and not
active:

`AUTHORISE_SWING_PC_003_OPTION_B_ROBUSTNESS_APPENDIX_V1`

## 7. Decision Rationale

Alex accepted `OPTION_A_PARK_PULLBACK`.

The bounded diagnostic answered the unresolved lifecycle question: the 17 no-order
rows were repeated observations during an existing symbol lifecycle. It did not
produce new independent fills. The remaining problem is evidence quantity and
concentration, not an unexamined join or classification ambiguity. Repeatedly
reworking the same four NFLX trades would add precision to the warning, not evidence
for a profile.

## 8. Gate Confirmation

- Revised PULLBACK profile: `NOT_AUTHORIZED`
- Serious full qualification: `BLOCKED`
- Paper trading: `BLOCKED`
- Live trading: `PROHIBITED`
- Broker/API/runtime action: `NOT_AUTHORIZED`
- Data acquisition: `STOPPED`
- TIGHT_BASE: remains isolated

This packet records Alex's final Option A decision. It did not authorize a
follow-on research lane. The later `SWING-PC-005` authorization covers a
documentation/design task only and does not alter the parked PULLBACK state.
