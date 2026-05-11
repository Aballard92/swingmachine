from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

import pandas as pd

from swingmachine.config import StrategyRuntimeConfig
from swingmachine.contracts import (
    BacktestEquityPoint,
    BacktestEvent,
    BacktestResult,
    BacktestTrade,
    HistoricalPortfolioLifecyclePendingOrderSnapshot,
    HistoricalPortfolioLifecyclePositionSnapshot,
    ManagedPosition,
    OrderIntent,
    ProtectedPosition,
    SetupSnapshot,
)
from swingmachine.entries import build_setup_snapshot, plan_entry
from swingmachine.enums import OrderIntentStatus, OrderReason, RegimeState, SymbolLifecycleState
from swingmachine.execution_model import (
    apply_execution_cost,
    simulate_entry_fill,
    simulate_stop_fill,
)
from swingmachine.exits import evaluate_exit_position
from swingmachine.lifecycle import classify_symbol_state, evaluate_pending_entry

REQUIRED_BACKTEST_PANEL_COLUMNS = (
    "symbol",
    "session_date",
    "raw_open",
    "raw_high",
    "raw_low",
    "raw_close",
    "raw_volume",
    "atr_14",
    "setup_valid",
    "pattern_type",
    "setup_id",
    "setup_start_date",
    "setup_end_date",
    "setup_high",
    "setup_low",
    "setup_high_date",
    "setup_low_date",
    "is_candidate",
    "entry_enabled",
    "split_adj_close",
    "ma50",
    "ma200",
    "ma200_slope_pct20",
    "dist_to_52w_high",
)


@dataclass(slots=True)
class _PendingEntryState:
    setup: SetupSnapshot
    intent: OrderIntent
    quantity: int
    atr_14_at_signal: float
    entry_regime_state: RegimeState
    submitted_session_index: int
    sector: str | None


@dataclass(slots=True)
class _ActivePositionState:
    symbol: str
    setup_id: str
    quantity: int
    entry_signal_date: pd.Timestamp
    entry_fill_date: pd.Timestamp
    entry_reference_price: float
    entry_fill_price: float
    atr_at_entry: float
    initial_stop: float
    current_stop: float
    highest_high_since_entry: float
    bars_since_entry: int
    entry_regime_state: RegimeState
    entry_transaction_cost: float
    sector: str | None
    order_intent_id: str | None


@dataclass(slots=True)
class _ExitPendingState:
    reason: OrderReason
    submitted_session_date: pd.Timestamp


def _validate_columns(frame: pd.DataFrame, required: tuple[str, ...]) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Missing required columns: {missing_str}")


def _prepare_panel(
    panel: pd.DataFrame,
    regime_frame: pd.DataFrame,
) -> pd.DataFrame:
    _validate_columns(panel, REQUIRED_BACKTEST_PANEL_COLUMNS)
    _validate_columns(
        regime_frame,
        (
            "session_date",
            "regime_state",
            "entry_enabled",
        ),
    )

    ordered = panel.copy()
    ordered["session_date"] = pd.to_datetime(ordered["session_date"])
    ordered = ordered.sort_values(["session_date", "symbol"]).reset_index(drop=True)

    regime = regime_frame.copy()
    regime["session_date"] = pd.to_datetime(regime["session_date"])
    regime = regime.sort_values("session_date").reset_index(drop=True)

    overlapping = [
        column for column in ("regime_state", "entry_enabled") if column in ordered.columns
    ]
    if overlapping:
        ordered = ordered.drop(columns=overlapping)

    merged = ordered.merge(regime, on="session_date", how="left", validate="many_to_one")
    if merged["regime_state"].isna().any():
        raise ValueError("Every backtest session must have regime context")
    return merged


def _shared_setup_preconditions_pass(
    row: pd.Series,
    config: StrategyRuntimeConfig,
) -> bool:
    earnings_distance = row.get("regular_closes_until_earnings_event")
    earnings_ok = pd.isna(earnings_distance) or float(earnings_distance) > float(
        config.events.min_regular_closes_before_earnings_for_new_entry
    )
    return (
        bool(row.get("is_candidate", False))
        and bool(row.get("entry_enabled", False))
        and float(row["split_adj_close"]) > float(row["ma50"])
        and float(row["ma50"]) > float(row["ma200"])
        and float(row["ma200_slope_pct20"]) > 0.0
        and float(row["dist_to_52w_high"])
        <= float(config.setup.shared_requirements.max_distance_from_52w_high)
        and earnings_ok
    )


def _hard_eligible(row: pd.Series) -> bool:
    if "universe_eligible" in row.index:
        return bool(row["universe_eligible"])
    if "rankable" in row.index:
        return bool(row["rankable"])
    return bool(row.get("is_candidate", False))


def _current_equity(
    *,
    cash: float,
    active_positions: dict[str, _ActivePositionState],
    row_by_symbol: dict[str, pd.Series],
) -> float:
    equity = cash
    for symbol, position in active_positions.items():
        row = row_by_symbol.get(symbol)
        if row is None:
            equity += position.quantity * position.entry_fill_price
        else:
            equity += position.quantity * float(row["raw_close"])
    return equity


def _protected_positions(
    active_positions: dict[str, _ActivePositionState],
) -> tuple[ProtectedPosition, ...]:
    return tuple(
        ProtectedPosition(
            symbol=position.symbol,
            quantity=position.quantity,
            entry_reference_price=position.entry_fill_price,
            protective_stop=position.current_stop,
            sector=position.sector,
        )
        for position in active_positions.values()
    )


def _event(
    *,
    session_date: pd.Timestamp,
    symbol: str,
    event_type: str,
    setup_id: str | None = None,
    state: SymbolLifecycleState | None = None,
    order_reason: OrderReason | None = None,
    detail: str | None = None,
) -> BacktestEvent:
    return BacktestEvent(
        session_date=session_date.date(),
        symbol=symbol,
        event_type=event_type,
        setup_id=setup_id,
        state=state,
        order_reason=order_reason,
        detail=detail,
    )


def _closed_trade(
    *,
    position: _ActivePositionState,
    exit_fill_date: pd.Timestamp,
    exit_reference_price: float,
    exit_fill_price: float,
    exit_transaction_cost: float,
    exit_regime_state: RegimeState,
    exit_reason: OrderReason,
) -> BacktestTrade:
    gross_pnl = (exit_reference_price - position.entry_reference_price) * position.quantity
    gross_return = exit_reference_price / position.entry_reference_price - 1.0
    total_transaction_cost = position.entry_transaction_cost + exit_transaction_cost
    net_pnl = gross_pnl - total_transaction_cost
    net_return = (
        exit_fill_price / position.entry_fill_price - 1.0
        if position.entry_fill_price > 0.0
        else gross_return
    )
    return BacktestTrade(
        symbol=position.symbol,
        setup_id=position.setup_id,
        entry_signal_date=position.entry_signal_date.date(),
        entry_fill_date=position.entry_fill_date.date(),
        entry_reference_price=position.entry_reference_price,
        entry_fill_price=position.entry_fill_price,
        exit_fill_date=exit_fill_date.date(),
        exit_reference_price=exit_reference_price,
        exit_fill_price=exit_fill_price,
        quantity=position.quantity,
        entry_regime_state=position.entry_regime_state,
        exit_regime_state=exit_regime_state,
        exit_reason=exit_reason,
        bars_held=position.bars_since_entry,
        initial_stop=position.initial_stop,
        final_stop=position.current_stop,
        entry_transaction_cost=position.entry_transaction_cost,
        exit_transaction_cost=exit_transaction_cost,
        total_transaction_cost=total_transaction_cost,
        gross_pnl=gross_pnl,
        gross_return=gross_return,
        net_pnl=net_pnl,
        net_return=net_return,
        sector=position.sector,
    )


def _pending_order_snapshot(
    *,
    pending: _PendingEntryState,
    session_date: pd.Timestamp,
    status: OrderIntentStatus,
    cancel_reason: str | None = None,
) -> HistoricalPortfolioLifecyclePendingOrderSnapshot:
    return HistoricalPortfolioLifecyclePendingOrderSnapshot(
        order_intent_id=pending.intent.intent_id,
        symbol=pending.intent.symbol,
        session_date=session_date.date(),
        status=status,
        side=pending.intent.side,
        order_type=pending.intent.order_type,
        quantity=pending.quantity,
        stop_price=pending.intent.stop_price,
        limit_price=pending.intent.limit_price,
        setup_id=pending.setup.setup_id,
        created_at=pending.intent.created_at,
        expires_at=pending.intent.expires_at,
        cancel_reason=cancel_reason,
        evidence={
            "source": "backtest",
            "submitted_session_index": pending.submitted_session_index,
        },
    )


def _active_position_snapshot(
    *,
    position: _ActivePositionState,
    session_date: pd.Timestamp,
    row_by_symbol: dict[str, pd.Series],
    state: SymbolLifecycleState,
) -> HistoricalPortfolioLifecyclePositionSnapshot:
    row = row_by_symbol.get(position.symbol)
    market_price = (
        position.entry_fill_price if row is None else float(row["raw_close"])
    )
    unrealized_pnl = (market_price - position.entry_fill_price) * position.quantity
    unrealized_pnl_pct = (
        market_price / position.entry_fill_price - 1.0
        if position.entry_fill_price > 0.0
        else 0.0
    )
    return HistoricalPortfolioLifecyclePositionSnapshot(
        position_id=(
            f"{position.symbol}:{position.setup_id}:"
            f"{position.entry_fill_date.date().isoformat()}"
        ),
        symbol=position.symbol,
        session_date=session_date.date(),
        state=state,
        quantity=position.quantity,
        entry_price=position.entry_fill_price,
        market_price=market_price,
        initial_stop=position.initial_stop,
        current_stop=position.current_stop,
        highest_high_since_entry=position.highest_high_since_entry,
        unrealized_pnl=unrealized_pnl,
        unrealized_pnl_pct=unrealized_pnl_pct,
        risk_amount=max(
            (position.entry_fill_price - position.current_stop) * position.quantity,
            0.0,
        ),
        sector=position.sector,
        setup_id=position.setup_id,
        order_intent_id=position.order_intent_id,
        opened_session=position.entry_fill_date.date(),
    )
def run_backtest(
    panel: pd.DataFrame,
    regime_frame: pd.DataFrame,
    config: StrategyRuntimeConfig,
    *,
    initial_equity: float = 100_000.0,
) -> BacktestResult:
    if initial_equity <= 0.0:
        raise ValueError("initial_equity must be strictly positive")

    prepared = _prepare_panel(panel, regime_frame)
    session_dates = list(pd.Index(prepared["session_date"].drop_duplicates()).sort_values())

    cash = float(initial_equity)
    spent_setup_ids: set[str] = set()
    pending_entries: dict[str, _PendingEntryState] = {}
    active_positions: dict[str, _ActivePositionState] = {}
    exit_pending: dict[str, _ExitPendingState] = {}
    trades: list[BacktestTrade] = []
    events: list[BacktestEvent] = []
    equity_curve: list[BacktestEquityPoint] = []
    pending_order_snapshots: list[HistoricalPortfolioLifecyclePendingOrderSnapshot] = []
    position_snapshots: list[HistoricalPortfolioLifecyclePositionSnapshot] = []

    for session_index, session_date in enumerate(session_dates):
        session_rows = prepared.loc[prepared["session_date"] == session_date].copy()
        sort_columns = ["symbol"]
        ascending = [True]
        if "candidate_score_pct" in session_rows.columns:
            sort_columns = ["candidate_score_pct", "symbol"]
            ascending = [False, True]
        session_rows = session_rows.sort_values(
            by=sort_columns,
            ascending=ascending,
            na_position="last",
        )
        row_by_symbol = {str(row["symbol"]): row for _, row in session_rows.iterrows()}
        filled_today: set[str] = set()

        for symbol, pending_exit in list(exit_pending.items()):
            row = row_by_symbol.get(symbol)
            if row is None:
                continue

            position = active_positions.pop(symbol)
            exit_fill = apply_execution_cost(
                reference_price=float(row["raw_open"]),
                row=row,
                quantity=position.quantity,
                side="sell",
                config=config,
            )
            cash += position.quantity * exit_fill.execution_price
            exit_regime_state = RegimeState(str(row["regime_state"]))
            trades.append(
                _closed_trade(
                    position=position,
                    exit_fill_date=session_date,
                    exit_reference_price=exit_fill.reference_price,
                    exit_fill_price=exit_fill.execution_price,
                    exit_transaction_cost=exit_fill.transaction_cost,
                    exit_regime_state=exit_regime_state,
                    exit_reason=pending_exit.reason,
                )
            )
            events.append(
                _event(
                    session_date=session_date,
                    symbol=symbol,
                    event_type="EXIT_FILLED",
                    setup_id=position.setup_id,
                    state=SymbolLifecycleState.CLOSED,
                    order_reason=pending_exit.reason,
                )
            )
            del exit_pending[symbol]

        for symbol, pending in list(pending_entries.items()):
            row = row_by_symbol.get(symbol)
            if row is None:
                continue

            earnings_distance = row.get("regular_closes_until_earnings_event")
            earnings_window_breached = (
                pd.notna(earnings_distance)
                and float(earnings_distance)
                <= config.events.min_regular_closes_before_earnings_for_new_entry
            )
            shared_preconditions_pass = _shared_setup_preconditions_pass(row, config)
            hard_eligible_after_cancel = _hard_eligible(row)
            candidate_eligible_after_cancel = bool(row.get("is_candidate", False))

            raw_open = float(row["raw_open"])
            if config.entry.cancel_unfilled_order_if_open_above_limit and raw_open > float(
                pending.intent.limit_price
            ):
                evaluation = evaluate_pending_entry(
                    pending.intent,
                    config=config,
                    official_open_next=raw_open,
                    regular_sessions_elapsed=session_index - pending.submitted_session_index,
                    regime_state=RegimeState(str(row["regime_state"])),
                    earnings_window_breached=earnings_window_breached,
                    shared_setup_preconditions_pass=shared_preconditions_pass,
                    hard_eligible_after_cancel=hard_eligible_after_cancel,
                    candidate_eligible_after_cancel=candidate_eligible_after_cancel,
                )
                if evaluation.mark_setup_spent and pending.setup.setup_id is not None:
                    spent_setup_ids.add(pending.setup.setup_id)
                events.append(
                    _event(
                        session_date=session_date,
                        symbol=symbol,
                        event_type="ENTRY_CANCELLED",
                        setup_id=pending.setup.setup_id,
                        state=evaluation.next_state,
                        detail="|".join(reason.value for reason in evaluation.cancel_reasons),
                    )
                )
                pending_order_snapshots.append(
                    _pending_order_snapshot(
                        pending=pending,
                        session_date=session_date,
                        status=OrderIntentStatus.CANCELLED,
                        cancel_reason="|".join(
                            reason.value for reason in evaluation.cancel_reasons
                        ),
                    )
                )
                del pending_entries[symbol]
                continue

            fill_price = simulate_entry_fill(row, pending.intent)
            if fill_price is not None:
                entry_fill = apply_execution_cost(
                    reference_price=fill_price,
                    row=row,
                    quantity=pending.quantity,
                    side="buy",
                    config=config,
                )
                cash -= pending.quantity * entry_fill.execution_price
                active_positions[symbol] = _ActivePositionState(
                    symbol=symbol,
                    setup_id=pending.setup.setup_id,
                    quantity=pending.quantity,
                    entry_signal_date=pd.Timestamp(pending.setup.session_date),
                    entry_fill_date=session_date,
                    entry_reference_price=entry_fill.reference_price,
                    entry_fill_price=entry_fill.execution_price,
                    atr_at_entry=pending.atr_14_at_signal,
                    initial_stop=pending.setup.initial_stop,
                    current_stop=pending.setup.initial_stop,
                    highest_high_since_entry=max(
                        entry_fill.reference_price,
                        float(row["raw_high"]),
                    ),
                    bars_since_entry=0,
                    entry_regime_state=pending.entry_regime_state,
                    entry_transaction_cost=entry_fill.transaction_cost,
                    sector=pending.sector,
                    order_intent_id=pending.intent.intent_id,
                )
                filled_today.add(symbol)
                events.append(
                    _event(
                        session_date=session_date,
                        symbol=symbol,
                        event_type="ENTRY_FILLED",
                        setup_id=pending.setup.setup_id,
                        state=SymbolLifecycleState.ACTIVE,
                        order_reason=OrderReason.ENTRY,
                    )
                )
                pending_order_snapshots.append(
                    _pending_order_snapshot(
                        pending=pending,
                        session_date=session_date,
                        status=OrderIntentStatus.FILLED,
                    )
                )
                del pending_entries[symbol]
                continue

            evaluation = evaluate_pending_entry(
                pending.intent,
                config=config,
                regular_sessions_elapsed=session_index - pending.submitted_session_index,
                regime_state=RegimeState(str(row["regime_state"])),
                earnings_window_breached=earnings_window_breached,
                shared_setup_preconditions_pass=shared_preconditions_pass,
                hard_eligible_after_cancel=hard_eligible_after_cancel,
                candidate_eligible_after_cancel=candidate_eligible_after_cancel,
            )
            if evaluation.should_cancel:
                if evaluation.mark_setup_spent and pending.setup.setup_id is not None:
                    spent_setup_ids.add(pending.setup.setup_id)
                events.append(
                    _event(
                        session_date=session_date,
                        symbol=symbol,
                        event_type="ENTRY_CANCELLED",
                        setup_id=pending.setup.setup_id,
                        state=evaluation.next_state,
                        detail="|".join(reason.value for reason in evaluation.cancel_reasons),
                    )
                )
                pending_order_snapshots.append(
                    _pending_order_snapshot(
                        pending=pending,
                        session_date=session_date,
                        status=OrderIntentStatus.CANCELLED,
                        cancel_reason="|".join(
                            reason.value for reason in evaluation.cancel_reasons
                        ),
                    )
                )
                del pending_entries[symbol]

        for symbol, position in list(active_positions.items()):
            if symbol in filled_today:
                continue

            row = row_by_symbol.get(symbol)
            if row is None:
                continue

            stop_fill_price = simulate_stop_fill(
                raw_open=float(row["raw_open"]),
                raw_low=float(row["raw_low"]),
                stop_price=position.current_stop,
            )
            if stop_fill_price is not None:
                exit_fill = apply_execution_cost(
                    reference_price=stop_fill_price,
                    row=row,
                    quantity=position.quantity,
                    side="sell",
                    config=config,
                )
                cash += position.quantity * exit_fill.execution_price
                exit_reason = (
                    OrderReason.TRAIL_STOP
                    if position.current_stop > position.initial_stop
                    else OrderReason.INITIAL_STOP
                )
                exit_regime_state = RegimeState(str(row["regime_state"]))
                trades.append(
                    _closed_trade(
                        position=position,
                        exit_fill_date=session_date,
                        exit_reference_price=exit_fill.reference_price,
                        exit_fill_price=exit_fill.execution_price,
                        exit_transaction_cost=exit_fill.transaction_cost,
                        exit_regime_state=exit_regime_state,
                        exit_reason=exit_reason,
                    )
                )
                events.append(
                    _event(
                        session_date=session_date,
                        symbol=symbol,
                        event_type="EXIT_FILLED",
                        setup_id=position.setup_id,
                        state=SymbolLifecycleState.CLOSED,
                        order_reason=exit_reason,
                    )
                )
                del active_positions[symbol]
                continue

            updated_high = max(position.highest_high_since_entry, float(row["raw_high"]))
            evaluation = evaluate_exit_position(
                ManagedPosition(
                    symbol=symbol,
                    quantity=position.quantity,
                    entry_fill_price=position.entry_fill_price,
                    atr_at_entry=position.atr_at_entry,
                    current_stop=position.current_stop,
                    highest_high_since_entry=updated_high,
                    bars_since_entry=position.bars_since_entry,
                    regular_closes_until_earnings_event=(
                        None
                        if pd.isna(row.get("regular_closes_until_earnings_event"))
                        else int(row["regular_closes_until_earnings_event"])
                    ),
                ),
                atr_14=float(row["atr_14"]),
                regime_state=RegimeState(str(row["regime_state"])),
                config=config,
            )
            position.current_stop = evaluation.updated_stop
            position.highest_high_since_entry = updated_high
            position.bars_since_entry += 1

            if evaluation.should_submit_exit_intent:
                exit_reason = evaluation.discretionary_exit_reasons[0]
                exit_pending[symbol] = _ExitPendingState(
                    reason=exit_reason,
                    submitted_session_date=session_date,
                )
                events.append(
                    _event(
                        session_date=session_date,
                        symbol=symbol,
                        event_type="EXIT_SUBMITTED",
                        setup_id=position.setup_id,
                        state=SymbolLifecycleState.EXIT_PENDING,
                        order_reason=exit_reason,
                    )
                )

        equity_before_entries = _current_equity(
            cash=cash,
            active_positions=active_positions,
            row_by_symbol=row_by_symbol,
        )
        submitted_today_risk_amount = 0.0
        open_positions = _protected_positions(active_positions)

        for _, row in session_rows.iterrows():
            symbol = str(row["symbol"])
            setup_id = row.get("setup_id")
            state = classify_symbol_state(
                hard_eligible=_hard_eligible(row),
                candidate_eligible=bool(row.get("is_candidate", False)),
                setup_valid=bool(row.get("setup_valid", False)),
                setup_id=None if pd.isna(setup_id) else str(setup_id),
                spent_setup_ids=spent_setup_ids,
                pending_entry_active=symbol in pending_entries,
                active_position=symbol in active_positions,
                exit_intent_active=symbol in exit_pending,
                config=config,
            )
            if state != SymbolLifecycleState.ARMED:
                continue

            setup = build_setup_snapshot(row, config)
            sector = (
                None if "sector" not in row.index or pd.isna(row["sector"]) else str(row["sector"])
            )
            created_at = datetime.combine(session_date.date(), time(16, 0))
            plan = plan_entry(
                setup,
                config,
                regime_state=RegimeState(str(row["regime_state"])),
                equity=equity_before_entries,
                pending_symbols=tuple(pending_entries.keys()),
                open_positions=open_positions,
                submitted_today_risk_amount=submitted_today_risk_amount,
                sector=sector,
                created_at=created_at,
                expires_at=None,
            )
            if not plan.approved or plan.order_intent is None:
                continue

            pending_entries[symbol] = _PendingEntryState(
                setup=setup,
                intent=plan.order_intent,
                quantity=plan.quantity,
                atr_14_at_signal=float(row["atr_14"]),
                entry_regime_state=RegimeState(str(row["regime_state"])),
                submitted_session_index=session_index,
                sector=sector,
            )
            submitted_today_risk_amount += setup.per_share_risk * plan.quantity
            events.append(
                _event(
                    session_date=session_date,
                    symbol=symbol,
                    event_type="ENTRY_SUBMITTED",
                    setup_id=setup.setup_id,
                    state=SymbolLifecycleState.PENDING_ENTRY,
                    order_reason=OrderReason.ENTRY,
                )
            )

        close_equity = _current_equity(
            cash=cash,
            active_positions=active_positions,
            row_by_symbol=row_by_symbol,
        )
        equity_curve.append(
            BacktestEquityPoint(
                session_date=session_date.date(),
                equity=max(close_equity, 0.0),
                cash=cash,
                open_positions=len(active_positions),
                pending_entries=len(pending_entries),
            )
        )
        for pending in pending_entries.values():
            pending_order_snapshots.append(
                _pending_order_snapshot(
                    pending=pending,
                    session_date=session_date,
                    status=OrderIntentStatus.ACTIVE,
                )
            )
        for symbol, position in active_positions.items():
            position_snapshots.append(
                _active_position_snapshot(
                    position=position,
                    session_date=session_date,
                    row_by_symbol=row_by_symbol,
                    state=(
                        SymbolLifecycleState.EXIT_PENDING
                        if symbol in exit_pending
                        else SymbolLifecycleState.ACTIVE
                    ),
                )
            )

    final_equity = equity_curve[-1].equity if equity_curve else initial_equity
    return BacktestResult(
        initial_equity=initial_equity,
        final_equity=final_equity,
        trades=tuple(trades),
        equity_curve=tuple(equity_curve),
        events=tuple(events),
        spent_setup_ids=tuple(sorted(spent_setup_ids)),
        pending_order_snapshots=tuple(pending_order_snapshots),
        position_snapshots=tuple(position_snapshots),
    )
