from __future__ import annotations

import importlib.util
from pathlib import Path
from zipfile import ZipFile

import pytest


def load_module():
    script = Path(__file__).parents[1] / "scripts" / "acquire_mps_kaggle_sec_mirrors.py"
    spec = importlib.util.spec_from_file_location("acquire_mps_kaggle_sec_mirrors", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_kaggle_api_urls_need_no_credentials() -> None:
    module = load_module()

    metadata, download = module.api_urls("svendaj/sec-edgar-cik-files-dataset")

    assert metadata == (
        "https://www.kaggle.com/api/v1/datasets/view/svendaj/sec-edgar-cik-files-dataset"
    )
    assert download == (
        "https://www.kaggle.com/api/v1/datasets/download/svendaj/sec-edgar-cik-files-dataset"
    )


def test_extract_allowlist_only_writes_requested_members(tmp_path: Path) -> None:
    module = load_module()
    archive = tmp_path / "sample.zip"
    with ZipFile(archive, "w") as bundle:
        bundle.writestr("wanted.parquet", b"wanted")
        bundle.writestr("ignored.csv", b"ignored")

    records = module.extract_allowlist(
        archive,
        tmp_path / "output",
        {"wanted.parquet": "data/wanted.parquet"},
        max_member_bytes=100,
    )

    assert (tmp_path / "output/data/wanted.parquet").read_bytes() == b"wanted"
    assert not (tmp_path / "output/ignored.csv").exists()
    assert records[0]["bytes"] == 6


def test_extract_allowlist_rejects_missing_member(tmp_path: Path) -> None:
    module = load_module()
    archive = tmp_path / "sample.zip"
    with ZipFile(archive, "w") as bundle:
        bundle.writestr("other.csv", b"other")

    with pytest.raises(ValueError, match="missing required members"):
        module.extract_allowlist(
            archive,
            tmp_path / "output",
            {"wanted.parquet": "data/wanted.parquet"},
            max_member_bytes=100,
        )
