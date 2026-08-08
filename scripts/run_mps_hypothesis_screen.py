#!/usr/bin/env python3
"""Execute the single authorized SWING-PC-005A sequential preflight."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from swingmachine.mps_hypothesis_screen import (
    audit_gate_zero,
    render_gate_zero_markdown,
)

DEFAULT_ROOT = Path.home() / ".local/share/swingmachine-data-staging"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    feature_root = DEFAULT_ROOT / "mps-feature-ready-001"
    gate_zero = audit_gate_zero(
        summary_path=feature_root / "mps_feature_ready_summary.json",
        feature_path=feature_root / "mps_computed_features.parquet",
        feature_input_path=feature_root / "mps_feature_input_panel.parquet",
        config_path=Path("config/mps_1.yaml"),
        corporate_actions_path=(
            DEFAULT_ROOT / "tiingo-batch-001-local-inputs" / "corporate_action_events.parquet"
        ),
        benchmark_path=None,
    )
    report = {
        "task_id": "SWING-PC-005A",
        "generated_at": datetime.now(UTC).isoformat(),
        "authorization": [
            "ACCEPT_SWING_PC_005_DESIGN_V1",
            "AUTHORISE_SWING_PC_005A_ONE_BOUNDED_OFFLINE_SCREEN_V1",
        ],
        "outcome": gate_zero["failure_outcome"] or "GATE_0_PASS",
        "gate_zero": gate_zero,
        "limitations": [
            "PARTIAL_RESEARCH_ONLY",
            "ASSUMED_FALSE_NO_POINT_IN_TIME_SOURCE",
        ],
        "authority": {
            "profile_build": False,
            "serious_qualification": False,
            "paper_trading": False,
            "live_trading": False,
            "broker_api_runtime": False,
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    json_path = args.output_dir / "mps_hypothesis_screen.json"
    markdown_path = args.output_dir / "mps_hypothesis_screen.md"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_gate_zero_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "json": str(json_path),
                "markdown": str(markdown_path),
                "outcome": report["outcome"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
