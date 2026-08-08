#!/usr/bin/env python3
"""Build an offline, point-in-time shares eligibility panel."""

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

PRICE_REQUIRED_COLUMNS = {
    "security_id",
    "ticker",
    "trading_date",
    "available_at",
    "close",
}
SHARES_REQUIRED_COLUMNS = {
    "stable_security_id",
    "ticker",
    "cik",
    "accession_compact",
    "source_available_at",
    "available_at",
    "concept",
    "period_end",
    "shares_outstanding",
    "source_kind",
    "source_priority",
    "source_sha256",
}
ACTION_REQUIRED_COLUMNS = {
    "ticker",
    "trading_date",
    "available_at",
    "split_factor",
}
CONCEPT_PRIORITY = {
    "EntityCommonStockSharesOutstanding": 0,
    "InvestmentCompanySharesOutstanding": 1,
    "CommonStockSharesOutstanding": 2,
}


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


def _accession_number(value: Any) -> int:
    digits = "".join(character for character in str(value) if character.isdigit())
    if not digits:
        raise ValueError(f"invalid accession number: {value!r}")
    return int(digits)


def resolve_effective_shares(
    shares: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Resolve one unambiguous shares fact per ticker and conservative availability."""
    _require_columns(shares, SHARES_REQUIRED_COLUMNS, "shares")
    prepared = shares.copy()
    prepared["ticker"] = _normalised_tickers(prepared["ticker"], "shares")
    unknown_concepts = sorted(set(prepared["concept"]) - set(CONCEPT_PRIORITY))
    if unknown_concepts:
        raise ValueError(f"unsupported shares concepts: {unknown_concepts}")
    prepared["_shares_fact_available_ts"] = pd.to_datetime(
        prepared["available_at"], utc=True, errors="coerce"
    )
    prepared["_shares_source_available_ts"] = pd.to_datetime(
        prepared["source_available_at"], utc=True, errors="coerce"
    )
    prepared["_shares_period_end_ts"] = pd.to_datetime(
        prepared["period_end"], utc=True, errors="coerce"
    ).dt.normalize()
    prepared["shares_outstanding"] = pd.to_numeric(prepared["shares_outstanding"], errors="coerce")
    prepared["source_priority"] = pd.to_numeric(prepared["source_priority"], errors="coerce")
    invalid = (
        prepared["_shares_fact_available_ts"].isna()
        | prepared["_shares_period_end_ts"].isna()
        | prepared["shares_outstanding"].isna()
        | ~np.isfinite(prepared["shares_outstanding"])
        | prepared["shares_outstanding"].le(0.0)
        | prepared["source_priority"].isna()
        | prepared["_shares_period_end_ts"].gt(prepared["_shares_fact_available_ts"].dt.normalize())
    )
    invalid_fact_count = int(invalid.sum())
    prepared = prepared.loc[~invalid].copy()
    prepared["_shares_source_available_ts"] = prepared["_shares_source_available_ts"].fillna(
        prepared["_shares_fact_available_ts"]
    )
    prepared["_concept_priority"] = prepared["concept"].map(CONCEPT_PRIORITY)
    prepared["_accession_number"] = prepared["accession_compact"].map(_accession_number)

    selected: list[pd.Series] = []
    unresolved: list[str] = []
    grouped = prepared.groupby(["ticker", "_shares_fact_available_ts"], sort=True)
    for (ticker, available_at), group in grouped:
        candidates = group.loc[
            group["_shares_period_end_ts"].eq(group["_shares_period_end_ts"].max())
        ]
        candidates = candidates.loc[
            candidates["_concept_priority"].eq(candidates["_concept_priority"].min())
        ]
        candidates = candidates.loc[
            candidates["_shares_source_available_ts"].eq(
                candidates["_shares_source_available_ts"].max()
            )
        ]
        candidates = candidates.loc[
            candidates["source_priority"].eq(candidates["source_priority"].min())
        ]
        candidates = candidates.loc[
            candidates["_accession_number"].eq(candidates["_accession_number"].max())
        ]
        values = candidates["shares_outstanding"].drop_duplicates()
        if len(values) != 1:
            unresolved.append(f"{ticker}@{available_at.isoformat()}")
            continue
        selected.append(
            candidates.sort_values(
                ["source_kind", "concept", "accession_compact"], kind="stable"
            ).iloc[-1]
        )
    if unresolved:
        raise ValueError(f"unresolved effective shares conflicts: {unresolved}")

    columns = [
        "ticker",
        "_shares_fact_available_ts",
        "_shares_period_end_ts",
        "shares_outstanding",
        "stable_security_id",
        "cik",
        "accession_compact",
        "concept",
        "source_kind",
        "source_priority",
        "source_sha256",
    ]
    selected_frame = pd.DataFrame(selected) if selected else prepared.iloc[0:0]
    effective = selected_frame[columns].rename(
        columns={
            "shares_outstanding": "shares_outstanding_raw",
            "stable_security_id": "shares_stable_security_id",
            "cik": "shares_cik",
            "accession_compact": "shares_accession_compact",
            "concept": "shares_concept",
            "source_kind": "shares_source_kind",
            "source_priority": "shares_source_priority",
            "source_sha256": "shares_source_sha256",
        }
    )
    effective = effective.sort_values(
        ["ticker", "_shares_fact_available_ts"], kind="stable"
    ).reset_index(drop=True)
    if effective.duplicated(["ticker", "_shares_fact_available_ts"]).any():
        raise ValueError("duplicate effective ticker/availability rows")
    return effective, {
        "input_fact_count": len(shares),
        "invalid_fact_count": invalid_fact_count,
        "effective_fact_count": len(effective),
        "unresolved_conflict_count": 0,
    }


def resolve_split_actions(actions: pd.DataFrame) -> pd.DataFrame:
    """Return validated split events, excluding dividends and unit factors."""
    _require_columns(actions, ACTION_REQUIRED_COLUMNS, "corporate actions")
    prepared = actions.copy()
    prepared["ticker"] = _normalised_tickers(prepared["ticker"], "corporate actions")
    prepared["split_factor"] = pd.to_numeric(prepared["split_factor"], errors="coerce")
    prepared["_split_date_ts"] = pd.to_datetime(
        prepared["trading_date"], utc=True, errors="coerce"
    ).dt.normalize()
    prepared["_split_available_ts"] = pd.to_datetime(
        prepared["available_at"], utc=True, errors="coerce"
    )
    splits = prepared.loc[~np.isclose(prepared["split_factor"], 1.0)].copy()
    invalid = (
        splits["split_factor"].isna()
        | ~np.isfinite(splits["split_factor"])
        | splits["split_factor"].le(0.0)
        | splits["_split_date_ts"].isna()
        | splits["_split_available_ts"].isna()
        | splits["_split_available_ts"].lt(splits["_split_date_ts"])
    )
    if invalid.any():
        raise ValueError("corporate actions contain invalid split events")
    conflicts = splits.groupby(["ticker", "_split_date_ts"])["split_factor"].nunique().gt(1)
    if conflicts.any():
        keys = [f"{ticker}@{session.date()}" for ticker, session in conflicts[conflicts].index]
        raise ValueError(f"conflicting split events: {keys}")
    splits = splits.drop_duplicates(["ticker", "_split_date_ts", "split_factor"])
    splits = splits.sort_values(["ticker", "_split_date_ts"], kind="stable")
    for ticker, group in splits.groupby("ticker", sort=True):
        if not group["_split_available_ts"].is_monotonic_increasing:
            raise ValueError(f"split availability is not chronological for {ticker}")
    return splits[["ticker", "_split_date_ts", "_split_available_ts", "split_factor"]].reset_index(
        drop=True
    )


def _split_adjustment(
    rows: pd.DataFrame,
    splits: pd.DataFrame,
) -> np.ndarray:
    factors = np.ones(len(rows), dtype=float)
    available = rows["shares_data_available"].to_numpy(dtype=bool)
    factors[~available] = np.nan
    if splits.empty or not available.any():
        return factors
    split_available = splits["_split_available_ts"].astype("int64").to_numpy()
    split_dates = splits["_split_date_ts"].astype("int64").to_numpy()
    cumulative = np.cumprod(splits["split_factor"].to_numpy(dtype=float))
    price_available = rows["_price_available_ts"].astype("int64").to_numpy()
    fact_period_end = rows["_shares_period_end_ts"].astype("int64").to_numpy()
    numerator_positions = np.searchsorted(split_available, price_available, side="right") - 1
    denominator_positions = np.searchsorted(split_dates, fact_period_end, side="right") - 1
    numerator = np.where(numerator_positions >= 0, cumulative[numerator_positions], 1.0)
    denominator = np.where(denominator_positions >= 0, cumulative[denominator_positions], 1.0)
    factors[available] = numerator[available] / denominator[available]
    return factors


def build_eligibility_panel(
    prices: pd.DataFrame,
    shares: pd.DataFrame,
    actions: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """As-of join shares and apply splits after each fact's period end."""
    _require_columns(prices, PRICE_REQUIRED_COLUMNS, "prices")
    prepared_prices = prices.copy()
    prepared_prices["ticker"] = _normalised_tickers(prepared_prices["ticker"], "prices")
    prepared_prices["_trading_date_ts"] = pd.to_datetime(
        prepared_prices["trading_date"], utc=True, errors="coerce"
    ).dt.normalize()
    prepared_prices["_price_available_ts"] = pd.to_datetime(
        prepared_prices["available_at"], utc=True, errors="coerce"
    )
    prepared_prices["close"] = pd.to_numeric(prepared_prices["close"], errors="coerce")
    if (
        prepared_prices["_trading_date_ts"].isna().any()
        or prepared_prices["_price_available_ts"].isna().any()
        or prepared_prices["close"].isna().any()
        or ~np.isfinite(prepared_prices["close"]).all()
        or prepared_prices["close"].le(0.0).any()
    ):
        raise ValueError("prices contain invalid dates, availability, or closes")
    if prepared_prices.duplicated(["ticker", "_trading_date_ts"]).any():
        raise ValueError("duplicate ticker/trading_date price rows")

    effective, fact_evidence = resolve_effective_shares(shares)
    splits = resolve_split_actions(actions)
    unknown_action_symbols = sorted(set(splits["ticker"]) - set(prepared_prices["ticker"]))
    if unknown_action_symbols:
        raise ValueError(f"split events contain unknown price symbols: {unknown_action_symbols}")

    parts: list[pd.DataFrame] = []
    for ticker, price_group in prepared_prices.groupby("ticker", sort=True):
        left = price_group.sort_values("_price_available_ts", kind="stable")
        right = effective.loc[effective["ticker"].eq(ticker)].drop(columns="ticker")
        joined = pd.merge_asof(
            left,
            right.sort_values("_shares_fact_available_ts", kind="stable"),
            left_on="_price_available_ts",
            right_on="_shares_fact_available_ts",
            direction="backward",
            allow_exact_matches=True,
        )
        joined["shares_data_available"] = joined["shares_outstanding_raw"].notna()
        ticker_splits = splits.loc[splits["ticker"].eq(ticker)]
        joined["shares_split_adjustment_factor"] = _split_adjustment(joined, ticker_splits)
        joined["shares_outstanding"] = (
            pd.to_numeric(joined["shares_outstanding_raw"], errors="coerce")
            * joined["shares_split_adjustment_factor"]
        )
        has_symbol_facts = not right.empty
        joined["shares_data_reason"] = np.where(
            joined["shares_data_available"],
            "AVAILABLE",
            ("NO_PRIOR_POINT_IN_TIME_FACT" if has_symbol_facts else "NO_SHARES_FACTS_FOR_SYMBOL"),
        )
        joined["market_cap"] = joined["close"] * joined["shares_outstanding"]
        parts.append(joined)

    panel = pd.concat(parts, ignore_index=True).sort_values(
        ["ticker", "_trading_date_ts"], kind="stable"
    )
    panel["shares_fact_available_at"] = panel["_shares_fact_available_ts"].map(
        lambda value: None if pd.isna(value) else value.isoformat().replace("+00:00", "Z")
    )
    panel["shares_period_end"] = panel["_shares_period_end_ts"].map(
        lambda value: None if pd.isna(value) else value.date().isoformat()
    )
    panel = panel.drop(
        columns=[
            "_trading_date_ts",
            "_price_available_ts",
            "_shares_fact_available_ts",
            "_shares_period_end_ts",
        ]
    ).reset_index(drop=True)
    unavailable = ~panel["shares_data_available"]
    split_adjusted = panel["shares_data_available"] & ~np.isclose(
        panel["shares_split_adjustment_factor"], 1.0
    )
    by_symbol: dict[str, dict[str, Any]] = {}
    for ticker, group in panel.groupby("ticker", sort=True):
        usable = group.loc[group["shares_data_available"]]
        by_symbol[ticker] = {
            "price_row_count": len(group),
            "shares_available_row_count": len(usable),
            "shares_unavailable_row_count": int((~group["shares_data_available"]).sum()),
            "first_shares_eligible_session": (
                None if usable.empty else str(usable.iloc[0]["trading_date"])
            ),
            "split_adjusted_row_count": int(
                (
                    group["shares_data_available"]
                    & ~np.isclose(group["shares_split_adjustment_factor"], 1.0)
                ).sum()
            ),
        }
    evidence: dict[str, Any] = {
        **fact_evidence,
        "price_row_count": len(panel),
        "price_symbol_count": panel["ticker"].nunique(),
        "shares_available_row_count": int(panel["shares_data_available"].sum()),
        "shares_unavailable_row_count": int(unavailable.sum()),
        "symbols_with_eligible_rows": int(
            panel.loc[panel["shares_data_available"], "ticker"].nunique()
        ),
        "symbols_without_eligible_rows": sorted(
            set(panel["ticker"]) - set(panel.loc[panel["shares_data_available"], "ticker"])
        ),
        "split_event_count": len(splits),
        "split_adjusted_row_count": int(split_adjusted.sum()),
        "by_symbol": by_symbol,
    }
    return panel, evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--shares", type=Path, required=True)
    parser.add_argument("--shares-summary", type=Path, required=True)
    parser.add_argument("--corporate-actions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    shares_summary = json.loads(args.shares_summary.read_text(encoding="utf-8"))
    expected_shares_sha256 = shares_summary["output"]["sha256"]
    observed_shares_sha256 = file_sha256(args.shares)
    if observed_shares_sha256 != expected_shares_sha256:
        raise ValueError(
            "shares Parquet SHA256 does not match its summary: "
            f"{observed_shares_sha256} != {expected_shares_sha256}"
        )

    prices = pq.read_table(args.prices).to_pandas()
    shares = pq.read_table(args.shares).to_pandas()
    actions = pq.read_table(args.corporate_actions).to_pandas()
    panel, evidence = build_eligibility_panel(prices, shares, actions)
    price_symbols = set(panel["ticker"])
    expected_symbols = set(shares["ticker"].astype(str).str.upper()) | set(
        shares_summary["shares_missing_symbols"]
    )
    if price_symbols != expected_symbols:
        raise ValueError(
            "price cohort does not match shares cohort: "
            f"missing={sorted(expected_symbols - price_symbols)}, "
            f"unexpected={sorted(price_symbols - expected_symbols)}"
        )
    if len(price_symbols) != int(shares_summary["cohort_symbol_count"]):
        raise ValueError("observed cohort symbol count does not match shares summary")

    output_path = args.output / "shares_eligibility_panel.parquet"
    atomic_parquet(panel, output_path)
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "purpose": "POINT_IN_TIME_SHARES_ELIGIBILITY_RESEARCH_PANEL",
        "availability_policy": shares_summary["availability_policy"],
        "fact_resolution_policy": [
            "LATEST_PERIOD_END_PER_TICKER_AND_CONSERVATIVE_AVAILABILITY",
            "ENTITY_THEN_INVESTMENT_COMPANY_THEN_COMMON_STOCK_CONCEPT",
            "LATEST_SOURCE_TIMESTAMP_THEN_SOURCE_PRIORITY_THEN_ACCESSION",
            "FAIL_ON_REMAINING_VALUE_CONFLICT",
        ],
        "split_adjustment_policy": (
            "PRODUCT_OF_SPLIT_FACTORS_AFTER_FACT_PERIOD_END_AND_AVAILABLE_BY_PRICE_CLOSE"
        ),
        **evidence,
        "source_gate_pass": not evidence["symbols_without_eligible_rows"],
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY",
        "inputs": {
            "prices": {"path": str(args.prices), "sha256": file_sha256(args.prices)},
            "shares": {"path": str(args.shares), "sha256": observed_shares_sha256},
            "shares_summary": {
                "path": str(args.shares_summary),
                "sha256": file_sha256(args.shares_summary),
            },
            "corporate_actions": {
                "path": str(args.corporate_actions),
                "sha256": file_sha256(args.corporate_actions),
            },
        },
        "output": {"path": str(output_path), "sha256": file_sha256(output_path)},
    }
    summary_path = args.output / "shares_eligibility_panel_summary.json"
    atomic_write(
        summary_path,
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
