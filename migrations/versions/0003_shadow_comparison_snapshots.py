"""Add immutable shadow comparison snapshots.

Revision ID: 0003_shadow_comparison_snapshots
Revises: 0002_runtime_events
Create Date: 2026-04-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_shadow_comparison_snapshots"
down_revision = "0002_runtime_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shadow_fill_comparison_snapshots",
        sa.Column("snapshot_id", sa.String(length=64), nullable=False),
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
        sa.PrimaryKeyConstraint("snapshot_id"),
    )
    op.create_index(
        "ix_shadow_fill_comparison_snapshots_intent_id",
        "shadow_fill_comparison_snapshots",
        ["intent_id"],
        unique=False,
    )
    op.create_index(
        "ix_shadow_fill_comparison_snapshots_recorded_at",
        "shadow_fill_comparison_snapshots",
        ["recorded_at"],
        unique=False,
    )
    op.create_index(
        "ix_shadow_fill_comparison_snapshots_session_date",
        "shadow_fill_comparison_snapshots",
        ["session_date"],
        unique=False,
    )
    op.create_index(
        "ix_shadow_fill_comparison_snapshots_setup_id",
        "shadow_fill_comparison_snapshots",
        ["setup_id"],
        unique=False,
    )
    op.create_index(
        "ix_shadow_fill_comparison_snapshots_source_as_of",
        "shadow_fill_comparison_snapshots",
        ["source_as_of"],
        unique=False,
    )
    op.create_index(
        "ix_shadow_fill_comparison_snapshots_source_regime_state",
        "shadow_fill_comparison_snapshots",
        ["source_regime_state"],
        unique=False,
    )
    op.create_index(
        "ix_shadow_fill_comparison_snapshots_status",
        "shadow_fill_comparison_snapshots",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_shadow_fill_comparison_snapshots_symbol",
        "shadow_fill_comparison_snapshots",
        ["symbol"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shadow_fill_comparison_snapshots_symbol",
        table_name="shadow_fill_comparison_snapshots",
    )
    op.drop_index(
        "ix_shadow_fill_comparison_snapshots_status",
        table_name="shadow_fill_comparison_snapshots",
    )
    op.drop_index(
        "ix_shadow_fill_comparison_snapshots_source_regime_state",
        table_name="shadow_fill_comparison_snapshots",
    )
    op.drop_index(
        "ix_shadow_fill_comparison_snapshots_source_as_of",
        table_name="shadow_fill_comparison_snapshots",
    )
    op.drop_index(
        "ix_shadow_fill_comparison_snapshots_setup_id",
        table_name="shadow_fill_comparison_snapshots",
    )
    op.drop_index(
        "ix_shadow_fill_comparison_snapshots_session_date",
        table_name="shadow_fill_comparison_snapshots",
    )
    op.drop_index(
        "ix_shadow_fill_comparison_snapshots_recorded_at",
        table_name="shadow_fill_comparison_snapshots",
    )
    op.drop_index(
        "ix_shadow_fill_comparison_snapshots_intent_id",
        table_name="shadow_fill_comparison_snapshots",
    )
    op.drop_table("shadow_fill_comparison_snapshots")
