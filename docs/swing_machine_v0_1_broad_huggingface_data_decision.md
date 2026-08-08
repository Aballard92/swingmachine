# Broad Hugging Face Data Acquisition Decision

Report: `broad_huggingface_data_acquisition_decision_20260508T083002Z`

Status: `WARN`

Decision: `DEFER_BROAD_HUGGINGFACE_ACQUISITION_UNTIL_ALPACA_HYPOTHESIS_SHOWS_EDGE`

## Rationale

- Current broad Alpaca evidence does not prove edge, so broader provider data would validate a weak/non-promotable candidate rather than unlock paper readiness.
- Matched contract-window Hugging Face checks are already available for provider-stability research.
- Broad Hugging Face acquisition becomes higher priority only after a revised Alpaca-side hypothesis earns deeper offline qualification.

## Current gap

- `alpaca_broad_source_start`: 2023-01-20
- `huggingface_widest_source_start`: 2024-04-22
- `missing_like_for_like_broad_warmup`: True
- `evidence_path`: reports/swing_machine_v0_1/huggingface_broad_manifest_feasibility_20260507T201000Z.json

## Minimum data requirement if reopened

- Full 16-symbol overlap with broad Alpaca panel.
- Coverage from at least 2023-01-20 through 2025-07-31 or a formally redesigned common window.
- Comparable adjustment policy or explicit adjustment transform.
- Manifest/preflight/data-quality pass before provider qualification.

## Gate status

- Paper gate: `BLOCKED`
- Serious full run gate: `HISTORICAL_OFFLINE_ONLY_ALLOWED`
