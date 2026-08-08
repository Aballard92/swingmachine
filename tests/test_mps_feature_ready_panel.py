from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


def load_module():
    script = Path(__file__).parents[1] / "scripts" / "build_mps_feature_ready_panel.py"
    spec = importlib.util.spec_from_file_location("build_mps_feature_ready_panel", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def eligibility_rows(ticker: str = "AAA") -> pd.DataFrame:
    rows = []
    for session, close, dividend, split in (
        ("2025-01-02", 100.0, 0.0, 1.0),
        ("2025-01-03", 51.0, 1.0, 2.0),
        ("2025-01-06", 52.0, 0.0, 1.0),
    ):
        rows.append(
            {
                "security_id": f"SEC-{ticker}",
                "ticker": ticker,
                "trading_date": session,
                "available_at": f"{session}T21:00:00Z",
                "open": close,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000_000.0,
                "div_cash": dividend,
                "split_factor": split,
                "shares_data_available": True,
                "shares_data_reason": "AVAILABLE",
                "shares_outstanding": 10_000_000.0,
                "market_cap": close * 10_000_000.0,
            }
        )
    return pd.DataFrame(rows)


def queue_document(ticker: str = "AAA") -> dict:
    return {
        "selected": [
            {
                "security_id": f"SEC-{ticker}",
                "ticker": ticker,
                "name": "AAA Corporation",
                "exchange": "NYSE",
                "alpha_delisting_date": "2025-01-06",
                "request_start_date": "2025-01-02",
                "request_end_date": "2025-01-06",
            }
        ]
    }


def tiingo_manifest(ticker: str = "AAA") -> dict:
    return {
        "source_files": [
            {
                "security_id": f"SEC-{ticker}",
                "ticker": ticker,
            }
        ]
    }


def classifications(status: str, ticker: str = "AAA") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": ticker,
                "expected_exchange": "NYSE",
                "classification_status": status,
            }
        ]
    )


def test_causal_total_return_uses_same_day_dividend_and_split() -> None:
    module = load_module()

    result = module.causal_total_return_index(eligibility_rows())

    assert result.iloc[0] == 100.0
    assert result.iloc[1] == pytest.approx(104.0)
    assert result.iloc[2] == pytest.approx(104.0 * 52.0 / 51.0)


def test_feature_input_metadata_fails_closed_at_terminal_session() -> None:
    module = load_module()

    panel = module.build_feature_input_panel(
        eligibility_rows(),
        queue_document(),
        tiingo_manifest(),
        classifications("PROVEN_UNIQUE_COMMON_STOCK"),
    )
    evidence = module.validate_feature_input_panel(panel)

    assert panel["security_type"].eq("common_stock").all()
    assert panel["primary_exchange"].eq("NYSE").all()
    assert panel["country_of_primary_listing"].eq("US").all()
    assert panel["sector"].eq("UNKNOWN").all()
    assert panel["is_tradable"].tolist() == [True, True, False]
    assert panel["is_delisted"].tolist() == [False, False, True]
    assert evidence["classification_eligible_symbol_count"] == 1
    assert evidence["terminal_masked_row_count"] == 1


def test_feature_input_uses_row_aligned_point_in_time_reference_metadata() -> None:
    module = load_module()
    reference = eligibility_rows()[["security_id", "ticker", "trading_date"]].copy()
    reference["sector"] = [
        "UNKNOWN",
        "SIC_D_MANUFACTURING",
        "SIC_D_MANUFACTURING",
    ]
    reference["sector_reference_available"] = [False, True, True]
    reference["sector_reference_status"] = [
        "UNAVAILABLE_NO_PRIOR_SEC_SIC",
        "POINT_IN_TIME_SEC_SIC_AVAILABLE",
        "POINT_IN_TIME_SEC_SIC_AVAILABLE",
    ]
    reference["reference_available_at"] = pd.to_datetime(
        [None, "2025-01-02T21:30:00Z", "2025-01-02T21:30:00Z"],
        utc=True,
    )
    reference["reference_accession"] = [pd.NA, "A", "A"]
    reference["reference_form"] = [pd.NA, "10-Q", "10-Q"]
    reference["reference_period"] = [pd.NA, "2024-09-30", "2024-09-30"]
    reference["reference_filing_ticker"] = [pd.NA, "AAA", "AAA"]
    reference["reference_evidence_kind"] = [
        pd.NA,
        "HASH_PINNED_SEC_SUBMISSIONS_ARCHIVE",
        "HASH_PINNED_SEC_SUBMISSIONS_ARCHIVE",
    ]
    reference["reference_evidence_url"] = [pd.NA, pd.NA, pd.NA]
    reference["sic"] = pd.Series([pd.NA, 2834, 2834], dtype="Int64")

    panel = module.build_feature_input_panel(
        eligibility_rows(),
        queue_document(),
        tiingo_manifest(),
        classifications("PROVEN_HISTORICAL_COMMON_STOCK"),
        reference,
    )
    evidence = module.validate_feature_input_panel(panel)

    assert list(panel["sector"]) == [
        "UNKNOWN",
        "SIC_D_MANUFACTURING",
        "SIC_D_MANUFACTURING",
    ]
    assert evidence["common_unknown_sector_row_count"] == 1
    assert evidence["common_reference_unavailable_row_count"] == 1
    assert evidence["reference_available_row_counts_by_evidence_kind"] == {
        "HASH_PINNED_SEC_SUBMISSIONS_ARCHIVE": 2
    }
    assert evidence["reference_metadata_policy"] == "SEC_FILING_ACCEPTANCE_TIME_FORWARD_ONLY"


@pytest.mark.parametrize(
    "status",
    ["AMBIGUOUS_IDENTITY", "NO_IDENTIFIER", "PROVEN_NON_COMMON"],
)
def test_unproven_or_non_common_classification_is_never_tradable(
    status: str,
) -> None:
    module = load_module()

    panel = module.build_feature_input_panel(
        eligibility_rows(),
        queue_document(),
        tiingo_manifest(),
        classifications(status),
    )

    assert not panel["classification_eligible"].any()
    assert not panel["is_tradable"].any()
    assert panel["security_type"].ne("common_stock").all()


def test_provider_crosscheck_reports_but_does_not_hide_mismatch() -> None:
    module = load_module()
    panel = module.build_feature_input_panel(
        eligibility_rows(),
        queue_document(),
        tiingo_manifest(),
        classifications("PROVEN_UNIQUE_COMMON_STOCK"),
    )
    provider = panel[
        ["security_id", "ticker", "trading_date", "total_return_adjusted_close"]
    ].rename(columns={"total_return_adjusted_close": "provider_adjusted_close"})
    provider.loc[2, "provider_adjusted_close"] *= 1.01

    result = module.provider_return_crosscheck(panel, provider)

    assert not result["crosscheck_gate_pass"]
    assert result["mismatch_count"] == 1
    assert result["mismatch_symbols"] == ["AAA"]
    assert result["mismatch_rows"][0]["trading_date"] == "2025-01-06"


def test_provider_crosscheck_explains_half_cent_raw_close_precision() -> None:
    module = load_module()
    panel = pd.DataFrame(
        {
            "security_id": ["SEC-AAA"] * 4,
            "ticker": ["AAA"] * 4,
            "trading_date": [
                "2025-01-02",
                "2025-01-03",
                "2025-01-06",
                "2025-01-07",
            ],
            "session_date": pd.to_datetime(
                ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"]
            ),
            "close": [10.0, 9.0, 10.0, 11.0],
            "div_cash": [0.0] * 4,
            "split_factor": [1.0] * 4,
        }
    )
    panel["total_return_adjusted_close"] = module.causal_total_return_index(panel)
    provider = panel[["security_id", "ticker", "trading_date", "close"]].rename(
        columns={"close": "provider_adjusted_close"}
    )
    provider.loc[1, "provider_adjusted_close"] = 9.005

    result = module.provider_return_crosscheck(panel, provider)

    assert result["mismatch_count"] == 2
    assert result["precision_explained_mismatch_count"] == 2
    assert result["unexplained_mismatch_count"] == 0
    assert result["crosscheck_gate_pass"]
    assert len(result["precision_rows"]) == 1
    assert result["precision_rows"][0]["trading_date"] == "2025-01-03"


def test_validation_rejects_shares_value_on_unavailable_row() -> None:
    module = load_module()
    panel = module.build_feature_input_panel(
        eligibility_rows(),
        queue_document(),
        tiingo_manifest(),
        classifications("PROVEN_UNIQUE_COMMON_STOCK"),
    )
    panel.loc[0, "shares_data_available"] = False

    with pytest.raises(ValueError, match="unavailable shares rows contain shares values"):
        module.validate_feature_input_panel(panel)
