from __future__ import annotations

from datetime import datetime

from swingmachine.config import load_strategy_config
from swingmachine.contracts import BrokerOrderSnapshot
from swingmachine.entries import build_setup_snapshot, make_entry_order_intent
from swingmachine.enums import (
    BrokerOrderStatus,
    OrderIntentStatus,
    OrderSide,
    OrderType,
    PatternType,
)
from swingmachine.order_intents import OrderIntentService
from swingmachine.reconciliation import ReconciliationService
from swingmachine.storage import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)


def _services() -> tuple[OrderIntentService, ReconciliationService]:
    engine = create_database_engine()
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    return OrderIntentService(session_factory), ReconciliationService(session_factory)


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


def _broker_snapshot(
    intent, *, broker_order_id: str, status: BrokerOrderStatus
) -> BrokerOrderSnapshot:
    return BrokerOrderSnapshot(
        broker_order_id=broker_order_id,
        symbol=intent.symbol,
        side=OrderSide.BUY,
        order_type=OrderType.STOP_LIMIT,
        quantity=float(intent.quantity),
        stop_price=intent.stop_price,
        limit_price=intent.limit_price,
        status=status,
        created_at=intent.created_at,
    )


def test_reconcile_recovers_generated_intent_from_matching_broker_order() -> None:
    order_service, reconciliation_service = _services()
    intent = _entry_intent("setup-reconcile-1")

    assert order_service.submit_intent(intent).accepted is True

    result = reconciliation_service.reconcile_orders(
        [
            _broker_snapshot(
                intent,
                broker_order_id="broker-1",
                status=BrokerOrderStatus.OPEN,
            )
        ]
    )

    recovered = order_service.get_intent(intent.intent_id)
    assert recovered is not None
    assert recovered.broker_order_id == "broker-1"
    assert order_service.get_intent_status(intent.intent_id) == OrderIntentStatus.ACTIVE
    assert result.recovered_intent_ids == (intent.intent_id,)
    assert order_service.pending_entry_symbols() == ("AAA",)


def test_reconcile_terminal_broker_status_closes_local_intent() -> None:
    order_service, reconciliation_service = _services()
    intent = _entry_intent("setup-reconcile-1")

    assert order_service.submit_intent(intent).accepted is True
    order_service.mark_submitted(intent.intent_id, broker_order_id="broker-1")

    result = reconciliation_service.reconcile_orders(
        [
            _broker_snapshot(
                intent,
                broker_order_id="broker-1",
                status=BrokerOrderStatus.CANCELLED,
            )
        ]
    )

    assert result.terminalized_intent_ids == (intent.intent_id,)
    assert order_service.get_intent_status(intent.intent_id) == OrderIntentStatus.CANCELLED
    assert order_service.pending_entry_symbols() == ()


def test_reconcile_reports_missing_active_broker_order_without_silent_status_change() -> None:
    order_service, reconciliation_service = _services()
    intent = _entry_intent("setup-reconcile-1")

    assert order_service.submit_intent(intent).accepted is True
    order_service.mark_submitted(intent.intent_id, broker_order_id="broker-1")

    result = reconciliation_service.reconcile_orders([])

    assert result.missing_broker_order_intent_ids == (intent.intent_id,)
    assert order_service.get_intent_status(intent.intent_id) == OrderIntentStatus.ACTIVE


def test_recovery_after_reconcile_blocks_duplicate_entry_creation() -> None:
    order_service, reconciliation_service = _services()
    first_intent = _entry_intent("setup-reconcile-1", symbol="AAA")
    replacement_intent = _entry_intent("setup-reconcile-2", symbol="AAA")

    assert order_service.submit_intent(first_intent).accepted is True
    reconciliation_service.reconcile_orders(
        [
            _broker_snapshot(
                first_intent,
                broker_order_id="broker-1",
                status=BrokerOrderStatus.OPEN,
            )
        ]
    )

    recovery = order_service.recover_state()
    blocked = order_service.submit_intent(replacement_intent)

    assert tuple(intent.intent_id for intent in recovery.pending_entry_intents) == (
        first_intent.intent_id,
    )
    assert blocked.accepted is False
    assert blocked.reason == "PENDING_ENTRY_EXISTS"


def test_reconcile_reports_unmatched_broker_orders() -> None:
    _, reconciliation_service = _services()
    intent = _entry_intent("setup-reconcile-1")

    result = reconciliation_service.reconcile_orders(
        [
            _broker_snapshot(
                intent,
                broker_order_id="broker-orphan",
                status=BrokerOrderStatus.OPEN,
            )
        ]
    )

    assert result.unmatched_broker_order_ids == ("broker-orphan",)
