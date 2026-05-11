from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from swingmachine.enums import ReviewStatus
from swingmachine.lookahead_audit import (
    build_lookahead_audit_report,
    write_lookahead_audit_report_json,
)
from swingmachine.runtime import app
from tests.historical_panel_helpers import (
    add_prepared_features_to_manifest,
    write_prepared_feature_file,
)

HISTORICAL_PANEL_FIXTURE = Path("tests/fixtures/historical_panel")


def test_lookahead_audit_passes_clean_prepared_feature_panel(tmp_path: Path) -> None:
    manifest_path = _manifest_with_features(tmp_path)

    report = build_lookahead_audit_report(manifest_path)

    assert report.status is ReviewStatus.PASS
    assert report.feature_window_check is ReviewStatus.PASS
    assert report.symbol_reference_check is ReviewStatus.PASS
    assert report.earnings_timing_check is ReviewStatus.PASS
    assert report.session_order_check is ReviewStatus.PASS
    assert report.violations == ()


def test_lookahead_audit_fails_feature_session_before_feature_start(
    tmp_path: Path,
) -> None:
    manifest_path = _manifest_with_features(tmp_path, feature_start_session="2026-04-23")

    report = build_lookahead_audit_report(manifest_path)

    assert report.status is ReviewStatus.FAIL
    assert report.feature_window_check is ReviewStatus.FAIL
    assert any(
        violation.code in {"feature_session_before_feature_start", "manifest_validation_failed"}
        for violation in report.violations
    )


def test_lookahead_audit_fails_non_strict_session_order(tmp_path: Path) -> None:
    manifest_path = _manifest_with_features(tmp_path)
    feature_path = manifest_path.parent / "features.csv"
    features = pd.read_csv(feature_path)
    reversed_aaa = features[features["symbol"] == "AAA"].iloc[::-1]
    others = features[features["symbol"] != "AAA"]
    pd.concat([reversed_aaa, others], ignore_index=True).to_csv(feature_path, index=False)

    report = build_lookahead_audit_report(manifest_path)

    assert report.status is ReviewStatus.FAIL
    assert report.session_order_check is ReviewStatus.FAIL
    assert any(
        violation.code == "features_session_order_not_strict"
        for violation in report.violations
    )


def test_lookahead_audit_fails_invalid_earnings_timing(tmp_path: Path) -> None:
    manifest_path = _manifest_with_features(tmp_path)
    feature_path = manifest_path.parent / "features.csv"
    features = pd.read_csv(feature_path)
    features.loc[0, "regular_closes_until_earnings_event"] = -1
    features.to_csv(feature_path, index=False)

    report = build_lookahead_audit_report(manifest_path)

    assert report.status is ReviewStatus.FAIL
    assert any(
        violation.code in {"manifest_validation_failed", "invalid_earnings_timing_value"}
        for violation in report.violations
    )


def test_lookahead_audit_report_writer_creates_json(tmp_path: Path) -> None:
    manifest_path = _manifest_with_features(tmp_path)
    output_path = tmp_path / "lookahead_audit.json"

    report = build_lookahead_audit_report(manifest_path)
    written_path = write_lookahead_audit_report_json(report, output_path)

    assert written_path == output_path
    assert '"status": "PASS"' in output_path.read_text(encoding="utf-8")


def test_runtime_cli_builds_lookahead_audit_report(tmp_path: Path) -> None:
    manifest_path = _manifest_with_features(tmp_path)
    output_path = tmp_path / "lookahead_audit.json"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "build-lookahead-audit-report",
            "--manifest",
            str(manifest_path),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert output_path.exists()


def _manifest_with_features(
    tmp_path: Path,
    *,
    feature_start_session: str | None = None,
) -> Path:
    panel_path = tmp_path / "panel"
    shutil.copytree(HISTORICAL_PANEL_FIXTURE, panel_path)
    manifest_path = panel_path / "manifest.yaml"
    feature_path = write_prepared_feature_file(panel_path)
    add_prepared_features_to_manifest(
        manifest_path,
        feature_path,
        feature_start_session=feature_start_session,
    )
    return manifest_path
