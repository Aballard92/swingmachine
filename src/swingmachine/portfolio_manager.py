from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from swingmachine.config import StrategyRuntimeConfig
from swingmachine.contracts import EntryPlan, PortfolioEntryBatch, ProtectedPosition, SetupSnapshot
from swingmachine.entries import plan_entry, portfolio_heat
from swingmachine.enums import RegimeState


def reserved_position_from_plan(
    plan: EntryPlan,
    *,
    sector: str | None = None,
) -> ProtectedPosition:
    if not plan.approved:
        raise ValueError("plan must be approved to reserve portfolio risk")
    if plan.quantity < 1:
        raise ValueError("approved plan must have quantity >= 1")

    return ProtectedPosition(
        symbol=plan.setup.symbol,
        quantity=plan.quantity,
        entry_reference_price=plan.setup.entry_trigger,
        protective_stop=plan.setup.initial_stop,
        sector=sector,
    )


class PortfolioManager:
    def __init__(self, config: StrategyRuntimeConfig) -> None:
        self._config = config

    def plan_ranked_entries(
        self,
        setups: Sequence[SetupSnapshot],
        *,
        regime_state: RegimeState,
        equity: float,
        pending_symbols: Sequence[str] = (),
        open_positions: Sequence[ProtectedPosition] = (),
        submitted_today_risk_amount: float = 0.0,
        sector_by_symbol: Mapping[str, str | None] | None = None,
        vol_target_size_multiplier: float | None = None,
        created_at: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> PortfolioEntryBatch:
        if equity <= 0.0:
            raise ValueError("equity must be strictly positive")
        if submitted_today_risk_amount < 0.0:
            raise ValueError("submitted_today_risk_amount cannot be negative")

        projected_positions = list(open_positions)
        projected_pending_symbols = set(pending_symbols)
        running_submitted_today_risk = submitted_today_risk_amount
        batch_new_risk_amount = 0.0

        plans: list[EntryPlan] = []
        for setup in setups:
            sector = None
            if sector_by_symbol is not None:
                sector = sector_by_symbol.get(setup.symbol)

            plan = plan_entry(
                setup,
                self._config,
                regime_state=regime_state,
                equity=equity,
                pending_symbols=tuple(sorted(projected_pending_symbols)),
                open_positions=tuple(projected_positions),
                submitted_today_risk_amount=running_submitted_today_risk,
                sector=sector,
                vol_target_size_multiplier=vol_target_size_multiplier,
                created_at=created_at,
                expires_at=expires_at,
            )
            plans.append(plan)

            if not plan.approved:
                continue

            projected_pending_symbols.add(setup.symbol)
            projected_positions.append(
                reserved_position_from_plan(
                    plan,
                    sector=sector,
                )
            )

            reserved_risk_amount = setup.per_share_risk * plan.quantity
            batch_new_risk_amount += reserved_risk_amount
            running_submitted_today_risk += reserved_risk_amount

        approved_count = sum(1 for plan in plans if plan.approved)
        final_portfolio_heat = portfolio_heat(tuple(projected_positions), equity)
        final_projected_daily_new_risk = max(running_submitted_today_risk / equity, 0.0)

        return PortfolioEntryBatch(
            plans=tuple(plans),
            approved_count=approved_count,
            rejected_count=len(plans) - approved_count,
            batch_new_risk_amount=max(batch_new_risk_amount, 0.0),
            projected_portfolio_heat=max(final_portfolio_heat, 0.0),
            projected_daily_new_risk=final_projected_daily_new_risk,
        )
