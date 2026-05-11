from __future__ import annotations

from datetime import date

import pandas as pd

from swingmachine.backtest import run_backtest
from swingmachine.config import load_strategy_config
from swingmachine.contracts import BacktestEvent
from swingmachine.enums import OrderReason, PatternType, RegimeState, SymbolLifecycleState
from swingmachine.research import (
    apply_config_overrides,
    backtest_result_fingerprint,
    build_walk_forward_windows,
    candidate_ranking_fingerprint,
    duplicate_entry_submission_keys,
    repeated_backtest_is_identical,
    repeated_candidate_ranking_is_identical,
    run_parameter_sweep,
    run_walk_forward_study,
)


def _ranking_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
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


def _backtest_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2026-04-20", periods=4)
    panel = pd.DataFrame(
        {
            "symbol": ["AAA"] * len(dates),
            "session_date": list(dates),
            "pattern_type": [PatternType.PULLBACK.value] + [None] * (len(dates) - 1),
            "setup_id": ["setup-research-1"] + [None] * (len(dates) - 1),
            "setup_start_date": [dates[0]] + [pd.NaT] * (len(dates) - 1),
            "setup_end_date": [dates[0]] + [pd.NaT] * (len(dates) - 1),
            "setup_high": [100.0] + [float("nan")] * (len(dates) - 1),
            "setup_low": [94.0] + [float("nan")] * (len(dates) - 1),
            "setup_high_date": [dates[0]] + [pd.NaT] * (len(dates) - 1),
            "setup_low_date": [dates[0]] + [pd.NaT] * (len(dates) - 1),
            "setup_valid": [True] + [False] * (len(dates) - 1),
            "is_candidate": [True] + [False] * (len(dates) - 1),
            "entry_enabled": [True] * len(dates),
            "split_adj_close": [100.0, 100.5, 101.2, 101.1],
            "ma50": [90.0] * len(dates),
            "ma200": [80.0] * len(dates),
            "ma200_slope_pct20": [0.02] * len(dates),
            "dist_to_52w_high": [0.03] * len(dates),
            "raw_open": [99.8, 100.3, 101.2, 101.0],
            "raw_high": [100.2, 101.0, 101.5, 101.3],
            "raw_low": [99.5, 99.7, 100.8, 100.9],
            "raw_close": [100.0, 100.5, 101.2, 101.1],
            "raw_volume": [1_000_000_000_000.0] * len(dates),
            "atr_14": [2.0] * len(dates),
            "regular_closes_until_earnings_event": [10, 1, 0, 0],
            "candidate_score_pct": [1.0, 0.0, 0.0, 0.0],
            "spread_bps": [0.0] * len(dates),
            "fx_conversion_cost_bps": [0.0] * len(dates),
            "sector": ["TECH"] * len(dates),
        }
    )
    regime = pd.DataFrame(
        {
            "session_date": dates,
            "regime_state": [RegimeState.RISK_ON.value] * len(dates),
            "entry_enabled": [True] * len(dates),
        }
    )
    return panel, regime


def _walkforward_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2026-04-20", periods=6)
    panel = pd.DataFrame(
        {
            "symbol": ["AAA"] * len(dates),
            "session_date": list(dates),
            "pattern_type": [None, None, PatternType.PULLBACK.value, None, None, None],
            "setup_id": [None, None, "setup-wf-1", None, None, None],
            "setup_start_date": [pd.NaT, pd.NaT, dates[2], pd.NaT, pd.NaT, pd.NaT],
            "setup_end_date": [pd.NaT, pd.NaT, dates[2], pd.NaT, pd.NaT, pd.NaT],
            "setup_high": [
                float("nan"),
                float("nan"),
                100.0,
                float("nan"),
                float("nan"),
                float("nan"),
            ],
            "setup_low": [
                float("nan"),
                float("nan"),
                94.0,
                float("nan"),
                float("nan"),
                float("nan"),
            ],
            "setup_high_date": [pd.NaT, pd.NaT, dates[2], pd.NaT, pd.NaT, pd.NaT],
            "setup_low_date": [pd.NaT, pd.NaT, dates[2], pd.NaT, pd.NaT, pd.NaT],
            "setup_valid": [False, False, True, False, False, False],
            "is_candidate": [False, False, True, False, False, False],
            "entry_enabled": [True] * len(dates),
            "split_adj_close": [99.0, 99.4, 100.0, 100.5, 101.2, 101.1],
            "ma50": [90.0] * len(dates),
            "ma200": [80.0] * len(dates),
            "ma200_slope_pct20": [0.02] * len(dates),
            "dist_to_52w_high": [0.03] * len(dates),
            "raw_open": [98.8, 99.2, 99.8, 100.3, 101.2, 101.0],
            "raw_high": [99.3, 99.5, 100.2, 101.0, 101.5, 101.3],
            "raw_low": [98.6, 99.0, 99.5, 99.7, 100.8, 100.9],
            "raw_close": [99.0, 99.4, 100.0, 100.5, 101.2, 101.1],
            "raw_volume": [1_000_000_000_000.0] * len(dates),
            "atr_14": [2.0] * len(dates),
            "regular_closes_until_earnings_event": [10, 10, 10, 1, 0, 0],
            "candidate_score_pct": [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
            "spread_bps": [0.0] * len(dates),
            "fx_conversion_cost_bps": [0.0] * len(dates),
            "sector": ["TECH"] * len(dates),
        }
    )
    regime = pd.DataFrame(
        {
            "session_date": dates,
            "regime_state": [RegimeState.RISK_ON.value] * len(dates),
            "entry_enabled": [True] * len(dates),
        }
    )
    return panel, regime


def test_build_walk_forward_windows_supports_anchored_expanding_windows() -> None:
    dates = pd.bdate_range("2026-01-05", periods=10)

    windows = build_walk_forward_windows(
        dates,
        train_sessions=4,
        test_sessions=2,
        step_sessions=2,
        anchored=True,
    )

    assert [window.train_sessions for window in windows] == [4, 6, 8]
    assert windows[0].train_start_date == dates[0].date()
    assert windows[0].test_start_date == dates[4].date()
    assert windows[-1].test_end_date == dates[9].date()


def test_build_walk_forward_windows_supports_rolling_windows() -> None:
    dates = pd.bdate_range("2026-01-05", periods=10)

    windows = build_walk_forward_windows(
        dates,
        train_sessions=4,
        test_sessions=2,
        step_sessions=2,
        anchored=False,
    )

    assert [window.train_start_date for window in windows] == [
        dates[0].date(),
        dates[2].date(),
        dates[4].date(),
    ]
    assert [window.test_start_date for window in windows] == [
        dates[4].date(),
        dates[6].date(),
        dates[8].date(),
    ]


def test_candidate_ranking_fingerprint_is_reproducible() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    panel, regime = _ranking_panel()

    first = candidate_ranking_fingerprint(panel, regime, config)
    second = candidate_ranking_fingerprint(panel, regime, config)

    assert first == second
    assert repeated_candidate_ranking_is_identical(panel, regime, config) is True


def test_apply_config_overrides_updates_nested_values() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")

    updated = apply_config_overrides(
        config,
        {
            "risk.risk_per_trade_pct_equity": 0.004,
            "entry.order_expiry_sessions": 2,
        },
    )

    assert updated.risk.risk_per_trade_pct_equity == 0.004
    assert updated.entry.order_expiry_sessions == 2
    assert updated.config_hash() != config.config_hash()


def test_backtest_fingerprint_is_reproducible_and_has_no_duplicate_entry_submissions() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    panel, regime = _backtest_panel()

    first = run_backtest(panel, regime, config)
    second = run_backtest(panel, regime, config)

    assert backtest_result_fingerprint(first) == backtest_result_fingerprint(second)
    assert repeated_backtest_is_identical(panel, regime, config) is True
    assert duplicate_entry_submission_keys(first.events) == ()


def test_run_parameter_sweep_reflects_config_override_effects() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    panel, regime = _backtest_panel()

    results = run_parameter_sweep(
        panel,
        regime,
        config,
        [
            {"risk.risk_per_trade_pct_equity": 0.001},
            {"risk.risk_per_trade_pct_equity": 0.006},
        ],
    )

    assert len(results) == 2
    assert results[0].trade_count == 1
    assert results[1].trade_count == 1
    assert results[1].net_pnl > results[0].net_pnl
    assert results[0].config_hash != results[1].config_hash


def test_run_walk_forward_study_is_deterministic() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    panel, regime = _walkforward_panel()

    first = run_walk_forward_study(
        panel,
        regime,
        config,
        train_sessions=2,
        test_sessions=4,
        anchored=True,
    )
    second = run_walk_forward_study(
        panel,
        regime,
        config,
        train_sessions=2,
        test_sessions=4,
        anchored=True,
    )

    assert [item.model_dump(mode="json") for item in first] == [
        item.model_dump(mode="json") for item in second
    ]
    assert len(first) == 1
    assert first[0].window.train_sessions == 2
    assert first[0].window.test_sessions == 4
    assert first[0].trade_count == 1
    assert first[0].backtest_fingerprint != ""


def test_duplicate_entry_submission_keys_detect_repeated_setup_submission() -> None:
    events = (
        BacktestEvent(
            session_date=date(2026, 4, 20),
            symbol="AAA",
            event_type="ENTRY_SUBMITTED",
            setup_id="dup-1",
            state=SymbolLifecycleState.PENDING_ENTRY,
            order_reason=OrderReason.ENTRY,
        ),
        BacktestEvent(
            session_date=date(2026, 4, 21),
            symbol="AAA",
            event_type="ENTRY_SUBMITTED",
            setup_id="dup-1",
            state=SymbolLifecycleState.PENDING_ENTRY,
            order_reason=OrderReason.ENTRY,
        ),
    )

    assert duplicate_entry_submission_keys(events) == ("AAA|dup-1",)
