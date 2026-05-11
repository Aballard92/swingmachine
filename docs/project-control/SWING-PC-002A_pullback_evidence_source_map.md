# SWING-PC-002A - PULLBACK Evidence Source Map

Status: `READY_WITH_LIMITATIONS`
Scope: read-only evidence/source map plus this documentation file

## 1. Purpose

This document maps the existing SwingMachine evidence sources for a future `SWING-PC-002` offline PULLBACK fill/lifecycle diagnostic report. It exists to confirm what can be implemented from current artifacts without guessing, inventing fields, changing strategy behavior, or running any replay/paper/live/broker path.

Current gates remain unchanged:

- Paper trading: `BLOCKED`
- Live trading: `PROHIBITED`
- Serious full qualification: `BLOCKED_UNTIL_REVISED_CANDIDATE_SELECTED_FOR_OFFLINE_QUALIFICATION`
- Revised profile build: not authorized
- Broker commands: not authorized

## 2. Source Artifacts Found

| Source | What it appears to contain | Currency | Use in future diagnostic |
| --- | --- | --- | --- |
| `docs/project-control/SWING-PC-001_pullback_fill_lifecycle_research_design.md` | Accepted design packet defining research questions, required evidence, GO/NO-GO/INCONCLUSIVE criteria, and stop conditions. | Current | Yes, controlling design input. |
| `docs/swing_machine_v0_1_next_baseline_candidate_selection.md` | Stable docs version of latest selection packet: no revised baseline selected; next work is deeper PULLBACK fill/lifecycle research. | Current | Yes, gate/decision context. |
| `docs/swing_machine_v0_1_revised_candidate_hypothesis_gate.md` | Gate says `DO_NOT_BUILD_REVISED_PROFILE_YET`; PULLBACK contradiction is only partial and provider-positive edge fails. | Current | Yes, gate/decision context. |
| `reports/swing_machine_v0_1/historical_research_artifact_index_20260508T080800Z/historical_research_artifact_index.md` | Index of current versus superseded/context artifacts; paper trading blocked. | Current generated index | Yes, helps avoid stale report selection. |
| `reports/swing_machine_v0_1/pullback_traded_vs_accepted_root_cause_20260508T081457Z/pullback_traded_vs_accepted_root_cause.json` | PULLBACK root-cause metrics: all accepted, traded accepted, untraded accepted populations; forward returns, SPY-excess returns, net PnL, win rate, feature summaries. | Current for PULLBACK contradiction | Yes, primary summary input. |
| `reports/swing_machine_v0_1/pullback_traded_vs_accepted_root_cause_20260508T081457Z/pullback_traded_vs_accepted_root_cause.md` | Human-readable root-cause packet: all accepted PULLBACK 27 rows, traded 4 rows, untraded 23 rows; conclusion says deeper replay only. | Current for PULLBACK contradiction | Yes, citation-friendly summary. |
| `reports/swing_machine_v0_1/feature_outcome_attribution_broad_feature_snapshot_20260507T224500Z/feature_outcome_attribution_dataset.json` | Broad Alpaca attribution source dataset with 4,640 rows, 51 accepted, 9 traded, 27 PULLBACK accepted, forward returns, benchmark returns, SPY-excess returns, trade flags, lifecycle outcome fields, and feature snapshots. | Current primary row-level dataset | Yes, primary row-level input. |
| `reports/swing_machine_v0_1/feature_outcome_attribution_broad_feature_snapshot_20260507T224500Z/feature_outcome_attribution_rows.csv` | Flat CSV view of the same attribution rows; 45 columns including candidate identity, decision, pattern, traded flag, trade id, entry/exit dates, exit reason, bars held, net PnL/return, forward returns, benchmark returns, excess returns, and feature columns. | Current primary row-level dataset | Yes, convenient tabular input. |
| `reports/swing_machine_v0_1/pattern_specific_benchmark_diagnostic_broad_20260508T062913Z/pattern_specific_benchmark_diagnostic_report.json` | Pattern-level diagnostic: PULLBACK mixed, TIGHT_BASE negative/isolate; includes accepted/traded counts and benchmark-relative metrics by pattern. | Current pattern diagnostic | Yes, summary/cross-check. |
| `reports/swing_machine_v0_1/traded_lifecycle_decomposition_broad_20260508T011500Z/traded_lifecycle_decomposition_report.json` | Traded lifecycle decomposition by setup type, exit reason, bars-held bucket, feature bucket; PULLBACK 4 trades, net PnL 633.99, win rate 0.75, average bars held 9.5. | Current lifecycle summary | Yes, lifecycle summary input. |
| `reports/swing_machine_v0_1/cost_slippage_stress_broad_20260508T080525Z/cost_slippage_stress_report.json` | Cost/slippage stress scenarios overall, by pattern, and by feature bucket; includes 0/5/10/25/50 bps scenario metrics. | Current cost stress | Yes, cost input. |
| `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/provider_accepted_vs_near_miss_comparison/provider_accepted_vs_near_miss_comparison.json` | Provider comparison for contract window; stable enough for research but no positive accepted edge across both providers. | Current provider comparison | Yes, provider limitation input. |
| `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/alpaca_feature_outcome_attribution/feature_outcome_attribution_dataset.json` | Alpaca contract-window row-level attribution dataset. | Current provider row dataset | Yes, optional provider cross-check. |
| `reports/swing_machine_v0_1/provider_matched_attribution_contract_20260508T070500Z/huggingface_feature_outcome_attribution/feature_outcome_attribution_dataset.json` | Hugging Face contract-window row-level attribution dataset with coverage limitations. | Yes, optional provider cross-check with explicit limitation. |
| `reports/swing_machine_v0_1/warmup_null_aware_denominator_audit_v2_20260508T082357Z/warmup_null_aware_denominator_audit.json` | Null-aware denominator audit v2; core feature null filtering does not change accepted-edge conclusion. | Current; supersedes first denominator audit | Yes, denominator/feature coverage guardrail. |
| `reports/swing_machine_v0_1/feature_null_stability_audit_20260508T080049Z/feature_null_stability_audit.json` | Feature null/stability audit across broad Alpaca and contract provider artifacts; warns about warm-up nulls and candidate score coverage. | Current feature stability context | Yes, field-coverage caveat. |
| `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T155720Z/portfolio_lifecycle_trade_ledger.json` | Source broad lifecycle trade ledger referenced by the primary attribution dataset; 9 trades with entry/exit fills, prices, stops, PnL, return, setup id, and trade id. | Current primary lifecycle ledger for broad attribution | Yes, primary trade-detail input. |
| `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T155720Z/portfolio_lifecycle_pending_orders.json` | Broad lifecycle pending orders; 46 rows with order status, cancel reason, session date, setup id, order type, quantity, stop/limit prices. | Current primary order-detail input | Yes, fill/non-fill input with join limitations. |
| `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T155720Z/portfolio_lifecycle_transitions.json` | Broad lifecycle transitions; 44 rows with state transitions, triggers, setup id, symbol, session date, reason codes. | Current primary lifecycle-transition input | Yes, transition-path input. |
| `reports/swing_machine_v0_1/scanner_broad_research_20260507T164230Z/scanner_material_decisions.json` | Source broad scanner decisions referenced by the primary attribution dataset; 4,640 material rows, 51 `ACCEPTED_SETUP`, 27 accepted PULLBACK, 24 accepted TIGHT_BASE. | Current primary scanner row input | Yes, scanner/candidate state input. |
| `reports/swing_machine_v0_1/scanner_broad_research_20260507T164230Z/scanner_rejection_reasons.json` | Rejection reason counts by session and aggregate. | Current scanner support artifact | Yes, optional rejection summary. |
| `reports/swing_machine_v0_1/paper_readiness_blocker_refresh_20260508T081020Z/paper_readiness_blocker_refresh.md` | Paper-readiness blocker refresh; explicitly says do not start paper trading or live execution. | Current gate evidence | Yes, gate reminder only. |
| `config/swing_machine_v0_1_pullback_only_config.yaml` | Historical offline controlled PULLBACK-only revision config. | Superseded as deployable candidate; no revised profile selected | No for implementation input; only context if needed. |
| `config/swing_machine_v0_1_pullback_only_profile.yaml` | Historical profile alias for PULLBACK-only revision. | Superseded/not current candidate | No for implementation input. |
| Older paper runbooks and paper-readiness docs under `docs/` | Historical paper/paper-review context. | Stale/superseded by current blocked gates | No; must not be treated as approval. |

## 3. Field Availability Check

Verdict key: `FOUND`, `PARTIAL`, `NOT_FOUND`, `UNKNOWN`.

| Field group | Verdict | Evidence |
| --- | --- | --- |
| Candidate identity | `FOUND` | `feature_outcome_attribution_rows.csv` has `symbol`, `signal_session`, `next_session`, `candidate_id`, `setup_id`, `pattern_type`, and `panel_id`. Scanner decisions have the same core candidate/session/setup fields. Provider/source window is available through `panel_id`, source paths, and provider-specific artifact directories. |
| Candidate state | `FOUND` | Scanner and attribution rows expose `decision` (`ACCEPTED_SETUP`/`REJECTED`), `reason_codes`, `rejection_reasons`, `candidate_rejection_reasons`, `signal_rejection_reasons`, `risk_rejection_reasons`, `order_rejection_reasons`, `candidate_score_pct`, `rank`, and raw feature snapshot fields. Feature buckets exist in summary reports; future code may need to bucket raw feature fields explicitly. |
| Trade/fill state | `PARTIAL` | Attribution rows expose `traded`, `trade_id`, `entry_fill_date`, `exit_fill_date`, `exit_reason`, `bars_held`, `net_pnl`, and `net_return`. Trade ledger has `entry_fill_date`, `entry_fill_price`, `entry_reference_price`, `quantity`, and transaction costs. Pending orders have `status` (`ACTIVE`/`FILLED`/`CANCELLED`), `cancel_reason`, `order_type`, `session_date`, `setup_id`, `stop_price`, and `limit_price`. There is no single canonical row-level `filled` field in the attribution dataset; filled/unfilled status must be joined from pending orders/trades by `setup_id`/`trade_id`. |
| Lifecycle state | `PARTIAL` | Trade ledger has `exit_fill_date`, `exit_reason`, `bars_held`, `initial_stop`, `final_stop`, and trade ids. Transitions have `from_state`, `to_state`, `trigger`, `reason_codes`, `session_date`, and `setup_id`. Exit reasons indicate stop/time/trail outcomes, but explicit `stop_hit` and `target_hit` boolean fields were not found. Target behavior appears unavailable unless implemented from existing lifecycle semantics. |
| Outcome | `PARTIAL` | Attribution rows and trade ledger expose `net_pnl`, `net_return`, forward close returns, benchmark forward close returns, and forward close excess returns for 1/5/10/20 days. Historical performance artifacts expose drawdown at aggregate/equity levels. Direct per-trade `r_multiple`, max adverse excursion, and max drawdown fields were not found in the inspected row-level artifacts. R may be derivable for traded rows from entry/initial stop and PnL, but must be labelled derived and may not be available for unfilled candidates. |
| Cost/slippage | `FOUND` | `cost_slippage_stress_report.json` exposes base and stressed scenario metrics for 0/5/10/25/50 bps overall and by pattern, including PULLBACK. Trade ledger exposes transaction costs for realized trades. |

### Specific SWING-PC-001 Field Checklist

| Required field | Status | Notes |
| --- | --- | --- |
| `symbol` | `FOUND` | Attribution, scanner, lifecycle, pending orders, transitions. |
| setup date | `FOUND` | `signal_session`, `next_session`, and `entry_signal_date`; no literal `setup_date` name needed if mapped. |
| pattern/setup type | `FOUND` | `pattern_type` in scanner/attribution; setup type in lifecycle summaries. |
| provider/source window | `PARTIAL` | `panel_id`, source paths, provider-specific directories; broad rows are Alpaca-side by source, provider is not always a per-row field. |
| accepted candidate status | `FOUND` | `decision=ACCEPTED_SETUP` in scanner/attribution. |
| rejection/acceptance reason | `FOUND` | `reason_codes` and rejection arrays; accepted rows generally use `SETUP_VALID`. |
| candidate score or feature bucket | `PARTIAL` | `candidate_score_pct` exists but has null caveats in some broad feature snapshots; raw feature fields exist, bucket labels mainly in reports. |
| traded flag | `FOUND` | `traded` in attribution rows. |
| filled flag | `PARTIAL` | Pending order `status=FILLED` and trade ledger entries exist; not a direct attribution field. |
| fill date | `FOUND` | `entry_fill_date` in attribution/trade ledger. |
| fill price | `FOUND` | `entry_fill_price` in trade ledger. |
| entry type | `FOUND` | `order_type` in pending orders; not directly in attribution rows. |
| non-fill/expiry/cancel reason | `PARTIAL` | `cancel_reason` in pending orders; requires setup-level join and may not classify every untraded accepted candidate. |
| exit date | `FOUND` | `exit_fill_date`. |
| exit reason | `FOUND` | `exit_reason`. |
| bars held | `FOUND` | `bars_held`. |
| stop hit | `PARTIAL` | Inferred only from `exit_reason` values like `INITIAL_STOP`/`TRAIL_STOP`; no explicit boolean found. |
| target hit | `NOT_FOUND` | No explicit target-hit field found in inspected artifacts. |
| transition path | `FOUND` | `portfolio_lifecycle_transitions.json` has state transition rows by `setup_id`. |
| net PnL | `FOUND` | `net_pnl`. |
| net return | `FOUND` | `net_return`. |
| R multiple | `PARTIAL` | Not direct. May be derived for filled trades if initial risk can be reconstructed; do not fake it for unfilled candidates. |
| max drawdown/adverse excursion | `PARTIAL` | Aggregate drawdown artifacts and feature drawdown fields exist; per-trade MAE/max drawdown not found. |
| benchmark/SPY return | `FOUND` | `benchmark_forward_close_returns` / flat CSV benchmark return columns. |
| benchmark excess return | `FOUND` | `forward_close_excess_returns` / flat CSV excess return columns. |
| forward returns | `FOUND` | 1/5/10/20 day forward close returns in primary attribution dataset; SWING-PC-001's 40-day window is not present in current row dataset. |
| base cost result | `FOUND` | Cost stress report scenario `0` and trade ledger transaction costs. |
| stressed cost result | `FOUND` | Cost stress report scenarios include 10/25/50 bps. |

## 4. Implementation Feasibility

Verdict: `READY_WITH_LIMITATIONS`

`SWING-PC-002` can be implemented cleanly as an offline diagnostic using existing artifacts if the first version is honest about limitations.

Ready inputs:

- Row-level accepted/traded/untraded PULLBACK attribution.
- Scanner decision rows and reason codes.
- Lifecycle trade ledger, pending orders, and transitions.
- Forward raw, benchmark, and SPY-excess returns for 1/5/10/20 days.
- Pattern-level, lifecycle-level, provider-level, and cost-stress summaries.
- Current decision/gate docs.

Limitations:

- Filled/unfilled status is not a single field in the primary attribution rows; it requires joining pending orders and trade ledger by `setup_id`/`trade_id`.
- Direct R multiple is not present; deriving it must be explicit and may only apply to filled trades with sufficient risk fields.
- Per-trade max adverse excursion and max drawdown were not found in the inspected row-level artifacts.
- Explicit target-hit fields were not found.
- Provider comparison should remain a separate contract-window cross-check, not merged into the broad Alpaca window without a provider policy.
- Current forward-return windows are 1/5/10/20 days in the primary attribution dataset; 40-day evidence would require either additional existing artifacts or a future explicit extension.

## 5. Implementation Warning List

Future implementation must not:

- Infer filled versus unfilled status if pending-order/trade-ledger joins are missing or ambiguous.
- Treat `traded=True` as equivalent to every accepted candidate's fill eligibility.
- Invent `target_hit`, R multiple, max adverse excursion, or per-trade drawdown fields.
- Treat broad Alpaca and contract-window Hugging Face datasets as one merged population.
- Treat stale paper-readiness reports or old paper runbooks as current approval.
- Treat the historical PULLBACK-only config/profile as a selected candidate.
- Change strategy logic, config, or profile files to make the diagnostic easier.
- Run scanner or lifecycle replays as part of SWING-PC-002A.
- Run paper trading, live trading, or broker commands.
- Edit generated reports in place.
- Hide provider/data limitations behind a `GO` decision.

## 6. Suggested SWING-PC-002 Implementation Scope

Proceed with `SWING-PC-002` only after this map is reviewed.

Recommended scope:

- Build an offline-only report generator that reads existing artifacts and writes a new timestamped diagnostic output directory.
- Primary input: `reports/swing_machine_v0_1/feature_outcome_attribution_broad_feature_snapshot_20260507T224500Z/feature_outcome_attribution_dataset.json` or its CSV equivalent.
- Primary scanner input: `reports/swing_machine_v0_1/scanner_broad_research_20260507T164230Z/scanner_material_decisions.json`.
- Primary lifecycle inputs:
  - `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T155720Z/portfolio_lifecycle_trade_ledger.json`
  - `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T155720Z/portfolio_lifecycle_pending_orders.json`
  - `reports/swing_machine_v0_1/lifecycle_broad_research_20260507T155720Z/portfolio_lifecycle_transitions.json`
- Supporting inputs:
  - PULLBACK root-cause packet
  - pattern-specific benchmark diagnostic
  - traded lifecycle decomposition
  - cost/slippage stress report
  - provider comparison report and provider attribution datasets
  - null-aware denominator and feature-stability reports

Likely files to create in the future task:

- `reports/swing_machine_v0_1/pullback_fill_lifecycle_research_<timestamp>/pullback_fill_lifecycle_research.json`
- `reports/swing_machine_v0_1/pullback_fill_lifecycle_research_<timestamp>/pullback_fill_lifecycle_research.md`
- Focused tests for row loading, PULLBACK population splits, pending-order/trade joins, cost metric extraction, and GO/NO-GO/INCONCLUSIVE classification.

Likely modules involved:

- `src/swingmachine/feature_outcomes.py` for attribution/reporting style and existing metric helpers.
- `src/swingmachine/replay.py` only for artifact schema knowledge, not for running replays.
- `src/swingmachine/contracts.py` if a typed report contract is added.
- `tests/test_feature_outcomes.py` as the closest test pattern for attribution/report writers.

Known limitations to carry into the first diagnostic:

- Use 1/5/10/20 day forward windows unless a later task explicitly adds 40-day returns.
- Mark R multiple and adverse excursion as derived/unavailable unless safely computed from existing trade fields.
- Treat provider evidence as a separate limitation/cross-check section.
- Keep TIGHT_BASE out of scope except as a warning/reference.

Implementation should proceed as `READY_WITH_LIMITATIONS`, not as a profile-building or paper-readiness task.

## 7. Gate Confirmation

- No paper trading is authorized or triggered by this map.
- No live trading is authorized or triggered by this map.
- No broker command is authorized or triggered by this map.
- No source code, test, config, data, generated report, migration, broker/runtime path, or strategy profile change is authorized by this map.
