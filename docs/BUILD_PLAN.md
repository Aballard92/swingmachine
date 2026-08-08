# Swingmachine Build Plan

This is the short program index for the current design/build phase. The detailed
solution design and delivery roadmap is
`docs/SOLUTION_DESIGN_AND_DELIVERY_ROADMAP.md`.

The historical-panel requirements are in
`docs/HISTORICAL_PANEL_REQUIREMENTS.md`.

This phase intentionally excludes live broker integration, broker credentials,
broker-vendor-specific work, production deployment, autonomous trading, and
strategy-performance baselining.

## Working Principles

- Group work into designed delivery batches with contracts, implementation,
  tests, docs, and handover updates moving together.
- Keep paper/shadow/audit boundaries explicit until data, replay, operations,
  and approval checks are stronger.
- Treat generated reports and replay artifacts as evidence. They should be
  reproducible, inspectable, and backed by durable database rows or stable files.
- Prefer contract-tested prepared data before adding external vendor ingestion.
- Keep validation honest: record what was run and do not imply live readiness or
  profitability from local CLI success.

## Current Program

### Batch 1: Replay Platform Foundation

Status: partly complete.

Completed:

- Historical panel manifest and whole-panel validator.
- Tiny manifest-backed replay proof.
- Focused tests for valid panels, malformed panels, deterministic tiny replay,
  and invalid-panel replay refusal.

Next grouped upgrade:

- Promote the tiny proof into a general historical replay runner.
- Add run-scoped artifacts.
- Add a runtime CLI command for replay.
- Preserve validation failures as structured artifacts.
- Store basic material-decision outputs for later decision tracing.
- Keep the purpose as machinery validation, not strategy-performance validation.

## Upcoming Program Batches

### Batch 2: Decision Explanation And Reconciliation

Purpose: make material decisions and non-decisions explainable.

Planned outputs:

- Decision trace contract.
- Reason categories for accepted, rejected, skipped, submitted, filled, expired,
  and unmatched outcomes.
- Stage count reconciliation across candidate scoring, setup detection, backtest,
  shadow, paper, audit, and review.

### Batch 3: Review Over Replay Panels

Purpose: make replay evidence visible through the existing review system.

Planned outputs:

- Replay-aware JSON/HTML review report sections.
- Trend summaries across repeated replay-review runs.
- Operator guidance for recurring validation and reconciliation issues.

### Batch 4: Larger Prepared Panel Adoption

Purpose: move beyond tiny fixtures only when failures are diagnosable.

Planned outputs:

- External prepared-data path convention.
- Manifest examples for larger panels.
- Optional row-count and checksum checks.
- Artifact-size controls.

### Batch 5: Contract, Typing, And Operational Hardening

Purpose: tighten critical replay/review boundaries after the data and artifact
path is clear.

Planned outputs:

- Expanded typed-core coverage where it improves safety.
- Artifact schema tests.
- Interrupted-run recovery guidance.

## Deferred Work

These are deliberately not active:

- Live broker adapter.
- Broker-specific credentials, API permissions, or order routing.
- Production scheduler, service manager, queue, alert transport, or deployment.
- Risk/compliance control plane.
- Profitability baselining or optimization.

They should only start after historical replay, decision traceability, review
reconciliation, operator workflow, and data contracts are materially stronger.
