import json
from datetime import date, timedelta

import pytest

from swingmachine.mps_validation import (
    ExperimentRegistry,
    apply_one_way_costs,
    block_bootstrap_mean_ci,
    freeze_temporal_plan,
    neighbourhood_stability,
    probability_of_backtest_overfitting,
)


def trading_dates(count: int) -> list[date]:
    return [date(2000, 1, 1) + timedelta(days=index) for index in range(count)]


def test_holdout_is_frozen_at_longer_of_five_years_or_quarter():
    plan = freeze_temporal_plan(trading_dates(6_000))
    assert plan.holdout_frozen is True
    assert len(plan.holdout_dates) == 1_500
    assert set(plan.development_dates).isdisjoint(plan.holdout_dates)


def test_walk_forward_has_exact_embargo():
    plan = freeze_temporal_plan(trading_dates(6_000), embargo_sessions=30)
    window = plan.walk_forward_windows[0]
    dates = plan.development_dates
    assert dates.index(window.validation_start) - dates.index(window.development_end) == 31


def test_costs_are_one_way_turnover_times_cost_rate():
    assert apply_one_way_costs([0.01], [2.0], 20) == pytest.approx((0.006,))


def test_bootstrap_fails_closed_for_too_few_observations():
    result = block_bootstrap_mean_ci([0.01] * 10, block_size=20)
    assert result.status == "INSUFFICIENT_DATA"
    assert result.value is None


def test_pbo_fails_closed_without_multiple_variants():
    result = probability_of_backtest_overfitting({"B0": [0.01] * 100})
    assert result.status == "INSUFFICIENT_DATA"


def test_neighbourhood_stability_applies_eighty_percent_gate():
    assert neighbourhood_stability(1.0, [0.79, 0.80, 0.81]).status == "PASS"
    assert neighbourhood_stability(1.0, [0.60, 0.70, 0.79]).status == "FAIL"


def test_registry_is_append_only_and_preserves_failed_attempts(tmp_path):
    path = tmp_path / "registry.jsonl"
    registry = ExperimentRegistry(path)
    registry.append(
        strategy_variant="B2",
        configuration={"rank": 0.9},
        data_hash="abc",
        status="FAILED_GATE",
        outcome={"reason": "sharpe"},
    )
    registry.append(
        strategy_variant="B3",
        configuration={"rank": 0.9},
        data_hash="abc",
        status="BLOCKED",
        outcome={"reason": "data"},
    )
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert [record["status"] for record in records] == ["FAILED_GATE", "BLOCKED"]
