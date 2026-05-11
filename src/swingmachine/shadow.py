from __future__ import annotations

from datetime import datetime, time

import pandas as pd

from swingmachine.config import StrategyRuntimeConfig
from swingmachine.contracts import (
    RuntimeCycleResult,
    ShadowEntryBatch,
    ShadowFillComparison,
    ShadowFillComparisonBatch,
)
from swingmachine.data_contracts import validate_next_session_market_data
from swingmachine.enums import RuntimeMode, ShadowFillStatus
from swingmachine.execution_model import apply_execution_cost, simulate_entry_fill
from swingmachine.monitoring import MonitoringService


def _prepare_market_data(market_data: pd.DataFrame) -> pd.DataFrame:
    return validate_next_session_market_data(market_data)


def compare_next_session_shadow_fills(
    shadow_entry_batch: ShadowEntryBatch,
    market_data: pd.DataFrame,
    config: StrategyRuntimeConfig,
    *,
    monitoring_service: MonitoringService | None = None,
) -> ShadowFillComparisonBatch:
    monitoring = monitoring_service or MonitoringService(config)
    prepared_market = _prepare_market_data(market_data)
    row_by_symbol = {str(row["symbol"]): row for _, row in prepared_market.iterrows()}

    comparisons: list[ShadowFillComparison] = []
    alerts = []
    compared_proposals = [
        proposal
        for proposal in shadow_entry_batch.proposals
        if proposal.would_submit and proposal.hypothetical_intent is not None
    ]

    for proposal in compared_proposals:
        intent = proposal.hypothetical_intent
        if intent is None:
            continue

        row = row_by_symbol.get(intent.symbol)
        if row is None:
            comparisons.append(
                ShadowFillComparison(
                    symbol=proposal.symbol,
                    setup_id=proposal.setup_id,
                    intent_id=proposal.intent_id or "",
                    source_as_of=shadow_entry_batch.as_of,
                    source_regime_state=shadow_entry_batch.regime_state,
                    status=ShadowFillStatus.MISSING_MARKET_DATA,
                    would_fill=False,
                    would_remain_pending=False,
                    would_mark_setup_spent=False,
                    detail="NO_NEXT_SESSION_MARKET_DATA",
                )
            )
            continue

        session_date = pd.Timestamp(row["session_date"]).date()
        official_open = float(row["raw_open"])
        if (
            config.entry.cancel_unfilled_order_if_open_above_limit
            and intent.limit_price is not None
            and official_open > float(intent.limit_price)
        ):
            comparisons.append(
                ShadowFillComparison(
                    symbol=proposal.symbol,
                    setup_id=proposal.setup_id,
                    intent_id=proposal.intent_id or "",
                    source_as_of=shadow_entry_batch.as_of,
                    source_regime_state=shadow_entry_batch.regime_state,
                    session_date=session_date,
                    status=ShadowFillStatus.OPEN_GAP_CANCELLED,
                    would_fill=False,
                    would_remain_pending=False,
                    would_mark_setup_spent=True,
                    official_open=official_open,
                    detail="OPEN_GAP_ABOVE_LIMIT",
                )
            )
            continue

        reference_price = simulate_entry_fill(row, intent)
        if reference_price is None:
            comparisons.append(
                ShadowFillComparison(
                    symbol=proposal.symbol,
                    setup_id=proposal.setup_id,
                    intent_id=proposal.intent_id or "",
                    source_as_of=shadow_entry_batch.as_of,
                    source_regime_state=shadow_entry_batch.regime_state,
                    session_date=session_date,
                    status=ShadowFillStatus.UNFILLED,
                    would_fill=False,
                    would_remain_pending=True,
                    would_mark_setup_spent=False,
                    official_open=official_open,
                    detail="NO_TRIGGERED_FILL",
                )
            )
            continue

        quantity = max(int(round(float(intent.quantity))), 1)
        fill = apply_execution_cost(
            reference_price=reference_price,
            row=row,
            quantity=quantity,
            side="buy",
            config=config,
        )
        slippage_alert = monitoring.evaluate_slippage(
            triggered_at=datetime.combine(session_date, time(9, 30)),
            reference_price=fill.reference_price,
            executed_price=fill.execution_price,
            side=intent.side,
            symbol=intent.symbol,
        )
        if slippage_alert is not None:
            alerts.append(slippage_alert)

        comparisons.append(
            ShadowFillComparison(
                symbol=proposal.symbol,
                setup_id=proposal.setup_id,
                intent_id=proposal.intent_id or "",
                source_as_of=shadow_entry_batch.as_of,
                source_regime_state=shadow_entry_batch.regime_state,
                session_date=session_date,
                status=ShadowFillStatus.FILLED,
                would_fill=True,
                would_remain_pending=False,
                would_mark_setup_spent=False,
                official_open=official_open,
                reference_price=fill.reference_price,
                hypothetical_fill_price=fill.execution_price,
                transaction_cost=fill.transaction_cost,
                total_cost_bps=fill.total_cost_bps,
                slippage_alert=slippage_alert,
            )
        )

    return ShadowFillComparisonBatch(
        source_mode=RuntimeMode.SHADOW,
        source_as_of=shadow_entry_batch.as_of,
        source_regime_state=shadow_entry_batch.regime_state,
        source_proposal_count=len(shadow_entry_batch.proposals),
        compared_proposal_count=len(compared_proposals),
        skipped_proposal_count=len(shadow_entry_batch.proposals) - len(compared_proposals),
        comparisons=tuple(comparisons),
        alerts=tuple(alerts),
        filled_count=sum(
            1 for comparison in comparisons if comparison.status == ShadowFillStatus.FILLED
        ),
        unfilled_count=sum(
            1 for comparison in comparisons if comparison.status == ShadowFillStatus.UNFILLED
        ),
        cancelled_count=sum(
            1
            for comparison in comparisons
            if comparison.status == ShadowFillStatus.OPEN_GAP_CANCELLED
        ),
        missing_market_data_count=sum(
            1
            for comparison in comparisons
            if comparison.status == ShadowFillStatus.MISSING_MARKET_DATA
        ),
    )


def compare_runtime_cycle_shadow_fills(
    runtime_cycle_result: RuntimeCycleResult,
    market_data: pd.DataFrame,
    config: StrategyRuntimeConfig,
    *,
    monitoring_service: MonitoringService | None = None,
) -> ShadowFillComparisonBatch:
    if runtime_cycle_result.mode != RuntimeMode.SHADOW:
        raise ValueError("shadow fill comparison requires a SHADOW runtime cycle result")
    if runtime_cycle_result.shadow_entry_batch is None:
        raise ValueError("runtime cycle result does not contain a shadow_entry_batch")

    return compare_next_session_shadow_fills(
        runtime_cycle_result.shadow_entry_batch,
        market_data,
        config,
        monitoring_service=monitoring_service,
    )
