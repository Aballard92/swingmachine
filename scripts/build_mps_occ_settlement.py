#!/usr/bin/env python3
"""Normalize explicit delisting-settlement evidence from bounded OCC memo captures."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
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


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def load_cash_parser() -> Any:
    script = Path(__file__).with_name("acquire_mps_occ_memos.py")
    spec = importlib.util.spec_from_file_location("acquire_mps_occ_memos", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load OCC memo parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.cash_values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cash_values = load_cash_parser()

    records = [json.loads(line) for line in args.manifest.read_text().splitlines() if line]
    output_rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    rejected_hashes = []
    for record in records:
        final_values: set[float] = set()
        contingent = False
        final_memos = []
        non_cash_titles = []
        for memo in record["relevant_memos"]:
            path = Path(memo["path"])
            if file_sha256(path) != memo["sha256"]:
                rejected_hashes.append({"ticker": record["ticker"], "path": str(path)})
                continue
            markdown = path.read_text(encoding="utf-8")
            if memo["is_final_cash_settlement"]:
                values = cash_values(markdown)
                final_values.update(values)
                final_memos.append(int(memo["memo_number"]))
                contingent = contingent or bool(
                    re.search(
                        r"\b(CVR|CONTINGENT VALUE RIGHT|DAP RIGHT|DIVESTED ASSET PROCEED RIGHT)",
                        markdown,
                        re.I,
                    )
                )
            elif any(
                marker in memo["title"].upper()
                for marker in ("MERGER", "CONTRACT ADJUSTMENT", "DETERMINATION OF DELIVERABLE")
            ):
                non_cash_titles.append(memo["title"])

        if len(final_values) == 1:
            status = "FINAL_CASH_PLUS_CONTINGENT_RIGHT" if contingent else "FINAL_CASH_EXPLICIT"
            cash_per_share = next(iter(final_values))
        elif len(final_values) > 1:
            status = "FINAL_CASH_COMPONENTS_AMBIGUOUS"
            cash_per_share = None
        elif final_memos:
            status = "FINAL_CASH_MEMO_UNPARSED"
            cash_per_share = None
        elif non_cash_titles:
            status = "NON_CASH_OR_ELECTION_MERGER_UNPARSED"
            cash_per_share = None
        elif record["relevant_memos"]:
            status = "OCC_MEMO_PRESENT_SETTLEMENT_UNRESOLVED"
            cash_per_share = None
        else:
            status = "NO_OCC_MEMO"
            cash_per_share = None
        status_counts[status] += 1
        output_rows.append(
            {
                "ticker": record["ticker"],
                "expected_name": record["expected_name"],
                "settlement_status": status,
                "guaranteed_cash_per_share": cash_per_share,
                "cash_per_share_candidates": sorted(final_values),
                "has_contingent_right": contingent,
                "final_cash_memo_numbers": sorted(final_memos),
                "relevant_memo_count": len(record["relevant_memos"]),
                "search_source_url": record["search_underlying_url"],
                "search_source_sha256": record["search_sha256"],
            }
        )

    output_path = args.output / "occ_settlement_reference.parquet"
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    pq.write_table(pa.Table.from_pylist(output_rows), temporary, compression="zstd")
    temporary.replace(output_path)
    explicit_count = sum(
        count
        for status, count in status_counts.items()
        if status in {"FINAL_CASH_EXPLICIT", "FINAL_CASH_PLUS_CONTINGENT_RIGHT"}
    )
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "cohort_symbol_count": len(records),
        "status_counts": dict(sorted(status_counts.items())),
        "explicit_guaranteed_cash_symbols": explicit_count,
        "source_hash_rejections": rejected_hashes,
        "settlement_gate_pass": explicit_count == len(records) and not rejected_hashes,
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY_REQUIRES_PRIMARY_SOURCE_CROSS_CHECK",
        "source_warning": (
            "OCC memos are unofficial summaries; complex stock/election mergers and contingent "
            "rights remain fail-closed."
        ),
        "output": {"path": str(output_path), "sha256": file_sha256(output_path)},
    }
    atomic_write(
        args.output / "occ_settlement_summary.json",
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["settlement_gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
