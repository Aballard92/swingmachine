from __future__ import annotations

from swingmachine.config import StrategyRuntimeConfig
from swingmachine.contracts import ExitEvaluation, ManagedPosition
from swingmachine.enums import OrderReason, RegimeState


def trailing_is_active(
    position: ManagedPosition,
    config: StrategyRuntimeConfig,
) -> bool:
    if not config.stops.trailing.enabled:
        return False

    activation_level = (
        position.entry_fill_price
        + config.stops.trailing.activate_after_gain_atr * position.atr_at_entry
    )
    return position.highest_high_since_entry >= activation_level


def effective_trailing_multiple(
    regime_state: RegimeState,
    config: StrategyRuntimeConfig,
) -> float:
    if regime_state == RegimeState.RISK_OFF:
        return config.stops.trailing.risk_off_trailing_atr_multiple
    return config.stops.trailing.trailing_atr_multiple


def compute_updated_stop(
    position: ManagedPosition,
    *,
    atr_14: float,
    regime_state: RegimeState,
    config: StrategyRuntimeConfig,
) -> tuple[bool, float, float | None]:
    if atr_14 <= 0.0:
        raise ValueError("atr_14 must be strictly positive")

    if not trailing_is_active(position, config):
        return False, position.current_stop, None

    trailing_multiple = effective_trailing_multiple(regime_state, config)
    trailed_stop = position.highest_high_since_entry - trailing_multiple * atr_14
    return True, max(position.current_stop, trailed_stop), trailing_multiple


def progress_atr(position: ManagedPosition) -> float:
    raw_progress = (
        position.highest_high_since_entry - position.entry_fill_price
    ) / position.atr_at_entry
    return max(raw_progress, 0.0)


def time_stop_triggered(
    position: ManagedPosition,
    config: StrategyRuntimeConfig,
) -> bool:
    if not config.stops.time_stop.enabled:
        return False

    return (
        position.bars_since_entry >= config.stops.time_stop.max_bars_without_progress
        and progress_atr(position) < config.stops.time_stop.min_progress_after_n_bars_atr
    )


def earnings_exit_triggered(
    regular_closes_until_earnings_event: int | None,
    config: StrategyRuntimeConfig,
) -> bool:
    if config.events.allow_holding_through_earnings:
        return False
    if regular_closes_until_earnings_event is None:
        return False
    return regular_closes_until_earnings_event <= config.exits.earnings_exit_lead_regular_closes


def evaluate_exit_position(
    position: ManagedPosition,
    *,
    atr_14: float,
    regime_state: RegimeState,
    config: StrategyRuntimeConfig,
    regular_closes_until_earnings_event: int | None = None,
) -> ExitEvaluation:
    trailing_active, updated_stop, trailing_multiple = compute_updated_stop(
        position,
        atr_14=atr_14,
        regime_state=regime_state,
        config=config,
    )

    earnings_regular_closes = regular_closes_until_earnings_event
    if earnings_regular_closes is None:
        earnings_regular_closes = position.regular_closes_until_earnings_event

    earnings_exit = earnings_exit_triggered(earnings_regular_closes, config)
    time_exit = time_stop_triggered(position, config)

    discretionary_exit_reasons: list[OrderReason] = []
    if earnings_exit:
        discretionary_exit_reasons.append(OrderReason.EARNINGS_EXIT)
    if time_exit:
        discretionary_exit_reasons.append(OrderReason.TIME_EXIT)

    return ExitEvaluation(
        symbol=position.symbol,
        current_stop=position.current_stop,
        updated_stop=updated_stop,
        trailing_active=trailing_active,
        effective_trailing_multiple=trailing_multiple,
        progress_atr=progress_atr(position),
        time_stop_triggered=time_exit,
        earnings_exit_triggered=earnings_exit,
        should_submit_exit_intent=len(discretionary_exit_reasons) > 0,
        discretionary_exit_reasons=tuple(discretionary_exit_reasons),
    )
