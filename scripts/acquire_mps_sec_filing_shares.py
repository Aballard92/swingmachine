#!/usr/bin/env python3
"""Acquire targeted SEC filing documents for shares-outstanding remediation."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SEC_ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{document}"
ALLOWED_FORMS = {"10-K", "10-Q", "N-CSR", "N-CSRS"}
BLOCK_PAGE_MARKERS = (
    b"Your Request Originates from an Undeclared Automated Tool",
    b"Request Rate Threshold Exceeded",
)


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


def parse_cik_overrides(values: list[str]) -> dict[str, int]:
    overrides: dict[str, int] = {}
    for value in values:
        ticker, separator, cik_text = value.partition("=")
        ticker = ticker.upper()
        if not separator or not ticker or not cik_text.isdigit():
            raise ValueError(f"invalid CIK override, expected TICKER=CIK: {value}")
        if ticker in overrides:
            raise ValueError(f"duplicate CIK override: {ticker}")
        overrides[ticker] = int(cik_text)
    return overrides


def load_resolutions(
    path: Path,
    tickers: set[str],
    *,
    cik_overrides: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload["resolutions"]
    selected = [row for row in rows if str(row["ticker"]).upper() in tickers]
    found = {str(row["ticker"]).upper() for row in selected}
    missing = sorted(tickers - found)
    if missing:
        raise ValueError(f"tickers missing from resolution seed: {missing}")
    unresolved = sorted(
        str(row["ticker"]).upper() for row in selected if row.get("accepted_cik") is None
    )
    if unresolved:
        raise ValueError(f"tickers have unresolved CIKs: {unresolved}")
    cik_overrides = cik_overrides or {}
    unknown_overrides = sorted(set(cik_overrides) - tickers)
    if unknown_overrides:
        raise ValueError(f"CIK overrides outside selected tickers: {unknown_overrides}")
    resolved: list[dict[str, Any]] = []
    for row in selected:
        ticker = str(row["ticker"]).upper()
        updated = dict(row)
        if ticker in cik_overrides:
            updated["seed_cik"] = int(row["accepted_cik"])
            updated["accepted_cik"] = cik_overrides[ticker]
            updated["acquisition_cik_override"] = True
        resolved.append(updated)
    return sorted(resolved, key=lambda row: str(row["ticker"]).upper())


class SecClient:
    def __init__(self, user_agent: str, *, request_interval_seconds: float) -> None:
        if "@" not in user_agent:
            raise ValueError("SEC user agent must include a contact email")
        if request_interval_seconds < 0.1:
            raise ValueError("request interval must be at least 0.1 seconds")
        self.user_agent = user_agent
        self.request_interval_seconds = request_interval_seconds
        self.last_request_at = 0.0

    def get(self, url: str, *, max_bytes: int) -> bytes:
        delay = self.request_interval_seconds - (time.monotonic() - self.last_request_at)
        if delay > 0:
            time.sleep(delay)
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Encoding": "identity",
            },
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with urlopen(request, timeout=60) as response:
                    payload = response.read(max_bytes + 1)
                    self.last_request_at = time.monotonic()
                    if len(payload) > max_bytes:
                        raise ValueError(f"SEC response exceeds {max_bytes} bytes: {url}")
                    if any(marker in payload for marker in BLOCK_PAGE_MARKERS):
                        raise ValueError(f"SEC fair-access block page returned: {url}")
                    return payload
            except (HTTPError, URLError, TimeoutError) as error:
                self.last_request_at = time.monotonic()
                last_error = error
                if attempt == 2:
                    break
                time.sleep(2**attempt)
        raise ValueError(f"SEC request failed after retries: {url}") from last_error


def filing_rows(submissions: dict[str, Any]) -> list[dict[str, str]]:
    recent = submissions["filings"]["recent"]
    rows: list[dict[str, str]] = []
    for index, form in enumerate(recent["form"]):
        if form not in ALLOWED_FORMS:
            continue
        row = {
            "accession": str(recent["accessionNumber"][index]),
            "filing_date": str(recent["filingDate"][index]),
            "report_date": str(recent["reportDate"][index]),
            "form": str(form),
            "primary_document": str(recent["primaryDocument"][index]),
        }
        if not row["primary_document"]:
            continue
        rows.append(row)
    rows.sort(key=lambda row: (row["filing_date"], row["accession"]))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution-seed", type=Path, required=True)
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--cik-override", action="append", default=[])
    parser.add_argument("--user-agent", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--request-interval-seconds", type=float, default=0.25)
    parser.add_argument("--max-filing-bytes", type=int, default=20_000_000)
    parser.add_argument("--reuse-existing", action="store_true")
    args = parser.parse_args()

    tickers = {str(ticker).upper() for ticker in args.ticker}
    cik_overrides = parse_cik_overrides(args.cik_override)
    resolutions = load_resolutions(
        args.resolution_seed,
        tickers,
        cik_overrides=cik_overrides,
    )
    client = SecClient(
        args.user_agent,
        request_interval_seconds=args.request_interval_seconds,
    )
    args.output.mkdir(parents=True, exist_ok=True)

    artifacts: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    for resolution in resolutions:
        ticker = str(resolution["ticker"]).upper()
        cik = int(resolution["accepted_cik"])
        submissions_url = SEC_SUBMISSIONS.format(cik=cik)
        submissions_payload = client.get(submissions_url, max_bytes=5_000_000)
        submissions_path = args.output / f"CIK{cik:010d}" / "submissions.json"
        atomic_write(submissions_path, submissions_payload)
        submissions = json.loads(submissions_payload)
        if int(submissions["cik"]) != cik:
            raise ValueError(f"SEC submissions CIK mismatch for {ticker}")
        entities.append(
            {
                "ticker": ticker,
                "cik": cik,
                "entity_name": str(submissions["name"]),
                "seed_cik": resolution.get("seed_cik"),
                "acquisition_cik_override": bool(resolution.get("acquisition_cik_override")),
                "submissions_url": submissions_url,
                "submissions_path": str(submissions_path),
                "submissions_sha256": file_sha256(submissions_path),
            }
        )

        for filing in filing_rows(submissions):
            accession_compact = filing["accession"].replace("-", "")
            url = SEC_ARCHIVE.format(
                cik=cik,
                accession=accession_compact,
                document=filing["primary_document"],
            )
            path = (
                args.output / f"CIK{cik:010d}" / f"{accession_compact}_{filing['primary_document']}"
            )
            reused = args.reuse_existing and path.is_file()
            if reused:
                payload_size = path.stat().st_size
                if payload_size > args.max_filing_bytes:
                    raise ValueError(f"existing filing exceeds size cap: {path}")
                payload = path.read_bytes()
                if any(marker in payload for marker in BLOCK_PAGE_MARKERS):
                    raise ValueError(f"existing filing is an SEC block page: {path}")
            else:
                payload = client.get(url, max_bytes=args.max_filing_bytes)
                atomic_write(path, payload)
            artifacts.append(
                {
                    "ticker": ticker,
                    "cik": cik,
                    **filing,
                    "accession_compact": accession_compact,
                    "url": url,
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": file_sha256(path),
                    "reused_existing": reused,
                }
            )

    manifest = {
        "task_id": "SWING-MPS-DATA-001",
        "access": "ANONYMOUS_NO_ACCOUNT_NO_API_KEY",
        "source": "SEC EDGAR primary filing documents",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "user_agent_identified": True,
        "request_interval_seconds": args.request_interval_seconds,
        "forms": sorted(ALLOWED_FORMS),
        "entities": entities,
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "qualification_usable": False,
        "decision": "SOURCE_ACQUIRED_RESEARCH_ONLY",
    }
    atomic_write(
        args.output / "acquisition_manifest.json",
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
