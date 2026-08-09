# AGENTS.md - SwingMachine Codex Instructions

## Repo Purpose

SwingMachine is intended to become an autonomous daily-bar swing-trading bot that can
research, identify, execute, monitor, exit, and review swing trades while managing
account-level risk and balance.

The current repo phase is controlled offline research and qualification, not
autonomous execution.

## Repo Operating Model v2

- GitHub repo: durable delivery contract, change history, PR review, and evidence record.
- ChatGPT Project: control room, Product Owner, Solution Architect, Delivery
  Controller, issue-contract author, independent reviewer, and source-of-truth steward.
- Codex: bounded repo operator, BA, Developer, and Tester for authorised tasks only.
- Alex/user: Sponsor and final decision-maker.

Codex executes bounded tasks. Codex must not own roadmap, strategy, architecture, or
prioritisation unless explicitly asked to propose options.

## Source Of Truth And Task Authority

Product and domain truth remains local to SwingMachine. Use it in this order:

1. `docs/project-control/*.md`
2. Current repo code, tests, and config where directly relevant to the bounded task
3. Older docs, runbooks, and reports only as historical evidence

For delivery execution, one authoritative GitHub issue freezes the bounded task
contract. The issue may narrow permissions and scope but may not silently override
product/domain rules above. Any conflict is a stop condition.

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

## GitHub-First Issue-As-Contract Workflow

Every bounded Codex delivery task must have exactly one authoritative GitHub issue
before execution starts. Chat analysis, a `/goal`, a branch, a commit, or a PR may
point to that issue but may not replace or widen it.

The issue contract is drafted and maintained by ChatGPT and accepted by the Sponsor.
It must freeze at least:

- outcome and why now;
- accepted state;
- included and excluded scope;
- architecture and ownership boundaries;
- trust model and evidence limits;
- allowed and prohibited permissions;
- deliverables;
- acceptance criteria;
- independent tests/checks;
- evidence required;
- defect policy;
- stop conditions;
- change control;
- PR/merge policy;
- handover format.

Once implementation starts, material scope, permission, trust-model, or acceptance
changes require an explicit issue amendment accepted by the Sponsor. Codex must stop
rather than infer permission.

For tasks that change repository files:

1. Work on an issue-linked branch created from the authorised base.
2. Change only issue-authorised paths.
3. Open one issue-linked PR for the coherent delivery.
4. Put detailed completion evidence on the authoritative issue and link the PR.
5. ChatGPT independently reviews the issue contract, diff, evidence, and checks.
6. Alex/Sponsor explicitly accepts, revises, rejects, rolls back, or defers.
7. Merge and issue closure happen only after explicit Sponsor acceptance.

Direct-to-`main` delivery is prohibited. Green CI, a PR, a Codex completion claim, or
repository access never constitutes Sponsor acceptance.

For bounded tasks with no repository change, the authoritative issue still records the
contract and detailed evidence; no empty PR is required.

## Codex Default Permissions

By default, Codex may inspect the SwingMachine repo and the active authorised GitHub
issue, and report findings.

For an active issue contract Codex may post completion or blocker evidence to that
issue when the issue explicitly authorises GitHub evidence. Codex must not create,
rewrite, close, relabel, reprioritise, or broaden GitHub issues unless separately
authorised.

Codex may edit only within an explicitly authorised issue scope. Codex may run checks
only when authorised by that issue.

Codex must not, unless explicitly authorised:

- Modify application code.
- Stage, commit, push, create branches, or open PRs outside the active issue contract.
- Create, amend, close, relabel, or reprioritise GitHub issues.
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

## Cross-Repo Boundary

Trading212 is read-only from the SwingMachine project. SwingMachine tasks may not edit,
commit, branch, comment on, open/close issues in, run state-changing commands in, or
otherwise mutate Trading212 unless Alex explicitly approves a separate Trading212
issue contract. Cross-project architecture comparison never grants mutation authority.

## Git Rules

- Never run `git add .`.
- Never run `git add -A`.
- Never bulk-stage untracked files.
- Use explicit path staging only when staging is authorised by the active issue.
- Do not stage `README.md` unless specifically authorised.
- Do not deliver directly to `main`.
- Branch, commit, push, and PR permissions come only from the active issue contract.
- Report final git status after any authorised git task.

## Standard Task Lifecycle

1. ChatGPT defines and creates the authoritative GitHub issue contract.
2. Alex/Sponsor accepts the task scope/permissions or requests amendment.
3. Codex confirms issue identity, repo identity, base branch/HEAD, and git state.
4. Codex confirms staged, dirty, and untracked files and preserves unrelated work.
5. Codex executes only the frozen issue scope.
6. Codex runs only authorised checks.
7. Codex records detailed evidence on the issue and links the PR when one exists.
8. Codex returns the compact GitHub handoff in chat.
9. ChatGPT independently reviews the issue, diff, evidence, and checks.
10. Alex decides accept, revise, rollback, reject, or follow-up.
11. Merge/closure occurs only after explicit Sponsor acceptance.

## Definition Of Ready

A task is ready only when its authoritative GitHub issue contains the DeliveryOS
contract fields required by `.delivery-os/core/1.0.0/docs/04-issue-as-contract.md` and
makes the following operational permissions unambiguous:

- edits allowed or prohibited;
- tests/checks allowed or prohibited;
- GitHub evidence/comment permission;
- branch/commit/push/PR permission;
- live/API/broker/runtime/provider/data permission;
- acceptance criteria;
- reporting/handover format.

If a material field is missing or conflicts with project/domain rules, stop before
editing and escalate through the issue contract.

## Definition Of Done

A task is done only when the issue evidence records:

- task outcome;
- repo and issue identity checked;
- pre-existing git state;
- files changed;
- files inspected;
- commands/checks run and exact results;
- checks skipped and why;
- acceptance-criteria status;
- risks/blockers;
- remaining unknowns;
- PR/change identity where applicable;
- recommended next action;
- explicit confirmation that prohibited surfaces remained untouched.

A Codex `done` claim is evidence for review, not Sponsor acceptance.

## Standard Compact GitHub Handoff

Detailed evidence belongs on the authoritative issue. The chat response should normally
be only:

```text
GITHUB_REVIEW_READY:
<TASK-ID task title> complete.
GitHub issue: #<issue number> <issue URL>
PR: #<pr number> <PR URL> | NONE (no repository change)
Evidence posted to issue.
Recommended next action: <one short sentence>
```

If blocked, replace `GITHUB_REVIEW_READY` with `GITHUB_BLOCKED` and state the stop
condition in one sentence. ChatGPT then reads GitHub evidence directly.

## SwingMachine Trading And Research Gates

- Current phase is offline research and qualification only.
- Paper trading is blocked.
- Live trading is prohibited.
- Broker/API/live commands require exact human approval.
- No revised baseline candidate is selected.
- Serious full qualification is blocked until a revised candidate is selected.
- PULLBACK is `PARKED_INCONCLUSIVE`; it is not the current implementation lane.
- H1 and H2 are parked after `NO_FAMILY_PASSES_DISCOVERY`, pending current
  research-validity review of whether that evidence is suitable for strategy selection.
- Gate 2 and the frozen holdout remain unopened.
- No new strategy-screen implementation is authorised before research-validity review.
- TIGHT_BASE remains isolated unless explicitly redesigned and requalified.
- Broad provider/data acquisition is stopped unless a new bounded task satisfies
  the five-part exception in
  `docs/project-control/10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md`.
- Available provider credit does not itself grant acquisition permission.
- Alpaca is the primary broad research source for now unless a future accepted issue
  changes the provider policy for a decision-critical need.
- Strategy behaviour must be explicit config/profile behaviour, not hidden `.env`
  behaviour.
- Backtests are evidence, not proof.
- No forced trades.
- Preserve risk/reward discipline, position sizing, and drawdown controls.
- No guaranteed profitability claims.
- Do not expose secrets.
