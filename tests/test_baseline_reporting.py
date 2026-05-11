from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from swingmachine.baseline import build_swing_baseline_manifest_from_profile_alias
from swingmachine.baseline_reporting import (
    SwingBaselineReportPackage,
    SwingBaselineReportPackageSummary,
    build_baseline_report_package,
    build_baseline_report_package_from_profile_alias,
    write_baseline_report_package_from_profile_alias,
    write_baseline_report_package_json,
)
from swingmachine.enums import RegimeState
from swingmachine.swing_contracts import (
    SwingCandidate,
    SwingRankingResult,
    build_quality_score,
)

PROFILE_ALIAS_PATH = "config/swing_machine_v0_1_profile.yaml"


def _manifest():
    return build_swing_baseline_manifest_from_profile_alias(PROFILE_ALIAS_PATH)


def _candidate(config_hash: str) -> SwingCandidate:
    score = build_quality_score(score_raw=1.0, score_percentile=1.0)
    return SwingCandidate(
        candidate_id="candidate:RF_TPC_V2:AAA:2026-04-23",
        strategy_id="RF_TPC_V2",
        config_hash=config_hash,
        symbol="AAA",
        session_date=date(2026, 4, 23),
        regime_state=RegimeState.RISK_ON,
        eligible=True,
        quality_score=score,
        ranking=SwingRankingResult(
            rank=1,
            score=score,
            trend_quality=0.8,
            dist_to_52w_high=0.01,
            tie_break_symbol="AAA",
        ),
    )


def test_build_baseline_report_package_summarizes_contained_artifacts() -> None:
    manifest = _manifest()
    generated_at = datetime(2026, 5, 5, 14, 0, tzinfo=UTC)
    candidate = _candidate(manifest.config_hash)

    package = build_baseline_report_package(
        manifest,
        generated_at=generated_at,
        candidates=(candidate,),
    )

    assert package.package_id.startswith("baseline_report_package:swing_machine_v0_1:")
    assert package.generated_at == generated_at
    assert package.manifest.config_hash == manifest.config_hash
    assert package.qualification_checklist.config_hash == manifest.config_hash
    assert package.summary.candidate_count == 1
    assert package.summary.serious_full_run_allowed is False


def test_baseline_report_package_rejects_artifact_config_hash_mismatch() -> None:
    manifest = _manifest()
    candidate = _candidate("wrong-config-hash")

    with pytest.raises(ValidationError, match="artifact config_hash"):
        build_baseline_report_package(manifest, candidates=(candidate,))


def test_baseline_report_package_rejects_summary_mismatch() -> None:
    manifest = _manifest()
    candidate = _candidate(manifest.config_hash)
    package = build_baseline_report_package(manifest, candidates=(candidate,))

    with pytest.raises(ValidationError, match="summary"):
        SwingBaselineReportPackage(
            package_id=package.package_id,
            generated_at=package.generated_at,
            manifest=package.manifest,
            qualification_checklist=package.qualification_checklist,
            candidates=package.candidates,
            summary=SwingBaselineReportPackageSummary(
                candidate_count=0,
                serious_full_run_allowed=package.manifest.serious_full_run_allowed,
            ),
        )


def test_write_baseline_report_package_json_writes_serialized_package(tmp_path) -> None:
    manifest = _manifest()
    package = build_baseline_report_package(manifest)
    output_path = tmp_path / "baseline_report_package.json"

    written_path = write_baseline_report_package_json(package, output_path)

    assert written_path == output_path
    payload = output_path.read_text(encoding="utf-8")
    assert '"baseline_id": "swing_machine_v0_1"' in payload
    assert '"serious_full_run_allowed": false' in payload


def test_build_baseline_report_package_from_profile_alias_uses_alias_identity() -> None:
    generated_at = datetime(2026, 5, 5, 15, 0, tzinfo=UTC)

    package = build_baseline_report_package_from_profile_alias(
        PROFILE_ALIAS_PATH,
        generated_at=generated_at,
        satisfied_check_ids=("explicit_baseline_profile",),
        blocked_check_ids=("selected_period_replay",),
    )

    assert package.generated_at == generated_at
    assert package.manifest.strategy_id == "RF_TPC_V2"
    assert package.manifest.strategy_version == "2.1.0"
    assert package.manifest.config_path.endswith("swing_trading_bot_config_template_v2.yaml")
    assert package.qualification_checklist.satisfied_check_ids == ("explicit_baseline_profile",)
    assert "selected_period_replay" in package.qualification_checklist.blocked_check_ids
    assert package.summary.serious_full_run_allowed is False


def test_write_baseline_report_package_from_profile_alias_writes_package(tmp_path) -> None:
    output_path = tmp_path / "reports" / "baseline_report_package.json"

    written_path = write_baseline_report_package_from_profile_alias(
        PROFILE_ALIAS_PATH,
        output_path,
        generated_at=datetime(2026, 5, 5, 15, 30, tzinfo=UTC),
    )

    payload = output_path.read_text(encoding="utf-8")

    assert written_path == output_path
    assert '"package_id": "baseline_report_package:swing_machine_v0_1:' in payload
    assert '"strategy_id": "RF_TPC_V2"' in payload
    assert '"serious_full_run_allowed": false' in payload


def test_baseline_report_package_smoke_writes_no_live_side_effect_artifact(tmp_path) -> None:
    output_path = tmp_path / "baseline-smoke" / "baseline_report_package.json"

    write_baseline_report_package_from_profile_alias(
        PROFILE_ALIAS_PATH,
        output_path,
        generated_at=datetime(2026, 5, 5, 16, 0, tzinfo=UTC),
    )

    payload = output_path.read_text(encoding="utf-8")

    assert '"manifest": {' in payload
    assert '"qualification_checklist": {' in payload
    assert '"summary": {' in payload
    assert '"serious_full_run_allowed": false' in payload
    assert "LIVE" not in payload
