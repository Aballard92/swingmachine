#!/usr/bin/env python3
"""Acquire the two anonymous Kaggle SEC mirrors used by the MPS research lane."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from zipfile import ZipFile

SOURCES = (
    {
        "key": "cik",
        "ref": "svendaj/sec-edgar-cik-files-dataset",
        "page_url": "https://www.kaggle.com/datasets/svendaj/sec-edgar-cik-files-dataset",
        "archive_name": "sec_edgar_cik_files.zip",
        "members": {
            "CIK_company_lookup.parquet": "sec_cik/CIK_company_lookup.parquet",
            "CIK_company_ticker_exchange.parquet": ("sec_cik/CIK_company_ticker_exchange.parquet"),
        },
    },
    {
        "key": "facts",
        "ref": "vadimvanak/company-facts-2",
        "page_url": "https://www.kaggle.com/datasets/vadimvanak/company-facts-2",
        "archive_name": "sec_financial_facts.zip",
        "members": {
            "facts.parquet": "sec_facts/facts.parquet",
            "submissions.csv": "sec_facts/submissions.csv",
        },
    },
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


def api_urls(ref: str) -> tuple[str, str]:
    return (
        f"https://www.kaggle.com/api/v1/datasets/view/{ref}",
        f"https://www.kaggle.com/api/v1/datasets/download/{ref}",
    )


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


def extract_allowlist(
    archive: Path,
    output: Path,
    members: dict[str, str],
    *,
    max_member_bytes: int,
) -> list[dict[str, Any]]:
    extracted = []
    with ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        missing = sorted(set(members) - names)
        if missing:
            raise ValueError(f"archive is missing required members: {missing}")
        for member, relative_target in members.items():
            info = bundle.getinfo(member)
            if info.flag_bits & 0x1:
                raise ValueError(f"encrypted ZIP member rejected: {member}")
            if info.file_size > max_member_bytes:
                raise ValueError(f"ZIP member exceeds {max_member_bytes} bytes: {member}")
            target = output / relative_target
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix(target.suffix + ".tmp")
            with bundle.open(info) as source, temporary.open("wb") as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
            temporary.replace(target)
            extracted.append(
                {
                    "member": member,
                    "path": str(target),
                    "bytes": target.stat().st_size,
                    "sha256": file_sha256(target),
                }
            )
    return extracted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-download-bytes", type=int, default=500_000_000)
    parser.add_argument("--max-member-bytes", type=int, default=400_000_000)
    parser.add_argument(
        "--reuse-existing-archives",
        action="store_true",
        help="Use already present archive names after hashing instead of downloading again.",
    )
    args = parser.parse_args()
    if args.max_download_bytes <= 0 or args.max_member_bytes <= 0:
        raise ValueError("byte limits must be positive")
    args.output.mkdir(parents=True, exist_ok=True)

    records = []
    for source in SOURCES:
        metadata_url, download_url = api_urls(str(source["ref"]))
        metadata_path = args.output / "metadata" / f"{source['key']}.json"
        metadata_record = download(
            metadata_url,
            metadata_path,
            max_bytes=5_000_000,
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        archive_path = args.output / "archives" / str(source["archive_name"])
        if args.reuse_existing_archives and archive_path.is_file():
            archive_record = {
                "url": download_url,
                "http_status": None,
                "content_type": None,
                "path": str(archive_path),
                "bytes": archive_path.stat().st_size,
                "sha256": file_sha256(archive_path),
                "reused_existing": True,
            }
        else:
            archive_record = download(
                download_url,
                archive_path,
                max_bytes=args.max_download_bytes,
            )
        extracted = extract_allowlist(
            archive_path,
            args.output,
            dict(source["members"]),
            max_member_bytes=args.max_member_bytes,
        )
        records.append(
            {
                "dataset_ref": source["ref"],
                "dataset_page_url": source["page_url"],
                "retrieved_at": datetime.now(UTC).isoformat(),
                "license": metadata.get("licenseName"),
                "last_updated": metadata.get("lastUpdated"),
                "metadata": metadata_record,
                "archive": archive_record,
                "extracted": extracted,
            }
        )

    manifest = {
        "task_id": "SWING-MPS-DATA-001",
        "access": "ANONYMOUS_NO_ACCOUNT_NO_API_KEY",
        "sources": records,
    }
    atomic_write(
        args.output / "acquisition_manifest.json",
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
