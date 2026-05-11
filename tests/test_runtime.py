from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from typer.testing import CliRunner

from swingmachine.broker import PaperBrokerAdapter
from swingmachine.config import load_strategy_config
from swingmachine.contracts import RuntimeCycleInput, SetupSnapshot
from swingmachine.data_contracts import (
    load_historical_panel_manifest,
    validate_historical_panel_manifest,
)
from swingmachine.entries import build_setup_snapshot
from swingmachine.enums import PatternType, RegimeState, ReviewStatus, RuntimeMode
from swingmachine.order_intents import OrderIntentService
from swingmachine.runtime import (
    app,
    build_runtime,
    build_runtime_run_history,
    write_runtime_cycle_result,
)
from swingmachine.storage import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)


def _setup_snapshot(setup_id: str, *, symbol: str = "AAA") -> SetupSnapshot:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    return build_setup_snapshot(
        {
            "symbol": symbol,
            "session_date": "2026-04-23",
            "pattern_type": PatternType.PULLBACK.value,
            "setup_id": setup_id,
            "setup_start_date": "2026-04-18",
            "setup_end_date": "2026-04-23",
            "setup_high": 100.0,
            "setup_low": 94.0,
            "setup_high_date": "2026-04-18",
            "setup_low_date": "2026-04-22",
            "atr_14": 2.0,
            "setup_valid": True,
        },
        config,
    )


def test_trading_runtime_paper_cycle_submits_order(tmp_path: Path) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    database_url = f"sqlite+pysqlite:///{tmp_path / 'paper_runtime.db'}"
    runtime = build_runtime(config, database_url=database_url)

    result = runtime.run_cycle(
        RuntimeCycleInput(
            as_of="2026-04-24T16:05:00",
            regime_state=RegimeState.RISK_ON,
            equity=100_000.0,
            last_data_at="2026-04-24T16:04:00",
            expires_at="2026-04-25T16:00:00",
            setups=(_setup_snapshot("setup-runtime-paper"),),
            sector_by_symbol={"AAA": "TECH"},
        ),
        mode=RuntimeMode.PAPER,
    )

    assert result.pending_entry_batch is not None
    assert result.paper_entry_batch is not None
    assert result.paper_entry_batch.submissions[0].submitted is True

    engine = create_database_engine(database_url)
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    assert len(OrderIntentService(session_factory).recover_state().pending_entry_intents) == 1
    assert len(PaperBrokerAdapter(session_factory).list_open_orders()) == 1


def test_trading_runtime_shadow_cycle_is_dry_run(tmp_path: Path) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    database_url = f"sqlite+pysqlite:///{tmp_path / 'shadow_runtime.db'}"
    runtime = build_runtime(config, database_url=database_url)
    result = runtime.run_cycle(
        RuntimeCycleInput(
            as_of="2026-04-24T16:05:00",
            regime_state=RegimeState.RISK_ON,
            equity=100_000.0,
            last_data_at="2026-04-24T16:04:00",
            expires_at="2026-04-25T16:00:00",
            setups=(_setup_snapshot("setup-runtime-shadow"),),
        ),
        mode=RuntimeMode.SHADOW,
    )

    assert result.paper_entry_batch is None
    assert result.shadow_entry_batch is not None
    assert result.shadow_entry_batch.proposals[0].would_submit is True

    engine = create_database_engine(database_url)
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    assert OrderIntentService(session_factory).recover_state().pending_entry_intents == ()
    assert PaperBrokerAdapter(session_factory).list_open_orders() == ()


def test_runtime_cli_writes_cycle_result_json(tmp_path: Path) -> None:
    input_path = tmp_path / "cycle_input.yaml"
    output_path = tmp_path / "cycle_output.json"
    database_path = tmp_path / "runtime.db"
    input_path.write_text(
        "\n".join(
            [
                "as_of: '2026-04-24T16:05:00'",
                "regime_state: RISK_ON",
                "equity: 100000.0",
                "last_data_at: '2026-04-24T16:04:00'",
                "expires_at: '2026-04-25T16:00:00'",
                "setups:",
                "  - symbol: AAA",
                "    session_date: '2026-04-23'",
                "    pattern_type: PULLBACK",
                "    setup_id: setup-runtime-cli",
                "    setup_start_date: '2026-04-18'",
                "    setup_end_date: '2026-04-23'",
                "    setup_high: 100.0",
                "    setup_low: 94.0",
                "    setup_high_date: '2026-04-18'",
                "    setup_low_date: '2026-04-22'",
                "    entry_trigger: 100.2",
                "    entry_limit: 101.7",
                "    initial_stop: 93.8",
                "    per_share_risk: 6.4",
                "    spent: false",
            ]
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "run-cycle",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--mode",
            "SHADOW",
            "--database-url",
            f"sqlite+pysqlite:///{database_path}",
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "SHADOW"
    assert payload["shadow_entry_batch"]["proposals"][0]["would_submit"] is True


def test_runtime_cli_compares_shadow_fills_json(tmp_path: Path) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    database_url = f"sqlite+pysqlite:///{tmp_path / 'runtime.db'}"
    runtime = build_runtime(config, database_url=database_url)
    shadow_result = runtime.run_cycle(
        RuntimeCycleInput(
            as_of="2026-04-24T16:05:00",
            regime_state=RegimeState.RISK_ON,
            equity=100_000.0,
            last_data_at="2026-04-24T16:04:00",
            expires_at="2026-04-25T16:00:00",
            setups=(_setup_snapshot("setup-runtime-compare"),),
        ),
        mode=RuntimeMode.SHADOW,
    )

    shadow_result_path = tmp_path / "shadow_result.json"
    market_data_path = tmp_path / "market_data.csv"
    output_path = tmp_path / "shadow_comparison.json"
    write_runtime_cycle_result(shadow_result, shadow_result_path)
    market_data_path.write_text(
        "\n".join(
            [
                "symbol,session_date,raw_open,raw_high,raw_low,raw_close,raw_volume,spread_bps,fx_conversion_cost_bps",
                "AAA,2026-04-25,100.3,101.0,99.7,100.5,1000000000000,60.0,0.0",
            ]
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "compare-shadow-fills",
            "--shadow-result",
            str(shadow_result_path),
            "--market-data",
            str(market_data_path),
            "--output",
            str(output_path),
            "--database-url",
            database_url,
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["filled_count"] == 1
    assert payload["comparisons"][0]["status"] == "FILLED"

    summary_output_path = tmp_path / "shadow_summary.json"
    summary_invocation = runner.invoke(
        app,
        [
            "summarize-shadow-fills",
            "--output",
            str(summary_output_path),
            "--database-url",
            database_url,
            "--regime-state",
            "RISK_ON",
        ],
    )

    assert summary_invocation.exit_code == 0, summary_invocation.stdout
    summary_payload = json.loads(summary_output_path.read_text(encoding="utf-8"))
    assert summary_payload["summary"]["comparison_count"] == 1
    assert summary_payload["by_regime"][0]["source_regime_state"] == "RISK_ON"


def test_runtime_cli_runs_paper_shadow_audit_workflow(tmp_path: Path) -> None:
    input_path = tmp_path / "cycle_input.yaml"
    market_data_path = tmp_path / "market_data.csv"
    output_dir = tmp_path / "workflow"
    database_url = f"sqlite+pysqlite:///{tmp_path / 'workflow.db'}"

    input_path.write_text(
        "\n".join(
            [
                "as_of: '2026-04-24T16:05:00'",
                "regime_state: RISK_ON",
                "equity: 100000.0",
                "last_data_at: '2026-04-24T16:04:00'",
                "expires_at: '2026-04-25T16:00:00'",
                "setups:",
                "  - symbol: AAA",
                "    session_date: '2026-04-23'",
                "    pattern_type: PULLBACK",
                "    setup_id: setup-runtime-workflow",
                "    setup_start_date: '2026-04-18'",
                "    setup_end_date: '2026-04-23'",
                "    setup_high: 100.0",
                "    setup_low: 94.0",
                "    setup_high_date: '2026-04-18'",
                "    setup_low_date: '2026-04-22'",
                "    entry_trigger: 100.2",
                "    entry_limit: 101.7",
                "    initial_stop: 93.8",
                "    per_share_risk: 6.4",
                "    spent: false",
            ]
        ),
        encoding="utf-8",
    )
    market_data_path.write_text(
        "\n".join(
            [
                "symbol,session_date,raw_open,raw_high,raw_low,raw_close,raw_volume",
                "AAA,2026-04-25,100.3,101.0,99.7,100.5,1000000",
            ]
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "run-paper-shadow-audit",
            "--input",
            str(input_path),
            "--market-data",
            str(market_data_path),
            "--output-dir",
            str(output_dir),
            "--database-url",
            database_url,
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    workflow_summary = json.loads((output_dir / "workflow_summary.json").read_text())
    assert workflow_summary["status"] == "SUCCEEDED"
    assert workflow_summary["metrics"]["paper"]["submitted_count"] == 1
    assert workflow_summary["metrics"]["shadow"]["would_submit_count"] == 1
    assert (output_dir / "paper_result.json").exists()
    assert (output_dir / "shadow_comparison.json").exists()
    assert (output_dir / "audit_report_latest.json").exists()

    run_history_path = tmp_path / "run_history.json"
    history_invocation = runner.invoke(
        app,
        [
            "list-run-history",
            "--output",
            str(run_history_path),
            "--database-url",
            database_url,
        ],
    )

    assert history_invocation.exit_code == 0, history_invocation.stdout
    run_history = json.loads(run_history_path.read_text())
    assert run_history["count"] == 1
    assert run_history["runs"][0]["command"] == "run-paper-shadow-audit"

    run_events_path = tmp_path / "run_events.json"
    events_invocation = runner.invoke(
        app,
        [
            "list-run-events",
            "--output",
            str(run_events_path),
            "--database-url",
            database_url,
            "--run-id",
            workflow_summary["run_id"],
        ],
    )

    assert events_invocation.exit_code == 0, events_invocation.stdout
    run_events = json.loads(run_events_path.read_text())
    assert run_events["count"] == 10
    event_types = {event["event_type"] for event in run_events["events"]}
    assert event_types >= {
        "PAPER_ENTRY_SUBMISSION_DECIDED",
        "RUNTIME_CYCLE_RESULT_WRITTEN",
        "SHADOW_COMPARISON_WRITTEN",
        "SHADOW_ENTRY_PROPOSAL_DECIDED",
        "SHADOW_FILL_COMPARISON_RECORDED",
        "SHADOW_SUMMARY_WRITTEN",
        "PAPER_SHADOW_AUDIT_SUMMARY_WRITTEN",
        "AUDIT_REPORT_WRITTEN",
        "WORKFLOW_SUMMARY_WRITTEN",
    }
    assert {event["run_id"] for event in run_events["events"]} == {workflow_summary["run_id"]}

    decision_events = {
        event["event_type"]: event
        for event in run_events["events"]
        if event["event_type"]
        in {
            "PAPER_ENTRY_SUBMISSION_DECIDED",
            "SHADOW_ENTRY_PROPOSAL_DECIDED",
            "SHADOW_FILL_COMPARISON_RECORDED",
        }
    }
    assert decision_events["PAPER_ENTRY_SUBMISSION_DECIDED"]["symbol"] == "AAA"
    assert decision_events["PAPER_ENTRY_SUBMISSION_DECIDED"]["setup_id"] == (
        "setup-runtime-workflow"
    )
    assert decision_events["PAPER_ENTRY_SUBMISSION_DECIDED"]["intent_id"] is not None
    assert decision_events["PAPER_ENTRY_SUBMISSION_DECIDED"]["payload"]["submitted"] is True
    assert decision_events["SHADOW_ENTRY_PROPOSAL_DECIDED"]["payload"]["would_submit"] is True
    assert decision_events["SHADOW_FILL_COMPARISON_RECORDED"]["payload"]["status"] == "FILLED"


def test_runtime_cli_runs_historical_replay_workflow(tmp_path: Path) -> None:
    output_dir = tmp_path / "historical_replay"

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "run-historical-replay",
            "--manifest",
            "tests/fixtures/historical_panel/manifest.yaml",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    workflow_summary = json.loads((output_dir / "workflow_summary.json").read_text())
    assert workflow_summary["status"] == "SUCCEEDED"
    assert workflow_summary["replay_status"] == "PASS"
    assert workflow_summary["metrics"]["setup_count"] == 1
    assert workflow_summary["database_url_source"] == "output_dir_default"
    assert (output_dir / "validation_summary.json").exists()
    assert (output_dir / "replay_summary.json").exists()
    assert (output_dir / "stage_counts.json").exists()
    assert (output_dir / "material_decisions.json").exists()
    assert (output_dir / "decision_traces.json").exists()
    assert (output_dir / "reconciliation_summary.json").exists()
    assert (output_dir / "baseline_report_package.json").exists()
    assert (output_dir / "freeze_readiness.json").exists()

    run_history_path = tmp_path / "historical_replay_run_history.json"
    database_url = f"sqlite+pysqlite:///{output_dir / 'historical_replay_runtime.db'}"
    history_invocation = runner.invoke(
        app,
        [
            "list-run-history",
            "--output",
            str(run_history_path),
            "--database-url",
            database_url,
        ],
    )
    assert history_invocation.exit_code == 0, history_invocation.stdout
    run_history = json.loads(run_history_path.read_text())
    assert run_history["count"] == 1
    assert run_history["runs"][0]["command"] == "run-historical-replay"

    run_events_path = tmp_path / "historical_replay_run_events.json"
    events_invocation = runner.invoke(
        app,
        [
            "list-run-events",
            "--output",
            str(run_events_path),
            "--database-url",
            database_url,
            "--run-id",
            workflow_summary["run_id"],
        ],
    )
    assert events_invocation.exit_code == 0, events_invocation.stdout
    run_events = json.loads(run_events_path.read_text())
    assert {event["event_type"] for event in run_events["events"]} == {
        "HISTORICAL_REPLAY_WRITTEN",
        "WORKFLOW_SUMMARY_WRITTEN",
    }

    review_output_path = tmp_path / "historical_replay_review.json"
    review_invocation = runner.invoke(
        app,
        [
            "run-review-report",
            "--output",
            str(review_output_path),
            "--database-url",
            database_url,
            "--as-of",
            "2026-04-28",
            "--lookback-days",
            "1",
            "--no-require-decision-events",
            "--no-require-shadow-snapshots",
            "--no-require-audit-snapshots",
            "--replay-output-dir",
            str(output_dir),
        ],
    )
    assert review_invocation.exit_code == 0, review_invocation.stdout
    review_payload = json.loads(review_output_path.read_text())
    replay_checks = [
        check
        for check in review_payload["review_checks"]
        if check["category"].startswith("replay_")
    ]
    assert replay_checks
    assert {check["status"] for check in replay_checks} == {"PASS"}
    assert review_payload["replay_artifacts"][0]["replay_summary"]["status"] == "PASS"


def test_runtime_cli_runs_historical_scanner_replay_workflow(tmp_path: Path) -> None:
    output_dir = tmp_path / "historical_scanner_replay"

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "run-historical-scanner-replay",
            "--manifest",
            "tests/fixtures/historical_panel/manifest.yaml",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    workflow_summary = json.loads((output_dir / "workflow_summary.json").read_text())
    assert workflow_summary["status"] == "SUCCEEDED"
    assert workflow_summary["scanner_status"] == "PASS"
    assert workflow_summary["metrics"]["eligible_signal_session_count"] == 6
    assert workflow_summary["metrics"]["processed_signal_session_count"] == 6
    assert workflow_summary["metrics"]["total_decision_traces"] == 12
    assert workflow_summary["database_url_source"] == "output_dir_default"
    assert (output_dir / "scanner_replay_summary.json").exists()
    assert (output_dir / "scanner_session_results.json").exists()
    assert (output_dir / "scanner_decision_density.json").exists()
    assert (output_dir / "scanner_rejection_reasons.json").exists()
    assert (output_dir / "scanner_material_decisions.json").exists()
    assert (output_dir / "scanner_baseline_report_package.json").exists()
    assert (output_dir / "scanner_artifact_manifest.json").exists()


def test_runtime_cli_runs_historical_portfolio_lifecycle_replay_workflow(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "historical_portfolio_lifecycle_replay"

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "run-historical-portfolio-lifecycle-replay",
            "--manifest",
            "tests/fixtures/historical_panel/manifest.yaml",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    workflow_summary = json.loads((output_dir / "workflow_summary.json").read_text())
    assert workflow_summary["status"] == "SUCCEEDED"
    assert workflow_summary["lifecycle_status"] == "PASS"
    assert workflow_summary["metrics"]["processed_session_count"] == 7
    assert workflow_summary["metrics"]["transition_count"] == 2
    assert workflow_summary["metrics"]["pending_order_snapshot_count"] > 0
    assert workflow_summary["metrics"]["position_snapshot_count"] > 0
    assert workflow_summary["metrics"]["reconciliation_warning_count"] == 0
    assert workflow_summary["database_url_source"] == "output_dir_default"
    assert (output_dir / "portfolio_lifecycle_replay_summary.json").exists()
    assert (output_dir / "portfolio_lifecycle_session_states.json").exists()
    assert (output_dir / "portfolio_lifecycle_transitions.json").exists()
    assert (output_dir / "portfolio_lifecycle_positions.json").exists()
    assert (output_dir / "portfolio_lifecycle_pending_orders.json").exists()
    assert (output_dir / "portfolio_lifecycle_exposure.json").exists()
    assert (output_dir / "portfolio_lifecycle_reconciliation.json").exists()
    assert (output_dir / "portfolio_lifecycle_baseline_package.json").exists()
    assert (output_dir / "portfolio_lifecycle_artifact_manifest.json").exists()


def test_runtime_cli_preflights_selected_period_qualification_blocked(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "selected_period_preflight.json"

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "preflight-selected-period-qualification",
            "--plan",
            "config/swing_machine_v0_1_selected_periods.yaml",
            "--output",
            str(output_path),
        ],
    )

    assert invocation.exit_code == 1, invocation.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert payload["blockers"][0]["code"] == "data_manifest_missing"


def test_runtime_cli_preflights_selected_period_qualification_with_manifests(
    tmp_path: Path,
) -> None:
    manifest_by_period = {}
    for period_id in (
        "smoke_recent_5_sessions",
        "recent_medium_replay_window",
        "historical_contract_stability_window",
    ):
        manifest_path = tmp_path / period_id / "manifest.yaml"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text("panel_id: placeholder\n", encoding="utf-8")
        manifest_by_period[period_id] = manifest_path
    output_path = tmp_path / "selected_period_preflight.json"

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "preflight-selected-period-qualification",
            "--plan",
            "config/swing_machine_v0_1_selected_periods.yaml",
            "--output",
            str(output_path),
            "--data-manifest",
            f"smoke_recent_5_sessions={manifest_by_period['smoke_recent_5_sessions']}",
            "--data-manifest",
            f"recent_medium_replay_window={manifest_by_period['recent_medium_replay_window']}",
            "--data-manifest",
            "historical_contract_stability_window="
            f"{manifest_by_period['historical_contract_stability_window']}",
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["blocker_count"] == 0


def test_runtime_cli_builds_historical_panel_manifest(tmp_path: Path) -> None:
    output_path = tmp_path / "manifest.yaml"

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "build-historical-panel-manifest",
            "--output",
            str(output_path),
            "--panel-id",
            "selected-period-smoke",
            "--ohlcv",
            "tests/fixtures/historical_panel/ohlcv.csv",
            "--symbol-reference",
            "tests/fixtures/historical_panel/symbol_reference.csv",
            "--corporate-actions",
            "tests/fixtures/historical_panel/corporate_actions.csv",
            "--earnings-events",
            "tests/fixtures/historical_panel/earnings_events.csv",
            "--description",
            "Selected-period smoke manifest builder proof",
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    manifest = load_historical_panel_manifest(output_path)
    validation = validate_historical_panel_manifest(output_path)

    assert manifest.panel_id == "selected-period-smoke"
    assert manifest.files.ohlcv.path == "ohlcv.csv"
    assert manifest.files.ohlcv.row_count is not None
    assert len(manifest.files.ohlcv.sha256 or "") == 64
    assert manifest.expected_symbol_count == 2
    assert validation.status is ReviewStatus.PASS


def test_runtime_cli_preflights_selected_period_data_inputs_blocked(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "selected_period_data_input_preflight.json"

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "preflight-selected-period-data-inputs",
            "--input-plan",
            "config/swing_machine_v0_1_selected_period_data_inputs.example.yaml",
            "--output",
            str(output_path),
        ],
    )

    assert invocation.exit_code == 1, invocation.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert payload["blocker_count"] > 0
    assert "source_file_missing" in {blocker["code"] for blocker in payload["blockers"]}


def test_runtime_cli_builds_selected_period_data_input_plan(tmp_path: Path) -> None:
    data_root = tmp_path / "qualification"
    for period_id in (
        "smoke_recent_5_sessions",
        "recent_medium_replay_window",
        "historical_contract_stability_window",
    ):
        period_dir = data_root / period_id
        period_dir.mkdir(parents=True)
        for file_name in (
            "ohlcv.csv",
            "symbol_reference.csv",
            "corporate_actions.csv",
            "earnings_events.csv",
        ):
            (period_dir / file_name).write_text("placeholder\n", encoding="utf-8")
    output_path = tmp_path / "selected_period_data_inputs.yaml"
    preflight_output_path = tmp_path / "selected_period_data_input_preflight.json"

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "build-selected-period-data-input-plan",
            "--data-root",
            str(data_root),
            "--output",
            str(output_path),
            "--selected-period-plan",
            "config/swing_machine_v0_1_selected_periods.yaml",
        ],
    )
    preflight_invocation = runner.invoke(
        app,
        [
            "preflight-selected-period-data-inputs",
            "--input-plan",
            str(output_path),
            "--output",
            str(preflight_output_path),
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    assert output_path.exists()
    assert preflight_invocation.exit_code == 0, preflight_invocation.stdout
    payload = json.loads(preflight_output_path.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["blocker_count"] == 0


def test_runtime_cli_builds_selected_period_manifests(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/historical_panel")
    data_root = tmp_path / "qualification_sources"
    for period_id in (
        "smoke_recent_5_sessions",
        "recent_medium_replay_window",
        "historical_contract_stability_window",
    ):
        period_dir = data_root / period_id
        period_dir.mkdir(parents=True)
        for file_name in (
            "ohlcv.csv",
            "symbol_reference.csv",
            "corporate_actions.csv",
            "earnings_events.csv",
        ):
            shutil.copyfile(fixture_root / file_name, period_dir / file_name)
    input_plan_path = tmp_path / "selected_period_data_inputs.yaml"
    manifest_root = tmp_path / "manifests"
    summary_path = tmp_path / "manifest_summary.json"

    runner = CliRunner()
    build_input_invocation = runner.invoke(
        app,
        [
            "build-selected-period-data-input-plan",
            "--data-root",
            str(data_root),
            "--output",
            str(input_plan_path),
        ],
    )
    manifest_invocation = runner.invoke(
        app,
        [
            "build-selected-period-manifests",
            "--input-plan",
            str(input_plan_path),
            "--output-root",
            str(manifest_root),
            "--summary-output",
            str(summary_path),
        ],
    )

    assert build_input_invocation.exit_code == 0, build_input_invocation.stdout
    assert manifest_invocation.exit_code == 0, manifest_invocation.stdout
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["manifest_count"] == 3
    for period_id, manifest_path in summary["manifest_paths"].items():
        manifest = load_historical_panel_manifest(manifest_path)
        validation = validate_historical_panel_manifest(manifest_path)
        assert manifest.panel_id == period_id
        assert validation.status is ReviewStatus.PASS


def test_runtime_cli_indexes_qualification_evidence(tmp_path: Path) -> None:
    output_path = tmp_path / "qualification_evidence_index.json"

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "index-qualification-evidence",
            "--evidence-root",
            str(tmp_path / "empty_evidence"),
            "--output",
            str(output_path),
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["baseline_id"] == "swing_machine_v0_1"
    assert payload["all_required_present"] is False
    assert payload["missing_required_count"] == 30


def test_runtime_cli_summarizes_review_run_trends(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'review_trends.db'}"
    history = build_runtime_run_history(database_url=database_url)
    history.record_run(
        command="run-cycle",
        status="SUCCEEDED",
        started_at=datetime(2026, 4, 23, 16, 0),
        metrics={"submitted_count": 1},
    )
    history.record_run(
        command="run-review-report",
        status="SUCCEEDED",
        started_at=datetime(2026, 4, 24, 16, 0),
        output_path="output/review_pass.json",
        metrics={
            "review_status": "PASS",
            "review_check_warn_count": 0,
            "review_check_fail_count": 0,
            "non_pass_review_check_count": 0,
            "non_pass_review_checks": [],
            "latest_window_metrics": {
                "window": "5d",
                "paper_shadow_alignment_rate": 1.0,
                "paper_shadow_divergent_count": 0,
                "shadow_missing_market_data_count": 0,
                "shadow_slippage_alert_rate": 0.0,
            },
            "rolling_window_metrics": [
                {
                    "window": "5d",
                    "paper_shadow_record_count": 3,
                    "paper_shadow_alignment_rate": 1.0,
                    "paper_shadow_divergent_count": 0,
                    "shadow_comparison_count": 3,
                    "shadow_missing_market_data_count": 0,
                    "shadow_slippage_alert_rate": 0.0,
                }
            ],
        },
    )
    history.record_run(
        command="run-review-report",
        status="SUCCEEDED",
        started_at=datetime(2026, 4, 25, 16, 0),
        output_path="output/review_warn.json",
        metrics={
            "review_status": "WARN",
            "review_check_warn_count": 2,
            "review_check_fail_count": 0,
            "non_pass_review_check_count": 2,
            "non_pass_review_checks": [
                {"category": "paper_shadow_alignment_rate", "status": "WARN"},
                {"category": "paper_shadow_divergent_count", "status": "WARN"},
            ],
            "latest_window_metrics": {
                "window": "5d",
                "paper_shadow_alignment_rate": 0.8,
                "paper_shadow_divergent_count": 1,
                "shadow_missing_market_data_count": 0,
                "shadow_slippage_alert_rate": 0.1,
            },
            "rolling_window_metrics": [
                {
                    "window": "5d",
                    "paper_shadow_record_count": 5,
                    "paper_shadow_alignment_rate": 0.8,
                    "paper_shadow_divergent_count": 1,
                    "shadow_comparison_count": 5,
                    "shadow_missing_market_data_count": 0,
                    "shadow_slippage_alert_rate": 0.1,
                }
            ],
        },
    )
    output_path = tmp_path / "review_trends.json"

    invocation = CliRunner().invoke(
        app,
        [
            "summarize-review-run-trends",
            "--output",
            str(output_path),
            "--database-url",
            database_url,
            "--limit",
            "10",
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["source_command"] == "run-review-report"
    assert payload["source_run_limit"] == 10
    assert payload["run_count"] == 2
    assert payload["status_counts"]["PASS"] == 1
    assert payload["status_counts"]["WARN"] == 1
    assert payload["latest_run"]["review_status"] == "WARN"
    assert payload["non_pass_review_check_total"] == 2
    assert payload["average_non_pass_review_check_count"] == 1.0
    assert payload["non_pass_category_counts"] == {
        "paper_shadow_alignment_rate": 1,
        "paper_shadow_divergent_count": 1,
    }
    five_day_trend = payload["window_metric_trends"]["5d"]
    assert five_day_trend["sample_count"] == 2
    assert five_day_trend["latest"]["paper_shadow_alignment_rate"] == 0.8
    assert five_day_trend["averages"]["paper_shadow_alignment_rate"] == 0.9
    assert five_day_trend["maximums"]["paper_shadow_divergent_count"] == 1.0
