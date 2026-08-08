# Swing Machine v0.1 Delivery Plan

Created: 2026-05-05
Target baseline candidate: `swing_machine_v0_1`

Documentation location decision: `docs/` is the existing repository location for delivery and operating documents.

## 1. Delivery principles

| Principle | Meaning |
| --- | --- |
| Baseline first | Build a coherent, explainable, testable baseline before chasing performance. |
| Explicit config only | Strategy behaviour lives in serialisable profile/config, not hidden `.env` switches. |
| Typed contracts | Prefer pydantic/dataclass contracts over loose dictionaries for baseline surfaces. |
| Explain every decision | Every accept/reject/size/order/hold/exit decision needs machine-readable reasons. |
| Parity from the start | Research, replay, paper, and shadow paths must share contracts or produce comparable artifacts. |
| Instrumentation is product | Reports and manifests are first-class deliverables. |
| Safety boundary | No live broker, production deployment, scheduler, destructive database change, or real order routing without explicit approval. |
| No dead time | If a task is blocked, record the blocker and move to another safe unblocked task. |

## 2. Epics

| Epic | Objective |
| --- | --- |
| Discovery and governance | Document actual current state and define v0.1 boundary. |
| Baseline profile/config | Tie explicit config to baseline id, manifest, and freeze status. |
| Data and universe foundation | Govern data contracts, universe members, and data fail-closed rules. |
| Candidate generation | Build typed candidate and eligibility outputs. |
| Signal feature snapshot | Ensure every signal can explain its features and setup evidence. |
| Eligibility gates | Introduce consistent gate/rejection reason taxonomy. |
| Quality scoring and ranking | Expose deterministic score, percentile, rank, and tie-breaks. |
| Risk and portfolio constraints | Explain and test per-trade and portfolio-level sizing. |
| Order planning | Produce safe, deduped, explainable paper/shadow order plans. |
| Trade lifecycle and exits | Record state transitions and exit decisions. |
| Research/runtime parity | Add checks that selected decisions match across paths. |
| Reporting and instrumentation | Produce manifest, reports, traces, and review surfaces. |
| QA and qualification | Add unit, contract, parity, smoke, dry-run, and selected-period gates. |
| Release/freeze process | Define and execute baseline freeze review when evidence is ready. |

## 3. Definition of Ready

A task is ready when:

| Requirement | Rule |
| --- | --- |
| Scope | A specific component, contract, report, or test is named. |
| Safety | The task does not require live trading, production deployment, destructive migration, or broker credentials. |
| Inputs | Required existing modules/files are known or discoverable locally. |
| Acceptance | At least one observable acceptance criterion is defined. |
| Tests | Relevant test tier is identified, or the task is docs-only. |
| Config | Any strategy behaviour change is explicit in profile/config and documented. |

## 4. Definition of Done

A task is done when:

| Requirement | Rule |
| --- | --- |
| Implementation | Code/docs/tests are updated as scoped. |
| Contracts | Typed models reject invalid or hidden fields where practical. |
| Explainability | Decision outputs include reason/evidence fields. |
| Safety | No live broker/deployment/destructive DB side effect was introduced. |
| Tests | Focused tests/checks were run or a reason is recorded. |
| Documentation | Backlog and implementation log are updated. |

## 5. Acceptance criteria format

Each backlog item should include:

| Field | Meaning |
| --- | --- |
| Given | Preconditions and input artifacts. |
| When | Action or command/module call. |
| Then | Expected output, contract, report, or test result. |
| And | Safety/instrumentation/negative-case expectations. |

## 6. Test gates

| Change type | Required gate |
| --- | --- |
| Docs only | Markdown review by content; no runtime test required. |
| Pure contract model | Focused unit/contract tests plus Ruff on changed code. |
| Config/profile | Config load/hash tests and negative validation tests. |
| Data validators | Focused validator tests and relevant replay precondition test. |
| Candidate/signal/risk logic | Unit tests plus deterministic fixture test. |
| Runtime/reporting wiring | Focused CLI/service tests with temp DB/output. |
| Replay/parity | Replay workflow tests on tiny/selected fixture. |
| Release/freeze | Ruff, typed-core mypy, focused plus full pytest where practical. |

## 7. Documentation expectations

| Area | Documentation rule |
| --- | --- |
| Assumptions | Record in current-state, baseline, design, or implementation log. |
| Architecture decisions | Record in decision log section or a future ADR file. |
| Config changes | Update profile comments/docs and baseline manifest implications. |
| New report fields | Document field meaning and source. |
| Blockers | Record blocker, missing information, and next unblocked task. |
| Validation | Record exact command/check and result in implementation log. |

## 8. Decision log

Decision records should use this format:

| Field | Required content |
| --- | --- |
| Decision ID | Example: `SWING-ADR-001`. |
| Date | Absolute date. |
| Context | What problem forced the decision. |
| Decision | The chosen option. |
| Alternatives | Plausible alternatives rejected. |
| Consequences | Tradeoffs and follow-up work. |

Initial decisions:

| ID | Date | Decision |
| --- | --- | --- |
| `SWING-ADR-001` | 2026-05-05 | Treat `swing_machine_v0_1` as a governed baseline candidate wrapper around existing explicit v2 profile logic, not as a new performance variant. |
| `SWING-ADR-002` | 2026-05-05 | Keep `.env` infrastructure-only and prohibit hidden environment-controlled strategy behaviour. |
| `SWING-ADR-003` | 2026-05-05 | Keep live trading, production deployment, and live broker integration out of v0.1. |

## 9. Blocker handling

If blocked:

| Step | Action |
| --- | --- |
| 1 | Mark the backlog item `blocked`. |
| 2 | Record the exact missing input or unsafe choice. |
| 3 | Add follow-up work if needed. |
| 4 | Move to the next safe unblocked item. |
| 5 | Ask for input only if all useful progress is blocked or a safety-sensitive choice is unavoidable. |

## 10. Release/freeze process

Before `swing_machine_v0_1` can be frozen:

| Gate | Required evidence |
| --- | --- |
| Profile freeze | Explicit config path and config hash. |
| Manifest | Baseline manifest says all mandatory checks are satisfied. |
| Data contract | Historical panel manifests validate for selected qualification data. |
| Contract coverage | Candidate, signal, risk, order, lifecycle, exit, rejection, and report contracts exist. |
| Test evidence | Unit, contract, smoke, dry-run, and parity tests pass. |
| Replay evidence | Selected-period replay artifacts are deterministic and reviewable. |
| Paper/shadow evidence | Runtime comparison artifacts are generated without live broker. |
| Review status | Operator review report passes configured strict thresholds. |
| Safety review | Live/full execution remains prohibited unless separately approved. |

## 11. Qualification stages

| Stage | Purpose |
| --- | --- |
| Unit tier | Prove individual formulas/contracts/gates. |
| Contract tier | Prove serialisable models and validators. |
| Smoke tier | Prove CLI/services run on tiny fixtures. |
| Dry-run tier | Prove paper/shadow workflow creates no real orders. |
| Selected-period research qualification | Prove deterministic selected historical decisions and reports. |
| Paper/runtime comparison | Compare paper/shadow decisions and fills over controlled local samples. |
| Baseline freeze review | Review manifest, reports, blockers, and safety boundary. |

## 12. No-dead-time operating model

Work loop:

1. Pick the next `safe to implement immediately: yes` backlog item.
2. Inspect only the relevant files not already inspected for the task.
3. Implement the smallest coherent contract/report/test change.
4. Run focused tests/checks where practical.
5. Fix failures caused by the change.
6. Update backlog status and implementation log.
7. Move to the next unblocked item.

Do not stop after planning. Stop only for live-trading risk, destructive change, real broker execution, or a material architecture fork that cannot be safely assumed.

## Additional decision records

| ID | Date | Context | Decision | Consequences |
| --- | --- | --- | --- | --- |
| `SWING-ADR-004` | 2026-05-05 | v0.1 needs honest portfolio-risk boundaries without overclaiming a correlation model. | Defer explicit correlation enforcement from `swing_machine_v0_1`; keep position concentration, sector concentration, portfolio heat, daily new risk, and duplicate-symbol exposure as the enforced baseline constraints. | Baseline reports and qualification notes must state that correlation risk is a known v0.1 gap. A later version may add a simple correlation or factor-exposure proxy only through explicit config and tests. |
