#!/usr/bin/env python3
"""Apply a hash-bound reviewed CIK correction to an existing resolution seed."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any


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


def apply_override(
    seed: dict[str, Any],
    override: dict[str, Any],
    *,
    evidence_path: Path,
    override_sha256: str,
) -> dict[str, Any]:
    actual_evidence_hash = file_sha256(evidence_path)
    if actual_evidence_hash != override["evidence_sha256"]:
        raise ValueError("review evidence hash mismatch")
    ticker = str(override["ticker"]).upper()
    matches = [row for row in seed["resolutions"] if str(row["ticker"]).upper() == ticker]
    if len(matches) != 1:
        raise ValueError(f"resolution seed does not contain exactly one {ticker} row")
    row = matches[0]
    expected_seed_cik = int(override["rejected_seed_cik"])
    if int(row["accepted_cik"]) != expected_seed_cik:
        raise ValueError(f"{ticker} seed CIK no longer matches reviewed rejection")

    corrected = json.loads(json.dumps(seed))
    corrected_row = next(
        item for item in corrected["resolutions"] if str(item["ticker"]).upper() == ticker
    )
    corrected_row["accepted_cik"] = int(override["accepted_cik"])
    corrected_row["resolution_status"] = "REVIEWED_SEC_IDENTITY_CORRECTION"
    corrected_row["review"] = {
        **override,
        "evidence_path": str(evidence_path),
    }
    corrected["source_hashes"] = {
        **corrected.get("source_hashes", {}),
        "parent_resolution_seed": override["parent_resolution_seed_sha256"],
        "identity_correction": override_sha256,
    }
    status_counts: dict[str, int] = {}
    for item in corrected["resolutions"]:
        status = str(item["resolution_status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    corrected["status_counts"] = dict(sorted(status_counts.items()))
    corrected["identity_gate_pass"] = all(
        item.get("accepted_cik") is not None for item in corrected["resolutions"]
    )
    corrected["unresolved_symbols"] = sorted(
        str(item["ticker"]) for item in corrected["resolutions"] if item.get("accepted_cik") is None
    )
    return corrected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--override", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    seed_hash = file_sha256(args.seed)
    override = json.loads(args.override.read_text(encoding="utf-8"))
    if seed_hash != override["parent_resolution_seed_sha256"]:
        raise ValueError("parent resolution seed hash mismatch")
    evidence_path = Path(str(override["evidence_path"]))
    if not evidence_path.is_absolute():
        evidence_path = args.override.parent / evidence_path
    corrected = apply_override(
        json.loads(args.seed.read_text(encoding="utf-8")),
        override,
        evidence_path=evidence_path,
        override_sha256=file_sha256(args.override),
    )
    atomic_write(
        args.output,
        (json.dumps(corrected, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(
        json.dumps(
            {
                "identity_gate_pass": corrected["identity_gate_pass"],
                "output": str(args.output),
                "output_sha256": file_sha256(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
