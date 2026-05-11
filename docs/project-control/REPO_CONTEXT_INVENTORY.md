# swingmachine Repo Context Inventory

Created: 2026-05-08
Repo confirmed: `/home/alexballard92/swingmachine`
Write scope used for this audit: `docs/project-control/` only

## Audit scope

This is a practical source-of-truth inventory for deciding what belongs in a ChatGPT Project. It covers repo documents, obvious high-context config files, code-map files, test-map files, and generated report areas that affect current project state.

It does not attempt to upload or enumerate every generated report, fixture, data file, or source module line-by-line. The objective is a minimal, useful context pack.

## Current source-of-truth summary

The repo is a deterministic daily-bar swing trading engine in build/research/qualification phase. It is not paper-ready or live-ready. The latest decision state is:

- Paper trading: blocked.
- Serious full run: blocked until a revised candidate is selected for offline qualification.
- Current candidate: no revised baseline candidate selected.
- Next best work: design deeper PULLBACK fill/lifecycle replay research.
- TIGHT_BASE: should be isolated from the next candidate unless explicitly redesigned.
- Hugging Face broad data: acquisition deferred until an Alpaca-side hypothesis shows edge.

## Inventory

| File path | Type | Summary | Relevance | Upload to ChatGPT Project | Why it matters | Stale, duplicate, or contradiction notes |
| --- | --- | --- | --- | --- | --- | --- |
| `README.md` | setup | Main repo overview, current scope, setup, paper/shadow/audit workflow, data contracts, migrations, runtime commands, quality gates. | High | Yes | Best compact entrypoint for the repo. | Appears broadly current, but project status decisions are more current in newer v0.1 docs. |
| `BUILD_HANDOVER_AND_AUDIT.md` | architecture | Large handover and critical assessment from 2026-04-30 covering north star, architecture, engines, gaps. | Medium | Maybe | Useful background for architecture and original build audit. | Older than v0.1 discovery/design docs; upload only if historical context is needed. |
| `SESSION_CONTINUATION.md` | roadmap | Saved continuation note from 2026-04-29 with current intent, validation, next moves. | Archive | No | Useful only for old recovery context. | Stale; superseded by implementation log, backlog, and next-day decision docs. |
| `docs/swing_machine_current_state_review.md` | product | Specific current-state review of existing swing-related state, architecture, data, runtime, research, testing, risks. | High | Yes | One of the best source-of-truth docs for where the repo stood at baseline discovery. | Created 2026-05-05; should be supplemented with latest blocker/selection docs. |
| `docs/swing_machine_v0_1_baseline_definition.md` | product | Defines what `swing_machine_v0_1` should mean: purpose, scope, universe, candidates, signals, risk, lifecycle, reporting, qualification. | High | Yes | Core product definition. | Still relevant; latest decisions say no candidate currently selected. |
| `docs/swing_machine_v0_1_solution_design.md` | architecture | Technical target architecture, domain model, contracts, config/profile rules, parity, reporting, testing, delivery sequence. | High | Yes | Core implementation design. | May not include every later report artifact; pair with latest decision docs. |
| `docs/swing_machine_v0_1_delivery_plan.md` | roadmap | Delivery principles, epics, readiness/done criteria, qualification stages, blocker handling. | High | Yes | Defines delivery governance. | Still useful; detailed backlog has moved beyond it. |
| `docs/swing_machine_v0_1_backlog.md` | backlog | Massive autonomous backlog with activity IDs through current follow-ups. | High | Maybe | Actual working backlog and status ledger. | Very large and contains old/completed/superseded items; should be consolidated before upload unless full backlog history is desired. |
| `docs/swing_machine_v0_1_implementation_log.md` | backlog | Very large chronological implementation log with completed activities, tests, artifacts, decisions. | Medium | Maybe | Forensic record of what changed and what evidence exists. | Too large/noisy for compact project context; prefer latest summaries and artifact index. |
| `docs/swing_machine_v0_1_next_day_decision_shortlist.md` | roadmap | Current concise shortlist: paper blocked, serious full run historical/offline only, PULLBACK next research, TIGHT_BASE isolate. | High | Yes | Best short current-state decision doc. | Current as of latest run. |
| `docs/swing_machine_v0_1_revised_candidate_hypothesis_gate.md` | roadmap | Gate saying `DO_NOT_BUILD_REVISED_PROFILE_YET`; lists allowed/disallowed next work. | High | Yes | Prevents premature profile implementation. | Current; should be treated as controlling over older revision docs. |
| `docs/swing_machine_v0_1_next_baseline_candidate_selection.md` | roadmap | Latest candidate selection packet: no revised baseline selected; next best work is deeper PULLBACK fill/lifecycle replay research. | High | Yes | Most important current decision state. | Current and supersedes older revision/paper-readiness optimism. |
| `docs/swing_machine_v0_1_broad_huggingface_data_decision.md` | roadmap | Decision to defer broad Hugging Face acquisition until Alpaca-side edge is proven. | High | Yes | Key data/provider decision. | Current. |
| `docs/swing_machine_v0_1_benchmark_relative_feature_design.md` | architecture | Benchmark-relative feature groups and rules; explicitly says implementation should not secretly change strategy behavior. | High | Yes | Important for feature/outcome research context. | Design current; strategy behavior still gated. |
| `docs/swing_machine_v0_1_trading212_data_solution_design.md` | architecture | How Trading212 Alpaca/Hugging Face research DBs feed selected-period qualification. | High | Yes | Essential data-source architecture and provider caveat. | Current enough; later decision docs refine provider usage. |
| `docs/swing_machine_v0_1_data_source_decision.md` | product | Data source decision: Alpaca primary candidate, Hugging Face comparison/audit only until drift is explained. | Medium | Optional | Useful provider decision history. | Includes correction that current selected periods were not covered; later historical/broad docs supersede parts. |
| `docs/swing_machine_v0_1_huggingface_drift_investigation.md` | testing | Investigates Alpaca/Hugging Face price/session drift and adjustment policy concerns. | Medium | Optional | Explains why HF is comparison/audit only. | Older than broad HF defer decision, but still useful evidence. |
| `docs/swing_machine_v0_1_data_provenance_template.md` | setup | Template for selected-period data provenance. | Medium | Optional | Useful operational standard for future data packages. | Not a current decision; template only. |
| `docs/HISTORICAL_PANEL_REQUIREMENTS.md` | testing | Historical panel and replay requirements: data contracts, validation, deterministic replay. | High | Optional | Strong data/replay requirement reference. | Older generic doc; still useful if ChatGPT needs data contract context. |
| `docs/OPERATING_RUNBOOK.md` | setup | Local paper, shadow, audit, historical panel validation, and recovery runbook. | High | Optional | Operational commands and workflow. | It is a local/paper/shadow runbook, not permission to run paper/live. Pair with current paper-blocked docs. |
| `docs/swing_machine_v0_1_selected_period_runbook.md` | setup | Selected-period qualification runbook and data preparation steps. | Medium | Optional | Useful for future qualification operations. | States selected-period qualification blocked; later historical work moved beyond some parts. |
| `docs/swing_machine_v0_1_qualification_gate_checklist.md` | testing | Short checklist of current qualification gate status. | Medium | Optional | Fast gate checklist. | Older than latest blocker refresh/selection packet. |
| `docs/swing_machine_v0_1_qualification_mini_plan.md` | roadmap | Qualification workstreams A-E. | Medium | Optional | Good context for avoiding item-by-item drift. | Older than latest post-overnight shortlist. |
| `docs/swing_machine_v0_1_mechanical_readiness_solution_design.md` | architecture | Implementation-ready design for mechanical readiness reports and decision ledger. | Medium | Optional | Useful if future work touches readiness evidence. | Later work likely implemented much of it. |
| `docs/swing_machine_v0_1_mechanical_readiness_completion_design.md` | architecture | Target mechanical standard and readiness categories. | Medium | Optional | Good quality standard reference. | Older checkpoint; latest state says mechanical readiness is stronger but edge blocked. |
| `docs/swing_machine_v0_1_multi_session_scanner_design.md` | architecture | Multi-session scanner qualification design and research/runtime parity boundary. | Medium | Optional | Important for scanner-density work. | Some implementation now exists; design may be partially superseded. |
| `docs/swing_machine_v0_1_tier2_portfolio_lifecycle_qualification_design.md` | architecture | Tier 2 portfolio/lifecycle qualification design. | Medium | Optional | Useful for lifecycle simulation semantics. | Some implementation and evidence now exists; pair with latest lifecycle reports if needed. |
| `docs/swing_machine_v0_1_historical_performance_solution_design.md` | architecture | Performance qualification solution design and provider comparison commands/contracts. | Medium | Optional | Useful for historical performance/reporting context. | Later performance evidence showed no edge. |
| `docs/swing_machine_v0_1_historical_performance_qualification_design.md` | architecture | Defines historical performance qualification metrics and gating. | Medium | Optional | Good benchmark/performance standard. | Superseded by later result docs and current candidate selection decision. |
| `docs/swing_machine_v0_1_post_qualification_research_plan.md` | roadmap | Post-failed-baseline research plan and immediate research tranche. | Medium | Optional | Useful for research principles and questions. | Partly superseded by latest next-day shortlist and selection packet. |
| `docs/swing_machine_v0_1_working_backlog_solution_design.md` | backlog | Elaborated overnight backlog items `SWING-V01-177` to `SWING-V01-192`. | Medium | Maybe | Useful detail for recently completed diagnostics. | Most items now completed; current selection packet is more concise. |
| `docs/swing_machine_v0_1_revision_design.md` | roadmap | Controlled offline revision candidates after failed historical profitability qualification. | Medium | Maybe | Explains PULLBACK-only and TIGHT_BASE options. | Superseded by `DO_NOT_BUILD_REVISED_PROFILE_YET` and no-candidate-selected packet. |
| `docs/swing_machine_v0_1_first_paper_runbook.md` | setup | First controlled paper runbook, exact paper command requiring approval, shadow preview. | Medium | No | Operationally important later, but risky/noisy in current ChatGPT Project. | Stale/conflicting with latest paper gate `BLOCKED`; do not upload unless clearly marked blocked. |
| `docs/swing_machine_v0_1_paper_trading_review_packet.md` | testing | Paper-trading review packet saying engineering gates passed but approval required. | Medium | No | Historical paper-readiness context. | Contradicted/superseded by latest blocker refresh and candidate-selection packet; do not upload into active source pack. |
| `docs/swing_machine_v0_1_serious_full_run_readiness_decision.md` | roadmap | Older serious full run readiness decision: not ready. | Low | No | Historical safety decision. | Superseded by later guarded plans and current no-candidate-selected gate. |
| `docs/swing_machine_v0_1_guarded_serious_full_run_plan.md` | roadmap | Guarded serious full-run plan and execution placeholder. | Low | No | Historical planning context. | Current state blocks serious full run until revised candidate selection. |
| `docs/swing_machine_v0_1_historical_broad_serious_run.md` | testing | Broad historical serious offline run results and interpretation. | Low | No | Historical evidence. | Superseded by later attribution, blocker refresh, and selection packet. |
| `docs/swing_machine_v0_1_historical_broad_scanner_qualification.md` | testing | Broad scanner-density qualification results. | Medium | Optional | Good scanner-density evidence if needed. | Older evidence; current summary docs are smaller. |
| `docs/swing_machine_v0_1_historical_freeze_review_packet.md` | testing | Historical freeze review packet and operator checklist. | Low | No | Historical qualification packet. | Superseded by later blocked paper/current selection state. |
| `docs/swing_machine_v0_1_historical_qualification_run.md` | testing | Historical qualification run notes, evidence generated, replay failure, next tasks. | Low | No | Historical run context. | Superseded by later qualification/performance docs. |
| `docs/swing_machine_v0_1_decision_density_review.md` | testing | Review of decision-density issue and recommendation. | Low | No | Historical issue explanation. | Superseded by scanner-density implementation evidence. |
| `docs/swing_machine_v0_1_alpaca_manifest_promotion_plan.md` | setup | Alpaca manifest promotion plan and why promotion was blocked. | Low | No | Historical data-promotion context. | Later broad data/source decisions supersede parts. |
| `docs/swing_machine_v0_1_excluded_symbol_decision.md` | product | Decision around excluded symbols and qualification panel impact. | Low | No | Useful only for data provenance detail. | Not needed in compact Project source pack. |
| `docs/BUILD_PLAN.md` | roadmap | Short program index for older design/build phase. | Low | No | Historical orientation. | Superseded by v0.1 delivery plan/backlog/current shortlist. |
| `docs/BUILD_ROADMAP.md` | roadmap | Older build roadmap generated 2026-04-30. | Low | No | Historical workstream context. | Superseded by v0.1 docs. |
| `docs/SOLUTION_DESIGN_AND_DELIVERY_ROADMAP.md` | architecture | Older broad solution design and delivery roadmap. | Medium | Maybe | Useful for architecture origin. | Superseded/overlapped by `swing_machine_v0_1_solution_design.md`. |
| `swing_trading_bot_design_spec_v2.md` | architecture | Implementation-ready strategy spec v2.1 for RF_TPC_V2. | High | Optional | Strategy-level detail behind current config and engine. | Older than v0.1 baseline docs but still authoritative for original strategy formulas. |
| `swing_trading_bot_config_template_v2.yaml` | config | Main explicit strategy config template v2.1. | High | Yes | Core config source for baseline behavior. | Current baseline config reference. Upload with caution because it is long but important. |
| `config/swing_machine_v0_1_profile.yaml` | config | Baseline profile alias pointing at v2 config and prohibiting serious full run until qualified. | High | Yes | Connects baseline identity to explicit config. | Current, compact. |
| `config/swing_machine_v0_1_selected_periods_historical_broad.yaml` | config | Broad approved historical offline replay window config. | High | Yes | Defines broad historical window used in recent evidence. | Current for broad offline research; not paper permission. |
| `config/swing_machine_v0_1_trading212_sources.yaml` | config | Local Trading212 Alpaca/Hugging Face source DB paths and export settings. | Medium | Maybe | Important local data-source config. | Contains absolute local paths; upload only if path context is useful and safe. |
| `config/swing_machine_v0_1_selected_periods_historical.yaml` | config | Historical selected-period plan. | Medium | Optional | Useful for selected-period qualification history. | Broad config more relevant currently. |
| `config/swing_machine_v0_1_selected_periods.yaml` | config | Recent selected-period plan pointing to 2026 dates. | Low | No | Earlier selected-period plan. | Current local data ended earlier; this was corrected/superseded. |
| `config/swing_machine_v0_1_pullback_only_config.yaml` | config | Offline controlled PULLBACK-only revision config. | Medium | Maybe | Useful for historical PULLBACK-only evidence. | Superseded as deployable candidate; latest gate says do not build revised profile yet. |
| `config/swing_machine_v0_1_pullback_only_profile.yaml` | config | Profile alias for PULLBACK-only revision. | Low | No | Historical revision alias. | Not current candidate. |
| `config/swing_machine_v0_1_selected_period_data_inputs.example.yaml` | setup | Example data input plan. | Low | No | Template only. | Not needed for compact Project context. |
| `swing_trading_bot_design_spec.md` | stale | Deprecated v1 strategy spec. | Archive | No | Historical only. | Explicitly deprecated; do not upload. |
| `swing_trading_bot_config_template.yaml` | stale | Deprecated v1 config template. | Archive | No | Historical only. | Explicitly deprecated; do not upload. |
| `swing_trading_bot_codex_feedback_resolution_v2.md` | architecture | Maps review findings to v2 spec/config updates. | Medium | Optional | Useful if reviewing design rationale. | Mostly superseded by v2 spec and v0.1 docs. |
| `pyproject.toml` | setup | Python package metadata, dependencies, CLI entrypoint, test/ruff config. | High | Yes | Essential setup/testing context. | Current source of dependency/test config. |
| `examples/historical_panel_external_manifest.example.yaml` | setup | Example external historical panel manifest. | Low | No | Template/reference. | Not needed in minimal Project pack. |
| `examples/runtime_cycle_input.yaml` | setup | Example runtime cycle input. | Low | No | Useful only when running runtime examples. | Avoid upload while paper/live blocked. |
| `src/swingmachine/swing_contracts.py` | code | Typed swing domain contracts: rejection reasons, gates, quality score, universe member, candidate, signal/risk/order/lifecycle models. | High | No | Important code area, but Project source pack should not need source code unless coding support is expected. | Use inventory summary instead of uploading code. |
| `src/swingmachine/swing_adapters.py` | code | Adapters converting scored frames/setup snapshots/entry plans into typed swing candidates, signals, risk plans, order plans, lifecycle transitions. | High | No | Core research/runtime parity code. | Upload only for code-focused Project, not source-of-truth docs pack. |
| `src/swingmachine/config.py` | code | Typed strategy config loader and config hashing. | High | No | Explains explicit config behavior. | Prefer uploading YAML config and solution docs. |
| `src/swingmachine/contracts.py` | code | Large Pydantic contract definitions for bars, features, runtime, replay, reports, diagnostics. | High | No | Core schemas. | Too large; use docs unless code review needed. |
| `src/swingmachine/data_contracts.py` | code | Historical panel/data validators and manifest loading. | High | No | Data-contract implementation. | Prefer `HISTORICAL_PANEL_REQUIREMENTS.md` and runbooks. |
| `src/swingmachine/replay.py` | code | Historical replay, scanner replay, lifecycle artifact generation, parity outputs. | High | No | Core offline qualification engine. | Too large for Project source unless coding. |
| `src/swingmachine/runtime.py` | code | CLI and runtime orchestration for paper/shadow/audit/replay/reporting commands. | High | No | Operationally important. | Avoid uploading into non-code Project; runbooks summarize commands. |
| `src/swingmachine/feature_outcomes.py` | code | Feature/outcome attribution, accepted-vs-near-miss, buckets, distributions, lifecycle, exit-path, pattern diagnostics. | High | No | Current research evidence engine. | Recent code changed; upload only if ChatGPT Project will support code edits. |
| `src/swingmachine/performance.py` | code | Historical performance and provider comparison reporting. | Medium | No | Important for qualification evidence. | Docs/reports summarize current conclusions. |
| `src/swingmachine/trading212_source.py` | code | Read-only Trading212 research DB inspection/export/provider drift tooling. | Medium | No | Data-source implementation. | Data-source design docs are better for context. |
| `src/swingmachine/prepared_features.py` | code | Prepared feature panel generation from manifests. | Medium | No | Feature generation path. | Covered by feature design/data docs. |
| `src/swingmachine/backtest.py` | code | Backtest simulation and lifecycle state machinery. | Medium | No | Core mechanics. | Avoid upload unless coding. |
| `src/swingmachine/signals.py` | code | Universe eligibility, candidate scoring, setup detection. | Medium | No | Strategy behavior. | Config/spec/docs should be uploaded instead. |
| `src/swingmachine/entries.py` | code | Entry setup snapshots, portfolio heat, entry planning. | Medium | No | Risk/order mechanics. | Covered by solution/design docs. |
| `src/swingmachine/exits.py` | code | Exit evaluation, trailing stops, time stop, earnings exit. | Medium | No | Exit mechanics. | Covered by baseline/solution docs. |
| `src/swingmachine/storage.py` | code | SQLAlchemy tables and persistence helpers. | Medium | No | Operational persistence. | Runbooks and README summarize. |
| `src/swingmachine/broker.py` | code | Broker abstraction and paper broker adapter. | Medium | No | Execution interface. | Do not upload for source pack; paper/live blocked. |
| `tests/` | testing | Broad test suite covering contracts, config, data, replay, runtime, broker, monitoring, performance, feature outcomes, Trading212 source, etc. | High | No | Shows quality coverage. | Uploading full tests is not practical; summarize test areas in source pack. |
| `tests/test_feature_outcomes.py` | testing | Focused tests for attribution, near-miss, bucket, distribution, lifecycle, exit path, pattern diagnostics. | Medium | No | Important for latest research diagnostics. | Upload only if code-focused. |
| `tests/test_runtime.py` | testing | CLI/runtime workflow tests including paper/shadow/replay/report commands. | Medium | No | Operational confidence. | Avoid in compact source pack. |
| `tests/test_trading212_source.py` | testing | Read-only Trading212 data source and export tests. | Medium | No | Data-source confidence. | Upload only if code-focused. |
| `reports/swing_machine_v0_1/historical_research_artifact_index_20260508T080800Z/` | testing | Latest artifact index: 18 current artifacts, 2 superseded/context, no missing paths. | High | Maybe | Best report-map source if generated reports are needed. | Generated evidence, not stable docs; upload markdown version only if report paths matter. |
| `reports/swing_machine_v0_1/paper_readiness_blocker_refresh_20260508T081020Z/` | testing | Latest blocker refresh: paper gate blocked with five blocking items and two warnings. | High | Maybe | Critical current decision evidence. | Generated report; current docs summarize it, but markdown can be useful. |
| `reports/swing_machine_v0_1/next_baseline_candidate_selection_packet_20260508T083158Z/` | roadmap | Generated report backing `docs/swing_machine_v0_1_next_baseline_candidate_selection.md`. | High | No | Evidence behind latest selection state. | Use stable docs version instead. |
| `reports/swing_machine_v0_1/` | archive | Many generated historical, scanner, lifecycle, provider, attribution, and diagnostic report folders. | Medium | No | Evidence archive. | Do not bulk upload; too noisy and many artifacts are superseded. |
| `data/qualification_manifests/` | config | Historical panel manifests, provider manifests, selected-period manifests. | Medium | No | Important local qualification inputs. | Upload only selected manifest if debugging data; otherwise docs/config summarize. |
| `data/qualification_sources/` | archive | Exported source data from Trading212 providers. | Low | No | Raw/derived data. | Do not upload; large and not source-of-truth narrative. |
| `.pytest_cache/README.md` | stale | Pytest cache readme. | Archive | No | No project context. | Ignore. |

## Major stale or conflicting areas

| Area | Issue | Practical handling |
| --- | --- | --- |
| Paper-trading docs | `docs/swing_machine_v0_1_first_paper_runbook.md` and `docs/swing_machine_v0_1_paper_trading_review_packet.md` contain paper-run preparation language, but current gate is blocked. | Do not upload into active source pack unless clearly marked archive/superseded. |
| Serious full-run docs | Older serious-run readiness/plans and historical run reports are superseded by current no-candidate-selected decision. | Keep local/archive; upload current gate docs instead. |
| Backlog/log | Backlog and implementation log are enormous and include old/completed/superseded items. | Consolidate before uploading; upload shortlist/selection/gate docs now. |
| Strategy spec versions | v1 design/config are explicitly deprecated; v2 remains useful but v0.1 docs govern current baseline. | Upload v2 config/spec only if strategy mechanics are needed; never upload v1. |
| Build roadmap family | `BUILD_PLAN`, `BUILD_ROADMAP`, and `SOLUTION_DESIGN_AND_DELIVERY_ROADMAP` overlap with newer v0.1 docs. | Prefer v0.1 current-state/baseline/solution/delivery docs. |
| Generated reports | Many report folders encode evidence but are timestamped and often superseded. | Upload only current stable summary docs or latest markdown reports if needed. |

## Recommended interpretation

For a ChatGPT Project source of truth, the repo needs a compact control pack, not the full repository. The best pack is the current product definition, current architecture, current delivery rules, current decision gates, key config, and one or two data-provider/context docs. Avoid old runbooks that imply paper readiness.
