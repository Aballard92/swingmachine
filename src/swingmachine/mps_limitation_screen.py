"""Sequential absolute-return exploratory screen for SWING-PC-006."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Any

import pandas as pd

from swingmachine.mps_backtest import run_mps_backtest
from swingmachine.mps_config import MpsConfig, load_mps_config
from swingmachine.mps_contracts import (
    CorporateActionRecord,
    MpsBacktestResult,
    MpsCorporateActionType,
    MpsTrade,
    MpsVariant,
)
from swingmachine.mps_hypothesis_screen import (
    ACCEPTED_DATE_PLAN_SHA256,
    EXPECTED_CONFIG_HASH,
    EXPECTED_HASHES,
    file_sha256,
    research_eligibility_mask,
    temporal_plan_evidence,
)
from swingmachine.mps_signals import variant_signal_mask
from swingmachine.mps_validation import (
    annualized_sharpe,
    block_bootstrap_mean_ci,
    deflated_sharpe_ratio,
    diagnostic_as_dict,
    probability_of_backtest_overfitting,
)

TASK_ID = "SWING-PC-006"
INITIAL_CASH = 100_000.0
COST_SCENARIOS = (5, 10, 20, 50)
SCENARIOS = ("LAST_CLOSE", "TOTAL_LOSS")
VARIANTS = {
    "B0": MpsVariant.B0_RANK_ONLY,
    "H1": MpsVariant.B1_MOMENTUM_TREND,
    "H2": MpsVariant.B3_MOMENTUM_BREAKOUT,
}
PARTITIONS = {
    "discovery": (date(2008, 1, 2), date(2016, 1, 4)),
    "validation_1": (date(2016, 2, 18), date(2018, 2, 15)),
    "validation_2": (date(2018, 2, 16), date(2020, 2, 19)),
    "holdout": (date(2020, 12, 4), date(2025, 12, 10)),
}


def load_feature_partition(path: Path, start: date, end: date) -> pd.DataFrame:
    frame = pd.read_parquet(
        path,
        filters=[
            ("session_date", ">=", pd.Timestamp(start)),
            ("session_date", "<=", pd.Timestamp(end)),
        ],
    )
    frame["session_date"] = pd.to_datetime(frame["session_date"])
    return frame.sort_values(["session_date", "ticker", "security_id"]).reset_index(drop=True)


def build_research_actions(
    actions: pd.DataFrame,
    *,
    start: date,
    end: date,
) -> tuple[CorporateActionRecord, ...]:
    prepared = actions.copy()
    prepared["effective_date"] = pd.to_datetime(prepared["trading_date"]).dt.date
    prepared = prepared.loc[prepared["effective_date"].between(start, end, inclusive="both")]
    output: list[CorporateActionRecord] = []
    for row in prepared.itertuples(index=False):
        event_time = pd.Timestamp(row.event_time).to_pydatetime()
        available_at = pd.Timestamp(row.available_at).to_pydatetime()
        if float(row.split_factor) != 1.0:
            output.append(
                CorporateActionRecord(
                    event_time=event_time,
                    available_at=available_at,
                    source_version=str(row.source_file_sha256),
                    source_record_id=(f"{row.security_id}:{row.trading_date}:SPLIT"),
                    security_id=str(row.security_id),
                    action_type=MpsCorporateActionType.SPLIT,
                    effective_date=row.effective_date,
                    split_ratio=float(row.split_factor),
                )
            )
        if float(row.div_cash) != 0.0:
            output.append(
                CorporateActionRecord(
                    event_time=event_time,
                    available_at=available_at,
                    source_version=str(row.source_file_sha256),
                    source_record_id=(f"{row.security_id}:{row.trading_date}:DIVIDEND"),
                    security_id=str(row.security_id),
                    action_type=MpsCorporateActionType.CASH_DIVIDEND,
                    effective_date=row.effective_date,
                    payment_date=row.effective_date,
                    cash_dividend_per_share=float(row.div_cash),
                )
            )
    return tuple(sorted(output, key=lambda item: (item.effective_date, item.source_record_id)))


def _trade_row(trade: MpsTrade, scenario: str) -> dict[str, Any]:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario}")
    terminal = trade.exit_reason == "UNRESOLVED_DELISTING_LAST_CLOSE"
    removed_proceeds = (
        trade.exit_fill_price * trade.exit_quantity
        if scenario == "TOTAL_LOSS" and terminal
        else 0.0
    )
    net_pnl = trade.net_pnl - removed_proceeds
    entry_cash = trade.entry_fill_price * trade.entry_quantity
    initial_risk = (trade.entry_fill_price - trade.initial_stop) * trade.entry_quantity
    return {
        "security_id": trade.security_id,
        "ticker": trade.ticker,
        "entry_session": trade.entry_session,
        "exit_session": trade.exit_session,
        "exit_reason": trade.exit_reason,
        "net_pnl": net_pnl,
        "trade_return": net_pnl / entry_cash,
        "realised_r": net_pnl / initial_risk,
        "holding_sessions": trade.holding_sessions,
        "mfe_r": trade.mfe_r,
        "mae_r": trade.mae_r,
        "terminal_total_loss_adjustment": removed_proceeds,
    }


def scenario_trade_rows(
    results: Sequence[MpsBacktestResult],
    scenario: str,
) -> list[dict[str, Any]]:
    return [_trade_row(trade, scenario) for result in results for trade in result.trades]


def scenario_equity(result: MpsBacktestResult, scenario: str) -> pd.Series:
    series = pd.Series(
        {point.session_date: point.equity for point in result.equity_curve},
        dtype=float,
    ).sort_index()
    if scenario == "LAST_CLOSE":
        return series
    if scenario != "TOTAL_LOSS":
        raise ValueError(f"unknown scenario {scenario}")
    adjustments: defaultdict[date, float] = defaultdict(float)
    for trade in result.trades:
        if trade.exit_reason == "UNRESOLVED_DELISTING_LAST_CLOSE":
            adjustments[trade.exit_session] += trade.exit_fill_price * trade.exit_quantity
    cumulative = 0.0
    adjusted = series.copy()
    for session in adjusted.index:
        cumulative += adjustments[session]
        adjusted.loc[session] -= cumulative
    if adjusted.le(0.0).any():
        raise ValueError("total-loss scenario exhausted account equity")
    return adjusted


def daily_returns(result: MpsBacktestResult, scenario: str) -> tuple[float, ...]:
    equity = scenario_equity(result, scenario)
    previous = pd.concat(
        [pd.Series([INITIAL_CASH]), equity.reset_index(drop=True).iloc[:-1]],
        ignore_index=True,
    )
    values = equity.reset_index(drop=True) / previous - 1.0
    return tuple(float(value) for value in values)


def _maximum_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1.0).min())


def aggregate_metrics(
    results: Sequence[MpsBacktestResult],
    scenario: str,
) -> dict[str, Any]:
    rows = scenario_trade_rows(results, scenario)
    daily = tuple(value for result in results for value in daily_returns(result, scenario))
    equities = [scenario_equity(result, scenario) for result in results]
    tickers = Counter(str(row["ticker"]) for row in rows)
    years = Counter(row["exit_session"].year for row in rows)
    exits = Counter(str(row["exit_reason"]) for row in rows)
    net_by_ticker: defaultdict[str, float] = defaultdict(float)
    net_by_year: defaultdict[int, float] = defaultdict(float)
    for row in rows:
        net_by_ticker[str(row["ticker"])] += float(row["net_pnl"])
        net_by_year[row["exit_session"].year] += float(row["net_pnl"])
    total_net = sum(float(row["net_pnl"]) for row in rows)
    positive = sum(max(float(row["net_pnl"]), 0.0) for row in rows)
    negative = -sum(min(float(row["net_pnl"]), 0.0) for row in rows)
    count = len(rows)
    return {
        "scenario": scenario,
        "completed_trades": count,
        "traded_securities": len(tickers),
        "net_pnl": total_net,
        "mean_trade_return": mean([float(row["trade_return"]) for row in rows]) if rows else None,
        "median_trade_return": median([float(row["trade_return"]) for row in rows])
        if rows
        else None,
        "mean_realised_r": mean([float(row["realised_r"]) for row in rows]) if rows else None,
        "median_realised_r": median([float(row["realised_r"]) for row in rows]) if rows else None,
        "win_rate": sum(float(row["net_pnl"]) > 0.0 for row in rows) / count if count else None,
        "profit_factor": positive / negative if negative > 0.0 else None,
        "average_hold": mean([int(row["holding_sessions"]) for row in rows]) if rows else None,
        "mean_mfe_r": mean([float(row["mfe_r"]) for row in rows]) if rows else None,
        "mean_mae_r": mean([float(row["mae_r"]) for row in rows]) if rows else None,
        "compounded_return": (
            float(pd.Series([1.0 + value for value in daily], dtype=float).prod() - 1.0)
            if daily
            else 0.0
        ),
        "annualized_sharpe": annualized_sharpe(daily),
        "maximum_drawdown": min(
            (_maximum_drawdown(equity) for equity in equities),
            default=0.0,
        ),
        "maximum_symbol_trade_share": max(tickers.values()) / count if count else None,
        "maximum_year_trade_share": max(years.values()) / count if count else None,
        "maximum_exit_trade_share": max(exits.values()) / count if count else None,
        "leave_one_security_out_min_net_pnl": min(
            (total_net - value for value in net_by_ticker.values()),
            default=None,
        ),
        "leave_one_year_out_min_net_pnl": min(
            (total_net - value for value in net_by_year.values()),
            default=None,
        ),
        "trades_by_symbol": dict(sorted(tickers.items())),
        "trades_by_year": {str(key): value for key, value in sorted(years.items())},
        "trades_by_exit": dict(sorted(exits.items())),
        "terminal_trade_count": sum(
            row["exit_reason"] == "UNRESOLVED_DELISTING_LAST_CLOSE" for row in rows
        ),
        "daily_returns": daily,
    }


def _serialize_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metrics.items() if key != "daily_returns"}


def _stage_operational_counts(result: MpsBacktestResult) -> dict[str, Any]:
    submitted = sum(
        int(event["candidate_count"])
        for event in result.audit_events
        if event["event"] == "DECISION_AUDIT"
    )
    fills = sum(event["event"] == "ENTRY_FILLED" for event in result.audit_events)
    return {
        "submitted_entries": submitted,
        "entry_fills": fills,
        "rejected_entries": len(result.rejected_orders),
        "fill_rate": fills / submitted if submitted else None,
    }


def run_stage(
    *,
    name: str,
    feature_path: Path,
    all_actions: pd.DataFrame,
    config: MpsConfig,
    data_version_hash: str,
) -> tuple[
    dict[str, Any],
    dict[str, dict[int, MpsBacktestResult]],
]:
    start, end = PARTITIONS[name]
    features = load_feature_partition(feature_path, start, end)
    eligible = research_eligibility_mask(features, config)
    features["eligible_universe"] = eligible
    regime = pd.DataFrame(
        {
            "session_date": sorted(features["session_date"].unique()),
            "regime_multiplier": 1.0,
        }
    )
    actions = build_research_actions(all_actions, start=start, end=end)
    bundles: dict[str, dict[int, MpsBacktestResult]] = {}
    report_variants: dict[str, Any] = {}
    for label, variant in VARIANTS.items():
        raw_signals = int(variant_signal_mask(features, variant, config).sum())
        cost_results: dict[int, MpsBacktestResult] = {}
        cost_report: dict[str, Any] = {}
        for cost in COST_SCENARIOS:
            result = run_mps_backtest(
                features,
                regime,
                config,
                variant,
                data_version_hash=data_version_hash,
                cost_bps=float(cost),
                corporate_actions=actions,
                common_lifecycle_policy=True,
                research_ex_date_dividends=True,
                force_unresolved_delisting_last_close=True,
            )
            cost_results[cost] = result
            cost_report[str(cost)] = {
                scenario: _serialize_metrics(aggregate_metrics((result,), scenario))
                for scenario in SCENARIOS
            }
        bundles[label] = cost_results
        report_variants[label] = {
            "variant": variant.value,
            "raw_signal_rows": raw_signals,
            **_stage_operational_counts(cost_results[5]),
            "cost_scenarios_bps": cost_report,
        }
    return (
        {
            "partition": name,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "rows": len(features),
            "research_eligible_rows": int(eligible.sum()),
            "research_eligible_symbols": int(features.loc[eligible, "security_id"].nunique()),
            "corporate_action_records": len(actions),
            "variants": report_variants,
        },
        bundles,
    )


def gate_one(bundles: dict[str, dict[int, MpsBacktestResult]]) -> dict[str, Any]:
    families: dict[str, Any] = {}
    for label in ("H1", "H2"):
        scenario_results: dict[str, Any] = {}
        for scenario in SCENARIOS:
            baseline = aggregate_metrics((bundles[label][5],), scenario)
            stress = aggregate_metrics((bundles[label][20],), scenario)
            checks = {
                "minimum_completed_trades": baseline["completed_trades"] >= 20,
                "minimum_traded_securities": baseline["traded_securities"] >= 4,
                "positive_mean_realised_r": (
                    baseline["mean_realised_r"] is not None and baseline["mean_realised_r"] > 0.0
                ),
                "positive_median_realised_r": (
                    baseline["median_realised_r"] is not None
                    and baseline["median_realised_r"] > 0.0
                ),
                "positive_20bps_mean_trade_return": (
                    stress["mean_trade_return"] is not None and stress["mean_trade_return"] > 0.0
                ),
                "maximum_drawdown": baseline["maximum_drawdown"] >= -0.12,
                "symbol_concentration": (
                    baseline["maximum_symbol_trade_share"] is not None
                    and baseline["maximum_symbol_trade_share"] <= 0.35
                ),
                "year_concentration": (
                    baseline["maximum_year_trade_share"] is not None
                    and baseline["maximum_year_trade_share"] <= 0.40
                ),
                "leave_one_security_out_positive": (
                    baseline["leave_one_security_out_min_net_pnl"] is not None
                    and baseline["leave_one_security_out_min_net_pnl"] > 0.0
                ),
            }
            scenario_results[scenario] = {
                "pass": all(checks.values()),
                "checks": checks,
            }
        families[label] = {
            "pass": all(scenario_results[scenario]["pass"] for scenario in SCENARIOS),
            "scenarios": scenario_results,
        }
    passed = [label for label, result in families.items() if result["pass"]]
    return {
        "gate": "GATE_1_DISCOVERY",
        "pass": bool(passed),
        "passing_families": passed,
        "families": families,
    }


def gate_two(
    validation: Sequence[dict[str, dict[int, MpsBacktestResult]]],
    eligible_families: Sequence[str],
) -> dict[str, Any]:
    families: dict[str, Any] = {}
    pbo_by_scenario: dict[str, Any] = {}
    for scenario in SCENARIOS:
        returns_by_variant = {
            label: tuple(
                value
                for window in validation
                for value in daily_returns(window[label][5], scenario)
            )
            for label in VARIANTS
        }
        pbo_by_scenario[scenario] = diagnostic_as_dict(
            probability_of_backtest_overfitting(returns_by_variant)
        )
    for label in eligible_families:
        scenario_results: dict[str, Any] = {}
        for scenario in SCENARIOS:
            baseline_results = tuple(window[label][5] for window in validation)
            stress_results = tuple(window[label][20] for window in validation)
            pooled = aggregate_metrics(baseline_results, scenario)
            stress = aggregate_metrics(stress_results, scenario)
            per_window = [aggregate_metrics((result,), scenario) for result in baseline_results]
            daily = tuple(
                value for result in baseline_results for value in daily_returns(result, scenario)
            )
            sharpe = annualized_sharpe(daily)
            dsr = deflated_sharpe_ratio(sharpe, daily, trials=2) if sharpe is not None else None
            pbo = pbo_by_scenario[scenario]
            checks = {
                "minimum_three_each_window": all(
                    metrics["completed_trades"] >= 3 for metrics in per_window
                ),
                "minimum_fifteen_pooled": pooled["completed_trades"] >= 15,
                "positive_mean_realised_r": (
                    pooled["mean_realised_r"] is not None and pooled["mean_realised_r"] > 0.0
                ),
                "positive_median_realised_r": (
                    pooled["median_realised_r"] is not None and pooled["median_realised_r"] > 0.0
                ),
                "positive_20bps_mean_trade_return": (
                    stress["mean_trade_return"] is not None and stress["mean_trade_return"] > 0.0
                ),
                "positive_each_window": all(
                    metrics["compounded_return"] > 0.0 for metrics in per_window
                ),
                "drawdown_each_window": all(
                    metrics["maximum_drawdown"] >= -0.12 for metrics in per_window
                ),
                "leave_one_security_out_positive": (
                    pooled["leave_one_security_out_min_net_pnl"] is not None
                    and pooled["leave_one_security_out_min_net_pnl"] > 0.0
                ),
                "deflated_sharpe": (
                    dsr is not None
                    and dsr.status == "OK"
                    and dsr.value is not None
                    and dsr.value >= 0.95
                ),
                "pbo": (pbo["status"] == "OK" and pbo["value"] is not None and pbo["value"] < 0.50),
            }
            scenario_results[scenario] = {
                "pass": all(checks.values()),
                "checks": checks,
                "pooled_baseline": _serialize_metrics(pooled),
                "pooled_20bps": _serialize_metrics(stress),
                "per_window_baseline": [_serialize_metrics(metrics) for metrics in per_window],
                "deflated_sharpe": (diagnostic_as_dict(dsr) if dsr is not None else None),
                "pbo": pbo,
            }
        families[label] = {
            "pass": all(scenario_results[scenario]["pass"] for scenario in SCENARIOS),
            "scenarios": scenario_results,
        }
    passed = [label for label, result in families.items() if result["pass"]]
    return {
        "gate": "GATE_2_WALK_FORWARD",
        "pass": bool(passed),
        "passing_families": passed,
        "pbo_by_scenario": pbo_by_scenario,
        "families": families,
    }


def gate_three(
    *,
    discovery: dict[str, dict[int, MpsBacktestResult]],
    validation: Sequence[dict[str, dict[int, MpsBacktestResult]]],
    holdout: dict[str, dict[int, MpsBacktestResult]],
    eligible_families: Sequence[str],
) -> dict[str, Any]:
    families: dict[str, Any] = {}
    for label in eligible_families:
        scenario_results: dict[str, Any] = {}
        for scenario in SCENARIOS:
            study_results = (
                discovery[label][5],
                *(window[label][5] for window in validation),
                holdout[label][5],
            )
            full = aggregate_metrics(study_results, scenario)
            hold = aggregate_metrics((holdout[label][5],), scenario)
            hold_stress = aggregate_metrics((holdout[label][20],), scenario)
            bootstrap = block_bootstrap_mean_ci(
                daily_returns(holdout[label][5], scenario),
                block_size=20,
                samples=2_000,
                confidence=0.95,
                seed=1,
            )
            checks = {
                "minimum_full_study_trades": full["completed_trades"] >= 30,
                "minimum_holdout_trades": hold["completed_trades"] >= 10,
                "minimum_full_study_securities": full["traded_securities"] >= 5,
                "minimum_holdout_securities": hold["traded_securities"] >= 3,
                "full_symbol_concentration": (
                    full["maximum_symbol_trade_share"] is not None
                    and full["maximum_symbol_trade_share"] <= 0.35
                ),
                "holdout_symbol_concentration": (
                    hold["maximum_symbol_trade_share"] is not None
                    and hold["maximum_symbol_trade_share"] <= 0.35
                ),
                "positive_mean_realised_r": (
                    hold["mean_realised_r"] is not None and hold["mean_realised_r"] > 0.0
                ),
                "positive_median_realised_r": (
                    hold["median_realised_r"] is not None and hold["median_realised_r"] > 0.0
                ),
                "positive_20bps_mean_trade_return": (
                    hold_stress["mean_trade_return"] is not None
                    and hold_stress["mean_trade_return"] > 0.0
                ),
                "positive_daily_mean": mean(daily_returns(holdout[label][5], scenario)) > 0.0,
                "positive_bootstrap_lower": (
                    bootstrap.status == "OK" and float(bootstrap.details["lower"]) > 0.0
                ),
                "maximum_drawdown": hold["maximum_drawdown"] >= -0.12,
                "leave_one_security_out_positive": (
                    hold["leave_one_security_out_min_net_pnl"] is not None
                    and hold["leave_one_security_out_min_net_pnl"] > 0.0
                ),
                "leave_one_year_out_positive": (
                    hold["leave_one_year_out_min_net_pnl"] is not None
                    and hold["leave_one_year_out_min_net_pnl"] > 0.0
                ),
                "year_concentration": (
                    hold["maximum_year_trade_share"] is not None
                    and hold["maximum_year_trade_share"] <= 0.40
                ),
                "exit_concentration": (
                    hold["maximum_exit_trade_share"] is not None
                    and hold["maximum_exit_trade_share"] <= 0.70
                ),
            }
            scenario_results[scenario] = {
                "pass": all(checks.values()),
                "checks": checks,
                "full_study_baseline": _serialize_metrics(full),
                "holdout_baseline": _serialize_metrics(hold),
                "holdout_20bps": _serialize_metrics(hold_stress),
                "bootstrap": diagnostic_as_dict(bootstrap),
            }
        families[label] = {
            "pass": all(scenario_results[scenario]["pass"] for scenario in SCENARIOS),
            "scenarios": scenario_results,
        }
    passed = [label for label, result in families.items() if result["pass"]]
    incremental: dict[str, Any] | None = None
    if set(passed) == {"H1", "H2"}:
        scenario_results = {}
        for scenario in SCENARIOS:
            h1 = daily_returns(holdout["H1"][5], scenario)
            h2 = daily_returns(holdout["H2"][5], scenario)
            difference = tuple(right - left for left, right in zip(h1, h2, strict=True))
            diagnostic = block_bootstrap_mean_ci(
                difference,
                block_size=20,
                samples=2_000,
                confidence=0.95,
                seed=1,
            )
            scenario_results[scenario] = {
                "pass": (
                    mean(difference) > 0.0
                    and diagnostic.status == "OK"
                    and float(diagnostic.details["lower"]) > 0.0
                ),
                "mean": mean(difference),
                "bootstrap": diagnostic_as_dict(diagnostic),
            }
        incremental = {
            "pass": all(scenario_results[scenario]["pass"] for scenario in SCENARIOS),
            "scenarios": scenario_results,
        }
    if "H2" in passed and "H1" not in passed:
        selected = "H2"
    elif "H1" in passed:
        selected = "H2" if incremental is not None and incremental["pass"] else "H1"
    else:
        selected = None
    return {
        "gate": "GATE_3_HOLDOUT",
        "pass": bool(passed),
        "passing_families": passed,
        "selected_family": selected,
        "h2_incremental": incremental,
        "families": families,
    }


def source_preflight(
    *,
    feature_path: Path,
    feature_input_path: Path,
    summary_path: Path,
    config_path: Path,
    corporate_actions_path: Path,
) -> dict[str, Any]:
    paths = {
        "computed_features": feature_path,
        "feature_input": feature_input_path,
        "summary": summary_path,
        "config": config_path,
        "corporate_actions": corporate_actions_path,
    }
    actual = {name: file_sha256(path) for name, path in paths.items()}
    expected = {key: EXPECTED_HASHES[key] for key in paths}
    config = load_mps_config(config_path)
    sessions = pd.read_parquet(feature_path, columns=["session_date"])
    temporal = temporal_plan_evidence(sessions)
    checks = {
        "fixed_hashes": all(actual[key] == expected[key] for key in paths),
        "parsed_config_hash": config.config_hash() == EXPECTED_CONFIG_HASH,
        "temporal_boundaries": bool(temporal["exact_boundaries_match"]),
        "holdout_frozen": bool(temporal["holdout_frozen"]),
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "actual_hashes": actual,
        "expected_hashes": expected,
        "actual_config_hash": config.config_hash(),
        "expected_config_hash": EXPECTED_CONFIG_HASH,
        "accepted_date_plan_sha256": ACCEPTED_DATE_PLAN_SHA256,
        "temporal_plan": temporal,
        "benchmark": {
            "status": "UNAVAILABLE_TRANSPORT",
            "stooq_response_sha256": (
                "54f1f005853d9e7053acfbd7182f892e2ddaee23118632aba39de0313e4c578c"
            ),
            "yahoo_response": "HTTP_429_NO_FILE_WRITTEN",
            "benchmark_metrics_calculated": False,
        },
    }


def execute_screen(
    *,
    feature_path: Path,
    feature_input_path: Path,
    summary_path: Path,
    config_path: Path,
    corporate_actions_path: Path,
) -> dict[str, Any]:
    preflight = source_preflight(
        feature_path=feature_path,
        feature_input_path=feature_input_path,
        summary_path=summary_path,
        config_path=config_path,
        corporate_actions_path=corporate_actions_path,
    )
    report: dict[str, Any] = {
        "task_id": TASK_ID,
        "evidence_grade": ("EXPLORATORY_ABSOLUTE_RETURN_RESEARCH_WITH_ACCEPTED_LIMITATIONS"),
        "source_preflight": preflight,
        "gate_1": None,
        "gate_2": None,
        "gate_3": None,
        "holdout_opened": False,
        "outcome": None,
    }
    if not preflight["pass"]:
        report["outcome"] = "STOP_SOURCE_OR_TEMPORALITY_INVALID"
        return report
    config = load_mps_config(config_path)
    actions = pd.read_parquet(corporate_actions_path)
    data_hash = str(preflight["actual_hashes"]["computed_features"])
    discovery_report, discovery = run_stage(
        name="discovery",
        feature_path=feature_path,
        all_actions=actions,
        config=config,
        data_version_hash=data_hash,
    )
    report["discovery"] = discovery_report
    report["gate_1"] = gate_one(discovery)
    if not report["gate_1"]["pass"]:
        report["outcome"] = "NO_FAMILY_PASSES_DISCOVERY"
        return report
    validation_reports = []
    validation_bundles = []
    for name in ("validation_1", "validation_2"):
        stage_report, stage_bundles = run_stage(
            name=name,
            feature_path=feature_path,
            all_actions=actions,
            config=config,
            data_version_hash=data_hash,
        )
        validation_reports.append(stage_report)
        validation_bundles.append(stage_bundles)
    report["validation"] = validation_reports
    report["gate_2"] = gate_two(
        validation_bundles,
        report["gate_1"]["passing_families"],
    )
    if not report["gate_2"]["pass"]:
        report["outcome"] = "STOP_WALK_FORWARD_NOT_STABLE"
        return report
    report["holdout_opened"] = True
    holdout_report, holdout = run_stage(
        name="holdout",
        feature_path=feature_path,
        all_actions=actions,
        config=config,
        data_version_hash=data_hash,
    )
    report["holdout"] = holdout_report
    report["gate_3"] = gate_three(
        discovery=discovery,
        validation=validation_bundles,
        holdout=holdout,
        eligible_families=report["gate_2"]["passing_families"],
    )
    selected = report["gate_3"]["selected_family"]
    if selected == "H1":
        report["outcome"] = "H1_ABSOLUTE_ONLY_EXPLORATORY_PASS"
    elif selected == "H2":
        report["outcome"] = "H2_ABSOLUTE_ONLY_EXPLORATORY_PASS"
    else:
        report["outcome"] = "INCONCLUSIVE_ABSOLUTE_ONLY_SCREEN"
    return report


def render_markdown(report: dict[str, Any], generated_at: str) -> str:
    gate_1 = report.get("gate_1")
    gate_2 = report.get("gate_2")
    gate_3 = report.get("gate_3")
    lines = [
        "# SWING-PC-006 - Limitation-Tolerant Exploratory Screen",
        "",
        f"Generated: `{generated_at}`",
        "",
        f"Outcome: `{report['outcome']}`",
        "",
        f"Evidence grade: `{report['evidence_grade']}`",
        "",
        "## Sequential result",
        "",
        f"- Gate 1: `{None if gate_1 is None else gate_1['pass']}`",
        f"- Gate 2: `{None if gate_2 is None else gate_2['pass']}`",
        f"- Holdout opened: `{str(report['holdout_opened']).lower()}`",
        f"- Gate 3: `{None if gate_3 is None else gate_3['pass']}`",
        "",
        "No benchmark-relative metric or claim is present. Stooq returned a",
        "JavaScript verification page and the sole Yahoo fallback returned HTTP",
        "429, so the screen used absolute net returns only.",
        "",
    ]
    if gate_1 is not None:
        lines.extend(["## Discovery", ""])
        discovery = report["discovery"]["variants"]
        for label in ("H1", "H2", "B0"):
            baseline = discovery[label]["cost_scenarios_bps"]["5"]["TOTAL_LOSS"]
            stress = discovery[label]["cost_scenarios_bps"]["20"]["TOTAL_LOSS"]
            family_pass = (
                gate_1["families"][label]["pass"] if label in gate_1["families"] else "control"
            )
            lines.append(
                f"- {label}: pass `{family_pass}`; "
                f"{baseline['completed_trades']} trades; "
                f"net PnL `{baseline['net_pnl']:.2f}`; "
                f"mean R `{baseline['mean_realised_r']}`; "
                f"20 bps mean return `{stress['mean_trade_return']}`."
            )
        lines.append("")
    lines.extend(
        [
            "## Authority",
            "",
            "This packet is exploratory evidence only. It authorizes no profile,",
            "qualification, paper/live trading, broker/runtime action, or further",
            "data acquisition.",
            "",
        ]
    )
    return "\n".join(lines)
