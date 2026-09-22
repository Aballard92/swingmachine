"""Streaming daily aggregation and explicit, decision-time reference joins.

No inferred holiday calendar, price adjustment factors, or earnings completeness.
The reference objects are inputs requiring provenance, not facts invented here.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from swingmachine.research_reset import Bar, guard_research_dates

NY = ZoneInfo("America/New_York")


def aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("an aware timestamp is required")


def text_fields(*values: str) -> None:
    if any(not isinstance(x, str) or not x.strip() for x in values):
        raise ValueError("nonempty identity/provenance fields required")


@dataclass(frozen=True)
class CalendarDay:
    session: date
    opens: datetime | None
    closes: datetime | None
    known_at: datetime
    ref_id: str

    def __post_init__(self):
        aware(self.known_at)
        text_fields(self.ref_id)
        if (self.opens is None) != (self.closes is None):
            raise ValueError("closed days need both session bounds absent")
        if self.opens is None and self.known_at > datetime.combine(self.session, time(9, 30), NY):
            raise ValueError("a closed-day declaration must be known before the regular open")
        if self.opens is not None:
            aware(self.opens)
            aware(self.closes)
            if not self.known_at <= self.opens < self.closes:
                raise ValueError("calendar must be known before an increasing session interval")
            if any(x.astimezone(NY).date() != self.session for x in (self.opens, self.closes)):
                raise ValueError("session bounds must fall on the declared New York date")
            if any(x.second or x.microsecond for x in (self.opens, self.closes)):
                raise ValueError("session bounds must be minute aligned")


@dataclass(frozen=True)
class Minute:
    timestamp: datetime
    instrument_id: int
    raw_symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    source_id: str
    record_index: int

    def __post_init__(self):
        aware(self.timestamp)
        text_fields(self.raw_symbol, self.source_id)
        if self.timestamp.second or self.timestamp.microsecond:
            raise ValueError("minute timestamp must mark the interval start")
        if any(
            type(v) is not int or v < 0
            for v in (self.instrument_id, self.record_index, self.volume)
        ):
            raise ValueError("instrument, index and volume must be nonnegative integers")
        if any(
            type(v) not in (int, float) or not math.isfinite(v)
            for v in (self.open, self.high, self.low, self.close)
        ):
            raise ValueError("finite numeric OHLC required")
        if (
            not 0
            < self.low
            <= min(self.open, self.close)
            <= max(self.open, self.close)
            <= self.high
        ):
            raise ValueError("invalid minute OHLC")


@dataclass(frozen=True)
class SecurityState:
    security_id: str
    effective_from: date
    known_at: datetime
    raw_symbol: str
    instrument_id: int
    sector: str
    listed: bool
    eligible: bool
    ref_id: str

    def __post_init__(self):
        aware(self.known_at)
        text_fields(self.security_id, self.raw_symbol, self.sector, self.ref_id)
        if type(self.instrument_id) is not int or self.instrument_id < 0:
            raise ValueError("invalid instrument identifier")
        if type(self.listed) is not bool or type(self.eligible) is not bool:
            raise ValueError("explicit listed/eligible flags required")


@dataclass(frozen=True)
class PopulationState:
    security_id: str
    effective_from: date
    known_at: datetime
    included: bool
    ref_id: str

    def __post_init__(self):
        aware(self.known_at)
        text_fields(self.security_id, self.ref_id)
        if type(self.included) is not bool:
            raise ValueError("explicit population inclusion required")


@dataclass(frozen=True)
class ActionCoverage:
    """Retrospective feed-completeness evidence; never a trading signal."""

    security_id: str
    start: date
    end: date
    ref_id: str

    def __post_init__(self):
        text_fields(self.security_id, self.ref_id)
        if self.start > self.end:
            raise ValueError("reversed action coverage")


@dataclass(frozen=True)
class CorporateAction:
    event_id: str
    security_id: str
    ex_session: date
    known_at: datetime
    split_ratio: float
    dividend: float
    payment_session: date | None
    ref_id: str

    def __post_init__(self):
        aware(self.known_at)
        text_fields(self.event_id, self.security_id, self.ref_id)
        if any(
            type(v) not in (int, float) or not math.isfinite(v)
            for v in (self.split_ratio, self.dividend)
        ):
            raise ValueError("finite action amounts required")
        if self.split_ratio <= 0 or self.dividend < 0:
            raise ValueError("invalid corporate action")
        if self.dividend and (
            self.payment_session is None or self.payment_session < self.ex_session
        ):
            raise ValueError("cash distributions require an explicit payment date on/after ex date")


@dataclass(frozen=True)
class EarningsState:
    security_id: str
    known_at: datetime
    coverage_start: date
    coverage_end: date
    event_sessions: tuple[date, ...]
    ref_id: str

    def __post_init__(self):
        aware(self.known_at)
        text_fields(self.security_id, self.ref_id)
        if self.coverage_start > self.coverage_end:
            raise ValueError("reversed earnings coverage")
        if tuple(sorted(set(self.event_sessions))) != self.event_sessions:
            raise ValueError("earnings events must be unique and increasing")
        if any(not self.coverage_start <= d <= self.coverage_end for d in self.event_sessions):
            raise ValueError("earnings event outside declared coverage")


@dataclass
class ReferenceBook:
    calendar: list[CalendarDay]
    securities: list[SecurityState]
    population: list[PopulationState]
    action_coverage: list[ActionCoverage]
    actions: list[CorporateAction]
    earnings: list[EarningsState]
    _index: dict = field(init=False, repr=False)

    def __post_init__(self):
        days = [d.session for d in self.calendar]
        if not days or days != sorted(set(days)):
            raise ValueError("calendar days must be unique and increasing")
        if len(days) != (days[-1] - days[0]).days + 1:
            raise ValueError(
                "calendar must explicitly include closed days; dates cannot be omitted"
            )
        self._index = {}
        for role in ("securities", "population", "action_coverage", "actions", "earnings"):
            grouped = defaultdict(list)
            seen = set()
            for row in getattr(self, role):
                key = (
                    row.security_id,
                    getattr(row, "effective_from", None),
                    getattr(row, "known_at", None),
                    getattr(row, "event_id", None),
                    getattr(row, "start", None),
                    getattr(row, "end", None),
                )
                if key in seen:
                    raise ValueError(f"ambiguous duplicate {role} reference")
                seen.add(key)
                grouped[row.security_id].append(row)
            self._index[role] = grouped

    def state(self, role: str, security_id: str, session: date, at: datetime):
        available = [
            r
            for r in self._index[role].get(security_id, [])
            if r.known_at <= at and r.effective_from <= session
        ]
        # Effective state takes precedence; a later correction to an older state
        # cannot replace an already effective newer state.
        return max(available, key=lambda r: (r.effective_from, r.known_at), default=None)

    def earnings_at(self, security_id: str, at: datetime):
        rows = [r for r in self._index["earnings"].get(security_id, []) if r.known_at <= at]
        return max(rows, key=lambda r: r.known_at, default=None)


@dataclass
class DailyBuild:
    bars: list[Bar]
    lineage: list[dict]
    action_events: list[dict]
    diagnostics: dict
    reference_states: list[dict] = field(default_factory=list)

    @property
    def passed(self):
        return not self.diagnostics["issues"]


def build_daily(
    minutes: Iterable[Minute],
    references: ReferenceBook,
    start: date,
    end: date,
    max_hold: int = 20,
) -> DailyBuild:
    """Consume sorted minutes once; memory grows with daily aggregates, not minutes.

    Daily raw_symbol changes do not change the permanent Bar.symbol identifier.
    Missing data is recorded globally; it never selects a profitable subset.
    """
    guard_research_dates(start, end)
    if type(max_hold) is not int or not 1 <= max_hold <= 20:
        raise ValueError("holding horizon must be 1..20 sessions")
    calendar = {d.session: d for d in references.calendar}
    if start not in calendar or end not in calendar:
        raise ValueError("calendar does not cover the full requested interval")
    sessions = [d for d in references.calendar if d.opens is not None]
    session_indices = {d.session: i for i, d in enumerate(sessions)}
    report = {
        "status": "BLOCKED",
        "issues": [],
        "context_gaps": [],
        "counts": Counter(),
        "coverage": [],
    }
    out = DailyBuild([], [], [], report)

    def problem(code, session, security_id, detail):
        report["issues"].append(
            {
                "code": code,
                "session": session.isoformat(),
                "security_id": security_id,
                "detail": detail,
            }
        )

    if not any(start <= d.session <= end for d in sessions):
        problem("EMPTY_SESSION_WINDOW", start, "ALL", "No open sessions in the requested interval.")
        return out

    aggregates: dict[tuple, dict] = {}
    previous = None
    at_timestamp = set()
    for minute in minutes:
        d = minute.timestamp.astimezone(NY).date()
        if not start <= d <= end:
            raise ValueError("minute lies outside the declared build interval")
        if previous is not None and minute.timestamp < previous:
            raise ValueError("minute stream must be ordered by timestamp")
        if minute.timestamp != previous:
            at_timestamp.clear()
        if minute.instrument_id in at_timestamp:
            raise ValueError("duplicate timestamp/instrument across minute sources")
        at_timestamp.add(minute.instrument_id)
        previous = minute.timestamp
        report["counts"]["input_minutes"] += 1
        day = calendar[d]
        if day.opens is None or not day.opens <= minute.timestamp < day.closes:
            report["counts"]["outside_regular_session"] += 1
            continue
        key = (d, minute.instrument_id, minute.raw_symbol)
        a = aggregates.get(key)
        if a is None:
            a = aggregates[key] = {
                "open": minute.open,
                "high": minute.high,
                "low": minute.low,
                "close": minute.close,
                "volume": 0,
                "first": minute.timestamp,
                "last": minute.timestamp,
                "minutes": 0,
                "sources": {},
            }
        a["high"], a["low"] = max(a["high"], minute.high), min(a["low"], minute.low)
        a["close"], a["last"] = minute.close, minute.timestamp
        a["volume"] += minute.volume
        a["minutes"] += 1
        span = a["sources"].setdefault(
            minute.source_id,
            {"first_record": minute.record_index, "last_record": minute.record_index, "records": 0},
        )
        span["last_record"] = minute.record_index
        span["records"] += 1
    by_session = defaultdict(dict)
    for (d, iid, name), a in aggregates.items():
        by_session[d][(iid, name)] = a

    all_ids = sorted(set(references._index["securities"]) | set(references._index["population"]))
    for day in sessions:
        d = day.session
        if not start <= d <= end:
            continue
        mapping, states = {}, {}
        for sid in all_ids:
            state = references.state("securities", sid, d, day.closes)
            population = references.state("population", sid, d, day.closes)
            if state is None:
                if population and population.included:
                    problem(
                        "MISSING_SECURITY_STATE",
                        d,
                        sid,
                        "Included security has no state known at the close.",
                    )
                continue
            key = (state.instrument_id, state.raw_symbol)
            if key in mapping:
                raise ValueError("ambiguous effective instrument/security mapping")
            mapping[key], states[sid] = sid, (state, population)
            out.reference_states.append(
                {
                    "session": d.isoformat(),
                    "security_id": sid,
                    "raw_symbol": state.raw_symbol,
                    "instrument_id": state.instrument_id,
                    "listed": state.listed,
                    "security_eligible": state.eligible,
                    "population_included": population.included if population else None,
                    "security_known_at": state.known_at.isoformat(),
                    "security_effective_from": state.effective_from.isoformat(),
                    "security_ref": state.ref_id,
                    "population_ref": population.ref_id if population else None,
                    "price_present": key in by_session[d],
                }
            )
            if population and population.included and state.listed and key not in by_session[d]:
                problem(
                    "MISSING_EXPECTED_DAILY_BAR",
                    d,
                    sid,
                    "No regular-session price; halt/no-trade/feed gap unresolved; no forward fill.",
                )
        for key, a in sorted(by_session[d].items()):
            sid = mapping.get(key)
            if sid is None:
                problem(
                    "UNRESOLVED_IDENTITY",
                    d,
                    str(key[0]),
                    "No matching raw-symbol/instrument state known at the close.",
                )
                continue
            state, population = states[sid]
            coverage = [
                c
                for c in references._index["action_coverage"].get(sid, [])
                if c.start <= d <= c.end
            ]
            if not coverage:
                problem(
                    "UNKNOWN_ACTION_COVERAGE",
                    d,
                    sid,
                    "Cannot assert a no-action day without action-feed evidence.",
                )
                continue
            # Event revisions after the session cannot alter its features/accounting.
            versions = {}
            late_events = set()
            for event in references._index["actions"].get(sid, []):
                if event.ex_session != d:
                    continue
                if event.known_at > day.opens:
                    late_events.add(event.event_id)
                    continue
                old = versions.get(event.event_id)
                if old is None or event.known_at > old.known_at:
                    versions[event.event_id] = event
            if late_events - versions.keys():
                problem(
                    "LATE_ACTION_KNOWLEDGE",
                    d,
                    sid,
                    "Effective action was not available before the session; accounting unresolved.",
                )
                continue
            ratio = math.prod(e.split_ratio for e in versions.values())
            dividend = sum(e.dividend for e in versions.values())
            earnings = references.earnings_at(sid, day.closes)
            index = session_indices[d]
            horizon = (
                sessions[index + max_hold].session if index + max_hold < len(sessions) else None
            )
            event_known = bool(
                earnings
                and horizon
                and earnings.coverage_start <= d
                and earnings.coverage_end >= horizon
            )
            distance = None
            if event_known:
                next_event = next((e for e in earnings.event_sessions if e >= d), None)
                if next_event is not None and next_event <= horizon:
                    # Events on nontrading days block the next exposed holding day.
                    distance = sum(d < s.session <= next_event for s in sessions)
            eligible = bool(
                population
                and population.included
                and state.listed
                and state.eligible
                and state.sector != "UNKNOWN"
                and event_known
            )
            gaps = []
            if population is None:
                gaps.append("UNKNOWN_POPULATION_STATE")
            if not event_known:
                gaps.append("UNKNOWN_EARNINGS_HORIZON")
            if state.sector == "UNKNOWN":
                gaps.append("UNKNOWN_SECTOR")
            if gaps:
                report["context_gaps"].append(
                    {"session": d.isoformat(), "security_id": sid, "reasons": gaps}
                )
            out.bars.append(
                Bar(
                    d,
                    sid,
                    a["open"],
                    a["high"],
                    a["low"],
                    a["close"],
                    a["volume"],
                    ratio,
                    dividend,
                    state.sector,
                    event_known,
                    distance,
                    eligible,
                )
            )
            for event in sorted(versions.values(), key=lambda e: e.event_id):
                event_row = asdict(event)
                event_row.update(
                    ex_session=d.isoformat(),
                    known_at=event.known_at.isoformat(),
                    payment_session=event.payment_session.isoformat()
                    if event.payment_session
                    else None,
                )
                out.action_events.append(event_row)
            minutes_expected = int((day.closes - day.opens).total_seconds() // 60)
            report["coverage"].append(
                {
                    "session": d.isoformat(),
                    "security_id": sid,
                    "observed_minutes": a["minutes"],
                    "session_minutes": minutes_expected,
                    "unprinted_minutes": minutes_expected - a["minutes"],
                    "gap_interpretation": "no trade or unavailable data; unresolved",
                }
            )
            out.lineage.append(
                {
                    "session": d.isoformat(),
                    "security_id": sid,
                    "raw_symbol": key[1],
                    "instrument_id": key[0],
                    "first_print": a["first"].isoformat(),
                    "last_print": a["last"].isoformat(),
                    "decision_at": day.closes.isoformat(),
                    "calendar_ref": day.ref_id,
                    "security_ref": state.ref_id,
                    "population_ref": population.ref_id if population else None,
                    "earnings_ref": earnings.ref_id if earnings else None,
                    "action_coverage_refs": sorted(c.ref_id for c in coverage),
                    "action_refs": sorted(e.ref_id for e in versions.values()),
                    "source_spans": a["sources"],
                    "price_convention": "raw venue-session OHLCV; split-only prefix features; "
                    "distributions in ledger",
                }
            )
    out.bars.sort(key=lambda b: (b.session, b.symbol))
    report["counts"]["daily_bars"] = len(out.bars)
    report["counts"]["eligible_bars"] = sum(b.eligible for b in out.bars)
    if not report["issues"]:
        report["status"] = "ADAPTER_MECHANICS_PASS_NOT_SOURCE_QUALIFICATION"
    return out


def reference_book_from_json(value: dict) -> ReferenceBook:
    """Strict typed conversion of the six retained reference tables."""
    tables = {}
    definitions = {
        "calendar": (CalendarDay, {"session"}, {"opens", "closes", "known_at"}),
        "securities": (SecurityState, {"effective_from"}, {"known_at"}),
        "population": (PopulationState, {"effective_from"}, {"known_at"}),
        "action_coverage": (ActionCoverage, {"start", "end"}, set()),
        "actions": (CorporateAction, {"ex_session", "payment_session"}, {"known_at"}),
        "earnings": (EarningsState, {"coverage_start", "coverage_end"}, {"known_at"}),
    }
    for name, (cls, dates, timestamps) in definitions.items():
        rows = value[name]
        if not isinstance(rows, list):
            raise ValueError(f"reference table {name} must be an array")
        tables[name] = []
        for original in rows:
            row = dict(original)
            for key in dates:
                if row.get(key) is not None:
                    row[key] = date.fromisoformat(row[key])
            for key in timestamps:
                if row.get(key) is not None:
                    row[key] = (
                        datetime.fromisoformat(row[key]).astimezone(UTC)
                        if datetime.fromisoformat(row[key]).tzinfo
                        else datetime.fromisoformat(row[key])
                    )
            if name == "earnings":
                row["event_sessions"] = tuple(date.fromisoformat(d) for d in row["event_sessions"])
            tables[name].append(cls(**row))
    return ReferenceBook(**tables)
