# Swing Machine v0.1 Serious Full Run Readiness Decision

Created: 2026-05-05
Decision status: **not ready for serious full run**

## Decision

Do not unblock a serious full `swing_machine_v0_1` run yet.

The correct next step is integration and qualification work first. The baseline foundation is materially stronger now, but it is still a governed candidate, not a qualified baseline.

## Why this decision is correct

The repository now has strong baseline governance foundations:

| Area | Current state |
| --- | --- |
| Current-state review | Complete. |
| Baseline definition | Complete. |
| Solution design | Complete. |
| Delivery plan | Complete. |
| Backlog and implementation log | Complete. |
| Profile alias | Complete: `config/swing_machine_v0_1_profile.yaml`. |
| Baseline manifest/checklist | Complete as typed contracts. |
| Feature snapshot wrapper | Complete. |
| Universe/candidate/signal contracts | Complete. |
| Candidate adapter | Complete. |
| Risk/order/lifecycle/exit contracts | Complete. |
| Baseline report package | Complete as pure package/writer. |
| Baseline parity comparator | Complete as package comparator. |
| Smoke/dry-run safety coverage | Initial focused coverage complete. |

However, the system is not yet ready for a serious full run because the following baseline-critical items remain incomplete or not yet integrated:

| Gap | Why it blocks serious full run |
| --- | --- |
| Signal adapter integration | The typed signal contract exists, but current setup/runtime outputs are not yet adapted into baseline signal artifacts. |
| Risk/order adapter integration | The typed risk/order contracts exist, but `EntryPlan`/`OrderIntent` outputs are not yet adapted into baseline report artifacts. |
| Lifecycle/exit adapter integration | The typed lifecycle/exit contracts exist, but existing lifecycle/exit decisions are not yet emitted into the baseline package. |
| Replay/runtime report hook | The baseline report package writer exists, but replay/runtime commands do not yet emit `baseline_report_package.json`. |
| End-to-end package parity | The parity comparator exists, but no real research-vs-runtime-compatible package pair is emitted by the system yet. |
| Selected-period qualification data | Not defined. Tiny fixtures prove machinery, not baseline qualification. |
| Freeze review | Not performed and cannot be performed until evidence above exists. |

## Current permission state

| Run type | Decision |
| --- | --- |
| Unit/contract tests | Allowed. |
| Focused smoke/package generation | Allowed. |
| Tiny fixture replay/proof | Conditionally allowed if explicitly run as machinery validation only. |
| Selected-period qualification preparation | Allowed. |
| Serious full baseline qualification run | **Blocked.** |
| Paper/live expansion | **Blocked.** |
| Real broker execution | **Prohibited.** |
| Production deployment/scheduler | **Prohibited.** |

## What would unblock a serious full run

A serious full run should only be unblocked after these activities are complete:

1. Add signal adapter from setup outputs to `SwingSignal`.
2. Add risk/order adapters from `EntryPlan` and `OrderIntent` to `SwingRiskPlan` and `SwingOrderPlan`.
3. Add lifecycle/exit adapters from pending-entry, position, and exit decisions to baseline lifecycle/exit artifacts.
4. Wire safe replay/report generation to emit `baseline_report_package.json`.
5. Produce a research package and a runtime-compatible package from the same controlled fixture or selected period.
6. Run baseline parity comparison and resolve differences or document accepted gaps.
7. Define selected-period qualification data and manifest requirements.
8. Run selected-period validation/replay as qualification preparation, not live trading.
9. Run freeze review and update the manifest/checklist only if all mandatory checks are satisfied.

## Educated recommendation

Proceed with integration and qualification work before any serious full run.

The next best implementation items are:

1. Signal adapter integration.
2. Risk/order adapter integration.
3. Lifecycle/exit adapter integration.
4. Safe replay/report package hook.
5. Selected-period qualification data definition.

## Safety note

Do not change `serious_full_run_allowed` to `true` manually. It should become true only through satisfied manifest/checklist evidence, not through operator intent alone.
