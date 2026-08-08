#!/usr/bin/env python3
"""Build and validate the offline MPS feature-ready research panel."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from swingmachine.mps_config import load_mps_config
from swingmachine.mps_features import REQUIRED_COLUMNS, compute_mps_features

ELIGIBILITY_REQUIRED_COLUMNS = REQUIRED_COLUMNS.intersection(
    {"security_id", "ticker", "open", "high", "low", "close", "volume"}
) | {
    "trading_date",
    "available_at",
    "div_cash",
    "split_factor",
    "shares_data_available",
    "shares_data_reason",
    "shares_outstanding",
    "market_cap",
}
CLASSIFICATION_REQUIRED_COLUMNS = {
    "ticker",
    "expected_exchange",
    "classification_status",
}
REFERENCE_REQUIRED_COLUMNS = {
    "security_id",
    "ticker",
    "trading_date",
    "sector",
    "sector_reference_available",
    "sector_reference_status",
    "reference_available_at",
    "reference_accession",
    "reference_form",
    "reference_period",
    "reference_filing_ticker",
    "reference_evidence_kind",
    "reference_evidence_url",
    "sic",
}
SUPPORTED_CLASSIFICATION_STATUSES = {
    "PROVEN_UNIQUE_COMMON_STOCK",
    "PROVEN_NON_COMMON",
    "AMBIGUOUS_IDENTITY",
    "NO_IDENTIFIER",
    "PROVEN_HISTORICAL_COMMON_STOCK",
    "PROVEN_HISTORICAL_NON_COMMON",
    "UNRESOLVED_HISTORICAL_CLASSIFICATION",
}
EXCHANGE_NORMALISATION = {
    "NASDAQ": "NASDAQ",
    "NYSE": "NYSE",
    "NYSE MKT": "NYSE_AMERICAN",
}
PROVEN_COMMON_STATUSES = {
    "PROVEN_UNIQUE_COMMON_STOCK",
    "PROVEN_HISTORICAL_COMMON_STOCK",
}
PROVEN_NON_COMMON_STATUSES = {
    "PROVEN_NON_COMMON",
    "PROVEN_HISTORICAL_NON_COMMON",
}
TOTAL_RETURN_BASE_VALUE = 100.0
PROVIDER_RETURN_TOLERANCE = 1e-6


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), temporary, compression="zstd")
    temporary.replace(path)


def _require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{label} missing columns: {', '.join(missing)}")


def _normalised_tickers(series: pd.Series, label: str) -> pd.Series:
    tickers = series.astype("string").str.strip().str.upper()
    if tickers.isna().any() or tickers.eq("").any():
        raise ValueError(f"{label} contains blank tickers")
    return tickers


def causal_total_return_index(frame: pd.DataFrame) -> pd.Series:
    """Build a forward-only total-return index from same-session known actions."""
    required = {"trading_date", "close", "div_cash", "split_factor"}
    _require_columns(frame, required, "total-return source")
    ordered = frame.sort_values("trading_date", kind="stable")
    close = pd.to_numeric(ordered["close"], errors="coerce").to_numpy(dtype=float)
    dividend = pd.to_numeric(ordered["div_cash"], errors="coerce").to_numpy(dtype=float)
    split = pd.to_numeric(ordered["split_factor"], errors="coerce").to_numpy(dtype=float)
    if (
        len(ordered) == 0
        or not np.isfinite(close).all()
        or not np.isfinite(dividend).all()
        or not np.isfinite(split).all()
        or (close <= 0.0).any()
        or (dividend < 0.0).any()
        or (split <= 0.0).any()
    ):
        raise ValueError("invalid close, dividend, or split values for total return")
    if dividend[0] != 0.0 or split[0] != 1.0:
        raise ValueError("first symbol row contains an action without a prior close")
    gross_returns = np.ones(len(ordered), dtype=float)
    if len(ordered) > 1:
        gross_returns[1:] = ((close[1:] + dividend[1:]) * split[1:]) / close[:-1]
    if not np.isfinite(gross_returns).all() or (gross_returns <= 0.0).any():
        raise ValueError("invalid causal total-return factor")
    values = TOTAL_RETURN_BASE_VALUE * np.cumprod(gross_returns)
    result = pd.Series(index=ordered.index, data=values, dtype=float)
    return result.reindex(frame.index)


def _metadata_rows(
    queue_document: dict[str, Any],
    tiingo_manifest: dict[str, Any],
    classifications: pd.DataFrame,
) -> pd.DataFrame:
    _require_columns(classifications, CLASSIFICATION_REQUIRED_COLUMNS, "classification")
    classification = classifications.copy()
    classification["ticker"] = _normalised_tickers(classification["ticker"], "classification")
    if classification.duplicated("ticker").any():
        raise ValueError("classification contains duplicate tickers")
    unknown_statuses = sorted(
        set(classification["classification_status"]) - SUPPORTED_CLASSIFICATION_STATUSES
    )
    if unknown_statuses:
        raise ValueError(f"unsupported classification statuses: {unknown_statuses}")

    queue_rows = {str(row["ticker"]).upper(): row for row in queue_document["selected"]}
    source_rows = {str(row["ticker"]).upper(): row for row in tiingo_manifest["source_files"]}
    source_symbols = set(source_rows)
    if not source_symbols.issubset(queue_rows):
        raise ValueError(
            f"Tiingo source symbols missing from queue: {sorted(source_symbols - set(queue_rows))}"
        )
    if set(classification["ticker"]) != source_symbols:
        raise ValueError(
            "classification cohort does not match Tiingo source cohort: "
            f"missing={sorted(source_symbols - set(classification['ticker']))}, "
            f"unexpected={sorted(set(classification['ticker']) - source_symbols)}"
        )

    rows: list[dict[str, Any]] = []
    for ticker in sorted(source_symbols):
        queue = queue_rows[ticker]
        source = source_rows[ticker]
        if str(queue["security_id"]) != str(source["security_id"]):
            raise ValueError(f"queue/source security_id mismatch for {ticker}")
        exchange = str(queue["exchange"])
        if exchange not in EXCHANGE_NORMALISATION:
            raise ValueError(f"unsupported exchange for {ticker}: {exchange}")
        rows.append(
            {
                "ticker": ticker,
                "metadata_security_id": str(queue["security_id"]),
                "company_name": str(queue["name"]),
                "primary_exchange": EXCHANGE_NORMALISATION[exchange],
                "country_of_primary_listing": "US",
                "sector": "UNKNOWN",
                "alpha_delisting_date": str(queue["alpha_delisting_date"]),
                "request_start_date": str(queue["request_start_date"]),
                "request_end_date": str(queue["request_end_date"]),
            }
        )
    metadata = pd.DataFrame(rows).merge(
        classification[["ticker", "classification_status", "expected_exchange"]],
        on="ticker",
        how="left",
        validate="one_to_one",
    )
    if (
        metadata["expected_exchange"].astype(str)
        != metadata["ticker"].map(
            {ticker: str(queue_rows[ticker]["exchange"]) for ticker in source_symbols}
        )
    ).any():
        raise ValueError("classification expected exchange does not match queue")
    return metadata


def build_feature_input_panel(
    eligibility: pd.DataFrame,
    queue_document: dict[str, Any],
    tiingo_manifest: dict[str, Any],
    classifications: pd.DataFrame,
    reference_metadata: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Add causal total return and conservative point-in-time universe metadata."""
    _require_columns(eligibility, ELIGIBILITY_REQUIRED_COLUMNS, "shares eligibility")
    prepared = eligibility.copy()
    prepared["ticker"] = _normalised_tickers(prepared["ticker"], "shares eligibility")
    prepared["session_date"] = pd.to_datetime(
        prepared["trading_date"], utc=True, errors="coerce"
    ).dt.tz_localize(None)
    if prepared["session_date"].isna().any():
        raise ValueError("shares eligibility contains invalid trading dates")
    if prepared.duplicated(["ticker", "session_date"]).any():
        raise ValueError("shares eligibility contains duplicate ticker/session rows")

    metadata = _metadata_rows(queue_document, tiingo_manifest, classifications)
    if set(prepared["ticker"]) != set(metadata["ticker"]):
        raise ValueError("shares eligibility cohort does not match metadata cohort")
    panel = prepared.merge(metadata, on="ticker", how="left", validate="many_to_one")
    if (panel["security_id"].astype(str) != panel["metadata_security_id"]).any():
        raise ValueError("price/security metadata security_id mismatch")
    if reference_metadata is None:
        panel["sector_reference_available"] = False
        panel["sector_reference_status"] = "UNAVAILABLE_NO_POINT_IN_TIME_SOURCE"
        panel["reference_available_at"] = pd.NaT
        panel["sic"] = pd.NA
        for column in (
            "reference_accession",
            "reference_form",
            "reference_period",
            "reference_filing_ticker",
            "reference_evidence_kind",
            "reference_evidence_url",
        ):
            panel[column] = pd.NA
    else:
        _require_columns(
            reference_metadata,
            REFERENCE_REQUIRED_COLUMNS,
            "reference metadata",
        )
        reference = reference_metadata[list(REFERENCE_REQUIRED_COLUMNS)].copy()
        reference["ticker"] = _normalised_tickers(
            reference["ticker"],
            "reference metadata",
        )
        if reference.duplicated(["security_id", "ticker", "trading_date"]).any():
            raise ValueError("reference metadata contains duplicate rows")
        panel = panel.drop(columns="sector").merge(
            reference,
            on=["security_id", "ticker", "trading_date"],
            how="left",
            validate="one_to_one",
        )
        if panel["sector_reference_available"].isna().any():
            raise ValueError("reference metadata coverage does not match price panel")
    panel["classification_eligible"] = panel["classification_status"].isin(PROVEN_COMMON_STATUSES)
    panel["security_type"] = np.select(
        [
            panel["classification_status"].isin(PROVEN_COMMON_STATUSES),
            panel["classification_status"].isin(PROVEN_NON_COMMON_STATUSES),
        ],
        ["common_stock", "excluded_non_common"],
        default="unresolved",
    )
    delisting_dates = pd.to_datetime(panel["alpha_delisting_date"], errors="raise")
    panel["is_delisted"] = panel["session_date"].ge(delisting_dates)
    terminal_session = panel.groupby("ticker")["session_date"].transform("max")
    panel["has_next_session_bar"] = panel["session_date"].lt(terminal_session)
    panel["is_tradable"] = (
        panel["classification_eligible"] & ~panel["is_delisted"] & panel["has_next_session_bar"]
    )
    panel["is_halted"] = False

    total_return = pd.Series(np.nan, index=panel.index, dtype=float)
    for _, indexes in panel.groupby("ticker", sort=True).groups.items():
        total_return.loc[indexes] = causal_total_return_index(panel.loc[indexes])
    panel["total_return_adjusted_close"] = total_return
    return panel.sort_values(["ticker", "session_date"], kind="stable").reset_index(drop=True)


def validate_feature_input_panel(panel: pd.DataFrame) -> dict[str, Any]:
    required = REQUIRED_COLUMNS | {
        "available_at",
        "shares_data_available",
        "shares_data_reason",
        "classification_status",
        "classification_eligible",
        "has_next_session_bar",
    }
    _require_columns(panel, required, "feature input")
    if panel.empty:
        raise ValueError("feature input is empty")
    if panel.duplicated(["security_id", "session_date"]).any():
        raise ValueError("feature input contains duplicate security_id/session rows")
    if panel.groupby("ticker")["security_id"].nunique().gt(1).any():
        raise ValueError("ticker maps to multiple security IDs")

    numeric = ["open", "high", "low", "close", "volume", "total_return_adjusted_close"]
    for column in numeric:
        values = pd.to_numeric(panel[column], errors="coerce")
        if values.isna().any() or not np.isfinite(values).all():
            raise ValueError(f"feature input contains non-finite {column}")
    if (panel[["open", "high", "low", "close"]] <= 0.0).any().any():
        raise ValueError("feature input contains non-positive OHLC")
    if (panel["volume"] < 0.0).any():
        raise ValueError("feature input contains negative volume")
    if (
        panel["high"].lt(panel[["open", "close", "low"]].max(axis=1)).any()
        or panel["low"].gt(panel[["open", "close", "high"]].min(axis=1)).any()
    ):
        raise ValueError("feature input contains inconsistent OHLC")
    if (panel["total_return_adjusted_close"] <= 0.0).any():
        raise ValueError("feature input contains non-positive total return index")

    shares_available = panel["shares_data_available"].fillna(False).astype(bool)
    shares = pd.to_numeric(panel["shares_outstanding"], errors="coerce")
    if shares.loc[shares_available].isna().any() or (shares.loc[shares_available] <= 0.0).any():
        raise ValueError("available shares rows lack positive shares")
    if shares.loc[~shares_available].notna().any():
        raise ValueError("unavailable shares rows contain shares values")
    if panel.loc[~panel["classification_eligible"], "is_tradable"].any():
        raise ValueError("unclassified or non-common symbols are tradable")
    if panel.loc[panel["is_delisted"], "is_tradable"].any():
        raise ValueError("delisted rows are tradable")
    if panel.loc[~panel["has_next_session_bar"], "is_tradable"].any():
        raise ValueError("terminal price rows are tradable")
    if not set(panel["primary_exchange"]).issubset(set(EXCHANGE_NORMALISATION.values())):
        raise ValueError("feature input contains unsupported normalized exchanges")
    if set(panel["country_of_primary_listing"]) != {"US"}:
        raise ValueError("feature input contains non-US or missing listing country")
    if panel["sector"].isna().any():
        raise ValueError("feature input contains missing sector")

    price_available = pd.to_datetime(panel["available_at"], utc=True, errors="coerce")
    if price_available.isna().any():
        raise ValueError("feature input contains invalid price availability")
    return {
        "schema_gate_pass": True,
        "row_count": len(panel),
        "symbol_count": int(panel["ticker"].nunique()),
        "start_session": panel["session_date"].min().date().isoformat(),
        "end_session": panel["session_date"].max().date().isoformat(),
        "classification_eligible_symbol_count": int(
            panel.loc[panel["classification_eligible"], "ticker"].nunique()
        ),
        "classification_blocked_symbols": sorted(
            set(panel.loc[~panel["classification_eligible"], "ticker"])
        ),
        "classification_unresolved_symbols": sorted(
            set(panel.loc[panel["security_type"].eq("unresolved"), "ticker"])
        ),
        "shares_available_row_count": int(shares_available.sum()),
        "shares_unavailable_row_count": int((~shares_available).sum()),
        "shares_fully_masked_symbols": sorted(
            panel.groupby("ticker")["shares_data_available"]
            .sum()
            .loc[lambda values: values.eq(0)]
            .index
        ),
        "static_tradable_row_count": int(panel["is_tradable"].sum()),
        "terminal_masked_row_count": int((~panel["has_next_session_bar"]).sum()),
        "unknown_sector_row_count": int(panel["sector"].eq("UNKNOWN").sum()),
        "common_unknown_sector_row_count": int(
            (panel["classification_eligible"] & panel["sector"].eq("UNKNOWN")).sum()
        ),
        "reference_available_row_count": int(
            panel["sector_reference_available"].astype(bool).sum()
        ),
        "reference_available_row_counts_by_evidence_kind": {
            str(key): int(value)
            for key, value in panel.loc[
                panel["sector_reference_available"].astype(bool),
                "reference_evidence_kind",
            ]
            .value_counts()
            .sort_index()
            .items()
        },
        "common_reference_unavailable_row_count": int(
            (
                panel["classification_eligible"] & ~panel["sector_reference_available"].astype(bool)
            ).sum()
        ),
        "halt_state_policy": "ASSUMED_FALSE_NO_POINT_IN_TIME_SOURCE",
        "reference_metadata_policy": (
            "SEC_FILING_ACCEPTANCE_TIME_FORWARD_ONLY"
            if panel["sector_reference_available"].any()
            else "RETROSPECTIVE_COHORT_METADATA_FOR_MACHINERY_VALIDATION_ONLY"
        ),
    }


def provider_return_crosscheck(
    panel: pd.DataFrame,
    provider_adjusted: pd.DataFrame,
    *,
    tolerance: float = PROVIDER_RETURN_TOLERANCE,
) -> dict[str, Any]:
    required = {
        "security_id",
        "ticker",
        "trading_date",
        "provider_adjusted_close",
    }
    _require_columns(provider_adjusted, required, "provider-adjusted prices")
    provider = provider_adjusted.copy()
    if provider.duplicated(["security_id", "ticker", "trading_date"]).any():
        raise ValueError("provider-adjusted prices contain duplicate rows")
    joined = panel.merge(
        provider[list(required)],
        on=["security_id", "ticker", "trading_date"],
        how="left",
        validate="one_to_one",
    ).sort_values(["ticker", "session_date"], kind="stable")
    adjusted_close = pd.to_numeric(joined["provider_adjusted_close"], errors="coerce")
    if adjusted_close.isna().any() or (adjusted_close <= 0.0).any():
        raise ValueError("provider-adjusted close coverage is incomplete or invalid")
    groups = joined.groupby("ticker", sort=False)
    derived_return = joined["total_return_adjusted_close"] / groups[
        "total_return_adjusted_close"
    ].shift(1)
    provider_return = adjusted_close / groups["provider_adjusted_close"].shift(1)
    comparable = derived_return.notna() & provider_return.notna()
    difference = (derived_return - provider_return).abs()
    mismatch = comparable & difference.gt(tolerance)
    scale = adjusted_close / joined["close"]
    precision_row = pd.Series(False, index=joined.index)
    for _, indexes in joined.groupby("ticker", sort=False).groups.items():
        ordered_indexes = list(indexes)
        for position in range(1, len(ordered_indexes) - 1):
            index = ordered_indexes[position]
            previous_index = ordered_indexes[position - 1]
            next_index = ordered_indexes[position + 1]
            if (
                float(joined.at[index, "div_cash"]) != 0.0
                or float(joined.at[index, "split_factor"]) != 1.0
                or not np.isclose(
                    scale.at[previous_index],
                    scale.at[next_index],
                    rtol=0.0,
                    atol=1e-12,
                )
            ):
                continue
            reference_scale = float((scale.at[previous_index] + scale.at[next_index]) / 2.0)
            provider_implied_raw_close = float(adjusted_close.at[index]) / reference_scale
            raw_close_difference = abs(
                provider_implied_raw_close - float(joined.at[index, "close"])
            )
            if np.isclose(
                raw_close_difference,
                0.005,
                rtol=0.0,
                atol=1e-9,
            ):
                precision_row.at[index] = True
    prior_precision_row = precision_row.groupby(joined["ticker"], sort=False).shift(
        1, fill_value=False
    )
    precision_explained = mismatch & (precision_row | prior_precision_row)
    unexplained = mismatch & ~precision_explained
    next_mismatch = mismatch.groupby(joined["ticker"], sort=False).shift(-1, fill_value=False)
    explanatory_precision_row = precision_row & (mismatch | next_mismatch)
    mismatch_rows = [
        {
            "ticker": str(joined.at[index, "ticker"]),
            "trading_date": str(joined.at[index, "trading_date"]),
            "derived_return_factor": float(derived_return.at[index]),
            "provider_return_factor": float(provider_return.at[index]),
            "absolute_difference": float(difference.at[index]),
        }
        for index in difference.loc[mismatch].sort_values(ascending=False).index[:25]
    ]
    return {
        "tolerance": tolerance,
        "comparable_return_count": int(comparable.sum()),
        "within_tolerance_count": int((comparable & ~mismatch).sum()),
        "mismatch_count": int(mismatch.sum()),
        "mismatch_symbols": sorted(set(joined.loc[mismatch, "ticker"])),
        "precision_explained_mismatch_count": int(precision_explained.sum()),
        "unexplained_mismatch_count": int(unexplained.sum()),
        "unexplained_mismatch_symbols": sorted(set(joined.loc[unexplained, "ticker"])),
        "precision_rows": [
            {
                "ticker": str(joined.at[index, "ticker"]),
                "trading_date": str(joined.at[index, "trading_date"]),
                "raw_close": float(joined.at[index, "close"]),
                "provider_adjusted_close": float(adjusted_close.at[index]),
                "explanation": "RAW_CLOSE_HALF_CENT_ROUNDING",
            }
            for index in explanatory_precision_row.loc[explanatory_precision_row].index
        ],
        "maximum_absolute_difference": float(difference.loc[comparable].max()),
        "crosscheck_gate_pass": not unexplained.any(),
        "mismatch_rows": mismatch_rows,
    }


def _verified_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    eligibility_summary = json.loads(args.shares_eligibility_summary.read_text(encoding="utf-8"))
    tiingo_manifest = json.loads(args.tiingo_manifest.read_text(encoding="utf-8"))
    classification_summary = json.loads(args.classification_summary.read_text(encoding="utf-8"))
    reference_summary = None
    if (args.reference_metadata is None) != (args.reference_metadata_summary is None):
        raise ValueError(
            "reference metadata and reference metadata summary must be supplied together"
        )
    if args.reference_metadata_summary is not None:
        reference_summary = json.loads(args.reference_metadata_summary.read_text(encoding="utf-8"))
    checks = {
        "shares_eligibility": (
            file_sha256(args.shares_eligibility),
            eligibility_summary["output"]["sha256"],
        ),
        "queue": (file_sha256(args.queue), tiingo_manifest["queue_sha256"]),
        "tradable_prices": (
            eligibility_summary["inputs"]["prices"]["sha256"],
            tiingo_manifest["output_sha256"]["tradable_prices.parquet"],
        ),
        "corporate_actions": (
            eligibility_summary["inputs"]["corporate_actions"]["sha256"],
            tiingo_manifest["output_sha256"]["corporate_action_events.parquet"],
        ),
        "classification": (
            file_sha256(args.classification),
            classification_summary["output"]["sha256"],
        ),
        "classification_queue": (
            file_sha256(args.queue),
            classification_summary["input_queue"]["sha256"],
        ),
        "provider_adjusted": (
            file_sha256(args.provider_adjusted),
            tiingo_manifest["output_sha256"]["provider_adjusted_prices.parquet"],
        ),
    }
    if reference_summary is not None:
        checks.update(
            {
                "reference_metadata": (
                    file_sha256(args.reference_metadata),
                    reference_summary["output"]["sha256"],
                ),
                "reference_classification": (
                    file_sha256(args.classification),
                    reference_summary["inputs"]["classification"]["sha256"],
                ),
                "reference_eligibility": (
                    file_sha256(args.shares_eligibility),
                    reference_summary["inputs"]["eligibility"]["sha256"],
                ),
            }
        )
    failed = {
        label: {"observed": observed, "expected": expected}
        for label, (observed, expected) in checks.items()
        if observed != expected
    }
    if failed:
        raise ValueError(f"input provenance hash mismatch: {failed}")
    return eligibility_summary, tiingo_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shares-eligibility", type=Path, required=True)
    parser.add_argument("--shares-eligibility-summary", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--tiingo-manifest", type=Path, required=True)
    parser.add_argument("--classification", type=Path, required=True)
    parser.add_argument("--classification-summary", type=Path, required=True)
    parser.add_argument("--reference-metadata", type=Path)
    parser.add_argument("--reference-metadata-summary", type=Path)
    parser.add_argument("--provider-adjusted", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config/mps_1.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    eligibility_summary, tiingo_manifest = _verified_inputs(args)
    queue_document = json.loads(args.queue.read_text(encoding="utf-8"))
    eligibility = pq.read_table(args.shares_eligibility).to_pandas()
    classifications = pq.read_table(args.classification).to_pandas()
    reference_metadata = (
        None
        if args.reference_metadata is None
        else pq.read_table(args.reference_metadata).to_pandas()
    )
    provider_adjusted = pq.read_table(args.provider_adjusted).to_pandas()
    panel = build_feature_input_panel(
        eligibility,
        queue_document,
        tiingo_manifest,
        classifications,
        reference_metadata,
    )
    validation = validate_feature_input_panel(panel)
    crosscheck = provider_return_crosscheck(panel, provider_adjusted)

    input_path = args.output / "mps_feature_input_panel.parquet"
    atomic_parquet(panel, input_path)
    config = load_mps_config(args.config)
    features = compute_mps_features(panel, config)
    invalid_eligibility = features["eligible_universe"] & (
        ~features["shares_data_available"]
        | ~features["classification_eligible"]
        | ~features["is_tradable"]
        | features["is_halted"]
        | features["is_delisted"]
    )
    if invalid_eligibility.any():
        raise ValueError("computed features contain rows that bypass fail-closed gates")
    features_path = args.output / "mps_computed_features.parquet"
    atomic_parquet(features, features_path)

    eligible = features["eligible_universe"].astype(bool)
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "purpose": "MPS_FEATURE_READY_MACHINERY_VALIDATION",
        **validation,
        "total_return_policy": (
            "CAUSAL_FORWARD_INDEX_USING_((CLOSE+DIV_CASH)*SPLIT_FACTOR)/PRIOR_CLOSE"
        ),
        "provider_total_return_crosscheck": crosscheck,
        "computed_feature_row_count": len(features),
        "eligible_universe_row_count": int(eligible.sum()),
        "symbols_with_eligible_universe_rows": int(features.loc[eligible, "ticker"].nunique()),
        "metadata_gates": {
            "common_stock_gate_pass": (not validation["classification_unresolved_symbols"]),
            "sector_gate_pass": validation["common_unknown_sector_row_count"] == 0,
            "halt_state_gate_pass": False,
            "historical_reference_windows_gate_pass": (
                validation["common_reference_unavailable_row_count"] == 0
            ),
            "shares_source_gate_pass": eligibility_summary["source_gate_pass"],
            "total_return_crosscheck_gate_pass": crosscheck["crosscheck_gate_pass"],
        },
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY",
        "config": {
            "path": str(args.config),
            "sha256": file_sha256(args.config),
            "config_hash": config.config_hash(),
        },
        "inputs": {
            "shares_eligibility": {
                "path": str(args.shares_eligibility),
                "sha256": file_sha256(args.shares_eligibility),
            },
            "shares_eligibility_summary": {
                "path": str(args.shares_eligibility_summary),
                "sha256": file_sha256(args.shares_eligibility_summary),
            },
            "queue": {"path": str(args.queue), "sha256": file_sha256(args.queue)},
            "tiingo_manifest": {
                "path": str(args.tiingo_manifest),
                "sha256": file_sha256(args.tiingo_manifest),
            },
            "classification": {
                "path": str(args.classification),
                "sha256": file_sha256(args.classification),
            },
            "classification_summary": {
                "path": str(args.classification_summary),
                "sha256": file_sha256(args.classification_summary),
            },
            **(
                {
                    "reference_metadata": {
                        "path": str(args.reference_metadata),
                        "sha256": file_sha256(args.reference_metadata),
                    },
                    "reference_metadata_summary": {
                        "path": str(args.reference_metadata_summary),
                        "sha256": file_sha256(args.reference_metadata_summary),
                    },
                }
                if args.reference_metadata is not None
                else {}
            ),
            "provider_adjusted": {
                "path": str(args.provider_adjusted),
                "sha256": file_sha256(args.provider_adjusted),
            },
        },
        "outputs": {
            "feature_input": {
                "path": str(input_path),
                "sha256": file_sha256(input_path),
            },
            "computed_features": {
                "path": str(features_path),
                "sha256": file_sha256(features_path),
            },
        },
    }
    summary_path = args.output / "mps_feature_ready_summary.json"
    atomic_write(
        summary_path,
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
