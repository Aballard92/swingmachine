> Deprecated: this v1 draft is retained for archive only. Do not implement from this file. Use `swing_trading_bot_design_spec_v2.md` instead.

# Regime-Filtered Trend-Pullback Swing Bot

## Purpose
Design a second autonomous trading bot, distinct from an intraday ORB system, that captures **multi-day to multi-week swing moves** using a rules-based continuation setup.

The recommended v1 strategy is:

**Long-only, regime-filtered trend/relative-strength pullback breakout**

This bot is built for deterministic execution, robust backtesting, and staged live deployment.

---

## 1) Strategic thesis

The bot does **not** assume that one candlestick pattern is the “ultimate setup.”
Instead, it expresses a stronger and more defensible thesis:

1. Securities with strong intermediate-term momentum and strong relative strength tend to continue outperforming.
2. Securities trading near their 52-week highs are stronger candidates than those that merely had good trailing returns.
3. Momentum/trend systems can suffer severe crash episodes after sharp market declines and during violent rebounds, so regime controls are mandatory.
4. Volatility scaling and turnover control materially improve live tradability.
5. Pure short-term reversal and naive earnings-drift implementations are not the right first autonomous swing bot for a liquid equity universe.

---

## 2) Recommended v1 system

### Name
`RF_TPC_V1` = **Regime-Filtered Trend Pullback Continuation v1**

### Timeframe
- Signal timeframe: **daily bars**
- Scan frequency: **once per day after market close**
- Typical holding period: **3 to 30 trading days**
- Execution style: next-session entry via **stop-limit** or tightly controlled limit logic

### Suitable use case
- Long-only account
- ISA / investment account compatible workflow
- Low operational complexity compared with intraday systems
- Good complement to ORB because the drivers, hold times, and monitoring pattern differ

---

## 3) Setup definition

The setup is a **pullback or tight consolidation inside a strong existing trend**.

### Stage A — Market regime must be supportive
Only allow new longs when the broad market is in a favorable regime.

Core regime logic:
- Benchmark close > 200-day moving average
- 200-day moving average slope > 0
- Realized market volatility below “panic” threshold
- Optional breadth confirmation: % of universe above 200-day average above threshold

Panic / crash filter:
- If the market recently suffered a large decline and is now rebounding sharply while volatility remains elevated, reduce or disable new momentum entries.

### Stage B — Security must already be strong
A symbol becomes a candidate only if it passes strength filters such as:
- Price above 50-day moving average
- 50-day moving average above 200-day moving average
- 200-day moving average rising
- Strong 6-month / 12-month momentum, preferably excluding the most recent month
- Trading close to its 52-week high
- Sufficient liquidity and acceptable spread/volume profile

### Stage C — Pullback/consolidation must be orderly
Inside the trend, look for one of two tactical patterns:

1. **Shallow pullback**
   - 3–10 down or mixed days
   - pullback low remains above key support (often 20EMA/50DMA)
   - drawdown from recent swing high remains modest
   - pullback occurs on lighter volume and/or lower volatility

2. **Tight base / volatility contraction**
   - 5–15 days of sideways compression
   - narrowing true range / ATR ratio
   - no major distribution bars
   - price stays near prior highs

### Stage D — Breakout trigger
Entry is armed only when price breaks above the local pivot/high of the pullback or tight base.

Trigger rules for v1:
- Buy stop-limit above pullback high / pivot high
- Reject entries if opening gap is too extended versus ATR
- Reject entries if signal is too close to earnings
- Reject entries if spread/liquidity deteriorates materially

---

## 4) Why this is the best first autonomous swing design

### Why not pure mean reversion?
Short-horizon reversal is much more sensitive to trading costs, turnover, and scalability. That makes it a weaker first autonomous bot unless the execution stack is already highly mature.

### Why not a classic PEAD bot first?
Classic post-earnings-announcement drift appears far weaker in modern large-cap stocks than in older literature. A richer earnings-text model may still be useful later, but it is better as an overlay than as the first standalone swing engine.

### Why this setup family?
This design captures the strongest practical elements from the literature while keeping implementation risk manageable:
- intermediate-horizon momentum/trend
- proximity to 52-week highs
- explicit crash avoidance
- volatility-aware sizing
- cost-aware, turnover-aware execution

---

## 5) Required data and information

### Market data
Required:
- Daily OHLCV bars
- Corporate actions: splits, dividends
- Reference data: ticker mapping, ISIN, exchange, sector, country, currency
- Instrument eligibility / tradability from broker

Preferred:
- Minute bars for analytics and post-trade slippage analysis
- Quote/spread data for more realistic cost models
- Halt/suspension status where available

### Benchmark / regime data
Required:
- Benchmark daily bars (e.g. SPY, QQQ, IWM, FTSE proxy, or chosen house benchmark)
- Realized volatility series

Preferred:
- Breadth measures
- VIX or similar volatility index
- Sector ETF trend data for confirmation

### Event data
Recommended:
- Earnings calendar
- EPS estimate, actual EPS, revenue estimate, actual revenue
- Surprise percentages
- Event confirmation status

Future enhancement:
- Earnings-call transcripts
- NLP-derived sentiment / text surprise

### Broker data
Required from execution venue:
- Account summary
- Open positions
- Pending orders
- Historical orders/fills
- Instrument catalogue

### Accounting / risk data
- Realized and unrealized P&L
- Net exposure
- Sector exposure
- Portfolio heat
- FX exposure
- Daily turnover
- Slippage logs

---

## 6) Feature engineering specification

### Core features
For each symbol on each trading day:
- `ret_21`
- `ret_63`
- `ret_126`
- `ret_252`
- `mom_252_21`  (12–1 style momentum proxy)
- `dist_to_52w_high`
- `ma_20`, `ma_50`, `ma_200`
- `ma_200_slope`
- `atr_14`
- `atr_pct = atr_14 / close`
- `range_compression_n`
- `volume_ratio_20`
- `pullback_depth_from_20d_high`
- `pullback_days`
- `rs_vs_benchmark`
- `earnings_days_to_next`
- `sector_trend_score`

### Optional advanced features
Phase 2/3 only:
- residual momentum score
- earnings surprise features
- text-based earnings-call features
- gap-behavior statistics
- market breadth-conditioned signal strength
- regime-specific expected slippage

---

## 7) Universe construction

### Recommended v1 universe
Use a **single, liquid universe** first.
Examples:
- U.S. common stocks + major ETFs
- or a curated liquid cross-listed/global set available in the chosen broker

### Hard filters
Suggested starting filters:
- price floor
- average daily dollar volume floor
- minimum 90–252 trading days of history
- common stocks / ETFs only
- exclude leveraged and inverse ETFs
- exclude instruments with chronic spread or halt issues

### Why keep universe tight in v1
A smaller, liquid universe reduces slippage uncertainty, corporate-action edge cases, and operational noise.

---

## 8) Signal logic

### 8.1 Regime engine
Outputs one of:
- `RISK_ON`
- `CAUTION`
- `RISK_OFF`
- `PANIC_REBOUND`

Suggested interpretation:
- `RISK_ON`: full normal operation
- `CAUTION`: smaller size, higher score threshold
- `RISK_OFF`: no new longs, only manage exits
- `PANIC_REBOUND`: no fresh momentum continuation entries; this state exists specifically to avoid classic momentum crash conditions

### 8.2 Candidate engine
Score each symbol only if all hard filters pass.

Composite score example:

```text
candidate_score =
    0.35 * zscore(mom_252_21)
  + 0.20 * zscore(ret_126)
  + 0.20 * zscore(rs_vs_benchmark)
  + 0.15 * zscore(1 - dist_to_52w_high)
  + 0.10 * zscore(trend_quality)
```

### 8.3 Setup detector
A valid setup requires:
- strong candidate score
- orderly pullback or tight base
- pullback depth below threshold
- range contraction / volatility compression
- price remains above support
- no disqualifying event proximity

### 8.4 Entry engine
Arms entry order when:
- price breaks above pivot/high
- regime is still valid
- spread and liquidity are acceptable
- order does not violate portfolio risk constraints

---

## 9) Entry rules (v1)

Recommended initial entry policy:

1. Compute next-session trigger price:
   - `entry_trigger = setup_high + entry_buffer`
2. Compute protective stop reference:
   - `initial_stop = min(setup_low, entry_trigger - stop_atr_mult * ATR)`
3. Position size from risk budget:
   - `shares = floor(risk_budget / (entry_trigger - initial_stop))`
4. Submit **stop-limit** entry order:
   - `stop = entry_trigger`
   - `limit = entry_trigger + slippage_allowance`
5. Cancel order if not filled within `N` sessions or if setup quality deteriorates

### Design notes
- Prefer stop-limit over pure market-stop for breakouts to cap slippage.
- Do not chase very large gaps.
- For v1, do not place new swing entries in extended hours unless explicitly researched and validated.

---

## 10) Position sizing

### Per-trade sizing
Use **risk-based position sizing**, not equal-weight entries.

Suggested v1 starting point:
- risk per trade: small fixed fraction of equity
- cap per-position gross exposure
- cap per-sector exposure
- cap total portfolio heat

### Portfolio-level scaling
Overlay a portfolio volatility target:
- reduce gross exposure when realized portfolio volatility rises
- reduce new risk in `CAUTION` and `PANIC_REBOUND`
- do not increase exposure solely because many signals appear at once

---

## 11) Exit logic

### Mandatory exits
1. **Initial hard stop**
   - below setup low or ATR-based threshold
2. **Time stop**
   - exit if trade fails to make progress within N bars
3. **Trend failure exit**
   - exit on close below tactical trend support / trailing stop
4. **Regime exit**
   - tighten stops or reduce exposure if market flips to `RISK_OFF`
5. **Event exit**
   - for v1, default rule is to avoid holding through earnings unless specifically tested and approved

### Recommended v1 trailing logic
Keep the exit logic simple and deterministic.
Example approach:
- Start with hard stop
- Once unrealized gain reaches threshold, trail using ATR or short MA logic
- Optional: move stop to breakeven only after objective follow-through criteria are met

### Should v1 use profit targets?
Default answer: **no fixed profit target**.
This system is a continuation engine; overly tight profit caps can cut the right tail.
If desired, add only a conservative scale-out rule after the base version is validated.

---

## 12) Execution design

### Order types
Use the broker’s documented support for:
- market
- limit
- stop
- stop-limit

### Important operational implications
- If the broker API does not document native OCO/bracket logic, implement **synthetic bracket behavior** in the bot.
- Because some order endpoints may be non-idempotent, the bot must include **client-side deduplication** and intent IDs.
- All order placement must pass rate-limit guards and retry rules.

### Execution policy for v1
- One end-of-day decision cycle
- Next-session order placement
- Intraday monitoring only for fills, stops, and safety events
- Avoid constant intraday re-optimization

---

## 13) State machine

Per symbol:

```text
INELIGIBLE
  -> ELIGIBLE
  -> CANDIDATE
  -> ARMED
  -> PENDING_ENTRY
  -> ACTIVE
  -> EXIT_PENDING
  -> CLOSED
  -> ELIGIBLE
```

### State responsibilities
- `ELIGIBLE`: passes universe and hard filters
- `CANDIDATE`: trend and score strong enough
- `ARMED`: pullback/base setup complete
- `PENDING_ENTRY`: order active at broker
- `ACTIVE`: filled position open
- `EXIT_PENDING`: exit order active or forced liquidation requested
- `CLOSED`: trade archived with analytics snapshot

---

## 14) System architecture for Codex

### Core modules
1. `data_ingestion`
2. `reference_master`
3. `feature_store`
4. `regime_engine`
5. `universe_builder`
6. `candidate_ranker`
7. `setup_detector`
8. `signal_engine`
9. `position_sizer`
10. `risk_engine`
11. `execution_adapter`
12. `order_state_machine`
13. `portfolio_manager`
14. `reconciliation`
15. `analytics`
16. `monitoring_alerts`
17. `backtest_engine`
18. `config_service`

### Recommended code principles
- Strategy logic must be **config-driven**, not hard-coded
- Separate pure signal code from broker side effects
- Every order decision must be reproducible from saved inputs
- Persist full audit context for every state transition
- Keep backtest and live logic as close as possible

---

## 15) Data contracts

### SymbolDailyBar
```yaml
symbol: str
session_date: date
open: float
high: float
low: float
close: float
volume: float
adjusted_close: float
corporate_action_factor: float
currency: str
exchange: str
is_regular_session: bool
```

### FeatureSnapshot
```yaml
symbol: str
session_date: date
mom_252_21: float
ret_126: float
ret_63: float
dist_to_52w_high: float
ma_50: float
ma_200: float
ma_200_slope: float
atr_14: float
atr_pct: float
pullback_depth: float
pullback_days: int
range_compression: float
volume_ratio_20: float
rs_vs_benchmark: float
earnings_days_to_next: int | null
candidate_score: float
setup_valid: bool
```

### OrderIntent
```yaml
intent_id: str
symbol: str
side: BUY | SELL
reason: ENTRY | STOP | TRAIL | TIME_EXIT | REGIME_EXIT | KILL_SWITCH
order_type: MARKET | LIMIT | STOP | STOP_LIMIT
quantity: float
stop_price: float | null
limit_price: float | null
created_at: datetime
expires_at: datetime | null
strategy_id: str
config_hash: str
```

---

## 16) Backtesting standard

### Non-negotiables
- No lookahead bias
- No survivorship bias
- Point-in-time universe rules
- Proper handling of delistings, splits, dividends, symbol changes
- Realistic execution assumptions
- Distinct in-sample, validation, and out-of-sample periods
- Walk-forward testing
- Sensitivity analysis across parameter ranges

### Cost model
At minimum include:
- spread/slippage model
- market impact proxy
- FX conversion cost if relevant
- venue-specific taxes/fees if relevant

### Validation framework
Run:
- rolling walk-forward tests
- regime-segmented analysis
- ablation tests
- combinatorially symmetric cross-validation / PBO analysis where feasible

### Key analytics
- CAGR
- annualized volatility
- Sharpe / Sortino / Calmar
- max drawdown
- hit rate
- average win / average loss
- expectancy
- turnover
- exposure
- sector concentration
- gap risk contribution
- trade duration distribution
- slippage by order type

---

## 17) Research sequence

### Phase 1 — Baseline
Backtest only:
- trend + momentum + 52-week-high candidate ranking
- pullback/base entry
- ATR stop
- no earnings hold
- no advanced NLP

### Phase 2 — Risk refinement
Add:
- regime states
- volatility scaling
- sector caps
- time stops
- panic-rebound suppression

### Phase 3 — Event refinement
Add:
- earnings calendar filter tuning
- surprise features
- optional “do not hold / do hold” conditional models

### Phase 4 — Advanced alpha overlays
Add one at a time:
- residual momentum
- transcript/text features
- sector-relative timing
- adaptive stop logic by regime

---

## 18) Live deployment plan

### Stage 0
Unit tests, integration tests, replay tests, failure-mode tests.

### Stage 1
Paper trading / demo environment only.

### Stage 2
Shadow mode on live data:
- generate signals
- record hypothetical orders
- compare with paper fills
- no live capital

### Stage 3
Small-capital launch:
- low position cap
- low daily risk budget
- manual kill switch always enabled

### Stage 4
Controlled scale-up:
- increase only after enough live sample size
- require live-vs-backtest drift analysis before each scale step

---

## 19) Operational risk controls

### Pre-trade
- max order notional
- max shares per order
- max position per symbol
- max net exposure
- max sector exposure
- max daily new risk
- duplicate-order protection
- stale-price protection
- stale-feature protection
- earnings proximity block
- spread/liquidity threshold block

### In-trade
- stop verification
- orphaned-order detection
- reconciliation against broker positions
- halt / suspension handling
- forced risk reduction on regime flip

### Global kill switches
- data feed stale
- broker unavailable
- abnormal slippage burst
- unexplained reconciliation mismatch
- daily drawdown breach
- excessive rejected/cancelled orders

### Logging and audit
Persist:
- input data hashes
- feature snapshots
- ranking outputs
- regime state
- order intents
- broker acknowledgements
- fills/cancels
- P&L events
- manual interventions

---

## 20) Suggested v1 parameter ranges to research

These are **research ranges**, not final values.

- momentum lookback: 63 / 126 / 252 days
- skip period: 0 to 21 trading days
- distance to 52-week high threshold: 0% to 15%
- pullback duration: 3 to 15 days
- pullback depth: 0.5 to 2.5 ATR
- stop multiple: 1.2 to 2.5 ATR
- order expiry: 1 to 5 sessions
- time stop: 5 to 15 sessions without progress
- earnings avoidance window: 3 to 10 sessions before event
- regime vol threshold: percentile-based rather than fixed value

Keep the final parameter set compact.
If many parameters need fine tuning to work, the design is likely too brittle.

---

## 21) Recommended v1 defaults

A sensible first production candidate:
- Long-only
- Daily bar engine
- U.S. liquid equities + ETFs, or equally liquid chosen broker universe
- 12–1 momentum + 6-month relative strength + distance to 52-week high
- trend filter: close > 50DMA > 200DMA, rising 200DMA
- pullback entry from orderly 3–10 day consolidation
- no new entries in `RISK_OFF` or `PANIC_REBOUND`
- ATR-based initial stop
- time stop + trailing exit
- no earnings holds in v1
- risk-based sizing with portfolio heat cap
- synthetic brackets if broker lacks native OCO/brackets

---

## 22) What Codex should build first

### Deliverable order
1. Data schema and ingestion
2. Feature computation library
3. Deterministic regime engine
4. Candidate ranker
5. Pullback/base detector
6. Order intent generator
7. Backtester with realistic fills
8. Broker adapter and reconciliation
9. Monitoring, dashboards, and alerts
10. Deployment pipeline and runbooks

### Definition of done for MVP
The bot is only “done” when it can:
- reproduce the same signal from the same data snapshot
- reconcile its intended state with broker state
- survive restarts without duplicate orders
- pass walk-forward and stress tests
- provide full trade-level auditability

---

## 23) Explicit non-goals for v1

Do **not** include in v1:
- discretionary chart-pattern exceptions
- multiple unrelated alpha ideas mixed together
- intraday signal generation for a daily system
- holding through earnings without dedicated research
- dozens of optimised filters
- machine learning for signal discovery before the deterministic baseline is proven

---

## 24) Final recommendation

If you want one professional-grade swing bot to build next, build this:

**A long-only, daily-bar, regime-filtered trend/relative-strength pullback breakout engine with 52-week-high awareness, ATR-based risk sizing, strict earnings and panic-state filters, synthetic bracket management, and institutional-style audit/risk controls.**

That gives you:
- a research-backed edge family
- manageable implementation complexity
- lower operational burden than intraday systems
- a clean path to later upgrades such as residual momentum and earnings-text overlays
