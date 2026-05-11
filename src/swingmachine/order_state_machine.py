from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from swingmachine.broker import BrokerAdapter
from swingmachine.config import StrategyRuntimeConfig
from swingmachine.contracts import (
    EntrySubmissionBatch,
    EntrySubmissionOutcome,
    OrderStateSynchronization,
    PendingEntryAction,
    PendingEntryBatchResult,
    PendingEntryCheck,
    PortfolioEntryBatch,
    ProtectedPosition,
    ReconciliationResult,
    SetupSnapshot,
)
from swingmachine.entries import portfolio_heat
from swingmachine.enums import MonitoringAlertType, OrderIntentStatus, RegimeState
from swingmachine.lifecycle import evaluate_pending_entry, setup_can_be_armed
from swingmachine.monitoring import MonitoringService
from swingmachine.order_intents import OrderIntentService
from swingmachine.portfolio_manager import PortfolioManager
from swingmachine.reconciliation import ReconciliationService

_BROKER_STATE_UNCERTAINTY_ALERTS = {
    MonitoringAlertType.BROKER_UNAVAILABLE,
    MonitoringAlertType.RECONCILIATION_MISMATCH,
}


def _empty_reconciliation_result() -> ReconciliationResult:
    return ReconciliationResult()


def _empty_portfolio_batch(
    *,
    equity: float,
    open_positions: Sequence[ProtectedPosition],
) -> PortfolioEntryBatch:
    return PortfolioEntryBatch(
        plans=(),
        approved_count=0,
        rejected_count=0,
        batch_new_risk_amount=0.0,
        projected_portfolio_heat=(
            portfolio_heat(open_positions, equity) if open_positions else 0.0
        ),
        projected_daily_new_risk=0.0,
    )


class OrderStateMachine:
    def __init__(
        self,
        config: StrategyRuntimeConfig,
        *,
        order_intent_service: OrderIntentService,
        broker_adapter: BrokerAdapter,
        reconciliation_service: ReconciliationService,
        portfolio_manager: PortfolioManager | None = None,
        monitoring_service: MonitoringService | None = None,
    ) -> None:
        self._config = config
        self._order_intent_service = order_intent_service
        self._broker_adapter = broker_adapter
        self._reconciliation_service = reconciliation_service
        self._portfolio_manager = portfolio_manager or PortfolioManager(config)
        self._monitoring_service = monitoring_service or MonitoringService(config)

    def synchronize(
        self,
        *,
        as_of: datetime,
        last_data_at: datetime | None = None,
        day_start_equity: float | None = None,
        current_equity: float | None = None,
        broker_available: bool = True,
    ) -> OrderStateSynchronization:
        alerts = []
        broker_health_detail: str | None = None
        reconciliation_result = _empty_reconciliation_result()

        if broker_available:
            try:
                broker_orders = self._broker_adapter.list_open_orders()
            except Exception as exc:  # pragma: no cover - defensive adapter wrapper
                broker_available = False
                broker_health_detail = f"Broker order listing failed: {exc}"
            else:
                reconciliation_result = self._reconciliation_service.reconcile_orders(broker_orders)
                self._mark_spent_setups_from_terminalized_reconciliation(
                    reconciliation_result,
                    marked_at=as_of,
                )

        alerts.append(
            self._monitoring_service.evaluate_broker_health(
                triggered_at=as_of,
                broker_available=broker_available,
                detail=broker_health_detail,
            )
        )
        if broker_available:
            alerts.append(
                self._monitoring_service.evaluate_reconciliation(
                    triggered_at=as_of,
                    reconciliation_result=reconciliation_result,
                )
            )
        if last_data_at is not None:
            alerts.append(
                self._monitoring_service.evaluate_stale_data(
                    as_of=as_of,
                    last_data_at=last_data_at,
                )
            )
        if day_start_equity is not None and current_equity is not None:
            alerts.append(
                self._monitoring_service.evaluate_drawdown(
                    triggered_at=as_of,
                    day_start_equity=day_start_equity,
                    current_equity=current_equity,
                )
            )

        return OrderStateSynchronization(
            recovery_state=self._order_intent_service.recover_state(),
            reconciliation_result=reconciliation_result,
            monitoring_report=self._monitoring_service.build_report(alerts),
        )

    def submit_entry_batch(
        self,
        setups: Sequence[SetupSnapshot],
        *,
        as_of: datetime,
        regime_state: RegimeState,
        equity: float,
        expires_at: datetime | None = None,
        last_data_at: datetime | None = None,
        day_start_equity: float | None = None,
        current_equity: float | None = None,
        broker_available: bool = True,
        open_positions: Sequence[ProtectedPosition] = (),
        submitted_today_risk_amount: float = 0.0,
        sector_by_symbol: Mapping[str, str | None] | None = None,
        vol_target_size_multiplier: float | None = None,
    ) -> EntrySubmissionBatch:
        sync = self.synchronize(
            as_of=as_of,
            last_data_at=last_data_at,
            day_start_equity=day_start_equity,
            current_equity=current_equity,
            broker_available=broker_available,
        )
        spent_setup_ids = set(sync.recovery_state.spent_setup_ids)
        blocked_spent_setup_ids: list[str] = []
        armable_setups: list[SetupSnapshot] = []
        for setup in setups:
            if setup.spent or not setup_can_be_armed(
                setup.setup_id,
                spent_setup_ids=spent_setup_ids,
                config=self._config,
            ):
                blocked_spent_setup_ids.append(setup.setup_id)
                continue
            armable_setups.append(setup)

        if sync.monitoring_report.kill_switch_active:
            return EntrySubmissionBatch(
                synchronization=sync,
                portfolio_batch=_empty_portfolio_batch(
                    equity=equity,
                    open_positions=open_positions,
                ),
                blocked_spent_setup_ids=tuple(blocked_spent_setup_ids),
                submissions=(),
            )

        portfolio_batch = self._portfolio_manager.plan_ranked_entries(
            armable_setups,
            regime_state=regime_state,
            equity=equity,
            pending_symbols=tuple(
                intent.symbol for intent in sync.recovery_state.pending_entry_intents
            ),
            open_positions=open_positions,
            submitted_today_risk_amount=submitted_today_risk_amount,
            sector_by_symbol=sector_by_symbol,
            vol_target_size_multiplier=vol_target_size_multiplier,
            created_at=as_of,
            expires_at=expires_at,
        )

        submissions: list[EntrySubmissionOutcome] = []
        for plan in portfolio_batch.plans:
            if not plan.approved:
                submissions.append(
                    EntrySubmissionOutcome(
                        symbol=plan.setup.symbol,
                        setup_id=plan.setup.setup_id,
                        approved=False,
                        submitted=False,
                        reject_reasons=plan.reject_reasons,
                    )
                )
                continue

            if plan.order_intent is None:
                submissions.append(
                    EntrySubmissionOutcome(
                        symbol=plan.setup.symbol,
                        setup_id=plan.setup.setup_id,
                        approved=True,
                        submitted=False,
                        reject_reasons=("MISSING_ORDER_INTENT",),
                    )
                )
                continue

            intent_result = self._order_intent_service.submit_intent(plan.order_intent)
            if not intent_result.accepted:
                submissions.append(
                    EntrySubmissionOutcome(
                        symbol=plan.setup.symbol,
                        setup_id=plan.setup.setup_id,
                        approved=True,
                        submitted=False,
                        intent_id=intent_result.existing_intent_id,
                        reject_reasons=((intent_result.reason or "INTENT_REJECTED"),),
                    )
                )
                continue

            broker_result = self._broker_adapter.submit_order_intent(plan.order_intent)
            if not broker_result.accepted:
                self._order_intent_service.mark_terminal(
                    plan.order_intent.intent_id,
                    status=OrderIntentStatus.REJECTED,
                )
                self._order_intent_service.mark_setup_spent(
                    setup_id=plan.setup.setup_id,
                    symbol=plan.setup.symbol,
                    marked_at=as_of,
                    reason=broker_result.reason or "BROKER_REJECTED",
                )
                submissions.append(
                    EntrySubmissionOutcome(
                        symbol=plan.setup.symbol,
                        setup_id=plan.setup.setup_id,
                        approved=True,
                        submitted=False,
                        intent_id=plan.order_intent.intent_id,
                        reject_reasons=((broker_result.reason or "BROKER_REJECTED"),),
                    )
                )
                continue

            submissions.append(
                EntrySubmissionOutcome(
                    symbol=plan.setup.symbol,
                    setup_id=plan.setup.setup_id,
                    approved=True,
                    submitted=True,
                    intent_id=plan.order_intent.intent_id,
                    broker_order_id=(
                        None if broker_result.order is None else broker_result.order.broker_order_id
                    ),
                    reused_existing_broker_order=broker_result.reused_existing,
                )
            )

        return EntrySubmissionBatch(
            synchronization=sync,
            portfolio_batch=portfolio_batch,
            blocked_spent_setup_ids=tuple(blocked_spent_setup_ids),
            submissions=tuple(submissions),
        )

    def process_pending_entries(
        self,
        checks_by_symbol: Mapping[str, PendingEntryCheck] | None = None,
        *,
        as_of: datetime,
        last_data_at: datetime | None = None,
        day_start_equity: float | None = None,
        current_equity: float | None = None,
        broker_available: bool = True,
    ) -> PendingEntryBatchResult:
        sync = self.synchronize(
            as_of=as_of,
            last_data_at=last_data_at,
            day_start_equity=day_start_equity,
            current_equity=current_equity,
            broker_available=broker_available,
        )
        if self._broker_state_uncertain(sync):
            return PendingEntryBatchResult(
                synchronization=sync,
                actions=(),
            )

        checks = checks_by_symbol or {}
        actions: list[PendingEntryAction] = []
        for intent in sync.recovery_state.pending_entry_intents:
            check = checks.get(intent.symbol, PendingEntryCheck())
            evaluation = evaluate_pending_entry(
                intent,
                config=self._config,
                official_open_next=check.official_open_next,
                regular_sessions_elapsed=int(check.regular_sessions_elapsed),
                regime_state=check.regime_state,
                earnings_window_breached=check.earnings_window_breached,
                shared_setup_preconditions_pass=check.shared_setup_preconditions_pass,
                intent_invalidated=check.intent_invalidated,
                fill_confirmed=check.fill_confirmed,
                hard_eligible_after_cancel=check.hard_eligible_after_cancel,
                candidate_eligible_after_cancel=check.candidate_eligible_after_cancel,
            )

            broker_cancelled = False
            broker_cancel_reason: str | None = None
            terminal_status: OrderIntentStatus | None = None
            setup_marked_spent = False

            if evaluation.should_cancel:
                desired_status = (
                    OrderIntentStatus.EXPIRED if evaluation.expired else OrderIntentStatus.CANCELLED
                )
                if intent.broker_order_id is None:
                    self._order_intent_service.mark_terminal(
                        intent.intent_id,
                        status=desired_status,
                    )
                    terminal_status = desired_status
                else:
                    cancel_result = self._broker_adapter.cancel_order(intent.broker_order_id)
                    broker_cancelled = cancel_result.cancelled
                    broker_cancel_reason = cancel_result.reason
                    if cancel_result.cancelled:
                        self._order_intent_service.mark_terminal(
                            intent.intent_id,
                            status=desired_status,
                            broker_order_id=intent.broker_order_id,
                        )
                        terminal_status = desired_status

                if (
                    terminal_status is not None
                    and evaluation.mark_setup_spent
                    and evaluation.setup_id is not None
                ):
                    self._order_intent_service.mark_setup_spent(
                        setup_id=evaluation.setup_id,
                        symbol=evaluation.symbol,
                        marked_at=as_of,
                        reason=",".join(reason.value for reason in evaluation.cancel_reasons),
                    )
                    setup_marked_spent = True

            actions.append(
                PendingEntryAction(
                    intent_id=intent.intent_id,
                    symbol=intent.symbol,
                    setup_id=intent.setup_id,
                    evaluation=evaluation,
                    broker_cancelled=broker_cancelled,
                    broker_cancel_reason=broker_cancel_reason,
                    terminal_status=terminal_status,
                    setup_marked_spent=setup_marked_spent,
                )
            )

        return PendingEntryBatchResult(
            synchronization=sync,
            actions=tuple(actions),
        )

    def _broker_state_uncertain(self, sync: OrderStateSynchronization) -> bool:
        return any(
            alert.alert_type in _BROKER_STATE_UNCERTAINTY_ALERTS
            for alert in sync.monitoring_report.alerts
        )

    def _mark_spent_setups_from_terminalized_reconciliation(
        self,
        reconciliation_result: ReconciliationResult,
        *,
        marked_at: datetime,
    ) -> None:
        for intent_id in reconciliation_result.terminalized_intent_ids:
            intent = self._order_intent_service.get_intent(intent_id)
            status = self._order_intent_service.get_intent_status(intent_id)
            if intent is None or intent.setup_id is None or status is None:
                continue
            if status not in {
                OrderIntentStatus.CANCELLED,
                OrderIntentStatus.REJECTED,
                OrderIntentStatus.EXPIRED,
            }:
                continue
            self._order_intent_service.mark_setup_spent(
                setup_id=intent.setup_id,
                symbol=intent.symbol,
                marked_at=marked_at,
                reason=status.value,
            )
