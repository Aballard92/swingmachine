from __future__ import annotations

from collections.abc import Collection

from swingmachine.config import StrategyRuntimeConfig
from swingmachine.contracts import OrderIntent, PendingEntryEvaluation
from swingmachine.enums import (
    OrderReason,
    OrderType,
    PendingEntryCancelReason,
    RegimeState,
    SymbolLifecycleState,
)


def setup_can_be_armed(
    setup_id: str | None,
    *,
    spent_setup_ids: Collection[str] = (),
    config: StrategyRuntimeConfig,
) -> bool:
    if setup_id is None:
        return False
    if not config.setup.setup_registry.disallow_reuse_of_spent_setup_id:
        return True
    return setup_id not in spent_setup_ids


def resolve_post_cancel_state(
    *,
    hard_eligible: bool,
    candidate_eligible: bool,
) -> SymbolLifecycleState:
    if not hard_eligible:
        return SymbolLifecycleState.INELIGIBLE
    if candidate_eligible:
        return SymbolLifecycleState.CANDIDATE
    return SymbolLifecycleState.ELIGIBLE


def classify_symbol_state(
    *,
    hard_eligible: bool,
    candidate_eligible: bool,
    setup_valid: bool = False,
    setup_id: str | None = None,
    spent_setup_ids: Collection[str] = (),
    pending_entry_active: bool = False,
    active_position: bool = False,
    exit_intent_active: bool = False,
    config: StrategyRuntimeConfig,
) -> SymbolLifecycleState:
    if pending_entry_active and active_position:
        raise ValueError("ACTIVE and PENDING_ENTRY may not coexist for the same symbol")
    if exit_intent_active and not active_position:
        raise ValueError("EXIT_PENDING requires an active position")

    if exit_intent_active:
        return SymbolLifecycleState.EXIT_PENDING
    if active_position:
        return SymbolLifecycleState.ACTIVE
    if pending_entry_active:
        return SymbolLifecycleState.PENDING_ENTRY
    if not hard_eligible:
        return SymbolLifecycleState.INELIGIBLE
    if (
        candidate_eligible
        and setup_valid
        and setup_can_be_armed(
            setup_id,
            spent_setup_ids=spent_setup_ids,
            config=config,
        )
    ):
        return SymbolLifecycleState.ARMED
    if candidate_eligible:
        return SymbolLifecycleState.CANDIDATE
    return SymbolLifecycleState.ELIGIBLE


def pending_entry_expired(
    *,
    regular_sessions_elapsed: int,
    config: StrategyRuntimeConfig,
) -> bool:
    if regular_sessions_elapsed < 0:
        raise ValueError("regular_sessions_elapsed cannot be negative")
    return regular_sessions_elapsed >= config.entry.order_expiry_sessions


def _validate_pending_entry_intent(intent: OrderIntent) -> None:
    if intent.reason != OrderReason.ENTRY:
        raise ValueError("pending-entry evaluation requires an ENTRY order intent")
    if intent.order_type != OrderType.STOP_LIMIT:
        raise ValueError("pending-entry evaluation requires a STOP_LIMIT order intent")
    if intent.limit_price is None:
        raise ValueError("pending-entry STOP_LIMIT intent must include limit_price")


def evaluate_pending_entry(
    intent: OrderIntent,
    *,
    config: StrategyRuntimeConfig,
    official_open_next: float | None = None,
    regular_sessions_elapsed: int = 0,
    regime_state: RegimeState | None = None,
    earnings_window_breached: bool = False,
    shared_setup_preconditions_pass: bool = True,
    intent_invalidated: bool = False,
    fill_confirmed: bool = False,
    hard_eligible_after_cancel: bool = True,
    candidate_eligible_after_cancel: bool = False,
) -> PendingEntryEvaluation:
    _validate_pending_entry_intent(intent)

    if fill_confirmed:
        return PendingEntryEvaluation(
            symbol=intent.symbol,
            setup_id=intent.setup_id,
            should_cancel=False,
            cancel_reasons=(),
            expired=False,
            mark_setup_spent=False,
            next_state=SymbolLifecycleState.ACTIVE,
        )

    cancel_reasons: list[PendingEntryCancelReason] = []
    if (
        official_open_next is not None
        and intent.limit_price is not None
        and config.entry.cancel_unfilled_order_if_open_above_limit
        and official_open_next > float(intent.limit_price)
    ):
        cancel_reasons.append(PendingEntryCancelReason.OPEN_GAP_ABOVE_LIMIT)
    if regime_state is not None and not config.regime_action(regime_state).entry_enabled:
        cancel_reasons.append(PendingEntryCancelReason.REGIME_BLOCKED)
    if earnings_window_breached:
        cancel_reasons.append(PendingEntryCancelReason.EARNINGS_WINDOW_BREACHED)
    if not shared_setup_preconditions_pass:
        cancel_reasons.append(PendingEntryCancelReason.SHARED_PRECONDITIONS_FAILED)
    if intent_invalidated:
        cancel_reasons.append(PendingEntryCancelReason.INTENT_INVALIDATED)
    if pending_entry_expired(
        regular_sessions_elapsed=regular_sessions_elapsed,
        config=config,
    ):
        cancel_reasons.append(PendingEntryCancelReason.EXPIRED)

    should_cancel = len(cancel_reasons) > 0
    next_state = SymbolLifecycleState.PENDING_ENTRY
    if should_cancel:
        next_state = resolve_post_cancel_state(
            hard_eligible=hard_eligible_after_cancel,
            candidate_eligible=candidate_eligible_after_cancel,
        )

    return PendingEntryEvaluation(
        symbol=intent.symbol,
        setup_id=intent.setup_id,
        should_cancel=should_cancel,
        cancel_reasons=tuple(cancel_reasons),
        expired=PendingEntryCancelReason.EXPIRED in cancel_reasons,
        mark_setup_spent=should_cancel and intent.setup_id is not None,
        next_state=next_state,
    )
