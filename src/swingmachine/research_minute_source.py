"""Read-only, hash-bound minute streams for the daily adapter.

The DBN implementation remains deliberately narrow. Official decoder parity is
a separate requirement before historical price conclusions, not implied by this
module decoding its own fixtures correctly.
"""

from __future__ import annotations

import hashlib
import heapq
import io
import json
import re
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from swingmachine.databento_audit import RECORD, read_v1_header
from swingmachine.research_daily import NY, Minute
from swingmachine.research_dbn import iter_dbn_blocks, iter_zstd_chunks
from swingmachine.research_reset import guard_research_dates
from swingmachine.research_source import _unique_object


def bundle_path(root: Path, relative: str) -> Path:
    rel = Path(relative)
    path = (root / rel).resolve()
    if rel.is_absolute() or ".." in rel.parts or not path.is_relative_to(root.resolve()):
        raise ValueError("source path escapes its declared root")
    return path


def _digest(stream, expected: str) -> None:
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("expected source SHA-256 is required")
    if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
        raise ValueError("minute source hash mismatch")
    stream.seek(0)


def stream_jsonl(path: Path, item: dict) -> Iterator[Minute]:
    """Hash and read one open file, so pathname replacement cannot swap inputs."""
    left, right = date.fromisoformat(item["start"]), date.fromisoformat(item["end"])
    guard_research_dates(left, right)
    with path.open("rb") as stream:
        _digest(stream, item["sha256"])
        previous = None
        for index, line in enumerate(stream):
            row = json.loads(line, object_pairs_hook=_unique_object)
            if not isinstance(row, dict):
                raise ValueError("minute JSONL rows must be objects")
            minute = Minute(
                **{
                    **row,
                    "timestamp": datetime.fromisoformat(row["timestamp"]),
                    "source_id": item["sha256"],
                    "record_index": index,
                }
            )
            if not left <= minute.timestamp.astimezone(NY).date() <= right:
                raise ValueError("minute outside its declared source dates")
            if previous is not None and minute.timestamp < previous:
                raise ValueError("unordered JSONL minute source")
            previous = minute.timestamp
            yield minute
        stream.seek(0)
        _digest(stream, item["sha256"])


def stream_dbn_v1(path: Path, item: dict) -> Iterator[Minute]:
    left, right = date.fromisoformat(item["start"]), date.fromisoformat(item["end"])
    guard_research_dates(left, right)
    guard_encoded_month(str(path), item)
    with path.open("rb") as raw:
        _digest(raw, item["sha256"])
        decoded = iter_zstd_chunks(iter(lambda: raw.read(1024 * 1024), b""))
        blocks = iter_dbn_blocks(decoded)
        try:
            kind, metadata = next(blocks)
            if kind != "metadata":
                raise ValueError("DBN metadata must precede records")
            header = read_v1_header(io.BytesIO(metadata))
            first = datetime.fromtimestamp(header["start_ns"] // 10**9, UTC).date()
            last = datetime.fromtimestamp((header["end_ns"] - 1) // 10**9, UTC).date()
            guard_research_dates(first, last)
            if first < left or last > right:
                raise ValueError("DBN metadata exceeds declared source dates")
            if header["partial"] or header["not_found"]:
                raise ValueError("DBN metadata declares partial or unfound symbols")
            maps = {}
            previous = -1
            index = 0
            for _kind, record in blocks:
                if len(record) != RECORD.size:
                    raise ValueError("truncated DBN minute record")
                length, rtype, publisher, iid, ts, op, hi, lo, cl, volume = RECORD.unpack(record)
                if (length, rtype, publisher) != (14, 33, 2):
                    raise ValueError("unsupported DBN record layout")
                if (
                    not header["start_ns"] <= ts < header["end_ns"]
                    or ts < previous
                    or ts % (60 * 10**9)
                ):
                    raise ValueError("invalid or unordered DBN minute timestamp")
                previous = ts
                instant = datetime.fromtimestamp(ts // 10**9, UTC)
                key = instant.year * 10000 + instant.month * 100 + instant.day
                if key not in maps:
                    mapping = {}
                    for a, b, instrument, name in header["mappings"]:
                        if a <= key < b:
                            if instrument in mapping and mapping[instrument] != name:
                                raise ValueError("ambiguous DBN identity mapping")
                            mapping[instrument] = name
                    maps[key] = mapping
                name = maps[key].get(iid)
                if name is None:
                    raise ValueError("unmapped DBN instrument")
                if max(op, hi, lo, cl) >= 2**63 - 1:
                    raise ValueError("DBN undefined price sentinel")
                yield Minute(
                    instant,
                    iid,
                    name,
                    op / 1e9,
                    hi / 1e9,
                    lo / 1e9,
                    cl / 1e9,
                    volume,
                    item["sha256"],
                    index,
                )
                index += 1
            raw.seek(0)
            _digest(raw, item["sha256"])
        finally:
            blocks.close()
            decoded.close()


def guard_encoded_month(relative: str, item: dict) -> None:
    """Trading212 source-freeze rule: reject protected months before path I/O.

    No claim that a dishonest filename can prove contents safe. Declared dates,
    trusted custody hashes and strict DBN metadata checks remain required.
    """
    if item["format"] != "dbn-v1-ohlcv-1m":
        return
    left, right = date.fromisoformat(item["start"]), date.fromisoformat(item["end"])
    for part in Path(relative).parts:
        if re.fullmatch(r"\d{4}-\d{2}", part):
            first = date.fromisoformat(part + "-01")
            following = date(first.year + (first.month == 12), first.month % 12 + 1, 1)
            last = following - timedelta(days=1)
            guard_research_dates(first, last)
            if not first <= left <= right <= last:
                raise ValueError("encoded source month disagrees with declared dates")


def stream_sources(root: Path, items: list[dict], start: date, end: date) -> Iterator[Minute]:
    """Validate all source boundaries before opening any source, then merge shards."""
    guard_research_dates(start, end)
    if not items or len({i["path"] for i in items}) != len(items):
        raise ValueError("nonempty unique minute source paths required")
    paths = []
    for item in items:
        guard_research_dates(date.fromisoformat(item["start"]), date.fromisoformat(item["end"]))
        if item["format"] not in ("jsonl", "dbn-v1-ohlcv-1m"):
            raise ValueError("unsupported minute source format")
        guard_encoded_month(item["path"], item)
    # Validate every lexical boundary before resolving any source path.
    for item in items:
        paths.append(bundle_path(root, item["path"]))
    streams = []
    try:
        for path, item in zip(paths, items, strict=True):
            reader = stream_jsonl if item["format"] == "jsonl" else stream_dbn_v1
            streams.append(reader(path, item))
        for minute in heapq.merge(*streams, key=lambda m: m.timestamp):
            if start <= minute.timestamp.astimezone(NY).date() <= end:
                yield minute
    finally:
        for stream in streams:
            stream.close()
