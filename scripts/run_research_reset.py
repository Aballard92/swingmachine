"""Offline research reset CLI. Uses the standard library; no provider/runtime calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swingmachine.databento_audit import audit_month, load_inventory, verify_custody  # noqa: E402
from swingmachine.research_calendar import DEFAULT_BUNDLE, calendar_reference_bundle  # noqa: E402
from swingmachine.research_daily import build_daily, reference_book_from_json  # noqa: E402
from swingmachine.research_evaluation import (  # noqa: E402
    evaluate_campaign,
    load_evaluation_spec,
    spy_total_returns,
)
from swingmachine.research_minute_source import bundle_path, stream_sources  # noqa: E402
from swingmachine.research_replay import load_replay_inputs, run_replay  # noqa: E402
from swingmachine.research_reset import (  # noqa: E402
    ResearchSimulator,
    SignalEngine,
    file_hash,
    guard_research_dates,
    passive_benchmark,
)
from swingmachine.research_source import ADJUSTMENT_POLICY, _unique_object, preflight  # noqa: E402


def write_json(path: Path, value: object) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def audit(args: argparse.Namespace) -> None:
    inventory = load_inventory(args.inventory)
    result = verify_custody(args.source_root, inventory)
    write_json(args.output / "custody.json", result)
    if result["status"] != "CUSTODY_PASS":
        raise ValueError("source custody failed; see custody.json")
    # Two predeclared samples, not chosen using observed data quality or returns.
    samples = []
    for item in result["files"]:
        if "/core-101/2019-01/" in item["relative_path"] or (
            "/core-101/2020-08/" in item["relative_path"]
        ):
            print(f"Profiling declared sample {item['relative_path']}", flush=True)
            samples.append(audit_month(args.source_root / item["relative_path"], item["sha256"]))
    write_json(args.output / "structural_samples.json", samples)
    print(
        json.dumps(
            {
                "verified_files": result["verified_files"],
                "verified_bytes": result["verified_bytes"],
                "deferred_files": result["deferred_files_not_read"],
                "sample_records": sum(s["records"] for s in samples),
                "status": "AUDIT_ONLY_NO_STRATEGY_RETURNS",
            }
        )
    )


def admit(args: argparse.Namespace):
    admission = preflight(args.manifest, args.plan)
    write_json(args.output / "readiness.json", admission.report)
    if not admission.passed:
        reasons = "; ".join(
            f"{i['code']} ({i['location']}): {i['detail']}" for i in admission.report["issues"][:10]
        )
        raise ValueError(f"input preflight blocked; see readiness.json: {reasons}")
    return admission


def check_source(args: argparse.Namespace) -> None:
    admission = admit(args)
    print(json.dumps({"status": admission.report["status"], "strategy_calculations": 0}))


def build_calendar(args: argparse.Namespace) -> None:
    references, receipt = calendar_reference_bundle(
        date.fromisoformat(args.start),
        date.fromisoformat(args.end),
        args.horizon_sessions,
        args.bundle,
    )
    write_json(args.output / "reference_tables.json", references)
    repo = Path(__file__).resolve().parents[1]
    receipt["reference_tables_sha256"] = file_hash(args.output / "reference_tables.json")
    receipt["code_sha256"] = {
        str(p.relative_to(repo)): file_hash(p)
        for p in [Path(__file__).resolve(), repo / "src/swingmachine/research_calendar.py"]
    }
    write_json(args.output / "calendar_receipt.json", receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "sessions_verified": receipt["sessions"],
                "calendar_rows": receipt["calendar_rows"],
                "strategy_calculations": 0,
            }
        )
    )


def build_source(args: argparse.Namespace) -> None:
    payload = args.manifest.read_bytes()
    spec = json.loads(payload, object_pairs_hook=_unique_object)
    start, end = date.fromisoformat(spec["start"]), date.fromisoformat(spec["end"])
    guard_research_dates(start, end)
    if (
        type(spec.get("version")) is not int
        or spec.get("version") != 1
        or spec.get("source_class")
        not in (
            "SYNTHETIC_FIXTURE",
            "HISTORICAL",
        )
    ):
        raise ValueError("explicit version 1 and source class required")
    reference_path = bundle_path(args.manifest.parent, spec["references_path"])
    reference_bytes = reference_path.read_bytes()
    reference_sha = hashlib.sha256(reference_bytes).hexdigest()
    if reference_sha != spec["references_sha256"]:
        raise ValueError("reference bundle hash mismatch")
    refs = reference_book_from_json(json.loads(reference_bytes, object_pairs_hook=_unique_object))
    root = args.source_root or args.manifest.parent
    result = build_daily(stream_sources(root, spec["minute_sources"], start, end), refs, start, end)
    write_json(args.output / "adapter_diagnostics.json", result.diagnostics)
    write_json(args.output / "daily_lineage.json", result.lineage)
    write_json(args.output / "daily_reference_states.json", result.reference_states)
    write_json(args.output / "action_events.json", result.action_events)
    write_json(
        args.output / "daily_bars.json",
        [{**asdict(b), "session": str(b.session)} for b in result.bars],
    )
    write_json(args.output / "reference_tables.json", json.loads(reference_bytes))
    repo = Path(__file__).resolve().parents[1]
    receipt = {
        "task_id": "SWING-RF-003",
        "source_class": spec["source_class"],
        "build_manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "references_sha256": reference_sha,
        "minute_sources": spec["minute_sources"],
        "code_sha256": {
            str(p.relative_to(repo)): file_hash(p)
            for p in [
                Path(__file__).resolve(),
                repo / "src/swingmachine/research_daily.py",
                repo / "src/swingmachine/research_minute_source.py",
                repo / "src/swingmachine/research_dbn.py",
                repo / "src/swingmachine/databento_audit.py",
                repo / "src/swingmachine/research_reset.py",
                repo / "src/swingmachine/research_source.py",
            ]
        },
        "source_qualification": "SYNTHETIC_MECHANICS_ONLY"
        if spec["source_class"] == "SYNTHETIC_FIXTURE"
        else "NOT_QUALIFIED",
        "official_decoder_parity": "NOT_ESTABLISHED_BY_BUILD",
        "strategy_calculations": 0,
        "python_version": sys.version,
        "limits": [
            "retained reference declarations still require source qualification",
            "venue-session prices are not consolidated prices or executable auction observations",
            "absence of a minute does not distinguish no trade from unavailable data",
        ],
    }
    write_json(args.output / "build_receipt.json", receipt)
    open_sessions = [d.session for d in refs.calendar if start <= d.session <= end and d.opens]
    source = {
        "contract_version": 1,
        "source_class": spec["source_class"],
        "start": str(open_sessions[0]) if open_sessions else str(start),
        "end": str(open_sessions[-1]) if open_sessions else str(end),
        "evaluation_start": spec.get("evaluation_start"),
        "sessions": [str(d) for d in open_sessions],
        "bars_path": "daily_bars.json",
        "bars_sha256": file_hash(args.output / "daily_bars.json"),
        "adjustment_policy": ADJUSTMENT_POLICY,
        "corporate_actions_complete": result.passed,
        "event_calendar_complete": not any(
            "UNKNOWN_EARNINGS_HORIZON" in g["reasons"] for g in result.diagnostics["context_gaps"]
        ),
        "session_calendar_complete": True,
        "supporting_evidence": {},
        "adapter_receipt_path": "build_receipt.json",
        "adapter_receipt_sha256": file_hash(args.output / "build_receipt.json"),
        "action_events_path": "action_events.json",
        "action_events_sha256": file_hash(args.output / "action_events.json"),
    }
    # Historical references need independent qualification. The build never
    # manufactures that approval from syntactic joins or completeness booleans.
    write_json(args.output / "daily_manifest.json", source)
    if not result.passed:
        raise ValueError("daily adapter has unresolved source/accounting issues; see diagnostics")
    print(
        json.dumps(
            {
                "status": result.diagnostics["status"],
                "source_class": spec["source_class"],
                "daily_rows": len(result.bars),
                "strategy_calculations": 0,
            }
        )
    )


def simulate_daily_fixture(args: argparse.Namespace) -> None:
    """Explicitly retained legacy regression fixture; not the active simulator."""
    admission = admit(args)
    source, plan = admission.source, admission.plan
    if source["source_class"] == "HISTORICAL":
        raise ValueError(
            "historical strategy testing awaits RF-003 source qualification "
            "and RF-005 evaluation freeze"
        )
    sessions, evaluation_start = admission.sessions, admission.evaluation_start
    by_date = admission.by_date
    repo = Path(__file__).resolve().parents[1]
    freeze = {
        "created_at": datetime.now(UTC).isoformat(),
        "execution_model": "LEGACY_IDEALIZED_DAILY_FIXTURE",
        "source_class": source["source_class"],
        "manifest_sha256": admission.report["verified_sha256"]["manifest"],
        "plan_sha256": admission.report["verified_sha256"]["plan"],
        "bars_sha256": admission.report["verified_sha256"]["bars"],
        "input_evidence_sha256": admission.report["verified_sha256"],
        "historical_qualification": admission.report["historical_qualification"],
        "plan": plan,
        "code_sha256": {
            str(p.relative_to(repo)): file_hash(p)
            for p in [
                Path(__file__).resolve(),
                repo / "src/swingmachine/research_reset.py",
                repo / "src/swingmachine/research_source.py",
            ]
        },
        "trials": len(plan["families"]) * len(plan["cost_bps_per_side"]),
        "holdout": "PRESERVED",
        "promotion": "UNAVAILABLE",
    }
    write_json(args.output / "pre_outcome_freeze.json", freeze)
    summaries = []
    benchmark = [
        b for d, bars in by_date.items() if d >= evaluation_start for b in bars if b.symbol == "SPY"
    ]
    for config in admission.configs:
        engine, sim = SignalEngine(config), ResearchSimulator(config)
        for session in sessions:
            bars = by_date[session]
            ideas = engine.observe(bars)
            if session < evaluation_start:
                # The final warmup close can plan the first evaluation open.
                sim.pending = ideas
            else:
                sim.step(session, bars, ideas)
        result = sim.result()
        result["source_class"] = source["source_class"]
        result["benchmark"] = passive_benchmark(benchmark, config)
        result["cash_benchmark_return_assumed"] = 0.0
        result["difference_from_full_exposure_spy"] = (
            result["net_return"] - result["benchmark"]["net_marked_return"]
        )
        write_json(args.output / f"{config.family}_{config.cost_bps_per_side}bps.json", result)
        summaries.append({k: v for k, v in result.items() if k not in ["trades", "equity"]})
    write_json(args.output / "summary.json", summaries)
    print(
        json.dumps(
            {
                "trials": len(summaries),
                "source_class": source["source_class"],
                "status": "EXPLORATORY_ONLY_NO_PROMOTION",
            }
        )
    )


def simulate(args: argparse.Namespace) -> None:
    admission = admit(args)
    if admission.source["source_class"] == "HISTORICAL":
        raise ValueError(
            "historical strategy testing awaits RF-003 qualification and RF-005 freeze"
        )
    if args.minute_manifest is None or args.settlement_calendar is None:
        raise ValueError(
            "minute manifest and explicit settlement calendar required for executable replay"
        )
    spec, evaluation_freeze = load_evaluation_spec(
        args.evaluation_spec, args.plan, args.execution_policy
    )
    inputs = load_replay_inputs(
        admission,
        args.minute_manifest,
        args.execution_policy,
        args.settlement_calendar,
        args.source_root,
    )
    write_json(args.output / "execution_readiness.json", inputs.receipt)
    write_json(args.output / "evaluation_freeze.json", evaluation_freeze)
    repo = Path(__file__).resolve().parents[1]
    freeze = {
        "created_at": datetime.now(UTC).isoformat(),
        "source_class": admission.source["source_class"],
        "execution_model": "FIXED_LIMIT_MINUTE_REPLAY_V1",
        "input_evidence_sha256": admission.report["verified_sha256"],
        "execution_input_sha256": inputs.receipt["sha256"],
        "plan": admission.plan,
        "trials": len(admission.configs),
        "holdout": "PRESERVED",
        "promotion": "UNAVAILABLE",
        "evaluation_protocol": "RF005_NUMERICAL_RULES_FROZEN_V1",
        "evaluation_spec_sha256": evaluation_freeze["spec_sha256"],
        "trial_ledger": evaluation_freeze["trial_ledger"],
        "code_sha256": {
            str(p.relative_to(repo)): file_hash(p)
            for p in [
                Path(__file__).resolve(),
                *[
                    repo / "src/swingmachine" / (name + ".py")
                    for name in (
                        "research_replay",
                        "research_execution",
                        "research_benchmark",
                        "research_evaluation",
                        "research_calendar",
                        "research_reset",
                        "research_source",
                        "research_daily",
                        "research_minute_source",
                        "research_dbn",
                        "databento_audit",
                    )
                ],
            ]
        },
    }
    write_json(args.output / "pre_outcome_freeze.json", freeze)
    ledger = evaluation_freeze["trial_ledger"]
    write_json(
        args.output / "trial_attempt_started.json", [{**r, "state": "STARTED"} for r in ledger]
    )
    try:
        results = run_replay(admission, inputs)
    except (ValueError, KeyError, TypeError, OSError):
        write_json(
            args.output / "trial_execution_ledger.json",
            [{**r, "state": "ABORTED_NO_ACCEPTED_OUTCOME"} for r in ledger],
        )
        raise
    summaries = []
    for result in results:
        config = result["config"]
        write_json(
            args.output / f"{config['family']}_{config['cost_bps_per_side']}bps.json", result
        )
        summaries.append(
            {
                k: v
                for k, v in result.items()
                if k
                not in (
                    "orders",
                    "fills",
                    "events",
                    "trades",
                    "equity",
                    "open_position_states",
                    "lifecycles",
                    "benchmark",
                )
            }
        )
    write_json(args.output / "summary.json", summaries)
    write_json(
        args.output / "trial_execution_ledger.json",
        [
            {
                **r,
                "state": "COMPLETED",
                "result_sha256": file_hash(
                    args.output
                    / f"{r['config']['family']}_{r['config']['cost_bps_per_side']}bps.json"
                ),
            }
            for r in ledger
        ],
    )
    days, spy_returns = spy_total_returns(admission)
    evaluation = evaluate_campaign(results, days, spy_returns, spec, ledger)
    write_json(args.output / "evaluation.json", evaluation)
    print(json.dumps({"status": "SYNTHETIC_EXECUTABLE_REPLAY_COMPLETE", "trials": len(results)}))


def freeze_evaluation(args: argparse.Namespace) -> None:
    _, receipt = load_evaluation_spec(args.evaluation_spec, args.plan, args.execution_policy)
    repo = Path(__file__).resolve().parents[1]
    receipt["code_sha256"] = {
        str(p.relative_to(repo)): file_hash(p)
        for p in [
            Path(__file__).resolve(),
            *[
                repo / "src/swingmachine" / (name + ".py")
                for name in (
                    "research_evaluation",
                    "research_benchmark",
                    "research_execution",
                    "research_replay",
                    "research_calendar",
                    "research_reset",
                )
            ],
        ]
    }
    write_json(args.output / "evaluation_freeze.json", receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "trials": len(receipt["trial_ledger"]),
                "historical_execution_ready": False,
                "prices_read": 0,
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("audit")
    a.add_argument("--source-root", type=Path, required=True)
    a.add_argument("--inventory", type=Path, required=True)
    s = sub.add_parser("simulate")
    f = sub.add_parser("freeze-evaluation")
    legacy = sub.add_parser(
        "simulate-daily-fixture", help="legacy idealized synthetic mechanics only"
    )
    s.add_argument("--minute-manifest", type=Path)
    s.add_argument("--source-root", type=Path)
    s.add_argument("--settlement-calendar", type=Path)
    for child in (s, f):
        child.add_argument(
            "--execution-policy", type=Path, default=Path("config/research_execution_v1.json")
        )
        child.add_argument(
            "--evaluation-spec", type=Path, default=Path("config/research_evaluation_v1.json")
        )
    f.add_argument("--plan", type=Path, default=Path("config/research_reset_v1.json"))
    p = sub.add_parser("preflight")
    b = sub.add_parser("build-daily")
    b.add_argument("--manifest", type=Path, required=True)
    b.add_argument("--source-root", type=Path)
    c = sub.add_parser("build-calendar")
    c.add_argument("--start", required=True)
    c.add_argument("--end", required=True)
    c.add_argument("--horizon-sessions", type=int, default=20)
    c.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    for child in (s, p, legacy):
        child.add_argument("--manifest", type=Path, required=True)
        child.add_argument("--plan", type=Path, default=Path("config/research_reset_v1.json"))
    for child in (a, s, p, b, c, legacy, f):
        child.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        {
            "audit": audit,
            "preflight": check_source,
            "simulate": simulate,
            "simulate-daily-fixture": simulate_daily_fixture,
            "build-daily": build_source,
            "build-calendar": build_calendar,
            "freeze-evaluation": freeze_evaluation,
        }[args.command](args)
    except (ValueError, KeyError, TypeError, OSError) as error:
        write_json(args.output / "FAILED.json", {"status": "FAILED_CLOSED", "reason": str(error)})
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
