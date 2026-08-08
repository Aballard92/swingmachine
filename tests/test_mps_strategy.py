from __future__ import annotations

from datetime import UTC, date, datetime

import numpy as np
import pandas as pd
import pytest

from swingmachine.mps_config import load_mps_config
from swingmachine.mps_contracts import (
    CorporateActionRecord,
    MpsCandidate,
    MpsCorporateActionType,
    MpsFill,
    MpsPosition,
    MpsVariant,
)
from swingmachine.mps_execution import simulate_entry, simulate_sell_stop
from swingmachine.mps_features import compute_mps_features, seeded_wilder_atr
from swingmachine.mps_portfolio import MpsPortfolioLedger
from swingmachine.mps_risk import plan_entry, post_fill_quantity
from swingmachine.mps_signals import select_candidates, updated_trailing_stop, variant_signal_mask


def _candidate() -> MpsCandidate:
    return MpsCandidate(
        security_id="SEC-AAA",
        ticker="AAA",
        signal_session=date(2026, 1, 2),
        variant=MpsVariant.B4_FULL_MPS1,
        momentum_rank=0.95,
        adv20_dollars=100_000_000,
        structure_stop=95.0,
        signal_close=100.0,
        signal_atr20=2.0,
        sector="Technology",
    )


def _position(quantity: int = 10) -> MpsPosition:
    return MpsPosition(
        security_id="SEC-AAA",
        ticker="AAA",
        quantity=quantity,
        entry_price=100.0,
        initial_stop=95.0,
        active_stop=95.0,
        initial_risk_per_share=5.0,
        sector="Technology",
        entry_session=date(2026, 1, 2),
        highest_close_since_entry=100.0,
        maximum_high_since_entry=100.0,
    )


def test_seeded_wilder_atr_matches_hand_calculation() -> None:
    frame = pd.DataFrame(
        {
            "high": [11.0, 12.0, 13.0, 14.0],
            "low": [9.0, 9.0, 10.0, 12.0],
            "close": [10.0, 11.0, 12.0, 13.0],
        }
    )
    result = seeded_wilder_atr(frame, 3)
    assert np.isnan(result.iloc[1])
    assert result.iloc[2] == pytest.approx((2.0 + 3.0 + 3.0) / 3.0)
    assert result.iloc[3] == pytest.approx((2 * result.iloc[2] + 2.0) / 3.0)


def test_momentum_first_valid_dates_and_eligible_only_average_ties() -> None:
    config = load_mps_config()
    dates = pd.bdate_range("2024-01-01", periods=260)
    rows = []
    for ticker, slope, eligible in (("AAA", 0.2, True), ("BBB", 0.1, True), ("CCC", 0.3, False)):
        for index, session in enumerate(dates):
            close = 100 + slope * index
            rows.append(
                {
                    "security_id": f"SEC-{ticker}",
                    "ticker": ticker,
                    "session_date": session,
                    "open": close,
                    "high": close + 1,
                    "low": close - 1,
                    "close": close,
                    "volume": 1_000_000,
                    "total_return_adjusted_close": close,
                    "security_type": "common_stock",
                    "primary_exchange": "NYSE",
                    "country_of_primary_listing": "US",
                    "sector": "Technology",
                    "is_tradable": eligible,
                    "is_halted": False,
                    "is_delisted": False,
                    "shares_outstanding": 100_000_000,
                }
            )
    features = compute_mps_features(pd.DataFrame(rows), config)
    aaa = features[features["ticker"] == "AAA"].reset_index(drop=True)
    assert pd.isna(aaa.loc[125, "mom_6m"])
    assert pd.notna(aaa.loc[126, "mom_6m"])
    assert pd.isna(aaa.loc[251, "mom_12m"])
    assert pd.notna(aaa.loc[252, "mom_12m"])
    last = features[features["session_date"] == dates[-1]]
    assert pd.isna(last.loc[last["ticker"] == "CCC", "momentum_rank"]).all()
    assert set(last.loc[last["ticker"].isin(["AAA", "BBB"]), "momentum_rank"]) == {0.5, 1.0}


def test_unavailable_shares_fail_closed_before_market_cap_and_momentum_rank() -> None:
    config = load_mps_config()
    dates = pd.bdate_range("2024-01-01", periods=260)
    rows = []
    for index, session in enumerate(dates):
        close = 100.0 + index * 0.2
        rows.append(
            {
                "security_id": "SEC-AAA",
                "ticker": "AAA",
                "session_date": session,
                "open": close,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000_000,
                "total_return_adjusted_close": close,
                "security_type": "common_stock",
                "primary_exchange": "NYSE",
                "country_of_primary_listing": "US",
                "sector": "Technology",
                "is_tradable": True,
                "is_halted": False,
                "is_delisted": False,
                "shares_outstanding": 100_000_000,
                "shares_data_available": False,
            }
        )

    features = compute_mps_features(pd.DataFrame(rows), config)

    assert not features["shares_data_available"].any()
    assert features["market_cap"].isna().all()
    assert not features["eligible_universe"].any()
    assert features["momentum_rank"].isna().all()


def test_b0_through_b4_masks_apply_incremental_conditions() -> None:
    config = load_mps_config()
    row = pd.DataFrame(
        {
            "eligible_universe": [True],
            "momentum_rank": [0.95],
            "trend_qualified": [True],
            "pullback_depth_atr": [1.0],
            "recent_sma20_touch": [True],
            "close_above_prior_high": [True],
            "close_location_value": [0.8],
            "close": [101.0],
            "sma50": [90.0],
            "prior_high20": [100.0],
        }
    )
    assert all(bool(variant_signal_mask(row, variant, config).iloc[0]) for variant in MpsVariant)
    row.loc[0, "recent_sma20_touch"] = False
    assert bool(variant_signal_mask(row, MpsVariant.B1_MOMENTUM_TREND, config).iloc[0])
    assert not bool(variant_signal_mask(row, MpsVariant.B2_MOMENTUM_PULLBACK, config).iloc[0])


def test_candidate_ordering_and_no_pyramiding() -> None:
    config = load_mps_config()
    frame = pd.DataFrame(
        {
            "security_id": ["2", "1", "3"],
            "ticker": ["BBB", "AAA", "CCC"],
            "session_date": pd.to_datetime(["2026-01-02"] * 3),
            "eligible_universe": [True] * 3,
            "momentum_rank": [0.95] * 3,
            "adv20_dollars": [100.0, 100.0, 90.0],
            "trend_qualified": [True] * 3,
            "pullback_depth_atr": [1.0] * 3,
            "recent_sma20_touch": [True] * 3,
            "close_above_prior_high": [True] * 3,
            "close_location_value": [0.8] * 3,
            "close": [100.0] * 3,
            "sma50": [90.0] * 3,
            "prior_high20": [99.0] * 3,
            "structure_stop": [95.0] * 3,
            "atr20": [2.0] * 3,
            "sector": ["Technology"] * 3,
        }
    )
    candidates = select_candidates(
        frame, MpsVariant.B4_FULL_MPS1, config, held_security_ids=frozenset({"2"})
    )
    assert [candidate.ticker for candidate in candidates] == ["AAA", "CCC"]


def test_entry_gap_guard_and_open_below_structure_stop_cancel() -> None:
    config = load_mps_config()
    assert simulate_entry(_candidate(), 101.1, config).reason_code == "ENTRY_GAP_GUARD"
    assert simulate_entry(_candidate(), 95.0, config).reason_code == "ENTRY_GAP_GUARD"
    close_stop = _candidate().model_copy(update={"signal_close": 95.5})
    assert simulate_entry(close_stop, 95.0, config).reason_code == "OPEN_AT_OR_BELOW_STRUCTURE_STOP"


def test_gap_stop_fills_from_open_and_intraday_from_stop_after_cost() -> None:
    config = load_mps_config()
    gap = simulate_sell_stop(90.0, 89.0, 95.0, config)
    intraday = simulate_sell_stop(100.0, 94.0, 95.0, config)
    assert gap.reference_price == 90.0 and gap.fill_price < 90.0
    assert intraday.reference_price == 95.0 and intraday.fill_price < 95.0


def test_risk_plan_uses_entry_cap_and_post_fill_trim() -> None:
    config = load_mps_config()
    plan = plan_entry(
        _candidate(),
        config,
        equity=100_000,
        cash=100_000,
        regime_multiplier=1.0,
        positions=(),
        current_prices={},
    )
    assert plan.approved
    assert plan.entry_cap == 101.0
    retained, trim = post_fill_quantity(plan, 105.0, config)
    assert retained <= plan.quantity
    assert trim == plan.quantity - retained


def test_trailing_stop_never_moves_down_and_requires_one_r() -> None:
    config = load_mps_config()
    position = _position()
    assert updated_trailing_stop(position, 104.9, 2.0, config) == 95.0
    raised = updated_trailing_stop(position, 110.0, 2.0, config)
    assert raised == 105.0
    position = position.model_copy(
        update={"active_stop": 106.0, "highest_close_since_entry": 112.0}
    )
    assert updated_trailing_stop(position, 108.0, 2.0, config) == 107.0


def test_split_preserves_equity_and_adjusts_quantity_basis_and_stops() -> None:
    ledger = MpsPortfolioLedger(99_000.0)
    fill = MpsFill(
        security_id="SEC-AAA",
        session_date=date(2026, 1, 2),
        side="BUY",
        quantity=10,
        reference_price=100.0,
        fill_price=100.0,
        cost_bps=0.0,
        reason_code="ENTRY",
    )
    ledger.book_entry(fill, _position())
    before = ledger.equity({"SEC-AAA": 100.0})
    action = CorporateActionRecord(
        event_time=datetime(2026, 1, 5, tzinfo=UTC),
        available_at=datetime(2026, 1, 5, tzinfo=UTC),
        source_version="v1",
        source_record_id="split",
        security_id="SEC-AAA",
        action_type=MpsCorporateActionType.SPLIT,
        effective_date=date(2026, 1, 5),
        split_ratio=2.0,
    )
    ledger.apply_corporate_action(action)
    after = ledger.equity({"SEC-AAA": 50.0})
    assert before == after
    assert ledger.positions["SEC-AAA"].quantity == 20
    assert ledger.positions["SEC-AAA"].active_stop == 47.5


def test_dividend_is_receivable_then_cash_on_payment_date() -> None:
    ledger = MpsPortfolioLedger(99_000.0)
    fill = MpsFill(
        security_id="SEC-AAA",
        session_date=date(2026, 1, 2),
        side="BUY",
        quantity=10,
        reference_price=100.0,
        fill_price=100.0,
        cost_bps=0.0,
        reason_code="ENTRY",
    )
    ledger.book_entry(fill, _position())
    action = CorporateActionRecord(
        event_time=datetime(2026, 1, 5, tzinfo=UTC),
        available_at=datetime(2026, 1, 5, tzinfo=UTC),
        source_version="v1",
        source_record_id="dividend",
        security_id="SEC-AAA",
        action_type=MpsCorporateActionType.CASH_DIVIDEND,
        effective_date=date(2026, 1, 5),
        payment_date=date(2026, 1, 10),
        cash_dividend_per_share=1.0,
    )
    cash = ledger.cash
    ledger.apply_corporate_action(action)
    ledger.settle_dividends(date(2026, 1, 9))
    assert ledger.cash == cash
    ledger.settle_dividends(date(2026, 1, 10))
    assert ledger.cash == cash + 10.0
