"""Isolated offline research mechanics for SWING-RF-001; no broker/runtime imports.

Inputs are validated daily bars, not unadjusted Databento files. A successful
simulation is mechanical evidence only. Real-data promotion is deliberately absent.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from statistics import mean, stdev
from typing import Literal

Family = Literal["momentum", "breakout", "reversal"]
PROTECTED_WINDOWS = ((date(2020, 12, 4), date(2025, 12, 10)),)


def fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def guard_research_dates(start: date, end: date) -> None:
    if start > end:
        raise ValueError("reversed research dates")
    if any(start <= right and end >= left for left, right in PROTECTED_WINDOWS):
        raise ValueError("research window intersects the preserved frozen holdout")


@dataclass(frozen=True)
class ResearchConfig:
    family: Family
    initial_cash: float = 100_000.0
    cost_bps_per_side: float = 10.0
    risk_fraction: float = 0.003
    name_fraction: float = 0.08
    sector_fraction: float = 0.20
    heat_fraction: float = 0.02
    new_risk_fraction: float = 0.01
    max_hold: int = 20
    min_rr: float = 2.0
    stop_atr: float = 2.0
    min_price: float = 5.0
    min_dollar_volume: float = 10_000_000.0
    max_volume_fraction: float = 0.001

    def __post_init__(self) -> None:
        if self.family not in ("momentum", "breakout", "reversal"):
            raise ValueError("unknown hypothesis family")
        for key, value in asdict(self).items():
            if key != "family" and (not math.isfinite(value) or value <= 0):
                raise ValueError(f"invalid research parameter: {key}")
        if self.cost_bps_per_side >= 100 or self.min_rr < 2 or self.max_hold > 20:
            raise ValueError("cost, RR or holding period outside the research contract")
        if isinstance(self.max_hold, bool) or not isinstance(self.max_hold, int):
            raise ValueError("holding period must be an integer")
        fractions = (
            self.risk_fraction,
            self.name_fraction,
            self.sector_fraction,
            self.heat_fraction,
            self.new_risk_fraction,
            self.max_volume_fraction,
        )
        if any(v > 1 for v in fractions):
            raise ValueError("fractions cannot exceed one")


@dataclass(frozen=True)
class Bar:
    session: date
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    # Input adapter must certify split continuity. Dividends are per held share,
    # accrued on ex date in research; this is NOT withdrawable broker cash.
    split_ratio: float = 1.0
    dividend: float = 0.0
    sector: str = "UNKNOWN"
    event_known: bool = False
    sessions_to_earnings: int | None = None
    eligible: bool = False

    def __post_init__(self) -> None:
        if not self.symbol or not self.sector:
            raise ValueError("symbol and sector must be explicit")
        values = (
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume,
            self.split_ratio,
            self.dividend,
        )
        if not all(math.isfinite(v) for v in values):
            raise ValueError("non-finite bar")
        if min(self.open, self.low, self.close, self.split_ratio) <= 0:
            raise ValueError("nonpositive price or split ratio")
        if self.high < max(self.open, self.close, self.low) or self.low > min(
            self.open, self.close
        ):
            raise ValueError("inconsistent OHLC")
        if self.volume < 0 or self.dividend < 0:
            raise ValueError("negative volume or dividend")
        if type(self.event_known) is not bool or type(self.eligible) is not bool:
            raise ValueError("eligibility and event knowledge must be explicit booleans")
        if self.sessions_to_earnings is not None and (
            type(self.sessions_to_earnings) is not int or self.sessions_to_earnings < 0
        ):
            raise ValueError("invalid earnings distance")


@dataclass(frozen=True)
class Idea:
    symbol: str
    signal_date: date
    reference: float
    stop: float
    target: float
    score: float
    average_volume: float
    sector: str

    def __post_init__(self) -> None:
        if (
            not self.symbol
            or not self.sector
            or not all(
                math.isfinite(x)
                for x in (self.reference, self.stop, self.target, self.score, self.average_volume)
            )
        ):
            raise ValueError("invalid idea")
        if not 0 < self.stop < self.reference < self.target or self.average_volume <= 0:
            raise ValueError("invalid target-bearing trade plan")


@dataclass
class Position:
    idea: Idea
    shares: float
    entry: float
    stop: float
    target: float
    entry_session: date
    initial_risk: float
    cost_basis: float
    bars_held: int = 0
    dividends: float = 0.0


class SignalEngine:
    """Prefix-only features; past bars rescaled only for splits effective today."""

    def __init__(self, config: ResearchConfig) -> None:
        self.config = config
        self.history: dict[str, list[Bar]] = {}
        self.last_session: date | None = None

    def observe(self, bars: list[Bar]) -> list[Idea]:
        sessions = {b.session for b in bars}
        if len(sessions) != 1 or len({b.symbol for b in bars}) != len(bars):
            raise ValueError("one nonempty unique-symbol session required")
        session = next(iter(sessions))
        if self.last_session is not None and session <= self.last_session:
            raise ValueError("sessions must increase strictly")
        # The caller supplies every official session, including sparse ones.
        present = {b.symbol for b in bars}
        for symbol in self.history.keys() - present:
            self.history[symbol] = []
        self.last_session = session
        candidates: list[Idea] = []
        c = self.config
        cost = c.cost_bps_per_side / 10_000
        for b in sorted(bars, key=lambda x: x.symbol):
            history = self.history.setdefault(b.symbol, [])
            if history and b.session <= history[-1].session:
                raise ValueError("duplicate or out-of-order session")
            if b.split_ratio != 1:
                ratio = b.split_ratio
                history[:] = [
                    Bar(
                        **{
                            **asdict(x),
                            "open": x.open / ratio,
                            "high": x.high / ratio,
                            "low": x.low / ratio,
                            "close": x.close / ratio,
                            "volume": x.volume * ratio,
                            "dividend": x.dividend / ratio,
                            "split_ratio": 1.0,
                        }
                    )
                    for x in history
                ]
            history.append(b)
            if len(history) > 253:
                del history[0]
            if len(history) < 200 or not b.eligible or not b.event_known:
                continue
            if b.sessions_to_earnings is not None and b.sessions_to_earnings <= c.max_hold:
                continue
            last20 = history[-20:]
            adv = mean(x.close * x.volume for x in last20)
            ma200 = mean(x.close for x in history[-200:])
            atr = mean(
                max(x.high - x.low, abs(x.high - prev.close), abs(x.low - prev.close))
                for prev, x in zip(history[-15:-1], history[-14:], strict=True)
            )
            if b.close < c.min_price or adv < c.min_dollar_volume or atr <= 0:
                continue
            if b.close <= ma200:
                continue
            momentum = history[-22].close / history[-127].close - 1.0
            breakout = b.close > max(x.high for x in history[-21:-1])
            displacement = (mean(x.close for x in last20) - b.close) / atr
            if c.family == "momentum":
                allowed, score = momentum > 0, momentum
            elif c.family == "breakout":
                allowed, score = breakout, momentum
            else:
                allowed, score = displacement >= 1.5, displacement
            if not allowed:
                continue
            stop = b.close - c.stop_atr * atr
            if stop <= 0:
                continue
            planned_entry = b.close * (1 + cost)
            planned_risk = planned_entry - stop * (1 - cost)
            target = (planned_entry + c.min_rr * planned_risk) / (1 - cost)
            candidates.append(
                Idea(
                    b.symbol,
                    b.session,
                    b.close,
                    stop,
                    target,
                    score,
                    mean(x.volume for x in last20),
                    b.sector,
                )
            )
        candidates.sort(key=lambda x: (-x.score, x.symbol))
        if c.family == "momentum" and candidates:
            candidates = candidates[: max(1, math.ceil(len(candidates) * 0.20))]
        return candidates


class ResearchSimulator:
    """Cash portfolio with next-open entries and conservative daily path bounds.

    Daily OHLC cannot resolve stop/target order; stop wins on ambiguous bars.
    Closing prices are never used to fund/sort orders at the same morning's open.
    """

    def __init__(self, config: ResearchConfig) -> None:
        self.config = config
        self.cash = config.initial_cash
        self.accrued_dividends = 0.0
        self.positions: dict[str, Position] = {}
        self.pending: list[Idea] = []
        self.trades: list[dict] = []
        self.equity: list[dict] = []
        self.rejections: Counter = Counter()
        self.last_session: date | None = None

    def _exit(self, symbol: str, bar: Bar, price: float, reason: str) -> None:
        p = self.positions.pop(symbol)
        fill = price * (1 - self.config.cost_bps_per_side / 10_000)
        proceeds = p.shares * fill
        self.cash += proceeds
        pnl = proceeds - p.cost_basis + p.dividends
        self.trades.append(
            {
                "symbol": symbol,
                "signal_date": p.idea.signal_date.isoformat(),
                "entry_date": p.entry_session.isoformat(),
                "exit_date": bar.session.isoformat(),
                "entry_fill": p.entry,
                "exit_fill": fill,
                "shares": p.shares,
                "net_pnl": pnl,
                "r": pnl / p.initial_risk,
                "reason": reason,
                "dividends": p.dividends,
                "bars_held": p.bars_held,
            }
        )

    def step(self, session: date, bars: list[Bar], ideas_at_close: list[Idea]) -> None:
        if self.last_session is not None and session <= self.last_session:
            raise ValueError("sessions must increase strictly")
        rows = {b.symbol: b for b in bars}
        if len(rows) != len(bars) or any(b.session != session for b in bars):
            raise ValueError("duplicate symbol or mixed sessions")
        if any(i.signal_date != session or i.symbol not in rows for i in ideas_at_close):
            raise ValueError("ideas must belong to the current completed session")
        missing = set(self.positions) - rows.keys()
        if missing:
            raise ValueError(f"missing held-position bar; accounting incomplete: {sorted(missing)}")
        cost = self.config.cost_bps_per_side / 10_000
        c = self.config
        # Corporate actions precede the open; only yesterday's holders accrue dividends.
        for symbol, p in list(self.positions.items()):
            b = rows[symbol]
            p.shares *= b.split_ratio
            p.entry /= b.split_ratio
            p.stop /= b.split_ratio
            p.target /= b.split_ratio
            dividend = b.dividend * p.shares
            p.dividends += dividend
            self.accrued_dividends += dividend
        opening_equity = (
            self.cash
            + self.accrued_dividends
            + sum(p.shares * rows[s].open for s, p in self.positions.items())
        )
        # Overnight protective stops and scheduled time exits happen before new buys.
        for symbol, p in list(self.positions.items()):
            b = rows[symbol]
            if b.open <= p.stop:
                self._exit(symbol, b, b.open, "gap_stop")
            elif p.bars_held >= c.max_hold:
                self._exit(symbol, b, b.open, "time_exit")
            elif b.open >= p.target:
                self._exit(symbol, b, p.target, "target_at_open_conservative")
        new_risk = 0.0
        for idea in self.pending:
            b = rows.get(idea.symbol)
            if b is None:
                self.rejections["missing_entry_bar"] += 1
                continue
            if idea.symbol in self.positions:
                self.rejections["existing_position"] += 1
                continue
            # Entry permission uses yesterday's knowledge, never today's close/event flags.
            if b.split_ratio != 1:
                self.rejections["split_at_entry_requires_new_plan"] += 1
                continue
            entry = b.open * (1 + cost)
            risk = entry - idea.stop * (1 - cost)
            reward = idea.target * (1 - cost) - entry
            if b.open <= idea.stop or risk <= 0 or reward / risk + 1e-10 < c.min_rr:
                self.rejections["gap_or_reward_risk"] += 1
                continue
            heat = sum(p.initial_risk for p in self.positions.values())
            sector_value = sum(
                p.shares * rows[s].open
                for s, p in self.positions.items()
                if p.idea.sector == idea.sector
            )
            risk_budget = min(
                c.risk_fraction * opening_equity,
                c.heat_fraction * opening_equity - heat,
                c.new_risk_fraction * opening_equity - new_risk,
            )
            shares = math.floor(
                max(
                    0.0,
                    min(
                        risk_budget / risk,
                        c.name_fraction * opening_equity / entry,
                        (c.sector_fraction * opening_equity - sector_value) / entry,
                        self.cash / entry,
                        idea.average_volume * c.max_volume_fraction,
                    ),
                )
            )
            if shares < 1:
                self.rejections["portfolio_or_liquidity_limit"] += 1
                continue
            basis = shares * entry
            self.cash -= basis
            new_risk += shares * risk
            self.positions[idea.symbol] = Position(
                idea, shares, entry, idea.stop, idea.target, session, shares * risk, basis
            )
        for symbol, p in list(self.positions.items()):
            b = rows[symbol]
            p.bars_held += 1
            if b.low <= p.stop:
                reason = "ambiguous_stop_first" if b.high >= p.target else "stop"
                self._exit(symbol, b, p.stop, reason)
            elif b.high >= p.target:
                self._exit(symbol, b, p.target, "target")
        market_value = sum(p.shares * rows[s].close for s, p in self.positions.items())
        total = self.cash + self.accrued_dividends + market_value
        self.equity.append(
            {
                "session": session.isoformat(),
                "equity": total,
                "cash": self.cash,
                "dividend_receivable": self.accrued_dividends,
                "market_value": market_value,
                "positions": len(self.positions),
            }
        )
        self.pending = ideas_at_close
        self.last_session = session

    def result(self) -> dict:
        initial = self.config.initial_cash
        values = [initial, *(x["equity"] for x in self.equity)]
        returns = [b / a - 1 for a, b in zip(values[:-1], values[1:], strict=True)]
        peak, drawdown = initial, 0.0
        for value in values:
            peak = max(peak, value)
            drawdown = min(drawdown, value / peak - 1)
        vol = stdev(returns) if len(returns) > 1 else 0.0
        open_value = self.equity[-1]["market_value"] if self.equity else 0.0
        open_basis = sum(p.cost_basis for p in self.positions.values())
        open_dividends = sum(p.dividends for p in self.positions.values())
        closed_pnl = sum(t["net_pnl"] for t in self.trades)
        unrealized = open_value - open_basis + open_dividends
        residual = values[-1] - initial - closed_pnl - unrealized
        if abs(residual) > max(1e-6, initial * 1e-10):
            raise ValueError("portfolio accounting does not reconcile")
        return {
            "status": "MECHANICAL_RESEARCH_ONLY",
            "config": asdict(self.config),
            "config_sha256": fingerprint(asdict(self.config)),
            "sessions": len(returns),
            "net_return": values[-1] / initial - 1,
            "max_drawdown": drawdown,
            "mean_close_exposure": mean(x["market_value"] / x["equity"] for x in self.equity)
            if self.equity
            else 0.0,
            "sharpe_zero_cash_rate": math.sqrt(252) * mean(returns) / vol if vol else None,
            "closed_trades": len(self.trades),
            "open_positions": len(self.positions),
            "closed_pnl": closed_pnl,
            "unrealized_pnl_including_accrual": unrealized,
            "accounting_residual": residual,
            "pending_ideas": len(self.pending),
            "rejections": dict(self.rejections),
            "trades": self.trades,
            "equity": self.equity,
            "limitations": [
                "daily OHLC stop-first ambiguity bound",
                "assumed fixed costs",
                "open-contingent sizing is idealized; executable auction/minute model unqualified",
                "dividends accrued, not reinvested",
                "open positions marked, not sold",
                "not evidence of out-of-sample edge or execution readiness",
            ],
        }


def passive_benchmark(bars: list[Bar], config: ResearchConfig) -> dict:
    """Fractional buy/hold, same cash/cost/accrual convention and evaluation dates.

    Full-market exposure is a hurdle, not a risk-matched alpha estimate.
    """
    if not bars or len({b.symbol for b in bars}) != 1:
        raise ValueError("one benchmark symbol required")
    if [b.session for b in bars] != sorted({b.session for b in bars}):
        raise ValueError("benchmark sessions must be unique and ordered")
    cost = config.cost_bps_per_side / 10_000
    shares = config.initial_cash / (bars[0].open * (1 + cost))
    dividends = 0.0
    values = []
    for index, b in enumerate(bars):
        if index:
            shares *= b.split_ratio
            dividends += b.dividend * shares
        values.append(shares * b.close + dividends)
    return {
        "symbol": bars[0].symbol,
        "net_marked_return": values[-1] / config.initial_cash - 1,
        "dividend_receivable": dividends,
        "closing_sale_cost": "not sold; marked like strategy",
        "comparison": "full exposure hurdle, not alpha",
        "sessions": len(bars),
    }
