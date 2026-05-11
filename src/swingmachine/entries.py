from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

import pandas as pd

from swingmachine.config import StrategyRuntimeConfig
from swingmachine.contracts import EntryPlan, OrderIntent, ProtectedPosition, SetupSnapshot
from swingmachine.enums import OrderReason, OrderSide, OrderType, RegimeState

REQUIRED_SETUP_COLUMNS = (
    "symbol",
    "session_date",
    "pattern_type",
    "setup_id",
    "setup_start_date",
    "setup_end_date",
    "setup_high",
    "setup_low",
    "setup_high_date",
    "setup_low_date",
    "atr_14",
    "setup_valid",
)


def _require_mapping_keys(
    values: Mapping[str, Any],
    required: Sequence[str],
) -> None:
    missing = [key for key in required if key not in values]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Missing required setup fields: {missing_str}")


def compute_entry_metrics(
    setup_row: Mapping[str, Any],
    config: StrategyRuntimeConfig,
) -> dict[str, float]:
    _require_mapping_keys(
        setup_row,
        (
            "setup_high",
            "setup_low",
            "atr_14",
        ),
    )

    setup_high = float(setup_row["setup_high"])
    setup_low = float(setup_row["setup_low"])
    atr_14 = float(setup_row["atr_14"])

    entry_trigger = setup_high + config.entry.entry_buffer_atr * atr_14
    entry_limit = entry_trigger + config.entry.max_gap_above_trigger_atr * atr_14

    stop_from_setup = setup_low - config.stops.setup_low_buffer_atr * atr_14
    stop_from_atr = entry_trigger - config.stops.stop_atr_multiple * atr_14
    initial_stop = min(stop_from_setup, stop_from_atr)
    per_share_risk = entry_trigger - initial_stop

    return {
        "entry_trigger": entry_trigger,
        "entry_limit": entry_limit,
        "stop_from_setup": stop_from_setup,
        "stop_from_atr": stop_from_atr,
        "initial_stop": initial_stop,
        "per_share_risk": per_share_risk,
    }


def build_setup_snapshot(
    setup_row: Mapping[str, Any],
    config: StrategyRuntimeConfig,
) -> SetupSnapshot:
    _require_mapping_keys(setup_row, REQUIRED_SETUP_COLUMNS)
    if not bool(setup_row["setup_valid"]):
        raise ValueError("Cannot build a setup snapshot from a non-valid setup row")

    metrics = compute_entry_metrics(setup_row, config)
    if metrics["per_share_risk"] <= 0.0:
        raise ValueError("per_share_risk must be strictly positive")

    return SetupSnapshot.model_validate(
        {
            "symbol": setup_row["symbol"],
            "session_date": setup_row["session_date"],
            "pattern_type": setup_row["pattern_type"],
            "setup_id": setup_row["setup_id"],
            "setup_start_date": setup_row["setup_start_date"],
            "setup_end_date": setup_row["setup_end_date"],
            "setup_high": setup_row["setup_high"],
            "setup_low": setup_row["setup_low"],
            "setup_high_date": setup_row["setup_high_date"],
            "setup_low_date": setup_row["setup_low_date"],
            "entry_trigger": metrics["entry_trigger"],
            "entry_limit": metrics["entry_limit"],
            "initial_stop": metrics["initial_stop"],
            "per_share_risk": metrics["per_share_risk"],
            "spent": False,
        }
    )


def build_setup_snapshots(
    setup_frame: pd.DataFrame,
    config: StrategyRuntimeConfig,
) -> list[SetupSnapshot]:
    snapshots: list[SetupSnapshot] = []
    for row in setup_frame.to_dict(orient="records"):
        if bool(row.get("setup_valid", False)):
            snapshots.append(build_setup_snapshot(row, config))
    return snapshots


def portfolio_heat(
    positions: Sequence[ProtectedPosition],
    equity: float,
) -> float:
    if equity <= 0.0:
        raise ValueError("equity must be strictly positive")
    risk_amount = sum(
        (position.entry_reference_price - position.protective_stop) * position.quantity
        for position in positions
    )
    return max(risk_amount / equity, 0.0)


def sector_gross_exposure(
    positions: Sequence[ProtectedPosition],
    equity: float,
) -> dict[str, float]:
    if equity <= 0.0:
        raise ValueError("equity must be strictly positive")

    exposures: dict[str, float] = {}
    for position in positions:
        if position.sector is None:
            continue
        exposures[position.sector] = (
            exposures.get(position.sector, 0.0)
            + (position.entry_reference_price * position.quantity) / equity
        )
    return exposures


def make_entry_order_intent(
    setup: SetupSnapshot,
    *,
    quantity: int,
    strategy_id: str,
    config_hash: str,
    created_at: datetime,
    expires_at: datetime | None,
) -> OrderIntent:
    if quantity < 1:
        raise ValueError("quantity must be at least 1")

    dedupe_payload = "|".join(
        [
            setup.symbol,
            setup.setup_id,
            OrderReason.ENTRY.value,
            OrderType.STOP_LIMIT.value,
            str(quantity),
            f"{setup.entry_trigger:.8f}",
            f"{setup.entry_limit:.8f}",
        ]
    )
    dedupe_key = hashlib.sha256(dedupe_payload.encode("utf-8")).hexdigest()
    intent_payload = "|".join([dedupe_key, created_at.isoformat(), str(expires_at)])
    intent_id = hashlib.sha256(intent_payload.encode("utf-8")).hexdigest()

    return OrderIntent(
        intent_id=intent_id,
        dedupe_key=dedupe_key,
        strategy_id=strategy_id,
        config_hash=config_hash,
        symbol=setup.symbol,
        setup_id=setup.setup_id,
        side=OrderSide.BUY,
        reason=OrderReason.ENTRY,
        order_type=OrderType.STOP_LIMIT,
        quantity=float(quantity),
        stop_price=setup.entry_trigger,
        limit_price=setup.entry_limit,
        created_at=created_at,
        expires_at=expires_at,
        broker_order_id=None,
    )


def plan_entry(
    setup: SetupSnapshot,
    config: StrategyRuntimeConfig,
    *,
    regime_state: RegimeState,
    equity: float,
    pending_symbols: Sequence[str] = (),
    open_positions: Sequence[ProtectedPosition] = (),
    submitted_today_risk_amount: float = 0.0,
    sector: str | None = None,
    vol_target_size_multiplier: float | None = None,
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> EntryPlan:
    if equity <= 0.0:
        raise ValueError("equity must be strictly positive")
    if submitted_today_risk_amount < 0.0:
        raise ValueError("submitted_today_risk_amount cannot be negative")

    action = config.regime_action(regime_state)
    base_risk_budget = equity * config.risk.risk_per_trade_pct_equity
    regime_risk_budget = base_risk_budget * action.size_multiplier

    effective_multiplier = 1.0
    if vol_target_size_multiplier is not None:
        effective_multiplier = min(max(vol_target_size_multiplier, 0.0), 1.0)
    effective_risk_budget = regime_risk_budget * effective_multiplier

    shares_from_risk = 0
    if setup.per_share_risk > 0.0:
        shares_from_risk = math.floor(effective_risk_budget / setup.per_share_risk)
    shares_from_notional = math.floor(
        (equity * config.risk.max_position_pct_equity) / setup.entry_trigger
    )
    quantity = min(shares_from_risk, shares_from_notional)

    current_portfolio_heat = portfolio_heat(open_positions, equity)
    proposed_risk_amount = setup.per_share_risk * max(quantity, 0)
    projected_portfolio_heat = current_portfolio_heat + proposed_risk_amount / equity
    projected_daily_new_risk = (submitted_today_risk_amount + proposed_risk_amount) / equity

    sector_exposures = sector_gross_exposure(open_positions, equity)
    current_sector_exposure = sector_exposures.get(sector, 0.0) if sector is not None else 0.0
    proposed_sector_exposure = (
        current_sector_exposure + (setup.entry_trigger * max(quantity, 0)) / equity
        if sector is not None
        else 0.0
    )

    open_symbols = {position.symbol for position in open_positions}
    pending_symbol_set = set(pending_symbols)

    reject_reasons: list[str] = []
    if not action.entry_enabled:
        reject_reasons.append("REGIME_BLOCKED")
    if setup.per_share_risk <= 0.0:
        reject_reasons.append("NON_POSITIVE_PER_SHARE_RISK")
    if setup.symbol in pending_symbol_set:
        reject_reasons.append("PENDING_ENTRY_EXISTS")
    if setup.symbol in open_symbols:
        reject_reasons.append("OPEN_POSITION_EXISTS")
    if quantity < 1:
        reject_reasons.append("SHARES_LT_ONE")
    if projected_portfolio_heat > config.risk.max_portfolio_heat_pct_equity:
        reject_reasons.append("PORTFOLIO_HEAT_LIMIT")
    if projected_daily_new_risk > config.risk.max_new_risk_per_day_pct_equity:
        reject_reasons.append("DAILY_NEW_RISK_LIMIT")
    if sector is not None and proposed_sector_exposure > config.risk.max_sector_pct_equity:
        reject_reasons.append("SECTOR_GROSS_LIMIT")

    approved = len(reject_reasons) == 0
    order_intent = None
    if approved and created_at is not None:
        order_intent = make_entry_order_intent(
            setup,
            quantity=quantity,
            strategy_id=config.strategy.id,
            config_hash=config.config_hash(),
            created_at=created_at,
            expires_at=expires_at,
        )

    return EntryPlan(
        setup=setup,
        approved=approved,
        reject_reasons=tuple(reject_reasons),
        quantity=max(quantity, 0),
        base_risk_budget=base_risk_budget,
        regime_risk_budget=regime_risk_budget,
        effective_risk_budget=effective_risk_budget,
        shares_from_risk=max(shares_from_risk, 0),
        shares_from_notional=max(shares_from_notional, 0),
        projected_portfolio_heat=max(projected_portfolio_heat, 0.0),
        projected_daily_new_risk=max(projected_daily_new_risk, 0.0),
        projected_sector_gross_exposure=max(proposed_sector_exposure, 0.0),
        order_intent=order_intent,
    )
