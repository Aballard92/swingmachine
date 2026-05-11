from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from swingmachine.baseline import (
    BASELINE_ID,
    INFRASTRUCTURE_ENV_KEYS_ALLOWED,
    PROFILE_ALIAS_VERSION,
    SELECTED_PERIOD_PLAN_VERSION,
    STRATEGY_BEHAVIOUR_ENV_KEYS_PROHIBITED,
    SwingSelectedQualificationPlan,
    build_baseline_qualification_checklist,
    build_swing_baseline_manifest,
    build_swing_baseline_manifest_from_profile_alias,
    load_strategy_config_from_profile_alias,
    load_swing_baseline_profile_alias,
    load_swing_selected_qualification_plan,
    required_qualification_check_ids,
    resolve_profile_alias_strategy_config_path,
    resolve_selected_qualification_profile_alias_path,
)
from swingmachine.config import load_strategy_config
from swingmachine.enums import BrokerName, RuntimeMode

CONFIG_PATH = "swing_trading_bot_config_template_v2.yaml"
PROFILE_ALIAS_PATH = "config/swing_machine_v0_1_profile.yaml"
SELECTED_PERIOD_PLAN_PATH = "config/swing_machine_v0_1_selected_periods.yaml"


def test_build_swing_baseline_manifest_records_explicit_config_identity() -> None:
    config = load_strategy_config(CONFIG_PATH)
    created_at = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)

    manifest = build_swing_baseline_manifest(config, CONFIG_PATH, created_at=created_at)

    assert manifest.baseline_id == BASELINE_ID
    assert manifest.strategy_id == config.strategy.id
    assert manifest.strategy_version == config.strategy.version
    assert manifest.config_path == CONFIG_PATH
    assert manifest.config_hash == config.config_hash()
    assert manifest.created_at == created_at
    assert manifest.strategy_behavior_sources == (CONFIG_PATH,)


def test_baseline_manifest_defaults_to_serious_full_run_prohibited() -> None:
    config = load_strategy_config(CONFIG_PATH)

    manifest = build_swing_baseline_manifest(config, CONFIG_PATH)

    assert manifest.serious_full_run_allowed is False
    assert manifest.serious_full_run_prohibition_reason is not None
    assert {check.status for check in manifest.qualification_checks} == {"required"}


def test_baseline_manifest_allows_serious_full_run_only_when_all_checks_are_satisfied() -> None:
    config = load_strategy_config(CONFIG_PATH)

    manifest = build_swing_baseline_manifest(
        config,
        CONFIG_PATH,
        satisfied_check_ids=required_qualification_check_ids(),
    )

    assert manifest.serious_full_run_allowed is True
    assert manifest.serious_full_run_prohibition_reason is None
    assert {check.status for check in manifest.qualification_checks} == {"satisfied"}


def test_baseline_manifest_keeps_env_policy_infrastructure_only() -> None:
    config = load_strategy_config(CONFIG_PATH)

    manifest = build_swing_baseline_manifest(config, CONFIG_PATH)

    assert manifest.hidden_environment_strategy_behavior_allowed is False
    assert manifest.infrastructure_env_keys_allowed == INFRASTRUCTURE_ENV_KEYS_ALLOWED
    assert "SWINGMACHINE_DATABASE_URL" in manifest.infrastructure_env_keys_allowed
    assert "SWINGMACHINE_CONFIG_PATH" in manifest.infrastructure_env_keys_allowed
    assert manifest.strategy_behaviour_env_keys_prohibited == STRATEGY_BEHAVIOUR_ENV_KEYS_PROHIBITED
    assert "risk_rules" in manifest.strategy_behaviour_env_keys_prohibited


def test_env_example_advertises_only_allowed_infrastructure_keys() -> None:
    env_text = Path(".env.example").read_text(encoding="utf-8")
    advertised_keys = {
        line.split("=", maxsplit=1)[0]
        for line in env_text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert advertised_keys <= set(INFRASTRUCTURE_ENV_KEYS_ALLOWED)
    for prohibited_fragment in STRATEGY_BEHAVIOUR_ENV_KEYS_PROHIBITED:
        assert prohibited_fragment not in env_text.lower()


def test_baseline_qualification_checklist_lists_outstanding_checks() -> None:
    config = load_strategy_config(CONFIG_PATH)
    manifest = build_swing_baseline_manifest(
        config,
        CONFIG_PATH,
        satisfied_check_ids=("explicit_baseline_profile",),
        blocked_check_ids=("selected_period_replay",),
    )
    generated_at = datetime(2026, 5, 5, 13, 0, tzinfo=UTC)

    checklist = build_baseline_qualification_checklist(manifest, generated_at=generated_at)

    assert checklist.generated_at == generated_at
    assert checklist.serious_full_run_allowed is False
    assert checklist.satisfied_check_ids == ("explicit_baseline_profile",)
    assert "selected_period_replay" in checklist.blocked_check_ids
    assert "selected_period_replay" in checklist.outstanding_check_ids
    assert "unit_contract_tests" in checklist.outstanding_check_ids


def test_baseline_qualification_checklist_clears_when_all_checks_are_satisfied() -> None:
    config = load_strategy_config(CONFIG_PATH)
    manifest = build_swing_baseline_manifest(
        config,
        CONFIG_PATH,
        satisfied_check_ids=required_qualification_check_ids(),
    )

    checklist = build_baseline_qualification_checklist(manifest)

    assert checklist.serious_full_run_allowed is True
    assert checklist.serious_full_run_prohibition_reason is None
    assert checklist.outstanding_check_ids == ()
    assert checklist.blocked_check_ids == ()


def test_current_baseline_runtime_vocabulary_is_paper_shadow_only() -> None:
    assert {mode.value for mode in RuntimeMode} == {"PAPER", "SHADOW"}
    assert {broker.value for broker in BrokerName} == {"PAPER"}
    assert "LIVE" not in {mode.value for mode in RuntimeMode}
    assert "LIVE" not in {broker.value for broker in BrokerName}


def test_swing_baseline_profile_alias_resolves_existing_strategy_config() -> None:
    alias = load_swing_baseline_profile_alias(PROFILE_ALIAS_PATH)
    resolved_config_path = resolve_profile_alias_strategy_config_path(PROFILE_ALIAS_PATH)
    config = load_strategy_config_from_profile_alias(PROFILE_ALIAS_PATH)
    direct_config = load_strategy_config(CONFIG_PATH)

    assert alias.baseline_id == BASELINE_ID
    assert alias.profile_alias_version == PROFILE_ALIAS_VERSION
    assert alias.expected_strategy_id == "RF_TPC_V2"
    assert alias.expected_strategy_version == "2.1.0"
    assert resolved_config_path.name == CONFIG_PATH
    assert config.config_hash() == direct_config.config_hash()


def test_swing_baseline_manifest_from_profile_alias_records_resolved_config_identity() -> None:
    direct_config = load_strategy_config(CONFIG_PATH)

    manifest = build_swing_baseline_manifest_from_profile_alias(PROFILE_ALIAS_PATH)

    assert manifest.baseline_id == BASELINE_ID
    assert manifest.strategy_id == "RF_TPC_V2"
    assert manifest.strategy_version == "2.1.0"
    assert manifest.config_path.endswith(CONFIG_PATH)
    assert manifest.config_hash == direct_config.config_hash()
    assert manifest.serious_full_run_allowed is False


def test_selected_qualification_plan_loads_safe_period_definition() -> None:
    plan = load_swing_selected_qualification_plan(SELECTED_PERIOD_PLAN_PATH)
    profile_alias_path = resolve_selected_qualification_profile_alias_path(
        SELECTED_PERIOD_PLAN_PATH
    )

    assert plan.baseline_id == BASELINE_ID
    assert plan.plan_version == SELECTED_PERIOD_PLAN_VERSION
    assert plan.required_data_contract_version == "prepared_market_and_historical_panel_v1"
    assert plan.run_policy == "DRY_RUN_REPLAY_ONLY"
    assert plan.serious_full_run_policy == "PROHIBITED_UNTIL_QUALIFIED"
    assert len(plan.periods) == 3
    assert "baseline_report_package.json" in plan.required_artifacts
    assert "baseline_parity_report.json" in plan.required_artifacts
    assert {period.period_id for period in plan.periods} == {
        "smoke_recent_5_sessions",
        "recent_medium_replay_window",
        "historical_contract_stability_window",
    }
    assert all(period.end_date >= period.start_date for period in plan.periods)
    assert profile_alias_path.name == Path(PROFILE_ALIAS_PATH).name


def test_selected_qualification_plan_rejects_duplicate_period_ids() -> None:
    plan = load_swing_selected_qualification_plan(SELECTED_PERIOD_PLAN_PATH)
    duplicate_period = plan.periods[0]

    payload = plan.model_dump(mode="json")
    payload["periods"] = [
        duplicate_period.model_dump(mode="json"),
        duplicate_period.model_dump(mode="json"),
    ]

    try:
        SwingSelectedQualificationPlan.model_validate(payload)
    except ValueError as exc:
        assert "period ids must be unique" in str(exc)
    else:
        raise AssertionError("duplicate selected qualification period ids should fail validation")


def test_pullback_only_revision_profile_alias_loads_explicit_config() -> None:
    from swingmachine.baseline import load_strategy_config_from_profile_alias

    config = load_strategy_config_from_profile_alias(
        "config/swing_machine_v0_1_pullback_only_profile.yaml"
    )

    assert config.strategy.version == "2.1.0-pullback-only-offline"
    assert [pattern.value for pattern in config.setup.pattern_priority] == ["PULLBACK"]
