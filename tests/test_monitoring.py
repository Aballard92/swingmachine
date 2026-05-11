from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from swingmachine.config import load_strategy_config
from swingmachine.contracts import ReconciliationResult
from swingmachine.enums import OrderSide
from swingmachine.monitoring import MonitoringService, adverse_slippage_bps


def test_adverse_slippage_bps_handles_buy_and_sell_asymmetrically() -> None:
    assert adverse_slippage_bps(
        reference_price=100.0,
        executed_price=100.5,
        side=OrderSide.BUY,
    ) == pytest.approx(50.0)
    assert adverse_slippage_bps(
        reference_price=100.0,
        executed_price=99.5,
        side=OrderSide.SELL,
    ) == pytest.approx(50.0)
    assert adverse_slippage_bps(
        reference_price=100.0,
        executed_price=99.5,
        side=OrderSide.BUY,
    ) == pytest.approx(0.0)


def test_monitoring_service_triggers_stale_data_and_drawdown_kill_switches() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    service = MonitoringService(config)
    now = datetime(2026, 4, 23, 16, 0)

    stale = service.evaluate_stale_data(
        as_of=now,
        last_data_at=now - timedelta(seconds=601),
    )
    drawdown = service.evaluate_drawdown(
        triggered_at=now,
        day_start_equity=100_000.0,
        current_equity=97_900.0,
    )

    assert stale is not None
    assert stale.kill_switch_active is True
    assert drawdown is not None
    assert drawdown.kill_switch_active is True


def test_monitoring_service_emits_slippage_warning_without_kill_switch() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    service = MonitoringService(config)
    now = datetime(2026, 4, 23, 16, 0)

    alert = service.evaluate_slippage(
        triggered_at=now,
        reference_price=100.0,
        executed_price=100.6,
        side=OrderSide.BUY,
        symbol="AAA",
        broker_order_id="broker-1",
    )

    assert alert is not None
    assert alert.kill_switch_active is False
    assert alert.symbol == "AAA"
    assert alert.broker_order_id == "broker-1"
    assert alert.metric_value == pytest.approx(60.0)


def test_monitoring_service_triggers_reconciliation_and_broker_health_kill_switches() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    service = MonitoringService(config)
    now = datetime(2026, 4, 23, 16, 0)
    reconciliation_result = ReconciliationResult(
        matched_intent_ids=(),
        recovered_intent_ids=(),
        terminalized_intent_ids=(),
        unmatched_broker_order_ids=("orphan-1",),
        ambiguous_intent_ids=("intent-2",),
        missing_broker_order_intent_ids=("intent-3",),
    )

    reconciliation_alert = service.evaluate_reconciliation(
        triggered_at=now,
        reconciliation_result=reconciliation_result,
    )
    broker_alert = service.evaluate_broker_health(
        triggered_at=now,
        broker_available=False,
        detail="Broker heartbeat failed",
    )

    assert reconciliation_alert is not None
    assert reconciliation_alert.kill_switch_active is True
    assert reconciliation_alert.metric_value == pytest.approx(3.0)
    assert broker_alert is not None
    assert broker_alert.kill_switch_active is True
    assert broker_alert.message == "Broker heartbeat failed"


def test_monitoring_service_build_report_aggregates_alerts() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    service = MonitoringService(config)
    now = datetime(2026, 4, 23, 16, 0)

    stale = service.evaluate_stale_data(
        as_of=now,
        last_data_at=now - timedelta(seconds=601),
    )
    slippage = service.evaluate_slippage(
        triggered_at=now,
        reference_price=100.0,
        executed_price=100.6,
        side=OrderSide.BUY,
    )
    report = service.build_report((stale, slippage, None))

    assert len(report.alerts) == 2
    assert report.kill_switch_active is True
