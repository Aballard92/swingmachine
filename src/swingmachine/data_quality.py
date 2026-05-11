from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from swingmachine.contracts import (
    HistoricalDataQualityIssue,
    HistoricalDataQualityReport,
    HistoricalDataQualitySymbolSummary,
)
from swingmachine.data_contracts import (
    HistoricalPanelData,
    load_historical_panel_data,
    validate_historical_panel_manifest,
)
from swingmachine.enums import ReviewStatus


def build_historical_data_quality_report(
    manifest_path: str | Path,
    *,
    benchmark_symbol: str | None = "SPY",
    checked_at: datetime | None = None,
) -> HistoricalDataQualityReport:
    """Build an offline data-quality and survivorship-risk audit for a panel.

    This report is deliberately non-destructive. It does not rewrite source
    data, create manifests, or run strategy logic. It complements manifest
    validation by summarising coverage, duplicate keys, OHLCV anomalies,
    benchmark coverage, and survivorship-risk warnings.
    """

    manifest_path = Path(manifest_path)
    checked_at = checked_at or datetime.utcnow()
    validation = validate_historical_panel_manifest(manifest_path)

    if validation.status is ReviewStatus.FAIL:
        issues = tuple(
            HistoricalDataQualityIssue(
                code=issue.code,
                severity="BLOCKER",
                field=issue.field,
                observed=getattr(issue, "observed", None),
                expected=getattr(issue, "expected", None),
                message=issue.message,
            )
            for issue in validation.errors
        )
        return HistoricalDataQualityReport(
            panel_id=validation.panel_id,
            manifest_path=str(manifest_path),
            status=ReviewStatus.FAIL,
            checked_at=checked_at,
            calendar="UNKNOWN",
            symbol_count=validation.symbol_count,
            session_count=validation.session_count,
            ohlcv_row_count=0,
            coverage_check=ReviewStatus.FAIL,
            duplicate_check=ReviewStatus.FAIL,
            price_volume_check=ReviewStatus.FAIL,
            benchmark_coverage_check=ReviewStatus.FAIL,
            survivorship_check=ReviewStatus.FAIL,
            benchmark_symbol=benchmark_symbol,
            issues=issues,
        )

    panel = load_historical_panel_data(manifest_path)
    ohlcv = _with_session_dates(panel.ohlcv)
    features = None if panel.features is None else _with_session_dates(panel.features)
    all_sessions = _unique_dates(ohlcv["session_date"])
    all_symbols = _panel_symbols(panel, ohlcv)
    issues: list[HistoricalDataQualityIssue] = []
    warnings: list[str] = [issue.message for issue in validation.warnings]

    duplicate_mask = ohlcv.duplicated(["symbol", "session_date"], keep=False)
    invalid_ohlc_mask = _invalid_ohlc_mask(ohlcv)
    negative_volume_mask = pd.to_numeric(ohlcv["raw_volume"], errors="coerce") < 0
    zero_volume_mask = pd.to_numeric(ohlcv["raw_volume"], errors="coerce") == 0

    if duplicate_mask.any():
        issues.append(
            HistoricalDataQualityIssue(
                code="duplicate_ohlcv_symbol_sessions",
                severity="BLOCKER",
                field="symbol/session_date",
                observed=int(duplicate_mask.sum()),
                expected=0,
                message="OHLCV data contains duplicate symbol/session rows",
            )
        )
    if invalid_ohlc_mask.any():
        issues.append(
            HistoricalDataQualityIssue(
                code="invalid_ohlc_relationships",
                severity="BLOCKER",
                field="raw_open/raw_high/raw_low/raw_close",
                observed=int(invalid_ohlc_mask.sum()),
                expected=0,
                message="OHLCV data contains impossible high/low/open/close relationships",
            )
        )
    if negative_volume_mask.any():
        issues.append(
            HistoricalDataQualityIssue(
                code="negative_volume_rows",
                severity="BLOCKER",
                field="raw_volume",
                observed=int(negative_volume_mask.sum()),
                expected=0,
                message="OHLCV data contains negative volume rows",
            )
        )
    if zero_volume_mask.any():
        issues.append(
            HistoricalDataQualityIssue(
                code="zero_volume_rows",
                severity="WARNING",
                field="raw_volume",
                observed=int(zero_volume_mask.sum()),
                expected=0,
                message="OHLCV data contains zero-volume rows that should be reviewed",
            )
        )

    symbol_summaries = _symbol_summaries(
        all_symbols=all_symbols,
        all_sessions=all_sessions,
        ohlcv=ohlcv,
        features=features,
        duplicate_mask=duplicate_mask,
        invalid_ohlc_mask=invalid_ohlc_mask,
        negative_volume_mask=negative_volume_mask,
        zero_volume_mask=zero_volume_mask,
    )
    missing_session_symbols = [
        summary
        for summary in symbol_summaries
        if summary.missing_session_count or summary.missing_feature_session_count
    ]
    for summary in missing_session_symbols:
        if summary.missing_session_count:
            issues.append(
                HistoricalDataQualityIssue(
                    code="missing_symbol_sessions",
                    severity="BLOCKER",
                    symbol=summary.symbol,
                    field="session_date",
                    observed=summary.missing_session_count,
                    expected=0,
                    message="Symbol is missing sessions from the panel session grid",
                )
            )
        if summary.missing_feature_session_count:
            issues.append(
                HistoricalDataQualityIssue(
                    code="missing_feature_sessions",
                    severity="BLOCKER",
                    symbol=summary.symbol,
                    field="features.session_date",
                    observed=summary.missing_feature_session_count,
                    expected=0,
                    message="Symbol is missing feature rows from the declared feature grid",
                )
            )

    _append_benchmark_coverage_issues(
        issues,
        ohlcv=ohlcv,
        all_sessions=all_sessions,
        benchmark_symbol=benchmark_symbol,
    )
    warnings.extend(_survivorship_warnings(panel, all_sessions=all_sessions))

    coverage_issue_codes = {"missing_symbol_sessions", "missing_feature_sessions"}
    coverage_check = _check_status(issues, coverage_issue_codes)
    duplicate_check = _check_status(issues, {"duplicate_ohlcv_symbol_sessions"})
    price_volume_check = _check_status(
        issues,
        {
            "invalid_ohlc_relationships",
            "negative_volume_rows",
            "zero_volume_rows",
        },
    )
    benchmark_coverage_check = _check_status(
        issues,
        {"benchmark_symbol_missing", "benchmark_sessions_missing"},
    )
    survivorship_check = ReviewStatus.WARN if warnings else ReviewStatus.PASS

    return HistoricalDataQualityReport(
        panel_id=panel.manifest.panel_id,
        manifest_path=str(manifest_path),
        status=_overall_status(issues, warnings),
        checked_at=checked_at,
        calendar=panel.manifest.calendar,
        source_start_session=panel.manifest.start_session,
        source_end_session=panel.manifest.end_session,
        replay_start_session=panel.manifest.replay_start_session,
        replay_end_session=panel.manifest.replay_end_session,
        symbol_count=len(all_symbols),
        session_count=len(all_sessions),
        ohlcv_row_count=len(ohlcv),
        feature_row_count=0 if features is None else len(features),
        coverage_check=coverage_check,
        duplicate_check=duplicate_check,
        price_volume_check=price_volume_check,
        benchmark_coverage_check=benchmark_coverage_check,
        survivorship_check=survivorship_check,
        benchmark_symbol=benchmark_symbol,
        issues=tuple(issues),
        warnings=tuple(warnings),
        symbol_summaries=tuple(symbol_summaries),
    )


def write_historical_data_quality_report_json(
    report: HistoricalDataQualityReport,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output_path


def write_historical_data_quality_report_markdown(
    report: HistoricalDataQualityReport,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_markdown(report), encoding="utf-8")
    return output_path


def _panel_symbols(panel: HistoricalPanelData, ohlcv: pd.DataFrame) -> tuple[str, ...]:
    if "symbol" in panel.symbol_reference:
        values = panel.symbol_reference["symbol"].astype(str).str.strip()
        return tuple(sorted(symbol for symbol in values.unique() if symbol))
    values = ohlcv["symbol"].astype(str).str.strip()
    return tuple(sorted(symbol for symbol in values.unique() if symbol))


def _symbol_summaries(
    *,
    all_symbols: tuple[str, ...],
    all_sessions: tuple[date, ...],
    ohlcv: pd.DataFrame,
    features: pd.DataFrame | None,
    duplicate_mask: pd.Series,
    invalid_ohlc_mask: pd.Series,
    negative_volume_mask: pd.Series,
    zero_volume_mask: pd.Series,
) -> list[HistoricalDataQualitySymbolSummary]:
    summaries: list[HistoricalDataQualitySymbolSummary] = []
    all_session_set = set(all_sessions)
    feature_session_set = (
        set(_unique_dates(features["session_date"])) if features is not None else set()
    )

    for symbol in all_symbols:
        symbol_mask = ohlcv["symbol"].astype(str) == symbol
        symbol_rows = ohlcv.loc[symbol_mask]
        symbol_sessions = set(_unique_dates(symbol_rows["session_date"]))
        feature_rows = (
            pd.DataFrame()
            if features is None
            else features.loc[features["symbol"].astype(str) == symbol]
        )
        symbol_feature_sessions = (
            set() if features is None else set(_unique_dates(feature_rows["session_date"]))
        )
        summaries.append(
            HistoricalDataQualitySymbolSummary(
                symbol=symbol,
                ohlcv_row_count=len(symbol_rows),
                first_session=min(symbol_sessions) if symbol_sessions else None,
                last_session=max(symbol_sessions) if symbol_sessions else None,
                missing_session_count=len(all_session_set - symbol_sessions),
                duplicate_ohlcv_row_count=int(duplicate_mask.loc[symbol_mask].sum()),
                invalid_ohlc_row_count=int(invalid_ohlc_mask.loc[symbol_mask].sum()),
                negative_volume_row_count=int(negative_volume_mask.loc[symbol_mask].sum()),
                zero_volume_row_count=int(zero_volume_mask.loc[symbol_mask].sum()),
                feature_row_count=len(feature_rows),
                missing_feature_session_count=(
                    0 if features is None else len(feature_session_set - symbol_feature_sessions)
                ),
            )
        )
    return summaries


def _append_benchmark_coverage_issues(
    issues: list[HistoricalDataQualityIssue],
    *,
    ohlcv: pd.DataFrame,
    all_sessions: tuple[date, ...],
    benchmark_symbol: str | None,
) -> None:
    if benchmark_symbol is None:
        return
    benchmark_rows = ohlcv[ohlcv["symbol"].astype(str) == benchmark_symbol]
    if benchmark_rows.empty:
        issues.append(
            HistoricalDataQualityIssue(
                code="benchmark_symbol_missing",
                severity="BLOCKER",
                symbol=benchmark_symbol,
                field="symbol",
                observed="missing",
                expected="present",
                message="Benchmark symbol is missing from the historical panel",
            )
        )
        return
    missing = set(all_sessions) - set(_unique_dates(benchmark_rows["session_date"]))
    if missing:
        issues.append(
            HistoricalDataQualityIssue(
                code="benchmark_sessions_missing",
                severity="BLOCKER",
                symbol=benchmark_symbol,
                field="session_date",
                observed=len(missing),
                expected=0,
                message="Benchmark symbol is missing sessions from the panel grid",
            )
        )


def _survivorship_warnings(
    panel: HistoricalPanelData,
    *,
    all_sessions: tuple[date, ...],
) -> list[str]:
    warnings: list[str] = []
    reference = panel.symbol_reference
    long_panel = len(all_sessions) >= 252

    if long_panel and (
        "effective_start_session" not in reference
        or reference["effective_start_session"].isna().all()
    ):
        warnings.append(
            "symbol reference is static across a long panel; survivorship and membership "
            "changes are not independently auditable"
        )
    if long_panel and panel.corporate_actions.empty:
        warnings.append(
            "corporate actions file is empty across a long panel; adjusted-price correctness "
            "depends on the upstream provider"
        )
    if panel.manifest.feature_coverage_scope == "tradable_reference" and "is_tradable" in reference:
        tradable_values = reference["is_tradable"].astype(bool)
        if long_panel and tradable_values.all():
            warnings.append(
                "all symbols are marked tradable for the full long panel; historical "
                "tradability changes are not represented"
            )

    return warnings


def _invalid_ohlc_mask(frame: pd.DataFrame) -> pd.Series:
    numeric = frame[["raw_open", "raw_high", "raw_low", "raw_close"]].apply(
        pd.to_numeric,
        errors="coerce",
    )
    positive_prices = (numeric > 0).all(axis=1)
    high_valid = numeric["raw_high"] >= numeric[["raw_open", "raw_low", "raw_close"]].max(axis=1)
    low_valid = numeric["raw_low"] <= numeric[["raw_open", "raw_high", "raw_close"]].min(axis=1)
    return ~(positive_prices & high_valid & low_valid)


def _with_session_dates(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = frame.copy()
    prepared["session_date"] = pd.to_datetime(prepared["session_date"], errors="raise").dt.date
    return prepared


def _unique_dates(values: Iterable[Any]) -> tuple[date, ...]:
    return tuple(sorted({value for value in values if pd.notna(value)}))


def _check_status(
    issues: list[HistoricalDataQualityIssue],
    issue_codes: set[str],
) -> ReviewStatus:
    matching = [issue for issue in issues if issue.code in issue_codes]
    if any(issue.severity == "BLOCKER" for issue in matching):
        return ReviewStatus.FAIL
    if matching:
        return ReviewStatus.WARN
    return ReviewStatus.PASS


def _overall_status(
    issues: list[HistoricalDataQualityIssue],
    warnings: list[str],
) -> ReviewStatus:
    if any(issue.severity == "BLOCKER" for issue in issues):
        return ReviewStatus.FAIL
    if warnings or any(issue.severity == "WARNING" for issue in issues):
        return ReviewStatus.WARN
    return ReviewStatus.PASS


def _render_markdown(report: HistoricalDataQualityReport) -> str:
    lines = [
        "# Historical Data Quality Report",
        "",
        f"Panel: `{report.panel_id}`",
        "",
        f"Status: `{report.status.value}`",
        "",
        f"Manifest: `{report.manifest_path}`",
        "",
        "## Coverage",
        "",
        f"- Source coverage: `{report.source_start_session}` to `{report.source_end_session}`",
        f"- Replay coverage: `{report.replay_start_session}` to `{report.replay_end_session}`",
        f"- Symbols: {report.symbol_count}",
        f"- Sessions: {report.session_count}",
        f"- OHLCV rows: {report.ohlcv_row_count}",
        f"- Feature rows: {report.feature_row_count}",
        "",
        "## Checks",
        "",
        "| Check | Status |",
        "| --- | --- |",
        f"| Coverage | `{report.coverage_check.value}` |",
        f"| Duplicates | `{report.duplicate_check.value}` |",
        f"| Price/volume | `{report.price_volume_check.value}` |",
        f"| Benchmark coverage | `{report.benchmark_coverage_check.value}` |",
        f"| Survivorship risk | `{report.survivorship_check.value}` |",
        "",
        "## Issues",
        "",
    ]
    if report.issues:
        lines.extend(
            f"- `{issue.severity}` `{issue.code}`"
            f"{' ' + issue.symbol if issue.symbol else ''}: {issue.message}"
            for issue in report.issues
        )
    else:
        lines.append("- None.")
    lines.extend(["", "## Warnings", ""])
    if report.warnings:
        lines.extend(f"- {warning}" for warning in report.warnings)
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Symbol summaries",
            "",
            "| Symbol | Rows | Missing sessions | Duplicate rows | Invalid OHLC | "
            "Zero volume | Feature rows | Missing feature sessions |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    lines.extend(
        (
            f"| `{summary.symbol}` | {summary.ohlcv_row_count} | "
            f"{summary.missing_session_count} | {summary.duplicate_ohlcv_row_count} | "
            f"{summary.invalid_ohlc_row_count} | {summary.zero_volume_row_count} | "
            f"{summary.feature_row_count} | {summary.missing_feature_session_count} |"
        )
        for summary in report.symbol_summaries
    )
    lines.append("")
    return "\n".join(lines)
