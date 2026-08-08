from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime

import pandas as pd
import pytest

from swingmachine.mps_backtest import run_mps_backtest
from swingmachine.mps_config import load_mps_config
from swingmachine.mps_contracts import (
    CorporateActionRecord,
    MpsCorporateActionType,
    MpsVariant,
)


def _feature_panel() -> pd.DataFrame:
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
        }
    )


def _regime(panel: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {"session_date": panel["session_date"], "regime_multiplier": [1.0] * len(panel)}
    )


def _fingerprint(result: object) -> str:
    payload = result.model_dump(mode="json")  # type: ignore[attr-defined]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def test_signal_at_close_never_fills_on_same_close_and_rank_exit_uses_next_open() -> None:
    panel = _feature_panel()
    result = run_mps_backtest(
        panel,
        _regime(panel),
        load_mps_config(),
        MpsVariant.B0_RANK_ONLY,
        data_version_hash="synthetic",
    )
    entry = next(event for event in result.audit_events if event["event"] == "ENTRY_FILLED")
    assert entry["session_date"] == panel.loc[1, "session_date"].date().isoformat()
    assert result.trades[0].exit_session == panel.loc[3, "session_date"].date()
    assert result.trades[0].exit_reason == "MOMENTUM_DETERIORATION"


def test_position_entered_at_open_is_exposed_to_same_session_stop() -> None:
    panel = _feature_panel()
    panel.loc[1, "low"] = 94.0
    result = run_mps_backtest(
        panel,
        _regime(panel),
        load_mps_config(),
        MpsVariant.B0_RANK_ONLY,
        data_version_hash="synthetic",
    )
    assert result.trades[0].entry_session == result.trades[0].exit_session
    assert result.trades[0].exit_reason == "STOP_INTRADAY"


def test_replaying_same_baseline_is_byte_stable() -> None:
    panel = _feature_panel()
    first = run_mps_backtest(
        panel,
        _regime(panel),
        load_mps_config(),
        MpsVariant.B4_FULL_MPS1,
        data_version_hash="synthetic",
    )
    second = run_mps_backtest(
        panel,
        _regime(panel),
        load_mps_config(),
        MpsVariant.B4_FULL_MPS1,
        data_version_hash="synthetic",
    )
    assert _fingerprint(first) == _fingerprint(second)


def test_common_lifecycle_makes_entry_mask_the_only_variant_difference() -> None:
    panel = _feature_panel()
    results = [
        run_mps_backtest(
            panel,
            _regime(panel),
            load_mps_config(),
            variant,
            data_version_hash="synthetic",
            common_lifecycle_policy=True,
        )
        for variant in (
            MpsVariant.B0_RANK_ONLY,
            MpsVariant.B1_MOMENTUM_TREND,
            MpsVariant.B3_MOMENTUM_BREAKOUT,
        )
    ]

    trades = [result.trades[0] for result in results]
    comparable = [trade.model_dump(mode="json", exclude={"variant"}) for trade in trades]
    assert comparable[0] == comparable[1] == comparable[2]


def test_research_dividend_is_non_spendable_until_trade_closes() -> None:
    panel = _feature_panel()
    action = CorporateActionRecord(
        event_time=datetime(2026, 1, 6, tzinfo=UTC),
        available_at=datetime(2026, 1, 6, tzinfo=UTC),
        source_version="synthetic",
        source_record_id="dividend",
        security_id="SEC-AAA",
        action_type=MpsCorporateActionType.CASH_DIVIDEND,
        effective_date=date(2026, 1, 6),
        payment_date=date(2026, 1, 6),
        cash_dividend_per_share=1.0,
    )
    without_dividend = run_mps_backtest(
        panel,
        _regime(panel),
        load_mps_config(),
        MpsVariant.B1_MOMENTUM_TREND,
        data_version_hash="synthetic",
        common_lifecycle_policy=True,
    )
    with_dividend = run_mps_backtest(
        panel,
        _regime(panel),
        load_mps_config(),
        MpsVariant.B1_MOMENTUM_TREND,
        data_version_hash="synthetic",
        corporate_actions=(action,),
        common_lifecycle_policy=True,
        research_ex_date_dividends=True,
    )

    trade = with_dividend.trades[0]
    expected_dividend = trade.entry_quantity * 1.0
    assert trade.net_pnl - without_dividend.trades[0].net_pnl == pytest.approx(expected_dividend)
    accrual = next(
        event
        for event in with_dividend.audit_events
        if event["event"] == "DIVIDEND_ACCRUED_NON_SPENDABLE"
    )
    assert accrual["amount"] == pytest.approx(expected_dividend)


def test_unresolved_terminal_position_closes_at_last_close() -> None:
    panel = _feature_panel()
    panel["is_delisted"] = [False, False, True, False]

    result = run_mps_backtest(
        panel,
        _regime(panel),
        load_mps_config(),
        MpsVariant.B1_MOMENTUM_TREND,
        data_version_hash="synthetic",
        common_lifecycle_policy=True,
        force_unresolved_delisting_last_close=True,
    )

    assert result.trades[0].exit_session == panel.loc[2, "session_date"].date()
    assert result.trades[0].exit_reason == "UNRESOLVED_DELISTING_LAST_CLOSE"
