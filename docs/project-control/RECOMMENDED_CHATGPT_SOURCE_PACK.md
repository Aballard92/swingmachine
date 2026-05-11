# Recommended ChatGPT Source Pack for swingmachine

Created: 2026-05-08
Repo: `/home/alexballard92/swingmachine`

## 1. Must upload to ChatGPT Project

This is the smallest practical set that preserves current product, architecture, roadmap, setup, testing, operational, and risk context without importing the whole repo.

| File | Why upload |
| --- | --- |
| `README.md` | Compact repo overview, setup, runtime commands, quality gates. |
| `docs/swing_machine_current_state_review.md` | Repository-specific current-state review and gap map. |
| `docs/swing_machine_v0_1_baseline_definition.md` | Product definition for `swing_machine_v0_1`. |
| `docs/swing_machine_v0_1_solution_design.md` | Core architecture, contracts, config, parity, reporting, testing design. |
| `docs/swing_machine_v0_1_delivery_plan.md` | Delivery rules, definitions of ready/done, qualification stages. |
| `docs/swing_machine_v0_1_next_day_decision_shortlist.md` | Current concise decision state and next backlog sequence. |
| `docs/swing_machine_v0_1_revised_candidate_hypothesis_gate.md` | Current gate: do not build revised profile yet. |
| `docs/swing_machine_v0_1_next_baseline_candidate_selection.md` | Current selection decision: no revised baseline candidate selected. |
| `docs/swing_machine_v0_1_broad_huggingface_data_decision.md` | Current provider-data decision: defer broad Hugging Face acquisition. |
| `docs/swing_machine_v0_1_benchmark_relative_feature_design.md` | Current benchmark-relative feature design and behavior boundaries. |
| `docs/swing_machine_v0_1_trading212_data_solution_design.md` | Trading212 Alpaca/Hugging Face data-source architecture and caveats. |
| `config/swing_machine_v0_1_profile.yaml` | Compact baseline profile alias and serious-run prohibition. |
| `config/swing_machine_v0_1_selected_periods_historical_broad.yaml` | Broad historical offline window currently used for research evidence. |
| `swing_trading_bot_config_template_v2.yaml` | Main explicit strategy config template. |
| `pyproject.toml` | Package, dependency, CLI, pytest, and ruff setup context. |
| `docs/project-control/REPO_CONTEXT_INVENTORY.md` | This inventory and upload guidance. |
| `docs/project-control/RECOMMENDED_CHATGPT_SOURCE_PACK.md` | Practical source-pack control file. |

## 2. Useful but optional

Upload these only if the Project needs deeper implementation, qualification, or data-source detail.

| File | Why optional |
| --- | --- |
| `swing_trading_bot_design_spec_v2.md` | Detailed original strategy spec; useful if discussing formulas and design rationale. |
| `docs/HISTORICAL_PANEL_REQUIREMENTS.md` | Detailed data/replay requirements. |
| `docs/OPERATING_RUNBOOK.md` | Local commands and recovery workflows; upload only with clear paper/live blocked context. |
| `docs/swing_machine_v0_1_selected_period_runbook.md` | Selected-period qualification operations. |
| `docs/swing_machine_v0_1_huggingface_drift_investigation.md` | Provider drift rationale. |
| `docs/swing_machine_v0_1_data_source_decision.md` | Data-source decision history. |
| `docs/swing_machine_v0_1_mechanical_readiness_solution_design.md` | Mechanical readiness implementation design. |
| `docs/swing_machine_v0_1_mechanical_readiness_completion_design.md` | Mechanical readiness standard. |
| `docs/swing_machine_v0_1_multi_session_scanner_design.md` | Scanner-density architecture. |
| `docs/swing_machine_v0_1_tier2_portfolio_lifecycle_qualification_design.md` | Lifecycle qualification design. |
| `docs/swing_machine_v0_1_historical_performance_solution_design.md` | Historical performance qualification/reporting architecture. |
| `docs/swing_machine_v0_1_post_qualification_research_plan.md` | Research principles and questions after failed baseline qualification. |
| `reports/swing_machine_v0_1/historical_research_artifact_index_20260508T080800Z/historical_research_artifact_index.md` | Only if generated report paths need to be navigable in ChatGPT. |
| `reports/swing_machine_v0_1/paper_readiness_blocker_refresh_20260508T081020Z/paper_readiness_blocker_refresh.md` | Only if you want the latest blocker report verbatim. |
| `config/swing_machine_v0_1_trading212_sources.yaml` | Useful local data-source paths; upload only if absolute local paths are acceptable in Project context. |

## 3. Do not upload

| File or area | Reason |
| --- | --- |
| `swing_trading_bot_design_spec.md` | Explicitly deprecated v1 strategy spec. |
| `swing_trading_bot_config_template.yaml` | Explicitly deprecated v1 config. |
| `SESSION_CONTINUATION.md` | Old session recovery note, superseded. |
| `.pytest_cache/README.md` | No project value. |
| `docs/swing_machine_v0_1_first_paper_runbook.md` | Current paper gate is blocked; this can confuse the Project. |
| `docs/swing_machine_v0_1_paper_trading_review_packet.md` | Superseded by current blocker/selection state. |
| `docs/swing_machine_v0_1_guarded_serious_full_run_plan.md` | Current serious full run is blocked until a revised candidate is selected. |
| `docs/swing_machine_v0_1_serious_full_run_readiness_decision.md` | Older serious-run decision, superseded by current gate docs. |
| `docs/swing_machine_v0_1_historical_freeze_review_packet.md` | Superseded historical freeze context. |
| `docs/swing_machine_v0_1_historical_broad_serious_run.md` | Historical result, now superseded by later diagnostics and no-candidate decision. |
| `docs/BUILD_PLAN.md` | Older build plan superseded by v0.1 docs. |
| `docs/BUILD_ROADMAP.md` | Older roadmap superseded by v0.1 docs. |
| `data/` | Raw/generated data and manifests; too large/noisy for source pack. |
| `reports/swing_machine_v0_1/` bulk upload | Generated evidence archive with many superseded reports. Upload only selected latest markdown summaries if needed. |
| `.venv/`, `.pytest_cache/`, generated DBs | Local/generated runtime artifacts. |
| Full `src/` and `tests/` trees | Not needed for source-of-truth Project unless the Project is specifically for coding over source. |

## 4. Needs consolidating first

| File or area | Consolidation needed |
| --- | --- |
| `docs/swing_machine_v0_1_backlog.md` | Too large for compact source pack. Create a current active-backlog snapshot with open items only. |
| `docs/swing_machine_v0_1_implementation_log.md` | Very useful but too large/noisy. Create a latest-state implementation summary. |
| Paper-readiness docs | Consolidate into one current `PAPER_TRADING_STATUS.md` that says blocked and why. |
| Serious-full-run docs | Consolidate into one current `SERIOUS_FULL_RUN_STATUS.md` that says blocked until revised candidate selection. |
| Historical/revision docs | Consolidate older broad/revision results into one `HISTORICAL_EVIDENCE_SUMMARY.md`. |
| Data-provider docs | Consolidate Alpaca/Hugging Face source decision, drift investigation, broad HF decision, and Trading212 source design into one current provider policy. |
| Strategy spec/config family | Make explicit that v2 spec/config are the only active baseline design references and v1 is archive. |

## 5. Missing context that should exist but does not

| Missing doc | Why it should exist |
| --- | --- |
| `docs/PROJECT_SOURCE_OF_TRUTH.md` | A single human-readable top-level project truth file: current status, active gate, active candidate, next work, prohibited actions. |
| `docs/CURRENT_BACKLOG_SNAPSHOT.md` | Compact open-only backlog so ChatGPT does not need the 4,500+ line full backlog. |
| `docs/CURRENT_RISK_REGISTER.md` | Live list of trading safety, data, research, provider, and operational risks. |
| `docs/CURRENT_DECISION_LOG.md` | ADR-style current decisions with superseded decisions clearly marked. |
| `docs/CURRENT_TESTING_STRATEGY.md` | Concise map of unit/contract/parity/smoke/dry-run/qualification tests and when to run them. |
| `docs/CURRENT_DATA_PROVIDER_POLICY.md` | Current Alpaca/Hugging Face policy, broad-data gap, and when to revisit acquisition. |
| `docs/CURRENT_OPERATIONAL_BOUNDARIES.md` | Explicit statement of allowed offline work and prohibited paper/live/broker actions. |
| `docs/CURRENT_ARCHITECTURE_MAP.md` | Small map from docs/configs to key modules without uploading source code. |

## Practical recommendation

Upload the Must Upload set first. Do not upload the full backlog, implementation log, reports tree, source tree, or tests tree yet.

Then create one consolidation layer inside the repo before adding more context to ChatGPT:

1. `PROJECT_SOURCE_OF_TRUTH.md`
2. `CURRENT_BACKLOG_SNAPSHOT.md`
3. `CURRENT_DECISION_LOG.md`
4. `CURRENT_OPERATIONAL_BOUNDARIES.md`

Those four would likely reduce the need to upload many older, conflicting documents.
