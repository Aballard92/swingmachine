#!/usr/bin/env python3
"""Classify acquired MPS symbols from preserved OpenFIGI responses."""

from __future__ import annotations

import argparse
import json
from collections import Counter
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--openfigi-raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    queue = {
        row["ticker"]: row for row in json.loads(args.queue.read_text(encoding="utf-8"))["selected"]
    }
    rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    for path in sorted(args.openfigi_raw_dir.glob("*.json")):
        ticker = path.stem.upper()
        document = json.loads(path.read_text(encoding="utf-8"))
        response = document["response"]
        candidates = response.get("data", [])
        if not candidates:
            status = "NO_IDENTIFIER"
        elif len(candidates) != 1:
            status = "AMBIGUOUS_IDENTITY"
        elif candidates[0].get("securityType2") != "Common Stock":
            status = "PROVEN_NON_COMMON"
        else:
            status = "PROVEN_UNIQUE_COMMON_STOCK"
        status_counts[status] += 1
        expected = queue.get(ticker, {})
        rows.append(
            {
                "ticker": ticker,
                "expected_name": expected.get("name"),
                "expected_exchange": expected.get("exchange"),
                "expected_delisting_date": expected.get("alpha_delisting_date"),
                "classification_status": status,
                "candidate_count": len(candidates),
                "candidate_security_types": sorted(
                    {
                        str(candidate.get("securityType"))
                        for candidate in candidates
                        if candidate.get("securityType") is not None
                    }
                ),
                "candidate_security_types_2": sorted(
                    {
                        str(candidate.get("securityType2"))
                        for candidate in candidates
                        if candidate.get("securityType2") is not None
                    }
                ),
                "candidate_names": [candidate.get("name") for candidate in candidates],
                "candidate_figis": [candidate.get("figi") for candidate in candidates],
                "candidate_composite_figis": [
                    candidate.get("compositeFIGI") for candidate in candidates
                ],
                "source_path": str(path),
                "source_sha256": file_sha256(path),
                "warning": response.get("warning"),
                "error": response.get("error"),
            }
        )

    parquet_path = args.output_dir / "openfigi_security_classification.parquet"
    pq.write_table(pa.Table.from_pylist(rows), parquet_path, compression="zstd")
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "api_version": "OpenFIGI v3",
        "input_queue": {
            "path": str(args.queue),
            "sha256": file_sha256(args.queue),
        },
        "classified_symbol_count": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "common_stock_gate_pass": (
            bool(rows) and status_counts["PROVEN_UNIQUE_COMMON_STOCK"] == len(rows)
        ),
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY",
        "handling": {
            "PROVEN_UNIQUE_COMMON_STOCK": "eligible for later gates",
            "PROVEN_NON_COMMON": "exclude",
            "AMBIGUOUS_IDENTITY": "reject until stable identity is proven",
            "NO_IDENTIFIER": "reject until independently classified",
        },
        "output": {
            "path": str(parquet_path),
            "sha256": file_sha256(parquet_path),
        },
    }
    (args.output_dir / "openfigi_security_classification_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "classified_symbol_count",
                    "status_counts",
                    "common_stock_gate_pass",
                    "decision",
                )
            },
            indent=2,
        )
    )
    return 0 if summary["common_stock_gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
