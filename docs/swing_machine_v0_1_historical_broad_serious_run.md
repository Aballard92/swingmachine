# Swing Machine v0.1 broad historical serious offline run

Date: 2026-05-06
Run ID: `20260506T124131Z`
Baseline: `swing_machine_v0_1`
Period: `historical_broad_2024_06_to_2025_07_v0_1`
Window: 2024-06-03 to 2025-07-31
Mode: offline historical replay only

## Safety boundary

This run did not trigger live trading, real broker orders, production deployment, or destructive database changes.

The run used the historical replay command path only:

- Manifest: `data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml`
- Config: `swing_trading_bot_config_template_v2.yaml`

## Plan and input artifacts

| Artifact | Status | Path |
| --- | --- | --- |
| Broad selected-period plan | Created | `config/swing_machine_v0_1_selected_periods_historical_broad.yaml` |
| Alpaca broad source coverage | Pass | `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_source_coverage.json` |
| Alpaca broad selected-period export | Pass | `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_selected_period_export.json` |
| Broad data-input plan | Pass | `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_data_input_plan.yaml` |
| Broad data-input preflight | Pass | `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_data_input_preflight.json` |
| Broad manifest build | Pass | `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_manifest_build_summary.json` |
| Broad selected-period preflight | Pass | `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_selected_period_preflight.json` |
| Broad data smoke | Pass | `reports/swing_machine_v0_1/trading212_alpaca_historical_broad_data_smoke_report.json` |
| Broad dry-run safety | Pass | `reports/swing_machine_v0_1/historical_broad_selected_period_dry_run_safety_report.json` |

## Replay outputs

| Lane | Status | Path |
| --- | --- | --- |
| Research replay | Pass | `reports/swing_machine_v0_1/serious_full_run_broad_research_20260506T124131Z/` |
| Runtime-compatible replay | Pass | `reports/swing_machine_v0_1/serious_full_run_broad_runtime_20260506T124131Z/` |
| Parity report | Pass | `reports/swing_machine_v0_1/historical_broad_serious_full_run_parity_report_20260506T124131Z.json` |
| Evidence index | Built | `reports/swing_machine_v0_1/historical_broad_serious_full_run_evidence_index_20260506T124131Z.json` |
| Run summary | Pass | `reports/swing_machine_v0_1/historical_broad_serious_full_run_summary_20260506T124131Z.json` |

## Key metrics

Both replay lanes reported the same core metrics:

- Status: `PASS`
- Validation status: `PASS`
- Validation errors: 0
- Validation warnings: 0
- Reconciliation status: `PASS`
- Decision traces: 16
- Rejected decisions: 14
- Setups: 2
- Backtest events: 3
- Shadow status counts: `FILLED: 1`, `UNFILLED: 1`
- Audit alignment counts: `ALIGNED_NOT_FILLED: 1`, `SHADOW_FILLED_PAPER_NOT_FILLED: 1`
- Parity differences: 0

## Interpretation

The broad offline machinery run passed. This is stronger evidence than the earlier smoke, medium, and contract-stability selected windows because it spans 2024-06-03 to 2025-07-31 and exercises the same baseline package contracts in paired research/runtime-compatible lanes.

However, the run still produced only 16 decision traces and 2 setups. That means this is clean replay/package/parity evidence, but it should not be misrepresented as a dense day-by-day historical scanner qualification over every session in the window.

## Current conclusion

The swing machine is materially closer to a real `swing_machine_v0_1` baseline candidate for offline historical replay and reporting.

The next engineering question is whether `swing_machine_v0_1` needs a true multi-session historical scanner mode before any paper/live runtime move. If yes, the next backlog should focus on daily replay/scanner semantics and decision-density reporting rather than strategy performance.
