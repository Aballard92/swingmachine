# Swing Machine v0.1 Implementation Log

Created: 2026-05-05
Repository root used: `/home/alexballard92/swingmachine`

Documentation location decision: this implementation log is created under `docs/`, matching the requested path and existing docs structure.

## Entries

### SWING-V01-001

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Created current-state review specific to the existing repository. |
| Files touched | `docs/swing_machine_current_state_review.md` |
| Tests added or updated | None. |
| Tests/checks run | Not applicable; docs-only. |
| Test result | Not applicable. |
| Assumptions made | `/home/alexballard92/swingmachine` is the effective repository root despite parent git state. |
| Blockers found | Branch creation is unsafe because git resolves to a larger parent repository with unrelated home-directory state. |
| Follow-up work created | Baseline manifest and qualification gates. |

### SWING-V01-002

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Defined `swing_machine_v0_1` as a governed baseline candidate, not a performance variant. |
| Files touched | `docs/swing_machine_v0_1_baseline_definition.md` |
| Tests added or updated | None. |
| Tests/checks run | Not applicable; docs-only. |
| Test result | Not applicable. |
| Assumptions made | Existing `RF_TPC_V2` strategy profile is the starting logic source, but not yet a qualified baseline. |
| Blockers found | None. |
| Follow-up work created | Explicit profile/manifest work and candidate/signal contracts. |

### SWING-V01-003

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Created implementation-ready solution design for architecture, contracts, parity, reports, and testing. |
| Files touched | `docs/swing_machine_v0_1_solution_design.md` |
| Tests added or updated | None. |
| Tests/checks run | Not applicable; docs-only. |
| Test result | Not applicable. |
| Assumptions made | New v0.1 components should reuse existing modules and add governance wrappers before changing runtime behaviour. |
| Blockers found | None. |
| Follow-up work created | Contract/reporting implementation tasks. |

### SWING-V01-004

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Created agile delivery plan with epics, gates, freeze process, qualification stages, and no-dead-time operating model. |
| Files touched | `docs/swing_machine_v0_1_delivery_plan.md` |
| Tests added or updated | None. |
| Tests/checks run | Not applicable; docs-only. |
| Test result | Not applicable. |
| Assumptions made | Focused validation is acceptable during incremental work; full suite remains a release/freeze gate because existing tests can be slow. |
| Blockers found | None. |
| Follow-up work created | Execute backlog top-down. |

### SWING-V01-005

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Created autonomous backlog and this implementation log. |
| Files touched | `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | None. |
| Tests/checks run | Not applicable; docs-only. |
| Test result | Not applicable. |
| Assumptions made | Backlog should include safe foundational tasks before runtime integration. |
| Blockers found | Selected-period qualification data is not defined yet. |
| Follow-up work created | SWING-V01-006 through SWING-V01-033. |

### SWING-V01-006

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added typed baseline manifest contract and focused tests. |
| Files touched | `src/swingmachine/baseline.py`, `tests/test_baseline.py` |
| Tests added or updated | `tests/test_baseline.py` |
| Tests/checks run | `ruff check src/swingmachine/baseline.py tests/test_baseline.py`; `pytest -q tests/test_baseline.py` |
| Test result | Ruff passed; pytest passed: `5 passed in 4.65s`. |
| Assumptions made | Serious full runs must default to prohibited until all required manifest checks are satisfied. |
| Blockers found | None. |
| Follow-up work created | Add manifest integration into replay/reporting once candidate/report contracts exist. |

### SWING-V01-008

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added focused test that `.env.example` advertises only allowed infrastructure keys and does not include prohibited strategy-behaviour fragments. |
| Files touched | `tests/test_baseline.py` |
| Tests added or updated | `test_env_example_advertises_only_allowed_infrastructure_keys` |
| Tests/checks run | `ruff check src/swingmachine/baseline.py tests/test_baseline.py`; `pytest -q tests/test_baseline.py` |
| Test result | Ruff passed; pytest passed: `5 passed in 4.65s`. |
| Assumptions made | `.env.example` should remain an operator template for infrastructure paths/mode only. |
| Blockers found | None. |
| Follow-up work created | Keep future strategy behaviour in explicit YAML/profile config and baseline manifest artifacts. |

### SWING-V01-009

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added first-class `SwingCandidate` contract with baseline metadata, eligibility gates, rejection reasons, quality score, and ranking result. |
| Files touched | `src/swingmachine/swing_contracts.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Candidate validation and serialization tests. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `15 passed in 15.41s`. |
| Assumptions made | Candidate contracts should be added as inert baseline-domain wrappers before dataframe adapters are introduced. |
| Blockers found | None. |
| Follow-up work created | SWING-V01-014 candidate generation adapter. |

### SWING-V01-010

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `SwingSignal` contract connecting a candidate to approved or rejected setup transition fields. |
| Files touched | `src/swingmachine/swing_contracts.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Signal validation and serialization tests. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `15 passed in 15.41s`. |
| Assumptions made | Approved signals must include setup, entry, stop, per-share risk, and score fields. |
| Blockers found | None. |
| Follow-up work created | Add adapters from existing setup snapshots to `SwingSignal`. |

### SWING-V01-015

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `SwingEligibilityGate` contract requiring failed gates to include a rejection reason and passed gates to omit one. |
| Files touched | `src/swingmachine/swing_contracts.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Eligibility gate positive/negative validation tests. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `15 passed in 15.41s`. |
| Assumptions made | Gate results should be reusable across candidates, signals, risk plans, and lifecycle decisions. |
| Blockers found | None. |
| Follow-up work created | Use gates in adapters and reports. |

### SWING-V01-016

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `SwingRejectionCategory` taxonomy and `SwingRejectionReason` contract. |
| Files touched | `src/swingmachine/swing_contracts.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Rejection reason usage tests through gate/candidate/signal validation. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `15 passed in 15.41s`. |
| Assumptions made | Initial taxonomy categories are data, universe, regime, trend, setup, event, risk, portfolio, runtime, and safety. |
| Blockers found | None. |
| Follow-up work created | Map existing string reject reasons into this taxonomy incrementally. |

### SWING-V01-017

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `SwingQualityScore` and `build_quality_score`, enforcing `quality_score_0_100 = score_percentile * 100`. |
| Files touched | `src/swingmachine/swing_contracts.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Quality score mapping and mismatch rejection tests. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `15 passed in 15.41s`. |
| Assumptions made | Review-facing quality score is percentile based and does not represent expected return. |
| Blockers found | None. |
| Follow-up work created | Candidate adapter should populate this from `candidate_score_pct`. |

### SWING-V01-018

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `SwingRankingResult` contract with rank, score, trend quality, 52-week-high distance, per-share risk, and symbol tie-break fields. |
| Files touched | `src/swingmachine/swing_contracts.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Ranking serialization test through candidate payload. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `15 passed in 15.41s`. |
| Assumptions made | Ranking artifact should expose tie-break inputs before implementing a dataframe adapter. |
| Blockers found | None. |
| Follow-up work created | Implement deterministic candidate ranking adapter against `score_candidates` output. |

### SWING-V01-012

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added baseline data contract version to `SwingBaselineManifest`, `SwingCandidate`, and `SwingUniverseMember` payloads. |
| Files touched | `src/swingmachine/baseline.py`, `src/swingmachine/swing_contracts.py`, `tests/test_baseline.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Manifest, candidate, and universe member serialization tests assert `prepared_market_and_historical_panel_v1`. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `17 passed in 16.60s`. |
| Assumptions made | Current baseline data contract version is the prepared market and historical panel v1 contract represented by existing validators. |
| Blockers found | None. |
| Follow-up work created | Propagate manifest/data contract version into replay/reporting package outputs. |

### SWING-V01-013

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `SwingUniverseMember` contract with reference metadata, baseline metadata, eligibility gates, and rejection reasons. |
| Files touched | `src/swingmachine/swing_contracts.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Universe member consistency and serialization tests. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `17 passed in 16.60s`. |
| Assumptions made | Universe member contract should capture current reference metadata without changing `signals.py` yet. |
| Blockers found | None. |
| Follow-up work created | SWING-V01-014 candidate generation contract adapter. |

### SWING-V01-019

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `SwingRiskPlan` contract with risk budgets, stop distance, quantity derivation, projected heat/new risk, constraints, and rejection reasons. |
| Files touched | `src/swingmachine/swing_contracts.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Risk plan validation and serialization tests. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `26 passed in 23.77s`. |
| Assumptions made | Risk plan contracts should initially wrap existing `EntryPlan` concepts without changing sizing behaviour. |
| Blockers found | None. |
| Follow-up work created | Add adapter from `EntryPlan` to `SwingRiskPlan`. |

### SWING-V01-020

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `SwingPortfolioConstraintResult` contract for risk/portfolio constraints with pass/fail evidence and mandatory reason for failures. |
| Files touched | `src/swingmachine/swing_contracts.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Constraint validation tests. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `26 passed in 23.77s`. |
| Assumptions made | Heat/sector/daily-risk/duplicate constraints can share one result model. |
| Blockers found | None. |
| Follow-up work created | Map portfolio manager outputs to constraint results. |

### SWING-V01-021

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `SwingOrderPlan` contract for safe reviewable order plans before runtime/paper/shadow submission. |
| Files touched | `src/swingmachine/swing_contracts.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Stop-limit order plan validation and serialization tests. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `26 passed in 23.77s`. |
| Assumptions made | Order plans are planning artifacts only and do not imply broker submission. |
| Blockers found | None. |
| Follow-up work created | Add report integration for order plans. |

### SWING-V01-022

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `SwingLifecycleTransition` contract for reportable state changes. |
| Files touched | `src/swingmachine/swing_contracts.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Lifecycle transition serialization test. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `26 passed in 23.77s`. |
| Assumptions made | Lifecycle reports should reference existing `SymbolLifecycleState` values. |
| Blockers found | None. |
| Follow-up work created | Add adapters from pending-entry/order-state decisions to lifecycle transitions. |

### SWING-V01-023

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `SwingExitDecision` contract with hold/exit validation and stop-tightening guard. |
| Files touched | `src/swingmachine/swing_contracts.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Exit decision validation tests. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `26 passed in 23.77s`. |
| Assumptions made | Exit decisions should not loosen stops in baseline reporting. |
| Blockers found | None. |
| Follow-up work created | Add adapter from `evaluate_exit_position` outputs to `SwingExitDecision`. |

### SWING-V01-026

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added focused unit/contract tests for the new baseline manifest, checklist, universe, candidate, signal, gate, rejection, quality, ranking, risk, order, lifecycle, and exit contracts. |
| Files touched | `tests/test_baseline.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | 28 focused tests now cover the new baseline foundation. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `28 passed in 4.05s`. |
| Assumptions made | Future contract/adapter additions should continue adding focused tests alongside implementation. |
| Blockers found | None. |
| Follow-up work created | Add adapter/reporting/CLI tests when integration begins. |

### SWING-V01-030

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `SwingBaselineQualificationChecklist` and `build_baseline_qualification_checklist` derived from the baseline manifest. |
| Files touched | `src/swingmachine/baseline.py`, `tests/test_baseline.py` |
| Tests added or updated | Checklist outstanding/blocked/all-satisfied tests. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py tests/test_baseline.py tests/test_swing_contracts.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py` |
| Test result | Ruff passed; pytest passed: `28 passed in 4.05s`. |
| Assumptions made | Checklist should be a pure object first, then serialized by replay/reporting in a later task. |
| Blockers found | None. |
| Follow-up work created | SWING-V01-025 reporting package and SWING-V01-029 manifest CLI/report integration. |

### SWING-V01-014

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `swing_candidates_from_scored_frame` adapter that converts existing `score_candidates` dataframe output into typed `SwingCandidate` artifacts with deterministic candidate ids, ranks, quality scores, gates, rejection reasons, baseline id, config hash, and data contract version. |
| Files touched | `src/swingmachine/swing_adapters.py`, `tests/test_swing_adapters.py` |
| Tests added or updated | Adapter tests for deterministic rank, score-threshold rejection, earnings-window rejection, and required-column failure. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py src/swingmachine/swing_adapters.py tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py` |
| Test result | Ruff passed; pytest passed: `32 passed in 74.37s`. |
| Assumptions made | The adapter should not alter existing scoring behaviour; it only wraps scored rows into baseline contracts. |
| Blockers found | None. |
| Follow-up work created | Add signal/risk/order adapters and baseline reporting package integration. |

### SWING-V01-028

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added focused dry-run safety test asserting the currently exposed runtime vocabulary is `PAPER`/`SHADOW` only and broker vocabulary is `PAPER` only, with no `LIVE` mode or live broker setting. |
| Files touched | `tests/test_baseline.py` |
| Tests added or updated | `test_current_baseline_runtime_vocabulary_is_paper_shadow_only` |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py src/swingmachine/swing_adapters.py tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py` |
| Test result | Ruff passed; pytest passed: `33 passed in 81.35s`. |
| Assumptions made | v0.1 baseline must remain local paper/shadow only until a separate live safety programme approves otherwise. |
| Blockers found | None. |
| Follow-up work created | Keep live broker/deployment work outside the baseline until freeze and safety review. |

### SWING-V01-007

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added explicit `swing_machine_v0_1` profile alias at `config/swing_machine_v0_1_profile.yaml`, plus typed alias loading/resolution helpers that enforce expected strategy id/version before building a baseline manifest. |
| Files touched | `config/swing_machine_v0_1_profile.yaml`, `src/swingmachine/baseline.py`, `tests/test_baseline.py` |
| Tests added or updated | Profile alias resolution test and manifest-from-alias identity/hash test. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py src/swingmachine/swing_adapters.py tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py` |
| Test result | Ruff passed; pytest passed: `35 passed in 99.50s`. |
| Assumptions made | The v0.1 baseline candidate should alias the existing `RF_TPC_V2` / `2.1.0` strategy profile rather than duplicate it into a separate frozen config before qualification. |
| Blockers found | None. |
| Follow-up work created | Baseline reporting/replay integration should use the alias path as the profile entry point. |

### SWING-V01-011

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `SwingFeatureSnapshotRecord`, `hash_feature_snapshot`, and `build_swing_feature_snapshot_record` to wrap the existing `FeatureSnapshot` with baseline id, data contract version, strategy id, config hash, stable hash, and consistency validation. |
| Files touched | `src/swingmachine/swing_contracts.py`, `tests/test_swing_contracts.py` |
| Tests added or updated | Feature snapshot wrapper serialization, symbol-mismatch rejection, and hash-mismatch rejection tests. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py src/swingmachine/swing_adapters.py tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py` |
| Test result | Ruff passed; pytest passed: `38 passed in 106.11s`. |
| Assumptions made | Baseline reports should reference immutable feature evidence by hash before runtime/replay integration is added. |
| Blockers found | None. |
| Follow-up work created | Add report package serialization and connect feature snapshot records to candidate/replay outputs. |

### SWING-V01-025

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added baseline reporting package scaffolding in `baseline_reporting.py`, including package summary counts, manifest/checklist/artifact consistency validation, package builder, and JSON writer. |
| Files touched | `src/swingmachine/baseline_reporting.py`, `tests/test_baseline_reporting.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Report package summary, artifact config-hash mismatch, summary mismatch, and JSON writer tests. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py src/swingmachine/swing_adapters.py src/swingmachine/baseline_reporting.py tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py` |
| Test result | Ruff passed; pytest passed: `42 passed in 121.47s`. |
| Assumptions made | The first reporting package should be a pure contract/serialization package before CLI/replay integration. |
| Blockers found | None. |
| Follow-up work created | SWING-V01-029 should wire manifest/report package writing into safe replay/report commands. |

### SWING-V01-029

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added alias-driven baseline report package integration functions: `build_baseline_report_package_from_profile_alias` and `write_baseline_report_package_from_profile_alias`. These produce/write a baseline report package from `config/swing_machine_v0_1_profile.yaml` without invoking runtime, replay, broker, or database side effects. |
| Files touched | `src/swingmachine/baseline_reporting.py`, `tests/test_baseline_reporting.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Tests for alias-driven package identity/checklist state and JSON writer output. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py src/swingmachine/swing_adapters.py src/swingmachine/baseline_reporting.py tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py` |
| Test result | Ruff passed; pytest passed: `44 passed in 49.10s`. |
| Assumptions made | The first integration should be a pure profile-alias-to-report-package writer before adding a runtime CLI/replay hook. |
| Blockers found | None. |
| Follow-up work created | A future CLI/replay task can call this writer to emit `baseline_report_package.json` beside replay/review artifacts. |

### SWING-V01-024

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `baseline_parity.py` with `SwingBaselineParityReport`, `SwingBaselineParityDifference`, and `compare_baseline_report_packages`. The comparator compares research and runtime-compatible baseline report packages by manifest identity, summary counts, and artifact payloads keyed by stable artifact IDs, returning field-level differences for mismatches and missing artifacts. |
| Files touched | `src/swingmachine/baseline_parity.py`, `tests/test_baseline_parity.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Parity pass test for equivalent packages with different package metadata, candidate field-difference test, missing-candidate test, and manifest config-hash mismatch test. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py src/swingmachine/swing_adapters.py src/swingmachine/baseline_reporting.py src/swingmachine/baseline_parity.py tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py tests/test_baseline_parity.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py tests/test_baseline_parity.py` |
| Test result | Ruff passed; pytest passed: `48 passed in 113.92s`. |
| Assumptions made | Research/runtime parity can be represented first as artifact-package comparison before wiring direct replay/runtime execution paths. |
| Blockers found | None. |
| Follow-up work created | Future replay/runtime hooks should emit comparable baseline report packages and run this comparator. |

### SWING-V01-027

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added smoke coverage proving a baseline report package can be generated from the v0.1 profile alias and written as a JSON artifact with manifest, qualification checklist, summary, serious-run prohibition, and no `LIVE` vocabulary. |
| Files touched | `tests/test_baseline_reporting.py` |
| Tests added or updated | `test_baseline_report_package_smoke_writes_no_live_side_effect_artifact` |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py src/swingmachine/swing_adapters.py src/swingmachine/baseline_reporting.py src/swingmachine/baseline_parity.py tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py tests/test_baseline_parity.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py tests/test_baseline_parity.py` |
| Test result | Ruff passed; pytest passed: `49 passed in 123.27s`. |
| Assumptions made | Smoke coverage should remain artifact-generation only until replay/runtime hooks are explicitly added. |
| Blockers found | None. |
| Follow-up work created | Future CLI/replay smoke should write this package beside replay artifacts. |

### SWING-V01-033

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Recorded `SWING-ADR-004` in the delivery plan: v0.1 defers explicit correlation enforcement while keeping position concentration, sector concentration, heat, daily new risk, and duplicate-symbol controls as enforced baseline constraints. |
| Files touched | `docs/swing_machine_v0_1_delivery_plan.md` |
| Tests added or updated | No code test; decision documented. |
| Tests/checks run | Focused baseline/report/parity validation run after the doc/test change. |
| Test result | Ruff passed; pytest passed: `49 passed in 123.27s`. |
| Assumptions made | It is safer to document correlation as a visible v0.1 gap than to add an under-specified correlation model. |
| Blockers found | None. |
| Follow-up work created | Later baseline versions may add an explicit correlation/factor proxy through config, reports, and tests. |

### SERIOUS-FULL-RUN-READINESS-2026-05-05

| Field | Value |
| --- | --- |
| Status | blocked |
| What changed | Added a formal serious full run readiness decision. The decision is that integration and qualification must come before any serious full run. |
| Files touched | `docs/swing_machine_v0_1_serious_full_run_readiness_decision.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | None; decision documentation only. |
| Tests/checks run | Not run; docs-only decision. |
| Test result | Not applicable. |
| Assumptions made | Serious full run permission should be evidence-driven through manifest/checklist completion, not manually toggled. |
| Blockers found | Missing signal/risk/order/lifecycle/exit adapters, replay/runtime package hook, selected-period qualification data, end-to-end parity evidence, and freeze review. |
| Follow-up work created | Continue with signal adapter, risk/order adapter, lifecycle/exit adapter, safe replay/report hook, and selected-period qualification definition. |

### SERIOUS-RUN-INTEGRATION-BACKLOG-2026-05-05

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added concrete serious-run integration path items `SWING-V01-034` through `SWING-V01-040` to the backlog and added the serious full run integration sequence to the solution design. |
| Files touched | `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_solution_design.md` |
| Tests added or updated | None; planning/control update. |
| Tests/checks run | Included in focused validation after `SWING-V01-034` implementation. |
| Test result | Ruff passed; pytest passed: `51 passed in 139.59s`. |
| Assumptions made | The integration path should be tracked before continuing implementation, but no broad redesign is required. |
| Blockers found | Serious full run remains blocked until integration, parity evidence, selected-period data, and freeze readiness are complete. |
| Follow-up work created | SWING-V01-035 through SWING-V01-040. |

### SWING-V01-034

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `swing_signal_from_setup_snapshot` adapter to convert an existing `SetupSnapshot` into an approved or rejected `SwingSignal` with setup prices, stop/risk fields, candidate id, quality score, config hash, gate evidence, and rejection reasons. |
| Files touched | `src/swingmachine/swing_adapters.py`, `tests/test_swing_adapters.py` |
| Tests added or updated | Approved signal adapter test and rejected signal adapter test. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py src/swingmachine/swing_adapters.py src/swingmachine/baseline_reporting.py src/swingmachine/baseline_parity.py tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py tests/test_baseline_parity.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py tests/test_baseline_parity.py` |
| Test result | Ruff passed; pytest passed: `51 passed in 139.59s`. |
| Assumptions made | The adapter should wrap existing setup output without changing setup detection or runtime execution. |
| Blockers found | None. |
| Follow-up work created | SWING-V01-035 risk/order adapter integration. |

### SWING-V01-035

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `swing_risk_plan_from_entry_plan` and `swing_order_plan_from_entry_plan` adapters to convert existing `EntryPlan`/`OrderIntent` artifacts into `SwingRiskPlan` and `SwingOrderPlan` baseline artifacts. The adapters include sizing evidence, projected portfolio constraints, order prices, dedupe key, and rejection reasons. |
| Files touched | `src/swingmachine/swing_adapters.py`, `tests/test_swing_adapters.py` |
| Tests added or updated | Approved risk/order adapter test and rejected risk/order adapter test with portfolio heat rejection evidence. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py src/swingmachine/swing_adapters.py src/swingmachine/baseline_reporting.py src/swingmachine/baseline_parity.py tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py tests/test_baseline_parity.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py tests/test_baseline_parity.py` |
| Test result | Ruff passed; pytest passed: `53 passed in 123.44s`. |
| Assumptions made | Risk/order adapters should wrap existing entry planning output without changing sizing logic, order-intent generation, broker state, or runtime submission. |
| Blockers found | None. |
| Follow-up work created | SWING-V01-036 lifecycle/exit adapter integration. |

### SWING-V01-036

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added lifecycle/exit adapter functions: `swing_lifecycle_transition_from_states` and `swing_exit_decision_from_values`. These create `SwingLifecycleTransition` and `SwingExitDecision` artifacts from explicit lifecycle/exit decision values using existing enums and config identity. |
| Files touched | `src/swingmachine/swing_adapters.py`, `tests/test_swing_adapters.py` |
| Tests added or updated | Lifecycle transition adapter test and hold/exit decision adapter test. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py src/swingmachine/swing_contracts.py src/swingmachine/swing_adapters.py src/swingmachine/baseline_reporting.py src/swingmachine/baseline_parity.py tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py tests/test_baseline_parity.py`; `pytest -q tests/test_baseline.py tests/test_swing_contracts.py tests/test_swing_adapters.py tests/test_baseline_reporting.py tests/test_baseline_parity.py` |
| Test result | Ruff passed; pytest passed: `55 passed in 59.98s`. |
| Assumptions made | The first lifecycle/exit integration should be explicit-value adapter builders before wiring into runtime internals. |
| Blockers found | None. |
| Follow-up work created | SWING-V01-037 safe replay/report package hook. |

### SWING-V01-037

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added a safe replay/report package hook. Historical manifest replay now includes `baseline_report_package.json` in deterministic artifact paths, writes a baseline report package beside replay artifacts, and carries the active strategy config path through the runtime CLI replay command. The emitted package keeps serious full run permission false and records manifest/checklist evidence from the replay result. |
| Files touched | `src/swingmachine/replay.py`, `src/swingmachine/runtime.py`, `tests/test_replay_workflow.py`, `tests/test_runtime.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Replay workflow artifact coverage and runtime CLI historical replay coverage now assert `baseline_report_package.json` is produced. |
| Tests/checks run | `ruff check src/swingmachine/replay.py src/swingmachine/runtime.py src/swingmachine/baseline.py src/swingmachine/baseline_reporting.py tests/test_replay_workflow.py tests/test_runtime.py`; `pytest -q tests/test_replay_workflow.py::test_historical_manifest_replay_writes_deterministic_material_artifacts tests/test_runtime.py::test_runtime_cli_runs_historical_replay_workflow tests/test_baseline_reporting.py` |
| Test result | Ruff passed; pytest passed: `9 passed in 246.11s`. |
| Assumptions made | The first replay integration should remain artifact-only and should not change broker, order submission, scheduling, database mutation, or production runtime behavior. |
| Blockers found | None for this item. Serious full run remains blocked until package parity evidence, selected-period data definition, and freeze readiness gates are complete. |
| Follow-up work created | SWING-V01-038 research-vs-runtime package parity evidence and SWING-V01-039 selected-period qualification data definition. |

### SWING-V01-038

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added file-based research/runtime baseline package parity evidence. `baseline_parity.py` can now load `baseline_report_package.json` files, compare them through the typed parity comparator, and write a JSON parity report artifact. |
| Files touched | `src/swingmachine/baseline_parity.py`, `tests/test_baseline_parity.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Added coverage proving two written research/runtime package JSON files compare cleanly despite different package metadata, and that the parity report can be written as JSON. |
| Tests/checks run | `ruff check src/swingmachine/baseline_parity.py tests/test_baseline_parity.py`; `pytest -q tests/test_baseline_parity.py` |
| Test result | Ruff passed; pytest passed: `5 passed in 18.96s`. |
| Assumptions made | File-based comparison is the safest first parity evidence because it avoids launching runtime jobs or full qualification backtests. |
| Blockers found | None for this item. Serious full run remains blocked until selected-period qualification data and freeze readiness gates are complete. |
| Follow-up work created | SWING-V01-039 selected-period qualification data definition and SWING-V01-040 serious full run freeze readiness gate. |

### SWING-V01-039

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added an explicit selected-period qualification plan and typed contract. `config/swing_machine_v0_1_selected_periods.yaml` defines three bounded replay/dry-run-only qualification windows, required artifacts, data requirements, acceptance evidence, and safety controls. `baseline.py` now includes typed selected-period plan/period models, loaders, and profile-alias resolution. |
| Files touched | `config/swing_machine_v0_1_selected_periods.yaml`, `src/swingmachine/baseline.py`, `tests/test_baseline.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Added tests for selected-period plan loading, safe policy fields, artifact requirements, period date ordering, profile alias resolution, and duplicate period-id rejection. |
| Tests/checks run | `ruff check src/swingmachine/baseline.py tests/test_baseline.py`; `pytest -q tests/test_baseline.py` |
| Test result | Ruff passed; pytest passed: `12 passed in 13.44s`. |
| Assumptions made | Selected-period evidence should be planned as bounded dry-run/replay windows first; data gaps should block qualification rather than be silently filled. |
| Blockers found | None for this item. Serious full run remains blocked until freeze readiness can evaluate manifest, parity, selected-period evidence, and operator approval together. |
| Follow-up work created | SWING-V01-040 serious full run freeze readiness gate. |

### SWING-V01-040

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added a formal serious full run freeze-readiness gate in `baseline_readiness.py`. The gate returns a typed decision with explicit blockers and evidence, and it can write a JSON readiness artifact. It blocks the current baseline unless manifest checks are all satisfied, a selected-period plan is provided and compatible, parity evidence exists and passes, and operator approval is recorded. |
| Files touched | `src/swingmachine/baseline_readiness.py`, `tests/test_baseline_readiness.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Added tests proving the current baseline blocks serious full run, a synthetic fully satisfied baseline allows only with all gates met, and failed parity evidence blocks with explicit evidence. |
| Tests/checks run | `ruff check src/swingmachine/baseline_readiness.py tests/test_baseline_readiness.py`; `pytest -q tests/test_baseline_readiness.py` |
| Test result | Ruff passed; pytest passed: `3 passed in 9.86s`. |
| Assumptions made | Operator approval remains a separate freeze gate even if all automated checks pass; this prevents accidental serious full run permission from code-only evidence. |
| Blockers found | Current baseline still blocks serious full run because the active manifest does not yet satisfy every mandatory qualification check and operator freeze approval has not been recorded. |
| Follow-up work created | Continue filling package artifacts with real candidate/signal/risk/order/lifecycle evidence and run selected-period dry-run qualification only after the data inputs are explicitly prepared. |

### SERIOUS-RUN-PACKAGE-INTEGRATION-BACKLOG-2026-05-05

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added follow-on integration backlog items `SWING-V01-041` through `SWING-V01-044` and documented the continuation sequence in the solution design. |
| Files touched | `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_solution_design.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | None; planning/control update. |
| Tests/checks run | Not run; docs-only update. |
| Test result | Not applicable. |
| Assumptions made | The next safe implementation priority is richer replay package evidence, not freeze execution or selected-period qualification execution. |
| Blockers found | Selected-period dry-run execution remains blocked until data/preflight gates are satisfied. |
| Follow-up work created | SWING-V01-041 through SWING-V01-044. |

### SWING-V01-041

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Replay results now carry baseline material artifacts and the replay package writer includes them in `baseline_report_package.json`. Successful replay builds candidate artifacts from the scored signal-session frame, signal artifacts from setup snapshots, in-memory dry-run entry plans through the portfolio manager, and risk/order plan artifacts through the existing adapters. `contracts.py` stores these replay artifacts generically to avoid a circular dependency with `swing_contracts.py`; the report package validates the concrete typed artifacts when written. |
| Files touched | `src/swingmachine/contracts.py`, `src/swingmachine/replay.py`, `tests/test_replay_workflow.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Replay artifact test now asserts the emitted baseline package includes candidate, signal, risk-plan, and order-plan counts and material symbols. |
| Tests/checks run | `ruff check src/swingmachine/contracts.py src/swingmachine/replay.py tests/test_replay_workflow.py`; `pytest -q tests/test_replay_workflow.py::test_historical_manifest_replay_writes_deterministic_material_artifacts` |
| Test result | Ruff passed; pytest passed: `1 passed in 200.52s`. |
| Assumptions made | Rebuilding entry plans in-memory for the report package is acceptable because it mirrors the safe replay inputs and does not submit broker orders or mutate production state. |
| Blockers found | None for this item. Serious full run remains blocked because freeze execution, operator approval, selected-period preflight, and selected-period qualification evidence are not complete. |
| Follow-up work created | SWING-V01-042 freeze-readiness artifact from replay evidence and SWING-V01-043 selected-period preflight validator. |

### SWING-V01-042

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Replay artifact output now includes `freeze_readiness.json`. The replay writer can load an explicit selected-period plan, evaluates the manifest through the freeze-readiness gate, and writes a blocked readiness decision because replay does not include parity reports or operator approval. Runtime CLI replay also produces the artifact. |
| Files touched | `src/swingmachine/replay.py`, `tests/test_replay_workflow.py`, `tests/test_runtime.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Replay artifact coverage now asserts blocker codes in `freeze_readiness.json`; runtime CLI replay coverage asserts the readiness artifact is produced. |
| Tests/checks run | `ruff check src/swingmachine/replay.py tests/test_replay_workflow.py tests/test_runtime.py`; `pytest -q tests/test_replay_workflow.py::test_historical_manifest_replay_writes_deterministic_material_artifacts tests/test_runtime.py::test_runtime_cli_runs_historical_replay_workflow` |
| Test result | Ruff passed; pytest passed: `2 passed in 326.48s`. |
| Assumptions made | Replay should not fabricate parity evidence or operator approval; it should emit explicit blockers instead. |
| Blockers found | Serious full run remains blocked by incomplete manifest checks, missing parity evidence inside replay, and missing operator approval. |
| Follow-up work created | SWING-V01-043 selected-period qualification preflight validator. |

### SWING-V01-043

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added a selected-period qualification preflight validator. `baseline_readiness.py` now produces typed preflight pass/block output, validates profile alias and strategy config resolution, checks required artifact declarations, and requires explicit data manifest paths for every selected period before replay execution. Updated the selected-period plan to include the new `freeze_readiness.json` artifact. |
| Files touched | `src/swingmachine/baseline_readiness.py`, `config/swing_machine_v0_1_selected_periods.yaml`, `tests/test_baseline_readiness.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Added tests proving preflight blocks without selected-period data manifests and passes when explicit placeholder manifest files are declared for every period. |
| Tests/checks run | `ruff check src/swingmachine/baseline_readiness.py tests/test_baseline_readiness.py`; `pytest -q tests/test_baseline_readiness.py` |
| Test result | Ruff passed; pytest passed: `5 passed in 12.13s`. |
| Assumptions made | Selected-period replay should remain blocked until every period has an explicit data manifest path; preflight should not load broker state or execute replay. |
| Blockers found | SWING-V01-044 remains blocked because real selected-period data manifest paths have not been provided or validated. |
| Follow-up work created | Provide or generate selected-period data manifests, then run preflight before any selected-period dry-run qualification. |

### SWING-V01-045

| Field | Value |
| --- | --- |
| Status | in progress |
| What changed | Started selected-period preflight CLI command implementation. |
| Files touched | `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Pending. |
| Tests/checks run | Pending. |
| Test result | Pending. |
| Assumptions made | CLI preflight should be safe to run repeatedly because it only reads plan/manifest paths and writes one JSON artifact. |
| Blockers found | None yet. |
| Follow-up work created | Complete CLI implementation and tests. |

### SWING-V01-045

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added the `preflight-selected-period-qualification` runtime CLI command. It accepts `--plan`, `--output`, and repeated `--data-manifest PERIOD_ID=MANIFEST_PATH` options, writes a typed selected-period preflight JSON artifact, exits with code 1 when blockers are present, and exits 0 only when all required data manifests are declared and exist. |
| Files touched | `src/swingmachine/runtime.py`, `tests/test_runtime.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Added CLI tests for blocked preflight output with missing manifests and passing preflight output with explicit manifest paths. |
| Tests/checks run | `ruff check src/swingmachine/runtime.py tests/test_runtime.py`; `pytest -q tests/test_runtime.py::test_runtime_cli_preflights_selected_period_qualification_blocked tests/test_runtime.py::test_runtime_cli_preflights_selected_period_qualification_with_manifests` |
| Test result | Ruff passed; pytest passed: `2 passed in 32.37s`. |
| Assumptions made | Preflight CLI must remain read/write-artifact only and must not run replay, broker, runtime cycle, or database writes. |
| Blockers found | Selected-period dry-run qualification remains blocked until real selected-period data manifest paths are provided and the preflight CLI passes against them. |
| Follow-up work created | Locate or generate real selected-period historical panel manifests, then run this preflight command before any selected-period replay. |

### SWING-V01-046

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Produced selected-period preflight blocker evidence at `reports/swing_machine_v0_1/selected_period_preflight.json`. Repository inventory found only the tiny fixture manifest at `tests/fixtures/historical_panel/manifest.yaml`; no real selected-period panel manifests are present. |
| Files touched | `reports/swing_machine_v0_1/selected_period_preflight.json`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | None; evidence artifact only. |
| Tests/checks run | `find . -path './.venv' -prune -o -name 'manifest.yaml' -print`; `python -c 'from swingmachine.runtime import main; main()' preflight-selected-period-qualification --plan config/swing_machine_v0_1_selected_periods.yaml --output reports/swing_machine_v0_1/selected_period_preflight.json` |
| Test result | Manifest inventory found only `tests/fixtures/historical_panel/manifest.yaml`. Initial console-script attempt failed because `./.venv/bin/swingmachine` is not installed in this venv. Direct Typer invocation through Python completed with expected `preflight_exit_code=1` and `artifact_status=written`. |
| Assumptions made | The tiny fixture manifest is not valid evidence for selected-period qualification because the plan requires three selected periods with explicit period-specific data manifests. |
| Blockers found | SWING-V01-044 remains blocked: real manifests for `smoke_recent_5_sessions`, `recent_medium_replay_window`, and `historical_contract_stability_window` are not present/provided. |
| Follow-up work created | Generate or provide real selected-period historical panel manifests, rerun preflight with three `--data-manifest PERIOD_ID=PATH` arguments, and only then consider selected-period dry-run replay. |

### SWING-V01-047

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added a safe historical panel manifest builder. `data_contracts.py` can now build/write a manifest from explicit prepared OHLCV, symbol reference, corporate action, earnings, and optional feature files with inferred formats, row counts, SHA-256 hashes, session bounds, symbol count, and session count. `runtime.py` exposes this through `build-historical-panel-manifest`. |
| Files touched | `src/swingmachine/data_contracts.py`, `src/swingmachine/runtime.py`, `tests/test_runtime.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Added a runtime CLI test that builds a manifest from the fixture CSV inputs, loads it, and validates it through the existing historical panel manifest validator. |
| Tests/checks run | `ruff check src/swingmachine/data_contracts.py src/swingmachine/runtime.py tests/test_runtime.py`; `pytest -q tests/test_runtime.py::test_runtime_cli_builds_historical_panel_manifest` |
| Test result | Ruff passed; pytest passed: `1 passed in 71.88s`. |
| Assumptions made | Manifest generation should only package explicit prepared files; it must not fetch market data, infer missing rows, run replay, submit orders, or write runtime databases. |
| Blockers found | Real selected-period source files are still not present in the repo, so this builder enables future manifest creation but does not by itself unblock SWING-V01-044. |
| Follow-up work created | Use `build-historical-panel-manifest` once real selected-period prepared files exist, then rerun selected-period preflight with the generated manifests. |

### SWING-V01-048

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `docs/swing_machine_v0_1_selected_period_runbook.md` with the safe selected-period sequence: prepare explicit data files, build manifests, run preflight, and only then consider selected-period dry-run replay. |
| Files touched | `docs/swing_machine_v0_1_selected_period_runbook.md`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | None; docs-only. |
| Tests/checks run | Not run; docs-only. |
| Test result | Not applicable. |
| Assumptions made | The venv may not have the `swingmachine` console script installed, so the runbook uses the direct Python Typer invocation that was proven during preflight evidence capture. |
| Blockers found | Selected-period replay remains blocked until real prepared data files and manifests exist. |
| Follow-up work created | Prepare or provide selected-period files under a chosen data location, build manifests, then rerun preflight. |

### SWING-V01-049

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added a grouped qualification mini-plan and reorganized the remaining work into data readiness, preflight, dry-run replay evidence, parity/evidence consolidation, and freeze/operator decision workstreams. |
| Files touched | `docs/swing_machine_v0_1_qualification_mini_plan.md`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | None; docs/governance only. |
| Tests/checks run | Not run; docs-only update. |
| Test result | Not applicable. |
| Assumptions made | The remaining blocker is qualification evidence, not more core scaffolding. The tiny fixture manifest must not be treated as selected-period qualification evidence. |
| Blockers found | Workstreams A-E remain blocked until real selected-period prepared files/manifests are available and preflight passes. |
| Follow-up work created | SWING-V01-050 through SWING-V01-054. |

### SWING-V01-055

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added Workstream A source-data input contract and preflight. `qualification_inputs.py` defines the selected-period data input plan, missing-file/period blockers, JSON writer, and preflight evaluator. `runtime.py` now exposes `preflight-selected-period-data-inputs`. Added an example input plan at `config/swing_machine_v0_1_selected_period_data_inputs.example.yaml` and wrote current blocker evidence to `reports/swing_machine_v0_1/selected_period_data_input_preflight.json`. |
| Files touched | `src/swingmachine/qualification_inputs.py`, `src/swingmachine/runtime.py`, `config/swing_machine_v0_1_selected_period_data_inputs.example.yaml`, `tests/test_qualification_inputs.py`, `tests/test_runtime.py`, `reports/swing_machine_v0_1/selected_period_data_input_preflight.json`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Added unit coverage for blocked/passing source input preflight and CLI coverage for blocked source input preflight against the example plan. |
| Tests/checks run | `ruff check src/swingmachine/qualification_inputs.py src/swingmachine/runtime.py tests/test_qualification_inputs.py tests/test_runtime.py`; `pytest -q tests/test_qualification_inputs.py tests/test_runtime.py::test_runtime_cli_preflights_selected_period_data_inputs_blocked`; `python -c 'from swingmachine.runtime import main; main()' preflight-selected-period-data-inputs --input-plan config/swing_machine_v0_1_selected_period_data_inputs.example.yaml --output reports/swing_machine_v0_1/selected_period_data_input_preflight.json` |
| Test result | Ruff passed; pytest passed: `3 passed in 106.89s`; direct CLI preflight produced expected `data_input_preflight_exit_code=1` and `artifact_status=written`. |
| Assumptions made | Source input preflight should only check explicit local files; it must not fetch market data, infer missing data, build manifests, run replay, touch broker paths, or write runtime databases. |
| Blockers found | Workstream A remains blocked because the selected-period source files referenced by the example input plan do not exist yet. |
| Follow-up work created | Replace the example input plan paths with real selected-period prepared file paths, rerun source-data preflight, then build manifests. |

### SWING-V01-055-RUNBOOK-UPDATE

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Updated the selected-period runbook to include source-data input preflight before manifest building. |
| Files touched | `docs/swing_machine_v0_1_selected_period_runbook.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | None; docs-only. |
| Tests/checks run | Not run; docs-only update. |
| Test result | Not applicable. |
| Assumptions made | Source-data input preflight should be the first operator command in Workstream A once real file paths are known. |
| Blockers found | None beyond the existing missing selected-period source files. |
| Follow-up work created | Provide real source file paths and rerun `preflight-selected-period-data-inputs`. |

### SWING-V01-056

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added a selected-period data input plan builder. `qualification_inputs.py` can now generate a data input plan from a conventional root containing `root/<period_id>/ohlcv`, `symbol_reference`, `corporate_actions`, `earnings_events`, and optional `features` files. `runtime.py` exposes `build-selected-period-data-input-plan`. |
| Files touched | `src/swingmachine/qualification_inputs.py`, `src/swingmachine/runtime.py`, `tests/test_qualification_inputs.py`, `tests/test_runtime.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Added unit coverage for generated plans and CLI coverage proving a generated plan passes source input preflight when required files exist. |
| Tests/checks run | `ruff check src/swingmachine/qualification_inputs.py src/swingmachine/runtime.py tests/test_qualification_inputs.py tests/test_runtime.py`; `pytest -q tests/test_qualification_inputs.py tests/test_runtime.py::test_runtime_cli_builds_selected_period_data_input_plan tests/test_runtime.py::test_runtime_cli_builds_selected_period_manifests` |
| Test result | Ruff passed; pytest passed as part of focused Workstream A run: `5 passed in 120.44s`. |
| Assumptions made | `.parquet` should be preferred when present and `.csv` should be used otherwise; features remain optional at the source input stage. |
| Blockers found | Real selected-period source files are still not present. |
| Follow-up work created | SWING-V01-057 batch selected-period manifest builder. |

### SWING-V01-057

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `build-selected-period-manifests`, a safe batch CLI command that reads a selected-period data input plan and writes one historical panel manifest per period under an output root. It can optionally write a summary JSON artifact listing generated manifest paths. |
| Files touched | `src/swingmachine/runtime.py`, `tests/test_runtime.py`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Added CLI coverage that builds a data input plan from fixture-backed period directories, builds three manifests, writes a summary, loads each manifest, and validates each manifest through the historical panel validator. |
| Tests/checks run | `ruff check src/swingmachine/qualification_inputs.py src/swingmachine/runtime.py tests/test_qualification_inputs.py tests/test_runtime.py`; `pytest -q tests/test_qualification_inputs.py tests/test_runtime.py::test_runtime_cli_builds_selected_period_data_input_plan tests/test_runtime.py::test_runtime_cli_builds_selected_period_manifests` |
| Test result | Ruff passed; pytest passed: `5 passed in 120.44s`. |
| Assumptions made | Batch manifest building should only package explicit prepared files and must not run replay, broker paths, runtime cycles, or database writes. |
| Blockers found | Workstream A remains blocked until real source files exist; the batch command is ready once source-input preflight passes. |
| Follow-up work created | Update runbook sequence and then use these commands once real qualification source data exists. |

### SWING-V01-056-057-RUNBOOK-UPDATE

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Updated the selected-period runbook with the source input plan builder and batch selected-period manifest builder commands. |
| Files touched | `docs/swing_machine_v0_1_selected_period_runbook.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | None; docs-only. |
| Tests/checks run | Not run; docs-only update. |
| Test result | Not applicable. |
| Assumptions made | The operator will arrange real prepared files under a chosen qualification data root before using these commands. |
| Blockers found | None beyond the existing missing selected-period prepared source files. |
| Follow-up work created | Use the new Workstream A command sequence once real data exists. |

### SWING-V01-058

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `docs/swing_machine_v0_1_data_provenance_template.md` for selected-period source data custody, preparation assumptions, point-in-time controls, known gaps, preflight evidence, and operator decision. |
| Files touched | `docs/swing_machine_v0_1_data_provenance_template.md`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | None; docs-only. |
| Tests/checks run | Not run; docs-only update. |
| Test result | Not applicable. |
| Assumptions made | Provenance should be completed before selected-period replay evidence is considered trustworthy. |
| Blockers found | None beyond the existing missing selected-period prepared files. |
| Follow-up work created | Complete one provenance record per selected period when real data is available. |

### SWING-V01-059

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added a qualification evidence indexer. `qualification_evidence.py` defines expected global and per-period qualification artifacts, typed evidence item/index models, an index builder, and JSON writer. `runtime.py` exposes `index-qualification-evidence`. Wrote the current evidence state to `reports/swing_machine_v0_1/qualification_evidence_index.json`. |
| Files touched | `src/swingmachine/qualification_evidence.py`, `src/swingmachine/runtime.py`, `tests/test_qualification_evidence.py`, `tests/test_runtime.py`, `reports/swing_machine_v0_1/qualification_evidence_index.json`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | Added tests for missing and complete evidence roots plus runtime CLI evidence indexing. |
| Tests/checks run | `ruff check src/swingmachine/qualification_evidence.py src/swingmachine/runtime.py tests/test_qualification_evidence.py tests/test_runtime.py`; `pytest -q tests/test_qualification_evidence.py tests/test_runtime.py::test_runtime_cli_indexes_qualification_evidence`; `python -c 'from swingmachine.runtime import main; main()' index-qualification-evidence --evidence-root reports/swing_machine_v0_1 --output reports/swing_machine_v0_1/qualification_evidence_index.json` |
| Test result | Ruff passed; pytest passed: `3 passed in 136.75s`; current evidence index artifact written. |
| Assumptions made | The indexer should check file presence only and must not inspect strategy performance, run replay, touch broker paths, or write runtime databases. |
| Blockers found | Current evidence index remains incomplete because selected-period manifests, replay packages, parity reports, and period-level readiness artifacts do not exist yet. |
| Follow-up work created | Use this index after source data, manifests, preflight, replay, and parity artifacts are generated to drive freeze readiness review. |

### SWING-V01-060

| Field | Value |
| --- | --- |
| Status | complete |
| What changed | Added `docs/swing_machine_v0_1_trading212_data_solution_design.md`, linked it from the main solution design, and added the Trading212 selected-period data backlog items `SWING-V01-060` through `SWING-V01-074`. |
| Files touched | `docs/swing_machine_v0_1_trading212_data_solution_design.md`, `docs/swing_machine_v0_1_solution_design.md`, `docs/swing_machine_v0_1_backlog.md`, `docs/swing_machine_v0_1_implementation_log.md` |
| Tests added or updated | None; docs/design/backlog only. |
| Tests/checks run | Not run; docs-only update. |
| Test result | Not applicable. |
| Assumptions made | Alpaca should be the first primary qualification source and Hugging Face should be retained as an independent cross-provider check. Trading212 DB access must be read-only and bounded because broad scans over the multi-GB DBs are too slow. |
| Blockers found | Export implementation is still required before real Alpaca/Hugging Face selected-period files can be generated. |
| Follow-up work created | SWING-V01-061 through SWING-V01-074. |

## SWING-V01-061 to SWING-V01-074 - Trading212 selected-period data source integration

Status: complete

What changed:

- Added `src/swingmachine/trading212_source.py` with typed Trading212 source configuration, read-only SQLite inspection, selected-period extraction planning, bounded source coverage checks, selected-period export, provider panel drift reporting, and JSON report writing.
- Added `config/swing_machine_v0_1_trading212_sources.yaml` for explicit Alpaca and Hugging Face source paths, output roots, timeframes, lookback settings, and data-availability exclusions.
- Added CLI commands in `src/swingmachine/runtime.py`:
  - `inspect-trading212-research-source`
  - `preflight-trading212-source-coverage`
  - `export-trading212-selected-period-data`
  - `compare-trading212-provider-panels`
- Added `tests/test_trading212_source.py` covering config loading, bounded inspection, coverage preferred/fallback behavior, missing symbol blockers, extraction lookback planning, export contract files, and provider drift detection.
- Exporter now writes repository-compatible `ohlcv.parquet` plus inspection-friendly `historical_ohlcv.csv`.
- Created `docs/swing_machine_v0_1_data_source_decision.md`.

Files touched:

- `src/swingmachine/trading212_source.py`
- `src/swingmachine/runtime.py`
- `config/swing_machine_v0_1_trading212_sources.yaml`
- `tests/test_trading212_source.py`
- `docs/swing_machine_v0_1_data_source_decision.md`
- `docs/swing_machine_v0_1_trading212_data_solution_design.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src/swingmachine/trading212_source.py tests/test_trading212_source.py src/swingmachine/runtime.py`
- `.venv/bin/python -m pytest tests/test_trading212_source.py -q`
- `inspect-trading212-research-source --provider alpaca`
- `inspect-trading212-research-source --provider huggingface`
- `preflight-trading212-source-coverage --provider alpaca`
- `preflight-trading212-source-coverage --provider huggingface`
- `export-trading212-selected-period-data --provider alpaca`
- `export-trading212-selected-period-data --provider huggingface`
- `compare-trading212-provider-panels`
- `build-selected-period-data-input-plan` for Alpaca and Hugging Face exports
- `build-selected-period-manifests` for Alpaca and Hugging Face exports
- `preflight-selected-period-data-inputs` for Alpaca and Hugging Face input plans

Test result:

- Ruff passed.
- Focused Trading212 adapter tests passed: 7 tests.
- Real source inspections passed and wrote reports.
- Real source coverage passed over the explicit 16-symbol panel for both providers.
- Real selected-period exports passed for both providers.
- Provider drift comparison intentionally failed and wrote evidence: 48 blockers across 48 period/symbol rows.
- Alpaca selected-period manifest/preflight integration passed.
- Hugging Face selected-period manifest/preflight integration passed.

Assumptions made:

- `ORCL`, `CRM`, `BAC`, and `CVX` are excluded from the v0.1 data qualification panel because both available Trading212 source databases lack selected-period coverage for them.
- Alpaca is the primary baseline data-source candidate because Hugging Face materially drifts from Alpaca and requires provenance/adjustment-policy investigation.
- Empty corporate-action and earnings-event files are acceptable placeholders for the first selected-period data-input gate, provided they satisfy the repository data contracts.

Blockers found:

- Hugging Face cannot be used as the baseline source until provider drift is explained.
- The four excluded symbols require a recovery/source decision before expanding the qualification universe back to the original 20 symbols.

Follow-up work created:

- `SWING-V01-075`: Investigate Hugging Face adjustment/provenance policy and explain provider drift.
- `SWING-V01-076`: Decide whether excluded symbols should be recovered or remain out of v0.1 qualification.
- `SWING-V01-077`: Promote Alpaca manifests into the baseline manifest package after the remaining qualification gates pass.

## SWING-V01-075 - Hugging Face adjustment/provenance drift investigation

Status: blocked

What changed:

- Created `docs/swing_machine_v0_1_huggingface_drift_investigation.md`.
- Compared exported Alpaca and Hugging Face selected-period panels for representative split-sensitive and ETF symbols.
- Identified systematic adjustment-scale drift and a Hugging Face session gap on `2024-11-13` for seven symbols.

Files touched:

- `docs/swing_machine_v0_1_huggingface_drift_investigation.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Local pandas comparison of Alpaca and Hugging Face exported `ohlcv.parquet` panels.
- Existing drift report: `reports/swing_machine_v0_1/trading212_provider_panel_drift_report.json`.

Test result:

- HF promotion remains blocked.
- Alpaca remains the primary selected-period data-source candidate.

Assumptions made:

- The observed 10x differences are most likely different split-adjustment policy, not random price error.
- The smaller SPY drift is most likely dividend/distribution adjustment policy difference.

Blockers found:

- HF adjustment policy is not documented in the swing machine repository.
- HF misses `2024-11-13` for seven symbols in the exported selected-period panel.

Follow-up work created:

- Define a formal OHLCV adjustment policy for `swing_machine_v0_1` before considering multi-provider parity transforms.

## SWING-V01-076 - Excluded symbol recovery/source decision

Status: complete

What changed:

- Created `docs/swing_machine_v0_1_excluded_symbol_decision.md`.
- Checked `ORCL`, `CRM`, `BAC`, and `CVX` in both Trading212 local source DBs for `1d` and `1m` availability.
- Confirmed the symbols are absent entirely from both DBs, not just missing in selected periods.

Files touched:

- `docs/swing_machine_v0_1_excluded_symbol_decision.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Read-only SQLite indexed first/last probes for each excluded symbol, provider, and timeframe.

Test result:

- Keep the symbols excluded from v0.1 qualification.

Assumptions made:

- v0.1 should prefer a smaller complete and explicit panel over a larger partially sourced panel.

Blockers found:

- Restoring these symbols requires a new explicit data source and full data-contract validation.

Follow-up work created:

- None beyond the existing condition that any future source expansion must be explicit and preflighted.

## SWING-V01-077 - Promote Alpaca manifests into baseline manifest package

Status: blocked

What changed:

- Created `docs/swing_machine_v0_1_alpaca_manifest_promotion_plan.md`.
- Recorded that Alpaca manifests are ready but must not be promoted until the remaining qualification gates pass.

Files touched:

- `docs/swing_machine_v0_1_alpaca_manifest_promotion_plan.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Relies on previously completed Alpaca data input plan, manifest build, and selected-period data input preflight.

Test result:

- Blocked by remaining qualification gates, not by data-source availability.

Assumptions made:

- Baseline manifest promotion should be treated as a freeze-gate action, not as a data-export side effect.

Blockers found:

- Remaining qualification gates are not yet complete.

Follow-up work created:

- Continue with parity, smoke, dry-run safety, baseline manifest, qualification checklist, and freeze-review work before any serious full run.

## SWING-V01-078 to SWING-V01-083 - Overnight qualification evidence batch

Status: complete

What changed:

- Added `src/swingmachine/overnight_qualification.py` for overnight-safe evidence consolidation, draft manifest bundle generation, selected-period data smoke checks, and dry-run safety checks.
- Added runtime commands:
  - `build-overnight-qualification-evidence-summary`
  - `write-draft-baseline-manifest-package`
  - `smoke-selected-period-data-package`
  - `check-selected-period-dry-run-safety`
- Added `tests/test_overnight_qualification.py`.
- Tightened Trading212 source coverage in `src/swingmachine/trading212_source.py` so coverage requires bars in the selected qualification window itself, not merely the broad extraction/lookback window.
- Generated overnight reports under `reports/swing_machine_v0_1/`.
- Added checkpoint and audit docs:
  - `docs/swing_machine_v0_1_overnight_checkpoint.md`
  - `docs/swing_machine_v0_1_research_runtime_parity_audit.md`
  - `docs/swing_machine_v0_1_qualification_gate_checklist.md`

Files touched:

- `src/swingmachine/overnight_qualification.py`
- `src/swingmachine/runtime.py`
- `src/swingmachine/trading212_source.py`
- `tests/test_overnight_qualification.py`
- `docs/swing_machine_v0_1_overnight_checkpoint.md`
- `docs/swing_machine_v0_1_research_runtime_parity_audit.md`
- `docs/swing_machine_v0_1_qualification_gate_checklist.md`
- `docs/swing_machine_v0_1_data_source_decision.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/overnight_qualification_evidence_summary.json`
- `reports/swing_machine_v0_1/draft_baseline_manifest_bundle.json`
- `reports/swing_machine_v0_1/draft_baseline_manifest.json`
- `reports/swing_machine_v0_1/draft_qualification_checklist.json`
- `reports/swing_machine_v0_1/draft_freeze_readiness.json`
- `reports/swing_machine_v0_1/selected_period_data_smoke_report.json`
- `reports/swing_machine_v0_1/selected_period_dry_run_safety_report.json`
- `reports/swing_machine_v0_1/trading212_alpaca_selected_period_preflight.json`
- `reports/swing_machine_v0_1/trading212_alpaca_source_coverage.json`
- `reports/swing_machine_v0_1/trading212_huggingface_source_coverage.json`

Tests/checks run:

- `.venv/bin/python -m ruff check src/swingmachine/overnight_qualification.py tests/test_overnight_qualification.py src/swingmachine/trading212_source.py tests/test_trading212_source.py src/swingmachine/runtime.py`
- `.venv/bin/python -m pytest tests/test_overnight_qualification.py tests/test_trading212_source.py -q`
- `preflight-selected-period-qualification` with real Alpaca manifest paths
- `preflight-trading212-source-coverage --provider alpaca`
- `preflight-trading212-source-coverage --provider huggingface`
- read-only SQLite first/last source date probes for representative symbols
- `write-draft-baseline-manifest-package`
- `smoke-selected-period-data-package`
- `check-selected-period-dry-run-safety`
- `build-overnight-qualification-evidence-summary`

Test result:

- Ruff passed.
- Focused tests passed: 10 tests.
- Selected-period qualification preflight with manifest paths passed, but is now considered non-qualifying because source coverage and smoke fail for the selected windows.
- Corrected source coverage fails for both providers: 0 of 48 selected period/symbol rows covered.
- Selected-period smoke fails with zero qualification sessions for all periods.
- Dry-run safety report passes and confirms serious full run remains blocked.
- Draft freeze readiness remains `BLOCK`.

Assumptions made:

- A selected-period data package cannot qualify a period unless rows exist inside that period's replay window; lookback-only rows are insufficient.
- Existing generated Trading212 exports are still useful diagnostics but must not be treated as qualification evidence for the current selected-period plan.

Blockers found:

- Trading212 local source DBs end on `2025-07-31`; current selected-period windows require `2025-09-02` through `2026-04-24`.
- HF provider drift remains unresolved.
- Research/runtime selected-period parity evidence is not available because selected-period data is not aligned.

Follow-up work created:

- `SWING-V01-084`: Decide whether to acquire newer data or shift selected periods to covered historical windows.
- `SWING-V01-085` through `SWING-V01-091`: Regenerate coverage, exports, manifests, smoke, replay, parity, freeze readiness, and freeze review after the data/window decision.

## SWING-V01-084 to SWING-V01-089 - Historical selected-period qualification path

Status: partially complete; replay/parity qualification blocked

What changed:

- Added `config/swing_machine_v0_1_selected_periods_historical.yaml` with covered historical windows ending no later than the local Trading212 source DB max date.
- Ran historical source coverage for Alpaca and Hugging Face.
- Exported historical Alpaca selected-period data.
- Built historical Alpaca data input plan and historical manifests.
- Ran historical data input preflight and selected-period qualification preflight.
- Ran selected-period data smoke against the historical Alpaca data input plan.
- Ran dry-run safety against the historical selected-period plan.
- Ran two historical smoke dry-run replay lanes using the same smoke manifest:
  - research lane
  - runtime-compatible lane
- Generated a package parity report between the two smoke replay lanes.
- Created `docs/swing_machine_v0_1_historical_qualification_run.md`.

Files touched:

- `config/swing_machine_v0_1_selected_periods_historical.yaml`
- `docs/swing_machine_v0_1_historical_qualification_run.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_source_coverage.json`
- `reports/swing_machine_v0_1/trading212_huggingface_historical_source_coverage.json`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_selected_period_export.json`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_data_input_plan.yaml`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_manifest_build_summary.json`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_data_input_preflight.json`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_selected_period_preflight.json`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_data_smoke_report.json`
- `reports/swing_machine_v0_1/historical_selected_period_dry_run_safety_report.json`
- `reports/swing_machine_v0_1/replay_historical_smoke_research/`
- `reports/swing_machine_v0_1/replay_historical_smoke_runtime_compatible/`
- `reports/swing_machine_v0_1/historical_smoke_baseline_parity_report.json`

Tests/checks run:

- `preflight-trading212-source-coverage --provider alpaca --selected-period-plan config/swing_machine_v0_1_selected_periods_historical.yaml`
- `preflight-trading212-source-coverage --provider huggingface --selected-period-plan config/swing_machine_v0_1_selected_periods_historical.yaml`
- `export-trading212-selected-period-data --provider alpaca --selected-period-plan config/swing_machine_v0_1_selected_periods_historical.yaml`
- `build-selected-period-data-input-plan --selected-period-plan config/swing_machine_v0_1_selected_periods_historical.yaml`
- `build-selected-period-manifests`
- `preflight-selected-period-data-inputs`
- `preflight-selected-period-qualification --plan config/swing_machine_v0_1_selected_periods_historical.yaml`
- `smoke-selected-period-data-package --input-plan reports/swing_machine_v0_1/trading212_alpaca_historical_data_input_plan.yaml`
- `check-selected-period-dry-run-safety --selected-period-plan config/swing_machine_v0_1_selected_periods_historical.yaml`
- `run-historical-replay` twice against `historical_smoke_5_sessions`
- `compare_baseline_report_package_files` between the two replay-emitted baseline report packages

Test result:

- Historical Alpaca coverage passed: 48 covered, 0 missing.
- Historical Hugging Face coverage passed: 48 covered, 0 missing.
- Historical Alpaca export passed.
- Historical data input preflight passed.
- Historical selected-period preflight passed.
- Historical data smoke passed:
  - `historical_smoke_5_sessions`: 5 qualification sessions, 16 symbols.
  - `historical_medium_replay_window`: 63 qualification sessions, 16 symbols.
  - `historical_contract_stability_window_v0_1`: 41 qualification sessions, 16 symbols.
- Historical dry-run safety passed and serious full run remains blocked.
- Historical smoke replay completed but failed in both lanes.
- Package parity between failed replay packages passed with zero differences, but is diagnostic only and not qualifying evidence.

Assumptions made:

- Historical machinery qualification is sufficient to continue engineering the baseline gates, but it does not prove recent-market readiness.
- Parity evidence is only qualifying when both compared replay packages are produced by passing replay runs.

Blockers found:

- Historical replay reconciliation failed because backtest submissions/fills were much broader than selected signal-session setup/shadow/paper evidence.
- The replay path needs explicit selected replay-window semantics so lookback rows can support indicators without becoming tradeable replay sessions.

Follow-up work created:

- `SWING-V01-092`: Add selected replay-window semantics to manifests/replay.
- `SWING-V01-093`: Regenerate historical manifests with replay-window metadata.
- `SWING-V01-094`: Rerun historical smoke replay after the replay-window fix.
- `SWING-V01-095`: Generate qualifying historical parity evidence from passing replay packages.

## SWING-V01-092 to SWING-V01-095 - Replay-window semantics and windowed smoke replay

Status: complete with warning blocker

What changed:

- Added optional `replay_start_session` and `replay_end_session` fields to `HistoricalPanelManifest`.
- Extended historical panel manifest builders to accept and persist replay-window metadata.
- Updated batch selected-period manifest generation to copy selected-period start/end dates into manifest replay-window fields.
- Updated historical replay execution so:
  - full manifest data remains available for feature/indicator calculation,
  - selected replay sessions are taken from manifest replay-window metadata when present,
  - backtest/reconciliation run only over the selected signal and next-session decision slice.
- Regenerated historical Alpaca manifests with replay-window metadata.
- Reran two historical smoke replay lanes with the regenerated manifest.
- Generated `reports/swing_machine_v0_1/historical_smoke_windowed_baseline_parity_report.json`.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/data_contracts.py`
- `src/swingmachine/runtime.py`
- `src/swingmachine/replay.py`
- `data/qualification_manifests/trading212/alpaca_historical/historical_smoke_5_sessions/manifest.yaml`
- `data/qualification_manifests/trading212/alpaca_historical/historical_medium_replay_window/manifest.yaml`
- `data/qualification_manifests/trading212/alpaca_historical/historical_contract_stability_window_v0_1/manifest.yaml`
- `reports/swing_machine_v0_1/replay_historical_smoke_research_windowed/`
- `reports/swing_machine_v0_1/replay_historical_smoke_runtime_windowed/`
- `reports/swing_machine_v0_1/historical_smoke_windowed_baseline_parity_report.json`
- `docs/swing_machine_v0_1_historical_qualification_run.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src/swingmachine/contracts.py src/swingmachine/data_contracts.py src/swingmachine/runtime.py src/swingmachine/replay.py tests/test_replay_workflow.py tests/test_runtime.py`
- `.venv/bin/python -m pytest tests/test_replay_workflow.py::test_historical_manifest_replay_writes_deterministic_material_artifacts tests/test_runtime.py::test_runtime_cli_builds_selected_period_manifests -q`
- `build-selected-period-manifests --input-plan reports/swing_machine_v0_1/trading212_alpaca_historical_data_input_plan.yaml --output-root data/qualification_manifests/trading212/alpaca_historical`
- `run-historical-replay` against `historical_smoke_5_sessions` for research and runtime-compatible lanes.
- `compare_baseline_report_package_files` for the two windowed replay packages.

Test result:

- Ruff passed.
- Focused tests passed: 2 tests.
- Regenerated manifest includes `replay_start_session: '2025-07-21'` and `replay_end_session: '2025-07-25'` while full data coverage starts `2024-03-08`.
- Windowed replay reconciliation passed in both lanes.
- Windowed replay status is `WARN` because manifest validation still warns about missing weekday sessions that are likely US market holidays.
- Windowed package parity passed with zero differences.

Assumptions made:

- Replay qualification should compare the selected signal/next-session decision slice, not the full indicator lookback window.
- A `WARN` replay result should not be treated as clean qualification evidence until the warning source is understood and accepted or fixed.

Blockers found:

- Historical panel validation uses a `WEEKDAY` calendar and flags known market holidays as missing sessions.

Follow-up work created:

- `SWING-V01-096`: Market-calendar-aware historical panel validation.
- `SWING-V01-097`: Rerun windowed historical smoke replay after calendar fix.
- `SWING-V01-098`: Run historical medium and stability replay only after smoke replay is clean.

## SWING-V01-096 to SWING-V01-097 - Market-calendar validation and clean historical smoke replay

Status: complete

What changed:

- Added `US_EQUITY` market-calendar support to historical panel expected-session validation.
- Selected-period manifest generation now emits `calendar: US_EQUITY`.
- Regenerated historical Alpaca manifests with both replay-window metadata and `US_EQUITY` calendar metadata.
- Reran historical smoke replay sequentially in the research and runtime-compatible lanes.
- Regenerated `reports/swing_machine_v0_1/historical_smoke_windowed_baseline_parity_report.json`.

Files touched:

- `src/swingmachine/data_contracts.py`
- `src/swingmachine/runtime.py`
- `tests/test_data_contracts.py`
- `data/qualification_manifests/trading212/alpaca_historical/historical_smoke_5_sessions/manifest.yaml`
- `data/qualification_manifests/trading212/alpaca_historical/historical_medium_replay_window/manifest.yaml`
- `data/qualification_manifests/trading212/alpaca_historical/historical_contract_stability_window_v0_1/manifest.yaml`
- `reports/swing_machine_v0_1/replay_historical_smoke_research_windowed/`
- `reports/swing_machine_v0_1/replay_historical_smoke_runtime_windowed/`
- `reports/swing_machine_v0_1/historical_smoke_windowed_baseline_parity_report.json`
- `docs/swing_machine_v0_1_historical_qualification_run.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src/swingmachine/data_contracts.py src/swingmachine/runtime.py tests/test_data_contracts.py`
- `.venv/bin/python -m pytest tests/test_data_contracts.py::test_validate_historical_panel_manifest_us_equity_calendar_skips_holidays tests/test_replay_workflow.py::test_historical_manifest_replay_writes_deterministic_material_artifacts tests/test_runtime.py::test_runtime_cli_builds_selected_period_manifests -q`
- `build-selected-period-manifests --input-plan reports/swing_machine_v0_1/trading212_alpaca_historical_data_input_plan.yaml --output-root data/qualification_manifests/trading212/alpaca_historical`
- `validate_historical_panel_manifest` on `historical_smoke_5_sessions`
- `run-historical-replay` for `replay_historical_smoke_research_windowed`
- `run-historical-replay` for `replay_historical_smoke_runtime_windowed`
- `compare_baseline_report_package_files` for the two clean smoke replay packages

Test result:

- Ruff passed.
- Focused tests passed: 3 tests.
- Historical smoke manifest validation is now `PASS` with no warnings.
- Research-lane historical smoke replay status is `PASS`.
- Runtime-compatible historical smoke replay status is `PASS`.
- Windowed historical smoke parity passed with zero differences.

Assumptions made:

- `US_EQUITY` holiday exclusions are appropriate for the current Trading212 US equity/ETF qualification panel.
- Sequential replay runs are preferred over parallel replay runs for this repo because parallel runs were slow and harder to control.

Blockers found:

- None for historical smoke replay. Medium and stability windows remain unrun.

Follow-up work created:

- `SWING-V01-098`: Run historical medium replay and parity.
- `SWING-V01-099`: Run historical contract-stability replay and parity after medium passes.
- `SWING-V01-100`: Build historical qualification evidence index.
- `SWING-V01-101`: Rebuild freeze readiness with historical evidence.

## SWING-V01-098 - Historical medium replay and parity

Status: complete

What changed:

- Ran historical medium replay sequentially in the research lane.
- Ran historical medium replay sequentially in the runtime-compatible lane.
- Generated `reports/swing_machine_v0_1/historical_medium_windowed_baseline_parity_report.json`.
- Updated historical qualification documentation and backlog status.

Files touched:

- `reports/swing_machine_v0_1/replay_historical_medium_research_windowed/`
- `reports/swing_machine_v0_1/replay_historical_medium_runtime_windowed/`
- `reports/swing_machine_v0_1/historical_medium_windowed_baseline_parity_report.json`
- `docs/swing_machine_v0_1_historical_qualification_run.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `run-historical-replay --manifest data/qualification_manifests/trading212/alpaca_historical/historical_medium_replay_window/manifest.yaml --output-dir reports/swing_machine_v0_1/replay_historical_medium_research_windowed --config swing_trading_bot_config_template_v2.yaml`
- `run-historical-replay --manifest data/qualification_manifests/trading212/alpaca_historical/historical_medium_replay_window/manifest.yaml --output-dir reports/swing_machine_v0_1/replay_historical_medium_runtime_windowed --config swing_trading_bot_config_template_v2.yaml`
- `compare_baseline_report_package_files` for the two medium replay packages.

Test result:

- Research-lane medium replay status: `PASS`.
- Runtime-compatible medium replay status: `PASS`.
- Validation warning count: 0 in both lanes.
- Reconciliation status: `PASS` in both lanes.
- Medium parity report passed with zero differences.

Assumptions made:

- Sequential replay remains the safest execution pattern for these checks because parallel replay was slower and harder to control.

Blockers found:

- None for the medium replay gate.

Follow-up work created:

- Continue to `SWING-V01-099`: historical contract-stability replay and parity.

## SWING-V01-099 - Historical contract-stability replay and parity

Status: complete

What changed:

- Ran historical contract-stability replay sequentially in the research lane.
- Ran historical contract-stability replay sequentially in the runtime-compatible lane.
- Generated `reports/swing_machine_v0_1/historical_stability_windowed_baseline_parity_report.json`.
- Updated historical qualification documentation and backlog status.

Files touched:

- `reports/swing_machine_v0_1/replay_historical_stability_research_windowed/`
- `reports/swing_machine_v0_1/replay_historical_stability_runtime_windowed/`
- `reports/swing_machine_v0_1/historical_stability_windowed_baseline_parity_report.json`
- `docs/swing_machine_v0_1_historical_qualification_run.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `run-historical-replay --manifest data/qualification_manifests/trading212/alpaca_historical/historical_contract_stability_window_v0_1/manifest.yaml --output-dir reports/swing_machine_v0_1/replay_historical_stability_research_windowed --config swing_trading_bot_config_template_v2.yaml`
- `run-historical-replay --manifest data/qualification_manifests/trading212/alpaca_historical/historical_contract_stability_window_v0_1/manifest.yaml --output-dir reports/swing_machine_v0_1/replay_historical_stability_runtime_windowed --config swing_trading_bot_config_template_v2.yaml`
- `compare_baseline_report_package_files` for the two contract-stability replay packages.

Test result:

- Research-lane contract-stability replay status: `PASS`.
- Runtime-compatible contract-stability replay completed successfully.
- Validation warning count: 0.
- Reconciliation status: `PASS`.
- Contract-stability parity report passed with zero differences.

Assumptions made:

- The contract-stability historical window is sufficient as the third selected replay tier for the current historical qualification batch.

Blockers found:

- None for the contract-stability replay gate.

Follow-up work created:

- Continue to `SWING-V01-100`: build historical qualification evidence index.

## SWING-V01-100 - Historical qualification evidence index

Status: complete

What changed:

- Generated `reports/swing_machine_v0_1/historical_qualification_evidence_index.json`.
- Indexed the historical selected-period plan and available qualification evidence under `reports/swing_machine_v0_1`.

Files touched:

- `reports/swing_machine_v0_1/historical_qualification_evidence_index.json`
- `docs/swing_machine_v0_1_historical_qualification_run.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `index-qualification-evidence --evidence-root reports/swing_machine_v0_1 --selected-period-plan config/swing_machine_v0_1_selected_periods_historical.yaml --output reports/swing_machine_v0_1/historical_qualification_evidence_index.json`

Test result:

- Evidence index generation completed successfully.
- Two initial invocations with stale option names failed without producing qualification artifacts; the corrected command succeeded.

Assumptions made:

- The evidence index is a reporting/indexing artifact and does not by itself approve a serious full run.

Blockers found:

- None for evidence indexing.

Follow-up work created:

- Continue to `SWING-V01-101`: rebuild freeze readiness with historical evidence.

## SWING-V01-101 - Historical freeze readiness rebuild

Status: complete with BLOCK decision

What changed:

- Generated `reports/swing_machine_v0_1/historical_baseline_manifest.json`.
- Generated `reports/swing_machine_v0_1/historical_qualification_checklist.json`.
- Generated `reports/swing_machine_v0_1/historical_freeze_readiness.json`.
- Carried clean historical smoke, medium, and contract-stability replay/parity evidence into freeze-readiness evaluation.
- Left `unit_contract_tests`, `operator_review_pass`, and `freeze_review` unsatisfied.

Files touched:

- `reports/swing_machine_v0_1/historical_baseline_manifest.json`
- `reports/swing_machine_v0_1/historical_qualification_checklist.json`
- `reports/swing_machine_v0_1/historical_freeze_readiness.json`
- `docs/swing_machine_v0_1_historical_qualification_run.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Programmatic freeze-readiness rebuild using `build_swing_baseline_manifest_from_profile_alias`, `build_baseline_qualification_checklist`, and `evaluate_serious_full_run_freeze_readiness`.

Test result:

- Readiness decision: `BLOCK`.
- Serious full run allowed: `false`.
- Blocker count: 2.
- Blocker codes: `manifest_checks_incomplete`, `operator_approval_missing`.
- Incomplete manifest checks: `unit_contract_tests`, `operator_review_pass`, `freeze_review`.

Assumptions made:

- Historical replay/parity evidence can satisfy replay, parity, smoke, dry-run, data-contract, reporting, and runtime/research parity gates.
- Focused unit/contract certification and human freeze approval must not be inferred from replay success.

Blockers found:

- `unit_contract_tests` certification remains incomplete.
- Operator freeze approval has not been recorded.
- Freeze review has not been completed.

Follow-up work created:

- `SWING-V01-102`: Certify focused unit and contract gate for historical freeze readiness.
- `SWING-V01-103`: Produce historical freeze review packet.
- `SWING-V01-104`: Record operator freeze-review decision.
- `SWING-V01-105`: Rebuild readiness after certification and review evidence.

## SWING-V01-102 - Focused unit and contract certification gate

Status: complete

What changed:

- Ran the focused unit/contract certification gate in smaller shards.
- Rebuilt historical baseline manifest, qualification checklist, and freeze readiness with `unit_contract_tests` satisfied.
- Left operator review and freeze approval unsatisfied.

Files touched:

- `reports/swing_machine_v0_1/historical_baseline_manifest.json`
- `reports/swing_machine_v0_1/historical_qualification_checklist.json`
- `reports/swing_machine_v0_1/historical_freeze_readiness.json`
- `docs/swing_machine_v0_1_historical_qualification_run.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_contracts.py tests/test_swing_contracts.py tests/test_signals.py tests/test_features.py tests/test_entries.py tests/test_exits.py tests/test_lifecycle.py tests/test_order_intents.py tests/test_order_state_machine.py tests/test_portfolio_manager.py -q`
- `.venv/bin/python -m pytest tests/test_baseline.py tests/test_baseline_parity.py tests/test_baseline_readiness.py tests/test_baseline_reporting.py tests/test_data_contracts.py tests/test_qualification_evidence.py tests/test_qualification_inputs.py -q`
- Programmatic freeze-readiness rebuild with `unit_contract_tests` satisfied and operator/freeze-review checks still blocked.

Test result:

- Contract/lifecycle/order/risk shard: 60 passed in 97.69s.
- Baseline/data/readiness/qualification shard: 72 passed in 196.98s.
- Updated readiness decision: `BLOCK`.
- Serious full run allowed: `false`.
- Remaining blocker evidence: `operator_review_pass`, `freeze_review`.
- Operator approval remains missing.

Assumptions made:

- The two passing shards are sufficient evidence for the `unit_contract_tests` manifest check.
- Historical replay artifacts, rather than slow pytest replay-workflow execution, remain the authoritative replay/parity evidence for this freeze packet.

Blockers found:

- Operator freeze review and approval remain incomplete.

Follow-up work created:

- Continue to `SWING-V01-103`: produce historical freeze review packet.

## SWING-V01-103 - Historical freeze review packet

Status: complete

What changed:

- Created `docs/swing_machine_v0_1_historical_freeze_review_packet.md`.
- Consolidated qualification evidence, replay tiers, parity reports, unit/contract certification, assumptions, prohibited actions, and operator review checklist.

Files touched:

- `docs/swing_machine_v0_1_historical_freeze_review_packet.md`
- `docs/swing_machine_v0_1_historical_qualification_run.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- No new code tests were required for this docs-only packet.

Test result:

- Freeze review packet created.
- Serious full run remains prohibited.

Assumptions made:

- The packet is a review artifact, not an approval artifact.

Blockers found:

- `SWING-V01-104` requires explicit operator freeze-review decision.
- `SWING-V01-105` is blocked until that decision is available.

Follow-up work created:

- `SWING-V01-104`: Record operator freeze-review decision.
- `SWING-V01-105`: Rebuild readiness after approval, if granted.

## SWING-V01-104 - Record operator freeze-review decision

Status: complete

What changed:

- Recorded operator approval of the engineering evidence.
- Created `reports/swing_machine_v0_1/historical_operator_freeze_approval.json`.

Files touched:

- `reports/swing_machine_v0_1/historical_operator_freeze_approval.json`
- `docs/swing_machine_v0_1_historical_qualification_run.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- No code tests required; this is an approval artifact.

Test result:

- Approval recorded.

Assumptions made:

- The user's statement `yes i am comfortable approving the engineering evidence` is explicit approval of the engineering evidence freeze review, not approval to execute live trading or real broker actions.

Blockers found:

- None for approval recording.

Follow-up work created:

- Continue to `SWING-V01-105`: rebuild readiness with operator approval.

## SWING-V01-105 - Rebuild readiness with operator approval

Status: complete

What changed:

- Rebuilt `reports/swing_machine_v0_1/historical_baseline_manifest.json` with all required checks satisfied.
- Rebuilt `reports/swing_machine_v0_1/historical_qualification_checklist.json`.
- Rebuilt `reports/swing_machine_v0_1/historical_freeze_readiness.json` with operator approval recorded.

Files touched:

- `reports/swing_machine_v0_1/historical_baseline_manifest.json`
- `reports/swing_machine_v0_1/historical_qualification_checklist.json`
- `reports/swing_machine_v0_1/historical_freeze_readiness.json`
- `docs/swing_machine_v0_1_historical_qualification_run.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Programmatic freeze-readiness rebuild with `operator_approved=True`.

Test result:

- Decision: `ALLOW`.
- Serious full run allowed: `true`.
- Blocker count: 0.

Assumptions made:

- Readiness `ALLOW` permits preparing a guarded serious full-run plan, but not executing a run unless the operator explicitly requests execution.

Blockers found:

- None for readiness rebuild.

Follow-up work created:

- Continue to `SWING-V01-108`: prepare guarded serious full-run plan.

## SWING-V01-108 - Guarded serious full-run plan

Status: complete for planning, execution not started

What changed:

- Created `docs/swing_machine_v0_1_guarded_serious_full_run_plan.md`.
- Defined preconditions, safety boundaries, command placeholder, post-run checks, stop conditions, and recommended next execution shape.

Files touched:

- `docs/swing_machine_v0_1_guarded_serious_full_run_plan.md`
- `docs/swing_machine_v0_1_historical_qualification_run.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- No runtime tests were run; no serious full run was executed.

Test result:

- Guarded plan created.

Assumptions made:

- The best next serious run is a broader historical replay package, not live/paper runtime action.

Blockers found:

- Execution still requires an explicit operator instruction to run.

Follow-up work created:

- Decide whether to run the existing selected-window serious replay or first build a broader historical manifest.

## SWING-V01-109 to SWING-V01-111 - Broad historical serious offline run

Status: complete

What changed:

- Created `config/swing_machine_v0_1_selected_periods_historical_broad.yaml` for a broader offline historical replay window from 2024-06-03 to 2025-07-31.
- Preflighted broad Alpaca historical source coverage.
- Exported broad selected-period data from the Trading212 Alpaca historical source.
- Built and preflighted the broad data-input plan.
- Built the broad historical panel manifest.
- Fixed selected-period plan contract issues found by preflight:
  - Restored literal-compatible `plan_version`.
  - Restored literal-compatible `serious_full_run_policy`.
  - Added required `freeze_readiness.json` and `qualification_checklist.json` artifacts.
- Ran broad data-smoke and dry-run safety checks.
- Ran paired broad offline historical replay in research and runtime-compatible lanes.
- Generated broad parity, evidence index, and summary artifacts.
- Created `docs/swing_machine_v0_1_historical_broad_serious_run.md`.

Files touched:

- `config/swing_machine_v0_1_selected_periods_historical_broad.yaml`
- `data/qualification_sources/trading212/alpaca/historical_broad_2024_06_to_2025_07_v0_1/`
- `data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_source_coverage.json`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_selected_period_export.json`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_data_input_plan.yaml`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_data_input_preflight.json`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_manifest_build_summary.json`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_selected_period_preflight.json`
- `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_data_smoke_report.json`
- `reports/swing_machine_v0_1/historical_broad_selected_period_dry_run_safety_report.json`
- `reports/swing_machine_v0_1/serious_full_run_broad_research_20260506T124131Z/`
- `reports/swing_machine_v0_1/serious_full_run_broad_runtime_20260506T124131Z/`
- `reports/swing_machine_v0_1/historical_broad_serious_full_run_parity_report_20260506T124131Z.json`
- `reports/swing_machine_v0_1/historical_broad_serious_full_run_evidence_index_20260506T124131Z.json`
- `reports/swing_machine_v0_1/historical_broad_serious_full_run_summary_20260506T124131Z.json`
- `docs/swing_machine_v0_1_historical_broad_serious_run.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `preflight-trading212-source-coverage --provider alpaca --selected-period-plan config/swing_machine_v0_1_selected_periods_historical_broad.yaml`
- `export-trading212-selected-period-data --provider alpaca --selected-period-plan config/swing_machine_v0_1_selected_periods_historical_broad.yaml`
- `build-selected-period-data-input-plan --selected-period-plan config/swing_machine_v0_1_selected_periods_historical_broad.yaml`
- `preflight-selected-period-data-inputs --input-plan reports/swing_machine_v0_1/trading212_alpaca_historical_broad_data_input_plan.yaml`
- `build-selected-period-manifests --input-plan reports/swing_machine_v0_1/trading212_alpaca_historical_broad_data_input_plan.yaml`
- `preflight-selected-period-qualification --plan config/swing_machine_v0_1_selected_periods_historical_broad.yaml`
- `smoke-selected-period-data-package --input-plan reports/swing_machine_v0_1/trading212_alpaca_historical_broad_data_input_plan.yaml`
- `check-selected-period-dry-run-safety --selected-period-plan config/swing_machine_v0_1_selected_periods_historical_broad.yaml`
- `run-historical-replay --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml` for research and runtime-compatible lanes.
- `compare_baseline_report_package_files` for broad research/runtime package parity.
- `index-qualification-evidence --selected-period-plan config/swing_machine_v0_1_selected_periods_historical_broad.yaml`.

Test result:

- Broad source coverage passed with 16 covered symbols and no blockers.
- Broad selected-period export passed with no blockers.
- Broad data-input preflight passed with no blockers.
- Broad selected-period qualification preflight passed with no blockers after contract fixes.
- Broad data smoke passed.
- Broad dry-run safety passed.
- Research replay status: `PASS`.
- Runtime-compatible replay status: `PASS`.
- Validation status: `PASS` with 0 errors and 0 warnings in both lanes.
- Reconciliation status: `PASS` in both lanes.
- Broad parity passed with 0 differences.

Assumptions made:

- The broad period from 2024-06-03 to 2025-07-31 is a reasonable first broader offline historical replay because it spans the previously qualified older stability and medium periods.
- The run remains offline machinery evidence and does not authorize live or paper runtime execution.

Blockers found:

- None for broad offline replay completion.
- Important caveat: broad replay emitted only 16 decision traces and 2 setups, so this is not yet proof of dense day-by-day scanner behaviour across the full historical window.

Follow-up work created:

- `SWING-V01-112`: Investigate decision-density semantics for broad historical replay.
- `SWING-V01-113`: Design true multi-session scanner/backtest qualification mode if required before paper/live runtime.

## SWING-V01-112 to SWING-V01-113 - Decision-density diagnostics and scanner design

Status: complete

What changed:

- Created `reports/swing_machine_v0_1/historical_broad_decision_density_diagnostics_20260506T124131Z.json`.
- Created `docs/swing_machine_v0_1_decision_density_review.md`.
- Created `docs/swing_machine_v0_1_multi_session_scanner_design.md`.
- Updated backlog with scanner implementation items `SWING-V01-114` through `SWING-V01-119`.

Files touched:

- `reports/swing_machine_v0_1/historical_broad_decision_density_diagnostics_20260506T124131Z.json`
- `docs/swing_machine_v0_1_decision_density_review.md`
- `docs/swing_machine_v0_1_multi_session_scanner_design.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Checks run:

- Generated diagnostics from the broad manifest, broad replay summaries, decision traces, baseline package, and parity report using the project virtual environment.

Result:

- Broad manifest replay-window session count: 291.
- Current selected-session replay signal session: `2025-07-30`.
- Current selected-session replay next session: `2025-07-31`.
- Decision traces: 16.
- Valid setups: 2.
- Explanation: current `run-historical-replay` is selected-session machinery replay, not dense day-by-day scanner replay.

Assumptions made:

- Existing selected-session replay semantics should remain unchanged because they are already qualified and useful.
- Multi-session scanner qualification should be implemented as a separate guarded offline path.

Blockers found:

- Paper/live runtime should remain deferred until scanner-density qualification is implemented and reviewed.

Follow-up work created:

- `SWING-V01-114`: Add typed scanner replay contracts.
- `SWING-V01-115`: Extract reusable selected-session replay internals.
- `SWING-V01-116`: Implement Tier 1 stateless scanner iterator and density artifacts.
- `SWING-V01-117`: Add guarded scanner replay CLI.
- `SWING-V01-118`: Add scanner parity report.
- `SWING-V01-119`: Run and review broad scanner-density qualification.

## SWING-V01-114 - Scanner replay contracts

Status: complete

What changed:

- Added typed scanner replay contracts:
  - `HistoricalScannerReplayDensityMetrics`
  - `HistoricalScannerReplaySessionResult`
  - `HistoricalScannerReplayStateSnapshot`
  - `HistoricalScannerReplaySummary`
  - `HistoricalScannerReplayArtifactManifest`
- Added focused contract coverage for the new scanner models.

Files touched:

- `src/swingmachine/contracts.py`
- `tests/test_contracts.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Checks run:

- `.venv/bin/python -m pytest tests/test_contracts.py::test_historical_scanner_replay_contracts_capture_density -q`

Result:

- 1 passed in 15.03s.

Assumptions made:

- Scanner qualification should use dedicated typed contracts rather than overloading selected-session replay result models.
- These contracts are additive and should not change existing selected-session replay behaviour.

Blockers found:

- None for scanner contracts.

Follow-up work created:

- `SWING-V01-115`: Extract reusable selected-session replay internals without changing `run-historical-replay` behaviour.

## SWING-V01-115 - Extract selected-session replay internals

Status: complete

What changed:

- Added internal `_SelectedReplaySessionWindow` and `_SelectedSessionReplayContext` helpers in `src/swingmachine/replay.py`.
- Extracted selected-session signal/context preparation from `_execute_historical_manifest_replay`.
- Preserved the public `run-historical-replay` selected-session behaviour.
- Added focused coverage proving the helper still selects a single signal session and keeps replay artifacts compatible.

Files touched:

- `src/swingmachine/replay.py`
- `tests/test_replay_workflow.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Checks run:

- `.venv/bin/python -m pytest tests/test_replay_workflow.py::test_selected_replay_context_preserves_single_signal_session_semantics tests/test_replay_workflow.py::test_historical_manifest_replay_writes_deterministic_material_artifacts -q`

Result:

- 2 passed in 302.84s.

Assumptions made:

- Future scanner work should reuse selected-session preparation logic but must not alter the already-qualified selected-session command semantics.
- It is acceptable for scanner extraction helpers to remain private until the scanner command is implemented.

Blockers found:

- None for this refactor slice.

Follow-up work created:

- `SWING-V01-116`: Implement Tier 1 stateless multi-session scanner iterator and density artifact writer.

## SWING-V01-116 - Tier 1 stateless scanner iterator and density artifacts

Status: complete

What changed:

- Added `run_historical_scanner_replay` in `src/swingmachine/replay.py`.
- Added `write_historical_scanner_replay_artifacts` in `src/swingmachine/replay.py`.
- Scanner replay now iterates every eligible signal/next-session pair inside the manifest replay window.
- Scanner replay emits density-oriented local artifacts:
  - `scanner_replay_summary.json`
  - `scanner_session_results.json`
  - `scanner_decision_density.json`
  - `scanner_rejection_reasons.json`
  - `scanner_material_decisions.json`
  - `scanner_baseline_report_package.json`
  - `scanner_artifact_manifest.json`
- Added focused scanner artifact coverage.

Files touched:

- `src/swingmachine/replay.py`
- `tests/test_replay_workflow.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Checks run:

- `.venv/bin/python -m pytest tests/test_replay_workflow.py::test_historical_scanner_replay_writes_density_artifacts -q`

Result:

- 1 passed in 93.73s.

Assumptions made:

- Tier 1 scanner qualification should remain stateless and density-focused.
- Portfolio carry-forward and lifecycle simulation should be deferred to a later Tier 2 design.

Blockers found:

- None for the library scanner path.

Follow-up work created:

- `SWING-V01-117`: Add guarded offline scanner CLI.

## SWING-V01-117 - Guarded scanner replay CLI

Status: complete

What changed:

- Added `run-historical-scanner-replay` command in `src/swingmachine/runtime.py`.
- The command loads a manifest/config, runs the Tier 1 scanner replay, writes scanner artifacts, records local run metadata, and writes `workflow_summary.json`.
- Added focused CLI coverage.

Files touched:

- `src/swingmachine/runtime.py`
- `tests/test_runtime.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Checks run:

- `.venv/bin/python -m pytest tests/test_runtime.py::test_runtime_cli_runs_historical_scanner_replay_workflow -q`
- `.venv/bin/python -m ruff check src/swingmachine/replay.py src/swingmachine/runtime.py src/swingmachine/contracts.py tests/test_replay_workflow.py tests/test_runtime.py tests/test_contracts.py`

Result:

- Scanner CLI test: 1 passed in 152.81s.
- Ruff changed-file check: passed.

Assumptions made:

- Scanner CLI is an offline artifact-generation command and does not authorize live or paper runtime execution.
- Runtime metadata can be recorded to an output-dir-local SQLite DB without touching production state.

Blockers found:

- None for the guarded scanner CLI.

Follow-up work created:

- `SWING-V01-118`: Add scanner research/runtime-compatible parity report.
- `SWING-V01-119`: Run broad scanner-density qualification after parity exists.

## SWING-V01-118 - Scanner research/runtime-compatible parity

Status: complete

What changed:

- Added `compare_historical_scanner_replay_output_dirs` in `src/swingmachine/replay.py`.
- Added `write_historical_scanner_parity_report_json` in `src/swingmachine/replay.py`.
- Scanner parity compares:
  - `scanner_replay_summary.json`
  - `scanner_session_results.json`
  - `scanner_decision_density.json`
  - `scanner_rejection_reasons.json`
  - `scanner_material_decisions.json`
  - `scanner_baseline_report_package.json`
- Scanner parity ignores generated timestamps but compares material density/session/package fields.
- Added focused parity coverage.

Files touched:

- `src/swingmachine/replay.py`
- `tests/test_baseline_parity.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Checks run:

- `.venv/bin/python -m pytest tests/test_baseline_parity.py::test_scanner_parity_compares_density_artifacts_ignoring_timestamps -q`
- `.venv/bin/python -m ruff check src/swingmachine/replay.py tests/test_baseline_parity.py`

Result:

- Scanner parity test: 1 passed in 117.05s.
- Ruff check: passed.

Assumptions made:

- Generated timestamps should not fail scanner parity.
- Material scanner density, rejection, session, and package fields must match exactly.

Blockers found:

- None for scanner parity.

Follow-up work created:

- `SWING-V01-119`: Run broad scanner-density qualification.

## SWING-V01-119 - Broad scanner-density qualification

Status: complete

What changed:

- Attempted broad scanner-density qualification with the initial scanner implementation.
- Stopped the first long-running offline scanner process and optimized scanner density generation after it proved too slow for practical qualification.
- Added grouped session-row handling so scanner density does not repeatedly reconvert/filter the full detected frame for every session.
- Reran focused scanner tests and lint after optimization.
- Ran paired broad scanner-density qualification in research and runtime-compatible lanes.
- Generated scanner parity report and scanner qualification summary.
- Created `docs/swing_machine_v0_1_historical_broad_scanner_qualification.md`.

Files touched:

- `src/swingmachine/replay.py`
- `reports/swing_machine_v0_1/scanner_broad_research_20260506T155037Z/`
- `reports/swing_machine_v0_1/scanner_broad_runtime_20260506T155037Z/`
- `reports/swing_machine_v0_1/historical_broad_scanner_parity_report_20260506T155037Z.json`
- `reports/swing_machine_v0_1/historical_broad_scanner_qualification_summary_20260506T155037Z.json`
- `docs/swing_machine_v0_1_historical_broad_scanner_qualification.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Checks run:

- `.venv/bin/python -m ruff check src/swingmachine/replay.py`
- `.venv/bin/python -m pytest tests/test_replay_workflow.py::test_historical_scanner_replay_writes_density_artifacts tests/test_runtime.py::test_runtime_cli_runs_historical_scanner_replay_workflow tests/test_baseline_parity.py::test_scanner_parity_compares_density_artifacts_ignoring_timestamps -q`
- `run-historical-scanner-replay --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml --output-dir reports/swing_machine_v0_1/scanner_broad_research_20260506T155037Z`
- `run-historical-scanner-replay --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml --output-dir reports/swing_machine_v0_1/scanner_broad_runtime_20260506T155037Z`
- `compare_historical_scanner_replay_output_dirs` for broad scanner research/runtime outputs.

Result:

- Focused scanner/parity tests after optimization: 3 passed in 267.87s.
- Research scanner status: `PASS`.
- Runtime-compatible scanner status: `PASS`.
- Eligible signal sessions: 290.
- Processed signal sessions: 290.
- Skipped sessions: 0.
- Total decision traces: 4,640.
- Total candidates: 4,640.
- Total setups: 434.
- Total rejections: 4,206.
- Sessions with setups: 232.
- Sessions without setups: 58.
- Scanner parity passed with 0 differences.

Assumptions made:

- Tier 1 scanner density may count signals/risk/order plans from setup validity without constructing full selected-session runtime package context for every session.
- Tier 1 scanner density is sufficient to close the decision-density gap, but not sufficient for full portfolio/lifecycle simulation qualification.

Blockers found:

- Broad scanner runtime is still heavy because setup detection over the full broad panel is expensive.
- Tier 2 portfolio/lifecycle simulation remains unbuilt.

Follow-up work created:

- `SWING-V01-120`: Decide/design Tier 2 portfolio/lifecycle simulation qualification before any paper/live runtime move.

## SWING-V01-120 - Tier 2 portfolio/lifecycle qualification design

Status: complete

What changed:

- Created `docs/swing_machine_v0_1_tier2_portfolio_lifecycle_qualification_design.md`.
- Decided that Tier 2 portfolio/lifecycle simulation qualification is required before any paper/live runtime move.
- Added a thorough pre-paper test gate that explicitly allows long-running validation before paper trading.
- Added backlog items `SWING-V01-121` through `SWING-V01-130`.

Files touched:

- `docs/swing_machine_v0_1_tier2_portfolio_lifecycle_qualification_design.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Checks run:

- No code checks were required; this was a design/backlog activity.

Result:

- Tier 2 design complete.
- Paper trading remains blocked.
- Next implementation item: `SWING-V01-121`.

Assumptions made:

- Existing `backtest.py`, `lifecycle.py`, and `exits.py` are the correct foundation for Tier 2.
- Tier 1 scanner-density evidence is necessary but not sufficient for paper trading.
- Full pre-paper testing may legitimately run longer than 30 minutes and should be bounded by a longer timeout rather than avoided.

Blockers found:

- Tier 2 portfolio/lifecycle qualification is unimplemented.
- Full pre-paper test gate has not been run.
- Paper-trading approval/runbook does not exist yet.

Follow-up work created:

- `SWING-V01-121`: Add Tier 2 lifecycle replay contracts and artifact manifest models.
- `SWING-V01-122`: Add lifecycle artifact schema tests and fixture builders.
- `SWING-V01-123`: Build lifecycle qualification artifacts from existing `BacktestResult` outputs.
- `SWING-V01-124`: Add lifecycle reconciliation checks.
- `SWING-V01-125`: Add lifecycle research/runtime-compatible parity report.
- `SWING-V01-126`: Add guarded offline lifecycle replay CLI.
- `SWING-V01-127`: Run fixture lifecycle qualification and focused tests.
- `SWING-V01-128`: Run broad historical lifecycle qualification.
- `SWING-V01-129`: Run thorough pre-paper test gate.
- `SWING-V01-130`: Produce paper-trading review packet after Tier 2 and full pre-paper gate pass.


## SWING-V01-121 - Tier 2 lifecycle replay contracts and artifact manifest models

Status: complete

What changed:

- Added typed Tier 2 portfolio/lifecycle replay contracts.
- Added lifecycle session state, transition, position snapshot, pending order snapshot, exposure snapshot, reconciliation, replay summary, and artifact manifest models.
- Added an immediate consistency guard preventing `exit_pending_count` from exceeding `open_position_count` in a session state.
- Added focused contract tests for state capture, enum parsing, manifest completeness, and invalid session-state rejection.

Files touched:

- `src/swingmachine/contracts.py`
- `tests/test_contracts.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src/swingmachine/contracts.py tests/test_contracts.py`
- `.venv/bin/python -m pytest tests/test_contracts.py -q`

Test result:

- Initial ruff run found one style issue in the new validator return annotation; fixed.
- Final ruff result: passed.
- Final pytest result: 7 passed in 33.00s.

Assumptions made:

- Existing `SymbolLifecycleState`, `OrderIntentStatus`, `OrderSide`, `OrderType`, `PendingEntryCancelReason`, and `ReviewStatus` enums are sufficient for the first Tier 2 contract layer.
- Reconciliation logic itself belongs in follow-on implementation items, while the contract layer should only reject obvious impossible session state.

Blockers found:

- None for this activity.

Follow-up work created:

- Continue with `SWING-V01-122`: add lifecycle artifact schema tests and fixture builders.

## SWING-V01-122 - Lifecycle artifact schema tests and fixture builders

Status: complete

What changed:

- Added reusable Tier 2 lifecycle artifact fixture builders.
- Added fixture package coverage for lifecycle summary, session state, transitions, position snapshots, pending order snapshots, exposure snapshots, reconciliation, and artifact manifest.
- Added schema tests proving the fixture package is JSON-serializable and round-trips through the Tier 2 contracts.
- Added outcome coverage for pending-entry, active-position, exit-pending, and portfolio-gate-blocked lifecycle transitions.

Files touched:

- `tests/fixtures/lifecycle_artifacts.py`
- `tests/test_lifecycle_artifact_fixtures.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check tests/fixtures/lifecycle_artifacts.py tests/test_lifecycle_artifact_fixtures.py`
- `.venv/bin/python -m pytest tests/test_lifecycle_artifact_fixtures.py -q`

Test result:

- Initial ruff run found one import-order issue; fixed with `ruff --fix`.
- Final ruff result: passed.
- Final pytest result: 4 passed in 20.97s.

Assumptions made:

- Tier 2 replay/parity tests should reuse explicit fixture builders rather than embedding large lifecycle dictionaries in each test.
- The fixture package should cover schema shape and lifecycle states, not simulate full historical behaviour yet.

Blockers found:

- None for this activity.

Follow-up work created:

- Continue with `SWING-V01-123`: build lifecycle qualification artifacts from existing backtest outputs.

## SWING-V01-123 - Build lifecycle qualification artifacts from existing backtest outputs

Status: complete

What changed:

- Added an offline Tier 2 portfolio/lifecycle artifact package builder in `src/swingmachine/replay.py`.
- Added a writer that emits all required lifecycle artifact files from an existing `BacktestResult`.
- Converted backtest equity points into lifecycle session states and exposure snapshots.
- Converted backtest events into lifecycle transitions.
- Converted closed backtest trades into lifecycle position snapshots where available.
- Emitted empty pending-order snapshots when the current backtest result lacks enough order detail, and surfaced that limitation as a reconciliation warning rather than inventing hidden state.
- Added a replay workflow test proving the writer creates the expected artifact package from the fixture backtest result.

Files touched:

- `src/swingmachine/replay.py`
- `tests/test_replay_workflow.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src/swingmachine/replay.py tests/test_replay_workflow.py`
- `.venv/bin/python -m pytest tests/test_replay_workflow.py::test_historical_portfolio_lifecycle_artifacts_from_backtest_result -q`

Test result:

- Ruff result: passed.
- Focused pytest result: 1 passed in 151.22s.

Assumptions made:

- `BacktestResult` is the correct source for the first Tier 2 artifact conversion layer.
- The current backtest output does not expose enough pending-order or open-position internals to create fully detailed snapshots, so missing detail should be explicit reconciliation warning evidence.
- Full reconciliation semantics belong in `SWING-V01-124`; this item only creates the artifact package from existing outputs.

Blockers found:

- Pending-order detail is not available from `BacktestResult` today.
- Open-position detail is limited to closed trades and equity counts unless the backtest output model is expanded later.

Follow-up work created:

- Continue with `SWING-V01-124`: add lifecycle reconciliation checks.

## SWING-V01-124 - Lifecycle reconciliation checks

Status: complete

What changed:

- Added deterministic Tier 2 reconciliation checks for lifecycle artifact consistency.
- Added checks for session/exposure count consistency, transition/event count consistency, position/trade count consistency, exit-filled/trade consistency, entry fill/cancel sanity, and session/exposure value consistency.
- Kept missing pending-order/open-position detail as explicit warnings where the current `BacktestResult` cannot provide full state.

Files touched:

- `src/swingmachine/replay.py`
- `tests/test_replay_workflow.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Covered in the Tier 2 focused shard under `SWING-V01-127`.

Test result:

- Focused Tier 2 shard passed.

Assumptions made:

- Missing lifecycle detail should warn, not fail, until the backtest output model is expanded.

Blockers found:

- `BacktestResult` lacks pending-order and complete open-position state export.

Follow-up work created:

- `SWING-V01-131`: export full backtest lifecycle state for Tier 2 snapshots.

## SWING-V01-125 - Lifecycle research/runtime parity report

Status: complete

What changed:

- Added `compare_historical_portfolio_lifecycle_output_dirs`.
- Added `write_historical_portfolio_lifecycle_parity_report_json`.
- Added lifecycle parity normalization to ignore run timestamps, output paths, and run IDs while preserving material lifecycle fields.
- Added lifecycle parity tests.

Files touched:

- `src/swingmachine/replay.py`
- `tests/test_baseline_parity.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Covered in the Tier 2 focused shard under `SWING-V01-127`.

Test result:

- Focused Tier 2 shard passed.

Assumptions made:

- Research/runtime-compatible lifecycle artifacts should compare file-by-file using the same shape as scanner parity.

Blockers found:

- None for parity mechanics.

Follow-up work created:

- Use parity in broad lifecycle qualification.

## SWING-V01-126 - Guarded offline lifecycle replay CLI

Status: complete

What changed:

- Added Typer command `run-historical-portfolio-lifecycle-replay`.
- Added offline replay function `run_historical_portfolio_lifecycle_replay`.
- Command writes lifecycle artifacts and workflow summary without broker adapters or paper/live order submission.
- Added CLI workflow test.

Files touched:

- `src/swingmachine/replay.py`
- `src/swingmachine/runtime.py`
- `tests/test_runtime.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Covered in the Tier 2 focused shard under `SWING-V01-127`.

Test result:

- Focused Tier 2 shard passed.

Assumptions made:

- `WARN` lifecycle status should produce a successful CLI exit because it is not a reconciliation failure, but it remains a paper-trading blocker.

Blockers found:

- The local virtualenv does not currently expose `.venv/bin/swingmachine`; broad execution used the replay function directly.

Follow-up work created:

- `SWING-V01-132`: repair local console-script entry point.

## SWING-V01-127 - Fixture lifecycle qualification and focused Tier 2 test shard

Status: complete

What changed:

- Ran focused Tier 2 ruff and pytest shard after implementing reconciliation, parity, and CLI mechanics.

Files touched:

- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src/swingmachine/replay.py src/swingmachine/runtime.py tests/test_replay_workflow.py tests/test_baseline_parity.py tests/test_runtime.py tests/fixtures/lifecycle_artifacts.py tests/test_lifecycle_artifact_fixtures.py`
- `.venv/bin/python -m pytest tests/test_lifecycle_artifact_fixtures.py tests/test_baseline_parity.py::test_lifecycle_parity_compares_artifacts_ignoring_run_metadata tests/test_replay_workflow.py::test_historical_portfolio_lifecycle_artifacts_from_backtest_result tests/test_runtime.py::test_runtime_cli_runs_historical_portfolio_lifecycle_replay_workflow -q`

Test result:

- Ruff passed.
- Focused pytest: 7 passed in 161.67s.

Assumptions made:

- Fixture lifecycle qualification is sufficient before broad lifecycle execution.

Blockers found:

- None for fixture qualification.

Follow-up work created:

- Continue to broad lifecycle qualification.

## SWING-V01-128 - Broad historical lifecycle qualification

Status: complete with blocker outcome

What changed:

- Ran broad offline portfolio/lifecycle replay over the Trading212 Alpaca historical broad manifest.
- Produced research and runtime-compatible lifecycle artifact directories.
- Produced lifecycle parity report and qualification summary.

Files touched:

- `reports/swing_machine_v0_1/lifecycle_broad_research_20260506T204644Z/`
- `reports/swing_machine_v0_1/lifecycle_broad_runtime_20260506T204644Z/`
- `reports/swing_machine_v0_1/historical_broad_lifecycle_parity_report_20260506T204644Z.json`
- `reports/swing_machine_v0_1/historical_broad_lifecycle_qualification_summary_20260506T204644Z.json`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Broad research lifecycle replay.
- Broad runtime-compatible lifecycle replay.
- Lifecycle parity comparison.

Test result:

- Run ID: `20260506T204644Z`.
- Processed sessions: 634.
- Lifecycle transitions: 490.
- Research status: `WARN`.
- Runtime-compatible status: `WARN`.
- Parity passed: true.
- Parity difference count: 0.
- Reconciliation failures: none.
- Reconciliation warning: `PENDING_ORDER_DETAILS_NOT_AVAILABLE_FROM_BACKTEST_RESULT`.

Assumptions made:

- Direct replay-function execution is acceptable qualification evidence because the local console script is unavailable and the same CLI path is covered by tests.

Blockers found:

- Broad lifecycle status is `WARN`, not `PASS`, because pending-order detail is missing from `BacktestResult`.
- `.venv/bin/swingmachine` is unavailable in the local venv.

Follow-up work created:

- `SWING-V01-131`: export full backtest lifecycle state.
- `SWING-V01-132`: repair local console-script entry point.

## SWING-V01-129 - Thorough pre-paper test gate

Status: complete

What changed:

- Ran full pre-paper test gate with long timeout.
- Fixed one stale invalid-panel replay artifact assertion discovered by the first full pytest attempt.
- Re-ran the full gate to clean completion.

Files touched:

- `tests/test_replay_workflow.py`
- `reports/swing_machine_v0_1/pre_paper_test_gate_20260506T215621Z/`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src tests`
- `.venv/bin/python -m pytest -q`

Test result:

- Initial full pytest attempt: 245 passed, 1 failed in 737.72s.
- Focused stale assertion test after fix: 1 passed in 53.46s.
- Final full ruff: passed.
- Final full pytest: 246 passed in 692.26s.
- Final gate summary: `reports/swing_machine_v0_1/pre_paper_test_gate_20260506T215621Z/pre_paper_test_gate_summary.json`.

Assumptions made:

- The stale test assertion should match the existing implementation, which writes `baseline_report_package` and `freeze_readiness` even when replay validation fails.

Blockers found:

- Test gate passed, but paper trading remains blocked by Tier 2 lifecycle warning status.

Follow-up work created:

- Resolve lifecycle-detail warning before paper trading or obtain explicit operator acceptance of the warning.

## SWING-V01-130 - Paper-trading review packet and guarded approval gate

Status: complete

What changed:

- Created paper-trading review packet.
- Recorded that paper trading remains blocked despite full-suite pass because broad Tier 2 lifecycle qualification is `WARN`.

Files touched:

- `docs/swing_machine_v0_1_paper_trading_review_packet.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- No additional tests; review packet was produced after `SWING-V01-129` evidence.

Test result:

- Not applicable.

Assumptions made:

- A deterministic `WARN` with zero parity differences is strong engineering evidence but not enough to automatically start paper trading.

Blockers found:

- Paper trading remains blocked pending lifecycle-detail work or explicit operator acceptance.

Follow-up work created:

- `SWING-V01-131`: export full backtest lifecycle state for Tier 2 snapshots.
- `SWING-V01-132`: repair local console-script entry point.

## SWING-V01-131 - Export full backtest lifecycle state for Tier 2 snapshots

Status: complete

What changed:

- Added pending-order and position snapshot exports to `BacktestResult`.
- Captured pending entry lifecycle snapshots from the stateful backtest.
- Captured active/open position snapshots from the stateful backtest.
- Wired Tier 2 lifecycle artifacts to consume real backtest pending-order and position snapshots.
- Updated reconciliation logic so the previous missing-detail warning is no longer emitted when snapshots are present.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/backtest.py`
- `src/swingmachine/replay.py`
- `tests/test_replay_workflow.py`
- `tests/test_runtime.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src/swingmachine/backtest.py src/swingmachine/contracts.py src/swingmachine/replay.py tests/test_replay_workflow.py tests/test_runtime.py`
- `.venv/bin/python -m pytest tests/test_replay_workflow.py::test_historical_portfolio_lifecycle_artifacts_from_backtest_result tests/test_runtime.py::test_runtime_cli_runs_historical_portfolio_lifecycle_replay_workflow -q`

Test result:

- Ruff passed.
- Focused pytest: 2 passed in 226.88s.

Assumptions made:

- Pending order snapshots should include active-per-session, filled, and cancelled lifecycle evidence.
- Position snapshots should include active and exit-pending per-session evidence, while closed-trade snapshots continue to represent closed positions.

Blockers found:

- None after implementation.

Follow-up work created:

- Rerun broad lifecycle qualification and full pre-paper gate.

## SWING-V01-132 - Repair local console-script entry point

Status: complete

What changed:

- Installed the project into the repo-local virtualenv in editable mode with `.venv/bin/python -m pip install -e .`.
- Confirmed `.venv/bin/swingmachine` exists.
- Confirmed `.venv/bin/swingmachine --help` exposes `run-historical-portfolio-lifecycle-replay`.

Files touched:

- Repo-local virtualenv installation metadata.
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pip install -e .`
- `.venv/bin/swingmachine --help | head -n 50`

Test result:

- Editable install succeeded.
- Console script command list includes `run-historical-portfolio-lifecycle-replay`.

Assumptions made:

- Repo-local editable install is the right fix; no global Python/tooling changes were made.

Blockers found:

- None after implementation.

Follow-up work created:

- Use `.venv/bin/swingmachine` for broad lifecycle qualification.

## Post-SWING-V01-131 broad lifecycle qualification rerun

Status: complete

What changed:

- Re-ran broad historical portfolio/lifecycle qualification via `.venv/bin/swingmachine` after lifecycle-state export and console-script repair.

Files touched:

- `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T065158Z/`
- `reports/swing_machine_v0_1/lifecycle_broad_runtime_20260507T065158Z/`
- `reports/swing_machine_v0_1/historical_broad_lifecycle_parity_report_20260507T065158Z.json`
- `reports/swing_machine_v0_1/historical_broad_lifecycle_qualification_summary_20260507T065158Z.json`

Tests/checks run:

- `run-historical-portfolio-lifecycle-replay` research lane via `.venv/bin/swingmachine`.
- `run-historical-portfolio-lifecycle-replay` runtime-compatible lane via `.venv/bin/swingmachine`.
- Lifecycle parity comparison.

Test result:

- Run ID: `20260507T065158Z`.
- Overall status: `PASS`.
- Research status: `PASS`.
- Runtime-compatible status: `PASS`.
- Parity passed: true.
- Parity difference count: 0.
- Processed sessions: 634.
- Lifecycle transitions: 490.
- Pending-order snapshots: 712.
- Position snapshots: 1080.
- Reconciliation failures: none.
- Reconciliation warnings: none.

Assumptions made:

- The broad lifecycle qualification is now clean enough to support operator consideration of a paper-trading trial.

Blockers found:

- None in Tier 2 lifecycle qualification.

Follow-up work created:

- Prepare first controlled paper-trading runbook and preflight.

## Post-SWING-V01-131 full pre-paper test gate rerun

Status: complete

What changed:

- Re-ran the full pre-paper test gate after lifecycle-state export and console-script repair.

Files touched:

- `reports/swing_machine_v0_1/pre_paper_test_gate_20260507T072058Z/`
- `docs/swing_machine_v0_1_paper_trading_review_packet.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src tests`
- `.venv/bin/python -m pytest -q`

Test result:

- Full ruff: passed.
- Full pytest: 246 passed in 1364.99s.
- Summary: `reports/swing_machine_v0_1/pre_paper_test_gate_20260507T072058Z/pre_paper_test_gate_summary.json`.

Assumptions made:

- Full pre-paper engineering gate is now current after the latest code changes.

Blockers found:

- None in engineering gates.

Follow-up work created:

- `SWING-V01-133`: prepare first controlled paper-trading runbook and command preflight.

## SWING-V01-133 - First controlled paper-trading runbook and command preflight

Status: complete

What changed:

- Created the first controlled paper-trading runbook.
- Documented the exact mandatory shadow preview command.
- Documented the exact paper-mode command that requires explicit operator approval.
- Documented cycle input requirements, approval checklist, stop criteria, and post-run review requirements.
- Ran a non-executing dry-run safety preflight.

Files touched:

- `docs/swing_machine_v0_1_first_paper_runbook.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/first_paper_preflight_20260507T075235Z.json`

Tests/checks run:

- `.venv/bin/swingmachine run-cycle --help`
- `.venv/bin/swingmachine check-selected-period-dry-run-safety --output reports/swing_machine_v0_1/first_paper_preflight_20260507T075235Z.json`

Test result:

- `run-cycle --help` confirmed required inputs and `--mode [PAPER|SHADOW]`.
- Dry-run safety preflight passed.
- Preflight confirmed broker execution, live order actions, and paper order actions are disabled in the dry-run replay context.

Assumptions made:

- The first paper trial should be one reviewed `run-cycle` invocation, not an unattended scheduler.
- A mandatory shadow preview must be reviewed before any paper-mode execution.
- Paper execution requires a concrete reviewed `cycle_input.yaml`, not just this runbook.

Blockers found:

- No concrete first paper `cycle_input.yaml` exists yet.
- Paper execution remains blocked until operator approves the exact command.

Follow-up work created:

- `SWING-V01-134`: prepare reviewed first paper cycle input package.
- `SWING-V01-135`: run first paper shadow preview only.
- `SWING-V01-136`: execute first controlled paper cycle only after explicit approval.

## SWING-V01-137 - Consolidated mechanical readiness report generator

Status: complete

What changed:

- Added typed mechanical readiness contracts.
- Added typed lookahead audit and decision ledger contracts required by the mechanical-readiness solution design.
- Added `src/swingmachine/mechanical_readiness.py`.
- Added evidence discovery/loading for existing qualification artifacts.
- Added conservative `PASS/WARN/BLOCK` decision logic.
- Added markdown rendering for operator review.
- Added CLI command `build-mechanical-readiness-report`.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/mechanical_readiness.py`
- `src/swingmachine/runtime.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src/swingmachine/lookahead_audit.py src/swingmachine/mechanical_readiness.py src/swingmachine/runtime.py tests/test_lookahead_audit.py`
- `.venv/bin/python -m ruff check src/swingmachine/mechanical_readiness.py docs/swing_machine_v0_1_backlog.md`
- `.venv/bin/swingmachine build-mechanical-readiness-report --output reports/swing_machine_v0_1/mechanical_readiness_20260507T093551Z.json --markdown-output reports/swing_machine_v0_1/mechanical_readiness_20260507T093551Z.md --lookahead-audit reports/swing_machine_v0_1/lookahead_audit_20260507T093407Z.json`

Test result:

- Ruff checks passed.
- Mechanical readiness report generated successfully.
- Readiness remains `BLOCK`, as expected, because `SWING-V01-139`, `SWING-V01-140`, and `SWING-V01-141` are not yet implemented.

Assumptions made:

- The first readiness report should be conservative and block until `SWING-V01-138` through `SWING-V01-141` exist.
- Latest artifact discovery can initially use deterministic path sorting under `reports/swing_machine_v0_1/`.
- Future git/build staleness detection can be added later if needed.

Blockers found:

- Mechanical readiness is intentionally still blocked until lookahead audit, decision ledger, risk/portfolio adversarial coverage, and exit lifecycle adversarial coverage are implemented.

Follow-up work created:

- Continue with `SWING-V01-138` lookahead-bias and point-in-time feature audit.

## SWING-V01-138 - Explicit lookahead-bias and point-in-time feature audit

Status: complete

What changed:

- Added `src/swingmachine/lookahead_audit.py`.
- Added a typed lookahead audit builder for historical panel manifests.
- Added structural checks for feature windows, point-in-time symbol reference coverage, earnings timing fields, and source-file session ordering.
- Added JSON report writer.
- Added CLI command `build-lookahead-audit-report`.
- Integrated latest lookahead audit discovery into the mechanical readiness report.
- Updated mechanical readiness next-action mapping so a lookahead warning points to the new data/provenance backlog item rather than implying the audit code itself is missing.

Files touched:

- `src/swingmachine/lookahead_audit.py`
- `src/swingmachine/mechanical_readiness.py`
- `src/swingmachine/runtime.py`
- `tests/test_lookahead_audit.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src/swingmachine/lookahead_audit.py src/swingmachine/mechanical_readiness.py src/swingmachine/runtime.py tests/test_lookahead_audit.py`
- `.venv/bin/python -m pytest tests/test_lookahead_audit.py -q`
- `.venv/bin/swingmachine build-lookahead-audit-report --output reports/swing_machine_v0_1/lookahead_audit_20260507T093407Z.json`
- `.venv/bin/swingmachine build-mechanical-readiness-report --output reports/swing_machine_v0_1/mechanical_readiness_20260507T093551Z.json --markdown-output reports/swing_machine_v0_1/mechanical_readiness_20260507T093551Z.md --lookahead-audit reports/swing_machine_v0_1/lookahead_audit_20260507T093407Z.json`

Test result:

- Ruff passed.
- `tests/test_lookahead_audit.py`: 6 passed in 25.29s on the final focused run.
- Broad lookahead audit report emitted with status `WARN`, zero violations, and one warning: current broad manifest has no prepared feature panel to audit.
- Mechanical readiness report emitted with decision `BLOCK`; remaining blockers are `decision_ledger_complete`, `risk_portfolio_adversarial_tests_complete`, and `exit_lifecycle_adversarial_tests_complete`.

Assumptions made:

- Missing prepared feature evidence should not be treated as a clean `PASS`.
- The correct behavior is `WARN` until either the broad manifest declares a prepared feature panel or equivalent runtime feature-provenance evidence exists.
- Session-order checks must inspect declared source files directly because the contract loader may normalize or sort frames.

Blockers found:

- The current broad historical manifest does not include a prepared feature panel, so lookahead feature-window cleanliness is not fully evidenced from the manifest.

Follow-up work created:

- Added `SWING-V01-151` for prepared feature provenance evidence.

## SWING-V01-151 - Prepared feature provenance evidence for broad lookahead audit

Status: complete

What changed:

- Added a backlog item to clear the new lookahead audit warning by providing prepared feature or equivalent provenance evidence for the broad historical manifest.
- Added `src/swingmachine/prepared_features.py`.
- Added CLI command `build-prepared-feature-panel`.
- Generated a broad prepared feature panel from the real canonical/core feature/scoring path.
- Updated the broad Alpaca historical manifest with the prepared feature file, row count, checksum, and `feature_start_session`.
- Re-ran broad manifest validation, lookahead audit, and mechanical readiness.

Files touched:

- `src/swingmachine/prepared_features.py`
- `src/swingmachine/runtime.py`
- `tests/test_prepared_features.py`
- `data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml`
- `data/qualification_sources/trading212/alpaca/historical_broad_2024_06_to_2025_07_v0_1/features.parquet`
- `reports/swing_machine_v0_1/prepared_feature_provenance_20260507T094604Z.json`
- `reports/swing_machine_v0_1/lookahead_audit_20260507T094604Z.json`
- `reports/swing_machine_v0_1/mechanical_readiness_20260507T094604Z.json`
- `reports/swing_machine_v0_1/mechanical_readiness_20260507T094604Z.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src/swingmachine/prepared_features.py src/swingmachine/runtime.py`
- `.venv/bin/swingmachine build-prepared-feature-panel --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml --output data/qualification_sources/trading212/alpaca/historical_broad_2024_06_to_2025_07_v0_1/features.parquet --provenance-output reports/swing_machine_v0_1/prepared_feature_provenance_20260507T094604Z.json`
- `.venv/bin/swingmachine build-lookahead-audit-report --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml --output reports/swing_machine_v0_1/lookahead_audit_20260507T094604Z.json`
- `.venv/bin/swingmachine build-mechanical-readiness-report --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml --output reports/swing_machine_v0_1/mechanical_readiness_20260507T094604Z.json --markdown-output reports/swing_machine_v0_1/mechanical_readiness_20260507T094604Z.md --lookahead-audit reports/swing_machine_v0_1/lookahead_audit_20260507T094604Z.json`
- `.venv/bin/python -m ruff check src/swingmachine/prepared_features.py src/swingmachine/runtime.py tests/test_prepared_features.py`
- `.venv/bin/python -m pytest tests/test_prepared_features.py -q`

Test result:

- Ruff passed.
- Broad prepared feature export completed.
- Broad prepared feature rows: 4656.
- Broad feature symbols: 16.
- Broad feature start session: `2024-06-03`.
- Broad manifest validation status: `PASS`.
- Broad lookahead audit status: `PASS`, with zero violations and zero warnings.
- Mechanical readiness remains `BLOCK` only because `SWING-V01-139`, `SWING-V01-140`, and `SWING-V01-141` are still outstanding.
- `tests/test_prepared_features.py`: 1 passed in 18.36s.

Assumptions made:

- Empty historical earnings input is represented explicitly as `regular_closes_until_earnings_event = 9999`, with provenance policy `no_earnings_events_supplied_default_9999`.
- The prepared feature panel uses the existing canonical price, core feature, regime, breadth, and candidate scoring path rather than the synthetic replay proof feature builder.

Blockers found:

- Earnings calendar absence remains a data-quality limitation for future profitability interpretation, even though it is now explicit in provenance.

Follow-up work created:

- Consider adding a real historical earnings source before treating earnings-filter performance as fully representative.

## SWING-V01-139 - End-to-end decision ledger package

Status: in progress

What changed:

- Added `src/swingmachine/decision_ledger.py`.
- Added CLI command `build-decision-ledger-report`.
- Added a lifecycle-linked ledger report from portfolio lifecycle transitions, pending orders, positions, and optional scanner material decisions.
- Added auto-discovery of decision ledger artifacts in the mechanical readiness report.
- Built the broad decision ledger artifact for the latest broad lifecycle evidence.

Files touched:

- `src/swingmachine/decision_ledger.py`
- `src/swingmachine/mechanical_readiness.py`
- `src/swingmachine/runtime.py`
- `tests/test_decision_ledger.py`
- `reports/swing_machine_v0_1/decision_ledger_20260507T095648Z.json`
- `reports/swing_machine_v0_1/mechanical_readiness_20260507T095648Z.json`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src/swingmachine/decision_ledger.py src/swingmachine/mechanical_readiness.py src/swingmachine/runtime.py tests/test_decision_ledger.py`
- `.venv/bin/python -m pytest tests/test_decision_ledger.py -q`
- `.venv/bin/swingmachine build-decision-ledger-report --lifecycle-artifact-manifest reports/swing_machine_v0_1/lifecycle_broad_research_20260507T065158Z/portfolio_lifecycle_artifact_manifest.json --scanner-material-decisions reports/swing_machine_v0_1/scanner_broad_research_20260506T155037Z/scanner_material_decisions.json --output reports/swing_machine_v0_1/decision_ledger_20260507T095648Z.json`

Test result:

- Ruff passed.
- `tests/test_decision_ledger.py`: 1 passed in 10.13s.
- Broad decision ledger emitted with status `WARN`, 203 rows, and 1123 missing links.

Assumptions made:

- It is better to emit a truthful `WARN` ledger than to fabricate candidate, rejection, signal, risk-plan, or order-plan links that are not present in the current artifacts.

Blockers found:

- Current broad artifacts do not include per-symbol rejected candidate reason rows or stable signal/risk/order-plan IDs.

Follow-up work created:

- Added `SWING-V01-152` to enrich decision ledger source artifacts.

## SWING-V01-140 - Risk and portfolio adversarial fixture coverage

Status: complete

What changed:

- Added adversarial portfolio tests for explicit pending symbol conflicts, existing open-position conflicts, and existing heat plus new-risk cap breaches.
- Created PASS evidence artifact `reports/swing_machine_v0_1/risk_portfolio_adversarial_tests_20260507T100218Z.json`.
- Added risk/portfolio adversarial evidence auto-discovery to mechanical readiness.

Files touched:

- `tests/test_portfolio_manager.py`
- `src/swingmachine/mechanical_readiness.py`
- `reports/swing_machine_v0_1/risk_portfolio_adversarial_tests_20260507T100218Z.json`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check tests/test_portfolio_manager.py`
- `.venv/bin/python -m pytest tests/test_portfolio_manager.py -q`

Test result:

- Ruff passed.
- `tests/test_portfolio_manager.py`: 7 passed in 19.86s.

Assumptions made:

- The adversarial evidence artifact can be a small JSON report that records the focused tests and coverage until a broader QA evidence index exists.

Blockers found:

- None.

Follow-up work created:

- None.

## SWING-V01-141 - Exit lifecycle adversarial fixture coverage

Status: complete

What changed:

- Added adversarial exit tests for stop monotonicity, non-positive ATR fail-closed behavior, stacked time/earnings exits, and disabled trailing behavior.
- Created PASS evidence artifact `reports/swing_machine_v0_1/exit_lifecycle_adversarial_tests_20260507T100416Z.json`.
- Added exit lifecycle adversarial evidence auto-discovery to mechanical readiness.

Files touched:

- `tests/test_exits.py`
- `src/swingmachine/mechanical_readiness.py`
- `reports/swing_machine_v0_1/exit_lifecycle_adversarial_tests_20260507T100416Z.json`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m ruff check tests/test_exits.py src/swingmachine/mechanical_readiness.py`
- `.venv/bin/python -m pytest tests/test_exits.py -q`
- `.venv/bin/swingmachine build-mechanical-readiness-report --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml --output reports/swing_machine_v0_1/mechanical_readiness_20260507T100449Z.json --markdown-output reports/swing_machine_v0_1/mechanical_readiness_20260507T100449Z.md`

Test result:

- Ruff passed.
- `tests/test_exits.py`: 9 passed in 9.17s.
- Latest mechanical readiness report status is `WARN`, decision `WARN`, blockers `[]`, warnings `['decision_ledger_complete']`, next required actions `['SWING-V01-152']`.

Assumptions made:

- Mechanical readiness can move from `BLOCK` to `WARN` once risk/portfolio and exit adversarial evidence are present, even while decision ledger enrichment remains incomplete.

Blockers found:

- None for exit lifecycle adversarial coverage.

Follow-up work created:

- Continue with `SWING-V01-152` to clear the final mechanical-readiness warning.

## SWING-V01-152 - Enrich decision ledger source artifacts

Status: complete

What changed:

- Added per-symbol `material_decision_rows` to scanner session results and scanner material decision artifacts.
- Persisted candidate IDs, setup IDs, accepted/rejected decisions, reason codes, signal IDs, risk-plan IDs, and order-plan IDs where available.
- Added deterministic ID fallback for trace-only scanner paths.
- Updated decision ledger generation to consume enriched scanner rows.
- Added rejected-candidate ledger rows with reason codes.
- Updated decision ledger missing-link logic so accepted setups require order/lifecycle links, while rejected candidates require candidate/rejection evidence only.
- Fixed `score_candidates()` idempotency when prepared feature panels already contain stale regime/scoring context columns.
- Rebuilt broad scanner, lifecycle, decision-ledger, and mechanical-readiness evidence from the updated broad manifest.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/replay.py`
- `src/swingmachine/decision_ledger.py`
- `src/swingmachine/signals.py`
- `tests/test_decision_ledger.py`
- `tests/test_replay_workflow.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/scanner_broad_research_20260507T125344Z/`
- `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T125344Z/`
- `reports/swing_machine_v0_1/decision_ledger_20260507T125344Z.json`
- `reports/swing_machine_v0_1/mechanical_readiness_20260507T125344Z.json`
- `reports/swing_machine_v0_1/mechanical_readiness_20260507T125344Z.md`

Tests/checks run:

- `.venv/bin/python -m ruff check src/swingmachine/contracts.py src/swingmachine/replay.py src/swingmachine/decision_ledger.py tests/test_decision_ledger.py`
- `.venv/bin/python -m pytest tests/test_decision_ledger.py -q`
- `.venv/bin/python -m ruff check src/swingmachine/replay.py tests/test_replay_workflow.py`
- `.venv/bin/python -m pytest tests/test_replay_workflow.py::test_historical_scanner_replay_writes_density_artifacts -q`
- `.venv/bin/python -m ruff check src/swingmachine/signals.py src/swingmachine/replay.py tests/test_replay_workflow.py`
- `.venv/bin/python -m pytest tests/test_signals.py::test_score_candidates_uses_cross_sectional_thresholds tests/test_replay_workflow.py::test_historical_scanner_replay_writes_density_artifacts -q`
- `.venv/bin/swingmachine run-historical-scanner-replay --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml --output-dir reports/swing_machine_v0_1/scanner_broad_research_20260507T125344Z`
- `.venv/bin/swingmachine run-historical-portfolio-lifecycle-replay --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml --output-dir reports/swing_machine_v0_1/lifecycle_broad_research_20260507T125344Z`
- `.venv/bin/swingmachine build-decision-ledger-report --lifecycle-artifact-manifest reports/swing_machine_v0_1/lifecycle_broad_research_20260507T125344Z/portfolio_lifecycle_artifact_manifest.json --scanner-material-decisions reports/swing_machine_v0_1/scanner_broad_research_20260507T125344Z/scanner_material_decisions.json --output reports/swing_machine_v0_1/decision_ledger_20260507T125344Z.json`
- `.venv/bin/swingmachine build-mechanical-readiness-report --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml --output reports/swing_machine_v0_1/mechanical_readiness_20260507T125344Z.json --markdown-output reports/swing_machine_v0_1/mechanical_readiness_20260507T125344Z.md --decision-ledger reports/swing_machine_v0_1/decision_ledger_20260507T125344Z.json`

Test result:

- Ruff passed for touched code/tests.
- `tests/test_decision_ledger.py`: 1 passed in 12.61s.
- Scanner artifact focused test: 1 passed in 198.42s after enrichment.
- Signal plus scanner focused test: 2 passed in 184.18s after idempotency fix.
- Broad scanner replay: `PASS`, 290 processed sessions, 4640 candidates, 51 setups.
- Broad lifecycle replay: `PASS`, 291 processed sessions, 44 transitions.
- Broad decision ledger: `PASS`, 4606 rows, 0 missing links, 4589 rejected candidates.
- Latest mechanical readiness: `PASS`, blockers `[]`, warnings `[]`, next required actions `[]`.

Assumptions made:

- Deterministic fallback IDs are acceptable for trace-only scanner paths because they use the same stable ID shape as the baseline adapters.
- Prepared feature panels may carry stale regime/scoring columns; `score_candidates()` should always merge fresh explicit regime context and avoid suffix collisions.

Blockers found:

- The first broad replay attempt failed because prepared features already contained `entry_enabled`, causing pandas merge suffixes and a missing `entry_enabled` column. This was fixed in `src/swingmachine/signals.py`.

Follow-up work created:

- Mechanical readiness is now clean; next work can move to historical performance qualification rather than more mechanical-readiness blockers.

## SWING-V01-139 - End-to-end decision ledger package completion update

Status: complete

What changed:

- The decision ledger is now supported by enriched source artifacts from `SWING-V01-152`.
- The broad decision ledger now passes with zero missing links.

Files touched:

- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Covered by the `SWING-V01-152` evidence run.

Test result:

- Broad decision ledger status `PASS`.
- Mechanical readiness status `PASS`.

Assumptions made:

- The decision ledger package is mechanically complete enough to unblock historical performance qualification.

Blockers found:

- None.

Follow-up work created:

- Move to historical performance qualification backlog.

## SWING-V01-143 - Historical performance qualification metric contracts

Status: complete

What changed:

- Added typed historical performance contracts for equity curve points, drawdown records, trade metrics, benchmark comparison, concentration, cost sensitivity, breakdowns, summary, and full report payloads.
- Added JSON-serializable report output expectations through Pydantic models.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/performance.py`
- `tests/test_performance.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_performance.py`
- `.venv/bin/python -m ruff check src/swingmachine/performance.py tests/test_performance.py src/swingmachine/contracts.py`

Test result:

- `tests/test_performance.py`: 2 passed in 13.70s.
- Ruff passed for the changed performance, contract, and test files.

Assumptions made:

- The first performance contract should support lifecycle-derived equity evidence immediately while making trade-ledger and cost-data limitations explicit.

Blockers found:

- None for typed metric contracts.

Follow-up work created:

- Bind benchmark comparison to qualified manifest prices.
- Replace lifecycle-position proxy trade metrics with a full historical trade fill and cost ledger.

## SWING-V01-144 - Historical performance engine from backtest/lifecycle outputs

Status: complete

What changed:

- Added `build_historical_performance_report()` to consume existing portfolio lifecycle replay artifacts.
- Added deterministic equity curve, daily return, CAGR, volatility, Sharpe, Sortino, drawdown, concentration, calendar breakdown, proxy trade metric, and placeholder cost-sensitivity calculations.
- Added `write_historical_performance_report()` to emit summary, equity curve, drawdown, and full report JSON artifacts.
- Exposed the performance report builder and writer through package lazy exports.
- Generated the first offline historical performance packet from the latest broad research lifecycle replay.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/performance.py`
- `src/swingmachine/__init__.py`
- `tests/test_performance.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/historical_performance_20260507T144006Z/`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_performance.py`
- `.venv/bin/python -m ruff check src/swingmachine/performance.py tests/test_performance.py src/swingmachine/contracts.py`
- Offline report build from `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T125344Z`

Test result:

- `tests/test_performance.py`: 2 passed in 13.70s.
- Ruff passed for the changed performance, contract, and test files.
- Offline performance packet status: `WARN`.
- Offline packet summary: 291 sessions, 2024-06-03 to 2025-07-31, initial equity 100000.0, final equity 99912.83466253462, total return -0.0008716533746537802, max drawdown -0.010256833824413891, closed trade count 9.

Assumptions made:

- Existing lifecycle replay artifacts are acceptable for the first performance packet because they are offline, deterministic, and generated after mechanical readiness passed.
- Proxy trade metrics are acceptable only as interim engineering evidence, not as final investable performance evidence.

Blockers found:

- Final profitability qualification is still blocked by missing full trade fill/cost ledger attribution and manifest-bound benchmark comparison.

Follow-up work created:

- Complete `SWING-V01-145` by loading benchmark prices from the qualified historical manifest.
- Complete `SWING-V01-146` by replacing placeholder cost sensitivity with explicit friction scenarios.

## SWING-V01-145 - Benchmark comparison design and implementation

Status: complete

What changed:

- Added `load_benchmark_price_rows_from_manifest()` to load benchmark prices from the same qualified historical manifest used by the replay.
- Updated `build_historical_performance_report()` so benchmark comparison can be bound directly to a manifest and benchmark symbol.
- Added aligned benchmark total return, max drawdown, excess return, and daily return correlation to the performance report.
- Generated a benchmark-bound historical performance packet using `SPY` from the broad Alpaca manifest.

Files touched:

- `src/swingmachine/performance.py`
- `src/swingmachine/__init__.py`
- `tests/test_performance.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/historical_performance_benchmark_20260507T150417Z/`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_performance.py`
- `.venv/bin/python -m ruff check src/swingmachine/__init__.py src/swingmachine/performance.py tests/test_performance.py src/swingmachine/contracts.py`
- Offline benchmark-bound performance report build from `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T125344Z` and `data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml`

Test result:

- `tests/test_performance.py`: 3 passed in 189.29s.
- Ruff passed for the changed files.
- Benchmark-bound packet status: `WARN`.
- Strategy total return: -0.0008716533746537802.
- Strategy max drawdown: -0.010256833824413891.
- `SPY` benchmark total return: 0.216229330020961.
- `SPY` benchmark max drawdown: -0.18707893996325287.
- Strategy excess return versus `SPY`: -0.2171009833956148.
- Daily return correlation versus `SPY`: 0.15957494914598855.

Assumptions made:

- `split_adj_close` from the manifest feature file is the preferred benchmark price series, falling back to `raw_close` only if prepared features are unavailable.

Blockers found:

- None for manifest-bound benchmark comparison.

Follow-up work created:

- `SWING-V01-146` remains the next blocker because final profitability evidence still needs explicit friction and trade fill/cost attribution.

## SWING-V01-146 - Cost and slippage sensitivity performance runs

Status: complete

What changed:

- Added typed cost scenario results to the historical performance contract.
- Replaced the placeholder cost-sensitivity report with explicit additional-cost scenarios.
- Sensitivity scenarios now estimate turnover from CLOSED lifecycle position snapshots and show adjusted final equity and total return under 0, 5, 10, 25, and 50 bps additional cost assumptions.
- Regenerated the benchmark-bound performance packet with cost scenarios.
- Added `SWING-V01-153` to capture the remaining final-quality trade fill/cost ledger gap.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/performance.py`
- `tests/test_performance.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/historical_performance_costs_20260507T152240Z/`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_performance.py`
- `.venv/bin/python -m ruff check src/swingmachine/__init__.py src/swingmachine/performance.py tests/test_performance.py src/swingmachine/contracts.py`
- Offline benchmark-bound performance report build with cost scenarios from `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T125344Z`

Test result:

- `tests/test_performance.py`: 3 passed in 128.92s.
- Ruff passed for the changed files.
- Latest performance packet status: `WARN`.
- Estimated turnover: 87401.91038421661.
- Additional 0 bps final equity: 99912.83466253462, total return -0.0008716533746537802.
- Additional 5 bps final equity: 99869.13370734251, total return -0.0013086629265749439.
- Additional 10 bps final equity: 99825.4327521504, total return -0.0017456724784959965.
- Additional 25 bps final equity: 99694.32988657408, total return -0.0030567011342591544.
- Additional 50 bps final equity: 99475.82511061353, total return -0.0052417488938647505.

Assumptions made:

- Until the trade ledger exists, lifecycle CLOSED-position turnover is the safest available deterministic proxy for sensitivity.

Blockers found:

- Serious profitability qualification remains blocked by the absence of a first-class trade fill/cost ledger.

Follow-up work created:

- `SWING-V01-153` should be treated as the next highest-priority item before claiming historical profitability qualification is complete.

## SWING-V01-153 - Historical trade fill and cost ledger

Status: complete

What changed:

- Added a typed `HistoricalTradeLedgerRow` contract.
- Added `portfolio_lifecycle_trade_ledger.json` to lifecycle replay artifacts.
- Added trade ledger path support to the lifecycle artifact manifest.
- Updated the lifecycle baseline package to include trade ledger count.
- Updated historical performance reporting to prefer trade ledger metrics over CLOSED-position proxy metrics.
- Updated cost sensitivity to use trade-ledger turnover and transaction cost attribution when available.
- Regenerated broad lifecycle artifacts with a 9-row trade ledger.
- Generated a new benchmark-bound historical performance packet using the trade ledger.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/replay.py`
- `src/swingmachine/performance.py`
- `tests/test_replay_workflow.py`
- `tests/test_performance.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T155720Z/`
- `reports/swing_machine_v0_1/historical_performance_trade_ledger_20260507T161427Z/`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_performance.py tests/test_replay_workflow.py::test_historical_portfolio_lifecycle_artifacts_from_backtest_result`
- `.venv/bin/python -m ruff check src/swingmachine/contracts.py src/swingmachine/replay.py src/swingmachine/performance.py tests/test_performance.py tests/test_replay_workflow.py`
- `.venv/bin/swingmachine run-historical-portfolio-lifecycle-replay --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml --output-dir reports/swing_machine_v0_1/lifecycle_broad_research_20260507T155720Z`
- Offline benchmark-bound performance report build from `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T155720Z`

Test result:

- Focused tests: 5 passed in 206.82s.
- Ruff passed for changed code/tests.
- Broad lifecycle replay: `PASS`, 291 sessions, 44 transitions, 9 exit fills, 9 trade ledger rows, final equity 99912.83466253462.
- Trade-ledger performance packet: `PASS`.
- Trade-ledger performance summary: strategy total return -0.0008716533746537802, max drawdown -0.010256833824413891, closed trade count 9, net PnL -87.16533746537864, total transaction cost 43.710547800406715, estimated turnover 87401.91038421661.
- `SPY` benchmark total return: 0.216229330020961.
- Strategy excess return versus `SPY`: -0.2171009833956148.
- Performance warnings: none.

Assumptions made:

- Backtest trade objects are the correct initial ledger source because lifecycle artifacts are currently derived from the same stateful backtest output.
- Trade ledger IDs can be deterministic from symbol, setup ID, exit date, and sequence index.

Blockers found:

- None for trade-ledger artifact emission and performance preference.

Follow-up work created:

- The engine now has cleaner historical performance evidence, but the current broad result is not a successful model result: it is slightly negative and materially underperforms `SPY` over the same dates.
- Next useful work is `SWING-V01-147` performance breakdowns and `SWING-V01-149` qualification decision packaging so we can explain where the underperformance comes from before changing strategy behaviour.

## SWING-V01-147 - Regime, period, sector, and ranking-bucket performance breakdowns

Status: in progress

What changed:

- Added typed performance breakdown bucket metrics.
- Added calendar monthly and yearly return breakdowns to the performance packet.
- Added trade-ledger breakdowns by entry regime, exit reason, and sector.
- Added explicit missing-breakdown reporting for setup type and ranking bucket.
- Generated a refreshed broad performance packet with breakdowns.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/performance.py`
- `tests/test_performance.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/historical_performance_breakdowns_20260507T162140Z/`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_performance.py`
- `.venv/bin/python -m ruff check src/swingmachine/contracts.py src/swingmachine/performance.py tests/test_performance.py`
- Offline benchmark-bound performance report build from `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T155720Z`

Test result:

- `tests/test_performance.py`: 4 passed in 86.93s.
- Ruff passed for changed performance/contracts/tests.
- Latest performance breakdown packet status: `PASS`.
- Entry regime buckets: `RISK_ON`.
- Exit reason buckets: `INITIAL_STOP`, `TIME_EXIT`, `TRAIL_STOP`.
- Sector buckets: `UNKNOWN`.
- Missing breakdowns: `setup_type`, `ranking_bucket`.

Assumptions made:

- Trade-ledger fields are sufficient for first-pass regime, exit-reason, and sector breakdowns.

Blockers found:

- Setup-type and ranking-bucket attribution is not present on the trade ledger yet and needs a join to scanner or decision-ledger metadata.

Follow-up work created:

- Added `SWING-V01-154` for setup-type and ranking-bucket performance attribution.

## SWING-V01-154 - Setup-type and ranking-bucket performance attribution

Status: complete

What changed:

- Added `pattern_type` to scanner material decision rows for future scanner replay outputs.
- Added attribution loading for scanner material decisions and decision-ledger shaped payloads.
- Added setup-type and score/rank bucket breakdowns to historical performance reporting.
- Changed missing setup/ranking attribution behavior so unattributed trades are not hidden under `UNKNOWN`.
- Refreshed the broad scanner replay to emit pattern-type attribution.
- Generated a fully attributed historical performance packet with no missing breakdowns.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/replay.py`
- `src/swingmachine/performance.py`
- `tests/test_performance.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/scanner_broad_research_20260507T164230Z/`
- `reports/swing_machine_v0_1/historical_performance_attributed_20260507T183207Z/`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_performance.py tests/test_replay_workflow.py::test_historical_scanner_replay_writes_density_artifacts`
- `.venv/bin/python -m ruff check src/swingmachine/contracts.py src/swingmachine/replay.py src/swingmachine/performance.py tests/test_performance.py tests/test_replay_workflow.py`
- `.venv/bin/swingmachine run-historical-scanner-replay --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml --output-dir reports/swing_machine_v0_1/scanner_broad_research_20260507T164230Z`
- Offline attributed performance report build from `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T155720Z`

Test result:

- Focused tests: 6 passed in 98.58s.
- Ruff passed for changed code/tests.
- Refreshed broad scanner replay: `PASS`, 290 processed sessions, 4640 material rows, 51 accepted setups.
- Accepted scanner pattern types: `PULLBACK`, `TIGHT_BASE`.
- Attributed performance packet: `PASS`, 9 closed trades, no missing breakdowns.
- `PULLBACK`: 4 trades, 3 winners, win rate 0.75, net PnL 633.9945425211051.
- `TIGHT_BASE`: 5 trades, 0 winners, win rate 0.0, net PnL -721.1598799864837.
- `score_80_90`: 4 trades, net PnL -21.989348108914896.
- `score_95_100`: 5 trades, net PnL -65.17598935646383.

Assumptions made:

- Candidate score buckets are acceptable ranking-bucket attribution while cross-sectional rank remains unavailable in the scanner material rows.

Blockers found:

- None for setup-type and score-bucket attribution.

Follow-up work created:

- The key model insight from the current broad slice is that `TIGHT_BASE` is damaging performance while `PULLBACK` is positive, but this is diagnostic only; it should not trigger strategy changes until provider robustness and qualification decision packaging are complete.

## SWING-V01-148 - Provider robustness comparison: Alpaca versus Hugging Face

Status: complete

What changed:

- Added typed provider performance comparison contracts.
- Added provider performance comparison builder and JSON writer.
- Added package exports for provider comparison helpers.
- Ran matching Alpaca and Hugging Face `historical_contract_stability_window` lifecycle replays.
- Built provider-specific performance reports.
- Wrote a provider performance comparison report.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/performance.py`
- `src/swingmachine/__init__.py`
- `tests/test_performance.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/lifecycle_provider_alpaca_contract_20260507T184000Z/`
- `reports/swing_machine_v0_1/lifecycle_provider_huggingface_contract_20260507T184000Z/`
- `reports/swing_machine_v0_1/performance_provider_alpaca_contract_20260507T184000Z/`
- `reports/swing_machine_v0_1/performance_provider_huggingface_contract_20260507T184000Z/`
- `reports/swing_machine_v0_1/provider_performance_comparison_contract_20260507T184000Z.json`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_performance.py`
- `.venv/bin/python -m ruff check src/swingmachine/contracts.py src/swingmachine/performance.py src/swingmachine/__init__.py tests/test_performance.py`
- `.venv/bin/swingmachine run-historical-portfolio-lifecycle-replay --manifest data/qualification_manifests/trading212/alpaca/historical_contract_stability_window/manifest.yaml --output-dir reports/swing_machine_v0_1/lifecycle_provider_alpaca_contract_20260507T184000Z`
- `.venv/bin/swingmachine run-historical-portfolio-lifecycle-replay --manifest data/qualification_manifests/trading212/huggingface/historical_contract_stability_window/manifest.yaml --output-dir reports/swing_machine_v0_1/lifecycle_provider_huggingface_contract_20260507T184000Z`
- Offline provider performance report and comparison build.

Test result:

- `tests/test_performance.py`: 6 passed in 21.19s.
- Ruff passed for changed comparison code/tests.
- Alpaca provider performance: `PASS`, 320 sessions, total return 0.009500954669388717, max drawdown -0.03425744682673115, 42 closed trades, net PnL 572.1841820490914, benchmark return 0.2847243577915821, excess return -0.2752234031221934.
- Hugging Face provider performance: `PASS`, 320 sessions, total return 0.011817282120604844, max drawdown -0.03205187732325998, 42 closed trades, net PnL 806.6053178857372, benchmark return 0.26487600824610213, excess return -0.2530587261254973.
- Provider comparison: `PASS`, total return delta -0.002316327451216127, max drawdown delta -0.002205569503471172, closed trade count delta 0, net PnL delta -234.42113583664582, excess return delta -0.02216467699669611, blockers `[]`, warnings `[]`.

Assumptions made:

- The matching `historical_contract_stability_window` is the fair provider comparison window because there is no Hugging Face broad manifest matching the Alpaca broad 2024-06 to 2025-07 panel.

Blockers found:

- No provider comparison blocker for the matching contract window.
- Broad historical performance remains Alpaca-only until a matching broad Hugging Face manifest exists.

Follow-up work created:

- `SWING-V01-149` should now package the qualification decision: mechanically pass, provider contract robustness pass, profitability not proven, paper trading still blocked.

## SWING-V01-149 - Historical performance qualification report and decision packet

Status: complete

What changed:

- Created a historical performance qualification decision packet in JSON and Markdown.
- Combined mechanical readiness, broad scanner/lifecycle replay, broad attributed performance, and provider robustness evidence.
- Made the decision explicit: paper trading is blocked because profitability is not proven.

Files touched:

- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/historical_performance_qualification_20260507T184000Z.json`
- `reports/swing_machine_v0_1/historical_performance_qualification_20260507T184000Z.md`

Tests/checks run:

- Decision packet generated from existing passing evidence artifacts.

Test result:

- Decision: `BLOCK_PAPER_TRADING_PROFITABILITY_NOT_PROVEN`.
- Paper trading gate: `BLOCKED`.
- Serious full run gate: `HISTORICAL_OFFLINE_ONLY_ALLOWED`.
- Blockers: `broad_historical_total_return_not_positive`, `broad_historical_underperforms_benchmark`, `no_matching_huggingface_broad_manifest_for_broad_provider_validation`.

Assumptions made:

- Mechanical readiness and provider robustness are necessary but not sufficient; benchmark-relative historical performance must not be ignored.

Blockers found:

- The current baseline candidate is not profitable enough to promote.
- The broad Alpaca performance result is not matched by a broad Hugging Face manifest.

Follow-up work created:

- Next backlog should focus on diagnostic analysis and controlled strategy design, not paper trading.

## SWING-V01-155 - Broad historical underperformance diagnostic report

Status: complete

What changed:

- Generated a diagnostic report from the attributed broad performance summary, trade ledger, and scanner material-decision attribution.
- Broke performance down by setup type, score bucket, exit reason, symbol, largest winners, and largest losers.
- Added follow-on backlog items for TIGHT_BASE mechanical audit and controlled baseline revision design.

Files touched:

- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/historical_performance_diagnostics_20260507T190000Z.json`
- `reports/swing_machine_v0_1/historical_performance_diagnostics_20260507T190000Z.md`

Tests/checks run:

- Diagnostic report generated from existing passing artifacts:
- `reports/swing_machine_v0_1/historical_performance_attributed_20260507T183207Z/historical_performance_summary.json`
- `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T155720Z/portfolio_lifecycle_trade_ledger.json`
- `reports/swing_machine_v0_1/scanner_broad_research_20260507T164230Z/scanner_material_decisions.json`

Test result:

- Diagnostic status: `PASS`.
- TIGHT_BASE: 5 trades, 0 winners, net PnL -721.16.
- PULLBACK: 4 trades, 3 winners, net PnL 633.99.
- Broad excess return versus SPY: -0.2171.
- Score bucket `score_95_100` was still negative, so higher candidate score did not rescue this broad slice.

Assumptions made:

- This is diagnostic evidence only and does not justify changing strategy behavior without a revision design and controlled offline comparison.

Blockers found:

- Paper trading remains blocked.
- The current failed result appears concentrated in TIGHT_BASE behavior, but the exact mechanical cause is not yet audited.

Follow-up work created:

- `SWING-V01-156` TIGHT_BASE mechanical audit.
- `SWING-V01-157` controlled baseline revision design.

## SWING-V01-156 - TIGHT_BASE mechanical audit

Status: complete

What changed:

- Generated a TIGHT_BASE mechanical audit from the broad trade ledger, scanner attribution, prepared feature panel, and active strategy config.
- Joined each TIGHT_BASE closed trade to setup-date feature evidence.
- Recorded config thresholds, candidate scores, exit reasons, bars held, stops, and PnL.

Files touched:

- `reports/swing_machine_v0_1/tight_base_mechanical_audit_20260507T191500Z.json`
- `reports/swing_machine_v0_1/tight_base_mechanical_audit_20260507T191500Z.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Audit generated from existing validated broad artifacts and prepared features.

Test result:

- Audit status: `PASS`.
- Classification: `PERFORMANCE_WEAK_PATTERN_NO_MECHANICAL_BUG_PROVEN`.
- TIGHT_BASE trades: 5.
- Winners: 0.
- Net PnL: -721.1598799864837.
- Exit reasons: `INITIAL_STOP`: 1, `TRAIL_STOP`: 3, `TIME_EXIT`: 1.
- Symbols: `AAPL`, `JPM`, `META`, `AVGO`, `NVDA`.

Assumptions made:

- Accepted setup attribution plus setup-date feature snapshots are sufficient to classify this as no proven mechanical bug at this stage.

Blockers found:

- TIGHT_BASE remains unsuitable for promotion without revision or removal evidence.

Follow-up work created:

- Proceed with `SWING-V01-157` controlled baseline revision design.

## SWING-V01-157 - Controlled baseline revision design

Status: complete

What changed:

- Created a controlled revision design for the failed `swing_machine_v0_1` baseline candidate.
- Defined frozen baseline evidence.
- Defined candidate revision paths: PULLBACK-only, tightened TIGHT_BASE gates, or TIGHT_BASE disabled pending future research.
- Added explicit non-goals and paper-trading guardrails.
- Added follow-on backlog items for explicit profiles, offline comparisons, and revision qualification.

Files touched:

- `docs/swing_machine_v0_1_revision_design.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Design activity only; no tests required.

Test result:

- Revision design completed.

Assumptions made:

- PULLBACK-only is the first controlled hypothesis because diagnostics show positive broad PULLBACK contribution while TIGHT_BASE was negative across all five trades.

Blockers found:

- Paper trading remains blocked.
- Tightened TIGHT_BASE comparison should not proceed until a single defensible threshold hypothesis is chosen.

Follow-up work created:

- `SWING-V01-158` create explicit offline revision profiles.
- `SWING-V01-159` run PULLBACK-only broad offline comparison.
- `SWING-V01-160` run tightened TIGHT_BASE comparison only if justified.
- `SWING-V01-161` produce revision qualification decision packet.

## SWING-V01-158 - Create explicit offline revision profiles

Status: complete

What changed:

- Created an explicit PULLBACK-only offline revision strategy config.
- Created a matching profile alias using the same baseline alias contract.
- Added a focused profile-loading test.
- The frozen baseline config and alias remain unchanged.

Files touched:

- `config/swing_machine_v0_1_pullback_only_config.yaml`
- `config/swing_machine_v0_1_pullback_only_profile.yaml`
- `tests/test_baseline.py`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python - <<'PY' ... load_strategy_config/load_strategy_config_from_profile_alias ... PY`
- `.venv/bin/python -m pytest tests/test_baseline.py::test_pullback_only_revision_profile_alias_loads_explicit_config`
- `.venv/bin/python -m ruff check tests/test_baseline.py`

Test result:

- Profile config loads successfully.
- Alias config hash matches direct config hash.
- Pattern priority is exactly `PULLBACK`.
- Focused pytest: 1 passed in 15.38s.
- Ruff passed for `tests/test_baseline.py`.
- A mistakenly broad Ruff command included YAML files and failed because Ruff parsed YAML as Python; this was a validation-command mistake, not a profile-load failure.

Assumptions made:

- The PULLBACK-only profile should keep all non-setup behavior unchanged: ranking, risk, entries, exits, costs, lifecycle, and reporting.

Blockers found:

- None for explicit PULLBACK-only profile creation.

Follow-up work created:

- Proceed to `SWING-V01-159` broad offline comparison.

## SWING-V01-159 - Run PULLBACK-only broad offline comparison

Status: complete

What changed:

- Ran the full broad offline scanner and lifecycle replay for the explicit PULLBACK-only revision profile.
- Built an attributed historical performance report for the revision.
- Built a frozen-baseline versus PULLBACK-only comparison packet.

Files touched:

- `reports/swing_machine_v0_1/scanner_pullback_only_broad_20260507T194500Z/`
- `reports/swing_machine_v0_1/lifecycle_pullback_only_broad_20260507T194500Z/`
- `reports/swing_machine_v0_1/historical_performance_pullback_only_broad_20260507T194500Z/`
- `reports/swing_machine_v0_1/revision_comparison_pullback_only_20260507T194500Z.json`
- `reports/swing_machine_v0_1/revision_comparison_pullback_only_20260507T194500Z.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline scanner replay using `config/swing_machine_v0_1_pullback_only_config.yaml`.
- Offline lifecycle replay using `config/swing_machine_v0_1_pullback_only_config.yaml`.
- Attributed performance report build against the same Alpaca broad manifest and SPY benchmark.

Test result:

- Scanner replay: `PASS`, 290 sessions, 4640 candidates, 28 setups.
- Lifecycle replay: `PASS`, 291 sessions, 36 transitions, final equity 100044.84091964609.
- Performance report: `PASS`, total return 0.00044840919646094157, max drawdown -0.008284587318765801, 6 closed trades, net PnL 44.840919646073104.
- SPY benchmark return: 0.216229330020961.
- Excess return: -0.21578092082450007.
- Comparison decision: `REVISION_IMPROVES_BASELINE_BUT_DOES_NOT_PROVE_MARKET_EDGE`.

Assumptions made:

- PULLBACK-only should be compared as an offline revision, not promoted directly.

Blockers found:

- PULLBACK-only still materially underperforms SPY.
- PULLBACK-only has only 6 closed trades in the broad slice, limiting confidence.

Follow-up work created:

- Revision qualification packet created under `SWING-V01-161`.

## SWING-V01-160 - Run tightened TIGHT_BASE broad offline comparison

Status: blocked

What changed:

- No tightened TIGHT_BASE run was executed.

Files touched:

- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- None.

Test result:

- Blocked by design discipline, not tooling.

Assumptions made:

- The audit did not identify a specific mechanical threshold breach, so a tightened TIGHT_BASE run would currently be curve-fit risk.

Blockers found:

- No defensible single threshold hypothesis has been selected.

Follow-up work created:

- Revisit only if deeper feature-level research identifies a non-curve-fit TIGHT_BASE hypothesis.

## SWING-V01-161 - Revision qualification decision packet

Status: complete

What changed:

- Created a PULLBACK-only revision qualification decision packet.
- The packet blocks paper trading because the revision still underperforms SPY and has low trade count.

Files touched:

- `reports/swing_machine_v0_1/revision_qualification_pullback_only_20260507T194500Z.json`
- `reports/swing_machine_v0_1/revision_qualification_pullback_only_20260507T194500Z.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Decision packet generated from existing PULLBACK-only performance and comparison artifacts.

Test result:

- Decision: `BLOCK_PAPER_TRADING_REVISION_EDGE_NOT_PROVEN`.
- Paper trading gate: `BLOCKED`.
- Blockers: `revision_underperforms_benchmark`, `revision_trade_count_too_low_for_confidence`, `provider_contract_window_not_rerun_for_revision_because_broad_edge_not_proven`.

Assumptions made:

- A revision that improves the baseline but still underperforms benchmark is not enough to justify paper trading.

Blockers found:

- Strategy edge remains unproven.

Follow-up work created:

- Next useful work should move from qualification plumbing to deeper strategy research or data-scope expansion, not paper trading.

## SWING-V01-162 - Post-qualification research protocol

Status: complete

What changed:

- Created a post-qualification research plan after the frozen baseline and PULLBACK-only revision both failed paper-trading qualification.
- Added the next research/data tranche to the backlog.
- Kept paper/live execution explicitly blocked.

Files touched:

- `docs/swing_machine_v0_1_post_qualification_research_plan.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- None. Documentation/governance item only.

Test result:

- Not applicable.

Assumptions made:

- The next useful work is evidence-led alpha research and data validation, not paper trading.
- The frozen baseline should remain unchanged while revised candidates are researched.

Blockers found:

- Paper trading remains blocked because edge is not proven.

Follow-up work created:

- `SWING-V01-163` broad Hugging Face data feasibility and manifest decision.
- `SWING-V01-164` historical data quality and survivorship audit.
- `SWING-V01-165` feature outcome attribution dataset.
- `SWING-V01-166` accepted versus near-miss research report.
- `SWING-V01-167` benchmark-relative feature design.

## SWING-V01-163 - Broad Hugging Face data feasibility and manifest decision

Status: complete

What changed:

- Inspected existing Hugging Face qualification source windows non-destructively.
- Compared Hugging Face coverage to the Alpaca broad qualification panel.
- Created JSON and Markdown feasibility reports.
- Decided not to create a broad Hugging Face manifest from current source data because it would not be like-for-like.

Files touched:

- `reports/swing_machine_v0_1/huggingface_broad_manifest_feasibility_20260507T201000Z.json`
- `reports/swing_machine_v0_1/huggingface_broad_manifest_feasibility_20260507T201000Z.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Non-destructive CSV coverage scan using `.venv/bin/python`.

Test result:

- Alpaca broad source coverage: 2023-01-20 to 2025-07-31, 16 symbols, 634 sessions, 10,144 rows.
- Widest Hugging Face source coverage: 2024-04-22 to 2025-07-31, 16 symbols, 320 sessions, 5,113 rows.
- Hugging Face symbol overlap with Alpaca broad: 16/16.
- Hugging Face does not cover the Alpaca broad source start and is missing 314 Alpaca broad source sessions in the widest available window.

Assumptions made:

- Provider validation should not compare panels with different feature warm-up histories and call them equivalent.
- The existing matched historical contract window remains useful for shorter-window provider validation.

Blockers found:

- Matching broad Hugging Face provider validation is blocked until extended Hugging Face source data exists.

Follow-up work created:

- Continue with `SWING-V01-164` Alpaca broad historical data quality and survivorship audit.

## SWING-V01-164 - Historical data quality and survivorship audit

Status: complete

What changed:

- Added typed historical data-quality report models.
- Added a reusable offline data-quality audit module.
- Added JSON and Markdown report writers.
- Added focused unit tests for clean panels, zero-volume warnings, missing benchmark blockers, and report writers.
- Generated the broad Alpaca historical data-quality audit report.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/data_quality.py`
- `src/swingmachine/__init__.py`
- `tests/test_data_quality.py`
- `reports/swing_machine_v0_1/historical_data_quality_alpaca_broad_20260507T203000Z.json`
- `reports/swing_machine_v0_1/historical_data_quality_alpaca_broad_20260507T203000Z.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_data_quality.py`
- `.venv/bin/python -m ruff check src/swingmachine/data_quality.py src/swingmachine/contracts.py src/swingmachine/__init__.py tests/test_data_quality.py`
- Offline broad Alpaca data-quality report generation against `data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml`.

Test result:

- Focused pytest: 4 passed in 118.43s.
- Ruff: all checks passed.
- Broad Alpaca data-quality report status: `WARN`.
- Coverage check: `PASS`.
- Duplicate check: `PASS`.
- Price/volume check: `PASS`.
- Benchmark coverage check: `PASS`.
- Survivorship check: `WARN`.
- Issues: 0.
- Warnings: static symbol reference across a long panel, empty corporate actions across a long panel, and all symbols marked tradable for the full long panel.

Assumptions made:

- Static symbol membership and empty corporate-action evidence should warn rather than fail because they are research-validity risks, not immediate mechanical data blockers.
- The broad Alpaca panel remains usable for offline research, but profitability conclusions must note survivorship and corporate-action audit limitations.

Blockers found:

- No mechanical data-quality blockers were found in the broad Alpaca panel.
- Research-validity warnings remain and should be carried into historical performance interpretation.

Follow-up work created:

- Proceed to `SWING-V01-165` feature outcome attribution dataset.

## SWING-V01-165 - Feature outcome attribution dataset

Status: complete

What changed:

- Added typed feature/outcome attribution dataset contracts.
- Added an offline `feature_outcomes` module that joins scanner material decisions, lifecycle trade ledger outcomes, and historical forward close returns.
- Added JSON, CSV, and Markdown writers for the research dataset.
- Added focused unit tests for trade joins, forward returns, rejection reasons, and writer output.
- Generated the broad Alpaca feature/outcome attribution package.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/feature_outcomes.py`
- `src/swingmachine/__init__.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/feature_outcome_attribution_broad_20260507T210000Z/feature_outcome_attribution_dataset.json`
- `reports/swing_machine_v0_1/feature_outcome_attribution_broad_20260507T210000Z/feature_outcome_attribution_rows.csv`
- `reports/swing_machine_v0_1/feature_outcome_attribution_broad_20260507T210000Z/feature_outcome_attribution_summary.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_feature_outcomes.py`
- `.venv/bin/python -m ruff check src/swingmachine/feature_outcomes.py src/swingmachine/contracts.py src/swingmachine/__init__.py tests/test_feature_outcomes.py`
- Offline broad feature/outcome attribution package generation.

Test result:

- Focused pytest: 2 passed in 71.29s.
- Ruff: all checks passed.
- Broad attribution rows: 4,640.
- Accepted rows: 51.
- Rejected rows: 4,589.
- Traded rows: 9.
- Accepted rows with 5-session forward return: 51.
- Rejected rows with 5-session forward return: 4,509.

Assumptions made:

- Forward outcome fields use close-to-close returns from `next_session` for 1, 5, 10, and 20 available symbol sessions.
- Actual trade outcomes remain sourced from the lifecycle trade ledger rather than inferred from forward returns.

Blockers found:

- None for dataset generation.

Follow-up work created:

- Proceed to `SWING-V01-166` accepted versus near-miss research report.

## SWING-V01-166 - Accepted versus near-miss research report

Status: complete

What changed:

- Added typed accepted-versus-near-miss report contracts.
- Added a reusable report builder over the feature/outcome attribution dataset.
- Added score-bucket and rejection-reason outcome summaries.
- Added JSON and Markdown report writers.
- Added focused unit tests for report metrics and writer output.
- Generated the broad accepted-versus-near-miss research report.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/feature_outcomes.py`
- `src/swingmachine/__init__.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/accepted_vs_near_miss_broad_20260507T213000Z/accepted_vs_near_miss_report.json`
- `reports/swing_machine_v0_1/accepted_vs_near_miss_broad_20260507T213000Z/accepted_vs_near_miss_report.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_feature_outcomes.py`
- `.venv/bin/python -m ruff check src/swingmachine/feature_outcomes.py src/swingmachine/contracts.py src/swingmachine/__init__.py tests/test_feature_outcomes.py`
- Offline broad accepted-versus-near-miss report generation.

Test result:

- Focused pytest: 4 passed in 63.84s.
- Ruff: all checks passed.
- Broad report status: `PASS`.
- Broad report conclusion: `ACCEPTED_OUTPERFORMS_NEAR_MISS_ON_20D_FORWARD_RETURN`.
- Accepted rows: 51.
- Rejected rows: 4,589.
- Near-miss rows: 585.
- Accepted average 20-session forward close return: 0.010460303504078264.
- Near-miss average 20-session forward close return: 0.005414402055030734.
- Accepted positive 20-session forward-return rate: 0.5490196078431373.
- Near-miss positive 20-session forward-return rate: 0.49333333333333335.

Assumptions made:

- Near-miss rows are rejected rows with available `candidate_score_pct >= 0.75`.
- This is a research diagnostic, not a profile-promotion test.

Blockers found:

- Accepted candidates show some forward-return separation, but lifecycle performance still underperforms SPY. This does not unblock paper trading.

Follow-up work created:

- Proceed to `SWING-V01-167` benchmark-relative feature design.

## SWING-V01-167 - Benchmark-relative feature design

Status: complete

What changed:

- Created a benchmark-relative feature design document based on the failed qualification evidence and accepted-versus-near-miss research report.
- Defined the target feature groups, config approach, non-change boundaries, and research acceptance criteria.
- Added follow-on implementation backlog items for config, feature formulas, excess-return attribution, regime bucket reports, and controlled candidate selection.

Files touched:

- `docs/swing_machine_v0_1_benchmark_relative_feature_design.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- None. Design/governance item only.

Test result:

- Not applicable.

Assumptions made:

- Benchmark-relative features should be computed and reported before they are allowed to change scoring or gating behavior.
- The frozen baseline and PULLBACK-only revision remain unchanged.

Blockers found:

- Paper trading remains blocked because lifecycle performance still does not prove benchmark-relative edge.

Follow-up work created:

- `SWING-V01-168` benchmark-relative config contract.
- `SWING-V01-169` benchmark-relative feature formulas.
- `SWING-V01-170` feature/outcome excess-return attribution.
- `SWING-V01-171` benchmark/regime outcome bucket report.
- `SWING-V01-172` controlled benchmark-relative candidate selection packet.

## SWING-V01-168 - Benchmark-relative config contract

Status: complete

What changed:

- Added an explicit typed `benchmark_relative_features` config section.
- Added benchmark-relative feature config to the frozen baseline config and the PULLBACK-only offline revision config.
- Kept `influence_strategy_behavior: false` in both configs so scoring/gating behavior remains unchanged.
- Added focused config assertions.

Files touched:

- `src/swingmachine/config.py`
- `swing_trading_bot_config_template_v2.yaml`
- `config/swing_machine_v0_1_pullback_only_config.yaml`
- `tests/test_config.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_config.py tests/test_baseline.py::test_pullback_only_revision_profile_alias_loads_explicit_config`
- `.venv/bin/python -m ruff check src/swingmachine/config.py tests/test_config.py`

Test result:

- Focused pytest: 3 passed in 3.44s.
- Ruff: all checks passed.

Assumptions made:

- Benchmark-relative fields should be explicitly configured even while behavior influence remains disabled.
- `compute: true` means research feature computation is allowed; it does not mean scoring or gating can use the features.

Blockers found:

- None.

Follow-up work created:

- Proceed to `SWING-V01-169` benchmark-relative feature formulas.

## SWING-V01-169 - Benchmark-relative feature formulas

Status: complete

What changed:

- Added multi-window benchmark-relative strength fields to `compute_core_features`.
- Added relative-strength acceleration fields.
- Added benchmark-relative drawdown and rebound fields.
- Preserved existing scoring behavior; no signal, gate, or profile behavior now consumes the new fields.
- Added deterministic formula assertions.

Files touched:

- `src/swingmachine/features.py`
- `tests/test_features.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_features.py tests/test_signals.py::test_score_candidates_uses_cross_sectional_thresholds`
- `.venv/bin/python -m ruff check src/swingmachine/features.py tests/test_features.py`

Test result:

- Focused pytest: 2 passed in 19.48s.
- Ruff: all checks passed.

Assumptions made:

- Benchmark-relative formulas should compute from the same aligned benchmark total-return close series used by existing `rs_vs_benchmark_126`.
- Feature computation is allowed by config, but strategy behavior influence remains disabled.

Blockers found:

- None.

Follow-up work created:

- Proceed to `SWING-V01-170` feature/outcome excess-return attribution.

## SWING-V01-170 - Feature/outcome excess-return attribution

Status: complete

What changed:

- Extended feature/outcome attribution rows with benchmark forward close returns and forward excess returns.
- Extended attribution dataset summaries with the benchmark symbol.
- Extended accepted-versus-near-miss report metrics to include average, median, and positive-rate excess returns.
- Updated report conclusions to prefer 20-session excess-return evidence when available.
- Regenerated the broad attribution and accepted-versus-near-miss reports with SPY-relative outcomes.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/feature_outcomes.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/feature_outcome_attribution_broad_excess_20260507T220000Z/feature_outcome_attribution_dataset.json`
- `reports/swing_machine_v0_1/feature_outcome_attribution_broad_excess_20260507T220000Z/feature_outcome_attribution_rows.csv`
- `reports/swing_machine_v0_1/feature_outcome_attribution_broad_excess_20260507T220000Z/feature_outcome_attribution_summary.md`
- `reports/swing_machine_v0_1/accepted_vs_near_miss_broad_excess_20260507T220000Z/accepted_vs_near_miss_report.json`
- `reports/swing_machine_v0_1/accepted_vs_near_miss_broad_excess_20260507T220000Z/accepted_vs_near_miss_report.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_feature_outcomes.py`
- `.venv/bin/python -m ruff check src/swingmachine/feature_outcomes.py src/swingmachine/contracts.py tests/test_feature_outcomes.py`
- Offline broad SPY-relative attribution and accepted-versus-near-miss report generation.

Test result:

- Focused pytest: 4 passed in 58.84s.
- Ruff: all checks passed.
- Broad excess attribution rows: 4,640.
- Accepted rows: 51.
- Rejected rows: 4,589.
- Near-miss rows: 585.
- Report conclusion: `NO_CLEAR_ACCEPTED_EDGE_OVER_NEAR_MISS_ON_20D_EXCESS_RETURN`.
- Accepted average 20-session excess return: -0.015076109274356514.
- Near-miss average 20-session excess return: -0.002207401081832543.
- Accepted positive 20-session excess-return rate: 0.4117647058823529.
- Near-miss positive 20-session excess-return rate: 0.4533333333333333.

Assumptions made:

- SPY is the benchmark for excess-return attribution unless explicitly configured otherwise.
- Excess-return evidence is more relevant than raw forward return when judging market edge.

Blockers found:

- Accepted candidates do not show a clear SPY-relative edge over near-misses on 20-session forward excess return.
- This reinforces the paper-trading block.

Follow-up work created:

- `SWING-V01-171` should not promote a revision unless regime/relative-strength buckets reveal defensible excess-return separation.

## SWING-V01-171 - Benchmark/regime outcome bucket report

Status: blocked

What changed:

- No benchmark/regime bucket report was generated from the current attribution package.
- The blocker is documented and follow-up propagation tasks were added.

Files touched:

- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- None.

Test result:

- Blocked before implementation.

Assumptions made:

- A legitimate benchmark/regime bucket report requires attribution rows to include benchmark-relative feature snapshot fields or regime context.

Blockers found:

- Current attribution rows include raw forward returns and SPY excess returns, but not the new benchmark-relative feature snapshot fields or regime bucket fields.

Follow-up work created:

- `SWING-V01-173` research-only benchmark-relative prepared feature artifact.
- `SWING-V01-174` propagate feature snapshots into attribution rows.
- `SWING-V01-175` rebuild broad attribution with benchmark-relative feature snapshots.
- `SWING-V01-176` benchmark/regime bucket report rerun.

## SWING-V01-172 - Controlled benchmark-relative candidate selection packet

Status: blocked

What changed:

- No candidate-selection packet was produced.

Files touched:

- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- None.

Test result:

- Blocked by missing benchmark/regime bucket evidence.

Assumptions made:

- Candidate selection must wait for bucketed excess-return evidence to avoid threshold chasing.

Blockers found:

- `SWING-V01-171` is blocked until enriched attribution rows exist.

Follow-up work created:

- Continue with `SWING-V01-173`.

## SWING-V01-173 - Research-only benchmark-relative prepared feature artifact

Status: complete

What changed:

- Generated a research-only prepared feature artifact from the broad Alpaca manifest using the updated benchmark-relative feature formulas.
- Wrote the artifact under `reports/` and left the baseline manifest unchanged.
- Confirmed the expected benchmark-relative fields are present.

Files touched:

- `reports/swing_machine_v0_1/prepared_features_broad_benchmark_relative_20260507T223000Z/features.parquet`
- `reports/swing_machine_v0_1/prepared_features_broad_benchmark_relative_20260507T223000Z/provenance.json`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Research-only prepared feature generation with `update_manifest=False`.
- Field presence check for benchmark-relative columns.

Test result:

- Row count: 4,656.
- Symbol count: 16.
- Start session: 2024-06-03.
- End session: 2025-07-31.
- Missing required benchmark-relative columns: none.
- Updated manifest path: none.
- Manifest validation status: none because no manifest mutation was performed.

Assumptions made:

- Generating a research-only artifact under `reports/` is safe and does not alter baseline manifest governance.

Blockers found:

- None for artifact generation.

Follow-up work created:

- Proceed to `SWING-V01-174` feature snapshot propagation into attribution rows.

## SWING-V01-174 - Propagate feature snapshots into attribution rows

Status: complete

What changed:

- Extended feature/outcome attribution rows with an optional selected feature snapshot map.
- Added optional feature snapshot source path and field list to attribution summaries.
- Added CSV flattening for selected feature fields.
- Added tests for feature snapshot joins.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/feature_outcomes.py`
- `tests/test_feature_outcomes.py`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_feature_outcomes.py`
- `.venv/bin/python -m ruff check src/swingmachine/feature_outcomes.py src/swingmachine/contracts.py tests/test_feature_outcomes.py`

Test result:

- Focused pytest: 4 passed in 14.16s.
- Ruff: all checks passed.

Assumptions made:

- Feature snapshot propagation should be optional and research-only.
- Attribution rows should remain valid without a feature snapshot source.

Blockers found:

- None.

Follow-up work created:

- Proceed to `SWING-V01-175` broad enriched attribution rebuild.

## SWING-V01-175 - Rebuild broad attribution with benchmark-relative feature snapshots

Status: complete

What changed:

- Rebuilt the broad feature/outcome attribution dataset with SPY excess returns and selected benchmark-relative feature snapshot fields.

Files touched:

- `reports/swing_machine_v0_1/feature_outcome_attribution_broad_feature_snapshot_20260507T224500Z/feature_outcome_attribution_dataset.json`
- `reports/swing_machine_v0_1/feature_outcome_attribution_broad_feature_snapshot_20260507T224500Z/feature_outcome_attribution_rows.csv`
- `reports/swing_machine_v0_1/feature_outcome_attribution_broad_feature_snapshot_20260507T224500Z/feature_outcome_attribution_summary.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline broad attribution rebuild using the research-only prepared feature artifact.

Test result:

- Row count: 4,640.
- Accepted rows: 51.
- Rejected rows: 4,589.
- Traded rows: 9.
- Rows with feature snapshot: 4,640.
- Warnings: none.

Assumptions made:

- The research-only prepared feature artifact is the correct feature source for benchmark-relative bucket analysis.

Blockers found:

- None.

Follow-up work created:

- Proceed to `SWING-V01-176` benchmark/regime bucket report rerun.

## SWING-V01-176 - Benchmark/regime bucket report rerun

Status: complete

What changed:

- Added typed feature snapshot bucket report contracts.
- Added reusable bucket report builder and writer over enriched attribution rows.
- Added tests for feature bucket grouping and writer output.
- Generated the broad feature snapshot bucket report.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/feature_outcomes.py`
- `src/swingmachine/__init__.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/feature_snapshot_bucket_broad_20260507T230000Z/feature_snapshot_bucket_report.json`
- `reports/swing_machine_v0_1/feature_snapshot_bucket_broad_20260507T230000Z/feature_snapshot_bucket_report.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_feature_outcomes.py`
- `.venv/bin/python -m ruff check src/swingmachine/feature_outcomes.py src/swingmachine/contracts.py src/swingmachine/__init__.py tests/test_feature_outcomes.py`
- Offline broad feature snapshot bucket report generation.

Test result:

- Focused pytest: 6 passed in 14.05s.
- Ruff: all checks passed.
- Bucket report status: `PASS`.
- Bucket report conclusion: `POTENTIAL_POSITIVE_EXCESS_BUCKET_REQUIRES_SELECTION_PACKET`.
- Rows: 4,640.
- Warnings: none.

Assumptions made:

- Bucket report evidence is diagnostic and does not by itself qualify a strategy profile.

Blockers found:

- None for bucket report generation.

Follow-up work created:

- Controlled candidate selection packet completed under `SWING-V01-172`.

## SWING-V01-172 - Controlled benchmark-relative candidate selection packet

Status: complete

What changed:

- Created a conservative benchmark-relative candidate selection packet.
- No new revision profile was selected.
- Paper trading remains blocked.

Files touched:

- `reports/swing_machine_v0_1/benchmark_relative_candidate_selection_20260507T231500Z.json`
- `reports/swing_machine_v0_1/benchmark_relative_candidate_selection_20260507T231500Z.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Decision packet assembled from generated research artifacts.

Test result:

- Decision: `NO_BENCHMARK_RELATIVE_REVISION_SELECTED_YET`.
- Paper trading gate: `BLOCKED`.
- Serious full run gate: `HISTORICAL_OFFLINE_ONLY_ALLOWED`.

Assumptions made:

- Overall SPY-relative accepted-vs-near-miss failure outweighs diagnostic bucket positives for profile selection.

Blockers found:

- No profile revision is justified yet.

Follow-up work created:

- Build accepted-only and traded-only bucket diagnostics before selecting any revised profile.

## Backlog update - accepted/traded bucket diagnostics

Status: complete

What changed:

- Added `SWING-V01-177` and `SWING-V01-178` to keep the next research pass explicit and governed.

Files touched:

- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- None. Backlog update only.

Test result:

- Not applicable.

Assumptions made:

- The next useful task is accepted-only and traded-only bucket diagnostics, not another profile variant.

Blockers found:

- None.

Follow-up work created:

- `SWING-V01-177` accepted-only and traded-only bucket diagnostics.
- `SWING-V01-178` controlled benchmark-relative hypothesis selection rerun.

## Overnight backlog expansion

Status: complete

What changed:

- Created an explicit overnight queue document.
- Expanded the autonomous backlog from `SWING-V01-179` through `SWING-V01-192`.
- Kept all new overnight work offline and research/governance focused.

Files touched:

- `docs/swing_machine_v0_1_overnight_queue.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- None. Backlog and queue expansion only.

Test result:

- Not applicable.

Assumptions made:

- Overnight work should prioritize diagnostics, robustness checks, provider stability, artifact indexing, and blocker refreshes before any new profile variant.
- Paper/live execution remains prohibited.

Blockers found:

- None for backlog expansion.

Follow-up work created:

- `SWING-V01-179` through `SWING-V01-192`.

## Working backlog solution design

Status: complete

What changed:

- Created an implementation-ready solution design and acceptance criteria document for open backlog items `SWING-V01-177` through `SWING-V01-192`.

Files touched:

- `docs/swing_machine_v0_1_working_backlog_solution_design.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- None. Documentation/governance item only.

Test result:

- Not applicable.

Assumptions made:

- The current working backlog is the open overnight tranche from `SWING-V01-177` through `SWING-V01-192`.
- All backlog execution remains offline until a later qualification packet explicitly changes the gate.

Blockers found:

- None.

Follow-up work created:

- Continue straight into `SWING-V01-177` implementation.

## SWING-V01-177 - Accepted-only and traded-only bucket diagnostics

Status: complete

What changed:

- Extended bucket metrics with accepted-only and traded-only subpopulation metrics.
- Added accepted-only raw/excess forward-return summaries.
- Added traded-only lifecycle metrics including trade count, win count, net PnL, average net PnL, average net return, and median net return.
- Updated feature bucket Markdown to show accepted-only and traded-only evidence separately.
- Regenerated the broad feature snapshot bucket report with subpopulation metrics.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/feature_outcomes.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/feature_snapshot_bucket_broad_subpop_20260508T000500Z/feature_snapshot_bucket_report.json`
- `reports/swing_machine_v0_1/feature_snapshot_bucket_broad_subpop_20260508T000500Z/feature_snapshot_bucket_report.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_feature_outcomes.py`
- `.venv/bin/python -m ruff check src/swingmachine/feature_outcomes.py src/swingmachine/contracts.py src/swingmachine/__init__.py tests/test_feature_outcomes.py`
- Offline broad feature snapshot bucket report regeneration.

Test result:

- Focused pytest: 6 passed in 141.23s.
- Ruff: all checks passed.
- Bucket report status: `PASS`.
- Report conclusion: `POTENTIAL_POSITIVE_EXCESS_BUCKET_REQUIRES_SELECTION_PACKET`.
- Accepted-only best 20-session excess-return buckets with at least five accepted rows were still negative.
- Some traded-only buckets had positive net PnL, but samples are small and not sufficient for profile promotion.

Assumptions made:

- Accepted-only excess-return evidence is more important than traded-only small-sample PnL for selecting a new profile.
- Traded-only positives should become hypotheses, not profile changes.

Blockers found:

- No benchmark-relative profile can be selected solely from `SWING-V01-177` evidence.

Follow-up work created:

- Proceed to `SWING-V01-178` controlled benchmark-relative hypothesis selection rerun.

## SWING-V01-178 - Controlled benchmark-relative hypothesis selection rerun

Status: complete

What changed:

- Created a controlled benchmark-relative hypothesis selection rerun after accepted-only and traded-only bucket diagnostics.
- No new revision profile was selected.
- Paper trading remains blocked.

Files touched:

- `reports/swing_machine_v0_1/benchmark_relative_hypothesis_selection_rerun_20260508T001500Z.json`
- `reports/swing_machine_v0_1/benchmark_relative_hypothesis_selection_rerun_20260508T001500Z.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Decision packet assembled from latest research artifacts.

Test result:

- Decision: `NO_REVISION_SELECTED_ACCEPTED_EXCESS_EVIDENCE_WEAK`.
- Paper trading gate: `BLOCKED`.
- Serious full run gate: `HISTORICAL_OFFLINE_ONLY_ALLOWED`.

Assumptions made:

- Accepted-only SPY-excess evidence should dominate small-sample traded-only positives when deciding whether to create a profile revision.

Blockers found:

- Accepted-only excess-return buckets are not positive.
- Traded-only positive buckets have small samples.
- Provider-matched confirmation is missing.
- Minimum-sample guardrails have not been applied yet.

Follow-up work created:

- Continue with `SWING-V01-179`, `SWING-V01-180`, and `SWING-V01-181` before any new profile is selected.

## SWING-V01-179 - Feature bucket robustness and minimum-sample guardrails

Status: complete

What changed:

- Added sample guardrails to feature bucket reports.
- Added per-bucket sample grades: `ROBUST`, `EXPLORATORY`, and `INSUFFICIENT`.
- Added explicit guardrail thresholds to the report model.
- Updated Markdown output to show sample grade.
- Regenerated the broad guarded bucket report.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/feature_outcomes.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/feature_snapshot_bucket_broad_guarded_20260508T003000Z/feature_snapshot_bucket_report.json`
- `reports/swing_machine_v0_1/feature_snapshot_bucket_broad_guarded_20260508T003000Z/feature_snapshot_bucket_report.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_feature_outcomes.py`
- `.venv/bin/python -m ruff check src/swingmachine/feature_outcomes.py src/swingmachine/contracts.py src/swingmachine/__init__.py tests/test_feature_outcomes.py`
- Offline broad guarded bucket report generation.

Test result:

- Focused pytest: 6 passed in 92.86s.
- Ruff: all checks passed.
- Sample guardrails: robust requires at least 30 accepted rows and 5 traded rows; exploratory requires at least 10 accepted rows or 3 traded rows.
- Broad bucket grades: 4 robust, 7 exploratory, 9 insufficient.
- Robust buckets with positive accepted-only 20-session excess return: 0.

Assumptions made:

- Positive traded-only buckets should not override negative accepted-only evidence without robust sample support.

Blockers found:

- No robust positive accepted-only excess-return bucket was found.

Follow-up work created:

- Proceed to `SWING-V01-180` distribution diagnostics.

## SWING-V01-180 - Accepted-candidate excess-return distribution report

Status: complete

What changed:

- Added typed excess-return distribution report contracts.
- Added accepted, near-miss, rejected, and all-row distribution report builder and writer.
- Added distribution metrics for mean, median, p10, p25, p75, p90, min, max, and positive rate.
- Added focused tests for distribution reports and writers.
- Generated the broad accepted excess-return distribution report.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/feature_outcomes.py`
- `src/swingmachine/__init__.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/accepted_excess_distribution_broad_20260508T004500Z/accepted_excess_distribution_report.json`
- `reports/swing_machine_v0_1/accepted_excess_distribution_broad_20260508T004500Z/accepted_excess_distribution_report.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_feature_outcomes.py`
- `.venv/bin/python -m ruff check src/swingmachine/feature_outcomes.py src/swingmachine/contracts.py src/swingmachine/__init__.py tests/test_feature_outcomes.py`
- Offline broad accepted excess-return distribution report generation.

Test result:

- Focused pytest: 8 passed in 174.28s.
- Ruff: all checks passed.
- Report status: `PASS`.
- Report conclusion: `NO_ACCEPTED_DISTRIBUTIONAL_20D_EXCESS_EDGE`.
- Accepted 20-session excess mean: -0.015076109274356514.
- Accepted 20-session excess median: -0.018542760293533966.
- Accepted 20-session excess positive rate: 0.4117647058823529.
- Near-miss 20-session excess mean: -0.002207401081832543.
- Rejected 20-session excess mean: 0.006998480920899183.

Assumptions made:

- Distributional SPY-excess evidence should be used before any new profile hypothesis is selected.

Blockers found:

- Accepted candidates do not show a distributional 20-session SPY-excess edge.

Follow-up work created:

- Proceed to `SWING-V01-181` traded-only lifecycle outcome decomposition.

## SWING-V01-181 - Traded-only lifecycle outcome decomposition

Status: complete

What changed:

- Added typed traded lifecycle decomposition report contracts.
- Added a reusable traded lifecycle decomposition report builder and writer.
- Added tests for setup-type, exit-reason, bars-held, and feature-bucket trade grouping.
- Generated the broad traded lifecycle decomposition report.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/feature_outcomes.py`
- `src/swingmachine/__init__.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/traded_lifecycle_decomposition_broad_20260508T011500Z/traded_lifecycle_decomposition_report.json`
- `reports/swing_machine_v0_1/traded_lifecycle_decomposition_broad_20260508T011500Z/traded_lifecycle_decomposition_report.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_feature_outcomes.py`
- `.venv/bin/python -m ruff check src/swingmachine/feature_outcomes.py src/swingmachine/contracts.py src/swingmachine/__init__.py tests/test_feature_outcomes.py`
- Offline broad traded lifecycle decomposition report generation.

Test result:

- Focused pytest: 10 passed in 172.75s.
- Ruff: all checks passed.
- Report status: `WARN` because traded sample is small.
- Report conclusion: `TRADED_LIFECYCLE_DOES_NOT_PROVE_EDGE`.
- Trade count: 9.
- Overall net PnL: -87.16533746537864.
- Overall win rate: 0.3333333333333333.
- PULLBACK: 4 trades, net PnL 633.9945425211051, win rate 0.75.
- TIGHT_BASE: 5 trades, net PnL -721.1598799864837, win rate 0.0.
- TRAIL_STOP: 6 trades, net PnL 717.2609604463299.
- INITIAL_STOP: 2 trades, net PnL -603.197755589257.
- TIME_EXIT: 1 trade, net PnL -201.22854232245163.

Assumptions made:

- Actual lifecycle net PnL should remain separate from forward close-to-close attribution.
- Small traded-only positives are hypotheses, not profile-selection evidence.

Blockers found:

- Traded sample remains too small to justify profile selection.
- TIGHT_BASE remains structurally weak in this broad lifecycle slice.

Follow-up work created:

- Proceed to `SWING-V01-182` exit-path diagnostics.

## SWING-V01-182 - Exit-path diagnostic for winners, losers, and time exits

Status: complete

What changed:

- Added typed exit-path diagnostic report contracts.
- Added post-exit forward-return and SPY-excess-return diagnostics from each trade exit date.
- Added diagnostic flags for loser recovery, avoided further weakness, winner continuation, winner reversal, initial-stop losses, and time-exit losses.
- Added tests for post-exit return calculations and writer output.
- Generated the broad exit-path diagnostic report.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/feature_outcomes.py`
- `src/swingmachine/__init__.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/exit_path_diagnostic_broad_20260508T013500Z/exit_path_diagnostic_report.json`
- `reports/swing_machine_v0_1/exit_path_diagnostic_broad_20260508T013500Z/exit_path_diagnostic_report.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_feature_outcomes.py`
- `.venv/bin/python -m ruff check src/swingmachine/feature_outcomes.py src/swingmachine/contracts.py src/swingmachine/__init__.py tests/test_feature_outcomes.py`
- Offline broad exit-path diagnostic report generation.

Test result:

- Focused pytest: 12 passed in 107.76s.
- Ruff: all checks passed.
- Report status: `WARN` because the exit diagnostic sample is small.
- Report conclusion: `EXIT_PATH_HYPOTHESES_REQUIRE_DEEPER_REPLAY`.
- Trade count: 9.
- Winners: 3.
- Losers: 6.
- Exit reason counts: INITIAL_STOP 2, TIME_EXIT 1, TRAIL_STOP 6.
- Diagnostic flags: loser_recovered_after_exit 5, loser_avoided_further_weakness 5, initial_stop_loss 2, time_exit_loss 1, winner_continued_after_exit 2, winner_reversed_after_exit 2.

Assumptions made:

- Post-exit diagnostics identify hypotheses only. They do not prove an exit rule should change without deeper replay.

Blockers found:

- Sample size remains too small for exit rule changes.

Follow-up work created:

- Proceed to `SWING-V01-183` pattern-specific benchmark-relative diagnostics.

## SWING-V01-183 - Pattern-specific benchmark-relative diagnostics

Status: complete

What changed:

- Added typed pattern-specific benchmark diagnostic contracts.
- Added a reusable pattern-specific benchmark diagnostic report builder and writer.
- Added per-pattern accepted-only benchmark-relative metrics, traded lifecycle metrics, sample grades, warnings, and recommendations.
- Added focused tests for report construction and artifact writing.
- Generated the broad offline pattern-specific benchmark diagnostic report.

Files touched:

- `src/swingmachine/contracts.py`
- `src/swingmachine/feature_outcomes.py`
- `src/swingmachine/__init__.py`
- `tests/test_feature_outcomes.py`
- `reports/swing_machine_v0_1/pattern_specific_benchmark_diagnostic_broad_20260508T062913Z/pattern_specific_benchmark_diagnostic_report.json`
- `reports/swing_machine_v0_1/pattern_specific_benchmark_diagnostic_broad_20260508T062913Z/pattern_specific_benchmark_diagnostic_report.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/python -m pytest tests/test_feature_outcomes.py`
- `.venv/bin/python -m ruff check src/swingmachine/feature_outcomes.py src/swingmachine/contracts.py src/swingmachine/__init__.py tests/test_feature_outcomes.py`
- Offline broad pattern-specific benchmark diagnostic report generation.

Test result:

- Focused pytest: 14 passed in 76.63s.
- Ruff: all checks passed.
- Report status: `WARN`.
- Report conclusion: `MIXED_OR_INSUFFICIENT_PATTERN_LEVEL_EVIDENCE`.
- Pattern count: 3.
- PULLBACK: 27 rows, 27 accepted, 4 traded, sample `EXPLORATORY`, accepted 20-session SPY-excess mean -0.024352428673817574, net PnL 633.9945425211051, recommendation `MIXED_PATTERN_EVIDENCE_REQUIRES_DEEPER_RESEARCH`.
- TIGHT_BASE: 24 rows, 24 accepted, 5 traded, sample `EXPLORATORY`, accepted 20-session SPY-excess mean -0.00464024994996282, net PnL -721.1598799864837, recommendation `PATTERN_SHOULD_BE_ISOLATED_OR_REDESIGNED`.
- pattern_missing: 4589 rows, 0 accepted, 0 traded, sample `INSUFFICIENT`, recommendation `INSUFFICIENT_SAMPLE_FOR_PATTERN_DECISION`.

Assumptions made:

- Pattern-specific diagnostics should not select a new profile unless both accepted-only benchmark-relative evidence and traded lifecycle evidence are positive with adequate sample depth.
- `pattern_missing` is rejected-row context, not a tradable strategy hypothesis.

Blockers found:

- PULLBACK remains mixed because traded lifecycle is positive but accepted-only 20-session SPY-excess is negative and the traded sample is only exploratory.
- TIGHT_BASE remains a likely isolation/redesign candidate, not a paper-trading candidate.
- No pattern-level evidence currently justifies paper trading.

Follow-up work created:

- Proceed to `SWING-V01-184` contract-window provider enrichment feasibility.

## SWING-V01-184 - Contract-window provider enrichment feasibility

Status: complete

What changed:

- Located the matched Alpaca and Hugging Face `historical_contract_stability_window` manifests.
- Built prepared feature panels in memory for both providers without mutating source manifests.
- Checked that all required benchmark-relative feature snapshot fields can be computed for both providers.
- Generated a contract-window provider enrichment feasibility report.

Files touched:

- `reports/swing_machine_v0_1/contract_window_provider_enrichment_feasibility_20260508T065026Z/contract_window_provider_enrichment_feasibility.json`
- `reports/swing_machine_v0_1/contract_window_provider_enrichment_feasibility_20260508T065026Z/contract_window_provider_enrichment_feasibility.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- In-memory prepared feature generation for `data/qualification_manifests/trading212/alpaca/historical_contract_stability_window/manifest.yaml`.
- In-memory prepared feature generation for `data/qualification_manifests/trading212/huggingface/historical_contract_stability_window/manifest.yaml`.
- Required benchmark-relative feature field coverage check against `DEFAULT_FEATURE_SNAPSHOT_FIELDS`.
- Provider symbol/session key comparison.

Test result:

- Feasibility report status: `WARN`.
- Decision: `PROCEED_NARROW_MATCHED_CONTRACT_WINDOW_WITH_COVERAGE_WARNINGS`.
- Alpaca prepared features: 5,120 rows, 16 symbols, 2024-04-22 to 2025-07-31, missing required fields: none.
- Hugging Face prepared features: 5,113 rows, 16 symbols, 2024-04-22 to 2025-07-31, missing required fields: none.
- Coverage delta: 7 Alpaca-only feature symbol/session keys, 0 Hugging Face-only feature symbol/session keys.
- Neither provider manifest currently declares prepared feature files.

Assumptions made:

- Provider-matched attribution is allowed only on the existing matched contract window, not on the broad Alpaca window.
- Missing Hugging Face rows must be carried into provider-matched interpretation rather than silently ignored.

Blockers found:

- Broad Hugging Face validation remains blocked.
- Provider manifests need research-only prepared feature artifacts before provider-matched attribution can run.

Follow-up work created:

- Proceed to `SWING-V01-185` provider-matched feature/outcome attribution packet.

## SWING-V01-185 - Provider-matched feature/outcome attribution packet

Status: complete

What changed:

- Wrote research-only prepared feature artifacts for Alpaca and Hugging Face contract-window manifests using `--no-update-manifest`.
- Ran bounded offline scanner replays for both provider contract windows to produce material decision rows.
- Joined provider scanner decisions, provider lifecycle trade ledgers, provider manifests, SPY forward returns, and prepared feature snapshots into provider-specific feature/outcome attribution datasets.
- Preserved benchmark-relative feature fields and SPY-excess forward returns for provider comparison.

Files touched:

- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/alpaca_prepared_features.parquet`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/alpaca_prepared_features_provenance.json`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/huggingface_prepared_features.parquet`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/huggingface_prepared_features_provenance.json`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/scanner_alpaca_contract/`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/scanner_huggingface_contract/`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/alpaca_feature_outcome_attribution/feature_outcome_attribution_dataset.json`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/alpaca_feature_outcome_attribution/feature_outcome_attribution_rows.csv`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/alpaca_feature_outcome_attribution/feature_outcome_attribution_summary.md`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/huggingface_feature_outcome_attribution/feature_outcome_attribution_dataset.json`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/huggingface_feature_outcome_attribution/feature_outcome_attribution_rows.csv`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/huggingface_feature_outcome_attribution/feature_outcome_attribution_summary.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- `.venv/bin/swingmachine build-prepared-feature-panel --no-update-manifest` for Alpaca contract manifest.
- `.venv/bin/swingmachine build-prepared-feature-panel --no-update-manifest` for Hugging Face contract manifest.
- `.venv/bin/swingmachine run-historical-scanner-replay` for Alpaca contract manifest.
- `.venv/bin/swingmachine run-historical-scanner-replay` for Hugging Face contract manifest.
- Offline provider feature/outcome attribution generation for both providers.

Test result:

- Alpaca scanner replay: `PASS`, 319 processed sessions, 5,104 material decision rows, 487 setups.
- Hugging Face scanner replay: `PASS`, 319 processed sessions, 5,097 material decision rows, 492 setups.
- Alpaca attribution: 5,104 rows, 487 accepted, 4,617 rejected, 42 traded, warnings: none.
- Hugging Face attribution: 5,097 rows, 492 accepted, 4,605 rejected, 42 traded, warnings: none.

Assumptions made:

- Prepared features are research artifacts for attribution and should not update the provider manifests during this task.
- Existing provider lifecycle trade ledgers from `20260507T184000Z` are the correct matched trade outcomes for this attribution packet.

Blockers found:

- Provider row counts differ because the Hugging Face panel remains seven symbol/session rows short versus Alpaca.
- Provider comparison must explicitly carry this mismatch and should not be interpreted as broad-provider validation.

Follow-up work created:

- Proceed to `SWING-V01-186` provider-matched accepted-versus-near-miss comparison.

## SWING-V01-186 - Provider-matched accepted-versus-near-miss comparison

Status: complete

What changed:

- Built accepted-versus-near-miss reports for Alpaca and Hugging Face provider-matched attribution datasets.
- Compared accepted counts, near-miss counts, accepted 20-session SPY-excess return, accepted positive SPY-excess hit rate, and conclusion stability.
- Generated JSON and Markdown provider comparison artifacts.

Files touched:

- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/alpaca_accepted_vs_near_miss/accepted_vs_near_miss_report.json`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/alpaca_accepted_vs_near_miss/accepted_vs_near_miss_report.md`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/huggingface_accepted_vs_near_miss/accepted_vs_near_miss_report.json`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/huggingface_accepted_vs_near_miss/accepted_vs_near_miss_report.md`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/provider_accepted_vs_near_miss_comparison/provider_accepted_vs_near_miss_comparison.json`
- `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/provider_accepted_vs_near_miss_comparison/provider_accepted_vs_near_miss_comparison.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline accepted-versus-near-miss report generation for Alpaca provider dataset.
- Offline accepted-versus-near-miss report generation for Hugging Face provider dataset.
- Offline provider comparison report generation.

Test result:

- Provider comparison decision: `PROVIDER_STABLE_BUT_NO_POSITIVE_ACCEPTED_EDGE`.
- Instability flags: none.
- Alpaca accepted 20-session SPY-excess mean: 0.00718414582769852.
- Hugging Face accepted 20-session SPY-excess mean: -0.0002551382005653741.
- Provider accepted 20-session SPY-excess delta: -0.007439284028263894.

Assumptions made:

- Provider stability requires no material metric drift, but promotion requires both providers to show a positive accepted-edge signal.
- A single-provider positive result is insufficient for paper readiness.

Blockers found:

- Provider-matched evidence does not prove a stable positive accepted-edge signal across both providers.
- Paper trading remains blocked.

Follow-up work created:

- Proceed to `SWING-V01-187` feature null/missingness and stability audit.

## SWING-V01-187 - Feature null/missingness and stability audit

Status: complete

What changed:

- Audited benchmark-relative feature snapshot fields across the broad Alpaca prepared feature artifact and the two provider contract prepared feature artifacts.
- Counted missing fields, null rates, infinities, numeric ranges, quantiles, and provider contract deltas.
- Generated JSON and Markdown feature null/stability audit artifacts.

Files touched:

- `reports/swing_machine_v0_1/feature_null_stability_audit_20260508T080049Z/feature_null_stability_audit.json`
- `reports/swing_machine_v0_1/feature_null_stability_audit_20260508T080049Z/feature_null_stability_audit.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline feature null/stability audit over `reports/swing_machine_v0_1/prepared_features_broad_benchmark_relative_20260507T223000Z/features.parquet`.
- Offline feature null/stability audit over provider contract Alpaca prepared features.
- Offline feature null/stability audit over provider contract Hugging Face prepared features.

Test result:

- Audit status: `WARN`.
- Decision: `FEATURE_AUDIT_PASS`.
- Warning count: 25.
- No required feature fields were missing.
- No infinite-value blockers were found.
- Null-rate warnings are concentrated in warm-up-sensitive benchmark-relative fields and candidate score/trend fields, especially in shorter provider contract artifacts.

Assumptions made:

- Warm-up nulls are warning-level if fields exist, no infinities are present, and downstream attribution only uses rows with observed forward/feature values.
- Provider contract feature distributions are more relevant for provider stability than broad-vs-contract distribution differences, because broad and contract windows differ by design.

Blockers found:

- No feature audit blocker.
- Feature null-rate warnings must remain visible in selection/qualification reports.

Follow-up work created:

- Proceed to `SWING-V01-188` cost/slippage stress by pattern and bucket.

## SWING-V01-188 - Cost/slippage stress by pattern and bucket

Status: complete

What changed:

- Generated a broad traded-lifecycle cost/slippage stress report from the attributed broad trade rows.
- Applied extra round-trip cost scenarios of 0, 5, 10, 25, and 50 bps.
- Summarized stress by overall traded lifecycle, pattern type, and feature buckets.
- Flagged cost fragility and resilience groups without changing strategy behavior.

Files touched:

- `reports/swing_machine_v0_1/cost_slippage_stress_broad_20260508T080525Z/cost_slippage_stress_report.json`
- `reports/swing_machine_v0_1/cost_slippage_stress_broad_20260508T080525Z/cost_slippage_stress_report.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline broad traded-lifecycle cost/slippage stress generation from `reports/swing_machine_v0_1/feature_outcome_attribution_broad_feature_snapshot_20260507T224500Z/feature_outcome_attribution_dataset.json`.

Test result:

- Report conclusion: `TRADED_LIFECYCLE_COST_STRESS_DOES_NOT_PROVE_EDGE`.
- Overall base net PnL: -87.16533746537864.
- Overall net PnL with extra 50 bps round-trip cost: -305.8880267695836.
- PULLBACK: `RESILIENT_TO_TESTED_COSTS`, base net PnL 633.9945425211051, 50 bps net PnL 517.4334530423915.
- TIGHT_BASE: `NEGATIVE_BEFORE_STRESS`, base net PnL -721.1598799864837, 50 bps net PnL -823.321479811975.

Assumptions made:

- Additional cost is applied as extra round-trip bps against approximate trade notional inferred from `net_pnl / net_return`.
- Cost stress is diagnostic only because the broad traded sample contains 9 trades.

Blockers found:

- Overall traded lifecycle remains negative before and after stress.
- PULLBACK resilience is sample-limited and does not justify paper trading.

Follow-up work created:

- Proceed to `SWING-V01-189` historical research artifact index.

## SWING-V01-189 - Historical research artifact index

Status: complete

What changed:

- Created a single historical research artifact index covering current evidence, superseded context, key report paths, and gate status.
- Separated current artifacts from superseded/context qualification packets.
- Recorded a compact decision summary for mechanical readiness, profitability edge, provider stability, pattern status, and paper trading.

Files touched:

- `reports/swing_machine_v0_1/historical_research_artifact_index_20260508T080800Z/historical_research_artifact_index.json`
- `reports/swing_machine_v0_1/historical_research_artifact_index_20260508T080800Z/historical_research_artifact_index.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline artifact existence check for indexed paths.

Test result:

- Artifact index status: `PASS`.
- Current artifacts indexed: 18.
- Superseded/context artifacts indexed: 2.
- Missing artifacts: 0.

Assumptions made:

- The index should avoid promoting superseded reports while keeping them available as context.

Blockers found:

- None for artifact indexing.

Follow-up work created:

- Proceed to `SWING-V01-190` paper-readiness blocker refresh.

## SWING-V01-190 - Paper-readiness blocker refresh

Status: complete

What changed:

- Created a paper-readiness blocker refresh separating research-edge, provider-stability, data-quality, mechanical, and operational-safety items.
- Marked paper trading explicitly blocked.
- Recorded the evidence required to clear each blocker.

Files touched:

- `reports/swing_machine_v0_1/paper_readiness_blocker_refresh_20260508T081020Z/paper_readiness_blocker_refresh.json`
- `reports/swing_machine_v0_1/paper_readiness_blocker_refresh_20260508T081020Z/paper_readiness_blocker_refresh.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline blocker refresh generation from current evidence paths and decisions.

Test result:

- Report status: `FAIL`.
- Paper gate: `BLOCKED`.
- Serious full run gate: `HISTORICAL_OFFLINE_ONLY_ALLOWED`.
- Blocking items: 5.
- Warning-level items: 2.

Assumptions made:

- Mechanical offline readiness and paper-readiness must remain separate.
- A sample-limited PULLBACK hypothesis cannot clear paper readiness without deeper qualification and accepted-edge evidence.

Blockers found:

- Research edge is not proven.
- Overall traded lifecycle is negative.
- Benchmark underperformance remains unresolved.
- Provider comparison does not show positive accepted edge across both providers.
- PULLBACK sample is too small for paper.

Follow-up work created:

- Proceed to `SWING-V01-191` overnight evidence summary packet.

## SWING-V01-191 - Overnight evidence summary packet

Status: complete

What changed:

- Created an overnight evidence summary packet covering completed activities, tests/checks, decisions, remaining blockers, and next recommended work.
- Kept paper/live gate status explicit.

Files touched:

- `reports/swing_machine_v0_1/overnight_evidence_summary_20260508T081201Z/overnight_evidence_summary.json`
- `reports/swing_machine_v0_1/overnight_evidence_summary_20260508T081201Z/overnight_evidence_summary.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline evidence summary generation from current completed items and report paths.

Test result:

- Summary status: `WARN`.
- Paper gate: `BLOCKED`.

Assumptions made:

- The summary should be a handoff artifact, not a new qualification decision.

Blockers found:

- No new blockers beyond the blocker refresh.

Follow-up work created:

- Proceed to `SWING-V01-192` backlog grooming and next-day decision shortlist.

## SWING-V01-192 - Backlog grooming and next-day decision shortlist

Status: complete

What changed:

- Marked the overnight queue complete through `SWING-V01-192`.
- Added a post-overnight decision shortlist to the backlog.
- Added follow-up backlog items `SWING-V01-193` through `SWING-V01-198` with objectives, implementation steps, dependencies, and acceptance criteria.
- Created a standalone next-day decision shortlist document.

Files touched:

- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_next_day_decision_shortlist.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Documentation/backlog update only; no tests required.

Test result:

- Backlog now has explicit follow-up tasks instead of blind one-by-one execution.

Assumptions made:

- The next work should resolve the PULLBACK contradiction, null/warm-up denominator risk, and TIGHT_BASE isolation before any new profile build.

Blockers found:

- Paper trading remains blocked.
- Revised profile implementation should not begin until the new design gate is satisfied.

Follow-up work created:

- `SWING-V01-193` through `SWING-V01-198`.

## SWING-V01-193 - PULLBACK traded-versus-accepted root-cause packet

Status: complete

What changed:

- Split accepted PULLBACK rows into traded and untraded accepted populations.
- Compared 20-session SPY-excess returns, hit rates, feature summaries, and traded lifecycle PnL.
- Generated JSON and Markdown root-cause packet.

Files touched:

- `reports/swing_machine_v0_1/pullback_traded_vs_accepted_root_cause_20260508T081457Z/pullback_traded_vs_accepted_root_cause.json`
- `reports/swing_machine_v0_1/pullback_traded_vs_accepted_root_cause_20260508T081457Z/pullback_traded_vs_accepted_root_cause.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline PULLBACK root-cause report generation from the broad feature/outcome attribution dataset.

Test result:

- Report conclusion: `PULLBACK_POSITIVE_LIFECYCLE_NOT_CONFIRMED_BY_ACCEPTED_EXCESS_EDGE`.
- All accepted PULLBACK rows: 27 rows, 20-session SPY-excess mean -0.024352428673817574, hit rate 0.2962962962962963.
- Traded accepted PULLBACK rows: 4 rows, 20-session SPY-excess mean 0.0075783415485345396, hit rate 0.5, net PnL 633.9945425211051.
- Untraded accepted PULLBACK rows: 23 rows, 20-session SPY-excess mean -0.029905606103791855, hit rate 0.2608695652173913.
- Flags: traded lifecycle positive; accepted PULLBACK 20d excess not positive; traded subset better than untraded on 20d excess; traded sample too small.

Assumptions made:

- The useful PULLBACK behavior, if real, may be in fill/lifecycle selection rather than raw accepted candidate quality.

Blockers found:

- PULLBACK is not paper-ready because the all-accepted evidence remains negative and the traded sample is too small.

Follow-up work created:

- Proceed to `SWING-V01-194` warm-up and null-aware selection denominator audit.

## SWING-V01-194 - Warm-up and null-aware selection denominator audit

Status: complete

What changed:

- Generated a null-aware denominator audit and corrected the initial denominator definition after it treated optional `candidate_score_pct` snapshot coverage as required.
- Created a v2 audit using core benchmark-relative and trend fields while treating `candidate_score_pct` as optional/non-filter because scanner rows carry score outside the feature snapshot.
- Compared all rows versus complete-core-feature rows overall and by pattern.

Files touched:

- `reports/swing_machine_v0_1/warmup_null_aware_denominator_audit_20260508T081656Z/warmup_null_aware_denominator_audit.json`
- `reports/swing_machine_v0_1/warmup_null_aware_denominator_audit_20260508T081656Z/warmup_null_aware_denominator_audit.md`
- `reports/swing_machine_v0_1/warmup_null_aware_denominator_audit_v2_20260508T082357Z/warmup_null_aware_denominator_audit.json`
- `reports/swing_machine_v0_1/warmup_null_aware_denominator_audit_v2_20260508T082357Z/warmup_null_aware_denominator_audit.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline null-aware denominator audit against the broad feature/outcome attribution dataset.
- Field coverage check for default feature snapshot fields.

Test result:

- v2 audit status: `PASS`.
- v2 conclusion: `CORE_NULL_FILTER_DOES_NOT_CHANGE_ACCEPTED_EDGE_CONCLUSION`.
- Complete-core rows: 4,640.
- Incomplete-core rows: 0.
- Accepted 20-session SPY-excess mean before core filter: -0.015076109274356514.
- Accepted 20-session SPY-excess mean after core filter: -0.015076109274356514.
- Changed flags: none.

Assumptions made:

- `candidate_score_pct` in the feature snapshot is optional for this denominator audit because scanner material decision rows already carry candidate score directly.

Blockers found:

- Null-aware filtering does not rescue the accepted-edge evidence.

Follow-up work created:

- Proceed to `SWING-V01-195` TIGHT_BASE isolation decision packet.

## SWING-V01-195 - TIGHT_BASE isolation decision packet

Status: complete

What changed:

- Created a TIGHT_BASE isolation decision packet.
- Summarized pattern diagnostic, traded lifecycle, cost stress, and accepted-distribution evidence.
- Defined re-entry acceptance criteria for any future TIGHT_BASE redesign.

Files touched:

- `reports/swing_machine_v0_1/tight_base_isolation_decision_20260508T082603Z/tight_base_isolation_decision.json`
- `reports/swing_machine_v0_1/tight_base_isolation_decision_20260508T082603Z/tight_base_isolation_decision.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline decision packet generation.

Test result:

- Decision: `ISOLATE_TIGHT_BASE_FROM_NEXT_BASELINE_CANDIDATE`.

Assumptions made:

- A decision packet can block accidental future inclusion without changing current strategy code.

Blockers found:

- TIGHT_BASE has negative lifecycle and cost-stress evidence and should not be included in a future candidate without explicit redesign evidence.

Follow-up work created:

- Proceed to `SWING-V01-196` revised candidate hypothesis design gate.

## SWING-V01-196 - Revised candidate hypothesis design gate

Status: complete

What changed:

- Created a revised-candidate hypothesis design gate report and stable docs version.
- Defined required evidence before building any revised profile variant.
- Explicitly disallowed paper/live execution, silent profile changes, and serious full qualification without a documented candidate hypothesis.

Files touched:

- `reports/swing_machine_v0_1/revised_candidate_hypothesis_design_gate_20260508T082758Z/revised_candidate_hypothesis_design_gate.json`
- `reports/swing_machine_v0_1/revised_candidate_hypothesis_design_gate_20260508T082758Z/revised_candidate_hypothesis_design_gate.md`
- `docs/swing_machine_v0_1_revised_candidate_hypothesis_gate.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline design gate generation.

Test result:

- Gate status: `FAIL`.
- Recommendation: `DO_NOT_BUILD_REVISED_PROFILE_YET`.

Assumptions made:

- The next profile should not be built until the PULLBACK contradiction is better explained and provider-positive-edge limitations are explicitly handled.

Blockers found:

- Provider-positive-edge gate is failing.
- PULLBACK contradiction and cost resilience gates are partial, not passed.

Follow-up work created:

- Proceed to `SWING-V01-197` broad Hugging Face data acquisition decision.

## SWING-V01-197 - Broad Hugging Face data acquisition decision

Status: complete

What changed:

- Created a broad Hugging Face data acquisition decision report and stable docs version.
- Decided to defer broader Hugging Face acquisition until an Alpaca-side hypothesis shows edge.
- Documented minimum data requirements if the decision is reopened.

Files touched:

- `reports/swing_machine_v0_1/broad_huggingface_data_acquisition_decision_20260508T083002Z/broad_huggingface_data_acquisition_decision.json`
- `reports/swing_machine_v0_1/broad_huggingface_data_acquisition_decision_20260508T083002Z/broad_huggingface_data_acquisition_decision.md`
- `docs/swing_machine_v0_1_broad_huggingface_data_decision.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline decision packet generation.

Test result:

- Decision: `DEFER_BROAD_HUGGINGFACE_ACQUISITION_UNTIL_ALPACA_HYPOTHESIS_SHOWS_EDGE`.

Assumptions made:

- Data acquisition should not outrun strategy evidence; current matched provider window is enough for research cross-checks.

Blockers found:

- Broad Hugging Face validation remains unavailable, but it is not the next limiting factor because no candidate edge is proven.

Follow-up work created:

- Proceed to `SWING-V01-198` next baseline candidate selection packet.

## SWING-V01-198 - Next baseline candidate selection packet

Status: complete

What changed:

- Created the next baseline candidate selection packet and stable docs version.
- Integrated PULLBACK root-cause, null-aware denominator, TIGHT_BASE isolation, revised-candidate design gate, and broad Hugging Face acquisition decision.
- Explicitly selected no revised baseline candidate.

Files touched:

- `reports/swing_machine_v0_1/next_baseline_candidate_selection_packet_20260508T083158Z/next_baseline_candidate_selection_packet.json`
- `reports/swing_machine_v0_1/next_baseline_candidate_selection_packet_20260508T083158Z/next_baseline_candidate_selection_packet.md`
- `docs/swing_machine_v0_1_next_baseline_candidate_selection.md`
- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`

Tests/checks run:

- Offline selection packet generation.

Test result:

- Selection: `NO_REVISED_BASELINE_CANDIDATE_SELECTED`.
- Next best work: `DESIGN_DEEPER_PULLBACK_FILL_AND_LIFECYCLE_REPLAY_RESEARCH`.
- Paper gate: `BLOCKED`.
- Serious full run gate: `BLOCKED_UNTIL_REVISED_CANDIDATE_SELECTED_FOR_OFFLINE_QUALIFICATION`.

Assumptions made:

- The correct next step is research design, not profile/config implementation.

Blockers found:

- No current candidate is strong enough for serious full qualification or paper trading.

Follow-up work created:

- Create a deeper PULLBACK fill/lifecycle replay research design and backlog before any revised profile build.
