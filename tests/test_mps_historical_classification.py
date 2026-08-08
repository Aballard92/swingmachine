from __future__ import annotations

import importlib.util
import json
from hashlib import sha256
from pathlib import Path


def load_module():
    script = Path(__file__).parents[1] / "scripts" / "build_mps_historical_classification.py"
    spec = importlib.util.spec_from_file_location("build_mps_historical_classification", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_row(ticker: str) -> dict:
    return {
        "ticker": ticker,
        "security_id": f"SEC-{ticker}",
        "first_date": "2020-01-01",
        "last_date": "2025-01-03",
    }


def queue_row(ticker: str, name: str) -> dict:
    return {
        "ticker": ticker,
        "security_id": f"SEC-{ticker}",
        "name": name,
        "exchange": "NYSE",
        "alpha_delisting_date": "2025-01-03",
        "tiingo_end_date": "2025-01-03",
        "selection_reason": "DELISTED_MISSING_PRICE_EXACT_TICKER_AND_END_DATE",
    }


def write_raw(path: Path, ticker: str, candidates: list[dict]) -> str:
    payload = {
        "request": {"idValue": ticker},
        "response": ({"data": candidates} if candidates else {"warning": "No identifier found."}),
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return sha256(path.read_bytes()).hexdigest()


def original_row(ticker: str, status: str, source_sha256: str) -> dict:
    return {
        "ticker": ticker,
        "classification_status": status,
        "source_sha256": source_sha256,
    }


def test_name_normalisation_handles_openfigi_abbreviations() -> None:
    module = load_module()

    score = module.name_similarity(
        "Bridge Investment Group Holdings Inc - Class A",
        "BRIDGE INVESTMENT GRP HDS-A",
    )

    assert score == 1.0


def test_unique_historical_name_selects_common_candidate(tmp_path: Path) -> None:
    module = load_module()
    ticker = "BRDG"
    raw_hash = write_raw(
        tmp_path / f"{ticker}.json",
        ticker,
        [
            {"name": "BRIDGE TECHNOLOGY INC", "securityType2": "Common Stock"},
            {
                "name": "BRIDGE INVESTMENT GRP HDS-A",
                "securityType": "Common Stock",
                "securityType2": "Common Stock",
                "figi": "TARGET",
            },
        ],
    )

    rows, evidence = module.resolve_historical_classifications(
        {
            "selected": [
                queue_row(
                    ticker,
                    "Bridge Investment Group Holdings Inc - Class A",
                )
            ]
        },
        {"source_files": [source_row(ticker)]},
        [original_row(ticker, "AMBIGUOUS_IDENTITY", raw_hash)],
        raw_dir=tmp_path,
        resolution_seed={ticker: {"accepted_cik": 1, "resolution_status": "UNIQUE"}},
        share_concepts={ticker: {"EntityCommonStockSharesOutstanding"}},
    )

    assert rows[0]["classification_status"] == module.COMMON_STATUS
    assert rows[0]["matched_candidate_figi"] == "TARGET"
    assert evidence["classification_resolution_gate_pass"]


def test_ticker_reuse_non_common_conflict_fails_closed(
    tmp_path: Path,
) -> None:
    module = load_module()
    ticker = "BLOX"
    raw_hash = write_raw(
        tmp_path / f"{ticker}.json",
        ticker,
        [
            {
                "name": "NICHOLAS CRYPTO INCOME ETF",
                "securityType": "ETP",
                "securityType2": "Mutual Fund",
            }
        ],
    )

    rows, _ = module.resolve_historical_classifications(
        {"selected": [queue_row(ticker, "Infoblox Inc")]},
        {"source_files": [source_row(ticker)]},
        [original_row(ticker, "PROVEN_NON_COMMON", raw_hash)],
        raw_dir=tmp_path,
        resolution_seed={ticker: {"accepted_cik": 1, "resolution_status": "REVIEWED"}},
        share_concepts={ticker: {"EntityCommonStockSharesOutstanding"}},
    )

    assert rows[0]["classification_status"] == module.UNRESOLVED_STATUS
    assert not rows[0]["classification_eligible"]
    assert rows[0]["resolution_method"] == "OPENFIGI_TICKER_REUSE_NON_COMMON_CONFLICT"


def test_unique_sec_historical_ticker_does_not_require_complete_price_lifecycle(
    tmp_path: Path,
) -> None:
    module = load_module()
    ticker = "NOVA"
    raw_hash = write_raw(tmp_path / f"{ticker}.json", ticker, [])
    queue = queue_row(ticker, "Sunnova Energy International Inc")
    source = source_row(ticker)
    source["last_date"] = "2020-06-25"

    rows, _ = module.resolve_historical_classifications(
        {"selected": [queue]},
        {"source_files": [source]},
        [original_row(ticker, "NO_IDENTIFIER", raw_hash)],
        raw_dir=tmp_path,
        resolution_seed={
            ticker: {
                "accepted_cik": 1772695,
                "resolution_status": "UNIQUE_HISTORICAL_FILING_TICKER",
            }
        },
        share_concepts={ticker: {"EntityCommonStockSharesOutstanding"}},
    )

    assert rows[0]["classification_status"] == module.COMMON_STATUS
    assert rows[0]["resolution_method"] == "SEC_UNIQUE_HISTORICAL_TICKER_PLUS_COMMON_SHARES"


def test_exact_non_common_target_remains_excluded(tmp_path: Path) -> None:
    module = load_module()
    ticker = "TURN"
    raw_hash = write_raw(
        tmp_path / f"{ticker}.json",
        ticker,
        [
            {
                "name": "180 DEGREE CAPITAL CORP",
                "securityType": "Closed-End Fund",
                "securityType2": "Mutual Fund",
            }
        ],
    )

    rows, _ = module.resolve_historical_classifications(
        {"selected": [queue_row(ticker, "180 Degree Capital Corp")]},
        {"source_files": [source_row(ticker)]},
        [original_row(ticker, "PROVEN_NON_COMMON", raw_hash)],
        raw_dir=tmp_path,
        resolution_seed={ticker: {"accepted_cik": 1, "resolution_status": "REVIEWED"}},
        share_concepts={ticker: {"InvestmentCompanySharesOutstanding"}},
    )

    assert rows[0]["classification_status"] == module.NON_COMMON_STATUS
    assert not rows[0]["classification_eligible"]
