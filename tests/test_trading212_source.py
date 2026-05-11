from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from swingmachine.trading212_source import (
    Trading212ResearchProviderConfig,
    build_trading212_extraction_plans,
    build_trading212_provider_panel_drift_report,
    export_trading212_selected_period_data,
    inspect_trading212_source,
    load_trading212_source_config,
    preflight_trading212_source_coverage,
)


def test_load_trading212_source_config(tmp_path: Path) -> None:
    db_path = tmp_path / "research.db"
    symbols_path = tmp_path / "symbols.txt"
    config_path = tmp_path / "sources.yaml"
    symbols_path.write_text("AAA\nBBB\n")
    config_path.write_text(
        f"""
baseline_id: swing_machine_v0_1
config_version: swing_machine_v0_1_trading212_sources_v1
providers:
  - provider: alpaca
    db_path: {db_path}
    symbols_file: {symbols_path}
    output_root: {tmp_path / "out"}
"""
    )

    config = load_trading212_source_config(config_path)

    assert config.baseline_id == "swing_machine_v0_1"
    assert config.providers[0].provider == "alpaca"
    assert config.providers[0].preferred_timeframe == "1d"
    assert config.providers[0].fallback_timeframe == "1m"


def test_inspect_trading212_source_reads_bounded_schema_and_samples(tmp_path: Path) -> None:
    provider_config = _provider_config(tmp_path, symbols=["AAA", "BBB"])
    _create_research_db(provider_config.db_path)

    inspection = inspect_trading212_source(provider_config, sample_symbol_limit=2)

    assert inspection.exists is True
    assert inspection.readable is True
    assert inspection.bars_table_exists is True
    assert {column.name for column in inspection.columns} >= {"symbol", "timeframe", "ts"}
    assert "idx_bars_symbol_tf_ts" in {index.name for index in inspection.indexes}
    assert inspection.sample_rows
    assert inspection.errors == []


def test_preflight_trading212_source_coverage_uses_preferred_then_fallback(
    tmp_path: Path,
) -> None:
    provider_config = _provider_config(tmp_path, symbols=["AAA", "BBB"])
    period_plan_path = _selected_period_plan(tmp_path)
    _create_research_db(provider_config.db_path)

    report = preflight_trading212_source_coverage(provider_config, period_plan_path)

    assert report.passed is True
    selected = {(row.symbol, row.selected_timeframe) for row in report.coverage_rows}
    assert ("AAA", "1d") in selected
    assert ("BBB", "1m") in selected


def test_preflight_trading212_source_coverage_reports_missing_symbol(
    tmp_path: Path,
) -> None:
    provider_config = _provider_config(tmp_path, symbols=["AAA", "BBB", "CCC"])
    period_plan_path = _selected_period_plan(tmp_path)
    _create_research_db(provider_config.db_path)

    report = preflight_trading212_source_coverage(provider_config, period_plan_path)

    assert report.passed is False
    assert "missing_bars:fixture_period:CCC" in report.blockers


def test_build_trading212_extraction_plans_adds_explicit_lookback(
    tmp_path: Path,
) -> None:
    provider_config = _provider_config(tmp_path, symbols=["AAA"])
    period_plan_path = _selected_period_plan(tmp_path)

    plans = build_trading212_extraction_plans(
        provider_config,
        period_plan_path,
        lookback_calendar_days=10,
    )

    assert len(plans) == 1
    assert plans[0].qualification_start_date.isoformat() == "2026-04-20"
    assert plans[0].extraction_start_date.isoformat() == "2026-04-10"
    assert plans[0].output_dir == provider_config.output_root / "fixture_period"


def test_export_trading212_selected_period_data_writes_valid_contract_files(
    tmp_path: Path,
) -> None:
    provider_config = _provider_config(tmp_path, symbols=["AAA", "BBB"])
    period_plan_path = _selected_period_plan(tmp_path)
    _create_research_db(provider_config.db_path)

    summary = export_trading212_selected_period_data(provider_config, period_plan_path)

    assert summary.passed is True
    exported_period = summary.periods[0]
    assert exported_period.historical_ohlcv_path.exists()
    assert exported_period.symbol_reference_path.exists()
    assert exported_period.corporate_actions_path.exists()
    assert exported_period.earnings_events_path.exists()
    historical = pd.read_parquet(exported_period.historical_ohlcv_path)
    assert set(historical["symbol"]) == {"AAA", "BBB"}
    bbb = historical[historical["symbol"] == "BBB"].iloc[0]
    assert bbb["raw_open"] == 10.0
    assert bbb["raw_high"] == 12.0
    assert bbb["raw_low"] == 9.0
    assert bbb["raw_close"] == 11.0
    assert bbb["raw_volume"] == 300.0
    assert exported_period.source_timeframes_by_symbol["AAA"] == "1d"
    assert exported_period.source_timeframes_by_symbol["BBB"] == "1m_aggregated_daily"


def test_provider_panel_drift_report_detects_value_drift(tmp_path: Path) -> None:
    left_csv = tmp_path / "left.csv"
    right_csv = tmp_path / "right.csv"
    left_csv.write_text(
        "symbol,session_date,raw_open,raw_high,raw_low,raw_close,raw_volume\n"
        "AAA,2026-04-20,10.0,11.0,9.0,10.5,1000\n"
    )
    right_csv.write_text(
        "symbol,session_date,raw_open,raw_high,raw_low,raw_close,raw_volume\n"
        "AAA,2026-04-20,10.0,11.0,9.0,10.8,1000\n"
    )
    left_summary = tmp_path / "left_summary.json"
    right_summary = tmp_path / "right_summary.json"
    left_summary.write_text(
        f"""{{
  "provider": "alpaca",
  "periods": [
    {{"period_id": "fixture_period", "historical_ohlcv_path": "{left_csv}"}}
  ]
}}
"""
    )
    right_summary.write_text(
        f"""{{
  "provider": "huggingface",
  "periods": [
    {{"period_id": "fixture_period", "historical_ohlcv_path": "{right_csv}"}}
  ]
}}
"""
    )

    report = build_trading212_provider_panel_drift_report(
        left_summary,
        right_summary,
        price_abs_tolerance=0.01,
    )

    assert report.passed is False
    assert report.blockers == ["value_drift:fixture_period:AAA"]
    assert round(report.rows[0].max_abs_close_diff or 0.0, 6) == 0.3


def _provider_config(tmp_path: Path, *, symbols: list[str]) -> Trading212ResearchProviderConfig:
    symbols_path = tmp_path / "symbols.txt"
    symbols_path.write_text("\n".join(symbols) + "\n")
    return Trading212ResearchProviderConfig(
        provider="alpaca",
        db_path=tmp_path / "research.db",
        symbols_file=symbols_path,
        output_root=tmp_path / "exported",
        preferred_timeframe="1d",
        fallback_timeframe="1m",
        lookback_calendar_days=30,
    )


def _selected_period_plan(tmp_path: Path) -> Path:
    path = tmp_path / "selected_periods.yaml"
    path.write_text(
        """
baseline_id: swing_machine_v0_1
plan_version: swing_machine_v0_1_selected_period_plan_v1
periods:
  - period_id: fixture_period
    start_date: 2026-04-20
    end_date: 2026-04-24
    purpose: fixture
"""
    )
    return path


def _create_research_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
create table bars (
    symbol text not null,
    timeframe text not null,
    ts text not null,
    o real not null,
    h real not null,
    l real not null,
    c real not null,
    v real not null,
    provider text not null,
    primary key (symbol, timeframe, ts, provider)
);
create index idx_bars_provider_tf_ts on bars(provider, timeframe, ts);
create index idx_bars_symbol_tf_ts on bars(symbol, timeframe, ts);
"""
    )
    conn.executemany(
        "insert into bars values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                "AAA",
                "1d",
                "2026-04-20T00:00:00+00:00",
                100.0,
                110.0,
                95.0,
                105.0,
                1_000.0,
                "fixture",
            ),
            (
                "AAA",
                "1d",
                "2026-04-21T00:00:00+00:00",
                105.0,
                111.0,
                101.0,
                108.0,
                1_100.0,
                "fixture",
            ),
            (
                "BBB",
                "1m",
                "2026-04-20T14:31:00+00:00",
                10.0,
                10.5,
                9.0,
                10.25,
                100.0,
                "fixture",
            ),
            (
                "BBB",
                "1m",
                "2026-04-20T14:32:00+00:00",
                10.25,
                12.0,
                10.0,
                11.0,
                200.0,
                "fixture",
            ),
        ],
    )
    conn.commit()
    conn.close()
