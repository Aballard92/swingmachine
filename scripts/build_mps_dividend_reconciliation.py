#!/usr/bin/env python3
"""Reconcile Tiingo dividend events to Alpha Vantage payment-date evidence."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
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
    parser.add_argument("--corporate-actions", type=Path, required=True)
    parser.add_argument("--alpha-raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    alpha_by_event: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    alpha_sources: dict[str, dict[str, Any]] = {}
    for path in sorted(args.alpha_raw_dir.glob("*.csv")):
        ticker = path.stem.upper()
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        for row in rows:
            alpha_by_event[(ticker, row["ex_dividend_date"])].append(row)
        alpha_sources[ticker] = {
            "path": str(path),
            "sha256": file_sha256(path),
            "rows": len(rows),
        }

    action_rows = pq.read_table(args.corporate_actions).to_pylist()
    dividend_rows = [row for row in action_rows if float(row["div_cash"] or 0) != 0]
    output_rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    for event in dividend_rows:
        ticker = str(event["ticker"])
        ex_date = str(event["trading_date"])
        matches = alpha_by_event.get((ticker, ex_date), [])
        alpha = matches[0] if len(matches) == 1 else None
        if not matches:
            status = "NO_ALPHA_EVENT"
        elif len(matches) > 1:
            status = "AMBIGUOUS_ALPHA_EVENTS"
        elif abs(float(event["div_cash"]) - float(alpha["amount"])) > 1e-8:
            status = "AMOUNT_MISMATCH"
        elif alpha["payment_date"] in ("", "None"):
            status = "MATCHED_PAYMENT_DATE_MISSING"
        else:
            status = "MATCHED_PAYMENT_DATE"
        status_counts[status] += 1
        output_rows.append(
            {
                "security_id": event["security_id"],
                "ticker": ticker,
                "ex_dividend_date": ex_date,
                "div_cash": float(event["div_cash"]),
                "tiingo_available_at": event["available_at"],
                "tiingo_source_file_sha256": event["source_file_sha256"],
                "alpha_declaration_date": None if alpha is None else alpha["declaration_date"],
                "alpha_record_date": None if alpha is None else alpha["record_date"],
                "alpha_payment_date": None
                if alpha is None or alpha["payment_date"] in ("", "None")
                else alpha["payment_date"],
                "alpha_amount": None if alpha is None else float(alpha["amount"]),
                "alpha_source_sha256": None
                if ticker not in alpha_sources
                else alpha_sources[ticker]["sha256"],
                "reconciliation_status": status,
            }
        )

    parquet_path = args.output_dir / "dividend_reconciliation.parquet"
    pq.write_table(pa.Table.from_pylist(output_rows), parquet_path, compression="zstd")
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "source_corporate_actions": {
            "path": str(args.corporate_actions),
            "sha256": file_sha256(args.corporate_actions),
        },
        "alpha_sources": alpha_sources,
        "tiingo_dividend_event_count": len(dividend_rows),
        "alpha_symbol_count": len(alpha_sources),
        "status_counts": dict(sorted(status_counts.items())),
        "payment_date_coverage_fraction": (
            status_counts["MATCHED_PAYMENT_DATE"] / len(dividend_rows) if dividend_rows else 0.0
        ),
        "amount_conflict_count": status_counts["AMOUNT_MISMATCH"],
        "payment_date_gate_pass": (
            bool(dividend_rows) and status_counts["MATCHED_PAYMENT_DATE"] == len(dividend_rows)
        ),
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY",
        "blocking_reason": (
            "Every dividend event requires a reconciled payment date; unresolved events "
            "remain fail-closed."
        ),
        "output": {
            "path": str(parquet_path),
            "sha256": file_sha256(parquet_path),
        },
    }
    (args.output_dir / "dividend_reconciliation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "tiingo_dividend_event_count",
                    "alpha_symbol_count",
                    "status_counts",
                    "payment_date_coverage_fraction",
                    "payment_date_gate_pass",
                    "decision",
                )
            },
            indent=2,
        )
    )
    return 0 if summary["payment_date_gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
