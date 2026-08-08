from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd


def load_module():
    script = Path(__file__).parents[1] / "scripts" / "build_mps_sec_reference_panel.py"
    spec = importlib.util.spec_from_file_location("build_mps_sec_reference_panel", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sector_from_sic_uses_top_level_divisions() -> None:
    module = load_module()

    assert module.sector_from_sic("2834") == "SIC_D_MANUFACTURING"
    assert module.sector_from_sic(6021) == "SIC_H_FINANCE_INSURANCE_REAL_ESTATE"
    assert module.sector_from_sic("9995") == "SIC_K_NONCLASSIFIABLE"
    assert module.sector_from_sic("") == "UNKNOWN"


def test_acceptance_timestamp_is_interpreted_as_new_york_time() -> None:
    module = load_module()

    assert module.accepted_at_utc("2025-07-01 16:30:00").isoformat() == "2025-07-01T20:30:00+00:00"
    assert module.accepted_at_utc("2025-01-02 16:30:00").isoformat() == "2025-01-02T21:30:00+00:00"


def test_reference_panel_applies_sic_only_after_public_acceptance() -> None:
    module = load_module()
    eligibility = pd.DataFrame(
        {
            "security_id": ["SEC-AAA"] * 3,
            "ticker": ["AAA"] * 3,
            "trading_date": ["2025-01-02", "2025-01-03", "2025-01-06"],
            "available_at": [
                "2025-01-02T21:00:00Z",
                "2025-01-03T21:00:00Z",
                "2025-01-06T21:00:00Z",
            ],
        }
    )
    classifications = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "classification_status": ["PROVEN_HISTORICAL_COMMON_STOCK"],
        }
    )
    events = pd.DataFrame(
        {
            "ticker": ["AAA", "AAA"],
            "accepted_cik": [1, 1],
            "sic": [2834, 7372],
            "sector": ["SIC_D_MANUFACTURING", "SIC_I_SERVICES"],
            "reference_available_at": pd.to_datetime(
                ["2025-01-02T21:30:00Z", "2025-01-06T20:00:00Z"],
                utc=True,
            ),
            "reference_accession": ["A", "B"],
            "reference_form": ["10-Q", "10-Q"],
            "reference_period": ["2024-09-30", "2024-12-31"],
            "reference_filing_ticker": ["AAA", "AAA"],
        }
    )

    panel = module.build_reference_panel(eligibility, classifications, events)

    assert list(panel["sector"]) == [
        "UNKNOWN",
        "SIC_D_MANUFACTURING",
        "SIC_I_SERVICES",
    ]
    assert list(panel["sector_reference_available"]) == [False, True, True]


def test_reference_panel_stays_unknown_without_events() -> None:
    module = load_module()
    eligibility = pd.DataFrame(
        {
            "security_id": ["SEC-AAA"],
            "ticker": ["AAA"],
            "trading_date": ["2025-01-02"],
            "available_at": ["2025-01-02T21:00:00Z"],
        }
    )
    classifications = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "classification_status": ["PROVEN_HISTORICAL_COMMON_STOCK"],
        }
    )

    panel = module.build_reference_panel(
        eligibility,
        classifications,
        pd.DataFrame(columns=["ticker"]),
    )

    assert panel.loc[0, "sector"] == "UNKNOWN"
    assert not panel.loc[0, "sector_reference_available"]


def test_supplemental_event_requires_matching_common_classification(
    tmp_path: Path,
) -> None:
    module = load_module()
    path = tmp_path / "events.json"
    path.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "ticker": "AAA",
                        "accepted_cik": 1,
                        "sic": 2834,
                        "accepted": "2025-01-02 16:30:00",
                        "accession": "0000000001-25-000001",
                        "form": "10-Q",
                        "period": "2024-09-30",
                        "filing_ticker": "AAA",
                        "evidence_kind": ("MANUALLY_REVIEWED_SEC_STATIC_FILING_HEADER"),
                        "evidence_url": (
                            "https://www.sec.gov/Archives/edgar/data/1/"
                            "000000000125000001/"
                            "0000000001-25-000001-index.htm"
                        ),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    classifications = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "accepted_cik": [1],
            "classification_status": ["PROVEN_HISTORICAL_COMMON_STOCK"],
        }
    )

    events = module.read_supplemental_events(
        path,
        classifications=classifications,
    )

    assert events.loc[0, "sector"] == "SIC_D_MANUFACTURING"
    assert events.loc[0, "reference_available_at"].isoformat() == "2025-01-02T21:30:00+00:00"
    assert events.loc[0, "reference_evidence_kind"] == "MANUALLY_REVIEWED_SEC_STATIC_FILING_HEADER"


def test_supplemental_event_rejects_wrong_cik(tmp_path: Path) -> None:
    module = load_module()
    path = tmp_path / "events.json"
    path.write_text(
        json.dumps(
            {
                "events": [
                    {
                        "ticker": "AAA",
                        "accepted_cik": 2,
                        "sic": 2834,
                        "accepted": "2025-01-02 16:30:00",
                        "accession": "0000000002-25-000001",
                        "form": "10-Q",
                        "period": "",
                        "filing_ticker": "AAA",
                        "evidence_kind": ("MANUALLY_REVIEWED_SEC_STATIC_FILING_HEADER"),
                        "evidence_url": (
                            "https://www.sec.gov/Archives/edgar/data/2/"
                            "000000000225000001/"
                            "0000000002-25-000001-index.htm"
                        ),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    classifications = pd.DataFrame(
        {
            "ticker": ["AAA"],
            "accepted_cik": [1],
            "classification_status": ["PROVEN_HISTORICAL_COMMON_STOCK"],
        }
    )

    with pd.option_context("mode.chained_assignment", None):
        try:
            module.read_supplemental_events(
                path,
                classifications=classifications,
            )
        except ValueError as error:
            assert "does not match common classification" in str(error)
        else:
            raise AssertionError("wrong CIK was accepted")
