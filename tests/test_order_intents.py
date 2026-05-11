from __future__ import annotations

from datetime import date, datetime

from swingmachine.config import load_strategy_config
from swingmachine.contracts import CanonicalSnapshotHashRecord, RegimeSnapshot
from swingmachine.entries import build_setup_snapshot, make_entry_order_intent
from swingmachine.enums import OrderIntentStatus, PatternType, RegimeState
from swingmachine.order_intents import OrderIntentService
from swingmachine.storage import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)


def _service() -> OrderIntentService:
    engine = create_database_engine()
    initialize_database(engine)
    return OrderIntentService(create_session_factory(engine))


def _entry_intent(setup_id: str, *, symbol: str = "AAA"):
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    setup = build_setup_snapshot(
        {
            "symbol": symbol,
            "session_date": "2026-04-23",
            "pattern_type": PatternType.PULLBACK.value,
            "setup_id": setup_id,
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


def test_submit_intent_persists_and_dedupes() -> None:
    service = _service()
    _, _, intent = _entry_intent("setup-intent-1")

    first = service.submit_intent(intent)
    second = service.submit_intent(intent)

    assert first.accepted is True
    assert second.accepted is False
    assert second.reason == "DUPLICATE_DEDUPE_KEY"
    assert second.existing_intent_id == intent.intent_id
    assert service.get_intent(intent.intent_id) == intent


def test_single_pending_entry_per_symbol_is_enforced() -> None:
    service = _service()
    _, _, first_intent = _entry_intent("setup-intent-1", symbol="AAA")
    _, _, second_intent = _entry_intent("setup-intent-2", symbol="AAA")

    accepted = service.submit_intent(first_intent)
    rejected = service.submit_intent(second_intent)

    assert accepted.accepted is True
    assert rejected.accepted is False
    assert rejected.reason == "PENDING_ENTRY_EXISTS"
    assert rejected.existing_intent_id == first_intent.intent_id


def test_spent_setup_blocks_resubmission_but_new_setup_can_proceed() -> None:
    service = _service()
    _, _, first_intent = _entry_intent("setup-intent-1", symbol="AAA")
    _, _, replacement_intent = _entry_intent("setup-intent-2", symbol="AAA")

    assert service.submit_intent(first_intent).accepted is True
    service.mark_terminal(first_intent.intent_id, status=OrderIntentStatus.CANCELLED)
    service.mark_setup_spent(
        setup_id="setup-intent-1",
        symbol="AAA",
        marked_at=datetime(2026, 4, 24, 9, 31),
        reason="OPEN_GAP_ABOVE_LIMIT",
    )

    _, _, blocked_intent = _entry_intent("setup-intent-1", symbol="AAA")
    blocked = service.submit_intent(blocked_intent)
    replacement = service.submit_intent(replacement_intent)

    assert blocked.accepted is False
    assert blocked.reason == "SPENT_SETUP_BLOCKED"
    assert replacement.accepted is True


def test_recovery_returns_nonterminal_entry_intents_and_spent_setups() -> None:
    service = _service()
    _, _, first_intent = _entry_intent("setup-intent-1", symbol="AAA")
    _, _, second_intent = _entry_intent("setup-intent-2", symbol="BBB")

    assert service.submit_intent(first_intent).accepted is True
    service.mark_submitted(first_intent.intent_id, broker_order_id="broker-1")
    assert service.submit_intent(second_intent).accepted is True
    service.mark_terminal(second_intent.intent_id, status=OrderIntentStatus.REJECTED)
    service.mark_setup_spent(
        setup_id="setup-intent-2",
        symbol="BBB",
        marked_at=datetime(2026, 4, 24, 10, 0),
        reason="BROKER_REJECT",
    )

    recovery = service.recover_state()

    assert tuple(intent.intent_id for intent in recovery.pending_entry_intents) == (
        first_intent.intent_id,
    )
    assert recovery.spent_setup_ids == ("setup-intent-2",)
    assert service.pending_entry_symbols() == ("AAA",)


def test_regime_snapshot_and_canonical_hash_round_trip() -> None:
    service = _service()
    snapshot = RegimeSnapshot(
        session_date=date(2026, 4, 23),
        benchmark_symbol="SPY",
        benchmark_close=510.0,
        benchmark_ma200=500.0,
        benchmark_ma200_slope_pct20=0.01,
        benchmark_dist_above_ma200=0.02,
        realized_vol_20=0.14,
        breadth_pct_above_ma200=0.62,
        panic_drawdown_126=-0.05,
        rebound_return_20=0.03,
        regime_state=RegimeState.RISK_ON,
        entry_enabled=True,
        size_multiplier=1.0,
        min_candidate_score_percentile=0.8,
        min_trend_quality=0.45,
    )
    hash_record = CanonicalSnapshotHashRecord(
        symbol="AAA",
        session_date=date(2026, 4, 23),
        snapshot_hash="hash-123",
        recorded_at=datetime(2026, 4, 23, 16, 5),
    )

    service.record_regime_snapshot(snapshot)
    service.record_canonical_snapshot_hash(hash_record)

    assert service.load_regime_snapshot(date(2026, 4, 23)) == snapshot
    assert (
        service.load_canonical_snapshot_hash(
            symbol="AAA",
            session_date=date(2026, 4, 23),
        )
        == hash_record
    )
