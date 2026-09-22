"""Read-only custody and narrow DBN-v1 OHLCV audit, without the provider SDK.

Only offline zstd decompression is invoked. This is not a general DBN adapter.
Layout reference: databento/dbn rust/dbn/src/decode/dbn/fsm.rs and record.rs.
No instrument prices are promoted to adjusted or qualified daily data here.
"""

from __future__ import annotations

import json
import struct
import subprocess
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import BinaryIO
from zoneinfo import ZoneInfo

from swingmachine.research_reset import file_hash, guard_research_dates

RECORD = struct.Struct("<BBHIQqqqqQ")
NEW_YORK = ZoneInfo("America/New_York")


def _exact(stream: BinaryIO, count: int) -> bytes:
    value = stream.read(count)
    if len(value) != count:
        raise ValueError("truncated DBN stream")
    return value


def read_v1_header(stream: BinaryIO) -> dict:
    header = _exact(stream, 8)
    if header[:4] != b"DBN\x01":
        raise ValueError("audit supports DBN v1 only")
    length = struct.unpack("<I", header[4:])[0]
    if not 100 <= length <= 16_000_000:
        raise ValueError("invalid metadata length")
    raw = _exact(stream, length)
    dataset = raw[:16].rstrip(b"\0").decode("ascii")
    schema = struct.unpack_from("<H", raw, 16)[0]
    start, end, limit = struct.unpack_from("<QQQ", raw, 18)
    if dataset != "XNAS.ITCH" or schema != 6 or raw[50:53] != b"\x01\x00\x00":
        raise ValueError("requires XNAS.ITCH ohlcv-1m, raw-symbol to instrument-id, no ts_out")
    if limit != 0:
        raise ValueError("record-limited data is not admissible")
    # DBN-v1 metadata: 53-byte fields + 47 reserved bytes, then schema definition.
    if len(raw) < 104 or struct.unpack_from("<I", raw, 100)[0] != 0:
        raise ValueError("unsupported schema definition")
    pos = 104

    def take(n: int) -> bytes:
        nonlocal pos
        if pos + n > len(raw):
            raise ValueError("truncated DBN metadata")
        value = raw[pos : pos + n]
        pos += n
        return value

    def number() -> int:
        return struct.unpack("<I", take(4))[0]

    def symbol() -> str:
        return take(22).split(b"\0", 1)[0].decode("ascii")

    lists = []
    for _ in range(3):
        count = number()
        if count > (len(raw) - pos) // 22:
            raise ValueError("invalid symbol count")
        lists.append([symbol() for _ in range(count)])
    mappings = []
    count = number()
    if count > (len(raw) - pos) // 26:
        raise ValueError("invalid mapping count")
    for _ in range(count):
        name, intervals = symbol(), number()
        if intervals > (len(raw) - pos) // 30:
            raise ValueError("invalid interval count")
        for _ in range(intervals):
            left, right, instrument = number(), number(), symbol()
            if left >= right or not instrument.isdigit():
                raise ValueError("invalid mapping interval")
            mappings.append((left, right, int(instrument), name))
    if pos != len(raw):
        raise ValueError("unexpected trailing metadata")
    return {
        "dataset": dataset,
        "schema": "ohlcv-1m",
        "start_ns": start,
        "end_ns": end,
        "symbols": lists[0],
        "partial": lists[1],
        "not_found": lists[2],
        "mappings": mappings,
    }


def verify_custody(root: Path, inventory: dict, end_month: str = "2020-11") -> dict:
    """Rebase only declared relative paths; do not read protected files' contents."""
    root = root.resolve(strict=True)
    checked, errors, deferred = [], [], 0
    objects = inventory["objects"]
    if len({x["relative_path"] for x in objects}) != len(objects):
        raise ValueError("duplicate inventory paths")
    for obj in objects:
        relative = Path(obj["relative_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("inventory path escapes source root")
        year_month = obj["year_month"]
        month_start = date.fromisoformat(year_month + "-01")
        next_month = date(
            month_start.year + (month_start.month == 12), month_start.month % 12 + 1, 1
        )
        if year_month > end_month:
            deferred += 1
            continue
        guard_research_dates(month_start, next_month)
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("inventory symlink escapes source root")
        valid = path.is_file() and path.stat().st_size == obj["size"]
        if valid:
            valid = file_hash(path) == obj["sha256"]
        item = {
            "relative_path": str(relative),
            "sha256": obj["sha256"],
            "size": obj["size"],
            "verified": valid,
        }
        (checked if valid else errors).append(item)
    return {
        "status": "CUSTODY_PASS" if checked and not errors else "CUSTODY_FAIL",
        "verified_files": len(checked),
        "verified_bytes": sum(x["size"] for x in checked),
        "deferred_files_not_read": deferred,
        "errors": errors,
        "files": checked,
    }


def audit_month(path: Path, expected_sha256: str) -> dict:
    """Structural/profile evidence only; 09:30–16:00 clock, NOT official sessions.

    This deliberately does not certify holidays, early closes, corporate actions,
    population eligibility, primary exchange openings or consolidated volume.
    """
    process = subprocess.Popen(
        ["zstd", "-dc", str(path)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    assert process.stdout is not None
    try:
        header = read_v1_header(process.stdout)
        first_date = datetime.fromtimestamp(header["start_ns"] / 1e9, UTC).date()
        # End is exclusive; subtract a nanosecond using integer division first.
        last_date = datetime.fromtimestamp((header["end_ns"] - 1) // 10**9, UTC).date()
        guard_research_dates(first_date, last_date)
        if file_hash(path) != expected_sha256:
            raise ValueError("source hash mismatch")
        count, malformed, duplicates, unmapped, out_of_order = 0, 0, 0, 0, 0
        clock_counts: Counter = Counter()
        symbols: set[str] = set()
        mapping_by_date: dict[int, dict[int, str]] = {}
        previous_timestamp = -1
        same_timestamp: set[int] = set()
        while True:
            block = process.stdout.read(RECORD.size * 8192)
            if not block:
                break
            if len(block) % RECORD.size:
                raise ValueError("truncated or variable-length OHLCV record")
            for (
                length,
                rtype,
                publisher,
                instrument,
                ts,
                op,
                hi,
                lo,
                cl,
                _vol,
            ) in RECORD.iter_unpack(block):
                if (length, rtype, publisher) != (14, 33, 2):
                    raise ValueError("unsupported OHLCV record header")
                if not header["start_ns"] <= ts < header["end_ns"]:
                    raise ValueError("record outside metadata dates")
                count += 1
                malformed += int(not (0 < lo <= min(op, cl) <= max(op, cl) <= hi < 2**63 - 1))
                out_of_order += int(ts < previous_timestamp)
                if ts != previous_timestamp:
                    same_timestamp.clear()
                duplicates += int(instrument in same_timestamp)
                same_timestamp.add(instrument)
                previous_timestamp = ts
                instant = datetime.fromtimestamp(ts // 10**9, UTC)
                ymd = instant.year * 10000 + instant.month * 100 + instant.day
                if ymd not in mapping_by_date:
                    mapping = {}
                    for left, right, iid, symbol in header["mappings"]:
                        if left <= ymd < right:
                            if iid in mapping and mapping[iid] != symbol:
                                raise ValueError("ambiguous point-in-time instrument mapping")
                            mapping[iid] = symbol
                    mapping_by_date[ymd] = mapping
                name = mapping_by_date[ymd].get(instrument)
                if name is None:
                    unmapped += 1
                else:
                    symbols.add(name)
                local = instant.astimezone(NEW_YORK)
                minute = local.hour * 60 + local.minute
                if local.weekday() < 5 and 570 <= minute < 960:
                    clock_counts[local.date().isoformat()] += 1
        if process.wait() != 0:
            raise ValueError("zstd decompression failed")
        return {
            "source_sha256": expected_sha256,
            "records": count,
            "malformed_ohlcv": malformed,
            "malformed_rate": malformed / count if count else None,
            "duplicate_timestamp_instrument": duplicates,
            "unmapped_records": unmapped,
            "out_of_order": out_of_order,
            "observed_symbols": len(symbols),
            "dates_with_regular_clock_bars": len(clock_counts),
            "regular_clock_records": sum(clock_counts.values()),
            "daily_regular_clock_counts": dict(sorted(clock_counts.items())),
            "status": "STRUCTURAL_SAMPLE_ONLY_NOT_STRATEGY_READY",
            "structural_errors": bool(malformed or duplicates or unmapped or out_of_order),
        }
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            process.wait()


def load_inventory(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or not isinstance(value.get("objects"), list):
        raise ValueError("source inventory must have an objects array")
    return value


def inventory_from_provider(root: Path, provider_inventory: Path) -> dict:
    """Match copied DBN objects to their recorded provider hashes, by filename only."""
    expected = {}
    data = json.loads(provider_inventory.read_text())
    for job in data["jobs"]:
        for item in job["files"]:
            if item["filename"].endswith(".dbn.zst"):
                prefix = item["sha256"][:12]
                if prefix in expected:
                    raise ValueError("ambiguous provider hash prefix")
                expected[prefix] = item
    observed = {}
    for path in root.rglob("*.dbn.zst"):
        prefix = path.name.rsplit("__sha256-", 1)[-1].split(".", 1)[0]
        if prefix not in expected or prefix in observed:
            raise ValueError("unexpected or duplicate raw object")
        observed[prefix] = path
    if observed.keys() != expected.keys():
        raise ValueError("copied raw inventory does not match provider file census")
    return {
        "provider_inventory_sha256": file_hash(provider_inventory),
        "objects": [
            {
                "relative_path": str(path.relative_to(root)),
                "year_month": path.parent.name,
                "size": expected[key]["size"],
                "sha256": expected[key]["sha256"],
            }
            for key, path in sorted(observed.items(), key=lambda x: str(x[1]))
        ],
    }
