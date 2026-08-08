"""Deterministic validation controls for MPS research.

This module contains no strategy-selection policy.  It freezes temporal splits,
records every experiment, and calculates diagnostics that a human decision
record can apply to preregistered acceptance gates.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
from itertools import combinations
from math import exp, isfinite, log, sqrt
from pathlib import Path
from random import Random
from statistics import NormalDist, mean, pstdev

TRADING_SESSIONS_PER_YEAR = 252


@dataclass(frozen=True)
class ValidationWindow:
    development_start: date
    development_end: date
    embargo_start: date
    embargo_end: date
    validation_start: date
    validation_end: date


@dataclass(frozen=True)
class TemporalPlan:
    development_dates: tuple[date, ...]
    holdout_dates: tuple[date, ...]
    walk_forward_windows: tuple[ValidationWindow, ...]
    holdout_frozen: bool = True


@dataclass(frozen=True)
class Diagnostic:
    status: str
    value: float | None
    details: Mapping[str, object]


def _ordered_unique_dates(sessions: Iterable[date]) -> tuple[date, ...]:
    ordered = tuple(sorted(set(sessions)))
    if not ordered:
        raise ValueError("at least one trading session is required")
    return ordered


def freeze_temporal_plan(
    sessions: Iterable[date],
    *,
    minimum_development_sessions: int = 8 * TRADING_SESSIONS_PER_YEAR,
    validation_sessions: int = 2 * TRADING_SESSIONS_PER_YEAR,
    step_sessions: int = 2 * TRADING_SESSIONS_PER_YEAR,
    embargo_sessions: int = 30,
) -> TemporalPlan:
    """Freeze an untouched holdout and anchored walk-forward windows.

    The holdout is the longer of the most recent five trading years or 25% of
    available sessions, matching the MPS-1 preregistration.
    """
    ordered = _ordered_unique_dates(sessions)
    holdout_size = max(5 * TRADING_SESSIONS_PER_YEAR, (len(ordered) + 3) // 4)
    if len(ordered) <= holdout_size:
        raise ValueError("history is too short to form the required holdout")
    development = ordered[:-holdout_size]
    holdout = ordered[-holdout_size:]
    if min(minimum_development_sessions, validation_sessions, step_sessions) <= 0:
        raise ValueError("window lengths must be positive")
    if embargo_sessions < 0:
        raise ValueError("embargo_sessions cannot be negative")

    windows: list[ValidationWindow] = []
    validation_start_index = minimum_development_sessions + embargo_sessions
    while validation_start_index + validation_sessions <= len(development):
        development_end_index = validation_start_index - embargo_sessions - 1
        embargo_start_index = development_end_index + 1
        embargo_end_index = validation_start_index - 1
        windows.append(
            ValidationWindow(
                development_start=development[0],
                development_end=development[development_end_index],
                embargo_start=development[embargo_start_index],
                embargo_end=development[embargo_end_index],
                validation_start=development[validation_start_index],
                validation_end=development[validation_start_index + validation_sessions - 1],
            )
        )
        validation_start_index += step_sessions
    return TemporalPlan(development, holdout, tuple(windows))


def annualized_sharpe(returns: Sequence[float]) -> float | None:
    clean = [float(value) for value in returns if isfinite(float(value))]
    if len(clean) < 2:
        return None
    volatility = pstdev(clean)
    if volatility == 0:
        return None
    return mean(clean) / volatility * sqrt(TRADING_SESSIONS_PER_YEAR)


def apply_one_way_costs(
    gross_returns: Sequence[float],
    one_way_turnover: Sequence[float],
    cost_bps: int,
) -> tuple[float, ...]:
    if len(gross_returns) != len(one_way_turnover):
        raise ValueError("returns and turnover lengths differ")
    if cost_bps < 0:
        raise ValueError("cost_bps cannot be negative")
    rate = cost_bps / 10_000.0
    return tuple(
        float(ret) - float(turnover) * rate
        for ret, turnover in zip(gross_returns, one_way_turnover, strict=True)
    )


def cost_stress_table(
    gross_returns: Sequence[float],
    one_way_turnover: Sequence[float],
    scenarios: Sequence[int] = (5, 10, 20, 50),
) -> dict[int, dict[str, float | None]]:
    output: dict[int, dict[str, float | None]] = {}
    for cost_bps in scenarios:
        net = apply_one_way_costs(gross_returns, one_way_turnover, cost_bps)
        compounded = 1.0
        for value in net:
            compounded *= 1.0 + value
        output[int(cost_bps)] = {
            "total_return": compounded - 1.0,
            "annualized_sharpe": annualized_sharpe(net),
        }
    return output


def block_bootstrap_mean_ci(
    returns: Sequence[float],
    *,
    block_size: int = 20,
    samples: int = 2_000,
    confidence: float = 0.95,
    seed: int = 1,
) -> Diagnostic:
    clean = tuple(float(value) for value in returns if isfinite(float(value)))
    if block_size <= 0 or samples <= 0 or not 0 < confidence < 1:
        raise ValueError("invalid bootstrap parameters")
    if len(clean) < 2 * block_size:
        return Diagnostic(
            "INSUFFICIENT_DATA", None, {"observations": len(clean), "minimum": 2 * block_size}
        )
    starts = range(0, len(clean) - block_size + 1)
    rng = Random(seed)
    estimates: list[float] = []
    for _ in range(samples):
        sample: list[float] = []
        while len(sample) < len(clean):
            start = rng.choice(starts)
            sample.extend(clean[start : start + block_size])
        estimates.append(mean(sample[: len(clean)]))
    estimates.sort()
    tail = (1.0 - confidence) / 2.0
    lower = estimates[int(tail * (samples - 1))]
    upper = estimates[int((1.0 - tail) * (samples - 1))]
    return Diagnostic(
        "OK", mean(clean), {"lower": lower, "upper": upper, "confidence": confidence, "seed": seed}
    )


def deflated_sharpe_ratio(
    observed_sharpe: float,
    returns: Sequence[float],
    *,
    trials: int,
) -> Diagnostic:
    """Approximate Bailey-Lopez de Prado DSR with non-normality adjustment."""
    clean = tuple(float(value) for value in returns if isfinite(float(value)))
    if len(clean) < 30 or trials < 1:
        return Diagnostic("INSUFFICIENT_DATA", None, {"observations": len(clean), "trials": trials})
    daily_sr = observed_sharpe / sqrt(TRADING_SESSIONS_PER_YEAR)
    mu = mean(clean)
    sigma = pstdev(clean)
    if sigma == 0:
        return Diagnostic("INSUFFICIENT_DATA", None, {"reason": "zero_variance"})
    standardized = tuple((value - mu) / sigma for value in clean)
    skew = mean(tuple(value**3 for value in standardized))
    kurtosis = mean(tuple(value**4 for value in standardized))
    sr_variance = max(
        (1.0 - skew * daily_sr + ((kurtosis - 1.0) / 4.0) * daily_sr**2) / (len(clean) - 1), 0.0
    )
    sr_std = sqrt(sr_variance)
    if sr_std == 0:
        return Diagnostic("INSUFFICIENT_DATA", None, {"reason": "zero_sharpe_variance"})
    if trials == 1:
        expected_max = 0.0
    else:
        normal = NormalDist()
        gamma = 0.5772156649015329
        expected_max = sr_std * (
            (1.0 - gamma) * normal.inv_cdf(1.0 - 1.0 / trials)
            + gamma * normal.inv_cdf(1.0 - 1.0 / (trials * exp(1.0)))
        )
    probability = NormalDist().cdf((daily_sr - expected_max) / sr_std)
    return Diagnostic(
        "OK",
        probability,
        {
            "expected_max_daily_sharpe": expected_max,
            "trials": trials,
            "skew": skew,
            "kurtosis": kurtosis,
        },
    )


def probability_of_backtest_overfitting(
    returns_by_variant: Mapping[str, Sequence[float]],
    *,
    slices: int = 8,
) -> Diagnostic:
    """Calculate CSCV PBO from equal-length, contemporaneous return series."""
    if slices < 4 or slices % 2:
        raise ValueError("slices must be an even integer of at least four")
    names = tuple(sorted(returns_by_variant))
    if len(names) < 2:
        return Diagnostic("INSUFFICIENT_DATA", None, {"variants": len(names)})
    lengths = {len(returns_by_variant[name]) for name in names}
    if len(lengths) != 1:
        raise ValueError("variant return series lengths differ")
    observations = lengths.pop()
    if observations < slices * 10:
        return Diagnostic(
            "INSUFFICIENT_DATA", None, {"observations": observations, "minimum": slices * 10}
        )
    boundaries = [round(index * observations / slices) for index in range(slices + 1)]
    index_slices = [tuple(range(boundaries[i], boundaries[i + 1])) for i in range(slices)]
    logits: list[float] = []
    for train_slice_ids in combinations(range(slices), slices // 2):
        train_set = set(train_slice_ids)
        train_indices = tuple(index for slice_id in train_set for index in index_slices[slice_id])
        test_indices = tuple(
            index
            for slice_id in range(slices)
            if slice_id not in train_set
            for index in index_slices[slice_id]
        )
        train_scores = {
            name: annualized_sharpe(tuple(returns_by_variant[name][i] for i in train_indices))
            for name in names
        }
        valid_train = {name: score for name, score in train_scores.items() if score is not None}
        if not valid_train:
            continue
        winner = max(valid_train, key=lambda name: (valid_train[name], name))
        test_scores = {
            name: annualized_sharpe(tuple(returns_by_variant[name][i] for i in test_indices))
            for name in names
        }
        valid_test = {name: score for name, score in test_scores.items() if score is not None}
        if winner not in valid_test or len(valid_test) < 2:
            continue
        ordered = sorted(valid_test, key=lambda name: (valid_test[name], name))
        rank = ordered.index(winner) + 1
        percentile = (rank - 0.5) / len(ordered)
        logits.append(log(percentile / (1.0 - percentile)))
    if not logits:
        return Diagnostic("INSUFFICIENT_DATA", None, {"reason": "no_valid_cscv_partitions"})
    pbo = sum(value <= 0.0 for value in logits) / len(logits)
    return Diagnostic(
        "OK", pbo, {"partitions": len(logits), "median_logit": sorted(logits)[len(logits) // 2]}
    )


def neighbourhood_stability(
    selected_performance: float,
    neighbouring_performance: Sequence[float],
    *,
    minimum_retention: float = 0.80,
) -> Diagnostic:
    clean = sorted(float(value) for value in neighbouring_performance if isfinite(float(value)))
    if selected_performance <= 0 or not clean:
        return Diagnostic("INSUFFICIENT_DATA", None, {"neighbours": len(clean)})
    midpoint = len(clean) // 2
    median = clean[midpoint] if len(clean) % 2 else (clean[midpoint - 1] + clean[midpoint]) / 2.0
    retention = median / selected_performance
    return Diagnostic(
        "PASS" if retention >= minimum_retention else "FAIL",
        retention,
        {"median": median, "minimum": minimum_retention},
    )


class ExperimentRegistry:
    """Append-only JSONL registry; failed and blocked attempts are retained."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @staticmethod
    def configuration_id(configuration: Mapping[str, object]) -> str:
        canonical = json.dumps(configuration, sort_keys=True, separators=(",", ":"), default=str)
        return sha256(canonical.encode("utf-8")).hexdigest()

    def append(
        self,
        *,
        strategy_variant: str,
        configuration: Mapping[str, object],
        data_hash: str,
        status: str,
        outcome: Mapping[str, object],
        attempted_at: datetime | None = None,
    ) -> dict[str, object]:
        record = {
            "attempted_at": (attempted_at or datetime.now(UTC)).isoformat(),
            "strategy_variant": strategy_variant,
            "configuration_id": self.configuration_id(configuration),
            "configuration": dict(configuration),
            "data_hash": data_hash,
            "status": status,
            "outcome": dict(outcome),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(record, sort_keys=True, separators=(",", ":"), default=str) + "\n"
            )
        return record


def diagnostic_as_dict(diagnostic: Diagnostic) -> dict[str, object]:
    return asdict(diagnostic)
