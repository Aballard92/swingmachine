from __future__ import annotations

import importlib.util
from pathlib import Path


def load_module():
    script = Path(__file__).parents[1] / "scripts" / "build_mps_sec_resolution_seed.py"
    spec = importlib.util.spec_from_file_location("build_mps_sec_resolution_seed", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unique_historical_ticker_wins_when_name_is_ambiguous() -> None:
    module = load_module()

    cik, status = module.choose_resolution({12}, {12, 99}, None)

    assert cik == 12
    assert status == "UNIQUE_HISTORICAL_FILING_TICKER"


def test_unique_ticker_and_unique_name_conflict_fails_closed() -> None:
    module = load_module()

    cik, status = module.choose_resolution({12}, {99}, None)

    assert cik is None
    assert status == "REJECTED_TICKER_NAME_CONFLICT"


def test_hash_bound_review_override_is_explicit() -> None:
    module = load_module()

    cik, status = module.choose_resolution(
        set(),
        {12, 99},
        {"accepted_cik": 12},
    )

    assert cik == 12
    assert status == "REVIEWED_SEC_SUBMISSIONS_OVERRIDE"
