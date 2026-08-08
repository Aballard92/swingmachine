#!/usr/bin/env python3
"""Acquire bounded OpenFIGI classification evidence for acquired MPS symbols."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pyarrow.parquet as pq


def acquired_tickers(prices: Path) -> list[str]:
    table = pq.read_table(prices, columns=["ticker"])
    return sorted({str(value) for value in table.column("ticker").to_pylist()})


def chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-batches", type=int, default=10)
    parser.add_argument("--delay-seconds", type=float, default=3.0)
    args = parser.parse_args()
    if args.max_batches < 1 or args.max_batches > 20:
        raise ValueError("max-batches must be between 1 and 20")

    raw = args.output / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "acquisition_manifest.jsonl"
    completed = {path.stem for path in raw.glob("*.json") if path.stat().st_size > 2}
    pending = [ticker for ticker in acquired_tickers(args.prices) if ticker not in completed]
    attempted_batches = 0

    with manifest_path.open("a", encoding="utf-8") as manifest:
        for tickers in chunks(pending, 10):
            if attempted_batches >= args.max_batches:
                break
            jobs = [
                {
                    "idType": "TICKER",
                    "idValue": ticker,
                    "exchCode": "US",
                    "marketSecDes": "Equity",
                    "includeUnlistedEquities": True,
                }
                for ticker in tickers
            ]
            body = json.dumps(jobs, separators=(",", ":")).encode("utf-8")
            request = Request(
                "https://api.openfigi.com/v3/mapping",
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "SwingMachineResearch/1.0",
                },
            )
            error = None
            try:
                with urlopen(request, timeout=120) as response:
                    payload = response.read()
                    status = response.status
                    rate_headers = {
                        key: response.headers.get(key)
                        for key in ("ratelimit-limit", "ratelimit-remaining", "ratelimit-reset")
                    }
            except HTTPError as exc:
                status = exc.code
                payload = exc.read()
                error = "HTTPError"
                rate_headers = {
                    key: exc.headers.get(key)
                    for key in ("ratelimit-limit", "ratelimit-remaining", "ratelimit-reset")
                }

            parsed: object = None
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                error = error or "JSONDecodeError"
            valid_envelope = isinstance(parsed, list) and len(parsed) == len(tickers)
            response_error_count = (
                sum(isinstance(result, dict) and "error" in result for result in parsed)
                if valid_envelope
                else 0
            )
            valid = valid_envelope and response_error_count == 0
            if valid:
                for ticker, job, result in zip(tickers, jobs, parsed, strict=True):
                    (raw / f"{ticker}.json").write_text(
                        json.dumps(
                            {
                                "request": job,
                                "response": result,
                            },
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n",
                        encoding="utf-8",
                    )

            record = {
                "tickers": tickers,
                "http_status": status,
                "valid": valid,
                "valid_envelope": valid_envelope,
                "response_error_count": response_error_count,
                "bytes": len(payload),
                "sha256": sha256(payload).hexdigest(),
                "retrieved_at": datetime.now(UTC).isoformat(),
                "error": error,
                "rate_limit": rate_headers,
                "endpoint": "https://api.openfigi.com/v3/mapping",
                "api_key_used": False,
            }
            manifest.write(json.dumps(record, sort_keys=True) + "\n")
            manifest.flush()
            print(
                ",".join(tickers),
                status,
                "VALID" if valid else "REJECTED",
                flush=True,
            )
            attempted_batches += 1
            if status == 429:
                break
            time.sleep(args.delay_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
