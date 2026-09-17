# 05 Backlog and Roadmap - swingmachine

## Active reset backlog — 8 September 2026

The sponsor accepted the offline reset direction, requested an elaborated backlog
and authorised work to begin. The active queue and task acceptance boundaries are
in [SWING_RF_BACKLOG.md](SWING_RF_BACKLOG.md). RF-001 delivered the foundation;
RF-002 delivered the shared input preflight, source contract and readiness
catalogue. RF-003 daily/reference mechanics, RF-004 executable fills and RF-005
numerical evaluation mechanics are implemented. Real daily data remains
unqualified. Discovery, independent evaluation and operational qualification
remain conditional on the outstanding evidence gates.
See [RF-002 delivery](SWING-RF-002_INPUT_CONTRACT_AND_READINESS.md).

Current goal checkpoint: RF-003 adapter/reference mechanics and Trading212
calendar/reader adoption are delivered; real source qualification remains open.
RF-004's executable minute engine and active CLI are implemented and verified:
30 final execution/replay tests plus 133 existing focused regressions pass, and
nine retained 60-session synthetic trials reconcile. See
[RF-004 evidence](SWING-RF-004_EXECUTION_DESIGN.md).

RF-005's numerical freeze, funded SPY benchmark, lagged-exposure diagnostic and
joint block-bootstrap calculations are implemented; all 186 focused research
tests pass. See [evaluation evidence](SWING-RF-005_EVALUATION_FREEZE.md).
Next: specify the smallest real-source/reference qualification increment and
resolve suitable independent date coverage. The calendar establishes only 283
permitted-interval sessions after warmup; validation/final dates remain unassigned.
The full three-objective goal remains active. Historical references, official
decoder parity, clearing-calendar and fill qualification remain separate
dependencies. See [Trading212 adoption](SWING-RF-003_TRADING212_ADOPTION.md).

No candidate has been promoted and no trading gate is opened. The older roadmap
below is historical context; its stop on new offline research is superseded for
this sponsor-authorised reset.

## Historical roadmap — pre-reset milestone

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
