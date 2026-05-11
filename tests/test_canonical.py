from __future__ import annotations

from datetime import date

import pandas as pd

from swingmachine.canonical import build_canonical_price_frame


def test_build_canonical_price_frame_adjusts_for_future_splits() -> None:
    frame = pd.DataFrame(
        {
            "session_date": [
                date(2026, 1, 5),
                date(2026, 1, 6),
                date(2026, 1, 7),
                date(2026, 1, 8),
            ],
            "raw_open": [100.0, 50.0, 55.0, 60.0],
            "raw_high": [101.0, 51.0, 56.0, 61.0],
            "raw_low": [99.0, 49.0, 54.0, 59.0],
            "raw_close": [100.0, 50.0, 55.0, 60.0],
            "raw_volume": [1_000.0, 2_000.0, 1_500.0, 1_200.0],
            "cash_dividend_per_share": [0.0, 0.0, 0.0, 0.0],
            "split_ratio": [1.0, 2.0, 1.0, 1.0],
        }
    )

    canonical = build_canonical_price_frame(frame)

    assert canonical["split_factor_cum"].tolist() == [0.5, 1.0, 1.0, 1.0]
    assert canonical["split_adj_close"].tolist() == [50.0, 50.0, 55.0, 60.0]
    assert canonical["split_adj_volume"].tolist() == [2_000.0, 2_000.0, 1_500.0, 1_200.0]


def test_build_canonical_price_frame_builds_total_return_index() -> None:
    frame = pd.DataFrame(
        {
            "session_date": [date(2026, 2, 2), date(2026, 2, 3), date(2026, 2, 4)],
            "raw_open": [100.0, 102.0, 101.0],
            "raw_high": [101.0, 103.0, 102.0],
            "raw_low": [99.0, 101.0, 100.0],
            "raw_close": [100.0, 102.0, 101.0],
            "raw_volume": [1_000.0, 1_100.0, 1_050.0],
            "cash_dividend_per_share": [0.0, 1.0, 0.0],
            "split_ratio": [1.0, 1.0, 1.0],
        }
    )

    canonical = build_canonical_price_frame(frame, total_return_index_base_value=100.0)

    assert canonical["tr_close_index"].iloc[0] == 100.0
    assert canonical["tr_close_index"].iloc[1] == 103.0
    assert canonical["tr_close_index"].iloc[2] == 103.0 * (101.0 / 102.0)
