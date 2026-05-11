from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from swingmachine.contracts import DecisionLedgerReport, DecisionLedgerRow
from swingmachine.enums import ReviewStatus


def build_decision_ledger_report(
    *,
    lifecycle_artifact_manifest_path: str | Path,
    scanner_material_decisions_path: str | Path | None = None,
    run_id: str | None = None,
    generated_at: datetime | None = None,
) -> DecisionLedgerReport:
    generated_at = generated_at or datetime.utcnow()
    lifecycle_artifact_manifest_path = Path(lifecycle_artifact_manifest_path)
    lifecycle_manifest = _read_json(lifecycle_artifact_manifest_path)
    panel_id = str(lifecycle_manifest["panel_id"])
    run_id = run_id or generated_at.strftime("%Y%m%dT%H%M%SZ")

    transitions_payload = _read_json(lifecycle_manifest["lifecycle_transitions_path"])
    pending_orders_payload = _read_json(lifecycle_manifest["lifecycle_pending_orders_path"])
    positions_payload = _read_json(lifecycle_manifest["lifecycle_positions_path"])
    summary_payload = _read_json(lifecycle_manifest["lifecycle_replay_summary_path"])
    scanner_payload = None
    if scanner_material_decisions_path is not None:
        scanner_payload = _read_json(scanner_material_decisions_path)

    transition_groups = _group_by_setup(transitions_payload.get("transitions", ()))
    pending_by_setup = _group_by_setup(pending_orders_payload.get("pending_orders", ()))
    positions_by_setup = _group_by_setup(positions_payload.get("positions", ()))
    scanner_symbols_by_session = _scanner_symbols_by_session(scanner_payload)
    material_rows = _scanner_material_rows(scanner_payload)
    material_by_setup = _material_rows_by_setup(material_rows)
    material_keys_used: set[tuple[str, str]] = set()
    rows = []

    for key in sorted(transition_groups):
        symbol, setup_id = key
        transitions = sorted(
            transition_groups[key],
            key=lambda item: (str(item.get("session_date")), str(item.get("transition_id"))),
        )
        pending_orders = pending_by_setup.get(key, [])
        positions = positions_by_setup.get(key, [])
        material_row = material_by_setup.get(key)
        if material_row is not None:
            material_keys_used.add(key)
        entry_submitted = _has_trigger(transitions, "ENTRY_SUBMITTED")
        entry_filled = _has_trigger(transitions, "ENTRY_FILLED")
        entry_cancelled = _has_trigger(transitions, "ENTRY_CANCELLED")
        exit_submitted = _has_trigger(transitions, "EXIT_SUBMITTED")
        exit_filled = _has_trigger(transitions, "EXIT_FILLED")
        trade_closed = any(str(item.get("state")) == "CLOSED" for item in positions) or exit_filled
        signal_session = _first_trigger_session(transitions, "ENTRY_SUBMITTED")
        next_session = _first_post_entry_session(transitions)
        latest_transition = transitions[-1] if transitions else {}
        latest_position = _latest_by_session(positions)
        order_intent_id = _first_non_empty(
            [item.get("order_intent_id") for item in pending_orders]
            + [item.get("order_intent_id") for item in positions]
            + [item.get("order_intent_id") for item in transitions]
        )
        position_id = _first_non_empty(
            [latest_position.get("position_id") if latest_position else None]
            + [item.get("position_id") for item in transitions]
        )
        lifecycle_state = latest_transition.get("to_state")
        if lifecycle_state is None and latest_position:
            lifecycle_state = latest_position.get("state")
        missing_links = _missing_links(
            signal_session=signal_session,
            symbol=symbol,
            setup_id=setup_id,
            scanner_symbols_by_session=scanner_symbols_by_session,
            pending_orders=pending_orders,
            positions=positions,
            entry_filled=entry_filled,
            material_row=material_row,
            accepted=True,
        )
        rows.append(
            DecisionLedgerRow(
                ledger_id=_ledger_id(panel_id, symbol, setup_id),
                panel_id=panel_id,
                symbol=symbol,
                signal_session=signal_session,
                next_session=next_session,
                setup_id=setup_id,
                decision=_decision(
                    entry_submitted=entry_submitted,
                    entry_filled=entry_filled,
                    entry_cancelled=entry_cancelled,
                    exit_submitted=exit_submitted,
                    trade_closed=trade_closed,
                ),
                reason_codes=_reason_codes(transitions),
                candidate_score_pct=_optional_float(material_row, "candidate_score_pct"),
                rank=_optional_int(material_row, "rank"),
                signal_id=_optional_str(material_row, "signal_id"),
                risk_plan_id=_optional_str(material_row, "risk_plan_id"),
                order_plan_id=_optional_str(material_row, "order_plan_id"),
                order_intent_id=order_intent_id,
                position_id=position_id,
                lifecycle_state=lifecycle_state,
                entry_submitted=entry_submitted,
                entry_filled=entry_filled,
                entry_cancelled=entry_cancelled,
                exit_submitted=exit_submitted,
                exit_filled=exit_filled,
                trade_closed=trade_closed,
                missing_links=missing_links,
            )
        )

    for material_row in material_rows:
        key = (str(material_row.get("symbol")), str(material_row.get("setup_id")))
        if material_row.get("setup_id") and key in material_keys_used:
            continue
        if material_row.get("decision") == "ACCEPTED_SETUP":
            continue
        symbol = str(material_row.get("symbol"))
        signal_session = material_row.get("signal_session")
        setup_id = _optional_str(material_row, "setup_id")
        rows.append(
            DecisionLedgerRow(
                ledger_id=_ledger_id(panel_id, symbol, setup_id or ""),
                panel_id=panel_id,
                symbol=symbol,
                signal_session=signal_session,
                next_session=material_row.get("next_session"),
                setup_id=setup_id,
                decision=str(material_row.get("decision") or "REJECTED_CANDIDATE"),
                reason_codes=tuple(str(code) for code in material_row.get("reason_codes", ())),
                candidate_score_pct=_optional_float(material_row, "candidate_score_pct"),
                rank=_optional_int(material_row, "rank"),
                signal_id=_optional_str(material_row, "signal_id"),
                risk_plan_id=_optional_str(material_row, "risk_plan_id"),
                order_plan_id=_optional_str(material_row, "order_plan_id"),
                order_intent_id=None,
                position_id=None,
                lifecycle_state="REJECTED",
                entry_submitted=False,
                entry_filled=False,
                entry_cancelled=False,
                exit_submitted=False,
                exit_filled=False,
                trade_closed=False,
                missing_links=_missing_links(
                    signal_session=signal_session,
                    symbol=symbol,
                    setup_id=setup_id or "",
                    scanner_symbols_by_session=scanner_symbols_by_session,
                    pending_orders=[],
                    positions=[],
                    entry_filled=False,
                    material_row=material_row,
                    accepted=False,
                ),
            )
        )

    warnings = _warnings(scanner_material_decisions_path, rows)
    missing_link_count = sum(len(row.missing_links) for row in rows)
    status = ReviewStatus.WARN if missing_link_count or warnings else ReviewStatus.PASS
    return DecisionLedgerReport(
        panel_id=panel_id,
        run_id=run_id,
        status=status,
        generated_at=generated_at,
        row_count=len(rows),
        accepted_setup_count=int(summary_payload.get("entry_submitted_count", 0)),
        rejected_candidate_count=_rejected_candidate_count(scanner_payload),
        missing_link_count=missing_link_count,
        rows=tuple(rows),
        warnings=tuple(warnings),
    )


def write_decision_ledger_report_json(
    report: DecisionLedgerReport,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return output_path


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _group_by_setup(items: Any) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in items or ():
        symbol = item.get("symbol")
        setup_id = item.get("setup_id")
        if not symbol or not setup_id:
            continue
        grouped[(str(symbol), str(setup_id))].append(item)
    return grouped


def _scanner_symbols_by_session(
    scanner_payload: dict[str, Any] | None,
) -> dict[str, set[str]]:
    if scanner_payload is None:
        return {}
    symbols_by_session = {}
    for session in scanner_payload.get("sessions", ()):
        symbols_by_session[str(session.get("signal_session"))] = {
            str(symbol) for symbol in session.get("accepted_setup_symbols", ())
        }
    return symbols_by_session


def _scanner_material_rows(scanner_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if scanner_payload is None:
        return []
    rows = []
    for session in scanner_payload.get("sessions", ()):
        rows.extend(session.get("material_decision_rows", ()))
    return rows


def _material_rows_by_setup(
    material_rows: list[dict[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    rows_by_setup = {}
    for row in material_rows:
        symbol = row.get("symbol")
        setup_id = row.get("setup_id")
        if not symbol or not setup_id:
            continue
        rows_by_setup[(str(symbol), str(setup_id))] = row
    return rows_by_setup


def _missing_links(
    *,
    signal_session: Any,
    symbol: str,
    setup_id: str,
    scanner_symbols_by_session: dict[str, set[str]],
    pending_orders: list[dict[str, Any]],
    positions: list[dict[str, Any]],
    entry_filled: bool,
    material_row: dict[str, Any] | None,
    accepted: bool,
) -> tuple[str, ...]:
    missing = []
    if signal_session is None:
        missing.append("signal_session_missing")
    if accepted and scanner_symbols_by_session and symbol not in scanner_symbols_by_session.get(
        str(signal_session),
        set(),
    ):
        missing.append("scanner_accepted_setup_link_missing")
    if accepted and not pending_orders:
        missing.append("pending_order_snapshot_missing")
    if entry_filled and not positions:
        missing.append("position_snapshot_missing")
    if material_row is None or not material_row.get("candidate_id"):
        missing.append("candidate_detail_missing")
    if not accepted and not material_row.get("reason_codes"):
        missing.append("candidate_rejection_detail_missing")
    if accepted and not material_row.get("signal_id"):
        missing.append("signal_detail_missing")
    if accepted and not material_row.get("risk_plan_id"):
        missing.append("risk_plan_detail_missing")
    if accepted and not material_row.get("order_plan_id"):
        missing.append("order_plan_detail_missing")
    if accepted and setup_id == "":
        missing.append("setup_id_missing")
    return tuple(dict.fromkeys(missing))


def _warnings(
    scanner_material_decisions_path: str | Path | None,
    rows: list[DecisionLedgerRow],
) -> list[str]:
    warnings = []
    if scanner_material_decisions_path is None:
        warnings.append("scanner material decisions path was not provided")
    if not rows:
        warnings.append("decision ledger has no rows")
    return warnings


def _has_trigger(transitions: list[dict[str, Any]], trigger: str) -> bool:
    return any(item.get("trigger") == trigger for item in transitions)


def _first_trigger_session(
    transitions: list[dict[str, Any]],
    trigger: str,
) -> Any:
    for item in transitions:
        if item.get("trigger") == trigger:
            return item.get("session_date")
    return None


def _first_post_entry_session(transitions: list[dict[str, Any]]) -> Any:
    for item in transitions:
        if item.get("trigger") in {"ENTRY_FILLED", "ENTRY_CANCELLED"}:
            return item.get("session_date")
    return None


def _latest_by_session(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not items:
        return None
    return sorted(items, key=lambda item: str(item.get("session_date")))[-1]


def _first_non_empty(values: list[Any]) -> str | None:
    for value in values:
        if value:
            return str(value)
    return None


def _reason_codes(transitions: list[dict[str, Any]]) -> tuple[str, ...]:
    codes = []
    for transition in transitions:
        codes.extend(str(code) for code in transition.get("reason_codes", ()))
    return tuple(dict.fromkeys(codes))


def _decision(
    *,
    entry_submitted: bool,
    entry_filled: bool,
    entry_cancelled: bool,
    exit_submitted: bool,
    trade_closed: bool,
) -> str:
    if trade_closed:
        return "TRADE_CLOSED"
    if exit_submitted:
        return "EXIT_PENDING"
    if entry_filled:
        return "OPEN_POSITION"
    if entry_cancelled:
        return "ENTRY_CANCELLED"
    if entry_submitted:
        return "ENTRY_PENDING"
    return "UNKNOWN"


def _rejected_candidate_count(scanner_payload: dict[str, Any] | None) -> int:
    if scanner_payload is None:
        return 0
    material_rows = _scanner_material_rows(scanner_payload)
    if material_rows:
        return sum(1 for row in material_rows if row.get("decision") != "ACCEPTED_SETUP")
    return sum(
        int(session.get("rejected_candidate_count", 0))
        + int(session.get("rejected_decision_count", 0))
        for session in scanner_payload.get("sessions", ())
    )


def _ledger_id(panel_id: str, symbol: str, setup_id: str) -> str:
    payload = f"{panel_id}|{symbol}|{setup_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _optional_float(row: dict[str, Any] | None, key: str) -> float | None:
    if row is None or row.get(key) is None:
        return None
    return float(row[key])


def _optional_int(row: dict[str, Any] | None, key: str) -> int | None:
    if row is None or row.get(key) is None:
        return None
    return int(row[key])


def _optional_str(row: dict[str, Any] | None, key: str) -> str | None:
    if row is None or row.get(key) is None:
        return None
    return str(row[key])
