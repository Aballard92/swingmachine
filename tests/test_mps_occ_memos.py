import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "acquire_mps_occ_memos.py"
SPEC = importlib.util.spec_from_file_location("acquire_mps_occ_memos", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_parse_and_filter_occ_memo_links():
    markdown = """
    [PlayAGS, Inc. - Cash Settlement Option Symbol: AGS](https://infomemo.theocc.com/infomemos?number=56784)
    [Unrelated Expiration](https://infomemo.theocc.com/infomemos?number=1)
    """
    links = MODULE.parse_memo_links(markdown)
    assert links[0][1] == "56784"
    assert MODULE.relevant_title("AGS", "PlayAGS Inc", links[0][0])
    assert not MODULE.relevant_title("AGS", "PlayAGS Inc", links[1][0])


def test_extract_cash_per_share_candidates_without_using_contract_total():
    markdown = """
    Each existing AGS Common Share will be converted into the right to receive
    $12.50 net cash per share. Per Contract: $1,250.00 Cash ($12.50 x 100).
    """
    assert MODULE.cash_values(markdown) == [12.5]


def test_extract_guaranteed_cash_with_contingent_right_and_final_component():
    markdown = """
    Each share will be converted into the right to receive $11.45 cash plus one
    non-transferable contingent right. The final cash consideration is $0.12423103
    per EPIX Common Share.
    """
    assert MODULE.cash_values(markdown) == [0.12423103, 11.45]


def test_memo_selection_prefers_final_cash_and_limits_repeated_tender_updates():
    links = [
        ("Issuer - Tender Offer Option Symbol: ABC", "100"),
        ("Issuer - Settlement Update Option Symbol: ABC", "110"),
        ("Issuer - Cash Settlement Option Symbol: ABC", "120"),
        ("Issuer - Broker-To-Broker Settlement Option Symbol: ABC", "105"),
    ]
    assert MODULE.select_memo_links(links, 2) == [
        ("Issuer - Cash Settlement Option Symbol: ABC", "120"),
        ("Issuer - Settlement Update Option Symbol: ABC", "110"),
    ]
