from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from swingmachine.storage import Base


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_alembic_upgrade_creates_current_schema(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'migration.db'}"
    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url, future=True)
    inspector = inspect(engine)
    expected_tables = {table.name for table in Base.metadata.sorted_tables}

    assert set(inspector.get_table_names()) == expected_tables | {"alembic_version"}
    for table_name in expected_tables:
        expected_columns = [column.name for column in Base.metadata.tables[table_name].columns]
        actual_columns = [column["name"] for column in inspector.get_columns(table_name)]
        assert actual_columns == expected_columns

    runtime_indexes = {index["name"] for index in inspector.get_indexes("runtime_runs")}
    assert runtime_indexes >= {
        "ix_runtime_runs_command",
        "ix_runtime_runs_mode",
        "ix_runtime_runs_started_at",
        "ix_runtime_runs_status",
    }

    event_indexes = {index["name"] for index in inspector.get_indexes("runtime_events")}
    assert event_indexes >= {
        "ix_runtime_events_command",
        "ix_runtime_events_event_type",
        "ix_runtime_events_occurred_at",
        "ix_runtime_events_run_id",
    }
