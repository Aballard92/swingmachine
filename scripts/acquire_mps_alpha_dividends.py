#!/usr/bin/env python3
"""Acquire bounded Alpha Vantage dividend histories without logging credentials."""

from __future__ import annotations

import argparse
import csv
import io
import json
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pyarrow.parquet as pq

REQUIRED_FIELDS = {
    "ex_dividend_date",
    "declaration_date",
    "record_date",
    "payment_date",
    "amount",
}


def dividend_tickers(corporate_actions: Path) -> list[str]:
    table = pq.read_table(corporate_actions, columns=["ticker", "div_cash"])
    tickers = {
        str(ticker)
        for ticker, amount in zip(
            table.column("ticker").to_pylist(),
            table.column("div_cash").to_pylist(),
            strict=True,
        )
        if float(amount or 0) != 0
    }
    return sorted(tickers)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corporate-actions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--max-symbols", type=int, default=20)
    parser.add_argument("--delay-seconds", type=float, default=15.0)
    args = parser.parse_args()
    if args.max_symbols < 1 or args.max_symbols > 20:
        raise ValueError("max-symbols must be between 1 and 20 to preserve daily headroom")

    token = args.token_file.read_text(encoding="utf-8").strip()
    raw = args.output / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "acquisition_manifest.jsonl"
    completed = {path.stem for path in raw.glob("*.csv") if path.stat().st_size > 10}
    attempted = 0

    with manifest_path.open("a", encoding="utf-8") as manifest:
        for ticker in dividend_tickers(args.corporate_actions):
            if ticker in completed:
                continue
            if attempted >= args.max_symbols:
                break
            query = urlencode(
                {
                    "function": "DIVIDENDS",
                    "symbol": ticker,
                    "datatype": "csv",
                    "apikey": token,
                }
            )
            request = Request(
                f"https://www.alphavantage.co/query?{query}",
                headers={"User-Agent": "SwingMachineResearch/1.0"},
            )
            error = None
            try:
                with urlopen(request, timeout=120) as response:
                    payload = response.read()
                    status = response.status
                    content_type = response.headers.get("Content-Type")
            except HTTPError as exc:
                status = exc.code
                payload = exc.read()
                content_type = exc.headers.get("Content-Type")
                error = "HTTPError"

            text = payload.decode("utf-8", errors="replace")
            rows: list[dict[str, str]] = []
            fields: set[str] = set()
            try:
                reader = csv.DictReader(io.StringIO(text))
                fields = set(reader.fieldnames or ())
                rows = list(reader)
            except csv.Error:
                error = error or "CSVError"
            valid = REQUIRED_FIELDS.issubset(fields) and bool(rows)
            if valid:
                (raw / f"{ticker}.csv").write_bytes(payload)

            record = {
                "ticker": ticker,
                "http_status": status,
                "content_type": content_type,
                "valid": valid,
                "rows": len(rows),
                "fields": sorted(fields),
                "bytes": len(payload),
                "sha256": sha256(payload).hexdigest(),
                "retrieved_at": datetime.now(UTC).isoformat(),
                "error": error,
                "request_template": (
                    "https://www.alphavantage.co/query?function=DIVIDENDS&symbol="
                    f"{ticker}&datatype=csv&apikey=REDACTED"
                ),
            }
            manifest.write(json.dumps(record, sort_keys=True) + "\n")
            manifest.flush()
            print(ticker, status, len(rows), "VALID" if valid else "REJECTED", flush=True)
            attempted += 1
            if status == 429 or "rate limit" in text.lower() or "frequency" in text.lower():
                break
            time.sleep(args.delay_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
