"""Read-only adapters for Trading212 research data sources.

The Trading212 ORB repository contains local research SQLite databases sourced from
Alpaca and Hugging Face. This module exposes a guarded, bounded export path that
turns those databases into swing-machine selected-period qualification inputs.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import yaml
from pydantic import BaseModel, ConfigDict, Field

from swingmachine.data_contracts import (
    validate_corporate_actions_data,
    validate_earnings_events_data,
    validate_historical_ohlcv_data,
    validate_symbol_reference_data,
)
from swingmachine.enums import AssetType

TRADING212_SOURCE_CONFIG_VERSION = "swing_machine_v0_1_trading212_sources_v1"
Trading212Provider = Literal["alpaca", "huggingface"]

HISTORICAL_OHLCV_COLUMNS = [
    "symbol",
    "session_date",
    "raw_open",
    "raw_high",
    "raw_low",
    "raw_close",
    "raw_volume",
]
SYMBOL_REFERENCE_COLUMNS = [
    "symbol",
    "asset_type",
    "exchange",
    "currency",
    "sector",
    "is_tradable",
]
CORPORATE_ACTION_COLUMNS = [
    "symbol",
    "ex_date",
    "split_ratio",
    "cash_dividend_per_share",
]
EARNINGS_EVENT_COLUMNS = [
    "symbol",
    "event_date",
    "event_session",
]
ETF_SYMBOLS = {"SPY", "QQQ", "IWM", "DIA"}


class Trading212ResearchProviderConfig(BaseModel):
    """Explicit configuration for one Trading212 research SQLite source."""

    model_config = ConfigDict(frozen=True)

    provider: Trading212Provider
    db_path: Path
    symbols_file: Path
    output_root: Path
    preferred_timeframe: str = "1d"
    fallback_timeframe: str = "1m"
    lookback_calendar_days: int = Field(default=500, ge=0)
    excluded_symbols: tuple[str, ...] = Field(default_factory=tuple)


class Trading212ResearchSourceConfigSet(BaseModel):
    """Configuration set for all available Trading212 research providers."""

    model_config = ConfigDict(frozen=True)

    baseline_id: str
    config_version: str = TRADING212_SOURCE_CONFIG_VERSION
    providers: list[Trading212ResearchProviderConfig]


class Trading212SourceColumn(BaseModel):
    name: str
    declared_type: str
    not_null: bool
    primary_key_position: int


class Trading212SourceIndex(BaseModel):
    name: str
    unique: bool
    origin: str
    partial: bool


class Trading212SourceSampleRow(BaseModel):
    symbol: str
    timeframe: str
    ts: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    provider: str | None = None


class Trading212SourceInspection(BaseModel):
    provider: Trading212Provider
    db_path: Path
    exists: bool
    readable: bool
    bars_table_exists: bool
    columns: list[Trading212SourceColumn] = Field(default_factory=list)
    indexes: list[Trading212SourceIndex] = Field(default_factory=list)
    sample_rows: list[Trading212SourceSampleRow] = Field(default_factory=list)
    sample_timeframes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class Trading212ExtractionPeriodPlan(BaseModel):
    provider: Trading212Provider
    period_id: str
    qualification_start_date: date
    qualification_end_date: date
    extraction_start_date: date
    extraction_end_date: date
    lookback_calendar_days: int
    output_dir: Path
    symbols: list[str]


class Trading212CoverageRow(BaseModel):
    period_id: str
    symbol: str
    preferred_timeframe: str
    preferred_row_count: int
    preferred_first_ts: str | None = None
    preferred_last_ts: str | None = None
    fallback_timeframe: str
    fallback_row_count: int
    fallback_first_ts: str | None = None
    fallback_last_ts: str | None = None
    covered: bool
    selected_timeframe: str | None = None
    blocker: str | None = None


class Trading212CoverageReport(BaseModel):
    provider: Trading212Provider
    db_path: Path
    selected_period_plan_path: Path
    checked_periods: int
    checked_symbols: int
    excluded_symbols: list[str]
    checked_rows: int
    covered_rows: int
    missing_rows: int
    passed: bool
    coverage_rows: list[Trading212CoverageRow]
    blockers: list[str]


class Trading212ExportedPeriod(BaseModel):
    period_id: str
    output_dir: Path
    historical_ohlcv_path: Path
    symbol_reference_path: Path
    corporate_actions_path: Path
    earnings_events_path: Path
    exported_symbols: list[str]
    missing_symbols: list[str]
    source_timeframes_by_symbol: dict[str, str]
    historical_ohlcv_rows: int


class Trading212SelectedPeriodExportSummary(BaseModel):
    provider: Trading212Provider
    db_path: Path
    selected_period_plan_path: Path
    output_root: Path
    passed: bool
    excluded_symbols: list[str]
    periods: list[Trading212ExportedPeriod]
    blockers: list[str]


class Trading212ProviderPanelDriftRow(BaseModel):
    period_id: str
    symbol: str
    left_sessions: int
    right_sessions: int
    matched_sessions: int
    missing_in_left: int
    missing_in_right: int
    max_abs_open_diff: float | None = None
    max_abs_high_diff: float | None = None
    max_abs_low_diff: float | None = None
    max_abs_close_diff: float | None = None
    max_abs_volume_diff: float | None = None
    passed: bool
    blocker: str | None = None


class Trading212ProviderPanelDriftReport(BaseModel):
    left_provider: str
    right_provider: str
    left_summary_path: Path
    right_summary_path: Path
    price_abs_tolerance: float
    volume_abs_tolerance: float
    passed: bool
    rows: list[Trading212ProviderPanelDriftRow]
    blockers: list[str]


def load_trading212_source_config(path: Path | str) -> Trading212ResearchSourceConfigSet:
    """Load explicit Trading212 source configuration from YAML."""

    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text()) or {}
    config = Trading212ResearchSourceConfigSet.model_validate(raw)
    if config.config_version != TRADING212_SOURCE_CONFIG_VERSION:
        raise ValueError(
            f"Unsupported Trading212 source config version: {config.config_version}"
        )
    return config


def trading212_provider_config(
    config_set: Trading212ResearchSourceConfigSet, provider: str
) -> Trading212ResearchProviderConfig:
    """Select one provider config by provider id."""

    for provider_config in config_set.providers:
        if provider_config.provider == provider:
            return provider_config
    available = ", ".join(sorted(item.provider for item in config_set.providers))
    raise ValueError(f"Unknown Trading212 provider {provider!r}; available: {available}")


def load_trading212_symbols(
    path: Path | str,
    max_symbols: int = 0,
    excluded_symbols: tuple[str, ...] | list[str] = (),
) -> list[str]:
    """Load a deterministic symbol universe from a Trading212 universe file."""

    symbols: list[str] = []
    exclusions = {symbol.upper() for symbol in excluded_symbols}
    for raw_line in Path(path).read_text().splitlines():
        symbol = raw_line.strip().upper()
        if not symbol or symbol.startswith("#"):
            continue
        if symbol in exclusions:
            continue
        symbols.append(symbol)
        if max_symbols and len(symbols) >= max_symbols:
            break
    return symbols


def inspect_trading212_source(
    provider_config: Trading212ResearchProviderConfig,
    sample_symbol_limit: int = 20,
) -> Trading212SourceInspection:
    """Inspect schema/index/sample rows using only bounded read-only queries."""

    exists = provider_config.db_path.exists()
    if not exists:
        return Trading212SourceInspection(
            provider=provider_config.provider,
            db_path=provider_config.db_path,
            exists=False,
            readable=False,
            bars_table_exists=False,
            errors=["database_path_missing"],
        )

    try:
        with _connect_read_only(provider_config.db_path) as conn:
            bars_table_exists = _bars_table_exists(conn)
            if not bars_table_exists:
                return Trading212SourceInspection(
                    provider=provider_config.provider,
                    db_path=provider_config.db_path,
                    exists=True,
                    readable=True,
                    bars_table_exists=False,
                    errors=["bars_table_missing"],
                )
            columns = _read_bars_columns(conn)
            indexes = _read_bars_indexes(conn)
            symbols = load_trading212_symbols(
                provider_config.symbols_file,
                max_symbols=sample_symbol_limit,
                excluded_symbols=provider_config.excluded_symbols,
            )
            sample_rows = _read_sample_rows(conn, symbols, limit=sample_symbol_limit)
            sample_timeframes = sorted({row.timeframe for row in sample_rows})
            return Trading212SourceInspection(
                provider=provider_config.provider,
                db_path=provider_config.db_path,
                exists=True,
                readable=True,
                bars_table_exists=True,
                columns=columns,
                indexes=indexes,
                sample_rows=sample_rows,
                sample_timeframes=sample_timeframes,
                errors=[],
            )
    except sqlite3.Error as exc:
        return Trading212SourceInspection(
            provider=provider_config.provider,
            db_path=provider_config.db_path,
            exists=True,
            readable=False,
            bars_table_exists=False,
            errors=[f"sqlite_error:{exc}"],
        )


def build_trading212_extraction_plans(
    provider_config: Trading212ResearchProviderConfig,
    selected_period_plan_path: Path | str,
    *,
    lookback_calendar_days: int | None = None,
    max_symbols: int = 0,
) -> list[Trading212ExtractionPeriodPlan]:
    """Build selected-period extraction windows with explicit lookback history."""

    selected_periods = _load_selected_periods(selected_period_plan_path)
    symbols = load_trading212_symbols(
        provider_config.symbols_file,
        max_symbols=max_symbols,
        excluded_symbols=provider_config.excluded_symbols,
    )
    lookback = (
        provider_config.lookback_calendar_days
        if lookback_calendar_days is None
        else lookback_calendar_days
    )
    plans: list[Trading212ExtractionPeriodPlan] = []
    for selected_period in selected_periods:
        start_date = selected_period["start_date"]
        end_date = selected_period["end_date"]
        period_id = selected_period["period_id"]
        plans.append(
            Trading212ExtractionPeriodPlan(
                provider=provider_config.provider,
                period_id=period_id,
                qualification_start_date=start_date,
                qualification_end_date=end_date,
                extraction_start_date=start_date - timedelta(days=lookback),
                extraction_end_date=end_date,
                lookback_calendar_days=lookback,
                output_dir=provider_config.output_root / period_id,
                symbols=symbols,
            )
        )
    return plans


def preflight_trading212_source_coverage(
    provider_config: Trading212ResearchProviderConfig,
    selected_period_plan_path: Path | str,
    *,
    max_symbols: int = 0,
) -> Trading212CoverageReport:
    """Run bounded coverage checks for each selected period and symbol."""

    plans = build_trading212_extraction_plans(
        provider_config,
        selected_period_plan_path,
        max_symbols=max_symbols,
    )
    coverage_rows: list[Trading212CoverageRow] = []
    blockers: list[str] = []
    with _connect_read_only(provider_config.db_path) as conn:
        for plan in plans:
            for symbol in plan.symbols:
                preferred = _count_symbol_rows(
                    conn,
                    symbol=symbol,
                    timeframe=provider_config.preferred_timeframe,
                    start_date=plan.qualification_start_date,
                    end_date=plan.qualification_end_date,
                )
                fallback = _count_symbol_rows(
                    conn,
                    symbol=symbol,
                    timeframe=provider_config.fallback_timeframe,
                    start_date=plan.qualification_start_date,
                    end_date=plan.qualification_end_date,
                )
                selected_timeframe: str | None = None
                blocker: str | None = None
                if preferred["row_count"]:
                    selected_timeframe = provider_config.preferred_timeframe
                elif fallback["row_count"]:
                    selected_timeframe = provider_config.fallback_timeframe
                else:
                    blocker = f"missing_bars:{plan.period_id}:{symbol}"
                    blockers.append(blocker)
                coverage_rows.append(
                    Trading212CoverageRow(
                        period_id=plan.period_id,
                        symbol=symbol,
                        preferred_timeframe=provider_config.preferred_timeframe,
                        preferred_row_count=preferred["row_count"],
                        preferred_first_ts=preferred["first_ts"],
                        preferred_last_ts=preferred["last_ts"],
                        fallback_timeframe=provider_config.fallback_timeframe,
                        fallback_row_count=fallback["row_count"],
                        fallback_first_ts=fallback["first_ts"],
                        fallback_last_ts=fallback["last_ts"],
                        covered=blocker is None,
                        selected_timeframe=selected_timeframe,
                        blocker=blocker,
                    )
                )
    covered_rows = sum(1 for row in coverage_rows if row.covered)
    missing_rows = len(coverage_rows) - covered_rows
    return Trading212CoverageReport(
        provider=provider_config.provider,
        db_path=provider_config.db_path,
        selected_period_plan_path=Path(selected_period_plan_path),
        checked_periods=len(plans),
        checked_symbols=len(plans[0].symbols) if plans else 0,
        excluded_symbols=list(provider_config.excluded_symbols),
        checked_rows=len(coverage_rows),
        covered_rows=covered_rows,
        missing_rows=missing_rows,
        passed=missing_rows == 0,
        coverage_rows=coverage_rows,
        blockers=blockers,
    )


def export_trading212_selected_period_data(
    provider_config: Trading212ResearchProviderConfig,
    selected_period_plan_path: Path | str,
    *,
    max_symbols: int = 0,
) -> Trading212SelectedPeriodExportSummary:
    """Export selected-period qualification inputs from a read-only research DB."""

    plans = build_trading212_extraction_plans(
        provider_config,
        selected_period_plan_path,
        max_symbols=max_symbols,
    )
    periods: list[Trading212ExportedPeriod] = []
    blockers: list[str] = []
    with _connect_read_only(provider_config.db_path) as conn:
        for plan in plans:
            period = _export_period(conn, provider_config, plan)
            periods.append(period)
            for symbol in period.missing_symbols:
                blockers.append(f"missing_bars:{period.period_id}:{symbol}")
    return Trading212SelectedPeriodExportSummary(
        provider=provider_config.provider,
        db_path=provider_config.db_path,
        selected_period_plan_path=Path(selected_period_plan_path),
        output_root=provider_config.output_root,
        passed=not blockers,
        excluded_symbols=list(provider_config.excluded_symbols),
        periods=periods,
        blockers=blockers,
    )


def write_trading212_json_report(path: Path | str, report: BaseModel) -> Path:
    """Write a pydantic report as deterministic JSON."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    )
    return output_path


def build_trading212_provider_panel_drift_report(
    left_summary_path: Path | str,
    right_summary_path: Path | str,
    *,
    price_abs_tolerance: float = 0.01,
    volume_abs_tolerance: float = 0.0,
) -> Trading212ProviderPanelDriftReport:
    """Compare two exported provider panels at period/symbol/session level."""

    left_path = Path(left_summary_path)
    right_path = Path(right_summary_path)
    left_summary = json.loads(left_path.read_text())
    right_summary = json.loads(right_path.read_text())
    left_periods = {period["period_id"]: period for period in left_summary["periods"]}
    right_periods = {period["period_id"]: period for period in right_summary["periods"]}
    rows: list[Trading212ProviderPanelDriftRow] = []
    blockers: list[str] = []
    for period_id in sorted(set(left_periods) | set(right_periods)):
        left_period = left_periods.get(period_id)
        right_period = right_periods.get(period_id)
        if left_period is None or right_period is None:
            blocker = f"missing_period:{period_id}"
            blockers.append(blocker)
            rows.append(
                Trading212ProviderPanelDriftRow(
                    period_id=period_id,
                    symbol="*",
                    left_sessions=0,
                    right_sessions=0,
                    matched_sessions=0,
                    missing_in_left=0,
                    missing_in_right=0,
                    passed=False,
                    blocker=blocker,
                )
            )
            continue
        left_frame = _read_exported_ohlcv_frame(left_period["historical_ohlcv_path"])
        right_frame = _read_exported_ohlcv_frame(
            right_period["historical_ohlcv_path"]
        )
        period_rows, period_blockers = _compare_provider_period_frames(
            period_id=period_id,
            left_frame=left_frame,
            right_frame=right_frame,
            price_abs_tolerance=price_abs_tolerance,
            volume_abs_tolerance=volume_abs_tolerance,
        )
        rows.extend(period_rows)
        blockers.extend(period_blockers)
    return Trading212ProviderPanelDriftReport(
        left_provider=left_summary["provider"],
        right_provider=right_summary["provider"],
        left_summary_path=left_path,
        right_summary_path=right_path,
        price_abs_tolerance=price_abs_tolerance,
        volume_abs_tolerance=volume_abs_tolerance,
        passed=not blockers,
        rows=rows,
        blockers=blockers,
    )


def _connect_read_only(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)


def _read_exported_ohlcv_frame(path: Path | str) -> pd.DataFrame:
    ohlcv_path = Path(path)
    if ohlcv_path.suffix == ".parquet":
        frame = pd.read_parquet(ohlcv_path)
    else:
        frame = pd.read_csv(ohlcv_path)
    frame["symbol"] = frame["symbol"].astype(str)
    return frame


def _compare_provider_period_frames(
    *,
    period_id: str,
    left_frame: pd.DataFrame,
    right_frame: pd.DataFrame,
    price_abs_tolerance: float,
    volume_abs_tolerance: float,
) -> tuple[list[Trading212ProviderPanelDriftRow], list[str]]:
    left_frame = left_frame.copy()
    right_frame = right_frame.copy()
    left_frame["session_date"] = left_frame["session_date"].astype(str)
    right_frame["session_date"] = right_frame["session_date"].astype(str)
    merged = left_frame.merge(
        right_frame,
        on=["symbol", "session_date"],
        how="outer",
        suffixes=("_left", "_right"),
        indicator=True,
    )
    rows: list[Trading212ProviderPanelDriftRow] = []
    blockers: list[str] = []
    for symbol in sorted(merged["symbol"].dropna().unique()):
        symbol_frame = merged[merged["symbol"] == symbol]
        missing_in_left = int((symbol_frame["_merge"] == "right_only").sum())
        missing_in_right = int((symbol_frame["_merge"] == "left_only").sum())
        matched = symbol_frame[symbol_frame["_merge"] == "both"]
        diffs = _provider_panel_diffs(matched)
        blocker: str | None = None
        if missing_in_left or missing_in_right:
            blocker = f"session_mismatch:{period_id}:{symbol}"
        elif _diff_exceeds_tolerance(
            diffs,
            price_abs_tolerance=price_abs_tolerance,
            volume_abs_tolerance=volume_abs_tolerance,
        ):
            blocker = f"value_drift:{period_id}:{symbol}"
        if blocker:
            blockers.append(blocker)
        rows.append(
            Trading212ProviderPanelDriftRow(
                period_id=period_id,
                symbol=symbol,
                left_sessions=int((symbol_frame["_merge"] != "right_only").sum()),
                right_sessions=int((symbol_frame["_merge"] != "left_only").sum()),
                matched_sessions=len(matched),
                missing_in_left=missing_in_left,
                missing_in_right=missing_in_right,
                max_abs_open_diff=diffs["raw_open"],
                max_abs_high_diff=diffs["raw_high"],
                max_abs_low_diff=diffs["raw_low"],
                max_abs_close_diff=diffs["raw_close"],
                max_abs_volume_diff=diffs["raw_volume"],
                passed=blocker is None,
                blocker=blocker,
            )
        )
    return rows, blockers


def _provider_panel_diffs(matched: pd.DataFrame) -> dict[str, float | None]:
    if matched.empty:
        return {
            "raw_open": None,
            "raw_high": None,
            "raw_low": None,
            "raw_close": None,
            "raw_volume": None,
        }
    diffs: dict[str, float | None] = {}
    for column in ("raw_open", "raw_high", "raw_low", "raw_close", "raw_volume"):
        diff = (matched[f"{column}_left"] - matched[f"{column}_right"]).abs()
        diffs[column] = float(diff.max()) if not diff.empty else None
    return diffs


def _diff_exceeds_tolerance(
    diffs: dict[str, float | None],
    *,
    price_abs_tolerance: float,
    volume_abs_tolerance: float,
) -> bool:
    for column in ("raw_open", "raw_high", "raw_low", "raw_close"):
        value = diffs[column]
        if value is not None and value > price_abs_tolerance:
            return True
    volume_value = diffs["raw_volume"]
    return volume_value is not None and volume_value > volume_abs_tolerance


def _bars_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "select 1 from sqlite_master where type = 'table' and name = 'bars' limit 1"
    ).fetchone()
    return row is not None


def _read_bars_columns(conn: sqlite3.Connection) -> list[Trading212SourceColumn]:
    rows = conn.execute("pragma table_info(bars)").fetchall()
    return [
        Trading212SourceColumn(
            name=row[1],
            declared_type=row[2],
            not_null=bool(row[3]),
            primary_key_position=int(row[5]),
        )
        for row in rows
    ]


def _read_bars_indexes(conn: sqlite3.Connection) -> list[Trading212SourceIndex]:
    rows = conn.execute("pragma index_list(bars)").fetchall()
    return [
        Trading212SourceIndex(
            name=row[1],
            unique=bool(row[2]),
            origin=row[3],
            partial=bool(row[4]),
        )
        for row in rows
    ]


def _read_sample_rows(
    conn: sqlite3.Connection, symbols: list[str], *, limit: int
) -> list[Trading212SourceSampleRow]:
    if not symbols or limit <= 0:
        return []
    sample_rows: list[Trading212SourceSampleRow] = []
    query = """
        select symbol, timeframe, ts, o, h, l, c, v, provider
        from bars
        where symbol = ?
        order by symbol, timeframe, ts
        limit ?
    """
    for symbol in symbols:
        for row in conn.execute(query, (symbol, limit)).fetchall():
            sample_rows.append(
                Trading212SourceSampleRow(
                    symbol=row[0],
                    timeframe=row[1],
                    ts=row[2],
                    open=row[3],
                    high=row[4],
                    low=row[5],
                    close=row[6],
                    volume=row[7],
                    provider=row[8],
                )
            )
            if len(sample_rows) >= limit:
                return sample_rows
    return sample_rows


def _load_selected_periods(path: Path | str) -> list[dict[str, Any]]:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    periods = raw.get("periods", [])
    parsed_periods: list[dict[str, Any]] = []
    for period in periods:
        parsed_periods.append(
            {
                "period_id": str(period["period_id"]),
                "start_date": _parse_date(period["start_date"]),
                "end_date": _parse_date(period["end_date"]),
            }
        )
    return parsed_periods


def _parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return date.fromisoformat(str(value))


def _window_bounds(start_date: date, end_date: date) -> tuple[str, str]:
    start_ts = datetime.combine(start_date, time.min, tzinfo=UTC).isoformat()
    exclusive_end_ts = datetime.combine(
        end_date + timedelta(days=1), time.min, tzinfo=UTC
    ).isoformat()
    return start_ts, exclusive_end_ts


def _count_symbol_rows(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    timeframe: str,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    start_ts, exclusive_end_ts = _window_bounds(start_date, end_date)
    first_row = conn.execute(
        """
        select ts
        from bars
        where symbol = ? and timeframe = ? and ts >= ? and ts < ?
        order by ts
        limit 1
        """,
        (symbol, timeframe, start_ts, exclusive_end_ts),
    ).fetchone()
    if first_row is None:
        return {"row_count": 0, "first_ts": None, "last_ts": None}
    last_row = conn.execute(
        """
        select ts
        from bars
        where symbol = ? and timeframe = ? and ts >= ? and ts < ?
        order by ts desc
        limit 1
        """,
        (symbol, timeframe, start_ts, exclusive_end_ts),
    ).fetchone()
    return {"row_count": 1, "first_ts": first_row[0], "last_ts": last_row[0]}


def _export_period(
    conn: sqlite3.Connection,
    provider_config: Trading212ResearchProviderConfig,
    plan: Trading212ExtractionPeriodPlan,
) -> Trading212ExportedPeriod:
    ohlcv_frames: list[pd.DataFrame] = []
    exported_symbols: list[str] = []
    missing_symbols: list[str] = []
    source_timeframes_by_symbol: dict[str, str] = {}
    for symbol in plan.symbols:
        preferred_frame = _fetch_daily_symbol_frame(
            conn,
            symbol=symbol,
            timeframe=provider_config.preferred_timeframe,
            start_date=plan.extraction_start_date,
            end_date=plan.extraction_end_date,
        )
        if not preferred_frame.empty:
            ohlcv_frames.append(preferred_frame)
            exported_symbols.append(symbol)
            source_timeframes_by_symbol[symbol] = provider_config.preferred_timeframe
            continue
        fallback_frame = _fetch_aggregated_intraday_symbol_frame(
            conn,
            symbol=symbol,
            timeframe=provider_config.fallback_timeframe,
            start_date=plan.extraction_start_date,
            end_date=plan.extraction_end_date,
        )
        if not fallback_frame.empty:
            ohlcv_frames.append(fallback_frame)
            exported_symbols.append(symbol)
            source_timeframes_by_symbol[symbol] = (
                f"{provider_config.fallback_timeframe}_aggregated_daily"
            )
        else:
            missing_symbols.append(symbol)
    historical_ohlcv = (
        pd.concat(ohlcv_frames, ignore_index=True)
        if ohlcv_frames
        else pd.DataFrame(columns=HISTORICAL_OHLCV_COLUMNS)
    )
    historical_ohlcv = historical_ohlcv[HISTORICAL_OHLCV_COLUMNS].sort_values(
        ["symbol", "session_date"]
    )
    symbol_reference = _build_symbol_reference(exported_symbols)
    corporate_actions = pd.DataFrame(columns=CORPORATE_ACTION_COLUMNS)
    earnings_events = pd.DataFrame(columns=EARNINGS_EVENT_COLUMNS)

    _ensure_contract_valid("historical_ohlcv", validate_historical_ohlcv_data, historical_ohlcv)
    _ensure_contract_valid("symbol_reference", validate_symbol_reference_data, symbol_reference)
    _ensure_contract_valid("corporate_actions", validate_corporate_actions_data, corporate_actions)
    _ensure_contract_valid("earnings_events", validate_earnings_events_data, earnings_events)

    plan.output_dir.mkdir(parents=True, exist_ok=True)
    historical_ohlcv_path = plan.output_dir / "ohlcv.parquet"
    historical_ohlcv_csv_path = plan.output_dir / "historical_ohlcv.csv"
    symbol_reference_path = plan.output_dir / "symbol_reference.csv"
    corporate_actions_path = plan.output_dir / "corporate_actions.csv"
    earnings_events_path = plan.output_dir / "earnings_events.csv"
    historical_ohlcv.to_parquet(historical_ohlcv_path, index=False)
    historical_ohlcv.to_csv(historical_ohlcv_csv_path, index=False)
    symbol_reference.to_csv(symbol_reference_path, index=False)
    corporate_actions.to_csv(corporate_actions_path, index=False)
    earnings_events.to_csv(earnings_events_path, index=False)

    return Trading212ExportedPeriod(
        period_id=plan.period_id,
        output_dir=plan.output_dir,
        historical_ohlcv_path=historical_ohlcv_path,
        symbol_reference_path=symbol_reference_path,
        corporate_actions_path=corporate_actions_path,
        earnings_events_path=earnings_events_path,
        exported_symbols=exported_symbols,
        missing_symbols=missing_symbols,
        source_timeframes_by_symbol=source_timeframes_by_symbol,
        historical_ohlcv_rows=len(historical_ohlcv),
    )


def _fetch_daily_symbol_frame(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    timeframe: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    start_ts, exclusive_end_ts = _window_bounds(start_date, end_date)
    rows = conn.execute(
        """
        select symbol, ts, o, h, l, c, v
        from bars
        where symbol = ? and timeframe = ? and ts >= ? and ts < ?
        order by ts
        """,
        (symbol, timeframe, start_ts, exclusive_end_ts),
    ).fetchall()
    if not rows:
        return pd.DataFrame(columns=HISTORICAL_OHLCV_COLUMNS)
    frame = pd.DataFrame(rows, columns=["symbol", "ts", "o", "h", "l", "c", "v"])
    frame["session_date"] = pd.to_datetime(frame["ts"], utc=True).dt.date.astype(str)
    return pd.DataFrame(
        {
            "symbol": frame["symbol"],
            "session_date": frame["session_date"],
            "raw_open": frame["o"],
            "raw_high": frame["h"],
            "raw_low": frame["l"],
            "raw_close": frame["c"],
            "raw_volume": frame["v"],
        }
    )


def _fetch_aggregated_intraday_symbol_frame(
    conn: sqlite3.Connection,
    *,
    symbol: str,
    timeframe: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    start_ts, exclusive_end_ts = _window_bounds(start_date, end_date)
    rows = conn.execute(
        """
        select symbol, ts, o, h, l, c, v
        from bars
        where symbol = ? and timeframe = ? and ts >= ? and ts < ?
        order by ts
        """,
        (symbol, timeframe, start_ts, exclusive_end_ts),
    ).fetchall()
    if not rows:
        return pd.DataFrame(columns=HISTORICAL_OHLCV_COLUMNS)
    frame = pd.DataFrame(rows, columns=["symbol", "ts", "o", "h", "l", "c", "v"])
    frame["session_date"] = pd.to_datetime(frame["ts"], utc=True).dt.date.astype(str)
    grouped = frame.groupby(["symbol", "session_date"], as_index=False).agg(
        raw_open=("o", "first"),
        raw_high=("h", "max"),
        raw_low=("l", "min"),
        raw_close=("c", "last"),
        raw_volume=("v", "sum"),
    )
    return grouped[HISTORICAL_OHLCV_COLUMNS]


def _build_symbol_reference(symbols: list[str]) -> pd.DataFrame:
    rows = []
    for symbol in sorted(symbols):
        rows.append(
            {
                "symbol": symbol,
                "asset_type": (
                    AssetType.ETF.value if symbol in ETF_SYMBOLS else AssetType.COMMON_STOCK.value
                ),
                "exchange": "UNKNOWN",
                "currency": "USD",
                "sector": "UNKNOWN",
                "is_tradable": True,
            }
        )
    return pd.DataFrame(rows, columns=SYMBOL_REFERENCE_COLUMNS)


def _ensure_contract_valid(name: str, validator: Any, frame: pd.DataFrame) -> None:
    result = validator(frame)
    errors = getattr(result, "errors", None)
    if errors:
        raise ValueError(f"{name} contract validation failed: {errors}")
    for attribute in ("passed", "is_valid", "valid"):
        if hasattr(result, attribute) and not getattr(result, attribute):
            raise ValueError(f"{name} contract validation failed: {result}")
