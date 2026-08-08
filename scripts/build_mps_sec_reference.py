#!/usr/bin/env python3
"""Build SEC stable-identity and point-in-time shares evidence for an MPS cohort."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from swingmachine.mps_public_data import extract_sec_shares_facts, parse_sec_submissions


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


def source_for(record: dict[str, Any], marker: str) -> dict[str, Any] | None:
    matches = [source for source in record["sources"] if marker in str(source["path"])]
    return matches[0] if len(matches) == 1 else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--prices", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    price_rows = pq.read_table(args.prices, columns=["security_id", "ticker"]).to_pylist()
    security_by_ticker = {str(row["ticker"]): str(row["security_id"]) for row in price_rows}
    records = [json.loads(line) for line in args.manifest.read_text().splitlines() if line]
    status_counts = Counter(str(record["resolution_status"]) for record in records)
    identity_rows: list[dict[str, Any]] = []
    share_rows: list[dict[str, Any]] = []
    rejected_sources: list[dict[str, Any]] = []

    for record in records:
        status = str(record["resolution_status"])
        if not status.startswith("ACCEPTED_"):
            continue
        ticker = str(record["ticker"])
        submissions_source = source_for(record, "/submissions/")
        facts_source = source_for(record, "/companyfacts/")
        if submissions_source is None or facts_source is None:
            rejected_sources.append({"ticker": ticker, "reason": "MISSING_UNIQUE_SOURCE"})
            continue
        submissions_path = Path(submissions_source["path"])
        facts_path = Path(facts_source["path"])
        if (
            file_sha256(submissions_path) != submissions_source["sha256"]
            or file_sha256(facts_path) != facts_source["sha256"]
        ):
            rejected_sources.append({"ticker": ticker, "reason": "SOURCE_HASH_MISMATCH"})
            continue
        try:
            submissions_payload = json.loads(submissions_path.read_text())
            facts_payload = json.loads(facts_path.read_text())
            issuer = parse_sec_submissions(submissions_payload)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            rejected_sources.append({"ticker": ticker, "reason": "INVALID_SEC_JSON"})
            continue

        security_id = security_by_ticker[ticker]
        identity_rows.append(
            {
                "security_id": security_id,
                "ticker": ticker,
                "expected_name": record["expected_name"],
                "expected_delisting_date": record["expected_delisting_date"],
                "cik": issuer.cik,
                "sec_name": issuer.name,
                "entity_type": issuer.entity_type,
                "sic": issuer.sic,
                "sic_description": issuer.sic_description,
                "sec_tickers": list(issuer.tickers),
                "sec_exchanges": list(issuer.exchanges),
                "former_names_json": json.dumps(issuer.former_names, sort_keys=True),
                "resolution_status": status,
                "submissions_source_sha256": submissions_source["sha256"],
                "companyfacts_source_sha256": facts_source["sha256"],
            }
        )
        for fact in extract_sec_shares_facts(facts_payload, issuer):
            share_rows.append(
                {
                    "security_id": security_id,
                    "ticker": ticker,
                    "cik": fact.cik,
                    "concept": fact.concept,
                    "shares_outstanding": fact.value,
                    "period_end": fact.period_end.isoformat(),
                    "accession": fact.accession,
                    "form": fact.form,
                    "filed": fact.filed.isoformat(),
                    "available_at": fact.available_at.isoformat(),
                    "companyfacts_source_sha256": facts_source["sha256"],
                }
            )

    identity_path = args.output / "sec_identity_reference.parquet"
    shares_path = args.output / "sec_shares_facts.parquet"
    pq.write_table(pa.Table.from_pylist(identity_rows), identity_path, compression="zstd")
    if share_rows:
        pq.write_table(pa.Table.from_pylist(share_rows), shares_path, compression="zstd")
    else:
        pq.write_table(
            pa.table(
                {
                    "security_id": pa.array([], type=pa.string()),
                    "ticker": pa.array([], type=pa.string()),
                    "cik": pa.array([], type=pa.int64()),
                    "shares_outstanding": pa.array([], type=pa.float64()),
                    "available_at": pa.array([], type=pa.string()),
                }
            ),
            shares_path,
            compression="zstd",
        )

    symbols_with_shares = {row["ticker"] for row in share_rows}
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "source": "SEC EDGAR submissions and companyfacts",
        "cohort_symbol_count": len(security_by_ticker),
        "manifest_record_count": len(records),
        "resolution_status_counts": dict(sorted(status_counts.items())),
        "identity_row_count": len(identity_rows),
        "identity_source_rejections": rejected_sources,
        "shares_fact_count": len(share_rows),
        "symbols_with_shares_facts": len(symbols_with_shares),
        "identity_gate_pass": len(identity_rows) == len(security_by_ticker),
        "shares_source_gate_pass": len(symbols_with_shares) == len(security_by_ticker),
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY",
        "outputs": {
            "identity": {"path": str(identity_path), "sha256": file_sha256(identity_path)},
            "shares": {"path": str(shares_path), "sha256": file_sha256(shares_path)},
        },
    }
    atomic_write(
        args.output / "sec_reference_summary.json",
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["identity_gate_pass"] and summary["shares_source_gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
