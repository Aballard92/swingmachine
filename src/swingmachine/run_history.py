from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from swingmachine.enums import RuntimeEventType, RuntimeMode
from swingmachine.storage import RuntimeEventRow, RuntimeRunRow


class RuntimeRunHistory:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_run(
        self,
        *,
        command: str,
        status: str,
        started_at: datetime,
        completed_at: datetime | None = None,
        mode: RuntimeMode | None = None,
        config_hash: str | None = None,
        input_path: str | None = None,
        output_path: str | None = None,
        detail: str | None = None,
        metrics: Mapping[str, object] | None = None,
    ) -> str:
        run_id = uuid4().hex
        metrics_json = None
        if metrics is not None:
            metrics_json = json.dumps(metrics, sort_keys=True, default=str)

        with self._session_factory.begin() as session:
            session.add(
                RuntimeRunRow(
                    run_id=run_id,
                    command=command,
                    status=status,
                    mode=None if mode is None else mode.value,
                    started_at=started_at,
                    completed_at=completed_at,
                    config_hash=config_hash,
                    input_path=input_path,
                    output_path=output_path,
                    detail=detail,
                    metrics_json=metrics_json,
                )
            )
        return run_id

    def record_event(
        self,
        *,
        command: str,
        event_type: RuntimeEventType,
        occurred_at: datetime | None = None,
        run_id: str | None = None,
        mode: RuntimeMode | None = None,
        symbol: str | None = None,
        setup_id: str | None = None,
        intent_id: str | None = None,
        output_path: str | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> str:
        event_id = uuid4().hex
        payload_json = None
        if payload is not None:
            payload_json = json.dumps(payload, sort_keys=True, default=str)

        with self._session_factory.begin() as session:
            session.add(
                RuntimeEventRow(
                    event_id=event_id,
                    run_id=run_id,
                    command=command,
                    event_type=event_type.value,
                    occurred_at=occurred_at or datetime.utcnow(),
                    mode=None if mode is None else mode.value,
                    symbol=symbol,
                    setup_id=setup_id,
                    intent_id=intent_id,
                    output_path=output_path,
                    payload_json=payload_json,
                )
            )
        return event_id

    def list_runs(self, *, limit: int = 100) -> tuple[dict[str, object], ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(RuntimeRunRow)
                .order_by(RuntimeRunRow.started_at.desc(), RuntimeRunRow.run_id.desc())
                .limit(limit)
            ).all()
        return tuple(_runtime_run_row_to_dict(row) for row in rows)

    def list_events(
        self,
        *,
        limit: int = 100,
        run_id: str | None = None,
        event_type: RuntimeEventType | None = None,
    ) -> tuple[dict[str, object], ...]:
        query = select(RuntimeEventRow)
        if run_id is not None:
            query = query.where(RuntimeEventRow.run_id == run_id)
        if event_type is not None:
            query = query.where(RuntimeEventRow.event_type == event_type.value)

        with self._session_factory() as session:
            rows = session.scalars(
                query.order_by(
                    RuntimeEventRow.occurred_at.desc(),
                    RuntimeEventRow.event_id.desc(),
                ).limit(limit)
            ).all()
        return tuple(_runtime_event_row_to_dict(row) for row in rows)


def _runtime_run_row_to_dict(row: RuntimeRunRow) -> dict[str, object]:
    metrics: object = None
    if row.metrics_json is not None:
        metrics = json.loads(row.metrics_json)
    return {
        "run_id": row.run_id,
        "command": row.command,
        "status": row.status,
        "mode": row.mode,
        "started_at": row.started_at.isoformat(),
        "completed_at": None if row.completed_at is None else row.completed_at.isoformat(),
        "config_hash": row.config_hash,
        "input_path": row.input_path,
        "output_path": row.output_path,
        "detail": row.detail,
        "metrics": metrics,
    }


def _runtime_event_row_to_dict(row: RuntimeEventRow) -> dict[str, object]:
    payload: object = None
    if row.payload_json is not None:
        payload = json.loads(row.payload_json)
    return {
        "event_id": row.event_id,
        "run_id": row.run_id,
        "command": row.command,
        "event_type": row.event_type,
        "occurred_at": row.occurred_at.isoformat(),
        "mode": row.mode,
        "symbol": row.symbol,
        "setup_id": row.setup_id,
        "intent_id": row.intent_id,
        "output_path": row.output_path,
        "payload": payload,
    }
