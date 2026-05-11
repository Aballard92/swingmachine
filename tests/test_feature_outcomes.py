from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from swingmachine.enums import ReviewStatus
from swingmachine.feature_outcomes import (
    build_accepted_excess_distribution_report,
    build_accepted_vs_near_miss_report,
    build_exit_path_diagnostic_report,
    build_feature_outcome_attribution_dataset,
    build_feature_snapshot_bucket_report,
    build_pattern_specific_benchmark_diagnostic_report,
    build_traded_lifecycle_decomposition_report,
    write_accepted_excess_distribution_report,
    write_accepted_vs_near_miss_report,
    write_exit_path_diagnostic_report,
    write_feature_outcome_attribution_dataset,
    write_feature_snapshot_bucket_report,
    write_pattern_specific_benchmark_diagnostic_report,
    write_traded_lifecycle_decomposition_report,
)

HISTORICAL_PANEL_FIXTURE = Path("tests/fixtures/historical_panel")


def test_feature_outcome_attribution_joins_trades_and_forward_returns(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    trade_ledger_path = _write_trade_ledger(tmp_path)
    feature_snapshot_path = _write_feature_snapshot(tmp_path)

    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        lifecycle_trade_ledger_path=trade_ledger_path,
        feature_snapshot_path=feature_snapshot_path,
        feature_snapshot_fields=("rs_vs_benchmark_20", "relative_rebound_20"),
        manifest_path=manifest_path,
        benchmark_symbol="BBB",
        forward_windows=(1, 5),
    )

    assert dataset.summary.panel_id == "tiny-historical-panel-v1"
    assert dataset.summary.row_count == 2
    assert dataset.summary.accepted_count == 1
    assert dataset.summary.rejected_count == 1
    assert dataset.summary.traded_count == 1
    accepted = dataset.rows[0]
    rejected = dataset.rows[1]
    assert accepted.traded is True
    assert accepted.trade_id == "trade-1"
    assert accepted.net_pnl == pytest.approx(97.5)
    assert accepted.forward_close_returns["1"] == pytest.approx(103.50 / 104.00 - 1.0)
    assert accepted.forward_close_returns["5"] == pytest.approx(105.40 / 104.00 - 1.0)
    benchmark_1d = 52.10 / 52.20 - 1.0
    assert accepted.benchmark_forward_close_returns["1"] == pytest.approx(benchmark_1d)
    assert accepted.forward_close_excess_returns["1"] == pytest.approx(
        accepted.forward_close_returns["1"] - benchmark_1d
    )
    assert accepted.feature_snapshot["rs_vs_benchmark_20"] == pytest.approx(0.03)
    assert accepted.feature_snapshot["relative_rebound_20"] == pytest.approx(0.02)
    assert rejected.traded is False
    assert rejected.rejection_reasons == ("MA50_NOT_ABOVE_MA200",)


def test_feature_outcome_attribution_writer_outputs_artifacts(tmp_path: Path) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        manifest_path=manifest_path,
        forward_windows=(1,),
    )

    paths = write_feature_outcome_attribution_dataset(dataset, tmp_path / "outcomes")

    assert set(paths) == {"dataset", "rows_csv", "summary_markdown"}
    assert json.loads(Path(paths["dataset"]).read_text())["summary"]["row_count"] == 2
    assert "forward_close_return_1d" in Path(paths["rows_csv"]).read_text()
    assert "forward_close_excess_return_1d" in Path(paths["rows_csv"]).read_text()
    assert "Feature Outcome Attribution Dataset" in Path(paths["summary_markdown"]).read_text()


def test_accepted_vs_near_miss_report_summarizes_forward_returns(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    trade_ledger_path = _write_trade_ledger(tmp_path)
    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        lifecycle_trade_ledger_path=trade_ledger_path,
        manifest_path=manifest_path,
        benchmark_symbol="BBB",
        forward_windows=(1, 5),
    )

    report = build_accepted_vs_near_miss_report(
        dataset,
        report_id="unit-report",
        near_miss_score_floor=0.50,
    )

    assert report.report_id == "unit-report"
    assert report.accepted.row_count == 1
    assert report.near_miss.row_count == 0
    assert report.by_score_bucket["score_090_100"].accepted_count == 1
    assert report.by_rejection_reason["MA50_NOT_ABOVE_MA200"].row_count == 1
    assert report.conclusion == "INSUFFICIENT_FORWARD_RETURN_EVIDENCE"


def test_accepted_vs_near_miss_report_writer_outputs_artifacts(tmp_path: Path) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        manifest_path=manifest_path,
        forward_windows=(1,),
    )
    report = build_accepted_vs_near_miss_report(dataset, report_id="unit-report")

    paths = write_accepted_vs_near_miss_report(report, tmp_path / "near_miss")

    assert set(paths) == {"report", "summary_markdown"}
    assert json.loads(Path(paths["report"]).read_text())["report_id"] == "unit-report"
    assert "Accepted Versus Near-Miss Report" in Path(paths["summary_markdown"]).read_text()


def test_feature_snapshot_bucket_report_summarizes_feature_buckets(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    feature_snapshot_path = _write_feature_snapshot(tmp_path)
    trade_ledger_path = _write_trade_ledger(tmp_path)
    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        lifecycle_trade_ledger_path=trade_ledger_path,
        feature_snapshot_path=feature_snapshot_path,
        feature_snapshot_fields=("rs_vs_benchmark_20",),
        manifest_path=manifest_path,
        benchmark_symbol="BBB",
        forward_windows=(1,),
    )

    report = build_feature_snapshot_bucket_report(
        dataset,
        report_id="unit-feature-buckets",
        bucket_fields=("rs_vs_benchmark_20",),
    )

    assert report.report_id == "unit-feature-buckets"
    rs_buckets = report.by_feature_bucket["rs_vs_benchmark_20"]
    assert rs_buckets["rs_vs_benchmark_20:2_to_5pct"].accepted_count == 1
    assert rs_buckets["rs_vs_benchmark_20:2_to_5pct"].accepted_only.row_count == 1
    assert rs_buckets["rs_vs_benchmark_20:2_to_5pct"].traded_only.trade_count == 1
    assert rs_buckets["rs_vs_benchmark_20:2_to_5pct"].traded_only.net_pnl == pytest.approx(
        97.5
    )
    assert rs_buckets["rs_vs_benchmark_20:2_to_5pct"].sample_grade == "INSUFFICIENT"
    assert rs_buckets["rs_vs_benchmark_20:lt_0"].rejected_count == 1


def test_feature_snapshot_bucket_report_writer_outputs_artifacts(tmp_path: Path) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    feature_snapshot_path = _write_feature_snapshot(tmp_path)
    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        feature_snapshot_path=feature_snapshot_path,
        feature_snapshot_fields=("rs_vs_benchmark_20",),
        manifest_path=manifest_path,
        benchmark_symbol="BBB",
        forward_windows=(1,),
    )
    report = build_feature_snapshot_bucket_report(dataset, report_id="unit-feature-buckets")

    paths = write_feature_snapshot_bucket_report(report, tmp_path / "feature_buckets")

    assert set(paths) == {"report", "summary_markdown"}
    payload = json.loads(Path(paths["report"]).read_text())
    assert payload["report_id"] == "unit-feature-buckets"
    assert payload["sample_guardrails"]["min_robust_accepted_rows"] == 30
    assert "Feature Snapshot Bucket Report" in Path(paths["summary_markdown"]).read_text()


def test_accepted_excess_distribution_report_summarizes_populations(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        manifest_path=manifest_path,
        benchmark_symbol="BBB",
        forward_windows=(1,),
    )

    report = build_accepted_excess_distribution_report(
        dataset,
        report_id="unit-distribution",
        near_miss_score_floor=0.50,
    )

    accepted = report.populations["accepted"]["1"]
    rejected = report.populations["rejected"]["1"]
    assert report.report_id == "unit-distribution"
    assert accepted.row_count == 1
    assert accepted.observed_count == 1
    assert accepted.mean is not None
    assert rejected.row_count == 1
    assert report.conclusion == "INSUFFICIENT_20D_DISTRIBUTION_EVIDENCE"


def test_accepted_excess_distribution_report_writer_outputs_artifacts(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        manifest_path=manifest_path,
        benchmark_symbol="BBB",
        forward_windows=(1,),
    )
    report = build_accepted_excess_distribution_report(dataset, report_id="unit-distribution")

    paths = write_accepted_excess_distribution_report(report, tmp_path / "distribution")

    assert set(paths) == {"report", "summary_markdown"}
    assert json.loads(Path(paths["report"]).read_text())["report_id"] == "unit-distribution"
    assert "Accepted Candidate Excess-Return Distribution Report" in Path(
        paths["summary_markdown"]
    ).read_text()


def test_traded_lifecycle_decomposition_report_summarizes_trades(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    trade_ledger_path = _write_trade_ledger(tmp_path)
    feature_snapshot_path = _write_feature_snapshot(tmp_path)
    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        lifecycle_trade_ledger_path=trade_ledger_path,
        feature_snapshot_path=feature_snapshot_path,
        feature_snapshot_fields=("rs_vs_benchmark_20",),
        manifest_path=manifest_path,
        benchmark_symbol="BBB",
        forward_windows=(1,),
    )

    report = build_traded_lifecycle_decomposition_report(
        dataset,
        report_id="unit-lifecycle",
        feature_bucket_fields=("rs_vs_benchmark_20",),
    )

    assert report.report_id == "unit-lifecycle"
    assert report.trade_count == 1
    assert report.overall.net_pnl == pytest.approx(97.5)
    assert report.by_setup_type["PULLBACK"].trade_count == 1
    assert report.by_exit_reason["TRAIL_STOP"].winning_trade_count == 1
    assert report.by_bars_held_bucket["bars_held:001_003"].average_bars_held == 3
    assert (
        report.by_feature_bucket["rs_vs_benchmark_20"]["rs_vs_benchmark_20:2_to_5pct"].net_pnl
        == pytest.approx(97.5)
    )


def test_traded_lifecycle_decomposition_report_writer_outputs_artifacts(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    trade_ledger_path = _write_trade_ledger(tmp_path)
    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        lifecycle_trade_ledger_path=trade_ledger_path,
        manifest_path=manifest_path,
        benchmark_symbol="BBB",
        forward_windows=(1,),
    )
    report = build_traded_lifecycle_decomposition_report(dataset, report_id="unit-lifecycle")

    paths = write_traded_lifecycle_decomposition_report(report, tmp_path / "lifecycle")

    assert set(paths) == {"report", "summary_markdown"}
    assert json.loads(Path(paths["report"]).read_text())["report_id"] == "unit-lifecycle"
    assert "Traded Lifecycle Outcome Decomposition" in Path(
        paths["summary_markdown"]
    ).read_text()


def test_exit_path_diagnostic_report_computes_post_exit_returns(tmp_path: Path) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    trade_ledger_path = _write_trade_ledger(tmp_path)
    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        lifecycle_trade_ledger_path=trade_ledger_path,
        manifest_path=manifest_path,
        benchmark_symbol="BBB",
        forward_windows=(1,),
    )

    report = build_exit_path_diagnostic_report(
        dataset,
        report_id="unit-exit-path",
        benchmark_symbol="BBB",
        forward_windows=(1,),
    )

    diagnostic = report.trades[0]
    assert report.report_id == "unit-exit-path"
    assert report.trade_count == 1
    assert report.winner_count == 1
    assert diagnostic.post_exit_forward_returns["1"] == pytest.approx(103.10 / 103.00 - 1.0)
    assert diagnostic.post_exit_benchmark_returns["1"] == pytest.approx(52.00 / 51.90 - 1.0)
    assert diagnostic.post_exit_excess_returns["1"] == pytest.approx(
        diagnostic.post_exit_forward_returns["1"] - diagnostic.post_exit_benchmark_returns["1"]
    )


def test_exit_path_diagnostic_report_writer_outputs_artifacts(tmp_path: Path) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    trade_ledger_path = _write_trade_ledger(tmp_path)
    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        lifecycle_trade_ledger_path=trade_ledger_path,
        manifest_path=manifest_path,
        benchmark_symbol="BBB",
        forward_windows=(1,),
    )
    report = build_exit_path_diagnostic_report(dataset, report_id="unit-exit-path")

    paths = write_exit_path_diagnostic_report(report, tmp_path / "exit_path")

    assert set(paths) == {"report", "summary_markdown"}
    assert json.loads(Path(paths["report"]).read_text())["report_id"] == "unit-exit-path"
    assert "Exit Path Diagnostic Report" in Path(paths["summary_markdown"]).read_text()


def test_pattern_specific_benchmark_diagnostic_report_summarizes_patterns(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    trade_ledger_path = _write_trade_ledger(tmp_path)
    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        lifecycle_trade_ledger_path=trade_ledger_path,
        manifest_path=manifest_path,
        benchmark_symbol="BBB",
        forward_windows=(1, 20),
    )

    report = build_pattern_specific_benchmark_diagnostic_report(
        dataset,
        report_id="unit-patterns",
    )

    pullback = report.patterns["PULLBACK"]
    assert report.report_id == "unit-patterns"
    assert report.pattern_count == 2
    assert pullback.accepted_count == 1
    assert pullback.traded_count == 1
    assert pullback.traded_lifecycle.net_pnl == pytest.approx(97.5)
    assert pullback.sample_grade == "INSUFFICIENT"
    assert pullback.recommendation == "INSUFFICIENT_SAMPLE_FOR_PATTERN_DECISION"
    assert report.patterns["pattern_missing"].rejected_count == 1


def test_pattern_specific_benchmark_diagnostic_report_writer_outputs_artifacts(
    tmp_path: Path,
) -> None:
    manifest_path = _copy_panel(tmp_path)
    scanner_path = _write_scanner_material_decisions(tmp_path)
    dataset = build_feature_outcome_attribution_dataset(
        scanner_material_decisions_path=scanner_path,
        manifest_path=manifest_path,
        benchmark_symbol="BBB",
        forward_windows=(1,),
    )
    report = build_pattern_specific_benchmark_diagnostic_report(dataset, report_id="unit-patterns")

    paths = write_pattern_specific_benchmark_diagnostic_report(report, tmp_path / "patterns")

    assert set(paths) == {"report", "summary_markdown"}
    assert json.loads(Path(paths["report"]).read_text())["report_id"] == "unit-patterns"
    assert "Pattern-Specific Benchmark Diagnostic Report" in Path(
        paths["summary_markdown"]
    ).read_text()


def _copy_panel(tmp_path: Path) -> Path:
    panel_path = tmp_path / "panel"
    shutil.copytree(HISTORICAL_PANEL_FIXTURE, panel_path)
    return panel_path / "manifest.yaml"


def _write_scanner_material_decisions(tmp_path: Path) -> Path:
    path = tmp_path / "scanner_material_decisions.json"
    payload = {
        "panel_id": "tiny-historical-panel-v1",
        "status": ReviewStatus.PASS.value,
        "sessions": [
            {
                "material_decision_rows": [
                    {
                        "panel_id": "tiny-historical-panel-v1",
                        "symbol": "AAA",
                        "signal_session": "2026-04-20",
                        "next_session": "2026-04-21",
                        "candidate_id": "candidate-1",
                        "setup_id": "setup-1",
                        "signal_id": "signal-1",
                        "risk_plan_id": "risk-1",
                        "order_plan_id": "order-1",
                        "decision": "ACCEPTED_SETUP",
                        "pattern_type": "PULLBACK",
                        "candidate_score_pct": 0.975,
                        "rank": None,
                        "reason_codes": ["SETUP_VALID"],
                        "candidate_rejection_reasons": [],
                        "signal_rejection_reasons": [],
                        "risk_rejection_reasons": [],
                        "order_rejection_reasons": [],
                    },
                    {
                        "panel_id": "tiny-historical-panel-v1",
                        "symbol": "BBB",
                        "signal_session": "2026-04-20",
                        "next_session": "2026-04-21",
                        "candidate_id": "candidate-2",
                        "setup_id": None,
                        "decision": "REJECTED",
                        "pattern_type": None,
                        "candidate_score_pct": None,
                        "rank": None,
                        "reason_codes": ["MA50_NOT_ABOVE_MA200"],
                    },
                ]
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_trade_ledger(tmp_path: Path) -> Path:
    path = tmp_path / "portfolio_lifecycle_trade_ledger.json"
    payload = {
        "panel_id": "tiny-historical-panel-v1",
        "trades": [
            {
                "trade_id": "trade-1",
                "setup_id": "setup-1",
                "entry_fill_date": "2026-04-21",
                "exit_fill_date": "2026-04-24",
                "exit_reason": "TRAIL_STOP",
                "bars_held": 3,
                "net_pnl": 97.5,
                "net_return": 0.0975,
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_feature_snapshot(tmp_path: Path) -> Path:
    path = tmp_path / "feature_snapshot.csv"
    path.write_text(
        "symbol,session_date,rs_vs_benchmark_20,relative_rebound_20\n"
        "AAA,2026-04-20,0.03,0.02\n"
        "BBB,2026-04-20,-0.01,-0.02\n",
        encoding="utf-8",
    )
    return path
