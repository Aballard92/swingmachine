# 01 Product Brief - swingmachine

## What this repo is for

`swingmachine` is a Python repository for designing, testing, qualifying, and eventually operating a deterministic daily-bar swing trading machine.

The repo is currently a research, qualification, and controlled-runtime project. It is not currently approved for paper trading or live trading.

## Main goal

Build a coherent `swing_machine_v0_1` baseline candidate that is:

- Mechanically complete.
- Explicitly configured.
- Research/runtime aligned.
- Fully instrumented and explainable.
- Testable through unit, contract, parity, smoke, dry-run, and historical qualification gates.
- Safe to review before any paper or live execution.

The immediate goal is not performance optimisation. The current goal is evidence-led baseline qualification and disciplined candidate selection.

## Intended users/operators

- Sponsor / Project Manager / final decision-maker: the human owner. Owns product direction, approval, prioritisation, and go/no-go decisions.
- ChatGPT Project: Product Owner, Solution Architect, and Delivery Controller. Maintains source of truth, frames options, controls roadmap, and decides what Codex should execute next when asked.
- Codex: BA, Developer, Tester, and Repo Operator. Executes bounded tasks, inspects repo state, writes code/docs where authorised, runs checks when authorised, and reports evidence back.

## What success looks like

Short-term success:

- Current truth is consolidated and not scattered across stale runbooks and generated reports.
- Codex tasks are bounded by current gates and do not drift into strategy changes.
- The next research lane is clearly defined before another profile is built.

Baseline success:

- A candidate profile has explicit config and no hidden `.env` strategy behaviour.
- Historical scanner, lifecycle, attribution, benchmark, provider, risk, and report evidence agree.
- The candidate proves a credible benchmark-relative edge before paper trading is considered.
- Paper trading is allowed only after explicit human approval of a specific command and current blocker review.

## Current product decision

Current decision state:

- No revised baseline candidate is selected.
- Paper trading is blocked.
- Serious full qualification is blocked until a revised candidate is selected for offline qualification.
- PULLBACK is `PARKED_INCONCLUSIVE`; it may re-enter only through separately
  authorised genuinely new independent evidence.
- The one authorised `SWING-PC-005A` screen stopped at Gate 0, and the separately
  authorised `SWING-PC-006` fallback ended `NO_FAMILY_PASSES_DISCOVERY`.
- H1 and H2 are parked, Gate 2 and the holdout remain unopened, and no further
  strategy-screen implementation ticket is currently authorised.
- TIGHT_BASE should be isolated from the next candidate unless explicitly redesigned and re-qualified.
- Further broad provider/data acquisition is stopped unless a new bounded task
  satisfies the five-part exception in
  `10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md`.

## Out of scope now

- Live trading.
- Real broker orders.
- Paper trading execution.
- Production deployment.
- Destructive data migrations or data rewrites.
- Performance chasing without a documented hypothesis.
- Silent strategy changes.
- Treating Hugging Face broad validation as available when current data does not support like-for-like broad coverage.
- Building a revised profile before the revised-candidate hypothesis gate is satisfied.
