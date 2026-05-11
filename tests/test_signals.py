from __future__ import annotations

import pandas as pd

from swingmachine.config import load_strategy_config
from swingmachine.enums import PatternType, RegimeState
from swingmachine.signals import detect_setups, score_candidates


def test_score_candidates_uses_cross_sectional_thresholds() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    session_date = pd.Timestamp("2026-04-23")
    panel = pd.DataFrame(
        {
            "symbol": ["AAA", "BBB", "CCC"],
            "session_date": [session_date, session_date, session_date],
            "raw_close": [100.0, 100.0, 100.0],
            "raw_volume": [1_000_000.0, 1_000_000.0, 1_000_000.0],
            "split_adj_close": [120.0, 110.0, 105.0],
            "split_adj_high": [121.0, 111.0, 106.0],
            "split_adj_low": [119.0, 109.0, 104.0],
            "ma50": [100.0, 100.0, 100.0],
            "ma200": [90.0, 90.0, 90.0],
            "ma200_slope_pct20": [0.02, 0.02, 0.02],
            "dist_to_52w_high": [0.01, 0.03, 0.05],
            "mom_252_21": [0.30, 0.15, 0.10],
            "ret_126": [0.22, 0.14, 0.09],
            "rs_vs_benchmark_126": [0.12, 0.05, 0.01],
            "trend_quality": [0.80, 0.65, 0.55],
            "regular_closes_until_earnings_event": [10, 10, 10],
            "history_days": [300, 300, 300],
            "avg_daily_dollar_volume_20": [25_000_000.0, 25_000_000.0, 25_000_000.0],
        }
    )
    regime = pd.DataFrame(
        {
            "session_date": [session_date],
            "regime_state": [RegimeState.RISK_ON.value],
            "entry_enabled": [True],
            "min_candidate_score_percentile": [0.80],
            "min_trend_quality": [0.45],
        }
    )

    scored = score_candidates(panel, regime, config).sort_values("symbol").reset_index(drop=True)

    assert scored["rankable"].tolist() == [True, True, True]
    assert bool(scored.loc[0, "is_candidate"])
    assert not bool(scored.loc[1, "is_candidate"])
    assert not bool(scored.loc[2, "is_candidate"])
    assert scored.loc[0, "candidate_score_pct"] == 1.0


def test_detect_setups_prefers_tight_base_and_uses_recent_low_tie_break() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    dates = pd.bdate_range("2026-04-01", periods=6)
    panel = pd.DataFrame(
        {
            "symbol": ["AAA"] * 6,
            "session_date": dates,
            "split_adj_close": [103.5, 104.0, 103.5, 103.2, 103.0, 103.1],
            "split_adj_high": [104.0, 105.0, 104.0, 104.5, 104.0, 104.2],
            "split_adj_low": [103.0, 102.0, 102.5, 102.0, 102.0, 102.0],
            "raw_volume": [900_000.0, 800_000.0, 780_000.0, 760_000.0, 740_000.0, 720_000.0],
            "ma50": [100.0] * 6,
            "ma200": [90.0] * 6,
            "ma200_slope_pct20": [0.02] * 6,
            "dist_to_52w_high": [0.04, 0.04, 0.04, 0.05, 0.05, 0.05],
            "mom_252_21": [0.20] * 6,
            "ret_126": [0.15] * 6,
            "rs_vs_benchmark_126": [0.08] * 6,
            "trend_quality": [0.70] * 6,
            "atr_14": [2.0] * 6,
            "range_compression_ratio": [0.75] * 6,
            "pullback_days": [0.0, 0.0, 1.0, 2.0, 3.0, 4.0],
            "pullback_depth_atr": [0.2, 0.0, 0.75, 0.9, 1.0, 0.95],
            "anchor_high_date": [dates[1]] * 6,
            "volume_ratio_20": [0.80] * 6,
            "is_candidate": [False, False, False, False, False, True],
            "entry_enabled": [True] * 6,
            "regular_closes_until_earnings_event": [10] * 6,
        }
    )

    detected = detect_setups(panel, config)
    last = detected.iloc[-1]

    assert bool(last["setup_valid"])
    assert last["pattern_type"] == PatternType.TIGHT_BASE.value
    assert last["setup_start_date"] == dates[0]
    assert last["setup_end_date"] == dates[-1]
    assert last["setup_high_date"] == dates[1]
    assert last["setup_low_date"] == dates[-1]
    assert isinstance(last["setup_id"], str)
    assert len(last["setup_id"]) == 64
