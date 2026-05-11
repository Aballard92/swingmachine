from __future__ import annotations

from collections.abc import Mapping, Sequence
from html import escape
from typing import cast

from swingmachine.contracts import OperatorReviewReport

ColumnSpec = tuple[str, tuple[str, ...]]


def render_operator_review_html(
    report: OperatorReviewReport,
    *,
    row_limit: int = 25,
) -> str:
    if row_limit < 0:
        raise ValueError("row_limit must be non-negative")

    payload = cast(dict[str, object], report.model_dump(mode="json"))
    rolling_audit = _as_mapping(payload.get("rolling_audit"))
    windows = _as_sequence(rolling_audit.get("windows"))
    runtime_runs = _as_sequence(payload.get("runtime_runs"))
    runtime_events = _as_sequence(payload.get("runtime_events"))
    decision_events = _as_sequence(payload.get("decision_events"))
    review_checks = _as_sequence(payload.get("review_checks"))
    review_exceptions = _as_sequence(payload.get("review_exceptions"))
    recent_divergences = _as_sequence(payload.get("recent_divergences"))
    recent_shadow_alerts = _as_sequence(payload.get("recent_shadow_alerts"))

    shadow_snapshots = _as_mapping(payload.get("shadow_comparison_snapshots"))
    audit_snapshots = _as_mapping(payload.get("paper_shadow_audit_snapshots"))

    parts = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Swingmachine Operator Review</title>",
        f"<style>{_STYLE}</style>",
        "</head>",
        "<body>",
        "<main>",
        "<header>",
        '<p class="eyebrow">Paper / shadow review</p>',
        "<h1>Swingmachine Operator Review</h1>",
        _metadata(payload),
        "</header>",
        _headline_metrics(
            {
                "windows": len(windows),
                "runtime runs": len(runtime_runs),
                "runtime events": len(runtime_events),
                "decision events": len(decision_events),
                "review status": payload.get("review_status") or "UNKNOWN",
                "review checks": len(review_checks),
                "review exceptions": len(review_exceptions),
            }
        ),
        _summary_pair(
            "Review Criteria",
            "Thresholds",
            _as_mapping(payload.get("review_thresholds")),
            "Current status",
            {
                "review_status": payload.get("review_status") or "UNKNOWN",
                "check_count": len(review_checks),
                "exception_count": len(review_exceptions),
            },
        ),
        _summary_pair(
            "Immutable Snapshot Summaries",
            "Shadow comparison snapshots",
            _as_mapping(shadow_snapshots.get("summary")),
            "Paper-shadow audit snapshots",
            _as_mapping(audit_snapshots.get("summary")),
        ),
        _table(
            "Rolling Audit Windows",
            windows,
            (
                ("window", ("window", "label")),
                ("from", ("window", "date_from")),
                ("to", ("window", "date_to")),
                ("audit rows", ("paper_shadow_audit", "summary", "record_count")),
                ("divergent", ("paper_shadow_audit", "summary", "divergent_count")),
                ("alignment rate", ("paper_shadow_audit", "summary", "alignment_rate")),
                ("comparisons", ("shadow_review", "summary", "comparison_count")),
                ("fill rate", ("shadow_review", "summary", "fill_rate")),
                ("slippage rate", ("shadow_review", "summary", "slippage_alert_rate")),
            ),
            row_limit=row_limit,
        ),
        _table(
            "Review Checks",
            review_checks,
            (
                ("status", ("status",)),
                ("category", ("category",)),
                ("window", ("window",)),
                ("observed", ("observed",)),
                ("threshold", ("threshold",)),
                ("message", ("message",)),
            ),
            row_limit=row_limit,
        ),
        _table(
            "Review Exceptions",
            review_exceptions,
            (
                ("severity", ("severity",)),
                ("category", ("category",)),
                ("window", ("window",)),
                ("count", ("count",)),
                ("message", ("message",)),
            ),
            row_limit=row_limit,
        ),
        _table(
            "Recent Divergences",
            recent_divergences,
            (
                ("source as of", ("source_as_of",)),
                ("symbol", ("symbol",)),
                ("setup", ("setup_id",)),
                ("alignment", ("alignment_status",)),
                ("paper status", ("paper_broker_status",)),
                ("shadow status", ("shadow_status",)),
                ("shadow fill", ("shadow_would_fill",)),
            ),
            row_limit=row_limit,
        ),
        _table(
            "Recent Shadow Alerts",
            recent_shadow_alerts,
            (
                ("source as of", ("source_as_of",)),
                ("symbol", ("symbol",)),
                ("setup", ("setup_id",)),
                ("status", ("status",)),
                ("fill price", ("hypothetical_fill_price",)),
                ("cost bps", ("total_cost_bps",)),
                ("detail", ("detail",)),
            ),
            row_limit=row_limit,
        ),
        _table(
            "Decision Events",
            decision_events,
            (
                ("occurred", ("occurred_at",)),
                ("event", ("event_type",)),
                ("command", ("command",)),
                ("mode", ("mode",)),
                ("symbol", ("symbol",)),
                ("setup", ("setup_id",)),
                ("intent", ("intent_id",)),
            ),
            row_limit=row_limit,
        ),
        _table(
            "Recent Runtime Runs",
            runtime_runs,
            (
                ("started", ("started_at",)),
                ("command", ("command",)),
                ("status", ("status",)),
                ("output", ("output_path",)),
            ),
            row_limit=row_limit,
        ),
        "</main>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def _as_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return {}


def _as_sequence(value: object) -> Sequence[object]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return cast(Sequence[object], value)
    return ()


def _metadata(payload: Mapping[str, object]) -> str:
    items = (
        ("generated", payload.get("generated_at")),
        ("as of", payload.get("as_of_date")),
        ("symbol", payload.get("symbol")),
        ("regime", payload.get("regime_state")),
        (
            "lookbacks",
            ", ".join(str(value) for value in _as_sequence(payload.get("lookback_days"))),
        ),
    )
    rows = "\n".join(f"<dt>{_text(label)}</dt><dd>{_value(value)}</dd>" for label, value in items)
    return f'<dl class="metadata">{rows}</dl>'


def _headline_metrics(metrics: Mapping[str, object]) -> str:
    items = "\n".join(
        f'<div class="metric"><span>{_text(label)}</span><strong>{_value(value)}</strong></div>'
        for label, value in metrics.items()
    )
    return f'<section class="metrics">{items}</section>'


def _summary_pair(
    title: str,
    left_title: str,
    left: Mapping[str, object],
    right_title: str,
    right: Mapping[str, object],
) -> str:
    return "\n".join(
        [
            "<section>",
            f"<h2>{_text(title)}</h2>",
            '<div class="summary-grid">',
            _summary_block(left_title, left),
            _summary_block(right_title, right),
            "</div>",
            "</section>",
        ]
    )


def _summary_block(title: str, values: Mapping[str, object]) -> str:
    if not values:
        return f'<div class="summary"><h3>{_text(title)}</h3><p class="empty">No data.</p></div>'
    rows = "\n".join(
        f"<dt>{_text(key.replace('_', ' '))}</dt><dd>{_value(value)}</dd>"
        for key, value in values.items()
    )
    return f'<div class="summary"><h3>{_text(title)}</h3><dl>{rows}</dl></div>'


def _table(
    title: str,
    rows: Sequence[object],
    columns: Sequence[ColumnSpec],
    *,
    row_limit: int,
) -> str:
    visible_rows = rows[:row_limit]
    header = "".join(f"<th>{_text(label)}</th>" for label, _path in columns)
    body_rows = []
    for row in visible_rows:
        row_map = _as_mapping(row)
        cells = "".join(f"<td>{_value(_extract(row_map, path))}</td>" for _label, path in columns)
        body_rows.append(f"<tr>{cells}</tr>")

    if body_rows:
        body = "\n".join(body_rows)
    else:
        body = f'<tr><td colspan="{len(columns)}" class="empty">No rows.</td></tr>'

    limited = ""
    if len(rows) > len(visible_rows):
        limited = f'<p class="limited">Showing {len(visible_rows)} of {len(rows)} rows.</p>'

    return "\n".join(
        [
            "<section>",
            f"<h2>{_text(title)}</h2>",
            '<div class="table-wrap">',
            "<table>",
            f"<thead><tr>{header}</tr></thead>",
            f"<tbody>{body}</tbody>",
            "</table>",
            "</div>",
            limited,
            "</section>",
        ]
    )


def _extract(row: Mapping[str, object], path: Sequence[str]) -> object:
    current: object = row
    for key in path:
        current_map = _as_mapping(current)
        if not current_map:
            return None
        current = current_map.get(key)
    return current


def _value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return _text(f"{value:.4f}".rstrip("0").rstrip("."))
    if isinstance(value, int):
        return _text(str(value))
    if isinstance(value, Mapping):
        return _text(", ".join(f"{key}={item}" for key, item in value.items()))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return _text(", ".join(str(item) for item in value))
    return _text(str(value))


def _text(value: str) -> str:
    return escape(value, quote=True)


_STYLE = """
:root {
  color-scheme: light;
  --bg: #f7f8fa;
  --ink: #17202a;
  --muted: #5d6875;
  --line: #d8dde4;
  --surface: #ffffff;
  --accent: #0f766e;
  --accent-2: #334155;
  --warning: #9a3412;
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
  line-height: 1.5;
}
main {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 32px 0 48px;
}
header {
  border-bottom: 1px solid var(--line);
  padding-bottom: 20px;
}
.eyebrow {
  color: var(--accent);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  margin: 0 0 6px;
  text-transform: uppercase;
}
h1 {
  font-size: clamp(2rem, 4vw, 3.5rem);
  line-height: 1.05;
  margin: 0;
}
h2 {
  color: var(--accent-2);
  font-size: 1.08rem;
  margin: 32px 0 10px;
}
h3 {
  font-size: 0.98rem;
  margin: 0 0 10px;
}
.metadata {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 10px 18px;
  margin: 20px 0 0;
}
.metadata dt,
.summary dt {
  color: var(--muted);
  font-size: 0.78rem;
  text-transform: uppercase;
}
.metadata dd,
.summary dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 10px;
  margin: 22px 0 6px;
}
.metric,
.summary {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
}
.metric span {
  color: var(--muted);
  display: block;
  font-size: 0.78rem;
  text-transform: uppercase;
}
.metric strong {
  display: block;
  font-size: 1.8rem;
  line-height: 1.1;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.summary dl {
  display: grid;
  grid-template-columns: minmax(140px, 1fr) minmax(80px, 1fr);
  gap: 6px 16px;
  margin: 0;
}
.table-wrap {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow-x: auto;
}
table {
  border-collapse: collapse;
  min-width: 100%;
}
th,
td {
  border-bottom: 1px solid var(--line);
  padding: 9px 10px;
  text-align: left;
  vertical-align: top;
}
th {
  background: #eef2f6;
  color: var(--accent-2);
  font-size: 0.76rem;
  text-transform: uppercase;
  white-space: nowrap;
}
td {
  font-size: 0.9rem;
  max-width: 360px;
  overflow-wrap: anywhere;
}
tbody tr:last-child td {
  border-bottom: 0;
}
.empty,
.limited {
  color: var(--muted);
}
.limited {
  margin: 8px 0 0;
}
@media (max-width: 760px) {
  main {
    width: min(100% - 20px, 1180px);
    padding-top: 22px;
  }
  .metadata,
  .metrics,
  .summary-grid {
    grid-template-columns: 1fr;
  }
  h1 {
    font-size: 2.1rem;
  }
}
""".strip()
