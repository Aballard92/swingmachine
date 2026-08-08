# Next Baseline Candidate Selection Packet

Report: `next_baseline_candidate_selection_packet_20260508T083158Z`

Status: `FAIL`

Selection: `NO_REVISED_BASELINE_CANDIDATE_SELECTED`

Next best work: `DESIGN_DEEPER_PULLBACK_FILL_AND_LIFECYCLE_REPLAY_RESEARCH`

## Inputs

| Input | Finding | Path |
| --- | --- | --- |
| `pullback_root_cause` | PULLBACK traded subset is positive but all accepted PULLBACK evidence is negative; deeper replay only. | `reports/swing_machine_v0_1/pullback_traded_vs_accepted_root_cause_20260508T081457Z/pullback_traded_vs_accepted_root_cause.json` |
| `null_denominator_audit` | Core null filtering does not change accepted-edge conclusion. | `reports/swing_machine_v0_1/warmup_null_aware_denominator_audit_v2_20260508T082357Z/warmup_null_aware_denominator_audit.json` |
| `tight_base_isolation` | TIGHT_BASE should be isolated from next baseline candidate. | `reports/swing_machine_v0_1/tight_base_isolation_decision_20260508T082603Z/tight_base_isolation_decision.json` |
| `revised_candidate_gate` | Do not build revised profile yet. | `reports/swing_machine_v0_1/revised_candidate_hypothesis_design_gate_20260508T082758Z/revised_candidate_hypothesis_design_gate.json` |
| `huggingface_data_decision` | Defer broad Hugging Face acquisition until an Alpaca hypothesis shows edge. | `reports/swing_machine_v0_1/broad_huggingface_data_acquisition_decision_20260508T083002Z/broad_huggingface_data_acquisition_decision.json` |

## Recommendations

| Option | Decision | Reason |
| --- | --- | --- |
| `no_build_continue_research` | `selected` | Evidence is not strong enough to build a revised baseline profile. The best next work is deeper PULLBACK replay/design research. |
| `pullback_only_profile_now` | `rejected` | PULLBACK has positive traded lifecycle but negative all-accepted 20d SPY-excess and only 4 broad trades. |
| `remove_tight_base_and_qualify` | `rejected_for_now` | TIGHT_BASE should be isolated, but removing it alone does not prove the remaining candidate has edge. |
| `collect_broad_huggingface_now` | `deferred` | No current Alpaca-side candidate has earned broad provider validation effort. |

## Required before candidate build

- A documented PULLBACK fill/lifecycle hypothesis.
- Evidence that traded-subset selection is repeatable beyond 4 trades.
- Explicit exclusion or redesign of TIGHT_BASE.
- Provider limitation handling in the selection packet.
- Cost-stressed lifecycle expectations before full qualification.

## Gate status

- Paper gate: `BLOCKED`
- Serious full run gate: `BLOCKED_UNTIL_REVISED_CANDIDATE_SELECTED_FOR_OFFLINE_QUALIFICATION`
