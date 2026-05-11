from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import median
from typing import Any

import pandas as pd

from swingmachine.contracts import (
    AcceptedCandidateExcessDistributionReport,
    AcceptedVersusNearMissReport,
    ExitPathDiagnosticReport,
    ExitPathTradeDiagnostic,
    FeatureOutcomeAttributionDataset,
    FeatureOutcomeAttributionRow,
    FeatureOutcomeAttributionSummary,
    FeatureOutcomeBucketMetrics,
    FeatureOutcomeDistributionMetrics,
    FeatureOutcomeSubsetMetrics,
    FeatureSnapshotBucketReport,
    PatternSpecificBenchmarkDiagnostic,
    PatternSpecificBenchmarkDiagnosticReport,
    TradedLifecycleGroupMetrics,
    TradedLifecycleOutcomeDecompositionReport,
)
from swingmachine.data_contracts import load_historical_panel_data
from swingmachine.enums import ReviewStatus

DEFAULT_FORWARD_WINDOWS = (1, 5, 10, 20)
DEFAULT_FEATURE_SNAPSHOT_FIELDS = (
    "rs_vs_benchmark_20",
    "rs_vs_benchmark_50",
    "rs_vs_benchmark_100",
    "rs_vs_benchmark_126",
    "rs_acceleration_20_vs_100",
    "rs_acceleration_50_vs_126",
    "symbol_drawdown_63",
    "benchmark_drawdown_63",
    "relative_drawdown_63",
    "relative_rebound_20",
    "regime_state",
    "candidate_score_pct",
    "trend_quality",
)
DEFAULT_BUCKET_FIELDS = (
    "regime_state",
    "rs_vs_benchmark_20",
    "rs_acceleration_20_vs_100",
    "relative_rebound_20",
    "relative_drawdown_63",
    "trend_quality",
)
MIN_ROBUST_ACCEPTED_ROWS = 30
MIN_ROBUST_TRADED_ROWS = 5
MIN_EXPLORATORY_ACCEPTED_ROWS = 10
MIN_EXPLORATORY_TRADED_ROWS = 3


def build_feature_outcome_attribution_dataset(
    *,
    scanner_material_decisions_path: str | Path,
    manifest_path: str | Path,
    lifecycle_trade_ledger_path: str | Path | None = None,
    feature_snapshot_path: str | Path | None = None,
    feature_snapshot_fields: Sequence[str] = DEFAULT_FEATURE_SNAPSHOT_FIELDS,
    benchmark_symbol: str | None = "SPY",
    forward_windows: Sequence[int] = DEFAULT_FORWARD_WINDOWS,
    generated_at: datetime | None = None,
) -> FeatureOutcomeAttributionDataset:
    """Build an offline feature/outcome table for material scanner decisions."""

    scanner_path = Path(scanner_material_decisions_path)
    manifest_path = Path(manifest_path)
    lifecycle_path = (
        None if lifecycle_trade_ledger_path is None else Path(lifecycle_trade_ledger_path)
    )
    feature_snapshot_source_path = (
        None if feature_snapshot_path is None else Path(feature_snapshot_path)
    )
    scanner_rows = _load_scanner_material_rows(scanner_path)
    trade_rows = [] if lifecycle_path is None else _load_trade_ledger_rows(lifecycle_path)
    trades_by_setup_id = _trades_by_setup_id(trade_rows)
    prices = _price_index(manifest_path)
    feature_snapshots, feature_snapshot_warnings = _load_feature_snapshots(
        feature_snapshot_source_path,
        fields=feature_snapshot_fields,
    )
    rows: list[FeatureOutcomeAttributionRow] = []
    warnings: list[str] = list(feature_snapshot_warnings)

    if not scanner_rows:
        warnings.append("scanner material decisions contained no rows")
    if lifecycle_path is not None and not trade_rows:
        warnings.append("lifecycle trade ledger contained no trades")

    for row in scanner_rows:
        setup_id = _optional_str(row.get("setup_id"))
        trade = trades_by_setup_id.get(setup_id or "")
        symbol = str(row["symbol"])
        signal_session = _parse_date(row["signal_session"])
        next_session = _optional_date(row.get("next_session"))
        candidate_forward_returns = _forward_close_returns(
            prices,
            symbol=symbol,
            start_session=next_session,
            windows=forward_windows,
        )
        benchmark_forward_returns = (
            {}
            if benchmark_symbol is None
            else _forward_close_returns(
                prices,
                symbol=benchmark_symbol,
                start_session=next_session,
                windows=forward_windows,
            )
        )
        rows.append(
            FeatureOutcomeAttributionRow(
                panel_id=str(row.get("panel_id") or ""),
                symbol=symbol,
                signal_session=signal_session,
                next_session=next_session,
                candidate_id=_optional_str(row.get("candidate_id")),
                setup_id=setup_id,
                signal_id=_optional_str(row.get("signal_id")),
                risk_plan_id=_optional_str(row.get("risk_plan_id")),
                order_plan_id=_optional_str(row.get("order_plan_id")),
                decision=str(row.get("decision") or ""),
                pattern_type=_optional_str(row.get("pattern_type")),
                candidate_score_pct=_optional_float(row.get("candidate_score_pct")),
                rank=_optional_int(row.get("rank")),
                reason_codes=_string_tuple(row.get("reason_codes")),
                rejection_reasons=_rejection_reasons(row),
                traded=trade is not None,
                trade_id=None if trade is None else _optional_str(trade.get("trade_id")),
                entry_fill_date=(
                    None if trade is None else _optional_date(trade.get("entry_fill_date"))
                ),
                exit_fill_date=(
                    None if trade is None else _optional_date(trade.get("exit_fill_date"))
                ),
                exit_reason=None if trade is None else _optional_str(trade.get("exit_reason")),
                bars_held=None if trade is None else _optional_int(trade.get("bars_held")),
                net_pnl=None if trade is None else _optional_float(trade.get("net_pnl")),
                net_return=None if trade is None else _optional_float(trade.get("net_return")),
                forward_close_returns=candidate_forward_returns,
                benchmark_forward_close_returns=benchmark_forward_returns,
                forward_close_excess_returns=_excess_returns(
                    candidate_forward_returns,
                    benchmark_forward_returns,
                ),
                feature_snapshot=feature_snapshots.get((symbol, signal_session), {}),
            )
        )

    panel_id = _dataset_panel_id(scanner_rows, rows)
    summary = FeatureOutcomeAttributionSummary(
        panel_id=panel_id,
        generated_at=generated_at or datetime.now(UTC),
        source_scanner_material_decisions_path=str(scanner_path),
        source_lifecycle_trade_ledger_path=None if lifecycle_path is None else str(lifecycle_path),
        source_manifest_path=str(manifest_path),
        source_feature_snapshot_path=(
            None if feature_snapshot_source_path is None else str(feature_snapshot_source_path)
        ),
        benchmark_symbol=benchmark_symbol,
        feature_snapshot_fields=tuple(feature_snapshot_fields),
        row_count=len(rows),
        accepted_count=sum(1 for row in rows if row.decision != "REJECTED"),
        rejected_count=sum(1 for row in rows if row.decision == "REJECTED"),
        traded_count=sum(1 for row in rows if row.traded),
        forward_windows=tuple(int(window) for window in forward_windows),
        warnings=tuple(warnings),
    )
    return FeatureOutcomeAttributionDataset(summary=summary, rows=tuple(rows))


def write_feature_outcome_attribution_dataset(
    dataset: FeatureOutcomeAttributionDataset,
    output_dir: str | Path,
) -> dict[str, str]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "feature_outcome_attribution_dataset.json"
    csv_path = destination / "feature_outcome_attribution_rows.csv"
    markdown_path = destination / "feature_outcome_attribution_summary.md"

    json_path.write_text(dataset.model_dump_json(indent=2) + "\n", encoding="utf-8")
    _write_rows_csv(dataset, csv_path)
    markdown_path.write_text(_render_markdown(dataset), encoding="utf-8")
    return {
        "dataset": str(json_path),
        "rows_csv": str(csv_path),
        "summary_markdown": str(markdown_path),
    }


def build_accepted_vs_near_miss_report(
    dataset_or_path: FeatureOutcomeAttributionDataset | str | Path,
    *,
    report_id: str | None = None,
    near_miss_score_floor: float = 0.75,
    generated_at: datetime | None = None,
) -> AcceptedVersusNearMissReport:
    dataset, source_path = _coerce_dataset(dataset_or_path)
    rows = list(dataset.rows)
    accepted_rows = [row for row in rows if row.decision != "REJECTED"]
    rejected_rows = [row for row in rows if row.decision == "REJECTED"]
    near_miss_rows = [
        row
        for row in rejected_rows
        if row.candidate_score_pct is not None
        and row.candidate_score_pct >= near_miss_score_floor
    ]
    by_score_bucket = {
        bucket_id: _bucket_metrics(bucket_id, bucket_rows)
        for bucket_id, bucket_rows in _rows_by_score_bucket(rows).items()
    }
    by_rejection_reason = {
        reason: _bucket_metrics(reason, reason_rows)
        for reason, reason_rows in _rows_by_rejection_reason(rejected_rows).items()
    }
    accepted_metrics = _bucket_metrics("accepted", accepted_rows)
    near_miss_metrics = _bucket_metrics("near_miss", near_miss_rows)
    warnings: list[str] = []
    if not near_miss_rows:
        warnings.append("near-miss definition matched no rows")
    if len(accepted_rows) < 30:
        warnings.append("accepted sample is small")
    if dataset.summary.warnings:
        warnings.extend(dataset.summary.warnings)

    return AcceptedVersusNearMissReport(
        report_id=report_id
        or f"accepted_vs_near_miss:{dataset.summary.panel_id}:{near_miss_score_floor}",
        generated_at=generated_at or datetime.now(UTC),
        status=ReviewStatus.WARN if warnings else ReviewStatus.PASS,
        source_dataset_path=source_path,
        row_count=len(rows),
        near_miss_definition=(
            "decision == REJECTED and candidate_score_pct is present and "
            f"candidate_score_pct >= {near_miss_score_floor}"
        ),
        accepted=accepted_metrics,
        rejected=_bucket_metrics("rejected", rejected_rows),
        near_miss=near_miss_metrics,
        by_score_bucket=by_score_bucket,
        by_rejection_reason=by_rejection_reason,
        conclusion=_accepted_vs_near_miss_conclusion(accepted_metrics, near_miss_metrics),
        warnings=tuple(warnings),
    )


def write_accepted_vs_near_miss_report(
    report: AcceptedVersusNearMissReport,
    output_dir: str | Path,
) -> dict[str, str]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "accepted_vs_near_miss_report.json"
    markdown_path = destination / "accepted_vs_near_miss_report.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_near_miss_markdown(report), encoding="utf-8")
    return {"report": str(json_path), "summary_markdown": str(markdown_path)}


def build_feature_snapshot_bucket_report(
    dataset_or_path: FeatureOutcomeAttributionDataset | str | Path,
    *,
    report_id: str | None = None,
    bucket_fields: Sequence[str] = DEFAULT_BUCKET_FIELDS,
    generated_at: datetime | None = None,
) -> FeatureSnapshotBucketReport:
    dataset, source_path = _coerce_dataset(dataset_or_path)
    rows = list(dataset.rows)
    by_feature_bucket = {
        field: {
            bucket_id: _bucket_metrics(bucket_id, bucket_rows)
            for bucket_id, bucket_rows in _rows_by_feature_bucket(rows, field).items()
        }
        for field in bucket_fields
    }
    warnings: list[str] = []
    for field in bucket_fields:
        if not any(field in row.feature_snapshot for row in rows):
            warnings.append(f"feature field {field} is missing from all rows")

    return FeatureSnapshotBucketReport(
        report_id=report_id or f"feature_snapshot_bucket:{dataset.summary.panel_id}",
        generated_at=generated_at or datetime.now(UTC),
        status=ReviewStatus.WARN if warnings else ReviewStatus.PASS,
        source_dataset_path=source_path,
        row_count=len(rows),
        bucket_fields=tuple(bucket_fields),
        sample_guardrails={
            "min_robust_accepted_rows": MIN_ROBUST_ACCEPTED_ROWS,
            "min_robust_traded_rows": MIN_ROBUST_TRADED_ROWS,
            "min_exploratory_accepted_rows": MIN_EXPLORATORY_ACCEPTED_ROWS,
            "min_exploratory_traded_rows": MIN_EXPLORATORY_TRADED_ROWS,
        },
        by_feature_bucket=by_feature_bucket,
        conclusion=_feature_bucket_conclusion(by_feature_bucket),
        warnings=tuple(warnings),
    )


def write_feature_snapshot_bucket_report(
    report: FeatureSnapshotBucketReport,
    output_dir: str | Path,
) -> dict[str, str]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "feature_snapshot_bucket_report.json"
    markdown_path = destination / "feature_snapshot_bucket_report.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_feature_bucket_markdown(report), encoding="utf-8")
    return {"report": str(json_path), "summary_markdown": str(markdown_path)}


def build_accepted_excess_distribution_report(
    dataset_or_path: FeatureOutcomeAttributionDataset | str | Path,
    *,
    report_id: str | None = None,
    near_miss_score_floor: float = 0.75,
    generated_at: datetime | None = None,
) -> AcceptedCandidateExcessDistributionReport:
    dataset, source_path = _coerce_dataset(dataset_or_path)
    rows = list(dataset.rows)
    accepted_rows = [row for row in rows if row.decision != "REJECTED"]
    rejected_rows = [row for row in rows if row.decision == "REJECTED"]
    near_miss_rows = [
        row
        for row in rejected_rows
        if row.candidate_score_pct is not None
        and row.candidate_score_pct >= near_miss_score_floor
    ]
    forward_windows = dataset.summary.forward_windows
    populations = {
        "accepted": _distribution_by_window("accepted", accepted_rows, forward_windows),
        "near_miss": _distribution_by_window(
            "near_miss",
            near_miss_rows,
            forward_windows,
        ),
        "rejected": _distribution_by_window("rejected", rejected_rows, forward_windows),
        "all_rows": _distribution_by_window("all_rows", rows, forward_windows),
    }
    warnings: list[str] = []
    if not accepted_rows:
        warnings.append("accepted population is empty")
    if not near_miss_rows:
        warnings.append("near-miss population is empty")

    return AcceptedCandidateExcessDistributionReport(
        report_id=report_id or f"accepted_excess_distribution:{dataset.summary.panel_id}",
        generated_at=generated_at or datetime.now(UTC),
        status=ReviewStatus.WARN if warnings else ReviewStatus.PASS,
        source_dataset_path=source_path,
        near_miss_definition=(
            "decision == REJECTED and candidate_score_pct is present and "
            f"candidate_score_pct >= {near_miss_score_floor}"
        ),
        populations=populations,
        conclusion=_distribution_conclusion(populations),
        warnings=tuple(warnings),
    )


def write_accepted_excess_distribution_report(
    report: AcceptedCandidateExcessDistributionReport,
    output_dir: str | Path,
) -> dict[str, str]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "accepted_excess_distribution_report.json"
    markdown_path = destination / "accepted_excess_distribution_report.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_distribution_markdown(report), encoding="utf-8")
    return {"report": str(json_path), "summary_markdown": str(markdown_path)}


def build_traded_lifecycle_decomposition_report(
    dataset_or_path: FeatureOutcomeAttributionDataset | str | Path,
    *,
    report_id: str | None = None,
    feature_bucket_fields: Sequence[str] = DEFAULT_BUCKET_FIELDS,
    generated_at: datetime | None = None,
) -> TradedLifecycleOutcomeDecompositionReport:
    dataset, source_path = _coerce_dataset(dataset_or_path)
    traded_rows = [row for row in dataset.rows if row.traded]
    by_setup_type = {
        group_id: _traded_group_metrics(group_id, group_rows)
        for group_id, group_rows in _group_traded_rows(
            traded_rows,
            lambda row: row.pattern_type or "pattern_missing",
        ).items()
    }
    by_exit_reason = {
        group_id: _traded_group_metrics(group_id, group_rows)
        for group_id, group_rows in _group_traded_rows(
            traded_rows,
            lambda row: row.exit_reason or "exit_reason_missing",
        ).items()
    }
    by_bars_held_bucket = {
        group_id: _traded_group_metrics(group_id, group_rows)
        for group_id, group_rows in _group_traded_rows(
            traded_rows,
            lambda row: _bars_held_bucket(row.bars_held),
        ).items()
    }
    by_feature_bucket = {
        field: {
            bucket_id: _traded_group_metrics(bucket_id, bucket_rows)
            for bucket_id, bucket_rows in _group_traded_rows(
                traded_rows,
                lambda row, field=field: _feature_bucket_id(
                    field,
                    row.feature_snapshot.get(field),
                ),
            ).items()
        }
        for field in feature_bucket_fields
    }
    warnings: list[str] = []
    if not traded_rows:
        warnings.append("dataset contains no traded rows")
    if len(traded_rows) < 30:
        warnings.append("traded sample is small")

    overall = _traded_group_metrics("overall", traded_rows)
    return TradedLifecycleOutcomeDecompositionReport(
        report_id=report_id or f"traded_lifecycle_decomposition:{dataset.summary.panel_id}",
        generated_at=generated_at or datetime.now(UTC),
        status=ReviewStatus.WARN if warnings else ReviewStatus.PASS,
        source_dataset_path=source_path,
        trade_count=len(traded_rows),
        overall=overall,
        by_setup_type=by_setup_type,
        by_exit_reason=by_exit_reason,
        by_bars_held_bucket=by_bars_held_bucket,
        by_feature_bucket=by_feature_bucket,
        conclusion=_traded_lifecycle_conclusion(overall),
        warnings=tuple(warnings),
    )


def write_traded_lifecycle_decomposition_report(
    report: TradedLifecycleOutcomeDecompositionReport,
    output_dir: str | Path,
) -> dict[str, str]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "traded_lifecycle_decomposition_report.json"
    markdown_path = destination / "traded_lifecycle_decomposition_report.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(
        _render_traded_lifecycle_markdown(report),
        encoding="utf-8",
    )
    return {"report": str(json_path), "summary_markdown": str(markdown_path)}


def build_exit_path_diagnostic_report(
    dataset_or_path: FeatureOutcomeAttributionDataset | str | Path,
    *,
    report_id: str | None = None,
    manifest_path: str | Path | None = None,
    benchmark_symbol: str | None = None,
    forward_windows: Sequence[int] = DEFAULT_FORWARD_WINDOWS,
    generated_at: datetime | None = None,
) -> ExitPathDiagnosticReport:
    dataset, source_path = _coerce_dataset(dataset_or_path)
    resolved_manifest_path = Path(manifest_path or dataset.summary.source_manifest_path)
    resolved_benchmark_symbol = benchmark_symbol or dataset.summary.benchmark_symbol
    prices = _price_index(resolved_manifest_path)
    traded_rows = [row for row in dataset.rows if row.traded]
    diagnostics = tuple(
        _exit_path_trade_diagnostic(
            row,
            prices=prices,
            benchmark_symbol=resolved_benchmark_symbol,
            forward_windows=forward_windows,
        )
        for row in traded_rows
    )
    exit_reason_counts: dict[str, int] = {}
    flag_counts: dict[str, int] = {}
    for diagnostic in diagnostics:
        reason = diagnostic.exit_reason or "exit_reason_missing"
        exit_reason_counts[reason] = exit_reason_counts.get(reason, 0) + 1
        for flag in diagnostic.diagnostic_flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
    warnings: list[str] = []
    if not diagnostics:
        warnings.append("dataset contains no traded rows")
    if len(diagnostics) < 30:
        warnings.append("exit diagnostic sample is small")

    return ExitPathDiagnosticReport(
        report_id=report_id or f"exit_path_diagnostic:{dataset.summary.panel_id}",
        generated_at=generated_at or datetime.now(UTC),
        status=ReviewStatus.WARN if warnings else ReviewStatus.PASS,
        source_dataset_path=source_path,
        source_manifest_path=str(resolved_manifest_path),
        benchmark_symbol=resolved_benchmark_symbol,
        trade_count=len(diagnostics),
        winner_count=sum(1 for diagnostic in diagnostics if diagnostic.winner),
        loser_count=sum(1 for diagnostic in diagnostics if not diagnostic.winner),
        exit_reason_counts=exit_reason_counts,
        diagnostic_flag_counts=flag_counts,
        trades=diagnostics,
        conclusion=_exit_path_conclusion(flag_counts, trade_count=len(diagnostics)),
        warnings=tuple(warnings),
    )


def write_exit_path_diagnostic_report(
    report: ExitPathDiagnosticReport,
    output_dir: str | Path,
) -> dict[str, str]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "exit_path_diagnostic_report.json"
    markdown_path = destination / "exit_path_diagnostic_report.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_exit_path_markdown(report), encoding="utf-8")
    return {"report": str(json_path), "summary_markdown": str(markdown_path)}


def build_pattern_specific_benchmark_diagnostic_report(
    dataset_or_path: FeatureOutcomeAttributionDataset | str | Path,
    *,
    report_id: str | None = None,
    generated_at: datetime | None = None,
) -> PatternSpecificBenchmarkDiagnosticReport:
    dataset, source_path = _coerce_dataset(dataset_or_path)
    rows = list(dataset.rows)
    patterns = {
        pattern_type: _pattern_specific_diagnostic(pattern_type, pattern_rows)
        for pattern_type, pattern_rows in _rows_by_pattern_type(rows).items()
    }
    warnings: list[str] = []
    if not patterns:
        warnings.append("dataset contains no pattern evidence")
    if any(pattern.sample_grade != "ROBUST" for pattern in patterns.values()):
        warnings.append("one or more pattern samples are below robust threshold")
    if dataset.summary.warnings:
        warnings.extend(dataset.summary.warnings)

    return PatternSpecificBenchmarkDiagnosticReport(
        report_id=report_id or f"pattern_specific_benchmark_diagnostic:{dataset.summary.panel_id}",
        generated_at=generated_at or datetime.now(UTC),
        status=ReviewStatus.WARN if warnings else ReviewStatus.PASS,
        source_dataset_path=source_path,
        benchmark_symbol=dataset.summary.benchmark_symbol,
        row_count=len(rows),
        pattern_count=len(patterns),
        sample_guardrails={
            "min_robust_accepted_rows": MIN_ROBUST_ACCEPTED_ROWS,
            "min_robust_traded_rows": MIN_ROBUST_TRADED_ROWS,
            "min_exploratory_accepted_rows": MIN_EXPLORATORY_ACCEPTED_ROWS,
            "min_exploratory_traded_rows": MIN_EXPLORATORY_TRADED_ROWS,
        },
        patterns=patterns,
        conclusion=_pattern_specific_report_conclusion(patterns),
        warnings=tuple(warnings),
    )


def write_pattern_specific_benchmark_diagnostic_report(
    report: PatternSpecificBenchmarkDiagnosticReport,
    output_dir: str | Path,
) -> dict[str, str]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "pattern_specific_benchmark_diagnostic_report.json"
    markdown_path = destination / "pattern_specific_benchmark_diagnostic_report.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(
        _render_pattern_specific_benchmark_markdown(report),
        encoding="utf-8",
    )
    return {"report": str(json_path), "summary_markdown": str(markdown_path)}


def _load_scanner_material_rows(path: Path) -> list[dict[str, Any]]:
    payload = _load_json_object(path)
    if "rows" in payload and isinstance(payload["rows"], list):
        return [dict(row) for row in payload["rows"] if isinstance(row, Mapping)]
    if "sessions" in payload and isinstance(payload["sessions"], list):
        rows: list[dict[str, Any]] = []
        for session in payload["sessions"]:
            if not isinstance(session, Mapping):
                continue
            rows.extend(
                dict(row)
                for row in session.get("material_decision_rows", [])
                if isinstance(row, Mapping)
            )
        return rows
    raise ValueError(f"unsupported scanner material decisions payload shape at {path}")


def _coerce_dataset(
    dataset_or_path: FeatureOutcomeAttributionDataset | str | Path,
) -> tuple[FeatureOutcomeAttributionDataset, str]:
    if isinstance(dataset_or_path, FeatureOutcomeAttributionDataset):
        return dataset_or_path, dataset_or_path.summary.source_scanner_material_decisions_path
    path = Path(dataset_or_path)
    payload = _load_json_object(path)
    return FeatureOutcomeAttributionDataset.model_validate(payload), str(path)


def _load_trade_ledger_rows(path: Path) -> list[dict[str, Any]]:
    payload = _load_json_object(path)
    if "trades" in payload and isinstance(payload["trades"], list):
        return [dict(row) for row in payload["trades"] if isinstance(row, Mapping)]
    if isinstance(payload, list):
        return [dict(row) for row in payload if isinstance(row, Mapping)]
    raise ValueError(f"unsupported lifecycle trade ledger payload shape at {path}")


def _load_feature_snapshots(
    path: Path | None,
    *,
    fields: Sequence[str],
) -> tuple[dict[tuple[str, date], dict[str, Any]], tuple[str, ...]]:
    if path is None:
        return {}, ()

    frame = _read_feature_snapshot_frame(path)
    required = {"symbol", "session_date"}
    missing_required = required - set(frame.columns)
    if missing_required:
        missing = ", ".join(sorted(missing_required))
        raise ValueError(f"feature snapshot source is missing required columns: {missing}")

    missing_fields = tuple(field for field in fields if field not in frame.columns)
    available_fields = tuple(field for field in fields if field in frame.columns)
    prepared = frame.copy()
    prepared["session_date"] = pd.to_datetime(prepared["session_date"], errors="raise").dt.date

    index: dict[tuple[str, date], dict[str, Any]] = {}
    for row in prepared.itertuples(index=False):
        payload = {field: _jsonable(getattr(row, field)) for field in available_fields}
        index[(str(row.symbol), row.session_date)] = payload

    warnings = (
        (f"feature snapshot source missing requested fields: {', '.join(missing_fields)}",)
        if missing_fields
        else ()
    )
    return index, warnings


def _read_feature_snapshot_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported feature snapshot source format: {path.suffix}")


def _load_json_object(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _trades_by_setup_id(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    trades: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        setup_id = _optional_str(row.get("setup_id"))
        if not setup_id:
            continue
        existing = trades.get(setup_id)
        if existing is None or _optional_date(row.get("exit_fill_date")) is not None:
            trades[setup_id] = row
    return trades


def _price_index(manifest_path: Path) -> dict[str, list[tuple[date, float]]]:
    panel = load_historical_panel_data(manifest_path)
    source = panel.features if panel.features is not None else panel.ohlcv
    price_column = "split_adj_close" if "split_adj_close" in source.columns else "raw_close"
    frame = source[["symbol", "session_date", price_column]].copy()
    frame["session_date"] = pd.to_datetime(frame["session_date"], errors="raise").dt.date
    frame[price_column] = pd.to_numeric(frame[price_column], errors="raise")
    index: dict[str, list[tuple[date, float]]] = {}
    for symbol, group in frame.sort_values(["symbol", "session_date"]).groupby("symbol"):
        index[str(symbol)] = [
            (row.session_date, float(getattr(row, price_column)))
            for row in group.itertuples(index=False)
        ]
    return index


def _forward_close_returns(
    prices: Mapping[str, Sequence[tuple[date, float]]],
    *,
    symbol: str,
    start_session: date | None,
    windows: Sequence[int],
) -> dict[str, float | None]:
    result = {str(int(window)): None for window in windows}
    if start_session is None:
        return result
    symbol_prices = list(prices.get(symbol, ()))
    date_to_index = {session: index for index, (session, _) in enumerate(symbol_prices)}
    start_index = date_to_index.get(start_session)
    if start_index is None:
        return result
    start_price = symbol_prices[start_index][1]
    if start_price <= 0.0:
        return result
    for window in windows:
        target_index = start_index + int(window)
        if target_index >= len(symbol_prices):
            continue
        result[str(int(window))] = symbol_prices[target_index][1] / start_price - 1.0
    return result


def _rejection_reasons(row: Mapping[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    for field in (
        "candidate_rejection_reasons",
        "signal_rejection_reasons",
        "risk_rejection_reasons",
        "order_rejection_reasons",
    ):
        reasons.extend(str(value) for value in row.get(field, ()) if value is not None)
    if not reasons and row.get("decision") == "REJECTED":
        reasons.extend(str(value) for value in row.get("reason_codes", ()) if value is not None)
    return tuple(reasons)


def _dataset_panel_id(
    scanner_rows: Sequence[Mapping[str, Any]],
    rows: Sequence[FeatureOutcomeAttributionRow],
) -> str:
    if scanner_rows:
        value = scanner_rows[0].get("panel_id")
        if value:
            return str(value)
    if rows:
        return rows[0].panel_id
    return "UNKNOWN"


def _write_rows_csv(dataset: FeatureOutcomeAttributionDataset, path: Path) -> None:
    windows = tuple(str(window) for window in dataset.summary.forward_windows)
    fieldnames = [
        "panel_id",
        "symbol",
        "signal_session",
        "next_session",
        "candidate_id",
        "setup_id",
        "decision",
        "pattern_type",
        "candidate_score_pct",
        "rank",
        "reason_codes",
        "rejection_reasons",
        "traded",
        "trade_id",
        "entry_fill_date",
        "exit_fill_date",
        "exit_reason",
        "bars_held",
        "net_pnl",
        "net_return",
    ]
    fieldnames.extend(f"forward_close_return_{window}d" for window in windows)
    fieldnames.extend(f"benchmark_forward_close_return_{window}d" for window in windows)
    fieldnames.extend(f"forward_close_excess_return_{window}d" for window in windows)
    feature_fields = tuple(dataset.summary.feature_snapshot_fields)
    fieldnames.extend(f"feature_{field}" for field in feature_fields)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in dataset.rows:
            payload = row.model_dump(mode="json")
            payload["reason_codes"] = "|".join(row.reason_codes)
            payload["rejection_reasons"] = "|".join(row.rejection_reasons)
            for window in windows:
                payload[f"forward_close_return_{window}d"] = row.forward_close_returns.get(
                    window
                )
                payload[f"benchmark_forward_close_return_{window}d"] = (
                    row.benchmark_forward_close_returns.get(window)
                )
                payload[f"forward_close_excess_return_{window}d"] = (
                    row.forward_close_excess_returns.get(window)
                )
            payload.pop("forward_close_returns", None)
            payload.pop("benchmark_forward_close_returns", None)
            payload.pop("forward_close_excess_returns", None)
            for field in feature_fields:
                payload[f"feature_{field}"] = row.feature_snapshot.get(field)
            payload.pop("feature_snapshot", None)
            writer.writerow({field: payload.get(field) for field in fieldnames})


def _render_markdown(dataset: FeatureOutcomeAttributionDataset) -> str:
    summary = dataset.summary
    lines = [
        "# Feature Outcome Attribution Dataset",
        "",
        f"Panel: `{summary.panel_id}`",
        "",
        f"Rows: {summary.row_count}",
        "",
        f"Accepted: {summary.accepted_count}",
        "",
        f"Rejected: {summary.rejected_count}",
        "",
        f"Traded: {summary.traded_count}",
        "",
        f"Benchmark symbol: `{summary.benchmark_symbol}`",
        "",
        f"Forward windows: `{', '.join(str(window) for window in summary.forward_windows)}`",
        "",
        "## Sources",
        "",
        f"- Scanner material decisions: `{summary.source_scanner_material_decisions_path}`",
        f"- Lifecycle trade ledger: `{summary.source_lifecycle_trade_ledger_path}`",
        f"- Historical manifest: `{summary.source_manifest_path}`",
        f"- Feature snapshot source: `{summary.source_feature_snapshot_path}`",
        "",
        "## Warnings",
        "",
    ]
    if summary.warnings:
        lines.extend(f"- {warning}" for warning in summary.warnings)
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def _bucket_metrics(
    bucket_id: str,
    rows: Sequence[FeatureOutcomeAttributionRow],
) -> FeatureOutcomeBucketMetrics:
    accepted_rows = [row for row in rows if row.decision != "REJECTED"]
    traded_rows = [row for row in rows if row.traded]
    sample_grade, sample_warnings = _sample_grade_and_warnings(
        accepted_count=len(accepted_rows),
        traded_count=len(traded_rows),
    )
    windows = sorted(
        {
            window
            for row in rows
            for window in row.forward_close_returns
        },
        key=lambda value: int(value),
    )
    average_returns: dict[str, float | None] = {}
    median_returns: dict[str, float | None] = {}
    positive_rates: dict[str, float | None] = {}
    average_excess_returns: dict[str, float | None] = {}
    median_excess_returns: dict[str, float | None] = {}
    positive_excess_rates: dict[str, float | None] = {}

    for window in windows:
        values = [
            value
            for row in rows
            if (value := row.forward_close_returns.get(window)) is not None
        ]
        average_returns[window] = sum(values) / len(values) if values else None
        median_returns[window] = median(values) if values else None
        positive_rates[window] = (
            sum(1 for value in values if value > 0.0) / len(values) if values else None
        )
        excess_values = [
            value
            for row in rows
            if (value := row.forward_close_excess_returns.get(window)) is not None
        ]
        average_excess_returns[window] = (
            sum(excess_values) / len(excess_values) if excess_values else None
        )
        median_excess_returns[window] = median(excess_values) if excess_values else None
        positive_excess_rates[window] = (
            sum(1 for value in excess_values if value > 0.0) / len(excess_values)
            if excess_values
            else None
        )

    return FeatureOutcomeBucketMetrics(
        bucket_id=bucket_id,
        row_count=len(rows),
        accepted_count=sum(1 for row in rows if row.decision != "REJECTED"),
        rejected_count=sum(1 for row in rows if row.decision == "REJECTED"),
        traded_count=sum(1 for row in rows if row.traded),
        sample_grade=sample_grade,
        sample_warnings=sample_warnings,
        average_forward_returns=average_returns,
        median_forward_returns=median_returns,
        positive_forward_return_rates=positive_rates,
        average_forward_excess_returns=average_excess_returns,
        median_forward_excess_returns=median_excess_returns,
        positive_forward_excess_return_rates=positive_excess_rates,
        accepted_only=_subset_metrics(accepted_rows),
        traded_only=_subset_metrics(traded_rows),
    )


def _sample_grade_and_warnings(
    *,
    accepted_count: int,
    traded_count: int,
) -> tuple[str, tuple[str, ...]]:
    warnings: list[str] = []
    if accepted_count < MIN_EXPLORATORY_ACCEPTED_ROWS:
        warnings.append("accepted sample below exploratory threshold")
    if traded_count < MIN_EXPLORATORY_TRADED_ROWS:
        warnings.append("traded sample below exploratory threshold")

    if accepted_count >= MIN_ROBUST_ACCEPTED_ROWS and traded_count >= MIN_ROBUST_TRADED_ROWS:
        return "ROBUST", tuple(warnings)
    if (
        accepted_count >= MIN_EXPLORATORY_ACCEPTED_ROWS
        or traded_count >= MIN_EXPLORATORY_TRADED_ROWS
    ):
        return "EXPLORATORY", tuple(warnings)
    return "INSUFFICIENT", tuple(warnings)


def _subset_metrics(
    rows: Sequence[FeatureOutcomeAttributionRow],
) -> FeatureOutcomeSubsetMetrics:
    windows = sorted(
        {
            window
            for row in rows
            for window in row.forward_close_returns
        },
        key=lambda value: int(value),
    )
    average_returns: dict[str, float | None] = {}
    median_returns: dict[str, float | None] = {}
    positive_rates: dict[str, float | None] = {}
    average_excess_returns: dict[str, float | None] = {}
    median_excess_returns: dict[str, float | None] = {}
    positive_excess_rates: dict[str, float | None] = {}

    for window in windows:
        values = [
            value
            for row in rows
            if (value := row.forward_close_returns.get(window)) is not None
        ]
        average_returns[window] = sum(values) / len(values) if values else None
        median_returns[window] = median(values) if values else None
        positive_rates[window] = (
            sum(1 for value in values if value > 0.0) / len(values) if values else None
        )
        excess_values = [
            value
            for row in rows
            if (value := row.forward_close_excess_returns.get(window)) is not None
        ]
        average_excess_returns[window] = (
            sum(excess_values) / len(excess_values) if excess_values else None
        )
        median_excess_returns[window] = median(excess_values) if excess_values else None
        positive_excess_rates[window] = (
            sum(1 for value in excess_values if value > 0.0) / len(excess_values)
            if excess_values
            else None
        )

    trade_rows = [row for row in rows if row.traded]
    net_pnls = [row.net_pnl for row in trade_rows if row.net_pnl is not None]
    net_returns = [row.net_return for row in trade_rows if row.net_return is not None]
    winning = sum(1 for value in net_pnls if value > 0.0)
    losing = sum(1 for value in net_pnls if value < 0.0)

    return FeatureOutcomeSubsetMetrics(
        row_count=len(rows),
        average_forward_returns=average_returns,
        median_forward_returns=median_returns,
        positive_forward_return_rates=positive_rates,
        average_forward_excess_returns=average_excess_returns,
        median_forward_excess_returns=median_excess_returns,
        positive_forward_excess_return_rates=positive_excess_rates,
        trade_count=len(trade_rows),
        winning_trade_count=winning,
        losing_trade_count=losing,
        trade_win_rate=winning / len(net_pnls) if net_pnls else None,
        net_pnl=sum(net_pnls) if net_pnls else None,
        average_net_pnl=sum(net_pnls) / len(net_pnls) if net_pnls else None,
        average_net_return=sum(net_returns) / len(net_returns) if net_returns else None,
        median_net_return=median(net_returns) if net_returns else None,
    )


def _rows_by_score_bucket(
    rows: Sequence[FeatureOutcomeAttributionRow],
) -> dict[str, list[FeatureOutcomeAttributionRow]]:
    buckets: dict[str, list[FeatureOutcomeAttributionRow]] = {
        "score_missing": [],
        "score_000_025": [],
        "score_025_050": [],
        "score_050_075": [],
        "score_075_090": [],
        "score_090_100": [],
    }
    for row in rows:
        score = row.candidate_score_pct
        if score is None:
            buckets["score_missing"].append(row)
        elif score < 0.25:
            buckets["score_000_025"].append(row)
        elif score < 0.50:
            buckets["score_025_050"].append(row)
        elif score < 0.75:
            buckets["score_050_075"].append(row)
        elif score < 0.90:
            buckets["score_075_090"].append(row)
        else:
            buckets["score_090_100"].append(row)
    return buckets


def _rows_by_rejection_reason(
    rows: Sequence[FeatureOutcomeAttributionRow],
) -> dict[str, list[FeatureOutcomeAttributionRow]]:
    buckets: dict[str, list[FeatureOutcomeAttributionRow]] = {}
    for row in rows:
        for reason in row.reason_codes or row.rejection_reasons:
            buckets.setdefault(reason, []).append(row)
    return dict(sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0])))


def _rows_by_feature_bucket(
    rows: Sequence[FeatureOutcomeAttributionRow],
    field: str,
) -> dict[str, list[FeatureOutcomeAttributionRow]]:
    buckets: dict[str, list[FeatureOutcomeAttributionRow]] = {}
    for row in rows:
        bucket_id = _feature_bucket_id(field, row.feature_snapshot.get(field))
        buckets.setdefault(bucket_id, []).append(row)
    return dict(sorted(buckets.items(), key=lambda item: item[0]))


def _rows_by_pattern_type(
    rows: Sequence[FeatureOutcomeAttributionRow],
) -> dict[str, list[FeatureOutcomeAttributionRow]]:
    buckets: dict[str, list[FeatureOutcomeAttributionRow]] = {}
    for row in rows:
        pattern_type = row.pattern_type or "pattern_missing"
        buckets.setdefault(pattern_type, []).append(row)
    return dict(sorted(buckets.items(), key=lambda item: item[0]))


def _feature_bucket_id(field: str, value: Any) -> str:
    if value in (None, ""):
        return f"{field}:missing"
    if isinstance(value, str):
        return f"{field}:{value}"
    numeric = float(value)
    if numeric < 0.0:
        return f"{field}:lt_0"
    if numeric < 0.02:
        return f"{field}:0_to_2pct"
    if numeric < 0.05:
        return f"{field}:2_to_5pct"
    return f"{field}:gte_5pct"


def _feature_bucket_conclusion(
    by_feature_bucket: Mapping[str, Mapping[str, FeatureOutcomeBucketMetrics]],
) -> str:
    best: FeatureOutcomeBucketMetrics | None = None
    for buckets in by_feature_bucket.values():
        for metrics in buckets.values():
            if metrics.accepted_count < 5:
                continue
            avg_excess = metrics.average_forward_excess_returns.get("20")
            if avg_excess is None:
                continue
            if best is None or avg_excess > (best.average_forward_excess_returns.get("20") or 0.0):
                best = metrics
    if best is None:
        return "INSUFFICIENT_BUCKET_EVIDENCE"
    if (best.average_forward_excess_returns.get("20") or 0.0) > 0.0:
        return "POTENTIAL_POSITIVE_EXCESS_BUCKET_REQUIRES_SELECTION_PACKET"
    return "NO_POSITIVE_20D_EXCESS_BUCKET_FOUND"


def _distribution_by_window(
    population_id: str,
    rows: Sequence[FeatureOutcomeAttributionRow],
    windows: Sequence[int],
) -> dict[str, FeatureOutcomeDistributionMetrics]:
    return {
        str(int(window)): _distribution_metrics(population_id, rows, int(window))
        for window in windows
    }


def _distribution_metrics(
    population_id: str,
    rows: Sequence[FeatureOutcomeAttributionRow],
    window: int,
) -> FeatureOutcomeDistributionMetrics:
    values = [
        value
        for row in rows
        if (value := row.forward_close_excess_returns.get(str(window))) is not None
    ]
    if not values:
        return FeatureOutcomeDistributionMetrics(
            population_id=population_id,
            window=window,
            row_count=len(rows),
            observed_count=0,
        )
    series = pd.Series(values, dtype=float)
    return FeatureOutcomeDistributionMetrics(
        population_id=population_id,
        window=window,
        row_count=len(rows),
        observed_count=len(values),
        mean=float(series.mean()),
        median=float(series.median()),
        p10=float(series.quantile(0.10)),
        p25=float(series.quantile(0.25)),
        p75=float(series.quantile(0.75)),
        p90=float(series.quantile(0.90)),
        minimum=float(series.min()),
        maximum=float(series.max()),
        positive_rate=float((series > 0.0).mean()),
    )


def _distribution_conclusion(
    populations: Mapping[str, Mapping[str, FeatureOutcomeDistributionMetrics]],
) -> str:
    accepted_20 = populations.get("accepted", {}).get("20")
    near_miss_20 = populations.get("near_miss", {}).get("20")
    if accepted_20 is None or near_miss_20 is None:
        return "INSUFFICIENT_20D_DISTRIBUTION_EVIDENCE"
    if accepted_20.mean is None or near_miss_20.mean is None:
        return "INSUFFICIENT_20D_DISTRIBUTION_EVIDENCE"
    if accepted_20.mean > 0.0 and accepted_20.mean > near_miss_20.mean:
        return "ACCEPTED_DISTRIBUTION_SHOWS_20D_EXCESS_EDGE"
    return "NO_ACCEPTED_DISTRIBUTIONAL_20D_EXCESS_EDGE"


def _group_traded_rows(
    rows: Sequence[FeatureOutcomeAttributionRow],
    key_fn: Any,
) -> dict[str, list[FeatureOutcomeAttributionRow]]:
    groups: dict[str, list[FeatureOutcomeAttributionRow]] = {}
    for row in rows:
        groups.setdefault(str(key_fn(row)), []).append(row)
    return dict(sorted(groups.items(), key=lambda item: item[0]))


def _traded_group_metrics(
    group_id: str,
    rows: Sequence[FeatureOutcomeAttributionRow],
) -> TradedLifecycleGroupMetrics:
    net_pnls = [row.net_pnl for row in rows if row.net_pnl is not None]
    net_returns = [row.net_return for row in rows if row.net_return is not None]
    bars_held = [row.bars_held for row in rows if row.bars_held is not None]
    winning = sum(1 for value in net_pnls if value > 0.0)
    losing = sum(1 for value in net_pnls if value < 0.0)
    windows = sorted(
        {
            window
            for row in rows
            for window in row.forward_close_excess_returns
        },
        key=lambda value: int(value),
    )
    average_excess_returns: dict[str, float | None] = {}
    positive_excess_rates: dict[str, float | None] = {}
    for window in windows:
        values = [
            value
            for row in rows
            if (value := row.forward_close_excess_returns.get(window)) is not None
        ]
        average_excess_returns[window] = sum(values) / len(values) if values else None
        positive_excess_rates[window] = (
            sum(1 for value in values if value > 0.0) / len(values) if values else None
        )

    exit_reason_counts: dict[str, int] = {}
    for row in rows:
        reason = row.exit_reason or "exit_reason_missing"
        exit_reason_counts[reason] = exit_reason_counts.get(reason, 0) + 1

    return TradedLifecycleGroupMetrics(
        group_id=group_id,
        trade_count=len(rows),
        symbol_count=len({row.symbol for row in rows}),
        setup_count=len({row.setup_id for row in rows if row.setup_id}),
        winning_trade_count=winning,
        losing_trade_count=losing,
        win_rate=winning / len(net_pnls) if net_pnls else None,
        net_pnl=sum(net_pnls) if net_pnls else 0.0,
        average_net_pnl=sum(net_pnls) / len(net_pnls) if net_pnls else None,
        average_net_return=sum(net_returns) / len(net_returns) if net_returns else None,
        median_net_return=median(net_returns) if net_returns else None,
        average_bars_held=sum(bars_held) / len(bars_held) if bars_held else None,
        exit_reason_counts=exit_reason_counts,
        average_forward_excess_returns=average_excess_returns,
        positive_forward_excess_return_rates=positive_excess_rates,
    )


def _bars_held_bucket(bars_held: int | None) -> str:
    if bars_held is None:
        return "bars_held:missing"
    if bars_held <= 3:
        return "bars_held:001_003"
    if bars_held <= 7:
        return "bars_held:004_007"
    if bars_held <= 14:
        return "bars_held:008_014"
    return "bars_held:015_plus"


def _traded_lifecycle_conclusion(overall: TradedLifecycleGroupMetrics) -> str:
    if overall.trade_count == 0:
        return "NO_TRADED_LIFECYCLE_EVIDENCE"
    if overall.net_pnl > 0.0 and (overall.average_net_return or 0.0) > 0.0:
        return "TRADED_LIFECYCLE_POSITIVE_BUT_SAMPLE_LIMITED"
    return "TRADED_LIFECYCLE_DOES_NOT_PROVE_EDGE"


def _pattern_specific_diagnostic(
    pattern_type: str,
    rows: Sequence[FeatureOutcomeAttributionRow],
) -> PatternSpecificBenchmarkDiagnostic:
    accepted_rows = [row for row in rows if row.decision != "REJECTED"]
    rejected_rows = [row for row in rows if row.decision == "REJECTED"]
    traded_rows = [row for row in rows if row.traded]
    all_rows = _bucket_metrics(f"pattern:{pattern_type}", rows)
    accepted_only = _subset_metrics(accepted_rows)
    rejected_only = _subset_metrics(rejected_rows)
    traded_lifecycle = _traded_group_metrics(pattern_type, traded_rows)
    warnings = list(all_rows.sample_warnings)
    accepted_excess_20d = accepted_only.average_forward_excess_returns.get("20")
    if accepted_excess_20d is None:
        warnings.append("accepted 20d benchmark-relative evidence is missing")
    elif accepted_excess_20d <= 0.0:
        warnings.append("accepted 20d benchmark-relative evidence is not positive")
    if traded_rows and traded_lifecycle.net_pnl <= 0.0:
        warnings.append("traded lifecycle net PnL is not positive")

    return PatternSpecificBenchmarkDiagnostic(
        pattern_type=pattern_type,
        row_count=len(rows),
        accepted_count=len(accepted_rows),
        rejected_count=len(rejected_rows),
        traded_count=len(traded_rows),
        sample_grade=all_rows.sample_grade,
        sample_warnings=all_rows.sample_warnings,
        all_rows=all_rows,
        accepted_only=accepted_only,
        rejected_only=rejected_only,
        traded_lifecycle=traded_lifecycle,
        exit_reason_counts=traded_lifecycle.exit_reason_counts,
        recommendation=_pattern_recommendation(
            sample_grade=all_rows.sample_grade,
            accepted_excess_20d=accepted_excess_20d,
            traded_lifecycle=traded_lifecycle,
        ),
        warnings=tuple(warnings),
    )


def _pattern_recommendation(
    *,
    sample_grade: str,
    accepted_excess_20d: float | None,
    traded_lifecycle: TradedLifecycleGroupMetrics,
) -> str:
    if sample_grade == "INSUFFICIENT":
        return "INSUFFICIENT_SAMPLE_FOR_PATTERN_DECISION"
    if accepted_excess_20d is None:
        return "INSUFFICIENT_20D_EXCESS_EVIDENCE"
    lifecycle_positive = (
        traded_lifecycle.trade_count > 0
        and traded_lifecycle.net_pnl > 0.0
        and (traded_lifecycle.average_net_return or 0.0) > 0.0
    )
    if accepted_excess_20d > 0.0 and lifecycle_positive:
        return "PATTERN_ELIGIBLE_FOR_DEEPER_RESEARCH_NOT_PAPER"
    if accepted_excess_20d <= 0.0 and not lifecycle_positive:
        return "PATTERN_SHOULD_BE_ISOLATED_OR_REDESIGNED"
    return "MIXED_PATTERN_EVIDENCE_REQUIRES_DEEPER_RESEARCH"


def _pattern_specific_report_conclusion(
    patterns: Mapping[str, PatternSpecificBenchmarkDiagnostic],
) -> str:
    if not patterns:
        return "NO_PATTERN_LEVEL_EVIDENCE"
    recommendations = {pattern.recommendation for pattern in patterns.values()}
    if "PATTERN_ELIGIBLE_FOR_DEEPER_RESEARCH_NOT_PAPER" in recommendations:
        return "PATTERN_LEVEL_HYPOTHESIS_EXISTS_FOR_DEEPER_RESEARCH_ONLY"
    if recommendations == {"PATTERN_SHOULD_BE_ISOLATED_OR_REDESIGNED"}:
        return "ALL_PATTERNS_WEAK_OR_NEGATIVE"
    if recommendations == {"INSUFFICIENT_SAMPLE_FOR_PATTERN_DECISION"}:
        return "PATTERN_LEVEL_EVIDENCE_SAMPLE_LIMITED"
    return "MIXED_OR_INSUFFICIENT_PATTERN_LEVEL_EVIDENCE"


def _exit_path_trade_diagnostic(
    row: FeatureOutcomeAttributionRow,
    *,
    prices: Mapping[str, Sequence[tuple[date, float]]],
    benchmark_symbol: str | None,
    forward_windows: Sequence[int],
) -> ExitPathTradeDiagnostic:
    exit_session = row.exit_fill_date
    post_exit_returns = _forward_close_returns(
        prices,
        symbol=row.symbol,
        start_session=exit_session,
        windows=forward_windows,
    )
    benchmark_returns = (
        {}
        if benchmark_symbol is None
        else _forward_close_returns(
            prices,
            symbol=benchmark_symbol,
            start_session=exit_session,
            windows=forward_windows,
        )
    )
    excess_returns = _excess_returns(post_exit_returns, benchmark_returns)
    flags = _exit_path_flags(row, excess_returns)
    return ExitPathTradeDiagnostic(
        trade_id=row.trade_id,
        symbol=row.symbol,
        setup_id=row.setup_id,
        pattern_type=row.pattern_type,
        exit_reason=row.exit_reason,
        bars_held=row.bars_held,
        net_pnl=row.net_pnl,
        net_return=row.net_return,
        winner=(row.net_pnl or 0.0) > 0.0,
        post_exit_forward_returns=post_exit_returns,
        post_exit_benchmark_returns=benchmark_returns,
        post_exit_excess_returns=excess_returns,
        diagnostic_flags=flags,
    )


def _exit_path_flags(
    row: FeatureOutcomeAttributionRow,
    excess_returns: Mapping[str, float | None],
) -> tuple[str, ...]:
    flags: list[str] = []
    net_pnl = row.net_pnl or 0.0
    winner = net_pnl > 0.0
    post_exit_5 = excess_returns.get("5")
    post_exit_10 = excess_returns.get("10")
    post_exit_20 = excess_returns.get("20")
    positive_after_exit = any(
        value is not None and value > 0.0 for value in (post_exit_5, post_exit_10, post_exit_20)
    )
    negative_after_exit = any(
        value is not None and value < 0.0 for value in (post_exit_5, post_exit_10, post_exit_20)
    )
    if winner and positive_after_exit:
        flags.append("winner_continued_after_exit")
    if winner and negative_after_exit:
        flags.append("winner_reversed_after_exit")
    if not winner and positive_after_exit:
        flags.append("loser_recovered_after_exit")
    if not winner and negative_after_exit:
        flags.append("loser_avoided_further_weakness")
    if row.exit_reason == "TIME_EXIT" and not winner:
        flags.append("time_exit_loss")
    if row.exit_reason == "INITIAL_STOP" and not winner:
        flags.append("initial_stop_loss")
    return tuple(flags)


def _exit_path_conclusion(
    flag_counts: Mapping[str, int],
    *,
    trade_count: int,
) -> str:
    if trade_count == 0:
        return "NO_EXIT_PATH_EVIDENCE"
    if flag_counts.get("loser_recovered_after_exit", 0) or flag_counts.get(
        "winner_continued_after_exit",
        0,
    ):
        return "EXIT_PATH_HYPOTHESES_REQUIRE_DEEPER_REPLAY"
    return "EXIT_PATH_DIAGNOSTIC_DOES_NOT_IDENTIFY_CLEAR_EXIT_EDGE"


def _accepted_vs_near_miss_conclusion(
    accepted: FeatureOutcomeBucketMetrics,
    near_miss: FeatureOutcomeBucketMetrics,
) -> str:
    accepted_20d = accepted.average_forward_returns.get("20")
    near_miss_20d = near_miss.average_forward_returns.get("20")
    accepted_excess_20d = accepted.average_forward_excess_returns.get("20")
    near_miss_excess_20d = near_miss.average_forward_excess_returns.get("20")
    if accepted_excess_20d is not None and near_miss_excess_20d is not None:
        if accepted_excess_20d > near_miss_excess_20d and accepted_excess_20d > 0.0:
            return "ACCEPTED_OUTPERFORMS_NEAR_MISS_ON_20D_EXCESS_RETURN"
        return "NO_CLEAR_ACCEPTED_EDGE_OVER_NEAR_MISS_ON_20D_EXCESS_RETURN"
    if accepted_20d is None or near_miss_20d is None:
        return "INSUFFICIENT_FORWARD_RETURN_EVIDENCE"
    if accepted_20d > near_miss_20d and accepted_20d > 0.0:
        return "ACCEPTED_OUTPERFORMS_NEAR_MISS_ON_20D_FORWARD_RETURN"
    return "NO_CLEAR_ACCEPTED_EDGE_OVER_NEAR_MISS_ON_20D_FORWARD_RETURN"


def _render_near_miss_markdown(report: AcceptedVersusNearMissReport) -> str:
    lines = [
        "# Accepted Versus Near-Miss Report",
        "",
        f"Report: `{report.report_id}`",
        "",
        f"Status: `{report.status.value}`",
        "",
        f"Rows: {report.row_count}",
        "",
        f"Near-miss definition: `{report.near_miss_definition}`",
        "",
        f"Conclusion: `{report.conclusion}`",
        "",
        "## Top-level buckets",
        "",
        "| Bucket | Rows | Accepted | Rejected | Traded | Avg 20d | "
        "Avg excess 20d | Positive excess 20d |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for metrics in (report.accepted, report.rejected, report.near_miss):
        lines.append(_metrics_markdown_row(metrics))
    lines.extend(["", "## Score buckets", ""])
    lines.extend(
        [
            "| Bucket | Rows | Accepted | Rejected | Traded | Avg 20d | "
            "Avg excess 20d | Positive excess 20d |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    lines.extend(_metrics_markdown_row(metrics) for metrics in report.by_score_bucket.values())
    lines.extend(["", "## Warnings", ""])
    if report.warnings:
        lines.extend(f"- {warning}" for warning in report.warnings)
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def _render_feature_bucket_markdown(report: FeatureSnapshotBucketReport) -> str:
    lines = [
        "# Feature Snapshot Bucket Report",
        "",
        f"Report: `{report.report_id}`",
        "",
        f"Status: `{report.status.value}`",
        "",
        f"Rows: {report.row_count}",
        "",
        f"Conclusion: `{report.conclusion}`",
        "",
    ]
    for field, buckets in report.by_feature_bucket.items():
        lines.extend(
            [
                f"## `{field}`",
                "",
                "| Bucket | Rows | Accepted | Rejected | Traded | Avg excess 20d | "
                "Accepted avg excess 20d | Accepted +excess 20d | Traded net PnL | "
                "Traded avg net return | Sample grade |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for metrics in buckets.values():
            lines.append(_feature_bucket_markdown_row(metrics))
        lines.append("")
    lines.extend(["## Warnings", ""])
    if report.warnings:
        lines.extend(f"- {warning}" for warning in report.warnings)
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def _render_distribution_markdown(
    report: AcceptedCandidateExcessDistributionReport,
) -> str:
    lines = [
        "# Accepted Candidate Excess-Return Distribution Report",
        "",
        f"Report: `{report.report_id}`",
        "",
        f"Status: `{report.status.value}`",
        "",
        f"Conclusion: `{report.conclusion}`",
        "",
        f"Near-miss definition: `{report.near_miss_definition}`",
        "",
        "| Population | Window | Rows | Observed | Mean | Median | P10 | P25 | "
        "P75 | P90 | Positive rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for population in report.populations.values():
        for metrics in population.values():
            lines.append(_distribution_markdown_row(metrics))
    lines.extend(["", "## Warnings", ""])
    if report.warnings:
        lines.extend(f"- {warning}" for warning in report.warnings)
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def _render_traded_lifecycle_markdown(
    report: TradedLifecycleOutcomeDecompositionReport,
) -> str:
    lines = [
        "# Traded Lifecycle Outcome Decomposition",
        "",
        f"Report: `{report.report_id}`",
        "",
        f"Status: `{report.status.value}`",
        "",
        f"Conclusion: `{report.conclusion}`",
        "",
        f"Trade count: {report.trade_count}",
        "",
        "## Overall",
        "",
        _traded_metrics_table((report.overall,)),
        "",
        "## By setup type",
        "",
        _traded_metrics_table(report.by_setup_type.values()),
        "",
        "## By exit reason",
        "",
        _traded_metrics_table(report.by_exit_reason.values()),
        "",
        "## By bars held",
        "",
        _traded_metrics_table(report.by_bars_held_bucket.values()),
        "",
        "## Warnings",
        "",
    ]
    if report.warnings:
        lines.extend(f"- {warning}" for warning in report.warnings)
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def _render_exit_path_markdown(report: ExitPathDiagnosticReport) -> str:
    lines = [
        "# Exit Path Diagnostic Report",
        "",
        f"Report: `{report.report_id}`",
        "",
        f"Status: `{report.status.value}`",
        "",
        f"Conclusion: `{report.conclusion}`",
        "",
        f"Trade count: {report.trade_count}",
        "",
        f"Winners: {report.winner_count}",
        "",
        f"Losers: {report.loser_count}",
        "",
        "## Exit reason counts",
        "",
    ]
    if report.exit_reason_counts:
        lines.extend(
            f"- `{reason}`: {count}"
            for reason, count in sorted(report.exit_reason_counts.items())
        )
    else:
        lines.append("- None.")
    lines.extend(["", "## Diagnostic flags", ""])
    if report.diagnostic_flag_counts:
        lines.extend(
            f"- `{flag}`: {count}"
            for flag, count in sorted(report.diagnostic_flag_counts.items())
        )
    else:
        lines.append("- None.")
    lines.extend(["", "## Warnings", ""])
    if report.warnings:
        lines.extend(f"- {warning}" for warning in report.warnings)
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def _render_pattern_specific_benchmark_markdown(
    report: PatternSpecificBenchmarkDiagnosticReport,
) -> str:
    lines = [
        "# Pattern-Specific Benchmark Diagnostic Report",
        "",
        f"Report: `{report.report_id}`",
        "",
        f"Status: `{report.status.value}`",
        "",
        f"Benchmark: `{report.benchmark_symbol}`",
        "",
        f"Conclusion: `{report.conclusion}`",
        "",
        f"Rows: {report.row_count}",
        "",
        "| Pattern | Rows | Accepted | Rejected | Traded | Sample | Accepted avg excess 20d | "
        "Accepted +excess 20d | Net PnL | Win rate | Recommendation |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for diagnostic in report.patterns.values():
        lines.append(_pattern_specific_markdown_row(diagnostic))
    lines.extend(["", "## Warnings", ""])
    if report.warnings:
        lines.extend(f"- {warning}" for warning in report.warnings)
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def _pattern_specific_markdown_row(
    diagnostic: PatternSpecificBenchmarkDiagnostic,
) -> str:
    accepted_avg_excess_20d = diagnostic.accepted_only.average_forward_excess_returns.get("20")
    accepted_positive_excess_20d = (
        diagnostic.accepted_only.positive_forward_excess_return_rates.get("20")
    )
    return (
        f"| `{diagnostic.pattern_type}` | {diagnostic.row_count} | "
        f"{diagnostic.accepted_count} | {diagnostic.rejected_count} | "
        f"{diagnostic.traded_count} | `{diagnostic.sample_grade}` | "
        f"{_fmt(accepted_avg_excess_20d)} | {_fmt(accepted_positive_excess_20d)} | "
        f"{diagnostic.traded_lifecycle.net_pnl:.2f} | "
        f"{_fmt(diagnostic.traded_lifecycle.win_rate)} | "
        f"`{diagnostic.recommendation}` |"
    )


def _traded_metrics_table(metrics: Sequence[TradedLifecycleGroupMetrics]) -> str:
    lines = [
        "| Group | Trades | Win rate | Net PnL | Avg net return | Median net return | "
        "Avg bars held | Avg excess 20d |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    lines.extend(_traded_metrics_row(metric) for metric in metrics)
    return "\n".join(lines)


def _traded_metrics_row(metrics: TradedLifecycleGroupMetrics) -> str:
    return (
        f"| `{metrics.group_id}` | {metrics.trade_count} | {_fmt(metrics.win_rate)} | "
        f"{metrics.net_pnl:.2f} | {_fmt(metrics.average_net_return)} | "
        f"{_fmt(metrics.median_net_return)} | {_fmt(metrics.average_bars_held)} | "
        f"{_fmt(metrics.average_forward_excess_returns.get('20'))} |"
    )


def _distribution_markdown_row(metrics: FeatureOutcomeDistributionMetrics) -> str:
    return (
        f"| `{metrics.population_id}` | {metrics.window} | {metrics.row_count} | "
        f"{metrics.observed_count} | {_fmt(metrics.mean)} | {_fmt(metrics.median)} | "
        f"{_fmt(metrics.p10)} | {_fmt(metrics.p25)} | {_fmt(metrics.p75)} | "
        f"{_fmt(metrics.p90)} | {_fmt(metrics.positive_rate)} |"
    )


def _fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.6f}"


def _feature_bucket_markdown_row(metrics: FeatureOutcomeBucketMetrics) -> str:
    avg_excess_20d = metrics.average_forward_excess_returns.get("20")
    accepted_avg_excess_20d = metrics.accepted_only.average_forward_excess_returns.get("20")
    accepted_positive_excess_20d = (
        metrics.accepted_only.positive_forward_excess_return_rates.get("20")
    )
    traded_net_pnl = metrics.traded_only.net_pnl
    traded_average_net_return = metrics.traded_only.average_net_return
    avg_excess_text = "" if avg_excess_20d is None else f"{avg_excess_20d:.6f}"
    accepted_avg_excess_text = (
        "" if accepted_avg_excess_20d is None else f"{accepted_avg_excess_20d:.6f}"
    )
    accepted_positive_text = (
        ""
        if accepted_positive_excess_20d is None
        else f"{accepted_positive_excess_20d:.3f}"
    )
    traded_net_pnl_text = "" if traded_net_pnl is None else f"{traded_net_pnl:.2f}"
    traded_average_net_return_text = (
        "" if traded_average_net_return is None else f"{traded_average_net_return:.6f}"
    )
    return (
        f"| `{metrics.bucket_id}` | {metrics.row_count} | {metrics.accepted_count} | "
        f"{metrics.rejected_count} | {metrics.traded_count} | {avg_excess_text} | "
        f"{accepted_avg_excess_text} | {accepted_positive_text} | {traded_net_pnl_text} | "
        f"{traded_average_net_return_text} | `{metrics.sample_grade}` |"
    )


def _metrics_markdown_row(metrics: FeatureOutcomeBucketMetrics) -> str:
    avg_20d = metrics.average_forward_returns.get("20")
    avg_excess_20d = metrics.average_forward_excess_returns.get("20")
    positive_excess_20d = metrics.positive_forward_excess_return_rates.get("20")
    avg_text = "" if avg_20d is None else f"{avg_20d:.6f}"
    avg_excess_text = "" if avg_excess_20d is None else f"{avg_excess_20d:.6f}"
    positive_excess_text = (
        "" if positive_excess_20d is None else f"{positive_excess_20d:.3f}"
    )
    return (
        f"| `{metrics.bucket_id}` | {metrics.row_count} | {metrics.accepted_count} | "
        f"{metrics.rejected_count} | {metrics.traded_count} | {avg_text} | "
        f"{avg_excess_text} | {positive_excess_text} |"
    )


def _excess_returns(
    candidate_returns: Mapping[str, float | None],
    benchmark_returns: Mapping[str, float | None],
) -> dict[str, float | None]:
    windows = sorted(set(candidate_returns) | set(benchmark_returns), key=lambda value: int(value))
    result: dict[str, float | None] = {}
    for window in windows:
        candidate_value = candidate_returns.get(window)
        benchmark_value = benchmark_returns.get(window)
        result[window] = (
            None
            if candidate_value is None or benchmark_value is None
            else candidate_value - benchmark_value
        )
    return result


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _optional_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return _parse_date(value)


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _jsonable(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value if item is not None)
