# 07 Codex Workflow and Guardrails - swingmachine

## Operating model

SwingMachine uses DeliveryOS 1.0.0 for shared delivery mechanics with stricter local
controls.

- GitHub: durable issue contract, branch/PR history, and delivery evidence.
- ChatGPT Project: Product Owner, Solution Architect, Delivery Controller,
  source-of-truth steward, issue-contract author, and independent reviewer.
- Codex: bounded BA, Developer, Tester, and Repo Operator.
- Alex/user: Sponsor and final decision-maker.

Codex does not own product direction, trading strategy, architecture, roadmap, or
prioritisation unless explicitly asked to propose options.

## Source of truth

Product/domain authority remains:

1. `docs/project-control/*.md`
2. Current repo code, tests, and config where directly relevant
3. Older docs, runbooks, and reports only as historical evidence

For one bounded delivery, the authoritative GitHub issue is the frozen execution
contract. It may narrow permissions but cannot override stricter product/domain rules.
A conflict is a stop condition.

## DeliveryOS GitHub-first default

Every bounded Codex delivery task must have one authoritative GitHub issue before
execution. Large chat prompts are no longer the durable task contract.

ChatGPT creates and maintains the issue. The issue freezes:

- outcome and `why_now`;
- accepted state;
- included/excluded scope;
- architecture and ownership;
- trust model and evidence limits;
- allowed/prohibited permissions;
- deliverables;
- acceptance criteria;
- independent tests/checks;
- evidence required;
- blocking-defect versus follow-up-hardening policy;
- stop conditions;
- change control;
- PR/merge policy;
- handover.

Once execution begins, Codex must not widen the contract. A material change requires an
explicit issue amendment drafted through ChatGPT and accepted by the Sponsor.

## Standard delivery lifecycle

1. ChatGPT creates the GitHub issue contract.
2. Sponsor accepts the bounded scope/permissions.
3. Codex reads the issue and confirms repo/base identity plus existing git state.
4. If repository files will change, Codex works on the issue-linked branch only.
5. Codex executes only the frozen contract and runs only authorised checks.
6. Codex opens/updates the issue-linked PR when repository changes are part of scope.
7. Codex posts detailed completion/blocker evidence to the issue.
8. Codex returns only the compact GitHub handoff in chat.
9. ChatGPT independently reviews the issue, diff, evidence, and checks.
10. Sponsor chooses accept, revise, reject, rollback, defer, or follow-up.
11. Merge and issue closure happen only after explicit Sponsor acceptance.

A PR, green CI, passing conformance, or Codex completion statement does not itself grant
acceptance.

## Repository-change policy

If a task changes repository files:

- one authoritative issue is required;
- use an issue-linked branch from the authorised base;
- direct-to-`main` delivery is prohibited;
- stage explicit paths only;
- never use `git add .` or `git add -A`;
- preserve unrelated staged/dirty/untracked work;
- one coherent issue-linked PR should carry the delivery;
- required fixes for frozen acceptance stay in the same feature unless the Sponsor
  explicitly changes the contract;
- merge is Sponsor-controlled after ChatGPT review.

If a bounded task produces no repository change, no empty PR is required; the issue
still carries the contract and detailed evidence.

## GitHub permissions

For an active authorised issue, Codex may read that issue and post evidence only when
its contract allows GitHub evidence.

Codex must not create, rewrite, close, relabel, reprioritise, or broaden GitHub issues
unless separately authorised. It must not infer GitHub mutation rights from repository
access.

## Default prohibited actions

Unless the active issue explicitly authorises them, Codex must not:

- modify application code, tests, config, data, reports, databases, runtime state,
  secrets, logs, or generated dumps;
- install packages;
- run provider/API/network acquisition;
- run broker/account/order actions;
- run paper or live trading;
- run production/deployment commands;
- make hidden strategy changes through `.env`;
- build or select a revised strategy profile;
- open Gate 2 or the frozen holdout;
- use old runbooks as permission;
- mutate another repository.

## Trading212 hard boundary

Trading212 is read-only from the SwingMachine project.

A SwingMachine issue may explicitly authorise read-only Trading212 inspection for a
bounded cross-project evidence question. That never grants mutation authority. A
SwingMachine task may not edit Trading212 files, run state-changing commands there,
create/update its issues, branch/commit/push, or otherwise mutate it. Any Trading212
mutation requires a separate explicit Sponsor-approved Trading212 issue contract.

## Definition of Ready

A Codex task is Ready when the authoritative issue has all DeliveryOS issue-contract
fields and makes these permissions unambiguous:

- repo and task identity;
- edits and allowed paths;
- prohibited paths/surfaces;
- tests/checks;
- GitHub evidence/comment permission;
- branch/commit/push/PR permission;
- provider/API/data permission;
- broker/paper/live/runtime permission;
- acceptance criteria;
- evidence/reporting format;
- stop conditions.

If a material field is absent or conflicts with current project rules, stop before
editing and escalate through the issue.

## Definition of Done

Detailed issue evidence must record:

1. task outcome;
2. repo and issue identity;
3. base/branch/HEAD and pre-existing git state;
4. files inspected;
5. files changed;
6. commands/checks run and exact results;
7. checks skipped and why;
8. acceptance-criteria status;
9. blocking defects or risks;
10. remaining unknowns;
11. PR/change identity where applicable;
12. exactly one recommended next action when requested;
13. explicit confirmation that prohibited surfaces remained untouched.

For documentation-only tasks, Done still requires the requested artifact, scope
integrity, evidence, and reviewability.

## Compact Codex handoff

After evidence is posted to GitHub, Codex should return:

```text
GITHUB_REVIEW_READY:
<TASK-ID task title> complete.
GitHub issue: #<issue number> <issue URL>
PR: #<pr number> <PR URL> | NONE (no repository change)
Evidence posted to issue.
Recommended next action: <one short sentence>
```

If a stop condition fires:

```text
GITHUB_BLOCKED:
<TASK-ID task title> stopped.
GitHub issue: #<issue number> <issue URL>
Stop condition: <one sentence>
Evidence posted to issue.
```

ChatGPT reads the durable evidence directly; Codex should not duplicate a large report
into chat unless specifically asked.

## Current SwingMachine research gates

- Current phase: offline research and qualification only.
- Paper trading: blocked.
- Live trading: prohibited.
- No revised baseline candidate is selected.
- PULLBACK remains `PARKED_INCONCLUSIVE`.
- TIGHT_BASE remains isolated unless explicitly redesigned and requalified.
- H1/H2 were parked after `NO_FAMILY_PASSES_DISCOVERY`, but the suitability of that
  evidence for programme-level strategy rejection is now under research-validity
  review.
- Gate 2 and the frozen holdout remain unopened.
- No new strategy screen or revised profile is authorised before the validity review.
- Further provider/data acquisition requires a new decision-critical issue satisfying
  `10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md`; unused provider credit is not
  permission.
- Strategy behaviour remains explicit in reviewed config/profile files, never hidden
  environment settings.
- Backtests are evidence, not proof.
- No forced trades or guaranteed-profitability claims.

## Suggested model/reasoning guidance

| Task type | Suggested reasoning | Notes |
| --- | --- | --- |
| Small docs update | Low/medium | Current project-control + active issue. |
| Repo audit/synthesis | Medium/high | Exact lineage and evidence; avoid generated-report sprawl. |
| Code implementation | Medium/high | Focused paths and independent tests. |
| Architecture/design proposal | High | ChatGPT owns direction; Codex may evidence/test bounded questions. |
| Research-validity/backtest logic | Highest available | Can change interpretation of trading evidence. |
| Trading safety decision | High | Sponsor owns final decision. |
| Paper/live operation | Highest + exact human approval | Not currently authorised. |
