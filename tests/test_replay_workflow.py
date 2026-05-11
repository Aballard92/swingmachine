from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
import yaml

from swingmachine.backtest import run_backtest
from swingmachine.config import StrategyRuntimeConfig, load_strategy_config
from swingmachine.contracts import RuntimeCycleInput, SetupSnapshot
from swingmachine.data_contracts import load_historical_panel_data
from swingmachine.entries import build_setup_snapshots
from swingmachine.enums import (
    AssetType,
    PaperShadowAlignmentStatus,
    PatternType,
    RegimeState,
    ReviewStatus,
    RuntimeMode,
    ShadowFillStatus,
)
from swingmachine.replay import (
    _build_selected_session_replay_context,
    _selected_replay_session_window,
    run_historical_manifest_replay,
    run_historical_scanner_replay,
    run_tiny_manifest_replay_proof,
    write_historical_portfolio_lifecycle_artifacts,
)
from swingmachine.runtime import (
    build_paper_shadow_audit_service,
    build_runtime,
    build_shadow_review_service,
)
from swingmachine.shadow import compare_runtime_cycle_shadow_fills
from swingmachine.signals import detect_setups, score_candidates
from tests.historical_panel_helpers import (
    add_prepared_features_to_manifest,
    sha256_file,
    write_prepared_feature_file,
)

HISTORICAL_PANEL_FIXTURE = Path("tests/fixtures/historical_panel")


def _replay_feature_fixture(
    config: StrategyRuntimeConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2026-04-20", periods=6)
    regime = pd.DataFrame(
        {
            "session_date": dates,
            "regime_state": [RegimeState.RISK_ON.value] * len(dates),
            "entry_enabled": [True] * len(dates),
            "min_candidate_score_percentile": [0.80] * len(dates),
            "min_trend_quality": [0.45] * len(dates),
        }
    )

    aaa = _symbol_feature_rows(
        symbol="AAA",
        dates=dates,
        closes=[103.5, 104.0, 103.5, 103.2, 103.0, 103.1],
        highs=[104.0, 105.0, 104.0, 104.5, 104.0, 104.2],
        lows=[103.0, 102.0, 102.5, 102.0, 102.0, 102.0],
        volumes=[900_000.0, 800_000.0, 780_000.0, 760_000.0, 740_000.0, 720_000.0],
        sector="TECH",
        score_bias=1.0,
    )
    bbb = _symbol_feature_rows(
        symbol="BBB",
        dates=dates,
        closes=[52.0, 52.2, 52.1, 52.0, 51.9, 52.0],
        highs=[52.4, 52.5, 52.3, 52.2, 52.1, 52.2],
        lows=[51.7, 51.8, 51.7, 51.6, 51.6, 51.7],
        volumes=[700_000.0] * len(dates),
        sector="UTIL",
        score_bias=0.0,
    )
    panel = pd.concat([aaa, bbb], ignore_index=True)
    scored = score_candidates(panel, regime, config)
    return detect_setups(scored, config), regime


def _symbol_feature_rows(
    *,
    symbol: str,
    dates: pd.DatetimeIndex,
    closes: list[float],
    highs: list[float],
    lows: list[float],
    volumes: list[float],
    sector: str,
    score_bias: float,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": [symbol] * len(dates),
            "session_date": dates,
            "raw_open": closes,
            "raw_high": highs,
            "raw_low": lows,
            "raw_close": closes,
            "raw_volume": volumes,
            "split_adj_close": closes,
            "split_adj_high": highs,
            "split_adj_low": lows,
            "ma50": [100.0 if symbol == "AAA" else 50.0] * len(dates),
            "ma200": [90.0 if symbol == "AAA" else 45.0] * len(dates),
            "ma200_slope_pct20": [0.02] * len(dates),
            "dist_to_52w_high": [0.04, 0.04, 0.04, 0.05, 0.05, 0.05],
            "mom_252_21": [0.20 + score_bias] * len(dates),
            "ret_126": [0.15 + score_bias] * len(dates),
            "rs_vs_benchmark_126": [0.08 + score_bias] * len(dates),
            "trend_quality": [0.70 if symbol == "AAA" else 0.50] * len(dates),
            "atr_14": [2.0] * len(dates),
            "range_compression_ratio": [0.75] * len(dates),
            "pullback_days": [0.0, 0.0, 1.0, 2.0, 3.0, 4.0],
            "pullback_depth_atr": [0.2, 0.0, 0.75, 0.9, 1.0, 0.95],
            "anchor_high_date": [dates[1]] * len(dates),
            "volume_ratio_20": [0.80] * len(dates),
            "regular_closes_until_earnings_event": [10] * len(dates),
            "history_days": [300] * len(dates),
            "avg_daily_dollar_volume_20": [25_000_000.0] * len(dates),
            "asset_type": [AssetType.COMMON_STOCK.value] * len(dates),
            "sector": [sector] * len(dates),
        }
    )


def test_fixture_replay_exercises_signal_backtest_shadow_and_audit(
    tmp_path: Path,
) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    detected, regime = _replay_feature_fixture(config)

    signal_date = pd.Timestamp("2026-04-27")
    final_session_setups = detected.loc[
        (detected["session_date"] == signal_date) & detected["setup_valid"]
    ]
    snapshots = build_setup_snapshots(final_session_setups, config)

    assert [setup.symbol for setup in snapshots] == ["AAA"]
    setup = snapshots[0]
    assert setup.pattern_type is PatternType.TIGHT_BASE
    assert setup.entry_trigger == pytest.approx(105.2)

    backtest_result = run_backtest(detected, regime, config)
    assert [event.event_type for event in backtest_result.events] == ["ENTRY_SUBMITTED"]
    assert backtest_result.final_equity == pytest.approx(100_000.0)

    database_url = f"sqlite+pysqlite:///{tmp_path / 'replay.db'}"
    cycle_input = RuntimeCycleInput(
        as_of="2026-04-27T16:05:00",
        regime_state=RegimeState.RISK_ON,
        equity=100_000.0,
        last_data_at="2026-04-27T16:04:00",
        expires_at="2026-04-28T16:00:00",
        setups=tuple(snapshots),
        sector_by_symbol={"AAA": "TECH"},
    )

    shadow_result = build_runtime(config, database_url=database_url).run_cycle(
        cycle_input,
        mode=RuntimeMode.SHADOW,
    )
    assert shadow_result.shadow_entry_batch is not None
    assert shadow_result.shadow_entry_batch.proposals[0].would_submit is True

    comparison_batch = compare_runtime_cycle_shadow_fills(
        shadow_result,
        _next_session_market_data(setup),
        config,
    )
    assert comparison_batch.filled_count == 1
    assert comparison_batch.comparisons[0].status is ShadowFillStatus.FILLED

    build_shadow_review_service(database_url=database_url).record_comparison_batch(comparison_batch)
    paper_result = build_runtime(config, database_url=database_url).run_cycle(
        cycle_input,
        mode=RuntimeMode.PAPER,
    )
    assert paper_result.paper_entry_batch is not None
    assert paper_result.paper_entry_batch.submissions[0].submitted is True

    audit_records = build_paper_shadow_audit_service(database_url=database_url).load_records()
    assert len(audit_records) == 1
    assert audit_records[0].setup_id == setup.setup_id
    assert (
        audit_records[0].alignment_status
        is PaperShadowAlignmentStatus.SHADOW_FILLED_PAPER_NOT_FILLED
    )


def test_tiny_manifest_replay_proof_is_deterministic(tmp_path: Path) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    manifest_path = HISTORICAL_PANEL_FIXTURE / "manifest.yaml"

    first = run_tiny_manifest_replay_proof(
        manifest_path,
        config,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'first.db'}",
    )
    second = run_tiny_manifest_replay_proof(
        manifest_path,
        config,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'second.db'}",
    )

    assert first.status is ReviewStatus.PASS
    assert first.signal_session is not None
    assert first.signal_session.isoformat() == "2026-04-27"
    assert first.next_session is not None
    assert first.next_session.isoformat() == "2026-04-28"
    assert first.setup_symbols == ("AAA",)
    assert first.shadow_status_counts == {"FILLED": 1}
    assert first.audit_alignment_counts == {"SHADOW_FILLED_PAPER_NOT_FILLED": 1}
    assert "ENTRY_SUBMITTED" in first.backtest_event_types
    assert "ENTRY_FILLED" in first.backtest_event_types

    assert first.setup_ids == second.setup_ids
    assert first.setup_symbols == second.setup_symbols
    assert first.backtest_event_types == second.backtest_event_types
    assert first.shadow_status_counts == second.shadow_status_counts
    assert first.audit_alignment_counts == second.audit_alignment_counts


def test_historical_manifest_replay_writes_deterministic_material_artifacts(
    tmp_path: Path,
) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    manifest_path = HISTORICAL_PANEL_FIXTURE / "manifest.yaml"

    first = run_historical_manifest_replay(
        manifest_path,
        config,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'first_artifacts.db'}",
        output_dir=tmp_path / "first_artifacts",
        selected_period_plan_path="config/swing_machine_v0_1_selected_periods.yaml",
    )
    run_historical_manifest_replay(
        manifest_path,
        config,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'second_artifacts.db'}",
        output_dir=tmp_path / "second_artifacts",
        selected_period_plan_path="config/swing_machine_v0_1_selected_periods.yaml",
    )

    assert first.status is ReviewStatus.PASS
    assert set(first.artifact_paths) == {
        "validation_summary",
        "replay_summary",
        "stage_counts",
        "material_decisions",
        "decision_traces",
        "reconciliation_summary",
        "baseline_report_package",
        "freeze_readiness",
    }
    for artifact_path in first.artifact_paths.values():
        assert Path(artifact_path).exists()
    assert not (tmp_path / "first_artifacts" / "failure_summary.json").exists()
    baseline_package = json.loads(
        (tmp_path / "first_artifacts" / "baseline_report_package.json").read_text(
            encoding="utf-8"
        )
    )
    assert baseline_package["baseline_id"] == "swing_machine_v0_1"
    assert baseline_package["manifest"]["config_hash"] == config.config_hash()
    assert baseline_package["summary"]["serious_full_run_allowed"] is False
    assert baseline_package["summary"]["candidate_count"] == 2
    assert baseline_package["summary"]["signal_count"] == 1
    assert baseline_package["summary"]["risk_plan_count"] == 1
    assert baseline_package["summary"]["order_plan_count"] == 1
    assert {candidate["symbol"] for candidate in baseline_package["candidates"]} == {"AAA", "BBB"}
    assert baseline_package["signals"][0]["symbol"] == "AAA"
    assert baseline_package["risk_plans"][0]["symbol"] == "AAA"
    assert baseline_package["order_plans"][0]["symbol"] == "AAA"
    freeze_readiness = json.loads(
        (tmp_path / "first_artifacts" / "freeze_readiness.json").read_text(encoding="utf-8")
    )
    assert freeze_readiness["decision"] == "BLOCK"
    assert freeze_readiness["serious_full_run_allowed"] is False
    assert {
        "manifest_checks_incomplete",
        "parity_evidence_missing",
        "operator_approval_missing",
    } <= {blocker["code"] for blocker in freeze_readiness["blockers"]}

    replay_summary = json.loads(
        (tmp_path / "first_artifacts" / "replay_summary.json").read_text(encoding="utf-8")
    )
    assert replay_summary["status"] == "PASS"
    assert replay_summary["feature_adapter"] == "proof_derived_from_ohlcv_v1"
    assert replay_summary["metrics"]["setup_count"] == 1

    stage_counts = json.loads(
        (tmp_path / "first_artifacts" / "stage_counts.json").read_text(encoding="utf-8")
    )
    assert {stage["stage"] for stage in stage_counts["stages"]} >= {
        "validation",
        "feature_adapter",
        "setup_detection",
        "backtest",
        "shadow_comparison",
        "paper_shadow_audit",
    }

    first_material = json.loads(
        (tmp_path / "first_artifacts" / "material_decisions.json").read_text(encoding="utf-8")
    )
    second_material = json.loads(
        (tmp_path / "second_artifacts" / "material_decisions.json").read_text(encoding="utf-8")
    )
    assert first_material == second_material
    assert first_material["setup_symbols"] == ["AAA"]
    assert first_material["shadow_status_counts"] == {"FILLED": 1}
    assert first_material["audit_alignment_counts"] == {"SHADOW_FILLED_PAPER_NOT_FILLED": 1}

    decision_traces = json.loads(
        (tmp_path / "first_artifacts" / "decision_traces.json").read_text(encoding="utf-8")
    )
    traces_by_symbol = {trace["symbol"]: trace for trace in decision_traces["traces"]}
    assert traces_by_symbol["AAA"]["decision"] == "ACCEPTED_SETUP"
    assert traces_by_symbol["AAA"]["reason_codes"] == ["SETUP_VALID"]
    assert traces_by_symbol["BBB"]["decision"] == "REJECTED"
    assert "CANDIDATE_SCORE_BELOW_THRESHOLD" in traces_by_symbol["BBB"]["reason_codes"]

    reconciliation = json.loads(
        (tmp_path / "first_artifacts" / "reconciliation_summary.json").read_text(encoding="utf-8")
    )
    assert reconciliation["status"] == "PASS"
    assert reconciliation["counts"]["setup_count"] == 1
    assert reconciliation["counts"]["paper_submission_count"] == 1
    assert {check["status"] for check in reconciliation["checks"]} == {"PASS"}


def test_selected_replay_context_preserves_single_signal_session_semantics() -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    panel_data = load_historical_panel_data(HISTORICAL_PANEL_FIXTURE / "manifest.yaml")
    session_window = _selected_replay_session_window(panel_data)

    assert session_window is not None
    assert session_window.signal_session.isoformat() == "2026-04-27"
    assert session_window.next_session.isoformat() == "2026-04-28"

    context = _build_selected_session_replay_context(
        panel_data=panel_data,
        config=config,
        signal_session=session_window.signal_session,
        next_session=session_window.next_session,
        initial_equity=100_000.0,
    )

    assert {trace.session_date for trace in context.decision_traces} == {
        session_window.signal_session
    }
    assert [setup.symbol for setup in context.setups] == ["AAA"]
    assert len(context.baseline_candidates) == 2
    assert len(context.baseline_signals) == 1
    assert len(context.baseline_risk_plans) == 1
    assert len(context.baseline_order_plans) == 1
    assert {
        pd.Timestamp(session).date()
        for session in pd.to_datetime(context.replay_detected["session_date"]).unique()
    } == {session_window.signal_session, session_window.next_session}


def test_historical_scanner_replay_writes_density_artifacts(tmp_path: Path) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    output_dir = tmp_path / "scanner_density"

    summary = run_historical_scanner_replay(
        HISTORICAL_PANEL_FIXTURE / "manifest.yaml",
        config,
        output_dir=output_dir,
    )

    assert summary.status is ReviewStatus.PASS
    assert summary.eligible_signal_session_count == 6
    assert summary.processed_signal_session_count == 6
    assert summary.skipped_session_count == 0
    assert summary.total_decision_traces == 12
    assert summary.total_candidates == 12
    assert summary.sessions_with_setups >= 1
    assert summary.session_results[-1].signal_session.isoformat() == "2026-04-27"
    assert summary.session_results[-1].next_session.isoformat() == "2026-04-28"
    assert summary.session_results[-1].density.accepted_setup_count == 1
    assert summary.session_results[-1].accepted_setup_symbols == ("AAA",)

    expected_artifacts = {
        "scanner_replay_summary.json",
        "scanner_session_results.json",
        "scanner_decision_density.json",
        "scanner_rejection_reasons.json",
        "scanner_material_decisions.json",
        "scanner_baseline_report_package.json",
        "scanner_artifact_manifest.json",
    }
    assert {path.name for path in output_dir.iterdir()} == expected_artifacts

    density = json.loads((output_dir / "scanner_decision_density.json").read_text())
    assert density["processed_signal_session_count"] == 6
    assert density["sessions"][-1]["accepted_setup_count"] == 1
    material_decisions = json.loads(
        (output_dir / "scanner_material_decisions.json").read_text(encoding="utf-8")
    )
    last_session = material_decisions["sessions"][-1]
    assert len(last_session["material_decision_rows"]) == 2
    accepted_rows = [
        row
        for row in last_session["material_decision_rows"]
        if row["decision"] == "ACCEPTED_SETUP"
    ]
    assert accepted_rows[0]["candidate_id"].startswith("candidate:")
    assert accepted_rows[0]["signal_id"].startswith("signal:")
    assert accepted_rows[0]["risk_plan_id"].startswith("risk_plan:")
    assert accepted_rows[0]["order_plan_id"].startswith("order_plan:")


def test_historical_portfolio_lifecycle_artifacts_from_backtest_result(
    tmp_path: Path,
) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    detected, regime = _replay_feature_fixture(config)
    backtest_result = run_backtest(detected, regime, config)
    output_dir = tmp_path / "portfolio_lifecycle"

    manifest = write_historical_portfolio_lifecycle_artifacts(
        backtest_result,
        output_dir,
        panel_id="fixture-panel",
        manifest_path=HISTORICAL_PANEL_FIXTURE / "manifest.yaml",
        config_hash=config.config_hash(),
    )

    expected_artifacts = {
        "portfolio_lifecycle_replay_summary.json",
        "portfolio_lifecycle_session_states.json",
        "portfolio_lifecycle_transitions.json",
        "portfolio_lifecycle_positions.json",
        "portfolio_lifecycle_trade_ledger.json",
        "portfolio_lifecycle_pending_orders.json",
        "portfolio_lifecycle_exposure.json",
        "portfolio_lifecycle_reconciliation.json",
        "portfolio_lifecycle_baseline_package.json",
        "portfolio_lifecycle_artifact_manifest.json",
    }
    assert {path.name for path in output_dir.iterdir()} == expected_artifacts
    assert manifest.lifecycle_parity_report_path is None

    summary = json.loads(
        (output_dir / "portfolio_lifecycle_replay_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["status"] == "PASS"
    assert summary["processed_session_count"] == 6
    assert summary["entry_submitted_count"] == 1
    assert summary["transition_count"] == 1
    assert summary["pending_order_snapshot_count"] > 0

    transitions = json.loads(
        (output_dir / "portfolio_lifecycle_transitions.json").read_text(
            encoding="utf-8"
        )
    )
    assert transitions["transitions"][0]["trigger"] == "ENTRY_SUBMITTED"
    assert transitions["transitions"][0]["from_state"] == "ARMED"
    assert transitions["transitions"][0]["to_state"] == "PENDING_ENTRY"

    trade_ledger = json.loads(
        (output_dir / "portfolio_lifecycle_trade_ledger.json").read_text(
            encoding="utf-8"
        )
    )
    assert trade_ledger["panel_id"] == "fixture-panel"
    assert trade_ledger["trades"] == []

    session_states = json.loads(
        (output_dir / "portfolio_lifecycle_session_states.json").read_text(
            encoding="utf-8"
        )
    )
    assert session_states["session_states"][-1]["pending_entry_count"] == 1

    reconciliation = json.loads(
        (output_dir / "portfolio_lifecycle_reconciliation.json").read_text(
            encoding="utf-8"
        )
    )
    assert reconciliation["status"] == "PASS"
    assert reconciliation["failures"] == []
    assert reconciliation["warnings"] == []


def test_historical_manifest_replay_uses_prepared_features_when_manifest_declares_them(
    tmp_path: Path,
) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    panel_path = tmp_path / "historical_panel"
    output_dir = tmp_path / "prepared_feature_artifacts"
    shutil.copytree(HISTORICAL_PANEL_FIXTURE, panel_path)
    manifest_path = panel_path / "manifest.yaml"
    features_path = write_prepared_feature_file(panel_path)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
    )

    result = run_historical_manifest_replay(
        manifest_path,
        config,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'prepared_features.db'}",
        output_dir=output_dir,
    )

    assert result.status is ReviewStatus.PASS
    assert result.feature_adapter == "prepared_features_v1"
    assert result.setup_symbols == ("AAA",)

    replay_summary = json.loads((output_dir / "replay_summary.json").read_text(encoding="utf-8"))
    assert replay_summary["feature_adapter"] == "prepared_features_v1"
    assert replay_summary["metrics"]["feature_adapter"] == "prepared_features_v1"

    stage_counts = json.loads((output_dir / "stage_counts.json").read_text(encoding="utf-8"))
    feature_adapter_stage = next(
        stage for stage in stage_counts["stages"] if stage["stage"] == "feature_adapter"
    )
    assert feature_adapter_stage["adapter"] == "prepared_features_v1"
    assert feature_adapter_stage["row_count"] == 14


def test_historical_manifest_replay_refuses_signal_before_prepared_features_start(
    tmp_path: Path,
) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    panel_path = tmp_path / "historical_panel"
    shutil.copytree(HISTORICAL_PANEL_FIXTURE, panel_path)
    manifest_path = panel_path / "manifest.yaml"
    features_path = write_prepared_feature_file(panel_path)
    features = pd.read_csv(features_path)
    features = features.loc[features["session_date"] == "2026-04-28"]
    features.to_csv(features_path, index=False)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
        feature_start_session="2026-04-28",
    )

    result = run_historical_manifest_replay(
        manifest_path,
        config,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'feature_start.db'}",
    )

    assert result.status is ReviewStatus.FAIL
    assert result.feature_adapter == "prepared_features_v1"
    assert result.reconciliation is not None
    assert result.reconciliation.checks[0].observed == "SIGNAL_SESSION_BEFORE_FEATURE_START"
    feature_adapter_stage = next(
        stage for stage in result.stage_summaries if stage["stage"] == "feature_adapter"
    )
    assert feature_adapter_stage["status"] == "FAIL"
    assert feature_adapter_stage["reason"] == "SIGNAL_SESSION_BEFORE_FEATURE_START"


def test_historical_manifest_replay_feature_precondition_respects_tradability_window(
    tmp_path: Path,
) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    panel_path = tmp_path / "historical_panel"
    shutil.copytree(HISTORICAL_PANEL_FIXTURE, panel_path)
    manifest_path = panel_path / "manifest.yaml"
    symbol_reference_path = panel_path / "symbol_reference.csv"
    symbol_reference = pd.read_csv(symbol_reference_path)
    symbol_reference["tradable_start_session"] = ""
    symbol_reference["tradable_end_session"] = ""
    symbol_reference.loc[
        symbol_reference["symbol"] == "BBB",
        "tradable_end_session",
    ] = "2026-04-24"
    symbol_reference.to_csv(symbol_reference_path, index=False)
    features_path = write_prepared_feature_file(panel_path)
    features = pd.read_csv(features_path)
    features = features.loc[
        (features["symbol"] == "AAA")
        | ((features["symbol"] == "BBB") & (features["session_date"] <= "2026-04-24"))
    ]
    features.to_csv(features_path, index=False)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
        feature_start_session="2026-04-20",
        feature_coverage_scope="tradable_reference",
    )

    result = run_historical_manifest_replay(
        manifest_path,
        config,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'tradable_scope.db'}",
    )

    assert result.status is ReviewStatus.PASS
    assert result.feature_adapter == "prepared_features_v1"
    assert result.setup_symbols == ("AAA",)


def test_historical_manifest_replay_feature_precondition_respects_effective_history(
    tmp_path: Path,
) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    panel_path = tmp_path / "historical_panel"
    shutil.copytree(HISTORICAL_PANEL_FIXTURE, panel_path)
    manifest_path = panel_path / "manifest.yaml"
    symbol_reference_path = panel_path / "symbol_reference.csv"
    symbol_reference = pd.read_csv(symbol_reference_path)
    symbol_reference["effective_start_session"] = ""
    symbol_reference["effective_end_session"] = ""
    bbb_base = symbol_reference.loc[symbol_reference["symbol"] == "BBB"].iloc[0].copy()
    bbb_early = bbb_base.copy()
    bbb_early["is_tradable"] = True
    bbb_early["effective_start_session"] = "2026-04-20"
    bbb_early["effective_end_session"] = "2026-04-24"
    bbb_late = bbb_base.copy()
    bbb_late["is_tradable"] = False
    bbb_late["effective_start_session"] = "2026-04-27"
    bbb_late["effective_end_session"] = "2026-04-28"
    symbol_reference = pd.concat(
        [
            symbol_reference.loc[symbol_reference["symbol"] != "BBB"],
            pd.DataFrame([bbb_early, bbb_late]),
        ],
        ignore_index=True,
    )
    symbol_reference.to_csv(symbol_reference_path, index=False)
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["files"]["symbol_reference"]["row_count"] = len(symbol_reference)
    manifest_path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")
    features_path = write_prepared_feature_file(panel_path)
    features = pd.read_csv(features_path)
    features = features.loc[
        (features["symbol"] == "AAA")
        | ((features["symbol"] == "BBB") & (features["session_date"] <= "2026-04-24"))
    ]
    features.to_csv(features_path, index=False)
    add_prepared_features_to_manifest(
        manifest_path,
        features_path,
        sha256=sha256_file(features_path),
        feature_start_session="2026-04-20",
        feature_coverage_scope="tradable_reference",
    )

    result = run_historical_manifest_replay(
        manifest_path,
        config,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'effective_history.db'}",
    )

    assert result.status is ReviewStatus.PASS
    assert result.feature_adapter == "prepared_features_v1"
    assert result.setup_symbols == ("AAA",)


def test_tiny_manifest_replay_proof_refuses_invalid_panel(tmp_path: Path) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    panel_path = tmp_path / "historical_panel"
    shutil.copytree(HISTORICAL_PANEL_FIXTURE, panel_path)
    (panel_path / "ohlcv.csv").unlink()

    result = run_tiny_manifest_replay_proof(
        panel_path / "manifest.yaml",
        config,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'invalid.db'}",
    )

    assert result.status is ReviewStatus.FAIL
    assert result.setup_ids == ()
    assert {issue.code for issue in result.validation.errors} == {"FILE_MISSING"}


def test_historical_manifest_replay_writes_failure_artifacts_for_invalid_panel(
    tmp_path: Path,
) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    panel_path = tmp_path / "historical_panel"
    output_dir = tmp_path / "invalid_artifacts"
    shutil.copytree(HISTORICAL_PANEL_FIXTURE, panel_path)
    (panel_path / "ohlcv.csv").unlink()

    result = run_historical_manifest_replay(
        panel_path / "manifest.yaml",
        config,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'invalid_artifacts.db'}",
        output_dir=output_dir,
    )

    assert result.status is ReviewStatus.FAIL
    assert set(result.artifact_paths) == {
        "validation_summary",
        "replay_summary",
        "stage_counts",
        "material_decisions",
        "decision_traces",
        "reconciliation_summary",
        "baseline_report_package",
        "freeze_readiness",
        "failure_summary",
    }
    failure_summary = json.loads((output_dir / "failure_summary.json").read_text(encoding="utf-8"))
    assert failure_summary["failure_stage"] == "validation"
    assert {issue["code"] for issue in failure_summary["validation_errors"]} == {"FILE_MISSING"}
    material_decisions = json.loads(
        (output_dir / "material_decisions.json").read_text(encoding="utf-8")
    )
    assert material_decisions["setup_ids"] == []
    reconciliation = json.loads(
        (output_dir / "reconciliation_summary.json").read_text(encoding="utf-8")
    )
    assert reconciliation["status"] == "FAIL"
    assert reconciliation["checks"][0]["observed"] == "VALIDATION_FAILED"


def _next_session_market_data(setup: SetupSnapshot) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": [setup.symbol],
            "session_date": [pd.Timestamp("2026-04-28")],
            "raw_open": [setup.entry_trigger + 0.01],
            "raw_high": [setup.entry_trigger + 0.50],
            "raw_low": [setup.entry_trigger - 0.50],
            "raw_close": [setup.entry_trigger + 0.20],
            "raw_volume": [2_000_000.0],
            "spread_bps": [2.0],
            "fx_conversion_cost_bps": [0.0],
        }
    )
