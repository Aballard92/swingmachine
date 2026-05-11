from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

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
from swingmachine.swing_contracts import (
    SwingCandidate,
    SwingEligibilityGate,
    SwingExitDecision,
    SwingFeatureSnapshotRecord,
    SwingLifecycleTransition,
    SwingOrderPlan,
    SwingPortfolioConstraintResult,
    SwingQualityScore,
    SwingRankingResult,
    SwingRejectionCategory,
    SwingRejectionReason,
    SwingRiskPlan,
    SwingSignal,
    SwingUniverseMember,
    build_quality_score,
    build_swing_feature_snapshot_record,
    hash_feature_snapshot,
)


def _reason() -> SwingRejectionReason:
    return SwingRejectionReason(
        code="TREND_CLOSE_BELOW_MA50",
        category=SwingRejectionCategory.TREND,
        message="Close is below MA50",
        evidence={"close": 99.0, "ma50": 100.0},
    )


def _passed_gate() -> SwingEligibilityGate:
    return SwingEligibilityGate(
        gate_id="trend.close_above_ma50",
        category=SwingRejectionCategory.TREND,
        passed=True,
        evidence={"close": 101.0, "ma50": 100.0},
    )


def _failed_gate() -> SwingEligibilityGate:
    return SwingEligibilityGate(
        gate_id="trend.close_above_ma50",
        category=SwingRejectionCategory.TREND,
        passed=False,
        reason=_reason(),
    )


def _passed_constraint() -> SwingPortfolioConstraintResult:
    return SwingPortfolioConstraintResult(
        constraint_id="portfolio.heat",
        category=SwingRejectionCategory.PORTFOLIO,
        passed=True,
        limit_value=0.02,
        projected_value=0.01,
    )


def _failed_constraint() -> SwingPortfolioConstraintResult:
    return SwingPortfolioConstraintResult(
        constraint_id="portfolio.heat",
        category=SwingRejectionCategory.PORTFOLIO,
        passed=False,
        limit_value=0.02,
        projected_value=0.03,
        reason=SwingRejectionReason(
            code="PORTFOLIO_HEAT_LIMIT",
            category=SwingRejectionCategory.PORTFOLIO,
            message="Projected heat exceeds limit",
        ),
    )


def _score() -> SwingQualityScore:
    return build_quality_score(score_raw=1.25, score_percentile=0.82)


def _ranking() -> SwingRankingResult:
    return SwingRankingResult(
        rank=1,
        score=_score(),
        trend_quality=0.74,
        dist_to_52w_high=0.04,
        per_share_risk=2.5,
        tie_break_symbol="AAPL",
    )


def _feature_snapshot() -> FeatureSnapshot:
    return FeatureSnapshot(
        symbol="AAPL",
        session_date=date(2026, 5, 5),
        ret_21=0.05,
        ret_63=0.12,
        ret_126=0.22,
        ret_252=0.31,
        mom_252_21=0.26,
        rs_vs_benchmark_126=0.08,
        ma20=105.0,
        ma50=100.0,
        ma200=90.0,
        ma50_slope_pct20=0.04,
        ma200_slope_pct20=0.02,
        atr_14=2.0,
        atr_5=1.5,
        atr_20=2.2,
        atr_pct=0.019,
        range_compression_ratio=0.75,
        dist_to_52w_high=0.04,
        pullback_days=4,
        pullback_depth_atr=1.1,
        volume_ratio_20=0.8,
        trend_quality=0.74,
        candidate_score_raw=1.25,
        candidate_score_pct=0.82,
        effective_candidate_score_threshold_pct=0.80,
        effective_min_trend_quality=0.45,
        pattern_type=None,
        setup_id=None,
        setup_start_date=None,
        setup_end_date=None,
        setup_high=None,
        setup_low=None,
        setup_high_date=None,
        setup_low_date=None,
        setup_valid=False,
        earnings_event_session=None,
        regular_closes_until_earnings_event=10,
    )


def test_failed_eligibility_gate_requires_rejection_reason() -> None:
    with pytest.raises(ValidationError, match="failed eligibility gates"):
        SwingEligibilityGate(
            gate_id="trend.close_above_ma50",
            category=SwingRejectionCategory.TREND,
            passed=False,
        )


def test_passed_eligibility_gate_rejects_rejection_reason() -> None:
    with pytest.raises(ValidationError, match="passed eligibility gates"):
        SwingEligibilityGate(
            gate_id="trend.close_above_ma50",
            category=SwingRejectionCategory.TREND,
            passed=True,
            reason=_reason(),
        )


def test_quality_score_maps_percentile_to_review_score() -> None:
    score = build_quality_score(score_raw=0.5, score_percentile=0.91)

    assert score.quality_score_0_100 == 91.0
    assert score.score_percentile == 0.91


def test_quality_score_rejects_mismatched_review_score() -> None:
    with pytest.raises(ValidationError, match="score_percentile"):
        SwingQualityScore(
            score_raw=0.5,
            score_percentile=0.91,
            quality_score_0_100=90.0,
        )


def test_eligible_candidate_requires_score_and_ranking() -> None:
    with pytest.raises(ValidationError, match="quality score"):
        SwingCandidate(
            candidate_id="candidate:AAPL:2026-05-05",
            strategy_id="RF_TPC_V2",
            config_hash="abc123",
            symbol="AAPL",
            session_date=date(2026, 5, 5),
            regime_state=RegimeState.RISK_ON,
            eligible=True,
            eligibility_gates=(_passed_gate(),),
        )


def test_eligible_candidate_rejects_failed_gate() -> None:
    with pytest.raises(ValidationError, match="failed eligibility gates"):
        SwingCandidate(
            candidate_id="candidate:AAPL:2026-05-05",
            strategy_id="RF_TPC_V2",
            config_hash="abc123",
            symbol="AAPL",
            session_date=date(2026, 5, 5),
            regime_state=RegimeState.RISK_ON,
            eligible=True,
            eligibility_gates=(_failed_gate(),),
            quality_score=_score(),
            ranking=_ranking(),
        )


def test_swing_candidate_serializes_baseline_metadata() -> None:
    candidate = SwingCandidate(
        candidate_id="candidate:AAPL:2026-05-05",
        strategy_id="RF_TPC_V2",
        config_hash="abc123",
        symbol="AAPL",
        session_date=date(2026, 5, 5),
        regime_state=RegimeState.RISK_ON,
        eligible=True,
        eligibility_gates=(_passed_gate(),),
        quality_score=_score(),
        ranking=_ranking(),
    )

    payload = candidate.model_dump(mode="json")

    assert payload["baseline_id"] == "swing_machine_v0_1"
    assert payload["data_contract_version"] == "prepared_market_and_historical_panel_v1"
    assert payload["ranking"]["rank"] == 1
    assert payload["quality_score"]["quality_score_0_100"] == 82.0


def test_feature_snapshot_record_hashes_and_serializes_existing_feature_contract() -> None:
    snapshot = _feature_snapshot()

    record = build_swing_feature_snapshot_record(
        snapshot,
        strategy_id="RF_TPC_V2",
        config_hash="abc123",
    )

    payload = record.model_dump(mode="json")

    assert record.feature_snapshot_hash == hash_feature_snapshot(snapshot)
    assert payload["baseline_id"] == "swing_machine_v0_1"
    assert payload["data_contract_version"] == "prepared_market_and_historical_panel_v1"
    assert payload["feature_snapshot"]["symbol"] == "AAPL"
    assert payload["feature_snapshot_hash"] == record.feature_snapshot_hash


def test_feature_snapshot_record_rejects_symbol_mismatch() -> None:
    snapshot = _feature_snapshot()

    with pytest.raises(ValidationError, match="symbol must match"):
        SwingFeatureSnapshotRecord(
            feature_snapshot_id="feature_snapshot:RF_TPC_V2:MSFT:2026-05-05",
            strategy_id="RF_TPC_V2",
            config_hash="abc123",
            symbol="MSFT",
            session_date=snapshot.session_date,
            feature_snapshot=snapshot,
            feature_snapshot_hash=hash_feature_snapshot(snapshot),
        )


def test_feature_snapshot_record_rejects_hash_mismatch() -> None:
    snapshot = _feature_snapshot()

    with pytest.raises(ValidationError, match="feature_snapshot_hash"):
        SwingFeatureSnapshotRecord(
            feature_snapshot_id="feature_snapshot:RF_TPC_V2:AAPL:2026-05-05",
            strategy_id="RF_TPC_V2",
            config_hash="abc123",
            symbol="AAPL",
            session_date=snapshot.session_date,
            feature_snapshot=snapshot,
            feature_snapshot_hash="not-the-real-hash",
        )


def test_ineligible_universe_member_requires_failed_gate_or_reason() -> None:
    with pytest.raises(ValidationError, match="ineligible universe members"):
        SwingUniverseMember(
            member_id="universe:AAPL:2026-05-05",
            strategy_id="RF_TPC_V2",
            config_hash="abc123",
            symbol="AAPL",
            session_date=date(2026, 5, 5),
            asset_type=AssetType.COMMON_STOCK,
            exchange="NASDAQ",
            currency="USD",
            sector="Technology",
            is_tradable=False,
            eligible=False,
        )


def test_universe_member_serializes_reference_and_gate_evidence() -> None:
    member = SwingUniverseMember(
        member_id="universe:AAPL:2026-05-05",
        strategy_id="RF_TPC_V2",
        config_hash="abc123",
        symbol="AAPL",
        session_date=date(2026, 5, 5),
        asset_type=AssetType.COMMON_STOCK,
        exchange="NASDAQ",
        currency="USD",
        sector="Technology",
        is_tradable=True,
        eligible=True,
        eligibility_gates=(_passed_gate(),),
    )

    payload = member.model_dump(mode="json")

    assert payload["baseline_id"] == "swing_machine_v0_1"
    assert payload["data_contract_version"] == "prepared_market_and_historical_panel_v1"
    assert payload["asset_type"] == "COMMON_STOCK"
    assert payload["eligibility_gates"][0]["passed"] is True


def test_approved_signal_requires_setup_price_risk_and_score_fields() -> None:
    with pytest.raises(ValidationError, match="setup, price, risk, and score"):
        SwingSignal(
            signal_id="signal:AAPL:2026-05-05",
            candidate_id="candidate:AAPL:2026-05-05",
            strategy_id="RF_TPC_V2",
            config_hash="abc123",
            symbol="AAPL",
            session_date=date(2026, 5, 5),
            regime_state=RegimeState.RISK_ON,
            approved=True,
            eligibility_gates=(_passed_gate(),),
        )


def test_approved_signal_requires_initial_stop_below_entry_trigger() -> None:
    with pytest.raises(ValidationError, match="initial_stop below entry_trigger"):
        SwingSignal(
            signal_id="signal:AAPL:2026-05-05",
            candidate_id="candidate:AAPL:2026-05-05",
            strategy_id="RF_TPC_V2",
            config_hash="abc123",
            symbol="AAPL",
            session_date=date(2026, 5, 5),
            regime_state=RegimeState.RISK_ON,
            approved=True,
            pattern_type=PatternType.TIGHT_BASE,
            setup_id="setup:AAPL:2026-05-05",
            entry_trigger=101.0,
            entry_limit=102.0,
            initial_stop=101.0,
            per_share_risk=1.0,
            quality_score=_score(),
            eligibility_gates=(_passed_gate(),),
        )


def test_swing_signal_serializes_approved_setup_transition() -> None:
    signal = SwingSignal(
        signal_id="signal:AAPL:2026-05-05",
        candidate_id="candidate:AAPL:2026-05-05",
        strategy_id="RF_TPC_V2",
        config_hash="abc123",
        symbol="AAPL",
        session_date=date(2026, 5, 5),
        regime_state=RegimeState.RISK_ON,
        approved=True,
        pattern_type=PatternType.TIGHT_BASE,
        setup_id="setup:AAPL:2026-05-05",
        entry_trigger=101.0,
        entry_limit=102.0,
        initial_stop=98.0,
        per_share_risk=3.0,
        quality_score=_score(),
        eligibility_gates=(_passed_gate(),),
    )

    payload = signal.model_dump(mode="json")

    assert payload["approved"] is True
    assert payload["baseline_id"] == "swing_machine_v0_1"
    assert payload["pattern_type"] == "TIGHT_BASE"
    assert payload["per_share_risk"] == 3.0


def test_failed_portfolio_constraint_requires_reason() -> None:
    with pytest.raises(ValidationError, match="failed portfolio constraints"):
        SwingPortfolioConstraintResult(
            constraint_id="portfolio.heat",
            category=SwingRejectionCategory.PORTFOLIO,
            passed=False,
            limit_value=0.02,
            projected_value=0.03,
        )


def test_risk_plan_requires_per_share_risk_to_match_stop_distance() -> None:
    with pytest.raises(ValidationError, match="per_share_risk"):
        SwingRiskPlan(
            risk_plan_id="risk:AAPL:2026-05-05",
            signal_id="signal:AAPL:2026-05-05",
            strategy_id="RF_TPC_V2",
            config_hash="abc123",
            symbol="AAPL",
            session_date=date(2026, 5, 5),
            approved=True,
            entry_trigger=101.0,
            initial_stop=98.0,
            per_share_risk=2.0,
            equity=100000.0,
            base_risk_budget=300.0,
            regime_risk_budget=300.0,
            effective_risk_budget=300.0,
            shares_from_risk=100,
            shares_from_notional=50,
            quantity=50,
            projected_portfolio_heat=0.01,
            projected_daily_new_risk=0.003,
            constraints=(_passed_constraint(),),
        )


def test_risk_plan_serializes_approved_risk_evidence() -> None:
    plan = SwingRiskPlan(
        risk_plan_id="risk:AAPL:2026-05-05",
        signal_id="signal:AAPL:2026-05-05",
        strategy_id="RF_TPC_V2",
        config_hash="abc123",
        symbol="AAPL",
        session_date=date(2026, 5, 5),
        approved=True,
        entry_trigger=101.0,
        initial_stop=98.0,
        per_share_risk=3.0,
        equity=100000.0,
        base_risk_budget=300.0,
        regime_risk_budget=300.0,
        effective_risk_budget=300.0,
        shares_from_risk=100,
        shares_from_notional=50,
        quantity=50,
        projected_portfolio_heat=0.01,
        projected_daily_new_risk=0.003,
        constraints=(_passed_constraint(),),
    )

    payload = plan.model_dump(mode="json")

    assert payload["approved"] is True
    assert payload["quantity"] == 50
    assert payload["constraints"][0]["constraint_id"] == "portfolio.heat"


def test_rejected_risk_plan_requires_failed_constraint_or_reason() -> None:
    with pytest.raises(ValidationError, match="rejected risk plans"):
        SwingRiskPlan(
            risk_plan_id="risk:AAPL:2026-05-05",
            signal_id="signal:AAPL:2026-05-05",
            strategy_id="RF_TPC_V2",
            config_hash="abc123",
            symbol="AAPL",
            session_date=date(2026, 5, 5),
            approved=False,
            entry_trigger=101.0,
            initial_stop=98.0,
            per_share_risk=3.0,
            equity=100000.0,
            base_risk_budget=300.0,
            regime_risk_budget=300.0,
            effective_risk_budget=300.0,
            shares_from_risk=100,
            shares_from_notional=50,
            quantity=0,
            projected_portfolio_heat=0.01,
            projected_daily_new_risk=0.003,
        )


def test_order_plan_requires_stop_limit_prices_and_dedupe_key_when_approved() -> None:
    with pytest.raises(ValidationError, match="stop and limit prices"):
        SwingOrderPlan(
            order_plan_id="order:AAPL:2026-05-05",
            risk_plan_id="risk:AAPL:2026-05-05",
            signal_id="signal:AAPL:2026-05-05",
            strategy_id="RF_TPC_V2",
            config_hash="abc123",
            symbol="AAPL",
            approved=True,
            side=OrderSide.BUY,
            reason=OrderReason.ENTRY,
            order_type=OrderType.STOP_LIMIT,
            quantity=50,
            initial_stop=98.0,
        )


def test_order_plan_serializes_safe_paper_shadow_order_plan() -> None:
    plan = SwingOrderPlan(
        order_plan_id="order:AAPL:2026-05-05",
        risk_plan_id="risk:AAPL:2026-05-05",
        signal_id="signal:AAPL:2026-05-05",
        strategy_id="RF_TPC_V2",
        config_hash="abc123",
        symbol="AAPL",
        approved=True,
        side=OrderSide.BUY,
        reason=OrderReason.ENTRY,
        order_type=OrderType.STOP_LIMIT,
        quantity=50,
        stop_price=101.0,
        limit_price=102.0,
        initial_stop=98.0,
        expires_at=datetime(2026, 5, 6, 21, 0, tzinfo=UTC),
        dedupe_key="RF_TPC_V2:AAPL:setup:AAPL:2026-05-05",
    )

    payload = plan.model_dump(mode="json")

    assert payload["approved"] is True
    assert payload["side"] == "BUY"
    assert payload["order_type"] == "STOP_LIMIT"
    assert payload["dedupe_key"].startswith("RF_TPC_V2:AAPL")


def test_lifecycle_transition_serializes_state_change() -> None:
    transition = SwingLifecycleTransition(
        transition_id="transition:AAPL:pending-entry-active",
        symbol="AAPL",
        occurred_at=datetime(2026, 5, 6, 14, 30, tzinfo=UTC),
        from_state=SymbolLifecycleState.PENDING_ENTRY,
        to_state=SymbolLifecycleState.ACTIVE,
        evidence={"fill_price": 101.0},
    )

    payload = transition.model_dump(mode="json")

    assert payload["from_state"] == "PENDING_ENTRY"
    assert payload["to_state"] == "ACTIVE"
    assert payload["evidence"]["fill_price"] == 101.0


def test_exit_decision_requires_order_reason_when_exit_required() -> None:
    with pytest.raises(ValidationError, match="order reason"):
        SwingExitDecision(
            exit_decision_id="exit:AAPL:2026-05-10",
            strategy_id="RF_TPC_V2",
            config_hash="abc123",
            symbol="AAPL",
            session_date=date(2026, 5, 10),
            exit_required=True,
            current_stop=98.0,
            updated_stop=99.0,
        )


def test_exit_decision_rejects_stop_loosen() -> None:
    with pytest.raises(ValidationError, match="must not loosen"):
        SwingExitDecision(
            exit_decision_id="exit:AAPL:2026-05-10",
            strategy_id="RF_TPC_V2",
            config_hash="abc123",
            symbol="AAPL",
            session_date=date(2026, 5, 10),
            exit_required=False,
            current_stop=98.0,
            updated_stop=97.0,
        )
