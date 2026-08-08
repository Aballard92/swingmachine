# Swing Machine v0.1 Autonomous Backlog

Created: 2026-05-05
Target baseline candidate: `swing_machine_v0_1`

Documentation location decision: this backlog is created under `docs/`, matching existing repository planning documents.

## Ordering rule

Work from top to bottom. If blocked, record the blocker and continue to the next safe unblocked item.

## Activities

### SWING-V01-001

| Field | Value |
| --- | --- |
| Title | Current-state review |
| Epic | Discovery and governance |
| Objective | Document actual repository state and maturity. |
| Why it matters | Prevents treating an existing v2 design/build system as either empty or already qualified. |
| Files/modules likely affected | `docs/swing_machine_current_state_review.md` |
| Implementation steps | Inspect repo docs/source/tests; map existing capabilities; identify gaps and risks. |
| Dependencies | None. |
| Tests to add or update | None; docs-only. |
| Acceptance criteria | Review is specific to repository files and identifies existing state, gaps, risks, and recommendation. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-002

| Field | Value |
| --- | --- |
| Title | Baseline definition |
| Epic | Discovery and governance |
| Objective | Define what `swing_machine_v0_1` means mechanically and operationally. |
| Why it matters | Establishes a target baseline without performance chasing. |
| Files/modules likely affected | `docs/swing_machine_v0_1_baseline_definition.md` |
| Implementation steps | Define purpose, boundaries, horizon, universe, candidate, gates, score, ranking, risk, lifecycle, reports, qualification, non-goals. |
| Dependencies | SWING-V01-001. |
| Tests to add or update | None; docs-only. |
| Acceptance criteria | Baseline definition states serious full run is prohibited until required checks pass. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-003

| Field | Value |
| --- | --- |
| Title | Solution design |
| Epic | Discovery and governance |
| Objective | Produce implementation-ready architecture and contracts. |
| Why it matters | Gives the build sequence and target components. |
| Files/modules likely affected | `docs/swing_machine_v0_1_solution_design.md` |
| Implementation steps | Define architecture, domain model, data contracts, config, parity, signal, risk, order, instrumentation, reporting, tests, risks, build sequence. |
| Dependencies | SWING-V01-002. |
| Tests to add or update | None; docs-only. |
| Acceptance criteria | Another engineer can identify what modules/contracts/reports need to be built. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-004

| Field | Value |
| --- | --- |
| Title | Agile delivery plan |
| Epic | Discovery and governance |
| Objective | Define delivery principles, gates, qualification, and no-dead-time model. |
| Why it matters | Keeps autonomous work safe and auditable. |
| Files/modules likely affected | `docs/swing_machine_v0_1_delivery_plan.md` |
| Implementation steps | Define epics, DoR, DoD, acceptance format, test gates, docs expectations, decision log, blockers, release/freeze, qualification stages. |
| Dependencies | SWING-V01-003. |
| Tests to add or update | None; docs-only. |
| Acceptance criteria | Delivery plan defines how work is tracked, tested, and frozen. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-005

| Field | Value |
| --- | --- |
| Title | Autonomous backlog and implementation log |
| Epic | Discovery and governance |
| Objective | Create ordered backlog and log format. |
| Why it matters | Enables safe autonomous progression. |
| Files/modules likely affected | `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Implementation steps | Create activity IDs, fields, dependencies, safety flags, and initial log entries. |
| Dependencies | SWING-V01-004. |
| Tests to add or update | None; docs-only. |
| Acceptance criteria | Backlog includes all mandatory areas and implementation log records completed/blocked work. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-006

| Field | Value |
| --- | --- |
| Title | Baseline manifest contract |
| Epic | Baseline profile/config |
| Objective | Add typed manifest for `swing_machine_v0_1`. |
| Why it matters | Binds baseline id, profile/config hash, qualification checks, and serious-run permission. |
| Files/modules likely affected | `src/swingmachine/baseline.py`, `tests/test_baseline.py` |
| Implementation steps | Add manifest/check models; add builder from `StrategyRuntimeConfig`; test config hash, env policy, and qualification status. |
| Dependencies | SWING-V01-002, SWING-V01-003. |
| Tests to add or update | Focused baseline tests. |
| Acceptance criteria | Manifest is serialisable, explicit, defaults to serious full run prohibited, and allows only when all mandatory checks are satisfied. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-007

| Field | Value |
| --- | --- |
| Title | Explicit swing profile alias |
| Epic | Baseline profile/config |
| Objective | Decide whether v0.1 gets a new profile file or manifest alias to existing v2 config. |
| Why it matters | Avoids confusing `RF_TPC_V2` strategy version with `swing_machine_v0_1` baseline governance. |
| Files/modules likely affected | `config/` or root YAML, docs, tests. |
| Implementation steps | Add explicit profile alias or copied frozen profile only if needed; document source and config hash. |
| Dependencies | SWING-V01-006. |
| Tests to add or update | Config load/hash test. |
| Acceptance criteria | Baseline profile path is unambiguous and serialisable. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-008

| Field | Value |
| --- | --- |
| Title | `.env` strategy-behaviour isolation test |
| Epic | Baseline profile/config |
| Objective | Guard against hidden environment-controlled strategy behaviour. |
| Why it matters | Reproducibility depends on explicit config only. |
| Files/modules likely affected | `.env.example`, `tests/test_config.py` or `tests/test_baseline.py` |
| Implementation steps | Document allowed env keys; test baseline manifest policy; ensure no strategy keys are advertised. |
| Dependencies | SWING-V01-006. |
| Tests to add or update | Contract/config policy tests. |
| Acceptance criteria | Env policy is test-covered and `.env.example` remains infrastructure-only. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-009

| Field | Value |
| --- | --- |
| Title | Typed swing candidate model |
| Epic | Candidate generation |
| Objective | Add a first-class candidate contract. |
| Why it matters | Separates reviewable candidate from setup/order intent. |
| Files/modules likely affected | `src/swingmachine/baseline.py` or new `src/swingmachine/swing_contracts.py`, tests. |
| Implementation steps | Define candidate id, symbol/session, feature snapshot reference, gates, score, rank, reasons. |
| Dependencies | SWING-V01-006. |
| Tests to add or update | Contract validation tests. |
| Acceptance criteria | Candidate serialises deterministically and rejects missing required fields. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-010

| Field | Value |
| --- | --- |
| Title | Typed swing signal model |
| Epic | Signal feature snapshot |
| Objective | Add signal contract connecting candidate to setup/order planning. |
| Why it matters | Makes candidate-to-intended-trade transition explainable. |
| Files/modules likely affected | `src/swingmachine/swing_contracts.py`, tests. |
| Implementation steps | Define signal id, candidate id, setup fields, regime, quality score, eligibility result, source config hash. |
| Dependencies | SWING-V01-009. |
| Tests to add or update | Contract validation tests. |
| Acceptance criteria | Signal can represent approved and rejected setup transitions. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-011

| Field | Value |
| --- | --- |
| Title | Feature snapshot baseline wrapper |
| Epic | Signal feature snapshot |
| Objective | Add baseline metadata around existing `FeatureSnapshot`. |
| Why it matters | Reports need baseline id, config hash, and data contract version. |
| Files/modules likely affected | Contracts/reporting tests. |
| Implementation steps | Wrap or extend reports without breaking existing `FeatureSnapshot`. |
| Dependencies | SWING-V01-009. |
| Tests to add or update | Contract/report tests. |
| Acceptance criteria | Feature snapshots in baseline reports identify profile/config/data source. |
| Safe to implement immediately | yes |
| Blocks later work | no |
| Status | complete |

### SWING-V01-012

| Field | Value |
| --- | --- |
| Title | Data contract version in baseline artifacts |
| Epic | Data and universe foundation |
| Objective | Record data contract id/version in manifests and reports. |
| Why it matters | Qualification artifacts must identify data assumptions. |
| Files/modules likely affected | `src/swingmachine/baseline.py`, `data_contracts.py`, replay/reporting tests. |
| Implementation steps | Define constant/version; add to manifest; later propagate to replay/report package. |
| Dependencies | SWING-V01-006. |
| Tests to add or update | Manifest and replay artifact tests. |
| Acceptance criteria | Baseline manifest includes data contract version. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-013

| Field | Value |
| --- | --- |
| Title | Universe member contract |
| Epic | Data and universe foundation |
| Objective | Represent universe eligibility and reference metadata as typed output. |
| Why it matters | Explains why a symbol entered or missed the universe. |
| Files/modules likely affected | New contract module, `signals.py` adapter, tests. |
| Implementation steps | Define member id, symbol, session, metadata, gate results, rejection reasons. |
| Dependencies | SWING-V01-012. |
| Tests to add or update | Contract and universe eligibility tests. |
| Acceptance criteria | Eligible/ineligible symbols have explicit reason records. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-014

| Field | Value |
| --- | --- |
| Title | Candidate generation contract adapter |
| Epic | Candidate generation |
| Objective | Convert `score_candidates` output into typed candidates. |
| Why it matters | Avoids downstream reports scraping dataframes. |
| Files/modules likely affected | `signals.py` or new adapter, tests. |
| Implementation steps | Map scored rows to `SwingCandidate`; include score components, gate reasons, rank fields. |
| Dependencies | SWING-V01-009, SWING-V01-013. |
| Tests to add or update | Deterministic candidate adapter tests. |
| Acceptance criteria | Adapter output is deterministic for fixed fixture. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-015

| Field | Value |
| --- | --- |
| Title | Eligibility gate model |
| Epic | Eligibility gates |
| Objective | Add typed gate result objects. |
| Why it matters | Explains eligibility and rejection consistently. |
| Files/modules likely affected | Contract module, candidate adapter tests. |
| Implementation steps | Define gate category, code, passed flag, evidence, severity. |
| Dependencies | SWING-V01-009. |
| Tests to add or update | Contract tests. |
| Acceptance criteria | Multiple gates can be attached to candidate/signal/risk decisions. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-016

| Field | Value |
| --- | --- |
| Title | Rejection reason taxonomy |
| Epic | Eligibility gates |
| Objective | Replace scattered string reasons over time with machine-readable codes. |
| Why it matters | Reports and parity checks need stable reason codes. |
| Files/modules likely affected | New enum/contract module, later entries/signals/lifecycle adapters. |
| Implementation steps | Define categories: data, universe, regime, trend, setup, event, risk, portfolio, runtime, safety. |
| Dependencies | SWING-V01-015. |
| Tests to add or update | Enum/contract tests. |
| Acceptance criteria | New baseline reports use stable reason codes. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-017

| Field | Value |
| --- | --- |
| Title | Quality scoring design implementation |
| Epic | Quality scoring and ranking |
| Objective | Expose review-facing quality score. |
| Why it matters | Candidate review should not require interpreting raw z-scores. |
| Files/modules likely affected | Candidate adapter, tests. |
| Implementation steps | Map candidate percentile to 0-100 score and expose score components. |
| Dependencies | SWING-V01-014. |
| Tests to add or update | Candidate score tests. |
| Acceptance criteria | Quality score is deterministic and documented as ranking quality, not expected return. |
| Safe to implement immediately | yes |
| Blocks later work | no |
| Status | complete |

### SWING-V01-018

| Field | Value |
| --- | --- |
| Title | Deterministic ranking artifact |
| Epic | Quality scoring and ranking |
| Objective | Emit rank and tie-break fields. |
| Why it matters | Baseline reports must explain candidate ordering. |
| Files/modules likely affected | Candidate adapter/reports, tests. |
| Implementation steps | Sort by score percentile, trend quality, 52-week distance, per-share risk proxy, symbol. |
| Dependencies | SWING-V01-017. |
| Tests to add or update | Ranking determinism tests. |
| Acceptance criteria | Ties resolve predictably and report tie-break values. |
| Safe to implement immediately | yes |
| Blocks later work | no |
| Status | complete |

### SWING-V01-019

| Field | Value |
| --- | --- |
| Title | Risk plan model |
| Epic | Risk and portfolio constraints |
| Objective | Add baseline risk plan wrapper around `EntryPlan`. |
| Why it matters | Risk sizing needs explainable, serialisable output. |
| Files/modules likely affected | New contract/report module, entries tests. |
| Implementation steps | Define budget, per-share risk, quantity derivation, projected heat, reject reasons. |
| Dependencies | SWING-V01-010, SWING-V01-016. |
| Tests to add or update | Contract/risk mapping tests. |
| Acceptance criteria | Approved and rejected entry plans produce complete risk explanations. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-020

| Field | Value |
| --- | --- |
| Title | Portfolio constraint model |
| Epic | Risk and portfolio constraints |
| Objective | Add typed portfolio constraint results. |
| Why it matters | Heat, sector, daily risk, and duplicate exposure must be explainable. |
| Files/modules likely affected | Portfolio manager adapter/tests. |
| Implementation steps | Define constraint code, limit, projected value, pass/fail, affected symbols/sectors. |
| Dependencies | SWING-V01-019. |
| Tests to add or update | Portfolio constraint tests. |
| Acceptance criteria | Batch planning records why later ranked entries are blocked. |
| Safe to implement immediately | yes |
| Blocks later work | no |
| Status | complete |

### SWING-V01-021

| Field | Value |
| --- | --- |
| Title | Order plan model |
| Epic | Order planning |
| Objective | Add explicit order plan separate from broker order. |
| Why it matters | Planned orders must be reviewable before paper/shadow submission. |
| Files/modules likely affected | Contract module, entries/order tests. |
| Implementation steps | Define order plan fields and link to risk plan, signal, intent id, expiry, no-chase boundary. |
| Dependencies | SWING-V01-019. |
| Tests to add or update | Contract/order plan tests. |
| Acceptance criteria | Order plan exists before runtime submission and has no live side effect. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-022

| Field | Value |
| --- | --- |
| Title | Lifecycle state model |
| Epic | Trade lifecycle and exits |
| Objective | Add reportable lifecycle transition model. |
| Why it matters | Baseline must explain state transitions. |
| Files/modules likely affected | Lifecycle/order-state adapters, tests. |
| Implementation steps | Define from_state, to_state, event, reason, evidence, timestamp. |
| Dependencies | SWING-V01-016. |
| Tests to add or update | Lifecycle transition tests. |
| Acceptance criteria | Pending cancel/expire/fill transitions can be reported with reason codes. |
| Safe to implement immediately | yes |
| Blocks later work | no |
| Status | complete |

### SWING-V01-023

| Field | Value |
| --- | --- |
| Title | Exit decision model |
| Epic | Trade lifecycle and exits |
| Objective | Add typed exit decision output. |
| Why it matters | Holds and exits must be explainable. |
| Files/modules likely affected | `exits.py` adapter/tests. |
| Implementation steps | Define decision type, trigger reason, updated stop, next action, evidence. |
| Dependencies | SWING-V01-022. |
| Tests to add or update | Exit decision tests. |
| Acceptance criteria | Stop/trailing/time/earnings decisions produce structured evidence. |
| Safe to implement immediately | yes |
| Blocks later work | no |
| Status | complete |

### SWING-V01-024

| Field | Value |
| --- | --- |
| Title | Research/runtime parity checks |
| Epic | Research/runtime parity |
| Objective | Add explicit parity checks for selected fixtures. |
| Why it matters | Prevents research-only/runtime-only drift. |
| Files/modules likely affected | `replay.py`, `research.py`, tests. |
| Implementation steps | Compare candidate, setup, risk, order, and report fields for fixed symbol/session inputs. |
| Dependencies | SWING-V01-014, SWING-V01-021. |
| Tests to add or update | Parity tests. |
| Acceptance criteria | Differences are reported with field-level reason, not hidden. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-025

| Field | Value |
| --- | --- |
| Title | Baseline reporting package |
| Epic | Reporting and instrumentation |
| Objective | Emit manifest, candidate, risk/order, lifecycle, and qualification artifacts. |
| Why it matters | Review requires a package, not scattered outputs. |
| Files/modules likely affected | `reporting.py`, new baseline/report module, runtime/replay tests. |
| Implementation steps | Add serializers, output paths, and references from review/replay outputs. |
| Dependencies | SWING-V01-006, SWING-V01-014, SWING-V01-021, SWING-V01-022. |
| Tests to add or update | Reporting/CLI tests. |
| Acceptance criteria | A baseline package can be produced without running live/paper orders. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-026

| Field | Value |
| --- | --- |
| Title | Unit test expansion |
| Epic | QA and qualification |
| Objective | Add focused unit tests for new baseline components. |
| Why it matters | Prevents contracts from becoming documentation-only. |
| Files/modules likely affected | `tests/test_baseline.py`, future contract tests. |
| Implementation steps | Add tests alongside each contract/adapter change. |
| Dependencies | Ongoing. |
| Tests to add or update | Unit tests. |
| Acceptance criteria | Every new pure component has at least one positive and one negative test. |
| Safe to implement immediately | yes |
| Blocks later work | no |
| Status | complete |

### SWING-V01-027

| Field | Value |
| --- | --- |
| Title | Smoke tests for baseline package |
| Epic | QA and qualification |
| Objective | Prove manifest/report package generation works on tiny fixture. |
| Why it matters | Baseline should be usable before selected-period qualification. |
| Files/modules likely affected | Replay/reporting tests. |
| Implementation steps | Add smoke test that produces manifest plus existing replay artifacts. |
| Dependencies | SWING-V01-025. |
| Tests to add or update | Smoke tests. |
| Acceptance criteria | Tiny fixture writes baseline package with no live side effects. |
| Safe to implement immediately | yes |
| Blocks later work | no |
| Status | complete |

### SWING-V01-028

| Field | Value |
| --- | --- |
| Title | Dry-run safety tests |
| Epic | QA and qualification |
| Objective | Prove v0.1 commands cannot route live orders. |
| Why it matters | Safety boundary is mandatory. |
| Files/modules likely affected | Runtime tests, baseline tests. |
| Implementation steps | Assert runtime modes remain paper/shadow and no live adapter/config is used. |
| Dependencies | SWING-V01-025. |
| Tests to add or update | Dry-run safety tests. |
| Acceptance criteria | Baseline package generation and replay do not require broker credentials or live adapter. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-029

| Field | Value |
| --- | --- |
| Title | Baseline manifest CLI/report integration |
| Epic | Reporting and instrumentation |
| Objective | Write manifest artifact from replay/report workflows. |
| Why it matters | Qualification packages need manifest evidence. |
| Files/modules likely affected | `runtime.py`, `replay.py`, `reporting.py`, tests. |
| Implementation steps | Add optional manifest writer to safe report/replay commands only. |
| Dependencies | SWING-V01-006, SWING-V01-025. |
| Tests to add or update | CLI/report tests. |
| Acceptance criteria | Manifest is written with config hash and serious-run prohibition status. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-030

| Field | Value |
| --- | --- |
| Title | Qualification checklist artifact |
| Epic | QA and qualification |
| Objective | Emit checklist status as JSON/Markdown. |
| Why it matters | Freeze review needs clear pass/block status. |
| Files/modules likely affected | Baseline/report module, docs, tests. |
| Implementation steps | Convert manifest checks into reviewable checklist output. |
| Dependencies | SWING-V01-006, SWING-V01-025. |
| Tests to add or update | Contract/report tests. |
| Acceptance criteria | Checklist lists required checks, evidence, blockers, and serious-run status. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-031

| Field | Value |
| --- | --- |
| Title | Freeze process execution |
| Epic | Release/freeze process |
| Objective | Run freeze checklist when all mandatory checks are satisfied. |
| Why it matters | Prevents accidental baseline promotion. |
| Files/modules likely affected | Docs, reports, validation logs. |
| Implementation steps | Run required gates, collect artifacts, record blockers or freeze approval. |
| Dependencies | SWING-V01-024 through SWING-V01-030. |
| Tests to add or update | Full release gate. |
| Acceptance criteria | Baseline is either frozen with evidence or explicitly blocked with reasons. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | not started |

### SWING-V01-032

| Field | Value |
| --- | --- |
| Title | Selected-period qualification data set |
| Epic | QA and qualification |
| Objective | Define and validate the first non-tiny historical qualification panel. |
| Why it matters | Tiny replay is machinery proof only. |
| Files/modules likely affected | `examples/`, `tests/fixtures/`, docs. |
| Implementation steps | Identify selected period, manifest requirements, expected artifacts, and data checks. |
| Dependencies | SWING-V01-012, SWING-V01-024. |
| Tests to add or update | Data/replay qualification tests. |
| Acceptance criteria | Selected-period panel validates and has deterministic replay artifacts. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | blocked |

### SWING-V01-033

| Field | Value |
| --- | --- |
| Title | Correlation/concentration gap decision |
| Epic | Risk and portfolio constraints |
| Objective | Decide whether v0.1 needs correlation proxy or explicitly defers it. |
| Why it matters | Portfolio risk could otherwise be overstated as complete. |
| Files/modules likely affected | Baseline definition/design, risk docs, future risk model. |
| Implementation steps | Record ADR; either implement simple proxy or mark non-blocking gap for v0.1. |
| Dependencies | SWING-V01-020. |
| Tests to add or update | If implemented, add risk tests. |
| Acceptance criteria | Reports clearly state whether correlation is enforced or deferred. |
| Safe to implement immediately | yes |
| Blocks later work | no |
| Status | complete |

### SWING-V01-034

| Field | Value |
| --- | --- |
| Title | Signal adapter integration |
| Epic | Signal feature snapshot |
| Objective | Convert setup outputs into `SwingSignal` artifacts. |
| Why it matters | Serious full run readiness needs baseline signal artifacts, not only setup rows/snapshots. |
| Files/modules likely affected | `src/swingmachine/swing_adapters.py`, `tests/test_swing_adapters.py` |
| Implementation steps | Add adapter from setup rows or `SetupSnapshot` plus score/candidate context to `SwingSignal`; validate approved/rejected transitions; include setup prices/risk and quality score. |
| Dependencies | SWING-V01-010, SWING-V01-014. |
| Tests to add or update | Signal adapter tests using existing setup fixture. |
| Acceptance criteria | Existing setup output can be represented as typed `SwingSignal` without changing setup detection or runtime execution. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-035

| Field | Value |
| --- | --- |
| Title | Risk/order adapter integration |
| Epic | Risk and portfolio constraints |
| Objective | Convert `EntryPlan` and `OrderIntent` outputs into `SwingRiskPlan` and `SwingOrderPlan` artifacts. |
| Why it matters | Baseline reports must explain sizing and order planning through typed artifacts. |
| Files/modules likely affected | `src/swingmachine/swing_adapters.py`, `tests/test_swing_adapters.py` |
| Implementation steps | Map approved/rejected entry plans, constraints, rejection reasons, and order intent fields to baseline contracts. |
| Dependencies | SWING-V01-019, SWING-V01-020, SWING-V01-021, SWING-V01-034. |
| Tests to add or update | Entry plan/order intent adapter tests. |
| Acceptance criteria | Approved and rejected plans serialize with risk/order evidence and no broker side effect. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-036

| Field | Value |
| --- | --- |
| Title | Lifecycle/exit adapter integration |
| Epic | Trade lifecycle and exits |
| Objective | Convert lifecycle and exit decisions into baseline lifecycle/exit artifacts. |
| Why it matters | Serious run readiness requires explainable state transitions and exit decisions. |
| Files/modules likely affected | `src/swingmachine/swing_adapters.py`, lifecycle/exit tests. |
| Implementation steps | Map pending-entry actions, lifecycle states, and `evaluate_exit_position` outputs to `SwingLifecycleTransition` and `SwingExitDecision`. |
| Dependencies | SWING-V01-022, SWING-V01-023. |
| Tests to add or update | Lifecycle/exit adapter tests. |
| Acceptance criteria | Fill/cancel/expire/hold/exit decisions can be represented in baseline artifacts. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-037

| Field | Value |
| --- | --- |
| Title | Safe replay/report package hook |
| Epic | Reporting and instrumentation |
| Objective | Emit a `baseline_report_package.json` artifact from the safe historical replay workflow without broker, live trading, deployment, or destructive database side effects. |
| Why it matters | Serious full run readiness needs replay/runtime artifacts that can be reviewed and compared before any larger qualification run is allowed. |
| Files/modules likely affected | `src/swingmachine/replay.py`, `src/swingmachine/runtime.py`, `tests/test_replay_workflow.py`, `tests/test_runtime.py`. |
| Implementation steps | Add the report package to replay artifact paths; pass the active strategy config path into replay artifact writing; build/write a baseline report package from replay material facts; keep serious full run prohibited in the emitted package; assert runtime CLI replay writes the artifact. |
| Dependencies | SWING-V01-023, SWING-V01-027, SWING-V01-034, SWING-V01-035, SWING-V01-036. |
| Tests to add or update | Replay workflow artifact test and runtime CLI replay test. |
| Acceptance criteria | Safe historical replay with an output directory writes `baseline_report_package.json`; the package includes manifest/checklist data, the active config hash, and `serious_full_run_allowed=false`; no live broker/order path is invoked. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-038

| Field | Value |
| --- | --- |
| Title | Research-vs-runtime package parity evidence |
| Epic | Research/runtime parity |
| Objective | Provide file-based parity evidence for two emitted `baseline_report_package.json` artifacts. |
| Why it matters | Serious full run readiness requires proof that research-style and runtime-style outputs can be compared deterministically before larger qualification runs are allowed. |
| Files/modules likely affected | `src/swingmachine/baseline_parity.py`, `tests/test_baseline_parity.py`. |
| Implementation steps | Add a typed report-package JSON loader; compare two package files through the existing parity comparator; add a JSON writer for parity reports; test equivalent research/runtime package files with different package metadata. |
| Dependencies | SWING-V01-024, SWING-V01-037. |
| Tests to add or update | Baseline parity file comparison test. |
| Acceptance criteria | Two written baseline report packages can be loaded, compared, and summarized as a typed parity report; generated metadata differences do not create false failures; field-level payload differences remain detectable. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-039

| Field | Value |
| --- | --- |
| Title | Selected-period qualification data definition |
| Epic | QA and qualification |
| Objective | Define a typed, explicit selected-period qualification plan for safe replay/dry-run evidence before any serious full run. |
| Why it matters | Qualification must be reproducible and bounded; selected periods, required artifacts, data requirements, and safety controls need to be explicit before larger runs are allowed. |
| Files/modules likely affected | `config/swing_machine_v0_1_selected_periods.yaml`, `src/swingmachine/baseline.py`, `tests/test_baseline.py`. |
| Implementation steps | Add a serialisable selected-period plan YAML; add typed models and loaders; validate date ordering, unique period ids, safe run policy, required data contract, and resolved profile alias; add tests. |
| Dependencies | SWING-V01-037. |
| Tests to add or update | Baseline tests for selected-period plan loading and validation. |
| Acceptance criteria | The selected-period plan loads as a typed contract; it is dry-run/replay-only; serious full run remains prohibited; required artifacts include baseline and parity reports; invalid duplicate period ids are rejected. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-040

| Field | Value |
| --- | --- |
| Title | Serious full run freeze readiness gate |
| Epic | Release/freeze process |
| Objective | Add a pure, typed freeze-readiness decision gate that blocks serious full run permission until all required baseline evidence is present. |
| Why it matters | Serious full run permission must be evidence-driven rather than manually inferred from partial implementation progress. |
| Files/modules likely affected | `src/swingmachine/baseline_readiness.py`, `tests/test_baseline_readiness.py`. |
| Implementation steps | Add readiness blocker and decision models; evaluate manifest qualification status, selected-period plan compatibility, parity evidence, and operator approval; write readiness decisions as JSON; test current blocked state, synthetic fully satisfied state, and failed parity evidence. |
| Dependencies | SWING-V01-038, SWING-V01-039. |
| Tests to add or update | Readiness gate unit tests. |
| Acceptance criteria | Current baseline evaluates to `BLOCK`; serious full run is allowed only when manifest checks are satisfied, selected-period plan matches, parity evidence passes, and operator approval is present; failed or missing evidence blocks with explicit reasons. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |


### SWING-V01-041

| Field | Value |
| --- | --- |
| Title | Populate replay baseline package with material artifacts |
| Epic | Reporting and instrumentation |
| Objective | Include typed candidate, signal, risk-plan, and order-plan artifacts in replay-emitted baseline report packages when the replay already produces enough safe in-memory evidence. |
| Why it matters | A package with only manifest/checklist evidence is not enough to qualify the baseline; reviewers need actual material decision artifacts from replay. |
| Files/modules likely affected | `src/swingmachine/contracts.py`, `src/swingmachine/replay.py`, `tests/test_replay_workflow.py`. |
| Implementation steps | Carry baseline artifact tuples on the replay result; build candidates from the scored signal-session frame; adapt setup snapshots into signals; build dry-run entry plans with the portfolio manager; adapt entry plans into risk and order plans; write those artifacts into `baseline_report_package.json`. |
| Dependencies | SWING-V01-034, SWING-V01-035, SWING-V01-037. |
| Tests to add or update | Replay artifact package tests. |
| Acceptance criteria | Successful historical replay emits non-empty candidate, signal, risk-plan, and order-plan counts in the baseline report package; artifact config hashes match the manifest; serious full run remains false. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-042

| Field | Value |
| --- | --- |
| Title | Emit freeze-readiness artifact from replay evidence |
| Epic | Release/freeze process |
| Objective | Write a freeze-readiness JSON artifact beside replay artifacts using the current manifest, optional selected-period plan, and available evidence. |
| Why it matters | Operators need a single explicit artifact explaining whether serious full run remains blocked. |
| Files/modules likely affected | `src/swingmachine/replay.py`, `tests/test_replay_workflow.py`, `tests/test_runtime.py`. |
| Implementation steps | Add `freeze_readiness.json` to replay artifact paths; optionally load a selected-period plan; evaluate readiness after package generation; write readiness output; keep missing parity/operator approval as blockers. |
| Dependencies | SWING-V01-040, SWING-V01-041. |
| Tests to add or update | Replay/runtime artifact tests for blocked readiness output. |
| Acceptance criteria | Replay writes a readiness artifact that blocks serious full run with explicit blocker codes. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-043

| Field | Value |
| --- | --- |
| Title | Selected-period qualification preflight validator |
| Epic | QA and qualification |
| Objective | Validate selected-period plan inputs and required artifact expectations before any selected-period replay is attempted. |
| Why it matters | Data gaps and unsafe run modes should fail fast before expensive or misleading qualification work. |
| Files/modules likely affected | `src/swingmachine/baseline_readiness.py`, `config/swing_machine_v0_1_selected_periods.yaml`, `tests/test_baseline_readiness.py`. |
| Implementation steps | Add preflight result/blocker models; check profile alias and strategy config resolution; verify required artifact declarations; require declared data manifests for every selected period; expose missing data as blockers rather than running replay. |
| Dependencies | SWING-V01-039, SWING-V01-041. |
| Tests to add or update | Preflight validator tests. |
| Acceptance criteria | Preflight produces typed pass/block output without loading broker state or executing replay. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-044

| Field | Value |
| --- | --- |
| Title | Selected-period dry-run qualification evidence run |
| Epic | QA and qualification |
| Objective | Run the smallest selected-period dry-run/replay qualification only after data inputs and preflight gates are satisfied. |
| Why it matters | This is the first evidence-producing qualification step beyond tiny machinery tests. |
| Files/modules likely affected | Reports, selected-period artifacts, implementation log. |
| Implementation steps | Confirm data paths and selected period; run dry-run/replay-only command; collect package, parity, replay, and readiness artifacts; record blockers or pass evidence. |
| Dependencies | SWING-V01-041, SWING-V01-042, SWING-V01-043. |
| Tests to add or update | Not applicable before execution; evidence is artifact-based. |
| Acceptance criteria | Selected-period evidence is generated without live broker/order effects, or the run is explicitly blocked before execution. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | blocked |

### SWING-V01-045

| Field | Value |
| --- | --- |
| Title | Selected-period preflight CLI command |
| Epic | QA and qualification |
| Objective | Expose the selected-period preflight validator through a safe operator-facing CLI command that writes a JSON artifact. |
| Why it matters | Operators need a reproducible command to prove selected-period data readiness before any dry-run qualification replay is attempted. |
| Files/modules likely affected | `src/swingmachine/runtime.py`, `tests/test_runtime.py`. |
| Implementation steps | Add a `preflight-selected-period-qualification` command; accept a selected-period plan path, output path, and repeated `period_id=manifest_path` arguments; write the typed preflight artifact; exit non-zero when blockers are present; do not run replay, broker, runtime cycle, or database writes. |
| Dependencies | SWING-V01-043. |
| Tests to add or update | Runtime CLI tests for blocked and passing preflight output. |
| Acceptance criteria | Missing data manifests produce `selected_period_preflight.json` with blockers and exit code 1; explicit existing manifests produce a passing artifact and exit code 0. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-046

| Field | Value |
| --- | --- |
| Title | Selected-period preflight blocker evidence |
| Epic | QA and qualification |
| Objective | Produce operator-visible evidence that selected-period qualification remains blocked because real selected-period manifests are absent. |
| Why it matters | The next serious-run gate should be blocked by concrete artifact evidence, not informal notes. |
| Files/modules likely affected | `reports/swing_machine_v0_1/selected_period_preflight.json`, `docs/swing_machine_v0_1_implementation_log.md`. |
| Implementation steps | Inventory available manifests; run `preflight-selected-period-qualification` with the selected-period plan; record expected blocker output. |
| Dependencies | SWING-V01-045. |
| Tests to add or update | None; evidence artifact only. |
| Acceptance criteria | Preflight exits non-zero and writes a blocker artifact without running replay or broker/runtime cycles. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-047

| Field | Value |
| --- | --- |
| Title | Historical panel manifest builder CLI |
| Epic | Data and universe foundation |
| Objective | Provide a safe command to build historical panel manifests from explicit prepared data files. |
| Why it matters | Selected-period qualification is blocked on real manifest paths; operators need a deterministic way to create those manifests from prepared files without running replay or trading logic. |
| Files/modules likely affected | `src/swingmachine/data_contracts.py`, `src/swingmachine/runtime.py`, `tests/test_runtime.py`. |
| Implementation steps | Add manifest builder/writer helper; infer file formats, row counts, hashes, dates, symbol/session counts; add a CLI command that writes a manifest from explicit inputs; test against fixture CSV inputs. |
| Dependencies | SWING-V01-046. |
| Tests to add or update | Runtime CLI manifest builder test. |
| Acceptance criteria | Command writes a manifest with deterministic file specs and hashes from explicit prepared inputs; it does not run replay, broker, runtime cycle, or database writes. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-048

| Field | Value |
| --- | --- |
| Title | Selected-period qualification runbook |
| Epic | QA and qualification |
| Objective | Document the safe operator sequence for preparing selected-period manifests and running preflight. |
| Why it matters | The data blocker needs an executable runbook so future work can resume without guessing the safe command sequence. |
| Files/modules likely affected | `docs/swing_machine_v0_1_selected_period_runbook.md`. |
| Implementation steps | Document required prepared files, manifest builder command, preflight command, expected exit codes, and safety boundaries. |
| Dependencies | SWING-V01-045, SWING-V01-047. |
| Tests to add or update | None; docs-only. |
| Acceptance criteria | Runbook states that serious full run remains prohibited and gives exact safe commands for manifest building and preflight. |
| Safe to implement immediately | yes |
| Blocks later work | no |
| Status | complete |

## Grouped remaining qualification backlog

The following items supersede ad-hoc item-by-item continuation for the remaining qualification phase. Earlier low-level implementation items remain as historical delivery evidence.

### SWING-V01-049

| Field | Value |
| --- | --- |
| Title | Qualification mini-plan and grouped workstreams |
| Epic | QA and qualification |
| Objective | Replace isolated remaining-item execution with grouped data, preflight, dry-run, parity, and freeze workstreams. |
| Why it matters | The baseline should advance through qualification gates, not opportunistic individual tasks. |
| Files/modules likely affected | `docs/swing_machine_v0_1_qualification_mini_plan.md`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md`. |
| Implementation steps | Create the qualification mini-plan; add grouped backlog structure; record that serious full run remains prohibited. |
| Dependencies | SWING-V01-045, SWING-V01-046, SWING-V01-047, SWING-V01-048. |
| Tests to add or update | None; docs/governance only. |
| Acceptance criteria | Remaining work is grouped into workstreams with clear entry/exit criteria and safety boundaries. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-050

| Field | Value |
| --- | --- |
| Title | Workstream A: selected-period data readiness and manifests |
| Epic | Data and universe foundation |
| Objective | Produce real historical panel manifests for all selected qualification periods. |
| Why it matters | Qualification cannot proceed without real data manifests. |
| Files/modules likely affected | `data/qualification/` or operator-supplied data paths, selected-period manifests, data provenance note. |
| Implementation steps | Identify source files; record provenance; build manifests with `build-historical-panel-manifest`; validate manifests; record blockers. |
| Dependencies | SWING-V01-047. |
| Tests to add or update | Manifest validation evidence. |
| Acceptance criteria | Three selected-period manifests exist and validate, or blockers are recorded. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | blocked |

### SWING-V01-051

| Field | Value |
| --- | --- |
| Title | Workstream B: selected-period preflight gate |
| Epic | QA and qualification |
| Objective | Run preflight against the real selected-period manifests before replay execution. |
| Why it matters | Data readiness must be proven before dry-run qualification. |
| Files/modules likely affected | `reports/swing_machine_v0_1/selected_period_preflight.json`. |
| Implementation steps | Run `preflight-selected-period-qualification` with all three real manifest paths; inspect blockers; fix or record failures. |
| Dependencies | SWING-V01-050. |
| Tests to add or update | Preflight artifact evidence. |
| Acceptance criteria | Preflight exits `0` with `passed=true` and `blocker_count=0`. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | blocked |

### SWING-V01-052

| Field | Value |
| --- | --- |
| Title | Workstream C: selected-period dry-run replay qualification evidence |
| Epic | QA and qualification |
| Objective | Produce bounded dry-run/replay evidence for selected periods after preflight passes. |
| Why it matters | Baseline promotion needs material replay evidence, not just contract tests. |
| Files/modules likely affected | Selected-period replay output directories and evidence artifacts. |
| Implementation steps | Run smoke period first; review artifacts; only then run medium/historical windows; record outcomes. |
| Dependencies | SWING-V01-051. |
| Tests to add or update | Artifact/evidence checks as needed. |
| Acceptance criteria | Required replay artifacts exist for each approved period and serious full run remains blocked unless freeze gates pass. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | blocked |

### SWING-V01-053

| Field | Value |
| --- | --- |
| Title | Workstream D: parity and qualification evidence consolidation |
| Epic | Research/runtime parity |
| Objective | Compare baseline packages and assemble a reviewable qualification evidence bundle. |
| Why it matters | Research/runtime parity and evidence traceability are required before freeze. |
| Files/modules likely affected | Parity reports, qualification evidence index, implementation log. |
| Implementation steps | Generate parity reports; consolidate manifests/packages/replay/readiness artifacts; record pass/fail/blocker state. |
| Dependencies | SWING-V01-052. |
| Tests to add or update | Parity report evidence. |
| Acceptance criteria | Parity passes or field-level blockers are documented; evidence index is complete. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | blocked |

### SWING-V01-054

| Field | Value |
| --- | --- |
| Title | Workstream E: freeze readiness and operator decision |
| Epic | Release/freeze process |
| Objective | Evaluate whether `swing_machine_v0_1` can be frozen or remains blocked. |
| Why it matters | Serious full run permission must be an explicit governed decision. |
| Files/modules likely affected | Freeze readiness artifact, serious full run decision document, implementation log. |
| Implementation steps | Run freeze readiness; review automated blockers; record operator approval/refusal; update serious full run decision. |
| Dependencies | SWING-V01-053. |
| Tests to add or update | Freeze-readiness evidence. |
| Acceptance criteria | Baseline is either frozen with evidence and approval, or explicitly blocked with reasons. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | blocked |

### SWING-V01-055

| Field | Value |
| --- | --- |
| Title | Workstream A source data input contract and preflight |
| Epic | Data and universe foundation |
| Objective | Define and preflight the explicit source-file inputs needed before selected-period manifests can be built. |
| Why it matters | Workstream A needs an input gate before manifest building, otherwise missing or ambiguous source files will be discovered too late. |
| Files/modules likely affected | `src/swingmachine/qualification_inputs.py`, `config/swing_machine_v0_1_selected_period_data_inputs.example.yaml`, `src/swingmachine/runtime.py`, tests, docs/log. |
| Implementation steps | Add typed source-input plan models; add source-file preflight result/blockers; add JSON writer; add a CLI command; add tests for missing and passing inputs. |
| Dependencies | SWING-V01-049, SWING-V01-050. |
| Tests to add or update | Qualification input unit tests and CLI wiring test. |
| Acceptance criteria | Source-file preflight blocks with explicit missing-file/period reasons and passes only when all required selected-period source files exist. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-056

| Field | Value |
| --- | --- |
| Title | Workstream A data input plan builder |
| Epic | Data and universe foundation |
| Objective | Generate a selected-period data input plan from a conventional qualification data root. |
| Why it matters | Once real prepared files exist, operators should not manually edit every source path before source-input preflight. |
| Files/modules likely affected | `src/swingmachine/qualification_inputs.py`, `src/swingmachine/runtime.py`, `tests/test_qualification_inputs.py`, `tests/test_runtime.py`, docs/log. |
| Implementation steps | Add data-root plan builder; choose existing `.parquet` or `.csv` files where present; make features optional; add a CLI command; test plan writing and CLI integration. |
| Dependencies | SWING-V01-055. |
| Tests to add or update | Qualification input plan-builder tests and CLI test. |
| Acceptance criteria | A data input plan can be generated from `root/<period_id>/` directories and passes source-input preflight when required files exist. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |
### SWING-V01-057

| Field | Value |
| --- | --- |
| Title | Workstream A batch selected-period manifest builder |
| Epic | Data and universe foundation |
| Objective | Build all selected-period historical panel manifests from a selected-period data input plan. |
| Why it matters | Once source input preflight passes, operators need one safe batch command to produce the three manifest paths required by the selected-period preflight gate. |
| Files/modules likely affected | `src/swingmachine/runtime.py`, `tests/test_runtime.py`, docs/log. |
| Implementation steps | Add a batch manifest builder CLI; load the source input plan; write one manifest per selected period under an output root; optionally write a summary artifact; test with fixture data copied into period directories. |
| Dependencies | SWING-V01-056. |
| Tests to add or update | Runtime CLI batch manifest-builder test. |
| Acceptance criteria | Command writes valid manifests for all selected periods from explicit prepared source files without replay, broker, runtime cycle, or database writes. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-058

| Field | Value |
| --- | --- |
| Title | Workstream A data provenance template |
| Epic | Data and universe foundation |
| Objective | Provide a review template for selected-period source data custody and preparation assumptions. |
| Why it matters | Qualification data needs provenance and point-in-time assumptions recorded before replay evidence is trusted. |
| Files/modules likely affected | `docs/swing_machine_v0_1_data_provenance_template.md`, implementation log. |
| Implementation steps | Create a template covering period identity, source files, adjustment assumptions, point-in-time controls, gaps, preflight evidence, and operator decision. |
| Dependencies | SWING-V01-049. |
| Tests to add or update | None; docs-only. |
| Acceptance criteria | Template can be copied for each selected period before manifest building and replay qualification. |
| Safe to implement immediately | yes |
| Blocks later work | no |
| Status | complete |

### SWING-V01-059

| Field | Value |
| --- | --- |
| Title | Qualification evidence indexer |
| Epic | QA and qualification |
| Objective | Build a single index of expected qualification artifacts and their present/missing status across selected periods. |
| Why it matters | Once data/preflight/replay/parity artifacts start appearing, operators need a grouped evidence view instead of manually checking files one by one. |
| Files/modules likely affected | `src/swingmachine/qualification_evidence.py`, `src/swingmachine/runtime.py`, tests, docs/log. |
| Implementation steps | Add typed evidence item/index models; derive expected global and per-period artifacts from the selected-period plan; add JSON writer and CLI command; test missing and complete evidence states. |
| Dependencies | SWING-V01-049, SWING-V01-058. |
| Tests to add or update | Qualification evidence tests and CLI wiring test. |
| Acceptance criteria | Evidence index reports required present/missing counts, period ids, missing artifacts, and exits without running replay or broker/runtime paths. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

## Trading212 selected-period data backlog

### SWING-V01-060

| Field | Value |
| --- | --- |
| Title | Trading212 research data source solution design |
| Epic | Data and universe foundation |
| Objective | Define how Alpaca and Hugging Face research DBs from the Trading212 repo feed swingmachine selected-period qualification. |
| Why it matters | This converts the remaining data blocker into a concrete implementation path. |
| Files/modules likely affected | `docs/swing_machine_v0_1_trading212_data_solution_design.md`, `docs/swing_machine_v0_1_solution_design.md`, backlog/log. |
| Implementation steps | Document source inventory, schema, contracts, output layout, source safety, components, CLI commands, delivery sequence, and open decisions. |
| Dependencies | SWING-V01-049 through SWING-V01-059. |
| Tests to add or update | None; docs/design only. |
| Acceptance criteria | Another engineer can implement the Trading212 data adapter without guessing source paths or contracts. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | complete |

### SWING-V01-061

| Field | Value |
| --- | --- |
| Title | Trading212 source config model |
| Epic | Data and universe foundation |
| Objective | Add typed config for Trading212 research providers, DB paths, symbols file, output root, and timeframe policy. |
| Why it matters | Source behavior must be explicit and serialisable, not hidden in `.env` or hardcoded script globals. |
| Files/modules likely affected | `src/swingmachine/trading212_source.py`, `config/swing_machine_v0_1_trading212_sources.yaml`, tests. |
| Implementation steps | Define provider config model; add YAML loader; validate provider names and paths; add default config for local Alpaca/Hugging Face DBs; test load/validation. |
| Dependencies | SWING-V01-060. |
| Tests to add or update | Unit tests for config loading and invalid providers. |
| Acceptance criteria | The two Trading212 DB sources can be loaded as explicit typed config without reading `.env`. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | not started |

### SWING-V01-062

| Field | Value |
| --- | --- |
| Title | Trading212 source schema inspector |
| Epic | Data and universe foundation |
| Objective | Inspect a Trading212 research DB safely and report schema/index/timeframe availability. |
| Why it matters | We need bounded evidence that the source DB matches the expected `bars` contract before export. |
| Files/modules likely affected | `src/swingmachine/trading212_source.py`, `src/swingmachine/runtime.py`, tests. |
| Implementation steps | Open SQLite read-only; inspect `bars` schema; inspect indexes; check sample rows; avoid full-table scans; add CLI `inspect-trading212-research-source`. |
| Dependencies | SWING-V01-061. |
| Tests to add or update | Fixture SQLite schema tests and CLI test. |
| Acceptance criteria | Inspector reports pass/fail schema state without mutating DB or running broad counts. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | not started |

### SWING-V01-063

| Field | Value |
| --- | --- |
| Title | Selected-period extraction planner |
| Epic | Data and universe foundation |
| Objective | Expand selected-period windows into provider extraction windows with long swing lookback. |
| Why it matters | Swing features require long historical context before each qualification window. |
| Files/modules likely affected | `src/swingmachine/trading212_source.py`, tests. |
| Implementation steps | Load selected-period plan; compute extraction start/end per period; load symbols file; enforce lookback session/calendar buffer; produce typed extraction plans. |
| Dependencies | SWING-V01-061. |
| Tests to add or update | Unit tests for extraction date expansion and symbol loading. |
| Acceptance criteria | Every selected period has deterministic extraction bounds and selected symbols. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | not started |

### SWING-V01-064

| Field | Value |
| --- | --- |
| Title | Bounded Trading212 source coverage preflight |
| Epic | Data and universe foundation |
| Objective | Check selected symbols and periods for available bars using indexed bounded queries. |
| Why it matters | We must know whether `1d` can be used or `1m` aggregation is required before export. |
| Files/modules likely affected | `src/swingmachine/trading212_source.py`, tests, reports. |
| Implementation steps | Query per symbol/timeframe/extraction window; report missing symbols, missing timeframe, min/max timestamps, and row counts; cap queries to selected symbols. |
| Dependencies | SWING-V01-062, SWING-V01-063. |
| Tests to add or update | Fixture SQLite coverage tests. |
| Acceptance criteria | Coverage preflight returns typed pass/block/warn output for Alpaca/Hugging Face without broad DB scans. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | not started |

### SWING-V01-065

| Field | Value |
| --- | --- |
| Title | Daily OHLCV export from Trading212 `1d` bars |
| Epic | Data and universe foundation |
| Objective | Export swing-compatible `ohlcv.csv` using provider `timeframe='1d'` rows when available. |
| Why it matters | Direct daily rows are the simplest safe source for swing selected-period panels. |
| Files/modules likely affected | `src/swingmachine/trading212_source.py`, tests. |
| Implementation steps | Fetch bounded `1d` rows; map columns to swing OHLCV contract; sort deterministically; validate using swingmachine data contracts; write CSV. |
| Dependencies | SWING-V01-064. |
| Tests to add or update | Unit test with fixture SQLite daily rows. |
| Acceptance criteria | Exported `ohlcv.csv` passes `validate_historical_ohlcv_data`. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | not started |

### SWING-V01-066

| Field | Value |
| --- | --- |
| Title | Daily OHLCV aggregation fallback from Trading212 `1m` bars |
| Epic | Data and universe foundation |
| Objective | Aggregate provider `1m` rows into daily OHLCV when `1d` rows are absent or insufficient. |
| Why it matters | The observed DB samples include `1m`; daily availability still needs bounded confirmation. |
| Files/modules likely affected | `src/swingmachine/trading212_source.py`, tests. |
| Implementation steps | Fetch bounded `1m`; filter regular session if needed; group by symbol/session; compute open/high/low/close/volume; validate output. |
| Dependencies | SWING-V01-065. |
| Tests to add or update | Aggregation tests for open/high/low/close/volume and invalid bars. |
| Acceptance criteria | Aggregated output is deterministic and passes the swing OHLCV contract. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | not started |

### SWING-V01-067

| Field | Value |
| --- | --- |
| Title | Symbol reference and empty event/action exporters |
| Epic | Data and universe foundation |
| Objective | Generate `symbol_reference.csv`, `corporate_actions.csv`, and `earnings_events.csv` for exported Trading212 periods. |
| Why it matters | The swing historical panel contract requires these files even if event/action sources are not yet available. |
| Files/modules likely affected | `src/swingmachine/trading212_source.py`, tests. |
| Implementation steps | Build reference rows from selected universe and coverage; create empty required-column corporate action and earnings files; validate contracts; record limitations. |
| Dependencies | SWING-V01-063. |
| Tests to add or update | Contract tests for generated files. |
| Acceptance criteria | Generated reference/action/event files pass swingmachine validators and make limitations explicit. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | not started |

### SWING-V01-068

| Field | Value |
| --- | --- |
| Title | Trading212 provider export CLI |
| Epic | Data and universe foundation |
| Objective | Export selected-period source files for one provider into the Workstream A directory layout. |
| Why it matters | This is the first command that turns Trading212 DB rows into swing-compatible prepared files. |
| Files/modules likely affected | `src/swingmachine/runtime.py`, `src/swingmachine/trading212_source.py`, tests. |
| Implementation steps | Add CLI `export-trading212-selected-period-data`; call coverage preflight; export OHLCV/reference/action/event files; write export summary and provenance draft. |
| Dependencies | SWING-V01-064, SWING-V01-065, SWING-V01-066, SWING-V01-067. |
| Tests to add or update | CLI fixture DB export test. |
| Acceptance criteria | CLI writes complete prepared files for fixture provider/periods without mutating source DBs. |
| Safe to implement immediately | yes |
| Blocks later work | yes |
| Status | not started |

### SWING-V01-069

| Field | Value |
| --- | --- |
| Title | Trading212 Alpaca selected-period export run |
| Epic | Data and universe foundation |
| Objective | Export real Alpaca selected-period files from the local Trading212 research DB. |
| Why it matters | Alpaca is the first primary candidate to unblock Workstream A. |
| Files/modules likely affected | `data/qualification_sources/trading212/alpaca/`, reports/log. |
| Implementation steps | Run source inspector; run bounded coverage preflight; export selected periods; write provenance; run source-input preflight. |
| Dependencies | SWING-V01-068. |
| Tests to add or update | Artifact evidence only. |
| Acceptance criteria | Alpaca source files exist for all three periods and source-input preflight passes. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | blocked until exporter is implemented |

### SWING-V01-070

| Field | Value |
| --- | --- |
| Title | Trading212 Hugging Face selected-period export run |
| Epic | Data and universe foundation |
| Objective | Export real Hugging Face selected-period files from the local Trading212 research DB. |
| Why it matters | Hugging Face provides provider-drift and cross-source evidence before promotion. |
| Files/modules likely affected | `data/qualification_sources/trading212/huggingface/`, reports/log. |
| Implementation steps | Run source inspector; run bounded coverage preflight; export selected periods; write provenance; run source-input preflight. |
| Dependencies | SWING-V01-068. |
| Tests to add or update | Artifact evidence only. |
| Acceptance criteria | Hugging Face source files exist for all three periods and source-input preflight passes, or blockers are explicit. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | blocked until exporter is implemented |

### SWING-V01-071

| Field | Value |
| --- | --- |
| Title | Trading212 provider panel drift report |
| Epic | Research/runtime parity |
| Objective | Compare exported Alpaca and Hugging Face daily panels before using them for qualification. |
| Why it matters | Known provider drift must be visible before interpreting selected-period evidence. |
| Files/modules likely affected | `src/swingmachine/trading212_source.py`, reports, tests. |
| Implementation steps | Compare symbol/session overlap, close drift, missing symbol-days, invalid OHLCV counts, and volume differences; write report. |
| Dependencies | SWING-V01-069, SWING-V01-070. |
| Tests to add or update | Drift report fixture tests. |
| Acceptance criteria | Drift report clearly states whether provider differences are acceptable, blocking, or review-required. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | blocked until provider exports exist |

### SWING-V01-072

| Field | Value |
| --- | --- |
| Title | Alpaca Workstream A manifest/preflight integration |
| Epic | QA and qualification |
| Objective | Run the existing Workstream A plan-builder, source preflight, manifest builder, and selected-period preflight on the Alpaca export root. |
| Why it matters | This converts exported Alpaca files into validated swing selected-period manifests. |
| Files/modules likely affected | `config/swing_machine_v0_1_selected_period_data_inputs_alpaca.yaml`, `data/qualification_manifests/trading212/alpaca/`, reports/log. |
| Implementation steps | Build input plan; run source preflight; build manifests; run selected-period preflight; update evidence index. |
| Dependencies | SWING-V01-069. |
| Tests to add or update | Artifact evidence only. |
| Acceptance criteria | Alpaca manifests exist and selected-period preflight passes or blockers are explicit. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | blocked until Alpaca export exists |

### SWING-V01-073

| Field | Value |
| --- | --- |
| Title | Hugging Face Workstream A manifest/preflight integration |
| Epic | QA and qualification |
| Objective | Run the existing Workstream A plan-builder, source preflight, manifest builder, and selected-period preflight on the Hugging Face export root. |
| Why it matters | This creates independent cross-provider selected-period manifests. |
| Files/modules likely affected | `config/swing_machine_v0_1_selected_period_data_inputs_huggingface.yaml`, `data/qualification_manifests/trading212/huggingface/`, reports/log. |
| Implementation steps | Build input plan; run source preflight; build manifests; run selected-period preflight; update evidence index. |
| Dependencies | SWING-V01-070. |
| Tests to add or update | Artifact evidence only. |
| Acceptance criteria | Hugging Face manifests exist and selected-period preflight passes or blockers are explicit. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | blocked until Hugging Face export exists |

### SWING-V01-074

| Field | Value |
| --- | --- |
| Title | Selected-period qualification source decision |
| Epic | Release/freeze process |
| Objective | Decide whether Alpaca alone can start smoke replay or whether both providers must pass before any replay. |
| Why it matters | This prevents accidental promotion from one provider when cross-provider evidence is required. |
| Files/modules likely affected | Decision doc, delivery plan, implementation log. |
| Implementation steps | Review Alpaca preflight, Hugging Face preflight, and drift report; record decision and conditions. |
| Dependencies | SWING-V01-071, SWING-V01-072, SWING-V01-073. |
| Tests to add or update | None; governance decision. |
| Acceptance criteria | Decision is explicit and serious full run remains prohibited unless all later freeze gates pass. |
| Safe to implement immediately | no |
| Blocks later work | yes |
| Status | blocked until provider evidence exists |

## Trading212 data-source backlog status update - 2026-05-05

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-061 | complete | Added explicit Trading212 source config model and provider config file. |
| SWING-V01-062 | complete | Added bounded read-only SQLite schema/index/sample inspector and CLI. |
| SWING-V01-063 | complete | Added selected-period extraction planner with explicit lookback windows. |
| SWING-V01-064 | complete | Added bounded source coverage preflight using indexed existence and first/last timestamp probes. |
| SWING-V01-065 | complete | Added daily OHLCV export from Trading212 `1d` bars. |
| SWING-V01-066 | complete | Added `1m` aggregation fallback for symbols without `1d` rows. |
| SWING-V01-067 | complete | Added symbol reference plus empty corporate action and earnings event exporters. |
| SWING-V01-068 | complete | Added Trading212 inspection, coverage, export, and provider-drift CLI commands. |
| SWING-V01-069 | complete | Ran Alpaca selected-period export for the declared 16-symbol panel. |
| SWING-V01-070 | complete | Ran Hugging Face selected-period export for the declared 16-symbol panel. |
| SWING-V01-071 | complete | Added and ran Alpaca-vs-Hugging-Face provider panel drift report; drift failed across all 48 period/symbol rows. |
| SWING-V01-072 | complete | Built Alpaca selected-period data input plan, manifests, and preflight report; preflight passed. |
| SWING-V01-073 | complete | Built Hugging Face selected-period data input plan, manifests, and preflight report; preflight passed. |
| SWING-V01-074 | complete | Recorded source decision: Alpaca primary candidate; Hugging Face comparison/audit only. |

New follow-up items created from this work:

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-075 | not started | Investigate Hugging Face adjustment/provenance policy and explain provider drift before using HF as a baseline source. |
| SWING-V01-076 | not started | Decide whether `ORCL`, `CRM`, `BAC`, and `CVX` should be recovered from another source or remain excluded from v0.1 qualification. |
| SWING-V01-077 | not started | Promote the selected Alpaca manifests into the baseline manifest package once the remaining qualification gates pass. |

## Hugging Face drift investigation status update - 2026-05-05

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-075 | blocked | Investigation completed enough for a decision: HF shows systematic adjustment/session drift and cannot be promoted. Promotion remains blocked until adjustment/provenance policy is known and tested. |

## Excluded symbol decision status update - 2026-05-05

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-076 | complete | `ORCL`, `CRM`, `BAC`, and `CVX` are absent entirely from both Trading212 local source DBs for `1d` and `1m`; keep excluded for v0.1 unless a new explicit source is added. |

## Alpaca manifest promotion status update - 2026-05-05

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-077 | blocked | Alpaca data manifests are ready, but promotion into the baseline manifest package is blocked until remaining qualification gates and freeze review pass. |

## Overnight qualification backlog update - 2026-05-05

| Activity ID | Title | Epic | Status | Safe to implement immediately | Blocks later work | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| SWING-V01-078 | Overnight evidence consolidation | Reporting and instrumentation | complete | yes | yes | Added consolidated overnight evidence summary and CLI. |
| SWING-V01-079 | Draft baseline manifest bundle | Baseline manifest/freeze process | complete | yes | yes | Generated blocked draft manifest, checklist, and freeze readiness artifacts. |
| SWING-V01-080 | Selected-period data smoke harness | QA and qualification | complete | yes | yes | Added guarded smoke harness and report. Current report fails because selected windows have zero covered sessions. |
| SWING-V01-081 | Dry-run safety report | QA and qualification | complete | yes | yes | Added dry-run safety report proving serious full run remains blocked and broker/order paths are disabled. |
| SWING-V01-082 | Correct source coverage semantics | Data and universe foundation | complete | yes | yes | Fixed Trading212 coverage to require bars in the selected qualification window, not merely the lookback extraction window. |
| SWING-V01-083 | Record selected-period data-window blocker | Discovery and governance | complete | yes | yes | Added overnight checkpoint documenting that Trading212 local DBs end `2025-07-31`. |
| SWING-V01-084 | Decide data/window path | Data and qualification | blocked | no | yes | Need operator decision: acquire newer data through current selected periods or adjust selected periods to covered historical windows. |
| SWING-V01-085 | Regenerate source coverage after data/window decision | Data and qualification | blocked | yes, after SWING-V01-084 | yes | Must pass before exports/manifests are qualification evidence. |
| SWING-V01-086 | Regenerate exports/manifests/preflights after data/window decision | Data and qualification | blocked | yes, after SWING-V01-085 | yes | Existing files are non-qualifying for current selected periods. |
| SWING-V01-087 | Rerun selected-period smoke after data/window decision | QA and qualification | blocked | yes, after SWING-V01-086 | yes | Must show qualification-session counts meet selected plan requirements. |
| SWING-V01-088 | Generate selected-period dry-run replay package | Research/runtime parity | blocked | yes, after SWING-V01-087 | yes | No broker or order submission permitted. |
| SWING-V01-089 | Generate research/runtime selected-period parity report | Research/runtime parity | blocked | yes, after SWING-V01-088 | yes | Use existing baseline package parity machinery. |
| SWING-V01-090 | Rebuild freeze readiness with current evidence | Release/freeze process | blocked | yes, after SWING-V01-089 | yes | Must still block until operator freeze approval is explicit. |
| SWING-V01-091 | Freeze review decision | Release/freeze process | blocked | no | yes | Requires operator approval. Serious full run remains prohibited until this passes. |

Recommended next path:

1. If newer data is available, refresh the Trading212 source DBs through at least `2026-04-24` and resume at `SWING-V01-085`.
2. If newer data is not available, create a historical selected-period plan ending no later than `2025-07-31`, explicitly label it as historical machinery qualification, and resume at `SWING-V01-085`.

## Historical selected-period qualification status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-084 | complete | Chose the historical qualification path rather than waiting for newer data; added `config/swing_machine_v0_1_selected_periods_historical.yaml`. |
| SWING-V01-085 | complete | Historical source coverage passed for Alpaca and Hugging Face over all 48 period/symbol checks. |
| SWING-V01-086 | complete | Regenerated Alpaca historical exports, input plan, manifests, and preflights. |
| SWING-V01-087 | complete | Historical selected-period data smoke passed for all three historical periods. |
| SWING-V01-088 | blocked | Historical smoke dry-run replay completed but returned `FAIL` in both research and runtime-compatible lanes due reconciliation mismatch. |
| SWING-V01-089 | blocked | Package parity report passed between two failed replay packages; this is diagnostic only and cannot qualify parity. |
| SWING-V01-090 | blocked | Freeze readiness cannot be rebuilt as passable evidence until replay and qualifying parity pass. |
| SWING-V01-091 | blocked | Freeze review remains blocked; serious full run remains prohibited. |

New follow-up items:

| Activity ID | Title | Epic | Status | Safe to implement immediately | Blocks later work | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| SWING-V01-092 | Add selected replay-window semantics to manifests/replay | Research/runtime parity | not started | yes | yes | Separate indicator lookback coverage from trade/reconciliation replay window. |
| SWING-V01-093 | Regenerate historical manifests with replay-window metadata | Data and qualification | blocked | yes, after SWING-V01-092 | yes | Historical manifests need explicit replay start/end or equivalent metadata. |
| SWING-V01-094 | Rerun historical smoke replay after replay-window fix | QA and qualification | blocked | yes, after SWING-V01-093 | yes | Must pass before medium/stability replay. |
| SWING-V01-095 | Generate qualifying historical parity evidence | Research/runtime parity | blocked | yes, after SWING-V01-094 | yes | Compare packages from passing replay lanes only. |

## Replay-window semantics status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-092 | complete | Added manifest replay-window fields and scoped replay backtest/reconciliation to selected signal/next-session window while preserving lookback data for features. |
| SWING-V01-093 | complete | Regenerated historical Alpaca manifests with replay-window metadata. |
| SWING-V01-094 | complete with warning | Historical smoke replay no longer fails reconciliation. Windowed replay status is `WARN` due market-holiday calendar validation warnings. |
| SWING-V01-095 | complete with warning | Windowed historical smoke package parity passed with zero differences, but qualification remains warning-blocked until calendar validation is resolved. |

New follow-up items:

| Activity ID | Title | Epic | Status | Safe to implement immediately | Blocks later work | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| SWING-V01-096 | Market-calendar-aware historical panel validation | Data and qualification | not started | yes | yes | Replace or extend `WEEKDAY` expected-session validation so known US market holidays are not treated as missing sessions. |
| SWING-V01-097 | Rerun windowed historical smoke replay after calendar fix | QA and qualification | blocked | yes, after SWING-V01-096 | yes | Target replay status should become `PASS`, not `WARN`. |
| SWING-V01-098 | Run historical medium and stability replay after smoke is clean | QA and qualification | blocked | yes, after SWING-V01-097 | yes | Do not widen replay until smoke replay is clean. |

## Market-calendar and clean smoke replay status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-096 | complete | Added `US_EQUITY` market-calendar-aware validation and selected-period manifest generation now emits `calendar: US_EQUITY`. |
| SWING-V01-097 | complete | Reran windowed historical smoke replay after calendar fix; both research and runtime-compatible lanes now report `PASS`. |
| SWING-V01-098 | not started | Next safe item: run historical medium replay and parity after smoke replay is clean. |

Updated next items:

| Activity ID | Title | Epic | Status | Safe to implement immediately | Blocks later work | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| SWING-V01-098 | Run historical medium replay and parity | QA and qualification | not started | yes | yes | Use `historical_medium_replay_window` manifest and sequential replay lanes. |
| SWING-V01-099 | Run historical contract-stability replay and parity | QA and qualification | blocked | yes, after SWING-V01-098 | yes | Use `historical_contract_stability_window_v0_1` only after medium passes. |
| SWING-V01-100 | Build historical qualification evidence index | Reporting and instrumentation | blocked | yes, after SWING-V01-099 | yes | Consolidate source, smoke, replay, parity, safety, and freeze blockers. |
| SWING-V01-101 | Rebuild freeze readiness with historical evidence | Release/freeze process | blocked | yes, after SWING-V01-100 | yes | Should still block serious full run unless all mandatory gates and operator approval exist. |

## Historical medium replay status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-098 | complete | Historical medium replay passed in research and runtime-compatible lanes; parity passed with zero differences. |
| SWING-V01-099 | not started | Next item: run historical contract-stability replay and parity. |

## Historical qualification batch status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-099 | complete | Historical contract-stability replay passed in research and runtime-compatible lanes; parity passed with zero differences. |
| SWING-V01-100 | complete | Historical qualification evidence index generated at `reports/swing_machine_v0_1/historical_qualification_evidence_index.json`. |
| SWING-V01-101 | complete with BLOCK decision | Historical baseline manifest, qualification checklist, and freeze readiness were rebuilt. Decision remains `BLOCK`; serious full run is still prohibited. |

Remaining backlog grouped by outcome, not one-by-one execution:

| Activity ID | Title | Epic | Status | Safe to implement immediately | Blocks later work | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| SWING-V01-102 | Certify focused unit and contract gate for historical freeze readiness | QA and qualification | not started | yes | yes | Run or assemble the focused unit/contract checks that can legitimately satisfy `unit_contract_tests`; avoid broad live/runtime execution. |
| SWING-V01-103 | Produce historical freeze review packet | Release/freeze process | not started | yes | yes | Consolidate manifests, evidence index, replay summaries, parity reports, dry-run safety, known assumptions, and prohibited actions for human review. |
| SWING-V01-104 | Record operator freeze-review decision | Release/freeze process | blocked | no, needs human approval | yes | Cannot be completed autonomously because it represents explicit operator approval. |
| SWING-V01-105 | Rebuild readiness after certification and review evidence | Release/freeze process | blocked | yes, after SWING-V01-102 and SWING-V01-104 | yes | Should only produce `ALLOW` if all required checks are satisfied and operator approval is explicitly recorded. |
| SWING-V01-106 | Optional Hugging Face provenance reconciliation | Data and qualification | not started | yes | no | Compare Hugging Face historical source coverage/provenance against Alpaca evidence; not required to unblock the current Alpaca historical run. |
| SWING-V01-107 | Optional broader historical selected-period expansion | QA and qualification | not started | yes | no | Add additional historical windows only if the operator wants wider coverage before freeze; avoid chasing newer data by default. |
| SWING-V01-108 | Serious full-run execution plan and guard review | Runtime safety | blocked | yes, after readiness `ALLOW` only | yes | Design the controlled serious full-run command/guard package, but do not execute until explicitly instructed. |

## Freeze-review preparation status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-102 | complete | Focused unit/contract certification passed in two shards: 60 contract/lifecycle/order/risk tests and 72 baseline/data/readiness/qualification tests. Historical readiness was rebuilt with `unit_contract_tests` satisfied. |
| SWING-V01-103 | complete | Created `docs/swing_machine_v0_1_historical_freeze_review_packet.md`. |
| SWING-V01-104 | blocked | Requires explicit operator freeze-review decision and cannot be completed autonomously. |
| SWING-V01-105 | blocked | Rebuild to an `ALLOW` decision is blocked until operator approval is recorded. |
| SWING-V01-106 | optional/not started | Hugging Face provenance reconciliation remains optional, not a blocker for the current Alpaca historical review packet. |
| SWING-V01-107 | optional/not started | Broader historical selected-period expansion remains optional. |
| SWING-V01-108 | blocked | Serious full-run execution planning remains blocked until readiness allows it. |

Current remaining critical path:

| Order | Activity ID | Decision needed |
| --- | --- | --- |
| 1 | SWING-V01-104 | Operator approves freeze, requests more evidence, or defers. |
| 2 | SWING-V01-105 | If approved, rebuild readiness with approval recorded. |
| 3 | SWING-V01-108 | Only after readiness returns `ALLOW`, prepare the guarded serious full-run command package. |

## Operator approval and serious full-run planning status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-104 | complete | Operator approved the engineering evidence; approval recorded at `reports/swing_machine_v0_1/historical_operator_freeze_approval.json`. |
| SWING-V01-105 | complete | Historical readiness rebuilt with operator approval; decision is `ALLOW`, serious full run allowed is `true`, blocker count is 0. |
| SWING-V01-108 | complete for planning, execution not started | Created `docs/swing_machine_v0_1_guarded_serious_full_run_plan.md`. No serious full run was executed. |

Current next decision:

| Option | Description | Recommendation |
| --- | --- | --- |
| Existing-window serious replay | Re-run an already qualified selected-period manifest as the first serious run. | Safest but low additional information. |
| Broader historical manifest first | Build/preflight a broader Alpaca historical manifest, then run paired replay if clean. | Recommended. |
| Live/paper runtime action | Move toward live/paper runtime execution. | Not recommended yet; requires separate explicit approval and runtime guard review. |

## Broad historical serious offline run status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-109 | complete | Created broad historical selected-period plan at `config/swing_machine_v0_1_selected_periods_historical_broad.yaml`. |
| SWING-V01-110 | complete | Preflighted and exported broad Alpaca historical data; all source/data/selected-period/data-smoke/dry-run safety gates passed. |
| SWING-V01-111 | complete | Ran paired broad historical serious offline replay. Research and runtime-compatible lanes passed. Parity passed with zero differences. Run ID: `20260506T124131Z`. |
| SWING-V01-112 | not started | Investigate decision-density semantics for broad historical replay. Current broad run produced 16 decision traces and 2 setups across the full 2024-06-03 to 2025-07-31 window. |
| SWING-V01-113 | not started | Design true multi-session scanner/backtest qualification mode if daily scanning over each historical session is required before paper/live runtime. |

Current next decision:

| Option | Description | Recommendation |
| --- | --- | --- |
| Accept broad replay evidence as sufficient for offline baseline machinery | Treat the passed broad replay/parity as enough for the current offline baseline milestone. | Reasonable for machinery qualification only. |
| Build decision-density diagnostics | Explain exactly why broad replay emits 16 decisions and 2 setups. | Recommended next. |
| Build true day-by-day scanner replay | Extend qualification from package replay to full historical scanner simulation. | Recommended before any paper/live runtime move. |
| Move toward live/paper runtime action | Start runtime execution planning. | Not recommended until decision-density and daily scanner semantics are clear. |

## Decision-density and scanner qualification status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-112 | complete | Decision-density diagnostics created at `reports/swing_machine_v0_1/historical_broad_decision_density_diagnostics_20260506T124131Z.json`; root cause documented in `docs/swing_machine_v0_1_decision_density_review.md`. |
| SWING-V01-113 | complete | Designed separate multi-session scanner qualification mode in `docs/swing_machine_v0_1_multi_session_scanner_design.md`. |
| SWING-V01-114 | complete | Added typed scanner replay contracts for session result, aggregate summary, density metrics, state snapshot, and artifact manifest. |
| SWING-V01-115 | complete | Extracted reusable selected-session replay window/context internals without changing `run-historical-replay` behaviour. |
| SWING-V01-116 | complete | Implemented Tier 1 stateless multi-session scanner iterator and per-session decision-density artifact writer. |
| SWING-V01-117 | complete | Added guarded offline `run-historical-scanner-replay` CLI command. |
| SWING-V01-118 | not started | Add scanner research/runtime-compatible parity report. |
| SWING-V01-119 | not started | Run broad historical scanner-density qualification and review decision density before any paper/live runtime move. |

Current critical path before paper/live runtime:

| Order | Activity ID | Objective |
| --- | --- | --- |
| 1 | SWING-V01-114 | Define scanner contracts so outputs are typed and reviewable. |
| 2 | SWING-V01-115 | Reuse proven selected-session logic safely. |
| 3 | SWING-V01-116 | Produce true day-by-day scanner density over the broad historical manifest. |
| 4 | SWING-V01-117 | Expose scanner replay through a guarded offline CLI. |
| 5 | SWING-V01-118 | Compare research/runtime-compatible scanner outputs. |
| 6 | SWING-V01-119 | Run and review broad scanner-density qualification. |



## Scanner contracts implementation status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-114 | complete | Added scanner replay contracts in `src/swingmachine/contracts.py` and focused contract coverage in `tests/test_contracts.py`. |
| SWING-V01-115 | not started | Next safe implementation slice: extract reusable selected-session replay internals without changing `run-historical-replay` behaviour. |

Current implementation guardrail: existing selected-session replay semantics must remain unchanged while scanner-specific internals are introduced.


## Selected-session replay internals extraction status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-115 | complete | Extracted selected-session window/context helpers in `src/swingmachine/replay.py`; protected existing replay artifacts with focused tests. |
| SWING-V01-116 | not started | Next safe slice: implement Tier 1 stateless multi-session scanner iterator and density artifact writer using the extracted internals. |

Guardrail carried forward: `run-historical-replay` remains selected-session machinery replay. Scanner behaviour must be introduced through a separate path.


## Scanner iterator and guarded CLI status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-116 | complete | Added Tier 1 stateless scanner replay library path and density artifacts in `src/swingmachine/replay.py`. |
| SWING-V01-117 | complete | Added guarded offline `run-historical-scanner-replay` CLI in `src/swingmachine/runtime.py`. |
| SWING-V01-118 | complete | Added scanner research/runtime-compatible parity report. |
| SWING-V01-119 | complete | Broad scanner-density qualification passed in paired lanes with zero parity differences. Run ID: `20260506T155037Z`. |

Scanner CLI safety boundary: the command writes local artifacts only, uses an output-dir-local SQLite runtime DB for run metadata, and does not trigger live trading or real broker orders.


## Scanner parity and broad scanner-density qualification status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-118 | complete | Added scanner parity comparison over scanner summary, session results, decision density, rejection reasons, material decisions, and scanner package artifacts. |
| SWING-V01-119 | complete | Ran paired broad scanner-density qualification. Research and runtime-compatible lanes passed; scanner parity passed with zero differences. Run ID: `20260506T155037Z`. |
| SWING-V01-120 | complete | Decided Tier 2 portfolio/lifecycle simulation qualification is required before paper/live runtime; design created. |

Current scanner qualification evidence:

| Evidence | Result |
| --- | --- |
| Eligible signal sessions | 290 |
| Processed signal sessions | 290 |
| Decision traces | 4,640 |
| Setups | 434 |
| Sessions with setups | 232 |
| Scanner parity differences | 0 |

Current recommendation: do not move to paper/live runtime yet. The next useful workstream is Tier 2 portfolio/lifecycle simulation or an explicit operator decision to defer Tier 2.

## Tier 2 portfolio/lifecycle qualification status update - 2026-05-06

| Activity ID | Status | Notes |
| --- | --- | --- |
| SWING-V01-120 | complete | Tier 2 portfolio/lifecycle simulation qualification design created at `docs/swing_machine_v0_1_tier2_portfolio_lifecycle_qualification_design.md`. Paper trading remains blocked. |
| SWING-V01-121 | not started | Add Tier 2 lifecycle replay contracts and artifact manifest models. |
| SWING-V01-122 | not started | Add lifecycle artifact schema tests and fixture builders. |
| SWING-V01-123 | not started | Build lifecycle qualification artifacts from existing `BacktestResult` outputs. |
| SWING-V01-124 | not started | Add lifecycle reconciliation checks for cash/equity, pending/active/exit state validity, fills, closes, spent setups, and exposure. |
| SWING-V01-125 | not started | Add lifecycle research/runtime-compatible parity report. |
| SWING-V01-126 | not started | Add guarded offline `run-historical-portfolio-lifecycle-replay` CLI. |
| SWING-V01-127 | not started | Run fixture lifecycle qualification and focused tests. |
| SWING-V01-128 | not started | Run broad historical lifecycle qualification. |
| SWING-V01-129 | not started | Run thorough pre-paper test gate with long bounded timeout. |
| SWING-V01-130 | blocked | Produce paper-trading review packet only after Tier 2 and full pre-paper gate pass. |

Current paper-trading status: blocked. The next implementation item is `SWING-V01-121`.


## Tier 2 portfolio/lifecycle qualification backlog slice - added 2026-05-06

This slice is required before any paper-trading move. Tier 1 scanner-density qualification passed, but it is stateless. Tier 2 must prove stateful pending-entry, active-position, exit, cash/equity, exposure, reconciliation, and research/runtime parity behaviour across historical sessions.

### SWING-V01-120 - Decide and design Tier 2 portfolio/lifecycle qualification

Epic: QA and qualification

Objective: Decide whether the system is ready for paper trading after Tier 1 scanner qualification, and define the missing Tier 2 gate.

Why it matters: Paper trading without stateful portfolio/lifecycle evidence would test unqualified behaviour.

Files/modules likely affected:

- `docs/swing_machine_v0_1_tier2_portfolio_lifecycle_qualification_design.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Review current Tier 1 evidence.
- Inspect existing stateful backtest, lifecycle, and exit code.
- Define Tier 2 artifacts, reconciliation checks, and pre-paper test policy.
- Mark paper trading blocked until Tier 2 and thorough test gate pass.

Dependencies: `SWING-V01-119`

Tests to add or update: None; design/backlog activity only.

Acceptance criteria:

- Tier 2 design exists.
- Paper-trading gate is explicit.
- Follow-on implementation activities are defined.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-121 - Add Tier 2 lifecycle replay contracts and artifact manifest models

Epic: Trade lifecycle and exits

Objective: Add typed contracts for Tier 2 portfolio/lifecycle replay artifacts.

Why it matters: The qualification run needs stable, reviewable outputs before a broad replay can be trusted.

Files/modules likely affected:

- `src/swingmachine/contracts.py`
- `tests/test_contracts.py`

Implementation steps:

- Add lifecycle replay summary model.
- Add session state model.
- Add transition model.
- Add position snapshot model.
- Add pending order snapshot model.
- Add exposure snapshot model.
- Add reconciliation model.
- Add artifact manifest model.
- Add focused contract tests.

Dependencies: `SWING-V01-120`

Tests to add or update: Contract tests for valid models, invalid state, serialization, and deterministic fields.

Acceptance criteria:

- Tier 2 contract models serialize to JSON-compatible structures.
- Required identity, date, state, evidence, and config fields are typed.
- Invalid impossible state summaries are rejected where practical.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-122 - Add lifecycle artifact schema tests and fixture builders

Epic: QA and qualification

Objective: Create small reusable fixtures for lifecycle replay packages.

Why it matters: Later replay/parity work should not depend on large historical data to prove schema correctness.

Files/modules likely affected:

- `tests/test_contracts.py`
- `tests/test_replay_workflow.py`
- possible `tests/fixtures/` helper module

Implementation steps:

- Build minimal valid lifecycle session fixture.
- Build pending-entry, active-position, exit-transition, and exposure fixtures.
- Add tests for manifest completeness and reconciliation serialization.

Dependencies: `SWING-V01-121`

Tests to add or update: New fixture-backed schema tests.

Acceptance criteria:

- Fixture package can represent pending, active, exited, and blocked lifecycle outcomes.
- Tests run without external data.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-123 - Build lifecycle qualification artifacts from existing backtest outputs

Epic: Trade lifecycle and exits

Objective: Convert existing `BacktestResult` state/trades/events/equity outputs into Tier 2 artifact files.

Why it matters: This uses the current stateful engine before introducing any new runtime behaviour.

Files/modules likely affected:

- `src/swingmachine/replay.py`
- `src/swingmachine/backtest.py` only if additional non-behavioural export fields are needed
- `tests/test_replay_workflow.py`

Implementation steps:

- Add artifact writer for lifecycle replay summary.
- Emit per-session state summaries from equity/events/trades where possible.
- Emit lifecycle transitions from existing event/trade evidence.
- Emit positions, pending orders, exposure, and manifest artifacts.
- Keep this offline and artifact-only.

Dependencies: `SWING-V01-121`, `SWING-V01-122`

Tests to add or update: Fixture replay artifact writer tests.

Acceptance criteria:

- A small historical fixture produces all required Tier 2 artifact files.
- No broker/order submission adapter can be reached.
- Output includes manifest paths and counts.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-124 - Add lifecycle reconciliation checks

Epic: QA and qualification

Objective: Add deterministic reconciliation checks for stateful lifecycle artifacts.

Why it matters: Passing artifacts are not enough; impossible or inconsistent portfolio state must fail before paper trading.

Files/modules likely affected:

- `src/swingmachine/replay.py`
- `tests/test_replay_workflow.py`

Implementation steps:

- Check active plus pending conflicts by symbol.
- Check exit-pending without active position.
- Check entry fills create one active position.
- Check closed positions map to trade records.
- Check cash/equity tolerance where available.
- Check exposure matches positions and pending plans.
- Write reconciliation JSON.

Dependencies: `SWING-V01-123`

Tests to add or update: Passing and failing reconciliation fixture tests.

Acceptance criteria:

- Reconciliation emits `PASS`/`FAIL` plus reason codes.
- Material inconsistency causes qualification failure.
- Rejection and lifecycle reason codes remain explainable.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-125 - Add lifecycle research/runtime-compatible parity report

Epic: Research/runtime parity

Objective: Compare two Tier 2 lifecycle replay output directories for deterministic parity.

Why it matters: Paper trading should not start if research and runtime-compatible lifecycle paths diverge.

Files/modules likely affected:

- `src/swingmachine/replay.py`
- `tests/test_baseline_parity.py`

Implementation steps:

- Add lifecycle artifact normalizer.
- Ignore run-specific timestamps/output paths only.
- Compare lifecycle summaries, states, transitions, positions, exposure, reconciliation, and manifest counts.
- Emit parity report JSON.

Dependencies: `SWING-V01-123`, `SWING-V01-124`

Tests to add or update: Lifecycle parity pass/fail tests.

Acceptance criteria:

- Identical fixture lifecycle packages pass with zero differences.
- Material transition/state/exposure differences fail.
- Timestamp/path-only differences are ignored.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-126 - Add guarded offline lifecycle replay CLI

Epic: Runtime jobs

Objective: Add a safe CLI for offline historical portfolio/lifecycle replay.

Why it matters: Qualification needs a repeatable operator command that cannot submit real broker orders.

Files/modules likely affected:

- `src/swingmachine/runtime.py`
- `src/swingmachine/replay.py`
- `tests/test_runtime.py`

Implementation steps:

- Add `run-historical-portfolio-lifecycle-replay` command.
- Require manifest, output directory, and explicit profile/config.
- Write artifacts only under output directory.
- Refuse live/paper broker modes.
- Return non-zero on failed reconciliation.

Dependencies: `SWING-V01-123`, `SWING-V01-124`

Tests to add or update: CLI smoke test with fixture data and safety refusal test.

Acceptance criteria:

- CLI runs fixture qualification offline.
- CLI refuses unsafe live/paper execution options.
- CLI writes manifest and summary artifacts.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-127 - Run fixture lifecycle qualification and focused tests

Epic: QA and qualification

Objective: Prove the Tier 2 implementation works on deterministic fixtures before broad historical execution.

Why it matters: Broad runs are expensive and should not be used as first-line debugging.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Run Tier 2 contract tests.
- Run lifecycle replay workflow tests.
- Run runtime CLI tests.
- Run lifecycle parity tests.
- Record outputs and failures.

Dependencies: `SWING-V01-121` through `SWING-V01-126`

Tests to add or update: None beyond executing the focused suite.

Acceptance criteria:

- Focused Tier 2 tests pass.
- Fixture lifecycle qualification artifacts are generated.
- Any failures are fixed or logged as blockers.

Safe to implement immediately: no

Blocks later work: yes

Status: complete

### SWING-V01-128 - Run broad historical lifecycle qualification

Epic: QA and qualification

Objective: Run Tier 2 over the broad historical manifest and produce qualification evidence.

Why it matters: This is the core stateful historical evidence required before any paper-trading decision.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`
- possible qualification summary doc

Implementation steps:

- Run broad research lifecycle replay.
- Run broad runtime-compatible lifecycle replay if applicable.
- Run lifecycle parity comparison.
- Record run IDs and metrics.
- Mark pass/fail/blocker.

Dependencies: `SWING-V01-127`

Tests to add or update: None; this is qualification execution.

Acceptance criteria:

- Broad lifecycle replay completes without unsafe runtime access.
- Reconciliation passes or produces explicit blockers.
- Parity passes with zero material differences.
- Evidence artifacts are stored under `reports/swing_machine_v0_1/`.

Safe to implement immediately: no

Blocks later work: yes

Status: complete

### SWING-V01-129 - Run thorough pre-paper test gate

Epic: QA and qualification

Objective: Run the full pre-paper validation suite with a long bounded timeout.

Why it matters: The user explicitly prefers a thorough suite before paper trading, even if it exceeds 30 minutes.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Run full `ruff check` over source/tests.
- Run full `pytest` suite.
- Confirm selected-session replay evidence remains clean.
- Confirm scanner-density evidence remains clean.
- Confirm Tier 2 lifecycle evidence remains clean.
- Rebuild or update readiness artifacts.

Dependencies: `SWING-V01-128`

Tests to add or update: None; this executes the full gate.

Acceptance criteria:

- Full suite passes within the agreed long timeout or fails with recorded blocker evidence.
- No live trading, broker orders, production deployment, or destructive DB changes occur.
- Paper-trading review remains blocked unless this gate passes.

Safe to implement immediately: no

Blocks later work: yes

Status: complete

### SWING-V01-130 - Produce paper-trading review packet and guarded approval gate

Epic: Release/freeze process

Objective: Produce the final operator review packet before any paper-trading trial.

Why it matters: Paper trading should be a controlled operational decision, not an automatic next command after tests pass.

Files/modules likely affected:

- `docs/swing_machine_v0_1_paper_trading_review_packet.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Summarize selected-session, scanner, lifecycle, parity, and full-suite evidence.
- List all residual risks and caveats.
- Confirm no `.env` strategy behaviour is required.
- Define the exact paper command/runbook, still guarded and dry-run reviewed.
- Require explicit operator approval before running paper runtime.

Dependencies: `SWING-V01-129`

Tests to add or update: None; review packet only.

Acceptance criteria:

- Review packet exists.
- Paper trading remains prohibited unless operator explicitly approves the exact next command.
- Residual blockers are explicit.

Safe to implement immediately: no

Blocks later work: yes

Status: complete

### SWING-V01-131 - Export full backtest lifecycle state for Tier 2 snapshots

Epic: Trade lifecycle and exits

Objective: Expand the stateful backtest output so Tier 2 artifacts can include real pending-order and open-position snapshots instead of warning about missing detail.

Why it matters: Broad lifecycle qualification is deterministic and parity-clean, but remains `WARN` until pending-order/open-position evidence is fully populated.

Files/modules likely affected:

- `src/swingmachine/backtest.py`
- `src/swingmachine/contracts.py`
- `src/swingmachine/replay.py`
- `tests/test_replay_workflow.py`

Implementation steps:

- Add typed backtest lifecycle state export fields.
- Capture pending entries with intent IDs, quantities, stop/limit prices, setup IDs, created/expiry sessions, and cancellation reasons.
- Capture active positions per session with current stop, highest high, risk amount, sector, and setup IDs.
- Feed these exports into Tier 2 lifecycle artifacts.
- Remove or reduce the current missing-detail reconciliation warnings when evidence is complete.

Dependencies: `SWING-V01-128`

Tests to add or update: Backtest lifecycle state export tests, artifact population tests, and broad lifecycle reconciliation tests.

Acceptance criteria:

- Tier 2 pending-order snapshots are populated from real backtest state.
- Tier 2 open-position snapshots are populated from real backtest state.
- Broad lifecycle replay can reach `PASS` unless another real reconciliation issue is found.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-132 - Repair local console-script entry point for broad CLI execution

Epic: Runtime jobs

Objective: Ensure the local virtualenv exposes the `swingmachine` console script declared in `pyproject.toml`.

Why it matters: The Typer command is tested, but broad execution had to call replay functions directly because `.venv/bin/swingmachine` was unavailable.

Files/modules likely affected:

- Local virtualenv/package installation state
- possibly project setup docs

Implementation steps:

- Inspect local package installation mode.
- Install the project into `.venv` if needed using the repo-local environment.
- Confirm `.venv/bin/swingmachine --help` works.
- Document the expected operator command.

Dependencies: none

Tests to add or update: CLI smoke command check if appropriate.

Acceptance criteria:

- `.venv/bin/swingmachine` exists and exposes `run-historical-portfolio-lifecycle-replay`.
- No global Python/tooling changes are required.

Safe to implement immediately: yes

Blocks later work: no

Status: complete

### SWING-V01-133 - Prepare first controlled paper-trading runbook and command preflight

Epic: Runtime jobs

Objective: Define and preflight the exact first paper-trading command without executing paper trading.

Why it matters: Engineering gates now pass, but paper trading is still an operator action and must be explicit, observable, reversible, and paper-only.

Files/modules likely affected:

- `docs/swing_machine_v0_1_first_paper_runbook.md`
- possible runtime/preflight helpers if missing

Implementation steps:

- Identify the intended paper runtime command and profile.
- Define database/output/report paths.
- Define kill-switch and stop criteria.
- Define first-run observation checklist.
- Confirm paper-only broker mode and no live order route.
- Run non-executing command/path/config preflight only.

Dependencies: `SWING-V01-130`, `SWING-V01-131`, `SWING-V01-132`

Tests to add or update: Dry-run/preflight test only if a helper is introduced.

Acceptance criteria:

- Runbook exists.
- Exact command is documented but not executed.
- Paper-only safety checks are explicit.
- Operator approval remains required before execution.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-134 - Prepare reviewed first paper cycle input package

Epic: Runtime jobs

Objective: Build the specific `cycle_input.yaml` package for the first controlled paper trial without executing paper mode.

Why it matters: The paper command requires a reviewed `RuntimeCycleInput`; the runbook alone is not enough to execute safely.

Files/modules likely affected:

- `reports/swing_machine_v0_1/first_paper_trial_<RUN_ID>/cycle_input.yaml`
- `reports/swing_machine_v0_1/first_paper_trial_<RUN_ID>/cycle_input_review.md`

Implementation steps:

- Select or generate reviewed setups from the latest eligible signal package.
- Build a concrete `RuntimeCycleInput` file.
- Hash the input file.
- Document each setup, sizing assumption, and rejection/safety expectation.
- Do not run paper mode.

Dependencies: `SWING-V01-133`

Tests to add or update: None unless a generator helper is introduced.

Acceptance criteria:

- Concrete cycle input exists.
- Review document explains every setup.
- Operator can decide whether to run shadow preview.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-135 - Run first paper shadow preview only

Epic: Runtime jobs

Objective: Run `run-cycle --mode SHADOW` against the reviewed first paper input and produce preview evidence.

Why it matters: Shadow preview is the mandatory final gate before paper execution.

Files/modules likely affected:

- `reports/swing_machine_v0_1/first_paper_trial_<RUN_ID>/shadow_preview.json`
- `reports/swing_machine_v0_1/first_paper_trial_<RUN_ID>/shadow_preview_review.md`

Implementation steps:

- Run the documented shadow command.
- Confirm no paper order batch is present.
- Review proposals, reject reasons, quantities, limits, stops, and alerts.
- Do not run paper mode.

Dependencies: `SWING-V01-134`

Tests to add or update: None.

Acceptance criteria:

- Shadow preview exists.
- Shadow review is complete.
- Paper execution remains blocked pending operator approval.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-136 - Execute first controlled paper cycle only after explicit approval

Epic: Runtime jobs

Objective: Execute one paper-mode cycle after the operator approves the exact command.

Why it matters: This is the first actual paper-trading action and must be controlled.

Files/modules likely affected:

- `reports/swing_machine_v0_1/first_paper_trial_<RUN_ID>/paper_cycle_output.json`
- `reports/swing_machine_v0_1/first_paper_trial_<RUN_ID>/paper_runtime.db`
- `reports/swing_machine_v0_1/first_paper_trial_<RUN_ID>/post_run_review.md`

Implementation steps:

- Confirm operator approval record exists.
- Execute the exact approved paper command.
- Review output and local paper runtime database.
- Record post-run review.
- Stop after one cycle.

Dependencies: `SWING-V01-135`, explicit operator approval

Tests to add or update: None.

Acceptance criteria:

- One paper cycle executes successfully or fails safely.
- Post-run review is complete.
- No live trading or real broker order path is used.

Safe to implement immediately: no

Blocks later work: yes

Status: blocked

## Mechanical readiness completion and historical performance qualification backlog slice - added 2026-05-07

This slice supersedes immediate paper execution as the next strategic direction. Paper trading remains important, but historical profitability should not be pursued until the engine is mechanically complete enough that results are trustworthy.

### SWING-V01-137 - Consolidated mechanical readiness report design and generator

Epic: QA and qualification

Objective: Produce a single mechanical readiness report that indexes data, config, scanner, lifecycle, parity, dry-run safety, tests, and blockers.

Why it matters: We need one authoritative `PASS/WARN/BLOCK` view before trusting historical performance or paper execution.

Files/modules likely affected:

- `src/swingmachine/mechanical_readiness.py`
- `src/swingmachine/runtime.py`
- `docs/swing_machine_v0_1_mechanical_readiness_completion_design.md`
- `reports/swing_machine_v0_1/mechanical_readiness_<RUN_ID>.json`

Implementation steps:

- Define readiness evidence inputs.
- Index latest broad scanner/lifecycle/parity/test/dry-run artifacts.
- Emit `PASS`, `WARN`, or `BLOCK` decision.
- Emit markdown summary for operator review.
- Add CLI command for report generation.

Dependencies: current qualification artifacts

Tests to add or update: Unit tests for pass/warn/block decision logic and missing-evidence blockers.

Acceptance criteria:

- Report identifies latest evidence.
- Missing or stale evidence blocks readiness.
- Clean current evidence produces `PASS` or explicit residual warnings.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-138 - Explicit lookahead-bias and point-in-time feature audit

Epic: Data and universe foundation

Objective: Add checks proving signal features, symbol eligibility, earnings timing, and replay windows do not use future information.

Why it matters: Historical performance is meaningless if the feature panel leaks future data.

Files/modules likely affected:

- `src/swingmachine/data_contracts.py`
- `src/swingmachine/replay.py`
- `tests/test_data_contracts.py`
- readiness reports

Implementation steps:

- Check feature session dates are not after signal decision dates.
- Check feature coverage start/end windows are respected.
- Check symbol reference effective/tradability windows are point-in-time.
- Check earnings timing fields are usable from the decision date.
- Add blocker codes for violations.

Dependencies: current data manifest validation

Tests to add or update: Positive/negative manifest and feature-window tests.

Acceptance criteria:

- Lookahead violations fail readiness.
- Clean historical panels pass with explicit evidence.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-151 - Prepared feature provenance evidence for broad lookahead audit

Epic: Data and universe foundation

Objective: Remove the remaining lookahead audit warning by either adding a prepared feature panel to the broad historical manifest or adding equivalent feature-provenance evidence for runtime-computed features.

Why it matters: The lookahead audit is implemented, but the current broad historical manifest does not declare prepared features, so the system cannot fully prove signal feature point-in-time cleanliness from the manifest alone.

Files/modules likely affected:

- `data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml`
- broad historical feature export artifacts
- `src/swingmachine/lookahead_audit.py`
- `reports/swing_machine_v0_1/lookahead_audit_<RUN_ID>.json`

Implementation steps:

- Decide whether broad historical qualification should use a declared prepared feature panel or explicit runtime feature-provenance manifest.
- If using prepared features, generate/export the feature panel deterministically from point-in-time OHLCV and symbol reference data.
- Add the feature file to the broad manifest with row count and checksum.
- Re-run the lookahead audit and require `PASS`.
- Rebuild the mechanical readiness report and confirm the lookahead warning clears.

Dependencies: `SWING-V01-138`, broad historical data source

Tests to add or update: Extend lookahead audit coverage if the chosen provenance format differs from prepared feature panels.

Acceptance criteria:

- Broad lookahead audit status is `PASS`, not `WARN`.
- Feature provenance is explicit and reviewable.
- Mechanical readiness no longer lists lookahead audit as a warning or next required action.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-139 - End-to-end decision ledger package

Epic: Reporting and instrumentation

Objective: Join candidate, rejection, signal, risk, order, lifecycle, position, and trade evidence into a single explainable ledger.

Why it matters: The engine should explain every material decision from universe review to lifecycle outcome.

Files/modules likely affected:

- `src/swingmachine/replay.py`
- `src/swingmachine/reporting.py`
- `tests/test_replay_workflow.py`
- `reports/swing_machine_v0_1/decision_ledger_<RUN_ID>.json`

Implementation steps:

- Define ledger row schema.
- Join by symbol, setup id, signal session, order intent id, and position id.
- Include accepted and rejected candidates.
- Include risk/order/lifecycle outcomes.
- Emit summary counts and missing-link warnings.

Dependencies: lifecycle artifacts and scanner artifacts

Tests to add or update: Fixture ledger completeness tests and missing-link failure tests.

Acceptance criteria:

- Ledger can trace accepted setup to order/lifecycle outcome.
- Ledger can explain rejected candidate reason codes.
- Missing critical links produce warnings or blockers.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-152 - Enrich decision ledger source artifacts

Epic: Reporting and instrumentation

Objective: Add candidate, rejection, signal, risk-plan, and order-plan detail to scanner/lifecycle artifacts so the decision ledger can clear missing-link warnings.

Why it matters: The initial ledger links accepted setups through order/lifecycle/position outcomes, but it cannot yet explain rejected candidate reason codes or risk/order-plan IDs because those details are not present in the current broad artifacts.

Files/modules likely affected:

- `src/swingmachine/replay.py`
- `src/swingmachine/decision_ledger.py`
- `tests/test_replay_workflow.py`
- `tests/test_decision_ledger.py`
- `reports/swing_machine_v0_1/decision_ledger_<RUN_ID>.json`

Implementation steps:

- Extend scanner artifacts with per-symbol candidate/rejection rows and reason codes.
- Extend scanner or lifecycle artifacts with stable signal, risk plan, and order plan identifiers.
- Update decision ledger joins to consume the enriched artifacts.
- Rebuild the broad decision ledger and require missing critical links to fall to zero or to explicitly justified residual warnings.

Dependencies: `SWING-V01-139`

Tests to add or update: Replay artifact fixture tests and decision ledger completeness tests.

Acceptance criteria:

- Rejected candidate rows include reason codes in the ledger.
- Accepted setup rows include signal, risk plan, and order plan identifiers where available.
- Mechanical readiness no longer lists decision ledger as a warning or next required action.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-140 - Risk and portfolio adversarial fixture coverage

Epic: Risk and portfolio constraints

Objective: Add adversarial tests for duplicate symbols, pending/open conflicts, portfolio heat, sector caps, daily risk caps, and rejected entries.

Why it matters: Mechanical confidence requires knowing portfolio controls fail closed.

Files/modules likely affected:

- `tests/test_replay_workflow.py`
- `tests/test_portfolio_manager.py`
- `tests/test_contracts.py`
- possible fixture helpers

Implementation steps:

- Add duplicate symbol fixture.
- Add pending plus active conflict fixture.
- Add portfolio heat cap fixture.
- Add sector concentration fixture.
- Add daily new risk cap fixture.
- Assert explicit reject reasons.

Dependencies: current portfolio/lifecycle contracts

Tests to add or update: New adversarial unit/fixture tests.

Acceptance criteria:

- Risk controls reject unsafe entries deterministically.
- Rejection reasons are explicit.
- No lifecycle artifact can silently exceed configured constraints.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-141 - Exit lifecycle adversarial fixture coverage

Epic: Trade lifecycle and exits

Objective: Add adversarial tests for initial stop, trailing stop, time exit, earnings exit, expiry, cancellation, and exit-pending behaviour.

Why it matters: Profitability and paper trading both depend on exits behaving exactly as designed.

Files/modules likely affected:

- `tests/test_replay_workflow.py`
- `tests/test_lifecycle.py`
- `tests/test_exits.py`
- `src/swingmachine/backtest.py` if export gaps are found

Implementation steps:

- Add stop-hit fixture.
- Add trailing-stop update and hit fixture.
- Add time-stop fixture.
- Add earnings-exit fixture.
- Add pending-entry expiry fixture.
- Assert lifecycle transitions and snapshots.

Dependencies: current lifecycle snapshot export

Tests to add or update: New exit lifecycle tests.

Acceptance criteria:

- Every supported exit path has deterministic fixture evidence.
- Lifecycle transitions reconcile with trades and equity.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-142 - First paper cycle input package generator design

Epic: Runtime jobs

Objective: Design how a reviewed `RuntimeCycleInput` should be generated from an approved signal package without manual YAML assembly mistakes.

Why it matters: Even if paper execution waits, cycle input generation must be mechanically safe and explainable.

Files/modules likely affected:

- `src/swingmachine/runtime.py`
- `src/swingmachine/replay.py`
- `docs/swing_machine_v0_1_first_paper_runbook.md`
- possible `src/swingmachine/cycle_input_builder.py`

Implementation steps:

- Define source artifacts for cycle input.
- Map signal/risk/order plans into `RuntimeCycleInput`.
- Include config hash, input hash, and review metadata.
- Add validation that mode is not embedded in input.
- Emit review markdown.

Dependencies: decision ledger package

Tests to add or update: Cycle input builder contract tests.

Acceptance criteria:

- Reviewed cycle input can be generated reproducibly.
- Input package is paper/shadow compatible and operator-reviewable.

Safe to implement immediately: yes

Blocks later work: no

Status: not started

### SWING-V01-143 - Historical performance qualification metric contracts

Epic: Research/backtesting

Objective: Define typed performance metric contracts for equity, trades, drawdowns, benchmark comparison, concentration, regimes, and cost sensitivity.

Why it matters: Performance results must be structured and reviewable, not ad hoc notebook output.

Files/modules likely affected:

- `src/swingmachine/contracts.py`
- `src/swingmachine/performance.py`
- `tests/test_contracts.py`
- `docs/swing_machine_v0_1_historical_performance_qualification_design.md`

Implementation steps:

- Add performance summary model.
- Add trade metrics model.
- Add drawdown model.
- Add benchmark comparison model.
- Add concentration model.
- Add cost sensitivity model.

Dependencies: mechanical readiness design

Tests to add or update: Contract serialization and validation tests.

Acceptance criteria:

- Performance report outputs are typed and JSON-serializable.
- Missing/invalid metric inputs are rejected explicitly.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-144 - Historical performance engine from backtest/lifecycle outputs

Epic: Research/backtesting

Objective: Calculate historical performance metrics from the qualified stateful backtest and lifecycle artifacts.

Why it matters: This is the first honest profitability measurement for the baseline.

Files/modules likely affected:

- `src/swingmachine/performance.py`
- `src/swingmachine/replay.py`
- `tests/test_performance.py`

Implementation steps:

- Load backtest/lifecycle results.
- Build equity curve metrics.
- Build trade metrics.
- Build drawdowns.
- Build exposure and concentration metrics.
- Emit artifacts.

Dependencies: `SWING-V01-143`, mechanical readiness gate

Tests to add or update: Deterministic fixture performance tests.

Acceptance criteria:

- Fixture performance metrics match hand-calculated expected values.
- Broad run can emit performance artifacts without strategy changes.

Safe to implement immediately: no

Blocks later work: yes

Status: complete

### SWING-V01-145 - Benchmark comparison design and implementation

Epic: Research/backtesting

Objective: Compare strategy returns against benchmark buy-and-hold over the same dates.

Why it matters: Absolute profit is not enough; the strategy must justify itself versus a simple alternative.

Files/modules likely affected:

- `src/swingmachine/performance.py`
- `src/swingmachine/data_contracts.py`
- `tests/test_performance.py`

Implementation steps:

- Select benchmark source from qualified manifest or validated provider file.
- Build buy-and-hold equity curve.
- Compare total return, drawdown, volatility, Sharpe, and excess return.
- Emit benchmark comparison artifact.

Progress note:

- Typed benchmark comparison support and aligned-date unit coverage now exist in `src/swingmachine/performance.py`.
- Benchmark prices are now loaded from the qualified historical manifest and included in the latest performance packet.

Dependencies: `SWING-V01-143`, `SWING-V01-144`

Tests to add or update: Benchmark fixture tests.

Acceptance criteria:

- Benchmark dates align with strategy dates.
- Missing benchmark data blocks performance decision unless explicitly accepted.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-146 - Cost and slippage sensitivity performance runs

Epic: Research/backtesting

Objective: Evaluate whether performance survives zero/base/high cost and slippage assumptions.

Why it matters: A fragile edge that disappears under realistic friction should not go to paper.

Files/modules likely affected:

- `src/swingmachine/performance.py`
- `src/swingmachine/backtest.py`
- performance reports

Implementation steps:

- Define cost scenarios.
- Run or re-price performance under each scenario.
- Compare total return, drawdown, profit factor, and expectancy.
- Emit sensitivity artifact.

Progress note:

- Explicit additional-cost scenarios are now emitted from lifecycle CLOSED-position turnover.
- Remaining final-quality gap is not the sensitivity mechanism; it is the lack of a first-class historical trade fill/cost ledger.

Dependencies: `SWING-V01-144`

Tests to add or update: Cost sensitivity fixture tests.

Acceptance criteria:

- Sensitivity report exists.
- Performance decision includes friction robustness.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-153 - Historical trade fill and cost ledger

Epic: Research/backtesting

Objective: Emit a first-class historical trade ledger containing entry fill, exit fill, quantity, gross PnL, net PnL, bars held, exit reason, and transaction cost attribution for each completed trade.

Why it matters: Current performance evidence uses lifecycle equity and CLOSED-position proxy metrics. That is useful engineering evidence, but final profitability qualification needs trade-level attribution that can be independently reviewed.

Files/modules likely affected:

- `src/swingmachine/replay.py`
- `src/swingmachine/backtest.py`
- `src/swingmachine/contracts.py`
- `src/swingmachine/performance.py`
- `tests/test_replay_workflow.py`
- `tests/test_backtest.py`
- `tests/test_performance.py`

Implementation steps:

- Define a typed historical trade ledger row.
- Emit closed-trade rows from the lifecycle replay using the same order/fill lifecycle evidence used for equity.
- Include entry and exit fill prices, reference prices, quantity, setup ID, order intent IDs where available, gross PnL, estimated or actual costs, net PnL, bars held, and exit reason.
- Teach performance reporting to prefer the trade ledger over CLOSED-position proxy metrics.
- Add reconciliation checks between final equity, closed trade PnL, and lifecycle transitions.
- Keep proxy mode only as a warning fallback.

Dependencies: `SWING-V01-144`, `SWING-V01-146`

Tests to add or update: Trade ledger fixture tests, lifecycle-to-ledger reconciliation tests, performance report preference tests.

Acceptance criteria:

- A broad lifecycle replay emits a historical trade ledger artifact.
- Performance reports use trade ledger metrics when present.
- Proxy trade metric warning disappears when a valid trade ledger is present.
- Ledger totals reconcile to lifecycle equity within documented tolerances.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-147 - Regime, period, sector, and ranking-bucket performance breakdowns

Epic: Research/backtesting

Objective: Break performance into regime, calendar period, sector, setup type, and ranking buckets.

Why it matters: We need to know whether results are robust or concentrated in one lucky slice.

Files/modules likely affected:

- `src/swingmachine/performance.py`
- `src/swingmachine/reporting.py`
- performance reports

Implementation steps:

- Group trades/equity by month and quarter.
- Group by regime.
- Group by sector and setup type.
- Group by ranking/quality bucket.
- Emit breakdown artifacts.

Progress note:

- Calendar, entry-regime, exit-reason, and sector trade breakdowns are now emitted from the trade ledger.
- Setup-type and ranking-bucket attribution is now emitted when scanner material decisions are supplied.

Dependencies: `SWING-V01-144`

Tests to add or update: Breakdown fixture tests.

Acceptance criteria:

- Performance concentration is explicit.
- Low-sample breakdowns are labelled as low confidence.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-154 - Setup-type and ranking-bucket performance attribution

Epic: Research/backtesting

Objective: Join historical trade ledger rows back to scanner/decision-ledger metadata so performance can be broken down by setup type, candidate score, rank, and ranking bucket.

Why it matters: Current performance breakdowns can explain calendar, regime, sector, and exit-reason behavior, but they cannot yet show whether ranking quality or setup type is helping or hurting.

Files/modules likely affected:

- `src/swingmachine/performance.py`
- `src/swingmachine/decision_ledger.py`
- `src/swingmachine/replay.py`
- `tests/test_performance.py`
- `tests/test_decision_ledger.py`

Implementation steps:

- Define setup/ranking attribution input contract.
- Load scanner material decisions or decision-ledger rows keyed by setup ID.
- Attach setup type, candidate score, rank, and rank bucket to trade ledger performance rows.
- Emit setup-type and ranking-bucket breakdowns.
- Keep missing-attribution warnings explicit when source metadata is absent.

Dependencies: `SWING-V01-147`, `SWING-V01-153`

Tests to add or update: Attribution join fixture tests and ranking-bucket breakdown tests.

Acceptance criteria:

- Performance reports include setup-type and ranking-bucket breakdowns when attribution metadata is available.
- Missing attribution is recorded explicitly rather than silently omitted.
- The broad performance packet either includes the attribution or records a precise missing-source reason.

Safe to implement immediately: yes

Blocks later work: no

Status: complete

### SWING-V01-148 - Provider robustness comparison: Alpaca versus Hugging Face

Epic: Data and universe foundation

Objective: Compare historical performance and decision stability across the owned Alpaca and Hugging Face datasets where compatible.

Why it matters: If results depend heavily on one provider's quirks, paper trading confidence should be lower.

Files/modules likely affected:

- `src/swingmachine/performance.py`
- `src/swingmachine/data_contracts.py`
- Trading212 source integration docs/reports

Implementation steps:

- Identify compatible Hugging Face manifest/panel.
- Run mechanical readiness checks on provider panel.
- Run performance report on both providers.
- Compare trades, returns, drawdowns, and missing-data effects.

Dependencies: `SWING-V01-144`, `SWING-V01-145`

Tests to add or update: Provider comparison fixture tests where possible.

Acceptance criteria:

- Provider comparison report exists or clearly blocks on data incompatibility.
- Provider drift is quantified.

Safe to implement immediately: yes

Blocks later work: no

Status: complete

### SWING-V01-149 - Historical performance qualification report and decision packet

Epic: QA and qualification

Objective: Produce the final historical performance review packet with decision: paper consideration, research required, or block.

Why it matters: This is the actual profitability checkpoint the user correctly identified as missing.

Files/modules likely affected:

- `docs/swing_machine_v0_1_historical_performance_review.md`
- `reports/swing_machine_v0_1/historical_performance_<RUN_ID>/`

Implementation steps:

- Gather performance artifacts.
- Summarize returns, drawdowns, trades, concentration, costs, benchmark, and provider robustness.
- Assign `PASS_FOR_PAPER_CONSIDERATION`, `WARN_RESEARCH_REQUIRED`, or `BLOCK_PAPER_TRADING`.
- Document caveats and next best actions.

Dependencies: `SWING-V01-143` through `SWING-V01-148`

Tests to add or update: None unless report generator is automated.

Acceptance criteria:

- Performance review packet exists.
- Paper decision is evidence-based.
- No strategy optimization is mixed into the qualification result.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

## Implementation-ready design refinement - added 2026-05-07

The mechanical readiness and historical performance backlog slices are now backed by implementation-ready solution designs:

- `docs/swing_machine_v0_1_mechanical_readiness_solution_design.md`
- `docs/swing_machine_v0_1_historical_performance_solution_design.md`

### SWING-V01-150 - Backlog/design consistency pass for mechanical and performance phases

Epic: Discovery and governance

Objective: Keep the detailed solution designs and backlog aligned before implementation begins.

Why it matters: The backlog items are now buildable, but implementation should reference the solution designs directly so scope does not drift.

Files/modules likely affected:

- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_mechanical_readiness_solution_design.md`
- `docs/swing_machine_v0_1_historical_performance_solution_design.md`

Implementation steps:

- Before starting each item from `SWING-V01-137` onward, check the corresponding design section.
- If implementation discovers a design gap, update the design and backlog before coding.
- Keep paper execution blocked until historical performance decision is complete or explicitly overridden.

Dependencies: none

Tests to add or update: None.

Acceptance criteria:

- Every new implementation item references the design section it implements.
- Design changes are recorded before code changes where materially relevant.

Safe to implement immediately: yes

Blocks later work: no

Status: complete

### SWING-V01-155 - Broad historical underperformance diagnostic report

Epic: QA and qualification

Objective: Diagnose why the broad historical performance packet failed profitability and benchmark-relative gates before making any strategy changes.

Why it matters: The next decision must be based on evidence, not guesswork or premature optimization.

Files/modules likely affected:

- `reports/swing_machine_v0_1/historical_performance_diagnostics_*.json`
- `reports/swing_machine_v0_1/historical_performance_diagnostics_*.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `docs/swing_machine_v0_1_backlog.md`

Implementation steps:

- Load attributed broad performance summary.
- Load broad lifecycle trade ledger.
- Load scanner material-decision attribution.
- Break down results by setup type, score bucket, exit reason, and symbol.
- Identify largest winners and losers.
- Record diagnostic findings and next questions.

Dependencies: `SWING-V01-149`, `SWING-V01-154`

Tests to add or update: Not required; this is an evidence-generation/reporting activity from existing validated artifacts.

Acceptance criteria:

- Diagnostic JSON and Markdown reports exist.
- TIGHT_BASE versus PULLBACK contribution is explicit.
- The report states whether further strategy changes are justified immediately or require design.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-156 - TIGHT_BASE mechanical audit

Epic: Signal feature snapshot

Objective: Audit the exact TIGHT_BASE trades and source feature snapshots to determine whether the setup logic is mechanically wrong, too permissive, or simply unprofitable in this slice.

Why it matters: TIGHT_BASE lost 5/5 trades in the broad slice. We need to know whether this is a bug, a config problem, or a weak pattern before changing the baseline.

Files/modules likely affected:

- `src/swingmachine/performance.py`
- `src/swingmachine/signals.py`
- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Extract TIGHT_BASE trade rows.
- Join each trade to setup-date feature rows.
- Record feature values, candidate scores, stops, exit reasons, and bars held.
- Compare observed values against config thresholds.
- Classify findings as bug, permissive gate, market sample issue, or inconclusive.

Dependencies: `SWING-V01-155`

Tests to add or update: Diagnostic fixture test if reusable code is added.

Acceptance criteria:

- TIGHT_BASE audit report exists.
- Each TIGHT_BASE trade has setup-date feature evidence.
- Any suspected mechanical issue is clearly separated from performance hypothesis.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-157 - Controlled baseline revision design

Epic: Baseline profile/config

Objective: Design controlled offline-only revision candidates based on diagnostic evidence without changing the frozen v0.1 baseline behavior prematurely.

Why it matters: The first baseline candidate failed profitability. Any revision must be explicit, reviewable, and compared against the frozen baseline.

Files/modules likely affected:

- `docs/swing_machine_v0_1_revision_design.md`
- `config/`
- `tests/`
- `reports/swing_machine_v0_1/`

Implementation steps:

- Define frozen baseline evidence.
- Define allowed revision hypotheses, such as PULLBACK-only or tighter TIGHT_BASE gates.
- Define non-goals and prohibited behavior changes.
- Define comparison gates and acceptance criteria.
- Add follow-on implementation tasks.

Dependencies: `SWING-V01-155`, `SWING-V01-156`

Tests to add or update: None for design; later revision tasks require parity and performance tests.

Acceptance criteria:

- Revision design exists before any strategy behavior is changed.
- Each proposed revision has a clear hypothesis and comparison gate.
- Paper trading remains blocked until a revised candidate qualifies.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-158 - Create explicit offline revision profiles

Epic: Baseline profile/config

Objective: Create explicit, reviewable offline-only revision profiles for controlled comparison against the frozen baseline.

Why it matters: Strategy behavior must change only through explicit profiles, not hidden code edits or ad hoc experiments.

Files/modules likely affected:

- `config/`
- `docs/swing_machine_v0_1_revision_design.md`
- `tests/`

Implementation steps:

- Identify current baseline config/profile file.
- Create a PULLBACK-only revision profile.
- Optionally create one tightened TIGHT_BASE profile only if thresholds are defensible from the audit.
- Add profile metadata explaining hypothesis and frozen-baseline comparison.
- Add config-loading tests if new profile aliases are introduced.

Dependencies: `SWING-V01-157`

Tests to add or update: Config/profile loading tests.

Acceptance criteria:

- Revision profiles are explicit and serializable.
- No `.env` strategy behavior is introduced.
- Frozen baseline remains unchanged.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-159 - Run PULLBACK-only broad offline comparison

Epic: Research/backtesting

Objective: Run the full offline scanner, lifecycle, attribution, performance, and qualification pipeline for the PULLBACK-only revision candidate.

Why it matters: The diagnostic evidence suggests PULLBACK may be the cleaner candidate, but it needs a controlled full comparison.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Run scanner replay with PULLBACK-only profile.
- Run lifecycle replay with PULLBACK-only profile.
- Build decision ledger if needed.
- Build attributed performance report.
- Compare against frozen baseline and SPY.

Dependencies: `SWING-V01-158`

Tests to add or update: Existing replay/performance tests should be sufficient unless profile loading changes.

Acceptance criteria:

- PULLBACK-only performance packet exists.
- Comparison against frozen baseline exists.
- Paper trading gate remains blocked unless a later qualification packet changes it.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-160 - Run tightened TIGHT_BASE broad offline comparison

Epic: Research/backtesting

Objective: If a defensible tightened TIGHT_BASE hypothesis exists, run it offline and compare against frozen baseline and PULLBACK-only.

Why it matters: TIGHT_BASE may be salvageable, but only if changes are explicit and not curve-fitted.

Files/modules likely affected:

- `config/`
- `reports/swing_machine_v0_1/`

Implementation steps:

- Select one tightened TIGHT_BASE hypothesis from audit evidence.
- Create explicit profile.
- Run scanner, lifecycle, attribution, and performance.
- Compare against frozen baseline and PULLBACK-only.

Dependencies: `SWING-V01-158`, `SWING-V01-159`

Tests to add or update: Config/profile tests if profile is added.

Acceptance criteria:

- Tightened TIGHT_BASE comparison exists or the task is explicitly blocked as too weakly justified.
- No ad hoc threshold search is performed.

Safe to implement immediately: no

Blocks later work: no

Status: blocked

### SWING-V01-161 - Revision qualification decision packet

Epic: QA and qualification

Objective: Produce a qualification decision packet for any revised candidate before paper trading is reconsidered.

Why it matters: A revised candidate must be governed through the same evidence gate as the frozen baseline.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Summarize frozen baseline versus revision evidence.
- Include benchmark and provider-comparison results.
- State paper-trading gate explicitly.
- Record blockers and next actions.

Dependencies: `SWING-V01-159`, optionally `SWING-V01-160`

Tests to add or update: Not required for report assembly unless reusable decision code is added.

Acceptance criteria:

- Decision packet exists.
- Paper-trading decision is explicit.
- Remaining blockers are clear.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-162 - Post-qualification research protocol

Epic: Research/backtesting

Objective: Define the research-governed path after the frozen baseline and first revision failed paper-trading qualification.

Why it matters: The project must not drift into ad hoc variant chasing. Further work needs a clear evidence protocol before new profiles are promoted.

Files/modules likely affected:

- `docs/swing_machine_v0_1_post_qualification_research_plan.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Summarize current qualification evidence.
- Define primary research questions.
- Define the immediate research tranche.
- Define promotion gates for any revised candidate.
- Keep paper/live execution blocked unless qualification evidence changes.

Dependencies: `SWING-V01-161`

Tests to add or update: None; documentation/governance item.

Acceptance criteria:

- A post-qualification research plan exists.
- The plan separates alpha research from execution readiness.
- Candidate promotion gates are explicit.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-163 - Broad Hugging Face data feasibility and manifest decision

Epic: Data and universe foundation

Objective: Determine whether the Hugging Face dataset can support a matching broad historical manifest for provider-level validation of the failed baseline and future revised candidates.

Why it matters: The current broad provider validation gap exists because no matching Hugging Face broad manifest has been proven available.

Files/modules likely affected:

- `data/qualification_sources/trading212/huggingface/`
- `data/manifests/` or the repository's existing manifest location
- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Inspect Hugging Face dataset coverage without moving or rewriting source data.
- Compare available symbol/date coverage to the Alpaca broad qualification manifest.
- Create a feasibility report.
- If coverage is sufficient and the repository has an established manifest builder, create a matching broad manifest.
- If coverage is insufficient, document the narrower validated window and block broad provider validation.

Dependencies: `SWING-V01-162`

Tests to add or update: Data-contract test only if a reusable manifest builder is added or changed.

Acceptance criteria:

- Feasibility report exists.
- Decision is explicit: create broad Hugging Face manifest, use shorter matched window, or block due to insufficient coverage.
- No source data is destructively changed.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-164 - Historical data quality and survivorship audit

Epic: Data and universe foundation

Objective: Audit the historical bars and benchmark data for gaps, duplicates, suspicious rows, and coverage mismatches before deeper alpha conclusions are trusted.

Why it matters: Historical performance evidence is only useful if the input data is good enough and aligned with the benchmark.

Files/modules likely affected:

- `src/swingmachine/data_quality.py`
- `reports/swing_machine_v0_1/`
- `tests/`

Implementation steps:

- Build a non-destructive audit over selected historical manifests.
- Count missing sessions per symbol.
- Detect duplicate symbol/date bars.
- Detect zero or negative OHLCV anomalies.
- Compare benchmark coverage to candidate symbol coverage.
- Emit JSON and Markdown reports.

Dependencies: `SWING-V01-163`

Tests to add or update: Unit tests for data-quality calculations using small fixtures.

Acceptance criteria:

- Data-quality report exists for the broad Alpaca manifest.
- Any provider-specific gaps are documented.
- The report is safe to run offline.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-165 - Feature outcome attribution dataset

Epic: Reporting and instrumentation

Objective: Create a reusable offline research table linking every material candidate to features, eligibility, score, rank, and forward/lifecycle outcomes.

Why it matters: We need to know whether the signal features separate better candidates from worse candidates before changing thresholds.

Files/modules likely affected:

- `src/swingmachine/performance.py`
- `src/swingmachine/replay.py`
- `reports/swing_machine_v0_1/`
- `tests/test_performance.py`

Implementation steps:

- Define the attribution row contract.
- Join material scanner decisions to lifecycle trade ledger where applicable.
- Add forward-return fields where historical bars are available.
- Preserve pattern type, score, rank, eligibility, and rejection reasons.
- Emit JSONL/CSV research table.

Dependencies: `SWING-V01-164`

Tests to add or update: Unit tests for accepted/traded and rejected/untraded attribution rows.

Acceptance criteria:

- Attribution table can be generated offline.
- Rows explain both accepted and rejected material candidates.
- The table is independent of paper/live runtime.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-166 - Accepted versus near-miss research report

Epic: Research/backtesting

Objective: Analyse whether accepted candidates outperform rejected near-miss candidates by score bucket, gate, pattern, and forward-return window.

Why it matters: If accepted candidates are not better than near misses, the scoring/gating model needs redesign rather than threshold tweaks.

Files/modules likely affected:

- `src/swingmachine/research.py`
- `reports/swing_machine_v0_1/`
- `tests/`

Implementation steps:

- Consume the feature outcome attribution dataset.
- Define near-miss candidate criteria.
- Calculate score-decile and gate-level outcome summaries.
- Emit JSON and Markdown reports.
- Record whether evidence supports a revised candidate.

Dependencies: `SWING-V01-165`

Tests to add or update: Unit tests for bucket calculations and near-miss classification.

Acceptance criteria:

- Accepted versus near-miss report exists.
- The report can reject weak gating/scoring hypotheses.
- No strategy profile changes are made by this task.

Safe to implement immediately: no

Blocks later work: yes

Status: complete

### SWING-V01-167 - Benchmark-relative feature design

Epic: Signal feature snapshot

Objective: Design benchmark-relative and market-regime features that could improve signal quality without relying on hidden behavior or ad hoc threshold search.

Why it matters: The current baseline loses badly to SPY, so future signal work must explicitly reason about benchmark-relative strength and market regime.

Files/modules likely affected:

- `docs/swing_machine_v0_1_solution_design.md`
- `docs/swing_machine_v0_1_post_qualification_research_plan.md`
- `src/swingmachine/signals.py`
- `tests/`

Implementation steps:

- Define candidate relative-strength features versus SPY.
- Define market-regime feature snapshots.
- Define config fields but do not enable new strategy behavior yet.
- Define parity requirements for research/runtime use.
- Add implementation backlog items for typed features and tests.

Dependencies: `SWING-V01-166`

Tests to add or update: Not required for design; later feature implementation must add unit and parity tests.

Acceptance criteria:

- Feature design is explicit and implementation-ready.
- Features are compatible with research/runtime parity.
- No profile promotion occurs in this task.

Safe to implement immediately: no

Blocks later work: no

Status: complete

### SWING-V01-168 - Benchmark-relative config contract

Epic: Baseline profile/config

Objective: Add explicit config/profile fields for benchmark-relative feature computation with behavior disabled by default.

Why it matters: New feature work must be explicit, serializable, and reviewable before it can influence strategy behavior.

Files/modules likely affected:

- `src/swingmachine/config.py`
- `config/`
- `tests/test_config.py`
- `docs/swing_machine_v0_1_benchmark_relative_feature_design.md`

Implementation steps:

- Add typed config for relative-strength windows, acceleration pairs, drawdown window, and rebound window.
- Default behavior influence to disabled.
- Update baseline config files explicitly.
- Add config-loading tests.

Dependencies: `SWING-V01-167`

Tests to add or update: Config loading and profile alias tests.

Acceptance criteria:

- Config is explicit and serializable.
- Existing baseline behavior remains unchanged.
- No `.env` strategy behavior is introduced.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-169 - Benchmark-relative feature formulas

Epic: Signal feature snapshot

Objective: Implement multi-window benchmark-relative feature formulas without changing candidate scoring or gating.

Why it matters: We need the research table to explain benchmark-relative opportunity quality before revising the strategy.

Files/modules likely affected:

- `src/swingmachine/features.py`
- `src/swingmachine/data_contracts.py`
- `tests/test_features.py`

Implementation steps:

- Compute `rs_vs_benchmark_20`, `rs_vs_benchmark_50`, `rs_vs_benchmark_100`, and preserve `rs_vs_benchmark_126`.
- Compute relative-strength acceleration fields.
- Compute symbol, benchmark, and relative drawdown/rebound fields.
- Add unit tests with deterministic expected values.

Dependencies: `SWING-V01-168`

Tests to add or update: Feature formula unit tests.

Acceptance criteria:

- New fields are computed when benchmark data is provided.
- New fields are null/NaN-safe when benchmark data is missing.
- Existing candidate scoring output is unchanged unless explicitly configured later.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-170 - Feature/outcome excess-return attribution

Epic: Reporting and instrumentation

Objective: Extend feature/outcome attribution with forward excess returns versus SPY and benchmark/regime bucket fields.

Why it matters: The next research decision should be based on benchmark-relative outcomes, not only raw forward returns.

Files/modules likely affected:

- `src/swingmachine/feature_outcomes.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/`

Implementation steps:

- Add benchmark forward returns for the same windows as candidate forward returns.
- Add forward excess return fields.
- Add benchmark/regime context fields where available.
- Update accepted-versus-near-miss reporting to include excess-return metrics.

Dependencies: `SWING-V01-169`

Tests to add or update: Attribution and near-miss report tests.

Acceptance criteria:

- Dataset includes raw and excess forward returns.
- Report can compare accepted and near-miss rows on excess returns.
- No profile behavior changes are made.

Safe to implement immediately: no

Blocks later work: yes

Status: complete

### SWING-V01-171 - Benchmark/regime outcome bucket report

Epic: Research/backtesting

Objective: Build a report that summarizes accepted, near-miss, and rejected outcomes by benchmark regime and relative-strength bucket.

Why it matters: We need to know whether the strategy works only in specific market backdrops or relative-strength regimes.

Files/modules likely affected:

- `src/swingmachine/feature_outcomes.py`
- `reports/swing_machine_v0_1/`
- `tests/test_feature_outcomes.py`

Implementation steps:

- Bucket rows by benchmark regime state.
- Bucket rows by relative-strength window values.
- Summarize raw and excess forward returns.
- Identify whether a controlled revision is justified.

Dependencies: `SWING-V01-170`

Tests to add or update: Bucket calculation tests.

Acceptance criteria:

- Regime/relative-strength bucket report exists.
- Findings explicitly support or reject a future revised candidate.
- Paper trading remains blocked.

Safe to implement immediately: no

Blocks later work: yes

Status: blocked

### SWING-V01-172 - Controlled benchmark-relative candidate selection packet

Epic: QA and qualification

Objective: Decide whether one benchmark-relative revision candidate is justified before creating or running a new profile.

Why it matters: This prevents threshold chasing and keeps profile revisions evidence-led.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`
- `config/`

Implementation steps:

- Summarize feature/outcome evidence.
- Select at most one revised candidate or explicitly reject revision.
- Define exact config changes and acceptance gates.
- State paper gate explicitly.

Dependencies: `SWING-V01-171`

Tests to add or update: Not required unless reusable decision code is added.

Acceptance criteria:

- Candidate-selection packet exists.
- Any selected revision is evidence-based and explicit.
- No strategy profile is changed before this packet exists.

Safe to implement immediately: no

Blocks later work: yes

Status: complete

### SWING-V01-173 - Research-only benchmark-relative prepared feature artifact

Epic: Data and universe foundation

Objective: Generate a research-only prepared feature artifact containing the new benchmark-relative fields without updating the baseline manifest.

Why it matters: Regime and benchmark-relative bucket reports require feature rows that contain the new formula outputs, but the frozen broad manifest should not be mutated casually.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `src/swingmachine/prepared_features.py`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Use the existing prepared feature builder with the updated formulas.
- Write output under reports, not over the manifest source file.
- Set `update_manifest: false`.
- Confirm the output contains the new benchmark-relative fields.

Dependencies: `SWING-V01-169`, `SWING-V01-170`

Tests to add or update: Not required if using existing prepared feature builder and prior formula tests.

Acceptance criteria:

- Research-only feature artifact exists.
- Baseline manifest is not updated.
- New benchmark-relative fields are present.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-174 - Propagate feature snapshots into attribution rows

Epic: Reporting and instrumentation

Objective: Extend feature/outcome attribution rows with selected candidate feature snapshot fields from a prepared feature artifact.

Why it matters: Bucket reports need to group outcomes by benchmark-relative features and regime context, not only score and rejection reason.

Files/modules likely affected:

- `src/swingmachine/feature_outcomes.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/`

Implementation steps:

- Accept an optional prepared feature artifact path.
- Join rows by symbol and signal session.
- Copy selected fields into attribution rows.
- Keep the join optional and research-only.

Dependencies: `SWING-V01-173`

Tests to add or update: Feature snapshot join tests.

Acceptance criteria:

- Attribution rows can include selected feature fields.
- Existing attribution behavior works without a feature artifact path.
- No strategy behavior changes.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-175 - Rebuild broad attribution with benchmark-relative feature snapshots

Epic: Research/backtesting

Objective: Rebuild the broad feature/outcome attribution dataset using the research-only prepared feature artifact.

Why it matters: This creates the input needed for benchmark/regime outcome bucket analysis.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Rebuild attribution rows with SPY excess returns.
- Include selected benchmark-relative feature snapshot fields.
- Emit JSON/CSV/Markdown outputs.

Dependencies: `SWING-V01-174`

Tests to add or update: Existing attribution tests should cover the code path.

Acceptance criteria:

- Broad attribution package includes feature snapshot fields.
- SPY excess returns remain present.
- No execution paths are triggered.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-176 - Benchmark/regime bucket report rerun

Epic: Research/backtesting

Objective: Complete the blocked benchmark/regime bucket report using the enriched attribution package.

Why it matters: This is the evidence needed before any controlled benchmark-relative revision candidate can be selected.

Files/modules likely affected:

- `src/swingmachine/feature_outcomes.py`
- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Bucket outcomes by benchmark-relative strength and regime fields.
- Summarize raw and SPY-excess forward returns.
- State whether a controlled revision is justified.

Dependencies: `SWING-V01-175`

Tests to add or update: Bucket report tests if new reusable code is added.

Acceptance criteria:

- Benchmark/regime bucket report exists.
- It explicitly supports or rejects a future revision.
- Paper trading remains blocked unless later qualification changes the gate.

Safe to implement immediately: no

Blocks later work: yes

Status: complete

### SWING-V01-177 - Accepted-only and traded-only bucket diagnostics

Epic: Research/backtesting

Objective: Extend bucket diagnostics so each bucket reports accepted-only and traded-only SPY-excess outcome metrics separately from all-row metrics.

Why it matters: The current bucket report can identify diagnostic buckets, but profile selection needs accepted/traded-specific evidence rather than all-row bucket averages.

Files/modules likely affected:

- `src/swingmachine/contracts.py`
- `src/swingmachine/feature_outcomes.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/`

Implementation steps:

- Extend bucket metrics with accepted-only forward and excess-return metrics.
- Extend bucket metrics with traded-only lifecycle outcome metrics where available.
- Update Markdown and JSON reports.
- Rerun the broad feature snapshot bucket report.

Dependencies: `SWING-V01-176`, `SWING-V01-172`

Tests to add or update: Bucket metrics tests for all-row, accepted-only, and traded-only calculations.

Acceptance criteria:

- Bucket report separates all-row, accepted-only, and traded-only evidence.
- The report can support or reject a single revision hypothesis.
- Paper trading remains blocked.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-178 - Controlled benchmark-relative hypothesis selection rerun

Epic: QA and qualification

Objective: Rerun the controlled candidate-selection packet after accepted-only and traded-only bucket diagnostics exist.

Why it matters: A revised profile should only be created if a single defensible benchmark-relative hypothesis survives stricter diagnostics.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`
- `config/`

Implementation steps:

- Review accepted-only and traded-only bucket evidence.
- Select at most one explicit revision hypothesis or reject revision.
- Define exact config changes if selected.
- Keep paper blocked unless a later qualification packet changes the gate.

Dependencies: `SWING-V01-177`

Tests to add or update: Not required unless reusable decision code is added.

Acceptance criteria:

- Hypothesis selection packet exists.
- Any selected profile change is explicitly justified.
- No ad hoc threshold search is performed.

Safe to implement immediately: no

Blocks later work: yes

Status: complete

### SWING-V01-179 - Feature bucket robustness and minimum-sample guardrails

Epic: Research/backtesting

Objective: Add robustness guardrails to feature bucket diagnostics so small or misleading buckets cannot be overinterpreted.

Why it matters: The current bucket report found potentially positive excess-return buckets, but profile selection needs minimum-sample and stability rules before any hypothesis is trusted.

Files/modules likely affected:

- `src/swingmachine/feature_outcomes.py`
- `src/swingmachine/contracts.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/`

Implementation steps:

- Add minimum accepted-row and traded-row sample fields to bucket reports.
- Flag buckets below minimum sample as exploratory.
- Add bucket warnings for thin evidence.
- Rerun the broad bucket report.

Dependencies: `SWING-V01-177`

Tests to add or update: Bucket guardrail tests.

Acceptance criteria:

- Bucket report distinguishes robust, exploratory, and insufficient buckets.
- Thin buckets cannot be used alone to select a profile.
- Paper trading remains blocked.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-180 - Accepted-candidate excess-return distribution report

Epic: Research/backtesting

Objective: Produce distribution-level diagnostics for accepted candidates across SPY-excess forward returns.

Why it matters: Averages hide tail risk and skew. We need median, percentiles, hit rate, and downside tail before interpreting accepted-signal quality.

Files/modules likely affected:

- `src/swingmachine/feature_outcomes.py`
- `reports/swing_machine_v0_1/`
- `tests/test_feature_outcomes.py`

Implementation steps:

- Summarize accepted rows by 1, 5, 10, and 20-session excess returns.
- Include median, p10, p25, p75, p90, min, max, and positive-rate.
- Compare accepted, near-miss, and all rejected distributions.
- Emit JSON and Markdown reports.

Dependencies: `SWING-V01-170`

Tests to add or update: Distribution metric tests.

Acceptance criteria:

- Distribution report exists.
- Report states whether accepted signals show a distributional edge.
- No profile behavior changes.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-181 - Traded-only lifecycle outcome decomposition

Epic: Trade lifecycle and exits

Objective: Decompose the nine broad lifecycle trades by setup type, bucket, exit reason, bars held, net return, and SPY-excess context.

Why it matters: Forward-return attribution and lifecycle PnL can diverge. We need to know whether losses come from signal selection, entry mechanics, exit rules, costs, or low sample size.

Files/modules likely affected:

- `src/swingmachine/performance.py`
- `src/swingmachine/feature_outcomes.py`
- `reports/swing_machine_v0_1/`
- `tests/`

Implementation steps:

- Join traded rows to feature snapshots and lifecycle trade ledger.
- Summarize trade outcomes by setup type, bucket, exit reason, and bars held.
- Separate raw PnL, net return, forward excess return, and actual lifecycle return.
- Emit JSON and Markdown reports.

Dependencies: `SWING-V01-175`

Tests to add or update: Trade decomposition tests if reusable code is added.

Acceptance criteria:

- Trade-only diagnostic packet exists.
- It identifies whether lifecycle losses are signal, entry, exit, cost, or sample related where evidence allows.
- No execution paths are triggered.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-182 - Exit-path diagnostic for winners, losers, and time exits

Epic: Trade lifecycle and exits

Objective: Diagnose whether current exit rules truncate winners, allow avoidable losers, or overuse time exits in the broad historical slice.

Why it matters: The strategy may have weak alpha, but it may also be losing edge through lifecycle mechanics. We need to separate those causes before revising entries.

Files/modules likely affected:

- `src/swingmachine/performance.py`
- `reports/swing_machine_v0_1/`
- `tests/`

Implementation steps:

- Analyze lifecycle trade ledger by exit reason.
- Compare bars held, net return, and forward returns after exit where available.
- Flag cases where post-exit continuation suggests premature exits.
- Flag cases where drawdown before exit suggests late exits.
- Emit JSON and Markdown report.

Dependencies: `SWING-V01-181`

Tests to add or update: Optional unit tests if reusable exit-diagnostic code is added.

Acceptance criteria:

- Exit-path diagnostic report exists.
- It clearly separates evidence from hypothesis.
- No exit rule changes are made in this task.

Safe to implement immediately: yes

Blocks later work: no

Status: complete

### SWING-V01-183 - Pattern-specific benchmark-relative diagnostics

Epic: Research/backtesting

Objective: Produce separate benchmark-relative diagnostics for `PULLBACK` and `TIGHT_BASE` accepted/traded rows.

Why it matters: PULLBACK and TIGHT_BASE behaved very differently in lifecycle results. Future decisions should not average away pattern-specific behavior.

Files/modules likely affected:

- `src/swingmachine/feature_outcomes.py`
- `reports/swing_machine_v0_1/`
- `tests/test_feature_outcomes.py`

Implementation steps:

- Split accepted and traded diagnostics by pattern type.
- Summarize SPY-excess forward returns and lifecycle returns.
- Compare PULLBACK-only, TIGHT_BASE-only, and all-pattern evidence.
- Record whether either pattern deserves further research.

Dependencies: `SWING-V01-177`, `SWING-V01-181`

Tests to add or update: Pattern grouping tests.

Acceptance criteria:

- Pattern-specific diagnostic report exists.
- PULLBACK and TIGHT_BASE conclusions are explicit.
- No pattern profile is changed.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-184 - Contract-window provider enrichment feasibility

Epic: Data and universe foundation

Objective: Determine whether the matched Alpaca/Hugging Face contract window can support enriched feature/outcome attribution and bucket diagnostics.

Why it matters: Broad Hugging Face coverage is insufficient, but the matched contract window can still test provider stability for candidate evidence.

Files/modules likely affected:

- `data/qualification_manifests/trading212/`
- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Identify matched Alpaca and Hugging Face contract manifests.
- Confirm both can generate prepared features with the benchmark-relative fields.
- Record any coverage or feature-start mismatch.
- Decide whether provider-matched attribution is safe to run.

Dependencies: `SWING-V01-169`

Tests to add or update: Not required unless code changes are needed.

Acceptance criteria:

- Provider enrichment feasibility report exists.
- Decision is explicit: proceed, narrow scope, or block.
- No source data is changed.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-185 - Provider-matched feature/outcome attribution packet

Epic: Research/runtime parity

Objective: Build Alpaca and Hugging Face feature/outcome attribution packets over the matched contract window if feasibility allows.

Why it matters: Provider-stable research signals are stronger than single-provider signals.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `src/swingmachine/feature_outcomes.py`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Generate research-only prepared features for both providers.
- Generate enriched attribution datasets for both providers.
- Preserve SPY-excess returns and feature snapshot fields.
- Emit provider-specific report folders.

Dependencies: `SWING-V01-184`

Tests to add or update: Existing attribution tests should cover code paths unless new helpers are added.

Acceptance criteria:

- Provider-matched attribution artifacts exist or task is blocked with evidence.
- Outputs are comparable on the same window.
- No paper/live paths are triggered.

Safe to implement immediately: yes - completed as bounded offline research with no manifest mutation

Blocks later work: yes

Status: complete

### SWING-V01-186 - Provider-matched accepted-versus-near-miss comparison

Epic: Research/runtime parity

Objective: Compare accepted-versus-near-miss SPY-excess outcomes across Alpaca and Hugging Face on the matched contract window.

Why it matters: A signal that changes materially by data provider should not be promoted.

Files/modules likely affected:

- `src/swingmachine/feature_outcomes.py`
- `reports/swing_machine_v0_1/`
- `tests/`

Implementation steps:

- Build accepted-versus-near-miss reports for both provider datasets.
- Compare accepted counts, near-miss counts, average excess returns, and hit rates.
- Flag provider instability.
- Emit JSON and Markdown comparison report.

Dependencies: `SWING-V01-185`

Tests to add or update: Provider comparison tests if reusable code is added.

Acceptance criteria:

- Provider comparison report exists.
- It states whether signal evidence is provider-stable.
- No profile selection occurs in this task.

Safe to implement immediately: yes - completed as offline report generation

Blocks later work: yes

Status: complete

### SWING-V01-187 - Feature null/missingness and stability audit

Epic: Data and universe foundation

Objective: Audit benchmark-relative feature fields for missingness, infinities, extreme values, and unstable distributions.

Why it matters: Research conclusions are unsafe if new features are sparse, unstable, or dominated by bad values.

Files/modules likely affected:

- `src/swingmachine/data_quality.py`
- `reports/swing_machine_v0_1/`
- `tests/`

Implementation steps:

- Audit selected feature snapshot fields across the research-only prepared feature artifact.
- Count nulls, infinities, min/max, percentiles, and per-symbol missingness.
- Emit JSON and Markdown reports.

Dependencies: `SWING-V01-173`

Tests to add or update: Feature audit tests if reusable code is added.

Acceptance criteria:

- Feature stability audit exists.
- Any problematic fields are clearly flagged before selection.
- No strategy behavior changes.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-188 - Cost/slippage stress by pattern and bucket

Epic: Risk and portfolio constraints

Objective: Stress historical lifecycle outcomes by additional costs across setup type and feature buckets.

Why it matters: Small observed edges can disappear under realistic costs. The current strategy must not be promoted on fragile net returns.

Files/modules likely affected:

- `src/swingmachine/performance.py`
- `reports/swing_machine_v0_1/`
- `tests/`

Implementation steps:

- Apply additional cost scenarios to traded lifecycle rows.
- Summarize impact by pattern type and feature bucket.
- Identify buckets whose evidence is cost-fragile.
- Emit JSON and Markdown reports.

Dependencies: `SWING-V01-181`

Tests to add or update: Cost stress tests if reusable code is added.

Acceptance criteria:

- Cost/slippage stress report exists.
- It identifies fragile and resilient groups.
- No risk model changes are made.

Safe to implement immediately: yes

Blocks later work: no

Status: complete

### SWING-V01-189 - Historical research artifact index

Epic: Reporting and instrumentation

Objective: Create an index of current historical research artifacts, decisions, gates, and latest report paths.

Why it matters: Overnight work creates many reports. The next-day review needs a single navigable index.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- List key reports by category.
- Record status, decision, and paper gate where available.
- Mark superseded reports.
- Emit JSON and Markdown artifact index.

Dependencies: None

Tests to add or update: Not required unless reusable indexing code is added.

Acceptance criteria:

- Artifact index exists.
- Latest evidence is easy to locate.
- Superseded reports are not mistaken for current decisions.

Safe to implement immediately: yes

Blocks later work: no

Status: complete

### SWING-V01-190 - Paper-readiness blocker refresh

Epic: QA and qualification

Objective: Refresh the explicit blocker list standing between current offline research and any future paper-trading recommendation.

Why it matters: The user needs a clear view of what remains blocked, what evidence has improved, and what must still be proven.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Read latest qualification, attribution, bucket, and selection reports.
- List current blockers and warnings.
- Distinguish mechanical blockers from profitability/edge blockers.
- Emit JSON and Markdown blocker refresh.

Dependencies: `SWING-V01-178` or latest selection packet

Tests to add or update: Not required.

Acceptance criteria:

- Blocker refresh exists.
- Paper gate is explicit.
- Mechanical readiness and edge readiness are separated.

Safe to implement immediately: yes

Blocks later work: no

Status: complete

### SWING-V01-191 - Overnight evidence summary packet

Epic: Reporting and instrumentation

Objective: Produce a concise summary packet of overnight discoveries, reports generated, tests run, blockers, and next recommended decisions.

Why it matters: The next morning should start from evidence, not from reconstructing state across logs.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Summarize completed overnight activities.
- Link generated artifacts.
- Summarize test/check outcomes.
- State decisions and remaining blockers.
- Recommend next-day decision points.

Dependencies: Complete after the overnight queue stops or reaches a natural checkpoint.

Tests to add or update: Not required.

Acceptance criteria:

- Overnight evidence summary exists.
- It can be read independently as a handoff.
- Paper/live gate status is explicit.

Safe to implement immediately: yes

Blocks later work: no

Status: complete

### SWING-V01-192 - Backlog grooming and next-day decision shortlist

Epic: Delivery governance

Objective: Reorder and groom the backlog after overnight evidence so the next day starts with decision-grade priorities.

Why it matters: The programme should avoid blindly ticking off tasks after the evidence changes.

Files/modules likely affected:

- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_overnight_queue.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Mark completed, blocked, and superseded tasks.
- Add follow-up tasks from overnight findings.
- Identify the top three decision points for the user.
- Preserve paper/live safety gates.

Dependencies: `SWING-V01-191`

Tests to add or update: Not required.

Acceptance criteria:

- Backlog status reflects current evidence.
- Next-day priorities are explicit.
- No hidden profile changes are introduced.

Safe to implement immediately: yes

Blocks later work: no

Status: complete

## Post-overnight decision shortlist - 2026-05-08

Decision state:

- Paper trading remains blocked.
- Serious full run remains historical-offline only.
- Mechanical readiness is materially improved for offline research, but profitability/edge is not proven.
- PULLBACK is the only currently interesting pattern hypothesis, but it is not paper-ready.
- TIGHT_BASE should be isolated or redesigned before any future baseline candidate uses it.

Top decision points:

1. Decide whether the next research lane is PULLBACK root-cause analysis or a broader fresh hypothesis design. Recommended: PULLBACK root-cause first because it is the only observed positive lifecycle pocket.
2. Decide whether to invest in broader Hugging Face data coverage now or accept Alpaca-only broad evidence as a research limitation. Recommended: defer data acquisition unless a new candidate shows edge on Alpaca first.
3. Decide whether TIGHT_BASE should be removed from the next candidate profile or redesigned behind an explicit research flag. Recommended: isolate it from any baseline candidate until it earns re-entry.

### SWING-V01-193 - PULLBACK traded-versus-accepted root-cause packet

Epic: Research/runtime parity

Objective: Explain why PULLBACK traded lifecycle is positive while accepted-only 20-session SPY-excess evidence is negative.

Why it matters: This is the main contradiction in the evidence. If fills/lifecycle selection are doing something useful, we need to understand it before designing a revised profile.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Split PULLBACK accepted rows into traded and untraded accepted populations.
- Compare score, feature snapshots, forward SPY-excess returns, entry/fill timing, and lifecycle PnL where available.
- Identify whether the positive result comes from order/fill selection, exit lifecycle, feature regime, or sample noise.
- Emit JSON and Markdown root-cause packet.

Dependencies: `SWING-V01-183`, `SWING-V01-188`

Tests to add or update: Not required unless reusable code is added.

Acceptance criteria:

- Packet explains traded versus accepted PULLBACK divergence.
- It states whether PULLBACK deserves deeper replay, redesign, or no further work.
- No profile change is made.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-194 - Warm-up and null-aware selection denominator audit

Epic: Data and universe foundation

Objective: Quantify how warm-up/null rows affect accepted-edge and bucket conclusions.

Why it matters: Feature null warnings are acceptable only if selection evidence is not being distorted by warm-up artifacts.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Recompute accepted and bucket diagnostics excluding rows with null required feature fields.
- Compare conclusions against current broad attribution reports.
- Flag any conclusion that changes after null-aware filtering.

Dependencies: `SWING-V01-187`

Tests to add or update: Not required unless reusable code is added.

Acceptance criteria:

- Null-aware diagnostic packet exists.
- It states whether warm-up/null rows materially change current conclusions.
- No profile change is made.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-195 - TIGHT_BASE isolation decision packet

Epic: Candidate generation

Objective: Produce a decision packet for isolating, disabling, or redesigning TIGHT_BASE in future baseline candidates.

Why it matters: TIGHT_BASE is the clearest drag in the current evidence and should not remain hidden inside any future baseline.

Files/modules likely affected:

- `docs/`
- `reports/swing_machine_v0_1/`

Implementation steps:

- Summarize TIGHT_BASE lifecycle, attribution, cost stress, and provider evidence.
- Define safe options: isolate, disable behind profile flag, or redesign with new gates.
- Recommend the safest option and acceptance criteria for any future re-entry.

Dependencies: `SWING-V01-183`, `SWING-V01-188`

Tests to add or update: None unless code changes are made.

Acceptance criteria:

- Decision packet exists.
- It prevents accidental TIGHT_BASE inclusion in a future baseline without explicit review.
- It does not modify strategy behavior by itself.

Safe to implement immediately: yes

Blocks later work: yes

Status: complete

### SWING-V01-196 - Revised candidate hypothesis design gate

Epic: Release/freeze process

Objective: Define the minimum evidence required before building any revised profile variant.

Why it matters: The programme should not jump from diagnostics into another ungoverned variant.

Files/modules likely affected:

- `docs/`
- `docs/swing_machine_v0_1_backlog.md`

Implementation steps:

- Define required inputs from PULLBACK root-cause, null-aware denominator audit, TIGHT_BASE decision, provider evidence, and cost stress.
- Define explicit go/no-go criteria for building a revised candidate profile.
- Add follow-up implementation items only after the gate is satisfied.

Dependencies: `SWING-V01-193`, `SWING-V01-194`, `SWING-V01-195`

Tests to add or update: None.

Acceptance criteria:

- Revised-profile build gate exists.
- Gate says what evidence is enough and what remains insufficient.
- No profile code is changed.

Safe to implement immediately: yes - completed after dependencies cleared

Blocks later work: yes

Status: complete

### SWING-V01-197 - Broad Hugging Face data acquisition decision

Epic: Data and universe foundation

Objective: Decide whether broader Hugging Face data should be acquired/prepared now or deferred.

Why it matters: Broad provider validation is blocked, but acquiring data before a viable Alpaca hypothesis may waste effort.

Files/modules likely affected:

- `docs/`
- `reports/swing_machine_v0_1/`

Implementation steps:

- Summarize current broad data gap and provider contract evidence.
- Estimate what broader Hugging Face data would need to cover.
- Recommend acquire now, defer, or replace with another provider.

Dependencies: `SWING-V01-163`, `SWING-V01-184`, `SWING-V01-186`

Tests to add or update: None.

Acceptance criteria:

- Decision packet exists.
- Data acquisition is not treated as a blocker for offline Alpaca hypothesis research unless explicitly decided.
- No data movement or external download occurs.

Safe to implement immediately: yes

Blocks later work: no

Status: complete

### SWING-V01-198 - Next baseline candidate selection packet

Epic: QA and qualification

Objective: Package evidence from root-cause, null-aware, TIGHT_BASE, provider, and cost diagnostics into a next-candidate recommendation.

Why it matters: A revised candidate should be selected from evidence, not built because one small bucket looked promising.

Files/modules likely affected:

- `reports/swing_machine_v0_1/`
- `docs/swing_machine_v0_1_implementation_log.md`

Implementation steps:

- Consume outputs from `SWING-V01-193` through `SWING-V01-197`.
- Recommend no-build, PULLBACK-only deeper replay, redesigned PULLBACK gates, or broader new hypothesis design.
- State whether serious historical qualification is still blocked or conditionally allowed.

Dependencies: `SWING-V01-196`

Tests to add or update: None unless code changes are made.

Acceptance criteria:

- Selection packet exists.
- Recommendation is explicit and evidence-backed.
- Paper gate remains blocked unless all blockers are explicitly cleared.

Safe to implement immediately: yes - completed after design gate

Blocks later work: yes

Status: complete
