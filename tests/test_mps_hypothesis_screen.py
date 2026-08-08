from __future__ import annotations

import pandas as pd

from swingmachine.mps_config import load_mps_config
from swingmachine.mps_hypothesis_screen import research_eligibility_mask


def _eligibility_panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "eligible_universe": [True, True, True],
            "classification_eligible": [True, True, True],
            "shares_data_available": [True, True, True],
            "market_cap": [1_000_000_000.0] * 3,
            "primary_exchange": ["NYSE"] * 3,
            "country_of_primary_listing": ["US"] * 3,
            "sector_reference_available": [True, False, True],
            "sector": ["Technology", "UNKNOWN", "Technology"],
            "is_tradable": [True, True, True],
            "is_halted": [False, False, False],
            "is_delisted": [False, False, False],
            "has_next_session_bar": [True, True, False],
        }
    )


def test_research_eligibility_fails_closed_on_sector_and_next_bar() -> None:
    mask = research_eligibility_mask(_eligibility_panel(), load_mps_config())

    assert mask.tolist() == [True, False, False]


def test_research_eligibility_fails_closed_on_missing_boolean_state() -> None:
    panel = _eligibility_panel().iloc[[0]].copy()
    panel["is_halted"] = panel["is_halted"].astype("boolean")
    panel.loc[panel.index[0], "is_halted"] = None

    mask = research_eligibility_mask(panel, load_mps_config())

    assert mask.tolist() == [False]
