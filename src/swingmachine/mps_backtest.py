from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import pandas as pd

from swingmachine.mps_config import MpsConfig
from swingmachine.mps_contracts import (
    CorporateActionRecord,
    MpsBacktestResult,
    MpsCandidate,
    MpsEntryPlan,
    MpsEquityPoint,
    MpsFill,
    MpsOrderRejection,
    MpsPosition,
    MpsTrade,
    MpsVariant,
)
from swingmachine.mps_execution import apply_one_way_cost, simulate_entry, simulate_sell_stop
from swingmachine.mps_portfolio import MpsPortfolioLedger
from swingmachine.mps_risk import actual_initial_stop, plan_entry, post_fill_quantity
from swingmachine.mps_signals import exit_reason, select_candidates, updated_trailing_stop


@dataclass(slots=True)
class _EntryState:
    candidate: MpsCandidate
    plan: MpsEntryPlan
    entry_reference: float
    entry_fill: float
    entry_quantity: int
    entry_cash_cost: float
    initial_stop: float
    minimum_low: float
    accrued_dividends: float = 0.0


def _record(
    events: list[dict[str, object]], session: date, phase: str, event: str, **detail: object
) -> None:
    events.append({"session_date": session.isoformat(), "phase": phase, "event": event, **detail})


def run_mps_backtest(
    features: pd.DataFrame,
    regime: pd.DataFrame,
    config: MpsConfig,
    variant: MpsVariant,
    *,
    data_version_hash: str,
    initial_cash: float = 100_000.0,
    cost_bps: float | None = None,
    corporate_actions: Sequence[CorporateActionRecord] = (),
    common_lifecycle_policy: bool = False,
    research_ex_date_dividends: bool = False,
    force_unresolved_delisting_last_close: bool = False,
) -> MpsBacktestResult:
    """Run B0-B4 through one deterministic next-open daily event path."""
    if config.earnings.enabled:
        raise ValueError("earnings overlay requires a point-in-time calendar adapter")
    required = {
        "security_id",
        "ticker",
        "session_date",
        "open",
        "high",
        "low",
        "close",
        "momentum_rank",
        "sma50",
        "atr20",
    }
    missing = sorted(required - set(features.columns))
    if missing:
        raise ValueError(f"backtest feature panel missing columns: {', '.join(missing)}")
    if force_unresolved_delisting_last_close and "is_delisted" not in features:
        raise ValueError("forced unresolved-delisting handling requires is_delisted")
    panel = features.copy()
    panel["session_date"] = pd.to_datetime(panel["session_date"])
    panel = panel.sort_values(["session_date", "ticker", "security_id"]).reset_index(drop=True)
    regime_frame = regime.copy()
    regime_frame["session_date"] = pd.to_datetime(regime_frame["session_date"])
    regime_map = dict(
        zip(regime_frame["session_date"].dt.date, regime_frame["regime_multiplier"], strict=True)
    )
    sessions = tuple(sorted(panel["session_date"].dt.date.unique()))
    rows_by_date = {
        session: frame.set_index("security_id", drop=False)
        for session, frame in panel.groupby(panel["session_date"].dt.date, sort=True)
    }
    actions_by_date: dict[date, list[CorporateActionRecord]] = defaultdict(list)
    for action in corporate_actions:
        actions_by_date[action.effective_date].append(action)
    ledger = MpsPortfolioLedger(initial_cash)
    one_way_cost = config.execution.baseline_one_way_cost_bps if cost_bps is None else cost_bps
    pending_entries: tuple[MpsCandidate, ...] = ()
    pending_exits: dict[str, str] = {}
    entry_states: dict[str, _EntryState] = {}
    trades: list[MpsTrade] = []
    equity_curve: list[MpsEquityPoint] = []
    rejected: list[MpsOrderRejection] = []
    events: list[dict[str, object]] = []
    high_water = initial_cash

    def close_position(session: date, security_id: str, reference: float, reason: str) -> None:
        position = ledger.positions[security_id]
        state = entry_states[security_id]
        fill_price = apply_one_way_cost(reference, one_way_cost, "SELL")
        fill = MpsFill(
            security_id=security_id,
            session_date=session,
            side="SELL",
            quantity=position.quantity,
            reference_price=reference,
            fill_price=fill_price,
            cost_bps=one_way_cost,
            reason_code=reason,
        )
        ledger.book_exit(fill)
        gross_pnl = (
            reference * position.quantity
            + state.accrued_dividends
            - state.entry_reference * state.entry_quantity
        )
        net_pnl = fill_price * position.quantity + state.accrued_dividends - state.entry_cash_cost
        ledger.cash += state.accrued_dividends
        risk_amount = state.initial_stop
        initial_risk_amount = (state.entry_fill - risk_amount) * state.entry_quantity
        trades.append(
            MpsTrade(
                security_id=security_id,
                ticker=position.ticker,
                variant=variant,
                entry_session=position.entry_session,
                exit_session=session,
                entry_reference_price=state.entry_reference,
                entry_fill_price=state.entry_fill,
                exit_reference_price=reference,
                exit_fill_price=fill_price,
                entry_quantity=state.entry_quantity,
                exit_quantity=position.quantity,
                initial_stop=state.initial_stop,
                exit_reason=reason,
                holding_sessions=position.holding_sessions,
                gross_pnl=gross_pnl,
                net_pnl=net_pnl,
                realised_r=net_pnl / initial_risk_amount,
                mfe_r=(position.maximum_high_since_entry - state.entry_fill)
                / (state.entry_fill - state.initial_stop),
                mae_r=(state.minimum_low - state.entry_fill)
                / (state.entry_fill - state.initial_stop),
                sector=position.sector,
            )
        )
        del entry_states[security_id]
        _record(
            events,
            session,
            "OPEN_OR_INTRADAY",
            "EXIT_FILLED",
            security_id=security_id,
            reason=reason,
            reference_price=reference,
            fill_price=fill_price,
        )

    for session in sessions:
        day = rows_by_date[session]
        for action in sorted(
            actions_by_date.get(session, ()), key=lambda item: item.source_record_id
        ):
            if research_ex_date_dividends and action.action_type.value == "CASH_DIVIDEND":
                if action.security_id in ledger.positions:
                    assert action.cash_dividend_per_share is not None
                    position = ledger.positions[action.security_id]
                    amount = position.quantity * action.cash_dividend_per_share
                    entry_states[action.security_id].accrued_dividends += amount
                    _record(
                        events,
                        session,
                        "BEFORE_OPEN",
                        "DIVIDEND_ACCRUED_NON_SPENDABLE",
                        security_id=action.security_id,
                        amount=amount,
                    )
                continue
            held_before_action = action.security_id in ledger.positions
            ledger.apply_corporate_action(action)
            if held_before_action and action.action_type.value == "SPLIT":
                assert action.split_ratio is not None
                state = entry_states[action.security_id]
                ratio = float(action.split_ratio)
                state.entry_reference /= ratio
                state.entry_fill /= ratio
                state.entry_quantity = int(round(state.entry_quantity * ratio))
                state.initial_stop /= ratio
                state.minimum_low /= ratio
            _record(
                events,
                session,
                "BEFORE_OPEN",
                "CORPORATE_ACTION_APPLIED",
                security_id=action.security_id,
                action_type=action.action_type.value,
            )
        ledger.settle_dividends(session)

        for security_id, reason in sorted(pending_exits.items()):
            if security_id in ledger.positions and security_id in day.index:
                close_position(session, security_id, float(day.loc[security_id, "open"]), reason)
        pending_exits = {}

        for security_id, position in sorted(tuple(ledger.positions.items())):
            if security_id not in day.index:
                continue
            row = day.loc[security_id]
            stop = simulate_sell_stop(
                float(row["open"]),
                float(row["low"]),
                position.active_stop,
                config,
                cost_bps=one_way_cost,
            )
            if stop.filled and stop.reason_code == "STOP_GAP":
                assert stop.reference_price is not None
                close_position(session, security_id, stop.reference_price, stop.reason_code)

        open_prices = {
            security_id: float(row["open"])
            for security_id, row in day.iterrows()
            if security_id in ledger.positions
        }
        current_equity = ledger.equity(open_prices)
        high_water = max(high_water, current_equity)
        drawdown = current_equity / high_water - 1.0
        entries_allowed = drawdown > -config.drawdown_controls.stop_new_entries_drawdown
        drawdown_multiplier = (
            0.5 if drawdown <= -config.drawdown_controls.half_risk_drawdown else 1.0
        )
        regime_multiplier = 1.0
        if variant is MpsVariant.B4_FULL_MPS1:
            value = regime_map.get(session)
            entries_allowed = entries_allowed and value is not None and pd.notna(value)
            regime_multiplier = float(value) if value is not None and pd.notna(value) else 0.0
        regime_multiplier *= drawdown_multiplier

        if entries_allowed:
            for candidate in pending_entries:
                if candidate.security_id not in day.index:
                    rejected.append(
                        MpsOrderRejection(
                            security_id=candidate.security_id,
                            reason_code="MISSING_NEXT_SESSION_BAR",
                            detail=session.isoformat(),
                        )
                    )
                    continue
                row = day.loc[candidate.security_id]
                execution = simulate_entry(
                    candidate, float(row["open"]), config, cost_bps=one_way_cost
                )
                if not execution.filled:
                    rejected.append(
                        MpsOrderRejection(
                            security_id=candidate.security_id,
                            reason_code=execution.reason_code,
                            detail=session.isoformat(),
                        )
                    )
                    continue
                current_prices = {
                    security_id: float(day.loc[security_id, "open"])
                    for security_id in ledger.positions
                    if security_id in day.index
                }
                equity = ledger.equity(current_prices)
                plan = plan_entry(
                    candidate,
                    config,
                    equity=equity,
                    cash=ledger.cash,
                    regime_multiplier=regime_multiplier,
                    positions=tuple(ledger.positions.values()),
                    current_prices=current_prices,
                )
                if not plan.approved:
                    rejected.append(
                        MpsOrderRejection(
                            security_id=candidate.security_id,
                            reason_code=plan.reason_code,
                            detail=session.isoformat(),
                        )
                    )
                    continue
                assert execution.reference_price is not None and execution.fill_price is not None
                stop = actual_initial_stop(candidate, execution.fill_price, config)
                distance = execution.fill_price - stop
                if (
                    distance <= 0
                    or distance
                    > config.initial_stop.maximum_risk_distance_atr * float(candidate.signal_atr20)
                    or distance / execution.fill_price
                    > config.initial_stop.maximum_risk_distance_fraction
                ):
                    rejected.append(
                        MpsOrderRejection(
                            security_id=candidate.security_id,
                            reason_code="INITIAL_STOP_DISTANCE",
                            detail=session.isoformat(),
                        )
                    )
                    continue
                retained, trim = post_fill_quantity(plan, execution.fill_price, config)
                if retained < 1:
                    rejected.append(
                        MpsOrderRejection(
                            security_id=candidate.security_id,
                            reason_code="POST_FILL_RISK",
                            detail=session.isoformat(),
                        )
                    )
                    continue
                if trim:
                    _record(
                        events,
                        session,
                        "OPEN",
                        "POST_FILL_TRIM_REQUIRED",
                        security_id=candidate.security_id,
                        trim_quantity=trim,
                    )
                fill = MpsFill(
                    security_id=candidate.security_id,
                    session_date=session,
                    side="BUY",
                    quantity=retained,
                    reference_price=execution.reference_price,
                    fill_price=execution.fill_price,
                    cost_bps=one_way_cost,
                    reason_code="ENTRY",
                )
                position = MpsPosition(
                    security_id=candidate.security_id,
                    ticker=candidate.ticker,
                    quantity=retained,
                    entry_price=execution.fill_price,
                    initial_stop=stop,
                    active_stop=stop,
                    initial_risk_per_share=distance,
                    sector=candidate.sector,
                    entry_session=session,
                    highest_close_since_entry=execution.fill_price,
                    maximum_high_since_entry=max(execution.fill_price, float(row["high"])),
                )
                ledger.book_entry(fill, position)
                entry_states[candidate.security_id] = _EntryState(
                    candidate=candidate,
                    plan=plan,
                    entry_reference=execution.reference_price,
                    entry_fill=execution.fill_price,
                    entry_quantity=retained,
                    entry_cash_cost=execution.fill_price * retained,
                    initial_stop=stop,
                    minimum_low=float(row["low"]),
                )
                _record(
                    events,
                    session,
                    "OPEN",
                    "ENTRY_FILLED",
                    security_id=candidate.security_id,
                    quantity=retained,
                    reference_price=execution.reference_price,
                    fill_price=execution.fill_price,
                )
        else:
            for candidate in pending_entries:
                rejected.append(
                    MpsOrderRejection(
                        security_id=candidate.security_id,
                        reason_code="DRAWDOWN_OR_REGIME_BLOCK",
                        detail=session.isoformat(),
                    )
                )
        pending_entries = ()

        for security_id, position in sorted(tuple(ledger.positions.items())):
            if security_id not in day.index or position.entry_session != session:
                continue
            row = day.loc[security_id]
            stop = simulate_sell_stop(
                float(row["open"]),
                float(row["low"]),
                position.active_stop,
                config,
                cost_bps=one_way_cost,
            )
            if stop.filled:
                assert stop.reference_price is not None
                close_position(session, security_id, stop.reference_price, stop.reason_code)

        for security_id, position in sorted(tuple(ledger.positions.items())):
            if security_id not in day.index:
                continue
            row = day.loc[security_id]
            state = entry_states[security_id]
            state.minimum_low = min(state.minimum_low, float(row["low"]))
            updated = position.model_copy(
                update={
                    "holding_sessions": position.holding_sessions + 1,
                    "highest_close_since_entry": max(
                        position.highest_close_since_entry, float(row["close"])
                    ),
                    "maximum_high_since_entry": max(
                        position.maximum_high_since_entry, float(row["high"])
                    ),
                }
            )
            if variant is MpsVariant.B4_FULL_MPS1 or common_lifecycle_policy:
                updated = updated.model_copy(
                    update={
                        "active_stop": updated_trailing_stop(
                            updated, float(row["close"]), float(row["atr20"]), config
                        )
                    }
                )
            ledger.positions[security_id] = updated
            if force_unresolved_delisting_last_close and bool(row["is_delisted"]):
                pending_exits.pop(security_id, None)
                close_position(
                    session,
                    security_id,
                    float(row["close"]),
                    "UNRESOLVED_DELISTING_LAST_CLOSE",
                )
                continue
            if not common_lifecycle_policy and variant in (
                MpsVariant.B0_RANK_ONLY,
                MpsVariant.B1_MOMENTUM_TREND,
            ):
                reason = (
                    "MOMENTUM_DETERIORATION"
                    if float(row["momentum_rank"]) < config.exits.momentum_hold_percentile
                    else None
                )
            else:
                reason = exit_reason(updated, row, config)
            if reason is not None:
                pending_exits[security_id] = reason

        closing_prices = {
            security_id: float(day.loc[security_id, "close"])
            for security_id in ledger.positions
            if security_id in day.index
        }
        closing_equity = ledger.equity(closing_prices)
        high_water = max(high_water, closing_equity)
        gross = sum(
            ledger.positions[security_id].quantity * price
            for security_id, price in closing_prices.items()
        )
        equity_curve.append(
            MpsEquityPoint(
                session_date=session,
                equity=closing_equity,
                cash=ledger.cash,
                gross_exposure=gross,
                position_count=len(ledger.positions),
            )
        )
        pending_entries = select_candidates(
            day.reset_index(drop=True),
            variant,
            config,
            held_security_ids=frozenset(ledger.positions),
        )
        _record(
            events,
            session,
            "CLOSE",
            "DECISION_AUDIT",
            candidate_count=len(pending_entries),
            pending_exit_count=len(pending_exits),
            equity=closing_equity,
        )

    return MpsBacktestResult(
        variant=variant,
        config_hash=config.config_hash(),
        data_version_hash=data_version_hash,
        cost_bps=one_way_cost,
        trades=tuple(trades),
        equity_curve=tuple(equity_curve),
        audit_events=tuple(events),
        rejected_orders=tuple(rejected),
    )
