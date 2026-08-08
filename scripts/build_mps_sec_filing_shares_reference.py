#!/usr/bin/env python3
"""Build point-in-time shares facts from SEC inline-XBRL filing covers."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

EXPECTED_CONCEPT = "EntityCommonStockSharesOutstanding"
EXPECTED_INLINE_NAME = f"dei:{EXPECTED_CONCEPT}".lower()
INVESTMENT_COMPANY_CONCEPT = "InvestmentCompanySharesOutstanding"
INVESTMENT_COMPANY_FORMS = {"N-CSR", "N-CSRS"}
ZERO_TOKENS = {"", "-", "—", "no", "none", "nil"}


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
    temporary = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(pa.Table.from_pylist(rows), temporary, compression="zstd")
    temporary.replace(path)


class InlineSharesParser(HTMLParser):
    """Extract contexts and exact DEI shares facts without third-party parsers."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.contexts: dict[str, dict[str, Any]] = {}
        self.facts: list[dict[str, Any]] = []
        self._context_id: str | None = None
        self._instant: str | None = None
        self._members: list[str] = []
        self._capture: dict[str, Any] | None = None

    @staticmethod
    def _is_tag(tag: str, local_name: str) -> bool:
        return tag == local_name or tag.endswith(f":{local_name}")

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        tag = tag.lower()
        attributes = {key.lower(): value for key, value in attrs}
        if self._is_tag(tag, "context"):
            self._context_id = attributes.get("id")
            self._instant = None
            self._members = []
        elif self._context_id and self._is_tag(tag, "instant"):
            self._capture = {"kind": "instant", "text": []}
        elif self._context_id and self._is_tag(tag, "explicitmember"):
            self._capture = {"kind": "member", "text": []}
        elif (
            tag == "ix:nonfraction"
            and str(attributes.get("name", "")).lower() == EXPECTED_INLINE_NAME
        ):
            self._capture = {
                "kind": "fact",
                "text": [],
                "attributes": attributes,
            }

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._capture["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._capture is not None:
            kind = self._capture["kind"]
            text = "".join(self._capture["text"]).strip()
            if kind == "instant" and self._is_tag(tag, "instant"):
                self._instant = text
                self._capture = None
            elif kind == "member" and self._is_tag(tag, "explicitmember"):
                self._members.append(text)
                self._capture = None
            elif kind == "fact" and tag == "ix:nonfraction":
                self.facts.append(
                    {
                        "text": text,
                        "attributes": self._capture["attributes"],
                    }
                )
                self._capture = None
        if self._context_id and self._is_tag(tag, "context"):
            self.contexts[self._context_id] = {
                "instant": self._instant,
                "members": tuple(self._members),
            }
            self._context_id = None


def parse_inline_number(text: str, attributes: dict[str, str | None]) -> Decimal:
    if str(attributes.get("format", "")).lower().endswith("fixed-zero"):
        return Decimal(0)
    normalized = text.replace(",", "").replace("\u00a0", "").replace("\u2014", "").strip()
    if text.strip().lower() in ZERO_TOKENS:
        return Decimal(0)
    if not normalized:
        raise ValueError("empty non-zero inline-XBRL share fact")
    try:
        value = Decimal(normalized)
    except InvalidOperation as error:
        raise ValueError(f"invalid inline-XBRL numeric text: {text!r}") from error
    scale = int(str(attributes.get("scale") or "0"))
    value *= Decimal(10) ** scale
    if attributes.get("sign") == "-":
        value = -value
    return value


def extract_facts(payload: bytes) -> list[dict[str, Any]]:
    document = payload.decode("utf-8", errors="replace")
    fact_blocks = [
        block
        for block in re.findall(
            r"<ix:nonfraction\b[^>]*>.*?</ix:nonfraction\s*>",
            document,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if re.search(
            rf"\bname\s*=\s*['\"]{re.escape(EXPECTED_INLINE_NAME)}['\"]",
            block.split(">", 1)[0],
            flags=re.IGNORECASE,
        )
    ]
    if not fact_blocks:
        return []
    context_ids: set[str] = set()
    for block in fact_blocks:
        match = re.search(
            r"\bcontextref\s*=\s*['\"]([^'\"]+)['\"]",
            block.split(">", 1)[0],
            flags=re.IGNORECASE,
        )
        if match is None:
            raise ValueError("shares fact is missing contextRef")
        context_ids.add(match.group(1))
    context_blocks: list[str] = []
    for context_id in sorted(context_ids):
        match = re.search(
            r"<(?:[A-Za-z0-9_-]+:)?context\b"
            rf"(?=[^>]*\bid\s*=\s*['\"]{re.escape(context_id)}['\"])[^>]*>"
            r".*?</(?:[A-Za-z0-9_-]+:)?context\s*>",
            document,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match is None:
            raise ValueError(f"shares context is missing: {context_id}")
        context_blocks.append(match.group(0))

    parser = InlineSharesParser()
    parser.feed("<html>" + "".join(context_blocks + fact_blocks) + "</html>")
    facts: list[dict[str, Any]] = []
    for fact in parser.facts:
        attributes = fact["attributes"]
        context = parser.contexts.get(str(attributes.get("contextref")))
        if context is None or context["instant"] is None:
            raise ValueError("shares fact has no resolvable instant context")
        unit = str(attributes.get("unitref", "")).lower()
        if "share" not in unit:
            raise ValueError(f"shares fact has unexpected unit reference: {unit}")
        value = parse_inline_number(str(fact["text"]), attributes)
        if value < 0:
            raise ValueError("shares fact is negative")
        facts.append(
            {
                "instant": str(context["instant"]),
                "members": tuple(context["members"]),
                "value": value,
            }
        )
    return facts


class FilingTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []

    def handle_data(self, data: str) -> None:
        normalized = " ".join(data.split())
        if normalized:
            self.text.append(normalized)


def extract_investment_company_shares(payload: bytes) -> Decimal:
    parser = FilingTextParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    text = " ".join(parser.text)
    matches = re.findall(
        r"\bShares outstanding\s+([\d,]+)\s+"
        r"Net asset value per outstanding share\b",
        text,
        flags=re.IGNORECASE,
    )
    values = {Decimal(match.replace(",", "")) for match in matches}
    if not values:
        raise ValueError("NO_INVESTMENT_COMPANY_SHARES_OUTSTANDING")
    if len(values) != 1:
        raise ValueError("conflicting investment-company shares outstanding")
    value = next(iter(values))
    if value <= 0:
        raise ValueError("investment-company shares outstanding is not positive")
    return value


def aggregate_filing_facts(
    facts: list[dict[str, Any]],
    *,
    filing_date: str,
) -> tuple[str, Decimal, str]:
    if not facts:
        raise ValueError("NO_ENTITY_COMMON_STOCK_SHARES_OUTSTANDING")
    filing_day = date.fromisoformat(filing_date)
    by_instant: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fact in facts:
        instant = date.fromisoformat(str(fact["instant"]))
        if instant > filing_day:
            raise ValueError("shares fact instant is after filing date")
        by_instant[instant.isoformat()].append(fact)
    selected_instant = max(by_instant)
    selected = by_instant[selected_instant]

    values_by_members: dict[tuple[str, ...], set[Decimal]] = defaultdict(set)
    for fact in selected:
        values_by_members[tuple(fact["members"])].add(Decimal(fact["value"]))
    conflicts = {
        members: values for members, values in values_by_members.items() if len(values) != 1
    }
    if conflicts:
        raise ValueError("conflicting shares values for the same XBRL context members")

    non_dimensional = values_by_members.get(())
    dimensional_total = sum(
        next(iter(values)) for members, values in values_by_members.items() if members
    )
    if non_dimensional is not None:
        total = next(iter(non_dimensional))
        if dimensional_total and total != dimensional_total:
            raise ValueError("non-dimensional and class-level shares totals disagree")
        method = "NON_DIMENSIONAL_TOTAL"
    else:
        total = dimensional_total
        method = "SUM_DISTINCT_CLASS_CONTEXTS"
    if total <= 0:
        raise ValueError("aggregated common shares outstanding is not positive")
    return selected_instant, total, method


def conservative_available_at(filed: str) -> str:
    filed_date = date.fromisoformat(filed)
    return (
        datetime.combine(
            filed_date,
            time.max,
            tzinfo=UTC,
        )
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_cohort_bounds(path: Path | None) -> dict[str, tuple[str, str]]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(row["ticker"]).upper(): (
            str(row["request_start_date"]),
            str(row["request_end_date"]),
        )
        for row in payload["selected"]
    }


def build_rows(
    manifest: dict[str, Any],
    *,
    cohort_bounds: dict[str, tuple[str, str]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if manifest.get("access") != "ANONYMOUS_NO_ACCOUNT_NO_API_KEY":
        raise ValueError("source access contract is not anonymous")
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    cohort_bounds = cohort_bounds or {}
    for artifact in manifest["artifacts"]:
        ticker = str(artifact["ticker"]).upper()
        bounds = cohort_bounds.get(ticker)
        if bounds and str(artifact["filing_date"]) < bounds[0]:
            rejected.append(
                {
                    "ticker": ticker,
                    "cik": int(artifact["cik"]),
                    "accession": str(artifact["accession"]),
                    "reason": "PRE_COHORT_AVAILABILITY",
                }
            )
            continue
        if bounds and str(artifact["filing_date"]) > bounds[1]:
            rejected.append(
                {
                    "ticker": ticker,
                    "cik": int(artifact["cik"]),
                    "accession": str(artifact["accession"]),
                    "reason": "POST_COHORT_AVAILABILITY",
                }
            )
            continue
        path = Path(artifact["path"])
        actual_hash = file_sha256(path)
        if actual_hash != artifact["sha256"]:
            raise ValueError(f"filing hash mismatch: {path}")
        try:
            facts = extract_facts(path.read_bytes())
            if facts:
                instant, total, method = aggregate_filing_facts(
                    facts,
                    filing_date=str(artifact["filing_date"]),
                )
                concept = EXPECTED_CONCEPT
            elif str(artifact["form"]) in INVESTMENT_COMPANY_FORMS:
                total = extract_investment_company_shares(path.read_bytes())
                instant = str(artifact["report_date"])
                date.fromisoformat(instant)
                method = "INVESTMENT_COMPANY_NAV_STATEMENT"
                concept = INVESTMENT_COMPANY_CONCEPT
            else:
                raise ValueError("NO_ENTITY_COMMON_STOCK_SHARES_OUTSTANDING")
        except ValueError as error:
            rejected.append(
                {
                    "ticker": ticker,
                    "cik": int(artifact["cik"]),
                    "accession": str(artifact["accession"]),
                    "reason": str(error),
                }
            )
            continue
        cik = int(artifact["cik"])
        rows.append(
            {
                "stable_security_id": f"CIK-{cik:010d}",
                "ticker": ticker,
                "cik": cik,
                "accession": str(artifact["accession"]),
                "accession_compact": str(artifact["accession_compact"]),
                "form": str(artifact["form"]),
                "filing_period": str(artifact["report_date"]),
                "available_at": conservative_available_at(str(artifact["filing_date"])),
                "availability_precision": "FILED_DATE_END_OF_DAY_CONSERVATIVE",
                "concept": concept,
                "period_start": None,
                "period_end": instant,
                "shares_outstanding": float(total),
                "aggregation_method": method,
                "source_url": str(artifact["url"]),
                "source_sha256": actual_hash,
            }
        )
    rows.sort(
        key=lambda row: (
            row["ticker"],
            row["available_at"],
            row["period_end"],
            row["accession"],
        )
    )
    return rows, rejected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    parser.add_argument("--cohort-queue", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(args.acquisition_manifest.read_text(encoding="utf-8"))
    cohort_bounds = load_cohort_bounds(args.cohort_queue)
    rows, rejected = build_rows(
        manifest,
        cohort_bounds=cohort_bounds,
    )
    values_by_key: dict[tuple[Any, ...], set[float]] = defaultdict(set)
    for row in rows:
        key = (
            row["cik"],
            row["accession_compact"],
            row["concept"],
            row["period_end"],
        )
        values_by_key[key].add(float(row["shares_outstanding"]))
    conflict_count = sum(len(values) > 1 for values in values_by_key.values())
    acquired_symbols = {str(entity["ticker"]).upper() for entity in manifest["entities"]}
    symbols_with_shares = {str(row["ticker"]) for row in rows}
    first_available_by_symbol = {
        ticker: min(str(row["available_at"]) for row in rows if str(row["ticker"]) == ticker)
        for ticker in symbols_with_shares
    }
    history_start_gaps = {
        ticker: {
            "cohort_start_date": cohort_bounds[ticker][0],
            "first_shares_available_at": first_available_by_symbol.get(ticker),
        }
        for ticker in sorted(acquired_symbols)
        if ticker in cohort_bounds
        and (
            first_available_by_symbol.get(ticker) is None
            or first_available_by_symbol[ticker][:10] > cohort_bounds[ticker][0]
        )
    }

    shares_path = args.output / "sec_filing_shares_facts.parquet"
    atomic_parquet(rows, shares_path)
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "source": "SEC EDGAR primary filing inline XBRL",
        "source_access": manifest["access"],
        "acquired_symbol_count": len(acquired_symbols),
        "shares_fact_count": len(rows),
        "symbols_with_shares_facts": len(symbols_with_shares),
        "shares_missing_symbols": sorted(acquired_symbols - symbols_with_shares),
        "filing_rejections": rejected,
        "shares_conflict_key_count": conflict_count,
        "shares_source_gate_pass": symbols_with_shares == acquired_symbols,
        "history_start_gaps": history_start_gaps,
        "history_start_gate_pass": not history_start_gaps,
        "availability_policy": "FILED_DATE_END_OF_DAY_CONSERVATIVE",
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY",
        "output": {
            "path": str(shares_path),
            "sha256": file_sha256(shares_path),
        },
    }
    atomic_write(
        args.output / "sec_filing_shares_summary.json",
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if conflict_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
