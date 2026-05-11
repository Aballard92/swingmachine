"""Add immutable runtime event ledger.

Revision ID: 0002_runtime_events
Revises: 0001_initial_schema
Create Date: 2026-04-25

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_runtime_events"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("command", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("setup_id", sa.String(length=128), nullable=True),
        sa.Column("intent_id", sa.String(length=128), nullable=True),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_runtime_events_command", "runtime_events", ["command"], unique=False)
    op.create_index("ix_runtime_events_event_type", "runtime_events", ["event_type"], unique=False)
    op.create_index("ix_runtime_events_intent_id", "runtime_events", ["intent_id"], unique=False)
    op.create_index("ix_runtime_events_mode", "runtime_events", ["mode"], unique=False)
    op.create_index(
        "ix_runtime_events_occurred_at", "runtime_events", ["occurred_at"], unique=False
    )
    op.create_index("ix_runtime_events_run_id", "runtime_events", ["run_id"], unique=False)
    op.create_index("ix_runtime_events_setup_id", "runtime_events", ["setup_id"], unique=False)
    op.create_index("ix_runtime_events_symbol", "runtime_events", ["symbol"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_runtime_events_symbol", table_name="runtime_events")
    op.drop_index("ix_runtime_events_setup_id", table_name="runtime_events")
    op.drop_index("ix_runtime_events_run_id", table_name="runtime_events")
    op.drop_index("ix_runtime_events_occurred_at", table_name="runtime_events")
    op.drop_index("ix_runtime_events_mode", table_name="runtime_events")
    op.drop_index("ix_runtime_events_intent_id", table_name="runtime_events")
    op.drop_index("ix_runtime_events_event_type", table_name="runtime_events")
    op.drop_index("ix_runtime_events_command", table_name="runtime_events")
    op.drop_table("runtime_events")
