#!/usr/bin/env python3
"""Build the preregistered first Tiingo acquisition batch."""

from __future__ import annotations

import argparse
import csv
import json
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

TARGET_START = date(2008, 1, 1)
TARGET_END = date(2025, 12, 31)
EXCLUDED_NAME_TERMS = (
    " WARRANT",
    " UNIT",
    " RIGHT",
    " PREFERRED",
    " PREFERENCE",
    " DEPOSITARY",
    " FUND",
    " NOTE",
    " ETF",
    " ETN",
    " ACQUISITION",
    " TRANSITION CORP",
    " BLANK CHECK",
    " SPAC",
    " TRUST",
    " PARTNERSHIP",
    " L.P.",
    " PLC",
    " N.V.",
    " NV",
    " S.A.",
    " SE",
)
COMMON_COMPANY_TERMS = (" INC", " CORP", " CORPORATION", " COMPANY", " CO ", " HOLDINGS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lifecycle", type=Path, required=True)
    parser.add_argument("--supported-tickers", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    lifecycle = [json.loads(line) for line in args.lifecycle.read_text().splitlines() if line]
    with zipfile.ZipFile(args.supported_tickers) as archive:
        with archive.open("supported_tickers.csv") as source:
            tiingo = list(csv.DictReader(line.decode("utf-8-sig") for line in source))
    tiingo_by_ticker: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in tiingo:
        if row["assetType"] == "Stock" and row["priceCurrency"] == "USD":
            tiingo_by_ticker[row["ticker"].upper()].append(row)

    accepted = []
    rejected = Counter()
    for row in lifecycle:
        if (
            not row["delisting_date"]
            or not row["eligible_exchange"]
            or row["asset_type"] != "Stock"
        ):
            continue
        upper_name = f" {row['name'].upper()}"
        if any(term in upper_name for term in EXCLUDED_NAME_TERMS):
            rejected["EXCLUDED_SECURITY_NAME"] += 1
            continue
        ticker = row["symbol"].upper()
        if "/P" in ticker or "-P-" in ticker or ticker.endswith("-P"):
            rejected["EXCLUDED_PREFERRED_SYMBOL"] += 1
            continue
        if len(ticker) >= 5 and ticker.endswith(("R", "W", "U")):
            rejected["EXCLUDED_SPECIAL_SUFFIX"] += 1
            continue
        if not any(term in upper_name for term in COMMON_COMPANY_TERMS):
            rejected["COMMON_COMPANY_NOT_PROVEN"] += 1
            continue
        if row["price_archive_present"]:
            rejected["ALREADY_IN_PRICE_ARCHIVE"] += 1
            continue
        alpha_end = date.fromisoformat(row["delisting_date"])
        if alpha_end < date(2010, 1, 4):
            rejected["DELISTED_BEFORE_TARGET"] += 1
            continue
        if alpha_end > TARGET_END:
            rejected["DELISTED_AFTER_TARGET"] += 1
            continue
        matches = tiingo_by_ticker.get(row["symbol"], [])
        exact = [
            candidate for candidate in matches if candidate.get("endDate") == row["delisting_date"]
        ]
        if len(exact) != 1:
            rejected["NO_UNIQUE_EXACT_TIINGO_LIFECYCLE"] += 1
            continue
        match = exact[0]
        start = max(TARGET_START, date.fromisoformat(match["startDate"]))
        end = min(TARGET_END, alpha_end)
        accepted.append(
            {
                "security_id": row["security_id"],
                "ticker": row["symbol"],
                "name": row["name"],
                "alpha_ipo_date": row["ipo_date"],
                "alpha_delisting_date": row["delisting_date"],
                "tiingo_start_date": match["startDate"],
                "tiingo_end_date": match["endDate"],
                "request_start_date": start.isoformat(),
                "request_end_date": end.isoformat(),
                "exchange": match["exchange"],
                "selection_reason": "DELISTED_MISSING_PRICE_EXACT_TICKER_AND_END_DATE",
            }
        )
    accepted.sort(key=lambda row: (row["alpha_delisting_date"], row["ticker"]), reverse=True)
    selected = accepted[: args.limit]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "task_id": "SWING-MPS-DATA-001",
                "selection": "most_recent_delisting_then_ticker_descending",
                "strategy_selection_use": False,
                "limit": args.limit,
                "eligible_exact_matches": len(accepted),
                "selected": selected,
                "rejections": dict(sorted(rejected.items())),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
