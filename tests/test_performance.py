from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from swingmachine import data_contracts
from swingmachine.performance import (
    build_historical_performance_report,
    build_provider_performance_comparison_report,
    load_benchmark_price_rows_from_manifest,
    write_historical_performance_report,
    write_provider_performance_comparison_report,
)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_lifecycle_artifacts(path: Path) -> None:
    path.mkdir()
    _write_json(
        path / "portfolio_lifecycle_replay_summary.json",
        {
            "panel_id": "test-panel",
            "initial_equity": 100_000.0,
            "final_equity": 102_000.0,
        },
    )
    _write_json(
        path / "portfolio_lifecycle_session_states.json",
        {
            "panel_id": "test-panel",
            "session_states": [
                {
                    "session_date": "2026-01-02",
                    "equity": 100_000.0,
                    "cash": 100_000.0,
                    "open_position_count": 0,
                    "pending_entry_count": 0,
                    "portfolio_heat": 0.0,
                    "daily_new_risk": 0.0,
                    "sector_exposure": {},
                },
                {
                    "session_date": "2026-01-05",
                    "equity": 98_000.0,
                    "cash": 98_000.0,
                    "open_position_count": 1,
                    "pending_entry_count": 0,
                    "portfolio_heat": 0.003,
                    "daily_new_risk": 300.0,
                    "sector_exposure": {"TECH": 4_000.0},
                },
                {
                    "session_date": "2026-01-06",
                    "equity": 102_000.0,
                    "cash": 102_000.0,
                    "open_position_count": 0,
                    "pending_entry_count": 1,
                    "portfolio_heat": 0.0,
                    "daily_new_risk": 0.0,
                    "sector_exposure": {},
                },
            ],
        },
    )
    _write_json(
        path / "portfolio_lifecycle_positions.json",
        {
            "panel_id": "test-panel",
            "positions": [
                {
                    "position_id": "AAA:1",
                    "symbol": "AAA",
                    "state": "CLOSED",
                    "entry_price": 100.0,
                    "market_price": 110.0,
                    "quantity": 10.0,
                    "session_date": "2026-01-06",
                },
                {
                    "position_id": "BBB:1",
                    "symbol": "BBB",
                    "state": "CLOSED",
                    "entry_price": 50.0,
                    "market_price": 45.0,
                    "quantity": 10.0,
                    "session_date": "2026-01-06",
                },
            ],
        },
    )


def _write_trade_ledger_artifact(path: Path) -> None:
    _write_json(
        path / "portfolio_lifecycle_trade_ledger.json",
        {
            "panel_id": "test-panel",
            "trades": [
                {
                    "trade_id": "AAA:setup:2026-01-06:1",
                    "symbol": "AAA",
                    "setup_id": "setup",
                    "position_id": "AAA:setup:2026-01-05:1",
                    "entry_signal_date": "2026-01-02",
                    "entry_fill_date": "2026-01-05",
                    "exit_fill_date": "2026-01-06",
                    "entry_reference_price": 100.0,
                    "entry_fill_price": 100.0,
                    "exit_reference_price": 110.0,
                    "exit_fill_price": 110.0,
                    "quantity": 10,
                    "entry_regime_state": "RISK_ON",
                    "exit_regime_state": "RISK_ON",
                    "exit_reason": "TRAIL_STOP",
                    "bars_held": 1,
                    "initial_stop": 95.0,
                    "final_stop": 100.0,
                    "entry_transaction_cost": 1.0,
                    "exit_transaction_cost": 1.5,
                    "total_transaction_cost": 2.5,
                    "gross_pnl": 100.0,
                    "gross_return": 0.10,
                    "net_pnl": 97.5,
                    "net_return": 0.0975,
                    "sector": "TECH",
                    "source": "BACKTEST_TRADE",
                }
            ],
        },
    )


def _write_attribution_artifact(path: Path) -> Path:
    attribution_path = path / "scanner_material_decisions.json"
    _write_json(
        attribution_path,
        {
            "panel_id": "test-panel",
            "sessions": [
                {
                    "material_decision_rows": [
                        {
                            "setup_id": "setup",
                            "decision": "ACCEPTED_SETUP",
                            "pattern_type": "PULLBACK",
                            "candidate_score_pct": 0.975,
                            "rank": None,
                        }
                    ]
                }
            ],
        },
    )
    return attribution_path


def test_build_historical_performance_report_from_lifecycle_artifacts(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "lifecycle"
    _write_lifecycle_artifacts(artifact_dir)

    report = build_historical_performance_report(
        artifact_dir,
        run_id="unit-run",
        benchmark_symbol="SPY",
        benchmark_price_rows=[
            {"session_date": "2026-01-02", "close": 100.0},
            {"session_date": "2026-01-05", "close": 101.0},
            {"session_date": "2026-01-06", "close": 104.0},
        ],
    )

    assert report.summary.panel_id == "test-panel"
    assert report.summary.run_id == "unit-run"
    assert report.summary.total_return == pytest.approx(0.02)
    assert report.summary.max_drawdown == pytest.approx(-0.02)
    assert report.summary.trade_metrics.closed_trade_count == 2
    assert report.summary.trade_metrics.winning_trade_count == 1
    assert report.summary.trade_metrics.losing_trade_count == 1
    assert report.summary.trade_metrics.net_pnl == pytest.approx(50.0)
    assert report.summary.concentration.max_open_position_count == 1
    assert report.summary.concentration.max_pending_entry_count == 1
    assert report.summary.concentration.max_single_sector_exposure_sector == "TECH"
    assert report.summary.benchmark_comparison is not None
    assert report.summary.benchmark_comparison.benchmark_total_return == pytest.approx(0.04)
    assert report.summary.benchmark_comparison.excess_return == pytest.approx(-0.02)
    assert report.summary.cost_sensitivity.estimated_turnover == pytest.approx(3_050.0)
    high_cost = report.summary.cost_sensitivity.scenarios[-1]
    assert high_cost.scenario_id == "additional_50bps"
    assert high_cost.estimated_total_additional_cost == pytest.approx(15.25)
    assert high_cost.estimated_final_equity == pytest.approx(101_984.75)
    assert report.summary.breakdown.monthly_returns["2026-01"] == pytest.approx(0.02)
    assert len(report.equity_curve) == 3
    assert report.equity_curve[1].drawdown == pytest.approx(-0.02)
    assert len(report.drawdown_records) == 1
    assert report.drawdown_records[0].recovered is True


def test_write_historical_performance_report_outputs_review_artifacts(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "lifecycle"
    output_dir = tmp_path / "performance"
    _write_lifecycle_artifacts(artifact_dir)
    report = build_historical_performance_report(artifact_dir)

    paths = write_historical_performance_report(report, output_dir)

    assert set(paths) == {"summary", "equity_curve", "drawdowns", "report"}
    assert json.loads((output_dir / "historical_performance_summary.json").read_text())[
        "panel_id"
    ] == "test-panel"
    assert json.loads((output_dir / "historical_equity_curve.json").read_text())[0][
        "equity"
    ] == 100_000.0


def test_build_historical_performance_report_prefers_trade_ledger(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "lifecycle"
    _write_lifecycle_artifacts(artifact_dir)
    _write_trade_ledger_artifact(artifact_dir)

    report = build_historical_performance_report(artifact_dir)

    assert report.summary.status.value == "PASS"
    assert report.summary.trade_metrics.source == "TRADE_LEDGER"
    assert report.summary.trade_metrics.closed_trade_count == 1
    assert report.summary.trade_metrics.net_pnl == pytest.approx(97.5)
    assert report.summary.trade_metrics.total_transaction_cost == pytest.approx(2.5)
    assert report.summary.cost_sensitivity.cost_source == "TRADE_LEDGER"
    assert report.summary.cost_sensitivity.estimated_turnover == pytest.approx(2_100.0)
    assert report.summary.breakdown.by_entry_regime["RISK_ON"].net_pnl == pytest.approx(
        97.5
    )
    assert report.summary.breakdown.by_exit_reason["TRAIL_STOP"].trade_count == 1
    assert report.summary.breakdown.by_sector["TECH"].total_transaction_cost == pytest.approx(
        2.5
    )
    assert "ranking_bucket" in report.summary.breakdown.missing_breakdowns
    assert report.summary.warnings == ()


def test_build_historical_performance_report_applies_trade_attribution(
    tmp_path: Path,
) -> None:
    artifact_dir = tmp_path / "lifecycle"
    _write_lifecycle_artifacts(artifact_dir)
    _write_trade_ledger_artifact(artifact_dir)
    attribution_path = _write_attribution_artifact(tmp_path)

    report = build_historical_performance_report(
        artifact_dir,
        attribution_path=attribution_path,
    )

    assert report.summary.breakdown.by_setup_type["PULLBACK"].trade_count == 1
    assert report.summary.breakdown.by_ranking_bucket["score_95_100"].net_pnl == pytest.approx(
        97.5
    )
    assert report.summary.breakdown.missing_breakdowns == ()


def test_load_benchmark_price_rows_from_manifest_prefers_feature_prices(monkeypatch) -> None:
    class Panel:
        ohlcv = pd.DataFrame(
            {
                "symbol": ["SPY", "SPY"],
                "session_date": ["2026-01-02", "2026-01-05"],
                "raw_close": [99.0, 101.0],
            }
        )
        features = pd.DataFrame(
            {
                "symbol": ["SPY", "SPY", "QQQ"],
                "session_date": ["2026-01-02", "2026-01-05", "2026-01-05"],
                "split_adj_close": [100.0, 104.0, 200.0],
            }
        )

    monkeypatch.setattr(data_contracts, "load_historical_panel_data", lambda _: Panel())

    rows = load_benchmark_price_rows_from_manifest("manifest.yaml", "SPY")

    assert rows == [
        {"session_date": "2026-01-02", "close": 100.0},
        {"session_date": "2026-01-05", "close": 104.0},
    ]


def test_build_provider_performance_comparison_report(tmp_path: Path) -> None:
    left = {
        "panel_id": "window",
        "status": "PASS",
        "start_date": "2026-01-02",
        "end_date": "2026-01-31",
        "session_count": 20,
        "total_return": 0.04,
        "max_drawdown": -0.02,
        "trade_metrics": {"closed_trade_count": 3, "net_pnl": 400.0},
        "benchmark_comparison": {"benchmark_total_return": 0.03, "excess_return": 0.01},
        "warnings": [],
    }
    right = {
        **left,
        "total_return": 0.01,
        "max_drawdown": -0.03,
        "trade_metrics": {"closed_trade_count": 2, "net_pnl": 100.0},
        "benchmark_comparison": {"benchmark_total_return": 0.03, "excess_return": -0.02},
    }
    left_path = tmp_path / "alpaca_summary.json"
    right_path = tmp_path / "hf_summary.json"
    output_path = tmp_path / "comparison.json"
    _write_json(left_path, left)
    _write_json(right_path, right)

    report = build_provider_performance_comparison_report(
        left_summary_path=left_path,
        right_summary_path=right_path,
        left_provider="alpaca",
        right_provider="huggingface",
    )
    written = write_provider_performance_comparison_report(report, output_path)

    assert report.status.value == "PASS"
    assert report.total_return_delta == pytest.approx(0.03)
    assert report.closed_trade_count_delta == 1
    assert report.net_pnl_delta == pytest.approx(300.0)
    assert report.excess_return_delta == pytest.approx(0.03)
    assert written == str(output_path)
