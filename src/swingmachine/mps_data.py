from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from typing import Protocol, TypeVar

from swingmachine.mps_contracts import (
    CorporateActionRecord,
    DailyPriceRecord,
    DataNotAvailableError,
    EarningsAnnouncementRecord,
    PointInTimeRecord,
    SecurityMasterRecord,
)

RecordT = TypeVar("RecordT", bound=PointInTimeRecord)


class TradingCalendar(Protocol):
    def is_session(self, session_date: date) -> bool: ...
    def next_session(self, session_date: date) -> date: ...
    def sessions(self, start: date, end: date) -> tuple[date, ...]: ...


class StaticTradingCalendar:
    def __init__(self, sessions: Sequence[date]) -> None:
        ordered = tuple(sorted(set(sessions)))
        if not ordered:
            raise ValueError("calendar requires at least one session")
        self._sessions = ordered
        self._positions = {session: index for index, session in enumerate(ordered)}

    def is_session(self, session_date: date) -> bool:
        return session_date in self._positions

    def next_session(self, session_date: date) -> date:
        if session_date not in self._positions:
            raise KeyError(f"unknown session {session_date}")
        position = self._positions[session_date] + 1
        if position >= len(self._sessions):
            raise KeyError(f"no next session after {session_date}")
        return self._sessions[position]

    def sessions(self, start: date, end: date) -> tuple[date, ...]:
        return tuple(session for session in self._sessions if start <= session <= end)


class PointInTimeDataPortal:
    """Deterministic in-memory portal used by backtest and dry-run adapters.

    Every returned record satisfies available_at <= decision_timestamp. A request
    for a specific record that exists only in the future fails closed.
    """

    def __init__(
        self,
        *,
        security_master: Iterable[SecurityMasterRecord],
        prices: Iterable[DailyPriceRecord],
        corporate_actions: Iterable[CorporateActionRecord] = (),
        earnings: Iterable[EarningsAnnouncementRecord] = (),
    ) -> None:
        self._security_master = self._ordered(security_master)
        self._prices = self._ordered(prices)
        self._corporate_actions = self._ordered(corporate_actions)
        self._earnings = self._ordered(earnings)

    @staticmethod
    def _ordered(records: Iterable[RecordT]) -> tuple[RecordT, ...]:
        return tuple(
            sorted(
                records,
                key=lambda item: (item.event_time, item.available_at, item.source_record_id),
            )
        )

    @staticmethod
    def _known(records: Iterable[RecordT], decision_timestamp: datetime) -> tuple[RecordT, ...]:
        return tuple(record for record in records if record.known_at(decision_timestamp))

    def security_master_as_of(
        self, decision_timestamp: datetime
    ) -> tuple[SecurityMasterRecord, ...]:
        known = self._known(self._security_master, decision_timestamp)
        active: dict[str, SecurityMasterRecord] = {}
        for record in known:
            if record.effective_from <= decision_timestamp and (
                record.effective_to is None or decision_timestamp <= record.effective_to
            ):
                previous = active.get(record.security_id)
                if previous is None or (record.available_at, record.source_record_id) > (
                    previous.available_at,
                    previous.source_record_id,
                ):
                    active[record.security_id] = record
        return tuple(sorted(active.values(), key=lambda item: (item.ticker, item.security_id)))

    def price(
        self, security_id: str, session_date: date, decision_timestamp: datetime
    ) -> DailyPriceRecord:
        matches = [
            record
            for record in self._prices
            if record.security_id == security_id and record.session_date == session_date
        ]
        known = [record for record in matches if record.known_at(decision_timestamp)]
        if not known:
            if matches:
                raise DataNotAvailableError(
                    f"price for {security_id} on {session_date} was not available at "
                    f"{decision_timestamp.isoformat()}"
                )
            raise KeyError(f"missing price for {security_id} on {session_date}")
        return max(known, key=lambda item: (item.available_at, item.source_record_id))

    def prices_through(
        self, security_id: str, end_session: date, decision_timestamp: datetime
    ) -> tuple[DailyPriceRecord, ...]:
        known = self._known(self._prices, decision_timestamp)
        latest: dict[date, DailyPriceRecord] = {}
        for record in known:
            if record.security_id != security_id or record.session_date > end_session:
                continue
            previous = latest.get(record.session_date)
            if previous is None or (record.available_at, record.source_record_id) > (
                previous.available_at,
                previous.source_record_id,
            ):
                latest[record.session_date] = record
        return tuple(latest[session] for session in sorted(latest))

    def corporate_actions_for_date(
        self, effective_date: date, decision_timestamp: datetime
    ) -> tuple[CorporateActionRecord, ...]:
        return tuple(
            record
            for record in self._known(self._corporate_actions, decision_timestamp)
            if record.effective_date == effective_date
        )

    def known_earnings(
        self, decision_timestamp: datetime
    ) -> tuple[EarningsAnnouncementRecord, ...]:
        return self._known(self._earnings, decision_timestamp)

    def version_hash(self) -> str:
        records = (*self._security_master, *self._prices, *self._corporate_actions, *self._earnings)
        payload = [record.model_dump(mode="json") for record in records]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
