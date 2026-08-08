from __future__ import annotations

from dataclasses import dataclass

from swingmachine.mps_config import MpsConfig
from swingmachine.mps_contracts import MpsCandidate


@dataclass(frozen=True, slots=True)
class MpsExecutionResult:
    filled: bool
    reason_code: str
    reference_price: float | None
    fill_price: float | None


def apply_one_way_cost(reference_price: float, cost_bps: float, side: str) -> float:
    if reference_price <= 0 or cost_bps < 0:
        raise ValueError("reference price must be positive and costs nonnegative")
    multiplier = cost_bps / 10_000.0
    if side == "BUY":
        return reference_price * (1.0 + multiplier)
    if side == "SELL":
        return reference_price * (1.0 - multiplier)
    raise ValueError(f"unsupported side {side}")


def simulate_entry(
    candidate: MpsCandidate, next_open: float, config: MpsConfig, *, cost_bps: float | None = None
) -> MpsExecutionResult:
    if candidate.signal_atr20 is None or candidate.structure_stop is None:
        return MpsExecutionResult(False, "MISSING_SIGNAL_RISK_INPUT", None, None)
    gap = abs(next_open - candidate.signal_close)
    if gap > config.entry.maximum_absolute_gap_atr * candidate.signal_atr20:
        return MpsExecutionResult(False, "ENTRY_GAP_GUARD", None, None)
    if next_open <= candidate.structure_stop:
        return MpsExecutionResult(False, "OPEN_AT_OR_BELOW_STRUCTURE_STOP", None, None)
    cost = config.execution.baseline_one_way_cost_bps if cost_bps is None else cost_bps
    return MpsExecutionResult(True, "FILLED", next_open, apply_one_way_cost(next_open, cost, "BUY"))


def simulate_sell_stop(
    raw_open: float,
    raw_low: float,
    stop_price: float,
    config: MpsConfig,
    *,
    cost_bps: float | None = None,
) -> MpsExecutionResult:
    if raw_open <= stop_price:
        reference, reason = raw_open, "STOP_GAP"
    elif raw_low <= stop_price:
        reference, reason = stop_price, "STOP_INTRADAY"
    else:
        return MpsExecutionResult(False, "STOP_NOT_REACHED", None, None)
    cost = config.execution.baseline_one_way_cost_bps if cost_bps is None else cost_bps
    return MpsExecutionResult(True, reason, reference, apply_one_way_cost(reference, cost, "SELL"))
