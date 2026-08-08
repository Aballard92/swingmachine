# Swing machine v0.1 Trading212 research data solution design

## Purpose

This design defines how the swing machine should use the existing Trading212 research datasets as selected-period qualification data sources.

The goal is to unblock Workstream A without introducing a new market-data vendor or live data dependency.

This design is data-preparation only. It must not run live trading, submit broker orders, run production deployment, mutate Trading212 research DBs, or treat profitability as a tuning signal.

## Existing source inventory

The Trading212 repository has two local research stores that can be used:

| Provider | Source DB | Intended role |
| --- | --- | --- |
| Alpaca | `/home/alexballard92/Trading212/t212-ai-bot/data/research_testing/sources/research_alpaca_local.db` | Primary selected-period qualification source |
| Hugging Face | `/home/alexballard92/Trading212/t212-ai-bot/data/research_testing/sources/research_hf_local.db` | Cross-provider comparison/check source |

Both stores expose a `bars` table with this shape:

| Column | Type | Meaning |
| --- | --- | --- |
| `symbol` | `TEXT` | Ticker symbol |
| `timeframe` | `TEXT` | Bar timeframe, for example `1m`, `5m`, `1d` if available |
| `ts` | `TEXT` | Timestamp string, UTC-like ISO format in observed samples |
| `o` | `REAL` | Open |
| `h` | `REAL` | High |
| `l` | `REAL` | Low |
| `c` | `REAL` | Close |
| `v` | `REAL` | Volume |
| `provider` | `TEXT` | Provider/import label |

Indexes observed:

- `idx_bars_provider_tf_ts`
- `idx_bars_symbol_tf_ts`
- primary key over `symbol`, `timeframe`, `ts`, `provider`

The ORB repo also has a small research universe in:

`/home/alexballard92/Trading212/t212-ai-bot/config/universe.txt`

Observed symbols include `SPY`, `AAPL`, `MSFT`, `NVDA`, `AMZN`, `META`, `GOOGL`, `TSLA`, `AMD`, `NFLX`, `AVGO`, `QCOM`, `INTC`, `ORCL`, `CRM`, `JPM`, `BAC`, `XOM`, `CVX`, and `QQQ`.

## Key data caveat

Previous ORB documentation noted meaningful Alpaca vs Hugging Face price drift, likely caused by adjusted-versus-unadjusted price policy differences.

Therefore:

- Do not merge Alpaca and Hugging Face rows into one qualification panel.
- Treat Alpaca as the first primary source candidate.
- Treat Hugging Face as an independent cross-check source.
- Record adjustment-policy uncertainty in provenance.
- Do not promote a baseline solely because it works on one provider.

## Selected-period requirements

The swing selected-period plan currently defines:

| Period ID | Qualification window | Minimum extraction lookback |
| --- | --- | --- |
| `smoke_recent_5_sessions` | `2026-04-20` to `2026-04-24` | at least 300 trading sessions before start |
| `recent_medium_replay_window` | `2026-03-02` to `2026-04-17` | at least 300 trading sessions before start |
| `historical_contract_stability_window` | `2025-09-02` to `2025-10-31` | at least 300 trading sessions before start |

The extractor should use a conservative calendar start date:

| Period ID | Suggested extraction start |
| --- | --- |
| `smoke_recent_5_sessions` | `2025-02-01` or earlier |
| `recent_medium_replay_window` | `2025-01-01` or earlier |
| `historical_contract_stability_window` | `2024-07-01` or earlier |

The exact implementation should compute or configure a lookback buffer rather than hardcoding only the qualification window.

## Target output layout

Use separate provider roots:

```text
data/qualification_sources/trading212/
  alpaca/
    smoke_recent_5_sessions/
      ohlcv.csv
      symbol_reference.csv
      corporate_actions.csv
      earnings_events.csv
      provenance.md
    recent_medium_replay_window/
      ...
    historical_contract_stability_window/
      ...
  huggingface/
    smoke_recent_5_sessions/
      ...
```

Then build normal swingmachine input plans/manifests from those roots.

## Data contracts to produce

### `ohlcv.csv`

Required columns for swingmachine:

- `symbol`
- `session_date`
- `raw_open`
- `raw_high`
- `raw_low`
- `raw_close`
- `raw_volume`

Mapping from Trading212 `bars`:

| Swing field | Trading212 field |
| --- | --- |
| `symbol` | `symbol` |
| `session_date` | date portion of `ts`, converted to trading session date |
| `raw_open` | `o` |
| `raw_high` | `h` |
| `raw_low` | `l` |
| `raw_close` | `c` |
| `raw_volume` | `v` |

If `timeframe='1d'` exists with enough coverage, use it.

If `1d` is absent or insufficient, aggregate from `1m` bars:

- `raw_open`: first minute open by timestamp for symbol/session.
- `raw_high`: maximum minute high for symbol/session.
- `raw_low`: minimum minute low for symbol/session.
- `raw_close`: last minute close by timestamp for symbol/session.
- `raw_volume`: sum of minute volume for symbol/session.

Aggregation must use regular-session bars only where possible. If the stored data includes pre/post-market rows, the extractor must filter to the intended regular session before aggregation.

### `symbol_reference.csv`

Required columns:

- `symbol`
- `asset_type`
- `exchange`
- `currency`
- `sector`
- `is_tradable`

Initial safe mapping:

| Field | Initial source/policy |
| --- | --- |
| `symbol` | Trading212 `config/universe.txt` intersected with DB coverage |
| `asset_type` | `EQUITY` for equities; `ETF` for `SPY`/`QQQ` if allowed by existing enum, otherwise documented conservative value |
| `exchange` | `UNKNOWN` unless a trusted metadata source is added |
| `currency` | `USD` |
| `sector` | `UNKNOWN` unless a trusted metadata source is added |
| `is_tradable` | `true` only for symbols explicitly selected and present in source data |

This is sufficient for machinery qualification, but not final production-grade universe metadata.

### `corporate_actions.csv`

Required columns:

- `symbol`
- `ex_date`
- `split_ratio`
- `cash_dividend_per_share`

Initial policy:

- Generate an empty file with required columns if no reliable corporate-action table exists in Trading212 research DBs.
- Record this as a provenance limitation.
- Do not claim adjustment certainty.

### `earnings_events.csv`

Required columns:

- `symbol`
- `event_date`
- `event_session`

Initial policy:

- Generate an empty file with required columns if no reliable earnings source exists.
- Record this as a provenance limitation.
- Do not enable earnings-sensitive qualification claims until real earnings data is added.

### `features.csv`

Initial policy:

- Do not require `features.csv` for the first data unblock.
- Let the existing swing replay path derive proof features when a prepared feature file is absent.
- Add a later task for real feature generation if selected-period qualification requires it.

## Source read safety

All Trading212 DB access must be read-only:

- Open SQLite connections with `mode=ro` URI where possible.
- Do not attach or mutate Trading212 DBs.
- Do not run broad full-table aggregate scans as part of normal preflight.
- Use bounded provider/symbol/timeframe/date filters.
- Prefer explicit symbol lists and selected date windows.
- Write outputs only inside the swingmachine repo or an explicitly chosen output root.

The ad-hoc broad count queries against the multi-GB DBs proved too slow. The implementation should use targeted indexed queries only.

## Proposed components

### `Trading212ResearchSourceConfig`

Fields:

- provider label: `alpaca` or `huggingface`
- DB path
- provider value policy, optional
- regular session filter policy
- timezone/session calendar policy
- selected symbols file
- output root

### `Trading212BarsSource`

Responsibilities:

- Connect read-only to one SQLite research DB.
- Inspect `bars` schema.
- Check bounded coverage for selected symbols/periods.
- Fetch `1d` rows where available.
- Fetch `1m` rows for aggregation fallback.

### `SelectedPeriodExtractionPlan`

Responsibilities:

- Expand selected-period windows to extraction windows with lookback.
- Hold period ID, qualification start/end, extraction start/end, and symbols.
- Keep provider-specific output paths.

### `Trading212DailyOhlcvExporter`

Responsibilities:

- Export `ohlcv.csv` for each period/provider.
- Use `1d` if valid, otherwise aggregate `1m`.
- Write deterministic sorted rows.
- Reject invalid OHLCV rows.
- Produce an extraction summary artifact.

### `Trading212SwingReferenceExporter`

Responsibilities:

- Write `symbol_reference.csv` for selected symbols.
- Write empty-but-contract-valid `corporate_actions.csv` and `earnings_events.csv` when source data is absent.
- Record provenance caveats.

### `Trading212ProviderComparisonReport`

Responsibilities:

- Compare Alpaca and Hugging Face exported daily panels.
- Report symbol/session overlap, close drift, missing symbol-days, and invalid bars.
- Do not decide strategy performance.

## Proposed CLI commands

### `inspect-trading212-research-source`

Purpose: bounded schema and coverage check.

Inputs:

- `--provider alpaca|huggingface`
- `--db PATH`
- `--symbols-file PATH`
- `--selected-period-plan PATH`
- `--output PATH`

Outputs:

- schema status
- distinct timeframes from bounded/source-safe inspection
- per-period/per-symbol coverage summary
- whether `1d` can be used or `1m` aggregation is required

### `export-trading212-selected-period-data`

Purpose: export swing-compatible source files for one provider.

Inputs:

- `--provider alpaca|huggingface`
- `--db PATH`
- `--symbols-file PATH`
- `--selected-period-plan PATH`
- `--output-root PATH`
- `--lookback-sessions 320`
- `--prefer-timeframe 1d`
- `--fallback-timeframe 1m`

Outputs:

- `ohlcv.csv`
- `symbol_reference.csv`
- `corporate_actions.csv`
- `earnings_events.csv`
- provenance draft
- export summary JSON

### `compare-trading212-provider-panels`

Purpose: compare exported Alpaca and Hugging Face daily panels.

Inputs:

- `--left-root data/qualification_sources/trading212/alpaca`
- `--right-root data/qualification_sources/trading212/huggingface`
- `--selected-period-plan PATH`
- `--output PATH`

Outputs:

- overlap report
- drift report
- missing-data report

## Delivery sequence

1. Add source config and schema/coverage inspector.
2. Add bounded source coverage tests with tiny SQLite fixtures.
3. Add daily OHLCV extraction from `1d` rows.
4. Add `1m` aggregation fallback.
5. Add symbol reference and empty action/event file generation.
6. Add one-provider export CLI.
7. Add Alpaca export run against local DB for selected periods.
8. Run source input preflight and manifest build for Alpaca.
9. Add Hugging Face export run.
10. Add provider-panel comparison report.
11. Decide whether Alpaca alone is enough for first smoke replay or whether Hugging Face cross-check is mandatory first.

## Open decisions

- Whether `SPY` and `QQQ` should be classified as `ETF` or normalized to a contract-accepted value.
- Whether to require real sector metadata before selected-period replay, or allow `UNKNOWN` for machinery qualification.
- Whether to export `features.csv` now or let replay derive proof features first.
- Whether the first selected-period replay should use Alpaca only or require both Alpaca and Hugging Face source preflight first.

## Safety decision

The first implementation should be the source inspector and fixture-backed extraction code. Do not run full selected-period replay from Trading212 data until exported files pass the existing source-input and manifest preflight gates.

## Implementation decision update - 2026-05-05

The Trading212 data-source implementation now exports both Alpaca and Hugging Face selected-period panels and compares them with a provider drift report.

Decision: use Alpaca as the primary `swing_machine_v0_1` selected-period qualification source candidate. Keep Hugging Face as a comparison/audit source only until its provenance and adjustment policy are explained.

The declared data-complete qualification panel excludes `ORCL`, `CRM`, `BAC`, and `CVX` because both source databases lacked coverage for those symbols across the selected periods. This exclusion is explicit in `config/swing_machine_v0_1_trading212_sources.yaml`.

The existing qualification manifest tooling expects `ohlcv.parquet`, so the exporter writes that parquet artifact plus a human-readable `historical_ohlcv.csv` inspection copy.

Evidence is recorded in `docs/swing_machine_v0_1_data_source_decision.md` and the report artifacts under `reports/swing_machine_v0_1/`.
