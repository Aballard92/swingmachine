from __future__ import annotations

from datetime import datetime

from swingmachine.broker import PaperBrokerAdapter
from swingmachine.config import load_strategy_config
from swingmachine.entries import build_setup_snapshot, make_entry_order_intent
from swingmachine.enums import BrokerOrderStatus, OrderIntentStatus, PatternType
from swingmachine.order_intents import OrderIntentService
from swingmachine.storage import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)


def _services() -> tuple[OrderIntentService, PaperBrokerAdapter]:
    engine = create_database_engine()
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    return OrderIntentService(session_factory), PaperBrokerAdapter(session_factory)


def _entry_intent(setup_id: str, *, symbol: str = "AAA"):
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    setup = build_setup_snapshot(
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
    return make_entry_order_intent(
        setup,
        quantity=10,
        strategy_id=config.strategy.id,
        config_hash=config.config_hash(),
        created_at=datetime(2026, 4, 23, 16, 10),
        expires_at=datetime(2026, 4, 28, 16, 0),
    )


def test_submit_order_intent_creates_broker_order_and_marks_intent_active() -> None:
    order_service, broker_adapter = _services()
    intent = _entry_intent("setup-broker-1")

    assert order_service.submit_intent(intent).accepted is True
    result = broker_adapter.submit_order_intent(intent)

    assert result.accepted is True
    assert result.reused_existing is False
    assert result.order is not None
    assert result.order.symbol == intent.symbol
    assert result.order.status == BrokerOrderStatus.OPEN
    assert order_service.get_intent_status(intent.intent_id) == OrderIntentStatus.ACTIVE
    assert (
        order_service.get_intent(intent.intent_id).broker_order_id == result.order.broker_order_id
    )


def test_submit_order_intent_is_idempotent_per_intent_id() -> None:
    order_service, broker_adapter = _services()
    intent = _entry_intent("setup-broker-1")

    assert order_service.submit_intent(intent).accepted is True
    first = broker_adapter.submit_order_intent(intent)
    second = broker_adapter.submit_order_intent(intent)

    assert first.order is not None
    assert second.order is not None
    assert second.reused_existing is True
    assert first.order.broker_order_id == second.order.broker_order_id
    assert len(broker_adapter.list_open_orders()) == 1


def test_cancel_order_updates_broker_and_intent_status() -> None:
    order_service, broker_adapter = _services()
    intent = _entry_intent("setup-broker-1")

    assert order_service.submit_intent(intent).accepted is True
    submission = broker_adapter.submit_order_intent(intent)
    broker_order_id = submission.order.broker_order_id

    cancelled = broker_adapter.cancel_order(broker_order_id)

    assert cancelled.cancelled is True
    assert cancelled.order is not None
    assert cancelled.order.status == BrokerOrderStatus.CANCELLED
    assert order_service.get_intent_status(intent.intent_id) == OrderIntentStatus.CANCELLED
    assert broker_adapter.list_open_orders() == ()


def test_update_order_status_propagates_terminal_state_to_intent() -> None:
    order_service, broker_adapter = _services()
    intent = _entry_intent("setup-broker-1")

    assert order_service.submit_intent(intent).accepted is True
    submission = broker_adapter.submit_order_intent(intent)

    updated = broker_adapter.update_order_status(
        submission.order.broker_order_id,
        status=BrokerOrderStatus.FILLED,
    )

    assert updated.status == BrokerOrderStatus.FILLED
    assert order_service.get_intent_status(intent.intent_id) == OrderIntentStatus.FILLED
    assert broker_adapter.list_open_orders() == ()


def test_adapter_is_restart_safe_on_same_persistent_store() -> None:
    engine = create_database_engine()
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    order_service = OrderIntentService(session_factory)
    first_adapter = PaperBrokerAdapter(session_factory)
    second_adapter = PaperBrokerAdapter(session_factory)
    intent = _entry_intent("setup-broker-1")

    assert order_service.submit_intent(intent).accepted is True
    first = first_adapter.submit_order_intent(intent)
    second = second_adapter.submit_order_intent(intent)

    assert first.order is not None
    assert second.order is not None
    assert second.reused_existing is True
    assert first.order.broker_order_id == second.order.broker_order_id
    assert len(second_adapter.list_open_orders()) == 1


def test_submit_unknown_intent_is_rejected() -> None:
    _, broker_adapter = _services()
    intent = _entry_intent("setup-broker-1")

    result = broker_adapter.submit_order_intent(intent)

    assert result.accepted is False
    assert result.reason == "UNKNOWN_INTENT"
