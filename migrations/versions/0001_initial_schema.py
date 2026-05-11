"""Initial Swingmachine schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-25

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broker_orders",
        sa.Column("broker_order_id", sa.String(length=128), nullable=False),
        sa.Column("intent_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("order_type", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("stop_price", sa.Float(), nullable=True),
        sa.Column("limit_price", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("broker_order_id"),
    )
    op.create_index("ix_broker_orders_intent_id", "broker_orders", ["intent_id"], unique=True)
    op.create_index("ix_broker_orders_status", "broker_orders", ["status"], unique=False)
    op.create_index("ix_broker_orders_symbol", "broker_orders", ["symbol"], unique=False)

    op.create_table(
        "canonical_snapshot_hashes",
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("symbol", "session_date"),
    )

    op.create_table(
        "order_intents",
        sa.Column("intent_id", sa.String(length=128), nullable=False),
        sa.Column("dedupe_key", sa.String(length=128), nullable=False),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("config_hash", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("setup_id", sa.String(length=128), nullable=True),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("order_type", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("stop_price", sa.Float(), nullable=True),
        sa.Column("limit_price", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("broker_order_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("intent_id"),
    )
    op.create_index("ix_order_intents_dedupe_key", "order_intents", ["dedupe_key"], unique=True)
    op.create_index("ix_order_intents_reason", "order_intents", ["reason"], unique=False)
    op.create_index("ix_order_intents_setup_id", "order_intents", ["setup_id"], unique=False)
    op.create_index("ix_order_intents_status", "order_intents", ["status"], unique=False)
    op.create_index("ix_order_intents_symbol", "order_intents", ["symbol"], unique=False)

    op.create_table(
        "regime_snapshots",
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("benchmark_symbol", sa.String(length=32), nullable=False),
        sa.Column("benchmark_close", sa.Float(), nullable=False),
        sa.Column("benchmark_ma200", sa.Float(), nullable=False),
        sa.Column("benchmark_ma200_slope_pct20", sa.Float(), nullable=False),
        sa.Column("benchmark_dist_above_ma200", sa.Float(), nullable=False),
        sa.Column("realized_vol_20", sa.Float(), nullable=False),
        sa.Column("breadth_pct_above_ma200", sa.Float(), nullable=True),
        sa.Column("panic_drawdown_126", sa.Float(), nullable=False),
        sa.Column("rebound_return_20", sa.Float(), nullable=False),
        sa.Column("regime_state", sa.String(length=32), nullable=False),
        sa.Column("entry_enabled", sa.Boolean(), nullable=False),
        sa.Column("size_multiplier", sa.Float(), nullable=False),
        sa.Column("min_candidate_score_percentile", sa.Float(), nullable=False),
        sa.Column("min_trend_quality", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("session_date"),
    )

    op.create_table(
        "runtime_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("command", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("config_hash", sa.String(length=128), nullable=True),
        sa.Column("input_path", sa.Text(), nullable=True),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("metrics_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_runtime_runs_command", "runtime_runs", ["command"], unique=False)
    op.create_index("ix_runtime_runs_mode", "runtime_runs", ["mode"], unique=False)
    op.create_index("ix_runtime_runs_started_at", "runtime_runs", ["started_at"], unique=False)
    op.create_index("ix_runtime_runs_status", "runtime_runs", ["status"], unique=False)

    op.create_table(
        "shadow_fill_comparisons",
        sa.Column("intent_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("setup_id", sa.String(length=128), nullable=False),
        sa.Column("source_mode", sa.String(length=16), nullable=False),
        sa.Column("source_as_of", sa.DateTime(), nullable=True),
        sa.Column("source_regime_state", sa.String(length=32), nullable=True),
        sa.Column("session_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("would_fill", sa.Boolean(), nullable=False),
        sa.Column("would_remain_pending", sa.Boolean(), nullable=False),
        sa.Column("would_mark_setup_spent", sa.Boolean(), nullable=False),
        sa.Column("official_open", sa.Float(), nullable=True),
        sa.Column("reference_price", sa.Float(), nullable=True),
        sa.Column("hypothetical_fill_price", sa.Float(), nullable=True),
        sa.Column("transaction_cost", sa.Float(), nullable=True),
        sa.Column("total_cost_bps", sa.Float(), nullable=True),
        sa.Column("slippage_alert_triggered_at", sa.DateTime(), nullable=True),
        sa.Column("slippage_alert_metric_value", sa.Float(), nullable=True),
        sa.Column("slippage_alert_threshold_value", sa.Float(), nullable=True),
        sa.Column("detail", sa.String(length=128), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("intent_id"),
    )
    op.create_index(
        "ix_shadow_fill_comparisons_session_date",
        "shadow_fill_comparisons",
        ["session_date"],
        unique=False,
    )
    op.create_index(
        "ix_shadow_fill_comparisons_setup_id",
        "shadow_fill_comparisons",
        ["setup_id"],
        unique=False,
    )
    op.create_index(
        "ix_shadow_fill_comparisons_source_as_of",
        "shadow_fill_comparisons",
        ["source_as_of"],
        unique=False,
    )
    op.create_index(
        "ix_shadow_fill_comparisons_source_regime_state",
        "shadow_fill_comparisons",
        ["source_regime_state"],
        unique=False,
    )
    op.create_index(
        "ix_shadow_fill_comparisons_status",
        "shadow_fill_comparisons",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_shadow_fill_comparisons_symbol",
        "shadow_fill_comparisons",
        ["symbol"],
        unique=False,
    )

    op.create_table(
        "spent_setups",
        sa.Column("setup_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("marked_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("setup_id"),
    )
    op.create_index("ix_spent_setups_symbol", "spent_setups", ["symbol"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_spent_setups_symbol", table_name="spent_setups")
    op.drop_table("spent_setups")

    op.drop_index("ix_shadow_fill_comparisons_symbol", table_name="shadow_fill_comparisons")
    op.drop_index("ix_shadow_fill_comparisons_status", table_name="shadow_fill_comparisons")
    op.drop_index(
        "ix_shadow_fill_comparisons_source_regime_state",
        table_name="shadow_fill_comparisons",
    )
    op.drop_index("ix_shadow_fill_comparisons_source_as_of", table_name="shadow_fill_comparisons")
    op.drop_index("ix_shadow_fill_comparisons_setup_id", table_name="shadow_fill_comparisons")
    op.drop_index("ix_shadow_fill_comparisons_session_date", table_name="shadow_fill_comparisons")
    op.drop_table("shadow_fill_comparisons")

    op.drop_index("ix_runtime_runs_status", table_name="runtime_runs")
    op.drop_index("ix_runtime_runs_started_at", table_name="runtime_runs")
    op.drop_index("ix_runtime_runs_mode", table_name="runtime_runs")
    op.drop_index("ix_runtime_runs_command", table_name="runtime_runs")
    op.drop_table("runtime_runs")

    op.drop_table("regime_snapshots")

    op.drop_index("ix_order_intents_symbol", table_name="order_intents")
    op.drop_index("ix_order_intents_status", table_name="order_intents")
    op.drop_index("ix_order_intents_setup_id", table_name="order_intents")
    op.drop_index("ix_order_intents_reason", table_name="order_intents")
    op.drop_index("ix_order_intents_dedupe_key", table_name="order_intents")
    op.drop_table("order_intents")

    op.drop_table("canonical_snapshot_hashes")

    op.drop_index("ix_broker_orders_symbol", table_name="broker_orders")
    op.drop_index("ix_broker_orders_status", table_name="broker_orders")
    op.drop_index("ix_broker_orders_intent_id", table_name="broker_orders")
    op.drop_table("broker_orders")
