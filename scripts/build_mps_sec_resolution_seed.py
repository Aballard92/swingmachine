#!/usr/bin/env python3
"""Resolve an MPS price cohort to stable SEC CIKs from anonymous mirror evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from swingmachine.mps_public_data import normalized_issuer_name


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


def choose_resolution(
    ticker_ciks: set[int],
    name_ciks: set[int],
    override: dict[str, Any] | None,
) -> tuple[int | None, str]:
    if override is not None:
        return int(override["accepted_cik"]), "REVIEWED_SEC_SUBMISSIONS_OVERRIDE"
    if len(ticker_ciks) == 1:
        ticker_cik = next(iter(ticker_ciks))
        if len(name_ciks) == 1 and ticker_cik not in name_ciks:
            return None, "REJECTED_TICKER_NAME_CONFLICT"
        return ticker_cik, "UNIQUE_HISTORICAL_FILING_TICKER"
    if len(ticker_ciks) > 1:
        intersection = ticker_ciks & name_ciks
        if len(intersection) == 1:
            return next(iter(intersection)), "UNIQUE_TICKER_NAME_INTERSECTION"
        return None, "REJECTED_AMBIGUOUS_HISTORICAL_TICKER"
    if len(name_ciks) == 1:
        return next(iter(name_ciks)), "UNIQUE_NORMALIZED_SEC_NAME"
    if len(name_ciks) > 1:
        return None, "REJECTED_AMBIGUOUS_SEC_NAME"
    return None, "REJECTED_MISSING_SEC_IDENTITY"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--cik-lookup", type=Path, required=True)
    parser.add_argument("--submissions", type=Path, required=True)
    parser.add_argument("--overrides", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    tickers = sorted(
        str(value).upper()
        for value in pq.read_table(args.prices, columns=["ticker"])
        .column("ticker")
        .unique()
        .to_pylist()
    )
    queue_payload = json.loads(args.queue.read_text(encoding="utf-8"))
    expected_by_ticker = {str(row["ticker"]).upper(): row for row in queue_payload["selected"]}
    missing_queue = sorted(set(tickers) - set(expected_by_ticker))
    if missing_queue:
        raise ValueError(f"cohort tickers missing from queue: {missing_queue}")

    cohort_rows = [
        {
            "ticker": ticker,
            "expected_name": str(expected_by_ticker[ticker]["name"]),
            "expected_norm": normalized_issuer_name(str(expected_by_ticker[ticker]["name"])),
        }
        for ticker in tickers
    ]
    connection = duckdb.connect()
    connection.execute("SET threads=4")
    connection.register("cohort", pa.Table.from_pylist(cohort_rows))

    ticker_rows = connection.execute(
        """
        SELECT c.ticker, s.cik
        FROM cohort c
        JOIN read_csv(?, header=true) s ON upper(s.ticker) = c.ticker
        GROUP BY ALL
        ORDER BY c.ticker, s.cik
        """,
        [str(args.submissions)],
    ).fetchall()
    ticker_ciks: dict[str, set[int]] = {ticker: set() for ticker in tickers}
    for ticker, cik in ticker_rows:
        ticker_ciks[str(ticker)].add(int(cik))

    name_rows = connection.execute(
        r"""
        WITH raw AS (
            SELECT
                cik,
                name,
                regexp_replace(
                    regexp_replace(
                        regexp_replace(
                            regexp_replace(
                                upper(replace(name, '&', ' AND ')),
                                '\s+-\s+CLASS\s+[A-Z0-9]+$',
                                ''
                            ),
                            '\b(CLASS|COMMON STOCK)\s+[A-Z0-9]+$',
                            ''
                        ),
                        '\b(INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC)\b',
                        ' ',
                        'g'
                    ),
                    '[^A-Z0-9]+',
                    ' ',
                    'g'
                ) AS normalization_step
            FROM read_parquet(?)
        ),
        normalized AS (
            SELECT
                cik,
                name,
                trim(regexp_replace(normalization_step, '\s+', ' ', 'g')) AS issuer_norm
            FROM raw
        )
        SELECT c.ticker, n.cik
        FROM cohort c
        JOIN normalized n ON n.issuer_norm = c.expected_norm
        GROUP BY ALL
        ORDER BY c.ticker, n.cik
        """,
        [str(args.cik_lookup)],
    ).fetchall()
    name_ciks: dict[str, set[int]] = {ticker: set() for ticker in tickers}
    for ticker, cik in name_rows:
        name_ciks[str(ticker)].add(int(cik))

    override_payload = json.loads(args.overrides.read_text(encoding="utf-8"))
    override_rows = (
        override_payload if isinstance(override_payload, list) else override_payload["overrides"]
    )
    overrides = {str(row["ticker"]).upper(): row for row in override_rows}
    unknown_overrides = sorted(set(overrides) - set(tickers))
    if unknown_overrides:
        raise ValueError(f"overrides outside cohort: {unknown_overrides}")
    for ticker, override in overrides.items():
        evidence_records = [
            {
                "path": override["evidence_path"],
                "sha256": override["evidence_sha256"],
            },
            *override.get("additional_evidence", ()),
        ]
        for evidence in evidence_records:
            evidence_path = Path(str(evidence["path"]))
            if not evidence_path.is_absolute():
                evidence_path = args.overrides.parent / evidence_path
            actual_hash = file_sha256(evidence_path)
            if actual_hash != evidence["sha256"]:
                raise ValueError(f"review evidence hash mismatch for {ticker}")
        accepted_cik = int(override["accepted_cik"])
        cik_exists = connection.execute(
            "SELECT count(*) FROM read_parquet(?) WHERE cik = ?",
            [str(args.cik_lookup), accepted_cik],
        ).fetchone()[0]
        if not cik_exists:
            raise ValueError(f"reviewed CIK absent from lookup for {ticker}")

    resolutions = []
    status_counts: Counter[str] = Counter()
    for cohort in cohort_rows:
        ticker = str(cohort["ticker"])
        accepted_cik, status = choose_resolution(
            ticker_ciks[ticker],
            name_ciks[ticker],
            overrides.get(ticker),
        )
        status_counts[status] += 1
        row = {
            "ticker": ticker,
            "expected_name": cohort["expected_name"],
            "accepted_cik": accepted_cik,
            "resolution_status": status,
            "historical_ticker_candidate_ciks": sorted(ticker_ciks[ticker]),
            "normalized_name_candidate_ciks": sorted(name_ciks[ticker]),
        }
        if ticker in overrides:
            row["review"] = overrides[ticker]
        resolutions.append(row)

    unresolved = [row["ticker"] for row in resolutions if row["accepted_cik"] is None]
    payload = {
        "task_id": "SWING-MPS-DATA-001",
        "cohort_symbol_count": len(tickers),
        "identity_gate_pass": not unresolved,
        "unresolved_symbols": unresolved,
        "status_counts": dict(sorted(status_counts.items())),
        "source_hashes": {
            "prices": file_sha256(args.prices),
            "queue": file_sha256(args.queue),
            "cik_lookup": file_sha256(args.cik_lookup),
            "submissions": file_sha256(args.submissions),
            "overrides": file_sha256(args.overrides),
        },
        "resolutions": resolutions,
    }
    atomic_write(
        args.output,
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode(),
    )
    summary = {key: value for key, value in payload.items() if key != "resolutions"}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if payload["identity_gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
