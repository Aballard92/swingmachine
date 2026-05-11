from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import yaml

from swingmachine.contracts import (
    HistoricalFeatureCoverageScope,
    HistoricalPanelFiles,
    HistoricalPanelFileSpec,
    HistoricalPanelFileSummary,
    HistoricalPanelManifest,
    HistoricalPanelValidationIssue,
    HistoricalPanelValidationResult,
)
from swingmachine.enums import AssetType, EarningsEventSession, ReviewStatus

REQUIRED_NEXT_SESSION_MARKET_COLUMNS = (
    "symbol",
    "session_date",
    "raw_open",
    "raw_high",
    "raw_low",
    "raw_close",
    "raw_volume",
)
REQUIRED_SYMBOL_REFERENCE_COLUMNS = (
    "symbol",
    "asset_type",
    "exchange",
    "currency",
    "sector",
    "is_tradable",
)
OPTIONAL_SYMBOL_REFERENCE_TRADABILITY_WINDOW_COLUMNS = (
    "tradable_start_session",
    "tradable_end_session",
)
OPTIONAL_SYMBOL_REFERENCE_EFFECTIVE_WINDOW_COLUMNS = (
    "effective_start_session",
    "effective_end_session",
)
REQUIRED_CORPORATE_ACTION_COLUMNS = (
    "symbol",
    "ex_date",
    "split_ratio",
    "cash_dividend_per_share",
)
REQUIRED_EARNINGS_EVENT_COLUMNS = (
    "symbol",
    "event_date",
    "event_session",
)
REQUIRED_HISTORICAL_OHLCV_COLUMNS = (
    "symbol",
    "session_date",
    "raw_open",
    "raw_high",
    "raw_low",
    "raw_close",
    "raw_volume",
)
REQUIRED_HISTORICAL_FEATURE_COLUMNS = (
    "symbol",
    "session_date",
    "raw_open",
    "raw_high",
    "raw_low",
    "raw_close",
    "raw_volume",
    "split_adj_close",
    "split_adj_high",
    "split_adj_low",
    "ma50",
    "ma200",
    "ma200_slope_pct20",
    "dist_to_52w_high",
    "mom_252_21",
    "ret_126",
    "rs_vs_benchmark_126",
    "trend_quality",
    "atr_14",
    "range_compression_ratio",
    "pullback_days",
    "pullback_depth_atr",
    "anchor_high_date",
    "volume_ratio_20",
    "regular_closes_until_earnings_event",
    "history_days",
    "avg_daily_dollar_volume_20",
    "asset_type",
    "sector",
    "exchange",
    "is_tradable",
)

_POSITIVE_PRICE_COLUMNS = ("raw_open", "raw_high", "raw_low", "raw_close")
_NON_NEGATIVE_OPTIONAL_COLUMNS = ("raw_volume", "spread_bps", "fx_conversion_cost_bps")
_HISTORICAL_FEATURE_POSITIVE_COLUMNS = (
    "raw_open",
    "raw_high",
    "raw_low",
    "raw_close",
    "split_adj_close",
    "split_adj_high",
    "split_adj_low",
    "ma50",
    "ma200",
    "atr_14",
)
_HISTORICAL_FEATURE_NON_NEGATIVE_COLUMNS = (
    "raw_volume",
    "range_compression_ratio",
    "pullback_days",
    "pullback_depth_atr",
    "volume_ratio_20",
    "regular_closes_until_earnings_event",
    "history_days",
    "avg_daily_dollar_volume_20",
)
_ASSET_TYPE_VALUES = {asset_type.value for asset_type in AssetType}
_EARNINGS_EVENT_SESSION_VALUES = {session.value for session in EarningsEventSession}
_US_EQUITY_MARKET_HOLIDAYS = {
    date.fromisoformat(value)
    for value in (
        "2022-01-17",
        "2022-02-21",
        "2022-04-15",
        "2022-05-30",
        "2022-06-20",
        "2022-07-04",
        "2022-09-05",
        "2022-11-24",
        "2022-12-26",
        "2023-01-02",
        "2023-01-16",
        "2023-02-20",
        "2023-04-07",
        "2023-05-29",
        "2023-06-19",
        "2023-07-04",
        "2023-09-04",
        "2023-11-23",
        "2023-12-25",
        "2024-01-01",
        "2024-01-15",
        "2024-02-19",
        "2024-03-29",
        "2024-05-27",
        "2024-06-19",
        "2024-07-04",
        "2024-09-02",
        "2024-11-28",
        "2024-12-25",
        "2025-01-01",
        "2025-01-09",
        "2025-01-20",
        "2025-02-17",
        "2025-04-18",
        "2025-05-26",
        "2025-06-19",
        "2025-07-04",
        "2025-09-01",
        "2025-11-27",
        "2025-12-25",
        "2026-01-01",
        "2026-01-19",
        "2026-02-16",
        "2026-04-03",
        "2026-05-25",
        "2026-06-19",
        "2026-07-03",
        "2026-09-07",
        "2026-11-26",
        "2026-12-25",
    )
}
_REQUIRED_PANEL_FILE_KEYS = (
    "ohlcv",
    "symbol_reference",
    "corporate_actions",
    "earnings_events",
)
_OPTIONAL_PANEL_FILE_KEYS = ("features",)
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


class PreparedDataValidationError(ValueError):
    """Raised when prepared operator inputs violate the runtime data contract."""


@dataclass(frozen=True, slots=True)
class HistoricalPanelData:
    manifest: HistoricalPanelManifest
    ohlcv: pd.DataFrame
    symbol_reference: pd.DataFrame
    corporate_actions: pd.DataFrame
    earnings_events: pd.DataFrame
    features: pd.DataFrame | None = None


def require_columns(
    frame: pd.DataFrame,
    required_columns: Iterable[str],
    *,
    frame_name: str = "data frame",
) -> None:
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        missing_str = ", ".join(missing)
        raise PreparedDataValidationError(
            f"{frame_name} is missing required columns: {missing_str}"
        )


def _normalize_symbol_column(prepared: pd.DataFrame, *, frame_name: str) -> None:
    prepared["symbol"] = prepared["symbol"].astype(str).str.strip()
    empty_symbols = prepared["symbol"] == ""
    if empty_symbols.any():
        raise PreparedDataValidationError(f"{frame_name} contains blank symbols")


def _reject_duplicate_keys(
    prepared: pd.DataFrame,
    key_columns: tuple[str, ...],
    *,
    frame_name: str,
) -> None:
    duplicate_keys = prepared.duplicated(subset=list(key_columns), keep=False)
    if not duplicate_keys.any():
        return

    duplicate_values = sorted(
        {
            "|".join(str(value) for value in row)
            for row in prepared.loc[duplicate_keys, list(key_columns)].itertuples(
                index=False,
                name=None,
            )
        }
    )
    duplicates_str = ", ".join(duplicate_values)
    raise PreparedDataValidationError(
        f"{frame_name} contains duplicate rows for {', '.join(key_columns)}: {duplicates_str}"
    )


def _coerce_boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "t", "yes", "y", "1"}:
            return True
        if normalized in {"false", "f", "no", "n", "0"}:
            return False
    raise PreparedDataValidationError("is_tradable must be a boolean value")


def validate_next_session_market_data(market_data: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize one next-session market row per symbol.

    This is the prepared data contract used by the paper/shadow audit workflow. It does
    not fetch or infer data; callers must provide already point-in-time-safe raw OHLCV.
    """

    require_columns(
        market_data,
        REQUIRED_NEXT_SESSION_MARKET_COLUMNS,
        frame_name="next-session market data",
    )
    prepared = market_data.copy()
    _normalize_symbol_column(prepared, frame_name="next-session market data")
    prepared["session_date"] = pd.to_datetime(prepared["session_date"], errors="raise")

    for column in _POSITIVE_PRICE_COLUMNS:
        prepared[column] = pd.to_numeric(prepared[column], errors="raise")
        invalid = prepared[column].isna() | (prepared[column] <= 0)
        if invalid.any():
            raise PreparedDataValidationError(f"{column} must be present and positive")

    for column in _NON_NEGATIVE_OPTIONAL_COLUMNS:
        if column not in prepared.columns:
            continue
        prepared[column] = pd.to_numeric(prepared[column], errors="raise")
        invalid = prepared[column].isna() | (prepared[column] < 0)
        if invalid.any():
            raise PreparedDataValidationError(f"{column} must be present and non-negative")

    high_too_low = prepared["raw_high"] < prepared[["raw_open", "raw_close", "raw_low"]].max(axis=1)
    low_too_high = prepared["raw_low"] > prepared[["raw_open", "raw_close", "raw_high"]].min(axis=1)
    if high_too_low.any():
        raise PreparedDataValidationError("raw_high must be at least open, low, and close")
    if low_too_high.any():
        raise PreparedDataValidationError("raw_low must be no greater than open, high, and close")

    _reject_duplicate_keys(
        prepared,
        ("symbol",),
        frame_name="next-session market data",
    )

    return prepared.sort_values(["session_date", "symbol"]).reset_index(drop=True)


def validate_historical_ohlcv_data(
    ohlcv: pd.DataFrame,
    *,
    start_session: date | None = None,
    end_session: date | None = None,
) -> pd.DataFrame:
    """Validate prepared historical raw OHLCV rows.

    This validates the replay panel input boundary. It does not canonicalize
    split-adjusted or total-return series, and it does not infer missing rows.
    """

    require_columns(
        ohlcv,
        REQUIRED_HISTORICAL_OHLCV_COLUMNS,
        frame_name="historical OHLCV data",
    )
    prepared = ohlcv.copy()
    _normalize_symbol_column(prepared, frame_name="historical OHLCV data")
    prepared["session_date"] = pd.to_datetime(prepared["session_date"], errors="raise")

    for column in _POSITIVE_PRICE_COLUMNS:
        prepared[column] = pd.to_numeric(prepared[column], errors="raise")
        invalid = prepared[column].isna() | (prepared[column] <= 0)
        if invalid.any():
            raise PreparedDataValidationError(f"{column} must be present and positive")

    prepared["raw_volume"] = pd.to_numeric(prepared["raw_volume"], errors="raise")
    invalid_volume = prepared["raw_volume"].isna() | (prepared["raw_volume"] < 0)
    if invalid_volume.any():
        raise PreparedDataValidationError("raw_volume must be present and non-negative")

    high_too_low = prepared["raw_high"] < prepared[["raw_open", "raw_close", "raw_low"]].max(axis=1)
    low_too_high = prepared["raw_low"] > prepared[["raw_open", "raw_close", "raw_high"]].min(axis=1)
    if high_too_low.any():
        raise PreparedDataValidationError("raw_high must be at least open, low, and close")
    if low_too_high.any():
        raise PreparedDataValidationError("raw_low must be no greater than open, high, and close")

    _reject_duplicate_keys(
        prepared,
        ("symbol", "session_date"),
        frame_name="historical OHLCV data",
    )

    if start_session is not None:
        before_start = prepared["session_date"].dt.date < start_session
        if before_start.any():
            raise PreparedDataValidationError(
                "historical OHLCV data contains rows before start_session"
            )
    if end_session is not None:
        after_end = prepared["session_date"].dt.date > end_session
        if after_end.any():
            raise PreparedDataValidationError(
                "historical OHLCV data contains rows after end_session"
            )

    return prepared.sort_values(["session_date", "symbol"]).reset_index(drop=True)


def validate_historical_feature_data(
    features: pd.DataFrame,
    *,
    start_session: date | None = None,
    end_session: date | None = None,
) -> pd.DataFrame:
    """Validate prepared replay feature rows supplied by a historical panel manifest."""

    require_columns(
        features,
        REQUIRED_HISTORICAL_FEATURE_COLUMNS,
        frame_name="historical feature data",
    )
    prepared = features.copy()
    _normalize_symbol_column(prepared, frame_name="historical feature data")
    prepared["session_date"] = pd.to_datetime(prepared["session_date"], errors="raise")
    prepared["anchor_high_date"] = pd.to_datetime(prepared["anchor_high_date"], errors="raise")

    for column in _HISTORICAL_FEATURE_POSITIVE_COLUMNS:
        prepared[column] = pd.to_numeric(prepared[column], errors="raise")
        invalid = prepared[column].isna() | (prepared[column] <= 0)
        if invalid.any():
            raise PreparedDataValidationError(f"{column} must be present and positive")

    for column in _HISTORICAL_FEATURE_NON_NEGATIVE_COLUMNS:
        prepared[column] = pd.to_numeric(prepared[column], errors="raise")
        invalid = prepared[column].isna() | (prepared[column] < 0)
        if invalid.any():
            raise PreparedDataValidationError(f"{column} must be present and non-negative")

    for column in ("ma200_slope_pct20", "mom_252_21", "ret_126", "rs_vs_benchmark_126"):
        prepared[column] = pd.to_numeric(prepared[column], errors="raise")
        if prepared[column].isna().any():
            raise PreparedDataValidationError(f"{column} must be present")

    for column in ("dist_to_52w_high", "trend_quality"):
        prepared[column] = pd.to_numeric(prepared[column], errors="raise")
        invalid = prepared[column].isna() | (prepared[column] < 0) | (prepared[column] > 1)
        if invalid.any():
            raise PreparedDataValidationError(f"{column} must be between 0 and 1")

    high_too_low = prepared["raw_high"] < prepared[["raw_open", "raw_close", "raw_low"]].max(axis=1)
    low_too_high = prepared["raw_low"] > prepared[["raw_open", "raw_close", "raw_high"]].min(axis=1)
    if high_too_low.any():
        raise PreparedDataValidationError("raw_high must be at least open, low, and close")
    if low_too_high.any():
        raise PreparedDataValidationError("raw_low must be no greater than open, high, and close")

    split_high_too_low = prepared["split_adj_high"] < prepared[
        ["split_adj_close", "split_adj_low"]
    ].max(axis=1)
    split_low_too_high = prepared["split_adj_low"] > prepared[
        ["split_adj_close", "split_adj_high"]
    ].min(axis=1)
    if split_high_too_low.any():
        raise PreparedDataValidationError("split_adj_high must be at least low and close")
    if split_low_too_high.any():
        raise PreparedDataValidationError("split_adj_low must be no greater than high and close")

    for column in ("asset_type", "sector", "exchange"):
        prepared[column] = prepared[column].astype(str).str.strip()
        if (prepared[column] == "").any():
            raise PreparedDataValidationError(f"{column} must be present")

    invalid_asset_types = ~prepared["asset_type"].isin(_ASSET_TYPE_VALUES)
    if invalid_asset_types.any():
        valid = ", ".join(sorted(_ASSET_TYPE_VALUES))
        raise PreparedDataValidationError(f"asset_type must be one of: {valid}")

    prepared["is_tradable"] = prepared["is_tradable"].map(_coerce_boolish)

    _reject_duplicate_keys(
        prepared,
        ("symbol", "session_date"),
        frame_name="historical feature data",
    )

    if start_session is not None:
        before_start = prepared["session_date"].dt.date < start_session
        if before_start.any():
            raise PreparedDataValidationError(
                "historical feature data contains rows before start_session"
            )
    if end_session is not None:
        after_end = prepared["session_date"].dt.date > end_session
        if after_end.any():
            raise PreparedDataValidationError(
                "historical feature data contains rows after end_session"
            )

    return prepared.sort_values(["session_date", "symbol"]).reset_index(drop=True)


def validate_symbol_reference_data(symbols: pd.DataFrame) -> pd.DataFrame:
    """Validate point-in-time symbol reference rows for universe construction."""

    require_columns(
        symbols,
        REQUIRED_SYMBOL_REFERENCE_COLUMNS,
        frame_name="symbol reference data",
    )
    prepared = symbols.copy()
    _normalize_symbol_column(prepared, frame_name="symbol reference data")

    for column in ("asset_type", "exchange", "currency", "sector"):
        prepared[column] = prepared[column].astype(str).str.strip()
        if (prepared[column] == "").any():
            raise PreparedDataValidationError(f"{column} must be present")

    invalid_asset_types = ~prepared["asset_type"].isin(_ASSET_TYPE_VALUES)
    if invalid_asset_types.any():
        valid = ", ".join(sorted(_ASSET_TYPE_VALUES))
        raise PreparedDataValidationError(f"asset_type must be one of: {valid}")

    prepared["currency"] = prepared["currency"].str.upper()
    invalid_currency = ~prepared["currency"].str.fullmatch(r"[A-Z]{3}")
    if invalid_currency.any():
        raise PreparedDataValidationError("currency must be an ISO-style three-letter code")

    prepared["is_tradable"] = prepared["is_tradable"].map(_coerce_boolish)
    for column in (
        *OPTIONAL_SYMBOL_REFERENCE_EFFECTIVE_WINDOW_COLUMNS,
        *OPTIONAL_SYMBOL_REFERENCE_TRADABILITY_WINDOW_COLUMNS,
    ):
        if column not in prepared.columns:
            prepared[column] = pd.NaT
        prepared[column] = pd.to_datetime(prepared[column], errors="raise")

    effective_start = prepared["effective_start_session"]
    effective_end = prepared["effective_end_session"]
    invalid_effective_window = (
        effective_start.notna() & effective_end.notna() & (effective_start > effective_end)
    )
    if invalid_effective_window.any():
        raise PreparedDataValidationError(
            "effective_start_session must be no later than effective_end_session"
        )

    start = prepared["tradable_start_session"]
    end = prepared["tradable_end_session"]
    invalid_window = start.notna() & end.notna() & (start > end)
    if invalid_window.any():
        raise PreparedDataValidationError(
            "tradable_start_session must be no later than tradable_end_session"
        )

    _validate_symbol_reference_history(prepared)
    return prepared.sort_values(
        ["symbol", "effective_start_session"],
        na_position="first",
    ).reset_index(drop=True)


def _validate_symbol_reference_history(prepared: pd.DataFrame) -> None:
    for symbol, group in prepared.groupby("symbol", sort=True):
        if len(group) == 1:
            continue

        missing_start = group["effective_start_session"].isna()
        if missing_start.any():
            raise PreparedDataValidationError(
                f"duplicate symbol reference rows must declare effective_start_session: {symbol}"
            )

        sorted_group = group.sort_values("effective_start_session")
        previous_end: pd.Timestamp | None = None
        for row in sorted_group.itertuples(index=False):
            current_start = pd.Timestamp(row.effective_start_session)
            if previous_end is not None and current_start <= previous_end:
                raise PreparedDataValidationError(
                    f"symbol reference data contains overlapping effective windows: {symbol}"
                )
            current_end_value = row.effective_end_session
            previous_end = (
                pd.Timestamp.max if pd.isna(current_end_value) else pd.Timestamp(current_end_value)
            )


def validate_corporate_actions_data(corporate_actions: pd.DataFrame) -> pd.DataFrame:
    """Validate prepared split/dividend adjustments used by canonical price building."""

    require_columns(
        corporate_actions,
        REQUIRED_CORPORATE_ACTION_COLUMNS,
        frame_name="corporate actions data",
    )
    prepared = corporate_actions.copy()
    _normalize_symbol_column(prepared, frame_name="corporate actions data")
    prepared["ex_date"] = pd.to_datetime(prepared["ex_date"], errors="raise")

    prepared["split_ratio"] = pd.to_numeric(prepared["split_ratio"], errors="raise")
    invalid_split = prepared["split_ratio"].isna() | (prepared["split_ratio"] <= 0)
    if invalid_split.any():
        raise PreparedDataValidationError("split_ratio must be present and positive")

    prepared["cash_dividend_per_share"] = pd.to_numeric(
        prepared["cash_dividend_per_share"],
        errors="raise",
    )
    invalid_dividend = prepared["cash_dividend_per_share"].isna() | (
        prepared["cash_dividend_per_share"] < 0
    )
    if invalid_dividend.any():
        raise PreparedDataValidationError(
            "cash_dividend_per_share must be present and non-negative"
        )

    _reject_duplicate_keys(
        prepared,
        ("symbol", "ex_date"),
        frame_name="corporate actions data",
    )
    return prepared.sort_values(["ex_date", "symbol"]).reset_index(drop=True)


def validate_earnings_events_data(earnings_events: pd.DataFrame) -> pd.DataFrame:
    """Validate prepared earnings calendar rows used by entry/exit guardrails."""

    require_columns(
        earnings_events,
        REQUIRED_EARNINGS_EVENT_COLUMNS,
        frame_name="earnings events data",
    )
    prepared = earnings_events.copy()
    _normalize_symbol_column(prepared, frame_name="earnings events data")
    prepared["event_date"] = pd.to_datetime(prepared["event_date"], errors="raise")
    prepared["event_session"] = prepared["event_session"].astype(str).str.strip()

    invalid_sessions = ~prepared["event_session"].isin(_EARNINGS_EVENT_SESSION_VALUES)
    if invalid_sessions.any():
        valid = ", ".join(sorted(_EARNINGS_EVENT_SESSION_VALUES))
        raise PreparedDataValidationError(f"event_session must be one of: {valid}")

    _reject_duplicate_keys(
        prepared,
        ("symbol", "event_date"),
        frame_name="earnings events data",
    )
    return prepared.sort_values(["event_date", "symbol"]).reset_index(drop=True)


def load_historical_panel_manifest(path: str | Path) -> HistoricalPanelManifest:
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as handle:
        if manifest_path.suffix.lower() == ".json":
            payload = json.load(handle)
        else:
            payload = yaml.safe_load(handle)
    return HistoricalPanelManifest.model_validate(payload)


def write_historical_panel_manifest_from_files(
    output_path: str | Path,
    *,
    panel_id: str,
    ohlcv_path: str | Path,
    symbol_reference_path: str | Path,
    corporate_actions_path: str | Path,
    earnings_events_path: str | Path,
    features_path: str | Path | None = None,
    base_path: str | Path | None = None,
    calendar: str = "WEEKDAY",
    timezone: str = "Europe/London",
    description: str | None = None,
    schema_version: str = "1.0",
    created_at: datetime | None = None,
    feature_start_session: date | None = None,
    replay_start_session: date | None = None,
    replay_end_session: date | None = None,
    feature_coverage_scope: HistoricalFeatureCoverageScope = "tradable_reference",
) -> Path:
    manifest = build_historical_panel_manifest_from_files(
        panel_id=panel_id,
        ohlcv_path=ohlcv_path,
        symbol_reference_path=symbol_reference_path,
        corporate_actions_path=corporate_actions_path,
        earnings_events_path=earnings_events_path,
        features_path=features_path,
        base_path=base_path,
        calendar=calendar,
        timezone=timezone,
        description=description,
        schema_version=schema_version,
        created_at=created_at,
        feature_start_session=feature_start_session,
        replay_start_session=replay_start_session,
        replay_end_session=replay_end_session,
        feature_coverage_scope=feature_coverage_scope,
    )
    manifest_path = Path(output_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        yaml.safe_dump(manifest.model_dump(mode="json", exclude_none=True), sort_keys=False),
        encoding="utf-8",
    )
    return manifest_path


def build_historical_panel_manifest_from_files(
    *,
    panel_id: str,
    ohlcv_path: str | Path,
    symbol_reference_path: str | Path,
    corporate_actions_path: str | Path,
    earnings_events_path: str | Path,
    features_path: str | Path | None = None,
    base_path: str | Path | None = None,
    calendar: str = "WEEKDAY",
    timezone: str = "Europe/London",
    description: str | None = None,
    schema_version: str = "1.0",
    created_at: datetime | None = None,
    feature_start_session: date | None = None,
    replay_start_session: date | None = None,
    replay_end_session: date | None = None,
    feature_coverage_scope: HistoricalFeatureCoverageScope = "tradable_reference",
) -> HistoricalPanelManifest:
    file_paths = {
        "ohlcv": Path(ohlcv_path).resolve(),
        "symbol_reference": Path(symbol_reference_path).resolve(),
        "corporate_actions": Path(corporate_actions_path).resolve(),
        "earnings_events": Path(earnings_events_path).resolve(),
    }
    if features_path is not None:
        file_paths["features"] = Path(features_path).resolve()
    resolved_base_path = _manifest_builder_base_path(
        tuple(file_paths.values()),
        None if base_path is None else Path(base_path),
    )
    frames = {
        file_key: _read_panel_frame(path, _infer_panel_file_format(path))
        for file_key, path in file_paths.items()
    }
    ohlcv = frames["ohlcv"].copy()
    require_columns(ohlcv, REQUIRED_HISTORICAL_OHLCV_COLUMNS, frame_name="historical OHLCV data")
    ohlcv["session_date"] = pd.to_datetime(ohlcv["session_date"], errors="raise")
    session_dates = ohlcv["session_date"].dt.date
    files = HistoricalPanelFiles(
        ohlcv=_manifest_file_spec(file_paths["ohlcv"], resolved_base_path, frames["ohlcv"]),
        symbol_reference=_manifest_file_spec(
            file_paths["symbol_reference"],
            resolved_base_path,
            frames["symbol_reference"],
        ),
        corporate_actions=_manifest_file_spec(
            file_paths["corporate_actions"],
            resolved_base_path,
            frames["corporate_actions"],
        ),
        earnings_events=_manifest_file_spec(
            file_paths["earnings_events"],
            resolved_base_path,
            frames["earnings_events"],
        ),
        features=None
        if features_path is None
        else _manifest_file_spec(file_paths["features"], resolved_base_path, frames["features"]),
    )
    inferred_feature_start_session = feature_start_session
    if inferred_feature_start_session is None and features_path is not None:
        features = frames["features"].copy()
        require_columns(
            features,
            ("session_date",),
            frame_name="historical feature data",
        )
        inferred_feature_start_session = pd.to_datetime(
            features["session_date"],
            errors="raise",
        ).dt.date.min()
    return HistoricalPanelManifest(
        panel_id=panel_id,
        schema_version=schema_version,
        created_at=created_at or datetime.utcnow(),
        description=description,
        base_path=None if resolved_base_path is None else str(resolved_base_path),
        calendar=calendar,
        timezone=timezone,
        start_session=session_dates.min(),
        end_session=session_dates.max(),
        feature_start_session=inferred_feature_start_session,
        replay_start_session=replay_start_session,
        replay_end_session=replay_end_session,
        feature_coverage_scope=feature_coverage_scope,
        expected_symbol_count=int(ohlcv["symbol"].astype(str).nunique()),
        expected_session_count=int(session_dates.nunique()),
        files=files,
    )


def validate_historical_panel_manifest(path: str | Path) -> HistoricalPanelValidationResult:
    """Validate a complete prepared historical panel from its manifest.

    The result is intentionally about machinery readiness: file presence, schema
    shape, cross-file consistency, and replay preconditions. It does not evaluate
    strategy performance.
    """

    manifest_path = Path(path)
    validated_at = datetime.utcnow()
    errors: list[HistoricalPanelValidationIssue] = []
    warnings: list[HistoricalPanelValidationIssue] = []
    summaries: list[HistoricalPanelFileSummary] = []
    frames: dict[str, pd.DataFrame] = {}

    try:
        manifest = load_historical_panel_manifest(manifest_path)
    except Exception as exc:
        return HistoricalPanelValidationResult(
            panel_id="UNKNOWN",
            manifest_path=str(manifest_path),
            status=ReviewStatus.FAIL,
            errors=(
                HistoricalPanelValidationIssue(
                    code="MANIFEST_LOAD_FAILED",
                    message=f"Failed to load historical panel manifest: {exc}",
                    path=str(manifest_path),
                ),
            ),
            symbol_count=0,
            session_count=0,
            validated_at=validated_at,
        )

    base_path = _resolve_panel_base_path(manifest_path, manifest.base_path)

    for file_key, spec in _iter_manifest_file_specs(manifest):
        file_path = _resolve_panel_file_path(base_path, spec)
        frame = _load_and_validate_panel_file(
            file_key=file_key,
            spec=spec,
            file_path=file_path,
            manifest=manifest,
            errors=errors,
        )
        if frame is None:
            continue
        frames[file_key] = frame
        summaries.append(_summarize_panel_file(file_key, file_path, frame))
        if spec.row_count is not None and len(frame) != spec.row_count:
            errors.append(
                HistoricalPanelValidationIssue(
                    code="ROW_COUNT_MISMATCH",
                    message=(
                        f"{file_key} row count mismatch: expected {spec.row_count}, "
                        f"observed {len(frame)}"
                    ),
                    file_key=file_key,
                    path=str(file_path),
                )
            )

    _validate_cross_file_panel_consistency(
        manifest=manifest,
        frames=frames,
        errors=errors,
        warnings=warnings,
    )

    ohlcv = frames.get("ohlcv")
    symbol_count = 0
    session_count = 0
    start_session = None
    end_session = None
    if ohlcv is not None:
        symbol_count = int(ohlcv["symbol"].nunique())
        sessions = _unique_session_dates(ohlcv, "session_date")
        session_count = len(sessions)
        if sessions:
            start_session = sessions[0]
            end_session = sessions[-1]

    status = ReviewStatus.FAIL if errors else ReviewStatus.WARN if warnings else ReviewStatus.PASS
    return HistoricalPanelValidationResult(
        panel_id=manifest.panel_id,
        manifest_path=str(manifest_path),
        status=status,
        errors=tuple(errors),
        warnings=tuple(warnings),
        file_summaries=tuple(summaries),
        symbol_count=symbol_count,
        session_count=session_count,
        start_session=start_session,
        end_session=end_session,
        validated_at=validated_at,
    )


def load_historical_panel_data(path: str | Path) -> HistoricalPanelData:
    """Load a prepared historical panel after enforcing manifest validation."""

    manifest_path = Path(path)
    validation = validate_historical_panel_manifest(manifest_path)
    if validation.status is ReviewStatus.FAIL:
        messages = "; ".join(issue.message for issue in validation.errors)
        raise PreparedDataValidationError(
            f"historical panel validation failed for {manifest_path}: {messages}"
        )

    manifest = load_historical_panel_manifest(manifest_path)
    base_path = _resolve_panel_base_path(manifest_path, manifest.base_path)
    errors: list[HistoricalPanelValidationIssue] = []
    frames: dict[str, pd.DataFrame] = {}

    for file_key, spec in _iter_manifest_file_specs(manifest):
        frame = _load_and_validate_panel_file(
            file_key=file_key,
            spec=spec,
            file_path=_resolve_panel_file_path(base_path, spec),
            manifest=manifest,
            errors=errors,
        )
        if frame is not None:
            frames[file_key] = frame

    if errors:
        messages = "; ".join(issue.message for issue in errors)
        raise PreparedDataValidationError(
            f"historical panel load failed for {manifest_path}: {messages}"
        )

    return HistoricalPanelData(
        manifest=manifest,
        ohlcv=frames["ohlcv"],
        symbol_reference=frames["symbol_reference"],
        corporate_actions=frames["corporate_actions"],
        earnings_events=frames["earnings_events"],
        features=frames.get("features"),
    )


def _iter_manifest_file_specs(
    manifest: HistoricalPanelManifest,
) -> Iterable[tuple[str, HistoricalPanelFileSpec]]:
    for file_key in _REQUIRED_PANEL_FILE_KEYS:
        yield file_key, getattr(manifest.files, file_key)
    for file_key in _OPTIONAL_PANEL_FILE_KEYS:
        spec = getattr(manifest.files, file_key)
        if spec is not None:
            yield file_key, spec


def _resolve_panel_base_path(manifest_path: Path, base_path: str | None) -> Path:
    if base_path is None:
        return manifest_path.parent
    resolved = Path(base_path)
    if resolved.is_absolute():
        return resolved
    return manifest_path.parent / resolved


def _resolve_panel_file_path(base_path: Path, spec: HistoricalPanelFileSpec) -> Path:
    file_path = Path(spec.path)
    if file_path.is_absolute():
        return file_path
    return base_path / file_path


def _load_and_validate_panel_file(
    *,
    file_key: str,
    spec: HistoricalPanelFileSpec,
    file_path: Path,
    manifest: HistoricalPanelManifest,
    errors: list[HistoricalPanelValidationIssue],
) -> pd.DataFrame | None:
    if not file_path.exists():
        errors.append(
            HistoricalPanelValidationIssue(
                code="FILE_MISSING",
                message=f"{file_key} file does not exist: {file_path}",
                file_key=file_key,
                path=str(file_path),
            )
        )
        return None

    if not _validate_panel_file_checksum(
        file_key=file_key,
        spec=spec,
        file_path=file_path,
        errors=errors,
    ):
        return None

    try:
        frame = _read_panel_frame(file_path, spec.format)
    except Exception as exc:
        errors.append(
            HistoricalPanelValidationIssue(
                code="FILE_READ_FAILED",
                message=f"Failed to read {file_key} file: {exc}",
                file_key=file_key,
                path=str(file_path),
            )
        )
        return None

    try:
        if file_key == "ohlcv":
            return validate_historical_ohlcv_data(
                frame,
                start_session=manifest.start_session,
                end_session=manifest.end_session,
            )
        if file_key == "symbol_reference":
            return validate_symbol_reference_data(frame)
        if file_key == "corporate_actions":
            return validate_corporate_actions_data(frame)
        if file_key == "earnings_events":
            return validate_earnings_events_data(frame)
        if file_key == "features":
            return validate_historical_feature_data(
                frame,
                start_session=manifest.start_session,
                end_session=manifest.end_session,
            )
    except PreparedDataValidationError as exc:
        errors.append(
            HistoricalPanelValidationIssue(
                code="FILE_VALIDATION_FAILED",
                message=f"{file_key} validation failed: {exc}",
                file_key=file_key,
                path=str(file_path),
            )
        )
        return None

    errors.append(
        HistoricalPanelValidationIssue(
            code="UNKNOWN_FILE_KEY",
            message=f"Unknown historical panel file key: {file_key}",
            file_key=file_key,
            path=str(file_path),
        )
    )
    return None


def _validate_panel_file_checksum(
    *,
    file_key: str,
    spec: HistoricalPanelFileSpec,
    file_path: Path,
    errors: list[HistoricalPanelValidationIssue],
) -> bool:
    if spec.sha256 is None:
        return True

    expected = spec.sha256.strip().lower()
    if _SHA256_HEX_RE.fullmatch(expected) is None:
        errors.append(
            HistoricalPanelValidationIssue(
                code="SHA256_INVALID",
                message=f"{file_key} sha256 must be a 64-character hex digest",
                file_key=file_key,
                path=str(file_path),
                field="sha256",
            )
        )
        return False

    observed = _sha256_file(file_path)
    if observed == expected:
        return True

    errors.append(
        HistoricalPanelValidationIssue(
            code="SHA256_MISMATCH",
            message=(f"{file_key} sha256 mismatch: expected {expected}, observed {observed}"),
            file_key=file_key,
            path=str(file_path),
            field="sha256",
        )
    )
    return False


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_builder_base_path(
    file_paths: tuple[Path, ...],
    explicit_base_path: Path | None,
) -> Path | None:
    if explicit_base_path is not None:
        return explicit_base_path.resolve()
    parents = {path.parent for path in file_paths}
    if len(parents) == 1:
        return next(iter(parents))
    return None


def _manifest_file_spec(
    file_path: Path,
    base_path: Path | None,
    frame: pd.DataFrame,
) -> HistoricalPanelFileSpec:
    return HistoricalPanelFileSpec(
        path=_manifest_file_path(file_path, base_path),
        format=_infer_panel_file_format(file_path),
        row_count=len(frame),
        sha256=_sha256_file(file_path),
    )


def _manifest_file_path(file_path: Path, base_path: Path | None) -> str:
    if base_path is None:
        return str(file_path)
    try:
        return os.path.relpath(file_path, base_path)
    except ValueError:
        return str(file_path)


def _infer_panel_file_format(path: Path) -> str:
    if path.suffix.lower() == ".parquet":
        return "parquet"
    return "csv"


def _read_panel_frame(path: Path, file_format: str) -> pd.DataFrame:
    normalized = file_format.lower().strip()
    if normalized == "csv":
        return pd.read_csv(path)
    if normalized == "parquet":
        return pd.read_parquet(path)
    raise PreparedDataValidationError(f"unsupported file format: {file_format}")


def _summarize_panel_file(
    file_key: str,
    path: Path,
    frame: pd.DataFrame,
) -> HistoricalPanelFileSummary:
    date_column = _date_column_for_file(file_key)
    sessions = _unique_session_dates(frame, date_column) if date_column in frame.columns else []
    symbol_count = int(frame["symbol"].nunique()) if "symbol" in frame.columns else 0
    return HistoricalPanelFileSummary(
        file_key=file_key,
        path=str(path),
        row_count=len(frame),
        symbol_count=symbol_count,
        start_session=sessions[0] if sessions else None,
        end_session=sessions[-1] if sessions else None,
    )


def _date_column_for_file(file_key: str) -> str:
    if file_key == "corporate_actions":
        return "ex_date"
    if file_key == "earnings_events":
        return "event_date"
    return "session_date"


def _unique_session_dates(frame: pd.DataFrame, date_column: str) -> list[date]:
    dates = pd.to_datetime(frame[date_column], errors="coerce").dropna().dt.date
    return sorted(set(dates))


def _validate_cross_file_panel_consistency(
    *,
    manifest: HistoricalPanelManifest,
    frames: dict[str, pd.DataFrame],
    errors: list[HistoricalPanelValidationIssue],
    warnings: list[HistoricalPanelValidationIssue],
) -> None:
    ohlcv = frames.get("ohlcv")
    reference = frames.get("symbol_reference")
    corporate_actions = frames.get("corporate_actions")
    earnings = frames.get("earnings_events")
    features = frames.get("features")

    if ohlcv is None:
        return

    ohlcv_symbols = set(str(symbol) for symbol in ohlcv["symbol"].unique())
    ohlcv_sessions = _unique_session_dates(ohlcv, "session_date")
    if not ohlcv_symbols:
        errors.append(
            HistoricalPanelValidationIssue(
                code="EMPTY_PANEL",
                message="Historical panel contains no OHLCV symbols",
                file_key="ohlcv",
            )
        )
    if not ohlcv_sessions:
        errors.append(
            HistoricalPanelValidationIssue(
                code="EMPTY_PANEL",
                message="Historical panel contains no OHLCV sessions",
                file_key="ohlcv",
            )
        )

    if (
        manifest.expected_symbol_count is not None
        and len(ohlcv_symbols) != manifest.expected_symbol_count
    ):
        errors.append(
            HistoricalPanelValidationIssue(
                code="EXPECTED_SYMBOL_COUNT_MISMATCH",
                message=(
                    "Manifest expected_symbol_count does not match observed OHLCV symbols: "
                    f"expected {manifest.expected_symbol_count}, observed {len(ohlcv_symbols)}"
                ),
                file_key="ohlcv",
            )
        )

    if (
        manifest.expected_session_count is not None
        and len(ohlcv_sessions) != manifest.expected_session_count
    ):
        errors.append(
            HistoricalPanelValidationIssue(
                code="EXPECTED_SESSION_COUNT_MISMATCH",
                message=(
                    "Manifest expected_session_count does not match observed OHLCV sessions: "
                    f"expected {manifest.expected_session_count}, observed {len(ohlcv_sessions)}"
                ),
                file_key="ohlcv",
            )
        )

    if manifest.feature_start_session is not None and not (
        manifest.start_session <= manifest.feature_start_session <= manifest.end_session
    ):
        errors.append(
            HistoricalPanelValidationIssue(
                code="FEATURE_START_SESSION_OUT_OF_RANGE",
                message=(
                    "feature_start_session must fall within the manifest start_session and "
                    "end_session"
                ),
                field="feature_start_session",
            )
        )

    if reference is not None:
        _validate_reference_consistency(
            ohlcv=ohlcv,
            ohlcv_symbols=ohlcv_symbols,
            reference=reference,
            errors=errors,
        )

    if reference is not None and corporate_actions is not None:
        _validate_known_symbols(
            file_key="corporate_actions",
            symbols=set(str(symbol) for symbol in corporate_actions["symbol"].unique()),
            reference_symbols=set(str(symbol) for symbol in reference["symbol"].unique()),
            code="CORPORATE_ACTION_UNKNOWN_SYMBOL",
            errors=errors,
        )

    if reference is not None and earnings is not None:
        _validate_known_symbols(
            file_key="earnings_events",
            symbols=set(str(symbol) for symbol in earnings["symbol"].unique()),
            reference_symbols=set(str(symbol) for symbol in reference["symbol"].unique()),
            code="EARNINGS_UNKNOWN_SYMBOL",
            errors=errors,
        )

    if features is not None:
        _validate_feature_consistency(
            manifest=manifest,
            features=features,
            ohlcv=ohlcv,
            reference=reference,
            errors=errors,
        )

    _warn_about_session_gaps(
        manifest=manifest,
        ohlcv=ohlcv,
        ohlcv_sessions=ohlcv_sessions,
        warnings=warnings,
    )


def _validate_reference_consistency(
    *,
    ohlcv: pd.DataFrame,
    ohlcv_symbols: set[str],
    reference: pd.DataFrame,
    errors: list[HistoricalPanelValidationIssue],
) -> None:
    reference_symbols = set(str(symbol) for symbol in reference["symbol"].unique())
    missing_reference = sorted(ohlcv_symbols - reference_symbols)
    for symbol in missing_reference:
        errors.append(
            HistoricalPanelValidationIssue(
                code="SYMBOL_REFERENCE_MISSING",
                message=f"OHLCV symbol is missing from symbol reference data: {symbol}",
                file_key="symbol_reference",
                symbol=symbol,
            )
        )

    if missing_reference:
        return

    ohlcv_keys = {
        (str(row.symbol), pd.Timestamp(row.session_date).date())
        for row in ohlcv[["symbol", "session_date"]].itertuples(index=False)
    }
    active_reference = symbol_reference_rows_for_sessions(
        symbol_sessions=ohlcv[["symbol", "session_date"]],
        reference=reference,
    )
    active_reference_keys = {
        (str(row.symbol), pd.Timestamp(row.session_date).date())
        for row in active_reference[["symbol", "session_date"]].itertuples(index=False)
    }
    missing_active_reference = sorted(ohlcv_keys - active_reference_keys)
    for symbol, session_date in missing_active_reference[:10]:
        errors.append(
            HistoricalPanelValidationIssue(
                code="SYMBOL_REFERENCE_SESSION_MISSING",
                message=(
                    "OHLCV symbol/session is missing an active symbol reference row: "
                    f"{symbol} {session_date.isoformat()}"
                ),
                file_key="symbol_reference",
                symbol=symbol,
                session_date=session_date,
            )
        )

    if len(missing_active_reference) > 10:
        errors.append(
            HistoricalPanelValidationIssue(
                code="SYMBOL_REFERENCE_SESSION_MISSING",
                message=(
                    "OHLCV symbol/session has additional rows missing active symbol "
                    f"reference coverage: {len(missing_active_reference) - 10}"
                ),
                file_key="symbol_reference",
            )
        )


def _validate_feature_consistency(
    *,
    manifest: HistoricalPanelManifest,
    features: pd.DataFrame,
    ohlcv: pd.DataFrame,
    reference: pd.DataFrame | None,
    errors: list[HistoricalPanelValidationIssue],
) -> None:
    reference_symbols = (
        set(str(symbol) for symbol in reference["symbol"].unique())
        if reference is not None
        else set(str(symbol) for symbol in ohlcv["symbol"].unique())
    )
    _validate_known_symbols(
        file_key="features",
        symbols=set(str(symbol) for symbol in features["symbol"].unique()),
        reference_symbols=reference_symbols,
        code="FEATURE_UNKNOWN_SYMBOL",
        errors=errors,
    )

    ohlcv_keys = {
        (str(row.symbol), pd.Timestamp(row.session_date).date())
        for row in ohlcv[["symbol", "session_date"]].itertuples(index=False)
    }
    feature_keys = {
        (str(row.symbol), pd.Timestamp(row.session_date).date())
        for row in features[["symbol", "session_date"]].itertuples(index=False)
    }
    missing_ohlcv_keys = sorted(feature_keys - ohlcv_keys)
    for symbol, session_date in missing_ohlcv_keys[:10]:
        errors.append(
            HistoricalPanelValidationIssue(
                code="FEATURE_SYMBOL_SESSION_MISSING_OHLCV",
                message=(
                    "features contains a symbol/session row missing from OHLCV data: "
                    f"{symbol} {session_date.isoformat()}"
                ),
                file_key="features",
                symbol=symbol,
                session_date=session_date,
            )
        )

    if len(missing_ohlcv_keys) > 10:
        errors.append(
            HistoricalPanelValidationIssue(
                code="FEATURE_SYMBOL_SESSION_MISSING_OHLCV",
                message=(
                    "features contains additional symbol/session rows missing from OHLCV data: "
                    f"{len(missing_ohlcv_keys) - 10}"
                ),
                file_key="features",
            )
        )

    if reference is not None:
        _validate_feature_reference_metadata_consistency(
            features=features,
            reference=reference,
            errors=errors,
        )

    _validate_required_feature_coverage(
        manifest=manifest,
        ohlcv=ohlcv,
        reference=reference,
        features=features,
        errors=errors,
    )


def _validate_feature_reference_metadata_consistency(
    *,
    features: pd.DataFrame,
    reference: pd.DataFrame,
    errors: list[HistoricalPanelValidationIssue],
) -> None:
    feature_metadata = features[
        ["symbol", "session_date", "asset_type", "sector", "exchange", "is_tradable"]
    ].copy()
    feature_metadata["symbol"] = feature_metadata["symbol"].astype(str)
    feature_metadata["session_date"] = pd.to_datetime(
        feature_metadata["session_date"],
        errors="raise",
    )
    for column in ("asset_type", "sector", "exchange"):
        feature_metadata[column] = feature_metadata[column].astype(str).str.strip()
    feature_metadata["is_tradable"] = feature_metadata["is_tradable"].map(_coerce_boolish)

    active_reference = symbol_reference_rows_for_sessions(
        symbol_sessions=feature_metadata[["symbol", "session_date"]],
        reference=reference,
    )
    active_reference_keys = {
        (str(row.symbol), pd.Timestamp(row.session_date).date())
        for row in active_reference[["symbol", "session_date"]].itertuples(index=False)
    }
    feature_keys = {
        (str(row.symbol), pd.Timestamp(row.session_date).date())
        for row in feature_metadata[["symbol", "session_date"]].itertuples(index=False)
    }
    missing_reference_keys = sorted(feature_keys - active_reference_keys)
    for symbol, session_date in missing_reference_keys[:10]:
        errors.append(
            HistoricalPanelValidationIssue(
                code="FEATURE_REFERENCE_SESSION_MISSING",
                message=(
                    "features contains a symbol/session row with no active symbol "
                    f"reference row: {symbol} {session_date.isoformat()}"
                ),
                file_key="features",
                symbol=symbol,
                session_date=session_date,
            )
        )

    if len(missing_reference_keys) > 10:
        errors.append(
            HistoricalPanelValidationIssue(
                code="FEATURE_REFERENCE_SESSION_MISSING",
                message=(
                    "features contains additional symbol/session rows with no active "
                    f"symbol reference row: {len(missing_reference_keys) - 10}"
                ),
                file_key="features",
            )
        )

    reference_metadata = active_reference[
        ["symbol", "session_date", "asset_type", "sector", "exchange", "is_tradable"]
    ].copy()
    for column in ("asset_type", "sector", "exchange"):
        reference_metadata[column] = reference_metadata[column].astype(str).str.strip()
    reference_metadata["is_tradable"] = reference_metadata["is_tradable"].map(_coerce_boolish)

    merged = feature_metadata.merge(
        reference_metadata,
        on=["symbol", "session_date"],
        how="inner",
        suffixes=("_feature", "_reference"),
    )
    remaining_issue_slots = 10
    mismatch_count = 0
    for field in ("asset_type", "sector", "exchange", "is_tradable"):
        mismatches = merged[merged[f"{field}_feature"] != merged[f"{field}_reference"]]
        mismatch_count += len(mismatches)
        for row in mismatches.head(remaining_issue_slots).itertuples(index=False):
            errors.append(
                HistoricalPanelValidationIssue(
                    code="FEATURE_REFERENCE_METADATA_MISMATCH",
                    message=(
                        "features metadata does not match active symbol reference: "
                        f"{row.symbol} {pd.Timestamp(row.session_date).date().isoformat()} "
                        f"{field} expected {getattr(row, f'{field}_reference')} "
                        f"observed {getattr(row, f'{field}_feature')}"
                    ),
                    file_key="features",
                    field=field,
                    symbol=str(row.symbol),
                    session_date=pd.Timestamp(row.session_date).date(),
                )
            )
        remaining_issue_slots -= min(len(mismatches), remaining_issue_slots)
        if remaining_issue_slots <= 0:
            break

    if mismatch_count > 10:
        errors.append(
            HistoricalPanelValidationIssue(
                code="FEATURE_REFERENCE_METADATA_MISMATCH",
                message=(
                    "features contains additional metadata mismatches against active "
                    f"symbol reference rows: {mismatch_count - 10}"
                ),
                file_key="features",
            )
        )


def _validate_required_feature_coverage(
    *,
    manifest: HistoricalPanelManifest,
    ohlcv: pd.DataFrame,
    reference: pd.DataFrame | None,
    features: pd.DataFrame,
    errors: list[HistoricalPanelValidationIssue],
) -> None:
    feature_start_session = manifest.feature_start_session or manifest.start_session
    required_ohlcv = expected_feature_coverage_rows(
        ohlcv=ohlcv,
        reference=reference,
        feature_start_session=feature_start_session,
        feature_coverage_scope=manifest.feature_coverage_scope,
    )
    if required_ohlcv.empty:
        return

    required_keys = {
        (str(row.symbol), pd.Timestamp(row.session_date).date())
        for row in required_ohlcv.itertuples(index=False)
    }
    feature_keys = {
        (str(row.symbol), pd.Timestamp(row.session_date).date())
        for row in features[["symbol", "session_date"]].itertuples(index=False)
    }
    missing_feature_keys = sorted(required_keys - feature_keys)
    for symbol, session_date in missing_feature_keys[:10]:
        errors.append(
            HistoricalPanelValidationIssue(
                code="FEATURE_COVERAGE_GAP",
                message=(
                    "features is missing required coverage from feature_start_session onward: "
                    f"{symbol} {session_date.isoformat()}"
                ),
                file_key="features",
                symbol=symbol,
                session_date=session_date,
            )
        )

    if len(missing_feature_keys) > 10:
        errors.append(
            HistoricalPanelValidationIssue(
                code="FEATURE_COVERAGE_GAP",
                message=(
                    "features is missing additional required coverage rows from "
                    f"feature_start_session onward: {len(missing_feature_keys) - 10}"
                ),
                file_key="features",
            )
        )


def expected_feature_coverage_rows(
    *,
    ohlcv: pd.DataFrame,
    reference: pd.DataFrame | None,
    feature_start_session: date,
    feature_coverage_scope: str,
) -> pd.DataFrame:
    required_ohlcv = ohlcv.loc[
        pd.to_datetime(ohlcv["session_date"]).dt.date >= feature_start_session,
        ["symbol", "session_date"],
    ].copy()
    if feature_coverage_scope == "all_ohlcv" or reference is None:
        return required_ohlcv
    if feature_coverage_scope == "tradable_reference":
        return _tradable_reference_coverage_rows(required_ohlcv=required_ohlcv, reference=reference)
    raise PreparedDataValidationError(
        f"unsupported feature_coverage_scope: {feature_coverage_scope}"
    )


def _tradable_reference_coverage_rows(
    *,
    required_ohlcv: pd.DataFrame,
    reference: pd.DataFrame,
) -> pd.DataFrame:
    active_reference = symbol_reference_rows_for_sessions(
        symbol_sessions=required_ohlcv,
        reference=reference,
    )
    if active_reference.empty:
        return required_ohlcv.iloc[0:0]

    session_dates = pd.to_datetime(active_reference["session_date"], errors="raise")
    tradable_start = pd.to_datetime(
        active_reference["tradable_start_session"],
        errors="coerce",
    )
    tradable_end = pd.to_datetime(active_reference["tradable_end_session"], errors="coerce")
    in_window = (tradable_start.isna() | (session_dates >= tradable_start)) & (
        tradable_end.isna() | (session_dates <= tradable_end)
    )
    tradable = active_reference["is_tradable"] & in_window
    return (
        active_reference.loc[tradable, ["symbol", "session_date"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )


def active_symbol_reference_rows(reference: pd.DataFrame, session: date) -> pd.DataFrame:
    """Return the one active symbol reference row per symbol for a session."""

    symbols = sorted(set(reference["symbol"].astype(str)))
    symbol_sessions = pd.DataFrame(
        {
            "symbol": symbols,
            "session_date": [pd.Timestamp(session)] * len(symbols),
        }
    )
    active = symbol_reference_rows_for_sessions(
        symbol_sessions=symbol_sessions,
        reference=reference,
    )
    return active.drop(columns=["session_date"]).reset_index(drop=True)


def symbol_reference_rows_for_sessions(
    *,
    symbol_sessions: pd.DataFrame,
    reference: pd.DataFrame,
) -> pd.DataFrame:
    """Join symbol/session rows to the active point-in-time reference rows."""

    sessions = symbol_sessions.copy()
    require_columns(sessions, ("symbol", "session_date"), frame_name="symbol/session data")
    sessions["symbol"] = sessions["symbol"].astype(str)
    sessions["session_date"] = pd.to_datetime(sessions["session_date"], errors="raise")

    reference_rows = reference.copy()
    require_columns(
        reference_rows,
        REQUIRED_SYMBOL_REFERENCE_COLUMNS,
        frame_name="symbol reference data",
    )
    reference_rows["symbol"] = reference_rows["symbol"].astype(str)
    for column in (
        *OPTIONAL_SYMBOL_REFERENCE_EFFECTIVE_WINDOW_COLUMNS,
        *OPTIONAL_SYMBOL_REFERENCE_TRADABILITY_WINDOW_COLUMNS,
    ):
        if column not in reference_rows.columns:
            reference_rows[column] = pd.NaT
        reference_rows[column] = pd.to_datetime(reference_rows[column], errors="coerce")

    merged = sessions.merge(reference_rows, on="symbol", how="inner")
    if merged.empty:
        return merged

    session_dates = pd.to_datetime(merged["session_date"], errors="raise")
    effective_start = pd.to_datetime(merged["effective_start_session"], errors="coerce")
    effective_end = pd.to_datetime(merged["effective_end_session"], errors="coerce")
    active = (effective_start.isna() | (session_dates >= effective_start)) & (
        effective_end.isna() | (session_dates <= effective_end)
    )
    active_rows = merged.loc[active].copy()
    duplicate_active = active_rows.duplicated(["symbol", "session_date"], keep=False)
    if duplicate_active.any():
        duplicate_symbols = sorted(set(active_rows.loc[duplicate_active, "symbol"].astype(str)))
        raise PreparedDataValidationError(
            "symbol reference data contains overlapping active rows for symbol/session: "
            f"{', '.join(duplicate_symbols)}"
        )
    return active_rows.sort_values(["session_date", "symbol"]).reset_index(drop=True)


def _validate_known_symbols(
    *,
    file_key: str,
    symbols: set[str],
    reference_symbols: set[str],
    code: str,
    errors: list[HistoricalPanelValidationIssue],
) -> None:
    for symbol in sorted(symbols - reference_symbols):
        errors.append(
            HistoricalPanelValidationIssue(
                code=code,
                message=f"{file_key} contains symbol missing from symbol reference data: {symbol}",
                file_key=file_key,
                symbol=symbol,
            )
        )


def _warn_about_session_gaps(
    *,
    manifest: HistoricalPanelManifest,
    ohlcv: pd.DataFrame,
    ohlcv_sessions: list[date],
    warnings: list[HistoricalPanelValidationIssue],
) -> None:
    expected_sessions = _expected_sessions_for_manifest(manifest)
    missing_sessions = sorted(set(expected_sessions) - set(ohlcv_sessions))
    if missing_sessions:
        missing_preview = ", ".join(session.isoformat() for session in missing_sessions[:5])
        warnings.append(
            HistoricalPanelValidationIssue(
                code="MISSING_EXPECTED_SESSIONS",
                message=(
                    "Historical panel is missing business sessions between start_session and "
                    f"end_session: {missing_preview}"
                ),
                file_key="ohlcv",
            )
        )

    expected_session_count = len(ohlcv_sessions)
    for symbol, symbol_rows in ohlcv.groupby("symbol"):
        symbol_sessions = _unique_session_dates(symbol_rows, "session_date")
        if len(symbol_sessions) < expected_session_count:
            warnings.append(
                HistoricalPanelValidationIssue(
                    code="INCOMPLETE_SYMBOL_HISTORY",
                    message=(
                        f"Symbol {symbol} has {len(symbol_sessions)} sessions; "
                        f"panel has {expected_session_count}"
                    ),
                    file_key="ohlcv",
                    symbol=str(symbol),
                )
            )


def _expected_sessions_for_manifest(manifest: HistoricalPanelManifest) -> list[date]:
    expected_sessions = [
        session.date() for session in pd.bdate_range(manifest.start_session, manifest.end_session)
    ]
    if manifest.calendar.upper() in {"US_EQUITY", "XNYS", "NYSE"}:
        return [
            session
            for session in expected_sessions
            if session not in _US_EQUITY_MARKET_HOLIDAYS
        ]
    return expected_sessions
