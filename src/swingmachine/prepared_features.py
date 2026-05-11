from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from swingmachine.canonical import build_canonical_price_frame
from swingmachine.config import load_strategy_config
from swingmachine.data_contracts import (
    HistoricalPanelData,
    load_historical_panel_data,
    symbol_reference_rows_for_sessions,
    validate_historical_panel_manifest,
)
from swingmachine.features import compute_core_features
from swingmachine.regime import compute_breadth_by_session, compute_regime_snapshots
from swingmachine.signals import score_candidates

PREPARED_FEATURE_BUILDER_VERSION = "prepared_core_features_v1"
DEFAULT_EARNINGS_DISTANCE_WHEN_NO_EVENT_DATA = 9999


def build_prepared_feature_panel_from_manifest(
    manifest_path: str | Path,
    *,
    config_path: str | Path = Path("swing_trading_bot_config_template_v2.yaml"),
    feature_start_session: date | None = None,
    earnings_distance_when_no_event_data: int = DEFAULT_EARNINGS_DISTANCE_WHEN_NO_EVENT_DATA,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest_path = Path(manifest_path)
    config = load_strategy_config(config_path)
    panel_data = load_historical_panel_data(manifest_path)
    selected_feature_start = (
        feature_start_session
        or panel_data.manifest.replay_start_session
        or panel_data.manifest.start_session
    )

    canonical_by_symbol = _canonical_by_symbol(panel_data)
    benchmark_symbol = config.regime.benchmark_symbol
    if benchmark_symbol not in canonical_by_symbol:
        raise ValueError(f"benchmark symbol {benchmark_symbol} is missing from historical panel")

    benchmark = canonical_by_symbol[benchmark_symbol]
    benchmark_tr_close_index = benchmark.set_index("session_date")["tr_close_index"]
    core_frames = [
        compute_core_features(
            canonical,
            config,
            benchmark_tr_close_index=benchmark_tr_close_index,
        )
        for canonical in canonical_by_symbol.values()
    ]
    core_panel = pd.concat(core_frames, ignore_index=True)
    core_panel = core_panel.sort_values(["symbol", "session_date"]).reset_index(drop=True)
    core_panel["history_days"] = core_panel.groupby("symbol").cumcount() + 1
    core_panel["avg_daily_dollar_volume_20"] = (
        core_panel["raw_close"].astype(float)
        .mul(core_panel["raw_volume"].astype(float))
        .groupby(core_panel["symbol"])
        .rolling(window=20, min_periods=20)
        .mean()
        .reset_index(level=0, drop=True)
    )
    core_panel["regular_closes_until_earnings_event"] = _regular_closes_until_earnings_event(
        core_panel,
        panel_data.earnings_events,
        default_distance=earnings_distance_when_no_event_data,
    )

    regime = _regime_frame(core_panel, benchmark, config_path=config_path)
    scored = score_candidates(core_panel, regime, config)
    scored = scored.sort_values(["symbol", "session_date"]).reset_index(drop=True)
    scored_dates = pd.to_datetime(scored["session_date"], errors="raise").dt.date
    scored = scored.loc[scored_dates >= selected_feature_start].reset_index(drop=True)

    provenance = {
        "builder_version": PREPARED_FEATURE_BUILDER_VERSION,
        "source_manifest_path": str(manifest_path),
        "source_panel_id": panel_data.manifest.panel_id,
        "config_path": str(config_path),
        "config_hash": config.config_hash(),
        "benchmark_symbol": benchmark_symbol,
        "feature_start_session": selected_feature_start.isoformat(),
        "row_count": len(scored),
        "symbol_count": int(scored["symbol"].nunique()),
        "start_session": str(pd.to_datetime(scored["session_date"]).dt.date.min()),
        "end_session": str(pd.to_datetime(scored["session_date"]).dt.date.max()),
        "earnings_event_rows": len(panel_data.earnings_events),
        "earnings_distance_policy": (
            "computed_from_earnings_events"
            if len(panel_data.earnings_events) > 0
            else f"no_earnings_events_supplied_default_{earnings_distance_when_no_event_data}"
        ),
    }
    return scored, provenance


def write_prepared_feature_panel_for_manifest(
    manifest_path: str | Path,
    *,
    output_path: str | Path,
    config_path: str | Path = Path("swing_trading_bot_config_template_v2.yaml"),
    provenance_output_path: str | Path | None = None,
    update_manifest: bool = True,
    feature_start_session: date | None = None,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    features, provenance = build_prepared_feature_panel_from_manifest(
        manifest_path,
        config_path=config_path,
        feature_start_session=feature_start_session,
    )
    _write_feature_frame(features, output_path)
    sha256 = _sha256_file(output_path)
    provenance = {
        **provenance,
        "output_path": str(output_path),
        "output_format": _feature_file_format(output_path),
        "output_sha256": sha256,
    }

    if update_manifest:
        _update_manifest_features(
            manifest_path,
            output_path=output_path,
            row_count=len(features),
            sha256=sha256,
            feature_start_session=provenance["feature_start_session"],
        )
        validation = validate_historical_panel_manifest(manifest_path)
        provenance["updated_manifest_path"] = str(manifest_path)
        provenance["manifest_validation_status"] = validation.status.value
        provenance["manifest_validation_error_count"] = len(validation.errors)
    else:
        provenance["updated_manifest_path"] = None
        provenance["manifest_validation_status"] = None
        provenance["manifest_validation_error_count"] = None

    if provenance_output_path is not None:
        provenance_path = Path(provenance_output_path)
        provenance_path.parent.mkdir(parents=True, exist_ok=True)
        provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
        provenance["provenance_output_path"] = str(provenance_path)

    return provenance


def _canonical_by_symbol(panel_data: HistoricalPanelData) -> dict[str, pd.DataFrame]:
    ohlcv = panel_data.ohlcv.copy()
    ohlcv["session_date"] = pd.to_datetime(ohlcv["session_date"], errors="raise")
    panel = symbol_reference_rows_for_sessions(
        symbol_sessions=ohlcv,
        reference=panel_data.symbol_reference,
    )
    panel = panel.sort_values(["symbol", "session_date"]).reset_index(drop=True)
    panel["cash_dividend_per_share"] = 0.0
    panel["split_ratio"] = 1.0

    canonical_by_symbol: dict[str, pd.DataFrame] = {}
    for symbol, group in panel.groupby("symbol", sort=True):
        canonical_by_symbol[str(symbol)] = build_canonical_price_frame(group)
    return canonical_by_symbol


def _regime_frame(
    core_panel: pd.DataFrame,
    benchmark: pd.DataFrame,
    *,
    config_path: str | Path,
) -> pd.DataFrame:
    config = load_strategy_config(config_path)
    breadth = compute_breadth_by_session(core_panel, config)
    return compute_regime_snapshots(benchmark, config, breadth_by_session=breadth)


def _regular_closes_until_earnings_event(
    feature_panel: pd.DataFrame,
    earnings_events: pd.DataFrame,
    *,
    default_distance: int,
) -> pd.Series:
    if earnings_events.empty:
        return pd.Series(default_distance, index=feature_panel.index, dtype=int)

    session_dates_by_symbol = {
        symbol: tuple(pd.to_datetime(group["session_date"], errors="raise").dt.date)
        for symbol, group in feature_panel.groupby("symbol", sort=True)
    }
    events_by_symbol = {
        symbol: tuple(sorted(pd.to_datetime(group["event_date"], errors="raise").dt.date))
        for symbol, group in earnings_events.groupby("symbol", sort=True)
    }
    values: list[int] = []
    for row in feature_panel.itertuples(index=False):
        symbol = str(row.symbol)
        session_date = pd.Timestamp(row.session_date).date()
        future_events = [
            event_date
            for event_date in events_by_symbol.get(symbol, ())
            if event_date >= session_date
        ]
        if not future_events:
            values.append(default_distance)
            continue
        next_event = future_events[0]
        values.append(
            sum(
                1
                for candidate_session in session_dates_by_symbol.get(symbol, ())
                if session_date < candidate_session <= next_event
            )
        )
    return pd.Series(values, index=feature_panel.index, dtype=int)


def _write_feature_frame(features: pd.DataFrame, output_path: Path) -> None:
    output_format = _feature_file_format(output_path)
    if output_format == "csv":
        features.to_csv(output_path, index=False)
        return
    if output_format == "parquet":
        features.to_parquet(output_path, index=False)
        return
    raise ValueError(f"Unsupported feature output format: {output_format}")


def _feature_file_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix == ".parquet":
        return "parquet"
    raise ValueError("feature output path must end with .csv or .parquet")


def _update_manifest_features(
    manifest_path: Path,
    *,
    output_path: Path,
    row_count: int,
    sha256: str,
    feature_start_session: str,
) -> None:
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["feature_start_session"] = feature_start_session
    payload["files"]["features"] = {
        "path": _path_for_manifest(manifest_path, output_path, payload.get("base_path")),
        "format": _feature_file_format(output_path),
        "row_count": row_count,
        "sha256": sha256,
    }
    manifest_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _path_for_manifest(manifest_path: Path, output_path: Path, base_path: str | None) -> str:
    base = Path(base_path or ".")
    if not base.is_absolute():
        base = manifest_path.parent / base
    try:
        return str(output_path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(output_path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
