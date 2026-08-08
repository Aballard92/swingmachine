# Swing Machine v0.1 Overnight Queue

Date: 2026-05-07

Purpose: keep offline research, diagnostics, reports, and tests moving without drifting into ad hoc strategy variants or paper/live execution.

## Hard safety gates

- Do not start paper trading.
- Do not start live trading.
- Do not submit broker orders.
- Do not deploy production jobs.
- Do not mutate source data destructively.
- Do not update the frozen broad manifest unless explicitly required and safe.
- Do not create a new revision profile until a controlled hypothesis-selection packet justifies it.

## Current gate state

- Paper trading: `BLOCKED`.
- Serious full run: `HISTORICAL_OFFLINE_ONLY_ALLOWED`.
- Current priority: prove or reject benchmark-relative signal hypotheses using offline historical evidence.

## Overnight execution order

1. `SWING-V01-177` - Accepted-only and traded-only bucket diagnostics.
2. `SWING-V01-178` - Controlled benchmark-relative hypothesis selection rerun.
3. `SWING-V01-179` - Feature bucket robustness and minimum-sample guardrails.
4. `SWING-V01-180` - Accepted-candidate excess-return distribution report.
5. `SWING-V01-181` - Traded-only lifecycle outcome decomposition.
6. `SWING-V01-182` - Exit-path diagnostic for winners, losers, and time exits.
7. `SWING-V01-183` - Pattern-specific benchmark-relative diagnostics.
8. `SWING-V01-184` - Contract-window provider enrichment feasibility.
9. `SWING-V01-185` - Provider-matched feature/outcome attribution packet.
10. `SWING-V01-186` - Provider-matched accepted-versus-near-miss comparison.
11. `SWING-V01-187` - Feature null/missingness and stability audit.
12. `SWING-V01-188` - Cost/slippage stress by pattern and bucket.
13. `SWING-V01-189` - Historical research artifact index.
14. `SWING-V01-190` - Paper-readiness blocker refresh.
15. `SWING-V01-191` - Overnight evidence summary packet.
16. `SWING-V01-192` - Backlog grooming and next-day decision shortlist.

## Stop conditions

Stop and report rather than forcing progress if:

- A task would require live/paper/broker execution.
- A task requires destructive source-data changes.
- A task requires choosing between materially different strategy architectures.
- Test failures suggest existing behavior was unintentionally changed.
- A new profile would be needed before the evidence supports it.

## Output expectations

Every completed overnight item should update:

- `docs/swing_machine_v0_1_backlog.md`
- `docs/swing_machine_v0_1_implementation_log.md`
- `reports/swing_machine_v0_1/` where the task creates evidence

Every blocked item should record:

- Why it is blocked.
- What evidence or decision is missing.
- What safe task was selected next.
