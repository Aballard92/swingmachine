from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from swingmachine.config import StrategyRuntimeConfig
from swingmachine.contracts import OrderIntent

DEFAULT_SPREAD_BPS = 5.0
PARTICIPATION_IMPACT_BPS_AT_FULL_BAR = 500.0
MAX_IMPACT_BPS = 25.0


@dataclass(slots=True)
class ExecutionFill:
    reference_price: float
    execution_price: float
    transaction_cost: float
    total_cost_bps: float


def simulate_entry_fill(row: pd.Series, intent: OrderIntent) -> float | None:
    if intent.stop_price is None or intent.limit_price is None:
        raise ValueError("entry simulation requires stop_price and limit_price")

    raw_open = float(row["raw_open"])
    raw_high = float(row["raw_high"])
    raw_low = float(row["raw_low"])
    stop_price = float(intent.stop_price)
    limit_price = float(intent.limit_price)

    if stop_price <= raw_open <= limit_price:
        return raw_open
    if raw_open < stop_price and raw_high >= stop_price and raw_low <= limit_price:
        return stop_price
    return None


def simulate_stop_fill(
    *,
    raw_open: float,
    raw_low: float,
    stop_price: float,
) -> float | None:
    if raw_open <= stop_price:
        return raw_open
    if raw_low <= stop_price:
        return stop_price
    return None


def row_float(
    row: pd.Series,
    column: str,
    *,
    default: float | None = None,
) -> float | None:
    if column not in row.index or pd.isna(row[column]):
        return default
    return float(row[column])


def execution_cost_bps(
    row: pd.Series,
    *,
    quantity: int,
    config: StrategyRuntimeConfig,
) -> float:
    spread_bps = 0.0
    if config.backtest.include_spread_model:
        spread_bps = row_float(row, "spread_bps", default=DEFAULT_SPREAD_BPS) or 0.0

    impact_bps = 0.0
    if config.backtest.include_market_impact_model:
        raw_volume = row_float(row, "raw_volume")
        if raw_volume is not None and raw_volume > 0.0:
            participation = min(quantity / raw_volume, 1.0)
            impact_bps = min(
                participation * PARTICIPATION_IMPACT_BPS_AT_FULL_BAR,
                MAX_IMPACT_BPS,
            )

    fx_cost_bps = 0.0
    if config.backtest.include_fx_cost_model:
        fx_cost_bps = row_float(row, "fx_conversion_cost_bps", default=0.0) or 0.0

    return max(spread_bps + impact_bps + fx_cost_bps, 0.0)


def apply_execution_cost(
    *,
    reference_price: float,
    row: pd.Series,
    quantity: int,
    side: Literal["buy", "sell"],
    config: StrategyRuntimeConfig,
) -> ExecutionFill:
    total_cost_bps = execution_cost_bps(
        row,
        quantity=quantity,
        config=config,
    )
    cost_multiplier = total_cost_bps / 10_000.0
    if side == "buy":
        execution_price = reference_price * (1.0 + cost_multiplier)
        transaction_cost = (execution_price - reference_price) * quantity
    else:
        execution_price = reference_price * (1.0 - cost_multiplier)
        transaction_cost = (reference_price - execution_price) * quantity

    return ExecutionFill(
        reference_price=reference_price,
        execution_price=execution_price,
        transaction_cost=max(transaction_cost, 0.0),
        total_cost_bps=total_cost_bps,
    )
