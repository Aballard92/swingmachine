# 04 Decision Log - swingmachine

This is a consolidated decision log for ChatGPT Project context. It is not a full ADR archive.

## Current controlling decisions

| Decision | Status | Rationale | Source context |
| --- | --- | --- | --- |
| Accept remaining historical-data unknowns as a research limitation and stop indefinite acquisition. | Current | Existing evidence supports a fail-closed partial research subset, but classification, historical reference, sector, shares, and halt-state gates remain incomplete. More accounts, APIs, downloads, or Vault transfers are not justified without a bounded decision-critical need. | `docs/project-control/10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md` |
| No revised baseline candidate is selected. | Current | Evidence does not justify building a revised profile yet. | `docs/swing_machine_v0_1_next_baseline_candidate_selection.md` |
| Paper trading is blocked. | Current | Research edge, lifecycle, benchmark, provider-positive-edge, and sample-size blockers remain open. | Latest blocker/selection docs and inventory. |
| Serious full qualification is blocked until a revised candidate is selected for offline qualification. | Current | No candidate has passed design gate. | `docs/swing_machine_v0_1_next_baseline_candidate_selection.md` |
| The bounded PULLBACK lifecycle diagnostic remains `INCONCLUSIVE`. | Current | Of 27 accepted observations, 10 were submitted lifecycles (4 filled, 6 cancelled) and 17 were repeated same-symbol observations during an existing pending/open lifecycle. The four filled rows remain too small and concentrated for profile design. | `reports/swing_machine_v0_1/pullback_fill_lifecycle_diagnostic_20260729T130830Z/pullback_fill_lifecycle_diagnostic.md` |
| PULLBACK is `PARKED_INCONCLUSIVE` under accepted `SWING-PC-003` Option A. | Current | The diagnostic did not add independent fills, all four filled trades remain in NFLX, and the filled 20-session excess median is negative. Re-analysis cannot close the sample or concentration blocker. | `docs/project-control/SWING-PC-003_pullback_lane_decision_packet.md` |
| The Option B robustness appendix is not authorized. | Current | Alex accepted Option A; the alternative could not create independent fills or authorize a profile. | `docs/project-control/SWING-PC-003_pullback_lane_decision_packet.md` |
| `SWING-PC-005` broader offline hypothesis-search design is accepted. | Current | Alex accepted the fixed two-family, common-lifecycle, sequential-gate design with `ACCEPT_SWING_PC_005_DESIGN_V1`. | `docs/project-control/SWING-PC-005_broader_offline_hypothesis_search_design.md` |
| The single authorized `SWING-PC-005A` execution stopped at Gate 0. | Current | No frozen SPY benchmark exists; all 974 dividend events lack payment dates; and 81 terminal delisted rows lack outcome semantics. The required outcome is `STOP_SOURCE_OR_TEMPORALITY_INVALID`; no strategy outcome or holdout was opened. | `reports/swing_machine_v0_1/broader_offline_hypothesis_screen_20260729T171017Z/mps_hypothesis_screen.md` |
| `SWING-PC-006` completed with `NO_FAMILY_PASSES_DISCOVERY`. | Current | The limitation-tolerant absolute-return fallback used the same fixed families and common lifecycle. H1 was positive on mean PnL/R but failed negative-median and 61.76% symbol-concentration gates. H2 was negative, traded only three securities, and was 79.31% concentrated. Gate 2 and holdout remained unopened. | `reports/swing_machine_v0_1/limitation_tolerant_screen_20260729T194422Z/mps_limitation_screen.md` |
| No further benchmark acquisition is justified in this lane. | Current | Stooq returned browser-verification HTML and the sole Yahoo fallback returned HTTP 429. The agreed absolute-only fallback still failed before validation, so more accounts, retries, or data sources cannot repair the decisive discovery evidence. | `docs/project-control/SWING-PC-006_limitation_tolerant_exploratory_screen_design.md` |
| TIGHT_BASE should be isolated from the next baseline candidate. | Current | TIGHT_BASE has negative lifecycle and cost-stress evidence. | TIGHT_BASE isolation packet, summarized in project-control inventory. |
| Broad Hugging Face or replacement-source acquisition is stopped for the current lane. | Current | No Alpaca-side candidate proves edge, existing historical unknowns are accepted fail closed, and further acquisition requires a new bounded five-part authorization. | `docs/project-control/10_HISTORICAL_DATA_LIMITATION_ACCEPTANCE.md` |
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
- What future decision-critical evidence, if any, would justify reopening data
  acquisition under the five-part stop-condition exception.
- Whether ChatGPT Project should include source code files for code-aware guidance, or only source-of-truth docs.
- Whether TIGHT_BASE should be permanently retired or allowed to re-enter after redesign.
