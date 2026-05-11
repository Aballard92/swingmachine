"""Add immutable paper-shadow audit snapshots.

Revision ID: 0004_paper_shadow_audit_snapshots
Revises: 0003_shadow_comparison_snapshots
Create Date: 2026-04-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_paper_shadow_audit_snapshots"
down_revision = "0003_shadow_comparison_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_shadow_audit_snapshots",
        sa.Column("snapshot_id", sa.String(length=64), nullable=False),
        sa.Column("snapshot_batch_id", sa.String(length=64), nullable=False),
        sa.Column("intent_id", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("setup_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("source_as_of", sa.DateTime(), nullable=True),
        sa.Column("source_regime_state", sa.String(length=32), nullable=True),
        sa.Column("alignment_status", sa.String(length=64), nullable=False),
        sa.Column("paper_intent_present", sa.Boolean(), nullable=False),
        sa.Column("paper_intent_status", sa.String(length=32), nullable=True),
        sa.Column("broker_order_id", sa.String(length=128), nullable=True),
        sa.Column("paper_broker_status", sa.String(length=32), nullable=True),
        sa.Column("paper_filled", sa.Boolean(), nullable=False),
        sa.Column("shadow_present", sa.Boolean(), nullable=False),
        sa.Column("shadow_status", sa.String(length=32), nullable=True),
        sa.Column("shadow_would_fill", sa.Boolean(), nullable=True),
        sa.Column("shadow_session_date", sa.Date(), nullable=True),
        sa.Column("shadow_hypothetical_fill_price", sa.Float(), nullable=True),
        sa.Column("shadow_total_cost_bps", sa.Float(), nullable=True),
        sa.Column("shadow_slippage_alert_triggered", sa.Boolean(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("snapshot_id"),
    )
    op.create_index(
        "ix_paper_shadow_audit_snapshots_alignment_status",
        "paper_shadow_audit_snapshots",
        ["alignment_status"],
        unique=False,
    )
    op.create_index(
        "ix_paper_shadow_audit_snapshots_created_at",
        "paper_shadow_audit_snapshots",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_paper_shadow_audit_snapshots_intent_id",
        "paper_shadow_audit_snapshots",
        ["intent_id"],
        unique=False,
    )
    op.create_index(
        "ix_paper_shadow_audit_snapshots_paper_broker_status",
        "paper_shadow_audit_snapshots",
        ["paper_broker_status"],
        unique=False,
    )
    op.create_index(
        "ix_paper_shadow_audit_snapshots_paper_intent_status",
        "paper_shadow_audit_snapshots",
        ["paper_intent_status"],
        unique=False,
    )
    op.create_index(
        "ix_paper_shadow_audit_snapshots_recorded_at",
        "paper_shadow_audit_snapshots",
        ["recorded_at"],
        unique=False,
    )
    op.create_index(
        "ix_paper_shadow_audit_snapshots_setup_id",
        "paper_shadow_audit_snapshots",
        ["setup_id"],
        unique=False,
    )
    op.create_index(
        "ix_paper_shadow_audit_snapshots_shadow_session_date",
        "paper_shadow_audit_snapshots",
        ["shadow_session_date"],
        unique=False,
    )
    op.create_index(
        "ix_paper_shadow_audit_snapshots_shadow_status",
        "paper_shadow_audit_snapshots",
        ["shadow_status"],
        unique=False,
    )
    op.create_index(
        "ix_paper_shadow_audit_snapshots_snapshot_batch_id",
        "paper_shadow_audit_snapshots",
        ["snapshot_batch_id"],
        unique=False,
    )
    op.create_index(
        "ix_paper_shadow_audit_snapshots_source_as_of",
        "paper_shadow_audit_snapshots",
        ["source_as_of"],
        unique=False,
    )
    op.create_index(
        "ix_paper_shadow_audit_snapshots_source_regime_state",
        "paper_shadow_audit_snapshots",
        ["source_regime_state"],
        unique=False,
    )
    op.create_index(
        "ix_paper_shadow_audit_snapshots_symbol",
        "paper_shadow_audit_snapshots",
        ["symbol"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_paper_shadow_audit_snapshots_symbol",
        table_name="paper_shadow_audit_snapshots",
    )
    op.drop_index(
        "ix_paper_shadow_audit_snapshots_source_regime_state",
        table_name="paper_shadow_audit_snapshots",
    )
    op.drop_index(
        "ix_paper_shadow_audit_snapshots_source_as_of",
        table_name="paper_shadow_audit_snapshots",
    )
    op.drop_index(
        "ix_paper_shadow_audit_snapshots_snapshot_batch_id",
        table_name="paper_shadow_audit_snapshots",
    )
    op.drop_index(
        "ix_paper_shadow_audit_snapshots_shadow_status",
        table_name="paper_shadow_audit_snapshots",
    )
    op.drop_index(
        "ix_paper_shadow_audit_snapshots_shadow_session_date",
        table_name="paper_shadow_audit_snapshots",
    )
    op.drop_index(
        "ix_paper_shadow_audit_snapshots_setup_id",
        table_name="paper_shadow_audit_snapshots",
    )
    op.drop_index(
        "ix_paper_shadow_audit_snapshots_recorded_at",
        table_name="paper_shadow_audit_snapshots",
    )
    op.drop_index(
        "ix_paper_shadow_audit_snapshots_paper_intent_status",
        table_name="paper_shadow_audit_snapshots",
    )
    op.drop_index(
        "ix_paper_shadow_audit_snapshots_paper_broker_status",
        table_name="paper_shadow_audit_snapshots",
    )
    op.drop_index(
        "ix_paper_shadow_audit_snapshots_intent_id",
        table_name="paper_shadow_audit_snapshots",
    )
    op.drop_index(
        "ix_paper_shadow_audit_snapshots_created_at",
        table_name="paper_shadow_audit_snapshots",
    )
    op.drop_index(
        "ix_paper_shadow_audit_snapshots_alignment_status",
        table_name="paper_shadow_audit_snapshots",
    )
    op.drop_table("paper_shadow_audit_snapshots")
