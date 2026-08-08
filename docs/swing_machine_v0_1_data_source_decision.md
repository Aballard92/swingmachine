# Swing Machine v0.1 Data Source Decision

Date: 2026-05-05

## Decision

Use the Trading212 repository's local Alpaca research SQLite database as the primary selected-period qualification data source for `swing_machine_v0_1`.

Keep the Trading212 repository's local Hugging Face research SQLite database as a comparison/audit source only until its adjustment/provenance policy is understood and the panel drift against Alpaca is explained.

Do not merge Alpaca and Hugging Face panels for baseline qualification.

## Declared qualification panel

The source configuration uses an explicit 16-symbol panel from the Trading212 ORB universe:

`SPY`, `AAPL`, `MSFT`, `NVDA`, `AMZN`, `META`, `GOOGL`, `TSLA`, `AMD`, `NFLX`, `AVGO`, `QCOM`, `INTC`, `JPM`, `XOM`, `QQQ`.

The following symbols are explicitly excluded because both Trading212 source databases lacked selected-period coverage for them:

`ORCL`, `CRM`, `BAC`, `CVX`.

This is a data-availability exclusion, not a strategy preference.

## Evidence

- Alpaca coverage preflight passed over the declared 16-symbol panel.
- Hugging Face coverage preflight passed over the declared 16-symbol panel.
- Alpaca selected-period export passed with 16 symbols and no missing symbols per period.
- Hugging Face selected-period export passed with 16 symbols and no missing symbols per period.
- Alpaca manifest build passed.
- Hugging Face manifest build passed.
- Alpaca selected-period input preflight passed.
- Hugging Face selected-period input preflight passed.
- Provider panel drift comparison failed: 48 drift blockers across 48 period/symbol rows.

## Report artifacts

- `reports/swing_machine_v0_1/trading212_alpaca_source_coverage.json`
- `reports/swing_machine_v0_1/trading212_huggingface_source_coverage.json`
- `reports/swing_machine_v0_1/trading212_alpaca_selected_period_export.json`
- `reports/swing_machine_v0_1/trading212_huggingface_selected_period_export.json`
- `reports/swing_machine_v0_1/trading212_provider_panel_drift_report.json`
- `reports/swing_machine_v0_1/trading212_alpaca_data_input_plan.json`
- `reports/swing_machine_v0_1/trading212_huggingface_data_input_plan.json`
- `reports/swing_machine_v0_1/trading212_alpaca_manifest_build_summary.json`
- `reports/swing_machine_v0_1/trading212_huggingface_manifest_build_summary.json`
- `reports/swing_machine_v0_1/trading212_alpaca_data_input_preflight.json`
- `reports/swing_machine_v0_1/trading212_huggingface_data_input_preflight.json`

## Generated data artifacts

- `data/qualification_sources/trading212/alpaca/`
- `data/qualification_sources/trading212/huggingface/`
- `data/qualification_manifests/trading212/alpaca/`
- `data/qualification_manifests/trading212/huggingface/`

## Rationale

The two providers have equal explicit panel coverage after excluding the same four missing symbols, but their exported values do not match. The drift is broad, not isolated. Because `swing_machine_v0_1` needs a stable, explainable baseline input, using one provider is safer than blending or switching between providers.

Alpaca is the recommended primary candidate because it is a conventional market-data provider path already present in the Trading212 research setup, while the Hugging Face panel appears to require additional provenance and adjustment-policy investigation before it can be trusted as the baseline input.

## Constraints

This decision does not permit a serious full swing run by itself. It only unblocks the selected-period data-input gate for a declared 16-symbol qualification panel.

A serious full run remains prohibited until the remaining qualification gates are complete, including research/runtime parity evidence, baseline manifest evidence, smoke/dry-run safety checks, and freeze review.

## Follow-up work

- Investigate why Hugging Face differs materially from Alpaca.
- Decide whether the four excluded symbols should be recovered from another source or remain out of the v0.1 qualification panel.
- Promote Alpaca selected-period manifests into the baseline manifest only after the remaining qualification gates pass.

## Correction - 2026-05-05 overnight checkpoint

The initial Trading212 source coverage report checked for any bars within the extraction/lookback window. The coverage rule has now been tightened to require bars inside each selected qualification window.

After this correction, both Alpaca and Hugging Face coverage fail for the current selected-period plan because the local Trading212 source DBs end on `2025-07-31`, while the selected-period plan requires windows from `2025-09-02` through `2026-04-24`.

Alpaca remains the preferred provider candidate when suitable data exists, but the current exported files must be treated as non-qualifying for the current selected-period plan.
