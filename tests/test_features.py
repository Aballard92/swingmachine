from __future__ import annotations

import math

import numpy as np
import pandas as pd

from swingmachine.canonical import build_canonical_price_frame
from swingmachine.config import load_strategy_config
from swingmachine.features import compute_core_features


def test_compute_core_features_matches_v21_formulas() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")

    dates = pd.bdate_range("2025-01-01", periods=260)
    closes = np.concatenate(
        [
            np.arange(100.0, 355.0),
            np.array([355.0, 354.0, 353.0, 352.0, 351.0]),
        ]
    )
    highs = closes + 1.0
    lows = closes - 1.0
    volumes = np.full(len(dates), 1_000_000.0)

    frame = pd.DataFrame(
        {
            "session_date": dates,
            "raw_open": closes,
            "raw_high": highs,
            "raw_low": lows,
            "raw_close": closes,
            "raw_volume": volumes,
            "cash_dividend_per_share": np.zeros(len(dates)),
            "split_ratio": np.ones(len(dates)),
        }
    )
    canonical = build_canonical_price_frame(frame)

    benchmark_tr_close = pd.Series(np.linspace(100.0, 200.0, len(dates)), index=dates)
    features = compute_core_features(
        canonical,
        config,
        benchmark_tr_close_index=benchmark_tr_close,
    )
    last = features.iloc[-1]

    expected_ma20 = closes[-20:].mean()
    expected_ret_21 = closes[-1] / closes[-22] - 1.0
    expected_ret_126 = closes[-1] / closes[-127] - 1.0
    expected_symbol_ret_20 = closes[-1] / closes[-21] - 1.0
    expected_symbol_ret_50 = closes[-1] / closes[-51] - 1.0
    expected_symbol_ret_100 = closes[-1] / closes[-101] - 1.0
    expected_benchmark_ret_126 = benchmark_tr_close.iloc[-1] / benchmark_tr_close.iloc[-127] - 1.0
    expected_benchmark_ret_20 = benchmark_tr_close.iloc[-1] / benchmark_tr_close.iloc[-21] - 1.0
    expected_benchmark_ret_50 = benchmark_tr_close.iloc[-1] / benchmark_tr_close.iloc[-51] - 1.0
    expected_benchmark_ret_100 = benchmark_tr_close.iloc[-1] / benchmark_tr_close.iloc[-101] - 1.0
    expected_dist_to_high = 1.0 - closes[-1] / highs[255]
    expected_symbol_drawdown_63 = closes[-1] / closes[-64:-1].max() - 1.0
    expected_benchmark_drawdown_63 = (
        benchmark_tr_close.iloc[-1] / benchmark_tr_close.iloc[-64:].max() - 1.0
    )

    x1 = min(max(((closes[-20:].mean() / closes[-50:].mean()) - 1.0) / 0.08, 0.0), 1.0)
    x2 = min(max(((closes[-50:].mean() / closes[-200:].mean()) - 1.0) / 0.15, 0.0), 1.0)
    x3 = min(max((last["ma50_slope_pct20"]) / 0.06, 0.0), 1.0)
    x4 = min(max((last["ma200_slope_pct20"]) / 0.03, 0.0), 1.0)
    expected_trend_quality = 0.30 * x1 + 0.35 * x2 + 0.20 * x3 + 0.15 * x4

    assert math.isclose(last["ma20"], expected_ma20)
    assert math.isclose(last["atr_14"], 2.0)
    assert math.isclose(last["range_compression_ratio"], 1.0)
    assert math.isclose(last["ret_21"], expected_ret_21)
    assert math.isclose(last["ret_126"], expected_ret_126)
    assert math.isclose(
        last["rs_vs_benchmark_20"],
        expected_symbol_ret_20 - expected_benchmark_ret_20,
    )
    assert math.isclose(
        last["rs_vs_benchmark_50"],
        expected_symbol_ret_50 - expected_benchmark_ret_50,
    )
    assert math.isclose(
        last["rs_vs_benchmark_100"],
        expected_symbol_ret_100 - expected_benchmark_ret_100,
    )
    assert math.isclose(last["rs_vs_benchmark_126"], expected_ret_126 - expected_benchmark_ret_126)
    assert math.isclose(
        last["rs_acceleration_20_vs_100"],
        last["rs_vs_benchmark_20"] - last["rs_vs_benchmark_100"],
    )
    assert math.isclose(
        last["rs_acceleration_50_vs_126"],
        last["rs_vs_benchmark_50"] - last["rs_vs_benchmark_126"],
    )
    assert math.isclose(last["symbol_drawdown_63"], expected_symbol_drawdown_63)
    assert math.isclose(last["benchmark_drawdown_63"], expected_benchmark_drawdown_63)
    assert math.isclose(
        last["relative_drawdown_63"],
        expected_symbol_drawdown_63 - expected_benchmark_drawdown_63,
    )
    assert math.isclose(
        last["relative_rebound_20"],
        expected_symbol_ret_20 - expected_benchmark_ret_20,
    )
    assert math.isclose(last["dist_to_52w_high"], expected_dist_to_high)
    assert last["pullback_days"] == 4.0
    assert math.isclose(last["pullback_depth_atr"], (highs[255] - closes[-1]) / 2.0)
    assert math.isclose(last["volume_ratio_20"], 1.0)
    assert math.isclose(last["trend_quality"], expected_trend_quality)
    assert str(last["anchor_high_date"].date()) == str(dates[255].date())
