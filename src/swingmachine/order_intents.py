from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from swingmachine.contracts import (
    CanonicalSnapshotHashRecord,
    OrderIntent,
    OrderIntentSubmissionResult,
    RegimeSnapshot,
    RestartRecoveryState,
)
from swingmachine.enums import OrderIntentStatus, OrderReason
from swingmachine.storage import (
    OrderIntentRow,
    SpentSetupRow,
    load_canonical_snapshot_hash,
    load_regime_snapshot,
    load_spent_setup_ids,
    nonterminal_entry_intent_rows,
    order_intent_from_row,
    upsert_canonical_snapshot_hash,
    upsert_regime_snapshot,
    upsert_spent_setup,
)

TERMINAL_INTENT_STATUSES = {
    OrderIntentStatus.FILLED,
    OrderIntentStatus.CANCELLED,
    OrderIntentStatus.REJECTED,
    OrderIntentStatus.EXPIRED,
}


class OrderIntentService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def submit_intent(self, intent: OrderIntent) -> OrderIntentSubmissionResult:
        with self._session_factory.begin() as session:
            if (
                intent.setup_id is not None
                and session.get(SpentSetupRow, intent.setup_id) is not None
            ):
                return OrderIntentSubmissionResult(
                    accepted=False,
                    reason="SPENT_SETUP_BLOCKED",
                    existing_intent_id=None,
                )

            existing = session.scalar(
                select(OrderIntentRow).where(OrderIntentRow.dedupe_key == intent.dedupe_key)
            )
            if existing is not None:
                return OrderIntentSubmissionResult(
                    accepted=False,
                    reason="DUPLICATE_DEDUPE_KEY",
                    existing_intent_id=existing.intent_id,
                    intent=order_intent_from_row(existing),
                )

            if intent.reason == OrderReason.ENTRY:
                active_symbol_entry = session.scalar(
                    select(OrderIntentRow)
                    .where(OrderIntentRow.symbol == intent.symbol)
                    .where(OrderIntentRow.reason == OrderReason.ENTRY.value)
                    .where(
                        OrderIntentRow.status.in_(
                            [
                                OrderIntentStatus.GENERATED.value,
                                OrderIntentStatus.ACTIVE.value,
                            ]
                        )
                    )
                )
                if active_symbol_entry is not None:
                    return OrderIntentSubmissionResult(
                        accepted=False,
                        reason="PENDING_ENTRY_EXISTS",
                        existing_intent_id=active_symbol_entry.intent_id,
                        intent=order_intent_from_row(active_symbol_entry),
                    )

            session.add(
                OrderIntentRow(
                    intent_id=intent.intent_id,
                    dedupe_key=intent.dedupe_key,
                    strategy_id=intent.strategy_id,
                    config_hash=intent.config_hash,
                    symbol=intent.symbol,
                    setup_id=intent.setup_id,
                    side=intent.side.value,
                    reason=intent.reason.value,
                    order_type=intent.order_type.value,
                    quantity=float(intent.quantity),
                    stop_price=(None if intent.stop_price is None else float(intent.stop_price)),
                    limit_price=(None if intent.limit_price is None else float(intent.limit_price)),
                    created_at=intent.created_at,
                    expires_at=intent.expires_at,
                    broker_order_id=intent.broker_order_id,
                    status=OrderIntentStatus.GENERATED.value,
                    updated_at=datetime.utcnow(),
                )
            )

        return OrderIntentSubmissionResult(
            accepted=True,
            reason=None,
            existing_intent_id=None,
            intent=intent,
        )

    def get_intent(self, intent_id: str) -> OrderIntent | None:
        with self._session_factory() as session:
            row = session.get(OrderIntentRow, intent_id)
            if row is None:
                return None
            return order_intent_from_row(row)

    def get_intent_status(self, intent_id: str) -> OrderIntentStatus | None:
        with self._session_factory() as session:
            row = session.get(OrderIntentRow, intent_id)
            if row is None:
                return None
            return OrderIntentStatus(row.status)

    def mark_submitted(
        self,
        intent_id: str,
        *,
        broker_order_id: str | None = None,
    ) -> OrderIntent:
        with self._session_factory.begin() as session:
            row = session.get(OrderIntentRow, intent_id)
            if row is None:
                raise KeyError(f"Unknown intent_id: {intent_id}")

            row.status = OrderIntentStatus.ACTIVE.value
            row.broker_order_id = broker_order_id
            row.updated_at = datetime.utcnow()
            return order_intent_from_row(row)

    def mark_terminal(
        self,
        intent_id: str,
        *,
        status: OrderIntentStatus,
        broker_order_id: str | None = None,
    ) -> OrderIntent:
        if status not in TERMINAL_INTENT_STATUSES:
            raise ValueError("status must be terminal")

        with self._session_factory.begin() as session:
            row = session.get(OrderIntentRow, intent_id)
            if row is None:
                raise KeyError(f"Unknown intent_id: {intent_id}")

            row.status = status.value
            if broker_order_id is not None:
                row.broker_order_id = broker_order_id
            row.updated_at = datetime.utcnow()
            return order_intent_from_row(row)

    def mark_setup_spent(
        self,
        *,
        setup_id: str,
        symbol: str | None,
        marked_at: datetime,
        reason: str | None = None,
    ) -> None:
        with self._session_factory.begin() as session:
            upsert_spent_setup(
                session,
                setup_id=setup_id,
                symbol=symbol,
                marked_at=marked_at,
                reason=reason,
            )

    def spent_setup_ids(self) -> tuple[str, ...]:
        with self._session_factory() as session:
            return load_spent_setup_ids(session)

    def pending_entry_symbols(self) -> tuple[str, ...]:
        with self._session_factory() as session:
            rows = nonterminal_entry_intent_rows(session)
            return tuple(sorted({row.symbol for row in rows}))

    def recover_state(self) -> RestartRecoveryState:
        with self._session_factory() as session:
            pending_rows = nonterminal_entry_intent_rows(session)
            return RestartRecoveryState(
                pending_entry_intents=tuple(order_intent_from_row(row) for row in pending_rows),
                spent_setup_ids=load_spent_setup_ids(session),
            )

    def record_regime_snapshot(self, snapshot: RegimeSnapshot) -> None:
        with self._session_factory.begin() as session:
            upsert_regime_snapshot(session, snapshot)

    def load_regime_snapshot(self, session_date: date) -> RegimeSnapshot | None:
        with self._session_factory() as session:
            return load_regime_snapshot(session, session_date)

    def record_canonical_snapshot_hash(
        self,
        record: CanonicalSnapshotHashRecord,
    ) -> None:
        with self._session_factory.begin() as session:
            upsert_canonical_snapshot_hash(session, record)

    def load_canonical_snapshot_hash(
        self,
        *,
        symbol: str,
        session_date: date,
    ) -> CanonicalSnapshotHashRecord | None:
        with self._session_factory() as session:
            return load_canonical_snapshot_hash(
                session,
                symbol=symbol,
                session_date=session_date,
            )
