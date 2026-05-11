from __future__ import annotations

import pytest

from swingmachine.config import load_strategy_config
from swingmachine.contracts import ManagedPosition
from swingmachine.enums import OrderReason, RegimeState
from swingmachine.exits import evaluate_exit_position


def _position(
    *,
    highest_high_since_entry: float = 103.0,
    bars_since_entry: int = 3,
    regular_closes_until_earnings_event: int | None = None,
) -> ManagedPosition:
    return ManagedPosition(
        symbol="AAA",
        quantity=25,
        entry_fill_price=100.0,
        atr_at_entry=2.0,
        current_stop=95.0,
        highest_high_since_entry=highest_high_since_entry,
        bars_since_entry=bars_since_entry,
        regular_closes_until_earnings_event=regular_closes_until_earnings_event,
    )


def test_evaluate_exit_position_activates_trailing_stop_in_risk_on() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")

    evaluation = evaluate_exit_position(
        _position(),
        atr_14=2.0,
        regime_state=RegimeState.RISK_ON,
        config=config,
    )

    assert evaluation.trailing_active is True
    assert evaluation.effective_trailing_multiple == pytest.approx(2.5)
    assert evaluation.updated_stop == pytest.approx(98.0)
    assert evaluation.progress_atr == pytest.approx(1.5)
    assert evaluation.should_submit_exit_intent is False
    assert evaluation.discretionary_exit_reasons == ()


def test_risk_off_trailing_stop_is_tighter_than_risk_on() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    position = _position(highest_high_since_entry=106.0)

    risk_on = evaluate_exit_position(
        position,
        atr_14=2.0,
        regime_state=RegimeState.RISK_ON,
        config=config,
    )
    risk_off = evaluate_exit_position(
        position,
        atr_14=2.0,
        regime_state=RegimeState.RISK_OFF,
        config=config,
    )

    assert risk_on.updated_stop == pytest.approx(101.0)
    assert risk_off.updated_stop == pytest.approx(102.5)
    assert risk_off.updated_stop > risk_on.updated_stop


def test_time_stop_generates_exit_intent_after_insufficient_progress() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")

    evaluation = evaluate_exit_position(
        _position(highest_high_since_entry=100.8, bars_since_entry=10),
        atr_14=2.0,
        regime_state=RegimeState.RISK_ON,
        config=config,
    )

    assert evaluation.trailing_active is False
    assert evaluation.time_stop_triggered is True
    assert evaluation.progress_atr == pytest.approx(0.4)
    assert evaluation.should_submit_exit_intent is True
    assert evaluation.discretionary_exit_reasons == (OrderReason.TIME_EXIT,)


def test_earnings_exit_uses_regular_close_countdown() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")

    evaluation = evaluate_exit_position(
        _position(regular_closes_until_earnings_event=1),
        atr_14=2.0,
        regime_state=RegimeState.RISK_ON,
        config=config,
    )

    assert evaluation.earnings_exit_triggered is True
    assert evaluation.should_submit_exit_intent is True
    assert evaluation.discretionary_exit_reasons == (OrderReason.EARNINGS_EXIT,)


def test_earnings_exit_is_suppressed_when_holds_are_allowed() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    hold_through_config = config.model_copy(
        update={"events": config.events.model_copy(update={"allow_holding_through_earnings": True})}
    )

    evaluation = evaluate_exit_position(
        _position(regular_closes_until_earnings_event=1),
        atr_14=2.0,
        regime_state=RegimeState.RISK_ON,
        config=hold_through_config,
    )

    assert evaluation.earnings_exit_triggered is False
    assert evaluation.should_submit_exit_intent is False
    assert evaluation.discretionary_exit_reasons == ()


def test_trailing_stop_never_loosens_existing_stop() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    position = _position(highest_high_since_entry=103.0).model_copy(
        update={"current_stop": 101.0}
    )

    evaluation = evaluate_exit_position(
        position,
        atr_14=2.0,
        regime_state=RegimeState.RISK_ON,
        config=config,
    )

    assert evaluation.trailing_active is True
    assert evaluation.updated_stop == pytest.approx(101.0)


def test_exit_evaluation_rejects_non_positive_atr() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")

    with pytest.raises(ValueError, match="atr_14"):
        evaluate_exit_position(
            _position(),
            atr_14=0.0,
            regime_state=RegimeState.RISK_ON,
            config=config,
        )


def test_time_and_earnings_exit_reasons_can_stack() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")

    evaluation = evaluate_exit_position(
        _position(
            highest_high_since_entry=100.8,
            bars_since_entry=10,
            regular_closes_until_earnings_event=1,
        ),
        atr_14=2.0,
        regime_state=RegimeState.RISK_ON,
        config=config,
    )

    assert evaluation.time_stop_triggered is True
    assert evaluation.earnings_exit_triggered is True
    assert evaluation.should_submit_exit_intent is True
    assert evaluation.discretionary_exit_reasons == (
        OrderReason.EARNINGS_EXIT,
        OrderReason.TIME_EXIT,
    )


def test_trailing_disabled_leaves_stop_unchanged() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    no_trailing = config.model_copy(
        update={
            "stops": config.stops.model_copy(
                update={
                    "trailing": config.stops.trailing.model_copy(update={"enabled": False})
                }
            )
        }
    )

    evaluation = evaluate_exit_position(
        _position(highest_high_since_entry=110.0),
        atr_14=2.0,
        regime_state=RegimeState.RISK_ON,
        config=no_trailing,
    )

    assert evaluation.trailing_active is False
    assert evaluation.effective_trailing_multiple is None
    assert evaluation.updated_stop == pytest.approx(95.0)
