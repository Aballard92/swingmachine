from datetime import UTC, datetime

from swingmachine.mps_public_data import (
    extract_sec_shares_facts,
    parse_alpha_vantage_listing_csv,
    parse_sec_submissions,
    parse_sec_ticker_proxy,
)


def test_alpha_listing_lifecycle_preserves_explicit_dates():
    payload = (
        "symbol,name,exchange,assetType,ipoDate,delistingDate,status\n"
        "OLD,Old Inc,NYSE,Stock,2001-01-02,2014-02-03,Delisted\n"
    )
    rows = parse_alpha_vantage_listing_csv(
        payload,
        "test",
    )
    assert rows[0].symbol == "OLD"
    assert rows[0].ipo_date.isoformat() == "2001-01-02"
    assert rows[0].delisting_date.isoformat() == "2014-02-03"


def test_alpha_error_payload_is_not_treated_as_empty_valid_universe():
    assert parse_alpha_vantage_listing_csv("{}", "test") == ()


def test_sec_proxy_wrapper_is_removed_without_changing_mapping():
    payload = (
        "Title: SEC\nMarkdown Content:\n"
        '{"0":{"cik_str":320193,"ticker":"AAPL","title":"Apple Inc."}}'
    )
    assert parse_sec_ticker_proxy(payload)[0].cik == 320193


def test_shares_fact_requires_accession_acceptance_timestamp():
    submissions = {
        "cik": "320193",
        "name": "Apple Inc.",
        "filings": {
            "recent": {"accessionNumber": ["known"], "acceptanceDateTime": ["2024-02-01T16:01:02Z"]}
        },
    }
    issuer = parse_sec_submissions(submissions)
    facts = {
        "facts": {
            "dei": {
                "EntityCommonStockSharesOutstanding": {
                    "units": {
                        "shares": [
                            {
                                "val": 100,
                                "end": "2024-01-26",
                                "filed": "2024-02-01",
                                "form": "10-Q",
                                "accn": "known",
                            },
                            {
                                "val": 101,
                                "end": "2024-01-27",
                                "filed": "2024-02-01",
                                "form": "10-Q",
                                "accn": "unknown",
                            },
                        ]
                    }
                }
            }
        }
    }
    rows = extract_sec_shares_facts(facts, issuer)
    assert len(rows) == 1
    assert rows[0].available_at == datetime(2024, 2, 1, 16, 1, 2, tzinfo=UTC)
