from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from pathlib import Path

from swingmachine.analytics import (
    paper_shadow_alignment_stats,
    paper_shadow_regime_stats,
    shadow_fill_regime_stats,
    shadow_fill_status_stats,
    summarize_paper_shadow_audit,
    summarize_shadow_fill_comparisons,
)
from swingmachine.contracts import (
    OperatorReviewCheck,
    OperatorReviewReport,
    OperatorReviewThresholds,
    PaperShadowAuditRecord,
    RollingAuditReport,
    RollingAuditWindow,
    RollingAuditWindowReport,
    ShadowFillComparison,
)
from swingmachine.enums import (
    PaperShadowAlignmentStatus,
    RegimeState,
    ReviewStatus,
    RuntimeEventType,
)
from swingmachine.paper_shadow_audit import PaperShadowAuditService
from swingmachine.run_history import RuntimeRunHistory
from swingmachine.shadow_reviews import ShadowReviewService

DEFAULT_REPORT_LOOKBACK_DAYS = (1, 5, 20)
DEFAULT_OPERATOR_REVIEW_THRESHOLDS = OperatorReviewThresholds()
REVIEW_REPORT_COMMAND = "run-review-report"
_ALIGNED_STATUSES = {
    PaperShadowAlignmentStatus.ALIGNED_FILLED,
    PaperShadowAlignmentStatus.ALIGNED_NOT_FILLED,
}
_DECISION_EVENT_TYPES = {
    RuntimeEventType.PENDING_ENTRY_ACTION_DECIDED.value,
    RuntimeEventType.PAPER_ENTRY_SUBMISSION_DECIDED.value,
    RuntimeEventType.SHADOW_ENTRY_PROPOSAL_DECIDED.value,
    RuntimeEventType.SHADOW_FILL_COMPARISON_RECORDED.value,
}


def _normalize_lookback_days(lookback_days: Sequence[int]) -> tuple[int, ...]:
    normalized = sorted({int(days) for days in lookback_days if int(days) > 0})
    if not normalized:
        raise ValueError("lookback_days must contain at least one positive integer")
    return tuple(normalized)


def _window_start(as_of_date: date, lookback_days: int) -> date:
    return as_of_date - timedelta(days=lookback_days - 1)


def _record_anchor_date(record: PaperShadowAuditRecord) -> date | None:
    if record.source_as_of is not None:
        return record.source_as_of.date()
    if record.created_at is not None:
        return record.created_at.date()
    return record.shadow_session_date


def _comparison_anchor_date(comparison: ShadowFillComparison) -> date | None:
    if comparison.source_as_of is not None:
        return comparison.source_as_of.date()
    return comparison.session_date


def _in_window(anchor_date: date | None, *, date_from: date, date_to: date) -> bool:
    return anchor_date is not None and date_from <= anchor_date <= date_to


def _record_sort_key(record: PaperShadowAuditRecord) -> tuple[datetime, str]:
    anchor = record.source_as_of or record.created_at
    if anchor is None:
        shadow_date = record.shadow_session_date or date.min
        anchor = datetime.combine(shadow_date, time.min)
    return anchor, record.intent_id


def _comparison_sort_key(comparison: ShadowFillComparison) -> tuple[datetime, str]:
    anchor = comparison.source_as_of
    if anchor is None:
        session_date = comparison.session_date or date.min
        anchor = datetime.combine(session_date, time.min)
    return anchor, comparison.intent_id


def _shadow_review_payload(
    comparisons: Sequence[ShadowFillComparison],
) -> dict[str, object]:
    return {
        "summary": summarize_shadow_fill_comparisons(comparisons),
        "by_regime": shadow_fill_regime_stats(comparisons).to_dict(orient="records"),
        "by_status": shadow_fill_status_stats(comparisons).to_dict(orient="records"),
    }


def _paper_shadow_audit_payload(
    records: Sequence[PaperShadowAuditRecord],
) -> dict[str, object]:
    return {
        "summary": summarize_paper_shadow_audit(records),
        "by_alignment": paper_shadow_alignment_stats(records).to_dict(orient="records"),
        "by_regime": paper_shadow_regime_stats(records).to_dict(orient="records"),
    }


def _recent_divergences(
    records: Sequence[PaperShadowAuditRecord],
    *,
    limit: int,
) -> tuple[dict[str, object], ...]:
    divergent = [record for record in records if record.alignment_status not in _ALIGNED_STATUSES]
    divergent.sort(key=_record_sort_key, reverse=True)
    return tuple(record.model_dump(mode="json") for record in divergent[:limit])


def _recent_shadow_alerts(
    comparisons: Sequence[ShadowFillComparison],
    *,
    limit: int,
) -> tuple[dict[str, object], ...]:
    alerted = [comparison for comparison in comparisons if comparison.slippage_alert is not None]
    alerted.sort(key=_comparison_sort_key, reverse=True)
    return tuple(comparison.model_dump(mode="json") for comparison in alerted[:limit])


def _dedupe_records(
    rows: Sequence[dict[str, object]],
    *,
    keys: Sequence[str],
    limit: int,
) -> tuple[dict[str, object], ...]:
    if limit <= 0:
        return ()

    seen: set[tuple[object, ...]] = set()
    deduped: list[dict[str, object]] = []
    for row in rows:
        row_key = tuple(row.get(key) for key in keys)
        if row_key in seen:
            continue
        seen.add(row_key)
        deduped.append(row)
        if len(deduped) >= limit:
            break
    return tuple(deduped)


def _summary_metric(payload: dict[str, object], key: str) -> float:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return 0.0
    value = summary.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _empty_review_status_counts() -> dict[str, int]:
    return {status.value: 0 for status in ReviewStatus}


def operator_review_run_metrics(report: OperatorReviewReport) -> dict[str, object]:
    status_counts = _empty_review_status_counts()
    category_status_counts: dict[str, dict[str, int]] = {}
    non_pass_checks: list[dict[str, object]] = []

    for check in report.review_checks:
        status_counts[check.status.value] += 1
        category_counts = category_status_counts.setdefault(
            check.category,
            _empty_review_status_counts(),
        )
        category_counts[check.status.value] += 1
        if check.status != ReviewStatus.PASS:
            non_pass_checks.append(check.model_dump(mode="json"))

    rolling_window_metrics: list[dict[str, object]] = []
    for window in report.rolling_audit.windows:
        paper_shadow_audit = window.paper_shadow_audit
        shadow_review = window.shadow_review
        rolling_window_metrics.append(
            {
                "window": window.window.label,
                "lookback_days": window.window.lookback_days,
                "date_from": window.window.date_from.isoformat(),
                "date_to": window.window.date_to.isoformat(),
                "paper_shadow_record_count": int(
                    _summary_metric(paper_shadow_audit, "record_count")
                ),
                "paper_shadow_aligned_count": int(
                    _summary_metric(paper_shadow_audit, "aligned_count")
                ),
                "paper_shadow_divergent_count": int(
                    _summary_metric(paper_shadow_audit, "divergent_count")
                ),
                "paper_shadow_alignment_rate": _summary_metric(
                    paper_shadow_audit,
                    "alignment_rate",
                ),
                "shadow_comparison_count": int(_summary_metric(shadow_review, "comparison_count")),
                "shadow_missing_market_data_count": int(
                    _summary_metric(shadow_review, "missing_market_data_count")
                ),
                "shadow_slippage_alert_count": int(
                    _summary_metric(shadow_review, "slippage_alert_count")
                ),
                "shadow_slippage_alert_rate": _summary_metric(
                    shadow_review,
                    "slippage_alert_rate",
                ),
            }
        )

    return {
        "review_status": report.review_status.value,
        "review_thresholds": report.review_thresholds.model_dump(mode="json"),
        "review_check_count": len(report.review_checks),
        "review_check_status_counts": status_counts,
        "review_check_category_status_counts": category_status_counts,
        "review_check_pass_count": status_counts[ReviewStatus.PASS.value],
        "review_check_warn_count": status_counts[ReviewStatus.WARN.value],
        "review_check_fail_count": status_counts[ReviewStatus.FAIL.value],
        "non_pass_review_check_count": len(non_pass_checks),
        "non_pass_review_checks": non_pass_checks,
        "window_count": len(report.rolling_audit.windows),
        "rolling_window_metrics": rolling_window_metrics,
        "latest_window_metrics": rolling_window_metrics[0] if rolling_window_metrics else None,
        "runtime_run_count": len(report.runtime_runs),
        "runtime_event_count": len(report.runtime_events),
        "decision_event_count": len(report.decision_events),
        "review_exception_count": len(report.review_exceptions),
        "shadow_snapshot_comparison_count": int(
            _summary_metric(report.shadow_comparison_snapshots, "comparison_count")
        ),
        "paper_shadow_audit_snapshot_record_count": int(
            _summary_metric(report.paper_shadow_audit_snapshots, "record_count")
        ),
        "replay_artifact_count": len(report.replay_artifacts),
        "replay_artifact_status_counts": _replay_artifact_status_counts(report.replay_artifacts),
    }


def summarize_operator_review_run_trends(
    runs: Sequence[dict[str, object]],
) -> dict[str, object]:
    review_runs = tuple(
        run
        for run in runs
        if run.get("command") == REVIEW_REPORT_COMMAND and isinstance(run.get("metrics"), dict)
    )
    status_counts = _empty_review_status_counts() | {"UNKNOWN": 0}
    non_pass_category_counts: dict[str, int] = {}
    run_summaries: list[dict[str, object]] = []
    window_metric_values: dict[str, dict[str, list[float]]] = {}
    latest_window_values: dict[str, dict[str, object]] = {}

    non_pass_counts: list[float] = []
    for run in review_runs:
        metrics = _as_dict(run.get("metrics"))
        status = _string_metric(metrics, "review_status") or "UNKNOWN"
        if status not in status_counts:
            status = "UNKNOWN"
        status_counts[status] += 1

        non_pass_count = _numeric_metric(metrics, "non_pass_review_check_count")
        non_pass_counts.append(non_pass_count)
        for check in _as_sequence(metrics.get("non_pass_review_checks")):
            check_map = _as_dict(check)
            category = _string_metric(check_map, "category")
            if category is not None:
                non_pass_category_counts[category] = non_pass_category_counts.get(category, 0) + 1

        latest_window = _as_dict(metrics.get("latest_window_metrics"))
        run_summaries.append(
            {
                "run_id": run.get("run_id"),
                "started_at": run.get("started_at"),
                "output_path": run.get("output_path"),
                "review_status": status,
                "review_check_warn_count": int(_numeric_metric(metrics, "review_check_warn_count")),
                "review_check_fail_count": int(_numeric_metric(metrics, "review_check_fail_count")),
                "non_pass_review_check_count": int(non_pass_count),
                "latest_window": latest_window.get("window"),
                "latest_alignment_rate": latest_window.get("paper_shadow_alignment_rate"),
                "latest_divergent_count": latest_window.get("paper_shadow_divergent_count"),
                "latest_missing_market_data_count": latest_window.get(
                    "shadow_missing_market_data_count"
                ),
                "latest_slippage_alert_rate": latest_window.get("shadow_slippage_alert_rate"),
            }
        )

        for window in _as_sequence(metrics.get("rolling_window_metrics")):
            window_map = _as_dict(window)
            window_label = _string_metric(window_map, "window")
            if window_label is None:
                continue
            latest_window_values.setdefault(window_label, window_map)
            metric_bucket = window_metric_values.setdefault(window_label, {})
            for key in (
                "paper_shadow_record_count",
                "paper_shadow_alignment_rate",
                "paper_shadow_divergent_count",
                "shadow_comparison_count",
                "shadow_missing_market_data_count",
                "shadow_slippage_alert_rate",
            ):
                value = window_map.get(key)
                if isinstance(value, (int, float)):
                    metric_bucket.setdefault(key, []).append(float(value))

    window_metric_trends = {
        window: _window_metric_trend(
            latest=latest_window_values.get(window, {}),
            metric_values=metric_values,
        )
        for window, metric_values in window_metric_values.items()
    }
    latest_run = run_summaries[0] if run_summaries else None
    oldest_run = run_summaries[-1] if run_summaries else None

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "source_command": REVIEW_REPORT_COMMAND,
        "run_count": len(review_runs),
        "latest_started_at": None if latest_run is None else latest_run.get("started_at"),
        "oldest_started_at": None if oldest_run is None else oldest_run.get("started_at"),
        "latest_run": latest_run,
        "status_counts": status_counts,
        "non_pass_review_check_total": int(sum(non_pass_counts)),
        "average_non_pass_review_check_count": _mean(non_pass_counts),
        "max_non_pass_review_check_count": int(max(non_pass_counts, default=0.0)),
        "non_pass_category_counts": non_pass_category_counts,
        "window_metric_trends": window_metric_trends,
        "runs": run_summaries,
    }


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ()


def _string_metric(metrics: dict[str, object], key: str) -> str | None:
    value = metrics.get(key)
    return value if isinstance(value, str) else None


def _numeric_metric(metrics: dict[str, object], key: str) -> float:
    value = metrics.get(key)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _mean(values: Sequence[float]) -> float:
    return 0.0 if not values else sum(values) / len(values)


def _replay_artifact_status_counts(
    replay_artifacts: Sequence[dict[str, object]],
) -> dict[str, int]:
    status_counts = _empty_review_status_counts() | {"UNKNOWN": 0}
    for artifact in replay_artifacts:
        replay_summary = _as_dict(artifact.get("replay_summary"))
        status = _string_metric(replay_summary, "status") or "UNKNOWN"
        if status not in status_counts:
            status = "UNKNOWN"
        status_counts[status] += 1
    return status_counts


def _window_metric_trend(
    *,
    latest: dict[str, object],
    metric_values: dict[str, list[float]],
) -> dict[str, object]:
    sample_count = max((len(values) for values in metric_values.values()), default=0)
    return {
        "sample_count": sample_count,
        "latest": latest,
        "averages": {key: _mean(values) for key, values in metric_values.items()},
        "minimums": {key: min(values) for key, values in metric_values.items()},
        "maximums": {key: max(values) for key, values in metric_values.items()},
    }


def _check_status(
    *,
    status: ReviewStatus,
    category: str,
    message: str,
    observed: float | int | str | bool | None = None,
    threshold: float | int | str | bool | None = None,
    window: str | None = None,
) -> OperatorReviewCheck:
    return OperatorReviewCheck(
        status=status,
        category=category,
        message=message,
        observed=observed,
        threshold=threshold,
        window=window,
    )


def _overall_review_status(checks: Sequence[OperatorReviewCheck]) -> ReviewStatus:
    if any(check.status == ReviewStatus.FAIL for check in checks):
        return ReviewStatus.FAIL
    if any(check.status == ReviewStatus.WARN for check in checks):
        return ReviewStatus.WARN
    return ReviewStatus.PASS


def _build_review_checks(
    *,
    rolling_audit: RollingAuditReport,
    runtime_runs: Sequence[dict[str, object]],
    decision_events: Sequence[dict[str, object]],
    shadow_snapshot_summary: dict[str, object],
    audit_snapshot_summary: dict[str, object],
    replay_artifacts: Sequence[dict[str, object]],
    thresholds: OperatorReviewThresholds,
) -> tuple[OperatorReviewCheck, ...]:
    checks: list[OperatorReviewCheck] = []

    runtime_run_count = len(runtime_runs)
    checks.append(
        _check_status(
            status=(
                ReviewStatus.FAIL
                if thresholds.require_runtime_runs and runtime_run_count == 0
                else ReviewStatus.PASS
            ),
            category="runtime_runs_present",
            observed=runtime_run_count,
            threshold=1 if thresholds.require_runtime_runs else 0,
            message="Runtime run history is required for review traceability.",
        )
    )

    decision_event_count = len(decision_events)
    checks.append(
        _check_status(
            status=(
                ReviewStatus.FAIL
                if thresholds.require_decision_events and decision_event_count == 0
                else ReviewStatus.PASS
            ),
            category="decision_events_present",
            observed=decision_event_count,
            threshold=1 if thresholds.require_decision_events else 0,
            message="Per-intent decision events are required for review traceability.",
        )
    )

    shadow_snapshot_count = _summary_metric(shadow_snapshot_summary, "comparison_count")
    checks.append(
        _check_status(
            status=(
                ReviewStatus.FAIL
                if thresholds.require_shadow_snapshots and shadow_snapshot_count == 0
                else ReviewStatus.PASS
            ),
            category="shadow_snapshots_present",
            observed=int(shadow_snapshot_count),
            threshold=1 if thresholds.require_shadow_snapshots else 0,
            message="Immutable shadow comparison snapshots are required for review.",
        )
    )

    audit_snapshot_count = _summary_metric(audit_snapshot_summary, "record_count")
    checks.append(
        _check_status(
            status=(
                ReviewStatus.FAIL
                if thresholds.require_paper_shadow_audit_snapshots and audit_snapshot_count == 0
                else ReviewStatus.PASS
            ),
            category="paper_shadow_audit_snapshots_present",
            observed=int(audit_snapshot_count),
            threshold=1 if thresholds.require_paper_shadow_audit_snapshots else 0,
            message="Immutable paper-shadow audit snapshots are required for review.",
        )
    )

    for window in rolling_audit.windows:
        window_label = window.window.label
        audit_summary = window.paper_shadow_audit
        shadow_summary = window.shadow_review
        record_count = _summary_metric(audit_summary, "record_count")
        comparison_count = _summary_metric(shadow_summary, "comparison_count")
        alignment_rate = _summary_metric(audit_summary, "alignment_rate")
        divergent_count = _summary_metric(audit_summary, "divergent_count")
        missing_market_data_count = _summary_metric(
            shadow_summary,
            "missing_market_data_count",
        )
        slippage_alert_rate = _summary_metric(shadow_summary, "slippage_alert_rate")

        checks.append(
            _check_status(
                status=(
                    ReviewStatus.WARN
                    if record_count > 0 and alignment_rate < thresholds.min_alignment_rate
                    else ReviewStatus.PASS
                ),
                category="paper_shadow_alignment_rate",
                window=window_label,
                observed=alignment_rate,
                threshold=thresholds.min_alignment_rate,
                message="Paper/shadow alignment rate is below the configured threshold.",
            )
        )
        checks.append(
            _check_status(
                status=(
                    ReviewStatus.WARN
                    if divergent_count > thresholds.max_divergent_count
                    else ReviewStatus.PASS
                ),
                category="paper_shadow_divergent_count",
                window=window_label,
                observed=int(divergent_count),
                threshold=thresholds.max_divergent_count,
                message="Paper/shadow divergent row count exceeds the configured threshold.",
            )
        )
        checks.append(
            _check_status(
                status=(
                    ReviewStatus.FAIL
                    if missing_market_data_count > thresholds.max_missing_market_data_count
                    else ReviewStatus.PASS
                ),
                category="shadow_missing_market_data_count",
                window=window_label,
                observed=int(missing_market_data_count),
                threshold=thresholds.max_missing_market_data_count,
                message="Shadow comparison missing-market-data count exceeds the threshold.",
            )
        )
        checks.append(
            _check_status(
                status=(
                    ReviewStatus.WARN
                    if comparison_count > 0
                    and slippage_alert_rate > thresholds.max_shadow_slippage_alert_rate
                    else ReviewStatus.PASS
                ),
                category="shadow_slippage_alert_rate",
                window=window_label,
                observed=slippage_alert_rate,
                threshold=thresholds.max_shadow_slippage_alert_rate,
                message="Shadow slippage alert rate exceeds the configured threshold.",
            )
        )

    for replay_artifact in replay_artifacts:
        checks.extend(_build_replay_artifact_checks(replay_artifact))

    return tuple(checks)


def _build_replay_artifact_checks(
    replay_artifact: dict[str, object],
) -> tuple[OperatorReviewCheck, ...]:
    replay_dir = str(replay_artifact.get("path") or "")
    replay_summary = _as_dict(replay_artifact.get("replay_summary"))
    validation_summary = _as_dict(replay_artifact.get("validation_summary"))
    decision_traces = _as_dict(replay_artifact.get("decision_traces"))
    reconciliation_summary = _as_dict(replay_artifact.get("reconciliation_summary"))
    load_errors = _as_sequence(replay_artifact.get("load_errors"))

    checks: list[OperatorReviewCheck] = []
    checks.append(
        _check_status(
            status=ReviewStatus.FAIL if load_errors else ReviewStatus.PASS,
            category="replay_artifacts_loadable",
            observed=len(load_errors),
            threshold=0,
            window=replay_dir,
            message="Replay artifact directory must contain readable replay JSON outputs.",
        )
    )
    checks.append(
        _status_value_check(
            category="replay_status",
            observed=_string_metric(replay_summary, "status"),
            window=replay_dir,
            message="Replay status from replay_summary.json must be PASS.",
        )
    )
    checks.append(
        _status_value_check(
            category="replay_validation_status",
            observed=_string_metric(validation_summary, "status"),
            window=replay_dir,
            message="Replay validation summary must be PASS.",
        )
    )
    checks.append(
        _status_value_check(
            category="replay_reconciliation_status",
            observed=_string_metric(reconciliation_summary, "status"),
            window=replay_dir,
            message="Replay reconciliation summary must be PASS.",
        )
    )

    trace_count = len(_as_sequence(decision_traces.get("traces")))
    checks.append(
        _check_status(
            status=ReviewStatus.WARN if trace_count == 0 else ReviewStatus.PASS,
            category="replay_decision_trace_count",
            observed=trace_count,
            threshold=1,
            window=replay_dir,
            message="Replay should produce decision traces for operator review.",
        )
    )

    failed_reconciliation_checks = [
        check
        for check in _as_sequence(reconciliation_summary.get("checks"))
        if _as_dict(check).get("status") == ReviewStatus.FAIL.value
    ]
    checks.append(
        _check_status(
            status=ReviewStatus.FAIL if failed_reconciliation_checks else ReviewStatus.PASS,
            category="replay_reconciliation_failed_checks",
            observed=len(failed_reconciliation_checks),
            threshold=0,
            window=replay_dir,
            message="Replay reconciliation has failing stage-count checks.",
        )
    )
    return tuple(checks)


def _status_value_check(
    *,
    category: str,
    observed: str | None,
    message: str,
    window: str | None,
) -> OperatorReviewCheck:
    if observed == ReviewStatus.PASS.value:
        status = ReviewStatus.PASS
    elif observed == ReviewStatus.WARN.value:
        status = ReviewStatus.WARN
    else:
        status = ReviewStatus.FAIL
    return _check_status(
        status=status,
        category=category,
        observed=observed or "MISSING",
        threshold=ReviewStatus.PASS.value,
        window=window,
        message=message,
    )


def _build_review_exceptions(
    *,
    rolling_audit: RollingAuditReport,
    runtime_runs: Sequence[dict[str, object]],
    runtime_events: Sequence[dict[str, object]],
    decision_events: Sequence[dict[str, object]],
    shadow_snapshot_summary: dict[str, object],
    audit_snapshot_summary: dict[str, object],
    replay_artifacts: Sequence[dict[str, object]],
    recent_divergences: Sequence[dict[str, object]],
    recent_shadow_alerts: Sequence[dict[str, object]],
    limit: int,
) -> tuple[dict[str, object], ...]:
    if limit <= 0:
        return ()

    exceptions: list[dict[str, object]] = []

    if not runtime_runs:
        exceptions.append(
            {
                "severity": "info",
                "category": "run_history",
                "message": "No runtime runs are recorded in the selected database.",
            }
        )
    if not runtime_events:
        exceptions.append(
            {
                "severity": "info",
                "category": "runtime_events",
                "message": "No runtime events are recorded in the selected database.",
            }
        )
    elif not decision_events:
        exceptions.append(
            {
                "severity": "warning",
                "category": "decision_ledger",
                "message": "Runtime events exist, but no per-intent decision events were found.",
            }
        )

    if _summary_metric(shadow_snapshot_summary, "comparison_count") == 0:
        exceptions.append(
            {
                "severity": "warning",
                "category": "shadow_comparison_snapshots",
                "message": "No immutable shadow comparison snapshots were found.",
            }
        )
    if _summary_metric(audit_snapshot_summary, "record_count") == 0:
        exceptions.append(
            {
                "severity": "warning",
                "category": "paper_shadow_audit_snapshots",
                "message": "No immutable paper-shadow audit snapshots were found.",
            }
        )

    for replay_artifact in replay_artifacts:
        replay_dir = str(replay_artifact.get("path") or "")
        for load_error in _as_sequence(replay_artifact.get("load_errors")):
            exceptions.append(
                {
                    "severity": "critical",
                    "category": "replay_artifact_load_error",
                    "path": replay_dir,
                    "message": str(load_error),
                }
            )
        replay_summary = _as_dict(replay_artifact.get("replay_summary"))
        replay_status = _string_metric(replay_summary, "status")
        if replay_status and replay_status != ReviewStatus.PASS.value:
            exceptions.append(
                {
                    "severity": "critical"
                    if replay_status == ReviewStatus.FAIL.value
                    else "warning",
                    "category": "replay_status",
                    "path": replay_dir,
                    "status": replay_status,
                    "message": (
                        "Replay output is not PASS and should be inspected "
                        "before expanding scope."
                    ),
                }
            )
        reconciliation_summary = _as_dict(replay_artifact.get("reconciliation_summary"))
        failed_checks = [
            check
            for check in _as_sequence(reconciliation_summary.get("checks"))
            if _as_dict(check).get("status") == ReviewStatus.FAIL.value
        ]
        if failed_checks:
            exceptions.append(
                {
                    "severity": "critical",
                    "category": "replay_reconciliation",
                    "path": replay_dir,
                    "count": len(failed_checks),
                    "message": "Replay reconciliation has failing checks.",
                }
            )

    for window in rolling_audit.windows:
        divergent_count = _summary_metric(window.paper_shadow_audit, "divergent_count")
        if divergent_count:
            exceptions.append(
                {
                    "severity": "warning",
                    "category": "paper_shadow_divergence",
                    "window": window.window.label,
                    "count": int(divergent_count),
                    "message": "Paper/shadow divergences are present in this window.",
                }
            )
        alert_count = _summary_metric(window.shadow_review, "slippage_alert_count")
        if alert_count:
            exceptions.append(
                {
                    "severity": "warning",
                    "category": "shadow_slippage_alert",
                    "window": window.window.label,
                    "count": int(alert_count),
                    "message": "Shadow fill slippage alerts are present in this window.",
                }
            )

    if recent_divergences:
        exceptions.append(
            {
                "severity": "warning",
                "category": "recent_divergence_rows",
                "count": len(recent_divergences),
                "message": "Recent divergent audit rows should be reviewed before expanding scope.",
            }
        )
    if recent_shadow_alerts:
        exceptions.append(
            {
                "severity": "warning",
                "category": "recent_shadow_alert_rows",
                "count": len(recent_shadow_alerts),
                "message": "Recent shadow alert rows should be reviewed before expanding scope.",
            }
        )

    return tuple(exceptions[:limit])


class RollingAuditReportService:
    def __init__(
        self,
        *,
        paper_shadow_audit_service: PaperShadowAuditService,
        shadow_review_service: ShadowReviewService,
    ) -> None:
        self._paper_shadow_audit_service = paper_shadow_audit_service
        self._shadow_review_service = shadow_review_service

    def build_report(
        self,
        *,
        as_of_date: date,
        lookback_days: Sequence[int] = DEFAULT_REPORT_LOOKBACK_DAYS,
        symbol: str | None = None,
        regime_state: RegimeState | None = None,
        exception_limit: int = 10,
    ) -> RollingAuditReport:
        if exception_limit < 0:
            raise ValueError("exception_limit must be non-negative")

        normalized_lookbacks = _normalize_lookback_days(lookback_days)
        records = self._paper_shadow_audit_service.load_records(
            symbol=symbol,
            regime_state=regime_state,
        )
        comparisons = self._shadow_review_service.load_comparisons(
            symbol=symbol,
            regime_state=regime_state,
        )

        windows: list[RollingAuditWindowReport] = []
        for days in normalized_lookbacks:
            window_start = _window_start(as_of_date, days)
            window_records = tuple(
                record
                for record in records
                if _in_window(
                    _record_anchor_date(record),
                    date_from=window_start,
                    date_to=as_of_date,
                )
            )
            window_comparisons = tuple(
                comparison
                for comparison in comparisons
                if _in_window(
                    _comparison_anchor_date(comparison),
                    date_from=window_start,
                    date_to=as_of_date,
                )
            )
            windows.append(
                RollingAuditWindowReport(
                    window=RollingAuditWindow(
                        label=f"{days}d",
                        lookback_days=days,
                        date_from=window_start,
                        date_to=as_of_date,
                    ),
                    shadow_review=_shadow_review_payload(window_comparisons),
                    paper_shadow_audit=_paper_shadow_audit_payload(window_records),
                    recent_divergences=_recent_divergences(
                        window_records,
                        limit=exception_limit,
                    ),
                    recent_shadow_alerts=_recent_shadow_alerts(
                        window_comparisons,
                        limit=exception_limit,
                    ),
                )
            )

        return RollingAuditReport(
            generated_at=datetime.utcnow(),
            as_of_date=as_of_date,
            symbol=symbol,
            regime_state=regime_state,
            windows=tuple(windows),
        )


class OperatorReviewReportService:
    def __init__(
        self,
        *,
        rolling_audit_report_service: RollingAuditReportService,
        paper_shadow_audit_service: PaperShadowAuditService,
        shadow_review_service: ShadowReviewService,
        runtime_run_history: RuntimeRunHistory,
    ) -> None:
        self._rolling_audit_report_service = rolling_audit_report_service
        self._paper_shadow_audit_service = paper_shadow_audit_service
        self._shadow_review_service = shadow_review_service
        self._runtime_run_history = runtime_run_history

    def build_report(
        self,
        *,
        as_of_date: date,
        lookback_days: Sequence[int] = DEFAULT_REPORT_LOOKBACK_DAYS,
        symbol: str | None = None,
        regime_state: RegimeState | None = None,
        event_limit: int = 100,
        run_limit: int = 20,
        exception_limit: int = 10,
        review_thresholds: OperatorReviewThresholds | None = None,
        replay_artifact_dirs: Sequence[str | Path] = (),
    ) -> OperatorReviewReport:
        if event_limit < 0:
            raise ValueError("event_limit must be non-negative")
        if run_limit < 0:
            raise ValueError("run_limit must be non-negative")
        if exception_limit < 0:
            raise ValueError("exception_limit must be non-negative")

        normalized_lookbacks = _normalize_lookback_days(lookback_days)
        thresholds = review_thresholds or DEFAULT_OPERATOR_REVIEW_THRESHOLDS
        rolling_audit = self._rolling_audit_report_service.build_report(
            as_of_date=as_of_date,
            lookback_days=normalized_lookbacks,
            symbol=symbol,
            regime_state=regime_state,
            exception_limit=exception_limit,
        )
        runtime_runs = self._runtime_run_history.list_runs(limit=run_limit)
        runtime_events = self._runtime_run_history.list_events(limit=event_limit)
        decision_events = tuple(
            event for event in runtime_events if event.get("event_type") in _DECISION_EVENT_TYPES
        )
        shadow_snapshot_summary = self._shadow_review_service.summarize_comparison_snapshots(
            symbol=symbol,
            regime_state=regime_state,
        )
        audit_snapshot_summary = self._paper_shadow_audit_service.summarize_record_snapshots(
            symbol=symbol,
            regime_state=regime_state,
        )
        replay_artifacts = tuple(load_replay_artifact_bundle(path) for path in replay_artifact_dirs)

        divergence_rows = [
            row for window in rolling_audit.windows for row in window.recent_divergences
        ]
        alert_rows = [
            row for window in rolling_audit.windows for row in window.recent_shadow_alerts
        ]
        recent_divergences = _dedupe_records(
            divergence_rows,
            keys=("intent_id", "setup_id", "alignment_status"),
            limit=exception_limit,
        )
        recent_shadow_alerts = _dedupe_records(
            alert_rows,
            keys=("intent_id", "setup_id", "status"),
            limit=exception_limit,
        )
        review_exceptions = _build_review_exceptions(
            rolling_audit=rolling_audit,
            runtime_runs=runtime_runs,
            runtime_events=runtime_events,
            decision_events=decision_events,
            shadow_snapshot_summary=shadow_snapshot_summary,
            audit_snapshot_summary=audit_snapshot_summary,
            replay_artifacts=replay_artifacts,
            recent_divergences=recent_divergences,
            recent_shadow_alerts=recent_shadow_alerts,
            limit=exception_limit,
        )
        review_checks = _build_review_checks(
            rolling_audit=rolling_audit,
            runtime_runs=runtime_runs,
            decision_events=decision_events,
            shadow_snapshot_summary=shadow_snapshot_summary,
            audit_snapshot_summary=audit_snapshot_summary,
            replay_artifacts=replay_artifacts,
            thresholds=thresholds,
        )

        return OperatorReviewReport(
            generated_at=datetime.utcnow(),
            as_of_date=as_of_date,
            symbol=symbol,
            regime_state=regime_state,
            review_status=_overall_review_status(review_checks),
            review_thresholds=thresholds,
            review_checks=review_checks,
            lookback_days=normalized_lookbacks,
            rolling_audit=rolling_audit,
            runtime_runs=runtime_runs,
            runtime_events=runtime_events,
            decision_events=decision_events,
            shadow_comparison_snapshots=shadow_snapshot_summary,
            paper_shadow_audit_snapshots=audit_snapshot_summary,
            replay_artifacts=replay_artifacts,
            recent_divergences=recent_divergences,
            recent_shadow_alerts=recent_shadow_alerts,
            review_exceptions=review_exceptions,
        )


def load_replay_artifact_bundle(path: str | Path) -> dict[str, object]:
    replay_dir = Path(path)
    artifacts: dict[str, object] = {"path": str(replay_dir), "load_errors": []}
    load_errors: list[str] = []
    for artifact_name in (
        "validation_summary",
        "replay_summary",
        "decision_traces",
        "reconciliation_summary",
    ):
        artifact_path = replay_dir / f"{artifact_name}.json"
        try:
            with artifact_path.open("r", encoding="utf-8") as handle:
                artifacts[artifact_name] = json.load(handle)
        except Exception as exc:
            load_errors.append(f"{artifact_path}: {exc}")
            artifacts[artifact_name] = {}
    artifacts["load_errors"] = tuple(load_errors)
    return artifacts
