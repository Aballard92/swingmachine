"""Hand-calculated synthetic source/reference cases, with no provider access."""

import json
import struct
import subprocess
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta

import pytest

from swingmachine.research_daily import (
    NY,
    ActionCoverage,
    CalendarDay,
    CorporateAction,
    EarningsState,
    Minute,
    PopulationState,
    ReferenceBook,
    SecurityState,
    build_daily,
    reference_book_from_json,
)
from swingmachine.research_minute_source import stream_sources
from swingmachine.research_reset import file_hash
from tests.test_databento_audit import metadata

D = date(2019, 3, 8)
KNOWN = datetime(2018, 12, 1, tzinfo=UTC)


def instant(d, hour=9, minute=30):
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=NY)


def reference_fixture(start=D, days=45):
    calendar = []
    for offset in range(days):
        d = start + timedelta(days=offset)
        opened = d.weekday() < 5
        calendar.append(
            CalendarDay(
                d,
                instant(d) if opened else None,
                instant(d, 16, 0) if opened else None,
                KNOWN,
                f"calendar:{d}",
            )
        )
    end = calendar[-1].session
    return ReferenceBook(
        calendar,
        [
            SecurityState(
                "PERMANENT_A", start, KNOWN, "AAA", 42, "TECH", True, True, "security:initial"
            )
        ],
        [PopulationState("PERMANENT_A", start, KNOWN, True, "population:initial")],
        [ActionCoverage("PERMANENT_A", start, end, "actions:coverage")],
        [],
        [EarningsState("PERMANENT_A", KNOWN, start, end, (), "earnings:initial")],
    )


def minute(d=D, offset=0, **kw):
    return Minute(
        **{
            "timestamp": instant(d) + timedelta(minutes=offset),
            "instrument_id": 42,
            "raw_symbol": "AAA",
            "open": 100,
            "high": 105,
            "low": 99,
            "close": 102,
            "volume": 10,
            "source_id": "synthetic-source",
            "record_index": offset + 1,
            **kw,
        }
    )


def rebuild(book, **kw):
    return ReferenceBook(
        **{
            **{
                k: getattr(book, k)
                for k in (
                    "calendar",
                    "securities",
                    "population",
                    "action_coverage",
                    "actions",
                    "earnings",
                )
            },
            **kw,
        }
    )


def test_raw_ohlcv_lineage_and_sparse_minutes_are_preserved():
    result = build_daily(
        [
            minute(offset=-1, open=500, high=500, low=500, close=500),
            minute(),
            minute(offset=389, open=102, high=110, low=98, close=108, volume=25),
            minute(offset=390, open=600, high=600, low=600, close=600),
        ],
        reference_fixture(),
        D,
        D,
    )
    assert result.passed
    b = result.bars[0]
    assert (b.open, b.high, b.low, b.close, b.volume) == (100, 110, 98, 108, 35)
    assert b.eligible and b.event_known and b.symbol == "PERMANENT_A"
    assert result.diagnostics["counts"]["outside_regular_session"] == 2
    assert result.diagnostics["coverage"][0]["unprinted_minutes"] == 388
    assert result.lineage[0]["source_spans"]["synthetic-source"]["records"] == 2
    assert result.lineage[0]["calendar_ref"] == f"calendar:{D}"


def test_dst_and_closed_weekend_use_explicit_calendar():
    monday = D + timedelta(days=3)
    friday = replace(minute(), timestamp=datetime(2019, 3, 8, 14, 30, tzinfo=UTC))
    mon = replace(minute(monday), timestamp=datetime(2019, 3, 11, 13, 30, tzinfo=UTC))
    result = build_daily(
        [friday, minute(D + timedelta(days=1)), mon], reference_fixture(), D, monday
    )
    assert result.passed and len(result.bars) == 2
    assert result.diagnostics["counts"]["outside_regular_session"] == 1


def test_early_close_excludes_the_close_boundary_minute():
    book = reference_fixture()
    days = [replace(book.calendar[0], closes=instant(D, 13, 0)), *book.calendar[1:]]
    result = build_daily(
        [minute(), minute(offset=209), minute(offset=210, high=999)],
        rebuild(book, calendar=days),
        D,
        D,
    )
    assert result.passed
    assert result.bars[0].high == 105
    assert result.diagnostics["coverage"][0]["session_minutes"] == 210


def test_ticker_and_instrument_change_keep_permanent_identity():
    monday = D + timedelta(days=3)
    book = reference_fixture()
    new = replace(
        book.securities[0],
        effective_from=monday,
        known_at=instant(D, 15, 0),
        raw_symbol="RENAMED",
        instrument_id=99,
        ref_id="rename",
    )
    result = build_daily(
        [minute(), minute(monday, raw_symbol="RENAMED", instrument_id=99)],
        rebuild(book, securities=[*book.securities, new]),
        D,
        monday,
    )
    assert result.passed
    assert [b.symbol for b in result.bars] == ["PERMANENT_A", "PERMANENT_A"]
    assert [row["raw_symbol"] for row in result.lineage] == ["AAA", "RENAMED"]


def test_future_security_population_and_earnings_revisions_do_not_change_past():
    book = reference_fixture()
    before = build_daily([minute()], book, D, D)
    future = instant(D + timedelta(days=1))
    modified = rebuild(
        book,
        securities=[
            *book.securities,
            replace(
                book.securities[0],
                known_at=future,
                sector="WRONG",
                eligible=False,
                ref_id="future-security",
            ),
        ],
        population=[
            *book.population,
            replace(
                book.population[0], known_at=future, included=False, ref_id="future-population"
            ),
        ],
        earnings=[
            *book.earnings,
            replace(book.earnings[0], known_at=future, event_sessions=(D,), ref_id="future-event"),
        ],
    )
    after = build_daily([minute()], modified, D, D)
    assert before.bars == after.bars
    assert before.lineage == after.lineage


def test_split_and_distribution_are_explicit_raw_price_and_payment_facts():
    book = reference_fixture()
    event = CorporateAction(
        "event1", "PERMANENT_A", D, KNOWN, 2, 1.25, D + timedelta(days=7), "action:event1"
    )
    result = build_daily(
        [minute(open=50, high=51, low=49, close=50)], rebuild(book, actions=[event]), D, D
    )
    assert result.passed
    assert (result.bars[0].open, result.bars[0].split_ratio, result.bars[0].dividend) == (
        50,
        2,
        1.25,
    )
    assert result.action_events[0]["payment_session"] == "2019-03-15"
    assert result.lineage[0]["action_refs"] == ["action:event1"]


def test_later_action_revision_does_not_rewrite_effective_day():
    book = reference_fixture()
    event = CorporateAction("event1", "PERMANENT_A", D, KNOWN, 2, 0, None, "initial")
    later = replace(event, known_at=instant(D, 17), split_ratio=10, ref_id="later")
    result = build_daily([minute()], rebuild(book, actions=[event, later]), D, D)
    assert result.passed and result.bars[0].split_ratio == 2


def test_unavailable_effective_action_blocks_accounting():
    book = reference_fixture()
    event = CorporateAction("event1", "PERMANENT_A", D, instant(D, 17), 2, 0, None, "late")
    result = build_daily([minute()], rebuild(book, actions=[event]), D, D)
    assert not result.passed and not result.bars
    assert result.diagnostics["issues"][0]["code"] == "LATE_ACTION_KNOWLEDGE"


def test_no_action_is_not_inferred_from_absent_coverage():
    result = build_daily([minute()], rebuild(reference_fixture(), action_coverage=[]), D, D)
    assert not result.passed and not result.bars
    assert result.diagnostics["issues"][0]["code"] == "UNKNOWN_ACTION_COVERAGE"


def test_missing_next_day_does_not_change_previous_bar_or_eligibility():
    book = reference_fixture()
    first = build_daily([minute()], book, D, D)
    missing = build_daily([minute()], book, D, D + timedelta(days=3))
    assert first.bars == missing.bars and missing.bars[0].eligible
    assert not missing.passed
    assert missing.diagnostics["issues"][0]["code"] == "MISSING_EXPECTED_DAILY_BAR"


@pytest.mark.parametrize("kind", ["earnings", "population", "sector"])
def test_unknown_context_preserves_prices_and_disables_entry(kind):
    book = reference_fixture()
    changes = (
        {kind: []}
        if kind != "sector"
        else {"securities": [replace(book.securities[0], sector="UNKNOWN")]}
    )
    result = build_daily([minute()], rebuild(book, **changes), D, D)
    assert result.bars and not result.bars[0].eligible
    assert result.diagnostics["context_gaps"]


def test_known_upcoming_earnings_distance_uses_sessions_not_calendar_days():
    book = reference_fixture()
    monday = D + timedelta(days=3)
    book = rebuild(book, earnings=[replace(book.earnings[0], event_sessions=(monday,))])
    result = build_daily([minute()], book, D, D)
    assert result.bars[0].sessions_to_earnings == 1


def test_calendar_hole_is_not_treated_as_a_holiday():
    book = reference_fixture()
    with pytest.raises(ValueError, match="closed days"):
        rebuild(book, calendar=book.calendar[:1] + book.calendar[2:])


def test_calendar_cannot_retroactively_exclude_a_trading_day():
    with pytest.raises(ValueError, match="closed-day"):
        CalendarDay(D, None, None, instant(D, 17), "late-closure")


def test_closed_only_window_has_no_admitted_daily_bundle():
    saturday = D + timedelta(days=1)
    result = build_daily([], reference_fixture(), saturday, saturday)
    assert not result.passed
    assert result.diagnostics["issues"][0]["code"] == "EMPTY_SESSION_WINDOW"


def test_event_beyond_holding_horizon_does_not_get_truncated_to_horizon():
    book = reference_fixture()
    book = rebuild(
        book, earnings=[replace(book.earnings[0], event_sessions=(D + timedelta(days=40),))]
    )
    result = build_daily([minute()], book, D, D)
    assert result.bars[0].event_known
    assert result.bars[0].sessions_to_earnings is None


def test_unlisted_state_is_retained_even_without_a_price():
    book = reference_fixture()
    monday = D + timedelta(days=3)
    unlisted = replace(
        book.securities[0],
        effective_from=monday,
        known_at=instant(D, 15),
        listed=False,
        eligible=False,
        ref_id="delisting-state",
    )
    result = build_daily(
        [minute()], rebuild(book, securities=[*book.securities, unlisted]), D, monday
    )
    state = result.reference_states[-1]
    assert not state["listed"] and not state["price_present"]
    assert state["security_ref"] == "delisting-state"
    assert len(result.bars) == 1  # no invented terminal price or cash proceeds


def test_duplicate_mapping_and_source_minutes_are_rejected():
    book = reference_fixture()
    with pytest.raises(ValueError, match="duplicate timestamp"):
        build_daily([minute(), minute(source_id="another-source")], book, D, D)
    with pytest.raises(ValueError, match="ambiguous effective"):
        build_daily(
            [minute()],
            rebuild(
                book,
                securities=[*book.securities, replace(book.securities[0], security_id="OTHER")],
            ),
            D,
            D,
        )


def test_protected_window_is_rejected_before_iterating_prices():
    def forbidden():
        raise AssertionError("price stream must remain unopened")
        yield

    with pytest.raises(ValueError, match="holdout"):
        build_daily(forbidden(), reference_fixture(), date(2023, 1, 1), date(2023, 1, 2))


def json_value(value):
    return json.loads(json.dumps(value, default=lambda x: x.isoformat()))


def test_reference_json_roundtrip_and_naive_time_rejection():
    book = reference_fixture()
    value = json_value(
        {
            k: [asdict(r) for r in getattr(book, k)]
            for k in (
                "calendar",
                "securities",
                "population",
                "action_coverage",
                "actions",
                "earnings",
            )
        }
    )
    assert reference_book_from_json(value).calendar == book.calendar
    value["securities"][0]["known_at"] = "2018-12-01T00:00:00"
    with pytest.raises(ValueError, match="aware"):
        reference_book_from_json(value)


def test_jsonl_source_is_hashed_and_merged_by_timestamp(tmp_path):
    items = []
    for name, row in [("second", minute(offset=1)), ("first", minute())]:
        data = asdict(row)
        data.pop("source_id")
        data.pop("record_index")
        path = tmp_path / f"{name}.jsonl"
        path.write_text(json.dumps(json_value(data)) + "\n")
        items.append(
            {
                "path": path.name,
                "format": "jsonl",
                "sha256": file_hash(path),
                "start": str(D),
                "end": str(D),
            }
        )
    rows = list(stream_sources(tmp_path, items, D, D))
    assert [r.timestamp.minute for r in rows] == [30, 31]
    assert rows[0].source_id == items[1]["sha256"]
    (tmp_path / items[0]["path"]).write_text("changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        list(stream_sources(tmp_path, items, D, D))


def test_narrow_dbn_stream_decodes_fixture_and_lineage(tmp_path):
    d = date(2019, 1, 2)
    timestamp = int(instant(d).timestamp()) * 10**9
    record = struct.pack(
        "<BBHIQqqqqQ",
        14,
        33,
        2,
        42,
        timestamp,
        100 * 10**9,
        102 * 10**9,
        99 * 10**9,
        101 * 10**9,
        123,
    )
    path = tmp_path / "fixture.dbn.zst"
    path.write_bytes(
        subprocess.run(
            ["zstd", "-c"], input=metadata() + record, capture_output=True, check=True
        ).stdout
    )
    item = {
        "path": path.name,
        "format": "dbn-v1-ohlcv-1m",
        "start": "2019-01-02",
        "end": "2019-01-31",
        "sha256": file_hash(path),
    }
    rows = list(stream_sources(tmp_path, [item], d, d))
    assert len(rows) == 1
    assert (rows[0].open, rows[0].close, rows[0].volume, rows[0].raw_symbol) == (
        100,
        101,
        123,
        "AAA",
    )
    assert rows[0].record_index == 0


def test_all_source_date_guards_run_before_any_file_is_opened(tmp_path):
    item = {
        "path": "missing",
        "format": "jsonl",
        "start": str(D),
        "end": str(D),
        "sha256": "0" * 64,
    }
    protected = {**item, "path": "protected", "start": "2023-01-01", "end": "2023-12-31"}
    with pytest.raises(ValueError, match="holdout"):
        list(stream_sources(tmp_path, [item, protected], D, D))
