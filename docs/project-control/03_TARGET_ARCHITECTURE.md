# 03 Target Architecture - swingmachine

## Intended architecture

`swingmachine` should remain a deterministic, explicit-config, daily-bar swing trading system with clear separation between:

- Data contracts and validation.
- Research/offline replay.
- Runtime/paper/shadow/audit execution paths.
- Strategy feature, candidate, signal, risk, order, lifecycle, and exit contracts.
- Reporting, evidence, and qualification gates.

Research and runtime should share or align the same feature definitions, candidate logic, risk sizing, order planning, lifecycle assumptions, report fields, and rejection reasons.

## Key modules/components

| Area | Key files/modules | Responsibility |
| --- | --- | --- |
| Config/profile | `config/*.yaml`, `src/swingmachine/config.py`, `src/swingmachine/baseline.py` | Explicit strategy config, profile aliases, selected-period plans, baseline manifests. |
| Domain contracts | `src/swingmachine/contracts.py`, `src/swingmachine/swing_contracts.py`, `src/swingmachine/enums.py` | Typed contracts and enums for bars, candidates, signals, orders, lifecycle, reports. |
| Data contracts | `src/swingmachine/data_contracts.py`, `src/swingmachine/data_quality.py`, `src/swingmachine/trading212_source.py` | Historical panel loading, validation, provider exports, data quality. |
| Market features | `src/swingmachine/canonical.py`, `src/swingmachine/features.py`, `src/swingmachine/prepared_features.py`, `src/swingmachine/regime.py` | Canonical prices, feature calculation, prepared feature panels, regime snapshots. |
| Strategy mechanics | `src/swingmachine/signals.py`, `src/swingmachine/entries.py`, `src/swingmachine/exits.py`, `src/swingmachine/lifecycle.py`, `src/swingmachine/swing_adapters.py` | Universe, scoring, setup detection, entry planning, exits, state classification, typed adapters. |
| Replay/research | `src/swingmachine/replay.py`, `src/swingmachine/backtest.py`, `src/swingmachine/research.py`, `src/swingmachine/performance.py`, `src/swingmachine/feature_outcomes.py` | Offline scanner, lifecycle, backtest, attribution, performance, diagnostics. |
| Runtime/paper/shadow | `src/swingmachine/runtime.py`, `src/swingmachine/broker.py`, `src/swingmachine/shadow.py`, `src/swingmachine/paper_shadow_audit.py`, `src/swingmachine/reporting.py` | CLI/runtime orchestration, paper broker, shadow fills, audit and operator review. |
| Storage | `src/swingmachine/storage.py`, migrations | SQLite/SQLAlchemy persistence for runtime and audit state. |
| Readiness/evidence | `src/swingmachine/mechanical_readiness.py`, `src/swingmachine/baseline_readiness.py`, `src/swingmachine/baseline_reporting.py`, `src/swingmachine/qualification_evidence.py` | Qualification evidence, readiness decisions, report packages, parity. |
| Tests | `tests/` | Unit, contract, replay, runtime, data, provider, report and parity checks. |

## Data flow where known

Typical offline qualification flow:

1. Trading212 or prepared historical data is exported into provider-specific qualification source files.
2. Historical manifests describe OHLCV, reference data, corporate actions, earnings, and optional prepared features.
3. Data contracts validate manifest and panel quality.
4. Prepared features and regime inputs are computed from historical panels.
5. Scanner replay creates material decision rows, candidates, setups, rejection reasons, and density artifacts.
6. Portfolio/lifecycle replay creates positions, pending orders, transitions, exposure snapshots, and trade ledgers.
7. Performance and attribution reports join scanner decisions, lifecycle trade outcomes, benchmark returns, and feature snapshots.
8. Qualification/reporting packets decide whether a candidate is research-only, blocked, or eligible for deeper review.

Runtime/paper/shadow flow exists but is currently not authorised for paper/live use.

## Integration points

- Trading212 repo local research DBs for Alpaca and Hugging Face historical data.
- Alpaca/Hugging Face provider panels through an ignored machine-local config
  copied from `config/swing_machine_v0_1_trading212_sources.example.yaml`.
- Local SQLite runtime/audit databases.
- CLI commands via `swingmachine` entrypoint.
- Optional paper broker/shadow comparison paths.

## Architecture guardrails

- Strategy behavior must be controlled by explicit config/profile files, not hidden `.env` behavior.
- `.env` may contain credentials, paths, API keys, and infrastructure settings only.
- Research/runtime parity matters from the beginning.
- Generated evidence must be explainable and reproducible.
- Paper/live broker actions require explicit human approval.
- Current work should stay offline until blockers are cleared.
- Do not treat a single-provider positive result as sufficient for promotion.
- Do not merge or normalise Alpaca and Hugging Face data without an explicit provider policy.

## Areas that should not be changed without approval

- Strategy entry/exit/risk behavior.
- Baseline profile identity and serious-run policy.
- Paper/live execution commands.
- Broker adapters and order submission paths.
- Database migrations or destructive data changes.
- Trading212 source paths or provider policy.
- TIGHT_BASE inclusion in any future candidate.
- Any revised profile build before the revised-candidate hypothesis gate passes.
