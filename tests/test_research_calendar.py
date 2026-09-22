"""Retained-source calendar validation and daily-reference integration."""

import json
import shutil
import subprocess
import sys
from datetime import UTC, date, timedelta

import pytest

from swingmachine.research_calendar import (
    CALENDAR_FILE,
    DEFAULT_BUNDLE,
    calendar_reference_bundle,
    verify_calendar,
)
from swingmachine.research_daily import NY, reference_book_from_json
from swingmachine.research_reset import file_hash
from tests.test_research_reset_cli import REPO


def test_official_calendar_reparse_and_publication_provenance():
    frozen, report = verify_calendar()
    assert (report["sessions"], report["closures"], report["early_closes"]) == (1258, 45, 9)
    assert report["year_session_counts"] == {
        "2019": 252,
        "2020": 253,
        "2021": 252,
        "2022": 251,
        "2023": 250,
    }
    assert not report["historical_calendar_version_claim"]
    assert report["observed_prices_read"] == 0
    assert [s["publication_date"] for s in report["sources"]] == ["2018-12-04", "2021-12-27", None]
    assert "2022-06-20" in {r["day"] for r in frozen["closures"]}


def test_dst_early_close_closed_dates_and_reference_roundtrip():
    value, _ = calendar_reference_bundle(date(2019, 1, 2), date(2019, 12, 31))
    book = reference_book_from_json(value)
    rows = {r.session.isoformat(): r for r in book.calendar}
    assert rows["2019-03-08"].opens.astimezone(UTC).hour == 14
    assert rows["2019-03-11"].opens.astimezone(UTC).hour == 13
    assert rows["2019-11-04"].opens.astimezone(UTC).hour == 14
    for label in ("2019-07-03", "2019-11-29", "2019-12-24"):
        row = rows[label]
        assert row.closes.astimezone(NY).hour == 13
        assert row.closes - row.opens == timedelta(minutes=210)
    for label in ("2019-07-04", "2019-07-06", "2019-07-07"):
        assert rows[label].opens is rows[label].closes is None
    assert all(r.known_at.date() == date(2018, 12, 5) for r in book.calendar)
    assert not book.securities and not book.actions and not book.earnings


def test_calendar_only_horizon_may_cross_protected_price_boundary():
    value, report = calendar_reference_bundle(date(2020, 11, 30), date(2020, 11, 30))
    assert report["calendar_end_including_lookahead"] == "2020-12-29"
    assert sum(r["opens"] is not None for r in value["calendar"][1:]) == 20
    assert report["source_qualification"] == "CALENDAR_ONLY_NOT_A_QUALIFIED_PRICE_BUNDLE"


@pytest.mark.parametrize("which", ["calendar", "capture"])
def test_calendar_or_capture_tampering_fails(tmp_path, which):
    bundle = tmp_path / "bundle"
    shutil.copytree(DEFAULT_BUNDLE, bundle)
    manifest = bundle / CALENDAR_FILE
    target = (
        manifest
        if which == "calendar"
        else bundle / json.loads(manifest.read_text())["sources"][0]["captured_path"]
    )
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_calendar(bundle)


def test_capture_symlink_cannot_escape_bundle(tmp_path):
    bundle = tmp_path / "bundle"
    shutil.copytree(DEFAULT_BUNDLE, bundle)
    frozen = json.loads((bundle / CALENDAR_FILE).read_text())
    path = bundle / frozen["sources"][0]["captured_path"]
    outside = tmp_path / "outside"
    path.rename(outside)
    path.symlink_to(outside)
    with pytest.raises(ValueError, match="escapes bundle"):
        verify_calendar(bundle)


@pytest.mark.parametrize("horizon", [-1, 253, True, 1.5])
def test_invalid_horizon_rejected(horizon):
    with pytest.raises(ValueError, match="horizon"):
        calendar_reference_bundle(date(2019, 1, 2), date(2019, 1, 3), horizon)


def test_protected_price_request_rejected_before_reading_calendar(tmp_path):
    with pytest.raises(ValueError, match="holdout"):
        calendar_reference_bundle(date(2023, 1, 2), date(2023, 1, 3), bundle=tmp_path)


def test_calendar_cli_emits_usable_reference_skeleton_and_receipt(tmp_path):
    output = tmp_path / "calendar"
    run = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/run_research_reset.py"),
            "build-calendar",
            "--start",
            "2019-01-02",
            "--end",
            "2019-01-31",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    receipt = json.loads((output / "calendar_receipt.json").read_text())
    assert receipt["reference_tables_sha256"] == file_hash(output / "reference_tables.json")
    refs = reference_book_from_json(json.loads((output / "reference_tables.json").read_text()))
    assert len(refs.calendar) == 59  # January 2 through March 1; February has 19 sessions
    assert refs.calendar[-1].session == date(2019, 3, 1)
    assert receipt["strategy_calculations"] == 0
    assert not (output / "daily_bars.json").exists()
