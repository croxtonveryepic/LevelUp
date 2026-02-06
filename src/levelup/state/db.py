"""SQLite schema and connection helper for state management."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".levelup" / "state.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id         TEXT PRIMARY KEY,
    task_title     TEXT NOT NULL,
    task_description TEXT NOT NULL DEFAULT '',
    project_path   TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',
    current_step   TEXT,
    language       TEXT,
    framework      TEXT,
    test_runner    TEXT,
    error_message  TEXT,
    context_json   TEXT,
    started_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    pid            INTEGER
);

CREATE TABLE IF NOT EXISTS checkpoint_requests (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT NOT NULL REFERENCES runs(run_id),
    step_name      TEXT NOT NULL,
    checkpoint_data TEXT,
    status         TEXT NOT NULL DEFAULT 'pending',
    decision       TEXT,
    feedback       TEXT DEFAULT '',
    created_at     TEXT NOT NULL,
    decided_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_cp_pending ON checkpoint_requests(run_id, status);
"""


def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Create a short-lived SQLite connection with WAL mode and busy timeout."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """Initialize the database schema."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
