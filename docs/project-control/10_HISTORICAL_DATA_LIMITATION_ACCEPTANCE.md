# Historical Data Limitation Acceptance - swingmachine

Status: `ACCEPTED_RESEARCH_LIMITATION`
Decision date: `2026-07-29`
Task: `SWING-MPS-DATA-001`

## Decision

The remaining historical-data unknowns are accepted as a documented limitation for
the current offline research phase. SwingMachine will use the evidence already
acquired, mask unresolved fields and rows fail closed, and return to the bounded
PULLBACK fill/lifecycle research lane.

This decision stops indefinite data acquisition. It does not convert partial data
into qualification-grade evidence and does not waive any research, profile, paper,
live, broker, or deployment gate.

## Evidence Accepted As Partial

| Evidence | Current result | Evidence identity |
| --- | --- | --- |
| Historical security classification | 82-symbol cohort: 79 historical common-stock symbols, OCFT and TURN historical non-common, BLOX unresolved because of ticker reuse. Classification gate failed; `PARTIAL_RESEARCH_ONLY`. | Summary SHA-256 `b375a3c09eee56c4d827520dfc20843b4504669c6c6511765cc8d335f806c40f`; output SHA-256 `6fb20f08650297eb2d6f9e5c07fc98821963e5ca438882d59559fb2ceee53ddf`. |
| Point-in-time SEC reference panel | 208,240 rows: 170,232 common-reference-available rows and 34,267 common-reference-unavailable rows. STLE has no reference evidence. Historical-window and sector gates failed; `PARTIAL_RESEARCH_ONLY`. | Summary SHA-256 `8923933a52e9611fcdc10d873397f4e1c68d62233c0e745134f7428e467b9705`; output SHA-256 `5d093211024625635d603a8a9bda2150198a5b673da41c8b26d3047006daa960`. |
| Feature-ready panel | 208,240 rows, 23,951 eligible rows across 25 symbols. BLOX, OCFT, and TURN are classification-blocked; 34,267 common-stock rows have unknown sector; 39,782 rows lack shares evidence; HLXB and STLE are fully shares-masked. Only the provider total-return cross-check passed. Qualification remains false and the decision is `PARTIAL_RESEARCH_ONLY`. | Summary SHA-256 `7cf6dd26d7fc0b1ddde13bcfa284c48b969988c638efc112fa31519adcd722c1`; feature-input SHA-256 `664c4c5664851f58a5d3d6a0ba116bce44a2c4106830c0663749a918ea028251`; computed-features SHA-256 `3da1df73028a4cb8c67d75cc99f9583bf98562ea1941d111ab6b920b8b2ea731`. |

The summaries are held under
`/home/alexballard92/.local/share/swingmachine-data-staging/`. Their absolute
paths are local evidence locations, not portable runtime dependencies.

## Accepted Operating Policy

- Use only rows whose required evidence is present and whose gates pass for the
  bounded research question.
- Preserve `unknown`, unavailable, unresolved, and masked states. Do not infer
  classification, sector, shares, halt state, or point-in-time facts merely to
  increase coverage.
- Keep the feature-ready panel marked `PARTIAL_RESEARCH_ONLY` and
  `qualification_usable=false`.
- Treat results from the eligible subset as bounded exploratory evidence, not as a
  population-complete or qualification-grade backtest.
- Retain immutable artifact paths and SHA-256 identities when an evidence packet
  depends on these data.
- Fail closed if a later task requires one of the unresolved fields or a gate that
  is currently false.

## Acquisition Stop Condition

No further API account, API key, paid feed, broad repository/dataset hunt, bulk
database download, or Vault transfer is justified for this lane unless a future
human-authorised bounded task:

1. names the exact unresolved field and population required;
2. shows that the field is decision-critical rather than merely desirable;
3. identifies a source that can materially close the gap;
4. defines a size, time, request, and storage bound; and
5. defines a stop condition before acquisition begins.

Absent all five conditions, work must use the proven subset, preserve unknowns, or
report the requested test as unavailable.

## Return To PULLBACK Research

The current bounded evidence is:

- Report:
  `reports/swing_machine_v0_1/pullback_fill_lifecycle_diagnostic_20260729T130830Z/`
- Report identities: JSON SHA-256
  `59cc627d6b73ca1137b7bc40b4043f957f1f92faaba564f8f18efc6917d2862f`;
  Markdown SHA-256
  `c57e0eb632248430c8a982865e360457444d88f5b4d8c991154399a832435203`.
- Verdict: `INCONCLUSIVE`.
- Raw accepted PULLBACK observations: 27.
- Submitted accepted lifecycles: 10; 4 filled and 6 cancelled; submitted fill rate
  40%.
- Repeated same-symbol observations during an existing lifecycle: 17; 6 while an
  entry was pending and 11 while a position was open.
- Remaining unexplained no-order observations: 0.
- The overlap classification is derived from dated lifecycle artifacts and the
  explicit `PENDING_ENTRY_EXISTS` / `OPEN_POSITION_EXISTS` portfolio rules; it is
  not represented as a directly recorded historical rejection code.
- All-accepted 20-session SPY-excess mean remains negative, while the four filled
  rows are directionally positive but too small and concentrated to support a
  profile build.

## Authority Boundaries

- Revised profile: `NOT_AUTHORIZED`
- Serious full qualification: `BLOCKED`
- Paper trading: `BLOCKED`
- Live trading: `PROHIBITED`
- Broker/API/runtime actions: `NOT_AUTHORIZED`
- Further data acquisition: stopped unless the bounded five-part condition above
  receives explicit human authorization

Alex subsequently accepted `SWING-PC-003` Option A. PULLBACK is
`PARKED_INCONCLUSIVE`; the bounded robustness appendix was not authorized. This
decision does not authorize a strategy profile, a follow-on research lane, or any
trading action. The separately authorized `SWING-PC-005` work is a design-only
existing-data task and does not alter this acquisition stop condition.
