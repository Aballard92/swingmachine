#!/usr/bin/env python3
"""Reconcile primary and fallback SEC point-in-time shares evidence."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, date, datetime, time
from hashlib import sha256
from pathlib import Path
from typing import Any

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


def date_text(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    return date.fromisoformat(str(value)[:10]).isoformat()


def conservative_available_at(value: Any) -> str:
    value_date = date.fromisoformat(str(value)[:10])
    return datetime.combine(value_date, time.max, tzinfo=UTC).isoformat().replace("+00:00", "Z")


def accession_key(value: Any) -> int:
    return int(str(value).replace("-", ""))


def comparison_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        int(row["cik"]),
        accession_key(row["accession_compact"]),
        str(row["concept"]),
        date_text(row["period_end"]),
    )


def canonical_primary(row: dict[str, Any], *, source_sha256: str) -> dict[str, Any]:
    source_available_at = str(row["available_at"])
    return {
        "stable_security_id": str(row["stable_security_id"]),
        "ticker": str(row["ticker"]).upper(),
        "cik": int(row["cik"]),
        "accession_compact": str(row["accession_compact"]),
        "form": str(row["form"]),
        "filing_period": str(row["filing_period"]),
        "source_available_at": source_available_at,
        "available_at": conservative_available_at(source_available_at),
        "availability_precision": "DATE_END_OF_DAY_CONSERVATIVE",
        "concept": str(row["concept"]),
        "period_start": (
            None if row.get("period_start") is None else date_text(row["period_start"])
        ),
        "period_end": date_text(row["period_end"]),
        "shares_outstanding": float(row["shares_outstanding"]),
        "source_kind": "KAGGLE_SEC_FINANCIAL_FACTS_MIRROR",
        "source_priority": 1,
        "source_sha256": source_sha256,
    }


def canonical_fallback(
    row: dict[str, Any],
    *,
    source_sha256: str,
    source_kind: str = "HF_SEC_COMPANYFACTS_MIRROR",
    source_priority: int = 2,
) -> dict[str, Any]:
    source_available_at = str(row["available_at"])
    return {
        "stable_security_id": str(row["stable_security_id"]),
        "ticker": str(row["ticker"]).upper(),
        "cik": int(row["cik"]),
        "accession_compact": str(row["accession_compact"]),
        "form": str(row["form"]),
        "filing_period": str(row["filing_period"]),
        "source_available_at": source_available_at,
        "available_at": conservative_available_at(source_available_at),
        "availability_precision": "DATE_END_OF_DAY_CONSERVATIVE",
        "concept": str(row["concept"]),
        "period_start": (
            None if row.get("period_start") is None else date_text(row["period_start"])
        ),
        "period_end": date_text(row["period_end"]),
        "shares_outstanding": float(row["shares_outstanding"]),
        "source_kind": source_kind,
        "source_priority": source_priority,
        "source_sha256": source_sha256,
    }


def reconcile_rows(
    primary_rows: list[dict[str, Any]],
    fallback_rows: list[dict[str, Any]],
    *,
    primary_sha256: str,
    fallback_sha256: str,
    filing_rows: list[dict[str, Any]] | None = None,
    filing_sha256: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    filing_rows = filing_rows or []
    if filing_rows and filing_sha256 is None:
        raise ValueError("filing source SHA256 is required when filing rows are supplied")
    primary_symbols = {str(row["ticker"]).upper() for row in primary_rows}
    fallback_symbols = {str(row["ticker"]).upper() for row in fallback_rows}
    fill_symbols = fallback_symbols - primary_symbols
    filing_symbols = {str(row["ticker"]).upper() for row in filing_rows}
    filing_fill_symbols = filing_symbols - primary_symbols - fallback_symbols

    primary_by_key: dict[tuple[Any, ...], set[float]] = defaultdict(set)
    fallback_by_key: dict[tuple[Any, ...], set[float]] = defaultdict(set)
    for row in primary_rows:
        primary_by_key[comparison_key(row)].add(float(row["shares_outstanding"]))
    for row in fallback_rows:
        fallback_by_key[comparison_key(row)].add(float(row["shares_outstanding"]))
    overlap_keys = set(primary_by_key) & set(fallback_by_key)
    overlap_conflicts = sum(primary_by_key[key] != fallback_by_key[key] for key in overlap_keys)

    rows = [canonical_primary(row, source_sha256=primary_sha256) for row in primary_rows]
    rows.extend(
        canonical_fallback(row, source_sha256=fallback_sha256)
        for row in fallback_rows
        if str(row["ticker"]).upper() in fill_symbols
    )
    rows.extend(
        canonical_fallback(
            row,
            source_sha256=str(filing_sha256),
            source_kind="SEC_INLINE_XBRL_PRIMARY_FILING",
            source_priority=3,
        )
        for row in filing_rows
        if str(row["ticker"]).upper() in filing_fill_symbols
    )
    rows.sort(
        key=lambda row: (
            row["ticker"],
            row["available_at"],
            row["period_end"],
            row["concept"],
            accession_key(row["accession_compact"]),
            row["shares_outstanding"],
        )
    )
    values_by_key: dict[tuple[Any, ...], set[float]] = defaultdict(set)
    for row in rows:
        values_by_key[comparison_key(row)].add(float(row["shares_outstanding"]))
    union_conflicts = sum(len(values) > 1 for values in values_by_key.values())
    evidence = {
        "primary_symbol_count": len(primary_symbols),
        "fallback_symbol_count": len(fallback_symbols),
        "fallback_fill_symbols": sorted(fill_symbols),
        "filing_fallback_symbol_count": len(filing_symbols),
        "filing_fallback_fill_symbols": sorted(filing_fill_symbols),
        "overlap_exact_key_count": len(overlap_keys),
        "overlap_value_conflict_count": overlap_conflicts,
        "union_conflict_key_count": union_conflicts,
    }
    return rows, evidence


def load_cohort(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    resolutions = payload if isinstance(payload, list) else payload["resolutions"]
    unresolved = [row["ticker"] for row in resolutions if row.get("accepted_cik") is None]
    if unresolved:
        raise ValueError(f"unresolved CIKs in cohort: {sorted(unresolved)}")
    return {str(row["ticker"]).upper() for row in resolutions}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--fallback", type=Path, required=True)
    parser.add_argument("--filing-fallback", type=Path)
    parser.add_argument("--filing-fallback-summary", type=Path)
    parser.add_argument("--resolution-seed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    primary_sha256 = file_sha256(args.primary)
    fallback_sha256 = file_sha256(args.fallback)
    filing_sha256 = file_sha256(args.filing_fallback) if args.filing_fallback is not None else None
    primary_rows = pq.read_table(args.primary).to_pylist()
    fallback_rows = pq.read_table(args.fallback).to_pylist()
    filing_rows = (
        pq.read_table(args.filing_fallback).to_pylist() if args.filing_fallback is not None else []
    )
    filing_summary = (
        json.loads(args.filing_fallback_summary.read_text(encoding="utf-8"))
        if args.filing_fallback_summary is not None
        else None
    )
    if filing_summary is not None and args.filing_fallback is None:
        raise ValueError("filing fallback summary requires a filing fallback")
    rows, evidence = reconcile_rows(
        primary_rows,
        fallback_rows,
        primary_sha256=primary_sha256,
        fallback_sha256=fallback_sha256,
        filing_rows=filing_rows,
        filing_sha256=filing_sha256,
    )
    cohort = load_cohort(args.resolution_seed)
    symbols_with_shares = {str(row["ticker"]) for row in rows}

    shares_path = args.output / "sec_shares_union.parquet"
    atomic_parquet(rows, shares_path)
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "source_precedence": [
            "KAGGLE_SEC_FINANCIAL_FACTS_MIRROR",
            "HF_SEC_COMPANYFACTS_MIRROR_FOR_PRIMARY_MISSING_SYMBOLS_ONLY",
            "SEC_INLINE_XBRL_PRIMARY_FILING_FOR_REMAINING_SYMBOLS_ONLY",
        ],
        "cohort_symbol_count": len(cohort),
        "shares_fact_count": len(rows),
        "symbols_with_shares_facts": len(symbols_with_shares),
        "shares_missing_symbols": sorted(cohort - symbols_with_shares),
        "shares_source_gate_pass": symbols_with_shares == cohort,
        "availability_policy": "DATE_END_OF_DAY_CONSERVATIVE",
        "filing_fallback_history_start_gate_pass": (
            None if filing_summary is None else bool(filing_summary["history_start_gate_pass"])
        ),
        "filing_fallback_history_start_gaps": (
            None if filing_summary is None else filing_summary["history_start_gaps"]
        ),
        **evidence,
        "sources": {
            "primary": {
                "path": str(args.primary),
                "sha256": primary_sha256,
            },
            "fallback": {
                "path": str(args.fallback),
                "sha256": fallback_sha256,
            },
            "filing_fallback": (
                None
                if args.filing_fallback is None
                else {
                    "path": str(args.filing_fallback),
                    "sha256": filing_sha256,
                    "summary_path": (
                        None
                        if args.filing_fallback_summary is None
                        else str(args.filing_fallback_summary)
                    ),
                    "summary_sha256": (
                        None
                        if args.filing_fallback_summary is None
                        else file_sha256(args.filing_fallback_summary)
                    ),
                }
            ),
        },
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY",
        "output": {
            "path": str(shares_path),
            "sha256": file_sha256(shares_path),
        },
    }
    atomic_write(
        args.output / "sec_shares_union_summary.json",
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return (
        0
        if evidence["overlap_value_conflict_count"] == 0
        and evidence["union_conflict_key_count"] == 0
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
