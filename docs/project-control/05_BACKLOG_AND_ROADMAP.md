# 05 Backlog and Roadmap - swingmachine

## Active milestone

**Research Validity Recovery**

Determine whether the current MPS research evidence is trustworthy enough to support
strategy-selection decisions before repairing the engine, acquiring more data, opening
validation/holdout gates, or designing another strategy candidate.

## Goal

Resolve the highest-value uncertainty first: did H1/H2 genuinely fail a valid strategy
screen, or were they evaluated through a population, lifecycle, price-series,
partition-accounting, or provenance path that is not suitable for programme-level
strategy selection?

Until that is answered:

- preserve `SWING-PC-006` as evidence;
- do not treat its programme-level meaning as final;
- keep H1/H2 parked;
- keep PULLBACK `PARKED_INCONCLUSIVE`;
- keep TIGHT_BASE isolated;
- keep Gate 2 and the frozen holdout unopened;
- do not build another profile;
- do not acquire additional data by inference;
- keep paper/live blocked.

## Delivery model

DeliveryOS 1.0.0 issue-as-contract is the default bounded-work mechanism.

- ChatGPT creates and maintains the authoritative GitHub issue contract.
- Codex executes only that frozen contract.
- Repository changes use an issue-linked branch and PR.
- Detailed evidence is posted to the issue.
- Chat handoff is compact.
- ChatGPT reviews independently.
- Sponsor explicitly accepts/revises/rejects/rolls back before merge/closure.
- Trading212 is read-only from SwingMachine unless separately authorised by the Sponsor.

## Success criteria for this milestone

- The five research-validity concerns are individually proven, rejected, or left
  explicitly inconclusive with exact evidence.
- `SWING-PC-006` receives one defensible evidence verdict:
  `VALID_FOR_STRATEGY_SELECTION`, `VALID_ONLY_FOR_COHORT_DIAGNOSTIC`,
  `INVALID_FOR_STRATEGY_SELECTION`, or `INCONCLUSIVE_PROVENANCE`.
- H1/H2 receive one controlled evidence status rather than being silently repaired or
  promoted.
- No Gate 2, holdout, new strategy screen, revised profile, provider acquisition,
  paper or live progression occurs during the audit.
- The next implementation/data task is chosen from the highest-severity confirmed
  blocker rather than from speculation.

## Now

1. **SWING-DELIVERY-001 — Activate DeliveryOS GitHub-first control-room workflow.**
   - Governance/documentation only.
   - Make issue-as-contract, branch/PR delivery, issue evidence and compact handoff the
     default.
   - Preserve all trading/research safety gates.

2. **SWING-PC-007 — MPS Research Validity Recovery Audit.**
   - Audit only; minimal synthetic reproductions are allowed.
   - Five areas: discovery-population suitability, carried-position intraday stops,
     price-series semantics, partition-end open-position accounting, and
     report-to-code/config/data provenance.
   - Do not fix defects or rerun the strategy screen.
   - This task must be issued as a DeliveryOS GitHub issue contract before Codex starts.

## Next

Conditional on `SWING-PC-007` evidence:

- If a mechanical validity defect is confirmed: specify and repair only the
  highest-severity defect, with focused tests and exact lineage evidence.
- If current evidence is valid only for a special cohort: specify the representative
  point-in-time daily research population required for strategy discovery.
- If provenance is insufficient: specify the SwingMachine-native decision/lineage and
  reconstructable evidence contract before another screen.
- If the engine/evidence is valid for strategy selection: only then decide whether the
  next move is a fresh hypothesis or a separately preregistered validation step.

Only one of these becomes `Now` after Sponsor review; do not run them in parallel by
inference.

## Later

- Specify SwingMachine-native strategy outcome and lineage contracts, including
  explicit target and reward-to-risk semantics, using proven domain-neutral research
  control patterns rather than Trading212 runtime assumptions.
- Build/admit a representative broad daily-bar research population when an exact data
  contract is known.
- Evaluate Databento or another provider only against that exact requirement. Unused
  Databento credit is available but is not acquisition authority.
- Run a new preregistered strategy screen only after engine, population and provenance
  validity are controlled.
- Reconsider paper/manual observation only after valid offline evidence and separate
  Sponsor approval.
- Consider shared-package extraction only if both projects independently prove stable,
  genuinely domain-neutral interfaces; do not create cross-repo runtime imports now.

## Blocked

- Gate 2: blocked pending research-validity decision.
- Frozen holdout: blocked and unopened.
- Revised baseline/profile: blocked pending valid evidence.
- New strategy screen: blocked pending validity recovery.
- Provider/data acquisition: blocked until an exact decision-critical requirement
  satisfies `10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md` and receives a new issue
  contract.
- Paper trading: blocked.
- Live trading: prohibited.
- Direct broker integration: not authorised.
- Trading212 mutation from SwingMachine: prohibited without separate Sponsor-approved
  Trading212 authority.
- Shared cross-repo package extraction: blocked until interfaces are independently
  stable and proven domain-neutral.

## Rejected / Not now

- Treat `NO_FAMILY_PASSES_DISCOVERY` as a final programme-level momentum-family
  rejection before validity audit.
- Tune H1/H2 to repair the prior result.
- Open validation/holdout to rescue discovery.
- Buy more historical data because provider credit exists.
- Merge the SwingMachine and Trading212 repos.
- Add a runtime dependency from SwingMachine to Trading212.
- Reuse ORB/minute-bar/targetless/15:55 force-flat semantics in SwingMachine.
- Build another profile variant without a valid evidence path.
- Use large chat prompts as the durable Codex contract once DeliveryOS GitHub-first
  workflow is active.

## Recently completed

- Repo house alignment and accepted DeliveryOS 1.0.0 pin.
- Current project-control source pack.
- `SWING-PC-001` through `SWING-PC-006` research/design sequence.
- PULLBACK set to `PARKED_INCONCLUSIVE`; TIGHT_BASE isolated.
- `SWING-PC-005A` stopped at source/temporality Gate 0.
- `SWING-PC-006` returned `NO_FAMILY_PASSES_DISCOVERY` with Gate 2/holdout unopened.
- Cross-project `SWING-XR-001` reuse/boundary audit completed locally and accepted as
  working architecture evidence with a stale-Trading212-snapshot caveat; it does not
  authorise Trading212 mutation.

## Next recommended Codex task

`SWING-PC-007 — MPS Research Validity Recovery Audit`

The authoritative task contract must live in GitHub. Codex should receive a compact
pointer to that issue rather than a duplicated long-form chat contract.
