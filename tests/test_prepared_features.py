from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from swingmachine.enums import ReviewStatus
from swingmachine.lookahead_audit import build_lookahead_audit_report
from swingmachine.prepared_features import write_prepared_feature_panel_for_manifest


def test_prepared_feature_writer_updates_manifest_and_passes_lookahead(
    tmp_path: Path,
) -> None:
    panel_path = tmp_path / "panel"
    panel_path.mkdir()
    dates = pd.bdate_range("2024-01-01", periods=300)
    _write_ohlcv(panel_path / "ohlcv.csv", dates)
    _write_symbol_reference(panel_path / "symbol_reference.csv")
    pd.DataFrame(
        columns=["symbol", "ex_date", "split_ratio", "cash_dividend_per_share"]
    ).to_csv(panel_path / "corporate_actions.csv", index=False)
    pd.DataFrame(columns=["symbol", "event_date", "event_session"]).to_csv(
        panel_path / "earnings_events.csv",
        index=False,
    )
    manifest_path = panel_path / "manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "panel_id": "prepared-feature-test-panel",
                "schema_version": "1.0",
                "created_at": "2026-05-07T09:00:00",
                "base_path": ".",
                "calendar": "WEEKDAY",
                "timezone": "Europe/London",
                "start_session": dates[0].date().isoformat(),
                "end_session": dates[-1].date().isoformat(),
                "replay_start_session": dates[260].date().isoformat(),
                "replay_end_session": dates[-1].date().isoformat(),
                "feature_coverage_scope": "tradable_reference",
                "expected_symbol_count": 3,
                "expected_session_count": len(dates),
                "files": {
                    "ohlcv": {
                        "path": "ohlcv.csv",
                        "format": "csv",
                        "row_count": len(dates) * 3,
                    },
                    "symbol_reference": {
                        "path": "symbol_reference.csv",
                        "format": "csv",
                        "row_count": 3,
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
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    provenance = write_prepared_feature_panel_for_manifest(
        manifest_path,
        output_path=panel_path / "features.csv",
    )
    report = build_lookahead_audit_report(manifest_path)

    assert provenance["manifest_validation_status"] == ReviewStatus.PASS.value
    assert provenance["row_count"] == 120
    assert provenance["earnings_distance_policy"] == "no_earnings_events_supplied_default_9999"
    assert report.status is ReviewStatus.PASS
    assert report.violations == ()


def _write_ohlcv(path: Path, dates: pd.DatetimeIndex) -> None:
    rows = []
    for offset, symbol in enumerate(("AAA", "BBB", "SPY")):
        trend = np.linspace(80.0 + offset * 10.0, 180.0 + offset * 10.0, len(dates))
        wave = np.sin(np.arange(len(dates)) / 12.0) * 2.0
        close = trend + wave
        rows.append(
            pd.DataFrame(
                {
                    "symbol": symbol,
                    "session_date": dates,
                    "raw_open": close - 0.5,
                    "raw_high": close + 1.0,
                    "raw_low": close - 1.0,
                    "raw_close": close,
                    "raw_volume": np.full(len(dates), 1_000_000.0 + offset * 1000.0),
                }
            )
        )
    pd.concat(rows, ignore_index=True).to_csv(path, index=False)


def _write_symbol_reference(path: Path) -> None:
    pd.DataFrame(
        {
            "symbol": ["AAA", "BBB", "SPY"],
            "asset_type": ["COMMON_STOCK", "COMMON_STOCK", "ETF"],
            "exchange": ["XNYS", "XNYS", "XNYS"],
            "currency": ["USD", "USD", "USD"],
            "sector": ["Technology", "Industrial", "Index"],
            "is_tradable": [True, True, True],
        }
    ).to_csv(path, index=False)
