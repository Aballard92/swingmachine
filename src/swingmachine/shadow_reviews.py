from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from swingmachine.analytics import (
    shadow_fill_comparisons_to_frame,
    shadow_fill_regime_stats,
    shadow_fill_status_stats,
    summarize_shadow_fill_comparisons,
)
from swingmachine.contracts import ShadowFillComparison, ShadowFillComparisonBatch
from swingmachine.enums import RegimeState, ShadowFillStatus
from swingmachine.storage import (
    load_shadow_fill_comparison_snapshots,
    load_shadow_fill_comparisons,
    record_shadow_fill_comparison_snapshot,
    upsert_shadow_fill_comparison,
)


class ShadowReviewService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_comparison_batch(
        self,
        batch: ShadowFillComparisonBatch,
        *,
        recorded_at: datetime | None = None,
    ) -> None:
        timestamp = recorded_at or datetime.utcnow()
        with self._session_factory.begin() as session:
            for comparison in batch.comparisons:
                upsert_shadow_fill_comparison(
                    session,
                    comparison,
                    source_mode=batch.source_mode,
                    recorded_at=timestamp,
                )
                record_shadow_fill_comparison_snapshot(
                    session,
                    comparison,
                    source_mode=batch.source_mode,
                    recorded_at=timestamp,
                )

    def load_comparisons(
        self,
        *,
        symbol: str | None = None,
        regime_state: RegimeState | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        statuses: Sequence[ShadowFillStatus] = (),
    ) -> tuple[ShadowFillComparison, ...]:
        with self._session_factory() as session:
            return load_shadow_fill_comparisons(
                session,
                symbol=symbol,
                regime_state=regime_state,
                date_from=date_from,
                date_to=date_to,
                statuses=tuple(statuses),
            )

    def load_comparison_snapshots(
        self,
        *,
        symbol: str | None = None,
        regime_state: RegimeState | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        statuses: Sequence[ShadowFillStatus] = (),
    ) -> tuple[ShadowFillComparison, ...]:
        with self._session_factory() as session:
            return load_shadow_fill_comparison_snapshots(
                session,
                symbol=symbol,
                regime_state=regime_state,
                date_from=date_from,
                date_to=date_to,
                statuses=tuple(statuses),
            )

    def summarize_comparisons(
        self,
        *,
        symbol: str | None = None,
        regime_state: RegimeState | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        statuses: Sequence[ShadowFillStatus] = (),
    ) -> dict[str, Any]:
        comparisons = self.load_comparisons(
            symbol=symbol,
            regime_state=regime_state,
            date_from=date_from,
            date_to=date_to,
            statuses=statuses,
        )
        return {
            "summary": summarize_shadow_fill_comparisons(comparisons),
            "by_regime": shadow_fill_regime_stats(comparisons).to_dict(orient="records"),
            "by_status": shadow_fill_status_stats(comparisons).to_dict(orient="records"),
            "rows": shadow_fill_comparisons_to_frame(comparisons).to_dict(orient="records"),
        }

    def summarize_comparison_snapshots(
        self,
        *,
        symbol: str | None = None,
        regime_state: RegimeState | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        statuses: Sequence[ShadowFillStatus] = (),
    ) -> dict[str, Any]:
        comparisons = self.load_comparison_snapshots(
            symbol=symbol,
            regime_state=regime_state,
            date_from=date_from,
            date_to=date_to,
            statuses=statuses,
        )
        return {
            "summary": summarize_shadow_fill_comparisons(comparisons),
            "by_regime": shadow_fill_regime_stats(comparisons).to_dict(orient="records"),
            "by_status": shadow_fill_status_stats(comparisons).to_dict(orient="records"),
            "rows": shadow_fill_comparisons_to_frame(comparisons).to_dict(orient="records"),
        }
