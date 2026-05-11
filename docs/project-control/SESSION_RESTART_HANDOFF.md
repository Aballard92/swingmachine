# Session Restart Handoff - swingmachine

Saved: 2026-05-08
Repo: `/home/alexballard92/swingmachine`

## Current repo state

We are in the existing `swingmachine` repository. Do not create a nested `swingmachine` folder.

Latest work was documentation-only under `docs/project-control/` to create a compact ChatGPT Project source-of-truth pack.

## Files created/updated in the latest documentation reset

- `docs/project-control/REPO_CONTEXT_INVENTORY.md`
- `docs/project-control/RECOMMENDED_CHATGPT_SOURCE_PACK.md`
- `docs/project-control/01_PRODUCT_BRIEF.md`
- `docs/project-control/02_CURRENT_STATE.md`
- `docs/project-control/03_TARGET_ARCHITECTURE.md`
- `docs/project-control/04_DECISION_LOG.md`
- `docs/project-control/05_BACKLOG_AND_ROADMAP.md`
- `docs/project-control/06_RUN_TEST_DEPLOY_GUIDE.md`
- `docs/project-control/07_CODEX_WORKFLOW_AND_GUARDRAILS.md`
- `docs/project-control/08_OPEN_RISKS_AND_QUESTIONS.md`
- `docs/project-control/SESSION_RESTART_HANDOFF.md`

No application code, config, tests, data, reports, or existing docs outside `docs/project-control/` were intentionally changed during the source-pack reset.

## Current product/qualification truth

- Paper trading remains `BLOCKED`.
- Live trading remains prohibited.
- No revised baseline candidate is selected.
- Do not build a revised profile yet.
- Serious full qualification is blocked until a revised candidate is selected for offline qualification.
- Next best work is deeper `PULLBACK` fill/lifecycle replay research design.
- `TIGHT_BASE` should be isolated unless explicitly redesigned and re-qualified.
- Broad Hugging Face acquisition should be deferred until an Alpaca-side hypothesis shows edge.

## Operating model captured in project-control docs

- Human sponsor: final decision-maker and prioritisation owner.
- ChatGPT Project: Product Owner, Solution Architect, Delivery Controller.
- Codex: BA, Developer, Tester, Repo Operator.
- Codex should execute bounded tasks and report evidence. It should not silently own product direction, architecture, roadmap, or prioritisation.

## Recommended ChatGPT Project upload pack

Must-upload list is recorded in:

- `docs/project-control/RECOMMENDED_CHATGPT_SOURCE_PACK.md`

The pack intentionally avoids uploading the full backlog, implementation log, generated reports tree, source tree, and tests tree unless a code-focused Project is needed.

## Important stale/conflicting docs to treat with caution

Do not treat these as current authority:

- `swing_trading_bot_design_spec.md`
- `swing_trading_bot_config_template.yaml`
- `SESSION_CONTINUATION.md`
- `docs/swing_machine_v0_1_first_paper_runbook.md`
- `docs/swing_machine_v0_1_paper_trading_review_packet.md`
- `docs/swing_machine_v0_1_guarded_serious_full_run_plan.md`
- Bulk generated reports under `reports/swing_machine_v0_1/` without checking latest superseding packets.

## Recommended next ticket

`SWING-PC-001 - Design deeper PULLBACK fill/lifecycle replay research packet`

Suggested scope:

- Documentation/design only first.
- No strategy config or code changes.
- Define what evidence would prove or disprove whether PULLBACK fill/lifecycle selection is repeatable.
- Inputs should include the latest PULLBACK root-cause, pattern diagnostic, cost stress, provider comparison, and null-aware denominator evidence.
- Output should include metrics, acceptance criteria, stop conditions, and follow-up implementation tickets.

## Resume instructions for next Codex session

1. Confirm cwd is `/home/alexballard92/swingmachine`.
2. Read `docs/project-control/SESSION_RESTART_HANDOFF.md` first.
3. Read `docs/project-control/05_BACKLOG_AND_ROADMAP.md` and `docs/project-control/07_CODEX_WORKFLOW_AND_GUARDRAILS.md` next.
4. If asked to continue implementation, start with `SWING-PC-001` unless the sponsor gives a different priority.
5. Keep paper/live/broker execution blocked unless the sponsor explicitly approves an exact command.
