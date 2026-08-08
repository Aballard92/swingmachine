# Swing Machine v0.1 Controlled Revision Design

## Purpose

This document defines controlled offline-only revision candidates after the first `swing_machine_v0_1` baseline candidate failed historical profitability qualification.

The goal is not to optimize performance opportunistically. The goal is to design explicit, reviewable hypotheses that can be compared against the frozen baseline using the same historical evidence pipeline.

## Current frozen baseline evidence

Frozen baseline evidence is the current mechanical and performance packet set:

- Mechanical readiness: `reports/swing_machine_v0_1/mechanical_readiness_20260507T125344Z.json`
- Broad scanner attribution: `reports/swing_machine_v0_1/scanner_broad_research_20260507T164230Z/`
- Broad lifecycle replay: `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T155720Z/`
- Broad attributed performance: `reports/swing_machine_v0_1/historical_performance_attributed_20260507T183207Z/`
- Qualification decision: `reports/swing_machine_v0_1/historical_performance_qualification_20260507T184000Z.json`
- Diagnostic report: `reports/swing_machine_v0_1/historical_performance_diagnostics_20260507T190000Z.json`
- TIGHT_BASE audit: `reports/swing_machine_v0_1/tight_base_mechanical_audit_20260507T191500Z.json`

## Current decision

Paper trading remains blocked.

The current baseline is mechanically credible but not profitable enough to promote:

- Broad total return is slightly negative.
- Broad excess return versus SPY is materially negative.
- TIGHT_BASE lost 5/5 trades in the broad slice.
- PULLBACK was positive in the broad slice.
- Provider contract-window robustness passed mechanically, but both providers underperformed benchmark.

## Revision principles

- Revisions must be explicit config/profile changes, not hidden code behavior.
- Revisions must be offline-only until qualification passes.
- The frozen baseline must remain reproducible for comparison.
- Each revision must have one primary hypothesis.
- No revision can be promoted from one lucky metric.
- Paper trading remains blocked until a revised candidate passes mechanical, historical, benchmark, attribution, and provider checks.

## Candidate revision A: PULLBACK-only baseline

Hypothesis: The initial baseline combines a profitable PULLBACK pattern with a damaging TIGHT_BASE pattern. A PULLBACK-only candidate may produce cleaner expectancy while preserving the existing engine, lifecycle, risk, order, and reporting architecture.

Configuration intent:

- Disable TIGHT_BASE from setup selection.
- Keep PULLBACK rules, scoring, risk, exits, order planning, lifecycle, costs, and reporting unchanged.
- Keep the same manifest, benchmark, and provider-comparison workflow.

Acceptance gates:

- Mechanical readiness remains PASS.
- Broad historical total return is positive.
- Broad excess return versus SPY is materially improved versus frozen baseline.
- Trade count remains large enough to review, not merely one or two trades.
- Provider contract-window comparison remains stable.
- Attribution report shows no new hidden concentration risk.

Risks:

- The PULLBACK result may be sample-specific with only four broad trades in current evidence.
- Removing TIGHT_BASE may reduce opportunity count too far.
- PULLBACK-only may still underperform SPY.

## Candidate revision B: TIGHT_BASE tightened gates

Hypothesis: TIGHT_BASE is not necessarily invalid, but the current gates are too permissive. Tightening compression, trend, score, or proximity-to-high thresholds may filter out weak bases.

Configuration intent:

- Keep TIGHT_BASE enabled, but change only explicit TIGHT_BASE/profile thresholds.
- Do not change exits, risk, costs, order planning, or lifecycle.
- Compare each threshold change as a named profile, not ad hoc code.

Acceptance gates:

- Mechanical readiness remains PASS.
- TIGHT_BASE win rate and net PnL improve materially without hidden degradation elsewhere.
- Combined broad result improves versus frozen baseline and PULLBACK-only candidate.
- Provider contract-window robustness does not fail.

Risks:

- Tightening gates can overfit five losing trades.
- More restrictive gates may remove too many opportunities.
- Without a wider broad Hugging Face panel, broad source robustness remains limited.

## Candidate revision C: TIGHT_BASE disabled pending future research

Hypothesis: TIGHT_BASE should be isolated from `swing_machine_v0_1` until it has independent research support. The v0.1 candidate should focus on the mechanically cleaner PULLBACK path.

Configuration intent:

- Remove TIGHT_BASE from v0.1 qualification candidate behavior.
- Preserve TIGHT_BASE code/contracts for future research but exclude it from baseline qualification.

Acceptance gates:

- Same as Candidate A, with an explicit non-goal that TIGHT_BASE performance is not part of v0.1.

Risks:

- This may narrow the baseline too aggressively.
- Future TIGHT_BASE research will need a separate delivery stream.

## Required implementation sequence

1. Create explicit offline revision profiles.
2. Run scanner and lifecycle replays for each revision on the same broad Alpaca manifest.
3. Build attributed performance reports for each revision.
4. Compare each revision against the frozen baseline and SPY.
5. Run provider contract-window comparison for the best candidate only.
6. Produce a revision qualification decision packet.
7. Keep paper trading blocked unless the decision packet explicitly changes the gate.

## Non-goals

- Do not tune thresholds by repeatedly chasing the best backtest result.
- Do not change risk, exits, costs, or order planning in the same revision as setup filtering.
- Do not promote from Alpaca-only broad evidence without documenting the limitation.
- Do not start paper trading from any revision until qualification is complete.

## New backlog items

- `SWING-V01-158`: Create explicit offline revision profiles.
- `SWING-V01-159`: Run PULLBACK-only broad offline comparison.
- `SWING-V01-160`: Run tightened TIGHT_BASE broad offline comparison if a defensible threshold hypothesis is selected.
- `SWING-V01-161`: Produce revision qualification decision packet.
- `SWING-V01-162`: Decide whether to build a matching broad Hugging Face manifest.
