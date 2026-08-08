from __future__ import annotations

import pandas as pd
import pytest

from swingmachine.mps_backtest import run_mps_backtest
from swingmachine.mps_config import load_mps_config
from swingmachine.mps_contracts import MpsCorporateActionType, MpsVariant
from swingmachine.mps_limitation_screen import (
    aggregate_metrics,
    build_research_actions,
)


def _panel() -> pd.DataFrame:
    dates = pd.bdate_range("2026-01-02", periods=4)
    return pd.DataFrame(
        {
            "security_id": ["SEC-AAA"] * 4,
            "ticker": ["AAA"] * 4,
            "session_date": dates,
            "open": [100.0, 100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0, 103.0],
            "low": [99.0, 99.0, 100.0, 101.0],
            "close": [100.0, 101.0, 102.0, 102.0],
            "momentum_rank": [0.95, 0.95, 0.60, 0.60],
            "sma50": [90.0] * 4,
            "atr20": [2.0] * 4,
            "eligible_universe": [True] * 4,
            "trend_qualified": [True] * 4,
            "pullback_depth_atr": [1.0] * 4,
            "recent_sma20_touch": [True] * 4,
            "close_above_prior_high": [True] * 4,
            "close_location_value": [0.8] * 4,
            "prior_high20": [99.0] * 4,
            "adv20_dollars": [100_000_000.0] * 4,
            "structure_stop": [95.0] * 4,
            "sector": ["Technology"] * 4,
            "is_delisted": [False, False, True, False],
        }
    )


def _regime(panel: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "session_date": panel["session_date"],
            "regime_multiplier": [1.0] * len(panel),
        }
    )


def test_build_research_actions_preserves_split_and_ex_date_dividend() -> None:
    actions = pd.DataFrame(
        {
            "security_id": ["SEC-AAA"],
            "ticker": ["AAA"],
            "trading_date": ["2026-01-05"],
            "event_time": ["2026-01-05T00:00:00Z"],
            "available_at": ["2026-01-05T21:00:00Z"],
            "div_cash": [1.0],
            "split_factor": [2.0],
            "payment_date": [None],
            "source_file_sha256": ["source"],
        }
    )

    records = build_research_actions(
        actions,
        start=pd.Timestamp("2026-01-01").date(),
        end=pd.Timestamp("2026-01-31").date(),
    )

    assert [record.action_type for record in records] == [
        MpsCorporateActionType.CASH_DIVIDEND,
        MpsCorporateActionType.SPLIT,
    ]
    dividend = records[0]
    assert dividend.payment_date == dividend.effective_date


def test_total_loss_scenario_removes_terminal_exit_proceeds() -> None:
    panel = _panel()
    result = run_mps_backtest(
        panel,
        _regime(panel),
        load_mps_config(),
        MpsVariant.B1_MOMENTUM_TREND,
        data_version_hash="synthetic",
        common_lifecycle_policy=True,
        research_ex_date_dividends=True,
        force_unresolved_delisting_last_close=True,
    )

    last_close = aggregate_metrics((result,), "LAST_CLOSE")
    total_loss = aggregate_metrics((result,), "TOTAL_LOSS")
    trade = result.trades[0]

    assert last_close["terminal_trade_count"] == 1
    assert total_loss["net_pnl"] == pytest.approx(
        last_close["net_pnl"] - trade.exit_fill_price * trade.exit_quantity
    )
    assert total_loss["compounded_return"] < last_close["compounded_return"]
