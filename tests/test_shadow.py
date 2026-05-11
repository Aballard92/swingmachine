from __future__ import annotations

import pandas as pd
import pytest

from swingmachine.config import load_strategy_config
from swingmachine.contracts import RuntimeCycleInput, SetupSnapshot
from swingmachine.entries import build_setup_snapshot
from swingmachine.enums import PatternType, RegimeState, RuntimeMode, ShadowFillStatus
from swingmachine.runtime import build_runtime
from swingmachine.shadow import compare_runtime_cycle_shadow_fills


def _setup_snapshot(setup_id: str, *, symbol: str = "AAA") -> SetupSnapshot:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    return build_setup_snapshot(
        {
            "symbol": symbol,
            "session_date": "2026-04-23",
            "pattern_type": PatternType.PULLBACK.value,
            "setup_id": setup_id,
            "setup_start_date": "2026-04-18",
            "setup_end_date": "2026-04-23",
            "setup_high": 100.0,
            "setup_low": 94.0,
            "setup_high_date": "2026-04-18",
            "setup_low_date": "2026-04-22",
            "atr_14": 2.0,
            "setup_valid": True,
        },
        config,
    )


def _shadow_result(setup_id: str, *, symbol: str = "AAA"):
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    runtime = build_runtime(config, database_url="sqlite+pysqlite:///:memory:")
    result = runtime.run_cycle(
        RuntimeCycleInput(
            as_of="2026-04-24T16:05:00",
            regime_state=RegimeState.RISK_ON,
            equity=100_000.0,
            last_data_at="2026-04-24T16:04:00",
            expires_at="2026-04-25T16:00:00",
            setups=(_setup_snapshot(setup_id, symbol=symbol),),
        ),
        mode=RuntimeMode.SHADOW,
    )
    return config, result


def test_compare_runtime_cycle_shadow_fills_detects_hypothetical_fill_and_alert() -> None:
    config, result = _shadow_result("setup-shadow-fill-1")
    market_data = pd.DataFrame(
        {
            "symbol": ["AAA"],
            "session_date": ["2026-04-25"],
            "raw_open": [100.3],
            "raw_high": [101.0],
            "raw_low": [99.7],
            "raw_close": [100.5],
            "raw_volume": [1_000_000_000_000.0],
            "spread_bps": [60.0],
            "fx_conversion_cost_bps": [0.0],
        }
    )

    comparison_batch = compare_runtime_cycle_shadow_fills(result, market_data, config)

    assert comparison_batch.filled_count == 1
    assert len(comparison_batch.alerts) == 1
    comparison = comparison_batch.comparisons[0]
    assert comparison.status == ShadowFillStatus.FILLED
    assert comparison.would_fill is True
    assert comparison.reference_price == pytest.approx(100.3)
    assert comparison.hypothetical_fill_price is not None
    assert comparison.hypothetical_fill_price > comparison.reference_price
    assert comparison.slippage_alert is not None
    assert comparison.slippage_alert.metric_value is not None
    assert comparison.slippage_alert.metric_value > 59.9


def test_compare_runtime_cycle_shadow_fills_detects_open_gap_cancellation() -> None:
    config, result = _shadow_result("setup-shadow-gap-1")
    market_data = pd.DataFrame(
        {
            "symbol": ["AAA"],
            "session_date": ["2026-04-25"],
            "raw_open": [102.0],
            "raw_high": [102.5],
            "raw_low": [101.9],
            "raw_close": [102.1],
            "raw_volume": [1_000_000.0],
        }
    )

    comparison_batch = compare_runtime_cycle_shadow_fills(result, market_data, config)

    assert comparison_batch.cancelled_count == 1
    comparison = comparison_batch.comparisons[0]
    assert comparison.status == ShadowFillStatus.OPEN_GAP_CANCELLED
    assert comparison.would_fill is False
    assert comparison.would_mark_setup_spent is True
    assert comparison.detail == "OPEN_GAP_ABOVE_LIMIT"


def test_compare_runtime_cycle_shadow_fills_detects_missing_market_data() -> None:
    config, result = _shadow_result("setup-shadow-missing-1")
    market_data = pd.DataFrame(
        {
            "symbol": ["BBB"],
            "session_date": ["2026-04-25"],
            "raw_open": [100.3],
            "raw_high": [101.0],
            "raw_low": [99.7],
            "raw_close": [100.5],
            "raw_volume": [1_000_000.0],
        }
    )

    comparison_batch = compare_runtime_cycle_shadow_fills(result, market_data, config)

    assert comparison_batch.missing_market_data_count == 1
    comparison = comparison_batch.comparisons[0]
    assert comparison.status == ShadowFillStatus.MISSING_MARKET_DATA
    assert comparison.would_fill is False
