from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import median
from typing import Any

from swingmachine.contracts import (
    HistoricalBenchmarkComparison,
    HistoricalBreakdownBucketMetrics,
    HistoricalBreakdownReport,
    HistoricalConcentrationReport,
    HistoricalCostScenarioResult,
    HistoricalCostSensitivityReport,
    HistoricalDrawdownRecord,
    HistoricalEquityCurvePoint,
    HistoricalPerformanceReport,
    HistoricalPerformanceSummary,
    HistoricalTradeMetrics,
    ProviderPerformanceComparisonReport,
    ProviderPerformanceLeg,
)
from swingmachine.enums import ReviewStatus

TRADING_DAYS_PER_YEAR = 252.0
DEFAULT_ADDITIONAL_COST_BPS_SCENARIOS = (0.0, 5.0, 10.0, 25.0, 50.0)


def build_historical_performance_report(
    lifecycle_artifact_dir: str | Path,
    *,
    run_id: str | None = None,
    benchmark_symbol: str | None = None,
    benchmark_manifest_path: str | Path | None = None,
    benchmark_price_rows: Sequence[Mapping[str, Any]] | None = None,
    attribution_path: str | Path | None = None,
    attribution_rows: Sequence[Mapping[str, Any]] | None = None,
) -> HistoricalPerformanceReport:
    artifact_dir = Path(lifecycle_artifact_dir)
    replay_summary = _load_json_object(artifact_dir / "portfolio_lifecycle_replay_summary.json")
    session_state_payload = _load_json_object(
        artifact_dir / "portfolio_lifecycle_session_states.json"
    )
    position_payload = _load_json_object(artifact_dir / "portfolio_lifecycle_positions.json")
    trade_ledger_payload = _load_json_object_optional(
        artifact_dir / "portfolio_lifecycle_trade_ledger.json"
    )

    session_states = sorted(
        session_state_payload.get("session_states", []),
        key=lambda row: _parse_date(row["session_date"]),
    )
    if not session_states:
        raise ValueError("portfolio lifecycle session states are empty")

    equity_curve = _build_equity_curve(session_states)
    drawdown_records = _build_drawdown_records(equity_curve)
    returns = [point.daily_return for point in equity_curve if point.daily_return is not None]
    initial_equity = float(replay_summary.get("initial_equity", equity_curve[0].equity))
    final_equity = float(replay_summary.get("final_equity", equity_curve[-1].equity))
    total_return = _total_return(initial_equity, final_equity)
    start_date = equity_curve[0].session_date
    end_date = equity_curve[-1].session_date
    cagr = _cagr(initial_equity, final_equity, start_date, end_date)
    annualized_volatility = _annualized_volatility(returns)
    sharpe_ratio = _sharpe_ratio(returns)
    sortino_ratio = _sortino_ratio(returns)
    max_drawdown_record = min(drawdown_records, key=lambda item: item.drawdown, default=None)
    max_drawdown = min((point.drawdown for point in equity_curve), default=0.0)
    if benchmark_price_rows is None and benchmark_symbol and benchmark_manifest_path:
        benchmark_price_rows = load_benchmark_price_rows_from_manifest(
            benchmark_manifest_path,
            benchmark_symbol,
        )

    positions = position_payload.get("positions", [])
    trade_ledger_rows = trade_ledger_payload.get("trades", []) if trade_ledger_payload else []
    if attribution_rows is None and attribution_path is not None:
        attribution_rows = load_trade_attribution_rows(attribution_path)
    trade_attribution = _trade_attribution_by_setup_id(attribution_rows or ())
    trade_metrics = (
        _trade_metrics_from_trade_ledger(trade_ledger_rows)
        if trade_ledger_rows
        else _trade_metrics_from_positions(positions)
    )
    concentration = _concentration_from_session_states(session_states)
    cost_sensitivity = (
        _cost_sensitivity_from_trade_ledger(
            trade_ledger_rows,
            base_total_transaction_cost=trade_metrics.total_transaction_cost,
            initial_equity=initial_equity,
            base_final_equity=final_equity,
            base_total_return=total_return,
        )
        if trade_ledger_rows
        else _cost_sensitivity_from_positions(
            positions,
            cost_source=trade_metrics.source,
            base_total_transaction_cost=trade_metrics.total_transaction_cost,
            initial_equity=initial_equity,
            base_final_equity=final_equity,
            base_total_return=total_return,
        )
    )
    benchmark_comparison = (
        _build_benchmark_comparison(
            equity_curve,
            benchmark_symbol=benchmark_symbol,
            benchmark_price_rows=benchmark_price_rows,
            strategy_total_return=total_return,
            strategy_max_drawdown=max_drawdown,
        )
        if benchmark_symbol and benchmark_price_rows
        else None
    )
    breakdown = _breakdown_from_equity_curve_and_trades(
        equity_curve,
        _apply_trade_attribution(trade_ledger_rows, trade_attribution),
    )

    warnings: list[str] = []
    warnings.extend(trade_metrics.warnings)
    warnings.extend(concentration.warnings)
    warnings.extend(cost_sensitivity.warnings)
    if benchmark_symbol and benchmark_comparison is None:
        warnings.append(
            "Benchmark comparison requested but no aligned benchmark prices were available."
        )

    summary = HistoricalPerformanceSummary(
        panel_id=str(replay_summary.get("panel_id", session_state_payload.get("panel_id", ""))),
        run_id=run_id or artifact_dir.name,
        generated_at=datetime.now(UTC),
        source_artifact_dir=str(artifact_dir),
        status=ReviewStatus.WARN if warnings else ReviewStatus.PASS,
        start_date=start_date,
        end_date=end_date,
        session_count=len(equity_curve),
        initial_equity=initial_equity,
        final_equity=final_equity,
        total_return=total_return,
        cagr=cagr,
        annualized_volatility=annualized_volatility,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        max_drawdown=max_drawdown,
        max_drawdown_start_date=(
            max_drawdown_record.start_date if max_drawdown_record is not None else None
        ),
        max_drawdown_trough_date=(
            max_drawdown_record.trough_date if max_drawdown_record is not None else None
        ),
        max_drawdown_recovery_date=(
            max_drawdown_record.recovery_date if max_drawdown_record is not None else None
        ),
        trade_metrics=trade_metrics,
        concentration=concentration,
        cost_sensitivity=cost_sensitivity,
        benchmark_comparison=benchmark_comparison,
        breakdown=breakdown,
        warnings=tuple(warnings),
    )
    return HistoricalPerformanceReport(
        summary=summary,
        equity_curve=tuple(equity_curve),
        drawdown_records=tuple(drawdown_records),
    )


def write_historical_performance_report(
    report: HistoricalPerformanceReport,
    output_dir: str | Path,
) -> dict[str, str]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    summary_path = destination / "historical_performance_summary.json"
    curve_path = destination / "historical_equity_curve.json"
    drawdown_path = destination / "historical_drawdown_records.json"
    report_path = destination / "historical_performance_report.json"

    summary_path.write_text(
        json.dumps(report.summary.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    curve_path.write_text(
        json.dumps(
            [point.model_dump(mode="json") for point in report.equity_curve],
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    drawdown_path.write_text(
        json.dumps(
            [record.model_dump(mode="json") for record in report.drawdown_records],
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "summary": str(summary_path),
        "equity_curve": str(curve_path),
        "drawdowns": str(drawdown_path),
        "report": str(report_path),
    }


def build_provider_performance_comparison_report(
    *,
    left_summary_path: str | Path,
    right_summary_path: str | Path,
    left_provider: str,
    right_provider: str,
    comparison_id: str | None = None,
) -> ProviderPerformanceComparisonReport:
    left_path = Path(left_summary_path)
    right_path = Path(right_summary_path)
    left_payload = _load_json_object(left_path)
    right_payload = _load_json_object(right_path)
    left = _provider_performance_leg(left_payload, provider=left_provider, path=left_path)
    right = _provider_performance_leg(right_payload, provider=right_provider, path=right_path)
    blockers: list[str] = []
    warnings: list[str] = []
    if left.start_date != right.start_date or left.end_date != right.end_date:
        blockers.append("provider_performance_windows_do_not_match")
    if left.session_count != right.session_count:
        warnings.append("provider_session_counts_differ")
    if left.status is not ReviewStatus.PASS or right.status is not ReviewStatus.PASS:
        warnings.append("one_or_more_provider_performance_reports_not_pass")
    if left.benchmark_total_return is None or right.benchmark_total_return is None:
        warnings.append("one_or_more_provider_reports_missing_benchmark")

    excess_return_delta = None
    if left.excess_return is not None and right.excess_return is not None:
        excess_return_delta = left.excess_return - right.excess_return

    status = ReviewStatus.FAIL if blockers else ReviewStatus.WARN if warnings else ReviewStatus.PASS
    return ProviderPerformanceComparisonReport(
        comparison_id=comparison_id
        or f"{left_provider}_vs_{right_provider}:{left.start_date}:{left.end_date}",
        generated_at=datetime.now(UTC),
        status=status,
        left=left,
        right=right,
        total_return_delta=left.total_return - right.total_return,
        max_drawdown_delta=left.max_drawdown - right.max_drawdown,
        closed_trade_count_delta=left.closed_trade_count - right.closed_trade_count,
        net_pnl_delta=left.net_pnl - right.net_pnl,
        excess_return_delta=excess_return_delta,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )


def write_provider_performance_comparison_report(
    report: ProviderPerformanceComparisonReport,
    output_path: str | Path,
) -> str:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return str(destination)


def load_benchmark_price_rows_from_manifest(
    manifest_path: str | Path,
    benchmark_symbol: str,
) -> list[dict[str, object]]:
    from swingmachine.data_contracts import load_historical_panel_data

    panel = load_historical_panel_data(manifest_path)
    source = panel.features if panel.features is not None else panel.ohlcv
    price_column = "split_adj_close" if "split_adj_close" in source.columns else "raw_close"
    if price_column not in source.columns:
        raise ValueError(
            f"benchmark source for {benchmark_symbol} is missing split_adj_close/raw_close"
        )

    benchmark = source.loc[
        source["symbol"].astype(str) == benchmark_symbol,
        ["session_date", price_column],
    ].copy()
    if benchmark.empty:
        raise ValueError(f"benchmark symbol {benchmark_symbol} was not found in {manifest_path}")
    benchmark = benchmark.sort_values("session_date")
    benchmark = benchmark.rename(columns={price_column: "close"})
    return [
        {"session_date": row.session_date, "close": float(row.close)}
        for row in benchmark.itertuples(index=False)
    ]


def load_trade_attribution_rows(path: str | Path) -> list[dict[str, Any]]:
    payload = _load_json_object(Path(path))
    if "rows" in payload and isinstance(payload["rows"], list):
        return [dict(row) for row in payload["rows"]]
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
    raise ValueError(f"unsupported attribution payload shape at {path}")


def _build_equity_curve(
    session_states: Sequence[Mapping[str, Any]],
) -> list[HistoricalEquityCurvePoint]:
    points: list[HistoricalEquityCurvePoint] = []
    initial_equity = float(session_states[0]["equity"])
    previous_equity: float | None = None
    running_peak = 0.0
    for row in session_states:
        session_date = _parse_date(row["session_date"])
        equity = float(row["equity"])
        cash = float(row.get("cash", 0.0))
        running_peak = max(running_peak, equity)
        daily_return = None
        if previous_equity is not None and previous_equity > 0.0:
            daily_return = equity / previous_equity - 1.0
        cumulative_return = _total_return(initial_equity, equity)
        drawdown = equity / running_peak - 1.0 if running_peak > 0.0 else 0.0
        points.append(
            HistoricalEquityCurvePoint(
                session_date=session_date,
                equity=equity,
                cash=cash,
                open_position_count=int(row.get("open_position_count", 0)),
                pending_entry_count=int(row.get("pending_entry_count", 0)),
                daily_return=daily_return,
                cumulative_return=cumulative_return,
                running_peak_equity=running_peak,
                drawdown=drawdown,
                portfolio_heat=float(row.get("portfolio_heat", 0.0)),
                daily_new_risk=float(row.get("daily_new_risk", 0.0)),
            )
        )
        previous_equity = equity
    return points


def _build_drawdown_records(
    equity_curve: Sequence[HistoricalEquityCurvePoint],
) -> list[HistoricalDrawdownRecord]:
    if not equity_curve:
        return []

    records: list[HistoricalDrawdownRecord] = []
    peak_index = 0
    peak_date = equity_curve[0].session_date
    peak_equity = float(equity_curve[0].equity)
    in_drawdown = False
    trough_index = 0
    trough_date = peak_date
    trough_equity = peak_equity
    trough_drawdown = 0.0

    for index, point in enumerate(equity_curve):
        equity = float(point.equity)
        if equity >= peak_equity:
            if in_drawdown:
                records.append(
                    HistoricalDrawdownRecord(
                        start_date=peak_date,
                        trough_date=trough_date,
                        recovery_date=point.session_date,
                        peak_equity=peak_equity,
                        trough_equity=trough_equity,
                        drawdown=trough_drawdown,
                        duration_sessions=index - peak_index,
                        recovered=True,
                    )
                )
            peak_index = index
            peak_date = point.session_date
            peak_equity = equity
            in_drawdown = False
            trough_index = index
            trough_date = point.session_date
            trough_equity = equity
            trough_drawdown = 0.0
            continue

        drawdown = equity / peak_equity - 1.0 if peak_equity > 0.0 else 0.0
        if not in_drawdown:
            in_drawdown = True
            trough_index = index
            trough_date = point.session_date
            trough_equity = equity
            trough_drawdown = drawdown
        elif drawdown < trough_drawdown:
            trough_index = index
            trough_date = point.session_date
            trough_equity = equity
            trough_drawdown = drawdown

    if in_drawdown:
        records.append(
            HistoricalDrawdownRecord(
                start_date=peak_date,
                trough_date=trough_date,
                recovery_date=None,
                peak_equity=peak_equity,
                trough_equity=trough_equity,
                drawdown=trough_drawdown,
                duration_sessions=trough_index - peak_index,
                recovered=False,
            )
        )
    return records


def _trade_metrics_from_positions(
    positions: Sequence[Mapping[str, Any]],
) -> HistoricalTradeMetrics:
    closed_by_position_id: dict[str, Mapping[str, Any]] = {}
    for row in positions:
        if str(row.get("state", "")).upper() != "CLOSED":
            continue
        position_id = str(row.get("position_id") or "")
        if not position_id:
            continue
        closed_by_position_id[position_id] = row

    net_pnls: list[float] = []
    net_returns: list[float] = []
    for row in closed_by_position_id.values():
        entry_price = float(row.get("entry_price", 0.0))
        market_price = float(row.get("market_price", 0.0))
        quantity = float(row.get("quantity", 0.0))
        entry_notional = entry_price * quantity
        net_pnl = (market_price - entry_price) * quantity
        net_pnls.append(net_pnl)
        if entry_notional > 0.0:
            net_returns.append(net_pnl / entry_notional)

    winning = sum(1 for pnl in net_pnls if pnl > 0.0)
    losing = sum(1 for pnl in net_pnls if pnl < 0.0)
    gross_profit = sum(pnl for pnl in net_pnls if pnl > 0.0)
    gross_loss = abs(sum(pnl for pnl in net_pnls if pnl < 0.0))
    closed_count = len(net_pnls)
    warning = (
        "Trade metrics are derived from CLOSED lifecycle position snapshots, "
        "not a full trade fill/cost ledger."
    )

    return HistoricalTradeMetrics(
        closed_trade_count=closed_count,
        winning_trade_count=winning,
        losing_trade_count=losing,
        win_rate=winning / closed_count if closed_count else None,
        gross_pnl=sum(net_pnls),
        net_pnl=sum(net_pnls),
        average_net_pnl=sum(net_pnls) / closed_count if closed_count else None,
        average_net_return=sum(net_returns) / len(net_returns) if net_returns else None,
        median_net_return=median(net_returns) if net_returns else None,
        best_net_return=max(net_returns) if net_returns else None,
        worst_net_return=min(net_returns) if net_returns else None,
        profit_factor=gross_profit / gross_loss if gross_loss > 0.0 else None,
        expectancy=sum(net_pnls) / closed_count if closed_count else None,
        average_bars_held=None,
        total_transaction_cost=0.0,
        source="LIFECYCLE_POSITION_PROXY",
        warnings=(warning,),
    )


def _trade_metrics_from_trade_ledger(
    trades: Sequence[Mapping[str, Any]],
) -> HistoricalTradeMetrics:
    net_pnls = [float(row.get("net_pnl", 0.0)) for row in trades]
    gross_pnls = [float(row.get("gross_pnl", 0.0)) for row in trades]
    net_returns = [float(row.get("net_return", 0.0)) for row in trades]
    bars_held = [float(row.get("bars_held", 0.0)) for row in trades]
    total_transaction_cost = sum(float(row.get("total_transaction_cost", 0.0)) for row in trades)
    winning = sum(1 for pnl in net_pnls if pnl > 0.0)
    losing = sum(1 for pnl in net_pnls if pnl < 0.0)
    gross_profit = sum(pnl for pnl in net_pnls if pnl > 0.0)
    gross_loss = abs(sum(pnl for pnl in net_pnls if pnl < 0.0))
    trade_count = len(trades)
    return HistoricalTradeMetrics(
        closed_trade_count=trade_count,
        winning_trade_count=winning,
        losing_trade_count=losing,
        win_rate=winning / trade_count if trade_count else None,
        gross_pnl=sum(gross_pnls),
        net_pnl=sum(net_pnls),
        average_net_pnl=sum(net_pnls) / trade_count if trade_count else None,
        average_net_return=sum(net_returns) / len(net_returns) if net_returns else None,
        median_net_return=median(net_returns) if net_returns else None,
        best_net_return=max(net_returns) if net_returns else None,
        worst_net_return=min(net_returns) if net_returns else None,
        profit_factor=gross_profit / gross_loss if gross_loss > 0.0 else None,
        expectancy=sum(net_pnls) / trade_count if trade_count else None,
        average_bars_held=sum(bars_held) / len(bars_held) if bars_held else None,
        total_transaction_cost=total_transaction_cost,
        source="TRADE_LEDGER",
    )


def _cost_sensitivity_from_positions(
    positions: Sequence[Mapping[str, Any]],
    *,
    cost_source: str,
    base_total_transaction_cost: float,
    initial_equity: float,
    base_final_equity: float,
    base_total_return: float,
) -> HistoricalCostSensitivityReport:
    estimated_turnover = 0.0
    seen_position_ids: set[str] = set()
    for row in positions:
        if str(row.get("state", "")).upper() != "CLOSED":
            continue
        position_id = str(row.get("position_id") or "")
        if not position_id or position_id in seen_position_ids:
            continue
        seen_position_ids.add(position_id)
        entry_price = float(row.get("entry_price", 0.0))
        exit_price = float(row.get("market_price", 0.0))
        quantity = float(row.get("quantity", 0.0))
        if entry_price <= 0.0 or exit_price <= 0.0 or quantity <= 0.0:
            continue
        estimated_turnover += (entry_price + exit_price) * quantity

    scenarios: list[HistoricalCostScenarioResult] = []
    for additional_cost_bps in DEFAULT_ADDITIONAL_COST_BPS_SCENARIOS:
        additional_cost = estimated_turnover * additional_cost_bps / 10_000.0
        estimated_final_equity = max(base_final_equity - additional_cost, 0.0)
        estimated_total_return = _total_return(initial_equity, estimated_final_equity)
        scenarios.append(
            HistoricalCostScenarioResult(
                scenario_id=f"additional_{additional_cost_bps:g}bps",
                additional_cost_bps=additional_cost_bps,
                estimated_total_additional_cost=additional_cost,
                estimated_final_equity=estimated_final_equity,
                estimated_total_return=estimated_total_return,
                delta_vs_base_equity=estimated_final_equity - base_final_equity,
                delta_vs_base_return=estimated_total_return - base_total_return,
            )
        )

    warnings = (
        "Cost sensitivity uses lifecycle CLOSED position snapshot turnover, "
        "not a full trade fill/cost ledger.",
    )
    if estimated_turnover == 0.0:
        warnings = (
            "Cost sensitivity could not estimate turnover because no closed "
            "position snapshots were available.",
        )

    return HistoricalCostSensitivityReport(
        cost_source=cost_source,
        base_total_transaction_cost=base_total_transaction_cost,
        base_final_equity=base_final_equity,
        base_total_return=base_total_return,
        estimated_turnover=estimated_turnover,
        scenarios=tuple(scenarios),
        warnings=warnings,
    )


def _cost_sensitivity_from_trade_ledger(
    trades: Sequence[Mapping[str, Any]],
    *,
    base_total_transaction_cost: float,
    initial_equity: float,
    base_final_equity: float,
    base_total_return: float,
) -> HistoricalCostSensitivityReport:
    estimated_turnover = 0.0
    for row in trades:
        entry_price = float(row.get("entry_fill_price", 0.0))
        exit_price = float(row.get("exit_fill_price", 0.0))
        quantity = float(row.get("quantity", 0.0))
        if entry_price <= 0.0 or exit_price <= 0.0 or quantity <= 0.0:
            continue
        estimated_turnover += (entry_price + exit_price) * quantity

    return HistoricalCostSensitivityReport(
        cost_source="TRADE_LEDGER",
        base_total_transaction_cost=base_total_transaction_cost,
        base_final_equity=base_final_equity,
        base_total_return=base_total_return,
        estimated_turnover=estimated_turnover,
        scenarios=tuple(
            _cost_scenario_results(
                estimated_turnover=estimated_turnover,
                initial_equity=initial_equity,
                base_final_equity=base_final_equity,
                base_total_return=base_total_return,
            )
        ),
    )


def _cost_scenario_results(
    *,
    estimated_turnover: float,
    initial_equity: float,
    base_final_equity: float,
    base_total_return: float,
) -> list[HistoricalCostScenarioResult]:
    scenarios: list[HistoricalCostScenarioResult] = []
    for additional_cost_bps in DEFAULT_ADDITIONAL_COST_BPS_SCENARIOS:
        additional_cost = estimated_turnover * additional_cost_bps / 10_000.0
        estimated_final_equity = max(base_final_equity - additional_cost, 0.0)
        estimated_total_return = _total_return(initial_equity, estimated_final_equity)
        scenarios.append(
            HistoricalCostScenarioResult(
                scenario_id=f"additional_{additional_cost_bps:g}bps",
                additional_cost_bps=additional_cost_bps,
                estimated_total_additional_cost=additional_cost,
                estimated_final_equity=estimated_final_equity,
                estimated_total_return=estimated_total_return,
                delta_vs_base_equity=estimated_final_equity - base_final_equity,
                delta_vs_base_return=estimated_total_return - base_total_return,
            )
        )
    return scenarios


def _concentration_from_session_states(
    session_states: Sequence[Mapping[str, Any]],
) -> HistoricalConcentrationReport:
    max_sector_pct: float | None = None
    max_sector_name: str | None = None
    for row in session_states:
        equity = float(row.get("equity", 0.0))
        sector_exposure = row.get("sector_exposure") or {}
        if not isinstance(sector_exposure, Mapping) or equity <= 0.0:
            continue
        for sector, value in sector_exposure.items():
            exposure = float(value)
            pct = exposure if abs(exposure) <= 1.0 else exposure / equity
            if max_sector_pct is None or pct > max_sector_pct:
                max_sector_pct = pct
                max_sector_name = str(sector)

    return HistoricalConcentrationReport(
        max_open_position_count=max(
            int(row.get("open_position_count", 0)) for row in session_states
        ),
        max_pending_entry_count=max(
            int(row.get("pending_entry_count", 0)) for row in session_states
        ),
        max_portfolio_heat=max(float(row.get("portfolio_heat", 0.0)) for row in session_states),
        max_daily_new_risk=max(float(row.get("daily_new_risk", 0.0)) for row in session_states),
        max_single_sector_exposure_pct_equity=max_sector_pct,
        max_single_sector_exposure_sector=max_sector_name,
    )


def _build_benchmark_comparison(
    equity_curve: Sequence[HistoricalEquityCurvePoint],
    *,
    benchmark_symbol: str | None,
    benchmark_price_rows: Sequence[Mapping[str, Any]] | None,
    strategy_total_return: float,
    strategy_max_drawdown: float,
) -> HistoricalBenchmarkComparison | None:
    if not benchmark_symbol or not benchmark_price_rows:
        return None

    benchmark_by_date: dict[date, float] = {}
    for row in benchmark_price_rows:
        close = _first_present(row, ("close", "split_adj_close", "raw_close"))
        if close is None:
            continue
        benchmark_by_date[_parse_date(row["session_date"])] = float(close)

    aligned_dates = [
        point.session_date for point in equity_curve if point.session_date in benchmark_by_date
    ]
    if len(aligned_dates) < 2:
        return None

    start_date = aligned_dates[0]
    end_date = aligned_dates[-1]
    start_close = benchmark_by_date[start_date]
    end_close = benchmark_by_date[end_date]
    if start_close <= 0.0 or end_close <= 0.0:
        return None

    benchmark_return = end_close / start_close - 1.0
    benchmark_curve = [
        HistoricalEquityCurvePoint(
            session_date=session_date,
            equity=benchmark_by_date[session_date],
            cash=0.0,
            open_position_count=0,
            pending_entry_count=0,
            daily_return=None,
            cumulative_return=benchmark_by_date[session_date] / start_close - 1.0,
            running_peak_equity=max(
                benchmark_by_date[date_]
                for date_ in aligned_dates
                if date_ <= session_date
            ),
            drawdown=0.0,
        )
        for session_date in aligned_dates
    ]
    benchmark_running_peak = 0.0
    benchmark_drawdowns: list[float] = []
    for point in benchmark_curve:
        benchmark_running_peak = max(benchmark_running_peak, float(point.equity))
        benchmark_drawdowns.append(
            float(point.equity) / benchmark_running_peak - 1.0
            if benchmark_running_peak > 0.0
            else 0.0
        )

    strategy_return_by_date = {
        point.session_date: point.daily_return
        for point in equity_curve
        if point.daily_return is not None
    }
    benchmark_returns: list[float] = []
    strategy_returns: list[float] = []
    previous_close: float | None = None
    for session_date in aligned_dates:
        close = benchmark_by_date[session_date]
        if previous_close is not None and previous_close > 0.0:
            strategy_return = strategy_return_by_date.get(session_date)
            if strategy_return is not None:
                benchmark_returns.append(close / previous_close - 1.0)
                strategy_returns.append(strategy_return)
        previous_close = close

    return HistoricalBenchmarkComparison(
        benchmark_symbol=benchmark_symbol,
        start_date=start_date,
        end_date=end_date,
        benchmark_start_close=start_close,
        benchmark_end_close=end_close,
        strategy_total_return=strategy_total_return,
        benchmark_total_return=benchmark_return,
        excess_return=strategy_total_return - benchmark_return,
        strategy_max_drawdown=strategy_max_drawdown,
        benchmark_max_drawdown=min(benchmark_drawdowns, default=0.0),
        daily_return_correlation=_correlation(strategy_returns, benchmark_returns),
    )


def _breakdown_from_equity_curve_and_trades(
    equity_curve: Sequence[HistoricalEquityCurvePoint],
    trade_ledger_rows: Sequence[Mapping[str, Any]],
) -> HistoricalBreakdownReport:
    monthly_returns: dict[str, float] = {}
    yearly_returns: dict[str, float] = {}
    if not equity_curve:
        return HistoricalBreakdownReport(
            missing_breakdowns=("calendar", "entry_regime", "exit_reason", "sector")
        )

    first_by_month: dict[str, float] = {}
    last_by_month: dict[str, float] = {}
    first_by_year: dict[str, float] = {}
    last_by_year: dict[str, float] = {}
    for point in equity_curve:
        month_key = point.session_date.strftime("%Y-%m")
        year_key = point.session_date.strftime("%Y")
        first_by_month.setdefault(month_key, float(point.equity))
        first_by_year.setdefault(year_key, float(point.equity))
        last_by_month[month_key] = float(point.equity)
        last_by_year[year_key] = float(point.equity)

    for key, first_value in first_by_month.items():
        monthly_returns[key] = _total_return(first_value, last_by_month[key])
    for key, first_value in first_by_year.items():
        yearly_returns[key] = _total_return(first_value, last_by_year[key])
    missing_breakdowns: list[str] = []
    by_entry_regime = _trade_breakdown_bucket_metrics(
        trade_ledger_rows,
        "entry_regime_state",
    )
    by_exit_reason = _trade_breakdown_bucket_metrics(trade_ledger_rows, "exit_reason")
    by_sector = _trade_breakdown_bucket_metrics(trade_ledger_rows, "sector")
    by_setup_type = _trade_breakdown_bucket_metrics(
        trade_ledger_rows,
        "setup_type",
        include_unknown=False,
    )
    by_ranking_bucket = _trade_breakdown_bucket_metrics(
        trade_ledger_rows,
        "ranking_bucket",
        include_unknown=False,
    )
    if not trade_ledger_rows:
        missing_breakdowns.extend(("entry_regime", "exit_reason", "sector"))
    if not by_setup_type:
        missing_breakdowns.append("setup_type")
    if not by_ranking_bucket:
        missing_breakdowns.append("ranking_bucket")
    return HistoricalBreakdownReport(
        monthly_returns=monthly_returns,
        yearly_returns=yearly_returns,
        by_entry_regime=by_entry_regime,
        by_exit_reason=by_exit_reason,
        by_sector=by_sector,
        by_setup_type=by_setup_type,
        by_ranking_bucket=by_ranking_bucket,
        missing_breakdowns=tuple(missing_breakdowns),
    )


def _trade_breakdown_bucket_metrics(
    trades: Sequence[Mapping[str, Any]],
    field_name: str,
    *,
    include_unknown: bool = True,
) -> dict[str, HistoricalBreakdownBucketMetrics]:
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    for row in trades:
        key = row.get(field_name)
        if key is None or key == "":
            if not include_unknown:
                continue
            key = "UNKNOWN"
        buckets.setdefault(str(key), []).append(row)

    return {
        key: _trade_bucket_metrics(rows)
        for key, rows in sorted(buckets.items(), key=lambda item: item[0])
    }


def _trade_bucket_metrics(
    trades: Sequence[Mapping[str, Any]],
) -> HistoricalBreakdownBucketMetrics:
    net_pnls = [float(row.get("net_pnl", 0.0)) for row in trades]
    gross_pnls = [float(row.get("gross_pnl", 0.0)) for row in trades]
    net_returns = [float(row.get("net_return", 0.0)) for row in trades]
    total_transaction_cost = sum(float(row.get("total_transaction_cost", 0.0)) for row in trades)
    winning = sum(1 for pnl in net_pnls if pnl > 0.0)
    losing = sum(1 for pnl in net_pnls if pnl < 0.0)
    trade_count = len(trades)
    return HistoricalBreakdownBucketMetrics(
        trade_count=trade_count,
        winning_trade_count=winning,
        losing_trade_count=losing,
        win_rate=winning / trade_count if trade_count else None,
        gross_pnl=sum(gross_pnls),
        net_pnl=sum(net_pnls),
        average_net_return=sum(net_returns) / len(net_returns) if net_returns else None,
        total_transaction_cost=total_transaction_cost,
    )


def _trade_attribution_by_setup_id(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    attribution: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        setup_id = row.get("setup_id")
        if not setup_id:
            continue
        existing = attribution.get(str(setup_id))
        if existing is None or row.get("decision") in {"TRADE_CLOSED", "ACCEPTED_SETUP"}:
            attribution[str(setup_id)] = row
    return attribution


def _apply_trade_attribution(
    trades: Sequence[Mapping[str, Any]],
    attribution_by_setup_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for trade in trades:
        row = dict(trade)
        attribution = attribution_by_setup_id.get(str(row.get("setup_id")))
        if attribution is not None:
            setup_type = attribution.get("pattern_type") or attribution.get("setup_type")
            candidate_score_pct = _optional_floatish(attribution.get("candidate_score_pct"))
            rank = _optional_intish(attribution.get("rank"))
            if setup_type:
                row["setup_type"] = str(setup_type)
            if candidate_score_pct is not None:
                row["candidate_score_pct"] = candidate_score_pct
            if rank is not None:
                row["rank"] = rank
            ranking_bucket = _ranking_bucket(rank=rank, candidate_score_pct=candidate_score_pct)
            if ranking_bucket is not None:
                row["ranking_bucket"] = ranking_bucket
        enriched.append(row)
    return enriched


def _ranking_bucket(
    *,
    rank: int | None,
    candidate_score_pct: float | None,
) -> str | None:
    if rank is not None:
        if rank == 1:
            return "rank_001"
        if rank <= 3:
            return "rank_002_003"
        if rank <= 5:
            return "rank_004_005"
        return "rank_006_plus"
    if candidate_score_pct is None:
        return None
    if candidate_score_pct >= 0.95:
        return "score_95_100"
    if candidate_score_pct >= 0.90:
        return "score_90_95"
    if candidate_score_pct >= 0.80:
        return "score_80_90"
    return "score_lt_80"


def _optional_floatish(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_intish(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object at {path}")
    return data


def _load_json_object_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _load_json_object(path)


def _provider_performance_leg(
    payload: Mapping[str, Any],
    *,
    provider: str,
    path: Path,
) -> ProviderPerformanceLeg:
    benchmark = payload.get("benchmark_comparison") or {}
    trade_metrics = payload.get("trade_metrics") or {}
    return ProviderPerformanceLeg(
        provider=provider,
        summary_path=str(path),
        panel_id=str(payload["panel_id"]),
        status=ReviewStatus(str(payload["status"])),
        start_date=_parse_date(payload["start_date"]),
        end_date=_parse_date(payload["end_date"]),
        session_count=int(payload["session_count"]),
        total_return=float(payload["total_return"]),
        max_drawdown=float(payload["max_drawdown"]),
        closed_trade_count=int(trade_metrics.get("closed_trade_count", 0)),
        net_pnl=float(trade_metrics.get("net_pnl", 0.0)),
        benchmark_total_return=(
            float(benchmark["benchmark_total_return"])
            if "benchmark_total_return" in benchmark
            else None
        ),
        excess_return=(
            float(benchmark["excess_return"]) if "excess_return" in benchmark else None
        ),
        warnings=tuple(str(item) for item in payload.get("warnings", ())),
    )


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()


def _total_return(initial_equity: float, final_equity: float) -> float:
    if initial_equity <= 0.0:
        return 0.0
    return final_equity / initial_equity - 1.0


def _cagr(
    initial_equity: float,
    final_equity: float,
    start_date: date,
    end_date: date,
) -> float | None:
    elapsed_days = (end_date - start_date).days
    if initial_equity <= 0.0 or final_equity < 0.0 or elapsed_days <= 0:
        return None
    return (final_equity / initial_equity) ** (365.25 / elapsed_days) - 1.0


def _annualized_volatility(returns: Sequence[float]) -> float | None:
    if len(returns) < 2:
        return None
    standard_deviation = _sample_std(returns)
    if standard_deviation is None:
        return None
    return standard_deviation * math.sqrt(TRADING_DAYS_PER_YEAR)


def _sharpe_ratio(returns: Sequence[float]) -> float | None:
    if len(returns) < 2:
        return None
    standard_deviation = _sample_std(returns)
    if standard_deviation is None or standard_deviation == 0.0:
        return None
    return (sum(returns) / len(returns)) / standard_deviation * math.sqrt(TRADING_DAYS_PER_YEAR)


def _sortino_ratio(returns: Sequence[float]) -> float | None:
    if not returns:
        return None
    downside = [item for item in returns if item < 0.0]
    if len(downside) < 2:
        return None
    downside_deviation = math.sqrt(sum(item * item for item in downside) / (len(downside) - 1))
    if downside_deviation == 0.0:
        return None
    return (sum(returns) / len(returns)) / downside_deviation * math.sqrt(TRADING_DAYS_PER_YEAR)


def _sample_std(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((item - mean) ** 2 for item in values) / (len(values) - 1)
    return math.sqrt(variance)


def _correlation(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_std = _sample_std(left)
    right_std = _sample_std(right)
    if left_std in (None, 0.0) or right_std in (None, 0.0):
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    covariance = sum(
        (left_item - left_mean) * (right_item - right_mean)
        for left_item, right_item in zip(left, right, strict=True)
    ) / (len(left) - 1)
    return covariance / (left_std * right_std)


def _first_present(row: Mapping[str, Any], names: Sequence[str]) -> Any:
    for name in names:
        value = row.get(name)
        if value is not None:
            return value
    return None
