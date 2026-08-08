from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path

import pyarrow as pa


def load_script(name: str):
    script = Path(__file__).parents[1] / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hugging_face_acquisition_is_commit_and_hash_pinned() -> None:
    module = load_script("acquire_mps_hf_sec_shares.py")

    assert module.PINNED_COMMIT in module.ARTIFACT_URL
    assert module.ARTIFACT_NAME in module.ARTIFACT_URL
    assert module.ARTIFACT_BYTES == 86_182_478
    assert len(module.ARTIFACT_SHA256) == 64


def test_hf_sec_rows_are_cik_filtered_and_date_conservative() -> None:
    module = load_script("build_mps_hf_sec_shares_reference.py")
    table = pa.Table.from_pylist(
        [
            {
                "end": "2025-03-31",
                "accn": "0001234567-25-000001",
                "fy": 2025,
                "fp": "Q1",
                "form": "10-Q",
                "filed": "2025-05-01",
                "unit": "shares",
                "val_dec": Decimal("12345678.000000000"),
                "source_folder": "CIK0001234567_EXAMPLE_INC",
                "label": "Entity Common Stock, Shares Outstanding",
            },
            {
                "end": "2025-03-31",
                "accn": "0009999999-25-000001",
                "fy": 2025,
                "fp": "Q1",
                "form": "10-Q",
                "filed": "2025-05-02",
                "unit": "shares",
                "val_dec": Decimal("999.000000000"),
                "source_folder": "CIK0009999999_OUTSIDE_COHORT",
                "label": "Entity Common Stock, Shares Outstanding",
            },
        ]
    )

    rows, rejected = module.normalized_rows(
        table,
        {
            1234567: {
                "ticker": "EXM",
                "accepted_cik": 1234567,
            }
        },
        source_sha256="a" * 64,
    )

    assert rejected == []
    assert len(rows) == 1
    assert rows[0]["ticker"] == "EXM"
    assert rows[0]["shares_outstanding"] == 12_345_678
    assert rows[0]["available_at"] == "2025-05-01T23:59:59.999999Z"
    assert rows[0]["accession_compact"] == "000123456725000001"


def test_hf_sec_rows_fail_closed_on_non_share_units() -> None:
    module = load_script("build_mps_hf_sec_shares_reference.py")
    table = pa.Table.from_pylist(
        [
            {
                "end": "2025-03-31",
                "accn": "0001234567-25-000001",
                "fy": 2025,
                "fp": "Q1",
                "form": "10-Q",
                "filed": "2025-05-01",
                "unit": "USD",
                "val_dec": Decimal("123.000000000"),
                "source_folder": "CIK0001234567_EXAMPLE_INC",
                "label": "Entity Common Stock, Shares Outstanding",
            }
        ]
    )

    rows, rejected = module.normalized_rows(
        table,
        {1234567: {"ticker": "EXM", "accepted_cik": 1234567}},
        source_sha256="a" * 64,
    )

    assert rows == []
    assert rejected[0]["reason"] == "UNEXPECTED_UNIT"
