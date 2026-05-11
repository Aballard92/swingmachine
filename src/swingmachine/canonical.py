from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

REQUIRED_RAW_BAR_COLUMNS = (
    "session_date",
    "raw_open",
    "raw_high",
    "raw_low",
    "raw_close",
    "raw_volume",
    "cash_dividend_per_share",
    "split_ratio",
)

RAW_PRICE_COLUMNS = ("raw_open", "raw_high", "raw_low", "raw_close")


def _validate_columns(frame: pd.DataFrame, required: Sequence[str]) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Missing required columns: {missing_str}")


def _ordered_frame(frame: pd.DataFrame) -> pd.DataFrame:
    _validate_columns(frame, REQUIRED_RAW_BAR_COLUMNS)
    ordered = frame.copy()
    ordered["session_date"] = pd.to_datetime(ordered["session_date"])
    ordered = ordered.sort_values("session_date").reset_index(drop=True)
    return ordered


def compute_split_factor_cum(split_ratio: pd.Series) -> pd.Series:
    ratios = split_ratio.astype(float)
    if (ratios <= 0).any():
        raise ValueError("split_ratio must be strictly positive")

    future_adjustments = 1.0 / ratios.shift(-1, fill_value=1.0)
    factors = future_adjustments.iloc[::-1].cumprod().iloc[::-1]
    return factors.astype(float)


def compute_total_return_index(
    split_adj_close: pd.Series,
    cash_dividend_per_share: pd.Series,
    *,
    base_value: float = 100.0,
) -> pd.Series:
    if base_value <= 0:
        raise ValueError("base_value must be strictly positive")

    close = split_adj_close.astype(float).reset_index(drop=True)
    dividends = cash_dividend_per_share.astype(float).reset_index(drop=True)

    if close.empty:
        return pd.Series(dtype=float)
    if (close <= 0).any():
        raise ValueError("split_adj_close must be strictly positive")
    if (dividends < 0).any():
        raise ValueError("cash_dividend_per_share cannot be negative")

    gross_returns = pd.Series(np.ones(len(close), dtype=float))
    if len(close) > 1:
        gross_returns.iloc[1:] = (
            close.iloc[1:].to_numpy() + dividends.iloc[1:].to_numpy()
        ) / close.iloc[:-1].to_numpy()

    return pd.Series(base_value * gross_returns.cumprod().to_numpy(), index=split_adj_close.index)


def build_canonical_price_frame(
    frame: pd.DataFrame,
    *,
    total_return_index_base_value: float = 100.0,
) -> pd.DataFrame:
    ordered = _ordered_frame(frame)
    split_factor_cum = compute_split_factor_cum(ordered["split_ratio"])

    canonical = ordered.copy()
    canonical["split_factor_cum"] = split_factor_cum

    for raw_column in RAW_PRICE_COLUMNS:
        split_adj_column = raw_column.replace("raw_", "split_adj_")
        canonical[split_adj_column] = canonical[raw_column].astype(float) * split_factor_cum

    canonical["split_adj_volume"] = canonical["raw_volume"].astype(float) / split_factor_cum
    canonical["tr_close_index"] = compute_total_return_index(
        canonical["split_adj_close"],
        canonical["cash_dividend_per_share"],
        base_value=total_return_index_base_value,
    )

    return canonical
