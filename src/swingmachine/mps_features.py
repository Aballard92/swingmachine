from __future__ import annotations

import math

import numpy as np
import pandas as pd

from swingmachine.mps_config import MpsConfig

REQUIRED_COLUMNS = {
    "security_id",
    "ticker",
    "session_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "total_return_adjusted_close",
    "security_type",
    "primary_exchange",
    "country_of_primary_listing",
    "sector",
    "is_tradable",
    "is_halted",
    "is_delisted",
    "shares_outstanding",
}


def seeded_wilder_atr(frame: pd.DataFrame, period: int) -> pd.Series:
    """Wilder ATR seeded with the arithmetic mean of the first `period` TR values."""
    if period <= 0:
        raise ValueError("ATR period must be positive")
    previous_close = frame["close"].astype(float).shift(1)
    true_range = pd.concat(
        [
            frame["high"].astype(float) - frame["low"].astype(float),
            (frame["high"].astype(float) - previous_close).abs(),
            (frame["low"].astype(float) - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    if len(frame) < period:
        return result
    first_position = period - 1
    result.iloc[first_position] = float(true_range.iloc[:period].mean())
    for position in range(period, len(frame)):
        result.iloc[position] = (
            (period - 1) * result.iloc[position - 1] + true_range.iloc[position]
        ) / period
    return result


def _symbol_features(frame: pd.DataFrame, config: MpsConfig) -> pd.DataFrame:
    result = frame.sort_values("session_date").copy()
    close = result["close"].astype(float)
    tr_close = result["total_return_adjusted_close"].astype(float)
    high = result["high"].astype(float)
    low = result["low"].astype(float)
    volume = result["volume"].astype(float)
    periods = config.features.sma_periods
    result["sma20"] = close.rolling(periods.short, min_periods=periods.short).mean()
    result["sma50"] = close.rolling(periods.intermediate, min_periods=periods.intermediate).mean()
    result["sma200"] = close.rolling(periods.long, min_periods=periods.long).mean()
    result["sma200_prior"] = result["sma200"].shift(config.features.long_sma_slope_lookback)
    result["atr20"] = seeded_wilder_atr(result, config.features.atr.period)
    legs = config.features.momentum.legs
    result["mom_6m"] = tr_close.shift(legs[0].end_lag) / tr_close.shift(legs[0].start_lag) - 1.0
    result["mom_12m"] = tr_close.shift(legs[1].end_lag) / tr_close.shift(legs[1].start_lag) - 1.0
    dollar_volume = close * volume
    result["adv20_dollars"] = dollar_volume.rolling(
        config.universe.median_dollar_volume_period,
        min_periods=config.universe.median_dollar_volume_period,
    ).median()
    result["history_sessions"] = np.arange(1, len(result) + 1)
    result["market_cap"] = (close * result["shares_outstanding"].astype(float)).where(
        result["shares_data_available"]
    )
    result["peak20"] = high.rolling(
        config.pullback.peak_lookback_sessions,
        min_periods=config.pullback.peak_lookback_sessions,
    ).max()
    result["prior_high20"] = high.shift(1).rolling(20, min_periods=20).max()
    result["pullback_depth_atr"] = (result["peak20"] - close) / result["atr20"]
    touch = low <= result["sma20"]
    result["recent_sma20_touch"] = (
        touch.rolling(
            config.pullback.sma_touch_lookback_sessions,
            min_periods=config.pullback.sma_touch_lookback_sessions,
        )
        .max()
        .fillna(0.0)
        .astype(bool)
    )
    daily_range = high - low
    result["close_location_value"] = np.where(
        daily_range > 0.0, (close - low) / daily_range, np.nan
    )
    result["close_above_prior_high"] = close > high.shift(1)
    result["trend_qualified"] = (
        (close > result["sma50"])
        & (result["sma50"] > result["sma200"])
        & (result["sma200"] > result["sma200_prior"])
    )
    swing_window = config.initial_stop.swing_low_lookback_sessions
    result["swing_low"] = low.rolling(swing_window, min_periods=swing_window).min()
    result["structure_stop"] = (
        result["swing_low"] - config.initial_stop.structure_buffer_atr * result["atr20"]
    )
    return result


def compute_mps_features(panel: pd.DataFrame, config: MpsConfig) -> pd.DataFrame:
    missing = sorted(REQUIRED_COLUMNS - set(panel.columns))
    if missing:
        raise ValueError(f"MPS feature panel missing columns: {', '.join(missing)}")
    prepared = panel.copy()
    prepared["session_date"] = pd.to_datetime(prepared["session_date"])
    prepared["shares_outstanding"] = pd.to_numeric(prepared["shares_outstanding"], errors="coerce")
    valid_shares = (
        prepared["shares_outstanding"].notna()
        & np.isfinite(prepared["shares_outstanding"])
        & prepared["shares_outstanding"].gt(0.0)
    )
    if "shares_data_available" in prepared:
        prepared["shares_data_available"] = (
            prepared["shares_data_available"].fillna(False).astype(bool) & valid_shares
        )
    else:
        prepared["shares_data_available"] = valid_shares
    prepared["shares_outstanding"] = prepared["shares_outstanding"].where(
        prepared["shares_data_available"]
    )
    if prepared.duplicated(["security_id", "session_date"]).any():
        raise ValueError("duplicate security_id/session_date rows")
    parts = [
        _symbol_features(group, config) for _, group in prepared.groupby("security_id", sort=True)
    ]
    result = pd.concat(parts, ignore_index=True).sort_values(
        ["session_date", "ticker", "security_id"]
    )
    universe = config.universe
    result["eligible_universe"] = (
        (result["security_type"] == "common_stock")
        & result["primary_exchange"].isin(universe.exchanges)
        & (result["country_of_primary_listing"] == universe.country_of_primary_listing)
        & result["is_tradable"].astype(bool)
        & ~result["is_halted"].astype(bool)
        & ~result["is_delisted"].astype(bool)
        & result["shares_data_available"]
        & (result["close"] >= universe.minimum_price)
        & (result["market_cap"] >= universe.minimum_market_cap)
        & (result["adv20_dollars"] >= universe.minimum_median_dollar_volume)
        & (result["history_sessions"] >= universe.minimum_history_sessions)
    )
    result["p6"] = np.nan
    result["p12"] = np.nan
    result["raw_momentum_score"] = np.nan
    result["momentum_rank"] = np.nan
    weights = config.features.momentum.legs
    for _, indexes in result.groupby("session_date", sort=True).groups.items():
        eligible_indexes = [
            index
            for index in indexes
            if bool(result.at[index, "eligible_universe"])
            and pd.notna(result.at[index, "mom_6m"])
            and pd.notna(result.at[index, "mom_12m"])
        ]
        if not eligible_indexes:
            continue
        p6 = result.loc[eligible_indexes, "mom_6m"].rank(method="average", pct=True)
        p12 = result.loc[eligible_indexes, "mom_12m"].rank(method="average", pct=True)
        raw = weights[0].weight * p6 + weights[1].weight * p12
        result.loc[eligible_indexes, "p6"] = p6
        result.loc[eligible_indexes, "p12"] = p12
        result.loc[eligible_indexes, "raw_momentum_score"] = raw
        result.loc[eligible_indexes, "momentum_rank"] = raw.rank(method="average", pct=True)
    return result.reset_index(drop=True)


def compute_regime_multiplier(benchmark: pd.DataFrame, config: MpsConfig) -> pd.DataFrame:
    required = {"session_date", "close", "total_return_adjusted_close"}
    missing = sorted(required - set(benchmark.columns))
    if missing:
        raise ValueError(f"benchmark missing columns: {', '.join(missing)}")
    result = benchmark.copy().sort_values("session_date").reset_index(drop=True)
    result["session_date"] = pd.to_datetime(result["session_date"])
    regime = config.market_regime
    result["market_sma200"] = (
        result["close"].rolling(regime.sma_period, min_periods=regime.sma_period).mean()
    )
    log_return = np.log(result["total_return_adjusted_close"].astype(float)).diff()
    result["market_rv20"] = log_return.rolling(
        regime.realised_volatility_period,
        min_periods=regime.realised_volatility_period,
    ).std(ddof=1) * math.sqrt(regime.annualisation_sessions)
    trend = np.where(result["close"] > result["market_sma200"], 1.0, regime.below_sma_multiplier)
    volatility = np.minimum(1.0, regime.target_annualised_volatility / result["market_rv20"])
    raw = trend * volatility
    result["regime_multiplier"] = pd.Series(raw, index=result.index).clip(
        lower=regime.minimum_multiplier,
        upper=regime.maximum_multiplier,
    )
    result.loc[
        result["market_sma200"].isna() | result["market_rv20"].isna(), "regime_multiplier"
    ] = np.nan
    return result
