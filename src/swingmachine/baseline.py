from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import Field, model_validator

from swingmachine.config import StrategyRuntimeConfig, load_strategy_config
from swingmachine.modeling import ImmutableModel

BASELINE_ID = "swing_machine_v0_1"
BASELINE_CONTRACT_VERSION = "swing_machine_v0_1_manifest_v1"
DATA_CONTRACT_VERSION = "prepared_market_and_historical_panel_v1"
PROFILE_ALIAS_VERSION = "swing_machine_v0_1_profile_alias_v1"
SELECTED_PERIOD_PLAN_VERSION = "swing_machine_v0_1_selected_period_plan_v1"

INFRASTRUCTURE_ENV_KEYS_ALLOWED: tuple[str, ...] = (
    "SWINGMACHINE_DATABASE_URL",
    "SWINGMACHINE_CONFIG_PATH",
    "SWINGMACHINE_RUNTIME_INPUT",
    "SWINGMACHINE_NEXT_SESSION_MARKET_DATA",
    "SWINGMACHINE_OUTPUT_DIR",
    "SWINGMACHINE_RUNTIME_MODE",
)

STRATEGY_BEHAVIOUR_ENV_KEYS_PROHIBITED: tuple[str, ...] = (
    "entry_filters",
    "exit_rules",
    "scoring_weights",
    "risk_rules",
    "universe_rules",
    "ranking_rules",
    "holding_periods",
    "time_windows",
    "stop_target_logic",
)

REQUIRED_BASELINE_CONTRACTS: tuple[str, ...] = (
    "explicit_strategy_profile",
    "data_contract",
    "typed_candidate_contract",
    "typed_signal_contract",
    "typed_risk_plan_contract",
    "typed_order_plan_contract",
    "typed_lifecycle_contract",
    "typed_exit_decision_contract",
    "rejection_reason_taxonomy",
    "baseline_reporting_package",
    "qualification_checklist",
)

_REQUIRED_QUALIFICATION_CHECKS: tuple[tuple[str, str], ...] = (
    ("explicit_baseline_profile", "Explicit baseline profile/config is recorded"),
    ("data_contract", "Prepared data contract and validation evidence are recorded"),
    ("typed_candidate_signal_contracts", "Candidate and signal contracts are present"),
    ("risk_order_lifecycle_contracts", "Risk, order, lifecycle, and exit contracts exist"),
    ("reporting_package", "Baseline manifest and decision reports are emitted"),
    ("unit_contract_tests", "Unit and contract tests pass"),
    ("smoke_tests", "Smoke tests pass on tiny fixtures"),
    ("dry_run_safety_tests", "Dry-run tests prove no live broker side effects"),
    ("research_runtime_parity", "Research/runtime parity checks pass"),
    ("selected_period_replay", "Selected-period replay artifacts are deterministic"),
    ("operator_review_pass", "Operator review report passes strict baseline thresholds"),
    ("freeze_review", "Baseline freeze review is approved"),
)

QualificationCheckStatus = Literal["required", "satisfied", "blocked", "deferred"]


class SwingBaselineProfileAlias(ImmutableModel):
    baseline_id: Literal["swing_machine_v0_1"]
    profile_alias_version: Literal["swing_machine_v0_1_profile_alias_v1"]
    strategy_config_path: str
    expected_strategy_id: str
    expected_strategy_version: str
    serious_full_run_policy: Literal["PROHIBITED_UNTIL_QUALIFIED"]
    notes: tuple[str, ...] = Field(default_factory=tuple)


class BaselineQualificationCheck(ImmutableModel):
    check_id: str
    title: str
    status: QualificationCheckStatus = "required"
    evidence: tuple[str, ...] = Field(default_factory=tuple)
    blocker: str | None = None


class SwingBaselineManifest(ImmutableModel):
    baseline_id: Literal["swing_machine_v0_1"]
    contract_version: Literal["swing_machine_v0_1_manifest_v1"]
    data_contract_version: Literal["prepared_market_and_historical_panel_v1"]
    strategy_id: str
    strategy_version: str
    strategy_description: str
    config_path: str
    config_hash: str
    created_at: datetime
    strategy_behavior_sources: tuple[str, ...]
    infrastructure_env_keys_allowed: tuple[str, ...]
    strategy_behaviour_env_keys_prohibited: tuple[str, ...]
    hidden_environment_strategy_behavior_allowed: Literal[False]
    required_contracts: tuple[str, ...]
    qualification_checks: tuple[BaselineQualificationCheck, ...]
    serious_full_run_allowed: bool
    serious_full_run_prohibition_reason: str | None


class SwingBaselineQualificationChecklist(ImmutableModel):
    baseline_id: Literal["swing_machine_v0_1"]
    contract_version: Literal["swing_machine_v0_1_manifest_v1"]
    generated_at: datetime
    config_hash: str
    serious_full_run_allowed: bool
    serious_full_run_prohibition_reason: str | None
    checks: tuple[BaselineQualificationCheck, ...]
    satisfied_check_ids: tuple[str, ...]
    outstanding_check_ids: tuple[str, ...]
    blocked_check_ids: tuple[str, ...]


class SwingSelectedQualificationPeriod(ImmutableModel):
    period_id: str
    title: str
    start_date: date
    end_date: date
    purpose: str
    minimum_session_count: int = Field(ge=1)
    maximum_symbol_count: int = Field(ge=1)
    data_requirements: tuple[str, ...] = Field(default_factory=tuple)
    required_artifacts: tuple[str, ...] = Field(default_factory=tuple)
    acceptance_evidence: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _period_dates_are_ordered(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError(
                "selected qualification period end_date must be on or after start_date"
            )
        return self


class SwingSelectedQualificationPlan(ImmutableModel):
    baseline_id: Literal["swing_machine_v0_1"]
    plan_version: Literal["swing_machine_v0_1_selected_period_plan_v1"]
    profile_alias_path: str
    required_data_contract_version: Literal["prepared_market_and_historical_panel_v1"]
    run_policy: Literal["DRY_RUN_REPLAY_ONLY"]
    serious_full_run_policy: Literal["PROHIBITED_UNTIL_QUALIFIED"]
    required_artifacts: tuple[str, ...] = Field(default_factory=tuple)
    safety_controls: tuple[str, ...] = Field(default_factory=tuple)
    periods: tuple[SwingSelectedQualificationPeriod, ...]

    @model_validator(mode="after")
    def _plan_periods_are_usable(self) -> Self:
        if not self.periods:
            raise ValueError("selected qualification plan must define at least one period")
        period_ids = [period.period_id for period in self.periods]
        if len(period_ids) != len(set(period_ids)):
            raise ValueError("selected qualification period ids must be unique")
        return self


def required_qualification_check_ids() -> tuple[str, ...]:
    return tuple(check_id for check_id, _title in _REQUIRED_QUALIFICATION_CHECKS)


def load_swing_baseline_profile_alias(path: str | Path) -> SwingBaselineProfileAlias:
    alias_path = Path(path)
    with alias_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at root of {alias_path}")
    return SwingBaselineProfileAlias.model_validate(data)


def load_swing_selected_qualification_plan(path: str | Path) -> SwingSelectedQualificationPlan:
    plan_path = Path(path)
    with plan_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at root of {plan_path}")
    return SwingSelectedQualificationPlan.model_validate(data)


def resolve_profile_alias_strategy_config_path(alias_path: str | Path) -> Path:
    alias_path = Path(alias_path)
    alias = load_swing_baseline_profile_alias(alias_path)
    config_path = Path(alias.strategy_config_path)
    if not config_path.is_absolute():
        config_path = alias_path.parent / config_path
    return config_path.resolve()


def resolve_selected_qualification_profile_alias_path(plan_path: str | Path) -> Path:
    plan_path = Path(plan_path)
    plan = load_swing_selected_qualification_plan(plan_path)
    profile_alias_path = Path(plan.profile_alias_path)
    if not profile_alias_path.is_absolute():
        profile_alias_path = plan_path.parent / profile_alias_path
    return profile_alias_path.resolve()


def load_strategy_config_from_profile_alias(alias_path: str | Path) -> StrategyRuntimeConfig:
    alias = load_swing_baseline_profile_alias(alias_path)
    config_path = resolve_profile_alias_strategy_config_path(alias_path)
    config = load_strategy_config(config_path)
    if config.strategy.id != alias.expected_strategy_id:
        raise ValueError(
            "Baseline profile alias expected strategy id "
            f"{alias.expected_strategy_id}, got {config.strategy.id}"
        )
    if config.strategy.version != alias.expected_strategy_version:
        raise ValueError(
            "Baseline profile alias expected strategy version "
            f"{alias.expected_strategy_version}, got {config.strategy.version}"
        )
    return config


def build_swing_baseline_manifest_from_profile_alias(
    alias_path: str | Path,
    *,
    created_at: datetime | None = None,
    satisfied_check_ids: tuple[str, ...] = (),
    blocked_check_ids: tuple[str, ...] = (),
) -> SwingBaselineManifest:
    config_path = resolve_profile_alias_strategy_config_path(alias_path)
    config = load_strategy_config_from_profile_alias(alias_path)
    return build_swing_baseline_manifest(
        config,
        config_path,
        created_at=created_at,
        satisfied_check_ids=satisfied_check_ids,
        blocked_check_ids=blocked_check_ids,
    )


def build_swing_baseline_manifest(
    config: StrategyRuntimeConfig,
    config_path: str | Path,
    *,
    created_at: datetime | None = None,
    satisfied_check_ids: tuple[str, ...] = (),
    blocked_check_ids: tuple[str, ...] = (),
) -> SwingBaselineManifest:
    satisfied = set(satisfied_check_ids)
    blocked = set(blocked_check_ids)
    checks = tuple(
        BaselineQualificationCheck(
            check_id=check_id,
            title=title,
            status=_check_status(check_id, satisfied, blocked),
            blocker="Required before serious full run" if check_id in blocked else None,
        )
        for check_id, title in _REQUIRED_QUALIFICATION_CHECKS
    )
    serious_full_run_allowed = all(check.status == "satisfied" for check in checks)
    return SwingBaselineManifest(
        baseline_id=BASELINE_ID,
        contract_version=BASELINE_CONTRACT_VERSION,
        data_contract_version=DATA_CONTRACT_VERSION,
        strategy_id=config.strategy.id,
        strategy_version=config.strategy.version,
        strategy_description=config.strategy.description,
        config_path=Path(config_path).as_posix(),
        config_hash=config.config_hash(),
        created_at=created_at or datetime.now(UTC),
        strategy_behavior_sources=(Path(config_path).as_posix(),),
        infrastructure_env_keys_allowed=INFRASTRUCTURE_ENV_KEYS_ALLOWED,
        strategy_behaviour_env_keys_prohibited=STRATEGY_BEHAVIOUR_ENV_KEYS_PROHIBITED,
        hidden_environment_strategy_behavior_allowed=False,
        required_contracts=REQUIRED_BASELINE_CONTRACTS,
        qualification_checks=checks,
        serious_full_run_allowed=serious_full_run_allowed,
        serious_full_run_prohibition_reason=None
        if serious_full_run_allowed
        else (
            "Serious full run prohibited until every mandatory baseline qualification "
            "check is satisfied."
        ),
    )


def build_baseline_qualification_checklist(
    manifest: SwingBaselineManifest,
    *,
    generated_at: datetime | None = None,
) -> SwingBaselineQualificationChecklist:
    satisfied_check_ids = tuple(
        check.check_id for check in manifest.qualification_checks if check.status == "satisfied"
    )
    blocked_check_ids = tuple(
        check.check_id for check in manifest.qualification_checks if check.status == "blocked"
    )
    outstanding_check_ids = tuple(
        check.check_id for check in manifest.qualification_checks if check.status != "satisfied"
    )
    return SwingBaselineQualificationChecklist(
        baseline_id=manifest.baseline_id,
        contract_version=manifest.contract_version,
        generated_at=generated_at or datetime.now(UTC),
        config_hash=manifest.config_hash,
        serious_full_run_allowed=manifest.serious_full_run_allowed,
        serious_full_run_prohibition_reason=manifest.serious_full_run_prohibition_reason,
        checks=manifest.qualification_checks,
        satisfied_check_ids=satisfied_check_ids,
        outstanding_check_ids=outstanding_check_ids,
        blocked_check_ids=blocked_check_ids,
    )


def _check_status(
    check_id: str,
    satisfied_check_ids: set[str],
    blocked_check_ids: set[str],
) -> QualificationCheckStatus:
    if check_id in blocked_check_ids:
        return "blocked"
    if check_id in satisfied_check_ids:
        return "satisfied"
    return "required"


__all__ = [
    "BASELINE_CONTRACT_VERSION",
    "BASELINE_ID",
    "DATA_CONTRACT_VERSION",
    "INFRASTRUCTURE_ENV_KEYS_ALLOWED",
    "PROFILE_ALIAS_VERSION",
    "REQUIRED_BASELINE_CONTRACTS",
    "SELECTED_PERIOD_PLAN_VERSION",
    "STRATEGY_BEHAVIOUR_ENV_KEYS_PROHIBITED",
    "BaselineQualificationCheck",
    "SwingBaselineProfileAlias",
    "SwingBaselineQualificationChecklist",
    "SwingBaselineManifest",
    "SwingSelectedQualificationPeriod",
    "SwingSelectedQualificationPlan",
    "build_baseline_qualification_checklist",
    "build_swing_baseline_manifest_from_profile_alias",
    "build_swing_baseline_manifest",
    "load_strategy_config_from_profile_alias",
    "load_swing_baseline_profile_alias",
    "load_swing_selected_qualification_plan",
    "required_qualification_check_ids",
    "resolve_profile_alias_strategy_config_path",
    "resolve_selected_qualification_profile_alias_path",
]
