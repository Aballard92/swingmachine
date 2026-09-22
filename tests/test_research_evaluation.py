"""Frozen-rule validation, independent arithmetic and bootstrap construction."""

import copy
import json
import math
import random
import subprocess
import sys
from dataclasses import asdict
from datetime import timedelta
from statistics import mean

import pytest

from swingmachine.research_evaluation import (
    _gates,
    account_returns,
    evaluate_campaign,
    load_evaluation_spec,
    partition_readiness,
    portfolio_metrics,
    sharpe,
    stationary_blocks,
    stationary_max_mean,
)
from swingmachine.research_reset import ResearchConfig
from tests.test_research_execution import D
from tests.test_research_reset_cli import REPO

SPEC_PATH = REPO / "config/research_evaluation_v1.json"
PLAN_PATH = REPO / "config/research_reset_v1.json"
POLICY_PATH = REPO / "config/research_execution_v1.json"


def frozen():
    return load_evaluation_spec(SPEC_PATH, PLAN_PATH, POLICY_PATH)


def toy_account():
    """Four-date net accounting example; not a generated strategy or price source."""
    days = [str(D + timedelta(days=i)) for i in range(4)]
    rows = [
        {
            "session": d,
            "equity": v,
            "settled_cash": cash,
            "market_value": v - cash,
            "unsettled_proceeds": 0,
            "dividend_receivable": 0,
            "marks": {"B": {"price": v - cash}},
        }
        for d, v, cash in zip(days, [110, 100, 120, 115], [60, 20, 70, 70], strict=True)
    ]
    return {
        "source_class": "SYNTHETIC_FIXTURE",
        "signal_planning_cost_bps": 10,
        "config": asdict(ResearchConfig("breakout", initial_cash=100)),
        "equity": rows,
        "lifecycles": [
            {
                "order_id": "A",
                "symbol": "A",
                "filled_quantity": 1,
                "initial_risk": 20,
                "realized_pnl": 10,
                "dividends": 0,
                "entry_session": days[0],
                "exit_session": days[2],
            },
            {
                "order_id": "B",
                "symbol": "B",
                "filled_quantity": 1,
                "initial_risk": 20,
                "realized_pnl": 0,
                "dividends": 0,
                "entry_session": days[1],
                "exit_session": None,
            },
        ],
        "open_position_states": [{"symbol": "B", "quantity": 1, "basis": 40}],
        "accounting_residual": 0,
        "benchmark": {
            "initial_cash": 100,
            "cost_bps_per_side": 10,
            "entry_share_fill_fraction": 1,
            "equity": [{"session": d, "equity": 101 + n} for n, d in enumerate(days)],
        },
    }


def test_frozen_plan_calendar_and_nine_trial_ledger():
    spec, receipt = frozen()
    assert len(receipt["trial_ledger"]) == 9
    assert {x["role"] for x in receipt["trial_ledger"]} == {"SELECTION", "STRESS", "DIAGNOSTIC"}
    readiness = receipt["partition_readiness"]
    assert readiness["assigned"]["warmup"]["sessions"] == 200
    assert readiness["assigned"]["development"]["sessions"] == 283
    assert readiness["unassigned"] == ["validation", "final"]
    assert not readiness["historical_execution_ready"]
    assert spec["exposure_history"]["prior_search_count"] is None


@pytest.mark.parametrize("target", ["spec", "plan", "policy"])
def test_post_freeze_mutation_is_rejected(tmp_path, target):
    paths = {"spec": SPEC_PATH, "plan": PLAN_PATH, "policy": POLICY_PATH}
    changed = tmp_path / "changed.json"
    changed.write_bytes(paths[target].read_bytes() + b" ")
    paths[target] = changed
    with pytest.raises(ValueError, match="changed|differs"):
        load_evaluation_spec(paths["spec"], paths["plan"], paths["policy"])


def test_partition_overlap_and_insufficient_embargo_rejected():
    spec, _ = frozen()
    spec = copy.deepcopy(spec)
    days = [str(D + timedelta(days=i)) for i in range(400)]
    spec["warmup_sessions"] = 20
    spec["gates"]["min_sessions"] = 20
    spec["partitions"] = {
        "warmup": {"start": days[0], "end": days[19]},
        "development": {"start": days[20], "end": days[99]},
        "validation": {"start": days[119], "end": days[199]},
        "final": None,
    }
    with pytest.raises(ValueError, match="embargo"):
        partition_readiness(spec, days)
    spec["partitions"]["validation"]["start"] = days[120]
    assert partition_readiness(spec, days)["unassigned"] == ["final"]
    spec["partitions"]["validation"]["start"] = days[99]
    with pytest.raises(ValueError, match="overlap"):
        partition_readiness(spec, days)


def test_account_denominator_and_zero_variance_are_explicit():
    rows = [{"session": "2019-01-02", "equity": 110}, {"session": "2019-01-03", "equity": 99}]
    assert account_returns(rows, 100)[1] == pytest.approx([0.1, -0.1])
    assert sharpe([0.01] * 20, 252) is None
    with pytest.raises(ValueError, match="unique"):
        account_returns([rows[0], rows[0]], 100)


def test_metrics_recompute_r_drawdown_attribution_and_lagged_exposure():
    spec, _ = frozen()
    result = toy_account()
    days = [r["session"] for r in result["equity"]]
    metrics, series = portfolio_metrics(result, days, [0.1, 0.1, -0.1, 0.2], spec)
    assert metrics["net_return"] == pytest.approx(0.15)
    assert metrics["max_drawdown"] == pytest.approx(1 - 100 / 110)
    assert metrics["mean_trade_r"] == metrics["median_trade_r"] == 0.5
    assert metrics["symbol_pnl"] == {"A": 10, "B": 5}
    assert metrics["positive_symbol_pnl_share"] == pytest.approx(2 / 3)
    assert metrics["pnl_without_best_symbol"] == 5
    assert metrics["accounting_residual_fraction"] == 0
    assert series["exposure_reference"] == pytest.approx([0, 50 / 110 * 0.1, -0.08, 50 / 120 * 0.2])
    assert metrics["exposure_diagnostic_is_executable"] is False


def test_corrupted_attribution_is_not_hidden_by_result_residual_flag():
    spec, _ = frozen()
    result = toy_account()
    result["lifecycles"][0]["realized_pnl"] = 999
    days = [r["session"] for r in result["equity"]]
    metrics, _ = portfolio_metrics(result, days, [0.01] * 4, spec)
    assert metrics["accounting_residual_fraction"] > 9
    assert not _gates(metrics, "stress", spec, [])["adequacy"]["accounting_residual_fraction"][
        "passed"
    ]


def test_prefix_sum_bootstrap_matches_explicit_index_expansion():
    series = {"a": [0.01, -0.02, 0.03, -0.01, 0.02], "b": [-0.03, 0.01, 0.02, 0.03, -0.01]}
    block, replicates, seed, alpha = 3, 199, 73, 0.05
    actual = stationary_max_mean(series, block, replicates, seed, alpha)
    rng, maxima = random.Random(seed), []
    for _ in range(replicates):
        indices = [
            i % 5
            for start, length in stationary_blocks(5, block, rng)
            for i in range(start, start + length)
        ]
        maxima.append(
            max(mean(values[i] for i in indices) - mean(values) for values in series.values())
        )
    critical = sorted(maxima)[math.ceil((replicates + 1) * (1 - alpha)) - 1]
    assert actual["critical_daily_mean"] == pytest.approx(critical)
    for name, values in series.items():
        assert actual["series"][name]["lower_bound"] == pytest.approx(mean(values) - critical)


def test_joint_resampling_preserves_duplicates_and_extra_search_cannot_lower_critical():
    values = [0.001, -0.002, 0.003, 0.004] * 30
    single = stationary_max_mean({"a": values}, 20, 199, 99, 0.05)
    duplicate = stationary_max_mean({"a": values, "same": values}, 20, 199, 99, 0.05)
    expanded = stationary_max_mean(
        {"a": values, "volatile": [x * 10 for x in values]}, 20, 199, 99, 0.05
    )
    assert duplicate["critical_daily_mean"] == single["critical_daily_mean"]
    assert expanded["critical_daily_mean"] >= single["critical_daily_mean"]
    assert duplicate["series"]["a"]["adjusted_tail_probability"] > 0


def test_stationary_blocks_retain_serial_dependence_in_clustered_series():
    # Long persistent clusters; an alternating 40-day cycle would introduce
    # negative longer-lag correlation and need not double a block-20 interval.
    values = ([0.01] * 80 + [-0.009] * 80) * 4
    iid = stationary_max_mean({"a": values}, 1, 999, 53, 0.05)
    blocked = stationary_max_mean({"a": values}, 20, 999, 53, 0.05)
    assert blocked["critical_daily_mean"] > iid["critical_daily_mean"] * 2


@pytest.mark.parametrize(
    "series", [{}, {"a": [1]}, {"a": [1, 2], "b": [1, 2, 3]}, {"a": [1, float("nan")]}]
)
def test_invalid_bootstrap_inputs(series):
    with pytest.raises(ValueError):
        stationary_max_mean(series, 20, 199, 1, 0.05)


def test_negative_median_is_diagnostic_not_automatic_failure():
    spec, _ = frozen()
    metrics = {
        "sessions": 300,
        "closed_lifecycles": 100,
        "filled_symbols": 20,
        "exposed_sessions": 200,
        "entry_cohorts": 15,
        "benchmark_share_fill_fraction": 1,
        "accounting_residual_fraction": 0,
        "sharpe": 1,
        "funded_spy_sharpe": 0.8,
        "mean_trade_r": 0.2,
        "median_trade_r": -0.5,
        "positive_symbol_pnl_share": 0.2,
        "positive_quarter_pnl_share": 0.4,
        "net_return": 0.1,
        "max_drawdown": 0.08,
        "pnl_without_best_symbol": 1000,
        "pnl_without_best_quarter": 1000,
    }
    bounds = [{"block": b, "cash": 0.0001, "exposure": 0.0001} for b in (20, 40)]
    assert _gates(metrics, "base", spec, bounds)["status"] == "PASS"
    metrics["positive_symbol_pnl_share"] = 0.36
    assert _gates(metrics, "base", spec, bounds)["status"] == "FAIL"
    metrics["closed_lifecycles"] = 2
    assert _gates(metrics, "base", spec, bounds)["status"] == "INCONCLUSIVE"


def test_trial_matrix_is_complete_and_synthetic_data_never_advances():
    spec, receipt = frozen()
    spec = copy.deepcopy(spec)
    spec["bootstrap"]["replicates"] = 199  # Pure calculator fixture, not the pinned CLI spec.
    ledger = copy.deepcopy(receipt["trial_ledger"])
    results = []
    for entry in ledger:
        result = toy_account()
        result["config"] = entry["config"]
        # Scale the independent accounting example into the frozen denomination.
        scale = entry["config"]["initial_cash"] / 100
        for row in result["equity"]:
            for key in ("equity", "settled_cash", "market_value"):
                row[key] *= scale
            row["marks"]["B"]["price"] *= scale
        for life in result["lifecycles"]:
            life["initial_risk"] *= scale
            life["realized_pnl"] *= scale
        result["open_position_states"][0]["basis"] *= scale
        result["benchmark"]["initial_cash"] *= scale
        result["benchmark"]["cost_bps_per_side"] = entry["config"]["cost_bps_per_side"]
        for row in result["benchmark"]["equity"]:
            row["equity"] *= scale
        results.append(result)
    days = [r["session"] for r in results[0]["equity"]]
    evaluation = evaluate_campaign(results, days, [0.01] * 4, spec, ledger, source_qualified=True)
    assert evaluation["candidate_for_independent_evaluation"] is None
    assert "SYNTHETIC_INPUT_NOT_MARKET_EVIDENCE" in evaluation["advancement_blockers"]
    assert evaluation["inference"][0]["joint_series"] == 18
    with pytest.raises(ValueError, match="missing, duplicate"):
        evaluate_campaign(results[:-1], days, [0.01] * 4, spec, ledger)
    results[-1]["equity"][0]["session"] = "2018-12-31"
    with pytest.raises(ValueError, match="calendar mismatch"):
        evaluate_campaign(results, days, [0.01] * 4, spec, ledger)


def test_freeze_command_reads_only_metadata(tmp_path):
    output = tmp_path / "freeze"
    run = subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts/run_research_reset.py"),
            "freeze-evaluation",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert run.returncode == 0, run.stderr
    receipt = json.loads((output / "evaluation_freeze.json").read_text())
    assert receipt["prices_read"] == receipt["strategy_calculations"] == 0
    assert len(receipt["trial_ledger"]) == 9
    assert not (output / "summary.json").exists()
