from __future__ import annotations

from datetime import datetime

from swingmachine.config import load_strategy_config
from swingmachine.contracts import ProtectedPosition, SetupSnapshot
from swingmachine.entries import build_setup_snapshot
from swingmachine.enums import PatternType, RegimeState
from swingmachine.portfolio_manager import PortfolioManager, reserved_position_from_plan


def _make_setup(
    *,
    symbol: str,
    setup_id: str,
) -> SetupSnapshot:
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
        load_strategy_config("swing_trading_bot_config_template_v2.yaml"),
    )


def test_portfolio_manager_reserves_daily_new_risk_across_batch() -> None:
    base_config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    config = base_config.model_copy(
        update={
            "risk": base_config.risk.model_copy(
                update={
                    "max_new_risk_per_day_pct_equity": 0.005,
                }
            )
        }
    )
    manager = PortfolioManager(config)

    result = manager.plan_ranked_entries(
        (
            _make_setup(symbol="AAA", setup_id="setup-1"),
            _make_setup(symbol="BBB", setup_id="setup-2"),
        ),
        regime_state=RegimeState.RISK_ON,
        equity=100_000.0,
        sector_by_symbol={
            "AAA": "TECH",
            "BBB": "INDUSTRIALS",
        },
        created_at=datetime(2026, 4, 23, 16, 10),
        expires_at=datetime(2026, 4, 24, 16, 0),
    )

    assert result.approved_count == 1
    assert result.rejected_count == 1
    assert result.plans[0].approved is True
    assert result.plans[1].approved is False
    assert "DAILY_NEW_RISK_LIMIT" in result.plans[1].reject_reasons
    assert (
        result.batch_new_risk_amount
        == result.plans[0].setup.per_share_risk * result.plans[0].quantity
    )


def test_portfolio_manager_reserves_sector_exposure_across_approved_entries() -> None:
    base_config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    config = base_config.model_copy(
        update={
            "risk": base_config.risk.model_copy(
                update={
                    "max_sector_pct_equity": 0.09,
                }
            )
        }
    )
    manager = PortfolioManager(config)

    result = manager.plan_ranked_entries(
        (
            _make_setup(symbol="AAA", setup_id="setup-1"),
            _make_setup(symbol="BBB", setup_id="setup-2"),
        ),
        regime_state=RegimeState.RISK_ON,
        equity=100_000.0,
        sector_by_symbol={
            "AAA": "TECH",
            "BBB": "TECH",
        },
        created_at=datetime(2026, 4, 23, 16, 10),
        expires_at=datetime(2026, 4, 24, 16, 0),
    )

    assert result.approved_count == 1
    assert result.plans[0].approved is True
    assert result.plans[1].approved is False
    assert "SECTOR_GROSS_LIMIT" in result.plans[1].reject_reasons


def test_portfolio_manager_treats_approved_entry_as_pending_for_later_same_symbol() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    manager = PortfolioManager(config)

    result = manager.plan_ranked_entries(
        (
            _make_setup(symbol="AAA", setup_id="setup-1"),
            _make_setup(symbol="AAA", setup_id="setup-2"),
        ),
        regime_state=RegimeState.RISK_ON,
        equity=100_000.0,
        created_at=datetime(2026, 4, 23, 16, 10),
        expires_at=datetime(2026, 4, 24, 16, 0),
    )

    assert result.approved_count == 1
    assert result.plans[0].approved is True
    assert result.plans[1].approved is False
    assert "PENDING_ENTRY_EXISTS" in result.plans[1].reject_reasons


def test_reserved_position_from_plan_uses_entry_trigger_and_initial_stop() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    manager = PortfolioManager(config)
    result = manager.plan_ranked_entries(
        (_make_setup(symbol="AAA", setup_id="setup-1"),),
        regime_state=RegimeState.RISK_ON,
        equity=100_000.0,
    )

    reserved = reserved_position_from_plan(result.plans[0], sector="TECH")

    assert reserved.symbol == "AAA"
    assert reserved.entry_reference_price == result.plans[0].setup.entry_trigger
    assert reserved.protective_stop == result.plans[0].setup.initial_stop
    assert reserved.sector == "TECH"


def test_portfolio_manager_rejects_existing_pending_symbol_conflict() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    manager = PortfolioManager(config)

    result = manager.plan_ranked_entries(
        (_make_setup(symbol="AAA", setup_id="setup-1"),),
        regime_state=RegimeState.RISK_ON,
        equity=100_000.0,
        pending_symbols=("AAA",),
        created_at=datetime(2026, 4, 23, 16, 10),
        expires_at=datetime(2026, 4, 24, 16, 0),
    )

    assert result.approved_count == 0
    assert result.rejected_count == 1
    assert "PENDING_ENTRY_EXISTS" in result.plans[0].reject_reasons


def test_portfolio_manager_rejects_existing_open_symbol_conflict() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    manager = PortfolioManager(config)

    result = manager.plan_ranked_entries(
        (_make_setup(symbol="AAA", setup_id="setup-1"),),
        regime_state=RegimeState.RISK_ON,
        equity=100_000.0,
        open_positions=(
            ProtectedPosition(
                symbol="AAA",
                quantity=10,
                entry_reference_price=100.0,
                protective_stop=90.0,
                sector="TECH",
            ),
        ),
        created_at=datetime(2026, 4, 23, 16, 10),
        expires_at=datetime(2026, 4, 24, 16, 0),
    )

    assert result.approved_count == 0
    assert result.rejected_count == 1
    assert "OPEN_POSITION_EXISTS" in result.plans[0].reject_reasons


def test_portfolio_manager_rejects_existing_heat_plus_new_risk_breach() -> None:
    base_config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    config = base_config.model_copy(
        update={
            "risk": base_config.risk.model_copy(
                update={
                    "max_portfolio_heat_pct_equity": 0.01,
                }
            )
        }
    )
    manager = PortfolioManager(config)

    result = manager.plan_ranked_entries(
        (_make_setup(symbol="BBB", setup_id="setup-2"),),
        regime_state=RegimeState.RISK_ON,
        equity=100_000.0,
        open_positions=(
            ProtectedPosition(
                symbol="AAA",
                quantity=90,
                entry_reference_price=100.0,
                protective_stop=90.0,
                sector="TECH",
            ),
        ),
        created_at=datetime(2026, 4, 23, 16, 10),
        expires_at=datetime(2026, 4, 24, 16, 0),
    )

    assert result.approved_count == 0
    assert result.rejected_count == 1
    assert "PORTFOLIO_HEAT_LIMIT" in result.plans[0].reject_reasons
