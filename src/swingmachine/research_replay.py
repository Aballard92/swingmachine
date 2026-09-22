"""Bind daily signal inputs to the same minute/reference source used for fills."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import date, timedelta
from itertools import groupby
from pathlib import Path

from swingmachine.research_benchmark import PassiveBenchmark
from swingmachine.research_daily import NY, ReferenceBook, build_daily, reference_book_from_json
from swingmachine.research_execution import ExecutionPolicy, ExecutionSimulator
from swingmachine.research_minute_source import bundle_path, stream_sources
from swingmachine.research_reset import SignalEngine, guard_research_dates
from swingmachine.research_source import SourceAdmission, _unique_object


@dataclass
class ReplayInputs:
    manifest: dict
    root: Path
    references: ReferenceBook
    policy: ExecutionPolicy
    settlement_dates: list[date]
    receipt: dict


def load_replay_inputs(
    admission: SourceAdmission,
    minute_manifest: Path,
    policy_path: Path,
    settlement_path: Path,
    source_root: Path | None = None,
) -> ReplayInputs:
    """Complete structural reconciliation before constructing a strategy engine."""
    if not admission.passed:
        raise ValueError("daily admission required before minute replay")
    if admission.source["source_class"] != "SYNTHETIC_FIXTURE":
        raise ValueError("historical replay awaits RF-003 qualification and RF-005 freeze")
    hashes = {}

    def read(path, label, expected=None):
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if expected is not None and digest != expected:
            raise ValueError(f"replay {label} hash mismatch")
        hashes[label] = digest
        value = json.loads(payload, object_pairs_hook=_unique_object)
        if not isinstance(value, dict):
            raise ValueError(f"replay {label} must be an object")
        return value

    spec = read(minute_manifest, "minute_manifest")
    start, end = date.fromisoformat(spec["start"]), date.fromisoformat(spec["end"])
    guard_research_dates(start, end)
    if type(spec.get("version")) is not int or spec["version"] != 1:
        raise ValueError("unsupported replay source version")
    if spec["source_class"] != admission.source["source_class"]:
        raise ValueError("daily and minute source classes disagree")
    if not start <= admission.sessions[0] <= admission.sessions[-1] <= end:
        raise ValueError("daily and minute date boundaries disagree")
    references = reference_book_from_json(
        read(
            bundle_path(minute_manifest.parent, spec["references_path"]),
            "reference_tables",
            spec["references_sha256"],
        )
    )
    sessions = [d.session for d in references.calendar if d.opens and start <= d.session <= end]
    if sessions != admission.sessions:
        raise ValueError("daily and minute exchange sessions disagree")
    policy = ExecutionPolicy(**read(policy_path, "execution_policy"))
    settlements = read(settlement_path, "settlement_calendar")
    if (
        type(settlements.get("version")) is not int
        or settlements["version"] != 1
        or settlements["source_class"] != admission.source["source_class"]
        or not settlements.get("ref_id")
        or not settlements.get("availability_policy")
    ):
        raise ValueError("explicit matching settlement calendar provenance required")
    dates = [date.fromisoformat(d) for d in settlements["dates"]]
    if not dates or dates != sorted(set(dates)) or dates[0] > sessions[0]:
        raise ValueError("settlement calendar coverage/order invalid")
    if sum(d > sessions[-1] for d in dates) < policy.settlement_days:
        raise ValueError("settlement calendar lookahead incomplete")
    root = source_root or minute_manifest.parent
    rebuilt = build_daily(
        stream_sources(root, spec["minute_sources"], start, end), references, start, end
    )
    expected = {(b.session, b.symbol): b for rows in admission.by_date.values() for b in rows}
    actual = {(b.session, b.symbol): b for b in rebuilt.bars}
    if not rebuilt.passed or actual != expected:
        raise ValueError("daily signal bars do not reconcile to minute/reference inputs")
    receipt = {
        "status": "SYNTHETIC_DAILY_MINUTE_RECONCILIATION_PASS",
        "sha256": hashes,
        "daily_rows_compared": len(actual),
        "sessions": len(sessions),
        "minute_sources": spec["minute_sources"],
        "strategy_calculations": 0,
        "execution_policy": read(policy_path, "execution_policy", hashes["execution_policy"]),
        "settlement_calendar_ref": settlements["ref_id"],
        "settlement_availability_policy": settlements["availability_policy"],
        "historical_qualification": "NOT_GRANTED",
        "benchmark_protocol": "FUNDED_FIXED_LIMIT_SPY_AND_LAGGED_EXPOSURE_V1",
    }
    return ReplayInputs(spec, root, references, policy, dates, receipt)


def _actions(book, day):
    versions, late = {}, set()
    for action in book.actions:
        if action.ex_session != day.session:
            continue
        key = (action.security_id, action.event_id)
        if action.known_at > day.opens:
            late.add(key)
        elif key not in versions or versions[key].known_at < action.known_at:
            versions[key] = action
    if late - versions.keys():
        raise ValueError("late effective action prevents executable accounting")
    return list(versions.values())


def _decision_context(book, day, sim, ideas, calendar_sessions):
    at = day.opens + timedelta(minutes=sim.policy.decision_minutes)
    entry, held = {}, {}
    index = calendar_sessions.index(day.session)
    horizon = calendar_sessions[index + sim.config.max_hold]
    for symbol in sim.positions.keys() | {i.symbol for i in ideas}:
        state = book.state("securities", symbol, day.session, at)
        population = book.state("population", symbol, day.session, at)
        if state:
            held[symbol] = state.sector
        earnings = book.earnings_at(symbol, at)
        covered = (
            earnings and earnings.coverage_start <= day.session and earnings.coverage_end >= horizon
        )
        event_free = covered and not any(
            day.session <= d <= horizon for d in earnings.event_sessions
        )
        if (
            state
            and state.listed
            and state.eligible
            and state.sector != "UNKNOWN"
            and population
            and population.included
            and event_free
        ):
            entry[symbol] = state.sector
    return entry, held


def run_replay(admission: SourceAdmission, inputs: ReplayInputs) -> list[dict]:
    """One source stream fans out to all frozen synthetic family/cost trials."""
    if not admission.passed or admission.source["source_class"] != "SYNTHETIC_FIXTURE":
        raise ValueError("historical replay remains unavailable before qualification/freeze")
    book, spec = inputs.references, inputs.manifest
    start, end = date.fromisoformat(spec["start"]), date.fromisoformat(spec["end"])
    calendar_sessions = [d.session for d in book.calendar if d.opens]
    if len(calendar_sessions) - calendar_sessions.index(admission.sessions[-1]) <= max(
        c.max_hold for c in admission.configs
    ):
        raise ValueError("execution context needs full holding-horizon calendar metadata")
    planning_cost = admission.plan["signal_planning_cost_bps_per_side"]
    engines = [SignalEngine(replace(c, cost_bps_per_side=planning_cost)) for c in admission.configs]
    sims = [
        ExecutionSimulator(c, inputs.policy, inputs.settlement_dates) for c in admission.configs
    ]
    pending = [[] for _ in sims]
    benchmarks = {
        c.cost_bps_per_side: PassiveBenchmark(c.initial_cash, c.cost_bps_per_side, inputs.policy)
        for c in admission.configs
    }
    stream = stream_sources(inputs.root, spec["minute_sources"], start, end)
    groups = groupby(stream, key=lambda b: b.timestamp.astimezone(NY).date())
    current = next(groups, None)
    try:
        for day in book.calendar:
            if not start <= day.session <= end:
                continue
            if current is not None and current[0] < day.session:
                raise ValueError("minute date missing from reference calendar")
            raw_rows = list(current[1]) if current is not None and current[0] == day.session else []
            if current is not None and current[0] == day.session:
                current = next(groups, None)
            if not day.opens:
                if raw_rows:
                    raise ValueError("price source contains observations on a declared closed day")
                continue
            # Warmup features still use the exact reconciled daily source.
            if day.session < admission.evaluation_start:
                for n, engine in enumerate(engines):
                    pending[n] = engine.observe(admission.by_date[day.session])
                continue
            actions = _actions(book, day)
            for n, sim in enumerate(sims):
                entry, held = _decision_context(book, day, sim, pending[n], calendar_sessions)
                sim.start_session(day, pending[n], actions, entry, held)
            for benchmark in benchmarks.values():
                benchmark.start_session(day, actions)
            by_time = {}
            for minute in raw_rows:
                if day.opens <= minute.timestamp < day.closes:
                    by_time.setdefault(minute.timestamp, []).append(minute)
            clock = day.opens
            while clock < day.closes:
                raw = by_time.get(clock, [])
                rows = {}
                if raw:
                    mapping = {}
                    for symbol in book._index["securities"]:
                        state = book.state("securities", symbol, day.session, clock)
                        if state:
                            key = (state.instrument_id, state.raw_symbol)
                            if key in mapping:
                                raise ValueError("ambiguous executable identity mapping")
                            mapping[key] = symbol
                    for minute in raw:
                        symbol = mapping.get((minute.instrument_id, minute.raw_symbol))
                        if symbol is None or symbol in rows:
                            raise ValueError("unresolved or duplicate executable minute identity")
                        rows[symbol] = minute
                for sim in sims:
                    sim.on_minute(clock, rows)
                for benchmark in benchmarks.values():
                    benchmark.on_minute(clock, rows.get("SPY"))
                clock += timedelta(minutes=1)
            for n, (engine, sim) in enumerate(zip(engines, sims, strict=True)):
                sim.finish_session()
                pending[n] = engine.observe(admission.by_date[day.session])
            for benchmark in benchmarks.values():
                benchmark.finish_session()
        if current is not None:
            raise ValueError("unconsumed minute source dates")
    finally:
        stream.close()
    return [
        sim.result()
        | {
            "source_class": admission.source["source_class"],
            "signal_planning_cost_bps": planning_cost,
            "benchmark": benchmarks[sim.config.cost_bps_per_side].result(),
        }
        for sim in sims
    ]
