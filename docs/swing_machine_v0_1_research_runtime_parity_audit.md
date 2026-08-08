# Swing Machine v0.1 Research/Runtime Parity Audit

Date: 2026-05-05

## Current parity assets

The repository already contains useful parity machinery:

| Area | Current asset |
| --- | --- |
| Typed baseline artifacts | `src/swingmachine/swing_contracts.py` |
| Adapters from existing runtime/research objects | `src/swingmachine/swing_adapters.py` |
| Baseline report package | `src/swingmachine/baseline_reporting.py` |
| Baseline package parity comparison | `src/swingmachine/baseline_parity.py` |
| Replay material artifact emission | `src/swingmachine/replay.py` |
| Freeze readiness gate | `src/swingmachine/baseline_readiness.py` |
| Selected-period plans/preflights | `src/swingmachine/baseline.py`, `src/swingmachine/qualification_inputs.py` |

## Current parity blockers

| Blocker | Detail | Required next action |
| --- | --- | --- |
| Selected-period data not aligned | Available Trading212 data ends `2025-07-31`, but selected periods begin `2025-09-02` or later. | Acquire newer data or select covered historical windows. |
| No selected-period replay package | Replay package evidence cannot be generated until data windows are covered. | Rerun after data/period decision. |
| No selected-period research-vs-runtime parity report | `baseline_parity.py` can compare packages, but no current selected-period package pair exists. | Generate research and runtime-compatible dry-run packages for the same data. |
| Provider adjustment policy unresolved | HF differs materially from Alpaca. | Keep HF out of baseline; document or transform adjustment policy before promotion. |
| Baseline manifest not frozen | Draft manifest exists only as blocked evidence. | Promote only after data, smoke, parity, replay, and freeze gates pass. |

## Recommendation

Do not build new strategy behavior next. The parity machinery exists; the gating issue is data/window alignment.

Next implementation should either:

- Create a covered historical selected-period plan using windows before `2025-07-31`, or
- Add a newer source refresh path and regenerate source coverage, exports, manifests, smoke, replay, parity, and freeze evidence.
