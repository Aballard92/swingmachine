from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from swingmachine.data_quality import (
    build_historical_data_quality_report,
    write_historical_data_quality_report_json,
    write_historical_data_quality_report_markdown,
)
from swingmachine.enums import ReviewStatus

HISTORICAL_PANEL_FIXTURE = Path("tests/fixtures/historical_panel")


def test_historical_data_quality_passes_clean_fixture(tmp_path: Path) -> None:
    manifest_path = _copy_panel(tmp_path)

    report = build_historical_data_quality_report(manifest_path, benchmark_symbol="AAA")

    assert report.status is ReviewStatus.PASS
    assert report.coverage_check is ReviewStatus.PASS
    assert report.duplicate_check is ReviewStatus.PASS
    assert report.price_volume_check is ReviewStatus.PASS
    assert report.benchmark_coverage_check is ReviewStatus.PASS
    assert report.symbol_count == 2
    assert report.session_count == 7
    assert report.ohlcv_row_count == 14
    assert report.issues == ()


def test_historical_data_quality_warns_on_zero_volume(tmp_path: Path) -> None:
    manifest_path = _copy_panel(tmp_path)
    ohlcv_path = manifest_path.parent / "ohlcv.csv"
    ohlcv = pd.read_csv(ohlcv_path)
    ohlcv.loc[0, "raw_volume"] = 0
    ohlcv.to_csv(ohlcv_path, index=False)

    report = build_historical_data_quality_report(manifest_path, benchmark_symbol="AAA")

    assert report.status is ReviewStatus.WARN
    assert report.price_volume_check is ReviewStatus.WARN
    assert any(issue.code == "zero_volume_rows" for issue in report.issues)


def test_historical_data_quality_fails_missing_benchmark(tmp_path: Path) -> None:
    manifest_path = _copy_panel(tmp_path)

    report = build_historical_data_quality_report(manifest_path, benchmark_symbol="SPY")

    assert report.status is ReviewStatus.FAIL
    assert report.benchmark_coverage_check is ReviewStatus.FAIL
    assert any(issue.code == "benchmark_symbol_missing" for issue in report.issues)


def test_historical_data_quality_writers_create_reports(tmp_path: Path) -> None:
    manifest_path = _copy_panel(tmp_path)
    report = build_historical_data_quality_report(manifest_path, benchmark_symbol="AAA")
    json_path = tmp_path / "data_quality.json"
    markdown_path = tmp_path / "data_quality.md"

    assert write_historical_data_quality_report_json(report, json_path) == json_path
    assert write_historical_data_quality_report_markdown(report, markdown_path) == markdown_path
    assert '"status": "PASS"' in json_path.read_text(encoding="utf-8")
    assert "Historical Data Quality Report" in markdown_path.read_text(encoding="utf-8")


def _copy_panel(tmp_path: Path) -> Path:
    panel_path = tmp_path / "panel"
    shutil.copytree(HISTORICAL_PANEL_FIXTURE, panel_path)
    return panel_path / "manifest.yaml"
