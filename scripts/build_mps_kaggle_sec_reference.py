#!/usr/bin/env python3
"""Build stable CIK identity and point-in-time shares evidence from anonymous SEC mirrors."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq


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


def atomic_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(pa.Table.from_pylist(rows), temporary, compression="zstd")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution-seed", type=Path, required=True)
    parser.add_argument("--cik-lookup", type=Path, required=True)
    parser.add_argument("--cik-metadata", type=Path, required=True)
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--submissions", type=Path, required=True)
    parser.add_argument("--facts-metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    seed_payload = json.loads(args.resolution_seed.read_text(encoding="utf-8"))
    resolutions = seed_payload if isinstance(seed_payload, list) else seed_payload["resolutions"]
    cohort_rows = [
        {
            "ticker": str(row["ticker"]),
            "cik": int(row["accepted_cik"]),
            "expected_name": str(row["expected_name"]),
            "stable_security_id": f"CIK-{int(row['accepted_cik']):010d}",
        }
        for row in resolutions
    ]
    ticker_by_cik = {row["cik"]: row["ticker"] for row in cohort_rows}

    connection = duckdb.connect()
    connection.execute("SET threads=4")
    connection.register("cohort", pa.Table.from_pylist(cohort_rows))
    connection.from_parquet(str(args.facts)).create_view("mirror_facts")
    connection.read_csv(str(args.submissions), header=True).create_view("mirror_submissions")
    lookup_rows = connection.execute(
        """
        SELECT c.ticker, c.cik, c.expected_name, c.stable_security_id,
               list(l.name ORDER BY l.name) AS sec_names
        FROM cohort c
        LEFT JOIN read_parquet(?) l USING (cik)
        GROUP BY ALL
        ORDER BY c.ticker
        """,
        [str(args.cik_lookup)],
    ).fetchall()
    identity_rows = [
        {
            "ticker": row[0],
            "cik": row[1],
            "expected_name": row[2],
            "stable_security_id": row[3],
            "sec_names": row[4],
            "identity_status": "CIK_PRESENT" if row[4] and row[4][0] is not None else "CIK_MISSING",
        }
        for row in lookup_rows
    ]
    identity_path = args.output / "sec_cik_identity.parquet"
    atomic_parquet(identity_rows, identity_path)

    shares_path = args.output / "sec_shares_facts.parquet"
    temporary_shares = shares_path.with_suffix(shares_path.suffix + ".tmp")
    connection.sql(
        """
        SELECT DISTINCT
            c.stable_security_id,
            c.ticker,
            s.cik,
            s.adsh AS accession_compact,
            s.form,
            CAST(s.period AS VARCHAR) AS filing_period,
            CAST(s.accepted AS VARCHAR) AS available_at,
            f.tag AS concept,
            CAST(f.start AS VARCHAR) AS period_start,
            CAST(f.end AS VARCHAR) AS period_end,
            f.value AS shares_outstanding
        FROM mirror_facts f
        JOIN mirror_submissions s USING (adsh)
        JOIN cohort c USING (cik)
        WHERE f.tag IN (
            'EntityCommonStockSharesOutstanding',
            'CommonStockSharesOutstanding'
        )
        ORDER BY c.ticker, s.accepted, f.end, f.tag, f.value
        """
    ).write_parquet(str(temporary_shares), compression="zstd")
    temporary_shares.replace(shares_path)
    shares = pq.read_table(shares_path)
    shares_rows = shares.to_pylist()
    symbols_with_shares = {str(row["ticker"]) for row in shares_rows}

    values_by_key: dict[tuple[Any, ...], set[float]] = {}
    for row in shares_rows:
        key = (
            row["cik"],
            row["accession_compact"],
            row["concept"],
            row["period_end"],
        )
        values_by_key.setdefault(key, set()).add(float(row["shares_outstanding"]))
    conflict_count = sum(len(values) > 1 for values in values_by_key.values())

    cik_metadata = json.loads(args.cik_metadata.read_text(encoding="utf-8"))
    facts_metadata = json.loads(args.facts_metadata.read_text(encoding="utf-8"))
    identity_missing = [
        row["ticker"] for row in identity_rows if row["identity_status"] != "CIK_PRESENT"
    ]
    shares_missing = sorted(set(ticker_by_cik.values()) - symbols_with_shares)
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "cohort_symbol_count": len(cohort_rows),
        "identity_row_count": len(identity_rows),
        "identity_missing_symbols": identity_missing,
        "identity_gate_pass": not identity_missing,
        "shares_fact_count": shares.num_rows,
        "symbols_with_shares_facts": len(symbols_with_shares),
        "shares_missing_symbols": shares_missing,
        "shares_conflict_key_count": conflict_count,
        "shares_source_gate_pass": len(symbols_with_shares) == len(cohort_rows),
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY",
        "sources": {
            "cik_mirror": {
                "dataset": cik_metadata.get("ref"),
                "license": cik_metadata.get("licenseName"),
                "last_updated": cik_metadata.get("lastUpdated"),
                "path": str(args.cik_lookup),
                "sha256": file_sha256(args.cik_lookup),
            },
            "financial_facts_mirror": {
                "dataset": facts_metadata.get("ref"),
                "license": facts_metadata.get("licenseName"),
                "last_updated": facts_metadata.get("lastUpdated"),
                "facts_path": str(args.facts),
                "facts_sha256": file_sha256(args.facts),
                "submissions_path": str(args.submissions),
                "submissions_sha256": file_sha256(args.submissions),
            },
        },
        "outputs": {
            "identity": {"path": str(identity_path), "sha256": file_sha256(identity_path)},
            "shares": {"path": str(shares_path), "sha256": file_sha256(shares_path)},
        },
    }
    atomic_write(
        args.output / "sec_kaggle_reference_summary.json",
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["identity_gate_pass"] and conflict_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
