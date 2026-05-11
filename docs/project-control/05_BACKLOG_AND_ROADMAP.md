# 05 Backlog and Roadmap - swingmachine

## Active milestone

Current milestone: reset source of truth and design the next research lane before building another profile.

## Goal

Move from scattered qualification evidence to a disciplined next step: deeper PULLBACK fill/lifecycle replay research design, without starting paper trading, live trading, or another ad hoc profile variant.

## Why this matters

The repo is mechanically stronger than before, but it has not proven a market edge. The next work must resolve the main contradiction:

- PULLBACK traded subset is positive.
- All accepted PULLBACK candidates are negative on 20-session SPY excess.
- The traded sample is too small.

Until that is understood, building a revised profile would be premature.

## Success criteria

- Current source-of-truth docs are concise and uploaded into ChatGPT Project.
- Codex receives bounded implementation/research tasks only.
- No paper/live/broker paths are triggered.
- PULLBACK fill/lifecycle hypothesis is clearly designed before any new profile is built.
- TIGHT_BASE remains isolated unless explicitly redesigned and accepted.
- Future candidate selection is evidence-backed.

## Out of scope

- Paper trading.
- Live trading.
- Broker orders.
- Production deployment.
- Destructive data or DB changes.
- New strategy profile implementation before the design gate passes.
- Broad Hugging Face acquisition before an Alpaca-side hypothesis shows edge.

## Now

1. Upload the project-control source pack into ChatGPT Project.
2. Use ChatGPT to product-own the next research design.
3. Ask Codex to execute only the next bounded ticket.

Recommended next Codex ticket:

`SWING-PC-001 - Design deeper PULLBACK fill/lifecycle replay research packet`

Objective:

- Create a docs-only research design for deeper PULLBACK replay.
- Define what evidence would prove or disprove fill/lifecycle selection.
- Define required datasets, reports, metrics, acceptance criteria, and stop conditions.
- Do not change strategy config or code unless a later ticket is approved.

## Next

Potential next tickets after `SWING-PC-001`:

- Implement offline-only PULLBACK fill/lifecycle diagnostic report if design is approved.
- Compare traded versus untraded PULLBACK candidates over more windows and provider contract data.
- Define candidate profile criteria if, and only if, deeper evidence supports it.
- Create a current active-backlog snapshot from the full backlog.
- Create a current decision log and risk register if ChatGPT Project needs lighter source files.

## Later

- Design a revised candidate profile if evidence supports one.
- Run offline selected-period or broad historical qualification for a selected candidate.
- Revisit broad Hugging Face data acquisition only after a candidate shows Alpaca-side edge.
- Reconsider paper-readiness only after all blockers are cleared and the sponsor approves a specific command.

## Blocked

- Paper trading: blocked by research-edge and sample-size evidence.
- Live trading: prohibited.
- Serious full qualification: blocked until a revised candidate is selected for offline qualification.
- TIGHT_BASE inclusion: blocked unless explicitly redesigned and re-qualified.
- Broad Hugging Face validation: blocked by current data coverage.

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

## Next recommended Codex task

`SWING-PC-001 - Design deeper PULLBACK fill/lifecycle replay research packet`

Suggested scope:

- Documentation-only.
- Create under `docs/project-control/` or `docs/` as approved by sponsor.
- Inputs: current PULLBACK root-cause packet, pattern diagnostic, cost stress, provider comparison, null-aware denominator audit.
- Output: one concise design/backlog ticket with metrics, acceptance criteria, and stop conditions.
