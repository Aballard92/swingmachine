from __future__ import annotations

from pathlib import Path

import pandas as pd

from swingmachine.overnight_qualification import (
    build_overnight_qualification_evidence_summary,
    check_selected_period_dry_run_safety,
    run_selected_period_data_smoke,
)


def test_overnight_evidence_summary_keeps_serious_run_blocked(tmp_path: Path) -> None:
    report_root = tmp_path / "reports"
    report_root.mkdir()
    _write_json(report_root / "trading212_alpaca_data_input_preflight.json", {"passed": True})
    _write_json(
        report_root / "trading212_alpaca_selected_period_preflight.json", {"passed": True}
    )
    _write_json(
        report_root / "trading212_provider_panel_drift_report.json", {"passed": False}
    )

    summary = build_overnight_qualification_evidence_summary(report_root)

    assert summary.data_input_gate_passed is True
    assert summary.selected_period_preflight_passed is True
    assert summary.provider_drift_passed is False
    assert summary.serious_full_run_allowed is False
    assert "provider_panel_drift_not_resolved_hf_comparison_only" in summary.blockers


def test_selected_period_data_smoke_validates_contract_files(tmp_path: Path) -> None:
    selected_plan = tmp_path / "selected_periods.yaml"
    selected_plan.write_text(
        """
baseline_id: swing_machine_v0_1
plan_version: swing_machine_v0_1_selected_period_plan_v1
profile_alias_path: profile.yaml
required_data_contract_version: prepared_market_and_historical_panel_v1
run_policy: DRY_RUN_REPLAY_ONLY
serious_full_run_policy: PROHIBITED_UNTIL_QUALIFIED
periods:
  - period_id: smoke_recent_5_sessions
    title: Fixture smoke
    start_date: 2026-04-20
    end_date: 2026-04-24
    purpose: test
    minimum_session_count: 1
    maximum_symbol_count: 2
""",
        encoding="utf-8",
    )
    period_root = tmp_path / "data" / "smoke_recent_5_sessions"
    period_root.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "symbol": "AAA",
                "session_date": "2026-04-20",
                "raw_open": 10.0,
                "raw_high": 11.0,
                "raw_low": 9.0,
                "raw_close": 10.5,
                "raw_volume": 1000.0,
            }
        ]
    ).to_parquet(period_root / "ohlcv.parquet", index=False)
    pd.DataFrame(
        [
            {
                "symbol": "AAA",
                "asset_type": "COMMON_STOCK",
                "exchange": "UNKNOWN",
                "currency": "USD",
                "sector": "UNKNOWN",
                "is_tradable": True,
            }
        ]
    ).to_csv(period_root / "symbol_reference.csv", index=False)
    pd.DataFrame(columns=["symbol", "ex_date", "split_ratio", "cash_dividend_per_share"]).to_csv(
        period_root / "corporate_actions.csv", index=False
    )
    pd.DataFrame(columns=["symbol", "event_date", "event_session"]).to_csv(
        period_root / "earnings_events.csv", index=False
    )
    input_plan = tmp_path / "input_plan.yaml"
    input_plan.write_text(
        f"""
baseline_id: swing_machine_v0_1
plan_version: swing_machine_v0_1_data_input_plan_v1
selected_period_plan_path: {selected_plan}
periods:
  - period_id: smoke_recent_5_sessions
    ohlcv_path: {period_root / 'ohlcv.parquet'}
    symbol_reference_path: {period_root / 'symbol_reference.csv'}
    corporate_actions_path: {period_root / 'corporate_actions.csv'}
    earnings_events_path: {period_root / 'earnings_events.csv'}
""",
        encoding="utf-8",
    )

    report = run_selected_period_data_smoke(input_plan)

    assert report.passed is True
    assert report.broker_execution_allowed is False
    assert report.periods[0].qualification_session_count == 1


def test_dry_run_safety_keeps_freeze_blocked() -> None:
    report = check_selected_period_dry_run_safety()

    assert report.passed is True
    assert report.broker_execution_allowed is False
    assert report.live_order_actions_allowed is False
    assert report.paper_order_actions_allowed is False
    assert report.serious_full_run_allowed is False
    assert report.freeze_decision == "BLOCK"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")
