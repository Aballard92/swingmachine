"""Frozen research gates, paired benchmarks and joint calendar-block inference.

Stationary circular blocks follow Politis/Romano; centered max-mean inference
follows White's least-favourable null construction. Approximate, conditional on
this declared matrix; not a correction for unknown earlier searches.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from bisect import bisect_left
from collections import defaultdict
from dataclasses import asdict, fields
from datetime import date
from itertools import accumulate
from pathlib import Path
from statistics import mean, median, stdev

from swingmachine.research_calendar import verify_calendar
from swingmachine.research_reset import ResearchConfig, fingerprint, guard_research_dates
from swingmachine.research_source import SourceAdmission, _unique_object

SPEC_SHA256 = "b633422a2914a9c31bede5f398b24b85b4c13405d24b323f2e5ca7652bec7526"


def trial_id(family: str, cost: float) -> str:
    return f"{family}:{cost:g}bps"


def trial_ledger(plan: dict, spec: dict) -> list[dict]:
    if (
        plan["families"] != spec["families"]
        or plan["cost_bps_per_side"] != spec["cost_bps_per_side"]
        or plan["signal_planning_cost_bps_per_side"] != spec["signal_planning_cost_bps"]
    ):
        raise ValueError("plan differs from frozen family/cost/planning ledger")
    names = {f.name for f in fields(ResearchConfig)} - {"family", "cost_bps_per_side", "max_hold"}
    ledger = []
    for family in spec["families"]:
        for cost in spec["cost_bps_per_side"]:
            config = ResearchConfig(
                family,
                cost_bps_per_side=cost,
                max_hold=plan["max_hold_by_family"][family],
                **{name: plan[name] for name in names},
            )
            role = (
                "SELECTION"
                if cost == spec["selection_cost_bps"]
                else "STRESS"
                if cost == spec["stress_cost_bps"]
                else "DIAGNOSTIC"
            )
            ledger.append(
                {
                    "trial_id": trial_id(family, cost),
                    "role": role,
                    "config": asdict(config),
                    "config_sha256": fingerprint(asdict(config)),
                    "signal_planning_cost_bps": spec["signal_planning_cost_bps"],
                }
            )
    return ledger


def partition_readiness(spec: dict, sessions: list[str]) -> dict:
    assigned, missing, prior_end = {}, [], None
    for name in ("warmup", "development", "validation", "final"):
        interval = spec["partitions"][name]
        if interval is None:
            missing.append(name)
            continue
        if missing:
            raise ValueError("a later partition cannot precede a missing earlier partition")
        left, right = interval["start"], interval["end"]
        guard_research_dates(date.fromisoformat(left), date.fromisoformat(right))
        if left not in sessions or right not in sessions:
            raise ValueError("partition endpoint outside the retained calendar")
        a, b = sessions.index(left), sessions.index(right)
        if b < a or (prior_end is not None and a <= prior_end):
            raise ValueError("partition dates overlap or are reversed")
        if name in ("validation", "final") and a - prior_end - 1 < spec["embargo_sessions"]:
            raise ValueError("partition embargo shorter than the frozen holding horizon")
        count = b - a + 1
        minimum = spec["warmup_sessions"] if name == "warmup" else spec["gates"]["min_sessions"]
        if count < minimum:
            raise ValueError("partition has insufficient declared sessions")
        assigned[name] = {**interval, "sessions": count}
        prior_end = b
    return {
        "assigned": assigned,
        "unassigned": missing,
        "independent_partition_dates_complete": not missing,
        "prior_search_count": spec["exposure_history"]["prior_search_count"],
        "historical_source_qualified": False,
        "historical_execution_ready": False,
    }


def load_evaluation_spec(path: Path, plan_path: Path, execution_path: Path) -> tuple[dict, dict]:
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != SPEC_SHA256:
        raise ValueError("evaluation v1 has changed; a new pre-outcome version is required")
    spec = json.loads(payload, object_pairs_hook=_unique_object)
    plan_bytes, execution_bytes = plan_path.read_bytes(), execution_path.read_bytes()
    if hashlib.sha256(plan_bytes).hexdigest() != spec["plan_sha256"]:
        raise ValueError("research plan differs from evaluation freeze")
    if hashlib.sha256(execution_bytes).hexdigest() != spec["execution_policy_sha256"]:
        raise ValueError("execution policy differs from evaluation freeze")
    plan = json.loads(plan_bytes, object_pairs_hook=_unique_object)
    calendar, calendar_receipt = verify_calendar()
    if calendar_receipt["calendar_sha256"] != spec["calendar_sha256"]:
        raise ValueError("frozen calendar mismatch")
    readiness = partition_readiness(spec, [r["day"] for r in calendar["sessions"]])
    return spec, {
        "task_id": "SWING-RF-005",
        "status": "NUMERICAL_RULES_FROZEN",
        "spec_sha256": SPEC_SHA256,
        "spec": spec,
        "trial_ledger": trial_ledger(plan, spec),
        "partition_readiness": readiness,
        "prices_read": 0,
        "strategy_calculations": 0,
        "permission": "NO_HISTORICAL_OR_TRADING_AUTHORITY_GRANTED",
    }


def stationary_blocks(n: int, expected_length: int, rng: random.Random):
    """Geometric blocks, uniform starting positions, circular continuation."""
    remaining = n
    while remaining:
        start = rng.randrange(n)
        length = (
            1
            if expected_length == 1
            else 1 + int(math.log1p(-rng.random()) / math.log1p(-1 / expected_length))
        )
        length = min(length, remaining)
        yield start, length
        remaining -= length


def stationary_max_mean(
    series: dict[str, list[float]], block: int, replicates: int, seed: int, alpha: float
) -> dict:
    """Shared block draws preserve contemporaneous dependence across all trials.

    Prefix sums implement exactly the same circular block sampling as explicit
    index expansion, without materialising B x n x k arrays or adding dependencies.
    """
    sizes = {len(x) for x in series.values()}
    if not series or len(sizes) != 1 or next(iter(sizes)) < 2:
        raise ValueError("aligned nonempty return series with at least two observations required")
    n = next(iter(sizes))
    if type(block) is not int or block < 1 or type(replicates) is not int or replicates < 19:
        raise ValueError("invalid bootstrap size or block length")
    if type(seed) is not int or not 0 < alpha < 0.5:
        raise ValueError("invalid bootstrap seed or alpha")
    if any(type(v) not in (int, float) or not math.isfinite(v) for x in series.values() for v in x):
        raise ValueError("finite numeric returns required")
    labels = sorted(series)
    averages = [math.fsum(series[k]) / n for k in labels]
    prefixes = [
        [0.0, *accumulate(v - average for v in series[k])]
        for k, average in zip(labels, averages, strict=True)
    ]
    rng, maxima = random.Random(seed), []
    for _ in range(replicates):
        sums = [0.0] * len(labels)
        for start, length in stationary_blocks(n, block, rng):
            end = start + length
            for j, prefix in enumerate(prefixes):
                sums[j] += (
                    (prefix[end] - prefix[start])
                    if end <= n
                    else (prefix[n] - prefix[start] + prefix[end - n])
                )
        maxima.append(max(sums) / n)
    maxima.sort()
    index = min(replicates - 1, math.ceil((replicates + 1) * (1 - alpha)) - 1)
    critical = maxima[index]
    return {
        "method": "STATIONARY_CIRCULAR_JOINT_MAX_CENTERED_MEAN",
        "sessions": n,
        "joint_series": len(labels),
        "block_sessions": block,
        "replicates": replicates,
        "seed": seed,
        "alpha": alpha,
        "critical_daily_mean": critical,
        "series": {
            label: {
                "mean": average,
                "lower_bound": average - critical,
                "adjusted_tail_probability": (1 + replicates - bisect_left(maxima, average))
                / (replicates + 1),
            }
            for label, average in zip(labels, averages, strict=True)
        },
        "scope": "approximate simultaneous inference for this matrix; prior searches uncorrected",
    }


def account_returns(rows: list[dict], initial: float) -> tuple[list[str], list[float]]:
    if not rows or not math.isfinite(initial) or initial <= 0:
        raise ValueError("positive initial capital and nonempty account required")
    days = [r["session"] for r in rows]
    if days != sorted(set(days)):
        raise ValueError("account dates must be unique and increasing")
    values = [initial, *[r["equity"] for r in rows]]
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError("account equity must be positive and finite")
    return days, [b / a - 1 for a, b in zip(values[:-1], values[1:], strict=True)]


def sharpe(returns: list[float], annual_sessions: int) -> float | None:
    vol = stdev(returns) if len(returns) > 1 else 0
    return math.sqrt(annual_sessions) * mean(returns) / vol if vol > 1e-15 else None


def spy_total_returns(admission: SourceAdmission) -> tuple[list[str], list[float]]:
    prior, days, returns = None, [], []
    for session in admission.sessions:
        rows = [b for b in admission.by_date[session] if b.symbol == "SPY"]
        if len(rows) != 1:
            raise ValueError("exactly one SPY observation required per session")
        bar = rows[0]
        if session >= admission.evaluation_start:
            if prior is None:
                raise ValueError("SPY warmup close required for exposure diagnostic")
            days.append(str(session))
            returns.append(bar.split_ratio * (bar.close + bar.dividend) / prior - 1)
        prior = bar.close
    return days, returns


def _positive_share(contributions: dict) -> float | None:
    positive = [v for v in contributions.values() if v > 0]
    return max(positive) / math.fsum(positive) if positive else None


def portfolio_metrics(
    result: dict, spy_days: list[str], spy_returns: list[float], spec: dict
) -> tuple[dict, dict]:
    initial = result["config"]["initial_cash"]
    rows = result["equity"]
    days, returns = account_returns(rows, initial)
    benchmark = result["benchmark"]
    bench_days, bench_returns = account_returns(benchmark["equity"], benchmark["initial_cash"])
    if days != spy_days or days != bench_days or len(spy_returns) != len(days):
        raise ValueError("strategy and benchmark calendar mismatch")
    if benchmark["initial_cash"] != initial or not math.isclose(
        benchmark["cost_bps_per_side"], result["config"]["cost_bps_per_side"]
    ):
        raise ValueError("benchmark capital/cost denomination mismatch")
    weight, exposure_returns, quarters = 0.0, [], defaultdict(float)
    residuals, peak, drawdown, previous = [], initial, 0.0, initial
    for row, spy in zip(rows, spy_returns, strict=True):
        if not math.isfinite(spy) or spy <= -1:
            raise ValueError("invalid SPY total return")
        market, value = row["market_value"], row["equity"]
        if not 0 <= market <= value + 1e-7:
            raise ValueError("invalid unlevered market exposure")
        exposure_returns.append(weight * spy)
        weight = min(1.0, market / value)
        residuals.append(
            value
            - market
            - row["settled_cash"]
            - row["unsettled_proceeds"]
            - row["dividend_receivable"]
        )
        d = date.fromisoformat(row["session"])
        quarters[f"{d.year}-Q{(d.month - 1) // 3 + 1}"] += value - previous
        previous = value
        peak = max(peak, value)
        drawdown = max(drawdown, 1 - value / peak)
    lives = result["lifecycles"]
    if len({x["order_id"] for x in lives}) != len(lives):
        raise ValueError("duplicate lifecycle identity")
    filled = [x for x in lives if x["filled_quantity"] > 0]
    closed, symbols, cohorts, pnl_by_symbol = [], set(), set(), defaultdict(float)
    for life in filled:
        if life["entry_session"] not in days or life["initial_risk"] <= 0:
            raise ValueError("invalid filled lifecycle date/risk")
        symbols.add(life["symbol"])
        cohorts.add(days.index(life["entry_session"]) // spec["entry_cohort_sessions"])
        pnl = life["realized_pnl"] + life["dividends"]
        pnl_by_symbol[life["symbol"]] += pnl
        if life["exit_session"] is not None:
            if life["exit_session"] not in days or life["exit_session"] < life["entry_session"]:
                raise ValueError("invalid lifecycle exit date")
            closed.append(pnl / life["initial_risk"])
    for position in result["open_position_states"]:
        symbol = position["symbol"]
        price = rows[-1]["marks"][symbol]["price"]
        pnl_by_symbol[symbol] += position["quantity"] * price - position["basis"]
    net_pnl = rows[-1]["equity"] - initial
    residuals.extend([net_pnl - math.fsum(pnl_by_symbol.values()), result["accounting_residual"]])
    if any(not math.isfinite(x) for x in residuals):
        raise ValueError("nonfinite accounting residual")
    metrics = {
        "sessions": len(days),
        "closed_lifecycles": len(closed),
        "filled_symbols": len(symbols),
        "exposed_sessions": sum(r["market_value"] > 0 for r in rows),
        "entry_cohorts": len(cohorts),
        "benchmark_share_fill_fraction": benchmark["entry_share_fill_fraction"],
        "accounting_residual_fraction": max(abs(x) for x in residuals) / initial,
        "net_return": net_pnl / initial,
        "net_pnl": net_pnl,
        "mean_trade_r": mean(closed) if closed else None,
        "median_trade_r": median(closed) if closed else None,
        "sharpe": sharpe(returns, spec["annual_sessions"]),
        "funded_spy_sharpe": sharpe(bench_returns, spec["annual_sessions"]),
        "funded_spy_net_return": benchmark["equity"][-1]["equity"] / initial - 1,
        "max_drawdown": drawdown,
        "positive_symbol_pnl_share": _positive_share(pnl_by_symbol),
        "positive_quarter_pnl_share": _positive_share(quarters),
        "pnl_without_best_symbol": net_pnl - max(pnl_by_symbol.values()) if pnl_by_symbol else None,
        "pnl_without_best_quarter": net_pnl - max(quarters.values()),
        "symbol_pnl": dict(pnl_by_symbol),
        "quarter_pnl": dict(quarters),
        "exposure_diagnostic_net_return": math.prod(1 + r for r in exposure_returns) - 1,
        "exposure_diagnostic_is_executable": False,
    }
    return metrics, {
        "cash": returns,
        "exposure": [a - b for a, b in zip(returns, exposure_returns, strict=True)],
        "exposure_reference": exposure_returns,
        "funded_spy": bench_returns,
    }


def _gates(metrics: dict, role: str, spec: dict, bounds: list[dict]) -> dict:
    gates = spec["gates"]
    adequate, economic = {}, {}

    def gate(target, name, value, threshold, op):
        passed = (
            value is not None
            and math.isfinite(value)
            and (
                value >= threshold
                if op == ">="
                else value <= threshold
                if op == "<="
                else value > threshold
            )
        )
        target[name] = {"value": value, "operator": op, "threshold": threshold, "passed": passed}

    for metric, key in [
        ("sessions", "min_sessions"),
        ("closed_lifecycles", "min_closed_lifecycles"),
        ("filled_symbols", "min_filled_symbols"),
        ("exposed_sessions", "min_exposed_sessions"),
        ("entry_cohorts", "min_entry_cohorts"),
        ("benchmark_share_fill_fraction", "min_benchmark_share_fill_fraction"),
    ]:
        gate(adequate, metric, metrics[metric], gates[key], ">=")
    gate(
        adequate,
        "accounting_residual_fraction",
        metrics["accounting_residual_fraction"],
        gates["max_accounting_residual_fraction"],
        "<=",
    )
    for key in (
        "sharpe",
        "funded_spy_sharpe",
        "mean_trade_r",
        "positive_symbol_pnl_share",
        "positive_quarter_pnl_share",
    ):
        adequate[f"defined_{key}"] = {"passed": metrics[key] is not None}
    gate(economic, "net_return", metrics["net_return"], 0, ">")
    gate(economic, "mean_trade_r", metrics["mean_trade_r"], gates[f"{role}_min_mean_r"], ">=")
    gate(economic, "max_drawdown", metrics["max_drawdown"], gates[f"{role}_max_drawdown"], "<=")
    for metric in ("positive_symbol_pnl_share", "positive_quarter_pnl_share"):
        gate(economic, metric, metrics[metric], gates[f"max_{metric}"], "<=")
    for metric in ("pnl_without_best_symbol", "pnl_without_best_quarter"):
        gate(economic, metric, metrics[metric], 0, ">")
    if role == "base":
        gate(economic, "minimum_sharpe", metrics["sharpe"], gates["base_min_sharpe"], ">=")
        if metrics["funded_spy_sharpe"] is not None:
            gate(
                economic,
                "funded_spy_sharpe_hurdle",
                metrics["sharpe"],
                metrics["funded_spy_sharpe"],
                ">=",
            )
        for item in bounds:
            for name in ("cash", "exposure"):
                gate(economic, f"{name}_lower_bound_block_{item['block']}", item[name], 0, ">")
    status = (
        "INCONCLUSIVE"
        if not all(x["passed"] for x in adequate.values())
        else "PASS"
        if all(x["passed"] for x in economic.values())
        else "FAIL"
    )
    return {
        "status": status,
        "adequacy": adequate,
        "economic": economic,
        "median_trade_r_is_gate": False,
    }


def evaluate_campaign(
    results: list[dict],
    spy_days: list[str],
    spy_returns: list[float],
    spec: dict,
    ledger: list[dict],
    phase: str = "development",
    source_qualified: bool = False,
    independent: bool = False,
) -> dict:
    if phase not in ("development", "validation", "final"):
        raise ValueError("unknown evaluation phase")
    expected = {r["trial_id"]: r for r in ledger}
    actual = {trial_id(r["config"]["family"], r["config"]["cost_bps_per_side"]): r for r in results}
    if len(actual) != len(results) or actual.keys() != expected.keys():
        raise ValueError("missing, duplicate or additional trial in the frozen matrix")
    classes = {r["source_class"] for r in results}
    if len(classes) != 1 or not classes <= {"SYNTHETIC_FIXTURE", "HISTORICAL"}:
        raise ValueError("trial source classes disagree")
    metrics, series, details = {}, {}, {}
    for key in sorted(actual):
        result = actual[key]
        if (
            fingerprint(result["config"]) != expected[key]["config_sha256"]
            or result["signal_planning_cost_bps"] != spec["signal_planning_cost_bps"]
        ):
            raise ValueError("result configuration differs from frozen ledger")
        metrics[key], details[key] = portfolio_metrics(result, spy_days, spy_returns, spec)
        for name in ("cash", "exposure"):
            series[f"{key}/{name}"] = details[key][name]
    bootstrap = spec["bootstrap"]
    if len(series) != bootstrap["joint_series"]:
        raise ValueError("joint test cardinality differs from frozen matrix")
    inference = [
        stationary_max_mean(
            series, block, bootstrap["replicates"], bootstrap["seed"] + block, bootstrap["alpha"]
        )
        for block in bootstrap["expected_block_sessions"]
    ]
    families = {}
    for family in spec["families"]:
        base = trial_id(family, spec["selection_cost_bps"])
        stress = trial_id(family, spec["stress_cost_bps"])
        bounds = [
            {
                "block": b["block_sessions"],
                **{k: b["series"][f"{base}/{k}"]["lower_bound"] for k in ("cash", "exposure")},
            }
            for b in inference
        ]
        base_gates, stress_gates = (
            _gates(metrics[base], "base", spec, bounds),
            _gates(metrics[stress], "stress", spec, []),
        )
        statuses = {base_gates["status"], stress_gates["status"]}
        status = (
            "INCONCLUSIVE"
            if "INCONCLUSIVE" in statuses
            else "PASS"
            if statuses == {"PASS"}
            else "FAIL"
        )
        families[family] = {
            "status": status,
            "base": base_gates,
            "stress": stress_gates,
            "rank_score": min(b["exposure"] for b in bounds),
        }
    passing = [f for f in families if families[f]["status"] == "PASS"]
    passing.sort(
        key=lambda f: (
            -families[f]["rank_score"],
            -metrics[trial_id(f, spec["selection_cost_bps"])]["sharpe"],
            f,
        )
    )
    blockers = []
    if classes == {"SYNTHETIC_FIXTURE"}:
        blockers.append("SYNTHETIC_INPUT_NOT_MARKET_EVIDENCE")
    elif spec["historical_execution"] != "ENABLED_BY_SEPARATE_QUALIFICATION":
        blockers.append("HISTORICAL_EXECUTION_NOT_ENABLED_BY_THIS_FREEZE")
    if not source_qualified:
        blockers.append("SOURCE_QUALIFICATION_INCOMPLETE")
    interval = spec["partitions"][phase]
    if interval is None:
        blockers.append("INDEPENDENT_PARTITION_DATES_UNASSIGNED")
    elif classes == {"HISTORICAL"} and (
        spy_days[0] != interval["start"] or spy_days[-1] != interval["end"]
    ):
        blockers.append("SCORED_DATES_DIFFER_FROM_FROZEN_PARTITION")
    if phase != "development" and not independent:
        blockers.append("INDEPENDENCE_NOT_ESTABLISHED")
    return {
        "task_id": "SWING-RF-005",
        "phase": phase,
        "source_class": next(iter(classes)),
        "metrics": metrics,
        "paired_daily_series": details,
        "inference": inference,
        "families": families,
        "candidate_for_independent_evaluation": passing[0]
        if passing and not blockers and phase == "development"
        else None,
        "advancement_blockers": blockers,
        "paper_live_promotion": "UNAVAILABLE",
        "independent_dates_complete": all(
            spec["partitions"][p] is not None for p in ("validation", "final")
        ),
        "prior_search_correction": "UNKNOWN_PRIOR_TRIALS_NOT_CORRECTED",
        "inference_limit": "conditional stationary-block approximation; "
        "finite history and regime changes remain limitations",
    }
