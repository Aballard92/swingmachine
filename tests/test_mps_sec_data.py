from swingmachine.mps_public_data import (
    normalized_issuer_name,
    parse_sec_browse_atom_ciks,
    sec_issuer_name_matches,
)


def test_sec_browse_atom_returns_distinct_sorted_ciks():
    payload = """<feed xmlns=\"http://www.w3.org/2005/Atom\">
    <company-info><cik>0001223862</cik></company-info>
    <entry><cik>0001531737</cik></entry><entry><cik>0001223862</cik></entry>
    </feed>"""
    assert parse_sec_browse_atom_ciks(payload) == (1223862, 1531737)


def test_issuer_name_normalization_removes_legal_and_class_suffixes():
    assert normalized_issuer_name("Steelcase Inc - Class A") == "STEELCASE"
    assert normalized_issuer_name("STEELCASE, INC.") == "STEELCASE"


def test_sec_issuer_name_match_accepts_former_name_but_not_unrelated_issuer():
    submissions = {
        "name": "Gold.com, Inc.",
        "formerNames": [{"name": "A-Mark Precious Metals, Inc."}],
    }
    assert sec_issuer_name_matches("A-Mark Precious Metals Inc", submissions)
    assert not sec_issuer_name_matches("Unrelated Company Inc", submissions)
