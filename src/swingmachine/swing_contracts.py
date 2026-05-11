from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import Field, model_validator

from swingmachine.baseline import BASELINE_ID, DATA_CONTRACT_VERSION
from swingmachine.contracts import FeatureSnapshot
from swingmachine.enums import (
    AssetType,
    OrderReason,
    OrderSide,
    OrderType,
    PatternType,
    RegimeState,
    SymbolLifecycleState,
)
from swingmachine.modeling import (
    ImmutableModel,
    NonNegativeFloat,
    NonNegativeInt,
    Percent,
    PositiveFloat,
    PositiveInt,
)


class SwingRejectionCategory(StrEnum):
    DATA = "DATA"
    UNIVERSE = "UNIVERSE"
    REGIME = "REGIME"
    TREND = "TREND"
    SETUP = "SETUP"
    EVENT = "EVENT"
    RISK = "RISK"
    PORTFOLIO = "PORTFOLIO"
    RUNTIME = "RUNTIME"
    SAFETY = "SAFETY"


class SwingRejectionReason(ImmutableModel):
    code: str
    category: SwingRejectionCategory
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class SwingEligibilityGate(ImmutableModel):
    gate_id: str
    category: SwingRejectionCategory
    passed: bool
    reason: SwingRejectionReason | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _failed_gates_must_have_reason(self) -> Self:
        if not self.passed and self.reason is None:
            raise ValueError("failed eligibility gates must include a rejection reason")
        if self.passed and self.reason is not None:
            raise ValueError("passed eligibility gates must not include a rejection reason")
        return self


class SwingQualityScore(ImmutableModel):
    score_raw: float
    score_percentile: Percent
    quality_score_0_100: NonNegativeFloat

    @model_validator(mode="after")
    def _quality_score_matches_percentile(self) -> Self:
        if self.quality_score_0_100 > 100:
            raise ValueError("quality_score_0_100 must be less than or equal to 100")
        expected_score = float(self.score_percentile) * 100.0
        if abs(float(self.quality_score_0_100) - expected_score) > 1e-9:
            raise ValueError("quality_score_0_100 must equal score_percentile * 100")
        return self


class SwingRankingResult(ImmutableModel):
    rank: PositiveInt
    score: SwingQualityScore
    trend_quality: Percent
    dist_to_52w_high: Percent
    per_share_risk: PositiveFloat | None = None
    tie_break_symbol: str


class SwingFeatureSnapshotRecord(ImmutableModel):
    feature_snapshot_id: str
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    data_contract_version: Literal["prepared_market_and_historical_panel_v1"] = (
        DATA_CONTRACT_VERSION
    )
    strategy_id: str
    config_hash: str
    symbol: str
    session_date: date
    feature_snapshot: FeatureSnapshot
    feature_snapshot_hash: str
    source_contract: Literal["FeatureSnapshot"] = "FeatureSnapshot"

    @model_validator(mode="after")
    def _feature_snapshot_record_is_consistent(self) -> Self:
        if self.symbol != self.feature_snapshot.symbol:
            raise ValueError("feature snapshot record symbol must match feature snapshot symbol")
        if self.session_date != self.feature_snapshot.session_date:
            raise ValueError(
                "feature snapshot record session_date must match feature snapshot session_date"
            )
        expected_hash = hash_feature_snapshot(self.feature_snapshot)
        if self.feature_snapshot_hash != expected_hash:
            raise ValueError("feature_snapshot_hash must match the wrapped feature snapshot")
        return self


class SwingUniverseMember(ImmutableModel):
    member_id: str
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    data_contract_version: Literal["prepared_market_and_historical_panel_v1"] = (
        DATA_CONTRACT_VERSION
    )
    strategy_id: str
    config_hash: str
    symbol: str
    session_date: date
    asset_type: AssetType
    exchange: str
    currency: str
    sector: str | None = None
    is_tradable: bool
    eligible: bool
    eligibility_gates: tuple[SwingEligibilityGate, ...] = Field(default_factory=tuple)
    rejection_reasons: tuple[SwingRejectionReason, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _universe_member_state_is_consistent(self) -> Self:
        failed_gates = tuple(gate for gate in self.eligibility_gates if not gate.passed)
        if self.eligible and failed_gates:
            raise ValueError("eligible universe members must not include failed gates")
        if not self.eligible and not failed_gates and not self.rejection_reasons:
            raise ValueError("ineligible universe members must include a failed gate or reason")
        return self


class SwingCandidate(ImmutableModel):
    candidate_id: str
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    data_contract_version: Literal["prepared_market_and_historical_panel_v1"] = (
        DATA_CONTRACT_VERSION
    )
    strategy_id: str
    config_hash: str
    symbol: str
    session_date: date
    regime_state: RegimeState
    feature_snapshot_ref: str | None = None
    eligible: bool
    eligibility_gates: tuple[SwingEligibilityGate, ...] = Field(default_factory=tuple)
    rejection_reasons: tuple[SwingRejectionReason, ...] = Field(default_factory=tuple)
    quality_score: SwingQualityScore | None = None
    ranking: SwingRankingResult | None = None

    @model_validator(mode="after")
    def _candidate_state_is_consistent(self) -> Self:
        failed_gates = tuple(gate for gate in self.eligibility_gates if not gate.passed)
        if self.eligible and failed_gates:
            raise ValueError("eligible candidates must not include failed eligibility gates")
        if self.eligible and self.quality_score is None:
            raise ValueError("eligible candidates must include a quality score")
        if self.eligible and self.ranking is None:
            raise ValueError("eligible candidates must include a ranking result")
        if not self.eligible and not failed_gates and not self.rejection_reasons:
            raise ValueError("ineligible candidates must include a failed gate or rejection reason")
        return self


class SwingSignal(ImmutableModel):
    signal_id: str
    candidate_id: str
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    strategy_id: str
    config_hash: str
    symbol: str
    session_date: date
    regime_state: RegimeState
    approved: bool
    pattern_type: PatternType | None = None
    setup_id: str | None = None
    entry_trigger: PositiveFloat | None = None
    entry_limit: PositiveFloat | None = None
    initial_stop: PositiveFloat | None = None
    per_share_risk: PositiveFloat | None = None
    quality_score: SwingQualityScore | None = None
    eligibility_gates: tuple[SwingEligibilityGate, ...] = Field(default_factory=tuple)
    rejection_reasons: tuple[SwingRejectionReason, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _signal_state_is_consistent(self) -> Self:
        failed_gates = tuple(gate for gate in self.eligibility_gates if not gate.passed)
        required_when_approved = (
            self.pattern_type,
            self.setup_id,
            self.entry_trigger,
            self.entry_limit,
            self.initial_stop,
            self.per_share_risk,
            self.quality_score,
        )
        if self.approved and failed_gates:
            raise ValueError("approved signals must not include failed eligibility gates")
        if self.approved and any(value is None for value in required_when_approved):
            raise ValueError("approved signals must include setup, price, risk, and score fields")
        if self.approved and self.initial_stop is not None and self.entry_trigger is not None:
            if self.initial_stop >= self.entry_trigger:
                raise ValueError("approved signals require initial_stop below entry_trigger")
        if not self.approved and not failed_gates and not self.rejection_reasons:
            raise ValueError("rejected signals must include a failed gate or rejection reason")
        return self


class SwingPortfolioConstraintResult(ImmutableModel):
    constraint_id: str
    category: SwingRejectionCategory
    passed: bool
    limit_value: NonNegativeFloat | None = None
    projected_value: NonNegativeFloat | None = None
    reason: SwingRejectionReason | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _failed_constraints_must_have_reason(self) -> Self:
        if not self.passed and self.reason is None:
            raise ValueError("failed portfolio constraints must include a rejection reason")
        if self.passed and self.reason is not None:
            raise ValueError("passed portfolio constraints must not include a rejection reason")
        return self


class SwingRiskPlan(ImmutableModel):
    risk_plan_id: str
    signal_id: str
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    strategy_id: str
    config_hash: str
    symbol: str
    session_date: date
    approved: bool
    entry_trigger: PositiveFloat
    initial_stop: PositiveFloat
    per_share_risk: PositiveFloat
    equity: PositiveFloat
    base_risk_budget: NonNegativeFloat
    regime_risk_budget: NonNegativeFloat
    effective_risk_budget: NonNegativeFloat
    shares_from_risk: NonNegativeInt
    shares_from_notional: NonNegativeInt
    quantity: NonNegativeInt
    projected_portfolio_heat: NonNegativeFloat
    projected_daily_new_risk: NonNegativeFloat
    constraints: tuple[SwingPortfolioConstraintResult, ...] = Field(default_factory=tuple)
    rejection_reasons: tuple[SwingRejectionReason, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _risk_plan_state_is_consistent(self) -> Self:
        failed_constraints = tuple(
            constraint for constraint in self.constraints if not constraint.passed
        )
        expected_risk = float(self.entry_trigger) - float(self.initial_stop)
        if expected_risk <= 0:
            raise ValueError("risk plans require initial_stop below entry_trigger")
        if abs(float(self.per_share_risk) - expected_risk) > 1e-9:
            raise ValueError("per_share_risk must equal entry_trigger - initial_stop")
        if self.approved and self.quantity < 1:
            raise ValueError("approved risk plans require quantity of at least 1")
        if self.approved and failed_constraints:
            raise ValueError("approved risk plans must not include failed constraints")
        if not self.approved and not failed_constraints and not self.rejection_reasons:
            raise ValueError("rejected risk plans must include a failed constraint or reason")
        return self


class SwingOrderPlan(ImmutableModel):
    order_plan_id: str
    risk_plan_id: str
    signal_id: str
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    strategy_id: str
    config_hash: str
    symbol: str
    approved: bool
    side: OrderSide
    reason: OrderReason
    order_type: OrderType
    quantity: NonNegativeInt
    stop_price: PositiveFloat | None = None
    limit_price: PositiveFloat | None = None
    initial_stop: PositiveFloat | None = None
    expires_at: datetime | None = None
    dedupe_key: str | None = None
    rejection_reasons: tuple[SwingRejectionReason, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _order_plan_state_is_consistent(self) -> Self:
        if self.approved and self.quantity < 1:
            raise ValueError("approved order plans require quantity of at least 1")
        if self.approved and self.order_type == OrderType.STOP_LIMIT:
            if self.stop_price is None or self.limit_price is None:
                raise ValueError("approved stop-limit order plans require stop and limit prices")
        if self.approved and self.dedupe_key is None:
            raise ValueError("approved order plans require a dedupe key")
        if not self.approved and not self.rejection_reasons:
            raise ValueError("rejected order plans must include rejection reasons")
        return self


class SwingLifecycleTransition(ImmutableModel):
    transition_id: str
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    symbol: str
    occurred_at: datetime
    from_state: SymbolLifecycleState
    to_state: SymbolLifecycleState
    reason: SwingRejectionReason | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class SwingExitDecision(ImmutableModel):
    exit_decision_id: str
    baseline_id: Literal["swing_machine_v0_1"] = BASELINE_ID
    strategy_id: str
    config_hash: str
    symbol: str
    session_date: date
    exit_required: bool
    order_reason: OrderReason | None = None
    current_stop: PositiveFloat
    updated_stop: PositiveFloat
    evidence: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _exit_decision_state_is_consistent(self) -> Self:
        if self.exit_required and self.order_reason is None:
            raise ValueError("exit decisions that require exit must include an order reason")
        if not self.exit_required and self.order_reason is not None:
            raise ValueError("hold decisions must not include an order reason")
        if self.updated_stop < self.current_stop:
            raise ValueError("updated_stop must not loosen below current_stop")
        return self


def build_quality_score(score_raw: float, score_percentile: float) -> SwingQualityScore:
    return SwingQualityScore(
        score_raw=score_raw,
        score_percentile=score_percentile,
        quality_score_0_100=score_percentile * 100.0,
    )


def hash_feature_snapshot(feature_snapshot: FeatureSnapshot) -> str:
    payload = json.dumps(feature_snapshot.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_swing_feature_snapshot_record(
    feature_snapshot: FeatureSnapshot,
    *,
    strategy_id: str,
    config_hash: str,
    feature_snapshot_id: str | None = None,
) -> SwingFeatureSnapshotRecord:
    snapshot_id = (
        feature_snapshot_id
        if feature_snapshot_id is not None
        else (
            "feature_snapshot:"
            f"{strategy_id}:{feature_snapshot.symbol}:{feature_snapshot.session_date.isoformat()}"
        )
    )
    return SwingFeatureSnapshotRecord(
        feature_snapshot_id=snapshot_id,
        strategy_id=strategy_id,
        config_hash=config_hash,
        symbol=feature_snapshot.symbol,
        session_date=feature_snapshot.session_date,
        feature_snapshot=feature_snapshot,
        feature_snapshot_hash=hash_feature_snapshot(feature_snapshot),
    )


__all__ = [
    "SwingCandidate",
    "SwingEligibilityGate",
    "SwingExitDecision",
    "SwingFeatureSnapshotRecord",
    "SwingLifecycleTransition",
    "SwingOrderPlan",
    "SwingPortfolioConstraintResult",
    "SwingQualityScore",
    "SwingRankingResult",
    "SwingRejectionCategory",
    "SwingRejectionReason",
    "SwingRiskPlan",
    "SwingSignal",
    "SwingUniverseMember",
    "build_quality_score",
    "build_swing_feature_snapshot_record",
    "hash_feature_snapshot",
]
