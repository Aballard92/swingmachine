from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import typer
import yaml

from swingmachine.broker import PaperBrokerAdapter
from swingmachine.config import StrategyRuntimeConfig, load_strategy_config
from swingmachine.contracts import (
    EntrySubmissionOutcome,
    OperatorReviewThresholds,
    OrderStateSynchronization,
    PendingEntryAction,
    PortfolioEntryBatch,
    ProtectedPosition,
    RuntimeCycleInput,
    RuntimeCycleResult,
    ShadowEntryBatch,
    ShadowFillComparison,
    ShadowFillComparisonBatch,
    ShadowSubmissionOutcome,
)
from swingmachine.data_contracts import validate_next_session_market_data
from swingmachine.entries import portfolio_heat
from swingmachine.enums import RegimeState, ReviewStatus, RuntimeEventType, RuntimeMode
from swingmachine.lifecycle import setup_can_be_armed
from swingmachine.monitoring import MonitoringService
from swingmachine.order_intents import OrderIntentService
from swingmachine.order_state_machine import OrderStateMachine
from swingmachine.paper_shadow_audit import PaperShadowAuditService
from swingmachine.portfolio_manager import PortfolioManager
from swingmachine.reconciliation import ReconciliationService
from swingmachine.reporting import (
    DEFAULT_REPORT_LOOKBACK_DAYS,
    OperatorReviewReportService,
    RollingAuditReportService,
    operator_review_run_metrics,
    summarize_operator_review_run_trends,
)
from swingmachine.review_rendering import render_operator_review_html
from swingmachine.run_history import RuntimeRunHistory
from swingmachine.shadow import compare_runtime_cycle_shadow_fills
from swingmachine.shadow_reviews import ShadowReviewService
from swingmachine.storage import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)


def _empty_shadow_batch(
    *,
    synchronization: OrderStateSynchronization,
    as_of: datetime,
    regime_state: RegimeState,
    equity: float,
    open_positions: tuple[ProtectedPosition, ...],
    blocked_spent_setup_ids: tuple[str, ...] = (),
) -> ShadowEntryBatch:
    return ShadowEntryBatch(
        as_of=as_of,
        regime_state=regime_state,
        synchronization=synchronization,
        portfolio_batch=PortfolioEntryBatch(
            plans=(),
            approved_count=0,
            rejected_count=0,
            batch_new_risk_amount=0.0,
            projected_portfolio_heat=(
                portfolio_heat(open_positions, equity) if open_positions else 0.0
            ),
            projected_daily_new_risk=0.0,
        ),
        blocked_spent_setup_ids=blocked_spent_setup_ids,
        proposals=(),
    )


class TradingRuntime:
    def __init__(
        self,
        config: StrategyRuntimeConfig,
        *,
        order_state_machine: OrderStateMachine,
        order_intent_service: OrderIntentService,
        portfolio_manager: PortfolioManager | None = None,
    ) -> None:
        self._config = config
        self._order_state_machine = order_state_machine
        self._order_intent_service = order_intent_service
        self._portfolio_manager = portfolio_manager or PortfolioManager(config)

    def run_cycle(
        self,
        cycle_input: RuntimeCycleInput,
        *,
        mode: RuntimeMode,
    ) -> RuntimeCycleResult:
        if mode == RuntimeMode.PAPER:
            pending_entry_batch = self._order_state_machine.process_pending_entries(
                cycle_input.pending_entry_checks,
                as_of=cycle_input.as_of,
                last_data_at=cycle_input.last_data_at,
                day_start_equity=cycle_input.day_start_equity,
                current_equity=cycle_input.current_equity,
                broker_available=cycle_input.broker_available,
            )
            paper_entry_batch = self._order_state_machine.submit_entry_batch(
                cycle_input.setups,
                as_of=cycle_input.as_of,
                regime_state=cycle_input.regime_state,
                equity=cycle_input.equity,
                expires_at=cycle_input.expires_at,
                last_data_at=cycle_input.last_data_at,
                day_start_equity=cycle_input.day_start_equity,
                current_equity=cycle_input.current_equity,
                broker_available=cycle_input.broker_available,
                open_positions=cycle_input.open_positions,
                submitted_today_risk_amount=cycle_input.submitted_today_risk_amount,
                sector_by_symbol=cycle_input.sector_by_symbol,
                vol_target_size_multiplier=cycle_input.vol_target_size_multiplier,
            )
            return RuntimeCycleResult(
                mode=mode,
                pending_entry_batch=pending_entry_batch,
                paper_entry_batch=paper_entry_batch,
            )

        shadow_entry_batch = self._build_shadow_entry_batch(cycle_input)
        return RuntimeCycleResult(
            mode=mode,
            shadow_entry_batch=shadow_entry_batch,
        )

    def _build_shadow_entry_batch(
        self,
        cycle_input: RuntimeCycleInput,
    ) -> ShadowEntryBatch:
        synchronization = self._order_state_machine.synchronize(
            as_of=cycle_input.as_of,
            last_data_at=cycle_input.last_data_at,
            day_start_equity=cycle_input.day_start_equity,
            current_equity=cycle_input.current_equity,
            broker_available=cycle_input.broker_available,
        )
        spent_setup_ids = set(synchronization.recovery_state.spent_setup_ids)
        blocked_spent_setup_ids: list[str] = []
        armable_setups = []
        for setup in cycle_input.setups:
            if setup.spent or not setup_can_be_armed(
                setup.setup_id,
                spent_setup_ids=spent_setup_ids,
                config=self._config,
            ):
                blocked_spent_setup_ids.append(setup.setup_id)
                continue
            armable_setups.append(setup)

        if synchronization.monitoring_report.kill_switch_active:
            return _empty_shadow_batch(
                synchronization=synchronization,
                as_of=cycle_input.as_of,
                regime_state=cycle_input.regime_state,
                equity=cycle_input.equity,
                open_positions=cycle_input.open_positions,
                blocked_spent_setup_ids=tuple(blocked_spent_setup_ids),
            )

        portfolio_batch = self._portfolio_manager.plan_ranked_entries(
            armable_setups,
            regime_state=cycle_input.regime_state,
            equity=cycle_input.equity,
            pending_symbols=tuple(
                intent.symbol for intent in synchronization.recovery_state.pending_entry_intents
            ),
            open_positions=cycle_input.open_positions,
            submitted_today_risk_amount=cycle_input.submitted_today_risk_amount,
            sector_by_symbol=cycle_input.sector_by_symbol,
            vol_target_size_multiplier=cycle_input.vol_target_size_multiplier,
            created_at=cycle_input.as_of,
            expires_at=cycle_input.expires_at,
        )

        proposals: list[ShadowSubmissionOutcome] = []
        for plan in portfolio_batch.plans:
            if not plan.approved:
                proposals.append(
                    ShadowSubmissionOutcome(
                        symbol=plan.setup.symbol,
                        setup_id=plan.setup.setup_id,
                        approved=False,
                        would_submit=False,
                        reject_reasons=plan.reject_reasons,
                    )
                )
                continue

            if plan.order_intent is None:
                proposals.append(
                    ShadowSubmissionOutcome(
                        symbol=plan.setup.symbol,
                        setup_id=plan.setup.setup_id,
                        approved=True,
                        would_submit=False,
                        reject_reasons=("MISSING_ORDER_INTENT",),
                    )
                )
                continue

            proposals.append(
                ShadowSubmissionOutcome(
                    symbol=plan.setup.symbol,
                    setup_id=plan.setup.setup_id,
                    approved=True,
                    would_submit=True,
                    intent_id=plan.order_intent.intent_id,
                    hypothetical_intent=plan.order_intent,
                )
            )

        return ShadowEntryBatch(
            as_of=cycle_input.as_of,
            regime_state=cycle_input.regime_state,
            synchronization=synchronization,
            portfolio_batch=portfolio_batch,
            blocked_spent_setup_ids=tuple(blocked_spent_setup_ids),
            proposals=tuple(proposals),
        )


def build_runtime(
    config: StrategyRuntimeConfig,
    *,
    database_url: str = "sqlite+pysqlite:///./swingmachine_runtime.db",
) -> TradingRuntime:
    engine = create_database_engine(database_url)
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    order_intent_service = OrderIntentService(session_factory)
    runtime = TradingRuntime(
        config,
        order_state_machine=OrderStateMachine(
            config,
            order_intent_service=order_intent_service,
            broker_adapter=PaperBrokerAdapter(session_factory),
            reconciliation_service=ReconciliationService(session_factory),
            portfolio_manager=PortfolioManager(config),
            monitoring_service=MonitoringService(config),
        ),
        order_intent_service=order_intent_service,
        portfolio_manager=PortfolioManager(config),
    )
    return runtime


def build_shadow_review_service(
    *,
    database_url: str = "sqlite+pysqlite:///./swingmachine_runtime.db",
) -> ShadowReviewService:
    engine = create_database_engine(database_url)
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    return ShadowReviewService(session_factory)


def build_paper_shadow_audit_service(
    *,
    database_url: str = "sqlite+pysqlite:///./swingmachine_runtime.db",
) -> PaperShadowAuditService:
    engine = create_database_engine(database_url)
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    return PaperShadowAuditService(session_factory)


def build_rolling_audit_report_service(
    *,
    database_url: str = "sqlite+pysqlite:///./swingmachine_runtime.db",
) -> RollingAuditReportService:
    engine = create_database_engine(database_url)
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    return RollingAuditReportService(
        paper_shadow_audit_service=PaperShadowAuditService(session_factory),
        shadow_review_service=ShadowReviewService(session_factory),
    )


def build_operator_review_report_service(
    *,
    database_url: str = "sqlite+pysqlite:///./swingmachine_runtime.db",
) -> OperatorReviewReportService:
    engine = create_database_engine(database_url)
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    paper_shadow_audit_service = PaperShadowAuditService(session_factory)
    shadow_review_service = ShadowReviewService(session_factory)
    return OperatorReviewReportService(
        rolling_audit_report_service=RollingAuditReportService(
            paper_shadow_audit_service=paper_shadow_audit_service,
            shadow_review_service=shadow_review_service,
        ),
        paper_shadow_audit_service=paper_shadow_audit_service,
        shadow_review_service=shadow_review_service,
        runtime_run_history=RuntimeRunHistory(session_factory),
    )


def build_runtime_run_history(
    *,
    database_url: str = "sqlite+pysqlite:///./swingmachine_runtime.db",
) -> RuntimeRunHistory:
    engine = create_database_engine(database_url)
    initialize_database(engine)
    session_factory = create_session_factory(engine)
    return RuntimeRunHistory(session_factory)


def load_runtime_cycle_input(path: str | Path) -> RuntimeCycleInput:
    input_path = Path(path)
    with input_path.open("r", encoding="utf-8") as handle:
        if input_path.suffix.lower() == ".json":
            payload = json.load(handle)
        else:
            payload = yaml.safe_load(handle)
    return RuntimeCycleInput.model_validate(payload)


def load_runtime_cycle_result(path: str | Path) -> RuntimeCycleResult:
    result_path = Path(path)
    with result_path.open("r", encoding="utf-8") as handle:
        if result_path.suffix.lower() == ".json":
            payload = json.load(handle)
        else:
            payload = yaml.safe_load(handle)
    return RuntimeCycleResult.model_validate(payload)


def load_market_data_frame(path: str | Path) -> pd.DataFrame:
    market_data_path = Path(path)
    suffix = market_data_path.suffix.lower()
    if suffix == ".csv":
        return validate_next_session_market_data(pd.read_csv(market_data_path))
    with market_data_path.open("r", encoding="utf-8") as handle:
        if suffix == ".json":
            payload = json.load(handle)
        else:
            payload = yaml.safe_load(handle)
    if payload is None:
        return pd.DataFrame()
    if isinstance(payload, dict):
        if "rows" in payload:
            payload = payload["rows"]
        else:
            payload = [payload]
    return validate_next_session_market_data(pd.DataFrame(payload))


def write_runtime_cycle_result(
    result: RuntimeCycleResult,
    path: str | Path,
) -> None:
    output_path = Path(path)
    payload = result.model_dump(mode="json")
    _write_payload(payload, output_path)


def write_shadow_fill_comparison_batch(
    result: ShadowFillComparisonBatch,
    path: str | Path,
) -> None:
    output_path = Path(path)
    payload = result.model_dump(mode="json")
    _write_payload(payload, output_path)


def _parse_iso_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def _parse_lookback_days(value: str) -> tuple[int, ...]:
    days: list[int] = []
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        days.append(int(part))
    return tuple(days)


def _shadow_summary_record_count(summary: Mapping[str, object]) -> int:
    summary_payload = summary.get("summary")
    if not isinstance(summary_payload, Mapping):
        return 0
    record_count = summary_payload.get("comparison_count")
    return record_count if isinstance(record_count, int) else 0


def _audit_summary_record_count(summary: Mapping[str, object]) -> int:
    summary_payload = summary.get("summary")
    if not isinstance(summary_payload, Mapping):
        return 0
    record_count = summary_payload.get("record_count")
    return record_count if isinstance(record_count, int) else 0


def _write_payload(
    payload: object,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        if output_path.suffix.lower() == ".json":
            json.dump(payload, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")
        else:
            yaml.safe_dump(payload, handle, sort_keys=True)


def _resolve_output_format(output_path: Path, output_format: str) -> str:
    normalized = output_format.lower()
    if normalized == "auto":
        suffix = output_path.suffix.lower()
        if suffix in {".html", ".htm"}:
            return "html"
        if suffix == ".json":
            return "json"
        if suffix in {".yaml", ".yml"}:
            return "yaml"
        return "json"
    if normalized not in {"json", "yaml", "html"}:
        raise typer.BadParameter("format must be one of: auto, json, yaml, html")
    return normalized


def _write_payload_as_format(
    payload: object,
    output_path: Path,
    *,
    output_format: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        if output_format == "json":
            json.dump(payload, handle, indent=2, sort_keys=True, default=str)
            handle.write("\n")
            return
        if output_format == "yaml":
            yaml.safe_dump(payload, handle, sort_keys=True)
            return
        raise typer.BadParameter("format must be one of: json, yaml")


def _validate_percent_option(value: float, *, option_name: str) -> float:
    if not 0.0 <= value <= 1.0:
        raise typer.BadParameter(f"{option_name} must be between 0 and 1")
    return value


def _validate_non_negative_int_option(value: int, *, option_name: str) -> int:
    if value < 0:
        raise typer.BadParameter(f"{option_name} must be non-negative")
    return value


def _record_runtime_run(
    *,
    database_url: str,
    command: str,
    started_at: datetime,
    status: str,
    mode: RuntimeMode | None = None,
    config_hash: str | None = None,
    input_path: Path | None = None,
    output_path: Path | None = None,
    detail: str | None = None,
    metrics: dict[str, object] | None = None,
) -> str:
    return build_runtime_run_history(database_url=database_url).record_run(
        command=command,
        status=status,
        started_at=started_at,
        completed_at=datetime.utcnow(),
        mode=mode,
        config_hash=config_hash,
        input_path=None if input_path is None else str(input_path),
        output_path=None if output_path is None else str(output_path),
        detail=detail,
        metrics=metrics,
    )


def _record_runtime_event(
    *,
    database_url: str,
    command: str,
    event_type: RuntimeEventType,
    run_id: str | None = None,
    mode: RuntimeMode | None = None,
    symbol: str | None = None,
    setup_id: str | None = None,
    intent_id: str | None = None,
    output_path: Path | None = None,
    payload: Mapping[str, object] | None = None,
) -> str:
    return build_runtime_run_history(database_url=database_url).record_event(
        command=command,
        event_type=event_type,
        run_id=run_id,
        mode=mode,
        symbol=symbol,
        setup_id=setup_id,
        intent_id=intent_id,
        output_path=None if output_path is None else str(output_path),
        payload=payload,
    )


def _record_runtime_cycle_decision_events(
    *,
    database_url: str,
    command: str,
    run_id: str,
    result: RuntimeCycleResult,
) -> None:
    if result.pending_entry_batch is not None:
        for action in result.pending_entry_batch.actions:
            _record_pending_entry_action_event(
                database_url=database_url,
                command=command,
                run_id=run_id,
                mode=result.mode,
                action=action,
            )

    if result.paper_entry_batch is not None:
        for submission in result.paper_entry_batch.submissions:
            _record_paper_submission_event(
                database_url=database_url,
                command=command,
                run_id=run_id,
                submission=submission,
            )

    if result.shadow_entry_batch is not None:
        for proposal in result.shadow_entry_batch.proposals:
            _record_shadow_proposal_event(
                database_url=database_url,
                command=command,
                run_id=run_id,
                proposal=proposal,
            )


def _record_pending_entry_action_event(
    *,
    database_url: str,
    command: str,
    run_id: str,
    mode: RuntimeMode,
    action: PendingEntryAction,
) -> None:
    _record_runtime_event(
        database_url=database_url,
        command=command,
        event_type=RuntimeEventType.PENDING_ENTRY_ACTION_DECIDED,
        run_id=run_id,
        mode=mode,
        symbol=action.symbol,
        setup_id=action.setup_id,
        intent_id=action.intent_id,
        payload={
            "should_cancel": action.evaluation.should_cancel,
            "cancel_reasons": [reason.value for reason in action.evaluation.cancel_reasons],
            "expired": action.evaluation.expired,
            "mark_setup_spent": action.evaluation.mark_setup_spent,
            "next_state": action.evaluation.next_state.value,
            "broker_cancelled": action.broker_cancelled,
            "broker_cancel_reason": action.broker_cancel_reason,
            "terminal_status": (
                None if action.terminal_status is None else action.terminal_status.value
            ),
            "setup_marked_spent": action.setup_marked_spent,
        },
    )


def _record_paper_submission_event(
    *,
    database_url: str,
    command: str,
    run_id: str,
    submission: EntrySubmissionOutcome,
) -> None:
    _record_runtime_event(
        database_url=database_url,
        command=command,
        event_type=RuntimeEventType.PAPER_ENTRY_SUBMISSION_DECIDED,
        run_id=run_id,
        mode=RuntimeMode.PAPER,
        symbol=submission.symbol,
        setup_id=submission.setup_id,
        intent_id=submission.intent_id,
        payload={
            "approved": submission.approved,
            "submitted": submission.submitted,
            "broker_order_id": submission.broker_order_id,
            "reused_existing_broker_order": submission.reused_existing_broker_order,
            "reject_reasons": list(submission.reject_reasons),
        },
    )


def _record_shadow_proposal_event(
    *,
    database_url: str,
    command: str,
    run_id: str,
    proposal: ShadowSubmissionOutcome,
) -> None:
    _record_runtime_event(
        database_url=database_url,
        command=command,
        event_type=RuntimeEventType.SHADOW_ENTRY_PROPOSAL_DECIDED,
        run_id=run_id,
        mode=RuntimeMode.SHADOW,
        symbol=proposal.symbol,
        setup_id=proposal.setup_id,
        intent_id=proposal.intent_id,
        payload={
            "approved": proposal.approved,
            "would_submit": proposal.would_submit,
            "reject_reasons": list(proposal.reject_reasons),
        },
    )


def _record_shadow_comparison_decision_events(
    *,
    database_url: str,
    command: str,
    run_id: str,
    batch: ShadowFillComparisonBatch,
) -> None:
    for comparison in batch.comparisons:
        _record_shadow_comparison_event(
            database_url=database_url,
            command=command,
            run_id=run_id,
            source_mode=batch.source_mode,
            comparison=comparison,
        )


def _record_shadow_comparison_event(
    *,
    database_url: str,
    command: str,
    run_id: str,
    source_mode: RuntimeMode,
    comparison: ShadowFillComparison,
) -> None:
    _record_runtime_event(
        database_url=database_url,
        command=command,
        event_type=RuntimeEventType.SHADOW_FILL_COMPARISON_RECORDED,
        run_id=run_id,
        mode=source_mode,
        symbol=comparison.symbol,
        setup_id=comparison.setup_id,
        intent_id=comparison.intent_id,
        payload={
            "status": comparison.status.value,
            "would_fill": comparison.would_fill,
            "would_remain_pending": comparison.would_remain_pending,
            "would_mark_setup_spent": comparison.would_mark_setup_spent,
            "session_date": None
            if comparison.session_date is None
            else comparison.session_date.isoformat(),
            "official_open": comparison.official_open,
            "reference_price": comparison.reference_price,
            "hypothetical_fill_price": comparison.hypothetical_fill_price,
            "transaction_cost": comparison.transaction_cost,
            "total_cost_bps": comparison.total_cost_bps,
            "slippage_alert": comparison.slippage_alert is not None,
            "detail": comparison.detail,
        },
    )


def _runtime_cycle_metrics(result: RuntimeCycleResult) -> dict[str, object]:
    if result.mode == RuntimeMode.PAPER:
        submissions = (
            () if result.paper_entry_batch is None else result.paper_entry_batch.submissions
        )
        return {
            "submitted_count": sum(1 for submission in submissions if submission.submitted),
            "rejected_count": sum(1 for submission in submissions if not submission.approved),
            "submission_count": len(submissions),
        }
    proposals = () if result.shadow_entry_batch is None else result.shadow_entry_batch.proposals
    return {
        "proposal_count": len(proposals),
        "would_submit_count": sum(1 for proposal in proposals if proposal.would_submit),
        "rejected_count": sum(1 for proposal in proposals if not proposal.approved),
    }


def _shadow_comparison_metrics(batch: ShadowFillComparisonBatch) -> dict[str, object]:
    return {
        "source_proposal_count": batch.source_proposal_count,
        "compared_proposal_count": batch.compared_proposal_count,
        "filled_count": batch.filled_count,
        "unfilled_count": batch.unfilled_count,
        "cancelled_count": batch.cancelled_count,
        "missing_market_data_count": batch.missing_market_data_count,
        "alert_count": len(batch.alerts),
    }


app = typer.Typer(no_args_is_help=True)


@app.callback()
def runtime_app() -> None:
    """Run Swingmachine operational cycles."""


@app.command("run-cycle")
def run_cycle_command(
    input_path: Path = typer.Option(..., "--input", exists=True, readable=True),
    output_path: Path = typer.Option(..., "--output"),
    mode: RuntimeMode = typer.Option(RuntimeMode.PAPER, "--mode"),
    config_path: Path = typer.Option(
        Path("swing_trading_bot_config_template_v2.yaml"),
        "--config",
        exists=True,
        readable=True,
    ),
    database_url: str = typer.Option(
        "sqlite+pysqlite:///./swingmachine_runtime.db",
        "--database-url",
    ),
) -> None:
    started_at = datetime.utcnow()
    config = load_strategy_config(config_path)
    runtime = build_runtime(config, database_url=database_url)
    cycle_input = load_runtime_cycle_input(input_path)
    result = runtime.run_cycle(cycle_input, mode=mode)
    write_runtime_cycle_result(result, output_path)
    metrics = _runtime_cycle_metrics(result)
    run_id = _record_runtime_run(
        database_url=database_url,
        command="run-cycle",
        started_at=started_at,
        status="SUCCEEDED",
        mode=mode,
        config_hash=config.config_hash(),
        input_path=input_path,
        output_path=output_path,
        metrics=metrics,
    )
    _record_runtime_event(
        database_url=database_url,
        command="run-cycle",
        event_type=RuntimeEventType.RUNTIME_CYCLE_RESULT_WRITTEN,
        run_id=run_id,
        mode=mode,
        output_path=output_path,
        payload=metrics,
    )
    _record_runtime_cycle_decision_events(
        database_url=database_url,
        command="run-cycle",
        run_id=run_id,
        result=result,
    )


@app.command("compare-shadow-fills")
def compare_shadow_fills_command(
    shadow_result_path: Path = typer.Option(..., "--shadow-result", exists=True, readable=True),
    market_data_path: Path = typer.Option(..., "--market-data", exists=True, readable=True),
    output_path: Path = typer.Option(..., "--output"),
    config_path: Path = typer.Option(
        Path("swing_trading_bot_config_template_v2.yaml"),
        "--config",
        exists=True,
        readable=True,
    ),
    database_url: str | None = typer.Option(None, "--database-url"),
) -> None:
    started_at = datetime.utcnow()
    config = load_strategy_config(config_path)
    runtime_cycle_result = load_runtime_cycle_result(shadow_result_path)
    market_data = load_market_data_frame(market_data_path)
    comparison_batch = compare_runtime_cycle_shadow_fills(
        runtime_cycle_result,
        market_data,
        config,
    )
    if database_url is not None:
        build_shadow_review_service(database_url=database_url).record_comparison_batch(
            comparison_batch
        )
    write_shadow_fill_comparison_batch(comparison_batch, output_path)
    if database_url is not None:
        metrics = _shadow_comparison_metrics(comparison_batch)
        run_id = _record_runtime_run(
            database_url=database_url,
            command="compare-shadow-fills",
            started_at=started_at,
            status="SUCCEEDED",
            mode=RuntimeMode.SHADOW,
            config_hash=config.config_hash(),
            input_path=shadow_result_path,
            output_path=output_path,
            detail=f"market_data={market_data_path}",
            metrics=metrics,
        )
        _record_runtime_event(
            database_url=database_url,
            command="compare-shadow-fills",
            event_type=RuntimeEventType.SHADOW_COMPARISON_WRITTEN,
            run_id=run_id,
            mode=RuntimeMode.SHADOW,
            output_path=output_path,
            payload=metrics,
        )
        _record_shadow_comparison_decision_events(
            database_url=database_url,
            command="compare-shadow-fills",
            run_id=run_id,
            batch=comparison_batch,
        )


@app.command("summarize-shadow-fills")
def summarize_shadow_fills_command(
    output_path: Path = typer.Option(..., "--output"),
    database_url: str = typer.Option(
        "sqlite+pysqlite:///./swingmachine_runtime.db",
        "--database-url",
    ),
    symbol: str | None = typer.Option(None, "--symbol"),
    regime_state: RegimeState | None = typer.Option(None, "--regime-state"),
    date_from: str | None = typer.Option(None, "--date-from"),
    date_to: str | None = typer.Option(None, "--date-to"),
) -> None:
    started_at = datetime.utcnow()
    review_service = build_shadow_review_service(database_url=database_url)
    summary = review_service.summarize_comparisons(
        symbol=symbol,
        regime_state=regime_state,
        date_from=_parse_iso_date(date_from),
        date_to=_parse_iso_date(date_to),
    )
    _write_payload(summary, output_path)
    metrics: dict[str, object] = {"record_count": _shadow_summary_record_count(summary)}
    run_id = _record_runtime_run(
        database_url=database_url,
        command="summarize-shadow-fills",
        started_at=started_at,
        status="SUCCEEDED",
        output_path=output_path,
        metrics=metrics,
    )
    _record_runtime_event(
        database_url=database_url,
        command="summarize-shadow-fills",
        event_type=RuntimeEventType.SHADOW_SUMMARY_WRITTEN,
        run_id=run_id,
        output_path=output_path,
        payload=metrics,
    )


@app.command("summarize-shadow-comparison-snapshots")
def summarize_shadow_comparison_snapshots_command(
    output_path: Path = typer.Option(..., "--output"),
    database_url: str = typer.Option(
        "sqlite+pysqlite:///./swingmachine_runtime.db",
        "--database-url",
    ),
    symbol: str | None = typer.Option(None, "--symbol"),
    regime_state: RegimeState | None = typer.Option(None, "--regime-state"),
    date_from: str | None = typer.Option(None, "--date-from"),
    date_to: str | None = typer.Option(None, "--date-to"),
) -> None:
    started_at = datetime.utcnow()
    review_service = build_shadow_review_service(database_url=database_url)
    summary = review_service.summarize_comparison_snapshots(
        symbol=symbol,
        regime_state=regime_state,
        date_from=_parse_iso_date(date_from),
        date_to=_parse_iso_date(date_to),
    )
    _write_payload(summary, output_path)
    metrics: dict[str, object] = {"record_count": _shadow_summary_record_count(summary)}
    run_id = _record_runtime_run(
        database_url=database_url,
        command="summarize-shadow-comparison-snapshots",
        started_at=started_at,
        status="SUCCEEDED",
        output_path=output_path,
        metrics=metrics,
    )
    _record_runtime_event(
        database_url=database_url,
        command="summarize-shadow-comparison-snapshots",
        event_type=RuntimeEventType.SHADOW_SUMMARY_WRITTEN,
        run_id=run_id,
        output_path=output_path,
        payload=metrics,
    )


@app.command("summarize-paper-shadow-audit")
def summarize_paper_shadow_audit_command(
    output_path: Path = typer.Option(..., "--output"),
    database_url: str = typer.Option(
        "sqlite+pysqlite:///./swingmachine_runtime.db",
        "--database-url",
    ),
    symbol: str | None = typer.Option(None, "--symbol"),
    regime_state: RegimeState | None = typer.Option(None, "--regime-state"),
    date_from: str | None = typer.Option(None, "--date-from"),
    date_to: str | None = typer.Option(None, "--date-to"),
) -> None:
    started_at = datetime.utcnow()
    audit_service = build_paper_shadow_audit_service(database_url=database_url)
    records = audit_service.load_records(
        symbol=symbol,
        regime_state=regime_state,
        date_from=_parse_iso_date(date_from),
        date_to=_parse_iso_date(date_to),
    )
    snapshot_batch_id = audit_service.record_snapshot_batch(records)
    summary = audit_service.summarize_record_snapshots(snapshot_batch_id=snapshot_batch_id)
    _write_payload(summary, output_path)
    metrics: dict[str, object] = {
        "record_count": _audit_summary_record_count(summary),
        "snapshot_batch_id": snapshot_batch_id,
    }
    run_id = _record_runtime_run(
        database_url=database_url,
        command="summarize-paper-shadow-audit",
        started_at=started_at,
        status="SUCCEEDED",
        output_path=output_path,
        metrics=metrics,
    )
    _record_runtime_event(
        database_url=database_url,
        command="summarize-paper-shadow-audit",
        event_type=RuntimeEventType.PAPER_SHADOW_AUDIT_SUMMARY_WRITTEN,
        run_id=run_id,
        output_path=output_path,
        payload=metrics,
    )


@app.command("summarize-paper-shadow-audit-snapshots")
def summarize_paper_shadow_audit_snapshots_command(
    output_path: Path = typer.Option(..., "--output"),
    database_url: str = typer.Option(
        "sqlite+pysqlite:///./swingmachine_runtime.db",
        "--database-url",
    ),
    snapshot_batch_id: str | None = typer.Option(None, "--snapshot-batch-id"),
    symbol: str | None = typer.Option(None, "--symbol"),
    regime_state: RegimeState | None = typer.Option(None, "--regime-state"),
    recorded_from: str | None = typer.Option(None, "--recorded-from"),
    recorded_to: str | None = typer.Option(None, "--recorded-to"),
) -> None:
    started_at = datetime.utcnow()
    audit_service = build_paper_shadow_audit_service(database_url=database_url)
    summary = audit_service.summarize_record_snapshots(
        snapshot_batch_id=snapshot_batch_id,
        symbol=symbol,
        regime_state=regime_state,
        recorded_from=_parse_iso_date(recorded_from),
        recorded_to=_parse_iso_date(recorded_to),
    )
    _write_payload(summary, output_path)
    metrics: dict[str, object] = {
        "record_count": _audit_summary_record_count(summary),
    }
    if snapshot_batch_id is not None:
        metrics["snapshot_batch_id"] = snapshot_batch_id
    run_id = _record_runtime_run(
        database_url=database_url,
        command="summarize-paper-shadow-audit-snapshots",
        started_at=started_at,
        status="SUCCEEDED",
        output_path=output_path,
        metrics=metrics,
    )
    _record_runtime_event(
        database_url=database_url,
        command="summarize-paper-shadow-audit-snapshots",
        event_type=RuntimeEventType.PAPER_SHADOW_AUDIT_SUMMARY_WRITTEN,
        run_id=run_id,
        output_path=output_path,
        payload=metrics,
    )


@app.command("run-audit-report-job")
def run_audit_report_job_command(
    output_dir: Path = typer.Option(..., "--output-dir"),
    database_url: str = typer.Option(
        "sqlite+pysqlite:///./swingmachine_runtime.db",
        "--database-url",
    ),
    as_of: str | None = typer.Option(None, "--as-of"),
    lookback_days: str = typer.Option(
        ",".join(str(days) for days in DEFAULT_REPORT_LOOKBACK_DAYS),
        "--lookback-days",
    ),
    symbol: str | None = typer.Option(None, "--symbol"),
    regime_state: RegimeState | None = typer.Option(None, "--regime-state"),
    output_format: str = typer.Option("json", "--format"),
    prefix: str = typer.Option("audit_report", "--prefix"),
    exception_limit: int = typer.Option(10, "--exception-limit"),
    write_latest: bool = typer.Option(True, "--write-latest/--no-write-latest"),
) -> None:
    started_at = datetime.utcnow()
    normalized_format = output_format.lower()
    if normalized_format not in {"json", "yaml"}:
        raise typer.BadParameter("format must be one of: json, yaml")

    as_of_date = _parse_iso_date(as_of) or date.today()
    report = build_rolling_audit_report_service(database_url=database_url).build_report(
        as_of_date=as_of_date,
        lookback_days=_parse_lookback_days(lookback_days),
        symbol=symbol,
        regime_state=regime_state,
        exception_limit=exception_limit,
    )
    suffix = ".json" if normalized_format == "json" else ".yaml"
    payload = report.model_dump(mode="json")
    dated_output_path = output_dir / f"{prefix}_{as_of_date.isoformat()}{suffix}"
    _write_payload(payload, dated_output_path)
    if write_latest:
        latest_output_path = output_dir / f"{prefix}_latest{suffix}"
        _write_payload(payload, latest_output_path)
    metrics: dict[str, object] = {
        "window_count": len(report.windows),
        "exception_limit": exception_limit,
    }
    run_id = _record_runtime_run(
        database_url=database_url,
        command="run-audit-report-job",
        started_at=started_at,
        status="SUCCEEDED",
        output_path=dated_output_path,
        metrics=metrics,
    )
    _record_runtime_event(
        database_url=database_url,
        command="run-audit-report-job",
        event_type=RuntimeEventType.AUDIT_REPORT_WRITTEN,
        run_id=run_id,
        output_path=dated_output_path,
        payload=metrics,
    )


@app.command("run-review-report")
def run_review_report_command(
    output_path: Path = typer.Option(..., "--output"),
    database_url: str = typer.Option(
        "sqlite+pysqlite:///./swingmachine_runtime.db",
        "--database-url",
    ),
    as_of: str | None = typer.Option(None, "--as-of"),
    lookback_days: str = typer.Option(
        ",".join(str(days) for days in DEFAULT_REPORT_LOOKBACK_DAYS),
        "--lookback-days",
    ),
    symbol: str | None = typer.Option(None, "--symbol"),
    regime_state: RegimeState | None = typer.Option(None, "--regime-state"),
    event_limit: int = typer.Option(100, "--event-limit"),
    run_limit: int = typer.Option(20, "--run-limit"),
    exception_limit: int = typer.Option(10, "--exception-limit"),
    output_format: str = typer.Option("auto", "--format"),
    html_row_limit: int = typer.Option(25, "--html-row-limit"),
    min_alignment_rate: float = typer.Option(0.95, "--min-alignment-rate"),
    max_divergent_count: int = typer.Option(0, "--max-divergent-count"),
    max_shadow_slippage_alert_rate: float = typer.Option(
        0.0,
        "--max-shadow-slippage-alert-rate",
    ),
    max_missing_market_data_count: int = typer.Option(0, "--max-missing-market-data-count"),
    require_runtime_runs: bool = typer.Option(
        True,
        "--require-runtime-runs/--no-require-runtime-runs",
    ),
    require_decision_events: bool = typer.Option(
        True,
        "--require-decision-events/--no-require-decision-events",
    ),
    require_shadow_snapshots: bool = typer.Option(
        True,
        "--require-shadow-snapshots/--no-require-shadow-snapshots",
    ),
    require_audit_snapshots: bool = typer.Option(
        True,
        "--require-audit-snapshots/--no-require-audit-snapshots",
    ),
    replay_output_dir: Path | None = typer.Option(
        None,
        "--replay-output-dir",
        exists=True,
        file_okay=False,
        readable=True,
        help="Optional historical replay artifact directory to include in review checks.",
    ),
) -> None:
    started_at = datetime.utcnow()
    resolved_format = _resolve_output_format(output_path, output_format)
    if html_row_limit < 0:
        raise typer.BadParameter("html-row-limit must be non-negative")
    review_thresholds = OperatorReviewThresholds(
        min_alignment_rate=_validate_percent_option(
            min_alignment_rate,
            option_name="min-alignment-rate",
        ),
        max_divergent_count=_validate_non_negative_int_option(
            max_divergent_count,
            option_name="max-divergent-count",
        ),
        max_shadow_slippage_alert_rate=_validate_percent_option(
            max_shadow_slippage_alert_rate,
            option_name="max-shadow-slippage-alert-rate",
        ),
        max_missing_market_data_count=_validate_non_negative_int_option(
            max_missing_market_data_count,
            option_name="max-missing-market-data-count",
        ),
        require_runtime_runs=require_runtime_runs,
        require_decision_events=require_decision_events,
        require_shadow_snapshots=require_shadow_snapshots,
        require_paper_shadow_audit_snapshots=require_audit_snapshots,
    )

    as_of_date = _parse_iso_date(as_of) or date.today()
    report = build_operator_review_report_service(database_url=database_url).build_report(
        as_of_date=as_of_date,
        lookback_days=_parse_lookback_days(lookback_days),
        symbol=symbol,
        regime_state=regime_state,
        event_limit=event_limit,
        run_limit=run_limit,
        exception_limit=exception_limit,
        review_thresholds=review_thresholds,
        replay_artifact_dirs=() if replay_output_dir is None else (replay_output_dir,),
    )
    payload = report.model_dump(mode="json")
    if resolved_format == "html":
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            render_operator_review_html(report, row_limit=html_row_limit),
            encoding="utf-8",
        )
    else:
        _write_payload_as_format(payload, output_path, output_format=resolved_format)

    metrics = operator_review_run_metrics(report) | {
        "exception_limit": exception_limit,
        "output_format": resolved_format,
        "html_row_limit": html_row_limit,
    }
    run_id = _record_runtime_run(
        database_url=database_url,
        command="run-review-report",
        started_at=started_at,
        status="SUCCEEDED",
        output_path=output_path,
        metrics=metrics,
    )
    _record_runtime_event(
        database_url=database_url,
        command="run-review-report",
        event_type=RuntimeEventType.REVIEW_REPORT_WRITTEN,
        run_id=run_id,
        output_path=output_path,
        payload=metrics,
    )


@app.command("run-paper-shadow-audit")
def run_paper_shadow_audit_command(
    input_path: Path = typer.Option(..., "--input", exists=True, readable=True),
    market_data_path: Path = typer.Option(..., "--market-data", exists=True, readable=True),
    output_dir: Path = typer.Option(..., "--output-dir"),
    config_path: Path = typer.Option(
        Path("swing_trading_bot_config_template_v2.yaml"),
        "--config",
        exists=True,
        readable=True,
    ),
    database_url: str = typer.Option(
        "sqlite+pysqlite:///./swingmachine_runtime.db",
        "--database-url",
    ),
    as_of: str | None = typer.Option(None, "--as-of"),
    lookback_days: str = typer.Option(
        ",".join(str(days) for days in DEFAULT_REPORT_LOOKBACK_DAYS),
        "--lookback-days",
    ),
) -> None:
    started_at = datetime.utcnow()
    output_dir.mkdir(parents=True, exist_ok=True)
    config = load_strategy_config(config_path)
    cycle_input = load_runtime_cycle_input(input_path)
    market_data = load_market_data_frame(market_data_path)
    runtime = build_runtime(config, database_url=database_url)

    shadow_result = runtime.run_cycle(cycle_input, mode=RuntimeMode.SHADOW)
    shadow_result_path = output_dir / "shadow_result.json"
    write_runtime_cycle_result(shadow_result, shadow_result_path)

    comparison_batch = compare_runtime_cycle_shadow_fills(
        shadow_result,
        market_data,
        config,
    )
    build_shadow_review_service(database_url=database_url).record_comparison_batch(comparison_batch)
    shadow_comparison_path = output_dir / "shadow_comparison.json"
    write_shadow_fill_comparison_batch(comparison_batch, shadow_comparison_path)

    paper_result = runtime.run_cycle(cycle_input, mode=RuntimeMode.PAPER)
    paper_result_path = output_dir / "paper_result.json"
    write_runtime_cycle_result(paper_result, paper_result_path)

    shadow_summary = build_shadow_review_service(database_url=database_url).summarize_comparisons()
    shadow_summary_path = output_dir / "shadow_summary.json"
    _write_payload(shadow_summary, shadow_summary_path)

    audit_service = build_paper_shadow_audit_service(database_url=database_url)
    audit_records = audit_service.load_records()
    audit_snapshot_batch_id = audit_service.record_snapshot_batch(audit_records)
    audit_summary = audit_service.summarize_record_snapshots(
        snapshot_batch_id=audit_snapshot_batch_id
    )
    audit_summary_path = output_dir / "paper_shadow_audit_summary.json"
    _write_payload(audit_summary, audit_summary_path)

    as_of_date = _parse_iso_date(as_of) or cycle_input.as_of.date()
    audit_report = build_rolling_audit_report_service(database_url=database_url).build_report(
        as_of_date=as_of_date,
        lookback_days=_parse_lookback_days(lookback_days),
    )
    audit_report_path = output_dir / f"audit_report_{as_of_date.isoformat()}.json"
    _write_payload(audit_report.model_dump(mode="json"), audit_report_path)
    _write_payload(audit_report.model_dump(mode="json"), output_dir / "audit_report_latest.json")

    paper_metrics = _runtime_cycle_metrics(paper_result)
    shadow_metrics = _runtime_cycle_metrics(shadow_result)
    shadow_comparison_metrics = _shadow_comparison_metrics(comparison_batch)
    shadow_summary_count = _shadow_summary_record_count(shadow_summary)
    metrics: dict[str, object] = {
        "paper": paper_metrics,
        "shadow": shadow_metrics,
        "shadow_comparison": shadow_comparison_metrics,
        "audit_record_count": _audit_summary_record_count(audit_summary),
        "audit_snapshot_batch_id": audit_snapshot_batch_id,
    }
    run_id = _record_runtime_run(
        database_url=database_url,
        command="run-paper-shadow-audit",
        started_at=started_at,
        status="SUCCEEDED",
        config_hash=config.config_hash(),
        input_path=input_path,
        output_path=output_dir,
        detail=f"market_data={market_data_path}",
        metrics=metrics,
    )
    workflow_summary = {
        "run_id": run_id,
        "status": "SUCCEEDED",
        "outputs": {
            "shadow_result": str(shadow_result_path),
            "shadow_comparison": str(shadow_comparison_path),
            "paper_result": str(paper_result_path),
            "shadow_summary": str(shadow_summary_path),
            "paper_shadow_audit_summary": str(audit_summary_path),
            "audit_report": str(audit_report_path),
            "audit_report_latest": str(output_dir / "audit_report_latest.json"),
        },
        "metrics": metrics,
    }
    _write_payload(workflow_summary, output_dir / "workflow_summary.json")
    _record_runtime_event(
        database_url=database_url,
        command="run-paper-shadow-audit",
        event_type=RuntimeEventType.RUNTIME_CYCLE_RESULT_WRITTEN,
        run_id=run_id,
        mode=RuntimeMode.SHADOW,
        output_path=shadow_result_path,
        payload=shadow_metrics,
    )
    _record_runtime_cycle_decision_events(
        database_url=database_url,
        command="run-paper-shadow-audit",
        run_id=run_id,
        result=shadow_result,
    )
    _record_runtime_event(
        database_url=database_url,
        command="run-paper-shadow-audit",
        event_type=RuntimeEventType.SHADOW_COMPARISON_WRITTEN,
        run_id=run_id,
        mode=RuntimeMode.SHADOW,
        output_path=shadow_comparison_path,
        payload=shadow_comparison_metrics,
    )
    _record_shadow_comparison_decision_events(
        database_url=database_url,
        command="run-paper-shadow-audit",
        run_id=run_id,
        batch=comparison_batch,
    )
    _record_runtime_event(
        database_url=database_url,
        command="run-paper-shadow-audit",
        event_type=RuntimeEventType.RUNTIME_CYCLE_RESULT_WRITTEN,
        run_id=run_id,
        mode=RuntimeMode.PAPER,
        output_path=paper_result_path,
        payload=paper_metrics,
    )
    _record_runtime_cycle_decision_events(
        database_url=database_url,
        command="run-paper-shadow-audit",
        run_id=run_id,
        result=paper_result,
    )
    _record_runtime_event(
        database_url=database_url,
        command="run-paper-shadow-audit",
        event_type=RuntimeEventType.SHADOW_SUMMARY_WRITTEN,
        run_id=run_id,
        output_path=shadow_summary_path,
        payload={"record_count": shadow_summary_count},
    )
    _record_runtime_event(
        database_url=database_url,
        command="run-paper-shadow-audit",
        event_type=RuntimeEventType.PAPER_SHADOW_AUDIT_SUMMARY_WRITTEN,
        run_id=run_id,
        output_path=audit_summary_path,
        payload={
            "record_count": _audit_summary_record_count(audit_summary),
            "snapshot_batch_id": audit_snapshot_batch_id,
        },
    )
    _record_runtime_event(
        database_url=database_url,
        command="run-paper-shadow-audit",
        event_type=RuntimeEventType.AUDIT_REPORT_WRITTEN,
        run_id=run_id,
        output_path=audit_report_path,
        payload={"window_count": len(audit_report.windows)},
    )
    _record_runtime_event(
        database_url=database_url,
        command="run-paper-shadow-audit",
        event_type=RuntimeEventType.WORKFLOW_SUMMARY_WRITTEN,
        run_id=run_id,
        output_path=output_dir / "workflow_summary.json",
        payload=metrics,
    )


@app.command("run-historical-replay")
def run_historical_replay_command(
    manifest_path: Path = typer.Option(..., "--manifest", exists=True, readable=True),
    output_dir: Path = typer.Option(..., "--output-dir"),
    config_path: Path = typer.Option(
        Path("swing_trading_bot_config_template_v2.yaml"),
        "--config",
        exists=True,
        readable=True,
    ),
    database_url: str | None = typer.Option(
        None,
        "--database-url",
        help="Defaults to a SQLite database inside --output-dir.",
    ),
    initial_equity: float = typer.Option(100_000.0, "--initial-equity"),
) -> None:
    if initial_equity <= 0:
        raise typer.BadParameter("initial-equity must be positive")

    from swingmachine.replay import (
        historical_replay_run_metrics,
        run_historical_manifest_replay,
    )

    started_at = datetime.utcnow()
    output_dir.mkdir(parents=True, exist_ok=True)
    database_url_source = "provided" if database_url is not None else "output_dir_default"
    resolved_database_url = database_url or (
        f"sqlite+pysqlite:///{output_dir / 'historical_replay_runtime.db'}"
    )
    config = load_strategy_config(config_path)
    result = run_historical_manifest_replay(
        manifest_path,
        config,
        database_url=resolved_database_url,
        output_dir=output_dir,
        initial_equity=initial_equity,
        baseline_config_path=config_path,
    )
    metrics = historical_replay_run_metrics(result)
    run_status = "FAILED" if result.status is ReviewStatus.FAIL else "SUCCEEDED"
    run_id = _record_runtime_run(
        database_url=resolved_database_url,
        command="run-historical-replay",
        started_at=started_at,
        status=run_status,
        config_hash=config.config_hash(),
        input_path=manifest_path,
        output_path=output_dir,
        detail=f"replay_status={result.status.value}",
        metrics=metrics,
    )
    workflow_summary_path = output_dir / "workflow_summary.json"
    workflow_summary = {
        "run_id": run_id,
        "status": run_status,
        "replay_status": result.status.value,
        "database_url_source": database_url_source,
        "outputs": result.artifact_paths,
        "metrics": metrics,
    }
    _write_payload(workflow_summary, workflow_summary_path)
    replay_summary_path = Path(result.artifact_paths["replay_summary"])
    _record_runtime_event(
        database_url=resolved_database_url,
        command="run-historical-replay",
        event_type=RuntimeEventType.HISTORICAL_REPLAY_WRITTEN,
        run_id=run_id,
        output_path=replay_summary_path,
        payload=metrics,
    )
    _record_runtime_event(
        database_url=resolved_database_url,
        command="run-historical-replay",
        event_type=RuntimeEventType.WORKFLOW_SUMMARY_WRITTEN,
        run_id=run_id,
        output_path=workflow_summary_path,
        payload=metrics,
    )


@app.command("run-historical-scanner-replay")
def run_historical_scanner_replay_command(
    manifest_path: Path = typer.Option(..., "--manifest", exists=True, readable=True),
    output_dir: Path = typer.Option(..., "--output-dir"),
    config_path: Path = typer.Option(
        Path("swing_trading_bot_config_template_v2.yaml"),
        "--config",
        exists=True,
        readable=True,
    ),
    database_url: str | None = typer.Option(
        None,
        "--database-url",
        help="Defaults to a SQLite database inside --output-dir.",
    ),
    initial_equity: float = typer.Option(100_000.0, "--initial-equity"),
) -> None:
    if initial_equity <= 0:
        raise typer.BadParameter("initial-equity must be positive")

    from swingmachine.replay import run_historical_scanner_replay

    started_at = datetime.utcnow()
    output_dir.mkdir(parents=True, exist_ok=True)
    database_url_source = "provided" if database_url is not None else "output_dir_default"
    resolved_database_url = database_url or (
        f"sqlite+pysqlite:///{output_dir / 'historical_scanner_replay_runtime.db'}"
    )
    config = load_strategy_config(config_path)
    summary = run_historical_scanner_replay(
        manifest_path,
        config,
        output_dir=output_dir,
        initial_equity=initial_equity,
    )
    metrics: dict[str, object] = {
        "panel_id": summary.panel_id,
        "status": summary.status.value,
        "eligible_signal_session_count": summary.eligible_signal_session_count,
        "processed_signal_session_count": summary.processed_signal_session_count,
        "skipped_session_count": summary.skipped_session_count,
        "total_decision_traces": summary.total_decision_traces,
        "total_candidates": summary.total_candidates,
        "total_setups": summary.total_setups,
        "total_rejections": summary.total_rejections,
        "sessions_with_setups": summary.sessions_with_setups,
        "sessions_without_setups": summary.sessions_without_setups,
    }
    run_status = "FAILED" if summary.status is ReviewStatus.FAIL else "SUCCEEDED"
    run_id = _record_runtime_run(
        database_url=resolved_database_url,
        command="run-historical-scanner-replay",
        started_at=started_at,
        status=run_status,
        config_hash=config.config_hash(),
        input_path=manifest_path,
        output_path=output_dir,
        detail=f"scanner_status={summary.status.value}",
        metrics=metrics,
    )
    workflow_summary_path = output_dir / "workflow_summary.json"
    workflow_summary = {
        "run_id": run_id,
        "status": run_status,
        "scanner_status": summary.status.value,
        "database_url_source": database_url_source,
        "outputs": {
            "scanner_replay_summary": str(output_dir / "scanner_replay_summary.json"),
            "scanner_session_results": str(output_dir / "scanner_session_results.json"),
            "scanner_decision_density": str(output_dir / "scanner_decision_density.json"),
            "scanner_rejection_reasons": str(output_dir / "scanner_rejection_reasons.json"),
            "scanner_material_decisions": str(output_dir / "scanner_material_decisions.json"),
            "scanner_baseline_report_package": str(
                output_dir / "scanner_baseline_report_package.json"
            ),
            "scanner_artifact_manifest": str(output_dir / "scanner_artifact_manifest.json"),
        },
        "metrics": metrics,
    }
    _write_payload(workflow_summary, workflow_summary_path)
    _record_runtime_event(
        database_url=resolved_database_url,
        command="run-historical-scanner-replay",
        event_type=RuntimeEventType.WORKFLOW_SUMMARY_WRITTEN,
        run_id=run_id,
        output_path=workflow_summary_path,
        payload=metrics,
    )
    if summary.status is ReviewStatus.FAIL:
        raise typer.Exit(1)


@app.command("run-historical-portfolio-lifecycle-replay")
def run_historical_portfolio_lifecycle_replay_command(
    manifest_path: Path = typer.Option(..., "--manifest", exists=True, readable=True),
    output_dir: Path = typer.Option(..., "--output-dir"),
    config_path: Path = typer.Option(
        Path("swing_trading_bot_config_template_v2.yaml"),
        "--config",
        exists=True,
        readable=True,
    ),
    database_url: str | None = typer.Option(
        None,
        "--database-url",
        help="Defaults to a SQLite run-history database inside --output-dir.",
    ),
    initial_equity: float = typer.Option(100_000.0, "--initial-equity"),
) -> None:
    if initial_equity <= 0:
        raise typer.BadParameter("initial-equity must be positive")

    from swingmachine.replay import run_historical_portfolio_lifecycle_replay

    started_at = datetime.utcnow()
    output_dir.mkdir(parents=True, exist_ok=True)
    database_url_source = "provided" if database_url is not None else "output_dir_default"
    resolved_database_url = database_url or (
        f"sqlite+pysqlite:///{output_dir / 'historical_portfolio_lifecycle_replay.db'}"
    )
    config = load_strategy_config(config_path)
    package = run_historical_portfolio_lifecycle_replay(
        manifest_path,
        config,
        output_dir=output_dir,
        initial_equity=initial_equity,
    )
    metrics: dict[str, object] = {
        "panel_id": package.summary.panel_id,
        "status": package.summary.status.value,
        "processed_session_count": package.summary.processed_session_count,
        "transition_count": package.summary.transition_count,
        "position_snapshot_count": package.summary.position_snapshot_count,
        "pending_order_snapshot_count": package.summary.pending_order_snapshot_count,
        "exposure_snapshot_count": package.summary.exposure_snapshot_count,
        "entry_submitted_count": package.summary.entry_submitted_count,
        "entry_filled_count": package.summary.entry_filled_count,
        "entry_cancelled_count": package.summary.entry_cancelled_count,
        "exit_submitted_count": package.summary.exit_submitted_count,
        "exit_filled_count": package.summary.exit_filled_count,
        "reconciliation_status": package.reconciliation.status.value,
        "reconciliation_failure_count": len(package.reconciliation.failures),
        "reconciliation_warning_count": len(package.reconciliation.warnings),
    }
    run_status = "FAILED" if package.summary.status is ReviewStatus.FAIL else "SUCCEEDED"
    run_id = _record_runtime_run(
        database_url=resolved_database_url,
        command="run-historical-portfolio-lifecycle-replay",
        started_at=started_at,
        status=run_status,
        config_hash=config.config_hash(),
        input_path=manifest_path,
        output_path=output_dir,
        detail=f"lifecycle_status={package.summary.status.value}",
        metrics=metrics,
    )
    workflow_summary_path = output_dir / "workflow_summary.json"
    workflow_summary = {
        "run_id": run_id,
        "status": run_status,
        "lifecycle_status": package.summary.status.value,
        "database_url_source": database_url_source,
        "outputs": {
            "portfolio_lifecycle_replay_summary": str(
                output_dir / "portfolio_lifecycle_replay_summary.json"
            ),
            "portfolio_lifecycle_session_states": str(
                output_dir / "portfolio_lifecycle_session_states.json"
            ),
            "portfolio_lifecycle_transitions": str(
                output_dir / "portfolio_lifecycle_transitions.json"
            ),
            "portfolio_lifecycle_positions": str(
                output_dir / "portfolio_lifecycle_positions.json"
            ),
            "portfolio_lifecycle_pending_orders": str(
                output_dir / "portfolio_lifecycle_pending_orders.json"
            ),
            "portfolio_lifecycle_exposure": str(
                output_dir / "portfolio_lifecycle_exposure.json"
            ),
            "portfolio_lifecycle_reconciliation": str(
                output_dir / "portfolio_lifecycle_reconciliation.json"
            ),
            "portfolio_lifecycle_baseline_package": str(
                output_dir / "portfolio_lifecycle_baseline_package.json"
            ),
            "portfolio_lifecycle_artifact_manifest": str(
                output_dir / "portfolio_lifecycle_artifact_manifest.json"
            ),
        },
        "metrics": metrics,
    }
    _write_payload(workflow_summary, workflow_summary_path)
    _record_runtime_event(
        database_url=resolved_database_url,
        command="run-historical-portfolio-lifecycle-replay",
        event_type=RuntimeEventType.WORKFLOW_SUMMARY_WRITTEN,
        run_id=run_id,
        output_path=workflow_summary_path,
        payload=metrics,
    )
    if package.summary.status is ReviewStatus.FAIL:
        raise typer.Exit(1)


@app.command("preflight-selected-period-qualification")
def preflight_selected_period_qualification_command(
    plan_path: Path = typer.Option(
        Path("config/swing_machine_v0_1_selected_periods.yaml"),
        "--plan",
        exists=True,
        readable=True,
    ),
    output_path: Path = typer.Option(..., "--output"),
    data_manifest: list[str] | None = typer.Option(
        None,
        "--data-manifest",
        help="Repeat as PERIOD_ID=MANIFEST_PATH for every selected qualification period.",
    ),
) -> None:
    from swingmachine.baseline_readiness import (
        preflight_selected_qualification_plan,
        write_selected_qualification_preflight_json,
    )

    result = preflight_selected_qualification_plan(
        plan_path,
        data_manifest_by_period=_parse_selected_period_data_manifests(data_manifest or ()),
    )
    write_selected_qualification_preflight_json(result, output_path)
    if not result.passed:
        raise typer.Exit(code=1)


@app.command("build-historical-panel-manifest")
def build_historical_panel_manifest_command(
    output_path: Path = typer.Option(..., "--output"),
    panel_id: str = typer.Option(..., "--panel-id"),
    ohlcv_path: Path = typer.Option(..., "--ohlcv", exists=True, readable=True),
    symbol_reference_path: Path = typer.Option(
        ...,
        "--symbol-reference",
        exists=True,
        readable=True,
    ),
    corporate_actions_path: Path = typer.Option(
        ...,
        "--corporate-actions",
        exists=True,
        readable=True,
    ),
    earnings_events_path: Path = typer.Option(
        ...,
        "--earnings-events",
        exists=True,
        readable=True,
    ),
    features_path: Path | None = typer.Option(
        None,
        "--features",
        exists=True,
        readable=True,
    ),
    base_path: Path | None = typer.Option(
        None,
        "--base-path",
        exists=True,
        file_okay=False,
    ),
    description: str | None = typer.Option(None, "--description"),
    calendar: str = typer.Option("WEEKDAY", "--calendar"),
    timezone: str = typer.Option("Europe/London", "--timezone"),
    feature_coverage_scope: str = typer.Option(
        "tradable_reference",
        "--feature-coverage-scope",
    ),
) -> None:
    from swingmachine.data_contracts import write_historical_panel_manifest_from_files

    write_historical_panel_manifest_from_files(
        output_path,
        panel_id=panel_id,
        ohlcv_path=ohlcv_path,
        symbol_reference_path=symbol_reference_path,
        corporate_actions_path=corporate_actions_path,
        earnings_events_path=earnings_events_path,
        features_path=features_path,
        base_path=base_path,
        description=description,
        calendar=calendar,
        timezone=timezone,
        feature_coverage_scope=feature_coverage_scope,  # type: ignore[arg-type]
    )


@app.command("preflight-selected-period-data-inputs")
def preflight_selected_period_data_inputs_command(
    input_plan_path: Path = typer.Option(
        Path("config/swing_machine_v0_1_selected_period_data_inputs.example.yaml"),
        "--input-plan",
        exists=True,
        readable=True,
    ),
    output_path: Path = typer.Option(..., "--output"),
    selected_period_plan_path: Path | None = typer.Option(
        None,
        "--selected-period-plan",
        exists=True,
        readable=True,
    ),
) -> None:
    from swingmachine.qualification_inputs import (
        preflight_selected_period_data_inputs,
        write_selected_period_data_input_preflight_json,
    )

    result = preflight_selected_period_data_inputs(
        input_plan_path,
        selected_period_plan_path=selected_period_plan_path,
    )
    write_selected_period_data_input_preflight_json(result, output_path)
    if not result.passed:
        raise typer.Exit(code=1)


@app.command("build-selected-period-data-input-plan")
def build_selected_period_data_input_plan_command(
    data_root: Path = typer.Option(..., "--data-root", exists=True, file_okay=False),
    output_path: Path = typer.Option(..., "--output"),
    selected_period_plan_path: Path = typer.Option(
        Path("config/swing_machine_v0_1_selected_periods.yaml"),
        "--selected-period-plan",
        exists=True,
        readable=True,
    ),
) -> None:
    from swingmachine.qualification_inputs import (
        build_selected_period_data_input_plan_from_root,
        write_selected_period_data_input_plan_yaml,
    )

    plan = build_selected_period_data_input_plan_from_root(
        data_root,
        selected_period_plan_path=selected_period_plan_path,
    )
    write_selected_period_data_input_plan_yaml(plan, output_path)


@app.command("build-selected-period-manifests")
def build_selected_period_manifests_command(
    input_plan_path: Path = typer.Option(..., "--input-plan", exists=True, readable=True),
    output_root: Path = typer.Option(..., "--output-root"),
    summary_output_path: Path | None = typer.Option(None, "--summary-output"),
) -> None:
    from swingmachine.baseline import load_swing_selected_qualification_plan
    from swingmachine.data_contracts import write_historical_panel_manifest_from_files
    from swingmachine.qualification_inputs import load_selected_period_data_input_plan

    input_plan = load_selected_period_data_input_plan(input_plan_path)
    selected_period_by_id = {
        period.period_id: period
        for period in load_swing_selected_qualification_plan(
            input_plan.selected_period_plan_path
        ).periods
    }
    manifest_paths: dict[str, str] = {}
    for period in input_plan.periods:
        selected_period = selected_period_by_id.get(period.period_id)
        manifest_path = output_root / period.period_id / "manifest.yaml"
        write_historical_panel_manifest_from_files(
            manifest_path,
            panel_id=period.period_id,
            ohlcv_path=period.ohlcv_path,
            symbol_reference_path=period.symbol_reference_path,
            corporate_actions_path=period.corporate_actions_path,
            earnings_events_path=period.earnings_events_path,
            features_path=period.features_path,
            calendar="US_EQUITY",
            description=f"Swing v0.1 selected-period manifest: {period.period_id}",
            replay_start_session=None if selected_period is None else selected_period.start_date,
            replay_end_session=None if selected_period is None else selected_period.end_date,
        )
        manifest_paths[period.period_id] = str(manifest_path)
    if summary_output_path is not None:
        _write_payload(
            {
                "baseline_id": "swing_machine_v0_1",
                "input_plan_path": str(input_plan_path),
                "manifest_count": len(manifest_paths),
                "manifest_paths": manifest_paths,
            },
            summary_output_path,
        )


@app.command("index-qualification-evidence")
def index_qualification_evidence_command(
    evidence_root: Path = typer.Option(..., "--evidence-root"),
    output_path: Path = typer.Option(..., "--output"),
    selected_period_plan_path: Path = typer.Option(
        Path("config/swing_machine_v0_1_selected_periods.yaml"),
        "--selected-period-plan",
        exists=True,
        readable=True,
    ),
) -> None:
    from swingmachine.qualification_evidence import (
        build_qualification_evidence_index,
        write_qualification_evidence_index_json,
    )

    index = build_qualification_evidence_index(
        evidence_root,
        selected_period_plan_path=selected_period_plan_path,
    )
    write_qualification_evidence_index_json(index, output_path)


def _parse_selected_period_data_manifests(entries: Iterable[str]) -> dict[str, Path]:
    manifests: dict[str, Path] = {}
    for entry in entries:
        if "=" not in entry:
            raise typer.BadParameter("data-manifest must use PERIOD_ID=MANIFEST_PATH")
        period_id, manifest_path = entry.split("=", maxsplit=1)
        period_id = period_id.strip()
        manifest_path = manifest_path.strip()
        if not period_id or not manifest_path:
            raise typer.BadParameter("data-manifest must use PERIOD_ID=MANIFEST_PATH")
        manifests[period_id] = Path(manifest_path)
    return manifests


@app.command("list-run-history")
def list_run_history_command(
    output_path: Path = typer.Option(..., "--output"),
    database_url: str = typer.Option(
        "sqlite+pysqlite:///./swingmachine_runtime.db",
        "--database-url",
    ),
    limit: int = typer.Option(100, "--limit"),
) -> None:
    runs = build_runtime_run_history(database_url=database_url).list_runs(limit=limit)
    _write_payload({"runs": list(runs), "count": len(runs)}, output_path)


@app.command("list-run-events")
def list_run_events_command(
    output_path: Path = typer.Option(..., "--output"),
    database_url: str = typer.Option(
        "sqlite+pysqlite:///./swingmachine_runtime.db",
        "--database-url",
    ),
    limit: int = typer.Option(100, "--limit"),
    run_id: str | None = typer.Option(None, "--run-id"),
    event_type: RuntimeEventType | None = typer.Option(None, "--event-type"),
) -> None:
    events = build_runtime_run_history(database_url=database_url).list_events(
        limit=limit,
        run_id=run_id,
        event_type=event_type,
    )
    _write_payload({"events": list(events), "count": len(events)}, output_path)


@app.command("summarize-review-run-trends")
def summarize_review_run_trends_command(
    output_path: Path = typer.Option(..., "--output"),
    database_url: str = typer.Option(
        "sqlite+pysqlite:///./swingmachine_runtime.db",
        "--database-url",
    ),
    limit: int = typer.Option(100, "--limit"),
) -> None:
    if limit < 0:
        raise typer.BadParameter("limit must be non-negative")
    runs = build_runtime_run_history(database_url=database_url).list_runs(limit=limit)
    summary = summarize_operator_review_run_trends(runs) | {"source_run_limit": limit}
    _write_payload(summary, output_path)


@app.command("inspect-trading212-research-source")
def inspect_trading212_research_source_command(
    provider: str = typer.Option(..., help="Trading212 research provider id."),
    config_path: str = typer.Option(
        "config/swing_machine_v0_1_trading212_sources.yaml",
        help="Trading212 source config path.",
    ),
    output: str | None = typer.Option(None, help="JSON inspection report output path."),
    sample_symbol_limit: int = typer.Option(
        20, min=1, help="Maximum configured symbols to sample."
    ),
) -> None:
    """Inspect a Trading212 research SQLite source using bounded read-only queries."""

    from pathlib import Path

    from swingmachine.trading212_source import (
        inspect_trading212_source,
        load_trading212_source_config,
        trading212_provider_config,
        write_trading212_json_report,
    )

    config_set = load_trading212_source_config(Path(config_path))
    provider_config = trading212_provider_config(config_set, provider)
    inspection = inspect_trading212_source(
        provider_config,
        sample_symbol_limit=sample_symbol_limit,
    )
    output_path = (
        Path(output)
        if output
        else Path(f"reports/swing_machine_v0_1/trading212_{provider}_source_inspection.json")
    )
    write_trading212_json_report(output_path, inspection)
    typer.echo(f"wrote {output_path}")
    if inspection.errors:
        raise typer.Exit(code=1)


@app.command("preflight-trading212-source-coverage")
def preflight_trading212_source_coverage_command(
    provider: str = typer.Option(..., help="Trading212 research provider id."),
    config_path: str = typer.Option(
        "config/swing_machine_v0_1_trading212_sources.yaml",
        help="Trading212 source config path.",
    ),
    selected_period_plan: str = typer.Option(
        "config/swing_machine_v0_1_selected_periods.yaml",
        help="Selected-period qualification plan path.",
    ),
    output: str | None = typer.Option(None, help="JSON coverage report output path."),
    max_symbols: int = typer.Option(
        0,
        min=0,
        help="Optional symbol limit for bounded smoke checks; 0 means all configured symbols.",
    ),
) -> None:
    """Preflight Trading212 selected-period data coverage without exporting data."""

    from pathlib import Path

    from swingmachine.trading212_source import (
        load_trading212_source_config,
        preflight_trading212_source_coverage,
        trading212_provider_config,
        write_trading212_json_report,
    )

    config_set = load_trading212_source_config(Path(config_path))
    provider_config = trading212_provider_config(config_set, provider)
    report = preflight_trading212_source_coverage(
        provider_config,
        Path(selected_period_plan),
        max_symbols=max_symbols,
    )
    output_path = (
        Path(output)
        if output
        else Path(f"reports/swing_machine_v0_1/trading212_{provider}_source_coverage.json")
    )
    write_trading212_json_report(output_path, report)
    typer.echo(f"wrote {output_path}")
    if not report.passed:
        raise typer.Exit(code=1)


@app.command("export-trading212-selected-period-data")
def export_trading212_selected_period_data_command(
    provider: str = typer.Option(..., help="Trading212 research provider id."),
    config_path: str = typer.Option(
        "config/swing_machine_v0_1_trading212_sources.yaml",
        help="Trading212 source config path.",
    ),
    selected_period_plan: str = typer.Option(
        "config/swing_machine_v0_1_selected_periods.yaml",
        help="Selected-period qualification plan path.",
    ),
    summary_output: str | None = typer.Option(
        None, help="JSON export summary output path."
    ),
    max_symbols: int = typer.Option(
        0,
        min=0,
        help="Optional symbol limit for bounded smoke exports; 0 means all configured symbols.",
    ),
) -> None:
    """Export selected-period qualification data from a Trading212 research source."""

    from pathlib import Path

    from swingmachine.trading212_source import (
        export_trading212_selected_period_data,
        load_trading212_source_config,
        trading212_provider_config,
        write_trading212_json_report,
    )

    config_set = load_trading212_source_config(Path(config_path))
    provider_config = trading212_provider_config(config_set, provider)
    summary = export_trading212_selected_period_data(
        provider_config,
        Path(selected_period_plan),
        max_symbols=max_symbols,
    )
    output_path = (
        Path(summary_output)
        if summary_output
        else Path(
            f"reports/swing_machine_v0_1/trading212_{provider}_selected_period_export.json"
        )
    )
    write_trading212_json_report(output_path, summary)
    typer.echo(f"wrote {output_path}")
    if not summary.passed:
        raise typer.Exit(code=1)


@app.command("compare-trading212-provider-panels")
def compare_trading212_provider_panels_command(
    left_summary: str = typer.Option(
        "reports/swing_machine_v0_1/trading212_alpaca_selected_period_export.json",
        help="Left provider selected-period export summary.",
    ),
    right_summary: str = typer.Option(
        "reports/swing_machine_v0_1/trading212_huggingface_selected_period_export.json",
        help="Right provider selected-period export summary.",
    ),
    output: str = typer.Option(
        "reports/swing_machine_v0_1/trading212_provider_panel_drift_report.json",
        help="JSON panel drift report output path.",
    ),
    price_abs_tolerance: float = typer.Option(
        0.01, min=0.0, help="Maximum allowed absolute OHLC price difference."
    ),
    volume_abs_tolerance: float = typer.Option(
        0.0, min=0.0, help="Maximum allowed absolute volume difference."
    ),
) -> None:
    """Compare exported Trading212 provider panels for selected periods."""

    from pathlib import Path

    from swingmachine.trading212_source import (
        build_trading212_provider_panel_drift_report,
        write_trading212_json_report,
    )

    report = build_trading212_provider_panel_drift_report(
        Path(left_summary),
        Path(right_summary),
        price_abs_tolerance=price_abs_tolerance,
        volume_abs_tolerance=volume_abs_tolerance,
    )
    write_trading212_json_report(Path(output), report)
    typer.echo(f"wrote {output}")
    if not report.passed:
        raise typer.Exit(code=1)


@app.command("build-overnight-qualification-evidence-summary")
def build_overnight_qualification_evidence_summary_command(
    report_root: Path = typer.Option(
        Path("reports/swing_machine_v0_1"),
        "--report-root",
        help="Directory containing qualification evidence reports.",
    ),
    output_path: Path = typer.Option(
        Path("reports/swing_machine_v0_1/overnight_qualification_evidence_summary.json"),
        "--output",
        help="Output JSON summary path.",
    ),
) -> None:
    from swingmachine.overnight_qualification import (
        build_overnight_qualification_evidence_summary,
        write_json_report,
    )

    summary = build_overnight_qualification_evidence_summary(report_root)
    write_json_report(summary, output_path)


@app.command("write-draft-baseline-manifest-package")
def write_draft_baseline_manifest_package_command(
    output_root: Path = typer.Option(
        Path("reports/swing_machine_v0_1"),
        "--output-root",
        help="Directory for draft manifest, checklist, and freeze readiness artifacts.",
    ),
    profile_alias_path: Path = typer.Option(
        Path("config/swing_machine_v0_1_profile.yaml"),
        "--profile-alias",
        help="Baseline profile alias path.",
    ),
    selected_period_plan_path: Path = typer.Option(
        Path("config/swing_machine_v0_1_selected_periods.yaml"),
        "--selected-period-plan",
        help="Selected-period qualification plan path.",
    ),
    summary_output: Path = typer.Option(
        Path("reports/swing_machine_v0_1/draft_baseline_manifest_bundle.json"),
        "--summary-output",
        help="Output JSON summary path.",
    ),
) -> None:
    from swingmachine.overnight_qualification import (
        write_draft_baseline_manifest_bundle,
        write_json_report,
    )

    bundle = write_draft_baseline_manifest_bundle(
        output_root,
        profile_alias_path=profile_alias_path,
        selected_period_plan_path=selected_period_plan_path,
    )
    write_json_report(bundle, summary_output)


@app.command("smoke-selected-period-data-package")
def smoke_selected_period_data_package_command(
    input_plan: Path = typer.Option(
        Path("reports/swing_machine_v0_1/trading212_alpaca_data_input_plan.json"),
        "--input-plan",
        help="Selected-period data input plan path.",
    ),
    output_path: Path = typer.Option(
        Path("reports/swing_machine_v0_1/selected_period_data_smoke_report.json"),
        "--output",
        help="Output JSON smoke report path.",
    ),
) -> None:
    from swingmachine.overnight_qualification import (
        run_selected_period_data_smoke,
        write_json_report,
    )

    report = run_selected_period_data_smoke(input_plan)
    write_json_report(report, output_path)
    if not report.passed:
        raise typer.Exit(code=1)


@app.command("check-selected-period-dry-run-safety")
def check_selected_period_dry_run_safety_command(
    selected_period_plan_path: Path = typer.Option(
        Path("config/swing_machine_v0_1_selected_periods.yaml"),
        "--selected-period-plan",
        help="Selected-period qualification plan path.",
    ),
    profile_alias_path: Path = typer.Option(
        Path("config/swing_machine_v0_1_profile.yaml"),
        "--profile-alias",
        help="Baseline profile alias path.",
    ),
    output_path: Path = typer.Option(
        Path("reports/swing_machine_v0_1/selected_period_dry_run_safety_report.json"),
        "--output",
        help="Output JSON dry-run safety report path.",
    ),
) -> None:
    from swingmachine.overnight_qualification import (
        check_selected_period_dry_run_safety,
        write_json_report,
    )

    report = check_selected_period_dry_run_safety(
        selected_period_plan_path,
        profile_alias_path=profile_alias_path,
    )
    write_json_report(report, output_path)
    if not report.passed:
        raise typer.Exit(code=1)


@app.command("build-lookahead-audit-report")
def build_lookahead_audit_report_command(
    manifest: Path = typer.Option(
        Path(
            "data/qualification_manifests/trading212/alpaca_historical_broad/"
            "historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml"
        ),
        "--manifest",
        exists=True,
        readable=True,
        help="Historical panel manifest path.",
    ),
    output: Path = typer.Option(
        Path("reports/swing_machine_v0_1/lookahead_audit.json"),
        "--output",
        help="Output JSON lookahead audit report path.",
    ),
) -> None:
    from swingmachine.lookahead_audit import (
        build_lookahead_audit_report,
        write_lookahead_audit_report_json,
    )

    report = build_lookahead_audit_report(manifest)
    write_lookahead_audit_report_json(report, output)
    typer.echo(f"wrote {output}")
    if report.status is ReviewStatus.FAIL:
        raise typer.Exit(code=1)


@app.command("build-prepared-feature-panel")
def build_prepared_feature_panel_command(
    manifest: Path = typer.Option(
        ...,
        "--manifest",
        exists=True,
        readable=True,
        help="Historical panel manifest path.",
    ),
    output: Path = typer.Option(
        ...,
        "--output",
        help="Prepared feature output path; .parquet or .csv.",
    ),
    config_path: Path = typer.Option(
        Path("swing_trading_bot_config_template_v2.yaml"),
        "--config",
        exists=True,
        readable=True,
        help="Explicit baseline strategy config path.",
    ),
    provenance_output: Path | None = typer.Option(
        None,
        "--provenance-output",
        help="Optional JSON provenance report output path.",
    ),
    update_manifest: bool = typer.Option(
        True,
        "--update-manifest/--no-update-manifest",
        help="Update the manifest features block after writing the feature file.",
    ),
) -> None:
    from swingmachine.prepared_features import write_prepared_feature_panel_for_manifest

    provenance = write_prepared_feature_panel_for_manifest(
        manifest,
        output_path=output,
        config_path=config_path,
        provenance_output_path=provenance_output,
        update_manifest=update_manifest,
    )
    typer.echo(f"wrote {output}")
    if provenance_output is not None:
        typer.echo(f"wrote {provenance_output}")
    if provenance.get("manifest_validation_status") == ReviewStatus.FAIL.value:
        raise typer.Exit(code=1)


@app.command("build-decision-ledger-report")
def build_decision_ledger_report_command(
    lifecycle_artifact_manifest: Path = typer.Option(
        ...,
        "--lifecycle-artifact-manifest",
        exists=True,
        readable=True,
        help="Portfolio lifecycle artifact manifest path.",
    ),
    output: Path = typer.Option(
        Path("reports/swing_machine_v0_1/decision_ledger.json"),
        "--output",
        help="Output JSON decision ledger report path.",
    ),
    scanner_material_decisions: Path | None = typer.Option(
        None,
        "--scanner-material-decisions",
        exists=True,
        readable=True,
        help="Optional scanner material decisions JSON path.",
    ),
) -> None:
    from swingmachine.decision_ledger import (
        build_decision_ledger_report,
        write_decision_ledger_report_json,
    )

    report = build_decision_ledger_report(
        lifecycle_artifact_manifest_path=lifecycle_artifact_manifest,
        scanner_material_decisions_path=scanner_material_decisions,
    )
    write_decision_ledger_report_json(report, output)
    typer.echo(f"wrote {output}")
    if report.status is ReviewStatus.FAIL:
        raise typer.Exit(code=1)


@app.command("build-mechanical-readiness-report")
def build_mechanical_readiness_report_command(
    output: Path = typer.Option(
        Path("reports/swing_machine_v0_1/mechanical_readiness_report.json"),
        "--output",
        help="Output JSON mechanical readiness report path.",
    ),
    markdown_output: Path | None = typer.Option(
        None,
        "--markdown-output",
        help="Optional markdown mechanical readiness report path.",
    ),
    report_root: Path = typer.Option(
        Path("reports/swing_machine_v0_1"),
        "--report-root",
        help="Directory containing qualification evidence reports.",
    ),
    profile_alias: Path = typer.Option(
        Path("config/swing_machine_v0_1_profile.yaml"),
        "--profile-alias",
        help="Baseline profile alias path.",
    ),
    manifest: Path = typer.Option(
        Path(
            "data/qualification_manifests/trading212/alpaca_historical_broad/"
            "historical_broad_2024_06_to_2025_07_v0_1/manifest.yaml"
        ),
        "--manifest",
        help="Historical panel manifest path.",
    ),
    scanner_summary: Path | None = typer.Option(
        None,
        "--scanner-summary",
        help="Optional explicit broad scanner qualification summary path.",
    ),
    scanner_parity: Path | None = typer.Option(
        None,
        "--scanner-parity",
        help="Optional explicit scanner parity report path.",
    ),
    lifecycle_summary: Path | None = typer.Option(
        None,
        "--lifecycle-summary",
        help="Optional explicit broad lifecycle qualification summary path.",
    ),
    lifecycle_parity: Path | None = typer.Option(
        None,
        "--lifecycle-parity",
        help="Optional explicit lifecycle parity report path.",
    ),
    pre_paper_gate: Path | None = typer.Option(
        None,
        "--pre-paper-gate",
        help="Optional explicit full pre-paper test gate summary path.",
    ),
    dry_run_safety: Path | None = typer.Option(
        None,
        "--dry-run-safety",
        help="Optional explicit dry-run safety report path.",
    ),
    lookahead_audit: Path | None = typer.Option(
        None,
        "--lookahead-audit",
        help="Optional lookahead audit report path.",
    ),
    decision_ledger: Path | None = typer.Option(
        None,
        "--decision-ledger",
        help="Optional decision ledger report path.",
    ),
    risk_portfolio_evidence: Path | None = typer.Option(
        None,
        "--risk-portfolio-evidence",
        help="Optional risk/portfolio adversarial evidence path.",
    ),
    exit_lifecycle_evidence: Path | None = typer.Option(
        None,
        "--exit-lifecycle-evidence",
        help="Optional exit lifecycle adversarial evidence path.",
    ),
) -> None:
    from swingmachine.mechanical_readiness import (
        build_mechanical_readiness_report,
        write_mechanical_readiness_report_json,
        write_mechanical_readiness_report_markdown,
    )

    report = build_mechanical_readiness_report(
        profile_alias_path=profile_alias,
        manifest_path=manifest,
        report_root=report_root,
        scanner_summary_path=scanner_summary,
        scanner_parity_path=scanner_parity,
        lifecycle_summary_path=lifecycle_summary,
        lifecycle_parity_path=lifecycle_parity,
        pre_paper_gate_path=pre_paper_gate,
        dry_run_safety_path=dry_run_safety,
        lookahead_audit_path=lookahead_audit,
        decision_ledger_path=decision_ledger,
        risk_portfolio_evidence_path=risk_portfolio_evidence,
        exit_lifecycle_evidence_path=exit_lifecycle_evidence,
    )
    write_mechanical_readiness_report_json(report, output)
    if markdown_output is not None:
        write_mechanical_readiness_report_markdown(report, markdown_output)
    typer.echo(f"wrote {output}")
    if report.decision == "BLOCK":
        raise typer.Exit(code=1)


def main() -> None:
    app()
