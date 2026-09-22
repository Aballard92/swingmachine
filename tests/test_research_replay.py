"""The active research CLI uses reconciled minutes and fixed order intents."""

import json
import subprocess
import sys
from dataclasses import replace
from datetime import timedelta

import pytest

from swingmachine.research_replay import _decision_context, load_replay_inputs
from swingmachine.research_source import preflight
from tests.research_fixture_factory import make_execution_bundle
from tests.test_research_daily_cli import command
from tests.test_research_execution import D, day, engine, idea
from tests.test_research_reset_cli import REPO, make_source

POLICY = REPO / "config/research_execution_v1.json"
PLAN = REPO / "config/research_reset_v1.json"


def prepared(tmp_path):
    minute_manifest, settlement = make_execution_bundle(tmp_path / "input")
    daily = tmp_path / "daily"
    built = command("build-daily", minute_manifest, daily)
    assert built.returncode == 0, built.stderr
    admission = preflight(daily / "daily_manifest.json", PLAN)
    assert admission.passed
    return admission, minute_manifest, settlement, daily


def run(daily, minutes, settlement, output):
    return subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/run_research_reset.py"),
            "simulate",
            "--manifest",
            str(daily / "daily_manifest.json"),
            "--minute-manifest",
            str(minutes),
            "--settlement-calendar",
            str(settlement),
            "--execution-policy",
            str(POLICY),
            "--plan",
            str(PLAN),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )


def test_active_cli_uses_fixed_minute_orders_for_all_nine_trials(tmp_path):
    _, minutes, settlement, daily = prepared(tmp_path)
    output = tmp_path / "replay"
    result = run(daily, minutes, settlement, output)
    assert result.returncode == 0, result.stderr
    freeze = json.loads((output / "pre_outcome_freeze.json").read_text())
    assert freeze["execution_model"] == "FIXED_LIMIT_MINUTE_REPLAY_V1"
    assert freeze["trials"] == 9 and freeze["promotion"] == "UNAVAILABLE"
    summaries = json.loads((output / "summary.json").read_text())
    assert len(summaries) == 9
    assert all(s["sessions"] == 10 and abs(s["accounting_residual"]) < 1e-7 for s in summaries)
    total_buys = 0
    shared_plans = {}
    for row in summaries:
        c = row["config"]
        data = json.loads((output / f"{c['family']}_{c['cost_bps_per_side']}bps.json").read_text())
        assert data["status"] == "OFFLINE_MINUTE_EXECUTION_MECHANICS_ONLY"
        orders = {o["order_id"]: o for o in data["orders"]}
        assert data["signal_planning_cost_bps"] == 10
        for order in orders.values():
            key = (c["family"], order["signal_date"], order["symbol"])
            shared_plans.setdefault(key, []).append((order["stop"], order["target"]))
        for fill in data["fills"]:
            if fill["side"] == "BUY":
                order = orders[fill["order_id"]]
                assert order["active_at"] <= fill["interval_start"] < order["expires_at"]
                assert fill["price"] <= order["limit"]
                total_buys += 1
    assert total_buys > 0
    assert any(len(plans) > 1 for plans in shared_plans.values())
    assert all(len(set(plans)) == 1 for plans in shared_plans.values())
    evaluation = json.loads((output / "evaluation.json").read_text())
    assert evaluation["candidate_for_independent_evaluation"] is None
    assert "SYNTHETIC_INPUT_NOT_MARKET_EVIDENCE" in evaluation["advancement_blockers"]
    assert len(evaluation["inference"]) == 2
    assert all(x["joint_series"] == 18 for x in evaluation["inference"])
    ledger = json.loads((output / "trial_execution_ledger.json").read_text())
    assert len(ledger) == 9 and {x["state"] for x in ledger} == {"COMPLETED"}
    again = tmp_path / "repeat"
    assert run(daily, minutes, settlement, again).returncode == 0
    assert (again / "summary.json").read_bytes() == (output / "summary.json").read_bytes()


def test_daily_only_source_cannot_silently_use_idealized_simulator(tmp_path):
    manifest, _ = make_source(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/run_research_reset.py"),
            "simulate",
            "--manifest",
            str(manifest),
            "--output",
            str(tmp_path / "result"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "minute manifest and explicit settlement calendar required" in result.stderr
    assert not (tmp_path / "result/summary.json").exists()


def test_daily_signals_must_reconcile_to_execution_source(tmp_path):
    admission, minutes, settlement, _ = prepared(tmp_path)
    session = admission.sessions[0]
    first = admission.by_date[session][0]
    admission.by_date[session][0] = replace(first, volume=first.volume + 1)
    with pytest.raises(ValueError, match="do not reconcile"):
        load_replay_inputs(admission, minutes, POLICY, settlement)


def test_settlement_coverage_and_reference_tamper_block_before_replay(tmp_path):
    admission, minutes, settlement, _ = prepared(tmp_path)
    document = json.loads(settlement.read_text())
    document["dates"] = document["dates"][:210]
    settlement.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="lookahead"):
        load_replay_inputs(admission, minutes, POLICY, settlement)
    spec = json.loads(minutes.read_text())
    (minutes.parent / spec["references_path"]).write_text("{}")
    with pytest.raises(ValueError, match="reference_tables hash mismatch"):
        load_replay_inputs(admission, minutes, POLICY, settlement)


def test_future_earnings_revision_cannot_change_earlier_entry_context(tmp_path):
    admission, minutes, settlement, _ = prepared(tmp_path)
    inputs = load_replay_inputs(admission, minutes, POLICY, settlement)
    book = inputs.references
    sessions = [d.session for d in book.calendar if d.opens]
    current = day()
    sim = engine()
    prior = _decision_context(book, current, sim, [idea()], sessions)
    row = book._index["earnings"]["A"][0]
    revised = replace(row, known_at=current.closes, event_sessions=(D + timedelta(days=1),))
    book._index["earnings"]["A"].append(revised)
    assert _decision_context(book, current, sim, [idea()], sessions) == prior
    book._index["earnings"]["A"][-1] = replace(revised, known_at=current.opens)
    assert "A" not in _decision_context(book, current, sim, [idea()], sessions)[0]
