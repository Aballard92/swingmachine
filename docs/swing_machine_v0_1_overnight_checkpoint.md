# Swing Machine v0.1 Overnight Checkpoint

Date: 2026-05-05

## Executive summary

The overnight-safe batch added deterministic evidence consolidation, a draft baseline manifest bundle, selected-period data smoke checks, and dry-run safety checks.

It also found and fixed a material preflight weakness: Trading212 source coverage was previously checking whether each symbol had any rows in the broad extraction/lookback window. It now checks whether each symbol has bars inside the selected qualification window itself.

After that correction, both Trading212 local sources fail coverage for the current selected-period plan because the source databases end on `2025-07-31`, while the selected-period plan asks for windows from `2025-09-02` through `2026-04-24`.

## Current evidence state

| Gate | Status | Evidence |
| --- | --- | --- |
| Alpaca source schema inspection | Pass | `reports/swing_machine_v0_1/trading212_alpaca_source_inspection.json` |
| Hugging Face source schema inspection | Pass | `reports/swing_machine_v0_1/trading212_huggingface_source_inspection.json` |
| Alpaca selected-window source coverage | Fail | `reports/swing_machine_v0_1/trading212_alpaca_source_coverage.json` |
| Hugging Face selected-window source coverage | Fail | `reports/swing_machine_v0_1/trading212_huggingface_source_coverage.json` |
| Alpaca data input preflight | Pass, but now non-qualifying | `reports/swing_machine_v0_1/trading212_alpaca_data_input_preflight.json` |
| Alpaca selected-period preflight with manifests | Pass, but now non-qualifying | `reports/swing_machine_v0_1/trading212_alpaca_selected_period_preflight.json` |
| Selected-period data smoke | Fail | `reports/swing_machine_v0_1/selected_period_data_smoke_report.json` |
| Dry-run safety | Pass | `reports/swing_machine_v0_1/selected_period_dry_run_safety_report.json` |
| Draft freeze readiness | Block | `reports/swing_machine_v0_1/draft_freeze_readiness.json` |
| Overnight evidence summary | Blocked | `reports/swing_machine_v0_1/overnight_qualification_evidence_summary.json` |

## Key finding

The Trading212 local research DBs have `1d` bars ending on `2025-07-31` for checked symbols including `SPY`, `AAPL`, `NVDA`, and `QQQ`.

The selected-period plan requires:

| Period | Start | End |
| --- | --- | --- |
| smoke_recent_5_sessions | 2026-04-20 | 2026-04-24 |
| recent_medium_replay_window | 2026-03-02 | 2026-04-17 |
| historical_contract_stability_window | 2025-09-02 | 2025-10-31 |

Therefore the current Trading212 source files cannot qualify the current selected-period plan.

## Smoke result

The selected-period smoke report failed with zero qualification sessions for every period:

- `smoke_recent_5_sessions:minimum_session_count_not_met:0`
- `recent_medium_replay_window:minimum_session_count_not_met:0`
- `historical_contract_stability_window:minimum_session_count_not_met:0`

This is correct and should remain blocking.

## Serious full run status

Serious full run remains prohibited.

Reasons:

- Current selected-period windows are not covered by available source data.
- Selected-period smoke does not pass.
- Hugging Face remains comparison-only because provider drift is unresolved.
- Research/runtime selected-period parity evidence is not complete.
- Selected-period replay evidence is not complete.
- Operator/freeze review approval is not recorded.

## Required decision

Choose one of these paths before attempting selected-period replay qualification:

1. Acquire newer Alpaca/Hugging Face source data covering at least `2025-09-02` through `2026-04-24`.
2. Adjust the selected-period plan to windows fully covered by the available data, ending no later than `2025-07-31`.

Recommendation: acquire newer data if the goal is to qualify against recent market behavior. If that is not available quickly, create a temporary historical qualification plan bounded by available data and explicitly mark it as a historical machinery qualification, not a recent baseline qualification.
