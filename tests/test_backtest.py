from __future__ import annotations

import pandas as pd
import pytest

from swingmachine.analytics import regime_segmented_trade_stats, summarize_backtest
from swingmachine.backtest import run_backtest
from swingmachine.config import load_strategy_config
from swingmachine.contracts import BacktestTrade
from swingmachine.enums import OrderReason, PatternType, RegimeState


def _regime_frame(dates: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "session_date": dates,
            "regime_state": [RegimeState.RISK_ON.value] * len(dates),
            "entry_enabled": [True] * len(dates),
        }
    )


def _base_rows(dates: pd.DatetimeIndex) -> dict[str, list[object]]:
    return {
        "symbol": ["AAA"] * len(dates),
        "session_date": list(dates),
        "pattern_type": [PatternType.PULLBACK.value] + [None] * (len(dates) - 1),
        "setup_id": ["setup-backtest-1"] + [None] * (len(dates) - 1),
        "setup_start_date": [dates[0]] + [pd.NaT] * (len(dates) - 1),
        "setup_end_date": [dates[0]] + [pd.NaT] * (len(dates) - 1),
        "setup_high": [100.0] + [float("nan")] * (len(dates) - 1),
        "setup_low": [94.0] + [float("nan")] * (len(dates) - 1),
        "setup_high_date": [dates[0]] + [pd.NaT] * (len(dates) - 1),
        "setup_low_date": [dates[0]] + [pd.NaT] * (len(dates) - 1),
        "setup_valid": [True] + [False] * (len(dates) - 1),
        "is_candidate": [True] + [False] * (len(dates) - 1),
        "entry_enabled": [True] * len(dates),
        "split_adj_close": [100.0, 100.5, 101.2, 101.1][: len(dates)],
        "ma50": [90.0] * len(dates),
        "ma200": [80.0] * len(dates),
        "ma200_slope_pct20": [0.02] * len(dates),
        "dist_to_52w_high": [0.03] * len(dates),
        "raw_open": [99.8, 100.3, 101.2, 101.0][: len(dates)],
        "raw_high": [100.2, 101.0, 101.5, 101.3][: len(dates)],
        "raw_low": [99.5, 99.7, 100.8, 100.9][: len(dates)],
        "raw_close": [100.0, 100.5, 101.2, 101.1][: len(dates)],
        "raw_volume": [1_000_000_000_000.0] * len(dates),
        "atr_14": [2.0] * len(dates),
        "regular_closes_until_earnings_event": [10, 1, 0, 0][: len(dates)],
        "candidate_score_pct": [1.0, 0.0, 0.0, 0.0][: len(dates)],
        "spread_bps": [0.0] * len(dates),
        "fx_conversion_cost_bps": [0.0] * len(dates),
        "sector": ["TECH"] * len(dates),
    }


def test_run_backtest_is_deterministic_and_generates_earnings_exit_trade() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    dates = pd.bdate_range("2026-04-20", periods=4)
    panel = pd.DataFrame(_base_rows(dates))

    first = run_backtest(panel, _regime_frame(dates), config)
    second = run_backtest(panel, _regime_frame(dates), config)

    assert [trade.model_dump(mode="json") for trade in first.trades] == [
        trade.model_dump(mode="json") for trade in second.trades
    ]
    assert [event.model_dump(mode="json") for event in first.events] == [
        event.model_dump(mode="json") for event in second.events
    ]

    assert len(first.trades) == 1
    trade = first.trades[0]
    assert trade.entry_fill_price == pytest.approx(100.3)
    assert trade.exit_fill_price == pytest.approx(101.0)
    assert trade.entry_reference_price == pytest.approx(100.3)
    assert trade.exit_reference_price == pytest.approx(101.0)
    assert trade.quantity == 46
    assert trade.exit_reason == OrderReason.EARNINGS_EXIT
    assert trade.total_transaction_cost == pytest.approx(0.0, abs=1e-6)
    assert trade.gross_pnl == pytest.approx(32.2)
    assert trade.net_pnl == pytest.approx(32.2)
    assert first.final_equity == pytest.approx(100_032.2)

    summary = summarize_backtest(first)
    assert summary["trade_count"] == 1
    assert summary["win_rate"] == 1.0
    assert summary["gross_pnl"] == pytest.approx(32.2)
    assert summary["net_pnl"] == pytest.approx(32.2)


def test_run_backtest_marks_gap_cancelled_setup_spent_and_does_not_resubmit() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    dates = pd.bdate_range("2026-04-20", periods=3)
    rows = _base_rows(dates)
    rows["setup_valid"] = [True, True, True]
    rows["is_candidate"] = [True, True, True]
    rows["pattern_type"] = [PatternType.PULLBACK.value] * 3
    rows["setup_id"] = ["setup-gap-1"] * 3
    rows["setup_start_date"] = [dates[0]] * 3
    rows["setup_end_date"] = list(dates)
    rows["setup_high"] = [100.0] * 3
    rows["setup_low"] = [94.0] * 3
    rows["setup_high_date"] = [dates[0]] * 3
    rows["setup_low_date"] = [dates[0]] * 3
    rows["raw_open"] = [99.8, 102.0, 100.4]
    rows["raw_high"] = [100.2, 102.5, 101.0]
    rows["raw_low"] = [99.5, 101.9, 100.0]
    rows["raw_close"] = [100.0, 102.1, 100.6]
    rows["split_adj_close"] = [100.0, 102.1, 100.6]
    rows["regular_closes_until_earnings_event"] = [10, 10, 10]
    panel = pd.DataFrame(rows)

    result = run_backtest(panel, _regime_frame(dates), config)

    assert result.trades == ()
    assert result.spent_setup_ids == ("setup-gap-1",)

    submit_events = [event for event in result.events if event.event_type == "ENTRY_SUBMITTED"]
    cancel_events = [event for event in result.events if event.event_type == "ENTRY_CANCELLED"]

    assert len(submit_events) == 1
    assert len(cancel_events) == 1
    assert cancel_events[0].detail == "OPEN_GAP_ABOVE_LIMIT"


def test_regime_segmented_trade_stats_groups_by_entry_regime() -> None:
    trades = (
        BacktestTrade(
            symbol="AAA",
            setup_id="one",
            entry_signal_date=pd.Timestamp("2026-04-20").date(),
            entry_fill_date=pd.Timestamp("2026-04-21").date(),
            entry_reference_price=100.0,
            entry_fill_price=100.0,
            exit_fill_date=pd.Timestamp("2026-04-22").date(),
            exit_reference_price=102.0,
            exit_fill_price=102.0,
            quantity=10,
            entry_regime_state=RegimeState.RISK_ON,
            exit_regime_state=RegimeState.RISK_ON,
            exit_reason=OrderReason.EARNINGS_EXIT,
            bars_held=1,
            initial_stop=95.0,
            final_stop=95.0,
            entry_transaction_cost=0.0,
            exit_transaction_cost=0.0,
            total_transaction_cost=0.0,
            gross_pnl=20.0,
            gross_return=0.02,
            net_pnl=20.0,
            net_return=0.02,
            sector="TECH",
        ),
        BacktestTrade(
            symbol="BBB",
            setup_id="two",
            entry_signal_date=pd.Timestamp("2026-04-20").date(),
            entry_fill_date=pd.Timestamp("2026-04-21").date(),
            entry_reference_price=50.0,
            entry_fill_price=50.0,
            exit_fill_date=pd.Timestamp("2026-04-24").date(),
            exit_reference_price=49.0,
            exit_fill_price=49.0,
            quantity=20,
            entry_regime_state=RegimeState.RISK_OFF,
            exit_regime_state=RegimeState.RISK_OFF,
            exit_reason=OrderReason.INITIAL_STOP,
            bars_held=2,
            initial_stop=48.0,
            final_stop=48.0,
            entry_transaction_cost=0.0,
            exit_transaction_cost=0.0,
            total_transaction_cost=0.0,
            gross_pnl=-20.0,
            gross_return=-0.02,
            net_pnl=-20.0,
            net_return=-0.02,
            sector="FIN",
        ),
    )

    summary = (
        regime_segmented_trade_stats(trades)
        .sort_values("entry_regime_state")
        .reset_index(drop=True)
    )

    assert summary.loc[0, "entry_regime_state"] == RegimeState.RISK_OFF.value
    assert summary.loc[0, "trade_count"] == 1
    assert summary.loc[0, "win_rate"] == 0.0
    assert summary.loc[1, "entry_regime_state"] == RegimeState.RISK_ON.value
    assert summary.loc[1, "gross_pnl"] == pytest.approx(20.0)


def test_run_backtest_applies_execution_cost_model_when_overrides_are_present() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    dates = pd.bdate_range("2026-04-20", periods=4)
    rows = _base_rows(dates)
    rows["raw_volume"] = [10_000.0] * len(dates)
    rows["spread_bps"] = [12.0] * len(dates)
    rows["fx_conversion_cost_bps"] = [8.0] * len(dates)
    panel = pd.DataFrame(rows)

    result = run_backtest(panel, _regime_frame(dates), config)

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.entry_fill_price > trade.entry_reference_price
    assert trade.exit_fill_price < trade.exit_reference_price
    assert trade.total_transaction_cost > 0.0
    assert trade.net_pnl < trade.gross_pnl

    summary = summarize_backtest(result)
    assert summary["total_transaction_cost"] == pytest.approx(trade.total_transaction_cost)
    assert summary["net_pnl"] == pytest.approx(trade.net_pnl)
