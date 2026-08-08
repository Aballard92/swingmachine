# Swing Machine v0.1 Baseline Definition

Created: 2026-05-05
Baseline candidate name: `swing_machine_v0_1`

Documentation location decision: `docs/` is the repository's established control-document location, so this file is created under `docs/`.

## 1. Purpose of the swing machine

`swing_machine_v0_1` should be the first governed baseline candidate for the repository's daily-bar swing trading engine. Its purpose is to produce deterministic, explainable, risk-bounded swing trade candidates and order plans that can be validated consistently across research, replay, paper, shadow, and audit workflows.

The baseline is not a profitability claim. It is a mechanical and governance baseline.

Primary role:

| Role | Definition |
| --- | --- |
| Research | Evaluate deterministic candidate, risk, order, lifecycle, and exit behaviour on prepared historical data. |
| Replay | Prove that data validation, signal path, backtest path, runtime path, and audit path can produce stable artifacts. |
| Paper/shadow | Exercise guarded runtime machinery without broker risk. |
| Governance | Record profile/config hash, data contract version, qualification status, decisions, and reports for review. |

## 2. Strategy boundaries

Initial baseline strategy family:

| Boundary | Decision |
| --- | --- |
| Direction | Long-only. |
| Timeframe | Daily bars from regular sessions. |
| Core thesis | Strong names resting in strong or acceptable markets, not cheap laggards. |
| Entry family | Trend/relative-strength pullback breakout using stop-limit entry. |
| Universe | Liquid common stocks and ETFs that pass explicit profile gates. |
| Position count | No pyramiding; no multiple active positions per symbol. |
| Pending entries | At most one pending entry per symbol. |
| Profit target | No fixed profit target in v0.1. |
| Broker | Paper/shadow only for this baseline definition. |

The existing `RF_TPC_V2` profile is the starting implementation profile. `swing_machine_v0_1` is the baseline governance wrapper around that profile and its qualification artifacts.

## 3. Trading horizon

Safest current assumption: the system targets multi-day to multi-week continuation trades. A position may exit quickly through an opening gap cancel, protective stop, time stop, earnings exit, or invalidation, but the intended lifecycle is longer than intraday and shorter than long-term investment holding.

The baseline must record:

| Concept | Required behaviour |
| --- | --- |
| Signal time | Regular-session daily close. |
| Entry time | Next regular session. |
| Monitoring | Intraday only for fills, stops, kill switches, and paper/shadow reconciliation. |
| Exit lifecycle | Stop, trailing stop, time stop, earnings exit, safety/manual exit, and lifecycle closure must be explicit. |

## 4. Universe selection

A symbol becomes reviewable only if it passes explicit universe and data gates.

Required v0.1 universe inputs:

| Input | Requirement |
| --- | --- |
| Symbol reference | Symbol, asset type, exchange, currency, sector, tradability, and optional effective/tradability windows. |
| Historical bars | Enough daily history for configured features and warm-up. |
| Corporate actions | Split/dividend records or explicit fail-closed evidence. |
| Earnings events | Upcoming event date/session where available. |
| Liquidity | Minimum price and 20-day average daily dollar volume. |

Eligibility assumptions:

| Rule | Default v0.1 assumption |
| --- | --- |
| Asset types | Common stock and ETF, subject to leveraged/inverse exclusion. |
| History | At least 252 sessions unless profile changes explicitly. |
| Price | At least configured minimum price. |
| Liquidity | At least configured minimum 20-day dollar volume. |
| Block/allow lists | Explicit config lists only. |
| Missing critical data | Fail closed. |

## 5. Candidate generation

A candidate is not an order. A candidate is a symbol-session snapshot that has enough valid data, passes universe gates, has computed features, and is eligible for ranking.

Candidate generation stages:

| Stage | Output |
| --- | --- |
| Data validation | Accepted/rejected symbol-session rows with reasons. |
| Feature snapshot | Typed values used for decisions. |
| Universe eligibility | Hard gate pass/fail and reasons. |
| Regime context | Current regime action thresholds. |
| Ranking input | Candidate score components and raw score. |
| Candidate state | Eligible candidate if score and trend-quality gates pass. |
| Setup state | Armed setup only if a valid pullback/tight-base setup exists. |

## 6. Signal feature snapshot

The signal feature snapshot must be typed and serialisable. It should include at minimum:

| Feature group | Required fields |
| --- | --- |
| Identity | Symbol, session date, profile id, config hash, data contract version. |
| Returns | 21-day, 63-day, 126-day, 252-day, 252-21 momentum, relative strength vs benchmark. |
| Trend | MA20, MA50, MA200, MA50 slope, MA200 slope, trend quality. |
| Volatility/range | ATR5, ATR14, ATR20, ATR percent, range compression. |
| Structure | Distance to 52-week high, pullback days, pullback depth, setup high/low/date fields. |
| Regime | Regime state, entry enabled, size multiplier, effective thresholds. |
| Events | Earnings session and regular closes until event. |
| Score/rank | Raw score, percentile/0-100 quality score, deterministic rank, tie-breaks. |
| Explainability | Gate outcomes, rejection reasons, calculation inputs. |

The existing `FeatureSnapshot` already covers many fields. v0.1 should make candidate/signal separation clearer and ensure feature snapshots appear in reports.

## 7. Eligibility gates

Hard gates must be deterministic and explainable.

Required v0.1 gate categories:

| Gate | Examples |
| --- | --- |
| Data gate | Required bars present, no duplicate symbol/session, valid OHLC, valid reference metadata. |
| Universe gate | Asset type, tradability, exchange, price, liquidity, block list, history. |
| Regime gate | Entry enabled for regime, fail-closed missing breadth/regime inputs. |
| Trend gate | Close above MA50, MA50 above MA200, positive MA200 slope. |
| Structure gate | Near enough to 52-week high, valid setup shape, setup not spent. |
| Event gate | Earnings window does not block new entry unless configured otherwise. |
| Risk gate | Per-share risk positive, quantity at least 1, heat/sector/daily-risk limits pass. |
| Runtime gate | No duplicate pending/active symbol, broker state certain, kill switch inactive. |

## 8. Quality score

The baseline should use a deterministic quality score for ranking and review. The current config uses cross-sectional z-score components and candidate score percentile. v0.1 should expose both:

| Score | Definition |
| --- | --- |
| `candidate_score_raw` | Weighted cross-sectional z-score from configured components. |
| `candidate_score_pct` | Percentile rank in the eligible cross-section. |
| `quality_score_0_100` | Review-facing score equal to percentile times 100 unless a future explicit config changes it. |

The score represents relative candidate quality within a session, not expected return.

## 9. Ranking

Ranking must be deterministic.

Required deterministic ordering:

1. Eligible/armed candidates only.
2. Higher `candidate_score_pct` first.
3. Higher `trend_quality` next.
4. Lower `dist_to_52w_high` next.
5. Lower per-share risk as a practical risk-efficiency tie-break.
6. Lexicographic symbol as final tie-break.

Every report should include the rank, score components, and tie-break values.

## 10. Risk model

The v0.1 risk model should be intentionally simple and explicit:

| Risk object | Required fields |
| --- | --- |
| Per-trade budget | Equity times `risk_per_trade_pct_equity` times regime size multiplier. |
| Stop distance | Entry trigger minus initial stop. Must be positive. |
| Shares from risk | Floor of effective risk budget divided by per-share risk. |
| Shares from notional | Floor of max position notional divided by entry reference. |
| Final quantity | Minimum of risk, notional, and portfolio constraints. |
| Reject reasons | Quantity below 1, invalid stop, heat breach, sector breach, daily-risk breach, duplicate exposure. |

Risk sizing must never increase above configured per-trade risk because of volatility targeting or regime logic.

## 11. Portfolio constraints

Required v0.1 constraints:

| Constraint | Required behaviour |
| --- | --- |
| Position concentration | Max position percent of equity. |
| Sector concentration | Max sector exposure percent of equity. |
| Portfolio heat | Sum of open/pending trade risk divided by equity. |
| Daily new risk | Cap risk introduced by new entries on a session. |
| Duplicate exposure | No active or pending duplicate symbol. |
| Correlation | Record as a known gap for v0.1 unless a simple proxy is implemented explicitly. |

## 12. Order planning

An order plan should contain:

| Field group | Required content |
| --- | --- |
| Identity | Symbol, setup id, strategy id, config hash, created timestamp. |
| Direction/type | Buy stop-limit entry for v0.1. |
| Prices | Entry trigger, limit price, initial stop, per-share risk. |
| Quantity | Planned shares and risk budget derivation. |
| Expiry | Next regular-session expiry or configured expiry sessions. |
| Safety | Opening-gap cancel boundary, no extended hours unless explicitly configured. |
| Dedupe | Dedupe key and one pending entry per symbol. |
| Explanations | Approved/rejected, reject reasons, feature snapshot reference. |

## 13. Entry lifecycle

Required entry lifecycle:

```text
eligible symbol -> candidate -> armed setup -> order plan -> pending entry -> active position or cancelled/rejected/expired
```

A candidate becomes an intended trade only when:

| Requirement | Decision |
| --- | --- |
| Candidate gates pass | Required. |
| Setup is fresh and valid | Required. |
| Setup id is not spent | Required. |
| Risk and portfolio plan pass | Required. |
| Runtime state permits entry | Required for paper/shadow runtime. |
| Manifest/report can explain decision | Required before qualification. |

## 14. Exit lifecycle

Exit concepts for v0.1:

| Exit type | Baseline definition |
| --- | --- |
| Initial stop | Protective hard stop derived from setup/ATR logic. |
| Trailing stop | Activates after configured follow-through; tightens in risk-off. |
| Time stop | Exit if insufficient progress after configured number of bars. |
| Earnings exit | Exit before earnings when holding through earnings is disabled. |
| Regime exit | No forced liquidation in current design; risk-off tightens trailing stop. |
| Manual/safety exit | Allowed only as explicit operator/runtime safety event and must be reported. |
| Target | No fixed profit target in v0.1. |

## 15. Runtime/research parity

Required parity surfaces:

| Surface | Parity requirement |
| --- | --- |
| Profile/config | Same config hash and baseline manifest. |
| Data contract | Same canonical series definitions and data validation rules. |
| Feature snapshot | Same fields, units, and warm-up policy. |
| Candidate generation | Same gates and rejection reasons. |
| Ranking | Same score components and tie-breaks. |
| Risk sizing | Same per-share risk, quantity, and portfolio constraints. |
| Order planning | Same price/expiry/dedupe rules. |
| Exit assumptions | Same stop, trailing, time, earnings, and regime behaviour. |
| Reporting | Same field names for decisions and reasons. |

Where exact sharing is not yet practical, v0.1 must document the divergence and add a parity check to the backlog.

## 16. Reporting and instrumentation

Required baseline artifacts:

| Artifact | Purpose |
| --- | --- |
| Baseline manifest | Binds baseline id, profile path, config hash, code contract version, qualification checks, and serious-run permission status. |
| Candidate report | Explains universe, features, gates, scores, ranks, and rejects. |
| Risk/order report | Explains sizing, constraints, order prices, dedupe, and approval/rejection. |
| Lifecycle report | Explains pending, fill, active, hold, exit, cancellation, and spent setup decisions. |
| Replay report | Shows validation, stage counts, material decisions, traces, and reconciliation checks. |
| Operator review | Summarises audit windows, runtime events, divergences, alerts, review checks, and status. |
| Qualification checklist | Shows whether serious qualification/full run is still prohibited. |

## 17. Qualification requirements

Before any serious swing baseline qualification run:

| Requirement | Status before this programme |
| --- | --- |
| Explicit baseline profile/config | Partial: v2 config exists, but no v0.1 manifest wrapper. |
| Data contract | Partial: prepared data validators and historical manifest exist. |
| Typed candidate/signal contracts | Partial: feature/setup/order contracts exist, clearer candidate/signal layer needed. |
| Risk/order/lifecycle contracts | Partial/strong. |
| Reporting package | Partial/strong for operator review; baseline-specific manifest needed. |
| Unit tests | Strong existing base. |
| Smoke tests | Partial through replay/runtime CLI tests. |
| Dry-run safety tests | Partial through paper/shadow tests. |
| Baseline manifest | Missing before this work. |
| Qualification checklist | Missing before this work. |

Serious full run is prohibited until the manifest reports all mandatory checks satisfied.

## 18. Non-goals

Do not build these for v0.1:

| Non-goal | Reason |
| --- | --- |
| Live broker integration | Safety and qualification must come first. |
| Production scheduler/deployment | No baseline freeze yet. |
| Strategy variants | Baseline first, performance later. |
| Backtest performance optimisation | Would blur the mechanical baseline. |
| Discretionary overlays | Hidden behaviour risk. |
| Earnings NLP or EPS surprise overlays | Explicitly out of current simple baseline scope. |
| Intraday alpha logic | Baseline is daily-bar swing. |
| Complex correlation model | Record as later enhancement unless a simple explicit proxy is added. |
