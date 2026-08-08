# Swingmachine Build Roadmap

Generated: 2026-04-30

The detailed control document for this phase is now
`docs/SOLUTION_DESIGN_AND_DELIVERY_ROADMAP.md`.

This file is the short roadmap index. It exists so a returning developer or
model can quickly see the active program, current batch, and deferred work
without reading the full solution design first.

## Current Phase

Swingmachine is in design/build. The active product problem is not live trading
and not strategy-performance baselining. The active problem is whether the local
research and review machinery can handle prepared historical data
deterministically, explain its decisions, and expose internal consistency
problems.

## Active Workstreams

1. Historical data foundation.
2. Replay and artifact platform.
3. Decision traceability.
4. Review intelligence.
5. Runtime and persistence hardening.
6. Type and contract boundary hardening.
7. Operator workflow and evidence management.

The full workstream definitions, dependencies, and acceptance criteria are in
`docs/SOLUTION_DESIGN_AND_DELIVERY_ROADMAP.md`.

## Current Delivery Batch

### Batch 1: Replay Platform Foundation

Status: partly complete.

Completed:

- Historical panel manifest and whole-panel validator.
- Tiny manifest-backed fixture under `tests/fixtures/historical_panel/`.
- Tiny manifest-backed replay proof in `src/swingmachine/replay.py`.
- Focused tests for valid panels, malformed panels, deterministic tiny replay,
  and invalid-panel replay refusal.
- README and runbook examples for validator/proof APIs.

Pending:

- General manifest replay runner.
- Runtime CLI command for replay.
- Run-scoped replay artifact directory.
- Structured failure artifacts for validation and replay failures.
- Basic material-decision artifacts that can later support decision traces.
- Persistence of replay metadata through the run-history layer.

Acceptance criteria:

- A valid tiny manifest runs through the general replay path.
- An invalid manifest produces a structured failure artifact and does not replay.
- Repeated runs over the same manifest/config have the same material decisions
  after volatile timestamps are ignored.
- Tests assert machinery consistency and determinism, not profitability.

## Next Delivery Batches

### Batch 2: Decision Explanation And Reconciliation

Goal: make accepted, rejected, skipped, submitted, filled, expired, and
unmatched decisions explainable.

Likely outputs:

- Decision trace contract.
- Reason-category artifacts.
- Stage count reconciliation.
- Accepted and mismatch fixtures.

### Batch 3: Review Over Replay Panels

Goal: make the existing review report consume replay evidence directly.

Likely outputs:

- Replay sections in JSON/HTML review reports.
- Trend summaries for repeated replay-review runs.
- Operator guidance for recurring validation or reconciliation issues.

### Batch 4: Larger Prepared Panel Adoption

Goal: move from tiny fixtures to modest external prepared panels without adding
vendor ingestion or performance claims.

Likely outputs:

- External prepared-data path convention.
- Manifest examples for larger panels.
- Optional row-count/checksum validation.
- Artifact-size controls and summaries.

### Batch 5: Contract, Typing, And Operational Hardening

Goal: tighten the modules that now sit on critical replay/review boundaries.

Likely outputs:

- Expanded `mypy_core.ini` coverage.
- Replay/review artifact schema tests.
- Interrupted-run recovery guidance.

## Deferred Work

These remain deliberately out of scope:

- Live broker adapters.
- Broker credentials, permissions, order routing, or account operations.
- Production scheduling, queues, services, deployment, or alerting.
- Strategy-performance baselining.
- Parameter optimization.
- Vendor-specific ingestion.
- Dashboards before artifact semantics are stable.

## Implementation Discipline

Before coding new runtime or replay surface, record:

- The delivery batch and workstreams affected.
- The problem being solved.
- Explicit non-goals.
- Contracts or artifact schemas that cross module boundaries.
- Tests and docs that will ship with the implementation.
- Commands to validate the change and any known gaps.

This keeps the work grouped around a designed capability rather than a sequence
of isolated changes.

## Decision Log

| Date | Decision | Reason | Evidence |
| --- | --- | --- | --- |
| 2026-04-30 | Treat the current phase as design/build, not live trading. | The system still needs stronger replay, traceability, review, and data contracts before live execution is a sensible topic. | `README.md`, `docs/OPERATING_RUNBOOK.md`, `docs/BUILD_PLAN.md` |
| 2026-04-30 | Use manifest-backed prepared panels before external ingestion. | The current risk is validating and replaying known prepared inputs, not fetching data. | `docs/HISTORICAL_PANEL_REQUIREMENTS.md`, `src/swingmachine/data_contracts.py` |
| 2026-04-30 | Separate machinery validation from strategy-performance baselining. | The system should not baseline returns until data, replay, traceability, and review semantics are stable. | `docs/HISTORICAL_PANEL_REQUIREMENTS.md`, `docs/SOLUTION_DESIGN_AND_DELIVERY_ROADMAP.md` |
| 2026-04-30 | Organize work by multi-step delivery batches and workstreams. | The build needs planned, coherent upgrades with lookahead rather than one-off implementation steps. | `docs/SOLUTION_DESIGN_AND_DELIVERY_ROADMAP.md` |
