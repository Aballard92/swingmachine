from __future__ import annotations

from datetime import date, timedelta

import pytest

from swingmachine.research_reset import (
    Bar,
    Idea,
    ResearchConfig,
    ResearchSimulator,
    SignalEngine,
    guard_research_dates,
    passive_benchmark,
)

D = date(2019, 1, 2)


def bar(day=0, symbol="A", **kw):
    return Bar(
        **{
            "session": D + timedelta(days=day),
            "symbol": symbol,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1_000_000,
            "eligible": True,
            "event_known": True,
            **kw,
        }
    )


def idea(day=0, symbol="A", **kw):
    return Idea(
        **{
            "symbol": symbol,
            "signal_date": D + timedelta(days=day),
            "reference": 100.0,
            "stop": 90.0,
            "target": 125.0,
            "score": 1.0,
            "average_volume": 1_000_000,
            "sector": "UNKNOWN",
            **kw,
        }
    )


def entered(**kw):
    sim = ResearchSimulator(ResearchConfig("breakout", **kw))
    sim.step(D, [bar()], [idea()])
    sim.step(D + timedelta(days=1), [bar(1)], [])
    assert sim.positions
    return sim


def test_signal_cannot_fill_on_signal_bar():
    sim = ResearchSimulator(ResearchConfig("breakout"))
    sim.step(D, [bar(high=150, low=50)], [idea()])
    assert not sim.trades and not sim.positions
    assert sim.cash == 100_000


def test_gap_stop_uses_open_and_can_exceed_one_r():
    sim = entered()
    sim.step(D + timedelta(days=2), [bar(2, open=80, low=75, close=80)], [])
    t = sim.trades[0]
    assert t["exit_fill"] == pytest.approx(79.92)
    assert t["reason"] == "gap_stop" and t["r"] < -1
    assert sim.result()["accounting_residual"] == pytest.approx(0, abs=1e-8)


def test_ambiguous_daily_path_uses_stop_first():
    sim = entered()
    sim.step(D + timedelta(days=2), [bar(2, low=85, high=130)], [])
    assert sim.trades[0]["reason"] == "ambiguous_stop_first"
    assert sim.trades[0]["net_pnl"] < 0


def test_adverse_entry_gap_cannot_destroy_reward_risk():
    sim = ResearchSimulator(ResearchConfig("breakout"))
    sim.step(D, [bar()], [idea()])
    sim.step(D + timedelta(days=1), [bar(1, open=110, high=111, low=109, close=110)], [])
    assert not sim.positions
    assert sim.rejections["gap_or_reward_risk"] == 1


def test_missing_held_price_stops_instead_of_inventing_equity():
    sim = entered()
    with pytest.raises(ValueError, match="missing held-position"):
        sim.step(D + timedelta(days=2), [bar(2, symbol="B")], [])


def test_split_does_not_create_phantom_loss_and_dividend_reconciles():
    sim = entered()
    shares = sim.positions["A"].shares
    sim.step(
        D + timedelta(days=2),
        [bar(2, open=50, high=51, low=49, close=50, split_ratio=2, dividend=1)],
        [],
    )
    p = sim.positions["A"]
    assert p.shares == 2 * shares and p.stop == 45
    assert sim.accrued_dividends == 2 * shares
    assert sim.equity[-1]["equity"] == pytest.approx(sim.equity[-2]["equity"] + 2 * shares)
    assert sim.result()["accounting_residual"] == pytest.approx(0, abs=1e-8)


def test_new_holder_does_not_get_ex_date_dividend():
    sim = ResearchSimulator(ResearchConfig("breakout"))
    sim.step(D, [bar()], [idea()])
    sim.step(D + timedelta(days=1), [bar(1, dividend=1)], [])
    assert sim.accrued_dividends == 0


def test_time_exit_occurs_next_open_after_max_hold():
    sim = entered(max_hold=2)
    sim.step(D + timedelta(days=2), [bar(2)], [])
    assert sim.positions
    sim.step(D + timedelta(days=3), [bar(3, open=101, close=101)], [])
    assert sim.trades[0]["reason"] == "time_exit"
    assert sim.trades[0]["bars_held"] == 2


def test_cash_sector_and_daily_heat_are_shared():
    c = ResearchConfig("breakout")
    sim = ResearchSimulator(c)
    names = [f"S{x}" for x in range(20)]
    sim.step(D, [bar(symbol=s) for s in names], [idea(symbol=s) for s in names])
    sim.step(D + timedelta(days=1), [bar(1, symbol=s) for s in names], [])
    assert sim.cash >= 0
    assert sum(p.cost_basis for p in sim.positions.values()) <= 100_000 * c.sector_fraction
    assert sum(p.initial_risk for p in sim.positions.values()) <= 100_000 * c.new_risk_fraction
    assert all(p.cost_basis <= 100_000 * c.name_fraction for p in sim.positions.values())


def test_today_close_cannot_change_open_sizing():
    # Recreate the entry morning with differing close, but identical open/range.
    for close in [95, 105]:
        sim = ResearchSimulator(ResearchConfig("breakout"))
        sim.step(D, [bar()], [idea()])
        sim.step(D + timedelta(days=1), [bar(1, high=110, low=94, close=close)], [])
        if close == 95:
            first = sim.positions["A"].shares
        else:
            assert sim.positions["A"].shares == first


@pytest.mark.parametrize(
    "kw",
    [{"cost_bps_per_side": float("nan")}, {"name_fraction": 1.1}, {"min_rr": 1}, {"max_hold": 2.5}],
)
def test_invalid_configuration_is_rejected(kw):
    with pytest.raises(ValueError):
        ResearchConfig("breakout", **kw)


def test_protected_windows_and_reversed_dates_rejected():
    guard_research_dates(date(2019, 1, 1), date(2020, 11, 30))
    for start, end in [
        (date(2020, 1, 1), date(2021, 1, 1)),
        (date(2023, 1, 1), date(2023, 2, 1)),
        (D, D - timedelta(days=1)),
    ]:
        with pytest.raises(ValueError):
            guard_research_dates(start, end)


def test_prefix_features_have_no_future_dependence_and_planned_net_rr():
    engine = SignalEngine(ResearchConfig("breakout"))
    earlier = []
    for day in range(210):
        price = 100 + day
        earlier = engine.observe(
            [bar(day, open=price, high=price + 0.1, low=price - 0.1, close=price)]
        )
    assert earlier
    value = earlier[0]
    assert (value.target * 0.999 - value.reference * 1.001) / (
        value.reference * 1.001 - value.stop * 0.999
    ) == pytest.approx(2)
    # Dataclass is immutable; later shock cannot alter previous decision.
    before = (value.stop, value.target, value.score)
    engine.observe([bar(210, open=1000, high=1100, low=900, close=1000)])
    assert (value.stop, value.target, value.score) == before


def test_unknown_events_prevent_ideas():
    engine = SignalEngine(ResearchConfig("breakout"))
    for day in range(210):
        price = 100 + day
        output = engine.observe(
            [
                bar(
                    day,
                    open=price,
                    high=price + 0.1,
                    low=price - 0.1,
                    close=price,
                    event_known=False,
                )
            ]
        )
        assert not output


def test_bad_bars_and_future_ideas_fail_closed():
    for kw in [{"close": float("nan")}, {"high": 90}, {"eligible": "true"}]:
        with pytest.raises(ValueError):
            bar(**kw)
    sim = ResearchSimulator(ResearchConfig("breakout"))
    with pytest.raises(ValueError, match="ideas"):
        sim.step(D, [bar()], [idea(1)])


def test_split_at_entry_cancels_old_price_plan():
    sim = ResearchSimulator(ResearchConfig("breakout"))
    sim.step(D, [bar()], [idea()])
    sim.step(D + timedelta(days=1), [bar(1, split_ratio=2, open=50, low=49, high=51, close=50)], [])
    assert not sim.positions
    assert sim.rejections["split_at_entry_requires_new_plan"] == 1


def test_unrealized_position_is_explicit_in_results():
    result = entered().result()
    assert result["closed_trades"] == 0 and result["open_positions"] == 1
    assert result["unrealized_pnl_including_accrual"] < 0
    assert result["net_return"] < 0  # entry cost is already paid


def test_missing_symbol_resets_feature_warmup():
    engine = SignalEngine(ResearchConfig("breakout"))
    for day in range(201):
        p = 100 + day
        engine.observe([bar(day, open=p, high=p + 0.1, low=p - 0.1, close=p)])
    engine.observe([bar(201, symbol="B")])
    assert not engine.observe([bar(202, open=400, high=401, low=399, close=400)])


def test_cost_stress_reduces_identical_trade_profit():
    pnls = []
    for cost in [5, 10, 20]:
        sim = entered(cost_bps_per_side=cost)
        sim.step(D + timedelta(days=2), [bar(2, high=126, close=124)], [])
        pnls.append(sim.result()["net_return"])
    assert pnls == sorted(pnls, reverse=True)


def test_benchmark_split_dividend_and_cost_have_known_value():
    config = ResearchConfig("breakout")
    result = passive_benchmark(
        [
            bar(dividend=1),  # buying on ex date is not entitled to this dividend
            bar(1, split_ratio=2, open=50, high=51, low=49, close=50, dividend=1),
        ],
        config,
    )
    shares = 100_000 / 100.1
    expected = shares * 2 * 50 + shares * 2
    assert result["net_marked_return"] == pytest.approx(expected / 100_000 - 1)
    assert result["dividend_receivable"] == pytest.approx(shares * 2)
