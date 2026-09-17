"""Funded, capacity-limited passive SPY benchmark for the offline minute replay."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

from swingmachine.research_daily import CalendarDay, CorporateAction, Minute
from swingmachine.research_execution import ExecutionPolicy
from swingmachine.research_reset import guard_research_dates


@dataclass(frozen=True)
class BenchmarkOrder:
    submitted_at: datetime
    active_at: datetime
    expires_at: datetime
    quantity: int
    limit: float


class PassiveBenchmark:
    """One fixed initial buy; distributions become cash only on payment dates.

    No stop/target, time exit, extra investment or boundary liquidation. A failed
    opening/mark/action contract is an error; a partially filled order is retained
    and reported as insufficient benchmark exposure by the evaluator.
    """

    def __init__(self, initial_cash: float, cost_bps: float, policy: ExecutionPolicy):
        if not math.isfinite(initial_cash) or initial_cash <= 0 or not 0 <= cost_bps < 100:
            raise ValueError("invalid benchmark capital or costs")
        self.initial = self.cash = initial_cash
        self.cost = cost_bps / 10000
        self.policy = policy
        self.quantity = self.remaining = self.filled = 0
        self.basis = self.distributions = self.total_costs = 0.0
        self.receivables: list[tuple[date, float]] = []
        self.equity: list[dict] = []
        self.fills: list[dict] = []
        self.order: BenchmarkOrder | None = None
        self.mark: tuple[datetime, float] | None = None
        self.day: CalendarDay | None = None
        self.clock: datetime | None = None
        self.last_day: date | None = None
        self.action_ids = set()

    def start_session(self, day: CalendarDay, actions: list[CorporateAction]) -> None:
        guard_research_dates(day.session, day.session)
        if self.day is not None or not day.opens or not day.closes:
            raise ValueError("benchmark requires one unfinished open session")
        if self.last_day and day.session <= self.last_day:
            raise ValueError("benchmark sessions must increase")
        relevant = [a for a in actions if a.security_id == "SPY"]
        if len({a.event_id for a in relevant}) != len(relevant) or any(
            a.event_id in self.action_ids or a.ex_session != day.session or a.known_at > day.opens
            for a in relevant
        ):
            raise ValueError("invalid benchmark action timing or identity")
        ratio = math.prod(a.split_ratio for a in relevant)
        shares = self.quantity * ratio
        if not math.isfinite(shares) or not math.isclose(shares, round(shares), abs_tol=1e-9):
            raise ValueError("benchmark fractional split terms unresolved")
        self.day, self.clock = day, day.opens
        self.opening = set()
        self.cash += sum(value for due, value in self.receivables if due <= day.session)
        self.receivables = [(due, value) for due, value in self.receivables if due > day.session]
        self.quantity = round(shares)
        if self.mark:
            self.mark = (self.mark[0], self.mark[1] / ratio)
        for action in relevant:
            self.action_ids.add(action.event_id)
            amount = self.quantity * action.dividend
            self.distributions += amount
            if amount:
                if action.payment_session <= day.session:
                    self.cash += amount
                else:
                    self.receivables.append((action.payment_session, amount))

    def on_minute(self, timestamp: datetime, bar: Minute | None) -> None:
        if not self.day or timestamp != self.clock or timestamp >= self.day.closes:
            raise ValueError("benchmark minute clock must be contiguous")
        if bar and bar.timestamp != timestamp:
            raise ValueError("future benchmark minute")
        if self.order and timestamp >= self.order.expires_at:
            self.remaining = 0
        if (
            bar
            and self.order
            and self.remaining
            and self.order.active_at <= timestamp < self.order.expires_at
        ):
            if bar.low < self.order.limit:
                q = min(self.remaining, math.floor(bar.volume * self.policy.participation))
                if q:
                    price = min(bar.open, self.order.limit)
                    fee = q * price * self.cost
                    paid = q * price + fee
                    self.cash -= paid
                    self.basis += paid
                    self.total_costs += fee
                    self.quantity += q
                    self.remaining -= q
                    self.filled += q
                    self.fills.append(
                        {
                            "interval_start": timestamp.isoformat(),
                            "quantity": q,
                            "price": price,
                            "cost": fee,
                        }
                    )
        if bar:
            self.mark = (timestamp + timedelta(minutes=1), bar.close)
            if timestamp < self.day.opens + timedelta(minutes=self.policy.decision_minutes):
                self.opening.add(timestamp)
        self.clock += timedelta(minutes=1)
        if self.last_day is None and self.clock == self.day.opens + timedelta(
            minutes=self.policy.decision_minutes
        ):
            expected = {
                self.day.opens + timedelta(minutes=n) for n in range(self.policy.decision_minutes)
            }
            if self.opening != expected:
                raise ValueError("benchmark opening observations incomplete")
            limit = math.floor(self.mark[1] / self.policy.tick + 1e-10) * self.policy.tick
            q = math.floor(self.cash / (limit * (1 + self.cost))) if limit else 0
            if q < 1:
                raise ValueError("benchmark capital cannot fund one share")
            self.order = BenchmarkOrder(
                self.clock,
                self.clock + timedelta(minutes=self.policy.latency_minutes),
                self.day.opens + timedelta(minutes=self.policy.expiry_minutes),
                q,
                limit,
            )
            self.remaining = q
        if self.cash < -1e-7:
            raise ValueError("benchmark cash invariant failed")

    def finish_session(self) -> None:
        if not self.day or self.clock != self.day.closes:
            raise ValueError("benchmark session unfinished")
        if not self.mark or self.mark[0].date() != self.day.closes.date():
            raise ValueError("benchmark session price missing")
        self.remaining = 0
        market = self.quantity * self.mark[1]
        receivable = sum(value for _, value in self.receivables)
        value = self.cash + receivable + market
        residual = value - self.initial - self.distributions - (market - self.basis)
        if abs(residual) > max(1e-6, self.initial * 1e-10):
            raise ValueError("benchmark accounting does not reconcile")
        self.equity.append(
            {
                "session": str(self.day.session),
                "equity": value,
                "cash": self.cash,
                "quantity": self.quantity,
                "market_value": market,
                "dividend_receivable": receivable,
                "accounting_residual": residual,
                "mark_observation_end": self.mark[0].isoformat(),
            }
        )
        self.last_day, self.day = self.day.session, None

    def result(self) -> dict:
        if self.day is not None or self.order is None:
            raise ValueError("benchmark has no complete scored run")
        order = {
            k: v.isoformat() if isinstance(v, datetime) else v
            for k, v in asdict(self.order).items()
        }
        return {
            "symbol": "SPY",
            "initial_cash": self.initial,
            "cost_bps_per_side": self.cost * 10000,
            "policy": "FUNDED_FIXED_LIMIT_BUY_HOLD_NO_REINVESTMENT",
            "order": order,
            "entry_share_fill_fraction": self.filled / self.order.quantity,
            "total_costs": self.total_costs,
            "fills": self.fills,
            "equity": self.equity,
            "net_marked_return": self.equity[-1]["equity"] / self.initial - 1,
            "limits": [
                "minute participation is assumed capacity, not proven liquidity",
                "partial initial investment remains cash; no catch-up buying",
                "open shares are marked, distributions are not reinvested",
            ],
        }
