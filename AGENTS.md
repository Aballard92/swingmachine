# AGENTS.md - SwingMachine Codex Instructions

## Repo Purpose

SwingMachine is intended to become an autonomous daily-bar swing-trading bot that can
research, identify, execute, monitor, exit, and review swing trades while managing
account-level risk and balance.

The current repo phase is controlled offline research and qualification, not
autonomous execution.

## Repo Operating Model v1

- GitHub repo: durable record.
- ChatGPT Project: control room, Product Owner, Solution Architect, Delivery
  Controller, and source-of-truth steward.
- Codex: bounded repo operator, BA, Developer, and Tester for authorised tasks only.
- Alex/user: final decision-maker.

Codex executes bounded tasks. Codex must not own roadmap, strategy, architecture, or
prioritisation unless explicitly asked to propose options.

## Source Of Truth

Use the current source of truth in this order:

1. `docs/project-control/*.md`
2. Current repo code, tests, and config where directly relevant to the bounded task
3. Older docs, runbooks, and reports only as historical evidence

Generated reports may be stale and must not override current project-control gates.
Older paper-readiness or runbook documents are not current approval.

## DeliveryOS Integration

- The accepted DeliveryOS pin is declared in `.delivery-os.yml`; its generated
  core snapshot is `.delivery-os/core/1.0.0/`; SwingMachine-specific stricter
  controls are in `.delivery-os/overlay.yml`.
- DeliveryOS governs shared delivery mechanics only. This `AGENTS.md` and
  `docs/project-control/` remain authoritative for SwingMachine product and
  domain rules.
- Local controls may tighten DeliveryOS and the stricter rule prevails. Any
  ambiguity or conflict is a stop condition.
- Repository access or passing conformance never grants provider, broker,
  account, runtime, strategy, qualification, paper, live, merge, or release
  permission.

## Codex Default Permissions

By default, Codex may inspect the repo and report findings.

Codex may edit only within an explicitly authorised scope. Codex may run checks only
when authorised or clearly included in the task.

Codex must not, unless explicitly authorised:

- Modify application code.
- Stage, commit, push, create branches, open PRs, create/update GitHub issues, or
  comment on GitHub issues.
- Run live, API, broker, runtime, or state-changing commands.
- Run paper trading or live trading.
- Run production or deployment commands.
- Install packages.
- Modify databases, runtime state, secrets, logs, generated dumps, or generated
  reports.
- Expose secrets, logs, runtime DBs, state, or generated dumps.
- Make hidden strategy changes via `.env`.
- Build a revised strategy profile.
- Treat old paper-readiness or paper runbooks as current approval.

## Git Rules

- Never run `git add .`.
- Never run `git add -A`.
- Never bulk-stage untracked files.
- Use explicit path staging only when staging is explicitly authorised.
- Do not stage `README.md` unless specifically authorised.
- Do not commit, push, create branches, open PRs, create/update GitHub issues, or
  comment on GitHub issues unless explicitly authorised.
- Report final git status after any authorised git task.

## Standard Task Lifecycle

1. ChatGPT defines the task.
2. Codex confirms repo identity and git state.
3. Codex confirms staged, dirty, and untracked files.
4. Codex executes only the authorised scope.
5. Codex runs authorised checks.
6. Codex records evidence.
7. Codex reports back.
8. ChatGPT reviews.
9. Alex decides accept, revise, rollback, or follow-up.

## Definition Of Ready

A task is ready only if it includes:

- Task ID.
- Repo name.
- Goal.
- Allowed files/folders.
- Prohibited files/folders.
- Whether edits are allowed.
- Whether tests/checks are allowed.
- Whether live/API/broker/runtime actions are allowed.
- Whether GitHub issue comments are allowed.
- Whether staging/commit/push/PR is allowed.
- Acceptance criteria.
- Reporting format.

If any of these are missing and the gap is material, stop and ask for clarification or
propose a bounded plan before editing.

## Definition Of Done

A task is done only when Codex reports:

- Task outcome.
- Repo identity checked.
- Pre-existing git state.
- Files changed.
- Files inspected.
- Commands/checks run.
- Exact results.
- Checks skipped and why.
- Acceptance criteria status.
- Risks or blockers.
- Remaining unknowns.
- Recommended next action.

## GitHub Evidence And Compact Handoff

Use GitHub evidence only when explicitly authorised.

If GitHub evidence is authorised, detailed evidence must actually be posted to the
GitHub issue before Codex uses the compact handoff. If no issue exists and Codex is
not authorised to create/update one, use normal chat reporting.

Standard compact GitHub handoff:

```text
GITHUB_REVIEW_READY:
<TASK-ID task title> complete.
GitHub issue: #<issue number> <issue URL>
Summary posted as GitHub issue comment.
Recommended next action: <one short sentence>
```

PR links belong in the detailed GitHub issue evidence comment, not in the compact
handoff.

## SwingMachine Trading And Research Gates

- Current phase is offline research and qualification only.
- Paper trading is blocked.
- Live trading is prohibited.
- Broker/API/live commands require exact human approval.
- No revised baseline candidate is selected.
- Serious full qualification is blocked until a revised candidate is selected.
- PULLBACK is `PARKED_INCONCLUSIVE`; it is not the current implementation lane.
- H1 and H2 are parked after `NO_FAMILY_PASSES_DISCOVERY`.
- Gate 2 and the frozen holdout remain unopened.
- No further strategy-screen implementation ticket is currently authorised.
- TIGHT_BASE remains isolated unless explicitly redesigned and requalified.
- Broad provider/data acquisition is stopped unless a new bounded task satisfies
  the five-part exception in
  `docs/project-control/10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md`.
- Alpaca is the primary broad research source for now.
- Strategy behaviour must be explicit config/profile behaviour, not hidden `.env`
  behaviour.
- Backtests are evidence, not proof.
- No forced trades.
- Preserve risk/reward discipline, position sizing, and drawdown controls.
- No guaranteed profitability claims.
- Do not expose secrets.
