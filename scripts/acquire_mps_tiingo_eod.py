#!/usr/bin/env python3
"""Resumably acquire a bounded Tiingo EOD queue without logging credentials."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--max-symbols", type=int, default=45)
    parser.add_argument("--delay-seconds", type=float, default=0.5)
    args = parser.parse_args()
    if args.max_symbols < 1 or args.max_symbols > 45:
        raise ValueError("max-symbols must be between 1 and 45 to preserve hourly headroom")
    token = args.token_file.read_text().strip()
    queue = json.loads(args.queue.read_text())["selected"]
    raw = args.output / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "acquisition_manifest.jsonl"
    completed = {path.stem for path in raw.glob("*.json") if path.stat().st_size > 2}
    terminal_empty: set[str] = set()
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                prior = json.loads(line)
            except json.JSONDecodeError:
                continue
            if prior.get("http_status") == 200 and prior.get("valid") is False:
                terminal_empty.add(str(prior.get("ticker", "")))
    attempted = 0
    with manifest_path.open("a", encoding="utf-8") as manifest:
        for item in queue:
            ticker = item["ticker"]
            if ticker in completed or ticker in terminal_empty:
                continue
            if attempted >= args.max_symbols:
                break
            params = urlencode(
                {
                    "startDate": item["request_start_date"],
                    "endDate": item["request_end_date"],
                }
            )
            request = Request(
                f"https://api.tiingo.com/tiingo/daily/{ticker}/prices?{params}",
                headers={
                    "Authorization": f"Token {token}",
                    "Content-Type": "application/json",
                    "User-Agent": "SwingMachineResearch/1.0",
                },
            )
            error = None
            try:
                with urlopen(request, timeout=120) as response:
                    payload = response.read()
                    status = response.status
            except HTTPError as exc:
                status = exc.code
                payload = exc.read()
                error = "HTTPError"
            valid = False
            bars = 0
            try:
                parsed = json.loads(payload)
                valid = isinstance(parsed, list) and bool(parsed)
                bars = len(parsed) if isinstance(parsed, list) else 0
            except json.JSONDecodeError:
                pass
            if valid:
                (raw / f"{ticker}.json").write_bytes(payload)
            record = {
                "security_id": item["security_id"],
                "ticker": ticker,
                "http_status": status,
                "valid": valid,
                "bars": bars,
                "bytes": len(payload),
                "sha256": sha256(payload).hexdigest(),
                "retrieved_at": datetime.now(UTC).isoformat(),
                "error": error,
                "request_start_date": item["request_start_date"],
                "request_end_date": item["request_end_date"],
            }
            manifest.write(json.dumps(record, sort_keys=True) + "\n")
            manifest.flush()
            print(ticker, status, bars, "VALID" if valid else "REJECTED")
            attempted += 1
            if status == 429:
                break
            time.sleep(args.delay_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
