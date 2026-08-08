from __future__ import annotations

import importlib.util
from pathlib import Path


def load_module():
    script = Path(__file__).parents[1] / "scripts" / "build_mps_sec_shares_union.py"
    spec = importlib.util.spec_from_file_location("build_mps_sec_shares_union", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(ticker: str, cik: int, accession: str, value: float) -> dict:
    return {
        "stable_security_id": f"CIK-{cik:010d}",
        "ticker": ticker,
        "cik": cik,
        "accession_compact": accession,
        "form": "10-Q",
        "filing_period": "2025Q1",
        "available_at": "2025-05-01 16:00:00",
        "concept": "EntityCommonStockSharesOutstanding",
        "period_start": None,
        "period_end": "2025-04-28",
        "shares_outstanding": value,
    }


def test_primary_wins_and_fallback_only_fills_missing_symbols() -> None:
    module = load_module()
    primary = [row("AAA", 1, "000000000125000001", 100)]
    fallback = [
        row("AAA", 1, "0000000001-25-000001", 100),
        row("BBB", 2, "0000000002-25-000001", 200),
    ]

    rows, evidence = module.reconcile_rows(
        primary,
        fallback,
        primary_sha256="a" * 64,
        fallback_sha256="b" * 64,
    )

    assert [item["ticker"] for item in rows] == ["AAA", "BBB"]
    assert rows[0]["source_priority"] == 1
    assert rows[1]["source_priority"] == 2
    assert evidence["fallback_fill_symbols"] == ["BBB"]
    assert evidence["overlap_exact_key_count"] == 1
    assert evidence["overlap_value_conflict_count"] == 0


def test_overlap_value_conflict_is_reported() -> None:
    module = load_module()
    primary = [row("AAA", 1, "000000000125000001", 100)]
    fallback = [row("AAA", 1, "0000000001-25-000001", 101)]

    _, evidence = module.reconcile_rows(
        primary,
        fallback,
        primary_sha256="a" * 64,
        fallback_sha256="b" * 64,
    )

    assert evidence["overlap_value_conflict_count"] == 1


def test_filing_fallback_only_fills_after_both_existing_sources() -> None:
    module = load_module()
    primary = [row("AAA", 1, "000000000125000001", 100)]
    fallback = [row("BBB", 2, "0000000002-25-000001", 200)]
    filing = [
        row("BBB", 2, "0000000002-25-000001", 200),
        row("CCC", 3, "0000000003-25-000001", 300),
    ]

    rows, evidence = module.reconcile_rows(
        primary,
        fallback,
        primary_sha256="a" * 64,
        fallback_sha256="b" * 64,
        filing_rows=filing,
        filing_sha256="c" * 64,
    )

    assert [item["ticker"] for item in rows] == ["AAA", "BBB", "CCC"]
    assert rows[-1]["source_kind"] == "SEC_INLINE_XBRL_PRIMARY_FILING"
    assert rows[-1]["source_priority"] == 3
    assert evidence["filing_fallback_fill_symbols"] == ["CCC"]
