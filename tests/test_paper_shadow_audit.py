from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from swingmachine.broker import PaperBrokerAdapter
from swingmachine.config import load_strategy_config
from swingmachine.contracts import RuntimeCycleInput, SetupSnapshot
from swingmachine.entries import build_setup_snapshot
from swingmachine.enums import (
    BrokerOrderStatus,
    PaperShadowAlignmentStatus,
    PatternType,
    RegimeState,
    RuntimeMode,
)
from swingmachine.paper_shadow_audit import PaperShadowAuditService
from swingmachine.runtime import app, build_paper_shadow_audit_service, build_runtime
from swingmachine.shadow import compare_runtime_cycle_shadow_fills
from swingmachine.shadow_reviews import ShadowReviewService
from swingmachine.storage import create_database_engine, create_session_factory, initialize_database


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


def _seed_audit_history(database_url: str) -> tuple[PaperShadowAuditService, PaperBrokerAdapter]:
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    runtime = build_runtime(config, database_url=database_url)
    shadow_result = runtime.run_cycle(
        RuntimeCycleInput(
            as_of="2026-04-24T16:05:00",
            regime_state=RegimeState.RISK_ON,
            equity=100_000.0,
            last_data_at="2026-04-24T16:04:00",
            expires_at="2026-04-25T16:00:00",
            setups=(_setup_snapshot("setup-audit-1"),),
        ),
        mode=RuntimeMode.SHADOW,
    )
    runtime.run_cycle(
        RuntimeCycleInput(
            as_of="2026-04-24T16:05:00",
            regime_state=RegimeState.RISK_ON,
            equity=100_000.0,
            last_data_at="2026-04-24T16:04:00",
            expires_at="2026-04-25T16:00:00",
            setups=(_setup_snapshot("setup-audit-1"),),
        ),
        mode=RuntimeMode.PAPER,
    )

    comparison_batch = compare_runtime_cycle_shadow_fills(
        shadow_result,
        market_data=pd.DataFrame(
            {
                "symbol": ["AAA"],
                "session_date": ["2026-04-25"],
                "raw_open": [100.3],
                "raw_high": [101.0],
                "raw_low": [99.7],
                "raw_close": [100.5],
                "raw_volume": [1_000_000_000_000.0],
                "spread_bps": [60.0],
                "fx_conversion_cost_bps": [0.0],
            }
        ),
        config=config,
    )
    shadow_review_service = ShadowReviewService(
        create_session_factory(create_database_engine(database_url))
    )
    shadow_review_service.record_comparison_batch(comparison_batch)

    audit_service = build_paper_shadow_audit_service(database_url=database_url)
    engine = create_database_engine(database_url)
    initialize_database(engine)
    broker = PaperBrokerAdapter(create_session_factory(engine))
    return audit_service, broker


def test_paper_shadow_audit_service_detects_alignment_transition(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'audit.db'}"
    audit_service, broker = _seed_audit_history(database_url)

    initial_records = audit_service.load_records()
    assert len(initial_records) == 1
    assert (
        initial_records[0].alignment_status
        == PaperShadowAlignmentStatus.SHADOW_FILLED_PAPER_NOT_FILLED
    )

    broker_order_id = initial_records[0].broker_order_id
    assert broker_order_id is not None
    broker.update_order_status(broker_order_id, status=BrokerOrderStatus.FILLED)

    updated_records = audit_service.load_records()
    assert updated_records[0].alignment_status == PaperShadowAlignmentStatus.ALIGNED_FILLED


def test_paper_shadow_audit_service_keeps_immutable_snapshots(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'audit_snapshots.db'}"
    audit_service, broker = _seed_audit_history(database_url)

    first_batch_id = audit_service.record_snapshot_batch(
        audit_service.load_records(),
        recorded_at=datetime(2026, 4, 26, 9, 0),
    )

    first_records = audit_service.load_record_snapshots(snapshot_batch_id=first_batch_id)
    assert len(first_records) == 1
    assert (
        first_records[0].alignment_status
        == PaperShadowAlignmentStatus.SHADOW_FILLED_PAPER_NOT_FILLED
    )

    broker_order_id = first_records[0].broker_order_id
    assert broker_order_id is not None
    broker.update_order_status(broker_order_id, status=BrokerOrderStatus.FILLED)

    second_batch_id = audit_service.record_snapshot_batch(
        audit_service.load_records(),
        recorded_at=datetime(2026, 4, 27, 9, 0),
    )

    all_snapshots = audit_service.load_record_snapshots()
    assert len(all_snapshots) == 2
    assert [record.snapshot_batch_id for record in all_snapshots] == [
        first_batch_id,
        second_batch_id,
    ]
    assert [record.alignment_status for record in all_snapshots] == [
        PaperShadowAlignmentStatus.SHADOW_FILLED_PAPER_NOT_FILLED,
        PaperShadowAlignmentStatus.ALIGNED_FILLED,
    ]
    assert all(record.snapshot_id for record in all_snapshots)


def test_paper_shadow_audit_cli_writes_summary_json(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'audit_cli.db'}"
    _seed_audit_history(database_url)
    output_path = tmp_path / "audit_summary.json"

    runner = CliRunner()
    invocation = runner.invoke(
        app,
        [
            "summarize-paper-shadow-audit",
            "--output",
            str(output_path),
            "--database-url",
            database_url,
            "--regime-state",
            "RISK_ON",
        ],
    )

    assert invocation.exit_code == 0, invocation.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    snapshot_batch_id = payload["snapshot_batch_id"]
    assert snapshot_batch_id
    assert payload["summary"]["record_count"] == 1
    assert payload["rows"][0]["snapshot_id"]
    assert payload["rows"][0]["snapshot_batch_id"] == snapshot_batch_id
    assert (
        payload["by_alignment"][0]["alignment_status"]
        == PaperShadowAlignmentStatus.SHADOW_FILLED_PAPER_NOT_FILLED.value
    )

    snapshot_output_path = tmp_path / "audit_snapshot_summary.json"
    snapshot_invocation = runner.invoke(
        app,
        [
            "summarize-paper-shadow-audit-snapshots",
            "--output",
            str(snapshot_output_path),
            "--database-url",
            database_url,
            "--snapshot-batch-id",
            snapshot_batch_id,
        ],
    )

    assert snapshot_invocation.exit_code == 0, snapshot_invocation.stdout
    snapshot_payload = json.loads(snapshot_output_path.read_text(encoding="utf-8"))
    assert snapshot_payload["snapshot_batch_id"] == snapshot_batch_id
    assert snapshot_payload["summary"]["record_count"] == 1
    assert snapshot_payload["rows"][0]["snapshot_batch_id"] == snapshot_batch_id
