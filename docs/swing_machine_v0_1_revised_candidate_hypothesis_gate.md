# Revised Candidate Hypothesis Design Gate

Report: `revised_candidate_hypothesis_design_gate_20260508T082758Z`

Status: `FAIL`

Recommendation: `DO_NOT_BUILD_REVISED_PROFILE_YET`

| Gate | Status | Current evidence | Required to pass |
| --- | --- | --- | --- |
| `pullback_contradiction_explained` | `partial` | PULLBACK traded subset outperforms untraded accepted subset, but all accepted PULLBACK remains negative on 20d SPY-excess and traded sample is 4. | Deeper replay must show whether fill/lifecycle selection is repeatable and not sample noise. |
| `null_denominator_safe` | `pass` | Core null filtering does not change accepted-edge conclusion; no core feature denominator blocker. | Keep field coverage visible in future selection packets. |
| `tight_base_removed_or_redesigned` | `pass_for_isolation` | TIGHT_BASE isolation decision exists. | Future candidates must exclude TIGHT_BASE or include explicit redesign evidence. |
| `provider_positive_edge` | `fail` | Contract-window provider comparison is stable but does not show a positive accepted edge across both providers. | Both providers should support the same positive hypothesis, or limitation must be formally accepted for offline-only research. |
| `cost_resilience` | `partial` | PULLBACK is cost-resilient in 4 trades; overall lifecycle is negative. | Candidate-level lifecycle must remain positive after cost stress with adequate sample size. |

## Minimum before profile build

- Resolve or explicitly scope the PULLBACK fill/lifecycle contradiction.
- Exclude TIGHT_BASE unless redesigned behind explicit config.
- Define a candidate profile in docs before code/config changes.
- Run offline historical replay and attribution before any paper consideration.
- Keep provider-positive-edge blocker open unless both providers support the hypothesis.

## Allowed next work

- deeper PULLBACK replay design
- candidate profile design document
- offline-only hypothesis packet

## Disallowed next work

- paper trading
- live trading
- silent profile changes
- serious full qualification run without a documented candidate hypothesis

## Gate status

- Paper gate: `BLOCKED`
- Serious full run gate: `HISTORICAL_OFFLINE_ONLY_ALLOWED`
