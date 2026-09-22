"""End-to-end offline mechanical fixtures; generated prices are not market evidence."""

import json
import math
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from swingmachine.research_reset import file_hash

REPO = Path(__file__).resolve().parents[1]


def make_source(tmp_path):
    sessions = [date(2019, 1, 2) + timedelta(days=x) for x in range(260)]
    rows = []
    for index, d in enumerate(sessions):
        for n, symbol in enumerate(["SPY", "A", "B", "C", "D", "E"]):

            def price(day, phase=n):
                return 100 + day * 0.2 + 4 * math.sin(day / 4 + phase)

            op, cl = price(max(0, index - 1)), price(index)
            rows.append(
                {
                    "session": d.isoformat(),
                    "symbol": symbol,
                    "open": op,
                    "close": cl,
                    "high": max(op, cl) + 0.2,
                    "low": min(op, cl) - 0.2,
                    "volume": 1_000_000,
                    "event_known": True,
                    "eligible": symbol != "SPY",
                    "sector": str(n),
                }
            )
    bars = tmp_path / "synthetic_bars.json"
    bars.write_text(json.dumps(rows))
    source = {
        "source_class": "SYNTHETIC_FIXTURE",
        "start": sessions[0].isoformat(),
        "end": sessions[-1].isoformat(),
        "evaluation_start": sessions[200].isoformat(),
        "sessions": [d.isoformat() for d in sessions],
        "bars_path": bars.name,
        "bars_sha256": file_hash(bars),
        "adjustment_policy": "raw_with_explicit_splits_and_dividend_accrual",
        "corporate_actions_complete": True,
        "event_calendar_complete": True,
        "session_calendar_complete": True,
    }
    manifest = tmp_path / "synthetic_manifest.json"
    manifest.write_text(json.dumps(source))
    return manifest, source


def run(manifest, output):
    return subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/run_research_reset.py"),
            "simulate-daily-fixture",
            "--manifest",
            str(manifest),
            "--plan",
            str(REPO / "config/research_reset_v1.json"),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_all_nine_trials_freeze_inputs_and_reconcile(tmp_path):
    manifest, _ = make_source(tmp_path)
    output = tmp_path / "results"
    result = run(manifest, output)
    assert result.returncode == 0, result.stderr
    summaries = json.loads((output / "summary.json").read_text())
    freeze = json.loads((output / "pre_outcome_freeze.json").read_text())
    assert len(summaries) == freeze["trials"] == 9
    assert freeze["source_class"] == "SYNTHETIC_FIXTURE"
    for s in summaries:
        assert s["closed_trades"] > 0
        assert s["sessions"] == s["benchmark"]["sessions"] == 60
        assert abs(s["accounting_residual"]) < 1e-7
        assert s["status"] == "MECHANICAL_RESEARCH_ONLY"
    # Same exact source/config/code produces identical strategy evidence.
    second = tmp_path / "rerun"
    assert run(manifest, second).returncode == 0
    assert (second / "summary.json").read_bytes() == (output / "summary.json").read_bytes()


def test_incomplete_corporate_actions_block_before_any_trial(tmp_path):
    manifest, source = make_source(tmp_path)
    source["corporate_actions_complete"] = False
    manifest.write_text(json.dumps(source))
    output = tmp_path / "blocked"
    assert run(manifest, output).returncode != 0
    assert "corporate_actions_complete" in (output / "FAILED.json").read_text()
    assert not (output / "summary.json").exists()


def test_mutated_source_blocks_before_results(tmp_path):
    manifest, source = make_source(tmp_path)
    (tmp_path / source["bars_path"]).write_text("[]")
    output = tmp_path / "changed"
    assert run(manifest, output).returncode != 0
    assert "hash mismatch" in (output / "FAILED.json").read_text()


def test_frozen_holdout_blocks_before_bar_read(tmp_path):
    manifest = tmp_path / "holdout_manifest.json"
    manifest.write_text(json.dumps({"start": "2023-01-01", "end": "2023-12-31"}))
    output = tmp_path / "holdout"
    assert run(manifest, output).returncode != 0
    assert "holdout" in (output / "FAILED.json").read_text()
