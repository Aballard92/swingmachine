from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from swingmachine.contracts import LookaheadAuditReport, LookaheadAuditViolation
from swingmachine.data_contracts import (
    HistoricalPanelData,
    load_historical_panel_data,
    validate_historical_panel_manifest,
)
from swingmachine.enums import ReviewStatus


def build_lookahead_audit_report(
    manifest_path: str | Path,
    *,
    checked_at: datetime | None = None,
) -> LookaheadAuditReport:
    """Build a structural point-in-time audit for a historical panel manifest.

    This audit does not claim to prove a model is profitable. It proves the
    panel has the mechanical evidence needed before profitability can be
    evaluated: valid manifest contracts, feature rows inside declared windows,
    effective symbol reference coverage for feature sessions, non-negative
    earnings timing fields, and deterministic per-symbol session order.
    """

    manifest_path = Path(manifest_path)
    checked_at = checked_at or datetime.utcnow()
    validation = validate_historical_panel_manifest(manifest_path)
    violations: list[LookaheadAuditViolation] = []
    warnings: list[str] = []

    if validation.status is not ReviewStatus.PASS:
        violations.extend(
            LookaheadAuditViolation(
                code="manifest_validation_failed",
                field=issue.field,
                observed=getattr(issue, "observed", None),
                expected=getattr(issue, "expected", None),
                message=issue.message,
            )
            for issue in validation.errors
        )
        return _report(
            panel_id=validation.panel_id,
            manifest_path=manifest_path,
            checked_at=checked_at,
            feature_window_check=ReviewStatus.FAIL,
            symbol_reference_check=ReviewStatus.FAIL,
            earnings_timing_check=ReviewStatus.FAIL,
            session_order_check=ReviewStatus.FAIL,
            violations=violations,
            warnings=warnings,
        )

    panel = load_historical_panel_data(manifest_path)
    raw_ohlcv = _read_declared_frame(
        manifest_path,
        panel.manifest.base_path,
        panel.manifest.files.ohlcv.path,
        panel.manifest.files.ohlcv.format,
    )
    raw_features = (
        None
        if panel.manifest.files.features is None
        else _read_declared_frame(
            manifest_path,
            panel.manifest.base_path,
            panel.manifest.files.features.path,
            panel.manifest.files.features.format,
        )
    )
    feature_window_violations = _feature_window_violations(panel)
    symbol_reference_violations = _symbol_reference_violations(panel)
    earnings_timing_violations = _earnings_timing_violations(panel)
    session_order_violations = _session_order_violations(
        raw_ohlcv=raw_ohlcv,
        raw_features=raw_features,
    )

    if panel.features is None:
        warnings.append("manifest has no prepared feature panel to audit")

    violations.extend(feature_window_violations)
    violations.extend(symbol_reference_violations)
    violations.extend(earnings_timing_violations)
    violations.extend(session_order_violations)

    return _report(
        panel_id=panel.manifest.panel_id,
        manifest_path=manifest_path,
        checked_at=checked_at,
        feature_window_check=_status_for(feature_window_violations),
        symbol_reference_check=_status_for(symbol_reference_violations),
        earnings_timing_check=_status_for(earnings_timing_violations),
        session_order_check=_status_for(session_order_violations),
        violations=violations,
        warnings=warnings,
    )


def write_lookahead_audit_report_json(
    report: LookaheadAuditReport,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output_path


def _feature_window_violations(
    panel: HistoricalPanelData,
) -> list[LookaheadAuditViolation]:
    if panel.features is None:
        return []

    manifest = panel.manifest
    features = _with_session_dates(panel.features)
    violations: list[LookaheadAuditViolation] = []
    min_session = manifest.start_session
    max_session = manifest.end_session
    feature_start_session = manifest.feature_start_session

    for row in features.itertuples(index=False):
        symbol = str(row.symbol)
        session_date = row.session_date
        if session_date < min_session or session_date > max_session:
            violations.append(
                LookaheadAuditViolation(
                    code="feature_session_outside_manifest_window",
                    symbol=symbol,
                    session_date=session_date,
                    field="session_date",
                    observed=session_date.isoformat(),
                    expected=f"{min_session.isoformat()}..{max_session.isoformat()}",
                    message="feature row session is outside the manifest panel window",
                )
            )
        if feature_start_session is not None and session_date < feature_start_session:
            violations.append(
                LookaheadAuditViolation(
                    code="feature_session_before_feature_start",
                    symbol=symbol,
                    session_date=session_date,
                    field="session_date",
                    observed=session_date.isoformat(),
                    expected=f">={feature_start_session.isoformat()}",
                    message="feature row is before the declared feature_start_session",
                )
            )

    return violations


def _symbol_reference_violations(
    panel: HistoricalPanelData,
) -> list[LookaheadAuditViolation]:
    if panel.features is None:
        return []

    features = _with_session_dates(panel.features)
    reference = _reference_with_window_dates(panel.symbol_reference)
    violations: list[LookaheadAuditViolation] = []

    for row in features.itertuples(index=False):
        symbol = str(row.symbol)
        session_date = row.session_date
        matching = _effective_reference_rows(reference, symbol=symbol, session_date=session_date)
        if matching.empty:
            violations.append(
                LookaheadAuditViolation(
                    code="missing_point_in_time_symbol_reference",
                    symbol=symbol,
                    session_date=session_date,
                    field="symbol_reference",
                    observed="missing",
                    expected="effective reference row",
                    message="feature row has no symbol reference row effective on that session",
                )
            )
            continue

        reference_row = matching.iloc[0]
        for field in ("asset_type", "sector", "exchange", "is_tradable"):
            if field not in features.columns or field not in reference.columns:
                continue
            observed = getattr(row, field)
            expected = reference_row[field]
            if _normalize_value(observed) == _normalize_value(expected):
                continue
            violations.append(
                LookaheadAuditViolation(
                    code="stale_or_future_symbol_reference_metadata",
                    symbol=symbol,
                    session_date=session_date,
                    field=field,
                    observed=_jsonable(observed),
                    expected=_jsonable(expected),
                    message="feature metadata differs from the point-in-time reference row",
                )
            )

        if panel.manifest.feature_coverage_scope == "tradable_reference":
            is_tradable = bool(reference_row["is_tradable"])
            if not is_tradable:
                violations.append(
                    LookaheadAuditViolation(
                        code="non_tradable_feature_in_tradable_scope",
                        symbol=symbol,
                        session_date=session_date,
                        field="is_tradable",
                        observed=False,
                        expected=True,
                        message="tradable_reference feature scope includes a non-tradable row",
                    )
                )

    return violations


def _earnings_timing_violations(
    panel: HistoricalPanelData,
) -> list[LookaheadAuditViolation]:
    if panel.features is None or "regular_closes_until_earnings_event" not in panel.features:
        return []

    features = _with_session_dates(panel.features)
    violations: list[LookaheadAuditViolation] = []

    for row in features.itertuples(index=False):
        observed = row.regular_closes_until_earnings_event
        if pd.isna(observed) or float(observed) < 0:
            violations.append(
                LookaheadAuditViolation(
                    code="invalid_earnings_timing_value",
                    symbol=str(row.symbol),
                    session_date=row.session_date,
                    field="regular_closes_until_earnings_event",
                    observed=_jsonable(observed),
                    expected="non-negative integer",
                    message=(
                        "earnings timing feature must be non-negative and known at "
                        "decision time"
                    ),
                )
            )

    return violations


def _session_order_violations(
    *,
    raw_ohlcv: pd.DataFrame,
    raw_features: pd.DataFrame | None,
) -> list[LookaheadAuditViolation]:
    frames: tuple[tuple[str, pd.DataFrame | None], ...] = (
        ("ohlcv", raw_ohlcv),
        ("features", raw_features),
    )
    violations: list[LookaheadAuditViolation] = []

    for frame_name, frame in frames:
        if frame is None or "symbol" not in frame or "session_date" not in frame:
            continue
        prepared = _with_session_dates(frame)
        for symbol, group in prepared.groupby("symbol", sort=False):
            previous = None
            for row in group.itertuples(index=False):
                session_date = row.session_date
                if previous is not None and session_date <= previous:
                    violations.append(
                        LookaheadAuditViolation(
                            code=f"{frame_name}_session_order_not_strict",
                            symbol=str(symbol),
                            session_date=session_date,
                            field="session_date",
                            observed=session_date.isoformat(),
                            expected=f">{previous.isoformat()}",
                            message=f"{frame_name} sessions must be strictly increasing per symbol",
                        )
                    )
                previous = session_date

    return violations


def _report(
    *,
    panel_id: str,
    manifest_path: Path,
    checked_at: datetime,
    feature_window_check: ReviewStatus,
    symbol_reference_check: ReviewStatus,
    earnings_timing_check: ReviewStatus,
    session_order_check: ReviewStatus,
    violations: list[LookaheadAuditViolation],
    warnings: list[str],
) -> LookaheadAuditReport:
    return LookaheadAuditReport(
        panel_id=panel_id,
        manifest_path=str(manifest_path),
        status=_overall_status(violations, warnings),
        checked_at=checked_at,
        feature_window_check=feature_window_check,
        symbol_reference_check=symbol_reference_check,
        earnings_timing_check=earnings_timing_check,
        session_order_check=session_order_check,
        violations=tuple(violations),
        warnings=tuple(warnings),
    )


def _read_declared_frame(
    manifest_path: Path,
    base_path: str | None,
    declared_path: str,
    declared_format: str,
) -> pd.DataFrame:
    file_path = Path(declared_path)
    if not file_path.is_absolute():
        file_path = manifest_path.parent / Path(base_path or ".") / file_path
    if declared_format == "csv":
        return pd.read_csv(file_path)
    if declared_format == "parquet":
        return pd.read_parquet(file_path)
    raise ValueError(f"Unsupported historical panel file format: {declared_format}")


def _with_session_dates(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.copy()
    prepared["session_date"] = pd.to_datetime(
        prepared["session_date"],
        errors="raise",
    ).dt.date
    return prepared


def _reference_with_window_dates(reference: pd.DataFrame) -> pd.DataFrame:
    prepared = reference.copy()
    for field in (
        "effective_start_session",
        "effective_end_session",
        "tradable_start_session",
        "tradable_end_session",
    ):
        if field in prepared:
            prepared[field] = pd.to_datetime(prepared[field], errors="coerce").dt.date
    return prepared


def _effective_reference_rows(
    reference: pd.DataFrame,
    *,
    symbol: str,
    session_date: Any,
) -> pd.DataFrame:
    symbol_rows = reference[reference["symbol"].astype(str) == symbol]
    if symbol_rows.empty:
        return symbol_rows
    mask = symbol_rows.apply(
        lambda row: _reference_row_effective(row, session_date=session_date),
        axis=1,
    )
    return symbol_rows[mask]


def _reference_row_effective(row: pd.Series, *, session_date: Any) -> bool:
    return (
        _window_allows(row, "effective_start_session", session_date, lower_bound=True)
        and _window_allows(row, "effective_end_session", session_date, lower_bound=False)
        and _window_allows(row, "tradable_start_session", session_date, lower_bound=True)
        and _window_allows(row, "tradable_end_session", session_date, lower_bound=False)
    )


def _window_allows(
    row: pd.Series,
    field: str,
    session_date: Any,
    *,
    lower_bound: bool,
) -> bool:
    if field not in row or pd.isna(row[field]):
        return True
    if lower_bound:
        return row[field] <= session_date
    return row[field] >= session_date


def _status_for(violations: list[LookaheadAuditViolation]) -> ReviewStatus:
    return ReviewStatus.FAIL if violations else ReviewStatus.PASS


def _overall_status(
    violations: list[LookaheadAuditViolation],
    warnings: list[str],
) -> ReviewStatus:
    if violations:
        return ReviewStatus.FAIL
    if warnings:
        return ReviewStatus.WARN
    return ReviewStatus.PASS


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().upper()
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return None
    return value


def _jsonable(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value
