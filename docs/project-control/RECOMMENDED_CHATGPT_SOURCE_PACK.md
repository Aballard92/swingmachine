# Recommended ChatGPT Source Pack for SwingMachine

Updated: 2026-08-08

## Compact current-control pack

Use these files together. They are small enough to review as one control packet
and are ordered from operating authority to supporting decisions:

1. `AGENTS.md`
2. `docs/project-control/01_PRODUCT_BRIEF.md`
3. `docs/project-control/02_CURRENT_STATE.md`
4. `docs/project-control/03_TARGET_ARCHITECTURE.md`
5. `docs/project-control/04_DECISION_LOG.md`
6. `docs/project-control/05_BACKLOG_AND_ROADMAP.md`
7. `docs/project-control/06_RUN_TEST_DEPLOY_GUIDE.md`
8. `docs/project-control/07_CODEX_WORKFLOW_AND_GUARDRAILS.md`
9. `docs/project-control/08_OPEN_RISKS_AND_QUESTIONS.md`
10. `docs/project-control/10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md`
11. `docs/project-control/SWING-PC-003_pullback_lane_decision_packet.md`
12. `docs/project-control/SWING-PC-005_broader_offline_hypothesis_search_design.md`
13. `docs/project-control/SWING-PC-006_limitation_tolerant_exploratory_screen_design.md`
14. `docs/project-control/SESSION_RESTART_HANDOFF.md`
15. `docs/project-control/EXTERNAL_HELP_HANDOFF.md`
16. `docs/evidence/2026-07-29-current-decision-evidence.md`

The current headline is: offline research only; no revised candidate; PULLBACK,
H1, and H2 parked; holdout unopened; paper blocked; live prohibited; no current
strategy implementation ticket.

## Add only when needed

- `README.md` for repository orientation and offline quality checks.
- `docs/README.md` for document authority and archive rules.
- `config/swing_machine_v0_1_profile.yaml` for the historical/mechanical baseline
  alias and its explicit non-candidate warning.
- `config/swing_machine_v0_1_trading212_sources.example.yaml` for the portable
  provider-source schema, never a populated machine-local copy.
- `swing_trading_bot_config_template_v2.yaml` and
  `swing_trading_bot_design_spec_v2.md` for historical implementation context;
  neither authorizes a candidate or trading action.
- A named source/test file only for a bounded code-review task.

## Do not use as current authority

- `docs/archive/`.
- Older runbooks, plans, reviews, backlogs, and design packets elsewhere under
  `docs/`.
- Deprecated v1 root spec/config files.
- Generated `reports/`, raw/generated `data/`, databases, logs, caches, `.env`,
  secrets, or populated local source configuration.
- The full source and test trees when only product/governance context is needed.

Generated evidence may be selected by exact path and verified against the hashes
in the evidence index, but it does not override current project-control gates.

## Refresh rule

When a controlling decision changes, update the affected project-control files,
the restart and external-help handoffs, and the evidence index in the same bounded
change. Do not solve drift by adding another competing current-status document.
