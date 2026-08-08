#!/usr/bin/env python3
"""Execute the single authorized SWING-PC-006 exploratory screen."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from swingmachine.mps_limitation_screen import execute_screen, render_markdown

DEFAULT_ROOT = Path.home() / ".local/share/swingmachine-data-staging"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    feature_root = DEFAULT_ROOT / "mps-feature-ready-001"
    report = execute_screen(
        feature_path=feature_root / "mps_computed_features.parquet",
        feature_input_path=feature_root / "mps_feature_input_panel.parquet",
        summary_path=feature_root / "mps_feature_ready_summary.json",
        config_path=Path("config/mps_1.yaml"),
        corporate_actions_path=(
            DEFAULT_ROOT / "tiingo-batch-001-local-inputs" / "corporate_action_events.parquet"
        ),
    )
    generated_at = datetime.now(UTC).isoformat()
    packet = {
        **report,
        "generated_at": generated_at,
        "authorization": "Alex: Proceed, 2026-07-29",
        "network_attempts": [
            {
                "source": "Stooq",
                "result": "JAVASCRIPT_VERIFICATION_HTML_NOT_DATA",
                "response_sha256": (
                    "54f1f005853d9e7053acfbd7182f892e2ddaee23118632aba39de0313e4c578c"
                ),
            },
            {
                "source": "Yahoo chart",
                "result": "HTTP_429_NO_FILE_WRITTEN",
            },
        ],
        "execution_history": [
            {
                "identity": ("limitation_tolerant_screen_20260729T184316Z"),
                "result": ("INFRASTRUCTURE_INVALID_CROSTINI_RESTART_NO_REPORT"),
                "vm_restart": "2026-07-29T19:50:38+01:00",
                "strategy_result_exposed": False,
            }
        ],
        "authority": {
            "profile_build": False,
            "serious_qualification": False,
            "paper_trading": False,
            "live_trading": False,
            "broker_api_runtime": False,
            "further_data_acquisition": False,
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    json_path = args.output_dir / "mps_limitation_screen.json"
    markdown_path = args.output_dir / "mps_limitation_screen.md"
    json_path.write_text(
        json.dumps(packet, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_markdown(packet, generated_at),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "json": str(json_path),
                "markdown": str(markdown_path),
                "outcome": packet["outcome"],
                "holdout_opened": packet["holdout_opened"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
