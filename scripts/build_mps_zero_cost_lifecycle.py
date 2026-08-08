#!/usr/bin/env python3
"""Build a deterministic listing-lifecycle panel from zero-cost sources."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from hashlib import sha256
from pathlib import Path

import pyarrow.parquet as pq

from swingmachine.mps_public_data import (
    ListingLifecycle,
    parse_alpha_vantage_listing_csv,
    parse_sec_ticker_proxy,
)

ELIGIBLE_EXCHANGES = {"NYSE", "NASDAQ", "NYSE MKT", "NYSE AMERICAN"}


def identity_key(row: ListingLifecycle) -> tuple[str, str, str]:
    return (
        row.symbol,
        row.ipo_date.isoformat() if row.ipo_date else "UNKNOWN",
        row.name.upper().strip(),
    )


def security_id(key: tuple[str, str, str]) -> str:
    return "AV-" + sha256("|".join(key).encode("utf-8")).hexdigest()[:20]


def price_symbols(root: Path) -> set[str]:
    symbols: set[str] = set()
    for path in sorted(root.glob("*.parquet")):
        parquet = pq.ParquetFile(path)
        for index in range(parquet.metadata.num_row_groups):
            column = parquet.read_row_group(index, columns=["symbol"]).column("symbol")
            symbols.update(str(value).upper() for value in column.unique().to_pylist() if value)
    return symbols


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alpha-root", type=Path, required=True)
    parser.add_argument("--price-root", type=Path, required=True)
    parser.add_argument("--sec-ticker-proxy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    snapshot_files = sorted(args.alpha_root.glob("active_*.csv")) + sorted(
        args.alpha_root.glob("delisted_*.csv")
    )
    snapshot_files = [
        path for path in snapshot_files if path.stat().st_size > 2 and "2014-07-10" not in path.name
    ]
    observations: dict[tuple[str, str, str], list[tuple[str, ListingLifecycle]]] = defaultdict(list)
    for path in snapshot_files:
        for row in parse_alpha_vantage_listing_csv(path.read_text(), f"alpha_vantage:{path.name}"):
            observations[identity_key(row)].append((path.name, row))

    prices = price_symbols(args.price_root)
    sec_by_ticker = {
        row.ticker: row for row in parse_sec_ticker_proxy(args.sec_ticker_proxy.read_text())
    }
    records = []
    conflicts = []
    for key, seen in sorted(observations.items()):
        rows = [row for _, row in seen]
        exchanges = sorted({row.exchange.upper() for row in rows})
        asset_types = sorted({row.asset_type for row in rows})
        delisting_dates = sorted(
            {row.delisting_date.isoformat() for row in rows if row.delisting_date}
        )
        if len(asset_types) != 1 or len(delisting_dates) > 1:
            conflicts.append(
                {"key": key, "asset_types": asset_types, "delisting_dates": delisting_dates}
            )
            continue
        row = rows[-1]
        sec = sec_by_ticker.get(row.symbol)
        records.append(
            {
                "security_id": security_id(key),
                "symbol": row.symbol,
                "name": row.name,
                "ipo_date": row.ipo_date.isoformat() if row.ipo_date else None,
                "delisting_date": delisting_dates[0] if delisting_dates else None,
                "status_latest_observed": row.status,
                "asset_type": asset_types[0],
                "exchanges_observed": exchanges,
                "eligible_exchange": bool(set(exchanges) & ELIGIBLE_EXCHANGES),
                "price_archive_present": row.symbol in prices,
                "current_sec_cik": sec.cik if sec else None,
                "snapshot_files": sorted({name for name, _ in seen}),
            }
        )

    def count(predicate):
        return sum(1 for row in records if predicate(row))

    stock_records = [
        row for row in records if row["asset_type"] == "Stock" and row["eligible_exchange"]
    ]
    delisted_stock_records = [row for row in stock_records if row["delisting_date"]]
    report = {
        "status": "PARTIAL_RESEARCH_ONLY",
        "snapshot_files": [path.name for path in snapshot_files],
        "counts": {
            "unique_lifecycle_identities": len(records),
            "conflicting_identities_rejected": len(conflicts),
            "eligible_exchange_stock_identities": len(stock_records),
            "eligible_stock_with_price_archive": sum(
                row["price_archive_present"] for row in stock_records
            ),
            "eligible_stock_with_current_sec_cik": sum(
                row["current_sec_cik"] is not None for row in stock_records
            ),
            "delisted_eligible_stock_identities": len(delisted_stock_records),
            "delisted_stock_with_price_archive": sum(
                row["price_archive_present"] for row in delisted_stock_records
            ),
            "delisted_stock_with_current_sec_cik": sum(
                row["current_sec_cik"] is not None for row in delisted_stock_records
            ),
            "price_archive_symbols": len(prices),
            "price_symbols_in_any_lifecycle": len(prices & {row["symbol"] for row in records}),
        },
        "gates": {
            "listing_lifecycle": "PASS_SOURCE_ACQUIRED",
            "stable_identity": "PARTIAL_HASH_OF_SYMBOL_IPO_NAME_NOT_PROVIDER_PERMANENT_ID",
            "price_coverage": "MEASURED_NOT_YET_QUALIFIED",
            "delisting_proceeds": "MISSING",
            "corporate_actions": "MISSING",
            "price_licence": "FAIL_HEXQUANT_OTHER_PAID_GATE",
            "adjustment_semantics": "UNRESOLVED",
        },
        "decision": "DO_NOT_UNBLOCK_MPS_YET",
    }
    (args.output / "lifecycle_records.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in records), encoding="utf-8"
    )
    (args.output / "lifecycle_conflicts.json").write_text(
        json.dumps(conflicts, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output / "lifecycle_coverage_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
