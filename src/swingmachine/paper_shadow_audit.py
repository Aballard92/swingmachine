from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from swingmachine.analytics import (
    paper_shadow_alignment_stats,
    paper_shadow_audit_to_frame,
    paper_shadow_regime_stats,
    summarize_paper_shadow_audit,
)
from swingmachine.contracts import PaperShadowAuditRecord
from swingmachine.enums import (
    BrokerOrderStatus,
    OrderIntentStatus,
    OrderReason,
    PaperShadowAlignmentStatus,
    RegimeState,
)
from swingmachine.storage import (
    BrokerOrderRow,
    OrderIntentRow,
    ShadowFillComparisonRow,
    load_paper_shadow_audit_snapshots,
    record_paper_shadow_audit_snapshot,
    shadow_fill_comparison_from_row,
)

_FILLED_BROKER_STATUSES = {BrokerOrderStatus.FILLED}
_FILLED_INTENT_STATUSES = {OrderIntentStatus.FILLED}


def _paper_filled(
    *,
    intent_status: OrderIntentStatus | None,
    broker_status: BrokerOrderStatus | None,
) -> bool:
    return intent_status in _FILLED_INTENT_STATUSES or broker_status in _FILLED_BROKER_STATUSES


def _alignment_status(
    *,
    paper_present: bool,
    paper_filled: bool,
    shadow_present: bool,
    shadow_would_fill: bool | None,
) -> PaperShadowAlignmentStatus:
    if shadow_present and not paper_present:
        return PaperShadowAlignmentStatus.SHADOW_ONLY
    if paper_present and not shadow_present:
        return PaperShadowAlignmentStatus.PAPER_ONLY
    if shadow_would_fill and paper_filled:
        return PaperShadowAlignmentStatus.ALIGNED_FILLED
    if not shadow_would_fill and not paper_filled:
        return PaperShadowAlignmentStatus.ALIGNED_NOT_FILLED
    if shadow_would_fill and not paper_filled:
        return PaperShadowAlignmentStatus.SHADOW_FILLED_PAPER_NOT_FILLED
    return PaperShadowAlignmentStatus.SHADOW_NOT_FILLED_PAPER_FILLED


def _audit_payload(
    records: tuple[PaperShadowAuditRecord, ...],
    *,
    snapshot_batch_id: str | None = None,
) -> dict[str, Any]:
    return {
        "snapshot_batch_id": snapshot_batch_id,
        "summary": summarize_paper_shadow_audit(records),
        "by_alignment": paper_shadow_alignment_stats(records).to_dict(orient="records"),
        "by_regime": paper_shadow_regime_stats(records).to_dict(orient="records"),
        "rows": paper_shadow_audit_to_frame(records).to_dict(orient="records"),
    }


class PaperShadowAuditService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def load_records(
        self,
        *,
        symbol: str | None = None,
        regime_state: RegimeState | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[PaperShadowAuditRecord, ...]:
        with self._session_factory() as session:
            order_query = (
                select(OrderIntentRow)
                .where(OrderIntentRow.reason == OrderReason.ENTRY.value)
                .order_by(OrderIntentRow.created_at, OrderIntentRow.intent_id)
            )
            if symbol is not None:
                order_query = order_query.where(OrderIntentRow.symbol == symbol)
            if date_from is not None:
                order_query = order_query.where(
                    OrderIntentRow.created_at >= datetime.combine(date_from, datetime.min.time())
                )
            if date_to is not None:
                order_query = order_query.where(
                    OrderIntentRow.created_at < datetime.combine(date_to, datetime.max.time())
                )

            order_rows = session.scalars(order_query).all()
            order_row_by_intent = {row.intent_id: row for row in order_rows}

            broker_rows = session.scalars(
                select(BrokerOrderRow)
                .where(
                    BrokerOrderRow.intent_id.in_(list(order_row_by_intent.keys()))
                    if order_row_by_intent
                    else False
                )
                .order_by(BrokerOrderRow.created_at, BrokerOrderRow.broker_order_id)
            ).all()
            broker_row_by_intent = {row.intent_id: row for row in broker_rows}

            shadow_query = select(ShadowFillComparisonRow).order_by(
                ShadowFillComparisonRow.source_as_of,
                ShadowFillComparisonRow.session_date,
                ShadowFillComparisonRow.intent_id,
            )
            if symbol is not None:
                shadow_query = shadow_query.where(ShadowFillComparisonRow.symbol == symbol)
            if regime_state is not None:
                shadow_query = shadow_query.where(
                    ShadowFillComparisonRow.source_regime_state == regime_state.value
                )
            if date_from is not None:
                shadow_query = shadow_query.where(
                    ShadowFillComparisonRow.source_as_of
                    >= datetime.combine(date_from, datetime.min.time())
                )
            if date_to is not None:
                shadow_query = shadow_query.where(
                    ShadowFillComparisonRow.source_as_of
                    < datetime.combine(date_to, datetime.max.time())
                )

            shadow_rows = session.scalars(shadow_query).all()
            shadow_by_intent = {
                row.intent_id: shadow_fill_comparison_from_row(row) for row in shadow_rows
            }

        if regime_state is not None:
            order_row_by_intent = {
                intent_id: row
                for intent_id, row in order_row_by_intent.items()
                if (
                    intent_id in shadow_by_intent
                    and shadow_by_intent[intent_id].source_regime_state == regime_state
                )
            }
            broker_row_by_intent = {
                intent_id: row
                for intent_id, row in broker_row_by_intent.items()
                if intent_id in order_row_by_intent
            }

        intent_ids = sorted(set(order_row_by_intent) | set(shadow_by_intent))
        records: list[PaperShadowAuditRecord] = []
        for intent_id in intent_ids:
            order_row = order_row_by_intent.get(intent_id)
            broker_row = broker_row_by_intent.get(intent_id)
            shadow = shadow_by_intent.get(intent_id)

            paper_intent_status = None if order_row is None else OrderIntentStatus(order_row.status)
            paper_broker_status = (
                None if broker_row is None else BrokerOrderStatus(broker_row.status)
            )
            paper_filled = _paper_filled(
                intent_status=paper_intent_status,
                broker_status=paper_broker_status,
            )
            shadow_would_fill = None if shadow is None else shadow.would_fill

            records.append(
                PaperShadowAuditRecord(
                    intent_id=intent_id,
                    symbol=(
                        order_row.symbol
                        if order_row is not None
                        else shadow.symbol
                        if shadow is not None
                        else ""
                    ),
                    setup_id=(
                        order_row.setup_id
                        if order_row is not None
                        else None
                        if shadow is None
                        else shadow.setup_id
                    ),
                    created_at=(None if order_row is None else order_row.created_at),
                    source_as_of=(None if shadow is None else shadow.source_as_of),
                    source_regime_state=(None if shadow is None else shadow.source_regime_state),
                    alignment_status=_alignment_status(
                        paper_present=order_row is not None,
                        paper_filled=paper_filled,
                        shadow_present=shadow is not None,
                        shadow_would_fill=shadow_would_fill,
                    ),
                    paper_intent_present=order_row is not None,
                    paper_intent_status=paper_intent_status,
                    broker_order_id=(None if order_row is None else order_row.broker_order_id),
                    paper_broker_status=paper_broker_status,
                    paper_filled=paper_filled,
                    shadow_present=shadow is not None,
                    shadow_status=None if shadow is None else shadow.status,
                    shadow_would_fill=shadow_would_fill,
                    shadow_session_date=None if shadow is None else shadow.session_date,
                    shadow_hypothetical_fill_price=(
                        None if shadow is None else shadow.hypothetical_fill_price
                    ),
                    shadow_total_cost_bps=(None if shadow is None else shadow.total_cost_bps),
                    shadow_slippage_alert_triggered=(
                        False if shadow is None else shadow.slippage_alert is not None
                    ),
                )
            )

        return tuple(records)

    def record_snapshot_batch(
        self,
        records: tuple[PaperShadowAuditRecord, ...],
        *,
        recorded_at: datetime | None = None,
        snapshot_batch_id: str | None = None,
    ) -> str:
        batch_id = snapshot_batch_id or uuid4().hex
        timestamp = recorded_at or datetime.utcnow()
        with self._session_factory.begin() as session:
            for record in records:
                record_paper_shadow_audit_snapshot(
                    session,
                    record,
                    snapshot_batch_id=batch_id,
                    recorded_at=timestamp,
                )
        return batch_id

    def load_record_snapshots(
        self,
        *,
        snapshot_batch_id: str | None = None,
        symbol: str | None = None,
        regime_state: RegimeState | None = None,
        recorded_from: date | None = None,
        recorded_to: date | None = None,
    ) -> tuple[PaperShadowAuditRecord, ...]:
        with self._session_factory() as session:
            return load_paper_shadow_audit_snapshots(
                session,
                snapshot_batch_id=snapshot_batch_id,
                symbol=symbol,
                regime_state=regime_state,
                recorded_from=recorded_from,
                recorded_to=recorded_to,
            )

    def summarize_records(
        self,
        *,
        symbol: str | None = None,
        regime_state: RegimeState | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        records = self.load_records(
            symbol=symbol,
            regime_state=regime_state,
            date_from=date_from,
            date_to=date_to,
        )
        return _audit_payload(records)

    def summarize_record_snapshots(
        self,
        *,
        snapshot_batch_id: str | None = None,
        symbol: str | None = None,
        regime_state: RegimeState | None = None,
        recorded_from: date | None = None,
        recorded_to: date | None = None,
    ) -> dict[str, Any]:
        records = self.load_record_snapshots(
            snapshot_batch_id=snapshot_batch_id,
            symbol=symbol,
            regime_state=regime_state,
            recorded_from=recorded_from,
            recorded_to=recorded_to,
        )
        return _audit_payload(records, snapshot_batch_id=snapshot_batch_id)
