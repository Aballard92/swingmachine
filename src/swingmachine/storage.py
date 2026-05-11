from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, Float, String, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from swingmachine.contracts import (
    BrokerOrderSnapshot,
    CanonicalSnapshotHashRecord,
    OrderIntent,
    PaperShadowAuditRecord,
    RegimeSnapshot,
    ShadowFillComparison,
)
from swingmachine.enums import (
    AlertSeverity,
    BrokerOrderStatus,
    MonitoringAlertType,
    OrderIntentStatus,
    OrderReason,
    OrderSide,
    OrderType,
    PaperShadowAlignmentStatus,
    RegimeState,
    RuntimeMode,
    ShadowFillStatus,
)


class Base(DeclarativeBase):
    pass


class OrderIntentRow(Base):
    __tablename__ = "order_intents"

    intent_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    dedupe_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    strategy_id: Mapped[str] = mapped_column(String(128))
    config_hash: Mapped[str] = mapped_column(String(128))
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    setup_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    side: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(String(32), index=True)
    order_type: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[float] = mapped_column(Float)
    stop_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    limit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class SpentSetupRow(Base):
    __tablename__ = "spent_setups"

    setup_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    marked_at: Mapped[datetime] = mapped_column(DateTime)
    reason: Mapped[str | None] = mapped_column(String(128), nullable=True)


class RegimeSnapshotRow(Base):
    __tablename__ = "regime_snapshots"

    session_date: Mapped[date] = mapped_column(Date, primary_key=True)
    benchmark_symbol: Mapped[str] = mapped_column(String(32))
    benchmark_close: Mapped[float] = mapped_column(Float)
    benchmark_ma200: Mapped[float] = mapped_column(Float)
    benchmark_ma200_slope_pct20: Mapped[float] = mapped_column(Float)
    benchmark_dist_above_ma200: Mapped[float] = mapped_column(Float)
    realized_vol_20: Mapped[float] = mapped_column(Float)
    breadth_pct_above_ma200: Mapped[float | None] = mapped_column(Float, nullable=True)
    panic_drawdown_126: Mapped[float] = mapped_column(Float)
    rebound_return_20: Mapped[float] = mapped_column(Float)
    regime_state: Mapped[str] = mapped_column(String(32))
    entry_enabled: Mapped[bool] = mapped_column(Boolean)
    size_multiplier: Mapped[float] = mapped_column(Float)
    min_candidate_score_percentile: Mapped[float] = mapped_column(Float)
    min_trend_quality: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class CanonicalSnapshotHashRow(Base):
    __tablename__ = "canonical_snapshot_hashes"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    session_date: Mapped[date] = mapped_column(Date, primary_key=True)
    snapshot_hash: Mapped[str] = mapped_column(String(128))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class BrokerOrderRow(Base):
    __tablename__ = "broker_orders"

    broker_order_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    intent_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(16))
    order_type: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[float] = mapped_column(Float)
    stop_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    limit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class ShadowFillComparisonRow(Base):
    __tablename__ = "shadow_fill_comparisons"

    intent_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    setup_id: Mapped[str] = mapped_column(String(128), index=True)
    source_mode: Mapped[str] = mapped_column(String(16))
    source_as_of: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    source_regime_state: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )
    session_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    would_fill: Mapped[bool] = mapped_column(Boolean)
    would_remain_pending: Mapped[bool] = mapped_column(Boolean)
    would_mark_setup_spent: Mapped[bool] = mapped_column(Boolean)
    official_open: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    hypothetical_fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    transaction_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost_bps: Mapped[float | None] = mapped_column(Float, nullable=True)
    slippage_alert_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    slippage_alert_metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    slippage_alert_threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class ShadowFillComparisonSnapshotRow(Base):
    __tablename__ = "shadow_fill_comparison_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(128), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    setup_id: Mapped[str] = mapped_column(String(128), index=True)
    source_mode: Mapped[str] = mapped_column(String(16))
    source_as_of: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    source_regime_state: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )
    session_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    would_fill: Mapped[bool] = mapped_column(Boolean)
    would_remain_pending: Mapped[bool] = mapped_column(Boolean)
    would_mark_setup_spent: Mapped[bool] = mapped_column(Boolean)
    official_open: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    hypothetical_fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    transaction_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost_bps: Mapped[float | None] = mapped_column(Float, nullable=True)
    slippage_alert_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    slippage_alert_metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    slippage_alert_threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class PaperShadowAuditSnapshotRow(Base):
    __tablename__ = "paper_shadow_audit_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_batch_id: Mapped[str] = mapped_column(String(64), index=True)
    intent_id: Mapped[str] = mapped_column(String(128), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    setup_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    source_as_of: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    source_regime_state: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )
    alignment_status: Mapped[str] = mapped_column(String(64), index=True)
    paper_intent_present: Mapped[bool] = mapped_column(Boolean)
    paper_intent_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    paper_broker_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    paper_filled: Mapped[bool] = mapped_column(Boolean)
    shadow_present: Mapped[bool] = mapped_column(Boolean)
    shadow_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    shadow_would_fill: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    shadow_session_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    shadow_hypothetical_fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    shadow_total_cost_bps: Mapped[float | None] = mapped_column(Float, nullable=True)
    shadow_slippage_alert_triggered: Mapped[bool] = mapped_column(Boolean)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class RuntimeRunRow(Base):
    __tablename__ = "runtime_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    command: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    config_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class RuntimeEventRow(Base):
    __tablename__ = "runtime_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    command: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    setup_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    intent_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)


def create_database_engine(url: str = "sqlite+pysqlite:///:memory:") -> Engine:
    return create_engine(url, future=True)


def create_sqlite_engine(path: str | Path) -> Engine:
    database_path = Path(path)
    return create_database_engine(f"sqlite+pysqlite:///{database_path}")


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def initialize_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def order_intent_from_row(row: OrderIntentRow) -> OrderIntent:
    return OrderIntent(
        intent_id=row.intent_id,
        dedupe_key=row.dedupe_key,
        strategy_id=row.strategy_id,
        config_hash=row.config_hash,
        symbol=row.symbol,
        setup_id=row.setup_id,
        side=OrderSide(row.side),
        reason=OrderReason(row.reason),
        order_type=OrderType(row.order_type),
        quantity=row.quantity,
        stop_price=row.stop_price,
        limit_price=row.limit_price,
        created_at=row.created_at,
        expires_at=row.expires_at,
        broker_order_id=row.broker_order_id,
    )


def regime_snapshot_from_row(row: RegimeSnapshotRow) -> RegimeSnapshot:
    return RegimeSnapshot(
        session_date=row.session_date,
        benchmark_symbol=row.benchmark_symbol,
        benchmark_close=row.benchmark_close,
        benchmark_ma200=row.benchmark_ma200,
        benchmark_ma200_slope_pct20=row.benchmark_ma200_slope_pct20,
        benchmark_dist_above_ma200=row.benchmark_dist_above_ma200,
        realized_vol_20=row.realized_vol_20,
        breadth_pct_above_ma200=row.breadth_pct_above_ma200,
        panic_drawdown_126=row.panic_drawdown_126,
        rebound_return_20=row.rebound_return_20,
        regime_state=RegimeState(row.regime_state),
        entry_enabled=row.entry_enabled,
        size_multiplier=row.size_multiplier,
        min_candidate_score_percentile=row.min_candidate_score_percentile,
        min_trend_quality=row.min_trend_quality,
    )


def canonical_snapshot_hash_from_row(
    row: CanonicalSnapshotHashRow,
) -> CanonicalSnapshotHashRecord:
    return CanonicalSnapshotHashRecord(
        symbol=row.symbol,
        session_date=row.session_date,
        snapshot_hash=row.snapshot_hash,
        recorded_at=row.recorded_at,
    )


def broker_order_snapshot_from_row(row: BrokerOrderRow) -> BrokerOrderSnapshot:
    return BrokerOrderSnapshot(
        broker_order_id=row.broker_order_id,
        symbol=row.symbol,
        side=OrderSide(row.side),
        order_type=OrderType(row.order_type),
        quantity=row.quantity,
        stop_price=row.stop_price,
        limit_price=row.limit_price,
        status=BrokerOrderStatus(row.status),
        created_at=row.created_at,
    )


def shadow_fill_comparison_from_row(
    row: ShadowFillComparisonRow | ShadowFillComparisonSnapshotRow,
) -> ShadowFillComparison:
    slippage_alert = None
    if row.slippage_alert_triggered_at is not None:
        slippage_alert = {
            "alert_type": MonitoringAlertType.SLIPPAGE,
            "severity": AlertSeverity.WARNING,
            "message": "Adverse execution slippage exceeded the configured alert threshold",
            "triggered_at": row.slippage_alert_triggered_at,
            "kill_switch_active": False,
            "symbol": row.symbol,
            "metric_value": row.slippage_alert_metric_value,
            "threshold_value": row.slippage_alert_threshold_value,
        }

    return ShadowFillComparison.model_validate(
        {
            "snapshot_id": (
                row.snapshot_id if isinstance(row, ShadowFillComparisonSnapshotRow) else None
            ),
            "symbol": row.symbol,
            "setup_id": row.setup_id,
            "intent_id": row.intent_id,
            "recorded_at": row.recorded_at,
            "source_as_of": row.source_as_of,
            "source_regime_state": (
                None if row.source_regime_state is None else RegimeState(row.source_regime_state)
            ),
            "session_date": row.session_date,
            "status": ShadowFillStatus(row.status),
            "would_fill": row.would_fill,
            "would_remain_pending": row.would_remain_pending,
            "would_mark_setup_spent": row.would_mark_setup_spent,
            "official_open": row.official_open,
            "reference_price": row.reference_price,
            "hypothetical_fill_price": row.hypothetical_fill_price,
            "transaction_cost": row.transaction_cost,
            "total_cost_bps": row.total_cost_bps,
            "slippage_alert": slippage_alert,
            "detail": row.detail,
        }
    )


def paper_shadow_audit_record_from_snapshot_row(
    row: PaperShadowAuditSnapshotRow,
) -> PaperShadowAuditRecord:
    return PaperShadowAuditRecord.model_validate(
        {
            "snapshot_id": row.snapshot_id,
            "snapshot_batch_id": row.snapshot_batch_id,
            "recorded_at": row.recorded_at,
            "intent_id": row.intent_id,
            "symbol": row.symbol,
            "setup_id": row.setup_id,
            "created_at": row.created_at,
            "source_as_of": row.source_as_of,
            "source_regime_state": (
                None if row.source_regime_state is None else RegimeState(row.source_regime_state)
            ),
            "alignment_status": PaperShadowAlignmentStatus(row.alignment_status),
            "paper_intent_present": row.paper_intent_present,
            "paper_intent_status": (
                None
                if row.paper_intent_status is None
                else OrderIntentStatus(row.paper_intent_status)
            ),
            "broker_order_id": row.broker_order_id,
            "paper_broker_status": (
                None
                if row.paper_broker_status is None
                else BrokerOrderStatus(row.paper_broker_status)
            ),
            "paper_filled": row.paper_filled,
            "shadow_present": row.shadow_present,
            "shadow_status": (
                None if row.shadow_status is None else ShadowFillStatus(row.shadow_status)
            ),
            "shadow_would_fill": row.shadow_would_fill,
            "shadow_session_date": row.shadow_session_date,
            "shadow_hypothetical_fill_price": row.shadow_hypothetical_fill_price,
            "shadow_total_cost_bps": row.shadow_total_cost_bps,
            "shadow_slippage_alert_triggered": row.shadow_slippage_alert_triggered,
        }
    )


def upsert_spent_setup(
    session: Session,
    *,
    setup_id: str,
    symbol: str | None,
    marked_at: datetime,
    reason: str | None = None,
) -> None:
    existing = session.get(SpentSetupRow, setup_id)
    if existing is None:
        session.add(
            SpentSetupRow(
                setup_id=setup_id,
                symbol=symbol,
                marked_at=marked_at,
                reason=reason,
            )
        )
        return

    existing.symbol = symbol
    existing.marked_at = marked_at
    existing.reason = reason


def load_spent_setup_ids(session: Session) -> tuple[str, ...]:
    rows = session.scalars(select(SpentSetupRow.setup_id).order_by(SpentSetupRow.setup_id)).all()
    return tuple(rows)


def upsert_regime_snapshot(session: Session, snapshot: RegimeSnapshot) -> None:
    existing = session.get(RegimeSnapshotRow, snapshot.session_date)
    if existing is None:
        session.add(
            RegimeSnapshotRow(
                session_date=snapshot.session_date,
                benchmark_symbol=snapshot.benchmark_symbol,
                benchmark_close=snapshot.benchmark_close,
                benchmark_ma200=snapshot.benchmark_ma200,
                benchmark_ma200_slope_pct20=snapshot.benchmark_ma200_slope_pct20,
                benchmark_dist_above_ma200=snapshot.benchmark_dist_above_ma200,
                realized_vol_20=snapshot.realized_vol_20,
                breadth_pct_above_ma200=snapshot.breadth_pct_above_ma200,
                panic_drawdown_126=snapshot.panic_drawdown_126,
                rebound_return_20=snapshot.rebound_return_20,
                regime_state=snapshot.regime_state.value,
                entry_enabled=snapshot.entry_enabled,
                size_multiplier=snapshot.size_multiplier,
                min_candidate_score_percentile=snapshot.min_candidate_score_percentile,
                min_trend_quality=snapshot.min_trend_quality,
            )
        )
        return

    existing.benchmark_symbol = snapshot.benchmark_symbol
    existing.benchmark_close = snapshot.benchmark_close
    existing.benchmark_ma200 = snapshot.benchmark_ma200
    existing.benchmark_ma200_slope_pct20 = snapshot.benchmark_ma200_slope_pct20
    existing.benchmark_dist_above_ma200 = snapshot.benchmark_dist_above_ma200
    existing.realized_vol_20 = snapshot.realized_vol_20
    existing.breadth_pct_above_ma200 = snapshot.breadth_pct_above_ma200
    existing.panic_drawdown_126 = snapshot.panic_drawdown_126
    existing.rebound_return_20 = snapshot.rebound_return_20
    existing.regime_state = snapshot.regime_state.value
    existing.entry_enabled = snapshot.entry_enabled
    existing.size_multiplier = snapshot.size_multiplier
    existing.min_candidate_score_percentile = snapshot.min_candidate_score_percentile
    existing.min_trend_quality = snapshot.min_trend_quality


def load_regime_snapshot(
    session: Session,
    session_date: date,
) -> RegimeSnapshot | None:
    row = session.get(RegimeSnapshotRow, session_date)
    if row is None:
        return None
    return regime_snapshot_from_row(row)


def upsert_canonical_snapshot_hash(
    session: Session,
    record: CanonicalSnapshotHashRecord,
) -> None:
    existing = session.get(
        CanonicalSnapshotHashRow,
        {"symbol": record.symbol, "session_date": record.session_date},
    )
    if existing is None:
        session.add(
            CanonicalSnapshotHashRow(
                symbol=record.symbol,
                session_date=record.session_date,
                snapshot_hash=record.snapshot_hash,
                recorded_at=record.recorded_at,
            )
        )
        return

    existing.snapshot_hash = record.snapshot_hash
    existing.recorded_at = record.recorded_at


def load_canonical_snapshot_hash(
    session: Session,
    *,
    symbol: str,
    session_date: date,
) -> CanonicalSnapshotHashRecord | None:
    row = session.get(
        CanonicalSnapshotHashRow,
        {"symbol": symbol, "session_date": session_date},
    )
    if row is None:
        return None
    return canonical_snapshot_hash_from_row(row)


def upsert_shadow_fill_comparison(
    session: Session,
    comparison: ShadowFillComparison,
    *,
    source_mode: RuntimeMode,
    recorded_at: datetime,
) -> None:
    existing = session.get(ShadowFillComparisonRow, comparison.intent_id)
    slippage_alert = comparison.slippage_alert
    slippage_alert_triggered_at = None if slippage_alert is None else slippage_alert.triggered_at
    slippage_alert_metric_value = None if slippage_alert is None else slippage_alert.metric_value
    slippage_alert_threshold_value = (
        None if slippage_alert is None else slippage_alert.threshold_value
    )

    if existing is None:
        session.add(
            ShadowFillComparisonRow(
                intent_id=comparison.intent_id,
                symbol=comparison.symbol,
                setup_id=comparison.setup_id,
                source_mode=source_mode.value,
                source_as_of=comparison.source_as_of,
                source_regime_state=(
                    None
                    if comparison.source_regime_state is None
                    else comparison.source_regime_state.value
                ),
                session_date=comparison.session_date,
                status=comparison.status.value,
                would_fill=comparison.would_fill,
                would_remain_pending=comparison.would_remain_pending,
                would_mark_setup_spent=comparison.would_mark_setup_spent,
                official_open=comparison.official_open,
                reference_price=comparison.reference_price,
                hypothetical_fill_price=comparison.hypothetical_fill_price,
                transaction_cost=comparison.transaction_cost,
                total_cost_bps=comparison.total_cost_bps,
                slippage_alert_triggered_at=slippage_alert_triggered_at,
                slippage_alert_metric_value=slippage_alert_metric_value,
                slippage_alert_threshold_value=slippage_alert_threshold_value,
                detail=comparison.detail,
                recorded_at=recorded_at,
            )
        )
        return

    existing.symbol = comparison.symbol
    existing.setup_id = comparison.setup_id
    existing.source_mode = source_mode.value
    existing.source_as_of = comparison.source_as_of
    existing.source_regime_state = (
        None if comparison.source_regime_state is None else comparison.source_regime_state.value
    )
    existing.session_date = comparison.session_date
    existing.status = comparison.status.value
    existing.would_fill = comparison.would_fill
    existing.would_remain_pending = comparison.would_remain_pending
    existing.would_mark_setup_spent = comparison.would_mark_setup_spent
    existing.official_open = comparison.official_open
    existing.reference_price = comparison.reference_price
    existing.hypothetical_fill_price = comparison.hypothetical_fill_price
    existing.transaction_cost = comparison.transaction_cost
    existing.total_cost_bps = comparison.total_cost_bps
    existing.slippage_alert_triggered_at = slippage_alert_triggered_at
    existing.slippage_alert_metric_value = slippage_alert_metric_value
    existing.slippage_alert_threshold_value = slippage_alert_threshold_value
    existing.detail = comparison.detail
    existing.recorded_at = recorded_at


def record_shadow_fill_comparison_snapshot(
    session: Session,
    comparison: ShadowFillComparison,
    *,
    source_mode: RuntimeMode,
    recorded_at: datetime,
) -> str:
    snapshot_id = uuid4().hex
    slippage_alert = comparison.slippage_alert
    slippage_alert_triggered_at = None if slippage_alert is None else slippage_alert.triggered_at
    slippage_alert_metric_value = None if slippage_alert is None else slippage_alert.metric_value
    slippage_alert_threshold_value = (
        None if slippage_alert is None else slippage_alert.threshold_value
    )

    session.add(
        ShadowFillComparisonSnapshotRow(
            snapshot_id=snapshot_id,
            intent_id=comparison.intent_id,
            symbol=comparison.symbol,
            setup_id=comparison.setup_id,
            source_mode=source_mode.value,
            source_as_of=comparison.source_as_of,
            source_regime_state=(
                None
                if comparison.source_regime_state is None
                else comparison.source_regime_state.value
            ),
            session_date=comparison.session_date,
            status=comparison.status.value,
            would_fill=comparison.would_fill,
            would_remain_pending=comparison.would_remain_pending,
            would_mark_setup_spent=comparison.would_mark_setup_spent,
            official_open=comparison.official_open,
            reference_price=comparison.reference_price,
            hypothetical_fill_price=comparison.hypothetical_fill_price,
            transaction_cost=comparison.transaction_cost,
            total_cost_bps=comparison.total_cost_bps,
            slippage_alert_triggered_at=slippage_alert_triggered_at,
            slippage_alert_metric_value=slippage_alert_metric_value,
            slippage_alert_threshold_value=slippage_alert_threshold_value,
            detail=comparison.detail,
            recorded_at=recorded_at,
        )
    )
    return snapshot_id


def load_shadow_fill_comparisons(
    session: Session,
    *,
    symbol: str | None = None,
    regime_state: RegimeState | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    statuses: tuple[ShadowFillStatus, ...] = (),
) -> tuple[ShadowFillComparison, ...]:
    query = select(ShadowFillComparisonRow)
    if symbol is not None:
        query = query.where(ShadowFillComparisonRow.symbol == symbol)
    if regime_state is not None:
        query = query.where(ShadowFillComparisonRow.source_regime_state == regime_state.value)
    if date_from is not None:
        query = query.where(ShadowFillComparisonRow.session_date >= date_from)
    if date_to is not None:
        query = query.where(ShadowFillComparisonRow.session_date <= date_to)
    if statuses:
        query = query.where(
            ShadowFillComparisonRow.status.in_([status.value for status in statuses])
        )

    rows = session.scalars(
        query.order_by(
            ShadowFillComparisonRow.source_as_of,
            ShadowFillComparisonRow.session_date,
            ShadowFillComparisonRow.intent_id,
        )
    ).all()
    return tuple(shadow_fill_comparison_from_row(row) for row in rows)


def load_shadow_fill_comparison_snapshots(
    session: Session,
    *,
    symbol: str | None = None,
    regime_state: RegimeState | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    statuses: tuple[ShadowFillStatus, ...] = (),
) -> tuple[ShadowFillComparison, ...]:
    query = select(ShadowFillComparisonSnapshotRow)
    if symbol is not None:
        query = query.where(ShadowFillComparisonSnapshotRow.symbol == symbol)
    if regime_state is not None:
        query = query.where(
            ShadowFillComparisonSnapshotRow.source_regime_state == regime_state.value
        )
    if date_from is not None:
        query = query.where(ShadowFillComparisonSnapshotRow.session_date >= date_from)
    if date_to is not None:
        query = query.where(ShadowFillComparisonSnapshotRow.session_date <= date_to)
    if statuses:
        query = query.where(
            ShadowFillComparisonSnapshotRow.status.in_([status.value for status in statuses])
        )

    rows = session.scalars(
        query.order_by(
            ShadowFillComparisonSnapshotRow.recorded_at,
            ShadowFillComparisonSnapshotRow.source_as_of,
            ShadowFillComparisonSnapshotRow.session_date,
            ShadowFillComparisonSnapshotRow.intent_id,
            ShadowFillComparisonSnapshotRow.snapshot_id,
        )
    ).all()
    return tuple(shadow_fill_comparison_from_row(row) for row in rows)


def record_paper_shadow_audit_snapshot(
    session: Session,
    record: PaperShadowAuditRecord,
    *,
    snapshot_batch_id: str,
    recorded_at: datetime,
) -> str:
    snapshot_id = uuid4().hex
    session.add(
        PaperShadowAuditSnapshotRow(
            snapshot_id=snapshot_id,
            snapshot_batch_id=snapshot_batch_id,
            intent_id=record.intent_id,
            symbol=record.symbol,
            setup_id=record.setup_id,
            created_at=record.created_at,
            source_as_of=record.source_as_of,
            source_regime_state=(
                None if record.source_regime_state is None else record.source_regime_state.value
            ),
            alignment_status=record.alignment_status.value,
            paper_intent_present=record.paper_intent_present,
            paper_intent_status=(
                None if record.paper_intent_status is None else record.paper_intent_status.value
            ),
            broker_order_id=record.broker_order_id,
            paper_broker_status=(
                None if record.paper_broker_status is None else record.paper_broker_status.value
            ),
            paper_filled=record.paper_filled,
            shadow_present=record.shadow_present,
            shadow_status=None if record.shadow_status is None else record.shadow_status.value,
            shadow_would_fill=record.shadow_would_fill,
            shadow_session_date=record.shadow_session_date,
            shadow_hypothetical_fill_price=record.shadow_hypothetical_fill_price,
            shadow_total_cost_bps=record.shadow_total_cost_bps,
            shadow_slippage_alert_triggered=record.shadow_slippage_alert_triggered,
            recorded_at=recorded_at,
        )
    )
    return snapshot_id


def load_paper_shadow_audit_snapshots(
    session: Session,
    *,
    snapshot_batch_id: str | None = None,
    symbol: str | None = None,
    regime_state: RegimeState | None = None,
    recorded_from: date | None = None,
    recorded_to: date | None = None,
) -> tuple[PaperShadowAuditRecord, ...]:
    query = select(PaperShadowAuditSnapshotRow)
    if snapshot_batch_id is not None:
        query = query.where(PaperShadowAuditSnapshotRow.snapshot_batch_id == snapshot_batch_id)
    if symbol is not None:
        query = query.where(PaperShadowAuditSnapshotRow.symbol == symbol)
    if regime_state is not None:
        query = query.where(PaperShadowAuditSnapshotRow.source_regime_state == regime_state.value)
    if recorded_from is not None:
        query = query.where(
            PaperShadowAuditSnapshotRow.recorded_at
            >= datetime.combine(recorded_from, datetime.min.time())
        )
    if recorded_to is not None:
        query = query.where(
            PaperShadowAuditSnapshotRow.recorded_at
            < datetime.combine(recorded_to, datetime.max.time())
        )

    rows = session.scalars(
        query.order_by(
            PaperShadowAuditSnapshotRow.recorded_at,
            PaperShadowAuditSnapshotRow.snapshot_batch_id,
            PaperShadowAuditSnapshotRow.source_as_of,
            PaperShadowAuditSnapshotRow.created_at,
            PaperShadowAuditSnapshotRow.intent_id,
            PaperShadowAuditSnapshotRow.snapshot_id,
        )
    ).all()
    return tuple(paper_shadow_audit_record_from_snapshot_row(row) for row in rows)


def nonterminal_entry_intent_rows(session: Session) -> tuple[OrderIntentRow, ...]:
    rows = session.scalars(
        select(OrderIntentRow)
        .where(OrderIntentRow.reason == OrderReason.ENTRY.value)
        .where(
            OrderIntentRow.status.in_(
                [
                    OrderIntentStatus.GENERATED.value,
                    OrderIntentStatus.ACTIVE.value,
                ]
            )
        )
        .order_by(OrderIntentRow.created_at, OrderIntentRow.intent_id)
    ).all()
    return tuple(rows)


def nonterminal_intent_rows(session: Session) -> tuple[OrderIntentRow, ...]:
    rows = session.scalars(
        select(OrderIntentRow)
        .where(
            OrderIntentRow.status.in_(
                [
                    OrderIntentStatus.GENERATED.value,
                    OrderIntentStatus.ACTIVE.value,
                ]
            )
        )
        .order_by(OrderIntentRow.created_at, OrderIntentRow.intent_id)
    ).all()
    return tuple(rows)


def open_broker_order_rows(session: Session) -> tuple[BrokerOrderRow, ...]:
    rows = session.scalars(
        select(BrokerOrderRow)
        .where(BrokerOrderRow.status == BrokerOrderStatus.OPEN.value)
        .order_by(BrokerOrderRow.created_at, BrokerOrderRow.broker_order_id)
    ).all()
    return tuple(rows)
