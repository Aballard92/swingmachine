# Swing Machine v0.1 mechanical readiness solution design

Date: 2026-05-07
Baseline: `swing_machine_v0_1`
Status: implementation-ready design

## Purpose

Define the concrete implementation needed to move the swing machine from mechanically qualified in parts to mechanically ready as a coherent engine.

This design covers `SWING-V01-137` through `SWING-V01-142`.

## Target architecture

Add a mechanical readiness layer that sits above existing qualification artifacts.

Components:

- `mechanical_readiness.py`
  - Evidence discovery.
  - Evidence loading.
  - Decision evaluation.
  - JSON/markdown report writing.

- `lookahead_audit.py` or `data_contracts.py` extension
  - Point-in-time feature checks.
  - Session-window checks.
  - Symbol-reference effective/tradability checks.
  - Earnings timing checks.

- `decision_ledger.py`
  - Joins scanner, signal, risk, order, lifecycle, position, and trade evidence.
  - Emits row-level explainability package.

- Existing modules extended as needed:
  - `runtime.py` for CLI commands.
  - `contracts.py` for typed report models.
  - `replay.py` for artifact readers/writers if reuse is cleaner.

## New CLI commands

### `build-mechanical-readiness-report`

Proposed signature:

```bash
.venv/bin/swingmachine build-mechanical-readiness-report \
  --output reports/swing_machine_v0_1/mechanical_readiness_<RUN_ID>.json \
  --markdown-output reports/swing_machine_v0_1/mechanical_readiness_<RUN_ID>.md \
  --profile-alias config/swing_machine_v0_1_profile.yaml \
  --manifest data/qualification_manifests/trading212/alpaca_historical_broad/historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml \
  --scanner-summary reports/.../scanner...json \
  --lifecycle-summary reports/.../historical_broad_lifecycle_qualification_summary_20260507T065158Z.json \
  --pre-paper-gate reports/.../pre_paper_test_gate_summary.json \
  --dry-run-safety reports/.../first_paper_preflight_20260507T075235Z.json
```

Default behaviour:

- If artifact paths are omitted, discover latest matching files under `reports/swing_machine_v0_1/`.
- Discovery must be deterministic by timestamp/run id.
- Missing evidence is a blocker.
- Stale evidence after latest code/config change is a warning initially, blocker if implemented later with git/build metadata.

### `build-decision-ledger`

Proposed signature:

```bash
.venv/bin/swingmachine build-decision-ledger \
  --scanner-output-dir reports/.../scanner_broad_research_<RUN_ID> \
  --lifecycle-output-dir reports/.../lifecycle_broad_research_<RUN_ID> \
  --output reports/swing_machine_v0_1/decision_ledger_<RUN_ID>.json \
  --markdown-output reports/swing_machine_v0_1/decision_ledger_<RUN_ID>.md
```

Default behaviour:

- Read scanner material decisions, scanner session results, lifecycle transitions, lifecycle positions, lifecycle pending orders, and lifecycle reconciliation.
- Join by symbol, setup id, session date, order intent id where available, and position id where available.
- Emit missing-link warnings.

## Typed contracts

Add to `contracts.py` or a dedicated contracts module.

### MechanicalReadinessDecision

Fields:

- `baseline_id: str`
- `run_id: str`
- `generated_at: datetime`
- `status: ReviewStatus`
- `decision: Literal["PASS", "WARN", "BLOCK"]`
- `profile_alias_path: str`
- `manifest_path: str`
- `config_hash: str | None`
- `evidence: tuple[MechanicalReadinessEvidence, ...]`
- `checks: tuple[MechanicalReadinessCheck, ...]`
- `blockers: tuple[str, ...]`
- `warnings: tuple[str, ...]`
- `next_required_actions: tuple[str, ...]`

### MechanicalReadinessEvidence

Fields:

- `evidence_id: str`
- `evidence_type: str`
- `path: str`
- `status: ReviewStatus`
- `run_id: str | None`
- `summary: dict[str, Any]`

Evidence types:

- `profile_alias`
- `historical_manifest`
- `scanner_qualification`
- `scanner_parity`
- `lifecycle_qualification`
- `lifecycle_parity`
- `full_test_gate`
- `dry_run_safety`
- `lookahead_audit`
- `decision_ledger`
- `risk_portfolio_adversarial_tests`
- `exit_lifecycle_adversarial_tests`

### MechanicalReadinessCheck

Fields:

- `check_id: str`
- `category: str`
- `status: ReviewStatus`
- `observed: Any`
- `expected: Any`
- `severity: Literal["INFO", "WARNING", "BLOCKER"]`
- `message: str`

### LookaheadAuditReport

Fields:

- `panel_id: str`
- `manifest_path: str`
- `status: ReviewStatus`
- `checked_at: datetime`
- `feature_window_check: ReviewStatus`
- `symbol_reference_check: ReviewStatus`
- `earnings_timing_check: ReviewStatus`
- `session_order_check: ReviewStatus`
- `violations: tuple[LookaheadAuditViolation, ...]`
- `warnings: tuple[str, ...]`

### LookaheadAuditViolation

Fields:

- `code: str`
- `symbol: str | None`
- `session_date: date | None`
- `field: str | None`
- `observed: Any`
- `expected: Any`
- `message: str`

### DecisionLedgerRow

Fields:

- `ledger_id: str`
- `panel_id: str`
- `symbol: str`
- `signal_session: date | None`
- `next_session: date | None`
- `setup_id: str | None`
- `decision: str`
- `reason_codes: tuple[str, ...]`
- `candidate_score_pct: float | None`
- `rank: int | None`
- `signal_id: str | None`
- `risk_plan_id: str | None`
- `order_plan_id: str | None`
- `order_intent_id: str | None`
- `position_id: str | None`
- `lifecycle_state: str | None`
- `entry_submitted: bool`
- `entry_filled: bool`
- `entry_cancelled: bool`
- `exit_submitted: bool`
- `exit_filled: bool`
- `trade_closed: bool`
- `missing_links: tuple[str, ...]`

### DecisionLedgerReport

Fields:

- `panel_id: str`
- `run_id: str`
- `status: ReviewStatus`
- `generated_at: datetime`
- `row_count: int`
- `accepted_setup_count: int`
- `rejected_candidate_count: int`
- `missing_link_count: int`
- `rows: tuple[DecisionLedgerRow, ...]`
- `warnings: tuple[str, ...]`

## Mechanical readiness decision matrix

### PASS

All are true:

- Profile alias loads.
- Manifest validation passes.
- Lookahead audit passes.
- Broad scanner qualification status is `PASS`.
- Scanner parity difference count is `0`.
- Broad lifecycle qualification status is `PASS`.
- Lifecycle parity difference count is `0`.
- Full ruff/pytest gate status is `PASS`.
- Dry-run safety status is `PASS`.
- Decision ledger status is `PASS` or only non-critical warnings.
- Risk/portfolio adversarial tests pass.
- Exit lifecycle adversarial tests pass.

### WARN

Any of the following:

- Optional evidence missing but not required for current phase.
- Decision ledger has non-critical missing links for rejected candidates.
- Provider comparison not yet run.
- First paper input package not yet built.

### BLOCK

Any of the following:

- Manifest validation fails.
- Lookahead audit fails.
- Scanner/lifecycle parity has material differences.
- Lifecycle reconciliation has failures or warnings.
- Full test gate fails.
- Dry-run safety fails.
- Live/paper action appears enabled before approval.
- Risk/portfolio adversarial tests fail.
- Exit lifecycle adversarial tests fail.

## Lookahead audit rules

### Feature session rule

For every decision row:

- `feature.session_date <= signal_session`
- No feature row after signal session may affect candidate score, setup, ranking, or entry plan.

### Prepared feature window rule

If manifest declares `feature_start_session`:

- No signal session before feature start can be replayed.
- Feature coverage scope must match manifest policy.

### Symbol reference rule

For every symbol/session:

- Effective start/end windows must contain the session.
- Tradable start/end windows must contain the session for tradable eligibility.
- Delisted/inactive rows must not be treated as eligible outside their windows.

### Earnings timing rule

If earnings fields are present:

- `regular_closes_until_earnings_event` must be non-negative.
- Entry eligibility must only use earnings events known or represented at the signal session.
- Missing earnings coverage is a warning unless entry logic depends on it; then blocker.

### Session ordering rule

- Historical sessions must be strictly increasing per symbol.
- Signal session must precede next execution session.
- Lifecycle fills must not occur before signal/order sessions.

## Decision ledger join rules

Primary keys:

- `symbol`
- `setup_id`
- `signal_session`
- `order_intent_id`
- `position_id`

Join priority:

1. Scanner accepted/rejected decision by symbol/session/setup.
2. Signal/risk/order plan by setup id.
3. Lifecycle transition by setup id and symbol.
4. Pending order snapshot by order intent id if available.
5. Position snapshot by position id if available, else symbol/setup/date.
6. Closed trade by symbol/setup id.

Critical missing links:

- Accepted setup without signal/risk/order evidence.
- Entry filled without pending order evidence.
- Closed trade without exit transition.
- Position snapshot without setup id.

Non-critical missing links:

- Rejected candidate without lifecycle evidence.
- Candidate without order evidence when explicitly rejected.

## Risk/portfolio adversarial test matrix

Required fixtures:

1. Duplicate symbol already pending.
2. Duplicate symbol already active.
3. Portfolio heat cap exceeded.
4. Daily new risk cap exceeded.
5. Sector cap exceeded.
6. Max open positions exceeded.
7. Invalid quantity/risk input.
8. Pending plus active conflict.

Expected outcome:

- Unsafe entry rejected.
- Explicit reject reason emitted.
- No order plan created for rejected entry.
- Lifecycle artifact does not show unsafe transition.

## Exit lifecycle adversarial test matrix

Required fixtures:

1. Initial stop hit.
2. Trailing stop activates and updates.
3. Trailing stop hit.
4. Time stop submits exit.
5. Earnings exit submits exit.
6. Pending entry expires.
7. Pending entry cancelled by open gap above limit.
8. Exit pending resolves to closed trade.

Expected outcome:

- Correct transition states.
- Correct order reason.
- Trade/equity reconciliation passes.
- Position snapshot state matches lifecycle event.

## Build sequence

1. Implement contracts for readiness, lookahead audit, and ledger.
2. Implement mechanical readiness evidence loader and report generator.
3. Implement lookahead audit.
4. Implement decision ledger generator.
5. Add risk/portfolio adversarial tests.
6. Add exit lifecycle adversarial tests.
7. Wire readiness report to include new audit/ledger/test evidence.
8. Run full pre-paper gate after completion.

## Acceptance for mechanical readiness phase

The phase is complete when:

- `build-mechanical-readiness-report` exists.
- Latest report returns `PASS` or only explicitly accepted warnings.
- Lookahead audit passes.
- Decision ledger exists and has no critical missing links.
- Risk/portfolio adversarial tests pass.
- Exit lifecycle adversarial tests pass.
- Full ruff and pytest pass after these changes.
