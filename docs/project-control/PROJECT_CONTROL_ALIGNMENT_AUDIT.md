# Project-Control Alignment Audit

Audit date: 2026-05-11
Repo path inspected: `/home/alexballard92/swingmachine`
Task: audit-only alignment against the GitHub + ChatGPT Project + Codex operating model

## 1. Current Repo / Project-Control Status

### Summary

SwingMachine already has a strong `docs/project-control/` control pack and is close to the intended ChatGPT Project + Codex operating model at the documentation level. The main gaps are:

- No root `AGENTS.md` was found.
- The local checkout does not appear to be a dedicated Git repository; `git rev-parse --show-toplevel` resolves to `/home/alexballard92`, with remote `https://github.com/Aballard92/CoreWorks.git`, and `swingmachine` appears untracked from that parent checkout.
- README and older runbooks still contain paper/shadow/runtime command language that can conflict with the current project-control gate unless readers start from `docs/project-control/`.
- Several project-control docs now exist beyond the eight-file standard pack, but there is not yet a single root agent instruction file to make Codex obey those boundaries automatically.

### `docs/project-control/`

`docs/project-control/` exists.

Standard pack status:

| Standard file | Status | Notes |
| --- | --- | --- |
| `01_PRODUCT_BRIEF.md` | Exists | Defines roles, product goal, current blocked paper/live state, current decision. |
| `02_CURRENT_STATE.md` | Exists | States research/offline qualification only, no revised candidate, paper blocked, live prohibited. |
| `03_TARGET_ARCHITECTURE.md` | Exists | Maps key modules and architecture guardrails; includes paper/live approval and DB/provider guardrails. |
| `04_DECISION_LOG.md` | Exists | Current decisions and rejected/superseded approaches. |
| `05_BACKLOG_AND_ROADMAP.md` | Exists | Current milestone and next lane; still references SWING-PC-001 as next, so it should be refreshed after SWING-PC-001/002A. |
| `06_RUN_TEST_DEPLOY_GUIDE.md` | Exists | Known commands and safety caveats; warns paper/live/broker commands require exact approval. |
| `07_CODEX_WORKFLOW_AND_GUARDRAILS.md` | Exists | Strong Codex workflow, DoR, DoD, reporting, and scope-control rules. |
| `08_OPEN_RISKS_AND_QUESTIONS.md` | Exists | Current technical/product/operational/data risks. |

Additional project-control files found:

- `09_PULLBACK_FILL_LIFECYCLE_REPLAY_RESEARCH_DESIGN.md`
- `RECOMMENDED_CHATGPT_SOURCE_PACK.md`
- `REPO_CONTEXT_INVENTORY.md`
- `SESSION_RESTART_HANDOFF.md`
- `SWING-PC-001_pullback_fill_lifecycle_research_design.md`
- `SWING-PC-002A_pullback_evidence_source_map.md`
- this audit: `PROJECT_CONTROL_ALIGNMENT_AUDIT.md`

### `AGENTS.md`

No root `AGENTS.md` was found.

This is the main Codex operating-model gap. The repo has guardrails in `docs/project-control/07_CODEX_WORKFLOW_AND_GUARDRAILS.md`, but Codex will not necessarily read that file unless the task or user says so. A root `AGENTS.md` should point Codex at the project-control source of truth and encode the strict repo-specific behavior.

### Older / stale docs that may conflict

These areas are explicitly risky or superseded:

| Area | Conflict risk | Current handling |
| --- | --- | --- |
| `README.md` | Contains paper/shadow/audit workflow commands and says runtime mode is `PAPER` broker only. This is useful operationally but can conflict with the current blocked paper gate. | Keep, but add a prominent project-control/current-gate pointer in a later docs batch. |
| `docs/swing_machine_v0_1_first_paper_runbook.md` | Can imply paper-run readiness. | Treat as stale/superseded unless explicitly marked blocked. |
| `docs/swing_machine_v0_1_paper_trading_review_packet.md` | Superseded by current blocker/selection state. | Do not treat as current approval. |
| `docs/swing_machine_v0_1_guarded_serious_full_run_plan.md` and serious-run docs | Serious full run is currently blocked until a revised candidate is selected. | Archive/context only. |
| `SESSION_CONTINUATION.md` | Old recovery note. | Superseded by `docs/project-control/SESSION_RESTART_HANDOFF.md` and current control docs. |
| `docs/BUILD_PLAN.md`, `docs/BUILD_ROADMAP.md`, `docs/SOLUTION_DESIGN_AND_DELIVERY_ROADMAP.md` | Older planning/control docs overlap with current v0.1/project-control docs. | Use current project-control docs first. |
| `swing_trading_bot_design_spec.md`, `swing_trading_bot_config_template.yaml` | Deprecated v1 strategy spec/config. | Archive only; v2 and v0.1 docs govern current baseline. |
| Full backlog / implementation log | Very large and mixed with completed/superseded work. | Use current project-control summaries unless forensic detail is needed. |

### Generated/runtime files that should not be source of truth

Do not treat these as source of truth:

- `.venv/`
- `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`
- `tests/__pycache__/`, `migrations/__pycache__/`
- `src/swingmachine.egg-info/`
- bulk `reports/swing_machine_v0_1/`
- bulk `data/`
- local SQLite/database/runtime outputs, if present
- logs/state/output folders, if present later

Generated reports can be evidence, but current stable docs should decide which reports are current.

## 2. Gap Analysis Against Standard Pack

| Item | Status | Gap |
| --- | --- | --- |
| `01_PRODUCT_BRIEF.md` | Present | No gap. |
| `02_CURRENT_STATE.md` | Present | No gap. |
| `03_TARGET_ARCHITECTURE.md` | Present | No gap. |
| `04_DECISION_LOG.md` | Present | No gap. |
| `05_BACKLOG_AND_ROADMAP.md` | Present | Needs refresh because SWING-PC-001 and SWING-PC-002A now exist; it still names SWING-PC-001 as next. |
| `06_RUN_TEST_DEPLOY_GUIDE.md` | Present | Mostly aligned; consider adding Git-root warning and current “no tests for docs-only audits” convention. |
| `07_CODEX_WORKFLOW_AND_GUARDRAILS.md` | Present | Strong, but should be referenced from root `AGENTS.md`. |
| `08_OPEN_RISKS_AND_QUESTIONS.md` | Present | Good; could add GitHub/repo-root alignment risk. |
| `AGENTS.md` | Missing | Create root `AGENTS.md` in a later approved task. |

GitHub durable-source gap:

- No repo-local `.git` directory was found.
- The current Git root resolves to `/home/alexballard92`, not `/home/alexballard92/swingmachine`.
- The detected remote is `Aballard92/CoreWorks`, not a SwingMachine-specific remote.
- `git status --short -- .` from the SwingMachine directory reports `?? ./`, which means the whole SwingMachine folder appears untracked from the parent Git root.

This should be resolved or explicitly documented before assuming GitHub is the durable source of truth for SwingMachine.

## 3. Codex Safety Alignment

| Safety topic | Status | Evidence / gap |
| --- | --- | --- |
| Codex role | Documented | `01_PRODUCT_BRIEF.md` and `07_CODEX_WORKFLOW_AND_GUARDRAILS.md` define Codex as BA, Developer, Tester, Repo Operator for bounded tasks. |
| Product direction ownership | Documented | Project-control docs say Sponsor/ChatGPT Project own product direction, roadmap, prioritisation, architecture decisions. |
| Definition of Ready | Documented | `07_CODEX_WORKFLOW_AND_GUARDRAILS.md` has a clear DoR. |
| Definition of Done | Documented | `07_CODEX_WORKFLOW_AND_GUARDRAILS.md` has a clear DoD and reporting shape. |
| Write permissions | Partially documented | Scope-control rules exist, but there is no root `AGENTS.md` permission matrix. |
| Live/API permissions | Partially documented | Paper/live/broker prohibitions are strong. API/provider/data-source permissions are implied by provider docs and config cautions but not consolidated in root guidance. |
| DB/state permissions | Partially documented | Destructive data/database changes are prohibited in project-control docs. Runtime DB/state/log handling should be explicit in `AGENTS.md`. |
| Secret handling | Partially documented | `06_RUN_TEST_DEPLOY_GUIDE.md` says `.env` may contain credentials and secrets must not be exposed. Root `AGENTS.md` should reinforce this. |
| Reporting format | Documented | `07_CODEX_WORKFLOW_AND_GUARDRAILS.md` defines final reporting requirements. |
| Batching rules | Partial / weak | Current docs imply bounded tasks and current tickets, but do not define a standard “small safe batch” migration pattern. |
| No broad refactor rule | Documented | `07_CODEX_WORKFLOW_AND_GUARDRAILS.md` says do not refactor opportunistically and do not fix unrelated bugs without approval. |
| Git/GitHub behavior | Gap | No root guidance says how to handle the current parent Git root / missing repo-local `.git` issue. |

## 4. Trading-Specific Gaps

| Trading control | Status | Notes |
| --- | --- | --- |
| No guaranteed profitability claims | Partial | Current docs repeatedly say edge is not proven, but a plain “no guaranteed profitability” warning should be explicit in `AGENTS.md` or operational boundaries. |
| Backtesting as evidence, not proof | Mostly documented | README and current docs distinguish machinery validation/evidence from performance proof; this should be consolidated. |
| Shadow/paper before live use | Documented historically; currently blocked | README and older runbooks describe shadow/paper workflows, while project-control blocks paper/live. Need a current status wrapper to avoid confusion. |
| No forced trades | Gap / not explicit | No concise current project-control rule found that says the system must allow no-trade outcomes and must not force trades. |
| Risk/reward discipline | Partial | Strategy spec/config document risk sizing, stops, and targets, but current project-control docs do not consolidate risk/reward rules. |
| Position sizing | Documented in strategy spec/config, partial in project-control | Needs concise current-source summary if ChatGPT Project is to own product direction. |
| Drawdown controls | Documented in strategy spec/config | Project-control should point to active config and clarify no live/paper drawdown control is currently operationally approved. |
| Broker/live order approval rules | Strong | Current docs repeatedly require explicit human approval for paper/live/broker commands. |
| Rejected candidate / no-trade tracking | Partial | Scanner/replay/reporting artifacts track rejections and no-candidate outcomes, but product-control docs should name this as a required research behavior. |
| Provider/data limitations | Strong | Current docs clearly block broad Hugging Face assumptions and warn against merging providers without policy. |
| No profile-building without gate | Strong | Current docs clearly block revised profile builds before the design gate passes. |

## 5. Recommended Safe Migration Plan

Do not apply this migration until explicitly approved.

Smallest safe batch:

1. Create root `AGENTS.md`.
   - Point Codex to `docs/project-control/01_PRODUCT_BRIEF.md` through `08_OPEN_RISKS_AND_QUESTIONS.md`.
   - State that `docs/project-control/` is the source-of-truth control layer.
   - State that Codex must not own product direction, architecture, roadmap, or prioritisation.
   - State docs-only tasks may only modify authorised docs.
   - State code/config/tests/data/reports/migrations/runtime paths are off limits unless explicitly permitted.
   - State paper/live/broker/API commands require exact human approval.
   - State DB/state/log/secrets are not to be modified or exposed unless explicitly permitted.
   - State no broad refactors, no unrelated fixes, and no hidden `.env` strategy behavior.
   - State the current Git-root warning: this directory is not currently a repo-local Git checkout.

2. Create a current operational boundary doc under `docs/project-control/`, or update the standard pack with a clear boundary section.
   - Candidate name: `docs/project-control/CURRENT_OPERATIONAL_BOUNDARIES.md`.
   - Purpose: one short source-of-truth page for paper/live/broker/API/DB/state/secrets/config/data/report permissions.

3. Refresh `05_BACKLOG_AND_ROADMAP.md`.
   - Mark SWING-PC-001 complete/accepted.
   - Mark SWING-PC-002A complete/audit.
   - Set next likely task to review/approve `SWING-PC-002A`, then implement `SWING-PC-002` only if accepted.

4. Add a README banner in a later docs batch.
   - The README should point readers to `docs/project-control/` for current gate status before running paper/shadow/runtime commands.
   - This reduces confusion from older operational commands without deleting useful runbook content.

5. Resolve GitHub source-of-truth status.
   - Decide whether SwingMachine should be its own GitHub repo, a tracked subdirectory of `CoreWorks`, or another arrangement.
   - Do not commit/push/create PR until the desired repository ownership is explicit.

Defer:

- Any source code edits.
- Any test edits.
- Any config/profile edits.
- Any generated report cleanup.
- Any paper/live/broker/runtime command.
- Any migration or database/state change.

## 6. Sources Reviewed

Read-only inspection covered:

- repo root listing and top-level file inventory
- `README.md`
- `pyproject.toml`
- `.github/workflows/ci.yml`
- `docs/project-control/`
- selected current docs in `docs/`
- project-control source pack and inventory files
- selected config file names and current config references
- report/data/cache/runtime directory names
- local Git root and remote metadata

No tests were run.
No package installs were run.
No paper/live/broker/API commands were run.

## 7. Risks / Unknowns

- The GitHub durable-source-of-truth status is not aligned until the repo-local Git arrangement is clarified.
- Root `AGENTS.md` is missing, so Codex behavior currently depends on the user or agent reading project-control docs manually.
- README operational commands can be misread without current gate context.
- Generated reports are numerous and can confuse current truth if read directly.
- The current standard pack is strong, but there is not yet one short operational-boundaries page.
- Trading-specific “no forced trades” and “no guaranteed profitability” rules should be made explicit.

## 8. Recommended Next Codex Task

Recommended next task:

`SWING-PC-003 - Add root AGENTS.md and current operational boundaries doc`

Suggested scope:

- Documentation-only.
- Create root `AGENTS.md`.
- Create `docs/project-control/CURRENT_OPERATIONAL_BOUNDARIES.md` or equivalent.
- Optionally refresh `docs/project-control/05_BACKLOG_AND_ROADMAP.md` to reflect SWING-PC-001 and SWING-PC-002A completion.
- Do not edit application code, tests, configs, data, reports, migrations, runtime paths, DB/state/logs/secrets, or strategy profiles.
- Do not run paper/live/broker/API commands.

## 9. Audit Confirmation

This audit created only:

- `docs/project-control/PROJECT_CONTROL_ALIGNMENT_AUDIT.md`

No application source code, tests, configs, data, generated reports, migrations, runtime state, logs, databases, secrets, or strategy profiles were modified by this audit.

No paper trading, live trading, broker commands, package installs, historical replays, tests, destructive commands, or API operations were run.
