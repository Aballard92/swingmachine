from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from swingmachine.contracts import (
    BrokerCancelResult,
    BrokerOrderSnapshot,
    BrokerSubmitResult,
    OrderIntent,
)
from swingmachine.enums import BrokerOrderStatus, OrderIntentStatus
from swingmachine.storage import (
    BrokerOrderRow,
    OrderIntentRow,
    broker_order_snapshot_from_row,
    open_broker_order_rows,
)

TERMINAL_INTENT_STATUS_BY_BROKER_STATUS = {
    BrokerOrderStatus.FILLED: OrderIntentStatus.FILLED,
    BrokerOrderStatus.CANCELLED: OrderIntentStatus.CANCELLED,
    BrokerOrderStatus.REJECTED: OrderIntentStatus.REJECTED,
    BrokerOrderStatus.EXPIRED: OrderIntentStatus.EXPIRED,
}


def _paper_broker_order_id(intent_id: str) -> str:
    digest = hashlib.sha256(intent_id.encode("utf-8")).hexdigest()[:20]
    return f"paper-{digest}"


class BrokerAdapter(ABC):
    @abstractmethod
    def submit_order_intent(self, intent: OrderIntent) -> BrokerSubmitResult:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> BrokerCancelResult:
        raise NotImplementedError

    @abstractmethod
    def get_order(self, broker_order_id: str) -> BrokerOrderSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    def list_open_orders(self) -> tuple[BrokerOrderSnapshot, ...]:
        raise NotImplementedError


class PaperBrokerAdapter(BrokerAdapter):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def submit_order_intent(self, intent: OrderIntent) -> BrokerSubmitResult:
        with self._session_factory.begin() as session:
            intent_row = session.get(OrderIntentRow, intent.intent_id)
            if intent_row is None:
                return BrokerSubmitResult(
                    accepted=False,
                    reused_existing=False,
                    reason="UNKNOWN_INTENT",
                )

            existing = session.scalar(
                select(BrokerOrderRow).where(BrokerOrderRow.intent_id == intent.intent_id)
            )
            if existing is not None:
                return BrokerSubmitResult(
                    accepted=True,
                    reused_existing=True,
                    order=broker_order_snapshot_from_row(existing),
                    reason=None,
                )

            broker_order_id = _paper_broker_order_id(intent.intent_id)
            row = BrokerOrderRow(
                broker_order_id=broker_order_id,
                intent_id=intent.intent_id,
                symbol=intent.symbol,
                side=intent.side.value,
                order_type=intent.order_type.value,
                quantity=float(intent.quantity),
                stop_price=(None if intent.stop_price is None else float(intent.stop_price)),
                limit_price=(None if intent.limit_price is None else float(intent.limit_price)),
                status=BrokerOrderStatus.OPEN.value,
                created_at=intent.created_at,
                updated_at=datetime.utcnow(),
            )
            session.add(row)

            intent_row.status = OrderIntentStatus.ACTIVE.value
            intent_row.broker_order_id = broker_order_id
            intent_row.updated_at = datetime.utcnow()

            return BrokerSubmitResult(
                accepted=True,
                reused_existing=False,
                order=broker_order_snapshot_from_row(row),
                reason=None,
            )

    def cancel_order(self, broker_order_id: str) -> BrokerCancelResult:
        with self._session_factory.begin() as session:
            row = session.get(BrokerOrderRow, broker_order_id)
            if row is None:
                return BrokerCancelResult(
                    cancelled=False,
                    order=None,
                    reason="UNKNOWN_BROKER_ORDER",
                )

            if row.status != BrokerOrderStatus.OPEN.value:
                return BrokerCancelResult(
                    cancelled=False,
                    order=broker_order_snapshot_from_row(row),
                    reason="ORDER_NOT_OPEN",
                )

            row.status = BrokerOrderStatus.CANCELLED.value
            row.updated_at = datetime.utcnow()

            intent_row = session.get(OrderIntentRow, row.intent_id)
            if intent_row is not None:
                intent_row.status = OrderIntentStatus.CANCELLED.value
                intent_row.updated_at = datetime.utcnow()

            return BrokerCancelResult(
                cancelled=True,
                order=broker_order_snapshot_from_row(row),
                reason=None,
            )

    def get_order(self, broker_order_id: str) -> BrokerOrderSnapshot | None:
        with self._session_factory() as session:
            row = session.get(BrokerOrderRow, broker_order_id)
            if row is None:
                return None
            return broker_order_snapshot_from_row(row)

    def list_open_orders(self) -> tuple[BrokerOrderSnapshot, ...]:
        with self._session_factory() as session:
            rows = open_broker_order_rows(session)
            return tuple(broker_order_snapshot_from_row(row) for row in rows)

    def list_orders(self) -> tuple[BrokerOrderSnapshot, ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(BrokerOrderRow).order_by(
                    BrokerOrderRow.created_at, BrokerOrderRow.broker_order_id
                )
            ).all()
            return tuple(broker_order_snapshot_from_row(row) for row in rows)

    def update_order_status(
        self,
        broker_order_id: str,
        *,
        status: BrokerOrderStatus,
    ) -> BrokerOrderSnapshot:
        with self._session_factory.begin() as session:
            row = session.get(BrokerOrderRow, broker_order_id)
            if row is None:
                raise KeyError(f"Unknown broker_order_id: {broker_order_id}")

            row.status = status.value
            row.updated_at = datetime.utcnow()

            intent_row = session.get(OrderIntentRow, row.intent_id)
            if intent_row is not None:
                if status == BrokerOrderStatus.OPEN:
                    intent_row.status = OrderIntentStatus.ACTIVE.value
                else:
                    intent_row.status = TERMINAL_INTENT_STATUS_BY_BROKER_STATUS[status].value
                intent_row.updated_at = datetime.utcnow()

            return broker_order_snapshot_from_row(row)
