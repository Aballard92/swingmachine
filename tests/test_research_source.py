"""Admission tests use generated data and evidence, never historical prices."""

import argparse
import json
import runpy
from pathlib import Path

import pytest

from swingmachine.research_reset import file_hash
from swingmachine.research_source import EVIDENCE_ROLES, preflight
from tests.test_research_reset_cli import REPO, make_source

PLAN = REPO / "config/research_reset_v1.json"


def save_source(manifest, source):
    manifest.write_text(json.dumps(source))


def change_rows(manifest, source, change):
    path = manifest.parent / source["bars_path"]
    rows = json.loads(path.read_text())
    change(rows)
    path.write_text(json.dumps(rows))
    source["bars_sha256"] = file_hash(path)
    save_source(manifest, source)


def codes(admission):
    return {i["code"] for i in admission.report["issues"]}


def historical_fixture(manifest, source):
    """Fake evidence exercises structure only; it is not qualified market data."""
    source["source_class"] = "HISTORICAL"
    source["supporting_evidence"] = {}
    for role in EVIDENCE_ROLES:
        path = manifest.parent / f"{role}.json"
        path.write_text(json.dumps({"fixture_only": True, "role": role}))
        source["supporting_evidence"][role] = {
            "path": path.name,
            "sha256": file_hash(path),
            "coverage_start": source["start"],
            "coverage_end": source["end"],
            "scope": "SYNTHETIC six-symbol fixture only",
            "provenance": "Generated test data; no real historical qualification",
            "availability_policy": "All synthetic values known at each decision close",
        }
    change_rows(manifest, source, lambda rows: [r.update(split_ratio=1, dividend=0) for r in rows])


def test_valid_fixture_preflight_has_no_outcomes(tmp_path):
    manifest, _ = make_source(tmp_path)
    admission = preflight(manifest, PLAN)
    assert admission.passed
    assert admission.report["status"] == "STRUCTURAL_PREFLIGHT_PASS"
    assert admission.report["counts"] == {
        "rows": 1560,
        "valid_unique_rows": 1560,
        "sessions": 260,
        "trials": 9,
    }
    assert admission.report["strategy_calculations"] == 0


@pytest.mark.parametrize(
    "mutation,expected",
    [
        (lambda rows: rows.append(rows[-1].copy()), "DUPLICATE_BAR"),
        (lambda rows: rows[-1].update(close=float("nan")), "INVALID_BAR"),
        (lambda rows: rows[-1].update(open=True), "INVALID_BAR"),
        (lambda rows: rows[-1].update(symbol=[]), "INVALID_BAR"),
        (lambda rows: rows[-1].update(event_known=False), "ELIGIBILITY_CONTEXT"),
        (lambda rows: rows[-1].pop("eligible"), "INVALID_BAR"),
        (lambda rows: rows.__delitem__(slice(-6, None)), "MISSING_SESSION"),
        (lambda rows: rows.pop(-6), "BENCHMARK_COVERAGE"),
        (lambda rows: rows[-1].update(session="2018-01-01"), "INVALID_BAR"),
    ],
)
def test_all_rows_checked_before_engine_construction(tmp_path, mutation, expected):
    manifest, source = make_source(tmp_path)
    change_rows(manifest, source, mutation)
    output = tmp_path / "out"
    output.mkdir()
    script = runpy.run_path(str(REPO / "scripts/run_research_reset.py"))

    def forbidden(*args, **kwargs):
        raise AssertionError("Strategy construction must not run for inadmissible inputs")

    script["simulate"].__globals__["SignalEngine"] = forbidden
    with pytest.raises(ValueError, match="input preflight blocked"):
        script["simulate"](argparse.Namespace(manifest=manifest, plan=PLAN, output=output))
    report = json.loads((output / "readiness.json").read_text())
    assert expected in {i["code"] for i in report["issues"]}
    assert sorted(p.name for p in output.iterdir()) == ["readiness.json"]


@pytest.mark.parametrize(
    "patch",
    [
        {"families": []},
        {"families": ["momentum", "momentum"]},
        {"cost_bps_per_side": [10, 10]},
        {"cost_bps_per_side": [True]},
        {"initial_cash": True},
        {"risk_fraction": float("inf")},
        {"protected_windows": []},
    ],
)
def test_invalid_plan_stops_before_price_read(tmp_path, patch):
    manifest, _ = make_source(tmp_path)
    plan = json.loads(PLAN.read_text())
    plan.update(patch)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    admission = preflight(manifest, plan_path)
    assert "PLAN_CONTRACT" in codes(admission)
    assert admission.report["bar_file_read"] is False


def test_protected_manifest_opens_no_other_files(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"start": "2020-01-01", "end": "2021-01-01"}))
    original = Path.read_bytes
    reads = []

    def read(path):
        reads.append(path)
        if path != manifest:
            raise AssertionError("Only the manifest may be read")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    assert codes(preflight(manifest, PLAN)) == {"DATE_BOUNDARY"}
    assert reads == [manifest]


def test_session_declaration_cannot_hide_protected_dates(tmp_path):
    manifest, source = make_source(tmp_path)
    source["sessions"].insert(20, "2023-01-03")
    save_source(manifest, source)
    admission = preflight(manifest, PLAN)
    assert "SESSION_CONTRACT" in codes(admission)
    assert not admission.report["bar_file_read"]


def test_generic_historical_evidence_is_insufficient(tmp_path):
    manifest, source = make_source(tmp_path)
    source.update(source_class="HISTORICAL", supporting_evidence="complete according to old report")
    save_source(manifest, source)
    admission = preflight(manifest, PLAN)
    assert not admission.passed
    assert len(admission.report["issues"]) == 6
    assert not admission.report["bar_file_read"]


def test_scoped_hashed_evidence_pass_is_only_structural(tmp_path):
    manifest, source = make_source(tmp_path)
    historical_fixture(manifest, source)
    admission = preflight(manifest, PLAN)
    assert admission.passed, admission.report
    assert set(EVIDENCE_ROLES) <= admission.report["verified_sha256"].keys()
    assert admission.report["historical_qualification"] == "NOT_ESTABLISHED_BY_PREFLIGHT"


@pytest.mark.parametrize(
    "patch,expected",
    [
        ({"coverage_start": "2019-02-01"}, "EVIDENCE_CONTRACT"),
        ({"coverage_end": "2023-01-01"}, "EVIDENCE_CONTRACT"),
        ({"availability_policy": ""}, "EVIDENCE_CONTRACT"),
        ({"sha256": "0" * 64}, "REFERENCE_INTEGRITY"),
        ({"path": "../outside.json"}, "REFERENCE_INTEGRITY"),
    ],
)
def test_unsupported_evidence_blocks_price_read(tmp_path, patch, expected):
    manifest, source = make_source(tmp_path)
    historical_fixture(manifest, source)
    source["supporting_evidence"]["corporate_actions"].update(patch)
    save_source(manifest, source)
    admission = preflight(manifest, PLAN)
    assert expected in codes(admission)
    assert not admission.report["bar_file_read"]


def test_reference_symlink_cannot_escape_bundle(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    manifest, source = make_source(bundle)
    original = bundle / source["bars_path"]
    outside = tmp_path / "outside.json"
    original.rename(outside)
    original.symlink_to(outside)
    admission = preflight(manifest, PLAN)
    assert "REFERENCE_INTEGRITY" in codes(admission)
    assert not admission.report["bar_file_read"]


def test_conflicting_json_fields_are_not_silently_overwritten(tmp_path):
    manifest, _ = make_source(tmp_path)
    text = manifest.read_text()
    manifest.write_text(text[:-1] + ', "start": "2023-01-01"}')
    admission = preflight(manifest, PLAN)
    assert "INVALID_DOCUMENT" in codes(admission)
    assert not admission.report["bar_file_read"]


def test_unknown_source_contract_version_is_not_assumed_compatible(tmp_path):
    manifest, source = make_source(tmp_path)
    source["contract_version"] = 2
    save_source(manifest, source)
    admission = preflight(manifest, PLAN)
    assert "SOURCE_VERSION" in codes(admission)
    assert not admission.report["bar_file_read"]
