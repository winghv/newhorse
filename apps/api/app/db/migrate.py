"""
Lightweight schema migration for SQLite development.
Adds missing columns to existing tables.
"""
from sqlalchemy import inspect, text
from app.db.base import engine
from app.core.terminal_ui import ui


def _column_exists(inspector, table: str, column: str) -> bool:
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def run_migrations():
    """Add any missing columns to existing tables."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    with engine.connect() as conn:
        # Projects table: add override_provider_id, override_api_key
        if "projects" in existing_tables:
            if not _column_exists(inspector, "projects", "override_provider_id"):
                conn.execute(text("ALTER TABLE projects ADD COLUMN override_provider_id VARCHAR(8)"))
                ui.info("Added projects.override_provider_id", "Migration")
            if not _column_exists(inspector, "projects", "override_api_key"):
                conn.execute(text("ALTER TABLE projects ADD COLUMN override_api_key TEXT"))
                ui.info("Added projects.override_api_key", "Migration")

        # Messages table: add model_id, provider_id
        if "messages" in existing_tables:
            if not _column_exists(inspector, "messages", "model_id"):
                conn.execute(text("ALTER TABLE messages ADD COLUMN model_id VARCHAR(128)"))
                ui.info("Added messages.model_id", "Migration")
            if not _column_exists(inspector, "messages", "provider_id"):
                conn.execute(text("ALTER TABLE messages ADD COLUMN provider_id VARCHAR(8)"))
                ui.info("Added messages.provider_id", "Migration")

        conn.commit()
