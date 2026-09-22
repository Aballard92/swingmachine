"""CLI integration: minute/reference bundle to admitted synthetic daily prices."""

import json
import subprocess
import sys

from swingmachine.research_reset import file_hash
from tests.research_fixture_factory import make_minute_bundle
from tests.test_research_reset_cli import REPO


def command(name, manifest, output):
    return subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/run_research_reset.py"),
            name,
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


def test_complete_synthetic_minute_to_daily_admission(tmp_path):
    manifest, spec = make_minute_bundle(tmp_path / "input")
    output = tmp_path / "daily"
    run = command("build-daily", manifest, output)
    assert run.returncode == 0, run.stderr
    bars = json.loads((output / "daily_bars.json").read_text())
    receipt = json.loads((output / "build_receipt.json").read_text())
    assert len(bars) == 1560
    assert receipt["strategy_calculations"] == 0
    assert receipt["references_sha256"] == spec["references_sha256"]
    admission = command("preflight", output / "daily_manifest.json", tmp_path / "admission")
    assert admission.returncode == 0, admission.stderr
    assert not (output / "summary.json").exists()
    second = tmp_path / "repeat"
    assert command("build-daily", manifest, second).returncode == 0
    for name in [
        "daily_bars.json",
        "daily_lineage.json",
        "action_events.json",
        "adapter_diagnostics.json",
    ]:
        assert (output / name).read_bytes() == (second / name).read_bytes()


def test_reference_hash_failure_precedes_minute_read(tmp_path):
    manifest, spec = make_minute_bundle(tmp_path / "input")
    (manifest.parent / spec["references_path"]).write_text("{}")
    (manifest.parent / spec["minute_sources"][0]["path"]).unlink()
    output = tmp_path / "blocked"
    run = command("build-daily", manifest, output)
    assert run.returncode == 1
    assert "reference bundle hash mismatch" in run.stderr
    assert not (output / "daily_bars.json").exists()


def test_incomplete_action_reference_is_explicit_blocked_evidence(tmp_path):
    manifest, spec = make_minute_bundle(tmp_path / "input")
    path = manifest.parent / spec["references_path"]
    value = json.loads(path.read_text())
    value["action_coverage"] = []
    path.write_text(json.dumps(value))
    spec["references_sha256"] = file_hash(path)
    manifest.write_text(json.dumps(spec))
    output = tmp_path / "blocked"
    run = command("build-daily", manifest, output)
    assert run.returncode == 1
    diagnostics = json.loads((output / "adapter_diagnostics.json").read_text())
    assert {i["code"] for i in diagnostics["issues"]} == {"UNKNOWN_ACTION_COVERAGE"}
    assert not json.loads((output / "daily_manifest.json").read_text())[
        "corporate_actions_complete"
    ]
    assert not (output / "summary.json").exists()
