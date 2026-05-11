# 07 Codex Workflow and Guardrails - swingmachine

## Repo Operating Model v1

- GitHub repo: durable record.
- ChatGPT Project: control room, Product Owner, Solution Architect, Delivery
  Controller, and source-of-truth steward.
- Codex: bounded repo operator, BA, Developer, and Tester for authorised tasks only.
- Alex/user: final decision-maker.

Codex executes bounded tasks. Codex must not own product direction, architecture,
roadmap, strategy, or prioritisation unless explicitly asked to propose options.

## Source Of Truth

Use the current source of truth in this order:

1. `docs/project-control/*.md`
2. Current repo code, tests, and config where directly relevant to the bounded task
3. Older docs, runbooks, and reports only as historical evidence

Generated reports may be stale and must not override current project-control gates.
Older paper-readiness or runbook documents are not current approval.

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

If these are missing, Codex should ask for clarification or propose a bounded plan
before editing.

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

For documentation-only tasks, Done means the requested docs exist in the authorised
folder and no out-of-scope files were modified.

## Normal Chat Reporting

Use normal chat reporting for audits, documentation-only tasks, local implementation
tasks, and any task where GitHub issue workflow has not been explicitly authorised.

Final reports should include the Definition of Done fields above and any user-specified
reporting format.

## GitHub Evidence Rule

Use GitHub evidence only when explicitly authorised.

If GitHub evidence is authorised, detailed evidence must actually be posted to the
GitHub issue before Codex uses the compact handoff. If no issue exists and Codex is not
authorised to create/update one, Codex must use normal chat reporting.

Detailed GitHub issue evidence should include files changed, files inspected, checks
run, exact results, risks, acceptance criteria status, and recommended next action.
GitHub workflow does not grant permission to broaden scope.

## Standard Compact GitHub Handoff

```text
GITHUB_REVIEW_READY:
<TASK-ID task title> complete.
GitHub issue: #<issue number> <issue URL>
Summary posted as GitHub issue comment.
Recommended next action: <one short sentence>
```

PR links belong in the detailed GitHub issue evidence comment, not in the compact
handoff.

## Scope-Control Rules

- Respect the allowed file scope exactly.
- Use small controlled batches.
- Do not create nested repo folders.
- Do not modify app code during documentation-only tasks.
- Do not modify app code unless explicitly authorised.
- Do not refactor opportunistically.
- Do not fix unrelated bugs without approval.
- Do not run live/API/paper/broker/runtime/state-changing commands without explicit
  approval of the exact command.
- Do not modify DB, state, secrets, or logs without explicit approval.
- Do not install packages unless explicitly authorised.
- Do not make strategy behavior changes from `.env`.
- Do not treat old runbooks as current when newer gate docs block execution.
- If evidence contradicts the intended task, stop and report the contradiction.

## SwingMachine Trading And Research Gates

- Current phase is offline research and qualification only.
- Paper trading is blocked.
- Live trading is prohibited.
- Broker/API/live commands require exact human approval.
- No revised baseline candidate is selected.
- Serious full qualification is blocked until a revised candidate is selected.
- PULLBACK fill/lifecycle replay research is the current research lane.
- TIGHT_BASE remains isolated unless explicitly redesigned and requalified.
- Broad Hugging Face acquisition is deferred.
- Alpaca is the primary broad research source for now.
- Strategy behaviour must be explicit config/profile behaviour, not hidden `.env`
  behaviour.
- Backtests are evidence, not proof.
- No forced trades.
- Preserve risk/reward discipline, position sizing, and drawdown controls.
- No guaranteed profitability claims.
- Do not expose secrets.

## Suggested Model/Reasoning Guidance By Task Type

| Task type | Suggested reasoning | Notes |
| --- | --- | --- |
| Small docs update | Low/medium | Use current project-control docs. |
| Repo audit/synthesis | Medium | Read bounded source docs, avoid generated-report sprawl. |
| Code implementation | Medium/high | Use focused file reads and tests. |
| Architecture/design proposal | High | ChatGPT Project should own; Codex can draft options. |
| Trading safety decision | High | Human sponsor must approve final decision. |
| Paper/live operation | High plus explicit human approval | Codex must not execute without exact command approval. |
