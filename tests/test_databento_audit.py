import io
import struct
import subprocess
from datetime import UTC, datetime

import pytest

from swingmachine.databento_audit import audit_month, read_v1_header, verify_custody
from swingmachine.research_reset import file_hash


def metadata():
    raw = bytearray(100)
    raw[:9] = b"XNAS.ITCH"
    struct.pack_into(
        "<HQQQ",
        raw,
        16,
        6,
        int(datetime(2019, 1, 2, tzinfo=UTC).timestamp()) * 10**9,
        int(datetime(2019, 2, 1, tzinfo=UTC).timestamp()) * 10**9,
        0,
    )
    raw[50:53] = b"\x01\x00\x00"
    raw += struct.pack("<II", 0, 1) + b"AAA".ljust(22, b"\0")
    raw += struct.pack("<III", 0, 0, 1)
    raw += b"AAA".ljust(22, b"\0") + struct.pack("<III", 1, 20190102, 20190201)
    raw += b"42".ljust(22, b"\0")
    return b"DBN\x01" + struct.pack("<I", len(raw)) + raw


def test_v1_symbol_mapping_uses_date_intervals():
    d = read_v1_header(io.BytesIO(metadata()))
    assert d["symbols"] == ["AAA"]
    assert d["mappings"] == [(20190102, 20190201, 42, "AAA")]


@pytest.mark.parametrize(
    "raw", [b"", b"DBN\x03\0\0\0\0", metadata()[:-1], b"DBN\x01\xff\xff\xff\xff"]
)
def test_bad_binary_inputs_rejected(raw):
    with pytest.raises(ValueError):
        read_v1_header(io.BytesIO(raw))


def test_custody_hash_and_protected_file_deferral(tmp_path):
    path = tmp_path / "source.dbn.zst"
    path.write_bytes(b"not market data: custody fixture")
    item = {
        "relative_path": path.name,
        "year_month": "2019-01",
        "size": path.stat().st_size,
        "sha256": file_hash(path),
    }
    protected = {**item, "relative_path": "missing-protected-file", "year_month": "2023-01"}
    result = verify_custody(tmp_path, {"objects": [item, protected]})
    assert result["verified_files"] == 1 and result["deferred_files_not_read"] == 1
    path.write_bytes(b"changed")
    assert verify_custody(tmp_path, {"objects": [item]})["status"] == "CUSTODY_FAIL"


def test_source_path_traversal_and_symlink_rejected(tmp_path):
    item = {"relative_path": "../escape", "year_month": "2019-01", "size": 0, "sha256": "0"}
    with pytest.raises(ValueError, match="escapes"):
        verify_custody(tmp_path, {"objects": [item]})
    (tmp_path / "link").symlink_to(tmp_path.parent)
    item["relative_path"] = "link/escape"
    with pytest.raises(ValueError, match="escapes"):
        verify_custody(tmp_path, {"objects": [item]})


def test_binary_audit_counts_duplicate_bad_price_and_unmapped_record(tmp_path):
    timestamp = int(datetime(2019, 1, 2, 14, 30, tzinfo=UTC).timestamp()) * 10**9

    def record(iid, op=100, low=99):
        return struct.pack(
            "<BBHIQqqqqQ",
            14,
            33,
            2,
            iid,
            timestamp,
            op * 10**9,
            101 * 10**9,
            low * 10**9,
            100 * 10**9,
            1000,
        )

    path = tmp_path / "sample.dbn.zst"
    payload = metadata() + record(42) + record(42, low=102) + record(99)
    path.write_bytes(
        subprocess.run(["zstd", "-c"], input=payload, capture_output=True, check=True).stdout
    )
    result = audit_month(path, file_hash(path))
    assert result["records"] == 3
    assert result["malformed_ohlcv"] == result["duplicate_timestamp_instrument"] == 1
    assert result["unmapped_records"] == 1 and result["structural_errors"]
