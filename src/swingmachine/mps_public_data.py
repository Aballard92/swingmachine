"""Zero-spend public-data normalization for the MPS remediation lane.

The functions in this module preserve source limitations. They do not infer
historical identity, availability timestamps, or corporate-action terms when a
source does not state them explicitly.
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from io import StringIO
from pathlib import Path
from xml.etree import ElementTree


@dataclass(frozen=True)
class PublicSourceFile:
    source_id: str
    path: str
    bytes: int
    sha256: str
    retrieved_at: str


@dataclass(frozen=True)
class ListingLifecycle:
    symbol: str
    name: str
    exchange: str
    asset_type: str
    ipo_date: date | None
    delisting_date: date | None
    status: str
    source_id: str


@dataclass(frozen=True)
class NasdaqSecurity:
    symbol: str
    security_name: str
    exchange: str
    etf: bool | None
    test_issue: bool
    source_created_at: str


@dataclass(frozen=True)
class SecTicker:
    cik: int
    ticker: str
    title: str


@dataclass(frozen=True)
class SecIssuerMetadata:
    cik: int
    name: str
    entity_type: str | None
    sic: str | None
    sic_description: str | None
    tickers: tuple[str, ...]
    exchanges: tuple[str, ...]
    former_names: tuple[Mapping[str, object], ...]
    acceptance_by_accession: Mapping[str, datetime]


@dataclass(frozen=True)
class SharesFact:
    cik: int
    concept: str
    value: float
    period_end: date
    accession: str
    form: str
    filed: date
    available_at: datetime


SHARES_CONCEPTS = (
    "EntityCommonStockSharesOutstanding",
    "CommonStockSharesOutstanding",
)


def _date(value: str | None) -> date | None:
    if not value or value in {"None", "null", "0000-00-00"}:
        return None
    return date.fromisoformat(value)


def sha256_file(path: str | Path, chunk_size: int = 64 * 1024) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def source_file_record(
    source_id: str,
    path: str | Path,
    retrieved_at: datetime,
) -> PublicSourceFile:
    if retrieved_at.tzinfo is None:
        raise ValueError("retrieved_at must be timezone-aware")
    resolved = Path(path)
    return PublicSourceFile(
        source_id=source_id,
        path=str(resolved),
        bytes=resolved.stat().st_size,
        sha256=sha256_file(resolved),
        retrieved_at=retrieved_at.astimezone(UTC).isoformat(),
    )


def parse_alpha_vantage_listing_csv(text: str, source_id: str) -> tuple[ListingLifecycle, ...]:
    if not text.strip() or text.lstrip().startswith("{"):
        return ()
    records = []
    for row in csv.DictReader(StringIO(text)):
        records.append(
            ListingLifecycle(
                symbol=row["symbol"].strip().upper(),
                name=row["name"].strip(),
                exchange=row["exchange"].strip(),
                asset_type=row["assetType"].strip(),
                ipo_date=_date(row.get("ipoDate")),
                delisting_date=_date(row.get("delistingDate")),
                status=row["status"].strip(),
                source_id=source_id,
            )
        )
    return tuple(records)


def _nasdaq_creation_time(rows: list[list[str]]) -> str:
    for row in reversed(rows):
        if row and row[0].startswith("File Creation Time:"):
            return row[0].split(":", 1)[1].strip()
    raise ValueError("Nasdaq source has no file creation timestamp")


def parse_nasdaq_directory(text: str, *, exchange_family: str) -> tuple[NasdaqSecurity, ...]:
    rows = list(csv.reader(StringIO(text), delimiter="|"))
    if len(rows) < 2:
        raise ValueError("Nasdaq directory is empty")
    headers = rows[0]
    created = _nasdaq_creation_time(rows)
    output = []
    for raw in rows[1:]:
        if not raw or raw[0].startswith("File Creation Time:"):
            continue
        row = dict(zip(headers, raw, strict=False))
        if exchange_family == "NASDAQ":
            symbol = row["Symbol"]
            exchange = "NASDAQ"
            etf = row.get("ETF") == "Y" if row.get("ETF") in {"Y", "N"} else None
        else:
            symbol = row["ACT Symbol"]
            exchange = row.get("Exchange", "")
            etf = row.get("ETF") == "Y" if row.get("ETF") in {"Y", "N"} else None
        output.append(
            NasdaqSecurity(
                symbol=symbol.strip().upper(),
                security_name=row["Security Name"].strip(),
                exchange=exchange.strip(),
                etf=etf,
                test_issue=row.get("Test Issue") == "Y",
                source_created_at=created,
            )
        )
    return tuple(output)


def parse_sec_ticker_proxy(text: str) -> tuple[SecTicker, ...]:
    marker = "Markdown Content:"
    payload = text.split(marker, 1)[1].strip() if marker in text else text.strip()
    start = payload.find("{")
    if start < 0:
        raise ValueError("SEC ticker payload has no JSON object")
    parsed = json.loads(payload[start:])
    return tuple(
        SecTicker(
            cik=int(row["cik_str"]),
            ticker=str(row["ticker"]).upper(),
            title=str(row["title"]),
        )
        for _, row in sorted(parsed.items(), key=lambda item: int(item[0]))
    )


def parse_sec_browse_atom_ciks(text: str) -> tuple[int, ...]:
    """Return the distinct issuer CIKs exposed by an SEC browse-company Atom feed."""

    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise ValueError("SEC browse-company response is not valid XML") from exc
    ciks = {
        int(element.text)
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "cik" and element.text and element.text.isdigit()
    }
    return tuple(sorted(ciks))


def normalized_issuer_name(value: str) -> str:
    """Normalize an issuer name for conservative SEC identity comparison."""

    normalized = value.upper().replace("&", " AND ")
    normalized = re.sub(r"\s+-\s+CLASS\s+[A-Z0-9]+$", "", normalized)
    normalized = re.sub(r"\b(CLASS|COMMON STOCK)\s+[A-Z0-9]+$", "", normalized)
    normalized = re.sub(
        r"\b(INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC)\b", " ", normalized
    )
    return " ".join(re.findall(r"[A-Z0-9]+", normalized))


def sec_issuer_name_matches(expected_name: str, submissions: Mapping[str, object]) -> bool:
    """Match an expected issuer name to the current or former SEC issuer names."""

    expected = normalized_issuer_name(expected_name)
    candidates = [str(submissions.get("name", ""))]
    for former in submissions.get("formerNames", ()):
        if isinstance(former, Mapping) and former.get("name"):
            candidates.append(str(former["name"]))
    return bool(expected) and expected in {normalized_issuer_name(name) for name in candidates}


def parse_sec_submissions(payload: Mapping[str, object]) -> SecIssuerMetadata:
    filings = payload.get("filings", {})
    recent = filings.get("recent", {}) if isinstance(filings, Mapping) else {}
    accessions = recent.get("accessionNumber", ()) if isinstance(recent, Mapping) else ()
    accepted = recent.get("acceptanceDateTime", ()) if isinstance(recent, Mapping) else ()
    acceptance_by_accession = {}
    for accession, timestamp in zip(accessions, accepted, strict=False):
        if timestamp:
            parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            acceptance_by_accession[str(accession)] = parsed.astimezone(UTC)
    return SecIssuerMetadata(
        cik=int(payload["cik"]),
        name=str(payload.get("name", "")),
        entity_type=str(payload["entityType"]) if payload.get("entityType") else None,
        sic=str(payload["sic"]) if payload.get("sic") else None,
        sic_description=str(payload["sicDescription"]) if payload.get("sicDescription") else None,
        tickers=tuple(str(value).upper() for value in payload.get("tickers", ())),
        exchanges=tuple(str(value) for value in payload.get("exchanges", ())),
        former_names=tuple(payload.get("formerNames", ())),
        acceptance_by_accession=acceptance_by_accession,
    )


def extract_sec_shares_facts(
    companyfacts: Mapping[str, object],
    issuer: SecIssuerMetadata,
) -> tuple[SharesFact, ...]:
    facts = companyfacts.get("facts", {})
    output = []
    for taxonomy in ("dei", "us-gaap"):
        taxonomy_facts = facts.get(taxonomy, {}) if isinstance(facts, Mapping) else {}
        if not isinstance(taxonomy_facts, Mapping):
            continue
        for concept in SHARES_CONCEPTS:
            concept_data = taxonomy_facts.get(concept)
            if not isinstance(concept_data, Mapping):
                continue
            units = concept_data.get("units", {})
            share_rows = units.get("shares", ()) if isinstance(units, Mapping) else ()
            for row in share_rows:
                accession = str(row.get("accn", ""))
                available_at = issuer.acceptance_by_accession.get(accession)
                if available_at is None:
                    continue
                if not all(row.get(key) is not None for key in ("val", "end", "filed", "form")):
                    continue
                output.append(
                    SharesFact(
                        cik=issuer.cik,
                        concept=concept,
                        value=float(row["val"]),
                        period_end=date.fromisoformat(str(row["end"])),
                        accession=accession,
                        form=str(row["form"]),
                        filed=date.fromisoformat(str(row["filed"])),
                        available_at=available_at,
                    )
                )
    return tuple(
        sorted(
            output,
            key=lambda row: (row.available_at, row.period_end, row.accession, row.concept),
        )
    )


def dataclass_rows(records: Iterable[object]) -> list[dict[str, object]]:
    return [asdict(record) for record in records]
