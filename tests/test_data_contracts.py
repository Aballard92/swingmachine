from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest
import yaml

from swingmachine.data_contracts import (
    PreparedDataValidationError,
    load_historical_panel_data,
    validate_corporate_actions_data,
    validate_earnings_events_data,
    validate_historical_panel_manifest,
    validate_next_session_market_data,
    validate_symbol_reference_data,
)
from swingmachine.enums import ReviewStatus
from tests.historical_panel_helpers import (
    add_prepared_features_to_manifest,
    sha256_file,
    write_prepared_feature_file,
)

HISTORICAL_PANEL_FIXTURE = Path("tests/fixtures/historical_panel")


def test_validate_next_session_market_data_normalizes_valid_rows() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAA"],
            "session_date": ["2026-04-25"],
            "raw_open": [100.0],
            "raw_high": [101.0],
            "raw_low": [99.0],
            "raw_close": [100.5],
            "raw_volume": [1_000_000],
            "spread_bps": [2.0],
        }
    )

    result = validate_next_session_market_data(frame)

    assert str(result.loc[0, "symbol"]) == "AAA"
    assert result.loc[0, "session_date"].date().isoformat() == "2026-04-25"


def test_validate_next_session_market_data_rejects_duplicate_symbols() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAA", "AAA"],
            "session_date": ["2026-04-25", "2026-04-25"],
            "raw_open": [100.0, 100.1],
            "raw_high": [101.0, 101.1],
            "raw_low": [99.0, 99.1],
            "raw_close": [100.5, 100.6],
            "raw_volume": [1_000_000, 2_000_000],
        }
    )

    with pytest.raises(PreparedDataValidationError, match="duplicate"):
        validate_next_session_market_data(frame)


def test_validate_next_session_market_data_rejects_invalid_ohlc() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAA"],
            "session_date": ["2026-04-25"],
            "raw_open": [100.0],
            "raw_high": [98.0],
            "raw_low": [99.0],
            "raw_close": [100.5],
            "raw_volume": [1_000_000],
        }
    )

    with pytest.raises(PreparedDataValidationError, match="raw_high"):
        validate_next_session_market_data(frame)


def test_validate_symbol_reference_data_normalizes_valid_rows() -> None:
    frame = pd.DataFrame(
        {
            "symbol": [" AAA "],
            "asset_type": ["COMMON_STOCK"],
            "exchange": ["XLON"],
            "currency": ["gbp"],
            "sector": ["Technology"],
            "is_tradable": ["yes"],
            "tradable_start_session": ["2026-04-20"],
            "tradable_end_session": ["2026-04-28"],
        }
    )

    result = validate_symbol_reference_data(frame)

    assert result.loc[0, "symbol"] == "AAA"
    assert result.loc[0, "currency"] == "GBP"
    assert bool(result.loc[0, "is_tradable"]) is True
    assert result.loc[0, "tradable_start_session"].date().isoformat() == "2026-04-20"
    assert result.loc[0, "tradable_end_session"].date().isoformat() == "2026-04-28"


def test_validate_symbol_reference_data_rejects_unknown_asset_type() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAA"],
            "asset_type": ["CRYPTO"],
            "exchange": ["XLON"],
            "currency": ["GBP"],
            "sector": ["Technology"],
            "is_tradable": [True],
        }
    )

    with pytest.raises(PreparedDataValidationError, match="asset_type"):
        validate_symbol_reference_data(frame)


def test_validate_symbol_reference_data_rejects_invalid_tradability_window() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAA"],
            "asset_type": ["COMMON_STOCK"],
            "exchange": ["XLON"],
            "currency": ["GBP"],
            "sector": ["Technology"],
            "is_tradable": [True],
            "tradable_start_session": ["2026-04-28"],
            "tradable_end_session": ["2026-04-20"],
        }
    )

    with pytest.raises(PreparedDataValidationError, match="tradable_start_session"):
        validate_symbol_reference_data(frame)


def test_validate_symbol_reference_data_allows_non_overlapping_history_rows() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAA", "AAA"],
            "asset_type": ["COMMON_STOCK", "COMMON_STOCK"],
            "exchange": ["XLON", "XLON"],
            "currency": ["GBP", "GBP"],
            "sector": ["Technology", "Industrial"],
            "is_tradable": [True, True],
            "effective_start_session": ["2026-04-20", "2026-04-27"],
            "effective_end_session": ["2026-04-24", "2026-04-28"],
        }
    )

    result = validate_symbol_reference_data(frame)

    assert list(result["sector"]) == ["Technology", "Industrial"]
    assert result.loc[0, "effective_start_session"].date().isoformat() == "2026-04-20"
    assert result.loc[1, "effective_end_session"].date().isoformat() == "2026-04-28"


def test_validate_symbol_reference_data_rejects_duplicate_history_without_effective_start() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAA", "AAA"],
            "asset_type": ["COMMON_STOCK", "COMMON_STOCK"],
            "exchange": ["XLON", "XLON"],
            "currency": ["GBP", "GBP"],
            "sector": ["Technology", "Industrial"],
            "is_tradable": [True, True],
        }
    )

    with pytest.raises(PreparedDataValidationError, match="effective_start_session"):
        validate_symbol_reference_data(frame)


def test_validate_symbol_reference_data_rejects_overlapping_effective_windows() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAA", "AAA"],
            "asset_type": ["COMMON_STOCK", "COMMON_STOCK"],
            "exchange": ["XLON", "XLON"],
            "currency": ["GBP", "GBP"],
            "sector": ["Technology", "Industrial"],
            "is_tradable": [True, True],
            "effective_start_session": ["2026-04-20", "2026-04-24"],
            "effective_end_session": ["2026-04-24", "2026-04-28"],
        }
    )

    with pytest.raises(PreparedDataValidationError, match="overlapping"):
        validate_symbol_reference_data(frame)


def test_validate_corporate_actions_data_rejects_invalid_split_ratio() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAA"],
            "ex_date": ["2026-04-25"],
            "split_ratio": [0.0],
            "cash_dividend_per_share": [0.0],
        }
    )

    with pytest.raises(PreparedDataValidationError, match="split_ratio"):
        validate_corporate_actions_data(frame)


def test_validate_corporate_actions_data_rejects_duplicate_symbol_ex_date() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAA", "AAA"],
            "ex_date": ["2026-04-25", "2026-04-25"],
            "split_ratio": [1.0, 1.0],
            "cash_dividend_per_share": [0.0, 0.1],
        }
    )

    with pytest.raises(PreparedDataValidationError, match="duplicate"):
        validate_corporate_actions_data(frame)


def test_validate_earnings_events_data_normalizes_valid_rows() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAA"],
            "event_date": ["2026-04-25"],
            "event_session": ["PRE_OPEN"],
        }
    )

    result = validate_earnings_events_data(frame)

    assert result.loc[0, "event_date"].date().isoformat() == "2026-04-25"
    assert result.loc[0, "event_session"] == "PRE_OPEN"


def test_validate_earnings_events_data_rejects_unknown_session() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["AAA"],
            "event_date": ["2026-04-25"],
            "event_session": ["MIDDAY"],
        }
    )

    with pytest.raises(PreparedDataValidationError, match="event_session"):
        validate_earnings_events_data(frame)


def test_validate_historical_panel_manifest_accepts_tiny_fixture() -> None:
    result = validate_historical_panel_manifest(HISTORICAL_PANEL_FIXTURE / "manifest.yaml")

    assert result.status is ReviewStatus.PASS
    assert result.panel_id == "tiny-historical-panel-v1"
    assert result.symbol_count == 2
    assert result.session_count == 7
    assert result.start_session is not None
    assert result.start_session.isoformat() == "2026-04-20"
    assert result.end_session is not None
    assert result.end_session.isoformat() == "2026-04-28"
    assert not result.errors
    assert not result.warnings
    assert {summary.file_key for summary in result.file_summaries} == {
        "ohlcv",
        "symbol_reference",
        "corporate_actions",
        "earnings_events",
    }


def test_validate_historical_panel_manifest_us_equity_calendar_skips_holidays(
    tmp_path: Path,
) -> None:
    panel_path = tmp_path / "us_equity_holiday_panel"
    panel_path.mkdir()
    pd.DataFrame(
        [
            {
                "symbol": "AAA",
                "session_date": "2024-07-03",
                "raw_open": 10.0,
                "raw_high": 11.0,
                "raw_low": 9.5,
                "raw_close": 10.5,
                "raw_volume": 1000.0,
            },
            {
                "symbol": "AAA",
                "session_date": "2024-07-05",
                "raw_open": 10.5,
                "raw_high": 11.5,
                "raw_low": 10.0,
                "raw_close": 11.0,
                "raw_volume": 1100.0,
            },
        ]
    ).to_csv(panel_path / "ohlcv.csv", index=False)
    pd.DataFrame(
        [
            {
                "symbol": "AAA",
                "asset_type": "COMMON_STOCK",
                "exchange": "UNKNOWN",
                "currency": "USD",
                "sector": "UNKNOWN",
                "is_tradable": True,
            }
        ]
    ).to_csv(panel_path / "symbol_reference.csv", index=False)
    pd.DataFrame(columns=["symbol", "ex_date", "split_ratio", "cash_dividend_per_share"]).to_csv(
        panel_path / "corporate_actions.csv",
        index=False,
    )
    pd.DataFrame(columns=["symbol", "event_date", "event_session"]).to_csv(
        panel_path / "earnings_events.csv",
        index=False,
    )
    manifest_path = panel_path / "manifest.yaml"
    manifest = {
        "panel_id": "us-equity-holiday-panel",
        "schema_version": "1.0",
        "created_at": "2026-05-06T00:00:00",
        "base_path": str(panel_path),
        "calendar": "US_EQUITY",
        "timezone": "Europe/London",
        "start_session": "2024-07-03",
        "end_session": "2024-07-05",
        "expected_symbol_count": 1,
        "expected_session_count": 2,
        "files": {
            "ohlcv": {"path": "ohlcv.csv", "format": "csv", "row_count": 2},
            "symbol_reference": {
                "path": "symbol_reference.csv",
                "format": "csv",
                "row_count": 1,
            },
            "corporate_actions": {
                "path": "corporate_actions.csv",
                "format": "csv",
                "row_count": 0,
            },
            "earnings_events": {
                "path": "earnings_events.csv",
                "format": "csv",
                "row_count": 0,
            },
        },
    }
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    result = validate_historical_panel_manifest(manifest_path)
    manifest["calendar"] = "WEEKDAY"
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    weekday_result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.PASS
    assert "MISSING_EXPECTED_SESSIONS" not in _issue_codes(result.warnings)
    assert weekday_result.status is ReviewStatus.WARN
    assert "MISSING_EXPECTED_SESSIONS" in _issue_codes(weekday_result.warnings)


def test_validate_historical_panel_manifest_accepts_optional_features_with_checksum(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    features_path = write_prepared_feature_file(manifest_path.parent)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
    )

    result = validate_historical_panel_manifest(manifest_path)
    panel_data = load_historical_panel_data(manifest_path)

    assert result.status is ReviewStatus.PASS
    assert not result.errors
    assert {summary.file_key for summary in result.file_summaries} == {
        "ohlcv",
        "symbol_reference",
        "corporate_actions",
        "earnings_events",
        "features",
    }
    feature_summary = next(
        summary for summary in result.file_summaries if summary.file_key == "features"
    )
    assert feature_summary.row_count == 14
    assert panel_data.features is not None
    assert len(panel_data.features) == 14


def test_validate_historical_panel_manifest_rejects_required_file_checksum_mismatch(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["files"]["ohlcv"]["sha256"] = "0" * 64
    manifest_path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert _issue_codes(result.errors) == {"SHA256_MISMATCH"}


def test_validate_historical_panel_manifest_rejects_feature_checksum_mismatch(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    features_path = write_prepared_feature_file(manifest_path.parent)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256="0" * 64,
    )

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert _issue_codes(result.errors) == {"SHA256_MISMATCH"}


def test_validate_historical_panel_manifest_rejects_invalid_feature_panel(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    features_path = write_prepared_feature_file(manifest_path.parent)
    features = pd.read_csv(features_path).drop(columns=["ma50"])
    features.to_csv(features_path, index=False)
    add_prepared_features_to_manifest(manifest_path, features_path)

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "FILE_VALIDATION_FAILED" in _issue_codes(result.errors)
    assert any("ma50" in issue.message for issue in result.errors)


def test_validate_historical_panel_manifest_accepts_optional_features_parquet(
    tmp_path: Path,
) -> None:
    pytest.importorskip("pyarrow")
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    features_path = write_prepared_feature_file(
        manifest_path.parent,
        file_name="features.parquet",
        file_format="parquet",
    )
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        file_format="parquet",
        sha256=sha256_file(features_path),
    )

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.PASS
    assert "features" in {summary.file_key for summary in result.file_summaries}


def test_validate_historical_panel_manifest_allows_feature_warmup_gap_before_feature_start(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    features_path = write_prepared_feature_file(manifest_path.parent)
    features = pd.read_csv(features_path)
    features = features.loc[
        pd.to_datetime(features["session_date"]).dt.date >= pd.Timestamp("2026-04-23").date()
    ]
    features.to_csv(features_path, index=False)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
        feature_start_session="2026-04-23",
    )

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.PASS
    assert not result.errors
    feature_summary = next(
        summary for summary in result.file_summaries if summary.file_key == "features"
    )
    assert feature_summary.row_count == 8
    assert feature_summary.start_session is not None
    assert feature_summary.start_session.isoformat() == "2026-04-23"


def test_validate_historical_panel_manifest_rejects_feature_gap_after_feature_start(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    features_path = write_prepared_feature_file(manifest_path.parent)
    features = pd.read_csv(features_path)
    missing_row = (features["symbol"] == "BBB") & (features["session_date"] == "2026-04-27")
    features = features.loc[~missing_row]
    features.to_csv(features_path, index=False)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
        feature_start_session="2026-04-20",
    )

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "FEATURE_COVERAGE_GAP" in _issue_codes(result.errors)
    assert any(
        issue.symbol == "BBB"
        and issue.session_date is not None
        and issue.session_date.isoformat() == "2026-04-27"
        for issue in result.errors
    )


def test_validate_historical_panel_manifest_rejects_feature_reference_metadata_mismatch(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    features_path = write_prepared_feature_file(manifest_path.parent)
    features = pd.read_csv(features_path)
    mismatched_row = (features["symbol"] == "AAA") & (features["session_date"] == "2026-04-27")
    features.loc[mismatched_row, "sector"] = "Incorrect"
    features.to_csv(features_path, index=False)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
        feature_start_session="2026-04-20",
    )

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "FEATURE_REFERENCE_METADATA_MISMATCH" in _issue_codes(result.errors)
    assert any(
        issue.field == "sector"
        and issue.symbol == "AAA"
        and issue.session_date is not None
        and issue.session_date.isoformat() == "2026-04-27"
        for issue in result.errors
    )


def test_validate_historical_panel_manifest_allows_tradable_reference_feature_scope(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    symbol_reference_path = manifest_path.parent / "symbol_reference.csv"
    symbol_reference = pd.read_csv(symbol_reference_path)
    symbol_reference.loc[symbol_reference["symbol"] == "BBB", "is_tradable"] = False
    symbol_reference.to_csv(symbol_reference_path, index=False)
    features_path = write_prepared_feature_file(manifest_path.parent)
    features = pd.read_csv(features_path)
    features = features.loc[features["symbol"] == "AAA"]
    features.to_csv(features_path, index=False)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
        feature_start_session="2026-04-20",
        feature_coverage_scope="tradable_reference",
    )

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.PASS
    assert not result.errors
    feature_summary = next(
        summary for summary in result.file_summaries if summary.file_key == "features"
    )
    assert feature_summary.row_count == 7


def test_validate_historical_panel_manifest_all_ohlcv_scope_requires_non_tradable_features(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    symbol_reference_path = manifest_path.parent / "symbol_reference.csv"
    symbol_reference = pd.read_csv(symbol_reference_path)
    symbol_reference.loc[symbol_reference["symbol"] == "BBB", "is_tradable"] = False
    symbol_reference.to_csv(symbol_reference_path, index=False)
    features_path = write_prepared_feature_file(manifest_path.parent)
    features = pd.read_csv(features_path)
    features = features.loc[features["symbol"] == "AAA"]
    features.to_csv(features_path, index=False)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
        feature_start_session="2026-04-20",
    )

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "FEATURE_COVERAGE_GAP" in _issue_codes(result.errors)
    assert any(issue.symbol == "BBB" for issue in result.errors)


def test_validate_historical_panel_manifest_tradable_scope_honors_tradability_window(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    symbol_reference_path = manifest_path.parent / "symbol_reference.csv"
    symbol_reference = pd.read_csv(symbol_reference_path)
    symbol_reference["tradable_start_session"] = ""
    symbol_reference["tradable_end_session"] = ""
    symbol_reference.loc[
        symbol_reference["symbol"] == "BBB",
        "tradable_start_session",
    ] = "2026-04-23"
    symbol_reference.loc[
        symbol_reference["symbol"] == "BBB",
        "tradable_end_session",
    ] = "2026-04-24"
    symbol_reference.to_csv(symbol_reference_path, index=False)
    features_path = write_prepared_feature_file(manifest_path.parent)
    features = pd.read_csv(features_path)
    bbb_tradable_window = (
        (features["symbol"] == "BBB")
        & (features["session_date"] >= "2026-04-23")
        & (features["session_date"] <= "2026-04-24")
    )
    features = features.loc[(features["symbol"] == "AAA") | bbb_tradable_window]
    features.to_csv(features_path, index=False)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
        feature_start_session="2026-04-20",
        feature_coverage_scope="tradable_reference",
    )

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.PASS
    assert not result.errors
    feature_summary = next(
        summary for summary in result.file_summaries if summary.file_key == "features"
    )
    assert feature_summary.row_count == 9


def test_validate_historical_panel_manifest_tradable_scope_honors_effective_history(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    symbol_reference_path = manifest_path.parent / "symbol_reference.csv"
    symbol_reference = pd.read_csv(symbol_reference_path)
    symbol_reference["effective_start_session"] = ""
    symbol_reference["effective_end_session"] = ""
    bbb_base = symbol_reference.loc[symbol_reference["symbol"] == "BBB"].iloc[0].copy()
    bbb_early = bbb_base.copy()
    bbb_early["is_tradable"] = False
    bbb_early["effective_start_session"] = "2026-04-20"
    bbb_early["effective_end_session"] = "2026-04-24"
    bbb_late = bbb_base.copy()
    bbb_late["is_tradable"] = True
    bbb_late["effective_start_session"] = "2026-04-27"
    bbb_late["effective_end_session"] = "2026-04-28"
    symbol_reference = pd.concat(
        [
            symbol_reference.loc[symbol_reference["symbol"] != "BBB"],
            pd.DataFrame([bbb_early, bbb_late]),
        ],
        ignore_index=True,
    )
    symbol_reference.to_csv(symbol_reference_path, index=False)
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["files"]["symbol_reference"]["row_count"] = len(symbol_reference)
    manifest_path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")
    features_path = write_prepared_feature_file(manifest_path.parent)
    features = pd.read_csv(features_path)
    bbb_late_window = (features["symbol"] == "BBB") & (features["session_date"] >= "2026-04-27")
    features = features.loc[(features["symbol"] == "AAA") | bbb_late_window]
    features.to_csv(features_path, index=False)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
        feature_start_session="2026-04-20",
        feature_coverage_scope="tradable_reference",
    )

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.PASS
    assert not result.errors
    feature_summary = next(
        summary for summary in result.file_summaries if summary.file_key == "features"
    )
    assert feature_summary.row_count == 9


def test_validate_historical_panel_manifest_rejects_stale_feature_metadata_with_reference_history(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    symbol_reference_path = manifest_path.parent / "symbol_reference.csv"
    symbol_reference = pd.read_csv(symbol_reference_path)
    symbol_reference["effective_start_session"] = ""
    symbol_reference["effective_end_session"] = ""
    bbb_base = symbol_reference.loc[symbol_reference["symbol"] == "BBB"].iloc[0].copy()
    bbb_early = bbb_base.copy()
    bbb_early["sector"] = "Index"
    bbb_early["effective_start_session"] = "2026-04-20"
    bbb_early["effective_end_session"] = "2026-04-24"
    bbb_late = bbb_base.copy()
    bbb_late["sector"] = "Healthcare"
    bbb_late["effective_start_session"] = "2026-04-27"
    bbb_late["effective_end_session"] = "2026-04-28"
    symbol_reference = pd.concat(
        [
            symbol_reference.loc[symbol_reference["symbol"] != "BBB"],
            pd.DataFrame([bbb_early, bbb_late]),
        ],
        ignore_index=True,
    )
    symbol_reference.to_csv(symbol_reference_path, index=False)
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["files"]["symbol_reference"]["row_count"] = len(symbol_reference)
    manifest_path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")
    features_path = write_prepared_feature_file(manifest_path.parent)
    features = pd.read_csv(features_path)
    stale_row = (features["symbol"] == "BBB") & (features["session_date"] == "2026-04-27")
    features.loc[stale_row, "sector"] = "Index"
    features.to_csv(features_path, index=False)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
        feature_start_session="2026-04-20",
    )

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "FEATURE_REFERENCE_METADATA_MISMATCH" in _issue_codes(result.errors)
    assert any(
        issue.field == "sector"
        and issue.symbol == "BBB"
        and issue.session_date is not None
        and issue.session_date.isoformat() == "2026-04-27"
        for issue in result.errors
    )


def test_validate_historical_panel_manifest_rejects_reference_history_gap(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    symbol_reference_path = manifest_path.parent / "symbol_reference.csv"
    symbol_reference = pd.read_csv(symbol_reference_path)
    symbol_reference["effective_start_session"] = ""
    symbol_reference["effective_end_session"] = ""
    symbol_reference.loc[
        symbol_reference["symbol"] == "BBB",
        "effective_start_session",
    ] = "2026-04-20"
    symbol_reference.loc[
        symbol_reference["symbol"] == "BBB",
        "effective_end_session",
    ] = "2026-04-24"
    symbol_reference.to_csv(symbol_reference_path, index=False)

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "SYMBOL_REFERENCE_SESSION_MISSING" in _issue_codes(result.errors)
    assert any(
        issue.symbol == "BBB"
        and issue.session_date is not None
        and issue.session_date.isoformat() == "2026-04-27"
        for issue in result.errors
    )


def test_validate_historical_panel_manifest_tradable_scope_rejects_gap_inside_window(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    symbol_reference_path = manifest_path.parent / "symbol_reference.csv"
    symbol_reference = pd.read_csv(symbol_reference_path)
    symbol_reference["tradable_start_session"] = ""
    symbol_reference["tradable_end_session"] = ""
    symbol_reference.loc[
        symbol_reference["symbol"] == "BBB",
        "tradable_start_session",
    ] = "2026-04-23"
    symbol_reference.loc[
        symbol_reference["symbol"] == "BBB",
        "tradable_end_session",
    ] = "2026-04-24"
    symbol_reference.to_csv(symbol_reference_path, index=False)
    features_path = write_prepared_feature_file(manifest_path.parent)
    features = pd.read_csv(features_path)
    bbb_tradable_gap = (features["symbol"] == "BBB") & (features["session_date"] == "2026-04-24")
    features = features.loc[(features["symbol"] == "AAA") | ~bbb_tradable_gap]
    features = features.loc[
        ~((features["symbol"] == "BBB") & (features["session_date"] < "2026-04-23"))
    ]
    features = features.loc[
        ~((features["symbol"] == "BBB") & (features["session_date"] > "2026-04-24"))
    ]
    features.to_csv(features_path, index=False)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
        feature_start_session="2026-04-20",
        feature_coverage_scope="tradable_reference",
    )

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "FEATURE_COVERAGE_GAP" in _issue_codes(result.errors)
    assert any(
        issue.symbol == "BBB"
        and issue.session_date is not None
        and issue.session_date.isoformat() == "2026-04-24"
        for issue in result.errors
    )


def test_validate_historical_panel_manifest_rejects_feature_start_outside_panel(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    features_path = write_prepared_feature_file(manifest_path.parent)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        feature_start_session="2026-05-01",
    )

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "FEATURE_START_SESSION_OUT_OF_RANGE" in _issue_codes(result.errors)


def test_validate_historical_panel_manifest_rejects_missing_file(tmp_path: Path) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    (manifest_path.parent / "ohlcv.csv").unlink()

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert _issue_codes(result.errors) == {"FILE_MISSING"}


def test_validate_historical_panel_manifest_rejects_missing_required_column(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    ohlcv_path = manifest_path.parent / "ohlcv.csv"
    ohlcv = pd.read_csv(ohlcv_path).drop(columns=["raw_high"])
    ohlcv.to_csv(ohlcv_path, index=False)

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "FILE_VALIDATION_FAILED" in _issue_codes(result.errors)
    assert any("raw_high" in issue.message for issue in result.errors)


def test_validate_historical_panel_manifest_rejects_duplicate_symbol_session(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    ohlcv_path = manifest_path.parent / "ohlcv.csv"
    ohlcv = pd.read_csv(ohlcv_path)
    ohlcv = pd.concat([ohlcv, ohlcv.iloc[[0]]], ignore_index=True)
    ohlcv.to_csv(ohlcv_path, index=False)

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "FILE_VALIDATION_FAILED" in _issue_codes(result.errors)
    assert any("duplicate" in issue.message for issue in result.errors)


def test_validate_historical_panel_manifest_rejects_invalid_ohlc(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    ohlcv_path = manifest_path.parent / "ohlcv.csv"
    ohlcv = pd.read_csv(ohlcv_path)
    ohlcv.loc[0, "raw_high"] = 98.0
    ohlcv.to_csv(ohlcv_path, index=False)

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "FILE_VALIDATION_FAILED" in _issue_codes(result.errors)
    assert any("raw_high" in issue.message for issue in result.errors)


def test_validate_historical_panel_manifest_rejects_unknown_earnings_session(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    earnings_path = manifest_path.parent / "earnings_events.csv"
    earnings = pd.read_csv(earnings_path)
    earnings.loc[0, "event_session"] = "MIDDAY"
    earnings.to_csv(earnings_path, index=False)

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "FILE_VALIDATION_FAILED" in _issue_codes(result.errors)
    assert any("event_session" in issue.message for issue in result.errors)


def test_validate_historical_panel_manifest_rejects_unknown_corporate_action_symbol(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    corporate_actions_path = manifest_path.parent / "corporate_actions.csv"
    corporate_actions = pd.read_csv(corporate_actions_path)
    corporate_actions.loc[0, "symbol"] = "ZZZ"
    corporate_actions.to_csv(corporate_actions_path, index=False)

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "CORPORATE_ACTION_UNKNOWN_SYMBOL" in _issue_codes(result.errors)


def test_validate_historical_panel_manifest_rejects_manifest_count_mismatch(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_historical_panel_fixture(tmp_path)
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["expected_symbol_count"] = 3
    manifest_path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")

    result = validate_historical_panel_manifest(manifest_path)

    assert result.status is ReviewStatus.FAIL
    assert "EXPECTED_SYMBOL_COUNT_MISMATCH" in _issue_codes(result.errors)


def _copy_historical_panel_fixture(tmp_path: Path) -> Path:
    panel_path = tmp_path / "historical_panel"
    shutil.copytree(HISTORICAL_PANEL_FIXTURE, panel_path)
    return panel_path / "manifest.yaml"


def _issue_codes(issues: object) -> set[str]:
    return {issue.code for issue in issues}
