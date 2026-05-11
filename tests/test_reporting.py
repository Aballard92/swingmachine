from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from swingmachine.broker import PaperBrokerAdapter
from swingmachine.config import load_strategy_config
from swingmachine.contracts import OperatorReviewThresholds, RuntimeCycleInput, SetupSnapshot
from swingmachine.entries import build_setup_snapshot
from swingmachine.enums import (
    BrokerOrderStatus,
    PatternType,
    RegimeState,
    ReviewStatus,
    RuntimeEventType,
    RuntimeMode,
)
from swingmachine.reporting import operator_review_run_metrics
from swingmachine.review_rendering import render_operator_review_html
from swingmachine.runtime import (
    app,
    build_operator_review_report_service,
    build_paper_shadow_audit_service,
    build_rolling_audit_report_service,
    build_runtime,
    build_runtime_run_history,
)
from swingmachine.shadow import compare_runtime_cycle_shadow_fills
from swingmachine.shadow_reviews import ShadowReviewService
from swingmachine.storage import create_database_engine, create_session_factory, initialize_database
from tests.fixtures.review_scenarios import (
    REVIEW_SCENARIO_AS_OF_DATE,
    REVIEW_SCENARIO_LOOKBACK_DAYS,
    ReviewScenarioName,
    seed_review_scenario_history,
)


def _write_replay_artifact_bundle(
    replay_dir: Path,
    *,
    replay_status: str = "PASS",
    validation_status: str = "PASS",
    reconciliation_status: str = "PASS",
    trace_count: int = 1,
    failed_reconciliation_checks: int = 0,
) -> None:
    replay_dir.mkdir(parents=True, exist_ok=True)
    (replay_dir / "validation_summary.json").write_text(
        json.dumps({"panel_id": "test-panel", "status": validation_status}),
        encoding="utf-8",
    )
    (replay_dir / "replay_summary.json").write_text(
        json.dumps({"panel_id": "test-panel", "status": replay_status}),
        encoding="utf-8",
    )
    traces = [
        {
            "panel_id": "test-panel",
            "symbol": f"SYM{index}",
            "session_date": "2026-04-27",
            "decision": "ACCEPTED_SETUP",
            "reason_codes": ["SETUP_VALID"],
        }
        for index in range(trace_count)
    ]
    (replay_dir / "decision_traces.json").write_text(
        json.dumps({"panel_id": "test-panel", "status": replay_status, "traces": traces}),
        encoding="utf-8",
    )
    checks = [
        {
            "name": f"check-{index}",
            "status": "FAIL",
            "observed": 0,
            "expected": 1,
        }
        for index in range(failed_reconciliation_checks)
    ]
    if not checks:
        checks = [{"name": "setup_to_shadow_proposal_count", "status": "PASS"}]
    (replay_dir / "reconciliation_summary.json").write_text(
        json.dumps(
            {
                "panel_id": "test-panel",
                "status": reconciliation_status,
                "counts": {"setup_count": trace_count},
                "checks": checks,
            }
        ),
        encoding="utf-8",
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


def _seed_report_history(database_url: str) -> None:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    runtime = build_runtime(config, database_url=database_url)
    shadow_review_service = ShadowReviewService(
        create_session_factory(create_database_engine(database_url))
    )

    scenarios = (
        {
            "setup_id": "setup-report-old",
            "symbol": "BBB",
            "session_date": "2026-04-20",
            "as_of": "2026-04-21T16:05:00",
            "last_data_at": "2026-04-21T16:04:00",
            "expires_at": "2026-04-22T16:00:00",
            "market_session_date": "2026-04-22",
            "raw_open": 100.3,
            "raw_high": 101.0,
            "raw_low": 99.7,
            "raw_close": 100.5,
        },
        {
            "setup_id": "setup-report-recent",
            "symbol": "AAA",
            "session_date": "2026-04-23",
            "as_of": "2026-04-24T16:05:00",
            "last_data_at": "2026-04-24T16:04:00",
            "expires_at": "2026-04-25T16:00:00",
            "market_session_date": "2026-04-25",
            "raw_open": 100.3,
            "raw_high": 101.0,
            "raw_low": 99.7,
            "raw_close": 100.5,
        },
    )

    for scenario in scenarios:
        cycle_input = RuntimeCycleInput(
            as_of=scenario["as_of"],
            regime_state=RegimeState.RISK_ON,
            equity=100_000.0,
            last_data_at=scenario["last_data_at"],
            expires_at=scenario["expires_at"],
            setups=(
                _setup_snapshot(
                    scenario["setup_id"],
                    symbol=scenario["symbol"],
                    session_date=scenario["session_date"],
                ),
            ),
        )
        shadow_result = runtime.run_cycle(cycle_input, mode=RuntimeMode.SHADOW)
        runtime.run_cycle(cycle_input, mode=RuntimeMode.PAPER)

        comparison_batch = compare_runtime_cycle_shadow_fills(
            shadow_result,
            market_data=pd.DataFrame(
                {
                    "symbol": [scenario["symbol"]],
                    "session_date": [scenario["market_session_date"]],
                    "raw_open": [scenario["raw_open"]],
                    "raw_high": [scenario["raw_high"]],
                    "raw_low": [scenario["raw_low"]],
                    "raw_close": [scenario["raw_close"]],
                    "raw_volume": [1_000_000_000_000.0],
                    "spread_bps": [60.0],
                    "fx_conversion_cost_bps": [0.0],
                }
            ),
            config=config,
        )
        shadow_review_service.record_comparison_batch(comparison_batch)

    audit_service = build_paper_shadow_audit_service(database_url=database_url)
    records_by_setup = {record.setup_id: record for record in audit_service.load_records()}
    engine = create_database_engine(database_url)
    initialize_database(engine)
    broker = PaperBrokerAdapter(create_session_factory(engine))
    broker_order_id = records_by_setup["setup-report-old"].broker_order_id
    assert broker_order_id is not None
    broker.update_order_status(broker_order_id, status=BrokerOrderStatus.FILLED)

    audit_service.record_snapshot_batch(
        audit_service.load_records(),
        recorded_at=datetime(2026, 4, 24, 16, 15),
    )
    run_history = build_runtime_run_history(database_url=database_url)
    run_id = run_history.record_run(
        command="seed-report-history",
        status="SUCCEEDED",
        started_at=datetime(2026, 4, 24, 16, 5),
        completed_at=datetime(2026, 4, 24, 16, 6),
    )
    run_history.record_event(
        command="seed-report-history",
        event_type=RuntimeEventType.PAPER_ENTRY_SUBMISSION_DECIDED,
        occurred_at=datetime(2026, 4, 24, 16, 5),
        run_id=run_id,
        mode=RuntimeMode.PAPER,
        symbol="AAA",
        setup_id="setup-report-recent",
        payload={"submitted": True},
    )


def test_rolling_audit_report_service_builds_windowed_summary(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'audit_report.db'}"
    _seed_report_history(database_url)

    report = build_rolling_audit_report_service(database_url=database_url).build_report(
        as_of_date=date(2026, 4, 24),
        lookback_days=(1, 5),
        exception_limit=5,
    )

    assert [window.window.label for window in report.windows] == ["1d", "5d"]

    one_day = report.windows[0]
    assert one_day.paper_shadow_audit["summary"]["record_count"] == 1
    assert one_day.shadow_review["summary"]["comparison_count"] == 1
    assert len(one_day.recent_divergences) == 1
    assert one_day.recent_divergences[0]["setup_id"] == "setup-report-recent"

    five_day = report.windows[1]
    assert five_day.paper_shadow_audit["summary"]["record_count"] == 2
    assert five_day.paper_shadow_audit["summary"]["aligned_count"] == 1
    assert five_day.shadow_review["summary"]["comparison_count"] == 2
    assert len(five_day.recent_divergences) == 1


def test_operator_review_report_service_composes_review_surface(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'operator_review.db'}"
    _seed_report_history(database_url)

    report = build_operator_review_report_service(database_url=database_url).build_report(
        as_of_date=date(2026, 4, 24),
        lookback_days=(1, 5),
        event_limit=20,
        run_limit=10,
        exception_limit=5,
    )

    assert report.lookback_days == (1, 5)
    assert report.review_status == ReviewStatus.WARN
    assert [window.window.label for window in report.rolling_audit.windows] == ["1d", "5d"]
    assert len(report.runtime_runs) == 1
    assert len(report.decision_events) == 1
    assert report.decision_events[0]["event_type"] == "PAPER_ENTRY_SUBMISSION_DECIDED"
    assert {
        check.category for check in report.review_checks if check.status == ReviewStatus.WARN
    } >= {"paper_shadow_alignment_rate", "paper_shadow_divergent_count"}
    assert report.shadow_comparison_snapshots["summary"]["comparison_count"] == 2
    assert report.paper_shadow_audit_snapshots["summary"]["record_count"] == 2
    assert report.recent_divergences[0]["setup_id"] == "setup-report-recent"
    assert {exception["category"] for exception in report.review_exceptions} >= {
        "paper_shadow_divergence",
        "recent_divergence_rows",
    }


def test_operator_review_report_status_can_pass_with_relaxed_thresholds(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'operator_review_relaxed.db'}"
    _seed_report_history(database_url)

    report = build_operator_review_report_service(database_url=database_url).build_report(
        as_of_date=date(2026, 4, 24),
        lookback_days=(1, 5),
        event_limit=20,
        run_limit=10,
        exception_limit=5,
        review_thresholds=OperatorReviewThresholds(
            min_alignment_rate=0.0,
            max_divergent_count=1,
            max_shadow_slippage_alert_rate=1.0,
            max_missing_market_data_count=0,
        ),
    )

    assert report.review_status == ReviewStatus.PASS
    assert {check.status for check in report.review_checks} == {ReviewStatus.PASS}


def test_operator_review_report_accepts_pass_replay_artifacts(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'operator_review_replay_pass.db'}"
    replay_dir = tmp_path / "replay_pass"
    _write_replay_artifact_bundle(replay_dir)

    report = build_operator_review_report_service(database_url=database_url).build_report(
        as_of_date=date(2026, 4, 24),
        lookback_days=(1,),
        review_thresholds=OperatorReviewThresholds(
            require_runtime_runs=False,
            require_decision_events=False,
            require_shadow_snapshots=False,
            require_paper_shadow_audit_snapshots=False,
        ),
        replay_artifact_dirs=(replay_dir,),
    )

    assert report.review_status == ReviewStatus.PASS
    assert len(report.replay_artifacts) == 1
    replay_categories = {
        check.category for check in report.review_checks if check.category.startswith("replay_")
    }
    assert replay_categories >= {
        "replay_artifacts_loadable",
        "replay_status",
        "replay_validation_status",
        "replay_reconciliation_status",
        "replay_decision_trace_count",
        "replay_reconciliation_failed_checks",
    }
    assert {
        check.status for check in report.review_checks if check.category.startswith("replay_")
    } == {ReviewStatus.PASS}

    metrics = operator_review_run_metrics(report)
    assert metrics["replay_artifact_count"] == 1
    assert metrics["replay_artifact_status_counts"]["PASS"] == 1


def test_operator_review_report_fails_on_replay_artifact_problems(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'operator_review_replay_fail.db'}"
    replay_dir = tmp_path / "replay_fail"
    _write_replay_artifact_bundle(
        replay_dir,
        replay_status="FAIL",
        validation_status="FAIL",
        reconciliation_status="FAIL",
        trace_count=0,
        failed_reconciliation_checks=2,
    )

    report = build_operator_review_report_service(database_url=database_url).build_report(
        as_of_date=date(2026, 4, 24),
        lookback_days=(1,),
        review_thresholds=OperatorReviewThresholds(
            require_runtime_runs=False,
            require_decision_events=False,
            require_shadow_snapshots=False,
            require_paper_shadow_audit_snapshots=False,
        ),
        replay_artifact_dirs=(replay_dir,),
    )

    assert report.review_status == ReviewStatus.FAIL
    non_pass = {
        check.category: check for check in report.review_checks if check.status != ReviewStatus.PASS
    }
    assert non_pass["replay_status"].status is ReviewStatus.FAIL
    assert non_pass["replay_validation_status"].status is ReviewStatus.FAIL
    assert non_pass["replay_reconciliation_status"].status is ReviewStatus.FAIL
    assert non_pass["replay_decision_trace_count"].status is ReviewStatus.WARN
    assert non_pass["replay_reconciliation_failed_checks"].status is ReviewStatus.FAIL
    assert {exception["category"] for exception in report.review_exceptions} >= {
        "replay_status",
        "replay_reconciliation",
    }


@pytest.mark.parametrize(
    ("scenario_name", "expected_status", "expected_non_pass_categories"),
    [
        ("pass", ReviewStatus.PASS, set()),
        (
            "warn",
            ReviewStatus.WARN,
            {"paper_shadow_alignment_rate", "paper_shadow_divergent_count"},
        ),
        ("fail", ReviewStatus.FAIL, {"shadow_missing_market_data_count"}),
    ],
)
def test_multi_session_review_scenarios_exercise_pass_warn_fail(
    tmp_path: Path,
    scenario_name: ReviewScenarioName,
    expected_status: ReviewStatus,
    expected_non_pass_categories: set[str],
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / f'review_{scenario_name}.db'}"
    seed_review_scenario_history(database_url=database_url, scenario_name=scenario_name)

    report = build_operator_review_report_service(database_url=database_url).build_report(
        as_of_date=REVIEW_SCENARIO_AS_OF_DATE,
        lookback_days=REVIEW_SCENARIO_LOOKBACK_DAYS,
        event_limit=20,
        run_limit=10,
        exception_limit=10,
    )

    assert report.review_status == expected_status
    latest_window = report.rolling_audit.windows[0]
    assert latest_window.paper_shadow_audit["summary"]["record_count"] == 3
    assert latest_window.shadow_review["summary"]["comparison_count"] == 3
    assert report.shadow_comparison_snapshots["summary"]["comparison_count"] == 3
    assert report.paper_shadow_audit_snapshots["summary"]["record_count"] == 3
    assert len(report.decision_events) == 3

    non_pass_categories = {
        check.category for check in report.review_checks if check.status != ReviewStatus.PASS
    }
    assert expected_non_pass_categories <= non_pass_categories
    if expected_status == ReviewStatus.PASS:
        assert non_pass_categories == set()

    metrics = operator_review_run_metrics(report)
    assert metrics["review_status"] == expected_status.value
    assert metrics["latest_window_metrics"]["paper_shadow_record_count"] == 3
    assert metrics["latest_window_metrics"]["shadow_comparison_count"] == 3
    assert metrics["review_check_status_counts"][expected_status.value] >= 1
    if expected_status == ReviewStatus.PASS:
        assert metrics["non_pass_review_check_count"] == 0
    else:
        assert metrics["non_pass_review_check_count"] >= len(non_pass_categories)

    payload = report.model_dump(mode="json")
    assert payload["review_status"] == expected_status.value
    payload_non_pass_checks = [
        check for check in payload["review_checks"] if check["status"] != ReviewStatus.PASS.value
    ]
    assert expected_non_pass_categories <= {check["category"] for check in payload_non_pass_checks}
    html = render_operator_review_html(report, row_limit=50)
    assert "Review Checks" in html
    assert expected_status.value in html
    for category in expected_non_pass_categories:
        assert category in html
    if expected_status == ReviewStatus.WARN:
        assert "Paper/shadow alignment rate is below the configured threshold." in html
        assert "Paper/shadow divergent row count exceeds the configured threshold." in html
        assert "0.6667" in html
        assert "0.95" in html
    if expected_status == ReviewStatus.FAIL:
        assert "Shadow comparison missing-market-data count exceeds the threshold." in html
        assert "shadow_missing_market_data_count" in html


def test_run_audit_report_job_cli_writes_dated_and_latest_files(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'audit_report_cli.db'}"
    _seed_report_history(database_url)
    output_dir = tmp_path / "reports"

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "run-audit-report-job",
            "--output-dir",
            str(output_dir),
            "--database-url",
            database_url,
            "--as-of",
            "2026-04-24",
            "--lookback-days",
            "1,5",
            "--format",
            "json",
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout

    dated_output = output_dir / "audit_report_2026-04-24.json"
    latest_output = output_dir / "audit_report_latest.json"
    assert dated_output.exists()
    assert latest_output.exists()

    payload = json.loads(dated_output.read_text(encoding="utf-8"))
    assert payload["as_of_date"] == "2026-04-24"
    assert [window["window"]["label"] for window in payload["windows"]] == ["1d", "5d"]
    assert payload["windows"][1]["paper_shadow_audit"]["summary"]["record_count"] == 2


def test_run_review_report_cli_writes_operator_review_file(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'operator_review_cli.db'}"
    _seed_report_history(database_url)
    output_path = tmp_path / "operator_review.json"

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "run-review-report",
            "--output",
            str(output_path),
            "--database-url",
            database_url,
            "--as-of",
            "2026-04-24",
            "--lookback-days",
            "1,5",
            "--event-limit",
            "20",
            "--run-limit",
            "10",
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["as_of_date"] == "2026-04-24"
    assert payload["review_status"] == "WARN"
    assert payload["review_thresholds"]["min_alignment_rate"] == 0.95
    assert {
        check["category"] for check in payload["review_checks"] if check["status"] == "WARN"
    } >= {"paper_shadow_alignment_rate", "paper_shadow_divergent_count"}
    assert [window["window"]["label"] for window in payload["rolling_audit"]["windows"]] == [
        "1d",
        "5d",
    ]
    assert payload["shadow_comparison_snapshots"]["summary"]["comparison_count"] == 2
    assert payload["paper_shadow_audit_snapshots"]["summary"]["record_count"] == 2
    assert payload["decision_events"][0]["event_type"] == "PAPER_ENTRY_SUBMISSION_DECIDED"
    assert payload["review_exceptions"]

    runs = build_runtime_run_history(database_url=database_url).list_runs(limit=1)
    assert runs[0]["command"] == "run-review-report"
    metrics = runs[0]["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["review_status"] == "WARN"
    assert metrics["review_check_warn_count"] >= 2
    assert metrics["review_check_fail_count"] == 0
    assert metrics["non_pass_review_check_count"] >= 2
    assert metrics["latest_window_metrics"]["window"] == "1d"
    assert metrics["latest_window_metrics"]["paper_shadow_record_count"] == 1
    assert metrics["latest_window_metrics"]["paper_shadow_divergent_count"] == 1
    assert metrics["latest_window_metrics"]["shadow_slippage_alert_rate"] == 1.0
    assert metrics["rolling_window_metrics"][1]["window"] == "5d"
    assert metrics["shadow_snapshot_comparison_count"] == 2
    assert metrics["paper_shadow_audit_snapshot_record_count"] == 2

    events = build_runtime_run_history(database_url=database_url).list_events(
        limit=1,
        event_type=RuntimeEventType.REVIEW_REPORT_WRITTEN,
    )
    assert events[0]["payload"] == metrics


def test_run_review_report_cli_writes_operator_review_html(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'operator_review_html.db'}"
    _seed_report_history(database_url)
    output_path = tmp_path / "operator_review.html"

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "run-review-report",
            "--output",
            str(output_path),
            "--database-url",
            database_url,
            "--as-of",
            "2026-04-24",
            "--lookback-days",
            "1,5",
            "--format",
            "html",
            "--html-row-limit",
            "5",
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    html = output_path.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert "Swingmachine Operator Review" in html
    assert "Review Criteria" in html
    assert "Review Checks" in html
    assert "WARN" in html
    assert "Rolling Audit Windows" in html
    assert "PAPER_ENTRY_SUBMISSION_DECIDED" in html
    assert "paper_shadow_divergence" in html
    assert "setup-report-recent" in html
