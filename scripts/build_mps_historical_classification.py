#!/usr/bin/env python3
"""Resolve historical MPS security types from preserved account-free evidence."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

COMMON_CONCEPTS = {
    "EntityCommonStockSharesOutstanding",
    "CommonStockSharesOutstanding",
}
COMMON_STATUS = "PROVEN_HISTORICAL_COMMON_STOCK"
NON_COMMON_STATUS = "PROVEN_HISTORICAL_NON_COMMON"
UNRESOLVED_STATUS = "UNRESOLVED_HISTORICAL_CLASSIFICATION"
EXACT_LIFECYCLE_REASON = "DELISTED_MISSING_PRICE_EXACT_TICKER_AND_END_DATE"
TOKEN_REPLACEMENTS = {
    "GRP": "GROUP",
    "HDS": "HOLDINGS",
    "TECHNO": "TECHNOLOGY",
}
IGNORED_NAME_TOKENS = {
    "A",
    "CLASS",
    "CO",
    "CORP",
    "CORPORATION",
    "INC",
    "LTD",
    "THE",
}


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


def atomic_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(pa.Table.from_pylist(rows), temporary, compression="zstd")
    temporary.replace(path)


def normalized_name_tokens(value: str) -> frozenset[str]:
    raw_tokens = re.findall(r"[A-Z0-9]+", value.upper())
    tokens = [TOKEN_REPLACEMENTS.get(token, token) for token in raw_tokens]
    return frozenset(token for token in tokens if token not in IGNORED_NAME_TOKENS)


def name_similarity(expected: str, candidate: str) -> float:
    expected_tokens = normalized_name_tokens(expected)
    candidate_tokens = normalized_name_tokens(candidate)
    if not expected_tokens or not candidate_tokens:
        return 0.0
    return len(expected_tokens & candidate_tokens) / len(expected_tokens | candidate_tokens)


def matching_candidates(
    expected_name: str,
    candidates: list[dict[str, Any]],
    *,
    threshold: float = 0.8,
) -> list[tuple[dict[str, Any], float]]:
    scored = [
        (candidate, name_similarity(expected_name, str(candidate.get("name", ""))))
        for candidate in candidates
    ]
    matches = [item for item in scored if item[1] >= threshold]
    return sorted(
        matches,
        key=lambda item: (
            item[1],
            str(item[0].get("name", "")),
            str(item[0].get("figi", "")),
        ),
        reverse=True,
    )


def _resolution_seed_rows(path: Path) -> dict[str, dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document if isinstance(document, list) else document["resolutions"]
    return {str(row["ticker"]).upper(): row for row in rows}


def _common_share_concepts(shares_path: Path) -> dict[str, set[str]]:
    table = pq.read_table(shares_path, columns=["ticker", "concept"])
    concepts: dict[str, set[str]] = {}
    for row in table.to_pylist():
        concepts.setdefault(str(row["ticker"]).upper(), set()).add(str(row["concept"]))
    return concepts


def _openfigi_document(
    ticker: str,
    *,
    raw_dir: Path,
    expected_sha256: str,
) -> tuple[dict[str, Any], str]:
    path = raw_dir / f"{ticker}.json"
    observed_sha256 = file_sha256(path)
    if observed_sha256 != expected_sha256:
        raise ValueError(
            f"OpenFIGI raw SHA256 mismatch for {ticker}: {observed_sha256} != {expected_sha256}"
        )
    return json.loads(path.read_text(encoding="utf-8")), observed_sha256


def resolve_historical_classifications(
    queue_document: dict[str, Any],
    tiingo_manifest: dict[str, Any],
    original_rows: list[dict[str, Any]],
    *,
    raw_dir: Path,
    resolution_seed: dict[str, dict[str, Any]],
    share_concepts: dict[str, set[str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    queue = {str(row["ticker"]).upper(): row for row in queue_document["selected"]}
    sources = {str(row["ticker"]).upper(): row for row in tiingo_manifest["source_files"]}
    original = {str(row["ticker"]).upper(): row for row in original_rows}
    cohort = set(sources)
    if set(original) != cohort:
        raise ValueError("OpenFIGI and Tiingo cohorts do not match")
    if not cohort.issubset(queue):
        raise ValueError("Tiingo source cohort is not contained in queue")

    rows: list[dict[str, Any]] = []
    for ticker in sorted(cohort):
        queue_row = queue[ticker]
        source_row = sources[ticker]
        original_row = original[ticker]
        seed_row = resolution_seed.get(ticker)
        concepts = sorted(share_concepts.get(ticker, set()))
        original_status = str(original_row["classification_status"])
        status = UNRESOLVED_STATUS
        method = "NO_ACCEPTED_RESOLUTION"
        matched_candidate: dict[str, Any] | None = None
        match_score: float | None = None
        raw_sha256: str | None = None

        if str(queue_row["security_id"]) != str(source_row["security_id"]):
            raise ValueError(f"queue/source security_id mismatch for {ticker}")
        if original_status == "PROVEN_UNIQUE_COMMON_STOCK":
            status = COMMON_STATUS
            method = "OPENFIGI_UNIQUE_COMMON_STOCK"
        else:
            document, raw_sha256 = _openfigi_document(
                ticker,
                raw_dir=raw_dir,
                expected_sha256=str(original_row["source_sha256"]),
            )
            candidates = list(document["response"].get("data", []))
            matches = matching_candidates(str(queue_row["name"]), candidates)
            if len(matches) == 1:
                matched_candidate, match_score = matches[0]
                if matched_candidate.get("securityType2") == "Common Stock":
                    status = COMMON_STATUS
                    method = "OPENFIGI_HISTORICAL_NAME_DISAMBIGUATION"
                else:
                    status = NON_COMMON_STATUS
                    method = "OPENFIGI_EXACT_HISTORICAL_NON_COMMON"
            elif len(matches) == 0:
                accepted_cik = None if seed_row is None else seed_row.get("accepted_cik")
                sec_resolution_status = (
                    None if seed_row is None else seed_row.get("resolution_status")
                )
                has_common_shares = bool(COMMON_CONCEPTS & set(concepts))
                exact_lifecycle = queue_row.get(
                    "selection_reason"
                ) == EXACT_LIFECYCLE_REASON and queue_row.get("tiingo_end_date") == queue_row.get(
                    "alpha_delisting_date"
                ) == source_row.get("last_date")
                if original_status == "PROVEN_NON_COMMON" and candidates:
                    method = "OPENFIGI_TICKER_REUSE_NON_COMMON_CONFLICT"
                elif (
                    accepted_cik is not None
                    and has_common_shares
                    and sec_resolution_status == "UNIQUE_HISTORICAL_FILING_TICKER"
                ):
                    status = COMMON_STATUS
                    method = "SEC_UNIQUE_HISTORICAL_TICKER_PLUS_COMMON_SHARES"
                elif accepted_cik is not None and has_common_shares and exact_lifecycle:
                    status = COMMON_STATUS
                    method = "EXACT_TIINGO_LIFECYCLE_PLUS_SEC_COMMON_SHARES"
            else:
                method = "MULTIPLE_HISTORICAL_NAME_MATCHES"

        rows.append(
            {
                "ticker": ticker,
                "expected_name": str(queue_row["name"]),
                "expected_exchange": str(queue_row["exchange"]),
                "expected_delisting_date": str(queue_row["alpha_delisting_date"]),
                "classification_status": status,
                "classification_eligible": status == COMMON_STATUS,
                "resolution_method": method,
                "original_classification_status": original_status,
                "matched_candidate_name": (
                    None if matched_candidate is None else matched_candidate.get("name")
                ),
                "matched_candidate_security_type": (
                    None if matched_candidate is None else matched_candidate.get("securityType")
                ),
                "matched_candidate_security_type_2": (
                    None if matched_candidate is None else matched_candidate.get("securityType2")
                ),
                "matched_candidate_figi": (
                    None if matched_candidate is None else matched_candidate.get("figi")
                ),
                "name_match_score": match_score,
                "accepted_cik": (None if seed_row is None else seed_row.get("accepted_cik")),
                "sec_resolution_status": (
                    None if seed_row is None else seed_row.get("resolution_status")
                ),
                "sec_share_concepts": concepts,
                "tiingo_security_id": str(source_row["security_id"]),
                "tiingo_first_date": str(source_row["first_date"]),
                "tiingo_last_date": str(source_row["last_date"]),
                "openfigi_source_sha256": (
                    str(original_row["source_sha256"]) if raw_sha256 is None else raw_sha256
                ),
            }
        )

    statuses = Counter(row["classification_status"] for row in rows)
    methods = Counter(row["resolution_method"] for row in rows)
    evidence = {
        "cohort_symbol_count": len(cohort),
        "common_stock_symbol_count": statuses[COMMON_STATUS],
        "non_common_symbol_count": statuses[NON_COMMON_STATUS],
        "non_common_symbols": sorted(
            row["ticker"] for row in rows if row["classification_status"] == NON_COMMON_STATUS
        ),
        "unresolved_symbol_count": statuses[UNRESOLVED_STATUS],
        "unresolved_symbols": sorted(
            row["ticker"] for row in rows if row["classification_status"] == UNRESOLVED_STATUS
        ),
        "status_counts": dict(sorted(statuses.items())),
        "resolution_method_counts": dict(sorted(methods.items())),
        "classification_resolution_gate_pass": statuses[UNRESOLVED_STATUS] == 0,
    }
    return rows, evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--tiingo-manifest", type=Path, required=True)
    parser.add_argument("--original-classification", type=Path, required=True)
    parser.add_argument("--openfigi-raw-dir", type=Path, required=True)
    parser.add_argument("--sec-resolution-seed", type=Path, required=True)
    parser.add_argument("--sec-shares", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    queue_document = json.loads(args.queue.read_text(encoding="utf-8"))
    tiingo_manifest = json.loads(args.tiingo_manifest.read_text(encoding="utf-8"))
    if file_sha256(args.queue) != tiingo_manifest["queue_sha256"]:
        raise ValueError("queue SHA256 does not match Tiingo manifest")
    original_rows = pq.read_table(args.original_classification).to_pylist()
    seed = _resolution_seed_rows(args.sec_resolution_seed)
    concepts = _common_share_concepts(args.sec_shares)
    rows, evidence = resolve_historical_classifications(
        queue_document,
        tiingo_manifest,
        original_rows,
        raw_dir=args.openfigi_raw_dir,
        resolution_seed=seed,
        share_concepts=concepts,
    )

    output_path = args.output / "historical_security_classification.parquet"
    atomic_parquet(rows, output_path)
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "purpose": "ACCOUNT_FREE_HISTORICAL_SECURITY_TYPE_RESOLUTION",
        **evidence,
        "input_queue": {
            "path": str(args.queue),
            "sha256": file_sha256(args.queue),
        },
        "inputs": {
            "tiingo_manifest": {
                "path": str(args.tiingo_manifest),
                "sha256": file_sha256(args.tiingo_manifest),
            },
            "original_classification": {
                "path": str(args.original_classification),
                "sha256": file_sha256(args.original_classification),
            },
            "sec_resolution_seed": {
                "path": str(args.sec_resolution_seed),
                "sha256": file_sha256(args.sec_resolution_seed),
            },
            "sec_shares": {
                "path": str(args.sec_shares),
                "sha256": file_sha256(args.sec_shares),
            },
        },
        "output": {
            "path": str(output_path),
            "sha256": file_sha256(output_path),
        },
        "metadata_temporality": ("RETROSPECTIVE_HISTORICAL_IDENTITY_FOR_MACHINERY_VALIDATION_ONLY"),
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY",
    }
    summary_path = args.output / "historical_security_classification_summary.json"
    atomic_write(
        summary_path,
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if evidence["classification_resolution_gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
