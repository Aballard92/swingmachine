# Swing Machine v0.1 Alpaca Manifest Promotion Plan

Date: 2026-05-05

## Current state

Alpaca selected-period data has passed the data-input gate for the declared 16-symbol panel.

Available artifacts:

- `reports/swing_machine_v0_1/trading212_alpaca_data_input_plan.json`
- `reports/swing_machine_v0_1/trading212_alpaca_manifest_build_summary.json`
- `reports/swing_machine_v0_1/trading212_alpaca_data_input_preflight.json`
- `data/qualification_manifests/trading212/alpaca/`

## Decision

Do not promote Alpaca manifests into the frozen `swing_machine_v0_1` baseline manifest yet.

## Why promotion is blocked

The data-input gate is now unblocked, but a serious full run still requires the remaining non-data qualification gates:

- Baseline manifest package references the chosen data source and active profile.
- Research/runtime parity evidence is current.
- Signal, risk, order, lifecycle, and reporting contract checks are current.
- Smoke checks pass against the selected-period data.
- Dry-run safety checks pass with no broker execution path enabled.
- Qualification checklist is complete.
- Freeze review explicitly approves `swing_machine_v0_1` for a selected-period qualification run.

## Promotion condition

Promote Alpaca manifests only when all remaining qualification gates pass and the baseline freeze checklist explicitly selects Alpaca as the source.

## Promotion action when unblocked

When unblocked, create or update the baseline manifest package to reference:

- Primary source: Trading212 local Alpaca research DB export
- Data panel: declared 16-symbol qualification panel
- Selected-period manifests: `data/qualification_manifests/trading212/alpaca/`
- Source decision: `docs/swing_machine_v0_1_data_source_decision.md`
- Excluded symbol decision: `docs/swing_machine_v0_1_excluded_symbol_decision.md`

## Safety note

This plan does not permit live trading, paper execution, or a serious full run. It only defines the conditions for promoting already-preflighted data manifests into the baseline package.
