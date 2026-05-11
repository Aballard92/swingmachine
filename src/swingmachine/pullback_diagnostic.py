from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import median
from typing import Any

PATTERN_TYPE = "PULLBACK"
DEFAULT_REPORT_ROOT = Path("reports/swing_machine_v0_1")


@dataclass(frozen=True)
class PullbackDiagnosticInputPaths:
    attribution_dataset: Path
    scanner_material_decisions: Path
    lifecycle_trade_ledger: Path
    lifecycle_pending_orders: Path
    lifecycle_transitions: Path
    root_cause_report: Path
    traded_lifecycle_report: Path
    pattern_benchmark_report: Path
    cost_slippage_report: Path
    provider_comparison_report: Path
    null_denominator_report: Path
    feature_stability_report: Path


def default_pullback_diagnostic_input_paths(
    report_root: str | Path = DEFAULT_REPORT_ROOT,
) -> PullbackDiagnosticInputPaths:
    root = Path(report_root)
    return PullbackDiagnosticInputPaths(
        attribution_dataset=root
        / "feature_outcome_attribution_broad_feature_snapshot_20260507T224500Z"
        / "feature_outcome_attribution_dataset.json",
        scanner_material_decisions=root
        / "scanner_broad_research_20260507T164230Z"
        / "scanner_material_decisions.json",
        lifecycle_trade_ledger=root
        / "lifecycle_broad_research_20260507T155720Z"
        / "portfolio_lifecycle_trade_ledger.json",
        lifecycle_pending_orders=root
        / "lifecycle_broad_research_20260507T155720Z"
        / "portfolio_lifecycle_pending_orders.json",
        lifecycle_transitions=root
        / "lifecycle_broad_research_20260507T155720Z"
        / "portfolio_lifecycle_transitions.json",
        root_cause_report=root
        / "pullback_traded_vs_accepted_root_cause_20260508T081457Z"
        / "pullback_traded_vs_accepted_root_cause.json",
        traded_lifecycle_report=root
        / "traded_lifecycle_decomposition_broad_20260508T011500Z"
        / "traded_lifecycle_decomposition_report.json",
        pattern_benchmark_report=root
        / "pattern_specific_benchmark_diagnostic_broad_20260508T062913Z"
        / "pattern_specific_benchmark_diagnostic_report.json",
        cost_slippage_report=root
        / "cost_slippage_stress_broad_20260508T080525Z"
        / "cost_slippage_stress_report.json",
        provider_comparison_report=root
        / "provider_matched_attribution_contract_20260508T070500Z"
        / "provider_accepted_vs_near_miss_comparison"
        / "provider_accepted_vs_near_miss_comparison.json",
        null_denominator_report=root
        / "warmup_null_aware_denominator_audit_v2_20260508T082357Z"
        / "warmup_null_aware_denominator_audit.json",
        feature_stability_report=root
        / "feature_null_stability_audit_20260508T080049Z"
        / "feature_null_stability_audit.json",
    )


def build_pullback_fill_lifecycle_diagnostic(
    *,
    input_paths: PullbackDiagnosticInputPaths | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    paths = input_paths or default_pullback_diagnostic_input_paths()
    generated = generated_at or datetime.now(UTC)

    attribution = _load_json(paths.attribution_dataset)
    rows = list(attribution.get("rows", ()))
    accepted_pullback = [
        row
        for row in rows
        if row.get("pattern_type") == PATTERN_TYPE and row.get("decision") != "REJECTED"
    ]
    traded_accepted = [row for row in accepted_pullback if row.get("traded") is True]
    untraded_accepted = [row for row in accepted_pullback if row.get("traded") is not True]

    trade_ledger = _load_json(paths.lifecycle_trade_ledger)
    pending_orders = _load_json(paths.lifecycle_pending_orders)
    transitions = _load_json(paths.lifecycle_transitions)
    root_cause = _load_json(paths.root_cause_report)
    traded_lifecycle = _load_json(paths.traded_lifecycle_report)
    pattern_benchmark = _load_json(paths.pattern_benchmark_report)
    cost_slippage = _load_json(paths.cost_slippage_report)
    provider_comparison = _load_json(paths.provider_comparison_report)
    null_denominator = _load_json(paths.null_denominator_report)
    feature_stability = _load_json(paths.feature_stability_report)

    trades_by_setup_id = {
        str(trade.get("setup_id")): trade
        for trade in trade_ledger.get("trades", ())
        if trade.get("setup_id") is not None
    }
    pending_by_setup_id = _group_by_setup_id(pending_orders.get("pending_orders", ()))
    transitions_by_setup_id = _group_by_setup_id(transitions.get("transitions", ()))

    candidates = [
        _candidate_diagnostic_row(
            row,
            trade=trades_by_setup_id.get(str(row.get("setup_id"))),
            pending_orders=pending_by_setup_id.get(str(row.get("setup_id")), []),
            transitions=transitions_by_setup_id.get(str(row.get("setup_id")), []),
        )
        for row in accepted_pullback
    ]

    fill_summary = _fill_classification_summary(candidates)
    lifecycle_summary = _lifecycle_summary(candidates)
    sample_warnings = _sample_warnings(candidates)
    missing_fields = _missing_fields_table()
    verdict = _diagnostic_verdict(
        accepted_metrics=_population_metrics("all_accepted_pullback", accepted_pullback),
        traded_metrics=_population_metrics("traded_accepted_pullback", traded_accepted),
        fill_summary=fill_summary,
    )

    report = {
        "report_id": f"pullback_fill_lifecycle_diagnostic_{generated:%Y%m%dT%H%M%SZ}",
        "generated_at": generated.isoformat(),
        "status": "WARN",
        "scope": "offline_existing_artifacts_only",
        "pattern_type": PATTERN_TYPE,
        "verdict": verdict,
        "gate_status": {
            "paper_trading": "BLOCKED",
            "live_trading": "PROHIBITED",
            "broker_api_runtime_actions": "NOT_AUTHORIZED",
            "profile_building": "NOT_AUTHORIZED",
        },
        "source_artifacts": _source_artifacts(paths),
        "source_cross_checks": {
            "root_cause": _root_cause_summary(root_cause),
            "traded_lifecycle": _traded_lifecycle_summary(traded_lifecycle),
            "pattern_benchmark": _pattern_benchmark_summary(pattern_benchmark),
            "null_denominator": _status_summary(null_denominator),
            "feature_stability": _status_summary(feature_stability),
        },
        "populations": {
            "all_accepted_pullback": _population_metrics(
                "all_accepted_pullback",
                accepted_pullback,
            ),
            "traded_accepted_pullback": _population_metrics(
                "traded_accepted_pullback",
                traded_accepted,
            ),
            "untraded_accepted_pullback": _population_metrics(
                "untraded_accepted_pullback",
                untraded_accepted,
            ),
        },
        "fill_classification": fill_summary,
        "entry_fill_summary": _entry_fill_summary(candidates),
        "lifecycle_summary": lifecycle_summary,
        "benchmark_spy_excess": _benchmark_summary(accepted_pullback, candidates),
        "cost_slippage_stress": _cost_slippage_summary(cost_slippage),
        "provider_source_window_limitations": _provider_limitations(provider_comparison),
        "sample_size_and_concentration_warnings": sample_warnings,
        "missing_unavailable_fields": missing_fields,
        "candidate_rows": candidates,
        "implementation_notes": (
            "Filled/unfilled status is classified from existing trade-ledger and "
            "pending-order artifacts. Missing fields are reported as unavailable or "
            "derived; no target-hit, direct R multiple, or adverse-excursion values "
            "are invented."
        ),
    }
    return report


def write_pullback_fill_lifecycle_diagnostic(
    report: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, str]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "pullback_fill_lifecycle_diagnostic.json"
    markdown_path = destination / "pullback_fill_lifecycle_diagnostic.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(markdown_path)}


def write_timestamped_pullback_fill_lifecycle_diagnostic(
    *,
    report_root: str | Path = DEFAULT_REPORT_ROOT,
    generated_at: datetime | None = None,
) -> dict[str, str]:
    generated = generated_at or datetime.now(UTC)
    report = build_pullback_fill_lifecycle_diagnostic(generated_at=generated)
    output_dir = (
        Path(report_root) / f"pullback_fill_lifecycle_diagnostic_{generated:%Y%m%dT%H%M%SZ}"
    )
    return write_pullback_fill_lifecycle_diagnostic(report, output_dir)


def _candidate_diagnostic_row(
    row: dict[str, Any],
    *,
    trade: dict[str, Any] | None,
    pending_orders: list[dict[str, Any]],
    transitions: list[dict[str, Any]],
) -> dict[str, Any]:
    fill_classification = _fill_classification(trade, pending_orders)
    transition_path = [
        {
            "session_date": transition.get("session_date"),
            "from_state": transition.get("from_state"),
            "to_state": transition.get("to_state"),
            "trigger": transition.get("trigger"),
            "reason_codes": transition.get("reason_codes") or [],
        }
        for transition in transitions
    ]
    filled_order = next(
        (order for order in pending_orders if order.get("status") == "FILLED"),
        None,
    )
    first_order = pending_orders[0] if pending_orders else {}
    cancel_reasons = sorted(
        {
            str(order.get("cancel_reason"))
            for order in pending_orders
            if order.get("cancel_reason") is not None
        }
    )
    entry_fill_date = (trade or {}).get("entry_fill_date") or row.get("entry_fill_date")
    return {
        "symbol": row.get("symbol"),
        "signal_session": row.get("signal_session"),
        "next_session": row.get("next_session"),
        "setup_id": row.get("setup_id"),
        "candidate_id": row.get("candidate_id"),
        "traded": row.get("traded") is True,
        "fill_classification": fill_classification,
        "order_statuses": [order.get("status") for order in pending_orders],
        "order_type": (filled_order or first_order).get("order_type"),
        "cancel_reasons": cancel_reasons,
        "entry_fill_date": entry_fill_date,
        "entry_fill_price": None if trade is None else trade.get("entry_fill_price"),
        "entry_reference_price": None if trade is None else trade.get("entry_reference_price"),
        "fill_delay_sessions": _date_delta(row.get("next_session"), entry_fill_date),
        "exit_fill_date": (trade or {}).get("exit_fill_date") or row.get("exit_fill_date"),
        "exit_reason": (trade or {}).get("exit_reason") or row.get("exit_reason"),
        "bars_held": (trade or {}).get("bars_held") or row.get("bars_held"),
        "initial_stop": None if trade is None else trade.get("initial_stop"),
        "final_stop": None if trade is None else trade.get("final_stop"),
        "stop_hit": _stop_hit((trade or {}).get("exit_reason") or row.get("exit_reason")),
        "target_hit": None,
        "target_hit_availability": "NOT_FOUND",
        "net_pnl": (trade or {}).get("net_pnl") if trade is not None else row.get("net_pnl"),
        "net_return": (
            (trade or {}).get("net_return") if trade is not None else row.get("net_return")
        ),
        "r_multiple": _r_multiple(trade),
        "r_multiple_availability": "DERIVED_FOR_FILLED_TRADES"
        if _r_multiple(trade) is not None
        else "NOT_FOUND",
        "max_adverse_excursion": None,
        "max_adverse_excursion_availability": "NOT_FOUND",
        "forward_close_return_20d": _window_value(row, "forward_close_returns", "20"),
        "benchmark_forward_close_return_20d": _window_value(
            row,
            "benchmark_forward_close_returns",
            "20",
        ),
        "forward_close_excess_return_20d": _window_value(
            row,
            "forward_close_excess_returns",
            "20",
        ),
        "feature_snapshot": row.get("feature_snapshot") or {},
        "transition_path": transition_path,
    }


def _fill_classification(
    trade: dict[str, Any] | None,
    pending_orders: list[dict[str, Any]],
) -> str:
    if trade is not None:
        return "FILLED"
    statuses = {order.get("status") for order in pending_orders}
    if "FILLED" in statuses:
        return "FILLED_WITH_ORDER_NO_TRADE_LEDGER_MATCH"
    if "CANCELLED" in statuses:
        return "UNFILLED_CANCELLED"
    if pending_orders:
        return "UNKNOWN_PENDING_ORDER_EVIDENCE"
    return "UNKNOWN_NO_ORDER_EVIDENCE"


def _r_multiple(trade: dict[str, Any] | None) -> float | None:
    if trade is None:
        return None
    entry = _as_float(trade.get("entry_fill_price"))
    stop = _as_float(trade.get("initial_stop"))
    quantity = _as_float(trade.get("quantity"))
    pnl = _as_float(trade.get("net_pnl"))
    if entry is None or stop is None or quantity is None or pnl is None:
        return None
    risk = (entry - stop) * quantity
    if risk <= 0:
        return None
    return pnl / risk


def _population_metrics(population_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    symbols = [str(row.get("symbol")) for row in rows if row.get("symbol") is not None]
    setup_ids = [str(row.get("setup_id")) for row in rows if row.get("setup_id") is not None]
    traded_rows = [row for row in rows if row.get("traded") is True]
    net_pnls = [_as_float(row.get("net_pnl")) for row in traded_rows]
    net_pnls = [value for value in net_pnls if value is not None]
    net_returns = [_as_float(row.get("net_return")) for row in traded_rows]
    net_returns = [value for value in net_returns if value is not None]
    return {
        "population_id": population_id,
        "row_count": len(rows),
        "symbol_count": len(set(symbols)),
        "setup_count": len(set(setup_ids)),
        "symbols": sorted(set(symbols)),
        "traded_count": len(traded_rows),
        "trade_conversion_rate": len(traded_rows) / len(rows) if rows else None,
        "net_pnl": sum(net_pnls) if net_pnls else None,
        "win_rate": sum(1 for value in net_pnls if value > 0.0) / len(net_pnls)
        if net_pnls
        else None,
        "average_net_return": sum(net_returns) / len(net_returns) if net_returns else None,
        "median_net_return": median(net_returns) if net_returns else None,
        "forward_returns": _window_metrics(rows, "forward_close_returns"),
        "benchmark_forward_returns": _window_metrics(rows, "benchmark_forward_close_returns"),
        "forward_excess_returns": _window_metrics(rows, "forward_close_excess_returns"),
        "positive_excess_rates": _positive_window_rates(rows, "forward_close_excess_returns"),
    }


def _fill_classification_summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(candidate["fill_classification"]) for candidate in candidates)
    return {
        "counts": dict(sorted(counts.items())),
        "filled_count": counts.get("FILLED", 0)
        + counts.get("FILLED_WITH_ORDER_NO_TRADE_LEDGER_MATCH", 0),
        "unfilled_count": counts.get("UNFILLED_CANCELLED", 0),
        "unknown_count": counts.get("UNKNOWN_NO_ORDER_EVIDENCE", 0)
        + counts.get("UNKNOWN_PENDING_ORDER_EVIDENCE", 0),
        "classification_policy": (
            "FILLED requires a trade-ledger match or filled pending order. "
            "UNFILLED_CANCELLED requires cancelled order evidence. Rows without order "
            "or trade evidence are marked UNKNOWN, not inferred."
        ),
    }


def _entry_fill_summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    filled = [
        candidate for candidate in candidates if candidate["fill_classification"] == "FILLED"
    ]
    delays = [
        delay
        for delay in (candidate.get("fill_delay_sessions") for candidate in filled)
        if delay is not None
    ]
    order_type_counts = Counter(
        candidate.get("order_type") or "UNKNOWN" for candidate in candidates
    )
    return {
        "order_type_counts": dict(sorted(order_type_counts.items())),
        "cancel_reason_counts": dict(
            sorted(
                Counter(
                    reason
                    for candidate in candidates
                    for reason in candidate.get("cancel_reasons", [])
                ).items()
            )
        ),
        "filled_entry_fill_dates": [
            {
                "symbol": candidate["symbol"],
                "setup_id": candidate["setup_id"],
                "entry_fill_date": candidate["entry_fill_date"],
                "entry_fill_price": candidate["entry_fill_price"],
                "fill_delay_sessions": candidate["fill_delay_sessions"],
            }
            for candidate in filled
        ],
        "average_fill_delay_sessions": sum(delays) / len(delays) if delays else None,
    }


def _lifecycle_summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    filled = [
        candidate for candidate in candidates if candidate["fill_classification"] == "FILLED"
    ]
    bars_held = [
        int(candidate["bars_held"])
        for candidate in filled
        if candidate.get("bars_held") is not None
    ]
    exit_reason_counts = Counter(candidate.get("exit_reason") or "UNKNOWN" for candidate in filled)
    bars_held_bucket_counts = Counter(
        _bars_held_bucket(candidate.get("bars_held")) for candidate in filled
    )
    return {
        "exit_reason_counts": dict(sorted(exit_reason_counts.items())),
        "bars_held_bucket_counts": dict(sorted(bars_held_bucket_counts.items())),
        "average_bars_held": sum(bars_held) / len(bars_held) if bars_held else None,
        "transition_trigger_counts": dict(
            sorted(
                Counter(
                    transition.get("trigger") or "UNKNOWN"
                    for candidate in candidates
                    for transition in candidate.get("transition_path", [])
                ).items()
            )
        ),
        "stop_hit_policy": (
            "stop_hit is derived only from exit_reason INITIAL_STOP or TRAIL_STOP; no "
            "direct stop-hit boolean was found."
        ),
        "target_hit_policy": (
            "target_hit is unavailable because no direct target-hit field was found."
        ),
    }


def _benchmark_summary(
    rows: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    by_fill = {
        classification: [
            row
            for row, candidate in zip(rows, candidates, strict=True)
            if candidate["fill_classification"] == classification
        ]
        for classification in sorted(
            {str(candidate["fill_classification"]) for candidate in candidates}
        )
    }
    return {
        "all_accepted": _window_metrics(rows, "forward_close_excess_returns"),
        "by_fill_classification": {
            classification: _window_metrics(group_rows, "forward_close_excess_returns")
            for classification, group_rows in by_fill.items()
        },
        "available_windows": sorted(
            {
                window
                for row in rows
                for window in (row.get("forward_close_excess_returns") or {}).keys()
            },
            key=int,
        ),
        "missing_40_day_window": "40" not in {
            window
            for row in rows
            for window in (row.get("forward_close_excess_returns") or {}).keys()
        },
    }


def _cost_slippage_summary(cost_slippage: dict[str, Any]) -> dict[str, Any]:
    by_pattern = cost_slippage.get("by_pattern") or {}
    pullback = by_pattern.get(PATTERN_TYPE) or {}
    return {
        "report_status": cost_slippage.get("status"),
        "conclusion": cost_slippage.get("conclusion"),
        "scenario_extra_round_trip_cost_bps": cost_slippage.get(
            "scenario_extra_round_trip_cost_bps",
            [],
        ),
        "pullback": pullback,
        "warnings": cost_slippage.get("warnings", []),
    }


def _provider_limitations(provider_comparison: dict[str, Any]) -> dict[str, Any]:
    providers = provider_comparison.get("providers") or provider_comparison.get("provider_metrics")
    return {
        "status": provider_comparison.get("status"),
        "decision": provider_comparison.get("decision") or provider_comparison.get("conclusion"),
        "scope": provider_comparison.get("scope"),
        "providers": providers,
        "policy": (
            "Provider evidence is a limitation/cross-check only. Broad Alpaca and "
            "contract-window Hugging Face rows are not merged into one population."
        ),
    }


def _sample_warnings(candidates: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    filled = [candidate for candidate in candidates if candidate["fill_classification"] == "FILLED"]
    symbols = Counter(str(candidate.get("symbol")) for candidate in candidates)
    filled_symbols = Counter(str(candidate.get("symbol")) for candidate in filled)
    if len(candidates) < 30:
        warnings.append("accepted PULLBACK sample below robust threshold of 30 rows")
    if len(filled) < 5:
        warnings.append("filled/traded PULLBACK sample below robust threshold of 5 trades")
    if len(filled_symbols) <= 1 and filled:
        warnings.append("filled/traded PULLBACK sample is concentrated in one symbol")
    if symbols:
        top_symbol, top_count = symbols.most_common(1)[0]
        if top_count / len(candidates) >= 0.5:
            warnings.append(
                f"accepted PULLBACK sample is concentrated: {top_symbol} is {top_count}/"
                f"{len(candidates)} rows"
            )
    warnings.append("backtests and diagnostics are evidence, not proof")
    warnings.append("diagnostic verdict does not authorize paper/live/broker actions")
    return warnings


def _missing_fields_table() -> list[dict[str, str]]:
    return [
        {
            "field": "filled",
            "status": "PARTIAL",
            "handling": (
                "Classified by joining trade ledger and pending orders; ambiguous rows "
                "stay UNKNOWN."
            ),
        },
        {
            "field": "target_hit",
            "status": "NOT_FOUND",
            "handling": "Reported unavailable; not inferred.",
        },
        {
            "field": "r_multiple",
            "status": "DERIVED_PARTIAL",
            "handling": (
                "Derived only for filled trades when entry price, initial stop, "
                "quantity, and PnL exist."
            ),
        },
        {
            "field": "max_adverse_excursion",
            "status": "NOT_FOUND",
            "handling": "Reported unavailable; not inferred.",
        },
        {
            "field": "per_trade_max_drawdown",
            "status": "NOT_FOUND",
            "handling": "Reported unavailable; aggregate drawdown artifacts are not substituted.",
        },
        {
            "field": "forward_40d",
            "status": "NOT_FOUND",
            "handling": "Primary attribution rows expose 1/5/10/20 day windows only.",
        },
        {
            "field": "unified_provider_population",
            "status": "NOT_ALLOWED",
            "handling": (
                "Alpaca and Hugging Face populations are not merged without provider policy."
            ),
        },
    ]


def _diagnostic_verdict(
    *,
    accepted_metrics: dict[str, Any],
    traded_metrics: dict[str, Any],
    fill_summary: dict[str, Any],
) -> dict[str, Any]:
    accepted_excess_20 = accepted_metrics["forward_excess_returns"].get("20", {}).get("mean")
    traded_excess_20 = traded_metrics["forward_excess_returns"].get("20", {}).get("mean")
    filled_count = fill_summary["filled_count"]
    reasons: list[str] = []
    if accepted_excess_20 is not None and accepted_excess_20 <= 0.0:
        reasons.append("accepted PULLBACK 20-session SPY-excess mean is not positive")
    if filled_count < 5:
        reasons.append("filled/traded PULLBACK sample remains below 5 trades")
    if traded_excess_20 is not None and traded_excess_20 > 0.0 and filled_count > 0:
        reasons.append("filled/traded subset is directionally positive but too small")
    if accepted_excess_20 is not None and accepted_excess_20 > 0.0 and filled_count >= 5:
        verdict = "GO"
        meaning = "ready to design a revised offline candidate-profile hypothesis only"
    elif (
        traded_excess_20 is not None
        and traded_excess_20 <= 0.0
        and accepted_excess_20 is not None
    ):
        verdict = "NO_GO"
        meaning = "park or reject PULLBACK as the current candidate lane"
    else:
        verdict = "INCONCLUSIVE"
        meaning = "more evidence or broader hypothesis search is needed"
    return {
        "verdict": verdict,
        "meaning": meaning,
        "reasons": reasons,
        "does_not_authorize": ["paper_trading", "live_trading", "broker_api", "profile_build"],
    }


def _render_markdown(report: dict[str, Any]) -> str:
    populations = report["populations"]
    verdict = report["verdict"]
    lines = [
        "# PULLBACK Fill/Lifecycle Diagnostic Report",
        "",
        f"Report: `{report['report_id']}`",
        "",
        f"Status: `{report['status']}`",
        "",
        f"Verdict: `{verdict['verdict']}`",
        "",
        f"Meaning: {verdict['meaning']}.",
        "",
        "## Gate Status",
        "",
        "| Gate | Status |",
        "| --- | --- |",
    ]
    lines.extend(f"| `{gate}` | `{status}` |" for gate, status in report["gate_status"].items())
    lines.extend(
        [
            "",
            "## Population Summary",
            "",
            "| Population | Rows | Symbols | Traded | Conversion | 20d excess mean | "
            "20d excess hit rate | Net PnL | Win rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for key in (
        "all_accepted_pullback",
        "traded_accepted_pullback",
        "untraded_accepted_pullback",
    ):
        lines.append(_population_markdown_row(populations[key]))
    lines.extend(
        [
            "",
            "## Fill Classification",
            "",
            "| Classification | Count |",
            "| --- | ---: |",
        ]
    )
    for classification, count in report["fill_classification"]["counts"].items():
        lines.append(f"| `{classification}` | {count} |")
    lines.extend(
        [
            "",
            report["fill_classification"]["classification_policy"],
            "",
            "## Entry/Fill Details",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Order type counts | `{report['entry_fill_summary']['order_type_counts']}` |",
            f"| Cancel reason counts | `{report['entry_fill_summary']['cancel_reason_counts']}` |",
            "| Average fill delay sessions | "
            f"{_fmt(report['entry_fill_summary']['average_fill_delay_sessions'])} |",
            "",
            "## Exit/Lifecycle Details",
            "",
            "| Metric | Value |",
            "| --- | --- |",
            f"| Exit reason counts | `{report['lifecycle_summary']['exit_reason_counts']}` |",
            "| Bars-held bucket counts | "
            f"`{report['lifecycle_summary']['bars_held_bucket_counts']}` |",
            f"| Average bars held | {_fmt(report['lifecycle_summary']['average_bars_held'])} |",
            "| Transition trigger counts | "
            f"`{report['lifecycle_summary']['transition_trigger_counts']}` |",
            "",
            "## Cost/Slippage Stress",
            "",
            "| Scenario | Net PnL | Win rate |",
            "| --- | ---: | ---: |",
        ]
    )
    scenario_metrics = (
        report["cost_slippage_stress"].get("pullback", {}).get("scenario_metrics", {})
    )
    for scenario, metrics in sorted(scenario_metrics.items(), key=lambda item: int(item[0])):
        lines.append(
            f"| `{scenario}bps` | {_fmt(metrics.get('net_pnl'))} | "
            f"{_fmt(metrics.get('win_rate'))} |"
        )
    lines.extend(
        [
            "",
            "## Provider / Source-Window Limitations",
            "",
            report["provider_source_window_limitations"]["policy"],
            "",
            f"Provider decision: `{report['provider_source_window_limitations'].get('decision')}`",
            "",
            "## Sample-Size And Concentration Warnings",
            "",
        ]
    )
    lines.extend(f"- {warning}" for warning in report["sample_size_and_concentration_warnings"])
    lines.extend(
        [
            "",
            "## Missing / Unavailable Fields",
            "",
            "| Field | Status | Handling |",
            "| --- | --- | --- |",
        ]
    )
    for row in report["missing_unavailable_fields"]:
        lines.append(f"| `{row['field']}` | `{row['status']}` | {row['handling']} |")
    lines.extend(
        [
            "",
            "## Verdict Reasons",
            "",
        ]
    )
    lines.extend(f"- {reason}" for reason in verdict["reasons"])
    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
        ]
    )
    lines.extend(
        f"- `{name}`: `{path}`" for name, path in report["source_artifacts"].items()
    )
    lines.append("")
    return "\n".join(lines)


def _population_markdown_row(metrics: dict[str, Any]) -> str:
    excess = metrics["forward_excess_returns"].get("20", {})
    return (
        f"| `{metrics['population_id']}` | {metrics['row_count']} | "
        f"{metrics['symbol_count']} | {metrics['traded_count']} | "
        f"{_fmt(metrics['trade_conversion_rate'])} | {_fmt(excess.get('mean'))} | "
        f"{_fmt(metrics['positive_excess_rates'].get('20'))} | {_fmt(metrics['net_pnl'])} | "
        f"{_fmt(metrics['win_rate'])} |"
    )


def _root_cause_summary(root_cause: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": root_cause.get("status"),
        "conclusion": root_cause.get("conclusion"),
        "recommendation": root_cause.get("recommendation"),
        "flags": root_cause.get("flags", []),
    }


def _traded_lifecycle_summary(traded_lifecycle: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": traded_lifecycle.get("status"),
        "conclusion": traded_lifecycle.get("conclusion"),
        "trade_count": traded_lifecycle.get("trade_count"),
        "warnings": traded_lifecycle.get("warnings", []),
    }


def _pattern_benchmark_summary(pattern_benchmark: dict[str, Any]) -> dict[str, Any]:
    pullback = (pattern_benchmark.get("patterns") or {}).get(PATTERN_TYPE, {})
    return {
        "status": pattern_benchmark.get("status"),
        "conclusion": pattern_benchmark.get("conclusion"),
        "pullback_recommendation": pullback.get("recommendation"),
        "pullback_sample_grade": pullback.get("sample_grade"),
    }


def _status_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "conclusion": payload.get("conclusion"),
        "report_id": payload.get("report_id"),
    }


def _source_artifacts(paths: PullbackDiagnosticInputPaths) -> dict[str, str]:
    return {field: str(getattr(paths, field)) for field in paths.__dataclass_fields__}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _group_by_setup_id(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        setup_id = row.get("setup_id")
        if setup_id is None:
            continue
        grouped.setdefault(str(setup_id), []).append(row)
    return grouped


def _window_metrics(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    windows = sorted(
        {
            window
            for row in rows
            for window in (row.get(field) or {}).keys()
            if str(window).isdigit()
        },
        key=int,
    )
    metrics: dict[str, dict[str, Any]] = {}
    for window in windows:
        values = [_as_float((row.get(field) or {}).get(window)) for row in rows]
        observed = [value for value in values if value is not None]
        metrics[window] = {
            "mean": sum(observed) / len(observed) if observed else None,
            "median": median(observed) if observed else None,
            "observed": len(observed),
        }
    return metrics


def _positive_window_rates(rows: list[dict[str, Any]], field: str) -> dict[str, float | None]:
    rates: dict[str, float | None] = {}
    for window, metrics in _window_metrics(rows, field).items():
        if metrics["observed"] == 0:
            rates[window] = None
            continue
        values = [_as_float((row.get(field) or {}).get(window)) for row in rows]
        observed = [value for value in values if value is not None]
        rates[window] = sum(1 for value in observed if value > 0.0) / len(observed)
    return rates


def _window_value(row: dict[str, Any], field: str, window: str) -> float | None:
    return _as_float((row.get(field) or {}).get(window))


def _date_delta(start: Any, end: Any) -> int | None:
    start_date = _parse_date(start)
    end_date = _parse_date(end)
    if start_date is None or end_date is None:
        return None
    return (end_date - start_date).days


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _stop_hit(exit_reason: Any) -> bool | None:
    if exit_reason in {"INITIAL_STOP", "TRAIL_STOP"}:
        return True
    if exit_reason is None:
        return None
    return False


def _bars_held_bucket(value: Any) -> str:
    bars = _as_float(value)
    if bars is None:
        return "bars_held:missing"
    if bars <= 3:
        return "bars_held:001_003"
    if bars <= 7:
        return "bars_held:004_007"
    if bars <= 14:
        return "bars_held:008_014"
    return "bars_held:015_plus"


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _fmt(value: Any) -> str:
    number = _as_float(value)
    if number is None:
        return ""
    return f"{number:.6f}"
