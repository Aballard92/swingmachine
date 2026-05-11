from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from swingmachine.contracts import BrokerOrderSnapshot, ReconciliationResult
from swingmachine.enums import BrokerOrderStatus, OrderIntentStatus
from swingmachine.storage import OrderIntentRow, nonterminal_intent_rows

TERMINAL_STATUS_BY_BROKER_STATUS = {
    BrokerOrderStatus.FILLED: OrderIntentStatus.FILLED,
    BrokerOrderStatus.CANCELLED: OrderIntentStatus.CANCELLED,
    BrokerOrderStatus.REJECTED: OrderIntentStatus.REJECTED,
    BrokerOrderStatus.EXPIRED: OrderIntentStatus.EXPIRED,
}

PRICE_TOLERANCE = 1e-9
QUANTITY_TOLERANCE = 1e-9


def _float_equal(left: float | None, right: float | None) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return abs(left - right) <= PRICE_TOLERANCE


def _intent_matches_broker_order(
    row: OrderIntentRow,
    broker_order: BrokerOrderSnapshot,
) -> bool:
    return (
        row.symbol == broker_order.symbol
        and row.side == broker_order.side.value
        and row.order_type == broker_order.order_type.value
        and abs(row.quantity - float(broker_order.quantity)) <= QUANTITY_TOLERANCE
        and _float_equal(row.stop_price, broker_order.stop_price)
        and _float_equal(row.limit_price, broker_order.limit_price)
    )


class ReconciliationService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def reconcile_orders(
        self,
        broker_orders: tuple[BrokerOrderSnapshot, ...] | list[BrokerOrderSnapshot],
    ) -> ReconciliationResult:
        with self._session_factory.begin() as session:
            local_rows = nonterminal_intent_rows(session)
            broker_order_map = {
                broker_order.broker_order_id: broker_order for broker_order in broker_orders
            }
            matched_broker_order_ids: set[str] = set()

            matched_intent_ids: list[str] = []
            recovered_intent_ids: list[str] = []
            terminalized_intent_ids: list[str] = []
            ambiguous_intent_ids: list[str] = []
            missing_broker_order_intent_ids: list[str] = []

            for row in local_rows:
                broker_order = None

                if row.broker_order_id is not None:
                    broker_order = broker_order_map.get(row.broker_order_id)

                if broker_order is None:
                    structural_matches = [
                        candidate
                        for candidate in broker_orders
                        if candidate.broker_order_id not in matched_broker_order_ids
                        and _intent_matches_broker_order(row, candidate)
                    ]
                    if len(structural_matches) == 1:
                        broker_order = structural_matches[0]
                    elif len(structural_matches) > 1:
                        ambiguous_intent_ids.append(row.intent_id)
                        continue

                if broker_order is None:
                    if row.status == OrderIntentStatus.ACTIVE.value:
                        missing_broker_order_intent_ids.append(row.intent_id)
                    continue

                matched_intent_ids.append(row.intent_id)
                matched_broker_order_ids.add(broker_order.broker_order_id)
                if row.broker_order_id != broker_order.broker_order_id:
                    row.broker_order_id = broker_order.broker_order_id

                if broker_order.status == BrokerOrderStatus.OPEN:
                    if row.status != OrderIntentStatus.ACTIVE.value:
                        recovered_intent_ids.append(row.intent_id)
                    row.status = OrderIntentStatus.ACTIVE.value
                else:
                    row.status = TERMINAL_STATUS_BY_BROKER_STATUS[broker_order.status].value
                    terminalized_intent_ids.append(row.intent_id)

                row.updated_at = datetime.utcnow()

            unmatched_broker_order_ids = sorted(
                broker_order.broker_order_id
                for broker_order in broker_orders
                if broker_order.broker_order_id not in matched_broker_order_ids
            )

        return ReconciliationResult(
            matched_intent_ids=tuple(matched_intent_ids),
            recovered_intent_ids=tuple(recovered_intent_ids),
            terminalized_intent_ids=tuple(terminalized_intent_ids),
            unmatched_broker_order_ids=tuple(unmatched_broker_order_ids),
            ambiguous_intent_ids=tuple(ambiguous_intent_ids),
            missing_broker_order_intent_ids=tuple(missing_broker_order_intent_ids),
        )
