#!/usr/bin/env python3
"""Exercise the frozen MPS research path with deterministic synthetic features.

Outputs from this script are engineering evidence only. They are deliberately
labelled so they cannot be mistaken for historical strategy qualification.
"""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

import pandas as pd

from swingmachine.mps_backtest import run_mps_backtest
from swingmachine.mps_config import load_mps_config
from swingmachine.mps_contracts import MpsVariant
from swingmachine.mps_validation import (
    ExperimentRegistry,
    annualized_sharpe,
    block_bootstrap_mean_ci,
    deflated_sharpe_ratio,
    diagnostic_as_dict,
    probability_of_backtest_overfitting,
)

SEED_DESCRIPTION = "formulaic_no_randomness_v1"


def build_feature_panel() -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-02", periods=160)
    rows: list[dict[str, object]] = []
    for symbol_index, (security_id, ticker, sector) in enumerate(
        (("SYN-A", "SYNA", "Technology"), ("SYN-B", "SYNB", "Industrials"))
    ):
        offset = symbol_index * 0.35
        for index, session in enumerate(dates):
            cycle = index % 20
            close = 100.0 + offset + index * 0.08 + (0.25 if cycle < 10 else -0.10)
            momentum_rank = 0.96 - symbol_index * 0.01 if cycle < 12 else 0.60
            rows.append(
                {
                    "security_id": security_id,
                    "ticker": ticker,
                    "session_date": session,
                    "open": close - 0.05,
                    "high": close + 1.0,
                    "low": close - 1.0,
                    "close": close,
                    "momentum_rank": momentum_rank,
                    "sma50": close - 5.0,
                    "atr20": 2.0,
                    "eligible_universe": True,
                    "trend_qualified": True,
                    "pullback_depth_atr": 1.0,
                    "recent_sma20_touch": True,
                    "close_above_prior_high": True,
                    "close_location_value": 0.80,
                    "prior_high20": close - 0.25,
                    "breakout_confirmed": True,
                    "adv20_dollars": 100_000_000.0 - symbol_index * 1_000_000.0,
                    "structure_stop": close - 3.0,
                    "sector": sector,
                }
            )
    return pd.DataFrame(rows)


def daily_returns(result: object) -> tuple[float, ...]:
    points = result.equity_curve  # type: ignore[attr-defined]
    return tuple(
        points[index].equity / points[index - 1].equity - 1.0 for index in range(1, len(points))
    )


def canonical_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config/mps_1.yaml"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    config = load_mps_config(args.config)
    panel = build_feature_panel()
    data_payload = panel.to_dict(orient="records")
    data_hash = canonical_hash(data_payload)
    regime = pd.DataFrame(
        {"session_date": sorted(panel["session_date"].unique()), "regime_multiplier": 1.0}
    )
    registry = ExperimentRegistry(args.output / "experiment_registry.jsonl")
    baseline: dict[str, dict[str, object]] = {}
    five_bps_returns: dict[str, tuple[float, ...]] = {}

    for variant in MpsVariant:
        scenario_results: dict[str, object] = {}
        for cost_bps in (5, 10, 20, 50):
            result = run_mps_backtest(
                panel,
                regime,
                config,
                variant,
                data_version_hash=data_hash,
                cost_bps=cost_bps,
            )
            returns = daily_returns(result)
            if cost_bps == 5:
                five_bps_returns[variant.value] = returns
            result_payload = result.model_dump(mode="json")
            summary = {
                "trade_count": len(result.trades),
                "ending_equity": result.equity_curve[-1].equity,
                "annualized_sharpe": annualized_sharpe(returns),
                "result_sha256": canonical_hash(result_payload),
            }
            scenario_results[str(cost_bps)] = summary
            registry.append(
                strategy_variant=variant.value,
                configuration={"config_hash": config.config_hash(), "cost_bps": cost_bps},
                data_hash=data_hash,
                status="SYNTHETIC_ENGINE_VALIDATION_ONLY",
                outcome=summary,
            )
        baseline[variant.value] = scenario_results

    reference_name = MpsVariant.B4_FULL_MPS1.value
    reference_returns = five_bps_returns[reference_name]
    reference_sharpe = annualized_sharpe(reference_returns)
    validation = {
        "block_bootstrap": diagnostic_as_dict(block_bootstrap_mean_ci(reference_returns, seed=1)),
        "deflated_sharpe": diagnostic_as_dict(
            deflated_sharpe_ratio(
                reference_sharpe or 0.0, reference_returns, trials=len(MpsVariant)
            )
        ),
        "pbo": diagnostic_as_dict(probability_of_backtest_overfitting(five_bps_returns, slices=8)),
        "parameter_neighbourhood": {
            "status": "NOT_RUN",
            "reason": "Synthetic engine evidence is not parameter-performance evidence.",
        },
        "walk_forward": {
            "status": "NOT_RUN",
            "reason": "Synthetic feature path is not an admissible historical time series.",
        },
    }
    manifest = {
        "evidence_class": "SYNTHETIC_ENGINE_VALIDATION_ONLY",
        "qualification_eligible": False,
        "profitability_claim": False,
        "formula": SEED_DESCRIPTION,
        "config_path": str(args.config),
        "config_hash": config.config_hash(),
        "data_hash": data_hash,
        "sessions": 160,
        "synthetic_securities": 2,
        "variants": [variant.value for variant in MpsVariant],
        "cost_bps": [5, 10, 20, 50],
    }
    for name, payload in (
        ("synthetic_manifest.json", manifest),
        ("synthetic_baseline_results.json", baseline),
        ("synthetic_validation_results.json", validation),
    ):
        (args.output / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
