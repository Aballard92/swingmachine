# Swing Machine v0.1 historical freeze review packet

Date: 2026-05-06
Baseline: `swing_machine_v0_1`
Profile alias: `config/swing_machine_v0_1_profile.yaml`
Selected-period plan: `config/swing_machine_v0_1_selected_periods_historical.yaml`

## Review decision required

This packet is prepared for operator freeze review. It does not approve a serious full run by itself.

Current readiness decision:

- Decision: `BLOCK`
- Serious full run allowed: `false`
- Remaining blockers: `operator_review_pass`, `freeze_review`, `operator_approval_missing`

A serious full run remains prohibited until the operator explicitly approves the freeze and readiness is rebuilt with that approval recorded.

## Evidence summary

| Gate | Status | Evidence |
| --- | --- | --- |
| Explicit baseline profile | Pass | `config/swing_machine_v0_1_profile.yaml` |
| Historical selected-period plan | Pass | `config/swing_machine_v0_1_selected_periods_historical.yaml` |
| Alpaca historical coverage | Pass | `reports/swing_machine_v0_1/trading212_alpaca_historical_source_coverage.json` |
| Hugging Face historical coverage | Pass, provenance secondary | `reports/swing_machine_v0_1/trading212_huggingface_historical_source_coverage.json` |
| Alpaca selected-period export | Pass | `reports/swing_machine_v0_1/trading212_alpaca_historical_selected_period_export.json` |
| Historical manifest build | Pass | `reports/swing_machine_v0_1/trading212_alpaca_historical_manifest_build_summary.json` |
| Historical data input preflight | Pass | `reports/swing_machine_v0_1/trading212_alpaca_historical_data_input_preflight.json` |
| Historical selected-period preflight | Pass | `reports/swing_machine_v0_1/trading212_alpaca_historical_selected_period_preflight.json` |
| Historical data smoke | Pass | `reports/swing_machine_v0_1/trading212_alpaca_historical_data_smoke_report.json` |
| Historical dry-run safety | Pass | `reports/swing_machine_v0_1/historical_selected_period_dry_run_safety_report.json` |
| Historical smoke replay | Pass | `reports/swing_machine_v0_1/replay_historical_smoke_research_windowed/replay_summary.json` and `reports/swing_machine_v0_1/replay_historical_smoke_runtime_windowed/replay_summary.json` |
| Historical smoke parity | Pass | `reports/swing_machine_v0_1/historical_smoke_windowed_baseline_parity_report.json` |
| Historical medium replay | Pass | `reports/swing_machine_v0_1/replay_historical_medium_research_windowed/replay_summary.json` and `reports/swing_machine_v0_1/replay_historical_medium_runtime_windowed/replay_summary.json` |
| Historical medium parity | Pass | `reports/swing_machine_v0_1/historical_medium_windowed_baseline_parity_report.json` |
| Historical contract-stability replay | Pass | `reports/swing_machine_v0_1/replay_historical_stability_research_windowed/replay_summary.json` and `reports/swing_machine_v0_1/replay_historical_stability_runtime_windowed/replay_summary.json` |
| Historical contract-stability parity | Pass | `reports/swing_machine_v0_1/historical_stability_windowed_baseline_parity_report.json` |
| Unit/contract certification | Pass | Focused pytest shards: 60 contract/lifecycle/order/risk tests and 72 baseline/data/readiness/qualification tests passed. |
| Freeze readiness | Block | `reports/swing_machine_v0_1/historical_freeze_readiness.json` |
| Evidence index | Built | `reports/swing_machine_v0_1/historical_qualification_evidence_index.json` |

## Replay tiers reviewed

| Tier | Purpose | Result |
| --- | --- | --- |
| Historical smoke | Fast proof that selected-period replay, dry-run safety, and research/runtime package parity can run cleanly on real historical panels. | Pass |
| Historical medium | Wider historical replay window to prove the clean smoke result is not a one-off artifact. | Pass |
| Historical contract-stability | Additional selected-period evidence that the contracts remain stable across another historical window. | Pass |

## Technical certification checks

The focused unit/contract gate was split into two shards to avoid long-running replay workflow tests masking the actual result:

- Contract/lifecycle/order/risk shard: `60 passed in 97.69s`.
- Baseline/data/readiness/qualification shard: `72 passed in 196.98s`.

The broader replay workflow has already been validated through the historical selected-period replay artifacts listed above. A previous all-in-one pytest command was interrupted by process timeout before producing a valid certification result; it is not used as pass evidence.

## Known assumptions

- Historical data is sufficient for the current qualification phase; newer data is not required before operator review unless the operator wants additional recency coverage.
- Alpaca historical evidence is the primary selected-period qualification source for this packet.
- Hugging Face coverage is useful as secondary provenance evidence, but not required to approve the Alpaca historical freeze packet.
- Replay-window semantics are intentional: historical lookback rows are retained for features, while trade simulation and reconciliation are scoped to selected replay sessions.
- `US_EQUITY` calendar validation is appropriate for the current US equity/ETF historical panels.

## Prohibited actions before approval

Do not run any serious full baseline run, live trading, real broker orders, production deployment action, destructive database change, or unguarded paper/live execution from this packet alone.

## Operator review checklist

Before approving the freeze, confirm:

- The profile/config hash in `reports/swing_machine_v0_1/historical_freeze_readiness.json` matches the reviewed baseline profile.
- The selected-period plan covers the intended historical qualification windows.
- The replay and parity artifacts listed in this packet are acceptable as evidence.
- The dry-run safety evidence is acceptable.
- The decision to rely on historical data without newer recency data is intentional.
- Any optional Hugging Face provenance reconciliation is either completed or explicitly deferred.
- The next serious full run, if later approved, will be guarded, dry-run/paper-safe as configured, and explicitly invoked by the operator.

## Current recommendation

Engineering evidence is now sufficient to move to operator freeze review. It is not sufficient to execute a serious full run automatically. The next action should be an explicit operator decision: approve the freeze for a controlled next run, request more evidence, or defer.
