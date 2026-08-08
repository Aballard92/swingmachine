# Swing Machine Current-State Review

Created: 2026-05-05
Repository root used: `/home/alexballard92/swingmachine`

Documentation location decision: the repository already uses `docs/` for build, runbook, roadmap, and historical-panel control documents, so this review is created in `docs/` as requested.

## 1. Executive summary

The swing machine is not an empty or purely speculative repository. It already contains a substantial design/build implementation for a deterministic daily-bar swing trading system, including typed YAML configuration, price canonicalisation, feature calculation, regime classification, candidate scoring, setup detection, entry planning, lifecycle handling, paper/shadow runtime, audit reporting, historical replay proof machinery, persistence, migrations, and a broad test suite.

The main maturity gap is not that no swing logic exists. The gap is that the repository does not yet have a clearly named, governed `swing_machine_v0_1` baseline candidate with explicit freeze criteria, baseline manifest, qualification checklist, and a signed-off boundary between machinery validation and serious baseline qualification. Existing files describe `RF_TPC_V2` / v2.1 strategy logic, but that is not the same as a frozen and qualified swing baseline.

Current readiness judgement:

| Area | Current maturity | Review judgement |
| --- | --- | --- |
| Strategy specification | Strong draft exists | `swing_trading_bot_design_spec_v2.md` and `swing_trading_bot_config_template_v2.yaml` are detailed enough to build from. |
| Runtime execution | Local paper/shadow only | Safe design/build scope. No live broker or deployment path observed. |
| Research/backtest | Partial | Deterministic machinery exists, but no serious selected-period swing baseline qualification should run yet. |
| Data ingestion | Prepared data only | Validators and manifests exist, but no production market/reference ingestion service. |
| Governance | Partial | Build roadmaps exist, but no `swing_machine_v0_1` baseline definition, manifest, backlog, or freeze process existed before this work. |
| Safety | Reasonable local safeguards | `.env.example` is infrastructure-only and README says live trading is out of scope. |
| Tests | Broad | Many focused tests exist across config, features, signals, entries, exits, runtime, reporting, replay, and migrations. |

## 2. Repository map

Relevant root files:

| Path | Relevance |
| --- | --- |
| `README.md` | Current operator entry point. States build-phase scope, paper/shadow/audit workflow, prepared data contract, historical replay proof, migrations, validation commands, and out-of-scope live broker/deployment work. |
| `pyproject.toml` | Package metadata, dependencies, CLI entry point, pytest/ruff/mypy configuration. Package description is regime-filtered trend pullback continuation swing trading bot. |
| `.env.example` | Local operator defaults only. Contains database URL, config path, runtime input path, market-data path, output dir, and runtime mode. It explicitly says the code does not load this file automatically and no broker credentials should be added. |
| `swing_trading_bot_design_spec_v2.md` | Main current strategy design. Describes daily long-only, regime-filtered trend/relative-strength pullback breakout, canonical price series, universe, regime, ranking, setups, entries, stops, exits, lifecycle, execution, and deployment phases. |
| `swing_trading_bot_config_template_v2.yaml` | Main typed strategy profile. Controls explicit strategy behaviour, including universe, breadth, regime actions, ranking weights, filters, features, setup rules, entry rules, risk, stops, exits, events, execution, monitoring, and backtest switches. |
| `swing_trading_bot_config_template.yaml` | Deprecated v1 config. It says not to implement from this file. |
| `docs/archive/build-phase/BUILD_HANDOVER_AND_AUDIT.md` | Existing handover/audit material. |
| `docs/archive/build-phase/BUILD_HANDOVER_SUMMARY.json` | Structured build handover summary. |
| `docs/archive/build-phase/SESSION_CONTINUATION.md` | Latest continuation note. Confirms design/build phase, paper/shadow/audit only, historical replay proof work, CI checks, and that parent git state is unreliable. |

Relevant docs:

| Path | Relevance |
| --- | --- |
| `docs/SOLUTION_DESIGN_AND_DELIVERY_ROADMAP.md` | Existing comprehensive roadmap/control document. It already maps much of the architecture and delivery state, but it is not a `swing_machine_v0_1` baseline definition/freeze plan. |
| `docs/BUILD_PLAN.md` | Program index. |
| `docs/BUILD_ROADMAP.md` | Short roadmap index. |
| `docs/HISTORICAL_PANEL_REQUIREMENTS.md` | Historical panel, validation, and replay requirements. |
| `docs/OPERATING_RUNBOOK.md` | Local paper/shadow/audit operating runbook. Explicitly not a live trading runbook. |

Relevant source modules:

| Path | Current role |
| --- | --- |
| `src/swingmachine/config.py` | Pydantic config model and `load_strategy_config`. This is the explicit profile contract. |
| `src/swingmachine/enums.py` | Shared enum vocabulary for regimes, lifecycle states, order reasons/types, runtime modes, review status, alerts, and data series. |
| `src/swingmachine/modeling.py` | Immutable pydantic base model and typed numeric constraints. |
| `src/swingmachine/contracts.py` | Main typed contract module. Includes bars, feature snapshots, regime snapshots, setups, order intents, entry plans, runtime inputs/results, backtest artifacts, audit/report objects, and replay results. |
| `src/swingmachine/data_contracts.py` | Prepared next-session, symbol reference, corporate action, earnings event, and historical panel manifest validators/loaders. |
| `src/swingmachine/canonical.py` | Split-adjusted OHLCV and total-return close-index construction. |
| `src/swingmachine/features.py` | Core feature calculation. Includes moving averages, ATRs, 52-week distance, pullback metrics, and trend quality. |
| `src/swingmachine/regime.py` | Benchmark/breadth regime inputs and regime classification. |
| `src/swingmachine/signals.py` | Universe eligibility, candidate scoring, and setup detection. |
| `src/swingmachine/entries.py` | Setup snapshots, stop/entry metrics, portfolio heat, and order intent construction. |
| `src/swingmachine/portfolio_manager.py` | Ranked entry batch planning with daily risk and sector reservations. |
| `src/swingmachine/exits.py` | Deterministic trailing, time, earnings, and regime-aware exit checks. |
| `src/swingmachine/lifecycle.py` | Symbol lifecycle state classification and pending-entry evaluation. |
| `src/swingmachine/backtest.py` | Historical event simulation using existing setup/entry/exit/lifecycle machinery. |
| `src/swingmachine/research.py` | Walk-forward windows, config overrides, ranking/backtest fingerprints, parameter sweeps, determinism checks. |
| `src/swingmachine/runtime.py` | Typer CLI and local runtime service for paper/shadow/audit/replay/reporting workflows. |
| `src/swingmachine/broker.py` | Broker adapter interface and `PaperBrokerAdapter`; no live broker adapter. |
| `src/swingmachine/order_intents.py` | Persistent order-intent service, dedupe, spent setup registry, recovery helpers. |
| `src/swingmachine/order_state_machine.py` | Synchronisation, entry batch submission, pending-entry processing. |
| `src/swingmachine/reconciliation.py` | Local/broker order reconciliation. |
| `src/swingmachine/monitoring.py` | Stale data, slippage, drawdown, reconciliation, and broker-health checks. |
| `src/swingmachine/shadow.py` | Shadow fill comparison against next-session market data. |
| `src/swingmachine/shadow_reviews.py` | Persistence and summary for shadow comparisons and snapshots. |
| `src/swingmachine/paper_shadow_audit.py` | Paper/shadow alignment and immutable audit snapshots. |
| `src/swingmachine/reporting.py` | Rolling audit reports and operator review reports. |
| `src/swingmachine/replay.py` | Historical manifest validation, tiny replay proof, replay artifacts, decision traces, reconciliation summary. |
| `src/swingmachine/storage.py` | SQLAlchemy local schema and persistence functions. |
| `src/swingmachine/analytics.py` | Backtest, shadow, and audit summary functions. |

Relevant tests:

| Area | Tests observed |
| --- | --- |
| Config/contracts | `tests/test_config.py`, `tests/test_contracts.py` |
| Data contracts | `tests/test_data_contracts.py` |
| Price/features/regime/signals | `tests/test_canonical.py`, `tests/test_features.py`, `tests/test_regime.py`, `tests/test_signals.py` |
| Entries/exits/lifecycle/risk | `tests/test_entries.py`, `tests/test_exits.py`, `tests/test_lifecycle.py`, `tests/test_portfolio_manager.py` |
| Runtime/order/broker/state | `tests/test_runtime.py`, `tests/test_broker.py`, `tests/test_order_intents.py`, `tests/test_order_state_machine.py`, `tests/test_reconciliation.py`, `tests/test_monitoring.py` |
| Research/replay/backtest | `tests/test_research.py`, `tests/test_replay_workflow.py`, `tests/test_backtest.py` |
| Reporting/audit/shadow | `tests/test_reporting.py`, `tests/test_shadow.py`, `tests/test_shadow_reviews.py`, `tests/test_paper_shadow_audit.py` |
| Migrations | `tests/test_migrations.py` |

## 3. Current architecture

The current architecture is a local design/build trading engine with this flow:

```text
YAML strategy profile
  -> typed StrategyRuntimeConfig
  -> prepared OHLCV/reference/corporate-action/earnings validation
  -> canonical split-adjusted and total-return price series
  -> feature calculation
  -> regime classification
  -> universe eligibility and candidate scoring
  -> setup detection
  -> entry/risk/order-intent planning
  -> backtest or local runtime cycle
  -> paper broker or shadow dry-run comparison
  -> SQLite persistence, runtime events, audit/review reports, replay artifacts
```

Important architectural facts:

| Fact | Implication |
| --- | --- |
| The runtime consumes prepared operator data. | The repo is not yet a full data ingestion platform. |
| `PAPER` and `SHADOW` are the only implemented operating modes. | Safe for local machinery validation; not live-ready. |
| Strategy behaviour is modeled in YAML and typed config classes. | This is a solid foundation for explicit baseline governance. |
| Contracts are mostly pydantic models. | The codebase already favours typed contracts over loose dictionaries. |
| Reporting and review artifacts already exist. | The missing layer is baseline-specific manifest/qualification governance, not generic logging. |
| Database tables are created locally and Alembic migrations exist. | Schema evolution is partly governed, but destructive migrations are not needed for v0.1 planning. |

## 4. Current strategy logic

The current strategy family is documented as long-only, daily-bar, regime-filtered trend / relative-strength pullback breakout.

Observed strategy boundaries:

| Component | Current behaviour |
| --- | --- |
| Direction | Long-only. |
| Timeframe | Daily regular-session bars. |
| Regime | Benchmark trend, benchmark realized volatility, breadth, and panic rebound state. Regime actions control entry enablement, size multiplier, minimum candidate percentile, and minimum trend quality. |
| Universe | Asset type, history length, price, 20-day dollar volume, leveraged/inverse ETF exclusion, allowed/blocked exchanges/symbols. |
| Ranking | Cross-sectional z-score over `mom_252_21`, `ret_126`, `rs_vs_benchmark_126`, 52-week-high proximity, and trend quality. |
| Candidate threshold | Regime-specific minimum candidate percentile and trend-quality threshold. |
| Setups | Pullback and tight-base setup families, with priority favoring `TIGHT_BASE` before `PULLBACK` in v2 config. |
| Entry | Stop-limit order planned after signal close for next regular session. Opening prints above limit cancel the setup. |
| Risk | Per-trade equity risk, max position, max sector exposure, portfolio heat, daily new risk, and volatility target. |
| Initial stop | Minimum of setup-low-derived stop and ATR stop, per v2 design. |
| Exits | Hard protective stop, ATR trailing after follow-through, time stop if insufficient progress, earnings exit, regime risk-off trailing tightening, no fixed profit target. |
| Lifecycle | Ineligible, eligible, candidate, armed, pending entry, active, exit pending, closed. |

Existing typed objects cover much of this, but the naming is not yet baseline-specific. `FeatureSnapshot` contains candidate and setup fields. `SetupSnapshot` acts as an armed setup/order-planning input. `EntryPlan`, `OrderIntent`, `ManagedPosition`, `PendingEntryCheck`, and audit/report models cover parts of the lifecycle.

## 5. Current data flow

Current data flow is prepared-data first:

| Data | Current source/handling |
| --- | --- |
| Next-session market data | Operator-provided CSV/YAML path through CLI options. Required columns include `symbol`, `session_date`, raw OHLC, and raw volume. Optional spread/fx costs are validated. |
| Historical OHLCV | Manifest-backed prepared panel through `data_contracts.py` and `replay.py`. |
| Symbol reference | Prepared file validated for asset type, exchange, currency, sector, tradability, and optional effective windows. |
| Corporate actions | Prepared split/dividend file validated by symbol/date. |
| Earnings events | Prepared file validated by symbol/date/session. |
| Canonical prices | In-memory construction in `canonical.py`: split-adjusted OHLCV and total-return close index. |
| Features | Calculated by `features.py` or consumed from prepared replay features when manifest declares them. |
| Runtime input | `RuntimeCycleInput` loaded from JSON/YAML and converted into pydantic contracts. |

Key missing data capabilities:

| Gap | Why it matters |
| --- | --- |
| No market-data fetcher/ingestion service | Runtime/research still depends on prepared files. |
| No reference-master service | Universe quality depends on external preparation discipline. |
| No corporate-action adjustment service | Canonical logic exists, but production feed handling is absent. |
| No feature store | Feature snapshots are computed/loaded in process rather than versioned as a durable dataset. |
| No baseline data contract version manifest | Historical replay has manifests, but the swing baseline itself does not yet emit a baseline manifest tying config, data contract, reports, and tests together. |

## 6. Current runtime flow

Current runtime is local and CLI-driven:

| Flow | Current state |
| --- | --- |
| `run-cycle` | Runs a paper or shadow cycle from `RuntimeCycleInput`. |
| `compare-shadow-fills` | Compares shadow proposals to next-session market data. |
| `run-paper-shadow-audit` | Runs shadow first, compares fills, then runs paper and writes audit artifacts. |
| `list-run-history` / `list-run-events` | Reads durable run/event ledger. |
| `run-audit-report-job` | Writes rolling audit reports. |
| `run-review-report` | Builds operator review report in JSON/YAML/HTML and records metrics/events. |
| `run-historical-replay` | Runs manifest-backed replay proof and writes deterministic artifacts. |

Runtime safety state:

| Safety concern | Current state |
| --- | --- |
| Live broker routing | Not implemented. |
| Broker credentials | Not present in `.env.example`; README says not live. |
| Scheduler/deployment | Not implemented. |
| Real order submission | No live adapter observed; `PaperBrokerAdapter` is local state only. |
| Database writes | Local SQLite runtime/audit/replay state only. |

## 7. Current research/backtest flow

Research/backtest exists but should not yet be treated as a qualified swing baseline.

Current capabilities:

| Capability | Current state |
| --- | --- |
| Backtest loop | `run_backtest` simulates setup, entry, pending-entry handling, active positions, exit pending, and closed trades using existing components. |
| Determinism checks | Research fingerprints compare repeated rankings/backtests. |
| Walk-forward windows | `build_walk_forward_windows` supports anchored expanding and rolling windows. |
| Parameter sweeps | `run_parameter_sweep` applies config overrides and captures results. |
| Historical replay proof | Manifest-backed replay validates data, builds feature panel, runs backtest/shadow/paper/audit path, and writes material decision artifacts. |
| Machinery validation | Tiny manifest replay is explicitly machinery validation, not return baselining. |

Research/runtime divergence today:

| Area | Current divergence |
| --- | --- |
| Data source | Research/replay uses historical panels; runtime uses prepared cycle input and next-session files. |
| Feature derivation | Historical replay can use prepared features or proof-derived features; runtime takes setup snapshots from runtime input. |
| Baseline qualification | No shared `swing_machine_v0_1` qualification manifest or checklist existed before this work. |
| Execution assumptions | Paper/shadow fill comparison exists; live execution model and broker contract tests are absent. |

## 8. Current config/profile handling

Observed config/profile model:

| Source | Current role |
| --- | --- |
| `swing_trading_bot_config_template_v2.yaml` | Primary explicit strategy profile. |
| `src/swingmachine/config.py` | Typed pydantic config contract. Extra fields are forbidden through `ImmutableModel`. |
| `swing_trading_bot_config_template.yaml` | Deprecated archive only. |
| `.env.example` | Infrastructure/operator defaults only. Not auto-loaded by code. |
| CLI arguments | Runtime paths, mode, database URL, output paths, review thresholds, and config path. |
| Hardcoded constants | Some defaults in code and test fixtures, but strategy behaviour is mostly in config. |

Important config rule for v0.1:

`.env` must remain limited to infrastructure concerns: paths, database URLs, runtime mode for safe local commands, API keys/credentials if a future adapter needs them, and operator environment names. It must not control entry filters, exit rules, scoring weights, risk rules, universe rules, ranking rules, holding periods, time windows, stop/target logic, or qualification thresholds unless those thresholds are explicit CLI/reporting inputs and recorded in artifacts.

## 9. Current testing and QA

Existing test coverage is broad for the design/build phase:

| Test area | Current coverage summary |
| --- | --- |
| Config | Loads v2 config and checks stable hash. |
| Contracts | Validates pydantic contract parsing. |
| Data validators | Tests next-session, symbol reference, corporate actions, earnings events, historical manifest, checksum, feature coverage, metadata consistency, and failure cases. |
| Strategy components | Tests canonical prices, features, regime classification, candidate scoring, setup detection, entry sizing, exits, lifecycle, portfolio manager. |
| Runtime | Tests paper cycle, shadow cycle, CLI outputs, paper/shadow/audit workflow, replay workflow, review trends. |
| Persistence/migrations | Tests Alembic schema creation and state persistence. |
| Reporting/audit | Tests rolling audit, operator review, thresholds, HTML rendering, shadow/paper audit snapshots. |
| Research/replay | Tests deterministic ranking/backtest, walk-forward, sweeps, replay artifacts, and invalid panel refusal. |

Known QA gaps before serious baseline qualification:

| Gap | Consequence |
| --- | --- |
| No baseline manifest test before this work | Cannot prove a run was tied to `swing_machine_v0_1`. |
| No full selected-period qualification gate | Cannot compare research and runtime behaviour over meaningful samples. |
| No coverage threshold | Broad tests exist, but untested branches may grow silently. |
| No live adapter contract tests | Acceptable for now because live is out of scope. |
| Full strict mypy is known to be non-blocking | Typed core is gated, but pandas-heavy modules still have typing debt. |
| No production data-ingestion tests | Prepared-file validators do not prove provider ingestion. |

## 10. Key gaps

| Gap | Priority | Notes |
| --- | --- | --- |
| `swing_machine_v0_1` baseline definition | High | Existing v2 strategy spec is not a baseline freeze/qualification contract. |
| Baseline manifest | High | Needed to bind config hash, data contract, report package, qualification checks, and serious-run prohibition status. |
| Explicit baseline profile naming | High | Existing config is `RF_TPC_V2`; v0.1 needs either a profile alias or manifest wrapper. |
| Research/runtime parity checklist | High | Replay exists, but v0.1 needs explicit parity acceptance criteria. |
| Candidate/signal domain separation | Medium | Existing `FeatureSnapshot`/setup rows contain candidate fields, but a clearer `SwingCandidate`/`SwingSignal` layer would improve explainability. |
| Rejection reason taxonomy | Medium | Reject reasons currently appear as strings in multiple components. A governed model would improve reports. |
| Portfolio correlation/concentration model | Medium | Sector and heat exist; correlation/duplicate exposure remains immature. |
| Serious qualification fixture set | High | Tiny manifest proves machinery only. Need selected-period panels before qualification. |
| Release/freeze process | High | No baseline freeze checklist existed before this work. |
| Production ingestion/scheduler/live broker | Low for v0.1 | Explicit non-goal until baseline is mechanically qualified. |

## 11. Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Mistaking v2 strategy spec for a qualified baseline | Serious full run could happen before governance is ready. | Define `swing_machine_v0_1` as a governed candidate with manifest and qualification gates. |
| Hidden strategy behaviour through environment variables | Results become unreproducible. | Keep `.env` infrastructure-only and record config hash/profile path in every baseline manifest. |
| Research/runtime drift | Backtest decisions may not match paper/shadow decisions. | Add parity checks around feature snapshots, candidate generation, risk plans, order plans, and report fields. |
| Prepared-data dependency | Bad external data prep can invalidate results. | Keep strict validators and require manifest/checksum evidence before qualification. |
| Overbuilding live execution too early | Safety and compliance risks. | Keep live broker/scheduler/deployment as non-goals until freeze review. |
| Stringly rejection reasons | Reports may be inconsistent. | Introduce typed rejection taxonomy in later backlog activity. |
| Parent git repository caveat | Branch/diff operations are unsafe or misleading. | Treat `/home/alexballard92/swingmachine` as effective root and inspect files directly. |

## 12. Recommended direction

Recommended baseline path:

1. Treat the existing `RF_TPC_V2` profile and v2.1 design as the starting strategy logic, not as a qualified baseline.
2. Define `swing_machine_v0_1` as a governed baseline candidate wrapper around explicit config, typed contracts, manifest, qualification checklist, and report package.
3. Do not chase backtest performance or add variants.
4. First build missing governance and contract surfaces: baseline manifest, candidate/signal models, rejection taxonomy, qualification checklist, and parity report structure.
5. Then align research/runtime artifacts so candidate features, eligibility gates, scores, ranks, risk plans, order plans, lifecycle decisions, and exit decisions are visible in both paths.
6. Only after unit, contract, smoke, dry-run, and selected-period machinery checks pass should a serious swing baseline qualification run be considered.
7. Keep live trading, production deployment, and real broker execution prohibited until a separate safety/release review explicitly approves them.
