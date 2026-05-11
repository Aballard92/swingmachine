from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from swingmachine.config import load_strategy_config
from swingmachine.contracts import RuntimeCycleInput, SetupSnapshot
from swingmachine.entries import build_setup_snapshot
from swingmachine.enums import PatternType, RegimeState, RuntimeMode, ShadowFillStatus
from swingmachine.runtime import app, build_runtime, build_shadow_review_service
from swingmachine.shadow import compare_runtime_cycle_shadow_fills


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


def _shadow_comparison_batch(tmp_path: Path):
    config = load_strategy_config("swing_trading_bot_config_template_v2.yaml")
    runtime = build_runtime(
        config,
        database_url=f"sqlite+pysqlite:///{tmp_path / 'shadow_runtime.db'}",
    )
    result = runtime.run_cycle(
        RuntimeCycleInput(
            as_of="2026-04-24T16:05:00",
            regime_state=RegimeState.RISK_ON,
            equity=100_000.0,
            last_data_at="2026-04-24T16:04:00",
            expires_at="2026-04-25T16:00:00",
            setups=(
                _setup_snapshot("setup-review-fill", symbol="AAA"),
                _setup_snapshot("setup-review-gap", symbol="BBB"),
            ),
        ),
        mode=RuntimeMode.SHADOW,
    )
    market_data = pd.DataFrame(
        {
            "symbol": ["AAA", "BBB"],
            "session_date": ["2026-04-25", "2026-04-25"],
            "raw_open": [100.3, 102.0],
            "raw_high": [101.0, 102.5],
            "raw_low": [99.7, 101.9],
            "raw_close": [100.5, 102.1],
            "raw_volume": [1_000_000_000_000.0, 1_000_000.0],
            "spread_bps": [60.0, 0.0],
            "fx_conversion_cost_bps": [0.0, 0.0],
        }
    )
    return compare_runtime_cycle_shadow_fills(result, market_data, config)


def test_shadow_review_service_persists_and_loads_comparisons(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'shadow_reviews.db'}"
    review_service = build_shadow_review_service(database_url=database_url)
    batch = _shadow_comparison_batch(tmp_path)

    review_service.record_comparison_batch(batch)
    comparisons = review_service.load_comparisons()

    assert len(comparisons) == 2
    assert {comparison.status for comparison in comparisons} == {
        ShadowFillStatus.FILLED,
        ShadowFillStatus.OPEN_GAP_CANCELLED,
    }
    assert {comparison.source_regime_state for comparison in comparisons} == {
        RegimeState.RISK_ON,
    }


def test_shadow_review_service_summarizes_persisted_history(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'shadow_reviews_summary.db'}"
    review_service = build_shadow_review_service(database_url=database_url)
    batch = _shadow_comparison_batch(tmp_path)

    review_service.record_comparison_batch(batch)
    summary = review_service.summarize_comparisons(regime_state=RegimeState.RISK_ON)

    assert summary["summary"]["comparison_count"] == 2
    assert summary["summary"]["filled_count"] == 1
    assert summary["summary"]["cancelled_count"] == 1
    assert summary["by_regime"][0]["source_regime_state"] == RegimeState.RISK_ON.value
    assert {row["status"] for row in summary["by_status"]} == {
        ShadowFillStatus.FILLED.value,
        ShadowFillStatus.OPEN_GAP_CANCELLED.value,
    }


def test_shadow_review_service_keeps_immutable_comparison_snapshots(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'shadow_review_snapshots.db'}"
    review_service = build_shadow_review_service(database_url=database_url)
    batch = _shadow_comparison_batch(tmp_path)

    review_service.record_comparison_batch(batch, recorded_at=datetime(2026, 4, 26, 9, 0))
    review_service.record_comparison_batch(batch, recorded_at=datetime(2026, 4, 27, 9, 0))

    assert len(review_service.load_comparisons()) == 2

    snapshots = review_service.load_comparison_snapshots()
    assert len(snapshots) == 4
    assert [comparison.intent_id for comparison in snapshots].count(
        batch.comparisons[0].intent_id
    ) == 2


def test_runtime_cli_summarizes_shadow_comparison_snapshots(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'shadow_review_snapshot_cli.db'}"
    review_service = build_shadow_review_service(database_url=database_url)
    batch = _shadow_comparison_batch(tmp_path)

    review_service.record_comparison_batch(batch, recorded_at=datetime(2026, 4, 26, 9, 0))
    review_service.record_comparison_batch(batch, recorded_at=datetime(2026, 4, 27, 9, 0))

    output_path = tmp_path / "shadow_snapshot_summary.json"
    invocation = CliRunner().invoke(
        app,
        [
            "summarize-shadow-comparison-snapshots",
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
    rows = payload["rows"]
    assert payload["summary"]["comparison_count"] == 4
    assert len(rows) == 4
    assert all(row["snapshot_id"] for row in rows)
    assert {row["status"] for row in rows} == {
        ShadowFillStatus.FILLED.value,
        ShadowFillStatus.OPEN_GAP_CANCELLED.value,
    }
    recorded_at_values = {row["recorded_at"] for row in rows}
    assert any(value.startswith("2026-04-26") for value in recorded_at_values)
    assert any(value.startswith("2026-04-27") for value in recorded_at_values)
