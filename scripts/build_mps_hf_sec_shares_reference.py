#!/usr/bin/env python3
"""Build point-in-time shares evidence from a pinned Hugging Face SEC mirror."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import UTC, date, datetime, time
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

CIK_PATTERN = re.compile(r"^CIK(?P<cik>\d{10})_")
EXPECTED_LABEL = "Entity Common Stock, Shares Outstanding"
EXPECTED_CONCEPT = "EntityCommonStockSharesOutstanding"
REQUIRED_COLUMNS = {
    "end",
    "accn",
    "fy",
    "fp",
    "form",
    "filed",
    "unit",
    "val_dec",
    "source_folder",
    "label",
}


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


def source_cik(source_folder: str) -> int | None:
    match = CIK_PATTERN.match(source_folder)
    return None if match is None else int(match.group("cik"))


def conservative_available_at(filed: str) -> str:
    filed_date = date.fromisoformat(filed)
    return (
        datetime.combine(
            filed_date,
            time.max,
            tzinfo=UTC,
        )
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_resolutions(path: Path) -> dict[int, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload["resolutions"]
    resolutions: dict[int, dict[str, Any]] = {}
    for row in rows:
        cik = row.get("accepted_cik")
        if cik is None:
            raise ValueError(f"unresolved CIK in resolution seed: {row.get('ticker')}")
        cik = int(cik)
        if cik in resolutions:
            raise ValueError(f"duplicate CIK in resolution seed: {cik}")
        resolutions[cik] = row
    return resolutions


def normalized_rows(
    table: pa.Table,
    resolutions: dict[int, dict[str, Any]],
    *,
    source_sha256: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    missing_columns = sorted(REQUIRED_COLUMNS - set(table.column_names))
    if missing_columns:
        raise ValueError(f"source is missing required columns: {missing_columns}")
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for source in table.select(sorted(REQUIRED_COLUMNS)).to_pylist():
        cik = source_cik(str(source["source_folder"]))
        if cik not in resolutions:
            continue
        ticker = str(resolutions[cik]["ticker"]).upper()
        reason = None
        if source["label"] != EXPECTED_LABEL:
            reason = "UNEXPECTED_LABEL"
        elif source["unit"] != "shares":
            reason = "UNEXPECTED_UNIT"
        elif source["val_dec"] is None or Decimal(source["val_dec"]) <= 0:
            reason = "INVALID_SHARE_VALUE"
        try:
            available_at = conservative_available_at(str(source["filed"]))
            date.fromisoformat(str(source["end"]))
        except ValueError:
            reason = reason or "INVALID_DATE"
            available_at = None
        if reason is not None:
            rejected.append(
                {
                    "ticker": ticker,
                    "cik": cik,
                    "accession": source["accn"],
                    "reason": reason,
                }
            )
            continue
        accession = str(source["accn"])
        rows.append(
            {
                "stable_security_id": f"CIK-{cik:010d}",
                "ticker": ticker,
                "cik": cik,
                "accession": accession,
                "accession_compact": accession.replace("-", ""),
                "form": str(source["form"]),
                "filing_period": f"{source['fy']}{source['fp']}",
                "available_at": available_at,
                "availability_precision": "FILED_DATE_END_OF_DAY_CONSERVATIVE",
                "concept": EXPECTED_CONCEPT,
                "period_start": None,
                "period_end": str(source["end"]),
                "shares_outstanding": float(Decimal(source["val_dec"])),
                "source_sha256": source_sha256,
            }
        )
    rows.sort(
        key=lambda row: (
            row["ticker"],
            row["available_at"],
            row["period_end"],
            row["accession"],
            row["shares_outstanding"],
        )
    )
    return rows, rejected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution-seed", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(args.acquisition_manifest.read_text(encoding="utf-8"))
    expected_hash = str(manifest["artifact"]["sha256"])
    actual_hash = file_sha256(args.source)
    if actual_hash != expected_hash:
        raise ValueError("source hash does not match acquisition manifest")
    if manifest.get("access") != "ANONYMOUS_NO_ACCOUNT_NO_API_KEY":
        raise ValueError("source access contract is not anonymous")

    resolutions = load_resolutions(args.resolution_seed)
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    parquet = pq.ParquetFile(args.source)
    for batch in parquet.iter_batches(
        batch_size=16_384,
        columns=sorted(REQUIRED_COLUMNS),
    ):
        batch_rows, batch_rejected = normalized_rows(
            pa.Table.from_batches([batch]),
            resolutions,
            source_sha256=actual_hash,
        )
        rows.extend(batch_rows)
        rejected.extend(batch_rejected)
    rows.sort(
        key=lambda row: (
            row["ticker"],
            row["available_at"],
            row["period_end"],
            row["accession"],
            row["shares_outstanding"],
        )
    )

    values_by_key: dict[tuple[Any, ...], set[float]] = defaultdict(set)
    for row in rows:
        key = (
            row["cik"],
            row["accession"],
            row["concept"],
            row["period_end"],
        )
        values_by_key[key].add(float(row["shares_outstanding"]))
    conflict_count = sum(len(values) > 1 for values in values_by_key.values())
    symbols_with_shares = {str(row["ticker"]) for row in rows}
    cohort_symbols = {str(resolution["ticker"]).upper() for resolution in resolutions.values()}

    shares_path = args.output / "hf_sec_shares_facts.parquet"
    atomic_parquet(rows, shares_path)
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "source": "Pinned Hugging Face mirror of SEC EDGAR companyfacts",
        "source_access": manifest["access"],
        "source_dataset_ref": manifest["dataset_ref"],
        "source_pinned_commit": manifest["pinned_commit"],
        "source_sha256": actual_hash,
        "cohort_symbol_count": len(cohort_symbols),
        "shares_fact_count": len(rows),
        "symbols_with_shares_facts": len(symbols_with_shares),
        "shares_missing_symbols": sorted(cohort_symbols - symbols_with_shares),
        "source_rejections": rejected,
        "shares_conflict_key_count": conflict_count,
        "shares_source_gate_pass": symbols_with_shares == cohort_symbols,
        "availability_policy": "FILED_DATE_END_OF_DAY_CONSERVATIVE",
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY",
        "output": {
            "path": str(shares_path),
            "sha256": file_sha256(shares_path),
        },
    }
    atomic_write(
        args.output / "hf_sec_shares_summary.json",
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if conflict_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
