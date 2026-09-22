"""Verify and convert the retained Trading212 official-source calendar.

Adapted from the independent table/footnote reparse and month-grid verifier
bd09258d8d8e2f71086b0901a3865d655a18f5f196b8bd57db4e4a86d94687ca.
Reads metadata only. Never derives a session calendar from observed prices.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import re
from dataclasses import asdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

from swingmachine.research_daily import NY, CalendarDay
from swingmachine.research_reset import guard_research_dates
from swingmachine.research_source import _unique_object

CALENDAR_FILE = "xnys_session_calendar_2019_2023_v1.json"
CALENDAR_SHA256 = "d0b12e24e20ac5bb6c5f22709cffd69af79fc2549298c53d5a7db5fd29f3c2fd"
CALENDAR_FINGERPRINT = "506afb3f5660d8ee321c9cff9ad314f63eb9f9bb40ea5adf835d180f4252b21f"
DEFAULT_BUNDLE = Path(__file__).resolve().parents[2] / "config/research/calendar_trading212_v1"
PUBLICATIONS = {"ice-2019-2021": date(2018, 12, 4), "ice-2022-2024": date(2021, 12, 27)}


def _checked_bytes(path: Path, expected: str) -> bytes:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("calendar evidence hash mismatch")
    return data


def _official_dates(text: str, years: tuple[int, ...]) -> tuple[set[str], set[str]]:
    """Reconstruct the two fixed official tables; reject format/count drift."""
    months = {name: i for i, name in enumerate(calendar.month_name) if name}
    weekdays = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
    pattern = rf"(?:{weekdays}), (\w+) (\d{{1,2}})"
    table = text[text.index("HOLIDAY  |") :]
    terminator = "* Each market" if years[0] == 2019 else "* No holiday"
    table = table[: table.index(terminator)]
    rows = re.split(
        r"(?m)^(?=New Year|Martin Luther|Washington|Good Friday|Memorial|Juneteenth|"
        r"Independence|Labor|Thanksgiving|Christmas)",
        table,
    )[1:]
    if len(rows) != (9 if years[0] == 2019 else 10):
        raise ValueError("official holiday table row count changed")
    closed, early = set(), set()

    def keep(target: set[str], year: int, month: str, day: str) -> None:
        value = str(date(year, months[month], int(day)))
        if "2019-01-02" <= value < "2024-01-01":
            target.add(value)

    for row in rows:
        found = re.findall(pattern, row)
        expected = years[1:] if years[0] == 2022 and row.startswith("New Year") else years
        if len(found) != len(expected):
            raise ValueError("official holiday date count changed")
        for year, (month, day) in zip(expected, found, strict=True):
            keep(closed, year, month, day)
    for row in text.splitlines():
        if "Each market will close early at 1:00 p.m." in row:
            for month, day, year in re.findall(pattern + r", (\d{4})", row):
                keep(early, int(year), month, day)
    return closed, early


def verify_calendar(bundle: Path = DEFAULT_BUNDLE) -> tuple[dict, dict]:
    """Rehash retained evidence and independently reconstruct all 1,258 sessions."""
    root = bundle.resolve()
    payload = _checked_bytes(root / CALENDAR_FILE, CALENDAR_SHA256)
    frozen = json.loads(payload, object_pairs_hook=_unique_object)
    # Trading212 canonical JSON includes a newline; Swing's generic hash does not.
    semantic = {k: v for k, v in frozen.items() if k != "calendar_fingerprint"}
    canonical = (json.dumps(semantic, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if hashlib.sha256(canonical).hexdigest() != CALENDAR_FINGERPRINT:
        raise ValueError("calendar semantic fingerprint mismatch")
    closed, early, sources = set(), set(), []
    for source in frozen["sources"]:
        relative = Path(source["captured_path"])
        path = (root / relative).resolve()
        if relative.is_absolute() or ".." in relative.parts or not path.is_relative_to(root):
            raise ValueError("calendar capture escapes bundle")
        data = _checked_bytes(path, source["captured_sha256"])
        if len(data) != source["captured_bytes"]:
            raise ValueError("calendar capture size mismatch")
        text = re.sub(r"^L\d+: ?", "", data.decode(), flags=re.M)
        source = dict(source)
        if source["id"] in PUBLICATIONS:
            pub = PUBLICATIONS[source["id"]]
            stamp = f"{calendar.month_abbr[pub.month]} {pub.day:02}, {pub.year}"
            if not re.search(rf"(?m)^{re.escape(stamp)}\s*$", text):
                raise ValueError("calendar publication date missing from capture")
            years = (2019, 2020, 2021) if pub.year == 2018 else (2022, 2023, 2024)
            c, e = _official_dates(text, years)
            closed.update(c)
            early.update(e)
            source["publication_date"] = str(pub)
            source["known_at_basis"] = "following_local_midnight_after_printed_publication_date"
        else:
            source["publication_date"] = None
            source["known_at_basis"] = "current_hours_capture_only_no_historical_version_claim"
        sources.append(source)
    if closed != {r["day"] for r in frozen["closures"]}:
        raise ValueError("official closures disagree with frozen calendar")
    if early != {r["day"] for r in frozen["early_closes"]}:
        raise ValueError("official early closes disagree with frozen calendar")
    expected = {}
    for year in range(2019, 2024):
        for month in range(1, 13):
            for day, weekday in calendar.Calendar().itermonthdays2(year, month):
                if not day or weekday >= 5:
                    continue
                label = str(date(year, month, day))
                if label >= "2019-01-02" and label not in closed:
                    expected[label] = 210 if label in early else 390
    if expected != {r["day"]: r["minutes"] for r in frozen["sessions"]} or len(expected) != len(
        frozen["sessions"]
    ):
        raise ValueError("official calendar month-grid reconstruction failed")
    report = {
        "status": "VERIFIED_CALENDAR_METADATA",
        "calendar_sha256": CALENDAR_SHA256,
        "calendar_fingerprint": CALENDAR_FINGERPRINT,
        "sessions": len(expected),
        "closures": len(closed),
        "early_closes": len(early),
        "year_session_counts": frozen["year_session_counts"],
        "verification": "official_table_and_footnote_reparse_plus_independent_month_grid",
        "sources": sources,
        "historical_calendar_version_claim": False,
        "observed_prices_read": 0,
        "strategy_calculations": 0,
        "limits": [
            "XNYS regular-session research policy for XNAS venue bars; not auction execution proof",
            "later source captures are not archived as-of page versions",
            "known_at reflects printed holiday/early-close publication dates; "
            "regular hours are an explicit fixed research assumption",
            "calendar metadata does not qualify security, action, earnings or price data",
        ],
    }
    return frozen, report


def calendar_reference_bundle(
    start: date, end: date, horizon_sessions: int = 20, bundle: Path = DEFAULT_BUNDLE
) -> tuple[dict, dict]:
    """Build calendar rows plus explicitly empty remaining reference tables.

    Prices for start..end must be permitted. Calendar-only lookahead can cross a
    protected price boundary; this function never opens a price source.
    """
    guard_research_dates(start, end)
    if type(horizon_sessions) is not int or not 0 <= horizon_sessions <= 252:
        raise ValueError("calendar horizon must be an integer from 0 to 252")
    frozen, report = verify_calendar(bundle)
    if start < date(2019, 1, 2) or end >= date(2024, 1, 1):
        raise ValueError("requested dates exceed verified calendar coverage")
    sessions = {date.fromisoformat(r["day"]): r["minutes"] for r in frozen["sessions"]}
    future = [d for d in sessions if d > end]
    if len(future) < horizon_sessions:
        raise ValueError("insufficient verified calendar lookahead")
    final = future[horizon_sessions - 1] if horizon_sessions else end
    rows = []
    day = start
    while day <= final:
        source_id = "ice-2019-2021" if day.year <= 2021 else "ice-2022-2024"
        known_at = datetime.combine(PUBLICATIONS[source_id] + timedelta(days=1), time(), NY)
        opens = datetime.combine(day, time(9, 30), NY) if day in sessions else None
        closes = opens + timedelta(minutes=sessions[day]) if opens else None
        row = CalendarDay(day, opens, closes, known_at, f"{CALENDAR_FINGERPRINT}:{source_id}")
        rows.append(
            {
                k: v.isoformat() if isinstance(v, (date, datetime)) else v
                for k, v in asdict(row).items()
            }
        )
        day += timedelta(days=1)
    remaining = ["securities", "population", "action_coverage", "actions", "earnings"]
    result = {"calendar": rows, **{k: [] for k in remaining}}
    report.update(
        {
            "requested_price_start": str(start),
            "requested_price_end": str(end),
            "calendar_end_including_lookahead": str(final),
            "horizon_sessions": horizon_sessions,
            "calendar_rows": len(rows),
            "reference_tables_still_required": remaining,
            "source_qualification": "CALENDAR_ONLY_NOT_A_QUALIFIED_PRICE_BUNDLE",
        }
    )
    return result, report
