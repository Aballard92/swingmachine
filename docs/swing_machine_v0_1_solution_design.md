# Swing Machine v0.1 Solution Design

Created: 2026-05-05
Target baseline candidate: `swing_machine_v0_1`

Documentation location decision: this design belongs in `docs/`, matching existing roadmap and runbook files.

## 1. Target architecture

`Swing_machine_v0_1` should be a governed baseline layer over the existing swing engine.

Target component map:

```text
Baseline profile/config
  -> baseline manifest
  -> data contract validation
  -> canonical price builder
  -> feature snapshot builder
  -> universe and candidate builder
  -> eligibility gates and rejection taxonomy
  -> quality score and deterministic ranker
  -> setup/signal builder
  -> risk and portfolio planner
  -> order planner
  -> lifecycle and exit engine
  -> research/runtime parity checks
  -> reporting package
  -> qualification checklist and freeze review
```

Reuse existing modules where possible:

| Target component | Existing module to build on | Required v0.1 work |
| --- | --- | --- |
| Profile/config | `config.py`, `swing_trading_bot_config_template_v2.yaml` | Add baseline manifest and explicit v0.1 profile governance. |
| Data contracts | `data_contracts.py` | Add baseline data-contract versioning in reports/manifests. |
| Canonical prices | `canonical.py` | Ensure baseline reports state series definitions. |
| Features | `features.py`, `contracts.FeatureSnapshot` | Ensure complete candidate feature snapshots are emitted. |
| Universe/candidates | `signals.py` | Add clearer candidate/signal contracts and rejection taxonomy. |
| Ranking | `signals.py` | Expose deterministic tie-breaks and review score. |
| Risk/order | `entries.py`, `portfolio_manager.py`, `contracts.EntryPlan`, `contracts.OrderIntent` | Add baseline order/risk report contract. |
| Lifecycle/exits | `lifecycle.py`, `exits.py`, `order_state_machine.py` | Ensure all transitions record reasons. |
| Runtime | `runtime.py` | Keep paper/shadow only; attach manifest/report metadata. |
| Research/replay | `backtest.py`, `research.py`, `replay.py` | Add parity checks and qualification report package. |
| Reporting | `reporting.py`, `analytics.py` | Add baseline-specific manifest/checklist and candidate/risk/lifecycle surfaces. |

## 2. Domain model

Target domain objects:

| Object | Existing status | v0.1 design |
| --- | --- | --- |
| Swing profile/config | Exists as `StrategyRuntimeConfig` | Baseline manifest records profile path, strategy id/version, config hash, and behaviour source. |
| Swing universe member | Partial in data/reference frames | Add typed member contract or report row with eligibility reasons. |
| Swing candidate | Partial inside scored feature rows | Add typed `SwingCandidate` with feature snapshot, gates, score, rank fields. |
| Swing signal | Partial as `SetupSnapshot` plus `OrderIntent` path | Add typed `SwingSignal` for candidate-to-setup transition. |
| Swing feature snapshot | Exists as `FeatureSnapshot` | Keep and extend reports to include profile/config/data version. |
| Eligibility result | Partial as booleans/reject strings | Add typed result with gate outcomes and rejection reasons. |
| Quality score | Partial as raw/pct columns | Expose `quality_score_0_100` and score components. |
| Ranking result | Partial through sorted frames | Add deterministic rank object with tie-break values. |
| Risk plan | Exists as `EntryPlan` | Add baseline risk report fields and rejection reason taxonomy. |
| Order plan | Exists as `OrderIntent` and `EntryPlan` | Add baseline order-plan wrapper linking feature/candidate/risk evidence. |
| Position lifecycle state | Exists as enums and lifecycle functions | Add event/report contract for transitions and reasons. |
| Exit decision | Partial in `exits.py` outputs | Add typed exit decision model with trigger, reason, next action, evidence. |
| Rejection reason | Partial as strings | Add enum/taxonomy with gate category and machine-readable code. |
| Baseline report/manifest | Missing before this work | Add manifest model and generated artifact. |

## 3. Data contracts

Expected inputs and outputs:

| Stage | Input | Output | Contract owner |
| --- | --- | --- | --- |
| Market data | Raw next-session CSV rows | Validated frame with required OHLCV/cost fields | `data_contracts.validate_next_session_market_data` |
| Historical bars | Manifest OHLCV file | Validated historical OHLCV frame | `data_contracts.validate_historical_panel_manifest` |
| Reference data | Symbol reference file | Validated reference frame | `data_contracts.validate_symbol_reference_data` |
| Corporate actions | Split/dividend file | Validated corporate-action frame | `data_contracts.validate_corporate_actions_data` |
| Earnings | Event file | Validated earnings frame | `data_contracts.validate_earnings_events_data` |
| Canonical bars | Raw bars and actions | Split-adjusted OHLCV plus total-return close index | `canonical.py` |
| Indicators/features | Canonical bars | Feature frame / `FeatureSnapshot` report | `features.py` / contracts |
| Candidate generation | Feature frame, regime frame, config | Candidate rows with gates, scores, ranks, reasons | `signals.py` plus new candidate contract |
| Risk planning | Setup/candidate, portfolio, config | `EntryPlan` / baseline risk plan report | `entries.py`, `portfolio_manager.py` |
| Order planning | Risk-approved plan | `OrderIntent` / order plan artifact | `entries.py`, `order_intents.py` |
| Lifecycle updates | Current state, market events, config | transition event, pending/action/exit decisions | `lifecycle.py`, `order_state_machine.py`, `exits.py` |
| Reports | Run/replay/audit state | Baseline manifest, review report, candidate/risk/order/lifecycle artifacts | `reporting.py` plus baseline module |

## 4. Config/profile design

Baseline behaviour must be explicit and serialisable.

Required design rules:

| Rule | Enforcement |
| --- | --- |
| Strategy behaviour is in YAML/profile config | Use `StrategyRuntimeConfig` and forbid hidden env strategy switches. |
| Profile identity is recorded | Baseline manifest records profile path, strategy id/version, and config hash. |
| `.env` is infrastructure-only | Allowed for database URL, paths, API keys, output dirs, safe runtime mode. |
| Runtime CLI overrides are visible | Report review thresholds and paths in run/event artifacts. |
| Deprecated configs are isolated | Do not implement from `swing_trading_bot_config_template.yaml`. |
| Config hash is stable | Keep tests around `config_hash`. |

Environment variables must not control:

| Prohibited env-controlled behaviour |
| --- |
| Entry filters |
| Exit rules |
| Scoring weights |
| Risk rules |
| Universe rules |
| Ranking rules |
| Holding periods |
| Time windows |
| Stop/target logic |
| Qualification pass/fail rules unless recorded as explicit CLI/report inputs |

## 5. Research/runtime parity design

Parity should be designed as artifact equality, not just code reuse.

Required parity checks:

| Parity area | Check |
| --- | --- |
| Config | Same config hash in research, replay, paper, shadow, and review artifacts. |
| Feature definitions | Same field names, units, and canonical price series. |
| Candidate generation | Same gates and candidate reason codes for equivalent symbol/session input. |
| Signal contracts | Same setup id, setup fields, entry trigger/limit/stop inputs. |
| Risk sizing | Same equity, per-share risk, budget, and quantity derivation. |
| Order planning | Same side/type/expiry/dedupe and no-chase boundary. |
| Exit assumptions | Same stop/trailing/time/earnings/regime logic. |
| Reports | Same rejection reason taxonomy and material decision IDs. |

Implementation pattern:

1. Generate baseline manifest for every candidate qualification package.
2. Use a common candidate/signal/risk/order report schema.
3. Add deterministic replay artifacts for candidate, risk, and lifecycle decisions.
4. Compare research-generated decisions against runtime-compatible dry-run decisions on selected periods.

## 6. Signal design

Signal flow:

```text
universe member -> candidate -> eligible candidate -> ranked candidate -> armed setup -> swing signal -> risk/order plan
```

A `SwingSignal` should include:

| Field group | Required fields |
| --- | --- |
| Identity | Symbol, session date, strategy id, config hash, baseline id. |
| Source candidate | Candidate id, feature snapshot hash/reference, rank, quality score. |
| Setup | Pattern type, setup id, setup high/low/dates, trigger, limit, initial stop. |
| Gates | Eligibility status, rejected gate codes, warning codes. |
| Regime | Regime state and effective thresholds. |
| Explanation | Human-readable summary plus machine-readable reasons. |

## 7. Risk and portfolio design

Risk and portfolio planning should remain conservative:

| Design area | Required behaviour |
| --- | --- |
| Per-trade risk | `equity * risk_per_trade_pct_equity * regime.size_multiplier`. |
| Per-share risk | `entry_trigger - initial_stop`; reject if non-positive. |
| Quantity | Minimum of risk-based shares and notional/portfolio limits. |
| Heat | Include active and approved/pending plans in projected heat. |
| Daily new risk | Reserve approved plans when ranking through a batch. |
| Sector exposure | Reserve approved plans to prevent later over-allocation. |
| Duplicate symbol | Reject if active or pending exposure already exists. |
| Correlation | Record as v0.1 gap unless implemented as explicit proxy. |

## 8. Order/lifecycle design

Order and lifecycle path:

| State | Decision owner | Required record |
| --- | --- | --- |
| Candidate | Candidate generator | Feature snapshot, gates, score, rank. |
| Armed | Setup detector | Setup id and setup evidence. |
| Planned | Risk/order planner | Entry plan and order intent. |
| Pending entry | Order state machine | Submission, expiry, duplicate, and broker-state evidence. |
| Active | Broker/paper fill event | Fill price, quantity, initial stop, lifecycle state. |
| Held | Exit engine | Updated stop and hold/exit decision evidence. |
| Exit pending | Exit order planner | Exit reason and intended action. |
| Closed/cancelled/rejected | Lifecycle/reporting | Terminal reason, spent setup state, audit event. |

No v0.1 implementation should submit real broker orders. Live routing remains prohibited.

## 9. Instrumentation design

Instrumentation is part of the product.

Required event/report fields:

| Area | Fields |
| --- | --- |
| Profile | Baseline id, strategy id/version, config path, config hash. |
| Data | Manifest path/hash, data contract version, validation status, row counts. |
| Universe | Reviewed symbols, accepted symbols, rejection counts/reasons. |
| Candidate | Feature values, score components, percentile, rank, gates. |
| Risk | Equity, budgets, per-share risk, quantity, projected heat/exposure. |
| Order | Intent id, dedupe key, prices, expiry, approved/rejected reasons. |
| Lifecycle | State transitions, pending-entry actions, fill/cancel/expire/exit reasons. |
| Exit | Trigger, stop values, time/earnings/regime evidence. |
| QA | Tests/checks run, results, qualification stage, blockers. |
| Baseline | Manifest, freeze status, serious-run permission flag. |

## 10. Reporting design

Required report package for baseline review:

| Report | Contents |
| --- | --- |
| `baseline_manifest.json` | Baseline id, config hash, profile path, qualification checks, serious-run status. |
| `candidate_report.json` | Universe/candidate/rejection/score/rank details. |
| `risk_order_report.json` | Entry plans, risk budgets, portfolio constraints, order intents. |
| `lifecycle_report.json` | State transitions and exit decisions. |
| `replay_summary.json` | Validation, stage counts, material decisions, reconciliation. |
| `operator_review.json/html` | Existing composed review surface plus baseline manifest reference. |
| `qualification_checklist.md/json` | Freeze/qualification status and blockers. |

## 11. Testing design

Test pyramid:

| Tier | Required checks |
| --- | --- |
| Unit tests | Config hash, manifest builder, candidate gates, score/rank, risk sizing, rejection taxonomy, lifecycle transitions. |
| Contract tests | Pydantic models reject missing/extra/invalid fields and serialise deterministically. |
| Parity tests | Same selected symbol/session produces equivalent candidate/risk/order decisions in research and runtime-compatible paths. |
| Smoke tests | Tiny manifest replay, runtime shadow cycle, paper/shadow/audit local workflow. |
| Dry-run tests | Prove shadow/paper paths do not require live broker credentials and do not route real orders. |
| Selected-period qualification checks | Fixed historical panels with manifest, artifacts, deterministic decision traces, and review outputs. |

## 12. Delivery risks

| Risk | Mitigation |
| --- | --- |
| The v2 spec is mistaken for a frozen baseline | Add v0.1 manifest and freeze gate. |
| Candidate/signal contracts duplicate existing models | Build wrappers only where they add governance/explainability; reuse existing contracts. |
| Tests become too slow | Keep focused tests for contract additions and reserve full suite for release gates. |
| Runtime side effects creep in | Keep foundational tasks pure, report-only, or paper/shadow guarded. |
| `.env` grows strategy switches | Add tests/docs around infrastructure-only env policy. |
| Parent git state blocks branch isolation | Work inside project root and avoid destructive git operations. |

## 13. Build sequence

Recommended build sequence:

1. Add current-state, baseline definition, solution design, delivery plan, backlog, and implementation log.
2. Add baseline manifest contract and tests.
3. Add candidate/signal/rejection/ranking typed wrappers without changing runtime behaviour.
4. Add report serializers for baseline manifest and candidate/risk/order decisions.
5. Wire manifest into replay/reporting outputs only.
6. Add parity checks for selected tiny/replay fixtures.
7. Add qualification checklist artifact.
8. Expand smoke/dry-run tests.
9. Freeze `swing_machine_v0_1` only after required checks pass.
10. Defer live broker/scheduler/deployment until a separate safety programme.

## 14. Serious full run integration path

The serious full run readiness decision created on 2026-05-05 adds a concrete integration path before any serious baseline run can be unlocked.

Required integration sequence:

1. `SWING-V01-034`: adapt setup outputs into `SwingSignal` artifacts.
2. `SWING-V01-035`: adapt `EntryPlan` and `OrderIntent` outputs into `SwingRiskPlan` and `SwingOrderPlan` artifacts.
3. `SWING-V01-036`: adapt lifecycle and exit decisions into `SwingLifecycleTransition` and `SwingExitDecision` artifacts.
4. `SWING-V01-037`: emit `baseline_report_package.json` from a safe replay/report path.
5. `SWING-V01-038`: generate research-vs-runtime-compatible package parity evidence.
6. `SWING-V01-039`: define selected-period qualification data requirements.
7. `SWING-V01-040`: perform freeze readiness review and only then allow the manifest/checklist to unblock serious full run.

Design rule: none of these items may introduce live broker execution, deployment, scheduler behaviour, destructive database changes, or hidden `.env` strategy behaviour.

## Serious full run integration continuation

The readiness gate added for `swing_machine_v0_1` is intentionally conservative. After the gate exists, the next build sequence is:

1. Populate replay-emitted baseline report packages with actual typed material artifacts already available in safe replay memory: candidates, signals, risk plans, and order plans.
2. Emit a freeze-readiness artifact beside replay outputs so every replay says explicitly whether serious full run is still blocked.
3. Add selected-period preflight validation before any selected-period replay is attempted.
4. Only then consider a selected-period dry-run qualification evidence run. This remains blocked until the data inputs and preflight gates are explicitly satisfied.

This sequence does not authorize live trading, real broker orders, production deployment, destructive database changes, or serious full run execution.

## Trading212 research data source design

The selected-period data source design for Alpaca and Hugging Face research DBs is defined in `docs/swing_machine_v0_1_trading212_data_solution_design.md`.

This design treats Alpaca as the first primary selected-period qualification source and Hugging Face as an independent cross-check. It requires read-only SQLite access, bounded indexed source checks, deterministic export of swing-compatible prepared files, provenance recording, source-input preflight, manifest building, selected-period preflight, and only then replay qualification.
