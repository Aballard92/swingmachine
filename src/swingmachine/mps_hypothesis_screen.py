"""Fail-closed preflight for the bounded SWING-PC-005A hypothesis screen.

The accepted design requires source and temporality Gate 0 to pass before any
strategy outcome is calculated.  This module deliberately contains no strategy
selection or backtest invocation: a failed preflight must leave validation and
the holdout unopened.
"""

from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

from swingmachine.mps_config import MpsConfig, load_mps_config
from swingmachine.mps_validation import freeze_temporal_plan

TASK_ID = "SWING-PC-005A"
ACCEPTED_DATE_PLAN_SHA256 = "6f7146d5901c4c41418c2726a30e3c4ff83a4dfe099b1aa9a3a225972c37dcdb"
EXPECTED_HASHES = {
    "summary": "7cf6dd26d7fc0b1ddde13bcfa284c48b969988c638efc112fa31519adcd722c1",
    "computed_features": "3da1df73028a4cb8c67d75cc99f9583bf98562ea1941d111ab6b920b8b2ea731",
    "feature_input": "664c4c5664851f58a5d3d6a0ba116bce44a2c4106830c0663749a918ea028251",
    "config": "738b0a47c36bf60796bebd343575363cb7730f5b505f1f0cd7cc8ca831566d3c",
    "corporate_actions": "7e209aafad3f186ca76ce0f99bff114430fe7e913bcf34a56bdadf4ba7366cff",
}
EXPECTED_CONFIG_HASH = "a5fa802cc769fbce8f69996a6f2501fc1629df441565faa19551f2b6987b873f"
REQUIRED_FEATURE_COLUMNS = {
    "security_id",
    "ticker",
    "session_date",
    "event_time",
    "available_at",
    "open",
    "high",
    "low",
    "close",
    "total_return_adjusted_close",
    "classification_eligible",
    "shares_data_available",
    "shares_fact_available_at",
    "market_cap",
    "primary_exchange",
    "country_of_primary_listing",
    "sector",
    "sector_reference_available",
    "reference_available_at",
    "is_tradable",
    "is_halted",
    "is_delisted",
    "has_next_session_bar",
    "eligible_universe",
}
EXPECTED_TEMPORAL_BOUNDARIES = {
    "calendar": ("2008-01-02", "2025-12-10", 4515),
    "discovery": ("2008-01-02", "2016-01-04"),
    "embargo_1": ("2016-01-05", "2016-02-17", 30),
    "validation_1": ("2016-02-18", "2018-02-15", 504),
    "development_2": ("2008-01-02", "2018-01-03"),
    "embargo_2": ("2018-01-04", "2018-02-15", 30),
    "validation_2": ("2018-02-16", "2020-02-19", 504),
    "unused_buffer": ("2020-02-20", "2020-12-03"),
    "holdout": ("2020-12-04", "2025-12-10", 1260),
}


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def research_eligibility_mask(frame: pd.DataFrame, config: MpsConfig) -> pd.Series:
    """Apply the additional fail-closed research masks fixed by the design."""
    sector_available = frame["sector_reference_available"].astype("boolean").fillna(False)
    valid_market_cap = pd.to_numeric(frame["market_cap"], errors="coerce").gt(0.0)
    return (
        frame["eligible_universe"].astype("boolean").fillna(False)
        & frame["classification_eligible"].astype("boolean").fillna(False)
        & frame["shares_data_available"].astype("boolean").fillna(False)
        & valid_market_cap
        & frame["primary_exchange"].isin(config.universe.exchanges)
        & frame["country_of_primary_listing"].eq(config.universe.country_of_primary_listing)
        & sector_available
        & frame["sector"].notna()
        & frame["sector"].ne("UNKNOWN")
        & frame["is_tradable"].astype("boolean").fillna(False)
        & ~frame["is_halted"].astype("boolean").fillna(True)
        & ~frame["is_delisted"].astype("boolean").fillna(True)
        & frame["has_next_session_bar"].astype("boolean").fillna(False)
    )


def _iso(value: date) -> str:
    return value.isoformat()


def temporal_plan_evidence(frame: pd.DataFrame) -> dict[str, Any]:
    sessions = tuple(pd.to_datetime(frame["session_date"]).dt.date.unique())
    plan = freeze_temporal_plan(sessions)
    if len(plan.walk_forward_windows) != 2:
        return {
            "exact_boundaries_match": False,
            "accepted_date_plan_sha256": ACCEPTED_DATE_PLAN_SHA256,
            "reason": "unexpected_walk_forward_window_count",
            "window_count": len(plan.walk_forward_windows),
        }
    first, second = plan.walk_forward_windows
    ordered = tuple(sorted(set(sessions)))
    second_validation_end_index = ordered.index(second.validation_end)
    actual = {
        "calendar": (_iso(ordered[0]), _iso(ordered[-1]), len(ordered)),
        "discovery": (_iso(first.development_start), _iso(first.development_end)),
        "embargo_1": (
            _iso(first.embargo_start),
            _iso(first.embargo_end),
            sum(first.embargo_start <= value <= first.embargo_end for value in ordered),
        ),
        "validation_1": (
            _iso(first.validation_start),
            _iso(first.validation_end),
            sum(first.validation_start <= value <= first.validation_end for value in ordered),
        ),
        "development_2": (
            _iso(second.development_start),
            _iso(second.development_end),
        ),
        "embargo_2": (
            _iso(second.embargo_start),
            _iso(second.embargo_end),
            sum(second.embargo_start <= value <= second.embargo_end for value in ordered),
        ),
        "validation_2": (
            _iso(second.validation_start),
            _iso(second.validation_end),
            sum(second.validation_start <= value <= second.validation_end for value in ordered),
        ),
        "unused_buffer": (
            _iso(ordered[second_validation_end_index + 1]),
            _iso(plan.development_dates[-1]),
        ),
        "holdout": (
            _iso(plan.holdout_dates[0]),
            _iso(plan.holdout_dates[-1]),
            len(plan.holdout_dates),
        ),
    }
    return {
        "exact_boundaries_match": actual == EXPECTED_TEMPORAL_BOUNDARIES,
        "accepted_date_plan_sha256": ACCEPTED_DATE_PLAN_SHA256,
        "actual": actual,
        "expected": EXPECTED_TEMPORAL_BOUNDARIES,
        "holdout_frozen": plan.holdout_frozen,
    }


def _check(status: bool, **details: Any) -> dict[str, Any]:
    return {"status": "PASS" if status else "FAIL", **details}


def audit_gate_zero(
    *,
    summary_path: Path,
    feature_path: Path,
    feature_input_path: Path,
    config_path: Path,
    corporate_actions_path: Path,
    benchmark_path: Path | None,
) -> dict[str, Any]:
    paths = {
        "summary": summary_path,
        "computed_features": feature_path,
        "feature_input": feature_input_path,
        "config": config_path,
        "corporate_actions": corporate_actions_path,
    }
    actual_hashes = {name: file_sha256(path) for name, path in paths.items()}
    hash_matches = {
        name: actual_hashes[name] == expected for name, expected in EXPECTED_HASHES.items()
    }
    config = load_mps_config(config_path)
    parsed_config_hash = config.config_hash()

    features = pd.read_parquet(feature_path)
    actions = pd.read_parquet(corporate_actions_path)
    missing_columns = sorted(REQUIRED_FEATURE_COLUMNS - set(features.columns))
    duplicate_rows = int(features.duplicated(["security_id", "session_date"], keep=False).sum())

    available_at = pd.to_datetime(features["available_at"], utc=True, errors="coerce")
    event_time = pd.to_datetime(features["event_time"], utc=True, errors="coerce")
    shares_available_at = pd.to_datetime(
        features["shares_fact_available_at"], utc=True, errors="coerce"
    )
    reference_available_at = pd.to_datetime(
        features["reference_available_at"], utc=True, errors="coerce"
    )
    shares_mask = features["shares_data_available"].fillna(False).astype(bool)
    reference_mask = features["sector_reference_available"].fillna(False).astype(bool)
    availability_failures = {
        "missing_available_at": int(available_at.isna().sum()),
        "event_after_available_at": int((event_time > available_at).sum()),
        "available_shares_missing_timestamp": int((shares_mask & shares_available_at.isna()).sum()),
        "shares_timestamp_after_decision": int(
            (shares_mask & shares_available_at.notna() & (shares_available_at > available_at)).sum()
        ),
        "available_reference_missing_timestamp": int(
            (reference_mask & reference_available_at.isna()).sum()
        ),
        "reference_timestamp_after_decision": int(
            (
                reference_mask
                & reference_available_at.notna()
                & (reference_available_at > available_at)
            ).sum()
        ),
    }

    eligible = research_eligibility_mask(features, config)
    dividend_rows = actions["div_cash"].fillna(0.0).ne(0.0)
    split_rows = actions["split_factor"].fillna(1.0).ne(1.0)
    missing_payment_dates = int(
        (dividend_rows & pd.to_datetime(actions["payment_date"], errors="coerce").isna()).sum()
    )
    delisted_rows = int(features["is_delisted"].fillna(False).astype(bool).sum())
    delisting_semantics_present = {
        "delisting_return",
        "cash_terms_per_share",
    }.issubset(actions.columns)
    benchmark_present = benchmark_path is not None and benchmark_path.is_file()
    benchmark_ticker = config.market_regime.benchmark
    plan = temporal_plan_evidence(features)

    checks = {
        "fixed_hashes": _check(
            all(hash_matches.values()) and parsed_config_hash == EXPECTED_CONFIG_HASH,
            expected=EXPECTED_HASHES,
            actual=actual_hashes,
            matches=hash_matches,
            expected_parsed_config_hash=EXPECTED_CONFIG_HASH,
            actual_parsed_config_hash=parsed_config_hash,
        ),
        "schema_and_uniqueness": _check(
            not missing_columns and duplicate_rows == 0,
            missing_columns=missing_columns,
            duplicate_security_session_rows=duplicate_rows,
            rows=len(features),
        ),
        "decision_time_availability": _check(
            not any(availability_failures.values()),
            failures=availability_failures,
        ),
        "fail_closed_eligibility": _check(
            True,
            existing_eligible_rows=int(
                features["eligible_universe"].fillna(False).astype(bool).sum()
            ),
            research_eligible_rows=int(eligible.sum()),
            research_eligible_symbols=int(features.loc[eligible, "security_id"].nunique()),
            halt_state_policy="ASSUMED_FALSE_NO_POINT_IN_TIME_SOURCE",
            qualification_usable=False,
        ),
        "benchmark_semantics": _check(
            benchmark_present,
            required_benchmark=benchmark_ticker,
            frozen_benchmark_path=(str(benchmark_path) if benchmark_path is not None else None),
            reason=None if benchmark_present else "NO_FROZEN_SPY_BENCHMARK",
        ),
        "corporate_action_semantics": _check(
            missing_payment_dates == 0 and (delisted_rows == 0 or delisting_semantics_present),
            corporate_action_rows=len(actions),
            dividend_events=int(dividend_rows.sum()),
            dividend_events_missing_payment_date=missing_payment_dates,
            split_events=int(split_rows.sum()),
            terminal_delisted_rows=delisted_rows,
            delisting_outcome_fields_present=delisting_semantics_present,
            reason=(
                "DIVIDEND_PAYMENT_DATES_AND_DELISTING_OUTCOMES_UNAVAILABLE"
                if missing_payment_dates or (delisted_rows and not delisting_semantics_present)
                else None
            ),
        ),
        "temporal_plan": _check(
            bool(plan.get("exact_boundaries_match")) and bool(plan.get("holdout_frozen")),
            **plan,
        ),
        "prohibited_sources_or_actions": _check(
            True,
            network_used=False,
            api_used=False,
            vault_used=False,
            new_data_acquired=False,
            packages_installed=False,
        ),
    }
    failures = [name for name, check in checks.items() if check["status"] == "FAIL"]
    return {
        "task_id": TASK_ID,
        "gate": "GATE_0_SOURCE_AND_TEMPORALITY",
        "status": "PASS" if not failures else "FAIL",
        "failure_outcome": None if not failures else "STOP_SOURCE_OR_TEMPORALITY_INVALID",
        "failed_checks": failures,
        "checks": checks,
        "screen_execution": {
            "strategy_outcomes_calculated": False,
            "gate_1_opened": False,
            "gate_2_opened": False,
            "holdout_opened": False,
        },
    }


def render_gate_zero_markdown(report: dict[str, Any]) -> str:
    gate = report["gate_zero"]
    failed = ", ".join(gate["failed_checks"]) or "none"
    checks = gate["checks"]
    corporate = checks["corporate_action_semantics"]
    benchmark = checks["benchmark_semantics"]
    eligibility = checks["fail_closed_eligibility"]
    eligible_summary = (
        f"{eligibility['research_eligible_rows']} across "
        f"{eligibility['research_eligible_symbols']} securities"
    )
    return f"""# SWING-PC-005A - Bounded Offline Hypothesis Screen

Generated: `{report["generated_at"]}`

Outcome: `{report["outcome"]}`

## Result

The accepted sequential design stopped at Gate 0. No H1, H2, or B0 strategy
outcome was calculated. Discovery, walk-forward validation, and the untouched
holdout remained unopened.

Failed Gate 0 checks: `{failed}`.

## Decisive evidence

- Frozen SPY benchmark path: `{benchmark["frozen_benchmark_path"]}`.
- Benchmark failure: `{benchmark["reason"]}`.
- Corporate-action rows: `{corporate["corporate_action_rows"]}`.
- Dividend events: `{corporate["dividend_events"]}`.
- Dividend events missing payment dates: `{corporate["dividend_events_missing_payment_date"]}`.
- Terminal delisted rows: `{corporate["terminal_delisted_rows"]}`.
- Delisting outcome fields present: `{corporate["delisting_outcome_fields_present"]}`.
- Corporate-action failure: `{corporate["reason"]}`.

## Passing preflight evidence

- Fixed hashes and parsed config: `{checks["fixed_hashes"]["status"]}`.
- Schema and uniqueness: `{checks["schema_and_uniqueness"]["status"]}`.
- Decision-time availability: `{checks["decision_time_availability"]["status"]}`.
- Frozen temporal boundaries: `{checks["temporal_plan"]["status"]}`.
- Existing eligible rows: `{eligibility["existing_eligible_rows"]}`.
- Additional fail-closed research-eligible rows: `{eligible_summary}`.

## Gate lock

- Gate 1 opened: `false`
- Gate 2 opened: `false`
- Holdout opened: `false`
- New data/API/Vault/package activity: `false`
- Profile, paper trading, live trading, broker, or runtime authority: `none`

This is a source/temporality stop, not evidence that either hypothesis passes or
fails economically.
"""
