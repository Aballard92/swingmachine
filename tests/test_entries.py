from __future__ import annotations

from datetime import datetime

import pytest

from swingmachine.config import load_strategy_config
from swingmachine.contracts import ProtectedPosition
from swingmachine.entries import (
    build_setup_snapshot,
    make_entry_order_intent,
    plan_entry,
    portfolio_heat,
)
from swingmachine.enums import PatternType, RegimeState


def test_build_setup_snapshot_uses_entry_and_stop_formulas() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    snapshot = build_setup_snapshot(
        {
            "symbol": "AAA",
            "session_date": "2026-04-23",
            "pattern_type": PatternType.PULLBACK.value,
            "setup_id": "setup-1",
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

    assert snapshot.entry_trigger == 100.2
    assert snapshot.entry_limit == 101.7
    assert snapshot.initial_stop == 93.8
    assert snapshot.per_share_risk == pytest.approx(6.4)


def test_plan_entry_sizes_order_and_builds_order_intent() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    snapshot = build_setup_snapshot(
        {
            "symbol": "AAA",
            "session_date": "2026-04-23",
            "pattern_type": PatternType.PULLBACK.value,
            "setup_id": "setup-1",
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
    created_at = datetime(2026, 4, 23, 16, 10)
    expires_at = datetime(2026, 4, 28, 16, 0)

    plan = plan_entry(
        snapshot,
        config,
        regime_state=RegimeState.RISK_ON,
        equity=100_000.0,
        open_positions=(
            ProtectedPosition(
                symbol="MSFT",
                quantity=10,
                entry_reference_price=300.0,
                protective_stop=290.0,
                sector="TECH",
            ),
        ),
        sector="TECH",
        created_at=created_at,
        expires_at=expires_at,
    )

    assert plan.approved is True
    assert plan.base_risk_budget == 300.0
    assert plan.regime_risk_budget == 300.0
    assert plan.quantity == 46
    assert plan.shares_from_risk == 46
    assert plan.shares_from_notional == 79
    assert round(plan.projected_portfolio_heat, 6) == round(
        (100.0 + 46 * snapshot.per_share_risk) / 100_000.0, 6
    )
    assert plan.order_intent is not None
    assert plan.order_intent.stop_price == snapshot.entry_trigger
    assert plan.order_intent.limit_price == snapshot.entry_limit


def test_plan_entry_rejects_duplicate_and_heat_breaches() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    snapshot = build_setup_snapshot(
        {
            "symbol": "AAA",
            "session_date": "2026-04-23",
            "pattern_type": PatternType.TIGHT_BASE.value,
            "setup_id": "setup-2",
            "setup_start_date": "2026-04-16",
            "setup_end_date": "2026-04-23",
            "setup_high": 50.0,
            "setup_low": 48.0,
            "setup_high_date": "2026-04-18",
            "setup_low_date": "2026-04-21",
            "atr_14": 1.0,
            "setup_valid": True,
        },
        config,
    )
    open_positions = (
        ProtectedPosition(
            symbol="IBM",
            quantity=150,
            entry_reference_price=100.0,
            protective_stop=88.0,
            sector="TECH",
        ),
    )

    plan = plan_entry(
        snapshot,
        config,
        regime_state=RegimeState.RISK_ON,
        equity=100_000.0,
        pending_symbols=("AAA",),
        open_positions=open_positions,
        submitted_today_risk_amount=900.0,
        sector="TECH",
    )

    assert plan.approved is False
    assert "PENDING_ENTRY_EXISTS" in plan.reject_reasons
    assert "PORTFOLIO_HEAT_LIMIT" in plan.reject_reasons
    assert "DAILY_NEW_RISK_LIMIT" in plan.reject_reasons
    assert "SECTOR_GROSS_LIMIT" in plan.reject_reasons


def test_make_entry_order_intent_is_deterministic() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    snapshot = build_setup_snapshot(
        {
            "symbol": "AAA",
            "session_date": "2026-04-23",
            "pattern_type": PatternType.PULLBACK.value,
            "setup_id": "setup-1",
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
    created_at = datetime(2026, 4, 23, 16, 10)
    expires_at = datetime(2026, 4, 28, 16, 0)

    first = make_entry_order_intent(
        snapshot,
        quantity=10,
        strategy_id=config.strategy.id,
        config_hash=config.config_hash(),
        created_at=created_at,
        expires_at=expires_at,
    )
    second = make_entry_order_intent(
        snapshot,
        quantity=10,
        strategy_id=config.strategy.id,
        config_hash=config.config_hash(),
        created_at=created_at,
        expires_at=expires_at,
    )

    assert first.intent_id == second.intent_id
    assert first.dedupe_key == second.dedupe_key


def test_portfolio_heat_matches_spec_formula() -> None:
    heat = portfolio_heat(
        (
            ProtectedPosition(
                symbol="AAA",
                quantity=10,
                entry_reference_price=100.0,
                protective_stop=95.0,
            ),
            ProtectedPosition(
                symbol="BBB",
                quantity=20,
                entry_reference_price=50.0,
                protective_stop=48.0,
            ),
        ),
        equity=10_000.0,
    )

    assert heat == ((100.0 - 95.0) * 10 + (50.0 - 48.0) * 20) / 10_000.0
