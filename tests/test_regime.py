from __future__ import annotations

import pandas as pd

from swingmachine.config import load_strategy_config
from swingmachine.enums import RegimeState
from swingmachine.regime import classify_regimes


def test_classify_regimes_panic_rebound_has_precedence() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    inputs = pd.DataFrame(
        {
            "session_date": [pd.Timestamp("2026-04-23")],
            "benchmark_symbol": ["SPY"],
            "benchmark_close": [90.0],
            "benchmark_ma200": [100.0],
            "benchmark_ma200_slope_pct20": [-0.01],
            "benchmark_dist_above_ma200": [-0.10],
            "realized_vol_20": [0.35],
            "panic_drawdown_126": [-0.25],
            "rebound_return_20": [0.12],
        }
    )
    breadth = pd.DataFrame(
        {
            "session_date": [pd.Timestamp("2026-04-23")],
            "breadth_constituents": [250],
            "breadth_pct_above_ma200": [0.80],
        }
    )

    result = classify_regimes(inputs, config, breadth_by_session=breadth)

    assert result.loc[0, "regime_state"] == RegimeState.PANIC_REBOUND.value
    assert not bool(result.loc[0, "entry_enabled"])


def test_classify_regimes_fail_closed_when_breadth_missing() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    inputs = pd.DataFrame(
        {
            "session_date": [pd.Timestamp("2026-04-23")],
            "benchmark_symbol": ["SPY"],
            "benchmark_close": [110.0],
            "benchmark_ma200": [100.0],
            "benchmark_ma200_slope_pct20": [0.01],
            "benchmark_dist_above_ma200": [0.10],
            "realized_vol_20": [0.15],
            "panic_drawdown_126": [-0.05],
            "rebound_return_20": [0.01],
        }
    )

    result = classify_regimes(inputs, config)

    assert result.loc[0, "regime_state"] == RegimeState.RISK_OFF.value
    assert not bool(result.loc[0, "entry_enabled"])
