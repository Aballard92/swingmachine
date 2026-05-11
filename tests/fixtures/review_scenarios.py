from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

import pandas as pd

from swingmachine.broker import PaperBrokerAdapter
from swingmachine.config import load_strategy_config
from swingmachine.contracts import RuntimeCycleInput, SetupSnapshot
from swingmachine.entries import build_setup_snapshot
from swingmachine.enums import (
    BrokerOrderStatus,
    PatternType,
    RegimeState,
    RuntimeEventType,
    RuntimeMode,
)
from swingmachine.runtime import (
    build_paper_shadow_audit_service,
    build_runtime,
    build_runtime_run_history,
)
from swingmachine.shadow import compare_runtime_cycle_shadow_fills
from swingmachine.shadow_reviews import ShadowReviewService
from swingmachine.storage import create_database_engine, create_session_factory, initialize_database

ReviewScenarioName = Literal["pass", "warn", "fail"]
REVIEW_SCENARIO_AS_OF_DATE = date(2026, 4, 24)
REVIEW_SCENARIO_LOOKBACK_DAYS = (5, 10)


@dataclass(frozen=True)
class ReviewScenarioCase:
    setup_id: str
    symbol: str
    session_date: str
    as_of: str
    last_data_at: str
    expires_at: str
    market_session_date: str
    broker_status: BrokerOrderStatus | None
    market_symbol: str | None = None
    raw_open: float = 100.3
    raw_high: float = 101.0
    raw_low: float = 99.7
    raw_close: float = 100.5
    spread_bps: float = 0.0
    fx_conversion_cost_bps: float = 0.0


def seed_review_scenario_history(
    *,
    database_url: str,
    scenario_name: ReviewScenarioName,
) -> None:
    cases = _scenario_cases(scenario_name)
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    runtime = build_runtime(config, database_url=database_url)
    engine = create_database_engine(database_url)
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    shadow_review_service = ShadowReviewService(session_factory)

    for case in cases:
        cycle_input = RuntimeCycleInput(
            as_of=case.as_of,
            regime_state=RegimeState.RISK_ON,
            equity=100_000.0,
            last_data_at=case.last_data_at,
            expires_at=case.expires_at,
            setups=(
                _setup_snapshot(
                    case.setup_id,
                    symbol=case.symbol,
                    session_date=case.session_date,
                ),
            ),
        )
        shadow_result = runtime.run_cycle(cycle_input, mode=RuntimeMode.SHADOW)
        runtime.run_cycle(cycle_input, mode=RuntimeMode.PAPER)

        comparison_batch = compare_runtime_cycle_shadow_fills(
            shadow_result,
            market_data=_market_data(case),
            config=config,
        )
        shadow_review_service.record_comparison_batch(comparison_batch)

    audit_service = build_paper_shadow_audit_service(database_url=database_url)
    records_by_setup = {record.setup_id: record for record in audit_service.load_records()}
    broker = PaperBrokerAdapter(session_factory)
    for case in cases:
        if case.broker_status is None:
            continue
        broker_order_id = records_by_setup[case.setup_id].broker_order_id
        assert broker_order_id is not None
        broker.update_order_status(broker_order_id, status=case.broker_status)

    audit_service.record_snapshot_batch(
        audit_service.load_records(),
        recorded_at=datetime(2026, 4, 24, 16, 30),
    )

    run_history = build_runtime_run_history(database_url=database_url)
    run_id = run_history.record_run(
        command=f"seed-review-scenario-{scenario_name}",
        status="SUCCEEDED",
        started_at=datetime(2026, 4, 24, 16, 20),
        completed_at=datetime(2026, 4, 24, 16, 21),
        metrics={"scenario": scenario_name, "case_count": len(cases)},
    )
    for case in cases:
        run_history.record_event(
            command=f"seed-review-scenario-{scenario_name}",
            event_type=RuntimeEventType.PAPER_ENTRY_SUBMISSION_DECIDED,
            occurred_at=datetime.fromisoformat(case.as_of),
            run_id=run_id,
            mode=RuntimeMode.PAPER,
            symbol=case.symbol,
            setup_id=case.setup_id,
            payload={"submitted": True, "scenario": scenario_name},
        )


def _setup_snapshot(
    setup_id: str,
    *,
    symbol: str,
    session_date: str,
) -> SetupSnapshot:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    return build_setup_snapshot(
        {
            "symbol": symbol,
            "session_date": session_date,
            "pattern_type": PatternType.PULLBACK.value,
            "setup_id": setup_id,
            "setup_start_date": session_date,
            "setup_end_date": session_date,
            "setup_high": 100.0,
            "setup_low": 94.0,
            "setup_high_date": session_date,
            "setup_low_date": session_date,
            "atr_14": 2.0,
            "setup_valid": True,
        },
        config,
    )


def _market_data(case: ReviewScenarioCase) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": [case.market_symbol or case.symbol],
            "session_date": [case.market_session_date],
            "raw_open": [case.raw_open],
            "raw_high": [case.raw_high],
            "raw_low": [case.raw_low],
            "raw_close": [case.raw_close],
            "raw_volume": [1_000_000_000_000.0],
            "spread_bps": [case.spread_bps],
            "fx_conversion_cost_bps": [case.fx_conversion_cost_bps],
        }
    )


def _scenario_cases(scenario_name: ReviewScenarioName) -> tuple[ReviewScenarioCase, ...]:
    base = (
        ReviewScenarioCase(
            setup_id=f"setup-review-{scenario_name}-aaa",
            symbol="AAA",
            session_date="2026-04-20",
            as_of="2026-04-21T16:05:00",
            last_data_at="2026-04-21T16:04:00",
            expires_at="2026-04-22T16:00:00",
            market_session_date="2026-04-22",
            broker_status=BrokerOrderStatus.FILLED,
        ),
        ReviewScenarioCase(
            setup_id=f"setup-review-{scenario_name}-bbb",
            symbol="BBB",
            session_date="2026-04-21",
            as_of="2026-04-22T16:05:00",
            last_data_at="2026-04-22T16:04:00",
            expires_at="2026-04-23T16:00:00",
            market_session_date="2026-04-23",
            broker_status=BrokerOrderStatus.FILLED,
        ),
        ReviewScenarioCase(
            setup_id=f"setup-review-{scenario_name}-ccc",
            symbol="CCC",
            session_date="2026-04-22",
            as_of="2026-04-23T16:05:00",
            last_data_at="2026-04-23T16:04:00",
            expires_at="2026-04-24T16:00:00",
            market_session_date="2026-04-24",
            broker_status=BrokerOrderStatus.FILLED,
        ),
    )

    if scenario_name == "pass":
        return base

    if scenario_name == "warn":
        return (
            base[0],
            base[1],
            ReviewScenarioCase(
                setup_id="setup-review-warn-ccc",
                symbol="CCC",
                session_date="2026-04-22",
                as_of="2026-04-23T16:05:00",
                last_data_at="2026-04-23T16:04:00",
                expires_at="2026-04-24T16:00:00",
                market_session_date="2026-04-24",
                broker_status=None,
            ),
        )

    return (
        base[0],
        base[1],
        ReviewScenarioCase(
            setup_id="setup-review-fail-ccc",
            symbol="CCC",
            session_date="2026-04-22",
            as_of="2026-04-23T16:05:00",
            last_data_at="2026-04-23T16:04:00",
            expires_at="2026-04-24T16:00:00",
            market_session_date="2026-04-24",
            broker_status=None,
            market_symbol="ZZZ",
        ),
    )
