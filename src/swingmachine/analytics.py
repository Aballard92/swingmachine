from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd

from swingmachine.contracts import (
    BacktestResult,
    BacktestTrade,
    PaperShadowAuditRecord,
    ShadowFillComparison,
)
from swingmachine.enums import PaperShadowAlignmentStatus, ShadowFillStatus


def trades_to_frame(trades: Sequence[BacktestTrade]) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(
            columns=[
                "symbol",
                "setup_id",
                "entry_signal_date",
                "entry_fill_date",
                "entry_reference_price",
                "entry_fill_price",
                "exit_fill_date",
                "exit_reference_price",
                "exit_fill_price",
                "quantity",
                "entry_regime_state",
                "exit_regime_state",
                "exit_reason",
                "bars_held",
                "initial_stop",
                "final_stop",
                "entry_transaction_cost",
                "exit_transaction_cost",
                "total_transaction_cost",
                "gross_pnl",
                "gross_return",
                "net_pnl",
                "net_return",
                "sector",
            ]
        )
    return pd.DataFrame([trade.model_dump(mode="json") for trade in trades])


def _max_drawdown(result: BacktestResult) -> float:
    if not result.equity_curve:
        return 0.0
    equity = pd.Series([point.equity for point in result.equity_curve], dtype=float)
    running_peak = equity.cummax()
    drawdown = equity / running_peak - 1.0
    return float(drawdown.min())


def summarize_backtest(result: BacktestResult) -> dict[str, Any]:
    trade_frame = trades_to_frame(result.trades)
    if trade_frame.empty:
        return {
            "trade_count": 0,
            "win_rate": 0.0,
            "gross_pnl": 0.0,
            "net_pnl": 0.0,
            "total_transaction_cost": 0.0,
            "avg_gross_return": 0.0,
            "avg_net_return": 0.0,
            "final_equity": result.final_equity,
            "max_drawdown": _max_drawdown(result),
        }

    wins = (trade_frame["net_pnl"] > 0.0).sum()
    trade_count = len(trade_frame)
    return {
        "trade_count": int(trade_count),
        "win_rate": float(wins / trade_count),
        "gross_pnl": float(trade_frame["gross_pnl"].sum()),
        "net_pnl": float(trade_frame["net_pnl"].sum()),
        "total_transaction_cost": float(trade_frame["total_transaction_cost"].sum()),
        "avg_gross_return": float(trade_frame["gross_return"].mean()),
        "avg_net_return": float(trade_frame["net_return"].mean()),
        "final_equity": result.final_equity,
        "max_drawdown": _max_drawdown(result),
    }


def regime_segmented_trade_stats(
    trades: Sequence[BacktestTrade],
) -> pd.DataFrame:
    trade_frame = trades_to_frame(trades)
    if trade_frame.empty:
        return pd.DataFrame(
            columns=[
                "entry_regime_state",
                "trade_count",
                "win_rate",
                "gross_pnl",
                "net_pnl",
                "total_transaction_cost",
                "avg_gross_return",
                "avg_net_return",
                "avg_bars_held",
            ]
        )

    grouped = trade_frame.groupby("entry_regime_state", sort=True)
    summary = grouped.agg(
        trade_count=("symbol", "size"),
        wins=("net_pnl", lambda values: (values > 0.0).sum()),
        gross_pnl=("gross_pnl", "sum"),
        net_pnl=("net_pnl", "sum"),
        total_transaction_cost=("total_transaction_cost", "sum"),
        avg_gross_return=("gross_return", "mean"),
        avg_net_return=("net_return", "mean"),
        avg_bars_held=("bars_held", "mean"),
    ).reset_index()
    summary["win_rate"] = summary["wins"] / summary["trade_count"]
    return summary[
        [
            "entry_regime_state",
            "trade_count",
            "win_rate",
            "gross_pnl",
            "net_pnl",
            "total_transaction_cost",
            "avg_gross_return",
            "avg_net_return",
            "avg_bars_held",
        ]
    ]


def shadow_fill_comparisons_to_frame(
    comparisons: Sequence[ShadowFillComparison],
) -> pd.DataFrame:
    if not comparisons:
        return pd.DataFrame(
            columns=[
                "snapshot_id",
                "symbol",
                "setup_id",
                "intent_id",
                "recorded_at",
                "source_as_of",
                "source_regime_state",
                "session_date",
                "status",
                "would_fill",
                "would_remain_pending",
                "would_mark_setup_spent",
                "official_open",
                "reference_price",
                "hypothetical_fill_price",
                "transaction_cost",
                "total_cost_bps",
                "slippage_alert_triggered",
                "slippage_alert_metric_value",
                "slippage_alert_threshold_value",
                "detail",
            ]
        )

    rows = []
    for comparison in comparisons:
        rows.append(
            {
                "snapshot_id": comparison.snapshot_id,
                "symbol": comparison.symbol,
                "setup_id": comparison.setup_id,
                "intent_id": comparison.intent_id,
                "recorded_at": comparison.recorded_at,
                "source_as_of": comparison.source_as_of,
                "source_regime_state": (
                    None
                    if comparison.source_regime_state is None
                    else comparison.source_regime_state.value
                ),
                "session_date": comparison.session_date,
                "status": comparison.status.value,
                "would_fill": comparison.would_fill,
                "would_remain_pending": comparison.would_remain_pending,
                "would_mark_setup_spent": comparison.would_mark_setup_spent,
                "official_open": comparison.official_open,
                "reference_price": comparison.reference_price,
                "hypothetical_fill_price": comparison.hypothetical_fill_price,
                "transaction_cost": comparison.transaction_cost,
                "total_cost_bps": comparison.total_cost_bps,
                "slippage_alert_triggered": comparison.slippage_alert is not None,
                "slippage_alert_metric_value": (
                    None
                    if comparison.slippage_alert is None
                    else comparison.slippage_alert.metric_value
                ),
                "slippage_alert_threshold_value": (
                    None
                    if comparison.slippage_alert is None
                    else comparison.slippage_alert.threshold_value
                ),
                "detail": comparison.detail,
            }
        )
    return pd.DataFrame(rows)


def summarize_shadow_fill_comparisons(
    comparisons: Sequence[ShadowFillComparison],
) -> dict[str, Any]:
    comparison_frame = shadow_fill_comparisons_to_frame(comparisons)
    if comparison_frame.empty:
        return {
            "comparison_count": 0,
            "actionable_comparison_count": 0,
            "filled_count": 0,
            "unfilled_count": 0,
            "cancelled_count": 0,
            "missing_market_data_count": 0,
            "fill_rate": 0.0,
            "cancel_rate": 0.0,
            "avg_total_cost_bps": 0.0,
            "avg_transaction_cost": 0.0,
            "slippage_alert_rate": 0.0,
        }

    actionable = comparison_frame.loc[
        comparison_frame["status"] != ShadowFillStatus.MISSING_MARKET_DATA.value
    ]
    fills = comparison_frame.loc[comparison_frame["status"] == ShadowFillStatus.FILLED.value]
    actionable_count = len(actionable)
    filled_count = int((comparison_frame["status"] == ShadowFillStatus.FILLED.value).sum())
    cancelled_count = int(
        (comparison_frame["status"] == ShadowFillStatus.OPEN_GAP_CANCELLED.value).sum()
    )
    missing_count = int(
        (comparison_frame["status"] == ShadowFillStatus.MISSING_MARKET_DATA.value).sum()
    )

    return {
        "comparison_count": int(len(comparison_frame)),
        "actionable_comparison_count": int(actionable_count),
        "filled_count": filled_count,
        "unfilled_count": int(
            (comparison_frame["status"] == ShadowFillStatus.UNFILLED.value).sum()
        ),
        "cancelled_count": cancelled_count,
        "missing_market_data_count": missing_count,
        "fill_rate": float(filled_count / actionable_count) if actionable_count else 0.0,
        "cancel_rate": float(cancelled_count / actionable_count) if actionable_count else 0.0,
        "avg_total_cost_bps": float(fills["total_cost_bps"].mean()) if not fills.empty else 0.0,
        "avg_transaction_cost": (
            float(fills["transaction_cost"].mean()) if not fills.empty else 0.0
        ),
        "slippage_alert_rate": (
            float(fills["slippage_alert_triggered"].mean()) if not fills.empty else 0.0
        ),
    }


def shadow_fill_regime_stats(
    comparisons: Sequence[ShadowFillComparison],
) -> pd.DataFrame:
    comparison_frame = shadow_fill_comparisons_to_frame(comparisons)
    if comparison_frame.empty:
        return pd.DataFrame(
            columns=[
                "source_regime_state",
                "comparison_count",
                "filled_count",
                "cancelled_count",
                "missing_market_data_count",
                "fill_rate",
                "avg_total_cost_bps",
                "avg_transaction_cost",
                "slippage_alert_rate",
            ]
        )

    grouped = comparison_frame.groupby("source_regime_state", dropna=False, sort=True)
    summary = grouped.agg(
        comparison_count=("symbol", "size"),
        filled_count=("status", lambda values: (values == ShadowFillStatus.FILLED.value).sum()),
        cancelled_count=(
            "status",
            lambda values: (values == ShadowFillStatus.OPEN_GAP_CANCELLED.value).sum(),
        ),
        missing_market_data_count=(
            "status",
            lambda values: (values == ShadowFillStatus.MISSING_MARKET_DATA.value).sum(),
        ),
        avg_total_cost_bps=("total_cost_bps", "mean"),
        avg_transaction_cost=("transaction_cost", "mean"),
        slippage_alert_rate=("slippage_alert_triggered", "mean"),
    ).reset_index()
    actionable = summary["comparison_count"] - summary["missing_market_data_count"]
    summary["fill_rate"] = [
        0.0 if actionable_count <= 0 else float(filled / actionable_count)
        for filled, actionable_count in zip(summary["filled_count"], actionable, strict=True)
    ]
    return summary[
        [
            "source_regime_state",
            "comparison_count",
            "filled_count",
            "cancelled_count",
            "missing_market_data_count",
            "fill_rate",
            "avg_total_cost_bps",
            "avg_transaction_cost",
            "slippage_alert_rate",
        ]
    ]


def shadow_fill_status_stats(
    comparisons: Sequence[ShadowFillComparison],
) -> pd.DataFrame:
    comparison_frame = shadow_fill_comparisons_to_frame(comparisons)
    if comparison_frame.empty:
        return pd.DataFrame(
            columns=[
                "status",
                "detail",
                "comparison_count",
                "avg_total_cost_bps",
                "avg_transaction_cost",
            ]
        )

    grouped = comparison_frame.groupby(["status", "detail"], dropna=False, sort=True)
    summary = grouped.agg(
        comparison_count=("symbol", "size"),
        avg_total_cost_bps=("total_cost_bps", "mean"),
        avg_transaction_cost=("transaction_cost", "mean"),
    ).reset_index()
    return summary[
        [
            "status",
            "detail",
            "comparison_count",
            "avg_total_cost_bps",
            "avg_transaction_cost",
        ]
    ]


def paper_shadow_audit_to_frame(
    records: Sequence[PaperShadowAuditRecord],
) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(
            columns=[
                "snapshot_id",
                "snapshot_batch_id",
                "recorded_at",
                "intent_id",
                "symbol",
                "setup_id",
                "created_at",
                "source_as_of",
                "source_regime_state",
                "alignment_status",
                "paper_intent_present",
                "paper_intent_status",
                "broker_order_id",
                "paper_broker_status",
                "paper_filled",
                "shadow_present",
                "shadow_status",
                "shadow_would_fill",
                "shadow_session_date",
                "shadow_hypothetical_fill_price",
                "shadow_total_cost_bps",
                "shadow_slippage_alert_triggered",
            ]
        )
    rows = []
    for record in records:
        rows.append(
            {
                "snapshot_id": record.snapshot_id,
                "snapshot_batch_id": record.snapshot_batch_id,
                "recorded_at": record.recorded_at,
                "intent_id": record.intent_id,
                "symbol": record.symbol,
                "setup_id": record.setup_id,
                "created_at": record.created_at,
                "source_as_of": record.source_as_of,
                "source_regime_state": (
                    None if record.source_regime_state is None else record.source_regime_state.value
                ),
                "alignment_status": record.alignment_status.value,
                "paper_intent_present": record.paper_intent_present,
                "paper_intent_status": (
                    None if record.paper_intent_status is None else record.paper_intent_status.value
                ),
                "broker_order_id": record.broker_order_id,
                "paper_broker_status": (
                    None if record.paper_broker_status is None else record.paper_broker_status.value
                ),
                "paper_filled": record.paper_filled,
                "shadow_present": record.shadow_present,
                "shadow_status": (
                    None if record.shadow_status is None else record.shadow_status.value
                ),
                "shadow_would_fill": record.shadow_would_fill,
                "shadow_session_date": record.shadow_session_date,
                "shadow_hypothetical_fill_price": record.shadow_hypothetical_fill_price,
                "shadow_total_cost_bps": record.shadow_total_cost_bps,
                "shadow_slippage_alert_triggered": record.shadow_slippage_alert_triggered,
            }
        )
    return pd.DataFrame(rows)


def summarize_paper_shadow_audit(
    records: Sequence[PaperShadowAuditRecord],
) -> dict[str, Any]:
    audit_frame = paper_shadow_audit_to_frame(records)
    if audit_frame.empty:
        return {
            "record_count": 0,
            "paper_present_count": 0,
            "shadow_present_count": 0,
            "paper_filled_count": 0,
            "shadow_filled_count": 0,
            "aligned_count": 0,
            "divergent_count": 0,
            "alignment_rate": 0.0,
        }

    aligned = audit_frame["alignment_status"].isin(
        [
            PaperShadowAlignmentStatus.ALIGNED_FILLED.value,
            PaperShadowAlignmentStatus.ALIGNED_NOT_FILLED.value,
        ]
    )
    return {
        "record_count": int(len(audit_frame)),
        "paper_present_count": int(audit_frame["paper_intent_present"].sum()),
        "shadow_present_count": int(audit_frame["shadow_present"].sum()),
        "paper_filled_count": int(audit_frame["paper_filled"].sum()),
        "shadow_filled_count": int(
            (audit_frame["shadow_status"] == ShadowFillStatus.FILLED.value).sum()
        ),
        "aligned_count": int(aligned.sum()),
        "divergent_count": int((~aligned).sum()),
        "alignment_rate": float(aligned.mean()),
    }


def paper_shadow_alignment_stats(
    records: Sequence[PaperShadowAuditRecord],
) -> pd.DataFrame:
    audit_frame = paper_shadow_audit_to_frame(records)
    if audit_frame.empty:
        return pd.DataFrame(columns=["alignment_status", "record_count"])
    grouped = audit_frame.groupby("alignment_status", sort=True)
    summary = grouped.agg(record_count=("intent_id", "size")).reset_index()
    return summary[["alignment_status", "record_count"]]


def paper_shadow_regime_stats(
    records: Sequence[PaperShadowAuditRecord],
) -> pd.DataFrame:
    audit_frame = paper_shadow_audit_to_frame(records)
    if audit_frame.empty:
        return pd.DataFrame(
            columns=[
                "source_regime_state",
                "record_count",
                "aligned_count",
                "paper_filled_count",
                "shadow_filled_count",
                "alignment_rate",
            ]
        )
    grouped = audit_frame.groupby("source_regime_state", dropna=False, sort=True)
    summary = grouped.agg(
        record_count=("intent_id", "size"),
        aligned_count=(
            "alignment_status",
            lambda values: values.isin(
                [
                    PaperShadowAlignmentStatus.ALIGNED_FILLED.value,
                    PaperShadowAlignmentStatus.ALIGNED_NOT_FILLED.value,
                ]
            ).sum(),
        ),
        paper_filled_count=("paper_filled", "sum"),
        shadow_filled_count=(
            "shadow_status",
            lambda values: (values == ShadowFillStatus.FILLED.value).sum(),
        ),
    ).reset_index()
    summary["alignment_rate"] = summary["aligned_count"] / summary["record_count"]
    return summary[
        [
            "source_regime_state",
            "record_count",
            "aligned_count",
            "paper_filled_count",
            "shadow_filled_count",
            "alignment_rate",
        ]
    ]
