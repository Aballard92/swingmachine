from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import sessionmaker

from swingmachine.broker import PaperBrokerAdapter
from swingmachine.config import load_strategy_config
from swingmachine.contracts import PendingEntryCheck, SetupSnapshot
from swingmachine.entries import build_setup_snapshot, make_entry_order_intent
from swingmachine.enums import OrderIntentStatus, PatternType, RegimeState
from swingmachine.monitoring import MonitoringService
from swingmachine.order_intents import OrderIntentService
from swingmachine.order_state_machine import OrderStateMachine
from swingmachine.portfolio_manager import PortfolioManager
from swingmachine.reconciliation import ReconciliationService
from swingmachine.storage import (
    OrderIntentRow,
    create_database_engine,
    create_session_factory,
    initialize_database,
)


def _services() -> tuple[
    sessionmaker,
    OrderIntentService,
    PaperBrokerAdapter,
    ReconciliationService,
    OrderStateMachine,
]:
    engine = create_database_engine()
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    order_service = OrderIntentService(session_factory)
    broker = PaperBrokerAdapter(session_factory)
    reconciliation = ReconciliationService(session_factory)
    state_machine = OrderStateMachine(
        config,
        order_intent_service=order_service,
        broker_adapter=broker,
        reconciliation_service=reconciliation,
        portfolio_manager=PortfolioManager(config),
        monitoring_service=MonitoringService(config),
    )
    return session_factory, order_service, broker, reconciliation, state_machine


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


def _entry_intent(setup_id: str, *, symbol: str = "AAA"):
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    setup = _setup_snapshot(setup_id, symbol=symbol)
    return make_entry_order_intent(
        setup,
        quantity=10,
        strategy_id=config.strategy.id,
        config_hash=config.config_hash(),
        created_at=datetime(2026, 4, 23, 16, 10),
        expires_at=datetime(2026, 4, 24, 16, 0),
    )


def test_synchronize_recovers_open_broker_order_into_pending_state() -> None:
    session_factory, order_service, broker, _, state_machine = _services()
    intent = _entry_intent("setup-sync-1")

    assert order_service.submit_intent(intent).accepted is True
    submit_result = broker.submit_order_intent(intent)
    assert submit_result.accepted is True

    with session_factory.begin() as session:
        row = session.get(OrderIntentRow, intent.intent_id)
        assert row is not None
        row.status = OrderIntentStatus.GENERATED.value

    sync = state_machine.synchronize(
        as_of=datetime(2026, 4, 24, 9, 30),
        last_data_at=datetime(2026, 4, 24, 9, 29),
    )

    assert sync.reconciliation_result.recovered_intent_ids == (intent.intent_id,)
    assert tuple(item.intent_id for item in sync.recovery_state.pending_entry_intents) == (
        intent.intent_id,
    )
    assert sync.monitoring_report.kill_switch_active is False


def test_submit_entry_batch_blocks_when_monitoring_kill_switch_is_active() -> None:
    _, _, _, _, state_machine = _services()

    result = state_machine.submit_entry_batch(
        (_setup_snapshot("setup-submit-1"),),
        as_of=datetime(2026, 4, 24, 9, 30),
        regime_state=RegimeState.RISK_ON,
        equity=100_000.0,
        last_data_at=datetime(2026, 4, 24, 9, 20),
        broker_available=False,
    )

    assert result.synchronization.monitoring_report.kill_switch_active is True
    assert result.portfolio_batch.approved_count == 0
    assert result.submissions == ()


def test_submit_entry_batch_skips_spent_setup_and_submits_fresh_setup() -> None:
    _, order_service, broker, _, state_machine = _services()
    spent_setup = _setup_snapshot("setup-spent", symbol="AAA")
    fresh_setup = _setup_snapshot("setup-fresh", symbol="BBB")

    order_service.mark_setup_spent(
        setup_id=spent_setup.setup_id,
        symbol=spent_setup.symbol,
        marked_at=datetime(2026, 4, 24, 9, 0),
        reason="EXPIRED",
    )

    result = state_machine.submit_entry_batch(
        (spent_setup, fresh_setup),
        as_of=datetime(2026, 4, 24, 9, 30),
        regime_state=RegimeState.RISK_ON,
        equity=100_000.0,
        last_data_at=datetime(2026, 4, 24, 9, 29),
        expires_at=datetime(2026, 4, 25, 16, 0),
        sector_by_symbol={
            "AAA": "TECH",
            "BBB": "INDUSTRIALS",
        },
    )

    assert result.blocked_spent_setup_ids == ("setup-spent",)
    assert len(result.submissions) == 1
    assert result.submissions[0].symbol == "BBB"
    assert result.submissions[0].submitted is True
    assert result.submissions[0].broker_order_id is not None
    assert tuple(order.symbol for order in broker.list_open_orders()) == ("BBB",)


def test_process_pending_entries_expires_order_and_marks_setup_spent() -> None:
    _, order_service, broker, _, state_machine = _services()
    intent = _entry_intent("setup-expire-1")
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")

    assert order_service.submit_intent(intent).accepted is True
    submit_result = broker.submit_order_intent(intent)
    assert submit_result.accepted is True

    result = state_machine.process_pending_entries(
        {
            "AAA": PendingEntryCheck(
                regular_sessions_elapsed=config.entry.order_expiry_sessions,
            )
        },
        as_of=datetime(2026, 4, 24, 16, 1),
        last_data_at=datetime(2026, 4, 24, 16, 0),
    )

    assert len(result.actions) == 1
    action = result.actions[0]
    assert action.evaluation.expired is True
    assert action.broker_cancelled is True
    assert action.terminal_status == OrderIntentStatus.EXPIRED
    assert action.setup_marked_spent is True
    assert order_service.get_intent_status(intent.intent_id) == OrderIntentStatus.EXPIRED
    assert "setup-expire-1" in order_service.spent_setup_ids()
