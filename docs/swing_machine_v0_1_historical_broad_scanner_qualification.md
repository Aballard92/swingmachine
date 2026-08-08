# Swing Machine v0.1 broad scanner-density qualification

Date: 2026-05-06
Run ID: `20260506T155037Z`
Baseline: `swing_machine_v0_1`
Period: `historical_broad_2024_06_to_2025_07_v0_1`
Window: 2024-06-03 to 2025-07-31
Mode: offline scanner-density qualification only

## Safety boundary

This qualification did not trigger live trading, real broker orders, production deployment, or destructive database changes.

The scanner command writes local artifacts only under `reports/swing_machine_v0_1/` and records local run metadata in an output-directory SQLite database.

## Implementation note

The first broad scanner attempt exceeded a 30-minute guard because the initial Tier 1 scanner built full selected-session pydantic package context for every session. The implementation was optimized so scanner-density qualification derives per-session counts directly from the detected setup frame while preserving the existing selected-session replay path.

## Outputs

| Artifact | Path |
| --- | --- |
| Research scanner output | `reports/swing_machine_v0_1/scanner_broad_research_20260506T155037Z/` |
| Runtime-compatible scanner output | `reports/swing_machine_v0_1/scanner_broad_runtime_20260506T155037Z/` |
| Scanner parity report | `reports/swing_machine_v0_1/historical_broad_scanner_parity_report_20260506T155037Z.json` |
| Scanner qualification summary | `reports/swing_machine_v0_1/historical_broad_scanner_qualification_summary_20260506T155037Z.json` |

## Result

| Metric | Value |
| --- | --- |
| Research status | `PASS` |
| Runtime-compatible status | `PASS` |
| Scanner parity | `PASS` |
| Parity differences | 0 |
| Eligible signal sessions | 290 |
| Processed signal sessions | 290 |
| Skipped sessions | 0 |
| Total decision traces | 4,640 |
| Total candidates | 4,640 |
| Total setups | 434 |
| Total rejections | 4,206 |
| Sessions with setups | 232 |
| Sessions without setups | 58 |
| Average candidates per session | 16.0 |
| Average setups per session | 1.4965517241379311 |
| Max setups per session | 4 |

## Interpretation

This closes the decision-density gap found after the broad selected-session serious replay.

The machine has now produced dense day-by-day scanner evidence across the broad historical replay window:

- One scanner decision set per eligible signal session.
- One decision trace per active symbol per processed session.
- Aggregate rejection/setup density across the full replay window.
- Research/runtime-compatible scanner parity with zero differences.

This is still Tier 1 scanner-density qualification, not Tier 2 portfolio/lifecycle simulation. It does not carry open positions, pending orders, stops, targets, exits, or portfolio heat across the whole historical period.

## Recommendation

Treat offline scanner-density qualification as passed for `swing_machine_v0_1`.

The next major decision is whether to build Tier 2 portfolio/lifecycle simulation before any paper/live runtime move. Recommendation: build Tier 2 or at least a lifecycle-state qualification harness before paper/live runtime execution.
