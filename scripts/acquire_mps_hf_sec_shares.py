#!/usr/bin/env python3
"""Acquire a pinned, anonymous SEC shares-outstanding mirror from Hugging Face."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

DATASET_REF = "DenyTranDFW/edgar_xbrl_companyfacts"
DATASET_PAGE_URL = f"https://huggingface.co/datasets/{DATASET_REF}"
DATASET_API_URL = f"https://huggingface.co/api/datasets/{DATASET_REF}"
PINNED_COMMIT = "ee7a2614eb8bdaf8c762e1a517183fb4ce8d0c2d"
ARTIFACT_NAME = "EntityCommonStockSharesOutstanding.parquet"
ARTIFACT_BYTES = 86_182_478
ARTIFACT_SHA256 = "6aa8ca1b483e106c95f0671e28b8105efb5deecce4eb73a63142a464c8933754"
ARTIFACT_URL = (
    f"https://huggingface.co/datasets/{DATASET_REF}/resolve/{PINNED_COMMIT}/{ARTIFACT_NAME}"
)


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


def download(url: str, path: Path, *, max_bytes: int) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "SwingMachineResearch/1.0"})
    temporary = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256()
    size = 0
    with urlopen(request, timeout=180) as response, temporary.open("wb") as handle:
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                temporary.unlink(missing_ok=True)
                raise ValueError(f"download exceeds {max_bytes} bytes: {url}")
            digest.update(chunk)
            handle.write(chunk)
        status = response.status
        content_type = response.headers.get("Content-Type")
    temporary.replace(path)
    return {
        "url": url,
        "http_status": status,
        "content_type": content_type,
        "path": str(path),
        "bytes": size,
        "sha256": digest.hexdigest(),
    }


def validate_artifact(path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    digest = file_sha256(path)
    if size != ARTIFACT_BYTES:
        raise ValueError(f"artifact size mismatch: expected {ARTIFACT_BYTES}, got {size}")
    if digest != ARTIFACT_SHA256:
        raise ValueError(f"artifact hash mismatch: expected {ARTIFACT_SHA256}, got {digest}")
    return {
        "url": ARTIFACT_URL,
        "http_status": None,
        "content_type": "application/octet-stream",
        "path": str(path),
        "bytes": size,
        "sha256": digest,
        "reused_existing": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-download-bytes", type=int, default=100_000_000)
    parser.add_argument(
        "--reuse-existing",
        action="store_true",
        help="Hash and reuse the pinned artifact when it is already present.",
    )
    args = parser.parse_args()
    if args.max_download_bytes < ARTIFACT_BYTES:
        raise ValueError(f"max-download-bytes must be at least the pinned {ARTIFACT_BYTES} bytes")
    args.output.mkdir(parents=True, exist_ok=True)

    metadata_path = args.output / "dataset_metadata.json"
    metadata_record = download(DATASET_API_URL, metadata_path, max_bytes=5_000_000)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("sha") != PINNED_COMMIT:
        raise ValueError("dataset head no longer matches the reviewed pinned commit")
    if metadata.get("private") or metadata.get("gated"):
        raise ValueError("dataset is no longer public and ungated")

    artifact_path = args.output / ARTIFACT_NAME
    if args.reuse_existing and artifact_path.is_file():
        artifact_record = validate_artifact(artifact_path)
    else:
        artifact_record = download(
            ARTIFACT_URL,
            artifact_path,
            max_bytes=args.max_download_bytes,
        )
        if (
            artifact_record["bytes"] != ARTIFACT_BYTES
            or artifact_record["sha256"] != ARTIFACT_SHA256
        ):
            artifact_path.unlink(missing_ok=True)
            raise ValueError("downloaded artifact does not match the reviewed pin")

    manifest = {
        "task_id": "SWING-MPS-DATA-001",
        "access": "ANONYMOUS_NO_ACCOUNT_NO_API_KEY",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "dataset_ref": DATASET_REF,
        "dataset_page_url": DATASET_PAGE_URL,
        "pinned_commit": PINNED_COMMIT,
        "license_tag": next(
            (
                str(tag).removeprefix("license:")
                for tag in metadata.get("tags", ())
                if str(tag).startswith("license:")
            ),
            None,
        ),
        "source_origin": "SEC EDGAR XBRL companyfacts mirror",
        "metadata": metadata_record,
        "artifact": artifact_record,
        "qualification_usable": False,
        "decision": "SOURCE_ACQUIRED_RESEARCH_ONLY",
    }
    atomic_write(
        args.output / "acquisition_manifest.json",
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
