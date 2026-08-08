#!/usr/bin/env python3
"""Normalize a bounded Tiingo EOD acquisition without overstating qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
from functools import cache
from pathlib import Path
from typing import Any

import exchange_calendars as xcals
import pyarrow as pa
import pyarrow.parquet as pq

REQUIRED_FIELDS = {
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "adjOpen",
    "adjHigh",
    "adjLow",
    "adjClose",
    "adjVolume",
    "divCash",
    "splitFactor",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


COMMON_FIELDS = [
    pa.field("security_id", pa.string()),
    pa.field("ticker", pa.string()),
    pa.field("trading_date", pa.string()),
    pa.field("event_time", pa.string()),
    pa.field("available_at", pa.string()),
]
SOURCE_HASH_FIELD = pa.field("source_file_sha256", pa.string())
TRADABLE_SCHEMA = pa.schema(
    COMMON_FIELDS
    + [
        pa.field("open", pa.float64()),
        pa.field("high", pa.float64()),
        pa.field("low", pa.float64()),
        pa.field("close", pa.float64()),
        pa.field("volume", pa.float64()),
        pa.field("div_cash", pa.float64()),
        pa.field("split_factor", pa.float64()),
        SOURCE_HASH_FIELD,
    ]
)
ADJUSTED_SCHEMA = pa.schema(
    COMMON_FIELDS
    + [
        pa.field("provider_adjusted_open", pa.float64()),
        pa.field("provider_adjusted_high", pa.float64()),
        pa.field("provider_adjusted_low", pa.float64()),
        pa.field("provider_adjusted_close", pa.float64()),
        pa.field("provider_adjusted_volume", pa.float64()),
        SOURCE_HASH_FIELD,
    ]
)
ACTION_SCHEMA = pa.schema(
    COMMON_FIELDS
    + [
        pa.field("div_cash", pa.float64()),
        pa.field("split_factor", pa.float64()),
        pa.field("payment_date", pa.string()),
        SOURCE_HASH_FIELD,
    ]
)

EXCHANGE_CALENDAR_NAMES = {
    "NASDAQ": "XNAS",
    "NYSE": "XNYS",
    "NYSE MKT": "XNYS",
}


@cache
def official_close(exchange: str, trading_date: str) -> str:
    calendar_name = EXCHANGE_CALENDAR_NAMES.get(exchange)
    if calendar_name is None:
        raise ValueError(f"unsupported exchange calendar: {exchange}")
    calendar = xcals.get_calendar(calendar_name)
    return calendar.session_close(trading_date).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    queue_doc = json.loads(args.queue.read_text(encoding="utf-8"))
    queue = {row["ticker"]: row for row in queue_doc["selected"]}
    args.output_dir.mkdir(parents=True, exist_ok=True)

    sources: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []
    tradable_row_count = 0
    adjusted_row_count = 0
    action_row_count = 0

    output_specs = {
        "tradable_prices.parquet": TRADABLE_SCHEMA,
        "provider_adjusted_prices.parquet": ADJUSTED_SCHEMA,
        "corporate_action_events.parquet": ACTION_SCHEMA,
    }
    temporary_paths = {name: args.output_dir / f".{name}.tmp" for name in output_specs}
    for path in temporary_paths.values():
        path.unlink(missing_ok=True)
    writers = {
        name: pq.ParquetWriter(temporary_paths[name], schema, compression="zstd")
        for name, schema in output_specs.items()
    }

    try:
        for path in sorted(args.raw_dir.glob("*.json")):
            ticker = path.stem.upper()
            identity = queue.get(ticker)
            if identity is None:
                warnings.append({"ticker": ticker, "reason": "NOT_IN_PREREGISTERED_QUEUE"})
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, list) or not payload:
                warnings.append({"ticker": ticker, "reason": "EMPTY_OR_INVALID_PAYLOAD"})
                continue
            missing = REQUIRED_FIELDS.difference(payload[0])
            if missing:
                warnings.append(
                    {"ticker": ticker, "reason": f"MISSING_FIELDS:{','.join(sorted(missing))}"}
                )
                continue

            source_hash = sha256(path)
            seen_dates: set[str] = set()
            valid = True
            symbol_tradable: list[dict[str, Any]] = []
            symbol_adjusted: list[dict[str, Any]] = []
            symbol_actions: list[dict[str, Any]] = []
            for row in payload:
                trading_date = str(row["date"])[:10]
                if trading_date in seen_dates:
                    warnings.append({"ticker": ticker, "reason": f"DUPLICATE_DATE:{trading_date}"})
                    valid = False
                    break
                seen_dates.add(trading_date)
                if (
                    not identity["request_start_date"]
                    <= trading_date
                    <= identity["request_end_date"]
                ):
                    warnings.append(
                        {"ticker": ticker, "reason": f"OUT_OF_BOUNDS_DATE:{trading_date}"}
                    )
                    valid = False
                    break
                try:
                    available_at = official_close(identity["exchange"], trading_date)
                except (KeyError, ValueError) as exc:
                    warnings.append(
                        {
                            "ticker": ticker,
                            "reason": f"OFFICIAL_CLOSE_UNAVAILABLE:{trading_date}:{exc}",
                        }
                    )
                    valid = False
                    break
                base = {
                    "security_id": identity["security_id"],
                    "ticker": ticker,
                    "trading_date": trading_date,
                    "event_time": row["date"],
                    "available_at": available_at,
                    "source_file_sha256": source_hash,
                }
                symbol_tradable.append(
                    base
                    | {
                        "open": row["open"],
                        "high": row["high"],
                        "low": row["low"],
                        "close": row["close"],
                        "volume": row["volume"],
                        "div_cash": row["divCash"],
                        "split_factor": row["splitFactor"],
                    }
                )
                symbol_adjusted.append(
                    base
                    | {
                        "provider_adjusted_open": row["adjOpen"],
                        "provider_adjusted_high": row["adjHigh"],
                        "provider_adjusted_low": row["adjLow"],
                        "provider_adjusted_close": row["adjClose"],
                        "provider_adjusted_volume": row["adjVolume"],
                    }
                )
                if float(row["divCash"] or 0) != 0 or float(row["splitFactor"] or 1) != 1:
                    symbol_actions.append(
                        base
                        | {
                            "div_cash": row["divCash"],
                            "split_factor": row["splitFactor"],
                            "payment_date": None,
                        }
                    )
            if not valid:
                continue
            writers["tradable_prices.parquet"].write_table(
                pa.Table.from_pylist(symbol_tradable, schema=TRADABLE_SCHEMA)
            )
            writers["provider_adjusted_prices.parquet"].write_table(
                pa.Table.from_pylist(symbol_adjusted, schema=ADJUSTED_SCHEMA)
            )
            if symbol_actions:
                writers["corporate_action_events.parquet"].write_table(
                    pa.Table.from_pylist(symbol_actions, schema=ACTION_SCHEMA)
                )
            tradable_row_count += len(symbol_tradable)
            adjusted_row_count += len(symbol_adjusted)
            action_row_count += len(symbol_actions)
            sources.append(
                {
                    "ticker": ticker,
                    "security_id": identity["security_id"],
                    "raw_file": str(path),
                    "raw_sha256": source_hash,
                    "rows": len(payload),
                    "first_date": min(seen_dates),
                    "last_date": max(seen_dates),
                }
            )
    finally:
        for writer in writers.values():
            writer.close()

    for name, temporary_path in temporary_paths.items():
        temporary_path.replace(args.output_dir / name)

    output_files = [
        args.output_dir / "tradable_prices.parquet",
        args.output_dir / "provider_adjusted_prices.parquet",
        args.output_dir / "corporate_action_events.parquet",
    ]
    manifest = {
        "task_id": "SWING-MPS-DATA-001",
        "source": "Tiingo EOD bounded acquisition",
        "queue_sha256": sha256(args.queue),
        "source_files": sources,
        "source_symbol_count": len(sources),
        "tradable_row_count": tradable_row_count,
        "adjusted_row_count": adjusted_row_count,
        "corporate_action_event_count": action_row_count,
        "warnings": warnings,
        "output_sha256": {path.name: sha256(path) for path in output_files},
        "qualification_usable": False,
        "blocking_fields": [
            "common-stock and ADR classification remains provisional",
            "dividend payment dates are absent",
            "delisting proceeds and merger consideration are absent",
        ],
        "available_at_semantics": {
            "definition": "official exchange session close",
            "exchange_calendar_mapping": EXCHANGE_CALENDAR_NAMES,
        },
        "adjusted_field_semantics": (
            "Provider-adjusted fields retained separately; downstream total-return "
            "contract validation required."
        ),
    }
    (args.output_dir / "panel_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: manifest[k]
                for k in (
                    "source_symbol_count",
                    "tradable_row_count",
                    "corporate_action_event_count",
                    "qualification_usable",
                    "blocking_fields",
                )
            },
            indent=2,
        )
    )
    return 0 if not warnings else 2


if __name__ == "__main__":
    raise SystemExit(main())
