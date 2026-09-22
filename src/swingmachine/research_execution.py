"""Offline executable-intent replay; no broker, account or runtime dependencies.

Minute OHLCV imposes capacity/path assumptions, not tick-exact execution proof.
One completed-minute clock is authoritative. Orders are immutable intents;
execution state, reservations and accounting evolve separately.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from statistics import mean, stdev

from swingmachine.research_daily import CalendarDay, CorporateAction, Minute, aware
from swingmachine.research_reset import Idea, ResearchConfig, fingerprint, guard_research_dates


@dataclass(frozen=True)
class ExecutionPolicy:
    decision_minutes: int = 5
    latency_minutes: int = 1
    expiry_minutes: int = 15
    participation: float = 0.001
    tick: float = 0.01
    settlement_days: int = 2
    drawdown_stop: float = 0.10

    def __post_init__(self):
        for name in ("decision_minutes", "latency_minutes", "expiry_minutes", "settlement_days"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError("positive integer execution timing required")
        if self.decision_minutes + self.latency_minutes >= self.expiry_minutes:
            raise ValueError("entry must activate before expiry")
        for name in ("participation", "tick", "drawdown_stop"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value < 1:
                raise ValueError("invalid execution fraction/tick")


@dataclass(frozen=True)
class OrderIntent:
    order_id: str
    symbol: str
    signal_date: date
    submitted_at: datetime
    active_at: datetime
    expires_at: datetime
    quantity: int
    limit: float
    stop: float
    target: float
    sector: str
    risk_per_share: float
    observed_close: float
    observation_end: datetime


@dataclass
class OrderState:
    intent: OrderIntent
    remaining: int
    status: str = "ACCEPTED"
    cancel_at: datetime | None = None


@dataclass
class Holding:
    order_id: str
    symbol: str
    sector: str
    quantity: int
    basis: float
    stop: float
    target: float
    risk_per_share: float
    entry_session: date
    bars_held: int = 0
    exit_reason: str | None = None


class ExecutionSimulator:
    """Consume complete minute groups in order, sharing cash/risk/capacity.

    Settlement dates are an explicit input, never silently inferred from the
    exchange calendar. Intraday cash earns zero. Equity marks are raw prices;
    all-in costs are charged on filled notional and are not included twice.
    """

    def __init__(
        self, config: ResearchConfig, policy: ExecutionPolicy, settlement_dates: list[date]
    ):
        if not settlement_dates or settlement_dates != sorted(set(settlement_dates)):
            raise ValueError("explicit increasing settlement dates required")
        self.config, self.policy = config, policy
        self.settlement_dates = tuple(settlement_dates)
        self.cash = config.initial_cash
        self.positions: dict[str, Holding] = {}
        self.orders: dict[str, OrderState] = {}
        self.lifecycles: dict[str, dict] = {}
        self.unsettled: list[tuple[date, float]] = []
        self.receivables: list[tuple[date, float]] = []
        self.marks: dict[str, tuple[datetime, float]] = {}
        self.events: list[dict] = []
        self.fills: list[dict] = []
        self.equity: list[dict] = []
        self.rejections = Counter()
        self.total_realized = self.distributions = self.fees = 0.0
        self.peak = config.initial_cash
        self.halted = False
        self.last_session: date | None = None
        self.day: CalendarDay | None = None
        self.clock: datetime | None = None
        self.action_ids: set[tuple[str, str]] = set()

    @property
    def cost(self) -> float:
        return self.config.cost_bps_per_side / 10_000

    def _event(self, kind: str, **values) -> None:
        self.events.append({"at": self.clock.isoformat(), "kind": kind, **values})

    def _end_order(self, order: OrderState, status: str, reason: str) -> None:
        if not order.remaining:
            return
        cancelled = order.remaining
        order.remaining, order.status, order.cancel_at = 0, status, None
        self._event(status, order_id=order.intent.order_id, quantity=cancelled, reason=reason)

    def request_cancel(self, order_id: str) -> None:
        """Inert client request: remaining quantity can fill until acknowledgement."""
        order = self.orders[order_id]
        if order.remaining and order.cancel_at is None:
            order.cancel_at = self.clock + timedelta(minutes=self.policy.latency_minutes)
            self._event("CANCEL_REQUESTED", order_id=order_id, ack_at=order.cancel_at.isoformat())

    def reject_order(self, order_id: str, reason: str) -> None:
        """Explicit simulated broker rejection; retain previously filled exposure."""
        self._end_order(self.orders[order_id], "REJECTED", reason)

    def _settlement(self, trade_day: date) -> date:
        index = bisect_right(self.settlement_dates, trade_day) + self.policy.settlement_days - 1
        if index >= len(self.settlement_dates):
            raise ValueError("settlement calendar does not cover sale maturity")
        return self.settlement_dates[index]

    def start_session(
        self,
        day: CalendarDay,
        ideas: list[Idea],
        actions: list[CorporateAction],
        entry_sectors: dict[str, str],
        held_sectors: dict[str, str],
    ) -> None:
        """References supplied here must be selected as of the 5-minute decision.

        The replay adapter owns reference provenance/coverage and full exchange
        calendar traversal. This core rejects future signals/actions and never
        consults current-session daily bars to size orders.
        """
        guard_research_dates(day.session, day.session)
        if not day.opens or not day.closes or self.day is not None:
            raise ValueError("one unfinished open session at a time")
        if self.last_session is not None and day.session <= self.last_session:
            raise ValueError("sessions must increase")
        if len({i.symbol for i in ideas}) != len(ideas) or any(
            i.signal_date >= day.session for i in ideas
        ):
            raise ValueError("unique prior-close ideas required")
        if self.last_session and any(i.signal_date != self.last_session for i in ideas):
            raise ValueError("stale ideas cannot cross missing sessions")
        if day.closes <= day.opens + timedelta(minutes=self.policy.expiry_minutes):
            raise ValueError("session too short for the execution policy")
        self._settlement(day.session)  # Validate future metadata before any mutation/fill.
        if len({(a.security_id, a.event_id) for a in actions}) != len(actions) or any(
            (a.security_id, a.event_id) in self.action_ids
            or a.ex_session != day.session
            or a.known_at > day.opens
            for a in actions
        ):
            raise ValueError("duplicate, misdated or late corporate action")
        # Multiple actions use a combined split, with distributions per final share.
        grouped: dict[str, list[CorporateAction]] = {}
        for action in actions:
            grouped.setdefault(action.security_id, []).append(action)
        for symbol, items in grouped.items():
            if symbol in self.positions:
                ratio = math.prod(a.split_ratio for a in items)
                quantity = self.positions[symbol].quantity * ratio
                if (
                    not math.isfinite(quantity)
                    or quantity < 1
                    or not math.isclose(quantity, round(quantity), abs_tol=1e-9)
                    or self.positions[symbol].stop / ratio < self.policy.tick
                ):
                    raise ValueError("fractional split/cash-in-lieu terms unresolved")
        self.day, self.clock = day, day.opens
        self.ideas = sorted(ideas, key=lambda i: (-i.score, i.symbol))
        self.entry_sectors, self.held_sectors = dict(entry_sectors), dict(held_sectors)
        self.opening: dict[str, set[datetime]] = {}
        self.changed_actions = set(grouped)
        for name in ("unsettled", "receivables"):
            items = getattr(self, name)
            self.cash += sum(value for due, value in items if due <= day.session)
            setattr(self, name, [(due, value) for due, value in items if due > day.session])
        for symbol, items in grouped.items():
            self.action_ids.update((a.security_id, a.event_id) for a in items)
            if symbol not in self.positions:
                continue
            position = self.positions[symbol]
            ratio = math.prod(a.split_ratio for a in items)
            if ratio != 1:
                self.lifecycles[position.order_id]["splits"].append(
                    {"session": str(day.session), "ratio": ratio}
                )
            position.quantity = round(position.quantity * ratio)
            tick = self.policy.tick
            position.stop = math.floor(position.stop / ratio / tick + 1e-10) * tick
            position.target = math.ceil(position.target / ratio / tick - 1e-10) * tick
            position.risk_per_share = max(
                position.risk_per_share / ratio,
                position.basis / position.quantity - position.stop * (1 - self.cost),
            )
            if symbol in self.marks:
                stamp, price = self.marks[symbol]
                self.marks[symbol] = (stamp, price / ratio)
            for action in items:
                entitlement = position.quantity * action.dividend
                self.distributions += entitlement
                self.lifecycles[position.order_id]["dividends"] += entitlement
                if entitlement:
                    if action.payment_session <= day.session:
                        self.cash += entitlement
                    else:
                        self.receivables.append((action.payment_session, entitlement))
                self._event(
                    "ACTION",
                    event_id=action.event_id,
                    symbol=symbol,
                    split_ratio=action.split_ratio,
                    entitlement=entitlement,
                    adjusted_stop=position.stop,
                    adjusted_target=position.target,
                    adjusted_quantity=position.quantity,
                )

    def _reserved(self) -> tuple[float, float, dict[str, float]]:
        cash = risk = 0.0
        sectors: dict[str, float] = {}
        for order in self.orders.values():
            if order.remaining:
                intent, q = order.intent, order.remaining
                cash += q * intent.limit * (1 + self.cost)
                risk += q * intent.risk_per_share
                sectors[intent.sector] = sectors.get(intent.sector, 0) + q * intent.limit
        return cash, risk, sectors

    def _value(self) -> tuple[float, float]:
        if self.positions.keys() - self.marks.keys():
            raise ValueError("missing held-position valuation")
        market = sum(p.quantity * self.marks[s][1] for s, p in self.positions.items())
        value = self.cash + market + sum(x[1] for x in self.unsettled + self.receivables)
        return value, market

    def _reject_idea(self, idea: Idea, reason: str) -> None:
        self.rejections[reason] += 1
        self._event("IDEA_REJECTED", symbol=idea.symbol, reason=reason)

    def _decide(self) -> None:
        end = self.day.opens + timedelta(minutes=self.policy.decision_minutes)
        required = {
            self.day.opens + timedelta(minutes=n) for n in range(self.policy.decision_minutes)
        }
        stale = any(
            s not in self.marks
            or self.marks[s][0] != end
            or self.held_sectors.get(s, "UNKNOWN") == "UNKNOWN"
            for s in self.positions
        )
        if stale:
            for idea in self.ideas:
                self._reject_idea(idea, "missing_fresh_held_mark_or_sector")
            return
        for symbol, position in self.positions.items():
            position.sector = self.held_sectors[symbol]
        equity, _ = self._value()
        self.peak = max(self.peak, equity)
        self.halted |= equity <= self.peak * (1 - self.policy.drawdown_stop)
        new_risk = 0.0
        c = self.config
        for idea in self.ideas:
            reason = None
            if self.halted:
                reason = "drawdown_circuit_breaker"
            elif idea.symbol in self.positions:
                reason = "existing_position"
            elif self.entry_sectors.get(idea.symbol, "UNKNOWN") == "UNKNOWN":
                reason = "entry_context_unavailable_or_ineligible"
            elif idea.symbol in self.changed_actions:
                reason = "action_at_entry_requires_new_plan"
            elif self.opening.get(idea.symbol, set()) != required:
                reason = "incomplete_opening_window"
            if reason:
                self._reject_idea(idea, reason)
                continue
            observed = self.marks[idea.symbol][1]
            tick = self.policy.tick
            stop = math.floor(idea.stop / tick + 1e-10) * tick
            target = math.floor(idea.target / tick + 1e-10) * tick
            maximum = (
                (target + c.min_rr * stop) * (1 - self.cost) / ((1 + c.min_rr) * (1 + self.cost))
            )
            limit = math.floor(min(observed, maximum) / tick + 1e-10) * tick
            risk = limit * (1 + self.cost) - stop * (1 - self.cost)
            reward = target * (1 - self.cost) - limit * (1 + self.cost)
            if stop <= 0 or observed <= stop or limit <= stop or reward < c.min_rr * risk - 1e-9:
                self._reject_idea(idea, "gap_or_reward_risk")
                continue
            reserved_cash, reserved_risk, reserved_sectors = self._reserved()
            sector = self.entry_sectors[idea.symbol]
            heat = sum(p.quantity * p.risk_per_share for p in self.positions.values())
            sector_value = sum(
                p.quantity * self.marks[s][1]
                for s, p in self.positions.items()
                if p.sector == sector
            )
            cash_per_share = limit * (1 + self.cost)
            quantity = math.floor(
                max(
                    0,
                    min(
                        (self.cash - reserved_cash) / cash_per_share,
                        c.name_fraction * equity / cash_per_share,
                        (
                            c.sector_fraction * equity
                            - sector_value
                            - reserved_sectors.get(sector, 0)
                        )
                        / cash_per_share,
                        c.risk_fraction * equity / risk,
                        (c.heat_fraction * equity - heat - reserved_risk) / risk,
                        (c.new_risk_fraction * equity - new_risk) / risk,
                        idea.average_volume * c.max_volume_fraction,
                    ),
                )
            )
            if not quantity:
                self._reject_idea(idea, "portfolio_or_liquidity_limit")
                continue
            identity = f"{self.day.session}:{idea.symbol}:{len(self.orders)}"
            intent = OrderIntent(
                identity,
                idea.symbol,
                idea.signal_date,
                end,
                end + timedelta(minutes=self.policy.latency_minutes),
                self.day.opens + timedelta(minutes=self.policy.expiry_minutes),
                quantity,
                limit,
                stop,
                target,
                sector,
                risk,
                observed,
                end,
            )
            self.orders[identity] = OrderState(intent, quantity)
            self.lifecycles[identity] = {
                "symbol": idea.symbol,
                "initial_risk": 0.0,
                "realized_pnl": 0.0,
                "dividends": 0.0,
                "entry_session": str(self.day.session),
                "exit_session": None,
                "filled_quantity": 0,
                "exit_quantity": 0,
                "splits": [],
            }
            new_risk += quantity * risk
            self._event("ORDER_ACCEPTED", order_id=identity, quantity=quantity)
        self._invariants()

    def _record_fill(self, order_id: str, side: str, q: int, price: float, reason: str) -> None:
        fee = q * price * self.cost
        self.fees += fee
        self.fills.append(
            {
                "order_id": order_id,
                "side": side,
                "quantity": q,
                "price": price,
                "cost": fee,
                "interval_start": self.clock.isoformat(),
                "interval_end": (self.clock + timedelta(minutes=1)).isoformat(),
                "reason": reason,
            }
        )

    def _sell(self, symbol: str, bar: Minute, capacity: int, reason: str, price: float) -> int:
        p = self.positions[symbol]
        q = min(p.quantity, capacity)
        if not q:
            self._event("EXIT_CAPACITY_UNAVAILABLE", symbol=symbol, reason=reason)
            return 0
        proceeds = q * price * (1 - self.cost)
        basis = p.basis * q / p.quantity
        self.unsettled.append((self._settlement(self.day.session), proceeds))
        self.total_realized += proceeds - basis
        life = self.lifecycles[p.order_id]
        life["realized_pnl"] += proceeds - basis
        life["exit_quantity"] += q
        self._record_fill(p.order_id, "SELL", q, price, reason)
        p.quantity -= q
        p.basis -= basis
        if not p.quantity:
            life["exit_session"] = str(self.day.session)
            del self.positions[symbol]
        return q

    def _exit_existing(self, symbol: str, bar: Minute, capacity: int) -> int:
        p = self.positions[symbol]
        stop = bar.low <= p.stop
        target = bar.high > p.target  # A touch alone does not prove a passive fill.
        if p.exit_reason == "stop":
            return self._sell(symbol, bar, capacity, "persistent_stop", bar.open)
        if p.exit_reason == "time_exit":
            # The previously committed market exit precedes intrabar extrema.
            used = self._sell(symbol, bar, capacity, "time_exit", bar.open)
            if symbol in self.positions and stop:
                self.positions[symbol].exit_reason = "stop"
            return used
        if stop:
            p.exit_reason = "stop"
            self._end_order(self.orders[p.order_id], "CANCELLED", "protective_stop")
            reason = (
                "ambiguous_stop_first" if target else "gap_stop" if bar.open < p.stop else "stop"
            )
            return self._sell(symbol, bar, capacity, reason, min(bar.open, p.stop))
        if target:
            self._end_order(self.orders[p.order_id], "CANCELLED", "target_exit")
            return self._sell(symbol, bar, capacity, "target", p.target)
        return 0

    def _buy(self, order: OrderState, bar: Minute, capacity: int) -> int:
        intent = order.intent
        if not order.remaining or not intent.active_at <= self.clock < intent.expires_at:
            return 0
        if bar.low >= intent.limit or not capacity:
            return 0
        q, price = min(order.remaining, capacity), min(bar.open, intent.limit)
        basis = q * price * (1 + self.cost)
        self.cash -= basis
        order.remaining -= q
        order.status = "PARTIALLY_FILLED" if order.remaining else "FILLED"
        if not order.remaining:
            order.cancel_at = None  # A terminal fill resolves a pending cancel request.
        p = self.positions.get(intent.symbol)
        if p is None:
            p = self.positions[intent.symbol] = Holding(
                intent.order_id,
                intent.symbol,
                intent.sector,
                0,
                0,
                intent.stop,
                intent.target,
                intent.risk_per_share,
                self.day.session,
            )
        p.quantity += q
        p.basis += basis
        life = self.lifecycles[intent.order_id]
        life["filled_quantity"] += q
        life["initial_risk"] += q * intent.risk_per_share
        self._record_fill(intent.order_id, "BUY", q, price, "fixed_limit")
        # Atomic contingent protection is a declared offline hypothesis. An
        # intrabar passive fill may follow the high, so no same-bar target credit.
        remaining = capacity - q
        if bar.low <= p.stop:
            p.exit_reason = "stop"
            self._end_order(order, "CANCELLED", "entry_bar_protective_stop")
            reason = "entry_bar_ambiguous_stop_first" if bar.high > p.target else "entry_bar_stop"
            remaining -= self._sell(intent.symbol, bar, remaining, reason, min(price, p.stop))
        return capacity - remaining

    def on_minute(self, timestamp: datetime, rows: dict[str, Minute]) -> None:
        """Rows belong to this completed interval; missing symbols stay absent."""
        aware(timestamp)
        if self.day is None or timestamp != self.clock or timestamp >= self.day.closes:
            raise ValueError("minute clock must be contiguous and inside the active session")
        if any(b.timestamp != timestamp for b in rows.values()):
            raise ValueError("future or mismatched minute observation")
        for order in self.orders.values():
            if order.cancel_at is not None and timestamp >= order.cancel_at:
                self._end_order(order, "CANCELLED", "client_cancel_acknowledged")
            elif timestamp >= order.intent.expires_at:
                self._end_order(order, "EXPIRED", "entry_window_ended")
        capacities = {s: math.floor(b.volume * self.policy.participation) for s, b in rows.items()}
        bought = set()
        for order in self.orders.values():
            symbol = order.intent.symbol
            held = self.positions.get(symbol)
            if held and held.exit_reason in ("stop", "time_exit"):
                continue
            if symbol in rows and order.remaining:
                used = self._buy(order, rows[symbol], capacities[symbol])
                capacities[symbol] -= used
                if used:
                    bought.add(symbol)
        # A still-active partial entry can fill before an intrabar stop. Do not
        # retrospectively cancel that buy using the later low. _buy accounts for
        # the resulting position's stop and shared capacity. Target-high ordering
        # remains unresolved in any interval receiving additional entry fills.
        for symbol in sorted(self.positions):
            if symbol in rows and symbol not in bought:
                capacities[symbol] -= self._exit_existing(symbol, rows[symbol], capacities[symbol])
        for symbol, bar in rows.items():
            self.marks[symbol] = (timestamp + timedelta(minutes=1), bar.close)
            if timestamp < self.day.opens + timedelta(minutes=self.policy.decision_minutes):
                self.opening.setdefault(symbol, set()).add(timestamp)
        self.clock += timedelta(minutes=1)
        if self.clock == self.day.opens + timedelta(minutes=self.policy.decision_minutes):
            self._decide()
        self._invariants()

    def _invariants(self) -> None:
        cash, _, _ = self._reserved()
        if self.cash < -1e-7 or cash > self.cash + 1e-7:
            raise ValueError("cash/reservation invariant violated")
        if any(p.quantity <= 0 or p.basis < -1e-7 for p in self.positions.values()):
            raise ValueError("position invariant violated")
        value, market = self._value()
        unrealized = market - sum(p.basis for p in self.positions.values())
        residual = (
            value - self.config.initial_cash - self.total_realized - self.distributions - unrealized
        )
        if abs(residual) > max(1e-6, self.config.initial_cash * 1e-10):
            raise ValueError("portfolio accounting does not reconcile")

    def finish_session(self) -> None:
        if self.day is None or self.clock != self.day.closes:
            raise ValueError("session must be completely replayed before close")
        for symbol in self.positions:
            if self.marks[symbol][0].date() != self.day.closes.date():
                raise ValueError("missing held-position session mark; accounting unresolved")
        for order in self.orders.values():
            self._end_order(order, "EXPIRED", "session_closed")
        value, market = self._value()
        self.peak = max(self.peak, value)
        self.halted |= value <= self.peak * (1 - self.policy.drawdown_stop)
        for position in self.positions.values():
            position.bars_held += 1
            if position.bars_held >= self.config.max_hold and position.exit_reason is None:
                position.exit_reason = "time_exit"
                self._event("TIME_EXIT_COMMITTED", symbol=position.symbol)
        self.equity.append(
            {
                "session": str(self.day.session),
                "equity": value,
                "settled_cash": self.cash,
                "unsettled_proceeds": sum(x[1] for x in self.unsettled),
                "dividend_receivable": sum(x[1] for x in self.receivables),
                "market_value": market,
                "positions": len(self.positions),
                "drawdown_halted": self.halted,
                "marks": {
                    s: {"observation_end": self.marks[s][0].isoformat(), "price": self.marks[s][1]}
                    for s in self.positions
                },
            }
        )
        self._invariants()
        self.last_session, self.day = self.day.session, None

    def result(self) -> dict:
        if self.day is not None:
            raise ValueError("cannot report an unfinished session")
        self._invariants()
        value, market = self._value()
        values = [self.config.initial_cash, *(e["equity"] for e in self.equity)]
        returns = [b / a - 1 for a, b in zip(values[:-1], values[1:], strict=True)]
        peak, drawdown = values[0], 0.0
        for x in values:
            peak = max(peak, x)
            drawdown = min(drawdown, x / peak - 1)
        trades = []
        for identity, life in self.lifecycles.items():
            if life["exit_session"] is not None:
                pnl = life["realized_pnl"] + life["dividends"]
                trades.append(
                    {"order_id": identity, **life, "net_pnl": pnl, "r": pnl / life["initial_risk"]}
                )
        intents = [
            {**asdict(o.intent), "state": o.status, "remaining": o.remaining}
            for o in self.orders.values()
        ]
        intents = [
            {k: v.isoformat() if isinstance(v, (datetime, date)) else v for k, v in r.items()}
            for r in intents
        ]
        vol = stdev(returns) if len(returns) > 1 else 0
        return {
            "status": "OFFLINE_MINUTE_EXECUTION_MECHANICS_ONLY",
            "config": asdict(self.config),
            "execution_policy": asdict(self.policy),
            "policy_sha256": fingerprint(asdict(self.policy)),
            "sessions": len(returns),
            "net_return": value / values[0] - 1,
            "max_drawdown": drawdown,
            "mean_close_exposure": mean(e["market_value"] / e["equity"] for e in self.equity)
            if self.equity
            else 0,
            "sharpe_zero_cash_rate": math.sqrt(252) * mean(returns) / vol if vol else None,
            "closed_trades": len(trades),
            "open_positions": len(self.positions),
            "total_costs": self.fees,
            "realized_pnl": self.total_realized,
            "distributions_accrued": self.distributions,
            "unrealized_price_pnl": market - sum(p.basis for p in self.positions.values()),
            "accounting_residual": value
            - values[0]
            - self.total_realized
            - self.distributions
            - market
            + sum(p.basis for p in self.positions.values()),
            "orders": intents,
            "fills": self.fills,
            "events": self.events,
            "trades": trades,
            "lifecycles": [{"order_id": key, **value} for key, value in self.lifecycles.items()],
            "open_position_states": [
                asdict(p) | {"entry_session": str(p.entry_session)} for p in self.positions.values()
            ],
            "equity": self.equity,
            "rejections": dict(self.rejections),
            "limitations": [
                "venue bar volume is an assumed capacity ceiling, not proven executable liquidity",
                "atomic contingent protection is an offline hypothesis "
                "requiring broker qualification",
                "passive entry-bar targets receive no credit; ambiguous stops use adverse ordering",
                "marks may be stale within a session; timestamps retained; "
                "missing session marks block",
                "open positions remain marked and unsettled cash/receivables remain explicit",
                "not qualified historical strategy outcomes or live readiness",
            ],
        }
