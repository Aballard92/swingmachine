#!/usr/bin/env python3
"""Acquire bounded OCC corporate-action memos through an anonymous text transport."""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from swingmachine.mps_public_data import normalized_issuer_name

MEMO_LINK = re.compile(r"\[([^\]]+)\]\(https://infomemo\.theocc\.com/infomemos\?number=(\d+)\)")
CASH_PER_SHARE = (
    re.compile(
        r"right\s+to\s+receive\s+\$([0-9][0-9,]*(?:\.[0-9]+)?)\s+net\s+cash\s+per\s+share",
        re.I,
    ),
    re.compile(
        r"right\s+to\s+receive\s+\$([0-9][0-9,]*(?:\.[0-9]+)?)\s+in\s+cash\s+per\s+share",
        re.I,
    ),
    re.compile(
        r"cash\s+consideration\s+of\s+\$([0-9][0-9,]*(?:\.[0-9]+)?)\s+per\s+share",
        re.I,
    ),
    re.compile(
        r"right\s+to\s+receive\s+\$([0-9][0-9,]*(?:\.[0-9]+)?)\s+cash\b",
        re.I,
    ),
    re.compile(
        r"cash\s+consideration\s+of\s+\$([0-9][0-9,]*(?:\.[0-9]+)?)\s+per\s+(?:common\s+)?(?:share|ads)",
        re.I,
    ),
    re.compile(
        r"final\s+cash\s+consideration\s+is\s+\$([0-9][0-9,]*(?:\.[0-9]+)?)\s+per\s+(?:[A-Z0-9-]+\s+)?(?:common\s+)?(?:share|ads)",
        re.I,
    ),
    re.compile(
        r"right\s+to\s+receive\s+\$([0-9][0-9,]*(?:\.[0-9]+)?)\s+net\s+cash\s+per\s+(?:share|ads)",
        re.I,
    ),
)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def retrieve(url: str, *, no_cache: bool = False) -> bytes:
    headers = {"User-Agent": "SwingMachineResearch/1.0"}
    if no_cache:
        headers["X-No-Cache"] = "true"
    request = Request(url, headers=headers)
    last_error: Exception | None = None
    for attempt in range(6):
        try:
            with urlopen(request, timeout=120) as response:
                return response.read()
        except HTTPError as exc:
            last_error = exc
            if exc.code != 429:
                raise
        except URLError as exc:
            last_error = exc
        time.sleep(min(30.0, 2.0 ** (attempt + 1)))
    assert last_error is not None
    raise last_error


def cached_retrieve(path: Path, url: str, *, no_cache: bool = False) -> bytes:
    if path.is_file() and path.stat().st_size > 100:
        return path.read_bytes()
    payload = retrieve(url, no_cache=no_cache)
    atomic_write(path, payload)
    return payload


def parse_memo_links(markdown: str) -> list[tuple[str, str]]:
    return list(dict.fromkeys(MEMO_LINK.findall(markdown)))


def relevant_title(ticker: str, expected_name: str, title: str) -> bool:
    ticker_pattern = re.compile(rf"Option Symbols?:[^\n]*\b{re.escape(ticker)}\b", re.I)
    if ticker_pattern.search(title):
        return True
    expected_tokens = normalized_issuer_name(expected_name).split()
    title_name = normalized_issuer_name(title)
    required_tokens = expected_tokens[:2] if len(expected_tokens) > 1 else expected_tokens
    return bool(required_tokens) and all(token in title_name.split() for token in required_tokens)


def cash_values(markdown: str) -> list[float]:
    values = {
        float(match.replace(",", ""))
        for pattern in CASH_PER_SHARE
        for match in pattern.findall(markdown)
    }
    return sorted(values)


def select_memo_links(links: list[tuple[str, str]], limit: int) -> list[tuple[str, str]]:
    def rank(item: tuple[str, str]) -> tuple[int, int]:
        title, number = item
        upper = title.upper()
        if "CASH SETTLEMENT" in upper and "ANTICIPATED" not in upper:
            priority = 0
        elif "SETTLEMENT UPDATE" in upper:
            priority = 1
        elif "BROKER-TO-BROKER" in upper:
            priority = 2
        elif any(word in upper for word in ("MERGER", "TENDER OFFER", "CONTRACT ADJUSTMENT")):
            priority = 3
        elif "ANTICIPATED CASH SETTLEMENT" in upper:
            priority = 4
        else:
            priority = 5
        return priority, -int(number)

    return sorted(links, key=rank)[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution-seed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--delay-seconds", type=float, default=0.5)
    parser.add_argument("--max-symbols", type=int, default=100)
    parser.add_argument("--max-memos-per-symbol", type=int, default=6)
    args = parser.parse_args()
    if args.delay_seconds < 0.1:
        raise ValueError("delay-seconds must be at least 0.1")
    payload = json.loads(args.resolution_seed.read_text(encoding="utf-8"))
    resolutions = payload if isinstance(payload, list) else payload["resolutions"]
    if len(resolutions) > args.max_symbols:
        raise ValueError("resolution seed exceeds max-symbols")

    memo_cache: dict[str, tuple[bytes, Path]] = {}
    records: list[dict[str, Any]] = []
    for index, resolution in enumerate(resolutions, start=1):
        ticker = str(resolution["ticker"]).upper()
        expected_name = str(resolution["expected_name"])
        company_phrase = normalized_issuer_name(expected_name)
        underlying_search = "https://infomemo.theocc.com/infomemo/search-memo?keyword=" + quote(
            f'"{company_phrase}"'
        )
        transport_search = "https://r.jina.ai/" + underlying_search
        search_path = args.output / "search" / f"{ticker}.md"
        search_was_cached = search_path.is_file() and search_path.stat().st_size > 100
        search_payload = cached_retrieve(search_path, transport_search, no_cache=True)
        if not search_was_cached:
            time.sleep(args.delay_seconds)
        markdown = search_payload.decode("utf-8", errors="replace")
        links = select_memo_links(
            [
                (title, number)
                for title, number in parse_memo_links(markdown)
                if relevant_title(ticker, expected_name, title)
            ],
            args.max_memos_per_symbol,
        )
        memo_records = []
        for title, number in links:
            if number not in memo_cache:
                underlying_url = f"https://infomemo.theocc.com/infomemos?number={number}"
                transport_url = "https://r.jina.ai/" + underlying_url
                memo_path = args.output / "memos" / f"{number}.md"
                memo_was_cached = memo_path.is_file() and memo_path.stat().st_size > 100
                memo_payload = cached_retrieve(memo_path, transport_url)
                memo_cache[number] = (memo_payload, memo_path)
                if not memo_was_cached:
                    time.sleep(args.delay_seconds)
            memo_payload, memo_path = memo_cache[number]
            memo_markdown = memo_payload.decode("utf-8", errors="replace")
            memo_records.append(
                {
                    "memo_number": int(number),
                    "title": title,
                    "underlying_url": (f"https://infomemo.theocc.com/infomemos?number={number}"),
                    "transport_url": (
                        f"https://r.jina.ai/https://infomemo.theocc.com/infomemos?number={number}"
                    ),
                    "path": str(memo_path),
                    "bytes": len(memo_payload),
                    "sha256": sha256(memo_payload).hexdigest(),
                    "cash_per_share_candidates": cash_values(memo_markdown),
                    "is_anticipated": "ANTICIPATED" in title.upper(),
                    "is_final_cash_settlement": (
                        "CASH SETTLEMENT" in title.upper() and "ANTICIPATED" not in title.upper()
                    ),
                }
            )
        records.append(
            {
                "ticker": ticker,
                "expected_name": expected_name,
                "retrieved_at": datetime.now(UTC).isoformat(),
                "search_underlying_url": underlying_search,
                "search_transport_url": transport_search,
                "search_path": str(search_path),
                "search_sha256": sha256(search_payload).hexdigest(),
                "relevant_memos": memo_records,
            }
        )
        print(f"{index:02d}/{len(resolutions)} {ticker} memos={len(memo_records)}", flush=True)

    manifest_path = args.output / "acquisition_manifest.jsonl"
    atomic_write(
        manifest_path,
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records).encode(),
    )
    final_cash = {
        record["ticker"]
        for record in records
        if any(
            memo["is_final_cash_settlement"] and memo["cash_per_share_candidates"]
            for memo in record["relevant_memos"]
        )
    }
    with_memos = {record["ticker"] for record in records if record["relevant_memos"]}
    summary = {
        "task_id": "SWING-MPS-DATA-001",
        "source": "Options Clearing Corporation information memos",
        "transport": "Jina AI anonymous text mirror",
        "cohort_symbol_count": len(records),
        "symbols_with_relevant_memos": len(with_memos),
        "symbols_with_final_cash_settlement_value": len(final_cash),
        "final_cash_settlement_symbols": sorted(final_cash),
        "qualification_usable": False,
        "decision": "PARTIAL_RESEARCH_ONLY_REQUIRES_PRIMARY_SOURCE_CROSS_CHECK",
        "source_warning": (
            "OCC labels each memo an unofficial summary and recommends independent verification."
        ),
        "manifest": {
            "path": str(manifest_path),
            "sha256": sha256(manifest_path.read_bytes()).hexdigest(),
        },
    }
    atomic_write(
        args.output / "acquisition_summary.json",
        (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
