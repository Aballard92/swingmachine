from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from swingmachine.config import StrategyRuntimeConfig
from swingmachine.contracts import MonitoringAlert, MonitoringReport, ReconciliationResult
from swingmachine.enums import AlertSeverity, MonitoringAlertType, OrderSide


def adverse_slippage_bps(
    *,
    reference_price: float,
    executed_price: float,
    side: OrderSide,
) -> float:
    if reference_price <= 0.0:
        raise ValueError("reference_price must be strictly positive")
    if executed_price <= 0.0:
        raise ValueError("executed_price must be strictly positive")

    if side == OrderSide.BUY:
        adverse_move = max(executed_price - reference_price, 0.0)
    else:
        adverse_move = max(reference_price - executed_price, 0.0)
    return adverse_move / reference_price * 10_000.0


class MonitoringService:
    def __init__(self, config: StrategyRuntimeConfig) -> None:
        self._config = config

    def evaluate_stale_data(
        self,
        *,
        as_of: datetime,
        last_data_at: datetime,
    ) -> MonitoringAlert | None:
        if not self._config.monitoring.enable_stale_data_checks:
            return None

        age_seconds = (as_of - last_data_at).total_seconds()
        if age_seconds <= self._config.monitoring.max_data_age_seconds:
            return None

        return MonitoringAlert(
            alert_type=MonitoringAlertType.STALE_DATA,
            severity=AlertSeverity.CRITICAL,
            message="Market data is stale beyond the configured maximum age",
            triggered_at=as_of,
            kill_switch_active=True,
            metric_value=age_seconds,
            threshold_value=float(self._config.monitoring.max_data_age_seconds),
        )

    def evaluate_slippage(
        self,
        *,
        triggered_at: datetime,
        reference_price: float,
        executed_price: float,
        side: OrderSide,
        symbol: str | None = None,
        broker_order_id: str | None = None,
    ) -> MonitoringAlert | None:
        if not self._config.monitoring.enable_slippage_alerts:
            return None

        slippage_bps = adverse_slippage_bps(
            reference_price=reference_price,
            executed_price=executed_price,
            side=side,
        )
        if slippage_bps <= self._config.monitoring.slippage_alert_bps:
            return None

        return MonitoringAlert(
            alert_type=MonitoringAlertType.SLIPPAGE,
            severity=AlertSeverity.WARNING,
            message="Adverse execution slippage exceeded the configured alert threshold",
            triggered_at=triggered_at,
            kill_switch_active=False,
            symbol=symbol,
            broker_order_id=broker_order_id,
            metric_value=slippage_bps,
            threshold_value=float(self._config.monitoring.slippage_alert_bps),
        )

    def evaluate_drawdown(
        self,
        *,
        triggered_at: datetime,
        day_start_equity: float,
        current_equity: float,
    ) -> MonitoringAlert | None:
        if not self._config.monitoring.enable_drawdown_kill_switch:
            return None
        if day_start_equity <= 0.0:
            raise ValueError("day_start_equity must be strictly positive")
        if current_equity < 0.0:
            raise ValueError("current_equity cannot be negative")

        drawdown_pct = max(1.0 - current_equity / day_start_equity, 0.0)
        if drawdown_pct < self._config.monitoring.daily_drawdown_kill_switch_pct:
            return None

        return MonitoringAlert(
            alert_type=MonitoringAlertType.DRAWDOWN_KILL_SWITCH,
            severity=AlertSeverity.CRITICAL,
            message="Daily drawdown breached the configured kill-switch threshold",
            triggered_at=triggered_at,
            kill_switch_active=True,
            metric_value=drawdown_pct,
            threshold_value=float(self._config.monitoring.daily_drawdown_kill_switch_pct),
        )

    def evaluate_reconciliation(
        self,
        *,
        triggered_at: datetime,
        reconciliation_result: ReconciliationResult,
    ) -> MonitoringAlert | None:
        if not self._config.monitoring.enable_reconciliation_kill_switch:
            return None

        mismatch_count = (
            len(reconciliation_result.unmatched_broker_order_ids)
            + len(reconciliation_result.ambiguous_intent_ids)
            + len(reconciliation_result.missing_broker_order_intent_ids)
        )
        if mismatch_count == 0:
            return None

        return MonitoringAlert(
            alert_type=MonitoringAlertType.RECONCILIATION_MISMATCH,
            severity=AlertSeverity.CRITICAL,
            message="Reconciliation detected unmatched, ambiguous, or missing broker state",
            triggered_at=triggered_at,
            kill_switch_active=True,
            metric_value=float(mismatch_count),
            threshold_value=0.0,
        )

    def evaluate_broker_health(
        self,
        *,
        triggered_at: datetime,
        broker_available: bool,
        detail: str | None = None,
    ) -> MonitoringAlert | None:
        if not self._config.monitoring.enable_broker_health_kill_switch:
            return None
        if broker_available:
            return None

        return MonitoringAlert(
            alert_type=MonitoringAlertType.BROKER_UNAVAILABLE,
            severity=AlertSeverity.CRITICAL,
            message=detail or "Broker health check failed",
            triggered_at=triggered_at,
            kill_switch_active=True,
        )

    def build_report(
        self,
        alerts: Iterable[MonitoringAlert | None],
    ) -> MonitoringReport:
        realized_alerts = tuple(alert for alert in alerts if alert is not None)
        return MonitoringReport(
            alerts=realized_alerts,
            kill_switch_active=any(alert.kill_switch_active for alert in realized_alerts),
        )
