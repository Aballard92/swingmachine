#!/usr/bin/env python3
"""Normalize acquired public reference probes into auditable JSON evidence."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from swingmachine.mps_public_data import (
    dataclass_rows,
    extract_sec_shares_facts,
    parse_alpha_vantage_listing_csv,
    parse_nasdaq_directory,
    parse_sec_submissions,
    parse_sec_ticker_proxy,
    source_file_record,
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    retrieved_at = datetime.now(UTC)

    files = {
        "alpha_delisted_sample": args.raw_root / "alpha_vantage/delisted_2014-07-10.csv",
        "nasdaq_listed": args.raw_root / "nasdaq_trader/nasdaqlisted.txt",
        "other_listed": args.raw_root / "nasdaq_trader/otherlisted.txt",
        "sec_ticker_proxy": args.raw_root / "sec_edgar_probe/company_tickers_proxy.txt",
        "sec_aapl_submissions": args.raw_root / "sec_edgar_probe/aapl_submissions.json",
        "sec_aapl_companyfacts": args.raw_root / "sec_edgar_probe/aapl_companyfacts.json",
        "openfigi_schema": args.raw_root / "source_probes/openfigi_schema.json",
    }
    missing = [name for name, path in files.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing source probes: {', '.join(missing)}")

    lifecycle = parse_alpha_vantage_listing_csv(
        files["alpha_delisted_sample"].read_text(), "alpha_vantage_demo"
    )
    nasdaq = parse_nasdaq_directory(files["nasdaq_listed"].read_text(), exchange_family="NASDAQ")
    other = parse_nasdaq_directory(files["other_listed"].read_text(), exchange_family="OTHER")
    sec_tickers = parse_sec_ticker_proxy(files["sec_ticker_proxy"].read_text())
    issuer = parse_sec_submissions(json.loads(files["sec_aapl_submissions"].read_text()))
    shares = extract_sec_shares_facts(
        json.loads(files["sec_aapl_companyfacts"].read_text()), issuer
    )

    manifest = {
        "evidence_class": "ZERO_COST_SOURCE_PROBE",
        "qualification_eligible": False,
        "sources": [
            source_file_record(name, path, retrieved_at).__dict__ for name, path in files.items()
        ],
    }
    report = {
        "status": "PARTIAL_RESEARCH_ONLY",
        "counts": {
            "alpha_historical_delisted_sample": len(lifecycle),
            "nasdaq_current": len(nasdaq),
            "other_exchange_current": len(other),
            "sec_current_ticker_cik": len(sec_tickers),
            "aapl_acceptance_timestamps": len(issuer.acceptance_by_accession),
            "aapl_pit_shares_facts": len(shares),
        },
        "proven": [
            "free current exchange directory with source creation timestamp",
            "free current SEC ticker-to-CIK index via proxy with direct issuer verification",
            "direct SEC filing acceptance timestamps",
            "shares facts can be restricted to known filing acceptance timestamps",
            "free OpenFIGI schema access",
            "historical delisted listing sample structure",
        ],
        "unresolved": [
            (
                "complete historical active and delisted listing status requires "
                "a free Alpha Vantage key"
            ),
            "SEC bulk archive blocked from this shell; per-CIK endpoints work",
            "delisting proceeds and merger terms remain unstructured",
            "price archive licence and adjustment semantics remain unresolved",
            "historical sector changes are not yet proven",
        ],
        "decision": "DO_NOT_UNBLOCK_MPS_YET",
    }
    write_json(args.output / "source_manifest.json", manifest)
    write_json(args.output / "probe_report.json", report)
    write_json(args.output / "alpha_delisted_sample.normalized.json", dataclass_rows(lifecycle))
    write_json(args.output / "nasdaq_current.normalized.json", dataclass_rows((*nasdaq, *other)))
    write_json(args.output / "sec_tickers_current.normalized.json", dataclass_rows(sec_tickers))
    write_json(args.output / "aapl_shares_pit_sample.normalized.json", dataclass_rows(shares))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
