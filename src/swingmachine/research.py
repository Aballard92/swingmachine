from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import pandas as pd

from swingmachine.analytics import summarize_backtest
from swingmachine.backtest import run_backtest
from swingmachine.config import StrategyRuntimeConfig
from swingmachine.contracts import (
    BacktestEvent,
    BacktestResult,
    ParameterSweepRun,
    WalkForwardWindow,
    WalkForwardWindowResult,
)
from swingmachine.signals import score_candidates

RANKING_FINGERPRINT_COLUMNS = (
    "session_date",
    "symbol",
    "rankable",
    "candidate_score_raw",
    "candidate_score_pct",
    "effective_candidate_score_threshold_pct",
    "effective_min_trend_quality",
    "is_candidate",
)


def _normalize_session_dates(session_dates: Sequence[object]) -> list[pd.Timestamp]:
    normalized = pd.Index(pd.to_datetime(list(session_dates))).dropna().unique().sort_values()
    return [pd.Timestamp(value) for value in normalized]


def _json_hash(payload: Any) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if hasattr(value, "value"):
        return _json_ready(value.value)
    return value


def _frame_hash(frame: pd.DataFrame, *, columns: Sequence[str]) -> str:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Missing required fingerprint columns: {missing_str}")

    normalized = frame.loc[:, list(columns)].copy()
    if "session_date" in normalized.columns:
        normalized["session_date"] = pd.to_datetime(normalized["session_date"]).dt.strftime(
            "%Y-%m-%d"
        )
    sort_columns = [column for column in ("session_date", "symbol") if column in normalized.columns]
    if sort_columns:
        normalized = normalized.sort_values(sort_columns, kind="mergesort").reset_index(drop=True)
    payload = json.loads(
        normalized.to_json(orient="records", date_format="iso", double_precision=15)
    )
    return _json_hash(payload)


def build_walk_forward_windows(
    session_dates: Sequence[object],
    *,
    train_sessions: int,
    test_sessions: int,
    step_sessions: int | None = None,
    anchored: bool = True,
) -> tuple[WalkForwardWindow, ...]:
    if train_sessions <= 0:
        raise ValueError("train_sessions must be strictly positive")
    if test_sessions <= 0:
        raise ValueError("test_sessions must be strictly positive")

    effective_step = test_sessions if step_sessions is None else step_sessions
    if effective_step <= 0:
        raise ValueError("step_sessions must be strictly positive")

    dates = _normalize_session_dates(session_dates)
    if len(dates) < train_sessions + test_sessions:
        return ()

    windows: list[WalkForwardWindow] = []
    train_start_index = 0
    window_index = 0

    while True:
        train_end_index = train_start_index + train_sessions - 1
        test_start_index = train_end_index + 1
        test_end_index = test_start_index + test_sessions - 1

        if test_end_index >= len(dates):
            break

        windows.append(
            WalkForwardWindow(
                window_index=window_index,
                train_start_date=dates[0].date() if anchored else dates[train_start_index].date(),
                train_end_date=dates[train_end_index].date(),
                test_start_date=dates[test_start_index].date(),
                test_end_date=dates[test_end_index].date(),
                train_sessions=train_end_index - (0 if anchored else train_start_index) + 1,
                test_sessions=test_sessions,
                anchored=anchored,
            )
        )

        window_index += 1
        if anchored:
            train_sessions += effective_step
        else:
            train_start_index += effective_step

    return tuple(windows)


def apply_config_overrides(
    config: StrategyRuntimeConfig,
    overrides: Mapping[str, Any],
) -> StrategyRuntimeConfig:
    payload = config.model_dump(mode="json")
    updated = dict(payload)

    for path, value in overrides.items():
        keys = path.split(".")
        cursor: dict[str, Any] = updated
        for key in keys[:-1]:
            if key not in cursor or not isinstance(cursor[key], dict):
                raise KeyError(f"Unknown config override path: {path}")
            cursor = cursor[key]
        leaf = keys[-1]
        if leaf not in cursor:
            raise KeyError(f"Unknown config override path: {path}")
        cursor[leaf] = _json_ready(value)

    return StrategyRuntimeConfig.model_validate(updated)


def _slice_frame_by_window(
    frame: pd.DataFrame,
    *,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    if "session_date" not in frame.columns:
        raise ValueError("Expected frame with session_date column")
    sliced = frame.copy()
    sliced["session_date"] = pd.to_datetime(sliced["session_date"])
    mask = (sliced["session_date"] >= pd.Timestamp(start_date)) & (
        sliced["session_date"] <= pd.Timestamp(end_date)
    )
    return sliced.loc[mask].reset_index(drop=True)


def _candidate_fingerprint_or_none(
    panel: pd.DataFrame,
    regime_frame: pd.DataFrame,
    config: StrategyRuntimeConfig,
) -> str | None:
    try:
        return candidate_ranking_fingerprint(panel, regime_frame, config)
    except ValueError:
        return None


def candidate_ranking_fingerprint(
    panel: pd.DataFrame,
    regime_frame: pd.DataFrame,
    config: StrategyRuntimeConfig,
) -> str:
    scored = score_candidates(panel, regime_frame, config)
    return _frame_hash(scored, columns=RANKING_FINGERPRINT_COLUMNS)


def backtest_result_fingerprint(result: BacktestResult) -> str:
    return _json_hash(result.model_dump(mode="json"))


def repeated_candidate_ranking_is_identical(
    panel: pd.DataFrame,
    regime_frame: pd.DataFrame,
    config: StrategyRuntimeConfig,
) -> bool:
    first = candidate_ranking_fingerprint(panel, regime_frame, config)
    second = candidate_ranking_fingerprint(panel, regime_frame, config)
    return first == second


def repeated_backtest_is_identical(
    panel: pd.DataFrame,
    regime_frame: pd.DataFrame,
    config: StrategyRuntimeConfig,
    *,
    initial_equity: float = 100_000.0,
) -> bool:
    first = run_backtest(
        panel,
        regime_frame,
        config,
        initial_equity=initial_equity,
    )
    second = run_backtest(
        panel,
        regime_frame,
        config,
        initial_equity=initial_equity,
    )
    return backtest_result_fingerprint(first) == backtest_result_fingerprint(second)


def run_walk_forward_study(
    panel: pd.DataFrame,
    regime_frame: pd.DataFrame,
    config: StrategyRuntimeConfig,
    *,
    train_sessions: int,
    test_sessions: int,
    step_sessions: int | None = None,
    anchored: bool = True,
    initial_equity: float = 100_000.0,
) -> tuple[WalkForwardWindowResult, ...]:
    session_dates = _normalize_session_dates(panel["session_date"].tolist())
    windows = build_walk_forward_windows(
        session_dates,
        train_sessions=train_sessions,
        test_sessions=test_sessions,
        step_sessions=step_sessions,
        anchored=anchored,
    )

    results: list[WalkForwardWindowResult] = []
    for window in windows:
        train_panel = _slice_frame_by_window(
            panel,
            start_date=window.train_start_date,
            end_date=window.train_end_date,
        )
        train_regime = _slice_frame_by_window(
            regime_frame,
            start_date=window.train_start_date,
            end_date=window.train_end_date,
        )
        test_panel = _slice_frame_by_window(
            panel,
            start_date=window.test_start_date,
            end_date=window.test_end_date,
        )
        test_regime = _slice_frame_by_window(
            regime_frame,
            start_date=window.test_start_date,
            end_date=window.test_end_date,
        )

        backtest_result = run_backtest(
            test_panel,
            test_regime,
            config,
            initial_equity=initial_equity,
        )
        summary = summarize_backtest(backtest_result)
        results.append(
            WalkForwardWindowResult(
                window=window,
                config_hash=config.config_hash(),
                train_candidate_fingerprint=_candidate_fingerprint_or_none(
                    train_panel,
                    train_regime,
                    config,
                ),
                test_candidate_fingerprint=_candidate_fingerprint_or_none(
                    test_panel,
                    test_regime,
                    config,
                ),
                backtest_fingerprint=backtest_result_fingerprint(backtest_result),
                trade_count=summary["trade_count"],
                final_equity=summary["final_equity"],
                gross_pnl=summary["gross_pnl"],
                net_pnl=summary["net_pnl"],
                max_drawdown=summary["max_drawdown"],
            )
        )

    return tuple(results)


def run_parameter_sweep(
    panel: pd.DataFrame,
    regime_frame: pd.DataFrame,
    config: StrategyRuntimeConfig,
    override_sets: Sequence[Mapping[str, Any]],
    *,
    initial_equity: float = 100_000.0,
) -> tuple[ParameterSweepRun, ...]:
    results: list[ParameterSweepRun] = []
    for index, overrides in enumerate(override_sets):
        override_mapping = {str(key): value for key, value in overrides.items()}
        modified_config = apply_config_overrides(config, override_mapping)
        backtest_result = run_backtest(
            panel,
            regime_frame,
            modified_config,
            initial_equity=initial_equity,
        )
        summary = summarize_backtest(backtest_result)
        results.append(
            ParameterSweepRun(
                run_index=index,
                overrides={key: _json_ready(value) for key, value in override_mapping.items()},
                config_hash=modified_config.config_hash(),
                backtest_fingerprint=backtest_result_fingerprint(backtest_result),
                trade_count=summary["trade_count"],
                final_equity=summary["final_equity"],
                gross_pnl=summary["gross_pnl"],
                net_pnl=summary["net_pnl"],
                max_drawdown=summary["max_drawdown"],
            )
        )

    return tuple(results)


def duplicate_entry_submission_keys(
    events: Sequence[BacktestEvent],
) -> tuple[str, ...]:
    keys = [
        f"{event.symbol}|{event.setup_id or ''}"
        for event in events
        if event.event_type == "ENTRY_SUBMITTED"
    ]
    counts = Counter(keys)
    duplicates = sorted(key for key, count in counts.items() if count > 1)
    return tuple(duplicates)
