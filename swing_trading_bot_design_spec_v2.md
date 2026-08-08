# Regime-Filtered Trend Pullback Continuation Swing Bot
## Implementation Design Spec v2.1

> **Mechanical design reference, not current strategy authority.** No revised
> candidate is selected. PULLBACK is parked, TIGHT_BASE is isolated, and this
> specification does not authorise qualification, runtime, paper, live, broker,
> provider, API, acquisition, or holdout actions.

## Purpose
This document replaces the first draft with an implementation-ready specification for a second autonomous bot alongside the ORB system.

The strategy recommendation is unchanged:

**Long-only, daily-bar, regime-filtered trend / relative-strength pullback breakout**

What changes in v2 is the level of determinism. The major ambiguities flagged in review have been removed:

1. **Corporate-action handling is explicit.** The bot uses three distinct price series: raw OHLCV for execution, split-adjusted OHLCV for chart structure, and a total-return close index for return ranking only.
2. **`trend_quality` is defined exactly** and stored in the feature contract.
3. **The regime engine is fully parameterized** with deterministic thresholds, transition precedence, and per-regime actions.
4. **Pending-entry behavior is constrained to one active entry intent per symbol** with a spent-setup rule to prevent stale-order resubmission and accidental pyramiding.
5. **Earnings timing is session-aware** through explicit earnings-session metadata and remaining-regular-close counts.
6. **Opening-gap enforcement is operationally consistent** because the stop-limit cap is the no-chase boundary and opening prints above that cap cancel the setup.
7. **`setup_id` tie-breaks are explicit** for repeated equal highs and lows.

---

## 1) Strategy summary

### Strategy ID
`RF_TPC_V2`

### Core thesis
The bot should buy **strong names resting in strong markets**, not cheap laggards.

The signal family remains:
- intermediate-term momentum and relative strength
- proximity to 52-week highs
- orderly pullbacks and tight bases inside an existing uptrend
- explicit crash / panic-rebound suppression
- ATR-based risk sizing and exit management

### Timeframe
- signal timeframe: **daily regular-session bars**
- scan schedule: **once per day after the regular close**
- entry schedule: **next regular session via overnight resting stop-limit with opening-gap cancel logic**
- typical hold: **3 to 30 trading days**
- live monitoring: **intraday for fills, stops, and kill switches only**

### Position policy
- long-only
- one open position per symbol
- one pending entry per symbol
- no pyramiding in v1/v2 baseline

---

## 2) Canonical data model and price-series policy

The earlier draft used the phrase “adjusted prices” too loosely. This specification now separates signal and execution data into explicit canonical series.

### 2.1 Canonical series

#### A. Raw execution series
Used only for execution simulation, broker reconciliation, and fill/slippage analytics.

```text
raw_open_t
raw_high_t
raw_low_t
raw_close_t
raw_volume_t
```

#### B. Split-adjusted chart series
Used for all chart-structure and setup features.

A cumulative split factor must be applied so that historical price discontinuities caused by splits and reverse splits are removed, while the current day's split-adjusted price equals the current raw price.

```text
split_adj_price_t = raw_price_t * split_factor_cum_t
split_adj_volume_t = raw_volume_t / split_factor_cum_t
```

For a 2-for-1 split, pre-split prices are halved and pre-split volumes are doubled in the split-adjusted series.

These fields are required:
```text
split_adj_open_t
split_adj_high_t
split_adj_low_t
split_adj_close_t
split_adj_volume_t
```

#### C. Total-return close index
Used **only** for long-horizon return features and relative-strength ranking.

Cash dividends must **not** alter OHLC values used for pattern recognition.
Instead, dividends are incorporated into a separate close-only total-return index.

Per-session total return:
```text
tr_ret_t = (split_adj_close_t + cash_dividend_per_share_t) / split_adj_close_{t-1} - 1
```

Total-return close index:
```text
tr_close_index_0 = 100.0
tr_close_index_t = tr_close_index_{t-1} * (1 + tr_ret_t)
```

This gives a deterministic close-only economic return series without creating fictional dividend-adjusted intraday highs and lows.

### 2.2 Deliberate policy choice

The design choice for v2 is:

- **Split-adjusted OHLCV** for pattern, ATR, moving averages, pivot highs/lows, 52-week-high distance, pullback depth, support checks, breadth, and benchmark trend structure.
- **Total-return close index** for `ret_*`, `mom_252_21`, and `rs_vs_benchmark`.
- **Raw OHLCV** for fill modeling and live order placement.

### 2.3 Feature source matrix

| Feature / function | Source series |
|---|---|
| MA20 / MA50 / MA200 | split-adjusted close |
| ATR / true range | split-adjusted OHLC |
| pivot highs / lows | split-adjusted high / low |
| pullback depth | split-adjusted high / close |
| distance to 52-week high | split-adjusted high / close |
| breadth `% above MA200` | split-adjusted close |
| benchmark trend state | split-adjusted close |
| benchmark realized volatility | total-return close index |
| `ret_21/63/126/252` | total-return close index |
| `mom_252_21` | total-return close index |
| `rs_vs_benchmark` | total-return close index |
| execution simulation | raw OHLC |
| live order prices | raw broker prices |
| P&L cash dividends | broker/accounting events |

### 2.4 Non-goal
The bot will **not** construct or use total-return-adjusted OHLC bars. That would distort ATR, pivots, and price-pattern geometry.

### 2.5 Earnings event timing policy
The bot requires point-in-time earnings metadata with:
- `earnings_event_date`
- `earnings_event_session` in `{PRE_OPEN, POST_CLOSE, UNKNOWN}`
- `regular_closes_until_earnings_event`

At the regular close of session `t`, define:

```text
regular_closes_until_earnings_event_t =
    count of future regular-session closes that occur before the confirmed earnings event timestamp
```

Examples measured at the regular close of session `t`:
- earnings `POST_CLOSE` on `t` -> `0`
- earnings `PRE_OPEN` on `t+1` -> `0`
- earnings `POST_CLOSE` on `t+1` -> `1`
- earnings `PRE_OPEN` on `t+2` -> `1`
- earnings `POST_CLOSE` on `t+2` -> `2`

Fail-closed rule:
- if an upcoming earnings event exists but `earnings_event_session = UNKNOWN`, set `regular_closes_until_earnings_event_t = 0`

This gives the daily close-based engine one deterministic scalar for both entry filtering and earnings exits.

---

## 3) Universe construction

### 3.1 Tradable universe
The default research and live universe is:
- common stocks
- non-leveraged ETFs
- liquid exchanges only
- instruments supported by the broker account

### 3.2 Hard eligibility filters
A symbol is eligible on session `t` only if:
- `min_history_days >= 252`
- `split_adj_close_t >= min_price`
- `avg_daily_dollar_volume_20_t >= min_avg_daily_dollar_volume_20`
- asset type in allowed set
- not in blocklist
- not halted/suspended if that data is available
- regular-session bar exists for `t`

### 3.3 Breadth universe
Breadth must be measured over the **point-in-time common-stock subset of the strategy universe**:
- same exchange / tradability / history / price / liquidity filters
- **ETFs excluded**
- blocklist still applied

This is the official answer to the breadth-scope question. The breadth calculation is intentionally aligned to the set of tradable common stocks the bot actually considers, not to ETFs and not to an external index-constituent dataset.

If breadth is enabled and the breadth universe has fewer than `breadth.min_constituents`, the system must fail closed for new entries and classify the session as `RISK_OFF` due to missing regime input.

---

## 4) Regime engine

The regime engine outputs exactly one of:
- `RISK_ON`
- `CAUTION`
- `RISK_OFF`
- `PANIC_REBOUND`

### 4.1 Benchmark inputs
For benchmark symbol `B` on session `t`:

```text
bench_close_t           = split_adj_close_B_t
bench_ma200_t           = SMA(split_adj_close_B, 200)
bench_ma200_slope_pct20 = bench_ma200_t / bench_ma200_{t-20} - 1
bench_dist_above_ma200  = bench_close_t / bench_ma200_t - 1

bench_tr_logret_t       = ln(tr_close_index_B_t / tr_close_index_B_{t-1})
realized_vol_20         = stdev(bench_tr_logret_{t-19:t}) * sqrt(252)

panic_drawdown_126      = bench_close_t / rolling_max(bench_close_{t-125:t}) - 1
rebound_return_20       = bench_close_t / bench_close_{t-20} - 1
```

Breadth:
```text
breadth_pct_above_ma200_t =
    count_u(split_adj_close_u_t > SMA(split_adj_close_u, 200)_t) / N_breadth_t
```

### 4.2 Deterministic state rules
State precedence is evaluated in this order:

#### A. `PANIC_REBOUND`
`PANIC_REBOUND` is true if all of the following are true:
- `panic_drawdown_126 <= panic_decline_threshold`
- `rebound_return_20 >= rebound_return_threshold`
- `realized_vol_20 >= panic_realized_vol_threshold`

#### B. `RISK_OFF`
If not in `PANIC_REBOUND`, classify as `RISK_OFF` if **any** of the following are true:
- `bench_close_t < bench_ma200_t`
- `bench_ma200_slope_pct20 <= 0`
- `breadth_pct_above_ma200_t < risk_off_min_pct_above_ma200`
- `realized_vol_20 >= risk_off_realized_vol_threshold`
- breadth input missing while breadth is enabled

#### C. `CAUTION`
If not in `PANIC_REBOUND` and not in `RISK_OFF`, classify as `CAUTION` if **any** of the following are true:
- `bench_dist_above_ma200 < caution_min_distance_above_ma200`
- `breadth_pct_above_ma200_t < risk_on_min_pct_above_ma200`
- `realized_vol_20 >= caution_realized_vol_threshold`

#### D. `RISK_ON`
If none of the above states apply, classify as `RISK_ON`.

### 4.3 Regime actions
Each regime has explicit downstream behavior:

| Regime | New entries | Size multiplier | Min candidate score percentile | Min trend quality |
|---|---:|---:|---:|---:|
| `RISK_ON` | yes | 1.00 | 0.80 | 0.45 |
| `CAUTION` | yes | 0.50 | 0.90 | 0.60 |
| `RISK_OFF` | no | 0.00 | 1.00 | 1.00 |
| `PANIC_REBOUND` | no | 0.00 | 1.00 | 1.00 |

This resolves the earlier ambiguity around `CAUTION`: it is fully specified and does both of the following:
- raises the selection threshold
- cuts new trade size by a fixed multiplier

---

## 5) Feature library

All formulas below are evaluated on session `t` using only information available by the regular close of `t`.

### 5.1 Core return features
Using `tr_close_index`:

```text
ret_21_t  = tr_close_t / tr_close_{t-21}  - 1
ret_63_t  = tr_close_t / tr_close_{t-63}  - 1
ret_126_t = tr_close_t / tr_close_{t-126} - 1
ret_252_t = tr_close_t / tr_close_{t-252} - 1

mom_252_21_t = tr_close_{t-21} / tr_close_{t-252} - 1
```

### 5.2 Relative strength
Using the same return source as above:

```text
rs_vs_benchmark_126_t = ret_126_t(symbol) - ret_126_t(benchmark)
```

### 5.3 Trend / structure features
Using split-adjusted chart series:

```text
ma20_t  = SMA(split_adj_close, 20)
ma50_t  = SMA(split_adj_close, 50)
ma200_t = SMA(split_adj_close, 200)

ma50_slope_pct20_t  = ma50_t  / ma50_{t-20}  - 1
ma200_slope_pct20_t = ma200_t / ma200_{t-20} - 1
```

### 5.4 ATR and volatility compression
Using split-adjusted OHLC and Wilder ATR:

```text
true_range_t =
    max(
        split_adj_high_t - split_adj_low_t,
        abs(split_adj_high_t - split_adj_close_{t-1}),
        abs(split_adj_low_t  - split_adj_close_{t-1})
    )

atr_14_t = WilderEMA(true_range, 14)
atr_5_t  = WilderEMA(true_range, 5)
atr_20_t = WilderEMA(true_range, 20)

atr_pct_t = atr_14_t / split_adj_close_t
range_compression_ratio_t = atr_5_t / atr_20_t
```

### 5.5 52-week-high distance
Using split-adjusted chart series:

```text
rolling_52w_high_t = rolling_max(split_adj_high_{t-251:t})
dist_to_52w_high_t = 1 - split_adj_close_t / rolling_52w_high_t
```

Clamp `dist_to_52w_high_t` to `[0, 1]` if the upstream data source can introduce tiny numerical overshoots.

### 5.6 Pullback features
Using split-adjusted chart series:

```text
anchor_high_20_t = rolling_max(split_adj_high_{t-19:t})
anchor_high_date = most recent date in [t-19, t] where split_adj_high == anchor_high_20_t

pullback_days_t = t - anchor_high_date
pullback_depth_atr_t = (anchor_high_20_t - split_adj_close_t) / atr_14_t
```

Tie-break rule for multiple equal highs:
- use the **most recent** occurrence of the maximum high

### 5.7 Volume feature
Using raw volume:

```text
volume_ratio_20_t = raw_volume_t / SMA(raw_volume, 20)_t
```

### 5.8 Exact `trend_quality` formula
`trend_quality` is a bounded continuous score in `[0, 1]`.

First define four normalized components:

```text
x1 = clamp((ma20_t / ma50_t  - 1) / 0.08, 0, 1)
x2 = clamp((ma50_t / ma200_t - 1) / 0.15, 0, 1)
x3 = clamp(ma50_slope_pct20_t  / 0.06, 0, 1)
x4 = clamp(ma200_slope_pct20_t / 0.03, 0, 1)
```

Then:

```text
trend_quality_t =
    0.30 * x1 +
    0.35 * x2 +
    0.20 * x3 +
    0.15 * x4
```

Interpretation:
- `x1` measures near-term trend stacking
- `x2` measures intermediate-term trend stacking
- `x3` measures short/medium slope strength
- `x4` measures long-term slope strength

This formula is mandatory for v2 and must be persisted in the feature store.

---

## 6) Candidate ranking

### 6.1 Hard preconditions before ranking
A symbol is rankable only if all are true:
- passes universe eligibility
- `split_adj_close_t > ma50_t`
- `ma50_t > ma200_t`
- `ma200_slope_pct20_t > 0`
- `dist_to_52w_high_t <= max_distance_from_52w_high`
- earnings filter does not block new entries
- current regime permits new entries

### 6.2 Cross-sectional normalization
On each session `t`, across the rankable universe:
1. winsorize each ranking component at the configured lower and upper percentiles
2. compute a cross-sectional z-score for each component
3. if a component's cross-sectional standard deviation is zero, set its z-score to zero for that session

### 6.3 Candidate score
The required v2 score is:

```text
candidate_score_raw_t =
    0.35 * zscore(mom_252_21_t)
  + 0.20 * zscore(ret_126_t)
  + 0.20 * zscore(rs_vs_benchmark_126_t)
  + 0.15 * zscore(1 - dist_to_52w_high_t)
  + 0.10 * zscore(trend_quality_t)
```

Then compute:
```text
candidate_score_pct_t = percentile_rank(candidate_score_raw_t)
```

### 6.4 Candidate state
A rankable symbol becomes a `CANDIDATE` only if:
- `candidate_score_pct_t >= regime.min_candidate_score_percentile`
- `trend_quality_t >= regime.min_trend_quality`

---

## 7) Setup detector

A `CANDIDATE` can become `ARMED` only if it forms one of the approved setup types:
- `PULLBACK`
- `TIGHT_BASE`

### 7.1 Shared setup preconditions
These are required for both setup types:
- `split_adj_close_t > ma50_t`
- `ma50_t > ma200_t`
- `ma200_slope_pct20_t > 0`
- `dist_to_52w_high_t <= max_distance_from_52w_high`
- regime still permits new entries
- `regular_closes_until_earnings_event` is null or `regular_closes_until_earnings_event > min_regular_closes_before_earnings_for_new_entry`

### 7.2 Pullback setup: exact rules
A `PULLBACK` exists on session `t` if all are true:
- `pullback_days_t` in `[pullback_min_days, pullback_max_days]`
- `pullback_depth_atr_t <= max_pullback_depth_atr`
- `range_compression_ratio_t <= max_pullback_range_compression_ratio`
- `min(split_adj_low over pullback window) >= ma50_t - support_buffer_atr * atr_14_t`

Definitions:
```text
pullback_window = [anchor_high_date, t]
setup_high_t    = max(split_adj_high over pullback_window)
setup_low_t     = min(split_adj_low  over pullback_window)
setup_high_date = most recent date in pullback_window where split_adj_high == setup_high_t
setup_low_date  = most recent date in pullback_window where split_adj_low  == setup_low_t
setup_start     = anchor_high_date
setup_end       = t
```

Optional dry-up filter if enabled:
```text
mean(raw_volume over pullback_window) / SMA(raw_volume, 20)_t <= max_setup_volume_ratio
```

### 7.3 Tight-base setup: exact rules
A `TIGHT_BASE` exists on session `t` if there is at least one integer `n` in `[tight_base_min_days, tight_base_max_days]` such that the last `n` sessions form a valid base.

For each candidate `n`, define:
```text
base_window_n      = [t-n+1, t]
base_range_atr_n   = (max(split_adj_high over base_window_n) - min(split_adj_low over base_window_n)) / atr_14_t
base_return_abs_n  = abs(split_adj_close_t / split_adj_close_{t-n+1} - 1)
```

A window is valid if:
- `base_range_atr_n <= max_base_range_atr`
- `base_return_abs_n <= max_base_drift_pct`
- `range_compression_ratio_t <= max_base_range_compression_ratio`

Selection rule:
- choose the **longest** valid base window ending on `t`

Then:
```text
setup_high_t = max(split_adj_high over chosen_base_window)
setup_low_t  = min(split_adj_low  over chosen_base_window)
setup_high_date = most recent date in chosen_base_window where split_adj_high == setup_high_t
setup_low_date  = most recent date in chosen_base_window where split_adj_low  == setup_low_t
setup_start  = first date in chosen_base_window
setup_end    = t
```

### 7.4 Setup type priority
If both `PULLBACK` and `TIGHT_BASE` are valid on the same session, choose:
1. `TIGHT_BASE` first
2. otherwise `PULLBACK`

Reason: the tighter pattern is preferred for stop placement and risk efficiency.

### 7.5 Setup identity
Every setup must have a deterministic `setup_id`:

```text
setup_id = sha256(
    symbol,
    pattern_type,
    setup_start_date,
    setup_end_date,
    setup_high_date,
    setup_low_date
)
```

The setup registry must persist:
- current active `setup_id`
- spent `setup_id`s
- entry intent associated with each `setup_id`

This is mandatory for stale-order protection.

---

## 8) Entry engine

### 8.1 Entry trigger
For a valid `ARMED` setup on session `t`:

```text
entry_trigger_t = setup_high_t + entry_buffer_atr * atr_14_t
entry_limit_t   = entry_trigger_t + max_gap_above_trigger_atr * atr_14_t
```

`entry_limit_t` is the hard no-chase cap for the setup.

### 8.2 Initial protective stop
Define:

```text
stop_from_setup_t = setup_low_t - setup_low_buffer_atr * atr_14_t
stop_from_atr_t   = entry_trigger_t - stop_atr_multiple * atr_14_t
initial_stop_t    = min(stop_from_setup_t, stop_from_atr_t)
per_share_risk_t  = entry_trigger_t - initial_stop_t
```

Reject the order if:
- `per_share_risk_t <= 0`
- portfolio heat / sector / notional limits would be violated
- another pending entry already exists for the symbol
- an open position already exists for the symbol

### 8.3 Overnight submission and opening-gap rule
The baseline system rests the entry order overnight because the stop-limit cap itself enforces the no-chase boundary.

Submission policy:
- create and transmit the entry order after the regular close of session `t`
- the order remains valid only for the next regular session unless it is cancelled earlier

Opening-gap rule:
- let `official_open_next` be the primary-market official regular-session opening print for session `t+1`
- if `official_open_next > entry_limit_t`, the order must remain unfilled at the open because the limit cap has been exceeded
- cancel any still-unfilled order immediately after observing `official_open_next`
- mark the setup as spent

Formally:
```text
official_open_next > entry_limit_t
```
then cancel the entry for that setup and mark the setup as spent.

### 8.4 Order type
Entry order is always:
- side: `BUY`
- type: `STOP_LIMIT`
- stop: `entry_trigger_t`
- limit: `entry_limit_t`

### 8.5 Expiry and stale-order rule
A pending entry expires at the close of the `order_expiry_sessions`-th regular session after submission if still unfilled.

Also cancel the pending entry immediately if any of the following occurs before fill:
- regime changes to a state that blocks new entries
- earnings window is breached
- symbol no longer passes shared setup preconditions
- a broker reject or reconciliation error invalidates the intent

### 8.6 One pending entry per symbol
This is now an explicit system rule:

- `max_pending_orders_per_symbol = 1`
- `max_open_positions_per_symbol = 1`
- `pyramiding_allowed = false`

### 8.7 Post-cancel / post-expiry transition
When an entry order is cancelled, rejected, or expires:
1. mark its `setup_id` as **spent**
2. clear the active pending intent for the symbol
3. re-evaluate the symbol in this order:
   - if hard eligibility fails -> `INELIGIBLE`
   - else if candidate criteria pass -> `CANDIDATE`
   - else -> `ELIGIBLE`

The symbol may return to `ARMED` only when a **new** `setup_id` forms. The same spent setup must never be re-submitted.

This resolves the stale-order and duplicate-entry ambiguity from the prior draft.

---

## 9) Position sizing and portfolio risk

### 9.1 Per-trade risk budget
On session `t`:

```text
base_risk_budget_t = equity_t * risk_per_trade_pct_equity
regime_risk_budget_t = base_risk_budget_t * regime.size_multiplier
```

### 9.2 Share calculation
```text
shares_from_risk   = floor(regime_risk_budget_t / per_share_risk_t)
shares_from_notional = floor((equity_t * max_position_pct_equity) / entry_trigger_t)

shares_t = min(shares_from_risk, shares_from_notional)
```

Reject the order if `shares_t < 1`.

### 9.3 Portfolio heat
Portfolio heat is defined as:

```text
portfolio_heat_t =
    sum_i((entry_reference_price_i - protective_stop_i) * quantity_i) / equity_t
```

A new order is allowed only if all remain within limits after hypothetical addition:
- `portfolio_heat <= max_portfolio_heat_pct_equity`
- `daily_new_risk <= max_new_risk_per_day_pct_equity`
- `sector_gross_exposure <= max_sector_pct_equity`

### 9.4 Volatility target overlay
A portfolio-level volatility target may further scale new trade size downward, but it must never increase size above the regime-adjusted risk budget.

---

## 10) Exit engine

The exit engine is deterministic and intentionally simple.

### 10.1 Initial hard stop
Immediately after fill, the position receives a hard protective stop derived from `initial_stop_t`.

### 10.2 Trailing stop activation
Trailing logic activates only after the trade has achieved minimum follow-through:

```text
max_high_since_entry >= entry_fill_price + trail_activate_after_gain_atr * atr_at_entry
```

When active:

```text
effective_trailing_multiple =
    trailing_atr_multiple                  if regime_state != RISK_OFF
    risk_off_trailing_atr_multiple         if regime_state == RISK_OFF

trailing_stop_t =
    max(existing_stop_t,
        highest_high_since_entry - effective_trailing_multiple * atr_14_t)
```

### 10.3 Time stop
A time stop triggers if the trade has not made enough progress within the allowed number of bars.

```text
progress_atr = (max_high_since_entry - entry_fill_price) / atr_at_entry
time_stop_triggered = (
    bars_since_entry >= max_bars_without_progress
    and progress_atr < min_progress_after_n_bars_atr
)
```

If triggered, submit an exit on the next regular session.

### 10.4 Earnings exit
If `allow_holding_through_earnings = false`, the earnings exit rule is evaluated after the regular close of session `t`.

For this daily post-close engine:
- `earnings_exit_lead_regular_closes` must be `>= 1`
- if `regular_closes_until_earnings_event_t` is null, no earnings exit is scheduled
- if `regular_closes_until_earnings_event_t <= earnings_exit_lead_regular_closes`, generate an `EARNINGS_EXIT` intent for the **next regular session**

This policy is deterministic for both `PRE_OPEN` and `POST_CLOSE` earnings events because the timing field counts remaining regular-session closes, not calendar days.

### 10.5 Regime exit policy
The v2 default is:
- `RISK_OFF`: do **not** force an immediate full liquidation
- instead, tighten trailing logic using `risk_off_trailing_atr_multiple`
- new entries remain blocked

This keeps the regime behavior deterministic without creating a second, ambiguous discretionary exit policy.

### 10.6 Profit targets
There is no fixed profit target in the baseline system.

---

## 11) State machine

### 11.1 States
Per symbol:

```text
INELIGIBLE
ELIGIBLE
CANDIDATE
ARMED
PENDING_ENTRY
ACTIVE
EXIT_PENDING
CLOSED
```

### 11.2 State meanings
- `INELIGIBLE`: fails universe or hard trading filters
- `ELIGIBLE`: passes hard filters but is not a candidate
- `CANDIDATE`: passes ranking and regime-specific thresholds
- `ARMED`: valid setup with fresh `setup_id`
- `PENDING_ENTRY`: exactly one entry intent active at broker
- `ACTIVE`: long position open
- `EXIT_PENDING`: an exit intent is active
- `CLOSED`: trade completed and archived

### 11.3 Allowed transitions
| From | Event | To |
|---|---|---|
| `INELIGIBLE` | hard filters pass | `ELIGIBLE` |
| `ELIGIBLE` | candidate criteria pass | `CANDIDATE` |
| `CANDIDATE` | valid fresh setup forms | `ARMED` |
| `ARMED` | entry intent submitted | `PENDING_ENTRY` |
| `ARMED` | setup invalidates before submission | `CANDIDATE` or `ELIGIBLE` |
| `PENDING_ENTRY` | fill confirmed | `ACTIVE` |
| `PENDING_ENTRY` | cancel / reject / expire | `CANDIDATE`, `ELIGIBLE`, or `INELIGIBLE` after ordered re-evaluation |
| `ACTIVE` | exit intent submitted | `EXIT_PENDING` |
| `EXIT_PENDING` | exit fill confirmed | `CLOSED` |
| `CLOSED` | next evaluation cycle | `ELIGIBLE` or `INELIGIBLE` |

### 11.4 Invariants
Mandatory invariants:
- at most one `ACTIVE` position per symbol
- at most one `PENDING_ENTRY` intent per symbol
- an `ACTIVE` position and `PENDING_ENTRY` entry may not coexist for the same symbol
- a spent `setup_id` cannot be re-armed

---

## 12) Data contracts

### 12.1 `SymbolDailyBar`
```yaml
symbol: str
session_date: date
session_type: REGULAR | PRE | POST

raw_open: float
raw_high: float
raw_low: float
raw_close: float
raw_volume: float

split_adj_open: float
split_adj_high: float
split_adj_low: float
split_adj_close: float
split_adj_volume: float

cash_dividend_per_share: float
split_ratio: float
tr_close_index: float

currency: str
exchange: str
is_tradable: bool
```

### 12.2 `FeatureSnapshot`
```yaml
symbol: str
session_date: date

ret_21: float
ret_63: float
ret_126: float
ret_252: float
mom_252_21: float
rs_vs_benchmark_126: float

ma20: float
ma50: float
ma200: float
ma50_slope_pct20: float
ma200_slope_pct20: float

atr_14: float
atr_5: float
atr_20: float
atr_pct: float
range_compression_ratio: float

dist_to_52w_high: float
pullback_days: int
pullback_depth_atr: float
volume_ratio_20: float
trend_quality: float

candidate_score_raw: float
candidate_score_pct: float
effective_candidate_score_threshold_pct: float
effective_min_trend_quality: float

pattern_type: PULLBACK | TIGHT_BASE | null
setup_id: str | null
setup_start_date: date | null
setup_end_date: date | null
setup_high: float | null
setup_low: float | null
setup_high_date: date | null
setup_low_date: date | null
setup_valid: bool

earnings_event_session: PRE_OPEN | POST_CLOSE | UNKNOWN | null
regular_closes_until_earnings_event: int | null
```

### 12.3 `RegimeSnapshot`
```yaml
session_date: date
benchmark_symbol: str

benchmark_close: float
benchmark_ma200: float
benchmark_ma200_slope_pct20: float
benchmark_dist_above_ma200: float

realized_vol_20: float
breadth_pct_above_ma200: float | null
panic_drawdown_126: float
rebound_return_20: float

regime_state: RISK_ON | CAUTION | RISK_OFF | PANIC_REBOUND
entry_enabled: bool
size_multiplier: float
min_candidate_score_percentile: float
min_trend_quality: float
```

### 12.4 `SetupSnapshot`
```yaml
symbol: str
session_date: date
pattern_type: PULLBACK | TIGHT_BASE
setup_id: str
setup_start_date: date
setup_end_date: date
setup_high: float
setup_low: float
setup_high_date: date
setup_low_date: date
entry_trigger: float
entry_limit: float
initial_stop: float
per_share_risk: float
spent: bool
```

### 12.5 `OrderIntent`
```yaml
intent_id: str
dedupe_key: str
strategy_id: str
config_hash: str

symbol: str
setup_id: str | null
side: BUY | SELL
reason: ENTRY | INITIAL_STOP | TRAIL_STOP | TIME_EXIT | EARNINGS_EXIT | REGIME_EXIT | KILL_SWITCH
order_type: MARKET | LIMIT | STOP | STOP_LIMIT

quantity: float
stop_price: float | null
limit_price: float | null

created_at: datetime
expires_at: datetime | null
broker_order_id: str | null
```

---

## 13) System modules for Codex

### 13.1 Required modules
1. `reference_master`
2. `corporate_action_service`
3. `market_data_ingestion`
4. `canonical_price_series`
5. `feature_store`
6. `regime_engine`
7. `universe_builder`
8. `candidate_ranker`
9. `setup_detector`
10. `setup_registry`
11. `position_sizer`
12. `risk_engine`
13. `order_intent_service`
14. `execution_adapter`
15. `order_state_machine`
16. `portfolio_manager`
17. `reconciliation`
18. `analytics`
19. `monitoring_alerts`
20. `backtest_engine`
21. `config_service`

### 13.2 New mandatory persistence added in v2
The following stores are now mandatory:
- **spent setup registry** keyed by `setup_id`
- **order intent dedupe store** keyed by `dedupe_key`
- **regime snapshot store**
- **canonical-price snapshot hashes** for reproducibility

### 13.3 Code principles
- strategy logic must be config-driven
- feature computation must be pure and side-effect free
- the same feature library must run in backtest and live
- every order decision must be reconstructable from saved inputs
- broker-side effects must be isolated behind the adapter
- the adapter must be restart-safe and deduplicate intents

---

## 14) Backtest / live parity standard

### 14.1 Signal / execution parity
Backtest and live must use the same source-policy matrix:

- chart features -> split-adjusted OHLC
- return ranking -> total-return close index
- fills -> raw OHLC
- P&L dividends -> accounting layer

### 14.2 Non-negotiables
- no lookahead bias
- no survivorship bias
- point-in-time universe membership
- point-in-time corporate actions
- point-in-time earnings calendars where possible
- point-in-time breadth universe
- realistic slippage and spread model
- same stale-order and spent-setup logic in backtest and live

### 14.3 Mandatory unit tests
At minimum, Codex should create tests for:
1. **split event continuity**
   - ATR, MA, and 52-week-high calculations remain continuous in split-adjusted space
2. **cash dividend handling**
   - dividends change `tr_close_index` but do not alter setup OHLC
3. **trend_quality determinism**
   - same input bars always produce the same bounded score
4. **regime precedence**
   - `PANIC_REBOUND` overrides `CAUTION` and `RISK_ON`
5. **breadth fail-closed behavior**
   - missing breadth input produces `RISK_OFF` when breadth is enabled
6. **spent-setup rule**
   - expired/cancelled setup cannot be re-submitted
7. **single pending order invariant**
   - duplicate entry intents for the same symbol are rejected
8. **state recovery**
   - restart with an existing broker order restores `PENDING_ENTRY` without creating a second order

### 14.4 Mandatory acceptance tests
The MVP is not accepted until it can demonstrate:
- identical candidate ranking from repeated runs on the same data snapshot
- no duplicate order creation across restart/replay scenarios
- correct reclassification after order expiry and cancel
- no divergence between backtest state logic and live state logic for the same historical replay

---

## 15) Deployment and management plan

### Phase 0 — Build contracts first
1. data contracts
2. canonical price-series service
3. corporate-action tests
4. regime engine tests
5. feature library tests

### Phase 1 — Research baseline
1. candidate ranker
2. setup detector
3. entry / exit logic
4. backtester
5. regime-segmented analytics

### Phase 2 — Operational layer
1. order intent service
2. broker adapter
3. reconciliation
4. monitoring and kill switches
5. restart recovery

### Phase 3 — Paper and shadow
1. paper trading only
2. shadow live order generation
3. compare intended vs hypothetical fills
4. verify spent-setup and cancel behavior

### Phase 4 — Small-capital launch
- low position cap
- low daily new-risk cap
- manual kill switch enabled
- strict drift review between live and backtest assumptions

### Phase 5 — Controlled scale
Increase only after:
- statistically meaningful live sample
- fill/slippage analysis
- regime-state drift review
- no duplicate-intent incidents
- no reconciliation control failures

---

## 16) Explicit answers to the review questions

### Q1. Should signal generation use split-adjusted OHLC only, or total-return-adjusted bars including dividends?
**Answer:** use a hybrid design:
- split-adjusted OHLC for chart, ATR, setup, stops, 52-week highs, breadth, and trend structure
- total-return close index for return-ranking features only
- raw OHLC for execution

### Q2. What is the exact formula for `trend_quality`?
**Answer:** the formula in section 5.8 is the required implementation:
```text
trend_quality =
    0.30 * clamp((ma20 / ma50 - 1) / 0.08, 0, 1)
  + 0.35 * clamp((ma50 / ma200 - 1) / 0.15, 0, 1)
  + 0.20 * clamp(ma50_slope_pct20 / 0.06, 0, 1)
  + 0.15 * clamp(ma200_slope_pct20 / 0.03, 0, 1)
```

### Q3. Is breadth measured over the tradable universe, a benchmark constituent set, or something else?
**Answer:** the point-in-time common-stock subset of the strategy universe after hard eligibility filters and with ETFs excluded.

### Q4. Is more than one pending entry per symbol intentional?
**Answer:** no. The v2 policy is exactly one pending entry and one open position per symbol, with no pyramiding.

---

## 17) Definition of done

The strategy is not implementation-ready until Codex delivers a system that can:
- reproduce the same signal from the same snapshot
- compute the exact feature set defined here
- show no ambiguity in price-source usage
- enforce one pending entry and one open position per symbol
- persist and honor spent setup IDs
- reconcile broker state without duplicate orders
- pass split/dividend replay tests
- pass walk-forward research and operational failure-mode tests
- provide full auditability for every state transition and order intent
