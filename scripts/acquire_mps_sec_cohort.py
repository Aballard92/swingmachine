#!/usr/bin/env python3
"""Acquire keyless SEC identity, submissions, and company-facts evidence for an MPS cohort."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pyarrow.parquet as pq

from swingmachine.mps_public_data import (
    normalized_issuer_name,
    parse_sec_browse_atom_ciks,
    sec_issuer_name_matches,
)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def request_bytes(url: str, user_agent: str) -> tuple[int, str | None, bytes]:
    request = Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "identity"})
    try:
        with urlopen(request, timeout=120) as response:
            return response.status, response.headers.get("Content-Type"), response.read()
    except HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type"), exc.read()


def source_record(url: str, path: Path, status: int, content_type: str | None) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "url": url,
        "path": str(path),
        "http_status": status,
        "content_type": content_type,
        "bytes": len(payload),
        "sha256": sha256(payload).hexdigest(),
    }


def load_expected(queue_path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(queue_path.read_text(encoding="utf-8"))
    selected = payload.get("selected", ())
    return {str(row["ticker"]).upper(): row for row in selected}


def load_resolution_seed(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload.get("resolutions", ())
    return {str(row["ticker"]).upper(): row for row in rows}


def cohort_tickers(prices_path: Path) -> list[str]:
    column = pq.read_table(prices_path, columns=["ticker"]).column("ticker")
    return sorted(str(value).upper() for value in column.unique().to_pylist())


def browse_url(*, ticker: str | None = None, company: str | None = None) -> str:
    query = {"action": "getcompany", "owner": "exclude", "output": "atom", "count": "10"}
    if ticker is not None:
        query["CIK"] = ticker
    elif company is not None:
        query["company"] = company
    else:
        raise ValueError("ticker or company is required")
    return "https://www.sec.gov/cgi-bin/browse-edgar?" + urlencode(query)


def data_url(kind: str, cik: int) -> str:
    if kind == "submissions":
        return f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
    if kind == "companyfacts":
        return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    raise ValueError(f"unsupported SEC data kind: {kind}")


def fetch_to_path(url: str, path: Path, user_agent: str) -> tuple[dict[str, Any], bytes]:
    status, content_type, payload = request_bytes(url, user_agent)
    atomic_write(path, payload)
    return source_record(url, path, status, content_type), payload


def candidate_is_issuer(expected_name: str, payload: dict[str, Any]) -> bool:
    return payload.get("entityType") == "operating" and sec_issuer_name_matches(
        expected_name, payload
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resolution-seed", type=Path)
    parser.add_argument(
        "--user-agent",
        default="SwingMachineResearch/1.0 (personal research; GitHub Aballard92)",
    )
    parser.add_argument("--delay-seconds", type=float, default=0.25)
    parser.add_argument("--max-symbols", type=int, default=100)
    args = parser.parse_args()
    if args.delay_seconds < 0.11:
        raise ValueError("delay-seconds must be at least 0.11 to respect SEC fair-access limits")
    tickers = cohort_tickers(args.prices)
    if len(tickers) > args.max_symbols:
        raise ValueError(f"cohort has {len(tickers)} symbols, exceeding max-symbols")

    expected_by_ticker = load_expected(args.queue)
    resolution_seed = load_resolution_seed(args.resolution_seed)
    manifest_path = args.output / "acquisition_manifest.jsonl"
    summary_path = args.output / "acquisition_summary.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []

    for index, ticker in enumerate(tickers, start=1):
        expected = expected_by_ticker.get(ticker)
        record: dict[str, Any] = {
            "ticker": ticker,
            "expected_name": None if expected is None else expected["name"],
            "expected_delisting_date": None
            if expected is None
            else expected["alpha_delisting_date"],
            "retrieved_at": datetime.now(UTC).isoformat(),
            "sources": [],
        }
        if expected is None:
            record["resolution_status"] = "REJECTED_MISSING_EXPECTED_IDENTITY"
            records.append(record)
            continue

        seed = resolution_seed.get(ticker)
        seeded_cik = None if seed is None else seed.get("accepted_cik", seed.get("cik"))
        if seeded_cik is not None:
            candidate_ciks = [int(seeded_cik)]
            resolution_method = "FROZEN_SEC_DISCOVERY_SEED"
            record["resolution_seed"] = seed
        else:
            ticker_url = browse_url(ticker=ticker)
            ticker_path = args.output / "browse" / f"{ticker}.ticker.atom"
            source, payload = fetch_to_path(ticker_url, ticker_path, args.user_agent)
            record["sources"].append(source)
            time.sleep(args.delay_seconds)
            try:
                candidate_ciks = list(parse_sec_browse_atom_ciks(payload.decode("utf-8")))
            except (UnicodeDecodeError, ValueError):
                candidate_ciks = []
            resolution_method = "SEC_TICKER_SEARCH"

        if not candidate_ciks:
            search_terms = [str(expected["name"])]
            simplified_name = normalized_issuer_name(str(expected["name"]))
            if simplified_name not in search_terms:
                search_terms.append(simplified_name)
            for search_index, search_term in enumerate(search_terms, start=1):
                name_url = browse_url(company=search_term)
                name_path = args.output / "browse" / f"{ticker}.name_{search_index}.atom"
                source, payload = fetch_to_path(name_url, name_path, args.user_agent)
                record["sources"].append(source)
                time.sleep(args.delay_seconds)
                try:
                    candidate_ciks = list(parse_sec_browse_atom_ciks(payload.decode("utf-8")))
                except (UnicodeDecodeError, ValueError):
                    candidate_ciks = []
                if candidate_ciks:
                    break
            resolution_method = "SEC_COMPANY_NAME_SEARCH"

        candidates: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
        for cik in candidate_ciks:
            url = data_url("submissions", cik)
            path = args.output / "submissions" / f"CIK{cik:010d}.json"
            source, submission_bytes = fetch_to_path(url, path, args.user_agent)
            record["sources"].append(source)
            time.sleep(args.delay_seconds)
            try:
                submission = json.loads(submission_bytes)
            except json.JSONDecodeError:
                continue
            candidates.append((cik, submission, source))

        issuer_candidates = [
            item for item in candidates if candidate_is_issuer(str(expected["name"]), item[1])
        ]
        direct_unique_issuer = len(candidate_ciks) == 1 and bool(candidates)
        direct_name_match = direct_unique_issuer and sec_issuer_name_matches(
            str(expected["name"]), candidates[0][1]
        )
        direct_operating_issuer = (
            direct_unique_issuer and candidates[0][1].get("entityType") == "operating"
        )
        if direct_name_match or direct_operating_issuer:
            accepted = candidates[0]
            status = (
                "ACCEPTED_TICKER_UNIQUE_NAME_MATCH"
                if direct_name_match
                else "ACCEPTED_TICKER_UNIQUE_NAME_REVIEW"
            )
        elif len(issuer_candidates) == 1:
            accepted = issuer_candidates[0]
            status = "ACCEPTED_UNIQUE_OPERATING_NAME_MATCH"
        else:
            accepted = None
            status = "REJECTED_AMBIGUOUS_OR_MISSING_ISSUER"

        record["resolution_method"] = resolution_method
        record["candidate_ciks"] = candidate_ciks
        record["candidate_entities"] = [
            {
                "cik": cik,
                "name": submission.get("name"),
                "entity_type": submission.get("entityType"),
                "name_match": sec_issuer_name_matches(str(expected["name"]), submission),
            }
            for cik, submission, _ in candidates
        ]
        record["resolution_status"] = status
        if accepted is not None:
            cik, submission, _ = accepted
            record["accepted_cik"] = cik
            record["sec_name"] = submission.get("name")
            facts_url = data_url("companyfacts", cik)
            facts_path = args.output / "companyfacts" / f"CIK{cik:010d}.json"
            facts_source, _ = fetch_to_path(facts_url, facts_path, args.user_agent)
            record["sources"].append(facts_source)
            time.sleep(args.delay_seconds)

        records.append(record)
        atomic_write(
            manifest_path,
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in records).encode(),
        )
        print(
            f"{index:02d}/{len(tickers)} {ticker} {status} {record.get('accepted_cik')}",
            flush=True,
        )

    counts: dict[str, int] = {}
    for record in records:
        status = str(record["resolution_status"])
        counts[status] = counts.get(status, 0) + 1
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "source": "SEC EDGAR keyless public endpoints",
        "source_documentation": (
            "https://www.sec.gov/search-filings/edgar-application-programming-interfaces"
        ),
        "cohort_symbol_count": len(tickers),
        "resolution_status_counts": dict(sorted(counts.items())),
        "accepted_symbol_count": sum(
            count for status, count in counts.items() if status.startswith("ACCEPTED_")
        ),
        "identity_gate_pass": all(
            str(record["resolution_status"]).startswith("ACCEPTED_") for record in records
        ),
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY",
        "manifest": {
            "path": str(manifest_path),
            "sha256": sha256(manifest_path.read_bytes()).hexdigest(),
        },
    }
    atomic_write(summary_path, (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode())
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["identity_gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
