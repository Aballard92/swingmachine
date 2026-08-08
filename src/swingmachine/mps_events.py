from __future__ import annotations

from datetime import date
from enum import IntEnum
from typing import Protocol

from swingmachine.modeling import ImmutableModel


class MpsSessionPhase(IntEnum):
    APPLY_CORPORATE_ACTIONS = 10
    PROCESS_PENDING_EXITS = 20
    PROCESS_GAP_STOPS = 30
    RECONCILE_OPEN_STATE = 40
    PROCESS_ENTRIES = 50
    ESTABLISH_INITIAL_STOPS = 60
    PROCESS_INTRADAY_STOPS = 70
    MARK_TO_MARKET = 80
    BUILD_ELIGIBLE_UNIVERSE = 90
    CALCULATE_FEATURES_AND_RANKS = 100
    GENERATE_EXIT_ORDERS = 110
    GENERATE_ENTRY_CANDIDATES = 120
    UPDATE_TRAILING_STOPS = 130
    WRITE_AUDIT_RECORD = 140


class MpsSessionEvent(ImmutableModel):
    session_date: date
    phase: MpsSessionPhase
    sequence: int


class MpsEventHandler(Protocol):
    def handle(self, event: MpsSessionEvent) -> None: ...


class MpsEventLoop:
    """Single deterministic phase sequence shared by research and dry-run adapters."""

    phases = tuple(MpsSessionPhase)

    def events_for_session(self, session_date: date) -> tuple[MpsSessionEvent, ...]:
        return tuple(
            MpsSessionEvent(session_date=session_date, phase=phase, sequence=index)
            for index, phase in enumerate(self.phases, start=1)
        )

    def run_session(
        self, session_date: date, handler: MpsEventHandler
    ) -> tuple[MpsSessionEvent, ...]:
        events = self.events_for_session(session_date)
        for event in events:
            handler.handle(event)
        return events
