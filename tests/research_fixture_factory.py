"""Reusable artificial minute/reference bundle, explicitly not market evidence."""

import json
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta

from swingmachine.research_daily import (
    ActionCoverage,
    CalendarDay,
    EarningsState,
    PopulationState,
    SecurityState,
)
from swingmachine.research_reset import file_hash
from tests.test_research_daily import instant, json_value
from tests.test_research_reset_cli import make_source


def make_minute_bundle(root):
    root.mkdir(parents=True, exist_ok=True)
    _, source = make_source(root)
    daily_rows = json.loads((root / source["bars_path"]).read_text())
    first, last = date.fromisoformat(source["start"]), date.fromisoformat(source["end"])
    known = datetime(2018, 1, 1, tzinfo=UTC)
    final_reference_day = last + timedelta(days=20)
    # Artificial calendar deliberately mirrors the original reset fixture's
    # consecutive days. No claim is made that weekends were actual sessions.
    calendar = [
        CalendarDay(d, instant(d), instant(d, 16, 0), known, f"calendar:{d}")
        for d in [first + timedelta(days=i) for i in range((final_reference_day - first).days + 1)]
    ]
    names = sorted({r["symbol"] for r in daily_rows})
    ids = {s: i + 1 for i, s in enumerate(names)}
    references = {
        "calendar": calendar,
        "securities": [
            SecurityState(
                s, first, known, s, ids[s], str(ids[s]), True, s != "SPY", f"security:{s}"
            )
            for s in names
        ],
        "population": [PopulationState(s, first, known, True, f"population:{s}") for s in names],
        "action_coverage": [
            ActionCoverage(s, first, final_reference_day, f"coverage:{s}") for s in names
        ],
        "actions": [],
        "earnings": [
            EarningsState(s, known, first, final_reference_day, (), f"earnings:{s}") for s in names
        ],
    }
    reference_path = root / "reference_tables.json"
    reference_path.write_text(
        json.dumps(json_value({k: [asdict(r) for r in rows] for k, rows in references.items()}))
    )
    minutes = []
    for row in daily_rows:
        d = date.fromisoformat(row["session"])
        base = {k: row[k] for k in ("open", "high", "low", "close")}
        base.update(instrument_id=ids[row["symbol"]], raw_symbol=row["symbol"])
        minutes.append(
            {
                **base,
                "timestamp": instant(d).isoformat(),
                "high": row["open"],
                "low": row["open"],
                "close": row["open"],
                "volume": 250_000,
            }
        )
        minutes.append({**base, "timestamp": instant(d, 15, 59).isoformat(), "volume": 750_000})
    minutes.sort(key=lambda m: (m["timestamp"], m["instrument_id"]))
    minute_path = root / "synthetic_minutes.jsonl"
    minute_path.write_text("".join(json.dumps(row) + "\n" for row in minutes))
    spec = {
        "version": 1,
        "source_class": "SYNTHETIC_FIXTURE",
        "start": source["start"],
        "end": source["end"],
        "evaluation_start": source["evaluation_start"],
        "references_path": reference_path.name,
        "references_sha256": file_hash(reference_path),
        "minute_sources": [
            {
                "path": minute_path.name,
                "format": "jsonl",
                "sha256": file_hash(minute_path),
                "start": source["start"],
                "end": source["end"],
            }
        ],
    }
    path = root / "build_manifest.json"
    path.write_text(json.dumps(spec, indent=2))
    return path, spec


def make_execution_bundle(root, sessions=210):
    """Denser artificial opening tape; daily OHLCV is preserved, no market facts."""
    manifest, spec = make_minute_bundle(root)
    path = root / spec["minute_sources"][0]["path"]
    original = [json.loads(line) for line in path.read_text().splitlines()]
    last = date.fromisoformat(spec["start"]) + timedelta(days=sessions - 1)
    expanded = []
    for row in original:
        stamp = datetime.fromisoformat(row["timestamp"])
        if stamp.date() > last:
            continue
        if stamp.hour == 9:
            for offset in range(15):
                expanded.append(
                    {
                        **row,
                        "timestamp": (stamp + timedelta(minutes=offset)).isoformat(),
                        "high": row["open"] + 0.05,
                        "low": row["open"] - 0.05,
                        "volume": 20000,
                    }
                )
        else:
            expanded.append({**row, "volume": 700000})
    expanded.sort(key=lambda r: (r["timestamp"], r["instrument_id"]))
    path.write_text("".join(json.dumps(r) + "\n" for r in expanded))
    spec["end"] = str(last)
    spec["minute_sources"][0].update(end=str(last), sha256=file_hash(path))
    manifest.write_text(json.dumps(spec, indent=2))
    references = json.loads((root / spec["references_path"]).read_text())
    settlement = root / "settlement_calendar.json"
    settlement.write_text(
        json.dumps(
            {
                "version": 1,
                "source_class": "SYNTHETIC_FIXTURE",
                "ref_id": "artificial-consecutive-settlement-dates",
                "availability_policy": "all fixture dates declared before simulation; "
                "not actual clearing dates",
                "dates": [r["session"] for r in references["calendar"]],
            },
            indent=2,
        )
    )
    return manifest, settlement
