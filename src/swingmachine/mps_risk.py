from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from swingmachine.mps_config import MpsConfig
from swingmachine.mps_contracts import MpsCandidate, MpsEntryPlan, MpsPosition


def portfolio_heat(
    positions: Sequence[MpsPosition], current_prices: Mapping[str, float], equity: float
) -> float:
    if equity <= 0:
        raise ValueError("equity must be positive")
    risk = sum(
        position.quantity * max(current_prices[position.security_id] - position.active_stop, 0.0)
        for position in positions
        if position.security_id in current_prices
    )
    return risk / equity


def plan_entry(
    candidate: MpsCandidate,
    config: MpsConfig,
    *,
    equity: float,
    cash: float,
    regime_multiplier: float,
    positions: Sequence[MpsPosition],
    current_prices: Mapping[str, float],
) -> MpsEntryPlan:
    if equity <= 0 or cash < 0:
        raise ValueError("equity must be positive and cash nonnegative")
    if candidate.signal_atr20 is None or candidate.structure_stop is None:
        raise ValueError("candidate is missing ATR or structure stop")
    entry_cap = (
        candidate.signal_close + config.entry.maximum_absolute_gap_atr * candidate.signal_atr20
    )
    stop_at_cap = min(
        candidate.structure_stop,
        entry_cap - config.initial_stop.minimum_volatility_distance_atr * candidate.signal_atr20,
    )
    risk_per_share = entry_cap - stop_at_cap
    risk_budget = equity * config.risk.base_risk_fraction_per_trade * regime_multiplier
    quantity_by_risk = math.floor(risk_budget / risk_per_share) if risk_per_share > 0 else 0
    quantity_by_notional = math.floor(
        equity * config.risk.maximum_position_notional_fraction / entry_cap
    )
    quantity_by_liquidity = math.floor(
        candidate.adv20_dollars * config.risk.maximum_adv_participation / entry_cap
    )
    quantity_by_cash = math.floor(cash / entry_cap)
    quantity = max(
        0, min(quantity_by_risk, quantity_by_notional, quantity_by_liquidity, quantity_by_cash)
    )
    reason = "APPROVED"
    approved = quantity >= 1
    if len(positions) >= config.risk.maximum_positions:
        approved, reason = False, "MAXIMUM_POSITIONS"
    if any(position.security_id == candidate.security_id for position in positions):
        approved, reason = False, "PYRAMIDING_PROHIBITED"
    gross = sum(
        position.quantity * current_prices.get(position.security_id, position.entry_price)
        for position in positions
    )
    if gross + quantity * entry_cap > equity * config.risk.maximum_gross_exposure:
        approved, reason = False, "MAXIMUM_GROSS_EXPOSURE"
    sector_notional = sum(
        position.quantity * current_prices.get(position.security_id, position.entry_price)
        for position in positions
        if position.sector == candidate.sector
    )
    if (
        sector_notional + quantity * entry_cap
        > equity * config.risk.maximum_sector_notional_fraction
    ):
        approved, reason = False, "MAXIMUM_SECTOR_NOTIONAL"
    proposed_risk = quantity * risk_per_share
    if (
        portfolio_heat(positions, current_prices, equity) + proposed_risk / equity
        > config.risk.maximum_portfolio_heat
    ):
        approved, reason = False, "MAXIMUM_PORTFOLIO_HEAT"
    sector_heat = (
        sum(
            position.quantity
            * max(
                current_prices.get(position.security_id, position.entry_price)
                - position.active_stop,
                0.0,
            )
            for position in positions
            if position.sector == candidate.sector
        )
        / equity
    )
    if sector_heat + proposed_risk / equity > config.risk.maximum_sector_heat:
        approved, reason = False, "MAXIMUM_SECTOR_HEAT"
    if quantity < 1:
        approved, reason = False, "QUANTITY_BELOW_ONE"
    return MpsEntryPlan(
        candidate=candidate,
        approved=approved,
        reason_code=reason,
        entry_cap=entry_cap,
        planned_stop=stop_at_cap,
        risk_budget=risk_budget,
        quantity=quantity if approved else 0,
        regime_multiplier=regime_multiplier,
    )


def actual_initial_stop(candidate: MpsCandidate, entry_price: float, config: MpsConfig) -> float:
    if candidate.signal_atr20 is None or candidate.structure_stop is None:
        raise ValueError("candidate is missing ATR or structure stop")
    return min(
        candidate.structure_stop,
        entry_price - config.initial_stop.minimum_volatility_distance_atr * candidate.signal_atr20,
    )


def post_fill_quantity(
    plan: MpsEntryPlan, entry_price: float, config: MpsConfig
) -> tuple[int, int]:
    stop = actual_initial_stop(plan.candidate, entry_price, config)
    actual_per_share = entry_price - stop
    maximum_risk = plan.risk_budget * config.risk.post_fill_risk_tolerance
    allowed = max(0, math.floor(maximum_risk / actual_per_share)) if actual_per_share > 0 else 0
    retained = min(plan.quantity, allowed)
    return retained, plan.quantity - retained
