# 09 PULLBACK Fill/Lifecycle Replay Research Design

Ticket: `SWING-PC-001`
Status: `DESIGN_READY_FOR_REVIEW`
Created: 2026-05-08

## Purpose

Design the next offline-only research packet for PULLBACK before any revised profile, serious full qualification, paper trading, live trading, or broker action is considered.

The research question is narrow:

Can the positive traded PULLBACK lifecycle subset be explained by repeatable fill/lifecycle selection, or is it a four-trade sample artifact that is contradicted by the broader accepted-candidate evidence?

## Current decision boundary

- Paper trading remains `BLOCKED`.
- Live trading remains `PROHIBITED`.
- No revised baseline candidate is selected.
- Do not build a revised profile yet.
- Do not change strategy config or code for this design ticket.
- TIGHT_BASE remains isolated unless explicitly redesigned and re-qualified.
- Broad Hugging Face acquisition remains deferred until an Alpaca-side hypothesis shows edge.

## Source evidence

| Evidence | Current finding | Source |
| --- | --- | --- |
| PULLBACK root-cause packet | All accepted PULLBACK rows are negative on 20-session SPY-excess, while the four traded accepted rows are positive in lifecycle PnL. | `reports/swing_machine_v0_1/pullback_traded_vs_accepted_root_cause_20260508T081457Z/pullback_traded_vs_accepted_root_cause.md` |
| Pattern diagnostic | PULLBACK is mixed: 27 accepted rows, 4 traded rows, accepted 20-session SPY-excess mean -0.024352, lifecycle net PnL 633.99. | `reports/swing_machine_v0_1/pattern_specific_benchmark_diagnostic_broad_20260508T062913Z/pattern_specific_benchmark_diagnostic_report.md` |
| Cost/slippage stress | PULLBACK remains positive under tested costs, but only across four trades; overall traded lifecycle remains negative. | `reports/swing_machine_v0_1/cost_slippage_stress_broad_20260508T080525Z/cost_slippage_stress_report.md` |
| Provider comparison | Contract-window provider evidence is stable but does not prove a positive accepted edge over near misses. | `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/provider_accepted_vs_near_miss_comparison/provider_accepted_vs_near_miss_comparison.md` |
| Null-aware denominator audit | Core null filtering does not change the accepted-edge conclusion. | `reports/swing_machine_v0_1/warmup_null_aware_denominator_audit_v2_20260508T082357Z/warmup_null_aware_denominator_audit.md` |
| Revised candidate gate | Do not build a revised profile until the PULLBACK contradiction is resolved or explicitly scoped. | `docs/swing_machine_v0_1_revised_candidate_hypothesis_gate.md` |
| Candidate selection packet | No revised baseline candidate selected; next best work is deeper PULLBACK fill/lifecycle replay research. | `docs/swing_machine_v0_1_next_baseline_candidate_selection.md` |

## Hypotheses

### H1 - Repeatable fill/lifecycle selection

The accepted PULLBACK candidate set may be weak as a raw signal, but the actual fill and lifecycle rules may select a repeatable subset with better forward behavior, lower adverse excursion, or better realized exit paths.

This is supported only if traded or simulated-filled subsets outperform unfilled accepted candidates across enough windows, symbols, and provider checks to make the effect unlikely to be sample noise.

### H0 - Sample artifact

The four positive traded PULLBACK outcomes may be a small-sample artifact. If fill status, lifecycle path, or exit timing does not produce stable separation from untraded accepted candidates, PULLBACK should not be promoted.

### H2 - Exit-path effect, not entry/fill effect

The positive lifecycle result may come from stop, time, or exit behavior rather than entry selection. This matters because a profile build based only on entry filters could preserve the wrong mechanism.

## Required dataset inputs

The research packet should use existing offline artifacts first:

- Broad feature/outcome attribution dataset used by the latest root-cause packet.
- Broad scanner material decisions for accepted PULLBACK candidates.
- Broad lifecycle trade ledger and transitions for actual PULLBACK trades.
- Pending-order and fill artifacts where available.
- SPY benchmark forward returns.
- Provider-matched Alpaca/Hugging Face contract-window attribution artifacts.
- Cost/slippage stress report inputs.

Do not acquire broader Hugging Face data for this ticket. If a later packet requires provider expansion, create a separate data-decision ticket with minimum comparable-window requirements.

## Required population splits

The report should separate these populations:

| Population | Definition |
| --- | --- |
| `accepted_pullback_all` | Every accepted PULLBACK scanner decision in the source window. |
| `accepted_pullback_traded` | Accepted PULLBACK rows that became lifecycle trades. |
| `accepted_pullback_untraded` | Accepted PULLBACK rows that did not become lifecycle trades. |
| `accepted_pullback_fill_eligible` | Accepted PULLBACK rows that had an entry plan and were realistically eligible to fill under the replay rules. |
| `accepted_pullback_not_fill_eligible` | Accepted PULLBACK rows blocked by entry mechanics, capacity, cash, risk, time, or order lifecycle rules. |
| `accepted_pullback_simulated_fill_variants` | Offline-only counterfactual fill subsets, if implemented in a later code ticket. |

The first implementation ticket may start with the first three splits if the current artifacts do not expose enough order-level detail. Missing order-detail fields must be reported explicitly rather than inferred silently.

## Required metrics

The research packet should report metrics at overall, symbol, month/quarter, setup-date, and provider scopes where sample size permits.

### Candidate and fill metrics

- Accepted rows, unique symbols, unique setup dates.
- Fill-eligible rows, filled/traded rows, unfilled rows.
- Fill rate by symbol, setup date, volatility bucket, trend-quality bucket, relative-strength bucket, and drawdown/rebound bucket.
- Rejection or non-fill reason counts, using current replay artifacts where available.
- Capacity, cash, position-limit, and duplicate-position constraints if they explain untraded accepted candidates.

### Benchmark-relative metrics

- 5, 10, 20, and 40-session raw forward returns.
- 5, 10, 20, and 40-session SPY-excess forward returns.
- Hit rates for positive raw and SPY-excess returns.
- Median, mean, trimmed mean, and lower-quartile SPY-excess returns.
- Traded versus untraded delta for the same metrics.

### Lifecycle metrics

- Net PnL and net return by trade.
- Win rate, profit factor, average winner, average loser.
- Bars held, max adverse excursion, max favorable excursion where available.
- Exit reason mix.
- Stop, time, and invalidation path frequency.
- Lifecycle return versus close-to-close forward return at 5, 10, 20, and 40 sessions.

### Cost and slippage metrics

- Base net PnL.
- Net PnL under 10, 25, and 50 bps stress.
- Break-even cost level where practical.
- Fragility classification by symbol and bucket, not only aggregate pattern.

### Provider stability metrics

- Alpaca versus Hugging Face accepted counts in matched windows.
- Provider deltas for accepted SPY-excess returns and hit rates.
- Provider deltas for fill-eligible or traded subsets if lifecycle artifacts are comparable.
- Explicit statement when provider comparison is unavailable or not like-for-like.

## Acceptance criteria for the research packet

The packet can support a later candidate-profile design only if all of these are true:

- The fill/lifecycle-selected PULLBACK subset remains positive on SPY-excess or realized lifecycle return after realistic costs.
- The effect is visible beyond the original four traded rows, either through additional historical windows, counterfactual fill-eligible subsets, or provider-matched lifecycle evidence.
- Traded or fill-eligible PULLBACK rows clearly outperform untraded accepted PULLBACK rows on benchmark-relative forward returns.
- The result is not concentrated in one symbol, one date cluster, or one exit-path anomaly without being labelled as such.
- Any provider limitation is explicitly accepted as a research limitation, not hidden as qualification evidence.
- The output includes enough concrete filter/lifecycle observations to draft a candidate-profile design without guessing.

The packet must not recommend paper trading directly. Its maximum positive recommendation is to create a candidate-profile design document for sponsor review.

## Stop conditions

Stop the lane and do not build a profile if any of these are true:

- Traded or fill-eligible PULLBACK rows do not materially outperform untraded accepted PULLBACK rows.
- Positive lifecycle evidence remains limited to the original four trades.
- Positive returns are erased by realistic cost/slippage stress.
- Results are dominated by a single symbol, date cluster, or unrepeatable exit event.
- Provider-matched evidence contradicts the Alpaca-side hypothesis and the limitation cannot be formally scoped.
- Required order/fill artifacts are missing and cannot distinguish fill selection from candidate quality.
- The report cannot explain whether the apparent edge is entry selection, order fill selection, exit behavior, or sample noise.

## Report shape

The implementation ticket should produce:

- `pullback_fill_lifecycle_replay_research.json`
- `pullback_fill_lifecycle_replay_research.md`

The Markdown packet should include:

1. Executive status: `PASS`, `WARN`, or `FAIL`.
2. Explicit recommendation:
   - `DESIGN_CANDIDATE_PROFILE_NEXT`
   - `CONTINUE_OFFLINE_RESEARCH`
   - `STOP_PULLBACK_PROFILE_LANE`
3. Source artifacts and run metadata.
4. Population split summary.
5. Fill and lifecycle explanation.
6. Benchmark-relative results.
7. Cost-stress results.
8. Provider-stability notes.
9. Acceptance-criteria table.
10. Stop-condition table.
11. Follow-up tickets.
12. Gate status confirming paper/live/broker actions remain blocked.

## Follow-up implementation tickets

### `SWING-PC-002` - Implement offline PULLBACK fill/lifecycle research report

Build the report generator for the packet above using existing artifacts only.

Allowed scope:

- Offline report code.
- Focused tests for population splitting and metric calculations.
- Generated report artifacts under `reports/swing_machine_v0_1/`.
- Stable docs summary only after the report exists.

Prohibited:

- Strategy config changes.
- Revised profile creation.
- Paper, live, or broker commands.
- Destructive data/database changes.

### `SWING-PC-003` - Review PULLBACK research packet and decide lane

Create a decision packet after `SWING-PC-002` completes.

Allowed recommendations:

- Continue PULLBACK offline research.
- Draft a candidate-profile design document.
- Stop the PULLBACK profile lane.

Prohibited recommendations:

- Paper trading.
- Live trading.
- Silent strategy/profile implementation.

### `SWING-PC-004` - Candidate-profile design only if gate passes

Only create this ticket if the decision packet supports profile design. The output must be a docs-only profile hypothesis with explicit exclusion of TIGHT_BASE unless separately redesigned.

## Current gate status

- `paper_trading`: `BLOCKED`
- `live_trading`: `PROHIBITED`
- `broker_actions`: `PROHIBITED_WITHOUT_EXACT_HUMAN_APPROVAL`
- `serious_full_qualification`: `BLOCKED_UNTIL_REVISED_CANDIDATE_SELECTED_FOR_OFFLINE_QUALIFICATION`
- `revised_profile_build`: `BLOCKED_UNTIL_PULLBACK_RESEARCH_PACKET_AND_DECISION_GATE`
