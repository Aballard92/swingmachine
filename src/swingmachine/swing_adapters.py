from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

import pandas as pd

from swingmachine.config import StrategyRuntimeConfig
from swingmachine.contracts import EntryPlan, SetupSnapshot
from swingmachine.enums import OrderReason, RegimeState, SymbolLifecycleState
from swingmachine.swing_contracts import (
    SwingCandidate,
    SwingEligibilityGate,
    SwingExitDecision,
    SwingLifecycleTransition,
    SwingOrderPlan,
    SwingPortfolioConstraintResult,
    SwingQualityScore,
    SwingRankingResult,
    SwingRejectionCategory,
    SwingRejectionReason,
    SwingRiskPlan,
    SwingSignal,
    build_quality_score,
)

REQUIRED_SCORED_CANDIDATE_COLUMNS: tuple[str, ...] = (
    "symbol",
    "session_date",
    "regime_state",
    "universe_eligible",
    "entry_enabled",
    "split_adj_close",
    "ma50",
    "ma200",
    "ma200_slope_pct20",
    "dist_to_52w_high",
    "trend_quality",
    "candidate_score_raw",
    "candidate_score_pct",
    "effective_candidate_score_threshold_pct",
    "effective_min_trend_quality",
    "is_candidate",
)


def swing_candidates_from_scored_frame(
    scored_frame: pd.DataFrame,
    config: StrategyRuntimeConfig,
    *,
    feature_snapshot_ref_column: str | None = None,
) -> tuple[SwingCandidate, ...]:
    _validate_columns(scored_frame, REQUIRED_SCORED_CANDIDATE_COLUMNS)
    scored = scored_frame.copy()
    scored["session_date"] = pd.to_datetime(scored["session_date"])

    rank_by_index = _candidate_ranks(scored)
    candidates: list[SwingCandidate] = []
    for row_index, row in scored.iterrows():
        candidates.append(
            _candidate_from_row(
                row,
                config,
                rank=rank_by_index.get(row_index),
                feature_snapshot_ref_column=feature_snapshot_ref_column,
            )
        )
    return tuple(candidates)


def swing_signal_from_setup_snapshot(
    setup: SetupSnapshot,
    config: StrategyRuntimeConfig,
    *,
    candidate_id: str,
    quality_score: SwingQualityScore,
    regime_state: RegimeState,
    approved: bool = True,
    rejection_reasons: tuple[SwingRejectionReason, ...] = (),
) -> SwingSignal:
    gates = (
        _gate(
            "setup.valid",
            SwingRejectionCategory.SETUP,
            approved,
            "SETUP_NOT_APPROVED",
            "Setup was not approved as a baseline signal",
            {"setup_id": setup.setup_id, "pattern_type": setup.pattern_type.value},
        ),
    )
    gate_rejection_reasons = tuple(gate.reason for gate in gates if gate.reason is not None)
    return SwingSignal(
        signal_id=_signal_id(config.strategy.id, setup.symbol, setup.session_date, setup.setup_id),
        candidate_id=candidate_id,
        strategy_id=config.strategy.id,
        config_hash=config.config_hash(),
        symbol=setup.symbol,
        session_date=setup.session_date,
        regime_state=regime_state,
        approved=approved,
        pattern_type=setup.pattern_type if approved else None,
        setup_id=setup.setup_id if approved else None,
        entry_trigger=setup.entry_trigger if approved else None,
        entry_limit=setup.entry_limit if approved else None,
        initial_stop=setup.initial_stop if approved else None,
        per_share_risk=setup.per_share_risk if approved else None,
        quality_score=quality_score if approved else None,
        eligibility_gates=gates,
        rejection_reasons=(*rejection_reasons, *gate_rejection_reasons),
    )


def swing_risk_plan_from_entry_plan(
    entry_plan: EntryPlan,
    config: StrategyRuntimeConfig,
    *,
    signal_id: str,
) -> SwingRiskPlan:
    rejection_reasons = _rejection_reasons_from_texts(entry_plan.reject_reasons)
    constraints = _portfolio_constraints_from_entry_plan(entry_plan, config)
    setup = entry_plan.setup
    return SwingRiskPlan(
        risk_plan_id=_risk_plan_id(
            config.strategy.id,
            setup.symbol,
            setup.session_date,
            setup.setup_id,
        ),
        signal_id=signal_id,
        strategy_id=config.strategy.id,
        config_hash=config.config_hash(),
        symbol=setup.symbol,
        session_date=setup.session_date,
        approved=entry_plan.approved,
        entry_trigger=setup.entry_trigger,
        initial_stop=setup.initial_stop,
        per_share_risk=setup.per_share_risk,
        equity=_equity_from_risk_budget(entry_plan, config),
        base_risk_budget=entry_plan.base_risk_budget,
        regime_risk_budget=entry_plan.regime_risk_budget,
        effective_risk_budget=entry_plan.effective_risk_budget,
        shares_from_risk=entry_plan.shares_from_risk,
        shares_from_notional=entry_plan.shares_from_notional,
        quantity=entry_plan.quantity,
        projected_portfolio_heat=entry_plan.projected_portfolio_heat,
        projected_daily_new_risk=entry_plan.projected_daily_new_risk,
        constraints=constraints,
        rejection_reasons=rejection_reasons,
    )


def swing_order_plan_from_entry_plan(
    entry_plan: EntryPlan,
    config: StrategyRuntimeConfig,
    *,
    signal_id: str,
    risk_plan_id: str,
) -> SwingOrderPlan:
    setup = entry_plan.setup
    order_intent = entry_plan.order_intent
    approved = entry_plan.approved and order_intent is not None
    rejection_reasons = _rejection_reasons_from_texts(entry_plan.reject_reasons)
    if entry_plan.approved and order_intent is None:
        rejection_reasons = (
            *rejection_reasons,
            SwingRejectionReason(
                code="ORDER_INTENT_MISSING",
                category=SwingRejectionCategory.RUNTIME,
                message="Approved entry plan did not include an order intent",
            ),
        )
    return SwingOrderPlan(
        order_plan_id=_order_plan_id(
            config.strategy.id,
            setup.symbol,
            setup.session_date,
            setup.setup_id,
        ),
        risk_plan_id=risk_plan_id,
        signal_id=signal_id,
        strategy_id=config.strategy.id,
        config_hash=config.config_hash(),
        symbol=setup.symbol,
        approved=approved,
        side=order_intent.side if order_intent is not None else "BUY",
        reason=order_intent.reason if order_intent is not None else "ENTRY",
        order_type=order_intent.order_type if order_intent is not None else config.entry.order_type,
        quantity=int(order_intent.quantity) if order_intent is not None else entry_plan.quantity,
        stop_price=order_intent.stop_price if order_intent is not None else None,
        limit_price=order_intent.limit_price if order_intent is not None else None,
        initial_stop=setup.initial_stop,
        expires_at=order_intent.expires_at if order_intent is not None else None,
        dedupe_key=order_intent.dedupe_key if order_intent is not None else None,
        rejection_reasons=rejection_reasons,
    )


def swing_lifecycle_transition_from_states(
    *,
    symbol: str,
    occurred_at: datetime,
    from_state: SymbolLifecycleState,
    to_state: SymbolLifecycleState,
    transition_id: str | None = None,
    reason: SwingRejectionReason | None = None,
    evidence: dict[str, Any] | None = None,
) -> SwingLifecycleTransition:
    return SwingLifecycleTransition(
        transition_id=transition_id
        or f"transition:{symbol}:{from_state.value}:{to_state.value}:{occurred_at.isoformat()}",
        symbol=symbol,
        occurred_at=occurred_at,
        from_state=from_state,
        to_state=to_state,
        reason=reason,
        evidence=evidence or {},
    )


def swing_exit_decision_from_values(
    config: StrategyRuntimeConfig,
    *,
    symbol: str,
    session_date: date,
    current_stop: float,
    updated_stop: float,
    exit_required: bool,
    order_reason: OrderReason | None = None,
    exit_decision_id: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> SwingExitDecision:
    return SwingExitDecision(
        exit_decision_id=exit_decision_id
        or f"exit_decision:{config.strategy.id}:{symbol}:{session_date.isoformat()}",
        strategy_id=config.strategy.id,
        config_hash=config.config_hash(),
        symbol=symbol,
        session_date=session_date,
        exit_required=exit_required,
        order_reason=order_reason,
        current_stop=current_stop,
        updated_stop=updated_stop,
        evidence=evidence or {},
    )


def _candidate_ranks(scored: pd.DataFrame) -> dict[Any, int]:
    eligible = scored.loc[scored["is_candidate"].fillna(False).astype(bool)].copy()
    if eligible.empty:
        return {}
    eligible["_symbol_sort"] = eligible["symbol"].astype(str)
    eligible = eligible.sort_values(
        by=[
            "session_date",
            "candidate_score_pct",
            "trend_quality",
            "dist_to_52w_high",
            "_symbol_sort",
        ],
        ascending=[True, False, False, True, True],
        kind="mergesort",
    )
    ranks: dict[Any, int] = {}
    for _session_date, session in eligible.groupby("session_date", sort=True):
        for rank, row_index in enumerate(session.index, start=1):
            ranks[row_index] = rank
    return ranks


def _candidate_from_row(
    row: pd.Series,
    config: StrategyRuntimeConfig,
    *,
    rank: int | None,
    feature_snapshot_ref_column: str | None,
) -> SwingCandidate:
    eligible = _as_bool(row["is_candidate"])
    gates = _candidate_gates(row, config)
    rejection_reasons = tuple(gate.reason for gate in gates if gate.reason is not None)
    quality_score = _quality_score_from_row(row) if eligible else None
    ranking = (
        SwingRankingResult(
            rank=rank if rank is not None else 1,
            score=quality_score,
            trend_quality=_as_float(row["trend_quality"]),
            dist_to_52w_high=_as_float(row["dist_to_52w_high"]),
            per_share_risk=None,
            tie_break_symbol=str(row["symbol"]),
        )
        if eligible and quality_score is not None
        else None
    )
    session_date = _row_date(row["session_date"])
    feature_snapshot_ref = (
        str(row[feature_snapshot_ref_column])
        if feature_snapshot_ref_column is not None
        and pd.notna(row.get(feature_snapshot_ref_column))
        else None
    )
    return SwingCandidate(
        candidate_id=_candidate_id(config.strategy.id, str(row["symbol"]), session_date),
        strategy_id=config.strategy.id,
        config_hash=config.config_hash(),
        symbol=str(row["symbol"]),
        session_date=session_date,
        regime_state=RegimeState(str(row["regime_state"])),
        feature_snapshot_ref=feature_snapshot_ref,
        eligible=eligible,
        eligibility_gates=gates,
        rejection_reasons=rejection_reasons,
        quality_score=quality_score,
        ranking=ranking,
    )


def _candidate_gates(
    row: pd.Series,
    config: StrategyRuntimeConfig,
) -> tuple[SwingEligibilityGate, ...]:
    return (
        _gate(
            "universe.eligible",
            SwingRejectionCategory.UNIVERSE,
            _as_bool(row["universe_eligible"]),
            "UNIVERSE_NOT_ELIGIBLE",
            "Symbol failed universe eligibility",
            {"universe_eligible": row.get("universe_eligible")},
        ),
        _gate(
            "regime.entry_enabled",
            SwingRejectionCategory.REGIME,
            _as_bool(row["entry_enabled"]),
            "REGIME_ENTRY_DISABLED",
            "Current regime does not allow new entries",
            {"regime_state": row.get("regime_state")},
        ),
        _gate(
            "trend.close_above_ma50",
            SwingRejectionCategory.TREND,
            _as_float(row["split_adj_close"]) > _as_float(row["ma50"]),
            "TREND_CLOSE_NOT_ABOVE_MA50",
            "Close is not above MA50",
            {"split_adj_close": row.get("split_adj_close"), "ma50": row.get("ma50")},
        ),
        _gate(
            "trend.ma50_above_ma200",
            SwingRejectionCategory.TREND,
            _as_float(row["ma50"]) > _as_float(row["ma200"]),
            "TREND_MA50_NOT_ABOVE_MA200",
            "MA50 is not above MA200",
            {"ma50": row.get("ma50"), "ma200": row.get("ma200")},
        ),
        _gate(
            "trend.ma200_slope_positive",
            SwingRejectionCategory.TREND,
            _as_float(row["ma200_slope_pct20"]) > 0.0,
            "TREND_MA200_SLOPE_NOT_POSITIVE",
            "MA200 slope is not positive",
            {"ma200_slope_pct20": row.get("ma200_slope_pct20")},
        ),
        _gate(
            "trend.near_52w_high",
            SwingRejectionCategory.TREND,
            _as_float(row["dist_to_52w_high"]) <= config.filters.max_distance_from_52w_high,
            "TREND_TOO_FAR_FROM_52W_HIGH",
            "Symbol is too far from its 52-week high",
            {
                "dist_to_52w_high": row.get("dist_to_52w_high"),
                "max_distance_from_52w_high": config.filters.max_distance_from_52w_high,
            },
        ),
        _gate(
            "score.candidate_score_threshold",
            SwingRejectionCategory.TREND,
            _score_gate_passes(
                row.get("candidate_score_pct"),
                row.get("effective_candidate_score_threshold_pct"),
            ),
            "SCORE_BELOW_EFFECTIVE_THRESHOLD",
            "Candidate score percentile is below the effective threshold",
            {
                "candidate_score_pct": row.get("candidate_score_pct"),
                "effective_candidate_score_threshold_pct": row.get(
                    "effective_candidate_score_threshold_pct"
                ),
            },
        ),
        _gate(
            "score.trend_quality_threshold",
            SwingRejectionCategory.TREND,
            _score_gate_passes(row.get("trend_quality"), row.get("effective_min_trend_quality")),
            "TREND_QUALITY_BELOW_EFFECTIVE_THRESHOLD",
            "Trend quality is below the effective threshold",
            {
                "trend_quality": row.get("trend_quality"),
                "effective_min_trend_quality": row.get("effective_min_trend_quality"),
            },
        ),
        _earnings_gate(row, config),
    )


def _earnings_gate(row: pd.Series, config: StrategyRuntimeConfig) -> SwingEligibilityGate:
    if "regular_closes_until_earnings_event" not in row.index:
        return _gate(
            "event.earnings_window",
            SwingRejectionCategory.EVENT,
            True,
            "EVENT_EARNINGS_WINDOW_BLOCKED",
            "Earnings window blocks new entry",
            {"regular_closes_until_earnings_event": None},
        )
    distance = row.get("regular_closes_until_earnings_event")
    passed = pd.isna(distance) or (
        _as_float(distance) > config.events.min_regular_closes_before_earnings_for_new_entry
    )
    return _gate(
        "event.earnings_window",
        SwingRejectionCategory.EVENT,
        passed,
        "EVENT_EARNINGS_WINDOW_BLOCKED",
        "Earnings window blocks new entry",
        {
            "regular_closes_until_earnings_event": distance,
            "min_regular_closes_before_earnings_for_new_entry": (
                config.events.min_regular_closes_before_earnings_for_new_entry
            ),
        },
    )


def _gate(
    gate_id: str,
    category: SwingRejectionCategory,
    passed: bool,
    reason_code: str,
    message: str,
    evidence: dict[str, Any],
) -> SwingEligibilityGate:
    reason = None
    if not passed:
        reason = SwingRejectionReason(
            code=reason_code,
            category=category,
            message=message,
            evidence=_json_safe_evidence(evidence),
        )
    return SwingEligibilityGate(
        gate_id=gate_id,
        category=category,
        passed=passed,
        reason=reason,
        evidence=_json_safe_evidence(evidence),
    )


def _quality_score_from_row(row: pd.Series) -> SwingQualityScore:
    return build_quality_score(
        score_raw=_as_float(row["candidate_score_raw"]),
        score_percentile=_as_float(row["candidate_score_pct"]),
    )


def _score_gate_passes(value: object, threshold: object) -> bool:
    if pd.isna(value) or pd.isna(threshold):
        return False
    return _as_float(value) >= _as_float(threshold)


def _validate_columns(frame: pd.DataFrame, required: Sequence[str]) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Missing required columns: {missing_str}")


def _candidate_id(strategy_id: str, symbol: str, session_date: date) -> str:
    return f"candidate:{strategy_id}:{symbol}:{session_date.isoformat()}"


def _signal_id(strategy_id: str, symbol: str, session_date: date, setup_id: str) -> str:
    return f"signal:{strategy_id}:{symbol}:{session_date.isoformat()}:{setup_id}"


def _risk_plan_id(strategy_id: str, symbol: str, session_date: date, setup_id: str) -> str:
    return f"risk_plan:{strategy_id}:{symbol}:{session_date.isoformat()}:{setup_id}"


def _order_plan_id(strategy_id: str, symbol: str, session_date: date, setup_id: str) -> str:
    return f"order_plan:{strategy_id}:{symbol}:{session_date.isoformat()}:{setup_id}"


def _equity_from_risk_budget(entry_plan: EntryPlan, config: StrategyRuntimeConfig) -> float:
    risk_pct = float(config.risk.risk_per_trade_pct_equity)
    if risk_pct <= 0:
        return 1.0
    return float(entry_plan.base_risk_budget) / risk_pct


def _portfolio_constraints_from_entry_plan(
    entry_plan: EntryPlan,
    config: StrategyRuntimeConfig,
) -> tuple[SwingPortfolioConstraintResult, ...]:
    constraints = [
        SwingPortfolioConstraintResult(
            constraint_id="portfolio.heat",
            category=SwingRejectionCategory.PORTFOLIO,
            passed=entry_plan.projected_portfolio_heat <= config.risk.max_portfolio_heat_pct_equity,
            limit_value=config.risk.max_portfolio_heat_pct_equity,
            projected_value=entry_plan.projected_portfolio_heat,
            reason=None
            if entry_plan.projected_portfolio_heat <= config.risk.max_portfolio_heat_pct_equity
            else SwingRejectionReason(
                code="PORTFOLIO_HEAT_LIMIT",
                category=SwingRejectionCategory.PORTFOLIO,
                message="Projected portfolio heat exceeds configured limit",
            ),
        ),
        SwingPortfolioConstraintResult(
            constraint_id="portfolio.daily_new_risk",
            category=SwingRejectionCategory.PORTFOLIO,
            passed=(
                entry_plan.projected_daily_new_risk
                <= config.risk.max_new_risk_per_day_pct_equity
            ),
            limit_value=config.risk.max_new_risk_per_day_pct_equity,
            projected_value=entry_plan.projected_daily_new_risk,
            reason=None
            if entry_plan.projected_daily_new_risk <= config.risk.max_new_risk_per_day_pct_equity
            else SwingRejectionReason(
                code="DAILY_NEW_RISK_LIMIT",
                category=SwingRejectionCategory.PORTFOLIO,
                message="Projected daily new risk exceeds configured limit",
            ),
        ),
        SwingPortfolioConstraintResult(
            constraint_id="portfolio.sector_exposure",
            category=SwingRejectionCategory.PORTFOLIO,
            passed=entry_plan.projected_sector_gross_exposure <= config.risk.max_sector_pct_equity,
            limit_value=config.risk.max_sector_pct_equity,
            projected_value=entry_plan.projected_sector_gross_exposure,
            reason=None
            if entry_plan.projected_sector_gross_exposure <= config.risk.max_sector_pct_equity
            else SwingRejectionReason(
                code="SECTOR_EXPOSURE_LIMIT",
                category=SwingRejectionCategory.PORTFOLIO,
                message="Projected sector exposure exceeds configured limit",
            ),
        ),
    ]
    for index, reason in enumerate(entry_plan.reject_reasons, start=1):
        constraints.append(
            SwingPortfolioConstraintResult(
                constraint_id=f"entry_plan.reject_reason.{index}",
                category=_category_for_reject_reason(reason),
                passed=False,
                reason=_rejection_reason_from_text(reason),
            )
        )
    return tuple(constraints)


def _rejection_reasons_from_texts(
    reject_reasons: tuple[str, ...],
) -> tuple[SwingRejectionReason, ...]:
    return tuple(_rejection_reason_from_text(reason) for reason in reject_reasons)


def _rejection_reason_from_text(reason: str) -> SwingRejectionReason:
    return SwingRejectionReason(
        code=_reason_code(reason),
        category=_category_for_reject_reason(reason),
        message=reason,
    )


def _category_for_reject_reason(reason: str) -> SwingRejectionCategory:
    normalized = reason.lower()
    if "heat" in normalized or "sector" in normalized or "portfolio" in normalized:
        return SwingRejectionCategory.PORTFOLIO
    if "duplicate" in normalized or "pending" in normalized or "active" in normalized:
        return SwingRejectionCategory.RUNTIME
    return SwingRejectionCategory.RISK


def _reason_code(reason: str) -> str:
    normalized = "".join(character if character.isalnum() else "_" for character in reason.upper())
    collapsed = "_".join(part for part in normalized.split("_") if part)
    return collapsed or "ENTRY_PLAN_REJECTED"


def _row_date(value: object) -> date:
    return pd.Timestamp(value).date()


def _as_bool(value: object) -> bool:
    if pd.isna(value):
        return False
    return bool(value)


def _as_float(value: object) -> float:
    return float(value)


def _json_safe_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in evidence.items():
        if pd.isna(value):
            safe[key] = None
        elif isinstance(value, pd.Timestamp):
            safe[key] = value.isoformat()
        else:
            safe[key] = value
    return safe


__all__ = [
    "REQUIRED_SCORED_CANDIDATE_COLUMNS",
    "swing_candidates_from_scored_frame",
    "swing_exit_decision_from_values",
    "swing_lifecycle_transition_from_states",
    "swing_order_plan_from_entry_plan",
    "swing_risk_plan_from_entry_plan",
    "swing_signal_from_setup_snapshot",
]
