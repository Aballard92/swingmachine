# Swing Machine v0.1 Qualification Gate Checklist

Date: 2026-05-05

## Current gate status

| Gate | Status | Evidence / blocker |
| --- | --- | --- |
| Explicit baseline profile | Pass | Draft manifest generated from `config/swing_machine_v0_1_profile.yaml`. |
| Data contract machinery | Pass | Data validators and manifest builders exist. |
| Selected-period source coverage | Blocked | Trading212 DBs end `2025-07-31`; current selected periods are later. |
| Selected-period data input preflight | Pass but stale/non-qualifying | File presence passed before coverage correction; must rerun after data/window decision. |
| Selected-period manifest preflight | Pass but stale/non-qualifying | Manifest paths exist but rows do not cover selected windows. |
| Selected-period smoke | Blocked | Zero qualification sessions in all current periods. |
| Dry-run safety | Pass | `selected_period_dry_run_safety_report.json`. |
| Research/runtime parity | Blocked | No selected-period package pair yet. |
| Selected-period replay | Blocked | Data/window mismatch. |
| Provider parity | Blocked for HF promotion | Provider drift unresolved. |
| Baseline freeze readiness | Blocked | Manifest incomplete, parity missing, operator approval missing. |
| Serious full run | Prohibited | Must remain prohibited. |

## Next gates to unblock

1. Decide whether to acquire newer data or shift selected periods to covered historical windows.
2. Regenerate source coverage and require it to pass on the selected replay windows.
3. Regenerate exports, manifests, selected-period preflight, and smoke report.
4. Generate dry-run replay/report packages only after smoke passes.
5. Generate research/runtime package parity evidence.
6. Rebuild draft manifest/checklist/freeze readiness.
7. Conduct freeze review.

## Rule

A file-presence preflight is not sufficient qualification evidence unless source coverage and selected-period smoke also pass for the exact selected replay windows.
