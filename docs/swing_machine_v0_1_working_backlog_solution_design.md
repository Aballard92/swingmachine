# Swing Machine v0.1 Working Backlog Solution Design

Date: 2026-05-07

Scope: open overnight/backlog items `SWING-V01-177` through `SWING-V01-192`.

Safety status: offline research and governance only. Paper trading, live trading, broker orders, production jobs, and destructive data changes remain prohibited.

## Working principles

- Build evidence before profile changes.
- Prefer reusable report builders over one-off scripts.
- Treat small-sample buckets as exploratory until guardrails prove otherwise.
- Keep raw forward return, SPY-excess forward return, and actual lifecycle return separate.
- Do not select a new profile until a controlled selection packet justifies one.
- Update backlog and implementation log after each completed or blocked activity.

## SWING-V01-177 - Accepted-only and traded-only bucket diagnostics

Solution design:

Extend the feature snapshot bucket report so every bucket contains three evidence layers:

- All rows in the bucket.
- Accepted setup rows only.
- Traded lifecycle rows only.

The accepted-only layer should summarize raw and SPY-excess forward returns. The traded-only layer should summarize forward returns plus lifecycle net PnL, net return, win rate, exit reasons where available, and trade count.

Acceptance criteria:

- Bucket metrics expose accepted-only row count and traded-only row count.
- Bucket metrics expose accepted-only raw and excess forward-return summaries.
- Bucket metrics expose traded-only lifecycle net PnL and return summaries where trade data exists.
- Markdown report shows accepted-only and traded-only evidence separately.
- Existing attribution and near-miss reports remain backward-compatible.
- Focused tests pass.
- Paper/live gates remain unchanged.

## SWING-V01-178 - Controlled benchmark-relative hypothesis selection rerun

Solution design:

Review `SWING-V01-177` outputs and rerun the selection packet. The packet should select at most one revision hypothesis or explicitly reject revision. If selected, it should define exact config changes but should not implement the new profile in the same task.

Acceptance criteria:

- Selection packet references the latest accepted/traded-only diagnostics.
- Decision is one of: no revision selected, one revision selected, or blocked.
- Any selected revision has exact proposed config changes and acceptance gates.
- Paper gate is explicit and remains blocked unless evidence justifies a future qualification step.

## SWING-V01-179 - Feature bucket robustness and minimum-sample guardrails

Solution design:

Add sample-size thresholds to bucket diagnostics. Buckets should be labelled `ROBUST`, `EXPLORATORY`, or `INSUFFICIENT` based on accepted-row count, traded-row count, and available forward-return observations.

Acceptance criteria:

- Bucket report includes sample-grade labels.
- Thin buckets cannot produce a profile-selection recommendation by themselves.
- Threshold values are explicit in the report.
- Unit tests cover robust, exploratory, and insufficient buckets.

## SWING-V01-180 - Accepted-candidate excess-return distribution report

Solution design:

Create a distribution report over accepted, near-miss, and rejected rows using SPY-excess returns over 1, 5, 10, and 20 sessions.

Acceptance criteria:

- Report includes count, mean, median, p10, p25, p75, p90, min, max, and positive-rate.
- Report compares accepted, near-miss, and rejected populations.
- Report states whether accepted rows show distributional excess-return edge.
- JSON and Markdown outputs are emitted.

## SWING-V01-181 - Traded-only lifecycle outcome decomposition

Solution design:

Join enriched attribution rows to the lifecycle trade ledger and summarize only actual trades by setup type, feature bucket, exit reason, bars held, net PnL, net return, and forward excess return.

Acceptance criteria:

- Report includes all nine broad lifecycle trades.
- Report separates actual lifecycle return from forward close-to-close outcomes.
- Report summarizes by setup type, exit reason, and selected feature buckets.
- Report identifies whether lifecycle loss appears entry, exit, cost, signal, or sample-size related where evidence allows.

## SWING-V01-182 - Exit-path diagnostic for winners, losers, and time exits

Solution design:

Analyze lifecycle exit behavior by comparing each trade exit to subsequent forward returns and the trade's prior drawdown/progress where available.

Acceptance criteria:

- Report splits trades by winner/loser and exit reason.
- Report flags potential premature exits and late exits as hypotheses, not facts.
- No exit rule changes are made.
- Report names the evidence needed before an exit-profile change.

## SWING-V01-183 - Pattern-specific benchmark-relative diagnostics

Solution design:

Split attribution and lifecycle evidence by `PULLBACK` and `TIGHT_BASE`. Keep accepted rows, traded rows, raw forward returns, SPY-excess returns, and lifecycle PnL separate.

Acceptance criteria:

- PULLBACK and TIGHT_BASE reports are separate or clearly separated in one packet.
- Each pattern has accepted/traded counts and excess-return distributions.
- TIGHT_BASE conclusions distinguish weak evidence from mechanical bugs.
- No pattern priority or profile behavior is changed.

## SWING-V01-184 - Contract-window provider enrichment feasibility

Solution design:

Check whether the matched Alpaca and Hugging Face contract manifests can generate benchmark-relative prepared features and enriched attribution over the same window.

Acceptance criteria:

- Feasibility report names both manifests and coverage windows.
- Decision is `PROCEED`, `NARROW_SCOPE`, or `BLOCKED`.
- No source data is mutated.
- Any provider coverage mismatch is explicit.

## SWING-V01-185 - Provider-matched feature/outcome attribution packet

Solution design:

If feasible, generate enriched attribution packages for Alpaca and Hugging Face contract windows using the same feature fields, benchmark symbol, and forward windows.

Acceptance criteria:

- Provider-specific attribution packages exist.
- Both packages use matched windows and comparable fields.
- Warnings are recorded for missing features or mismatched rows.
- No paper/live execution is triggered.

## SWING-V01-186 - Provider-matched accepted-versus-near-miss comparison

Solution design:

Compare provider-matched accepted-vs-near-miss results for counts, excess returns, hit rates, and direction of conclusion.

Acceptance criteria:

- Comparison report includes both provider report paths.
- Report flags provider-stable and provider-unstable metrics.
- Report blocks profile selection if provider instability is material.

## SWING-V01-187 - Feature null/missingness and stability audit

Solution design:

Audit selected benchmark-relative feature fields for nulls, infinities, extreme values, per-symbol coverage, and suspicious distribution shifts.

Acceptance criteria:

- Audit includes all selected feature snapshot fields.
- Audit reports null, infinite, min, max, mean, median, p05, p95, and per-symbol missingness.
- Any problematic field is flagged before use in profile selection.

## SWING-V01-188 - Cost/slippage stress by pattern and bucket

Solution design:

Apply additional cost scenarios to traded lifecycle rows and summarize impact by pattern and selected feature buckets.

Acceptance criteria:

- Report includes at least 5, 10, 25, and 50 bps additional cost scenarios.
- Report shows which groups remain positive or become negative under stress.
- Report identifies cost-fragile evidence.
- No risk or execution config changes are made.

## SWING-V01-189 - Historical research artifact index

Solution design:

Create a single navigable index of current reports, latest decisions, gate states, and superseded artifacts.

Acceptance criteria:

- Index has JSON and Markdown outputs.
- Latest current reports are clearly distinguished from superseded reports.
- Paper/live gate status is visible.
- Artifact paths are relative to the repository.

## SWING-V01-190 - Paper-readiness blocker refresh

Solution design:

Refresh blocker status using latest mechanical, data-quality, attribution, provider, and candidate-selection evidence.

Acceptance criteria:

- Blockers are split into mechanical, data, research edge, provider stability, and operational readiness categories.
- Paper gate is explicit.
- The report states what evidence would be needed to unblock paper later.

## SWING-V01-191 - Overnight evidence summary packet

Solution design:

Create a morning handoff that summarizes completed items, generated reports, tests run, decisions, and remaining blockers.

Acceptance criteria:

- Summary can be read independently.
- Includes report paths, test results, and gate state.
- Lists top next-day decisions.

## SWING-V01-192 - Backlog grooming and next-day decision shortlist

Solution design:

Groom backlog after overnight evidence. Mark complete/blocked/superseded items and create a short decision list for the user.

Acceptance criteria:

- Backlog statuses match implementation log.
- Next-day decision shortlist has no more than five items.
- Paper/live safety gates are preserved.
