"""Offline bundle preflight. Structural admission is not historical qualification.

Read declared dates before opening referenced files. Hash and parse the same bytes.
No feature, outcome, provider, runtime or broker code runs in this module.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from datetime import date
from pathlib import Path

from swingmachine.research_reset import (
    PROTECTED_WINDOWS,
    Bar,
    ResearchConfig,
    guard_research_dates,
)

EVIDENCE_ROLES = (
    "session_calendar",
    "corporate_actions",
    "earnings_calendar",
    "security_master",
    "population_selection",
)
ADJUSTMENT_POLICY = "raw_with_explicit_splits_and_dividend_accrual"


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


@dataclass
class SourceAdmission:
    report: dict
    source: dict
    plan: dict
    sessions: list[date]
    evaluation_start: date | None
    by_date: dict[date, list[Bar]]
    configs: list[ResearchConfig]

    @property
    def passed(self) -> bool:
        return not self.report["issues"]


def preflight(manifest: Path, plan_path: Path) -> SourceAdmission:
    """Collect independent gaps; stop at unsafe or uninterpretable boundaries."""
    report = {
        "contract_version": 1,
        "status": "BLOCKED",
        "source_class": None,
        "issues": [],
        "verified_sha256": {},
        "bar_file_read": False,
        "strategy_calculations": 0,
        "historical_qualification": "NOT_ESTABLISHED_BY_PREFLIGHT",
        "promotion": "UNAVAILABLE",
    }
    result = SourceAdmission(report, {}, {}, [], None, {}, [])

    def issue(code: str, location: str, detail: str, action: str) -> None:
        report["issues"].append(
            {"code": code, "location": location, "detail": detail, "required_action": action}
        )

    def read_object(path: Path, label: str) -> dict:
        try:
            payload = path.read_bytes()
            value = json.loads(payload, object_pairs_hook=_unique_object)
            if not isinstance(value, dict):
                raise ValueError("JSON object required")
            json.dumps(value, allow_nan=False)
            report["verified_sha256"][label] = hashlib.sha256(payload).hexdigest()
            return value
        except (ValueError, OSError, UnicodeError) as error:
            issue("INVALID_DOCUMENT", label, str(error), "Supply a readable JSON object.")
            return {}

    source = result.source = read_object(manifest, "manifest")
    try:
        left, right = date.fromisoformat(source["start"]), date.fromisoformat(source["end"])
        guard_research_dates(left, right)
    except (KeyError, TypeError, ValueError) as error:
        issue(
            "DATE_BOUNDARY", "start/end", str(error), "Declare an authorised non-holdout interval."
        )
        return result

    report["source_class"] = source.get("source_class")
    if type(source.get("contract_version", 1)) is not int or source.get("contract_version", 1) != 1:
        issue(
            "SOURCE_VERSION", "contract_version", "Unsupported source contract.", "Use version 1."
        )
    if source.get("source_class") not in ("SYNTHETIC_FIXTURE", "HISTORICAL"):
        issue(
            "SOURCE_CLASS",
            "source_class",
            "Unknown source class.",
            "Declare SYNTHETIC_FIXTURE or HISTORICAL.",
        )
    if source.get("adjustment_policy") != ADJUSTMENT_POLICY:
        issue(
            "ADJUSTMENT_POLICY",
            "adjustment_policy",
            "Unknown accounting convention.",
            f"Use {ADJUSTMENT_POLICY} after adapter qualification.",
        )
    for gate in (
        "corporate_actions_complete",
        "event_calendar_complete",
        "session_calendar_complete",
    ):
        if source.get(gate) is not True:
            issue(
                "INPUT_GATE",
                gate,
                f"Unresolved input gate: {gate}.",
                "Establish and document completeness before setting true.",
            )
    try:
        values = source["sessions"]
        if not isinstance(values, list):
            raise ValueError("sessions must be a list")
        sessions = [date.fromisoformat(d) for d in values]
        if (
            not sessions
            or sessions != sorted(set(sessions))
            or sessions[0] != left
            or sessions[-1] != right
        ):
            raise ValueError("sessions must be unique, increasing and span start/end exactly")
        result.sessions = sessions
        result.by_date = {d: [] for d in sessions}
        evaluation_start = date.fromisoformat(source["evaluation_start"])
        if evaluation_start not in sessions or sessions.index(evaluation_start) < 200:
            raise ValueError("evaluation needs at least 200 preceding declared sessions")
        result.evaluation_start = evaluation_start
    except (KeyError, TypeError, ValueError) as error:
        issue(
            "SESSION_CONTRACT",
            "sessions/evaluation_start",
            str(error),
            "Supply the complete session list and a 200-session warmup.",
        )

    plan = result.plan = read_object(plan_path, "plan")
    try:
        families, costs = plan["families"], plan["cost_bps_per_side"]
        if (
            not isinstance(families, list)
            or not families
            or any(type(f) is not str for f in families)
            or len(set(families)) != len(families)
        ):
            raise ValueError("families must be a nonempty unique list")
        if (
            not isinstance(costs, list)
            or not costs
            or any(type(c) not in (int, float) for c in costs)
            or len(set(costs)) != len(costs)
        ):
            raise ValueError("cost scenarios must be a nonempty unique numeric list")
        expected_windows = [[a.isoformat(), b.isoformat()] for a, b in PROTECTED_WINDOWS]
        if plan.get("protected_windows") != expected_windows:
            raise ValueError("plan must preserve the current protected windows")
        if (
            plan.get("purpose") != "OFFLINE_EXPLORATORY_ONLY"
            or plan.get("promotion") != "NOT_AVAILABLE_IN_THIS_EXPLORATORY_RUNNER"
        ):
            raise ValueError("unsupported research purpose or promotion declaration")
        names = {f.name for f in fields(ResearchConfig)} - {
            "family",
            "max_hold",
            "cost_bps_per_side",
        }
        parameters = {name: plan[name] for name in names}
        if any(type(v) not in (int, float) for v in parameters.values()):
            raise ValueError("research parameters must be explicit numbers, not booleans")
        result.configs = [
            ResearchConfig(
                family,
                cost_bps_per_side=cost,
                max_hold=plan["max_hold_by_family"][family],
                **parameters,
            )
            for family in families
            for cost in costs
        ]
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        issue(
            "PLAN_CONTRACT",
            "plan",
            str(error),
            "Correct the explicit family/cost/parameter matrix before running trials.",
        )

    def reference(ref: dict, label: str) -> bytes | None:
        try:
            relative = Path(ref["path"])
            root = manifest.resolve().parent
            path = (root / relative).resolve()
            if relative.is_absolute() or ".." in relative.parts or not path.is_relative_to(root):
                raise ValueError("reference must remain inside the manifest bundle")
            digest = ref["sha256"]
            if (
                type(digest) is not str
                or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)
            ):
                raise ValueError("expected lowercase SHA-256 is missing or invalid")
            payload = path.read_bytes()
            if label == "bars":
                report["bar_file_read"] = True
            actual = hashlib.sha256(payload).hexdigest()
            if actual != digest:
                raise ValueError("source hash mismatch")
            report["verified_sha256"][label] = actual
            return payload
        except (KeyError, TypeError, ValueError, OSError) as error:
            issue(
                "REFERENCE_INTEGRITY",
                label,
                str(error),
                "Supply a bundle-relative file and its verified SHA-256.",
            )
            return None

    if source.get("source_class") == "HISTORICAL":
        evidence = source.get("supporting_evidence")
        if not isinstance(evidence, dict):
            issue(
                "EVIDENCE_CONTRACT",
                "supporting_evidence",
                "Historical inputs require a role-to-reference object; "
                "labels/URLs are insufficient.",
                "Provide scoped local evidence for all five required roles.",
            )
            evidence = {}
        for role in EVIDENCE_ROLES:
            ref = evidence.get(role)
            try:
                if not isinstance(ref, dict):
                    raise ValueError("missing structured evidence reference")
                a, b = (
                    date.fromisoformat(ref["coverage_start"]),
                    date.fromisoformat(ref["coverage_end"]),
                )
                guard_research_dates(a, b)
                if a > left or b < right:
                    raise ValueError(
                        "evidence does not cover the full warmup and evaluation interval"
                    )
                for field in ("scope", "provenance", "availability_policy"):
                    if not isinstance(ref.get(field), str) or not ref[field].strip():
                        raise ValueError(f"missing {field}")
            except (KeyError, TypeError, ValueError) as error:
                issue(
                    "EVIDENCE_CONTRACT",
                    role,
                    str(error),
                    "Document authorised coverage, population scope, provenance "
                    "and decision-time availability.",
                )
                continue
            reference(ref, role)

    # Do not touch a price file when dates, source declarations or trial plan fail.
    if report["issues"]:
        return result
    payload = reference(
        {"path": source.get("bars_path"), "sha256": source.get("bars_sha256")}, "bars"
    )
    if payload is None:
        return result
    try:
        rows = json.loads(payload, object_pairs_hook=_unique_object)
        if not isinstance(rows, list):
            raise ValueError("bars must be a JSON array")
    except (ValueError, UnicodeError) as error:
        issue("BAR_DOCUMENT", "bars", str(error), "Supply canonical daily rows as a JSON array.")
        return result
    seen: set[tuple[date, str]] = set()
    numeric_fields = ("open", "high", "low", "close", "volume", "split_ratio", "dividend")
    for index, row in enumerate(rows):
        location = f"bars[{index}]"
        try:
            if not isinstance(row, dict):
                raise ValueError("bar must be an object")
            for field in ("symbol", "sector"):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    raise ValueError(f"explicit nonempty {field} required")
            if any(k in row and type(row[k]) not in (int, float) for k in numeric_fields):
                raise ValueError("price/volume/action fields must be numbers, not booleans")
            if any(k not in row for k in ("eligible", "event_known")):
                raise ValueError("explicit eligibility and event knowledge required")
            if source["source_class"] == "HISTORICAL" and any(
                k not in row for k in ("split_ratio", "dividend")
            ):
                raise ValueError(
                    "historical action values must be explicit, including no-action rows"
                )
            bar = Bar(**{**row, "session": date.fromisoformat(row["session"])})
            if bar.session not in result.by_date:
                raise ValueError("unexpected bar session outside the declared calendar")
            key = (bar.session, bar.symbol)
            if key in seen:
                issue(
                    "DUPLICATE_BAR",
                    location,
                    "Duplicate session/symbol key.",
                    "Reconcile duplicate sources; do not silently discard a row.",
                )
                continue
            seen.add(key)
            result.by_date[bar.session].append(bar)
            if bar.eligible and (not bar.event_known or bar.sector == "UNKNOWN"):
                issue(
                    "ELIGIBILITY_CONTEXT",
                    location,
                    "Eligible bar has unknown earnings or sector context.",
                    "Resolve decision-time context or explicitly mark ineligible.",
                )
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            issue(
                "INVALID_BAR",
                location,
                str(error),
                "Correct the row against the canonical Bar contract.",
            )
    for session, bars in result.by_date.items():
        if not bars:
            issue(
                "MISSING_SESSION",
                session.isoformat(),
                "No valid bars for a declared session.",
                "Reconcile the source/calendar gap.",
            )
        if session >= result.evaluation_start and sum(b.symbol == "SPY" for b in bars) != 1:
            issue(
                "BENCHMARK_COVERAGE",
                session.isoformat(),
                "Exactly one SPY bar is required for each evaluation session.",
                "Supply the benchmark before calculating strategy outcomes.",
            )
    report["counts"] = {
        "rows": len(rows),
        "valid_unique_rows": sum(map(len, result.by_date.values())),
        "sessions": len(result.sessions),
        "trials": len(result.configs),
    }
    if not report["issues"]:
        report["status"] = "STRUCTURAL_PREFLIGHT_PASS"
    return result
