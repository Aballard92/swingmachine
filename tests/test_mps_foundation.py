from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from swingmachine.mps_config import MpsConfig, load_mps_config
from swingmachine.mps_contracts import DailyPriceRecord, DataNotAvailableError
from swingmachine.mps_data import PointInTimeDataPortal, StaticTradingCalendar
from swingmachine.mps_events import MpsEventLoop, MpsSessionPhase
from tests.fixtures.mps import synthetic_prices, synthetic_security


def test_mps_config_loads_exact_baseline_and_hashes_deterministically() -> None:
    first = load_mps_config()
    second = load_mps_config()
    assert first.config_hash() == second.config_hash()
    assert first.strategy.name == "MPS_1"
    assert first.features.atr.method == "wilder"
    assert first.risk.maximum_positions == 8
    assert first.execution.stress_one_way_cost_bps == (10.0, 20.0, 50.0)
    assert first.execution.partial_fills_enabled is False


def test_mps_config_rejects_non_baseline_pyramiding() -> None:
    payload = load_mps_config().model_dump(mode="python")
    payload["strategy"]["pyramiding"] = True
    with pytest.raises(ValidationError):
        MpsConfig.model_validate(payload)


def test_point_in_time_portal_refuses_future_price() -> None:
    record = synthetic_prices(1)[0]
    portal = PointInTimeDataPortal(security_master=[synthetic_security()], prices=[record])
    decision = record.available_at - timedelta(seconds=1)
    with pytest.raises(DataNotAvailableError, match="not available"):
        portal.price(record.security_id, record.session_date, decision)


def test_point_in_time_portal_returns_price_once_available() -> None:
    record = synthetic_prices(1)[0]
    portal = PointInTimeDataPortal(security_master=[synthetic_security()], prices=[record])
    assert portal.price(record.security_id, record.session_date, record.available_at) == record


def test_point_in_time_portal_excludes_future_security_master_revision() -> None:
    future = synthetic_security(available_at=datetime(2025, 1, 1, tzinfo=UTC))
    portal = PointInTimeDataPortal(security_master=[future], prices=[])
    assert portal.security_master_as_of(datetime(2024, 1, 1, tzinfo=UTC)) == ()


def test_point_in_time_portal_version_hash_is_order_independent() -> None:
    prices = synthetic_prices(3)
    first = PointInTimeDataPortal(security_master=[synthetic_security()], prices=prices)
    second = PointInTimeDataPortal(security_master=[synthetic_security()], prices=reversed(prices))
    assert first.version_hash() == second.version_hash()


def test_daily_price_rejects_impossible_ohlc() -> None:
    payload = synthetic_prices(1)[0].model_dump(mode="python")
    payload["high"] = payload["low"] - 1.0
    with pytest.raises(ValidationError, match="high"):
        DailyPriceRecord.model_validate(payload)


def test_static_calendar_next_session_is_explicit() -> None:
    calendar = StaticTradingCalendar([date(2026, 1, 2), date(2026, 1, 5)])
    assert calendar.next_session(date(2026, 1, 2)) == date(2026, 1, 5)
    with pytest.raises(KeyError, match="no next session"):
        calendar.next_session(date(2026, 1, 5))


def test_event_loop_uses_exact_deterministic_phase_order() -> None:
    events = MpsEventLoop().events_for_session(date(2026, 1, 5))
    assert [event.phase for event in events] == list(MpsSessionPhase)
    assert events[0].phase is MpsSessionPhase.APPLY_CORPORATE_ACTIONS
    assert events[-1].phase is MpsSessionPhase.WRITE_AUDIT_RECORD
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
