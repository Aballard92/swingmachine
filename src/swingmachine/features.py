from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from swingmachine.config import StrategyRuntimeConfig

REQUIRED_CANONICAL_FEATURE_COLUMNS = (
    "session_date",
    "raw_volume",
    "split_adj_high",
    "split_adj_low",
    "split_adj_close",
    "tr_close_index",
)


def _validate_columns(frame: pd.DataFrame, required: Sequence[str]) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Missing required columns: {missing_str}")


def _ordered_frame(frame: pd.DataFrame) -> pd.DataFrame:
    _validate_columns(frame, REQUIRED_CANONICAL_FEATURE_COLUMNS)
    ordered = frame.copy()
    ordered["session_date"] = pd.to_datetime(ordered["session_date"])
    ordered = ordered.sort_values("session_date").reset_index(drop=True)
    return ordered


def _require_formula_windows(config: StrategyRuntimeConfig) -> None:
    ma_windows = set(config.features.moving_averages)
    atr_windows = set(config.features.atr_windows)
    required_mas = {20, 50, 200}
    required_atrs = {5, 14, 20}

    if not required_mas.issubset(ma_windows):
        raise ValueError("Feature formulas require moving averages 20, 50, and 200")
    if not required_atrs.issubset(atr_windows):
        raise ValueError("Feature formulas require ATR windows 5, 14, and 20")


def _align_series(series: pd.Series, ordered_dates: pd.Series) -> pd.Series:
    if len(series) == len(ordered_dates) and series.index.equals(ordered_dates.index):
        return series.astype(float).reset_index(drop=True)

    converted_dates = pd.to_datetime(ordered_dates)
    series_copy = series.copy()
    series_copy.index = pd.to_datetime(series_copy.index)
    aligned = series_copy.reindex(converted_dates)
    return aligned.astype(float).reset_index(drop=True)


def _rolling_most_recent_extreme_positions(
    values: pd.Series,
    *,
    window: int,
    mode: str,
) -> np.ndarray:
    array = values.to_numpy(dtype=float)
    positions = np.full(len(array), -1, dtype=int)

    for end in range(len(array)):
        start = max(0, end - window + 1)
        window_values = array[start : end + 1]
        valid = ~np.isnan(window_values)
        if not valid.any():
            continue

        if mode == "max":
            extreme = np.nanmax(window_values)
        elif mode == "min":
            extreme = np.nanmin(window_values)
        else:
            raise ValueError(f"Unsupported mode: {mode}")

        matches = np.flatnonzero(np.isclose(window_values, extreme, equal_nan=False))
        if matches.size > 0:
            positions[end] = start + int(matches[-1])

    return positions


def _positions_to_dates(positions: np.ndarray, session_dates: pd.Series) -> pd.Series:
    dates = pd.to_datetime(session_dates).to_numpy(dtype="datetime64[ns]")
    out = np.full(len(positions), np.datetime64("NaT"), dtype="datetime64[ns]")
    valid = positions >= 0
    out[valid] = dates[positions[valid]]
    return pd.Series(pd.to_datetime(out))


def wilder_ema(series: pd.Series, window: int) -> pd.Series:
    if window <= 0:
        raise ValueError("window must be strictly positive")
    return series.astype(float).ewm(alpha=1.0 / window, adjust=False).mean()


def compute_core_features(
    frame: pd.DataFrame,
    config: StrategyRuntimeConfig,
    *,
    benchmark_tr_close_index: pd.Series | None = None,
) -> pd.DataFrame:
    _require_formula_windows(config)
    ordered = _ordered_frame(frame)

    result = ordered.copy()
    tr_close = result["tr_close_index"].astype(float)
    split_adj_close = result["split_adj_close"].astype(float)
    split_adj_high = result["split_adj_high"].astype(float)
    split_adj_low = result["split_adj_low"].astype(float)
    raw_volume = result["raw_volume"].astype(float)

    for lookback in (21, 63, 126, 252):
        result[f"ret_{lookback}"] = tr_close / tr_close.shift(lookback) - 1.0

    result["mom_252_21"] = tr_close.shift(21) / tr_close.shift(252) - 1.0

    benchmark_tr_close: pd.Series | None = None
    benchmark_relative = config.benchmark_relative_features
    relative_strength_windows = tuple(benchmark_relative.relative_strength_windows)

    if benchmark_relative.compute and benchmark_tr_close_index is not None:
        benchmark_tr_close = _align_series(benchmark_tr_close_index, result["session_date"])
        for window in relative_strength_windows:
            symbol_return = tr_close / tr_close.shift(window) - 1.0
            benchmark_return = benchmark_tr_close / benchmark_tr_close.shift(window) - 1.0
            result[f"rs_vs_benchmark_{window}"] = symbol_return - benchmark_return
    else:
        for window in relative_strength_windows:
            result[f"rs_vs_benchmark_{window}"] = np.nan

    if "rs_vs_benchmark_126" not in result:
        result["rs_vs_benchmark_126"] = np.nan

    for window in (20, 50, 200):
        result[f"ma{window}"] = split_adj_close.rolling(window=window, min_periods=window).mean()

    slope_lookback = config.regime.ma200_slope_lookback_days
    result["ma50_slope_pct20"] = result["ma50"] / result["ma50"].shift(slope_lookback) - 1.0
    result["ma200_slope_pct20"] = result["ma200"] / result["ma200"].shift(slope_lookback) - 1.0

    prev_close = split_adj_close.shift(1)
    true_range = pd.concat(
        [
            split_adj_high - split_adj_low,
            (split_adj_high - prev_close).abs(),
            (split_adj_low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    result["true_range"] = true_range
    result["atr_5"] = wilder_ema(true_range, 5)
    result["atr_14"] = wilder_ema(true_range, 14)
    result["atr_20"] = wilder_ema(true_range, 20)
    result["atr_pct"] = result["atr_14"] / split_adj_close

    compression = config.features.range_compression_ratio
    numerator = result[f"atr_{compression.numerator_atr_window}"]
    denominator = result[f"atr_{compression.denominator_atr_window}"]
    result["range_compression_ratio"] = numerator / denominator

    lookback_52w = config.features.high_lookback_days_for_52w
    result["rolling_52w_high"] = split_adj_high.rolling(
        window=lookback_52w,
        min_periods=lookback_52w,
    ).max()
    result["dist_to_52w_high"] = (1.0 - split_adj_close / result["rolling_52w_high"]).clip(
        lower=0.0, upper=1.0
    )

    anchor_lookback = config.features.pullback_anchor_lookback_days
    anchor_positions = _rolling_most_recent_extreme_positions(
        split_adj_high,
        window=anchor_lookback,
        mode="max",
    )
    row_positions = np.arange(len(result), dtype=float)
    valid_anchor = anchor_positions >= 0
    pullback_days = np.full(len(result), np.nan, dtype=float)
    pullback_days[valid_anchor] = row_positions[valid_anchor] - anchor_positions[valid_anchor]

    anchor_high = np.full(len(result), np.nan, dtype=float)
    anchor_high[valid_anchor] = split_adj_high.to_numpy()[anchor_positions[valid_anchor]]

    result["anchor_high_20"] = anchor_high
    result["anchor_high_date"] = _positions_to_dates(anchor_positions, result["session_date"])
    result["pullback_days"] = pullback_days
    result["pullback_depth_atr"] = (result["anchor_high_20"] - split_adj_close) / result["atr_14"]

    for pair in benchmark_relative.acceleration_pairs:
        short_column = f"rs_vs_benchmark_{pair.short_window}"
        long_column = f"rs_vs_benchmark_{pair.long_window}"
        result[f"rs_acceleration_{pair.short_window}_vs_{pair.long_window}"] = (
            result[short_column] - result[long_column]
            if short_column in result and long_column in result
            else np.nan
        )

    drawdown_window = benchmark_relative.drawdown_window
    rebound_window = benchmark_relative.rebound_window
    symbol_rolling_high = split_adj_close.rolling(
        window=drawdown_window,
        min_periods=drawdown_window,
    ).max()
    result[f"symbol_drawdown_{drawdown_window}"] = split_adj_close / symbol_rolling_high - 1.0
    if benchmark_relative.compute and benchmark_tr_close is not None:
        benchmark_rolling_high = benchmark_tr_close.rolling(
            window=drawdown_window,
            min_periods=drawdown_window,
        ).max()
        result[f"benchmark_drawdown_{drawdown_window}"] = (
            benchmark_tr_close / benchmark_rolling_high - 1.0
        )
        result[f"relative_drawdown_{drawdown_window}"] = (
            result[f"symbol_drawdown_{drawdown_window}"]
            - result[f"benchmark_drawdown_{drawdown_window}"]
        )
        symbol_rebound = tr_close / tr_close.shift(rebound_window) - 1.0
        benchmark_rebound = benchmark_tr_close / benchmark_tr_close.shift(rebound_window) - 1.0
        result[f"relative_rebound_{rebound_window}"] = symbol_rebound - benchmark_rebound
    else:
        result[f"benchmark_drawdown_{drawdown_window}"] = np.nan
        result[f"relative_drawdown_{drawdown_window}"] = np.nan
        result[f"relative_rebound_{rebound_window}"] = np.nan

    result["volume_ratio_20"] = raw_volume / raw_volume.rolling(window=20, min_periods=20).mean()

    full_score_levels = config.ranking.trend_quality.full_score_levels
    weights = config.ranking.trend_quality.components

    x1 = ((result["ma20"] / result["ma50"] - 1.0) / full_score_levels.ma20_over_ma50).clip(0.0, 1.0)
    x2 = ((result["ma50"] / result["ma200"] - 1.0) / full_score_levels.ma50_over_ma200).clip(
        0.0, 1.0
    )
    x3 = (result["ma50_slope_pct20"] / full_score_levels.ma50_slope_pct20).clip(0.0, 1.0)
    x4 = (result["ma200_slope_pct20"] / full_score_levels.ma200_slope_pct20).clip(0.0, 1.0)

    result["trend_quality"] = (
        weights.ma20_over_ma50_weight * x1
        + weights.ma50_over_ma200_weight * x2
        + weights.ma50_slope_pct20_weight * x3
        + weights.ma200_slope_pct20_weight * x4
    ).clip(0.0, 1.0)

    return result
