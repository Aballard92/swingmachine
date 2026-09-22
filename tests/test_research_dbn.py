"""Trading212-derived chunk/corruption cases with Swing's stricter boundaries."""

import io
import struct
import subprocess
from datetime import date

import pytest

from swingmachine.databento_audit import read_v1_header
from swingmachine.research_dbn import DBNReadError, iter_dbn_blocks, iter_zstd_chunks
from swingmachine.research_minute_source import stream_sources
from swingmachine.research_reset import file_hash
from tests.test_databento_audit import metadata


def compressed(data):
    return subprocess.run(["zstd", "-c"], input=data, capture_output=True, check=True).stdout


def chunks(data, size):
    return (data[i : i + size] for i in range(0, len(data), size))


def payload():
    # Framer must retain bad OHLC evidence and unsupported types for the caller.
    record = struct.pack(
        "<BBHIQqqqqQ",
        14,
        33,
        2,
        42,
        1546443000000000000,
        100000000000,
        102000000000,
        99000000000,
        101000000000,
        123,
    )
    return metadata(), record


@pytest.mark.parametrize("input_size", [1, 7, 64, 4096])
@pytest.mark.parametrize("output_size", [1, 17, 4096, 1048576])
def test_streaming_chunk_boundaries_and_pending_output(input_size, output_size):
    head, record = payload()
    raw = head + record * 300
    decoded = iter_zstd_chunks(chunks(compressed(raw), input_size), chunk_size=output_size)
    blocks = list(iter_dbn_blocks(decoded))
    assert blocks == [("metadata", head)] + [("record", record)] * 300
    assert read_v1_header(io.BytesIO(blocks[0][1]))["schema"] == "ohlcv-1m"


def test_concatenated_compressed_frames_retain_whole_payload():
    head, record = payload()
    encoded = compressed(head + record[:9]) + compressed(record[9:])
    assert list(iter_dbn_blocks(iter_zstd_chunks(chunks(encoded, 7), 17))) == [
        ("metadata", head),
        ("record", record),
    ]


@pytest.mark.parametrize("change", ["corrupt", "truncate", "empty", "metadata", "record"])
def test_corrupt_or_truncated_streams_raise(change):
    head, record = payload()
    raw = head + record
    encoded = compressed(raw)
    if change == "corrupt":
        encoded = b"not a zstd frame"
    elif change == "truncate":
        encoded = encoded[:-1]
    elif change == "empty":
        encoded = b""
    elif change == "metadata":
        encoded = compressed(head[:-1])
    else:
        encoded = compressed(raw[:-1])
    with pytest.raises(DBNReadError):
        list(iter_dbn_blocks(iter_zstd_chunks(chunks(encoded, 7), 17)))


def test_unknown_record_type_is_preserved_by_framer_and_rejected_by_swing(tmp_path):
    head, record = payload()
    record = bytes([14, 99]) + record[2:]
    assert list(iter_dbn_blocks([head + record]))[-1] == ("record", record)
    path = tmp_path / "unknown.dbn.zst"
    path.write_bytes(compressed(head + record))
    item = {
        "path": path.name,
        "format": "dbn-v1-ohlcv-1m",
        "sha256": file_hash(path),
        "start": "2019-01-02",
        "end": "2019-01-31",
    }
    with pytest.raises(ValueError, match="unsupported DBN record"):
        list(stream_sources(tmp_path, [item], date(2019, 1, 2), date(2019, 1, 31)))


@pytest.mark.parametrize("month,message", [("2023-01", "holdout"), ("2019-02", "disagrees")])
def test_encoded_month_guard_runs_before_any_source_path_resolution(
    tmp_path, monkeypatch, month, message
):
    def forbidden(*args):
        raise AssertionError("path resolution must not be reached")

    monkeypatch.setattr("swingmachine.research_minute_source.bundle_path", forbidden)
    item = {
        "path": "missing",
        "format": "dbn-v1-ohlcv-1m",
        "sha256": "0" * 64,
        "start": "2019-01-02",
        "end": "2019-01-31",
    }
    other = {**item, "path": f"ohlcv-1m/core-101/{month}/data.dbn.zst"}
    with pytest.raises(ValueError, match=message):
        list(stream_sources(tmp_path, [item, other], date(2019, 1, 2), date(2019, 1, 31)))


@pytest.mark.parametrize("size", [0, -1, True, 1.2])
def test_invalid_decode_chunk_size(size):
    with pytest.raises(DBNReadError, match="chunk_size"):
        list(iter_zstd_chunks([], size))
