# External Help Handoff

## Canonical starting point

- Repository: `Aballard92/swingmachine`
- Alignment branch: `agent/house-alignment-20260808`
- Alignment base: `a9b203870383961494991ea65efd0f40cc66e4a1`
- Canonical handoff revision: the reviewed Git commit containing this file.
- Current authority: this directory, in the precedence order defined by
  `AGENTS.md`.

Do not start from an older local folder, generated report, paper-readiness
runbook, or historical design document. Confirm the repository, branch, HEAD,
working-tree state, and current project-control files before proposing work.

## Current product decision

- Phase: controlled offline research and qualification only.
- Revised baseline candidate: none selected.
- PULLBACK: `PARKED_INCONCLUSIVE`.
- H1 and H2: parked after `NO_FAMILY_PASSES_DISCOVERY`.
- Frozen holdout: unopened.
- TIGHT_BASE: isolated unless explicitly redesigned and requalified.
- Indefinite acquisition: stopped; the five-part exception in
  `10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md` controls any future proposal.
- Paper trading: blocked.
- Live trading: prohibited.
- Current strategy implementation ticket: none authorized.

## How outside help should engage

1. Read `AGENTS.md` and the current files in `docs/project-control/`.
2. State the exact task ID, allowed files, prohibited files, permitted checks,
   and Git/GitHub permissions before changing anything.
3. Keep proposals separate from accepted decisions. Do not infer a new strategy,
   data-acquisition lane, profile, runtime command, or roadmap priority.
4. Treat `docs/archive/`, older `docs/` material, and generated reports as
   historical evidence only.
5. Preserve fail-closed data handling and explicit configuration behavior.
6. Return evidence in the Definition of Done format in `AGENTS.md`.

## Safe initial contribution lanes

Suitable first tasks are read-only review, test-quality improvements, a bounded
reduction of the legacy strict-typing debt recorded in
`08_OPEN_RISKS_AND_QUESTIONS.md`, portable developer tooling, documentation
consistency, or a bounded design proposal.
Strategy research, source acquisition, holdout access, profile construction,
paper/runtime work, and broker/API access require a new explicit authorization.

## Baseline verification

The alignment pull request records the authoritative command results for lint,
core typing, full tests, DeliveryOS conformance, and repository hygiene. A helper
should re-run only the checks authorized for their task and report exact results;
passing tests are engineering evidence, not evidence of trading edge.
