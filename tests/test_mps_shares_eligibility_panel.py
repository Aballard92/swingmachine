from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


def load_module():
    script = Path(__file__).parents[1] / "scripts" / "build_mps_shares_eligibility_panel.py"
    spec = importlib.util.spec_from_file_location("build_mps_shares_eligibility_panel", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def price(ticker: str, session: str, close: float) -> dict:
    return {
        "security_id": f"PRICE-{ticker}",
        "ticker": ticker,
        "trading_date": session,
        "available_at": f"{session}T21:00:00Z",
        "close": close,
    }


def shares(
    ticker: str,
    *,
    available_at: str,
    period_end: str,
    value: float,
    accession: str = "0000000001-25-000001",
    source_available_at: str | None = None,
    concept: str = "EntityCommonStockSharesOutstanding",
) -> dict:
    return {
        "stable_security_id": f"CIK-{ticker}",
        "ticker": ticker,
        "cik": 1,
        "accession_compact": accession,
        "source_available_at": source_available_at or available_at,
        "available_at": available_at,
        "concept": concept,
        "period_end": period_end,
        "shares_outstanding": value,
        "source_kind": "TEST",
        "source_priority": 1,
        "source_sha256": "a" * 64,
    }


def split(ticker: str, session: str, factor: float) -> dict:
    return {
        "ticker": ticker,
        "trading_date": session,
        "available_at": f"{session}T21:00:00Z",
        "split_factor": factor,
    }


def test_conservative_fact_is_not_available_before_end_of_filing_day() -> None:
    module = load_module()
    prices = pd.DataFrame([price("AAA", "2025-01-02", 10.0), price("AAA", "2025-01-03", 11.0)])
    facts = pd.DataFrame(
        [
            shares(
                "AAA",
                available_at="2025-01-02T23:59:59.999999Z",
                period_end="2024-12-31",
                value=100.0,
            )
        ]
    )

    panel, evidence = module.build_eligibility_panel(
        prices, facts, pd.DataFrame(columns=sorted(module.ACTION_REQUIRED_COLUMNS))
    )

    assert not bool(panel.iloc[0]["shares_data_available"])
    assert panel.iloc[0]["shares_data_reason"] == "NO_PRIOR_POINT_IN_TIME_FACT"
    assert bool(panel.iloc[1]["shares_data_available"])
    assert panel.iloc[1]["shares_outstanding"] == 100.0
    assert evidence["shares_unavailable_row_count"] == 1


def test_missing_symbol_is_explicitly_ineligible() -> None:
    module = load_module()
    prices = pd.DataFrame([price("STLE", "2025-08-01", 25.0)])
    facts = pd.DataFrame(
        [
            shares(
                "AAA",
                available_at="2025-01-01T23:59:59.999999Z",
                period_end="2024-12-31",
                value=100.0,
            )
        ]
    )

    panel, evidence = module.build_eligibility_panel(
        prices, facts, pd.DataFrame(columns=sorted(module.ACTION_REQUIRED_COLUMNS))
    )

    assert not bool(panel.iloc[0]["shares_data_available"])
    assert panel.iloc[0]["shares_data_reason"] == "NO_SHARES_FACTS_FOR_SYMBOL"
    assert pd.isna(panel.iloc[0]["market_cap"])
    assert evidence["symbols_without_eligible_rows"] == ["STLE"]


def test_reverse_split_adjusts_carried_fact_and_preserves_market_cap() -> None:
    module = load_module()
    prices = pd.DataFrame([price("TURN", "2021-01-03", 3.0), price("TURN", "2021-01-04", 9.0)])
    facts = pd.DataFrame(
        [
            shares(
                "TURN",
                available_at="2021-01-01T23:59:59.999999Z",
                period_end="2020-12-31",
                value=300.0,
            )
        ]
    )
    actions = pd.DataFrame([split("TURN", "2021-01-04", 1.0 / 3.0)])

    panel, evidence = module.build_eligibility_panel(prices, facts, actions)

    assert panel.iloc[0]["shares_outstanding"] == pytest.approx(300.0)
    assert panel.iloc[1]["shares_outstanding"] == pytest.approx(100.0)
    assert panel.iloc[1]["shares_split_adjustment_factor"] == pytest.approx(1.0 / 3.0)
    assert panel.iloc[0]["market_cap"] == pytest.approx(panel.iloc[1]["market_cap"])
    assert evidence["split_adjusted_row_count"] == 1


def test_post_split_fact_resets_adjustment_factor() -> None:
    module = load_module()
    prices = pd.DataFrame([price("TURN", "2021-01-04", 9.0), price("TURN", "2021-01-07", 10.0)])
    facts = pd.DataFrame(
        [
            shares(
                "TURN",
                available_at="2021-01-01T23:59:59.999999Z",
                period_end="2020-12-31",
                value=300.0,
            ),
            shares(
                "TURN",
                available_at="2021-01-06T23:59:59.999999Z",
                period_end="2021-01-05",
                value=101.0,
                accession="0000000001-25-000002",
            ),
        ]
    )
    actions = pd.DataFrame([split("TURN", "2021-01-04", 1.0 / 3.0)])

    panel, _ = module.build_eligibility_panel(prices, facts, actions)

    assert panel.iloc[0]["shares_outstanding"] == pytest.approx(100.0)
    assert panel.iloc[1]["shares_outstanding"] == pytest.approx(101.0)
    assert panel.iloc[1]["shares_split_adjustment_factor"] == pytest.approx(1.0)


def test_entity_concept_and_later_amendment_win_deterministically() -> None:
    module = load_module()
    available = "2025-02-27T23:59:59.999999Z"
    facts = pd.DataFrame(
        [
            shares(
                "AAA",
                available_at=available,
                source_available_at="2025-02-27T08:00:00Z",
                period_end="2025-02-21",
                value=120.0,
                concept="CommonStockSharesOutstanding",
            ),
            shares(
                "AAA",
                available_at=available,
                source_available_at="2025-02-27T08:00:00Z",
                period_end="2025-02-21",
                value=100.0,
                accession="0000000001-25-000002",
            ),
            shares(
                "AAA",
                available_at=available,
                source_available_at="2025-02-27T21:00:00Z",
                period_end="2025-02-21",
                value=101.0,
                accession="0000000001-25-000003",
            ),
        ]
    )

    effective, _ = module.resolve_effective_shares(facts)

    assert len(effective) == 1
    assert effective.iloc[0]["shares_outstanding_raw"] == 101.0
    assert effective.iloc[0]["shares_concept"] == "EntityCommonStockSharesOutstanding"


def test_invalid_fact_is_excluded_and_symbol_stays_masked() -> None:
    module = load_module()
    prices = pd.DataFrame([price("AAA", "2025-01-03", 10.0)])
    facts = pd.DataFrame(
        [
            shares(
                "AAA",
                available_at="2025-01-02T23:59:59.999999Z",
                period_end="2024-12-31",
                value=0.0,
            )
        ]
    )

    panel, evidence = module.build_eligibility_panel(
        prices, facts, pd.DataFrame(columns=sorted(module.ACTION_REQUIRED_COLUMNS))
    )

    assert evidence["invalid_fact_count"] == 1
    assert evidence["effective_fact_count"] == 0
    assert not bool(panel.iloc[0]["shares_data_available"])
    assert panel.iloc[0]["shares_data_reason"] == "NO_SHARES_FACTS_FOR_SYMBOL"


def test_unresolved_effective_fact_conflict_fails_closed() -> None:
    module = load_module()
    available = "2025-02-27T23:59:59.999999Z"
    facts = pd.DataFrame(
        [
            shares(
                "AAA",
                available_at=available,
                period_end="2025-02-21",
                value=100.0,
            ),
            shares(
                "AAA",
                available_at=available,
                period_end="2025-02-21",
                value=101.0,
            ),
        ]
    )

    with pytest.raises(ValueError, match="unresolved effective shares conflicts"):
        module.resolve_effective_shares(facts)
