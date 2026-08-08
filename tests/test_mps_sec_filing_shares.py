from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path


def load_script(name: str):
    script = Path(__file__).parents[1] / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inline_document(*facts: str) -> bytes:
    return f"""
    <html>
      <xbrli:context id="class-a">
        <xbrli:entity>
          <xbrli:segment>
            <xbrldi:explicitMember>us-gaap:CommonClassAMember</xbrldi:explicitMember>
          </xbrli:segment>
        </xbrli:entity>
        <xbrli:period><xbrli:instant>2025-04-30</xbrli:instant></xbrli:period>
      </xbrli:context>
      <xbrli:context id="class-b">
        <xbrli:entity>
          <xbrli:segment>
            <xbrldi:explicitMember>us-gaap:CommonClassBMember</xbrldi:explicitMember>
          </xbrli:segment>
        </xbrli:entity>
        <xbrli:period><xbrli:instant>2025-04-30</xbrli:instant></xbrli:period>
      </xbrli:context>
      {"".join(facts)}
    </html>
    """.encode()


def test_class_level_entity_shares_are_summed() -> None:
    module = load_script("build_mps_sec_filing_shares_reference.py")
    payload = inline_document(
        """
        <ix:nonFraction unitRef="shares" contextRef="class-a"
          name="dei:EntityCommonStockSharesOutstanding"
          format="ixt:num-dot-decimal" scale="0">143,854,293</ix:nonFraction>
        """,
        """
        <ix:nonFraction unitRef="shares" contextRef="class-b"
          name="dei:EntityCommonStockSharesOutstanding"
          format="ixt:fixed-zero" scale="0">no</ix:nonFraction>
        """,
    )

    facts = module.extract_facts(payload)
    instant, value, method = module.aggregate_filing_facts(
        facts,
        filing_date="2025-05-07",
    )

    assert instant == "2025-04-30"
    assert value == Decimal("143854293")
    assert method == "SUM_DISTINCT_CLASS_CONTEXTS"


def test_conflicting_duplicate_class_facts_fail_closed() -> None:
    module = load_script("build_mps_sec_filing_shares_reference.py")
    payload = inline_document(
        """
        <ix:nonFraction unitRef="shares" contextRef="class-a"
          name="dei:EntityCommonStockSharesOutstanding"
          format="ixt:num-dot-decimal">100</ix:nonFraction>
        """,
        """
        <ix:nonFraction unitRef="shares" contextRef="class-a"
          name="dei:EntityCommonStockSharesOutstanding"
          format="ixt:num-dot-decimal">101</ix:nonFraction>
        """,
    )

    facts = module.extract_facts(payload)

    try:
        module.aggregate_filing_facts(facts, filing_date="2025-05-07")
    except ValueError as error:
        assert "conflicting shares values" in str(error)
    else:
        raise AssertionError("conflicting class facts were accepted")


def test_sec_client_requires_identified_contact() -> None:
    module = load_script("acquire_mps_sec_filing_shares.py")

    try:
        module.SecClient("SwingMachineResearch/1.0", request_interval_seconds=0.25)
    except ValueError as error:
        assert "contact email" in str(error)
    else:
        raise AssertionError("unidentified SEC user agent was accepted")


def test_investment_company_nav_statement_shares_are_exact() -> None:
    module = load_script("build_mps_sec_filing_shares_reference.py")
    payload = b"""
    <html><body>
      <div>Net assets</div><div>$</div><div>48,026,732</div>
      <div>Shares outstanding</div><div>10,000,141</div>
      <div>Net asset value per outstanding share</div><div>$</div><div>4.80</div>
    </body></html>
    """

    assert module.extract_investment_company_shares(payload) == Decimal("10000141")


def test_pre_cohort_filing_is_rejected_before_value_can_bleed_forward() -> None:
    module = load_script("build_mps_sec_filing_shares_reference.py")
    manifest = {
        "access": "ANONYMOUS_NO_ACCOUNT_NO_API_KEY",
        "artifacts": [
            {
                "ticker": "VMEO",
                "cik": 1837686,
                "accession": "0001837686-21-000004",
                "filing_date": "2021-05-10",
            }
        ],
    }

    rows, rejected = module.build_rows(
        manifest,
        cohort_bounds={"VMEO": ("2021-05-25", "2025-11-24")},
    )

    assert rows == []
    assert rejected[0]["reason"] == "PRE_COHORT_AVAILABILITY"


def test_acquisition_cik_override_preserves_seed_cik() -> None:
    module = load_script("acquire_mps_sec_filing_shares.py")
    override = module.parse_cik_overrides(["STLE=779227"])

    assert override == {"STLE": 779227}
