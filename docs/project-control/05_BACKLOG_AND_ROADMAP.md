# 05 Backlog and Roadmap - swingmachine

## Active milestone

Current milestone: close `SWING-PC-006` after both broader candidate families
failed the preregistered discovery gate.

## Goal

Keep PULLBACK `PARKED_INCONCLUSIVE`, park H1/H2 after discovery failure, and avoid
repairing the result through threshold changes, another data source, selective
exclusions, or holdout access. Do not start paper/live trading or build a profile.

## Why this matters

The repo is mechanically stronger than before, but it has not proven a market edge.
The bounded lifecycle diagnostic clarified the main contradiction:

- 27 accepted PULLBACK observations contain only 10 submitted lifecycles.
- Four submitted lifecycles filled and six cancelled.
- Seventeen observations were repeated same-symbol signals while an existing
  lifecycle was pending or open, not independent order submissions.
- All-accepted 20-session SPY excess remains negative.
- The four filled rows are directionally positive but too small and concentrated.

The no-order ambiguity is resolved, but the edge and sample-size blockers are not.
Building a revised profile remains premature.

## Success criteria

- Current source-of-truth docs record the data limitation, acquisition stop
  condition, and refreshed diagnostic result.
- Codex receives bounded implementation/research tasks only.
- No paper/live/broker paths are triggered.
- PULLBACK remains `PARKED_INCONCLUSIVE`; re-entry requires genuinely new
  independent evidence and a separate explicit authorization.
- TIGHT_BASE remains isolated unless explicitly redesigned and accepted.
- Future candidate selection is evidence-backed.

## Out of scope

- Paper trading.
- Live trading.
- Broker orders.
- Production deployment.
- Destructive data or DB changes.
- New strategy profile implementation before the design gate passes.
- Further broad provider, repository, database, API, or Vault acquisition without
  the documented bounded exception.

## Now

1. Preserve both `SWING-PC-005A` and `SWING-PC-006` packets.
2. Keep Gate 2 and the holdout unopened.
3. Park H1 and H2; make no threshold, source, or exclusion repair by inference.

Recommended next Codex ticket:

No implementation ticket is currently authorized.

Objective:

- Product Owner accepts `NO_FAMILY_PASSES_DISCOVERY` and decides whether the
  broader-strategy research programme should pause.

## Next

Conditional future ticket requiring separate authorization:

- No source-remediation ticket is recommended: the absolute-only fallback
  produced a decisive discovery failure without needing benchmark data.
- Define candidate profile criteria if, and only if, future independent evidence
  supports it.
- Create a current active-backlog snapshot from the full backlog.
- Create a current decision log and risk register if ChatGPT Project needs lighter source files.

## Later

- Design a revised candidate profile if evidence supports one.
- Run offline selected-period or broad historical qualification for a selected candidate.
- Revisit data acquisition only after a decision-critical need passes the five-part
  exception in `10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md`.
- Reconsider paper-readiness only after all blockers are cleared and the sponsor approves a specific command.

## Blocked

- Paper trading: blocked by research-edge and sample-size evidence.
- Live trading: prohibited.
- Serious full qualification: blocked until a revised candidate is selected for offline qualification.
- TIGHT_BASE inclusion: blocked unless explicitly redesigned and re-qualified.
- Broad cross-provider validation: unavailable under current coverage and accepted
  as a research limitation.

## Rejected / Not now

- PULLBACK-only profile now: not enough evidence.
- TIGHT_BASE default inclusion: current evidence is negative.
- Bulk report upload to ChatGPT Project: too noisy and stale/conflicting.
- Building another profile variant without a design gate: rejected.
- Paper-run commands from older runbooks: not current.

## Recently completed

- Repo context inventory for ChatGPT source-pack decisions.
- Recommended source-pack list.
- Current project-control pack creation.
- Pattern-specific diagnostics.
- Provider-matched attribution comparison.
- Feature null/stability audit.
- Cost/slippage stress.
- Paper-readiness blocker refresh.
- Next candidate selection packet: no revised candidate selected.
- `SWING-PC-001`: PULLBACK fill/lifecycle research design.
- `SWING-PC-002A`: evidence source map, `READY_WITH_LIMITATIONS`.
- Bounded PULLBACK diagnostic refresh: `INCONCLUSIVE`; 17 no-order rows resolved
  through same-symbol lifecycle overlap and zero remain unexplained.
- Historical-data limitation acceptance and indefinite-acquisition stop condition.
- `SWING-PC-003`: Option A accepted; PULLBACK set to
  `PARKED_INCONCLUSIVE`; Option B not authorized.
- `SWING-PC-005`: fixed two-family broader offline hypothesis-search design,
  accepted before execution.
- `SWING-PC-005A`: one bounded execution completed with
  `STOP_SOURCE_OR_TEMPORALITY_INVALID`; no strategy outcome or holdout opened.
- `SWING-PC-006`: limitation-tolerant absolute-return screen completed with
  `NO_FAMILY_PASSES_DISCOVERY`; H1/H2 parked and holdout unopened.

## Next recommended Codex task

No further strategy-screen task is authorized.

Suggested scope:

- Preserve both stop packets.
- Do not rerun either screen, open the holdout, build a profile, acquire more
  data, or begin another strategy search by inference.
