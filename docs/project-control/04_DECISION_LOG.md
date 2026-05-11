# 04 Decision Log - swingmachine

This is a consolidated decision log for ChatGPT Project context. It is not a full ADR archive.

## Current controlling decisions

| Decision | Status | Rationale | Source context |
| --- | --- | --- | --- |
| No revised baseline candidate is selected. | Current | Evidence does not justify building a revised profile yet. | `docs/swing_machine_v0_1_next_baseline_candidate_selection.md` |
| Paper trading is blocked. | Current | Research edge, lifecycle, benchmark, provider-positive-edge, and sample-size blockers remain open. | Latest blocker/selection docs and inventory. |
| Serious full qualification is blocked until a revised candidate is selected for offline qualification. | Current | No candidate has passed design gate. | `docs/swing_machine_v0_1_next_baseline_candidate_selection.md` |
| Next best work is deeper PULLBACK fill/lifecycle replay research design. | Current | PULLBACK traded subset is positive, but all accepted PULLBACK evidence remains negative and sample is too small. | `docs/swing_machine_v0_1_next_day_decision_shortlist.md` |
| TIGHT_BASE should be isolated from the next baseline candidate. | Current | TIGHT_BASE has negative lifecycle and cost-stress evidence. | TIGHT_BASE isolation packet, summarized in project-control inventory. |
| Broad Hugging Face acquisition should be deferred. | Current | No Alpaca-side candidate currently proves edge, so broad provider expansion is premature. | `docs/swing_machine_v0_1_broad_huggingface_data_decision.md` |
| Strategy behavior must be explicit config/profile behavior, not hidden `.env`. | Current | Reviewable, serialisable strategy config is required for qualification. | Baseline and solution design docs. |
| Alpaca is primary broad research source for now; Hugging Face is comparison/audit only where coverage is matched. | Current | Current HF data cannot support like-for-like broad validation. | Trading212 data design and HF decision docs. |

## Rejected or superseded approaches

| Approach | Status | Why rejected/superseded |
| --- | --- | --- |
| Use deprecated v1 strategy spec/config. | Rejected | Explicitly marked deprecated; v2 spec/config and v0.1 docs govern. |
| Start paper trading from earlier engineering gate evidence. | Superseded/rejected now | Later edge/profitability analysis blocked paper readiness. |
| Run serious full qualification immediately. | Rejected now | No revised candidate selected; current gate blocks this. |
| Promote PULLBACK-only profile now. | Rejected now | Positive traded lifecycle is only 4 trades and all-accepted PULLBACK 20d SPY-excess is negative. |
| Keep TIGHT_BASE inside next baseline candidate by default. | Rejected now | Negative lifecycle and cost-stress evidence. |
| Create a broad Hugging Face manifest from current source data. | Rejected now | Current HF data starts later and would silently change warm-up/provider comparison. |
| Bulk upload generated reports into ChatGPT Project. | Rejected | Too noisy, many superseded timestamped artifacts. |

## Older decisions that need caution

| Document/area | Caution |
| --- | --- |
| First paper runbook and paper review packet | These can imply paper readiness but are superseded by current blocked gate. |
| Serious full-run plan/readiness docs | Superseded by current no-candidate-selected decision. |
| Historical freeze/replay packets | Useful evidence, but current candidate selection has moved on. |
| Full backlog and implementation log | Valuable history, too large and mixed with completed/superseded work. |

## Unknowns needing sponsor or ChatGPT Product Owner confirmation

- What sample-size threshold is acceptable before paper-readiness can be reconsidered?
- Whether the next research lane should stay PULLBACK-specific or broaden to a fresh hypothesis search.
- Whether future provider validation should require both Alpaca and Hugging Face, or allow Alpaca-only broad evidence with explicit limitation.
- Whether ChatGPT Project should include source code files for code-aware guidance, or only source-of-truth docs.
- Whether TIGHT_BASE should be permanently retired or allowed to re-enter after redesign.
