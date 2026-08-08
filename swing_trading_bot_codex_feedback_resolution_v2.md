# Codex Feedback Resolution Note
## Swing Bot Spec v2.1

This note maps the review findings to the revised artifacts:
- design spec: `swing_trading_bot_design_spec_v2.md`
- config: `swing_trading_bot_config_template_v2.yaml`

## Resolved findings

### 1) Adjusted OHLC ambiguity
**Resolved.**

The revised design now uses three explicit series:
- raw OHLCV for execution
- split-adjusted OHLCV for setup/trend/ATR/52-week-high logic
- total-return close index for return-ranking features only

Where to review:
- design spec section 2
- design spec section 12.1
- config `data.canonical_price_series`
- config `backtest.signal_price_sources`

### 2) Undefined `trend_quality`
**Resolved.**

The revised design defines `trend_quality` as a bounded linear-clamped score:

```text
trend_quality =
    0.30 * clamp((ma20 / ma50 - 1) / 0.08, 0, 1)
  + 0.35 * clamp((ma50 / ma200 - 1) / 0.15, 0, 1)
  + 0.20 * clamp(ma50_slope_pct20 / 0.06, 0, 1)
  + 0.15 * clamp(ma200_slope_pct20 / 0.03, 0, 1)
```

Where to review:
- design spec section 5.8
- design spec section 12.2
- config `ranking.trend_quality`

### 3) Regime engine not reproducible from config
**Resolved.**

The revised config now carries:
- realized-vol thresholds for `CAUTION` and `RISK_OFF`
- breadth thresholds for `RISK_ON` and `RISK_OFF`
- minimum distance above MA200 for `CAUTION`
- panic-rebound thresholds
- explicit per-regime actions:
  - entry enabled / disabled
  - size multiplier
  - min candidate score percentile
  - min trend quality

Where to review:
- design spec section 4
- design spec section 12.3
- config `breadth`
- config `regime`

### 4) Multiple pending orders per symbol vs single `PENDING_ENTRY` state
**Resolved.**

The revised design explicitly sets:
- one pending entry per symbol
- one open position per symbol
- no pyramiding
- spent-setup logic after cancel / reject / expiry

The post-cancel transition is now deterministic:
1. mark setup as spent
2. clear pending intent
3. re-evaluate to `INELIGIBLE`, `ELIGIBLE`, or `CANDIDATE`
4. only a new `setup_id` can re-arm the symbol

Where to review:
- design spec sections 7.5, 8.5, 8.6, 8.7, 11
- config `entry.one_pending_entry_per_symbol`
- config `execution.max_pending_orders_per_symbol`
- config `execution.max_open_positions_per_symbol`
- config `setup.setup_registry`

## Additional follow-up fixes

### 5) Earnings timing was still ambiguous for a daily post-close engine
**Resolved.**

The revised design now uses:
- `earnings_event_session` with `PRE_OPEN | POST_CLOSE | UNKNOWN`
- `regular_closes_until_earnings_event`
- fail-closed treatment for `UNKNOWN` session timing by mapping it to zero remaining regular closes

This gives one deterministic field for both:
- blocking new entries near earnings
- scheduling exits before earnings without relying on calendar-day guesses

Where to review:
- design spec section 2.5
- design spec section 7.1
- design spec section 10.4
- design spec section 12.2
- config `events`
- config `exits`

### 6) Gap-block logic conflicted with overnight `STOP_LIMIT` order placement
**Resolved.**

The revised design now makes the stop-limit cap itself the hard no-chase boundary:
- `entry_limit = entry_trigger + max_gap_above_trigger_atr * ATR`
- the order may rest overnight
- if the official next-session open prints above `entry_limit`, cancel the still-unfilled order and mark the setup spent

Where to review:
- design spec sections 8.1, 8.3, 8.4
- config `entry`

### 7) `setup_id` still depended on undefined tie-breaks for repeated equal highs/lows
**Resolved.**

The revised design now defines `setup_high_date` and `setup_low_date` as the **most recent** occurrence of the setup high and setup low inside the chosen setup window.

Where to review:
- design spec sections 7.2, 7.3, 7.5
- design spec section 12.2
- design spec section 12.4

### 8) Superseded v1 files could still be implemented by mistake
**Resolved.**

The archived v1 documents remain in the repo, but they are now explicitly marked as deprecated and point to the v2.1 files as the implementation source of truth.

## Answers to open questions

### Should signals use split-adjusted OHLC only, or total-return-adjusted bars including dividends?
Use a hybrid:
- split-adjusted OHLC for chart/setup/regime structure
- total-return close index for long-horizon return ranking
- raw OHLC for execution

### What is the exact formula for `trend_quality`?
Defined above and in the design spec section 5.8.

### Is breadth measured over the tradable universe, a benchmark constituent set, or something else?
Breadth uses the point-in-time common-stock subset of the strategy universe after hard eligibility filters, excluding ETFs.

### Is more than one pending entry per symbol intentional?
No. The revised design allows exactly one pending entry and one open position per symbol.
