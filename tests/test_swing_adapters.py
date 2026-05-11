from __future__ import annotations

from datetime import UTC, date, datetime

import pandas as pd
import pytest

from swingmachine.config import load_strategy_config
from swingmachine.contracts import EntryPlan, OrderIntent, SetupSnapshot
from swingmachine.entries import build_setup_snapshot
from swingmachine.enums import (
    OrderReason,
    OrderSide,
    OrderType,
    RegimeState,
    SymbolLifecycleState,
)
from swingmachine.signals import score_candidates
from swingmachine.swing_adapters import (
    swing_candidates_from_scored_frame,
    swing_exit_decision_from_values,
    swing_lifecycle_transition_from_states,
    swing_order_plan_from_entry_plan,
    swing_risk_plan_from_entry_plan,
    swing_signal_from_setup_snapshot,
)

CONFIG_PATH = "swing_trading_bot_config_template_v2.yaml"


def _candidate_scoring_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    session_date = pd.Timestamp("2026-04-23")
    panel = pd.DataFrame(
        {
            "symbol": ["AAA", "BBB", "CCC"],
            "session_date": [session_date, session_date, session_date],
            "raw_close": [100.0, 100.0, 100.0],
            "raw_volume": [1_000_000.0, 1_000_000.0, 1_000_000.0],
            "split_adj_close": [120.0, 110.0, 105.0],
            "split_adj_high": [121.0, 111.0, 106.0],
            "split_adj_low": [119.0, 109.0, 104.0],
            "ma50": [100.0, 100.0, 100.0],
            "ma200": [90.0, 90.0, 90.0],
            "ma200_slope_pct20": [0.02, 0.02, 0.02],
            "dist_to_52w_high": [0.01, 0.03, 0.05],
            "mom_252_21": [0.30, 0.15, 0.10],
            "ret_126": [0.22, 0.14, 0.09],
            "rs_vs_benchmark_126": [0.12, 0.05, 0.01],
            "trend_quality": [0.80, 0.65, 0.55],
            "regular_closes_until_earnings_event": [10, 10, 10],
            "history_days": [300, 300, 300],
            "avg_daily_dollar_volume_20": [25_000_000.0, 25_000_000.0, 25_000_000.0],
        }
    )
    regime = pd.DataFrame(
        {
            "session_date": [session_date],
            "regime_state": [RegimeState.RISK_ON.value],
            "entry_enabled": [True],
            "min_candidate_score_percentile": [0.80],
            "min_trend_quality": [0.45],
        }
    )
    return panel, regime


def _setup_snapshot(config) -> SetupSnapshot:
    return build_setup_snapshot(
        {
            "symbol": "AAA",
            "session_date": pd.Timestamp("2026-04-23"),
            "pattern_type": "TIGHT_BASE",
            "setup_id": "setup-aaa",
            "setup_start_date": pd.Timestamp("2026-04-17"),
            "setup_end_date": pd.Timestamp("2026-04-23"),
            "setup_high": 100.0,
            "setup_low": 95.0,
            "setup_high_date": pd.Timestamp("2026-04-21"),
            "setup_low_date": pd.Timestamp("2026-04-22"),
            "setup_valid": True,
            "atr_14": 2.0,
        },
        config,
    )


def _order_intent(setup: SetupSnapshot, config) -> OrderIntent:
    return OrderIntent(
        intent_id="intent-aaa",
        dedupe_key=f"{config.strategy.id}:AAA:setup-aaa",
        strategy_id=config.strategy.id,
        config_hash=config.config_hash(),
        symbol="AAA",
        setup_id=setup.setup_id,
        side=OrderSide.BUY,
        reason=OrderReason.ENTRY,
        order_type=OrderType.STOP_LIMIT,
        quantity=50,
        stop_price=setup.entry_trigger,
        limit_price=setup.entry_limit,
        created_at=datetime(2026, 4, 23, 21, 0, tzinfo=UTC),
        expires_at=datetime(2026, 4, 24, 21, 0, tzinfo=UTC),
        broker_order_id=None,
    )


def _entry_plan(config, *, approved: bool = True) -> EntryPlan:
    setup = _setup_snapshot(config)
    return EntryPlan(
        setup=setup,
        approved=approved,
        reject_reasons=() if approved else ("portfolio heat limit breached",),
        quantity=50 if approved else 0,
        base_risk_budget=300.0,
        regime_risk_budget=300.0,
        effective_risk_budget=300.0,
        shares_from_risk=100,
        shares_from_notional=50,
        projected_portfolio_heat=0.01 if approved else 0.03,
        projected_daily_new_risk=0.003,
        projected_sector_gross_exposure=0.05,
        order_intent=_order_intent(setup, config) if approved else None,
    )


def test_scored_frame_adapter_builds_typed_candidates_with_deterministic_rank() -> None:
    config = load_strategy_config(CONFIG_PATH)
    panel, regime = _candidate_scoring_fixture()
    scored = score_candidates(panel, regime, config).sort_values("symbol").reset_index(drop=True)

    candidates = swing_candidates_from_scored_frame(scored, config)
    by_symbol = {candidate.symbol: candidate for candidate in candidates}

    assert tuple(by_symbol) == ("AAA", "BBB", "CCC")
    assert by_symbol["AAA"].eligible is True
    assert by_symbol["AAA"].candidate_id == "candidate:RF_TPC_V2:AAA:2026-04-23"
    assert by_symbol["AAA"].quality_score is not None
    assert by_symbol["AAA"].quality_score.quality_score_0_100 == 100.0
    assert by_symbol["AAA"].ranking is not None
    assert by_symbol["AAA"].ranking.rank == 1
    assert by_symbol["AAA"].ranking.tie_break_symbol == "AAA"


def test_scored_frame_adapter_explains_score_threshold_rejections() -> None:
    config = load_strategy_config(CONFIG_PATH)
    panel, regime = _candidate_scoring_fixture()
    scored = score_candidates(panel, regime, config).sort_values("symbol").reset_index(drop=True)

    candidates = swing_candidates_from_scored_frame(scored, config)
    rejected = {candidate.symbol: candidate for candidate in candidates if not candidate.eligible}

    assert set(rejected) == {"BBB", "CCC"}
    assert "SCORE_BELOW_EFFECTIVE_THRESHOLD" in {
        reason.code for reason in rejected["BBB"].rejection_reasons
    }
    assert rejected["BBB"].quality_score is None
    assert rejected["BBB"].ranking is None


def test_scored_frame_adapter_records_earnings_window_rejection() -> None:
    config = load_strategy_config(CONFIG_PATH)
    panel, regime = _candidate_scoring_fixture()
    panel.loc[0, "regular_closes_until_earnings_event"] = 1
    scored = score_candidates(panel, regime, config).sort_values("symbol").reset_index(drop=True)

    candidates = swing_candidates_from_scored_frame(scored, config)
    aaa = next(candidate for candidate in candidates if candidate.symbol == "AAA")

    assert aaa.eligible is False
    assert "EVENT_EARNINGS_WINDOW_BLOCKED" in {
        reason.code for reason in aaa.rejection_reasons
    }


def test_scored_frame_adapter_fails_fast_on_missing_required_column() -> None:
    config = load_strategy_config(CONFIG_PATH)
    panel, regime = _candidate_scoring_fixture()
    scored = score_candidates(panel, regime, config).drop(columns=["candidate_score_pct"])

    with pytest.raises(ValueError, match="candidate_score_pct"):
        swing_candidates_from_scored_frame(scored, config)


def test_setup_snapshot_adapter_builds_approved_swing_signal() -> None:
    config = load_strategy_config(CONFIG_PATH)
    setup = _setup_snapshot(config)
    panel, regime = _candidate_scoring_fixture()
    scored = score_candidates(panel, regime, config)
    candidate = next(
        candidate
        for candidate in swing_candidates_from_scored_frame(scored, config)
        if candidate.symbol == "AAA"
    )

    signal = swing_signal_from_setup_snapshot(
        setup,
        config,
        candidate_id=candidate.candidate_id,
        quality_score=candidate.quality_score,
        regime_state=RegimeState.RISK_ON,
    )

    assert signal.approved is True
    assert signal.signal_id == "signal:RF_TPC_V2:AAA:2026-04-23:setup-aaa"
    assert signal.setup_id == "setup-aaa"
    assert signal.entry_trigger == setup.entry_trigger
    assert signal.entry_limit == setup.entry_limit
    assert signal.initial_stop == setup.initial_stop
    assert signal.per_share_risk == setup.per_share_risk


def test_setup_snapshot_adapter_builds_rejected_swing_signal() -> None:
    config = load_strategy_config(CONFIG_PATH)
    setup = _setup_snapshot(config)
    score = next(
        candidate.quality_score
        for candidate in swing_candidates_from_scored_frame(
            score_candidates(*_candidate_scoring_fixture(), config),
            config,
        )
        if candidate.symbol == "AAA"
    )

    signal = swing_signal_from_setup_snapshot(
        setup,
        config,
        candidate_id="candidate:RF_TPC_V2:AAA:2026-04-23",
        quality_score=score,
        regime_state=RegimeState.RISK_ON,
        approved=False,
    )

    assert signal.approved is False
    assert signal.setup_id is None
    assert signal.quality_score is None
    assert "SETUP_NOT_APPROVED" in {reason.code for reason in signal.rejection_reasons}


def test_entry_plan_adapter_builds_approved_risk_and_order_plans() -> None:
    config = load_strategy_config(CONFIG_PATH)
    entry_plan = _entry_plan(config)
    signal_id = "signal:RF_TPC_V2:AAA:2026-04-23:setup-aaa"

    risk_plan = swing_risk_plan_from_entry_plan(entry_plan, config, signal_id=signal_id)
    order_plan = swing_order_plan_from_entry_plan(
        entry_plan,
        config,
        signal_id=signal_id,
        risk_plan_id=risk_plan.risk_plan_id,
    )

    assert risk_plan.approved is True
    assert risk_plan.quantity == 50
    assert risk_plan.base_risk_budget == 300.0
    assert {constraint.constraint_id for constraint in risk_plan.constraints} == {
        "portfolio.heat",
        "portfolio.daily_new_risk",
        "portfolio.sector_exposure",
    }
    assert all(constraint.passed for constraint in risk_plan.constraints)
    assert order_plan.approved is True
    assert order_plan.quantity == 50
    assert order_plan.stop_price == entry_plan.setup.entry_trigger
    assert order_plan.limit_price == entry_plan.setup.entry_limit
    assert order_plan.dedupe_key == "RF_TPC_V2:AAA:setup-aaa"


def test_entry_plan_adapter_builds_rejected_risk_and_order_plans() -> None:
    config = load_strategy_config(CONFIG_PATH)
    entry_plan = _entry_plan(config, approved=False)
    signal_id = "signal:RF_TPC_V2:AAA:2026-04-23:setup-aaa"

    risk_plan = swing_risk_plan_from_entry_plan(entry_plan, config, signal_id=signal_id)
    order_plan = swing_order_plan_from_entry_plan(
        entry_plan,
        config,
        signal_id=signal_id,
        risk_plan_id=risk_plan.risk_plan_id,
    )

    assert risk_plan.approved is False
    assert risk_plan.quantity == 0
    assert "PORTFOLIO_HEAT_LIMIT" in {
        constraint.reason.code
        for constraint in risk_plan.constraints
        if constraint.reason is not None
    }
    assert "PORTFOLIO_HEAT_LIMIT_BREACHED" in {
        reason.code for reason in risk_plan.rejection_reasons
    }
    assert order_plan.approved is False
    assert order_plan.quantity == 0
    assert "PORTFOLIO_HEAT_LIMIT_BREACHED" in {
        reason.code for reason in order_plan.rejection_reasons
    }


def test_lifecycle_adapter_builds_reportable_transition() -> None:
    occurred_at = datetime(2026, 4, 24, 14, 30, tzinfo=UTC)

    transition = swing_lifecycle_transition_from_states(
        symbol="AAA",
        occurred_at=occurred_at,
        from_state=SymbolLifecycleState.PENDING_ENTRY,
        to_state=SymbolLifecycleState.ACTIVE,
        evidence={"fill_price": 101.0},
    )

    assert transition.transition_id == (
        "transition:AAA:PENDING_ENTRY:ACTIVE:2026-04-24T14:30:00+00:00"
    )
    assert transition.symbol == "AAA"
    assert transition.from_state == SymbolLifecycleState.PENDING_ENTRY
    assert transition.to_state == SymbolLifecycleState.ACTIVE
    assert transition.evidence == {"fill_price": 101.0}


def test_exit_decision_adapter_builds_hold_and_exit_decisions() -> None:
    config = load_strategy_config(CONFIG_PATH)

    hold = swing_exit_decision_from_values(
        config,
        symbol="AAA",
        session_date=date(2026, 4, 25),
        current_stop=98.0,
        updated_stop=99.0,
        exit_required=False,
        evidence={"reason": "trail tightened but no exit"},
    )
    exit_decision = swing_exit_decision_from_values(
        config,
        symbol="AAA",
        session_date=date(2026, 4, 26),
        current_stop=99.0,
        updated_stop=100.0,
        exit_required=True,
        order_reason=OrderReason.TIME_EXIT,
        evidence={"bars_without_progress": 10},
    )

    assert hold.exit_required is False
    assert hold.order_reason is None
    assert hold.updated_stop == 99.0
    assert exit_decision.exit_required is True
    assert exit_decision.order_reason == OrderReason.TIME_EXIT
    assert exit_decision.config_hash == config.config_hash()
