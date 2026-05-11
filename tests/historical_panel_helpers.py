from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import yaml

from swingmachine.data_contracts import symbol_reference_rows_for_sessions


def build_prepared_feature_panel(panel_path: Path) -> pd.DataFrame:
    ohlcv = pd.read_csv(panel_path / "ohlcv.csv")
    reference = pd.read_csv(panel_path / "symbol_reference.csv")
    ohlcv["session_date"] = pd.to_datetime(ohlcv["session_date"], errors="raise")
    panel = symbol_reference_rows_for_sessions(symbol_sessions=ohlcv, reference=reference)
    panel = panel.sort_values(["symbol", "session_date"]).reset_index(drop=True)

    symbols = sorted(str(symbol) for symbol in panel["symbol"].unique())
    symbol_rank = {symbol: len(symbols) - index for index, symbol in enumerate(symbols)}
    symbol_count = max(len(symbols), 1)
    frames: list[pd.DataFrame] = []

    for symbol, group in panel.groupby("symbol", sort=True):
        group = group.copy().reset_index(drop=True)
        closes = group["raw_close"].astype(float)
        highs = group["raw_high"].astype(float)
        lows = group["raw_low"].astype(float)
        bias = symbol_rank[str(symbol)] / symbol_count

        group["split_adj_close"] = closes
        group["split_adj_high"] = highs
        group["split_adj_low"] = lows
        group["ma50"] = closes * 0.96
        group["ma200"] = closes * 0.87
        group["ma200_slope_pct20"] = 0.02
        group["dist_to_52w_high"] = 0.04
        group["mom_252_21"] = 0.20 + bias
        group["ret_126"] = 0.15 + bias
        group["rs_vs_benchmark_126"] = 0.08 + bias
        group["trend_quality"] = 0.70 if bias >= 1.0 else 0.50
        group["atr_14"] = (closes * 0.02).clip(lower=1.0)
        group["range_compression_ratio"] = 0.75
        group["pullback_days"] = group.index.astype(float)
        group["pullback_depth_atr"] = ((highs.cummax() - closes) / group["atr_14"]).clip(lower=0.0)
        group["anchor_high_date"] = group["session_date"].iloc[0]
        group["volume_ratio_20"] = 0.80
        group["regular_closes_until_earnings_event"] = 10
        group["history_days"] = 300 + group.index
        group["avg_daily_dollar_volume_20"] = (closes * group["raw_volume"].astype(float)).clip(
            lower=25_000_000.0
        )
        frames.append(group)

    return pd.concat(frames, ignore_index=True)


def write_prepared_feature_file(
    panel_path: Path,
    *,
    file_name: str = "features.csv",
    file_format: str = "csv",
) -> Path:
    feature_path = panel_path / file_name
    features = build_prepared_feature_panel(panel_path)
    if file_format == "csv":
        features.to_csv(feature_path, index=False)
    elif file_format == "parquet":
        features.to_parquet(feature_path, index=False)
    else:
        raise ValueError(f"Unsupported feature fixture format: {file_format}")
    return feature_path


def add_prepared_features_to_manifest(
    manifest_path: Path,
    feature_path: Path,
    *,
    file_format: str = "csv",
    sha256: str | None = None,
    feature_start_session: str | None = None,
    feature_coverage_scope: str | None = None,
) -> None:
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    try:
        feature_manifest_path = feature_path.relative_to(manifest_path.parent)
    except ValueError:
        feature_manifest_path = feature_path
    if file_format == "csv":
        features = pd.read_csv(feature_path)
    elif file_format == "parquet":
        features = pd.read_parquet(feature_path)
    else:
        raise ValueError(f"Unsupported feature fixture format: {file_format}")

    spec: dict[str, object] = {
        "path": str(feature_manifest_path),
        "format": file_format,
        "row_count": len(features),
    }
    if sha256 is not None:
        spec["sha256"] = sha256
    if feature_start_session is not None:
        payload["feature_start_session"] = feature_start_session
    if feature_coverage_scope is not None:
        payload["feature_coverage_scope"] = feature_coverage_scope
    payload["files"]["features"] = spec
    manifest_path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
