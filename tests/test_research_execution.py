"""Hand-audited minute execution, timing and portfolio accounting scenarios."""

from dataclasses import asdict, replace
from datetime import date, datetime, time, timedelta

import pytest

from swingmachine.research_daily import NY, CalendarDay, CorporateAction, Minute
from swingmachine.research_execution import ExecutionPolicy, ExecutionSimulator
from swingmachine.research_reset import Idea, ResearchConfig

D = date(2019, 1, 2)


def day(index=0):
    d = D + timedelta(days=index)
    return CalendarDay(
        d,
        datetime.combine(d, time(9, 30), NY),
        datetime.combine(d, time(16), NY),
        datetime(2018, 1, 1, tzinfo=NY),
        "synthetic-calendar",
    )


def idea(symbol="A", signal=None, **kw):
    return Idea(
        **{
            "symbol": symbol,
            "signal_date": signal or D - timedelta(days=1),
            "reference": 100,
            "stop": 90,
            "target": 125,
            "score": 1,
            "average_volume": 1_000_000,
            "sector": "TECH",
            **kw,
        }
    )


def bar(stamp, **kw):
    return Minute(
        **{
            "timestamp": stamp,
            "instrument_id": 1,
            "raw_symbol": "A",
            "open": 100,
            "high": 100.1,
            "low": 99.9,
            "close": 100,
            "volume": 100_000,
            "source_id": "synthetic-minute",
            "record_index": 0,
            **kw,
        }
    )


def engine(policy=None, **kw):
    return ExecutionSimulator(
        ResearchConfig("breakout", **{"initial_cash": 10000, **kw}),
        policy or ExecutionPolicy(),
        [D + timedelta(days=i) for i in range(60)],
    )


def start(sim, index=0, ideas=None, actions=None, entry=None, held=None):
    ideas = [idea(signal=day(index).session - timedelta(days=1))] if ideas is None else ideas
    sim.start_session(
        day(index),
        ideas,
        actions or [],
        {i.symbol: i.sector for i in ideas} if entry is None else entry,
        {s: p.sector for s, p in sim.positions.items()} if held is None else held,
    )


def tick(sim, symbols=("A",), **kw):
    sim.on_minute(sim.clock, {s: bar(sim.clock, **kw) for s in symbols})


def opening(sim, symbols=("A",)):
    for _ in range(5):
        tick(sim, symbols)


def finish(sim, **kw):
    # One explicit later mark, then genuinely absent intervals (never backfilled).
    if sim.clock < sim.day.closes:
        tick(sim, **kw)
    while sim.clock < sim.day.closes:
        sim.on_minute(sim.clock, {})
    sim.finish_session()


def entered(sim=None):
    sim = sim or engine()
    start(sim)
    opening(sim)
    tick(sim)  # 09:35 latency interval
    tick(sim)  # eligible at 09:36
    assert sim.positions["A"].quantity == 2
    return sim


def test_fixed_order_timing_rr_and_no_fill_on_latency_interval():
    sim = engine()
    start(sim)
    opening(sim)
    order = next(iter(sim.orders.values()))
    intent = order.intent
    assert (intent.quantity, intent.limit, intent.stop, intent.target) == (2, 100, 90, 125)
    assert intent.submitted_at == day().opens + timedelta(minutes=5)
    assert intent.active_at == day().opens + timedelta(minutes=6)
    assert intent.expires_at == day().opens + timedelta(minutes=15)
    tick(sim, low=80)
    assert not sim.fills
    tick(sim)
    assert sim.positions["A"].quantity == 2
    assert sim.cash == pytest.approx(9799.8)
    finish(sim)
    assert sim.result()["accounting_residual"] == pytest.approx(0, abs=1e-8)


def test_future_prices_and_volume_cannot_change_an_earlier_order():
    intents = []
    for future in [
        dict(open=80, low=75, high=85, close=80, volume=1000),
        dict(open=150, low=140, high=200, close=180, volume=900000),
    ]:
        sim = engine()
        start(sim)
        opening(sim)
        intent = next(iter(sim.orders.values())).intent
        before = asdict(intent)
        tick(sim, **future)
        tick(sim, **future)
        assert asdict(intent) == before
        intents.append(before)
    assert intents[0] == intents[1]


def test_entry_bar_stop_shares_capacity_and_cancels_unfilled_entry():
    sim = engine()
    start(sim)
    opening(sim)
    tick(sim)
    tick(sim, low=80, volume=1000)
    order = next(iter(sim.orders.values()))
    assert order.intent.quantity == 2 and order.status == "CANCELLED"
    assert sim.positions["A"].quantity == 1
    assert sim.positions["A"].exit_reason == "stop"
    assert [f["quantity"] for f in sim.fills] == [1]  # No capacity left for the stop.
    tick(sim, open=80, low=75, high=85, close=80, volume=1000)
    assert not sim.positions
    assert sim.fills[-1]["reason"] == "persistent_stop"
    assert sim.fills[-1]["price"] == 80
    finish(sim)
    assert sim.result()["trades"][0]["r"] < -1


def test_limit_touch_is_not_fill_and_expired_order_never_resurrects():
    sim = engine()
    start(sim)
    opening(sim)
    for _ in range(11):
        tick(sim, low=100)
    order = next(iter(sim.orders.values()))
    assert order.status == "EXPIRED" and not sim.fills
    tick(sim, low=90)
    assert not sim.fills


def test_later_stop_cannot_retroactively_cancel_an_eligible_partial_entry_fill():
    sim = engine()
    start(sim)
    opening(sim)
    tick(sim)
    tick(sim, volume=1000)  # First of two shares, no stop yet.
    assert sim.positions["A"].quantity == 1
    tick(sim, low=80, volume=1000)  # The second buy can precede the intrabar low.
    assert [f["side"] for f in sim.fills] == ["BUY", "BUY"]
    assert sim.positions["A"].quantity == 2
    assert sim.positions["A"].exit_reason == "stop"
    tick(sim, open=80, high=85, low=75, close=80)
    assert sim.fills[-1]["quantity"] == 2
    finish(sim)
    assert sim.result()["trades"][0]["net_pnl"] == pytest.approx(-40.36)


def test_partial_entry_cancel_request_is_not_instant_acknowledgement():
    sim = engine()
    start(sim)
    opening(sim)
    tick(sim)
    order = next(iter(sim.orders.values()))
    sim.request_cancel(order.intent.order_id)  # 09:36 request, ack at 09:37.
    tick(sim, volume=1000)
    assert order.status == "PARTIALLY_FILLED" and sim.positions["A"].quantity == 1
    tick(sim)
    assert order.status == "CANCELLED" and sim.positions["A"].quantity == 1


def test_explicit_broker_rejection_releases_reservation():
    sim = engine()
    start(sim)
    opening(sim)
    order = next(iter(sim.orders.values()))
    sim.reject_order(order.intent.order_id, "fixture_rejection")
    assert sim._reserved()[0] == 0
    tick(sim)
    tick(sim)
    assert not sim.fills and order.status == "REJECTED"


def test_stop_target_ambiguity_and_gap_loss_are_conservative():
    for changes, price, reason in [
        (dict(low=80, high=130), 90, "ambiguous_stop_first"),
        (dict(open=80, low=75, high=85, close=80), 80, "gap_stop"),
    ]:
        sim = entered()
        tick(sim, **changes)
        assert sim.fills[-1]["price"] == price
        assert sim.fills[-1]["reason"] == reason
        finish(sim)
        if reason == "gap_stop":
            assert sim.result()["trades"][0]["r"] < -1


def test_passive_entry_cannot_collect_a_target_high_that_may_precede_entry():
    sim = engine()
    start(sim)
    opening(sim)
    tick(sim)
    tick(sim, open=110, high=130, low=99, close=110)
    assert [f["side"] for f in sim.fills] == ["BUY"]
    tick(sim, open=125, high=125, low=124, close=125)
    assert len(sim.fills) == 1  # Target touch also does not establish a fill.
    tick(sim, open=126, high=127, low=125, close=126)
    assert sim.fills[-1]["price"] == 125 and not sim.positions


def test_zero_capacity_stop_persists_and_next_price_can_be_worse():
    sim = entered()
    tick(sim, low=80, volume=0)
    assert sim.positions["A"].exit_reason == "stop"
    tick(sim, open=70, low=69, high=71, close=70)
    assert sim.fills[-1]["price"] == 70


def test_missing_opening_minute_or_entry_context_produces_no_order():
    for missing in ("minute", "context"):
        sim = engine()
        start(sim, entry={} if missing == "context" else None)
        for n in range(5):
            tick(sim, () if missing == "minute" and n == 2 else ("A",))
        assert not sim.orders and sum(sim.rejections.values()) == 1


def test_missing_fresh_held_mark_prevents_new_risk():
    sim = entered()
    finish(sim)
    start(sim, 1, ideas=[idea("B", signal=D)])
    for n in range(5):
        tick(sim, ("B",) if n == 4 else ("A", "B"))
    assert len(sim.orders) == 1
    assert sim.rejections["missing_fresh_held_mark_or_sector"] == 1


def test_simultaneous_intents_share_cash_sector_and_risk_reservations():
    sim = engine(risk_fraction=0.1, new_risk_fraction=0.5, heat_fraction=0.5)
    names = [f"S{i}" for i in range(10)]
    start(sim, ideas=[idea(s) for s in names])
    opening(sim, names)
    orders = [o.intent for o in sim.orders.values()]
    assert sum(o.quantity * o.limit * 1.001 for o in orders) <= 2000
    assert all(o.quantity * o.limit * 1.001 <= 800 for o in orders)
    tick(sim, names)
    tick(sim, names)
    sim._invariants()
    assert sim.cash >= 8000


def test_unsettled_sales_cannot_finance_the_same_or_following_day():
    sim = engine(
        name_fraction=1,
        sector_fraction=1,
        risk_fraction=1,
        heat_fraction=1,
        new_risk_fraction=1,
        max_hold=1,
    )
    start(sim)
    opening(sim)
    tick(sim)
    tick(sim)
    assert sim.positions["A"].quantity == 99
    finish(sim)
    for index in (1, 2):
        start(sim, index, ideas=[idea("B", signal=D + timedelta(days=index - 1))])
        opening(sim, ("A", "B"))
        assert len(sim.orders) == 1
        finish(sim, symbols=("B",))
    assert sim.unsettled and sim.cash < 100
    start(sim, 3, ideas=[idea("B", signal=D + timedelta(days=2))])
    opening(sim, ("B",))
    assert len(sim.orders) == 2 and not sim.unsettled


def action(symbol="A", **kw):
    return CorporateAction(
        **{
            "event_id": "split-dividend",
            "security_id": symbol,
            "ex_session": D + timedelta(days=1),
            "known_at": datetime(2018, 12, 1, tzinfo=NY),
            "split_ratio": 2,
            "dividend": 1,
            "payment_session": D + timedelta(days=3),
            "ref_id": "synthetic-action",
            **kw,
        }
    )


def test_split_entitlement_partial_sale_and_payment_reconcile():
    sim = entered()
    finish(sim)
    start(sim, 1, ideas=[], actions=[action()])
    assert sim.positions["A"].quantity == 4
    assert sim.positions["A"].stop == 45
    assert sum(x[1] for x in sim.receivables) == 4
    assert sim.cash == pytest.approx(9799.8)
    tick(sim, open=63, high=64, low=62, close=63, volume=1000)
    assert sim.positions["A"].quantity == 3
    tick(sim, open=63, high=64, low=62, close=63)
    assert not sim.positions
    finish(sim)
    result = sim.result()
    assert result["trades"][0]["net_pnl"] == pytest.approx(53.55)
    assert result["accounting_residual"] == pytest.approx(0, abs=1e-8)
    for index in (2, 3):
        start(sim, index, ideas=[])
        finish(sim)
    assert not sim.receivables and not sim.unsettled
    assert sim.cash == pytest.approx(10053.55)


def test_fractional_split_blocks_before_mutating_cash_or_position():
    sim = engine()
    start(sim)
    opening(sim)
    tick(sim)
    tick(sim, volume=1000)
    order = next(iter(sim.orders.values()))
    sim.reject_order(order.intent.order_id, "retain_one_share")
    finish(sim)
    before = sim.cash, asdict(sim.positions["A"])
    with pytest.raises(ValueError, match="fractional"):
        start(sim, 1, ideas=[], actions=[action(split_ratio=0.5)])
    assert before == (sim.cash, asdict(sim.positions["A"]))


def test_split_protection_is_tick_aligned_without_losing_cost_basis():
    sim = entered()
    finish(sim)
    basis = sim.positions["A"].basis
    start(sim, 1, ideas=[], actions=[action(split_ratio=7, dividend=0)])
    position = sim.positions["A"]
    assert position.quantity == 14 and position.basis == basis
    assert position.stop == pytest.approx(12.85)
    assert position.target == pytest.approx(17.86)
    assert position.quantity * position.risk_per_share >= 2 * 10.19


def test_time_exit_is_committed_at_close_and_precedes_later_low():
    sim = entered(engine(max_hold=1))
    finish(sim)
    assert sim.positions["A"].exit_reason == "time_exit"
    start(sim, 1, ideas=[])
    tick(sim, open=105, high=110, low=80, close=100)
    assert sim.fills[-1]["price"] == 105
    assert sim.fills[-1]["reason"] == "time_exit"


def test_drawdown_circuit_breaker_halts_new_orders_and_retains_positions():
    sim = engine(
        name_fraction=1, sector_fraction=1, risk_fraction=1, heat_fraction=1, new_risk_fraction=1
    )
    start(sim, ideas=[idea(stop=50, target=225)])
    opening(sim)
    tick(sim)
    tick(sim)
    finish(sim, open=80, high=81, low=79, close=80)
    assert sim.halted and sim.positions
    start(sim, 1, ideas=[idea("B", signal=D)])
    for _ in range(5):
        tick(sim, ("A", "B"), open=80, high=81, low=79, close=80)
    assert sim.rejections["drawdown_circuit_breaker"] == 1 and sim.positions


def test_missing_full_session_held_price_cannot_be_marked_as_known():
    sim = entered()
    finish(sim)
    start(sim, 1, ideas=[])
    while sim.clock < sim.day.closes:
        sim.on_minute(sim.clock, {})
    with pytest.raises(ValueError, match="missing held-position session mark"):
        sim.finish_session()


def test_future_minutes_and_protected_dates_are_rejected():
    sim = engine()
    start(sim)
    with pytest.raises(ValueError, match="future"):
        sim.on_minute(sim.clock, {"A": bar(sim.clock + timedelta(minutes=1))})
    protected = replace(
        day(),
        session=date(2023, 1, 2),
        opens=datetime(2023, 1, 2, 9, 30, tzinfo=NY),
        closes=datetime(2023, 1, 2, 16, tzinfo=NY),
    )
    with pytest.raises(ValueError, match="holdout"):
        engine().start_session(protected, [], [], {}, {})


@pytest.mark.parametrize(
    "changes",
    [
        {"participation": 0},
        {"tick": True},
        {"latency_minutes": 10, "expiry_minutes": 15},
        {"settlement_days": 0},
    ],
)
def test_invalid_execution_policy(changes):
    with pytest.raises(ValueError):
        ExecutionPolicy(**changes)
