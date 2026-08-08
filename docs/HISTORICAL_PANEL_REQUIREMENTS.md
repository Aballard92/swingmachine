# Historical Panel and Replay Requirements

Generated: 2026-04-30

This document turns the current design/build questions into explicit
requirements. The purpose is to validate the machinery before we evaluate the
strategy. This is not a performance-baselining plan.

## 1. Plain-English Goal

Before we ask "does this strategy make money?", we need to answer a smaller and
more important set of engineering questions:

1. Can Swingmachine read a properly defined historical data panel?
2. Can it reject bad, incomplete, or contradictory data?
3. Can it replay the same input deterministically?
4. Can it explain what decisions it made?
5. Can backtest, shadow, paper, audit, and review outputs remain internally
   consistent?

Passing these checks means the workshop tools are becoming trustworthy. It does
not mean the strategy is good, profitable, deployable, or ready for live trading.

## 2. Non-Goals

Do not use this phase to:

- Baseline strategy returns.
- Optimize parameters.
- Compare strategy performance against benchmarks.
- Tune thresholds for profitability.
- Add live broker integrations.
- Add vendor-specific ingestion.
- Build dashboards before artifact semantics are stable.
- Claim production readiness from local replay success.

## 3. Required Terms

Historical panel:

- A named, versioned bundle of prepared files covering symbols, sessions,
  prices, corporate actions, earnings events, and symbol reference data.

Manifest:

- A machine-readable file that identifies what files belong to a historical
  panel, what schemas they use, what dates/symbols they claim to cover, and what
  validation expectations apply.

Replay:

- A deterministic run over a validated panel that records inputs, decisions,
  outputs, and review artifacts for inspection.

Baseline-worthy:

- A later state where data contracts, replay determinism, decision explanations,
  and audit consistency are strong enough that strategy-performance baselining
  would not be measuring obvious plumbing defects.

## 4. Requirement Themes

### Q1: Can The System Read A Properly Defined Data Panel?

Requirement HP-READ-1: Panel Manifest

- The system must accept one manifest path as the entry point for a historical
  panel.
- The manifest must include:
  - `panel_id`
  - `schema_version`
  - `created_at`
  - `description`
  - `base_path` or relative file paths
  - `calendar`
  - `timezone`
  - `start_session`
  - `end_session`
  - expected symbol count
  - expected session count
  - file entries for OHLCV, symbol reference, corporate actions, and earnings
  - optional file checksums or row counts

Requirement HP-READ-2: Required Files

- The first manifest-backed panel must describe these files:
  - historical OHLCV
  - symbol reference
  - corporate actions
  - earnings events
- Files may be CSV first. Parquet can be added when larger panels justify it.
- File paths must resolve relative to the manifest unless absolute paths are
  explicitly allowed later.

Requirement HP-READ-3: Clear Contract Boundary

- The repo should validate and consume prepared panels.
- The repo should not fetch external data during this phase.
- Any source/vendor metadata should be descriptive only, not code behavior.

Acceptance evidence:

- A valid tiny panel fixture loads from one manifest.
- The loaded contract reports panel id, session range, symbol count, file paths,
  and validation status.
- The implementation does not make network calls.

Likely files:

- `src/swingmachine/data_contracts.py`
- `src/swingmachine/contracts.py`
- `tests/test_data_contracts.py`
- `examples/`
- `tests/fixtures/`

### Q2: Can It Reject Bad, Incomplete, Or Contradictory Data?

Requirement HP-VALIDATE-1: Existing File-Level Validation

- Existing validators for next-session market data, symbol reference, corporate
  actions, and earnings events should be reused or extended where possible.
- Validation errors must be explicit enough for an operator to fix the input.

Current evidence:

- `validate_next_session_market_data`
- `validate_symbol_reference_data`
- `validate_corporate_actions_data`
- `validate_earnings_events_data`
- `tests/test_data_contracts.py`

Requirement HP-VALIDATE-2: Historical OHLCV Validation

- Historical OHLCV validation must reject:
  - missing required columns
  - blank symbols
  - invalid session dates
  - duplicate `symbol` + `session_date` rows
  - non-positive prices
  - negative volume
  - impossible high/low/open/close relationships
  - rows outside manifest session range

Requirement HP-VALIDATE-3: Cross-File Validation

- Whole-panel validation must reject:
  - OHLCV symbols missing from symbol reference
  - OHLCV symbol/session rows with no active symbol reference row
  - overlapping symbol reference effective windows
  - feature coverage gaps for tradable reference rows inside the selected replay
    scope
  - prepared feature row metadata that does not match the active symbol
    reference row for the same symbol/session
  - corporate-action symbols not present in reference data
  - earnings symbols not present in reference data
  - duplicate symbol/session keys
  - empty panel after filters
  - declared manifest counts that do not match observed data, when counts are
    provided

Requirement HP-VALIDATE-4: Time and Calendar Checks

- Validation must identify:
  - panel start/end sessions
  - gaps in expected sessions at panel level
  - symbols with incomplete histories
  - sessions outside the declared calendar
- The first implementation can report incomplete symbol histories as warnings if
  the replay can still fail closed later.

Requirement HP-VALIDATE-5: Validation Result Contract

- Validation should return a structured result, not only raise exceptions.
- Suggested fields:
  - `panel_id`
  - `status`: `PASS`, `WARN`, or `FAIL`
  - `errors`
  - `warnings`
  - `file_summaries`
  - `symbol_count`
  - `session_count`
  - `start_session`
  - `end_session`
  - `validated_at`

Acceptance evidence:

- Tests cover one valid tiny panel and malformed panels for:
  - missing file
  - missing required column
  - duplicate symbol/session
  - invalid OHLC
  - unknown earnings session
  - corporate action for unknown symbol
  - manifest count mismatch
- Error messages name the failing file and field.

Likely files:

- `src/swingmachine/data_contracts.py`
- `src/swingmachine/contracts.py`
- `tests/test_data_contracts.py`

### Q3: Can It Replay Deterministically?

Status: initial tiny replay proof implemented through
`run_tiny_manifest_replay_proof`; general replay runner pending.

Requirement HP-REPLAY-1: Replay Entry Point

- Replay must start from a validated manifest, not from ad hoc file arguments.
- The command or service should record:
  - manifest path
  - panel id
  - config path
  - output directory
  - database URL
  - run id
  - started/finished timestamps

Requirement HP-REPLAY-2: Deterministic Output

- Running the same manifest and config twice should produce the same material
  decisions:
  - candidate set
  - setup ids
  - order intent ids or stable logical equivalents
  - shadow comparison outcomes
  - audit summary counts
  - review status categories

Requirement HP-REPLAY-3: Stable Time Handling

- Replay must make session dates explicit.
- Replay must not depend on wall-clock time except for metadata fields such as
  `generated_at` or `started_at`.
- Any generated timestamps must be excluded from deterministic equality checks
  or compared separately.

Requirement HP-REPLAY-4: Failure Preservation

- If replay fails, it must leave enough evidence to diagnose:
  - panel id
  - failing symbol
  - failing session
  - failing stage
  - validation or runtime error message

Acceptance evidence:

- A tiny panel replay test runs twice and compares material outputs. Completed
  for the replay proof.
- A malformed panel does not enter replay. Completed for missing OHLCV file.
- A replay failure writes or returns a structured failure summary.
- Tests do not assert profitability. Completed.

Likely files:

- `src/swingmachine/runtime.py`
- `src/swingmachine/research.py`
- `src/swingmachine/backtest.py`
- `src/swingmachine/run_history.py`
- `tests/test_replay_workflow.py`
- `tests/test_runtime.py`

### Q4: Can It Explain What Decisions It Made?

Requirement HP-EXPLAIN-1: Decision Trace

- Replay must preserve enough per-symbol/per-session information to explain why
  a setup was accepted, rejected, submitted, expired, filled, or not filled.
- Explanation does not need to be beautiful UI yet. JSON artifacts are enough.

Requirement HP-EXPLAIN-2: Stage-Level Artifacts

- A replay output directory should include stage artifacts for:
  - validation summary
  - candidate scoring summary
  - setup detection summary
  - backtest summary
  - shadow result
  - shadow comparison summary
  - paper/audit summary where applicable
  - operator review summary where applicable

Requirement HP-EXPLAIN-3: Rejection Reasons

- Rejected or skipped decisions should include reason categories where feasible:
  - data validation failure
  - regime disabled
  - ranking threshold not met
  - setup invalid
  - risk sizing rejected
  - order guardrail rejected
  - missing next-session market data
  - shadow/paper mismatch

Requirement HP-EXPLAIN-4: No Performance Claims In Explanation Artifacts

- Explanation artifacts may report counts, statuses, alignment, and failure
  reasons.
- They should not present CAGR, Sharpe, win rate, or strategy score as a
  progression criterion in this phase.

Acceptance evidence:

- A replay artifact lets an operator trace at least one accepted setup from
  panel row -> features/signals -> setup -> order intent -> shadow/audit result.
- A rejected setup or invalid panel has a readable reason.
- The review surface remains focused on mechanics and consistency, not
  profitability.

Likely files:

- `src/swingmachine/reporting.py`
- `src/swingmachine/runtime.py`
- `src/swingmachine/contracts.py`
- `tests/test_replay_workflow.py`
- `tests/test_reporting.py`

### Q5: Can Backtest, Shadow, Paper, Audit, And Review Stay Internally Consistent?

Requirement HP-CONSISTENCY-1: Shared Identity

- Replay artifacts must use stable identifiers for:
  - panel id
  - run id
  - symbol
  - session
  - setup id
  - order intent id
  - snapshot batch id where applicable

Requirement HP-CONSISTENCY-2: Count Reconciliation

- The system must reconcile key counts across stages:
  - setups detected
  - entry intents created
  - shadow proposals
  - shadow fills
  - paper submissions
  - audit records
  - review checks

Requirement HP-CONSISTENCY-3: Known Difference Categories

- Differences between backtest, shadow, and paper should be categorized rather
  than hidden:
  - missing market data
  - order would not trigger
  - order would trigger but not fill paper state yet
  - slippage threshold breach
  - paper intent missing
  - shadow proposal missing
  - lifecycle expiration/cancel behavior

Requirement HP-CONSISTENCY-4: Review Status Separation

- Review `PASS` means the local machinery stayed internally consistent for that
  sample.
- Review `WARN` means inspect before expanding scope.
- Review `FAIL` means the run is not valid evidence.
- None of these statuses means "the strategy is profitable."

Acceptance evidence:

- A fixture replay produces expected count reconciliation.
- A fixture with an intentional mismatch reports a non-pass review category.
- `summarize-review-run-trends` can show whether consistency issues recur
  across repeated runs.

Likely files:

- `src/swingmachine/reporting.py`
- `src/swingmachine/paper_shadow_audit.py`
- `src/swingmachine/shadow_reviews.py`
- `src/swingmachine/run_history.py`
- `tests/test_reporting.py`
- `tests/test_runtime.py`

## 5. Traceability Matrix

| Question | Requirement IDs | Build Output | Evidence We Need |
| --- | --- | --- | --- |
| Can it read a panel? | HP-READ-* | Manifest loader and valid tiny panel | Valid fixture loads from one manifest |
| Can it reject bad data? | HP-VALIDATE-* | Whole-panel validator | Focused invalid-panel tests |
| Can it replay deterministically? | HP-REPLAY-* | Manifest-backed replay service/CLI | Same material outputs across repeated runs |
| Can it explain decisions? | HP-EXPLAIN-* | Stage artifacts and reason categories | Operator can trace one accepted and one rejected case |
| Can stages stay consistent? | HP-CONSISTENCY-* | Reconciliation and review checks | Count reconciliation and non-pass mismatch tests |

## 6. First Work Package

Work package name: historical panel manifest and validator.

Status: initial implementation completed.

Scope:

- Manifest shape is implemented through `HistoricalPanelManifest`.
- Tiny valid panel fixture exists under `tests/fixtures/historical_panel/`.
- Whole-panel validation result is implemented through
  `HistoricalPanelValidationResult`.
- Negative tests cover malformed panels in `tests/test_data_contracts.py`.
- README and runbook document how to point the validator at a panel.

Non-goals:

- No general replay command as part of this work package.
- No strategy return metrics.
- No optimization.
- No external ingestion.
- No dashboard.

Done when:

- A valid tiny panel returns structured `PASS` validation. Completed.
- Known malformed panels return structured `FAIL` validation or raise clear
  validation errors. Completed for the first malformed-panel set.
- The validator can be used as the required precondition for replay. Completed
  as a function-level contract; replay consumption is next.
- Docs make clear this is machinery validation, not strategy validation.
  Completed.

## 7. When Strategy Baselining Becomes Appropriate

Do not baseline until all of these are true:

- Manifest validation exists and catches obvious bad data.
- Replay is deterministic for the same manifest and config.
- Decision artifacts explain accepted and rejected setups.
- Backtest/shadow/paper/audit/review counts reconcile or explain differences.
- Repeated review trends are stable enough to distinguish recurring defects from
  isolated fixture problems.
- The team has explicitly chosen performance metrics and accepted their
  limitations.

Until then, tests should answer "did the machine behave coherently?", not "is
the strategy good?"
