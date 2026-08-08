# Swing Machine v0.1 Hugging Face Drift Investigation

Date: 2026-05-05

## Scope

This investigation compares the Trading212 repository's exported Alpaca and Hugging Face selected-period panels for the declared 16-symbol `swing_machine_v0_1` qualification panel.

It does not attempt to repair the Hugging Face source. It determines whether Hugging Face can be used as the primary baseline source today.

## Evidence used

- `reports/swing_machine_v0_1/trading212_alpaca_selected_period_export.json`
- `reports/swing_machine_v0_1/trading212_huggingface_selected_period_export.json`
- `reports/swing_machine_v0_1/trading212_provider_panel_drift_report.json`

## Summary finding

Hugging Face should not be used as the primary `swing_machine_v0_1` baseline data source yet.

The drift versus Alpaca is systematic and materially affects OHLCV values. The likely cause is a different price-adjustment policy, especially around stock splits and distributions. There are also session-level gaps in Hugging Face for a specific date.

## Key examples

### Split-scale drift

Examples from the exported panels show approximate 10x differences on known split-sensitive symbols:

| Period | Symbol | Date | Alpaca close | Hugging Face close | Pattern |
| --- | --- | --- | ---: | ---: | --- |
| historical_contract_stability_window | NVDA | 2024-06-05 | 122.37 | 1224.39 | Approx 10x scale difference |
| historical_contract_stability_window | AVGO | 2024-06-17 | 179.41 | 1829.89 | Approx 10x scale difference |
| historical_contract_stability_window | NFLX | 2025-06-30 | 133.94 | 1339.38 | Approx 10x scale difference |
| smoke_recent_5_sessions | NFLX | 2025-06-30 | 133.94 | 1339.38 | Approx 10x scale difference |

This is incompatible with a baseline engine unless the adjustment policy is explicit and shared by research/runtime.

### Distribution/adjustment drift

SPY showed persistent smaller price differences:

| Period | Symbol | Worst date | Alpaca close | Hugging Face close | Difference |
| --- | --- | --- | ---: | ---: | ---: |
| smoke_recent_5_sessions | SPY | 2024-12-06 | 597.20 | 607.88 | -10.68 |
| recent_medium_replay_window | SPY | 2024-12-04 | 596.93 | 607.61 | -10.68 |
| historical_contract_stability_window | SPY | 2024-06-18 | 535.47 | 548.49 | -13.02 |

This is consistent with a different adjusted/raw treatment and is not safe to ignore for signal, stop, target, or risk calculations.

### Session coverage drift

Hugging Face missed seven symbol/session rows that Alpaca contained:

- Date: `2024-11-13`
- Symbols: `AAPL`, `AMD`, `AMZN`, `AVGO`, `JPM`, `QCOM`, `XOM`
- Affected periods: `recent_medium_replay_window`, `historical_contract_stability_window`

## Decision impact

The provider drift report failed with 48 blockers across 48 period/symbol rows. This means every declared provider comparison row had either session mismatch or value drift under the current tolerances.

Hugging Face remains useful as an audit/comparison source, but not as the primary v0.1 baseline input.

## Blocker to HF promotion

Before Hugging Face can be promoted, the project needs an explicit answer to:

- Are Hugging Face OHLCV bars raw, split-adjusted, dividend-adjusted, or adjusted-close-derived?
- Are Alpaca OHLCV bars raw, split-adjusted, dividend-adjusted, or adjusted-close-derived in this local DB?
- Which adjustment policy does `swing_machine_v0_1` require for research/runtime parity?
- Can both provider exports be transformed into the same policy without lookahead or hidden behavior?
- Why is `2024-11-13` missing for seven Hugging Face symbols?

## Current recommendation

Use Alpaca as the primary selected-period qualification source candidate.

Keep Hugging Face out of the baseline manifest until the above questions are answered and a parity transform is implemented and tested.
