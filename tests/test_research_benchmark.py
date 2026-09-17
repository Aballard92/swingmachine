"""Hand-calculated benchmark cash, fill timing, splits and receivables."""

from datetime import timedelta

import pytest

from swingmachine.research_benchmark import PassiveBenchmark
from swingmachine.research_execution import ExecutionPolicy
from tests.test_research_execution import D, action, bar, day


def tick(sim, **kw):
    sim.on_minute(sim.clock, bar(sim.clock, **kw))


def finish(sim, **kw):
    if sim.clock < sim.day.closes:
        tick(sim, **kw)
    while sim.clock < sim.day.closes:
        sim.on_minute(sim.clock, None)
    sim.finish_session()


def opened(volume=100000):
    sim = PassiveBenchmark(10000, 10, ExecutionPolicy())
    sim.start_session(day(), [])
    for _ in range(5):
        tick(sim)
    assert sim.order.quantity == 99 and not sim.fills
    tick(sim)
    assert not sim.fills
    tick(sim, volume=volume)
    return sim


def test_benchmark_fixes_quantity_before_fill_and_keeps_cash_residual():
    sim = opened()
    assert sim.quantity == 99 and sim.cash == pytest.approx(90.1)
    assert sim.total_costs == pytest.approx(9.9)
    finish(sim)
    result = sim.result()
    assert result["entry_share_fill_fraction"] == 1
    assert result["equity"][-1]["equity"] == pytest.approx(9990.1)
    assert result["equity"][-1]["accounting_residual"] == pytest.approx(0, abs=1e-8)


def test_benchmark_partial_fill_expires_without_later_catchup():
    sim = opened(volume=1000)
    while sim.clock < sim.day.closes:
        sim.on_minute(sim.clock, None)
    sim.finish_session()
    assert sim.result()["entry_share_fill_fraction"] == pytest.approx(1 / 99)
    sim.start_session(day(1), [])
    for _ in range(16):
        tick(sim, open=50, high=51, low=49, close=50)
    assert sim.quantity == 1 and len(sim.fills) == 1
    finish(sim)


def test_benchmark_split_dividend_payment_is_not_reinvestment():
    sim = opened()
    finish(sim)
    sim.start_session(day(1), [action("SPY")])
    assert sim.quantity == 198
    assert sim.cash == pytest.approx(90.1)
    finish(sim, open=50, high=51, low=49, close=50)
    assert sim.equity[-1]["dividend_receivable"] == 198
    assert sim.equity[-1]["equity"] == pytest.approx(10188.1)
    for index in (2, 3):
        sim.start_session(day(index), [])
        finish(sim, open=50, high=51, low=49, close=50)
    assert sim.quantity == 198 and sim.cash == pytest.approx(288.1)
    assert not sim.receivables and len(sim.fills) == 1


def test_missing_benchmark_opening_minute_and_fractional_terms_fail_closed():
    sim = PassiveBenchmark(10000, 10, ExecutionPolicy())
    sim.start_session(day(), [])
    for _ in range(4):
        tick(sim)
    with pytest.raises(ValueError, match="opening observations"):
        sim.on_minute(sim.clock, None)
    sim = opened()
    finish(sim)
    cash = sim.cash
    with pytest.raises(ValueError, match="fractional"):
        sim.start_session(day(1), [action("SPY", split_ratio=0.5)])
    assert sim.cash == cash and sim.quantity == 99


def test_first_day_new_benchmark_holder_receives_no_ex_date_distribution():
    sim = PassiveBenchmark(10000, 10, ExecutionPolicy())
    sim.start_session(
        day(), [action("SPY", split_ratio=1, ex_session=D, payment_session=D + timedelta(days=2))]
    )
    for _ in range(7):
        tick(sim)
    finish(sim)
    assert sim.distributions == 0
