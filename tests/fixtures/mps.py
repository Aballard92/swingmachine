from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from swingmachine.mps_contracts import DailyPriceRecord, SecurityMasterRecord


def synthetic_security(*, available_at: datetime | None = None) -> SecurityMasterRecord:
    available = available_at or datetime(2020, 1, 1, tzinfo=UTC)
    return SecurityMasterRecord(
        event_time=datetime(2020, 1, 1, tzinfo=UTC),
        available_at=available,
        source_version="synthetic-v1",
        source_record_id="security-AAA-v1",
        security_id="SEC-AAA",
        ticker="AAA",
        effective_from=datetime(2020, 1, 1, tzinfo=UTC),
        security_type="common_stock",
        primary_exchange="NYSE",
        country_of_primary_listing="US",
        sector="Technology",
        is_tradable=True,
        is_halted=False,
        is_delisted=False,
        shares_outstanding=100_000_000,
    )


def synthetic_prices(count: int = 260) -> tuple[DailyPriceRecord, ...]:
    start = date(2020, 1, 1)
    rows = []
    for index in range(count):
        session = start + timedelta(days=index)
        close = 100.0 + index * 0.2
        rows.append(
            DailyPriceRecord(
                event_time=datetime.combine(session, datetime.min.time(), tzinfo=UTC),
                available_at=datetime.combine(session, datetime.max.time(), tzinfo=UTC),
                source_version="synthetic-v1",
                source_record_id=f"price-{session.isoformat()}",
                security_id="SEC-AAA",
                session_date=session,
                open=close - 0.1,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=1_000_000,
                total_return_adjusted_close=close,
            )
        )
    return tuple(rows)
