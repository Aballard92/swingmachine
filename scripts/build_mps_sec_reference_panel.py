#!/usr/bin/env python3
"""Build point-in-time SEC SIC reference metadata for the MPS research panel."""

from __future__ import annotations

import argparse
import csv
import io
import json
import tarfile
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

DEFAULT_MEMBER = "swingmachine_dataset_discovery/sec_facts/submissions.csv"
COMMON_STATUS = "PROVEN_HISTORICAL_COMMON_STOCK"
UNKNOWN_SECTOR = "UNKNOWN"
BULK_EVIDENCE_KIND = "HASH_PINNED_SEC_SUBMISSIONS_ARCHIVE"
SUPPLEMENTAL_EVIDENCE_KIND = "MANUALLY_REVIEWED_SEC_STATIC_FILING_HEADER"
EVENT_STRING_COLUMNS = (
    "ticker",
    "sector",
    "reference_accession",
    "reference_form",
    "reference_period",
    "reference_filing_ticker",
    "reference_evidence_kind",
    "reference_evidence_url",
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


def atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(
        pa.Table.from_pandas(frame, preserve_index=False),
        temporary,
        compression="zstd",
    )
    temporary.replace(path)


def sector_from_sic(value: str | int | None) -> str:
    """Map a four-digit SIC to its conservative top-level SIC division."""
    if value is None:
        return UNKNOWN_SECTOR
    text = str(value).strip()
    if not text.isdigit():
        return UNKNOWN_SECTOR
    sic = int(text)
    if sic <= 0 or sic > 9999:
        return UNKNOWN_SECTOR
    if 100 <= sic <= 999:
        return "SIC_A_AGRICULTURE_FORESTRY_FISHING"
    if 1000 <= sic <= 1499:
        return "SIC_B_MINING"
    if 1500 <= sic <= 1799:
        return "SIC_C_CONSTRUCTION"
    if 2000 <= sic <= 3999:
        return "SIC_D_MANUFACTURING"
    if 4000 <= sic <= 4999:
        return "SIC_E_TRANSPORT_COMMUNICATIONS_UTILITIES"
    if 5000 <= sic <= 5199:
        return "SIC_F_WHOLESALE_TRADE"
    if 5200 <= sic <= 5999:
        return "SIC_G_RETAIL_TRADE"
    if 6000 <= sic <= 6799:
        return "SIC_H_FINANCE_INSURANCE_REAL_ESTATE"
    if 7000 <= sic <= 8999:
        return "SIC_I_SERVICES"
    if 9000 <= sic <= 9899:
        return "SIC_J_PUBLIC_ADMINISTRATION"
    if 9900 <= sic <= 9999:
        return "SIC_K_NONCLASSIFIABLE"
    return UNKNOWN_SECTOR


def accepted_at_utc(value: str) -> pd.Timestamp:
    """Interpret SEC acceptance timestamps as America/New_York."""
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        raise ValueError("SEC acceptance timestamp unexpectedly contains a timezone")
    return timestamp.tz_localize(
        "America/New_York",
        ambiguous="raise",
        nonexistent="raise",
    ).tz_convert("UTC")


def read_sec_events(
    archive: Path,
    *,
    member: str,
    expected_member_sha256: str,
    classifications: pd.DataFrame,
) -> tuple[pd.DataFrame, str]:
    required = {
        "ticker",
        "accepted_cik",
        "classification_status",
    }
    missing = sorted(required - set(classifications.columns))
    if missing:
        raise ValueError(f"classification missing columns: {', '.join(missing)}")
    common = classifications.loc[classifications["classification_status"].eq(COMMON_STATUS)].copy()
    if common["accepted_cik"].isna().any():
        raise ValueError("common-stock classification contains missing accepted CIK")
    cik_to_ticker = {
        str(int(row.accepted_cik)): str(row.ticker).upper() for row in common.itertuples()
    }
    if len(cik_to_ticker) != len(common):
        raise ValueError("common-stock classification contains duplicate accepted CIK")

    with tarfile.open(archive, mode="r:gz") as bundle:
        handle = bundle.extractfile(member)
        if handle is None:
            raise ValueError(f"archive member not found: {member}")
        payload = handle.read()
    member_sha256 = sha256(payload).hexdigest()
    if member_sha256 != expected_member_sha256:
        raise ValueError("SEC submissions member SHA256 mismatch")

    rows: list[dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8")))
    required_fields = {"adsh", "cik", "sic", "form", "period", "accepted", "ticker"}
    if reader.fieldnames is None or not required_fields.issubset(reader.fieldnames):
        raise ValueError("SEC submissions member has an unexpected schema")
    for source in reader:
        ticker = cik_to_ticker.get(source["cik"])
        sector = sector_from_sic(source["sic"])
        if ticker is None or sector == UNKNOWN_SECTOR:
            continue
        rows.append(
            {
                "ticker": ticker,
                "accepted_cik": int(source["cik"]),
                "sic": int(source["sic"]),
                "sector": sector,
                "reference_available_at": accepted_at_utc(source["accepted"]),
                "reference_accession": source["adsh"],
                "reference_form": source["form"],
                "reference_period": source["period"],
                "reference_filing_ticker": source["ticker"].upper(),
                "reference_evidence_kind": BULK_EVIDENCE_KIND,
                "reference_evidence_url": pd.NA,
            }
        )
    events = pd.DataFrame(rows)
    if events.empty:
        return events, member_sha256
    events = normalize_events(events)
    return events, member_sha256


def common_classification_ciks(classifications: pd.DataFrame) -> dict[str, int]:
    required = {"ticker", "accepted_cik", "classification_status"}
    missing = sorted(required - set(classifications.columns))
    if missing:
        raise ValueError(f"classification missing columns: {', '.join(missing)}")
    common = classifications.loc[classifications["classification_status"].eq(COMMON_STATUS)]
    if common["accepted_cik"].isna().any():
        raise ValueError("common-stock classification contains missing accepted CIK")
    mapping = {str(row.ticker).upper(): int(row.accepted_cik) for row in common.itertuples()}
    if len(mapping) != len(common):
        raise ValueError("common-stock classification contains duplicate ticker")
    return mapping


def normalize_events(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events
    clashes = (
        events.groupby(["ticker", "reference_available_at"], dropna=False)["sic"].nunique().gt(1)
    )
    if clashes.any():
        raise ValueError("conflicting SIC values share an acceptance timestamp")
    events = (
        events.sort_values(
            [
                "ticker",
                "reference_available_at",
                "reference_accession",
                "reference_evidence_kind",
            ],
            kind="stable",
        )
        .drop_duplicates(
            ["ticker", "reference_available_at", "sic"],
            keep="first",
        )
        .reset_index(drop=True)
    )
    events["accepted_cik"] = events["accepted_cik"].astype("Int64")
    events["sic"] = events["sic"].astype("Int64")
    for column in EVENT_STRING_COLUMNS:
        events[column] = events[column].astype("string")
    return events


def read_supplemental_events(
    path: Path,
    *,
    classifications: pd.DataFrame,
) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise ValueError("supplemental events must be a JSON object containing events")
    required = {
        "ticker",
        "accepted_cik",
        "sic",
        "accepted",
        "accession",
        "form",
        "period",
        "filing_ticker",
        "evidence_kind",
        "evidence_url",
    }
    common_ciks = common_classification_ciks(classifications)
    rows: list[dict[str, Any]] = []
    for position, source in enumerate(payload["events"]):
        if not isinstance(source, dict):
            raise ValueError(f"supplemental event {position} is not an object")
        missing = sorted(required - set(source))
        if missing:
            raise ValueError(f"supplemental event {position} missing: {', '.join(missing)}")
        ticker = str(source["ticker"]).upper()
        cik = int(source["accepted_cik"])
        if common_ciks.get(ticker) != cik:
            raise ValueError(f"supplemental event {position} does not match common classification")
        if source["evidence_kind"] != SUPPLEMENTAL_EVIDENCE_KIND:
            raise ValueError(f"supplemental event {position} has invalid evidence kind")
        evidence_url = str(source["evidence_url"])
        if not evidence_url.startswith("https://www.sec.gov/Archives/edgar/data/"):
            raise ValueError(f"supplemental event {position} is not a static SEC URL")
        accession = str(source["accession"])
        if accession.replace("-", "") not in evidence_url:
            raise ValueError(f"supplemental event {position} accession is absent from evidence URL")
        sector = sector_from_sic(source["sic"])
        if sector == UNKNOWN_SECTOR:
            raise ValueError(f"supplemental event {position} has invalid SIC")
        rows.append(
            {
                "ticker": ticker,
                "accepted_cik": cik,
                "sic": int(source["sic"]),
                "sector": sector,
                "reference_available_at": accepted_at_utc(str(source["accepted"])),
                "reference_accession": accession,
                "reference_form": str(source["form"]),
                "reference_period": str(source["period"]),
                "reference_filing_ticker": str(source["filing_ticker"]).upper(),
                "reference_evidence_kind": source["evidence_kind"],
                "reference_evidence_url": evidence_url,
            }
        )
    return normalize_events(pd.DataFrame(rows))


def combine_events(
    archive_events: pd.DataFrame,
    supplemental_events: pd.DataFrame,
) -> pd.DataFrame:
    if archive_events.empty:
        return normalize_events(supplemental_events.copy())
    if supplemental_events.empty:
        return normalize_events(archive_events.copy())
    return normalize_events(pd.concat([archive_events, supplemental_events], ignore_index=True))


def build_reference_panel(
    eligibility: pd.DataFrame,
    classifications: pd.DataFrame,
    events: pd.DataFrame,
) -> pd.DataFrame:
    required = {"security_id", "ticker", "trading_date", "available_at"}
    missing = sorted(required - set(eligibility.columns))
    if missing:
        raise ValueError(f"eligibility missing columns: {', '.join(missing)}")
    classification = classifications.set_index("ticker")
    events = events.copy()
    for column in ("reference_evidence_kind", "reference_evidence_url"):
        if column not in events:
            events[column] = pd.Series(pd.NA, index=events.index, dtype="string")
    prepared = eligibility[list(required)].copy()
    prepared["ticker"] = prepared["ticker"].astype(str).str.upper()
    prepared["price_available_at"] = pd.to_datetime(
        prepared.pop("available_at"),
        utc=True,
        errors="raise",
    )
    if prepared.duplicated(["security_id", "ticker", "trading_date"]).any():
        raise ValueError("eligibility contains duplicate security/date rows")

    outputs: list[pd.DataFrame] = []
    for ticker, prices in prepared.groupby("ticker", sort=True):
        if ticker not in classification.index:
            raise ValueError(f"eligibility ticker missing from classification: {ticker}")
        issuer_events = events.loc[events["ticker"].eq(ticker)].copy()
        prices = prices.sort_values("price_available_at", kind="stable")
        if issuer_events.empty:
            joined = prices.copy()
            joined["accepted_cik"] = pd.Series(pd.NA, index=joined.index, dtype="Int64")
            joined["sic"] = pd.Series(pd.NA, index=joined.index, dtype="Int64")
            joined["reference_available_at"] = pd.Series(
                pd.NaT,
                index=joined.index,
                dtype="datetime64[ns, UTC]",
            )
            for column in (
                "reference_accession",
                "reference_form",
                "reference_period",
                "reference_filing_ticker",
                "reference_evidence_kind",
                "reference_evidence_url",
            ):
                joined[column] = pd.Series(
                    pd.NA,
                    index=joined.index,
                    dtype="string",
                )
            joined["sector"] = pd.Series(
                UNKNOWN_SECTOR,
                index=joined.index,
                dtype="string",
            )
        else:
            joined = pd.merge_asof(
                prices,
                issuer_events.drop(columns="ticker").sort_values(
                    "reference_available_at",
                    kind="stable",
                ),
                left_on="price_available_at",
                right_on="reference_available_at",
                direction="backward",
            )
            joined["sector"] = joined["sector"].fillna(UNKNOWN_SECTOR)
        joined["sector_reference_available"] = joined["sector"].ne(UNKNOWN_SECTOR)
        joined["sector_reference_status"] = joined["sector_reference_available"].map(
            {
                True: "POINT_IN_TIME_SEC_SIC_AVAILABLE",
                False: "UNAVAILABLE_NO_PRIOR_SEC_SIC",
            }
        )
        outputs.append(joined)
    panel = pd.concat(outputs, ignore_index=True)
    return panel.sort_values(["ticker", "trading_date"], kind="stable").reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--member", default=DEFAULT_MEMBER)
    parser.add_argument("--member-sha256", required=True)
    parser.add_argument("--classification", type=Path, required=True)
    parser.add_argument("--eligibility", type=Path, required=True)
    parser.add_argument("--supplemental-events", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    archive_sha256 = file_sha256(args.archive)
    if archive_sha256 != args.archive_sha256:
        raise ValueError("source archive SHA256 mismatch")
    classifications = pq.read_table(args.classification).to_pandas()
    eligibility = pq.read_table(
        args.eligibility,
        columns=["security_id", "ticker", "trading_date", "available_at"],
    ).to_pandas()
    archive_events, member_sha256 = read_sec_events(
        args.archive,
        member=args.member,
        expected_member_sha256=args.member_sha256,
        classifications=classifications,
    )
    supplemental_events = (
        read_supplemental_events(
            args.supplemental_events,
            classifications=classifications,
        )
        if args.supplemental_events is not None
        else pd.DataFrame()
    )
    events = combine_events(archive_events, supplemental_events)
    panel = build_reference_panel(eligibility, classifications, events)
    output_path = args.output / "sec_point_in_time_reference_panel.parquet"
    atomic_parquet(panel, output_path)

    common_symbols = set(
        classifications.loc[classifications["classification_status"].eq(COMMON_STATUS), "ticker"]
    )
    available = panel["sector_reference_available"].astype(bool)
    common = panel["ticker"].isin(common_symbols)
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "purpose": "POINT_IN_TIME_SEC_SIC_REFERENCE_METADATA",
        "source_policy": "SEC_FILING_ACCEPTANCE_TIME_FORWARD_ONLY",
        "taxonomy": "TOP_LEVEL_STANDARD_INDUSTRIAL_CLASSIFICATION_DIVISION",
        "row_count": len(panel),
        "symbol_count": int(panel["ticker"].nunique()),
        "common_stock_symbol_count": len(common_symbols),
        "reference_event_count": len(events),
        "reference_event_counts_by_evidence_kind": {
            str(key): int(value)
            for key, value in events["reference_evidence_kind"].value_counts().sort_index().items()
        },
        "reference_available_row_count": int(available.sum()),
        "reference_unavailable_row_count": int((~available).sum()),
        "common_reference_available_row_count": int((available & common).sum()),
        "common_reference_unavailable_row_count": int((~available & common).sum()),
        "symbols_with_reference": sorted(set(panel.loc[available, "ticker"])),
        "symbols_without_reference": sorted(common_symbols - set(panel.loc[available, "ticker"])),
        "sector_counts": {
            str(key): int(value)
            for key, value in panel.loc[available, "sector"].value_counts().sort_index().items()
        },
        "available_row_counts_by_evidence_kind": {
            str(key): int(value)
            for key, value in panel.loc[available, "reference_evidence_kind"]
            .value_counts()
            .sort_index()
            .items()
        },
        "sector_gate_pass": bool((available | ~common).all()),
        "historical_reference_windows_gate_pass": bool((available | ~common).all()),
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY",
        "inputs": {
            "archive": {
                "path": str(args.archive),
                "sha256": archive_sha256,
            },
            "archive_member": {
                "path": args.member,
                "sha256": member_sha256,
            },
            "classification": {
                "path": str(args.classification),
                "sha256": file_sha256(args.classification),
            },
            "eligibility": {
                "path": str(args.eligibility),
                "sha256": file_sha256(args.eligibility),
            },
            "supplemental_events": (
                {
                    "path": str(args.supplemental_events),
                    "sha256": file_sha256(args.supplemental_events),
                }
                if args.supplemental_events is not None
                else None
            ),
        },
        "output": {
            "path": str(output_path),
            "sha256": file_sha256(output_path),
        },
    }
    summary_path = args.output / "sec_point_in_time_reference_summary.json"
    atomic_write(
        summary_path,
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
