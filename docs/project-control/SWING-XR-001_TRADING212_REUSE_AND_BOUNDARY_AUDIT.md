# SWING-XR-001 — Trading212 reuse and SwingMachine platform boundary audit

**Task:** SWING-XR-001

**Audit date:** 2026-08-08

**Status:** Architecture evidence complete; all recommendations remain **PROPOSED FOR CHATGPT/SPONSOR REVIEW**, not accepted or authorised for implementation.
**Scope:** Local tracked documentation, source and focused test definitions only. No application, research, data, report, runtime, provider, broker, Git or GitHub operation was performed.

## 1. Executive conclusion

SwingMachine and Trading212 should remain separate, independently deployable products. Trading212 is an ORB-first intraday research engine whose strongest reusable assets are fail-closed contract semantics, deterministic fingerprints, lifecycle evidence, reconciliation primitives, batch/recovery patterns, finite-run control and pre-outcome source-freezing mechanics. SwingMachine is a daily-bar, target-bearing, multi-session research and signal-generation system for manual Trading212 execution. Its timing, entry/stop/target, minimum 2:1 reward-to-risk, overnight, event, corporate-action and portfolio-heat rules remain authoritative.

Direct source reuse would import incompatible intraday assumptions. The proposed boundary is therefore semantic reuse through project-owned adapters and conformance fixtures, with no direct repo-to-repo runtime imports. Trading212 implementations should be adapted only where their mechanics are domain-neutral. SwingMachine should retain its daily lifecycle and SQLAlchemy operational/audit state, while adding a separate finite research-run custody layer when authorised.

The current SwingMachine decision, risk and order contracts do not explicitly carry a profit target or reward-to-risk ratio. They also do not provide a complete strategy-outcome envelope, exact consumed-input fingerprint set, complete source/config/code lineage, or a content-addressed reconstructable evidence package. Those are architecture gaps; this audit does not fix them.

## 2. Safety boundary and evidence method

This audit used the task brief as the controlling safety state, followed by each repository's `docs/project-control/` material and then directly relevant tracked code and focused test definitions. Generated reports, local data, `.tmp`, runtime databases, Vault content, credentials, logs, preserved/archive checkouts and the Trading212 2023 holdout were not inspected.

The Trading212 checkout contains tracked documentation for an earlier Databento 2020 canonical-machine proof associated with issue #2371. The task brief states that the current outcome campaign is issue #2377 and must not be started, executed, commented on or altered. No network or GitHub lookup was made, so the brief's newer gate is treated as authoritative and the branch/document currency difference remains an explicit unknown.

Maturity labels mean:

- `PROVEN_SOURCE_TEST`: deterministic source exists and focused test definitions exercise the bounded mechanics; it does not establish market validity or production readiness.
- `PROVEN_REAL_MECHANICS`: tracked source-of-truth documentation records execution over real source material sufficient to prove the narrow mechanical path, not edge, breadth, profitability or qualification.
- `PARTIAL`: a useful surface exists but material completeness, integration or validity is missing.
- `BLOCKED`: the capability is prohibited, unopened, absent or not authorised in the current phase.

Classification labels are exactly: `ADOPT_CONTRACT_SEMANTICS`, `ADAPT_IMPLEMENTATION`, `RETAIN_SWINGMACHINE`, `KEEP_TRADING212_ONLY`, `BUILD_FRESH`, and `DEFER_SHARED_EXTRACTION`.

In the component matrix, **P** means the classification and implementation seam are **PROPOSED FOR CHATGPT/SPONSOR REVIEW**. No P item is accepted by this document.

## 3. Repository identities and pre-existing state

### SwingMachine

| Field | Recorded value |
|---|---|
| Resolved root | `/home/alexballard92/swingmachine` |
| Origin | `https://github.com/Aballard92/swingmachine.git` |
| Branch | `main` |
| HEAD | `23efab1945cf53bcc556e736cc52b27675eae640` |
| Upstream status | `main...origin/main` |
| Staged state | Clean |
| Dirty tracked state | Clean |
| Untracked state | Clean before this task |

### Trading212

| Field | Recorded value |
|---|---|
| Resolved root | `/home/alexballard92/Trading212/t212-ai-bot` |
| Origin | `https://github.com/Aballard92/Trading212.git` |
| Branch | `agent/t212-ier-machine-002-databento-proof` |
| HEAD | `8fe932ee489a4fb03191ed42f0d819d64ecc9898` |
| Upstream status | `agent/t212-ier-machine-002-databento-proof...origin/agent/t212-ier-machine-002-databento-proof` |
| Staged state | Clean |
| Dirty tracked state | Clean |
| Untracked state | Pre-existing: `.tmp/`, `scripts/build_historical_backtest_data_index.py`, `scripts/run_blank_slate_orb_15m_backtest.py`, `scripts/stage_retained_parquet_to_sqlite_bars.py` |

The Trading212 untracked paths were neither opened nor modified. No state in either checkout was cleaned or normalised.

## 4. Files inspected

### SwingMachine tracked sources

- Control: `AGENTS.md`, `README.md`, and `docs/project-control/01_PRODUCT_BRIEF.md`, `02_CURRENT_STATE.md`, `03_TARGET_ARCHITECTURE.md`, `04_DECISION_LOG.md`, `05_BACKLOG_AND_ROADMAP.md`, `07_CODEX_WORKFLOW_AND_GUARDRAILS.md`, `08_OPEN_RISKS_AND_QUESTIONS.md`.
- Contracts and adapters: `src/swingmachine/contracts.py`, `swing_contracts.py`, `swing_adapters.py`.
- Domain mechanics: `src/swingmachine/entries.py`, `lifecycle.py`, `backtest.py`, `features.py`.
- State and evidence: `src/swingmachine/storage.py`, `qualification_evidence.py`, `replay.py`, `performance.py`, `feature_outcomes.py`.
- Focused test definition/name surfaces: `tests/test_swing_contracts.py`, `test_swing_adapters.py`, `test_entries.py`, `test_lifecycle.py`, `test_replay_workflow.py`, `test_qualification_evidence.py`, `test_performance.py`, `test_feature_outcomes.py`, `test_portfolio_manager.py`.

### Trading212 tracked sources

- Control: `AGENTS.md`, `README.md`, and `docs/project-control/01_PRODUCT_BRIEF.md`, `02_CURRENT_STATE.md`, `03_TARGET_ARCHITECTURE.md`, `04_DECISION_LOG.md`, `14_TRADING212_SCOPE_AND_CAPABILITY_MATRIX.md`.
- Contracts and canonical mechanics: `src/t212_ai_bot/strategies/strategy_signal_contract.py`, `runtime/canonical_research_machine_cycle.py`, `runtime/in_memory_risk_portfolio_adapter.py`, `execution/execution_intent_summary.py`, `runtime/canonical_research_machine_lifecycle.py`, `runtime/canonical_research_machine_evidence.py`, `runtime/canonical_research_machine_recovery.py`, `runtime/canonical_research_machine_batch.py`, `runtime/canonical_research_machine_batch_portfolio.py`.
- Research control: `src/t212_ai_bot/research/historical_evidence_controls.py`, `finite_research_run_storage.py`, `databento_canonical_machine_proof.py`.
- Focused test definition/name surfaces corresponding to the files above, including `tests/test_databento_canonical_machine_proof.py`.

The expected path `src/t212_ai_bot/research/databento_pre_outcome_adapter.py` is not present at the recorded Trading212 HEAD. The tracked pre-outcome/source-freezing seam is instead implemented in `databento_canonical_machine_proof.py`.

## 5. Component-by-component capability and reuse matrix

| Component | Trading212 source and public surface | T212 maturity | Current SwingMachine equivalent | T212 dependencies / ORB assumptions | Classification | Rationale, principal risk and smallest future seam | P |
|---|---|---|---|---|---|---|---|
| Product boundary | `AGENTS.md`; project-control 01/02/03/14 | `PROVEN_SOURCE_TEST` | `AGENTS.md`; project-control 01/02/03 | ORB-first intraday research; autonomous ambitions are gated | `RETAIN_SWINGMACHINE` | Keep separate products and authority. Risk: importing T212 phase or permission claims. Seam: a docs-only boundary plus versioned adapter conformance, never shared runtime ownership. | P |
| Strategy decision contract | `strategy_signal_contract.py`: `build_strategy_signal_contract`, `validate_strategy_signal_contract`, policy; `canonical_research_machine_cycle.py`: caller-supplied outcome builders/validators | `PROVEN_SOURCE_TEST` | `SwingSignal`, `SetupSnapshot`, `EntryPlan`, `OrderIntent`; adapter builders | T212 supports `trade_idea/no_trade/reject/blocked`; targetless ORB v2 deliberately forbids target/RR | `ADOPT_CONTRACT_SEMANTICS` | Adopt explicit outcome envelope, reason codes, strategy/platform ownership and fail-closed validation. Risk: targetless policy weakening Swing rules. Seam: Swing-native envelope requiring entry, stop, target and RR for an approved trade. | P |
| Canonical cycle / orchestration | `canonical_research_machine_cycle.py`: fixture and caller-supplied build/validate functions | `PROVEN_SOURCE_TEST` | Separate candidate, signal, entry, replay and performance functions; no single exact-input cycle envelope | One-minute session and ORB outcome feed canonical cycle | `ADAPT_IMPLEMENTATION` | Adapt deterministic stage boundaries and fingerprints, not bar/session logic. Risk: false equivalence between minute and daily decisions. Seam: pure Swing cycle taking daily snapshots and returning typed stage results without I/O. | P |
| Market/session inputs | Cycle input validators; `databento_canonical_machine_proof.py`: source identity/freeze/staging/decoding surfaces | `PARTIAL` | `SymbolDailyBar`, `FeatureSnapshot`, feature preparation | One-minute regular session, opening range and ORB-specific validators | `RETAIN_SWINGMACHINE` | Preserve official daily-bar and corporate-action semantics. Risk: one-minute completeness rules becoming daily-universe validity rules. Seam: Swing `DailyDecisionInput` with calendar, adjustment and source identity. | P |
| Risk and position sizing | `in_memory_risk_portfolio_adapter.py`: target and targetless policy/build/validate | `PROVEN_SOURCE_TEST` | `SwingRiskPlan`, `EntryPlan`, `plan_entry`, sizing and heat calculations | In-memory fixture portfolio and intraday trade idea | `ADAPT_IMPLEMENTATION` | Reuse fail-closed limit checks/fingerprints; retain Swing stop distance, 2:1 RR and multi-day reservations. Risk: numeric compatibility hiding semantic mismatch. Seam: adapter from Swing trade plan plus portfolio snapshot into a Swing risk decision. | P |
| Portfolio allocation | `canonical_research_machine_batch_portfolio.py`: policy/build/validate/render | `PROVEN_SOURCE_TEST` | `PortfolioSnapshot`, `ProtectedPosition`, `portfolio_heat`, sector exposure and entry constraints | Groups simultaneous intraday decisions; no ranking, resizing or ordering | `ADAPT_IMPLEMENTATION` | Reuse deterministic limit aggregation, not allocation policy. Risk: batch simultaneity ignoring carried exposure and pending orders. Seam: multi-session reservation ledger keyed by position/pending intent. | P |
| Execution intent | `execution_intent_summary.py`: target/targetless build/validate policy; inert only | `PROVEN_SOURCE_TEST` | `OrderIntent`, `SwingOrderPlan`, deterministic intent builder | No-action intent; targetless path and intraday references | `ADOPT_CONTRACT_SEMANTICS` | Adopt inertness, dedupe, exact predecessor linkage and explicit no-broker authority. Risk: treating an intent as permission. Seam: Swing manual-execution packet with entry/stop/target and acknowledgement state, still inert. | P |
| Lifecycle | `canonical_research_machine_lifecycle.py`: target and targetless lifecycle/validation | `PROVEN_SOURCE_TEST` | `lifecycle.py`; historical portfolio lifecycle replay; active/pending/exit state | Next-minute-open fill, no same-bar fill, stop ordering, targetless option, 15:55 force-flat | `RETAIN_SWINGMACHINE` | Swing lifecycle must remain daily and multi-session. Risk: same-day force-flat and minute fill rules corrupting overnight behaviour. Seam: project-specific lifecycle adapter emitting common event primitives. | P |
| Event ledger | Lifecycle append-only event output and validators | `PROVEN_SOURCE_TEST` | `HistoricalPortfolioLifecycleTransition`, backtest events, runtime events | Intraday event ordering and ORB identifiers | `ADOPT_CONTRACT_SEMANTICS` | Adopt append-only, predecessor-linked, deterministic events. Risk: shared event names smuggling ORB meanings. Seam: neutral event header plus project-owned typed payload/schema version. | P |
| P&L / accounting | Lifecycle target/targetless mechanics-only gross P&L and reconciliation | `PROVEN_SOURCE_TEST` | `HistoricalTradeLedgerRow`, backtest fills/costs/equity, performance reports | Intraday entry/exit rules; canonical fixture excludes realistic costs | `RETAIN_SWINGMACHINE` | Retain daily gap, multi-day mark, cost and corporate-action accounting. Risk: fixture gross P&L being read as comparable performance. Seam: common reconciliation totals only, with project-owned accounting calculation. | P |
| Reconciliation | Lifecycle reconciliation and independent rebuild validators | `PROVEN_SOURCE_TEST` | `HistoricalPortfolioLifecycleReconciliation`, `ReconciliationResult`, replay parity | Reconciles canonical intraday inputs/results | `ADOPT_CONTRACT_SEMANTICS` | Adopt independent rebuild, denominators and fail-closed mismatch reporting. Risk: validating hashes without validating domain semantics. Seam: Swing reconciler that rebuilds from frozen daily inputs and project rules. | P |
| Evidence packaging | `canonical_research_machine_evidence.py`: package/review build, validate, render | `PROVEN_SOURCE_TEST` | `SwingQualificationEvidenceIndex`, replay manifests and output files | Canonical T212 lifecycle is embedded/rebuilt; in-memory fixtures | `ADAPT_IMPLEMENTATION` | Adapt exact input/result linkage and content hashes. Risk: current Swing presence-only index appearing reconstructable. Seam: content-addressed Swing evidence manifest with schema/config/code/input hashes. | P |
| Operator review | Evidence review builders/renderers | `PROVEN_SOURCE_TEST` | Reports and qualification evidence index; manual execution is product policy | T212 review vocabulary reflects intraday canonical outcomes | `ADAPT_IMPLEMENTATION` | Reuse non-approving, blocker-first review semantics. Risk: review rendering becoming strategy approval. Seam: Swing review packet showing target/RR, gaps, events and provenance without execution authority. | P |
| Batching | `canonical_research_machine_batch.py`: build/validate 1–64-item batches | `PROVEN_SOURCE_TEST` | Replay/scanner loops and partition outputs | Canonical item/session shape and in-memory recovery | `ADAPT_IMPLEMENTATION` | Reuse deterministic item identity, aggregation and fail-closed bounds. Risk: treating a selected batch as a discovery universe. Seam: bounded Swing partition manifest with declared population and denominators. | P |
| Checkpoint / recovery | `canonical_research_machine_recovery.py`: run/checkpoint/validate/resume | `PROVEN_SOURCE_TEST` | Runtime recovery rows plus replay artifacts; no equivalent exact research predecessor chain | In-memory fixture recovery | `ADAPT_IMPLEMENTATION` | Reuse predecessor fingerprints and deterministic resume semantics. Risk: resuming from mutable operational state as research proof. Seam: immutable run checkpoint referencing committed artifact hashes. | P |
| Persistence / run control | `finite_research_run_storage.py`: `SQLiteFixtureControlStore`, `StrictJSONFixtureArtifactStore`, environment/backup helpers | `PROVEN_SOURCE_TEST` | `storage.py`: SQLAlchemy operational and audit rows; replay files | Dedicated temporary SQLite metadata, strict content-addressed JSON, fixture caps | `ADAPT_IMPLEMENTATION` | Add a separate research custody plane; do not replace operational storage. Risk: mixing mutable state with immutable proof. Seam: store interfaces for run metadata and immutable artifact references outside runtime ORM tables. | P |
| Historical campaign controls | `historical_evidence_controls.py`: policy, campaign, fees, observations, summaries and validators | `PROVEN_SOURCE_TEST` | Qualification plans, replay/performance/outcome diagnostics | Pure controls; no general historical runner or decision-grade evidence | `ADOPT_CONTRACT_SEMANTICS` | Adopt bounded campaign identity, denominators, adequacy and fail-closed interpretation. Risk: control completeness being mistaken for research validity. Seam: Swing campaign manifest bound to a sponsor-approved candidate and universe. | P |
| Source custody / pre-outcome freeze | `databento_canonical_machine_proof.py`: root/source identity, frozen population, raw verification, staging and operator surfaces | `PROVEN_REAL_MECHANICS` | Selected-period manifests/preflights and canonical snapshot hashes | Databento DBN, selected ORB sessions/symbols and issue-specific roots; tracked proof is 2020, not the unopened 2023 holdout | `ADAPT_IMPLEMENTATION` | Adapt freeze-before-outcome, byte hashes and population commitment. Risk: ORB validators or issue-local paths becoming general contracts. Seam: provider-neutral Swing source manifest frozen before feature/outcome calculation. | P |
| Costs and fees | `historical_evidence_controls.py`: fee schedule/scenario controls; lifecycle gross mechanics | `PARTIAL` | Execution-cost application, trade ledger costs, cost sensitivity reports | Intraday fee/slippage scenarios; lifecycle evidence remains mechanics-only | `RETAIN_SWINGMACHINE` | Swing holding-period, spread, slippage and manual execution assumptions require independent calibration. Risk: intraday fee model distorting daily results. Seam: versioned Swing cost policy emitted into lineage and sensitivity outputs. | P |
| Robustness / concentration | Historical observation/summary, cohorts, concentration and interpretation validators | `PROVEN_SOURCE_TEST` | `performance.py` and `feature_outcomes.py` cost, concentration, pattern/exit diagnostics | Control logic can operate on synthetic inputs; not historical proof | `ADOPT_CONTRACT_SEMANTICS` | Adopt denominator and concentration schema semantics. Risk: passing control validation without suitable population. Seam: Swing metrics adapter over sponsor-approved partitions and discovery population. | P |
| Holdout controls | Project-control gates; forbidden-year/source guards in Databento proof tests | `BLOCKED` | Gate 2 and frozen holdout explicitly unopened | T212 2023 prospective holdout prohibited; campaign #2377 unopened by this task | `KEEP_TRADING212_ONLY` | Keep each product's holdout custody independent. Risk: cross-product exposure contaminating both research programmes. Seam: shared policy words only; no shared holdout IDs, data or access paths. | P |
| Monitoring / runtime / broker surfaces | Product/runtime docs; strategy contract reserves platform ownership | `BLOCKED` | Runtime/broker-shaped models exist, but current phase is offline; paper blocked and live prohibited | Autonomous runtime and broker direction; no current permission | `KEEP_TRADING212_ONLY` | Do not use T212 autonomy as Swing authority. Risk: architecture reuse silently broadening permissions. Seam: none until an explicit future sponsor gate; keep manual execution boundary. | P |
| User-facing output | Evidence renderers and inert intent summaries | `PARTIAL` | Reports, evidence indexes and manual-review outputs | T212 operator output is canonical intraday/ORB oriented | `BUILD_FRESH` | Build a Swing-native daily review packet when authorised. Risk: generic output omitting target, overnight/event risks or manual status. Seam: read-only schema/render spec before implementation. | P |

## 6. Trading212 assumptions that must not cross the boundary

Each item below is **PROPOSED FOR CHATGPT/SPONSOR REVIEW** as an explicit isolation rule:

1. **One-minute session semantics must not enter shared input contracts.** Shared primitives may identify an observation and timestamp, but session completeness and decision timing remain project-owned.
2. **Opening-range logic must remain Trading212-only.** ORB window construction, opening-range highs/lows and ORB rejection reasons are strategy adapter details.
3. **Targetless/no-RR behaviour must not be allowed by a Swing approved-trade adapter.** Trading212 targetless v2 is valid only inside its own policy. Swing requires an explicit target and minimum 2:1 reward-to-risk.
4. **Next-minute-open fill must remain Trading212-only.** Swing pending orders cross daily sessions and require official-open/gap handling.
5. **The 15:55 force-flat rule must remain Trading212-only.** Swing positions may be deliberately held overnight for multiple sessions.
6. **ORB-specific source validators must not define shared custody.** A shared manifest can carry hashes and identity; project adapters validate domain-specific bar/session/population rules.
7. **Intraday fee assumptions must not calibrate Swing accounting.** Cost schemas may be common, but values and application timing remain project-owned.
8. **Autonomous runtime/broker assumptions must not enter SwingMachine.** A reusable intent remains inert and non-authorising; Swing output supports manual review and execution only.

## 7. SwingMachine domain authority

Each item below is **PROPOSED FOR CHATGPT/SPONSOR REVIEW** as an explicit boundary assertion, while the underlying behaviour remains governed by current SwingMachine project control:

- Decisions are made on deterministic daily-bar timing, not an intraday opening window.
- Pending entries and active positions can span multiple official sessions.
- Overnight gaps must be represented in entry, stop, valuation and exit mechanics.
- Every approved trade requires an explicit entry, protective stop and target.
- Reward-to-risk must be explicit and at least 2:1; no targetless compatibility mode is valid for Swing approvals.
- Earnings and other event controls remain part of eligibility, cancellation and position management.
- Corporate actions and raw versus adjusted price semantics must be explicit by calculation purpose.
- Portfolio heat must include carried positions, pending risk reservations and multi-day exposure.
- Operator review and manual Trading212 execution remain mandatory; no contract, evidence package or intent grants broker permission.

## 8. SwingMachine contract and evidence gap assessment

| Required property | Current finding | Source-backed implication |
|---|---|---|
| Explicit target | **Gap.** `SwingSignal`, `SwingRiskPlan`, `SwingOrderPlan`, `SetupSnapshot`, `EntryPlan` and `OrderIntent` carry entry/limit/stop data but no target. | The domain rule cannot be reconstructed from the public decision/risk/order objects alone. |
| Reward-to-risk | **Gap.** Per-share risk is explicit; proposed reward and computed RR are not. | Minimum 2:1 enforcement is not auditable from the contract chain alone. |
| Strategy outcome envelope | **Partial gap.** Approval booleans, rejection reasons and setup objects exist, but there is no single versioned `trade/no-trade/reject/blocked` envelope binding the decision and platform ownership. | Consumers must infer outcome semantics from multiple models. |
| Exact consumed-input fingerprints | **Partial gap.** Config and feature snapshot hashes exist in selected surfaces; exact field-level inputs consumed by every stage are not consistently bound through the chain. | Deterministic output does not by itself prove exact input lineage. |
| Exact source/config/code lineage | **Gap.** Config hashes and selected manifests exist, but provider/source object identities and code commit/tree identity are not consistently carried in decision, risk, order and evidence contracts. | A result cannot be independently attributed to one complete source/config/code tuple. |
| Reconstructable evidence package | **Partial gap.** Replay produces rich artifacts and manifests; `SwingQualificationEvidenceIndex` records required names, paths and presence, not content hashes or a complete dependency graph. | Presence is not immutable custody and does not independently reconstruct the result. |

These gaps are findings only. **PROPOSED FOR CHATGPT/SPONSOR REVIEW:** resolve them through a future Swing-native contract specification before changing implementation.

## 9. Persistence boundary

| Concern | SwingMachine SQLAlchemy state | Trading212 finite research-run state | Proposed boundary |
|---|---|---|---|
| Primary purpose | Operational/runtime-shaped order, broker, shadow, run, event and audit state | Finite campaign admission, lease/checkpoint/control metadata and immutable content-addressed artifacts | **PROPOSED FOR CHATGPT/SPONSOR REVIEW:** retain both purposes as separate planes. |
| Mutability | Mutable records and upserts are appropriate for current state and recovery | Append/commit-oriented artifact custody with strict JSON and referenced hashes | **PROPOSED FOR CHATGPT/SPONSOR REVIEW:** never claim mutable ORM rows as immutable research evidence. |
| Domain coupling | Swing order, setup, runtime and broker-shaped tables | More domain-neutral run-control/store interfaces, but currently fixture-scoped | **PROPOSED FOR CHATGPT/SPONSOR REVIEW:** adapt the interfaces, not the T212 database or table schema. |
| Integration | Existing Swing code depends on SQLAlchemy models | Dedicated SQLite control store and artifact store | **PROPOSED FOR CHATGPT/SPONSOR REVIEW:** add an authorised research-custody seam beside SQLAlchemy; do not replace or merge implementations. |
| Evidence reference | Paths, runtime records and replay artifacts | Committed content hashes and predecessor-aware run state | **PROPOSED FOR CHATGPT/SPONSOR REVIEW:** operational records may reference immutable evidence IDs, but immutable artifacts must not depend on mutable row contents. |

The minimum future interface is a project-neutral `RunControlStore` plus `ImmutableArtifactStore`, with Swing-owned manifests and validators. It must be implemented inside SwingMachine first; no runtime import from Trading212 is permitted.

## 10. Architecture-level Databento corpus assessment

No Databento data, task-local artifacts, reports, `.tmp`, Vault paths or 2023 material were accessed. This assessment concerns only potential architectural roles:

| Possible role | Classification | Boundary |
|---|---|---|
| Mechanical parity fixture | **Potentially suitable.** | **PROPOSED FOR CHATGPT/SPONSOR REVIEW:** use only an explicitly authorised, non-holdout slice to compare decoding, source hashing and neutral lifecycle/event mechanics; never infer Swing edge. |
| Selected-liquid-stock secondary research panel | **Potentially suitable with material conditions.** | **PROPOSED FOR CHATGPT/SPONSOR REVIEW:** require legal/access approval, daily-bar derivation rules, corporate-action treatment, population declaration and independence from the candidate-selection universe. |
| Lifecycle stress panel | **Potentially suitable.** | **PROPOSED FOR CHATGPT/SPONSOR REVIEW:** use bounded sessions for gaps, missing bars and stop-order stress only after a dedicated protocol; do not carry ORB outcomes into Swing labels. |
| Sole broad-market candidate-selection universe | **Unsuitable.** | **PROPOSED FOR CHATGPT/SPONSOR REVIEW:** reject this role because a selected liquid corpus cannot establish broad, point-in-time discovery-population suitability and can embed survivorship/selection bias. |

This does not authorise acquisition, transformation, staging, inspection or outcome execution. Issue #2377 and the 2023 prospective holdout remain closed to this task.

## 11. Proposed target cross-repository architecture

All recommendations in this section are **PROPOSED FOR CHATGPT/SPONSOR REVIEW**:

1. **Independent products.** Each repository owns its application, strategy rules, data adapters, lifecycle, costs, persistence and release process. Each remains independently testable and deployable.
2. **No direct runtime imports.** SwingMachine must not import `t212_ai_bot`, and Trading212 must not import `swingmachine`. Cross-repository comparison is through versioned documents, fixtures and serialized conformance examples only.
3. **Project-specific strategy adapters.** A neutral outcome header can express `trade_idea`, `no_trade`, `reject` or `blocked`, but each project owns its trade-plan payload and validation. The Swing adapter must require entry, stop, target and RR >= 2.0.
4. **Project-specific lifecycle adapters.** A neutral event header may contain event ID, run ID, predecessor ID, observation identity, event type, payload schema and hashes. Fill, stop, target, gap and time-exit rules remain entirely inside each project.
5. **Genuinely common primitives only.** Candidate common semantics are: versioned outcome envelope; structured reason; exact input-fingerprint set; source/config/code lineage envelope; immutable artifact reference; append-only event header; reconciliation result; run/checkpoint identity; cost-component/scenario schema; population denominator and adequacy result; non-approving operator-review status.
6. **Capability firewall.** Common contracts must be silent on bar interval, opening range, target presence, fill timing, close-out time, provider, broker and autonomous execution. Project adapters add stricter invariants. A shared interface must never choose the least strict project rule.
7. **Swing-native first implementation.** Any authorised Swing work should first implement local schemas and adapters against local tests. Trading212 serves as source evidence, not a dependency.
8. **Deferred shared extraction.** Extract a shared package only when both repos independently implement the same versioned primitive, both have project-specific adapter and conformance tests, at least two real call sites per repo demonstrate stable semantics, two maintenance changes have been duplicated without domain divergence, and sponsor review confirms that the candidate interface contains no ORB, daily-swing, provider, runtime or broker policy. Until every condition is met, duplicate the small schema intentionally.

Conceptual dependency direction:

```text
SwingMachine domain adapters ─┐
                              ├─ serialized common semantic fixtures (no runtime import)
Trading212 domain adapters ───┘

SwingMachine: daily inputs → Swing outcome → Swing risk/portfolio → inert manual packet
              → multi-session lifecycle → Swing accounting/evidence

Trading212:   minute inputs → ORB outcome → T212 risk/portfolio → inert intent
              → intraday lifecycle → T212 accounting/evidence
```

## 12. Key conflicts and architecture risks

- **Target conflict:** Trading212 targetless v2 is explicitly valid there; SwingMachine's minimum 2:1 target-bearing rule cannot be optional.
- **Time-model conflict:** next-minute fill and 15:55 flattening are incompatible with daily pending orders, overnight gaps and multi-session positions.
- **Population conflict:** an ORB-selected liquid corpus can prove mechanics but not broad-market Swing discovery suitability.
- **Adjustment conflict:** Swing features use split-adjusted prices while execution/valuation paths use raw prices. The intended boundary is plausible but is not carried as explicit per-field lineage.
- **Carried-stop ambiguity:** the daily backtest checks a carried position's stop using the session raw open/low, then updates trailing state after the stop check. This is a daily OHLC approximation, not intraday path evidence; same-bar ordering and gap semantics require an explicit validity decision.
- **Partition-end ambiguity:** the backtest returns active positions and final marked equity without forcibly closing them. Performance and qualification denominators must explicitly distinguish closed trades, open positions and unrealised results at a partition boundary.
- **Evidence conflict:** path/presence manifests are weaker than immutable content-addressed lineage. Retrofitting hashes without a frozen source/config/code dependency graph would create superficial provenance.
- **Maturity conflict:** source-tested controls and real mechanical execution do not demonstrate strategy edge, profitability, representativeness or decision-grade research.
- **Permission conflict:** broker/runtime-shaped models or future autonomy language do not grant paper, live, account, provider or order authority.
- **Source-currency conflict:** this Trading212 checkout documents issue #2371-era proof while the controlling brief names unopened campaign #2377. No inference about #2377 state is made.

## 13. Proposed SwingMachine backlog

Every proposed backlog item is **PROPOSED FOR CHATGPT/SPONSOR REVIEW** and remains unaccepted.

### Now

- Review this boundary audit without changing application code or opening any research gate.
- Preserve the current offline-only state: no revised candidate, PULLBACK parked, H1/H2 parked, Gate 2/holdout unopened, paper blocked and live prohibited.
- Define a Swing-native decision and lineage contract on paper, explicitly covering target, RR, outcome, exact inputs and source/config/code identity.

### Next

- Specify docs-only conformance examples for the Swing decision/lineage contract, including trade, no-trade, reject and blocked outcomes and a mandatory target/RR invariant.

### Later

- Add a Swing-owned canonical daily cycle behind pure adapters.
- Add immutable evidence-manifest and finite-run custody interfaces beside the SQLAlchemy operational plane.
- Add daily lifecycle event/reconciliation conformance and operator-review schemas.
- Reassess shared-package extraction only when every trigger in section 11 is satisfied.

### Blocked

- Revised-strategy implementation or serious qualification until a revised candidate is selected.
- Gate 2 and any frozen-holdout access.
- Paper trading, live trading, autonomous runtime, broker/account/order actions.
- Broad data acquisition unless a new bounded task meets the current five-part exception.
- Any Databento use until a separately authorised protocol identifies source, population, custody, corporate-action treatment and non-holdout status.
- Discovery-population validity until point-in-time breadth, delistings/survivorship and representativeness are evidenced.
- Carried-position intraday-stop validity until daily OHLC ordering/gap limitations are explicitly adjudicated.
- Raw-versus-split-adjusted feature/input validity until calculation-specific lineage and corporate-action semantics are explicit.
- Partition-end performance validity until open positions, unrealised P&L and denominators are explicitly reconciled.
- Report-to-code provenance until evidence binds exact source, config, code and consumed-input hashes.

### Rejected / Not now

- Direct repo-to-repo runtime imports.
- Copying the Trading212 canonical lifecycle wholesale.
- Targetless/no-RR Swing trade ideas.
- One-minute, opening-range, next-minute-open or 15:55 force-flat semantics in shared contracts.
- Treating Trading212's selected Databento corpus as the sole Swing discovery universe.
- Replacing SwingMachine SQLAlchemy state with the Trading212 fixture store.
- Shared broker/runtime/autonomy abstractions.

### Recently completed

- Source-tested Swing contract, adapter, entry, lifecycle, replay, performance and diagnostic surfaces already exist as bounded foundations.
- Trading212 has source-tested canonical contract, risk, inert intent, lifecycle, evidence, batching, recovery and finite-run control primitives, plus narrowly documented real source-custody/mechanical proof.
- This audit records the cross-repository boundary without changing either implementation or research state.

## 14. Acceptance-criteria assessment

| Criterion | Status |
|---|---|
| Exactly one authorised Markdown document created | Met, subject to final Git verification |
| No existing file in either repository modified | Met, subject to final Git verification |
| Both identities and pre-existing states recorded | Met |
| Every required component source-backed and classified | Met |
| Direct, adapted, retained, fresh and deferred work separated | Met |
| Trading212 intraday assumptions isolated | Met |
| Swing daily/multi-session authority explicit | Met |
| Shared-package extraction trigger defined | Met |
| Databento reuse classified without data access | Met |
| Prior Swing validity concerns retained | Met |
| Exactly one next bounded task recommended | Met in section 15 |
| No tests, application commands, data/outcome reads or external actions | Met |

## 15. Recommended next bounded task

**One recommendation only — PROPOSED FOR CHATGPT/SPONSOR REVIEW:** `SWING-XR-002 — Specify the SwingMachine-native strategy outcome and lineage contract`, a documentation-only task limited to a single project-control document defining target-bearing trade/no-trade/reject/blocked schemas, minimum 2:1 RR validation, exact consumed-input fingerprints, source/config/code lineage, and reconstructable evidence-manifest requirements; no source, test, config, data, report, runtime, Git or GitHub changes.

## 16. Remaining unknowns

- The sponsor's eventual revised Swing strategy candidate and therefore its exact decision payload are not selected.
- Broad, point-in-time discovery-population suitability remains unproven.
- The intended raw-versus-adjusted price boundary is not fully encoded in lineage contracts.
- Daily OHLC data cannot resolve all intraday stop/target path ordering for carried positions.
- Partition-end open-position treatment is not yet a qualification rule.
- Complete report-to-code/source/config/input provenance is absent.
- Trading212 issue #2377 state was not inspected; the task brief alone controls it here.
- The suitability, entitlement and corporate-action properties of any Databento corpus for Swing research were not assessed from data.
- A common package may never be warranted; its trigger has not been met.

## 17. Final operation statement

No tests were run. No application or research command was run. No data, generated report, `.tmp`, Vault, 2023 raw/outcome or preserved/archive content was read. No provider, network, API, broker, account, order, runtime, paper or live action was performed. No file was staged or committed; no branch, push, PR, issue or comment action was performed. Trading212 issue #2377 was not started, executed, inspected, commented on or altered.

Final Git states are to be appended to the task handoff from the specified read-only verification commands; they are not embedded here as claims before verification.
