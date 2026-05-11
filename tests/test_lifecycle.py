from __future__ import annotations

from datetime import datetime

import pytest

from swingmachine.config import load_strategy_config
from swingmachine.entries import build_setup_snapshot, make_entry_order_intent
from swingmachine.enums import (
    PatternType,
    PendingEntryCancelReason,
    RegimeState,
    SymbolLifecycleState,
)
from swingmachine.lifecycle import (
    classify_symbol_state,
    evaluate_pending_entry,
    pending_entry_expired,
    setup_can_be_armed,
)


def _entry_intent():
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    setup = build_setup_snapshot(
        {
            "symbol": "AAA",
            "session_date": "2026-04-23",
            "pattern_type": PatternType.PULLBACK.value,
            "setup_id": "setup-lifecycle-1",
            "setup_start_date": "2026-04-18",
            "setup_end_date": "2026-04-23",
            "setup_high": 100.0,
            "setup_low": 94.0,
            "setup_high_date": "2026-04-18",
            "setup_low_date": "2026-04-22",
            "atr_14": 2.0,
            "setup_valid": True,
        },
        config,
    )
    intent = make_entry_order_intent(
        setup,
        quantity=10,
        strategy_id=config.strategy.id,
        config_hash=config.config_hash(),
        created_at=datetime(2026, 4, 23, 16, 10),
        expires_at=datetime(2026, 4, 28, 16, 0),
    )
    return config, setup, intent


def test_setup_can_be_armed_respects_spent_setup_registry() -> None:
    config, _, _ = _entry_intent()

    assert (
        setup_can_be_armed(
            "setup-lifecycle-1",
            spent_setup_ids=("setup-lifecycle-1",),
            config=config,
        )
        is False
    )

    relaxed_config = config.model_copy(
        update={
            "setup": config.setup.model_copy(
                update={
                    "setup_registry": config.setup.setup_registry.model_copy(
                        update={"disallow_reuse_of_spent_setup_id": False}
                    )
                }
            )
        }
    )
    assert (
        setup_can_be_armed(
            "setup-lifecycle-1",
            spent_setup_ids=("setup-lifecycle-1",),
            config=relaxed_config,
        )
        is True
    )


def test_classify_symbol_state_returns_candidate_for_spent_setup() -> None:
    config, setup, _ = _entry_intent()

    state = classify_symbol_state(
        hard_eligible=True,
        candidate_eligible=True,
        setup_valid=True,
        setup_id=setup.setup_id,
        spent_setup_ids=(setup.setup_id,),
        config=config,
    )

    assert state == SymbolLifecycleState.CANDIDATE


def test_classify_symbol_state_handles_exit_pending_and_invariant_violation() -> None:
    config, _, _ = _entry_intent()

    assert (
        classify_symbol_state(
            hard_eligible=False,
            candidate_eligible=False,
            active_position=True,
            exit_intent_active=True,
            config=config,
        )
        == SymbolLifecycleState.EXIT_PENDING
    )

    with pytest.raises(ValueError):
        classify_symbol_state(
            hard_eligible=True,
            candidate_eligible=True,
            pending_entry_active=True,
            active_position=True,
            config=config,
        )


def test_pending_entry_expired_uses_configured_session_threshold() -> None:
    config, _, _ = _entry_intent()

    assert (
        pending_entry_expired(
            regular_sessions_elapsed=config.entry.order_expiry_sessions - 1,
            config=config,
        )
        is False
    )
    assert (
        pending_entry_expired(
            regular_sessions_elapsed=config.entry.order_expiry_sessions,
            config=config,
        )
        is True
    )


def test_evaluate_pending_entry_cancels_for_open_gap_and_marks_setup_spent() -> None:
    config, setup, intent = _entry_intent()

    evaluation = evaluate_pending_entry(
        intent,
        config=config,
        official_open_next=setup.entry_limit + 0.01,
        hard_eligible_after_cancel=True,
        candidate_eligible_after_cancel=True,
    )

    assert evaluation.should_cancel is True
    assert evaluation.cancel_reasons == (PendingEntryCancelReason.OPEN_GAP_ABOVE_LIMIT,)
    assert evaluation.expired is False
    assert evaluation.mark_setup_spent is True
    assert evaluation.next_state == SymbolLifecycleState.CANDIDATE


def test_evaluate_pending_entry_collects_stale_order_cancel_reasons() -> None:
    config, _, intent = _entry_intent()

    evaluation = evaluate_pending_entry(
        intent,
        config=config,
        regular_sessions_elapsed=config.entry.order_expiry_sessions,
        regime_state=RegimeState.RISK_OFF,
        earnings_window_breached=True,
        shared_setup_preconditions_pass=False,
        intent_invalidated=True,
        hard_eligible_after_cancel=False,
        candidate_eligible_after_cancel=True,
    )

    assert evaluation.should_cancel is True
    assert evaluation.cancel_reasons == (
        PendingEntryCancelReason.REGIME_BLOCKED,
        PendingEntryCancelReason.EARNINGS_WINDOW_BREACHED,
        PendingEntryCancelReason.SHARED_PRECONDITIONS_FAILED,
        PendingEntryCancelReason.INTENT_INVALIDATED,
        PendingEntryCancelReason.EXPIRED,
    )
    assert evaluation.expired is True
    assert evaluation.next_state == SymbolLifecycleState.INELIGIBLE


def test_evaluate_pending_entry_fill_confirmation_transitions_to_active() -> None:
    config, _, intent = _entry_intent()

    evaluation = evaluate_pending_entry(
        intent,
        config=config,
        fill_confirmed=True,
        official_open_next=float(intent.limit_price) + 1.0,
        regular_sessions_elapsed=config.entry.order_expiry_sessions,
        regime_state=RegimeState.RISK_OFF,
        earnings_window_breached=True,
        shared_setup_preconditions_pass=False,
        intent_invalidated=True,
    )

    assert evaluation.should_cancel is False
    assert evaluation.cancel_reasons == ()
    assert evaluation.mark_setup_spent is False
    assert evaluation.next_state == SymbolLifecycleState.ACTIVE
