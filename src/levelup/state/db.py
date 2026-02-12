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

CURRENT_SCHEMA_VERSION = 7

# List of (target_version, sql) tuples. Each migration upgrades from target_version-1.
MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            rowid      INTEGER PRIMARY KEY CHECK (rowid = 1),
            version    INTEGER NOT NULL,
            applied_at TEXT NOT NULL
        );
        INSERT OR REPLACE INTO schema_version (rowid, version, applied_at)
        VALUES (1, 1, datetime('now'));
        """,
    ),
    (
        2,
        """
        ALTER TABLE runs ADD COLUMN total_cost_usd REAL DEFAULT 0;
        UPDATE schema_version SET version = 2, applied_at = datetime('now') WHERE rowid = 1;
        """,
    ),
    (
        3,
        """
        ALTER TABLE runs ADD COLUMN pause_requested INTEGER DEFAULT 0;
        UPDATE schema_version SET version = 3, applied_at = datetime('now') WHERE rowid = 1;
        """,
    ),
    (
        4,
        """
        ALTER TABLE runs ADD COLUMN ticket_number INTEGER;
        CREATE INDEX IF NOT EXISTS idx_runs_project_ticket ON runs(project_path, ticket_number);
        UPDATE schema_version SET version = 4, applied_at = datetime('now') WHERE rowid = 1;
        """,
    ),
    (
        5,
        """
        ALTER TABLE runs ADD COLUMN input_tokens INTEGER DEFAULT 0;
        ALTER TABLE runs ADD COLUMN output_tokens INTEGER DEFAULT 0;
        UPDATE schema_version SET version = 5, applied_at = datetime('now') WHERE rowid = 1;
        """,
    ),
    (
        6,
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            project_path    TEXT NOT NULL,
            ticket_number   INTEGER NOT NULL,
            title           TEXT NOT NULL,
            description     TEXT NOT NULL DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'pending',
            metadata_json   TEXT,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,
            UNIQUE(project_path, ticket_number)
        );
        CREATE INDEX IF NOT EXISTS idx_tickets_project ON tickets(project_path);
        CREATE INDEX IF NOT EXISTS idx_tickets_project_status ON tickets(project_path, status);
        UPDATE schema_version SET version = 6, applied_at = datetime('now') WHERE rowid = 1;
        """,
    ),
    (
        7,
        """
        CREATE TABLE IF NOT EXISTS projects (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            project_path TEXT NOT NULL UNIQUE,
            display_name TEXT,
            added_at     TEXT NOT NULL
        );
        UPDATE schema_version SET version = 7, applied_at = datetime('now') WHERE rowid = 1;
        """,
    ),
]


def _get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the current schema version, or 0 if the table doesn't exist."""
    try:
        row = conn.execute("SELECT version FROM schema_version WHERE rowid = 1").fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Run any pending schema migrations."""
    current = _get_schema_version(conn)

    if current > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {current} is newer than the code supports "
            f"(max {CURRENT_SCHEMA_VERSION}). Please upgrade LevelUp."
        )

    if current == CURRENT_SCHEMA_VERSION:
        return

    for target_version, sql in MIGRATIONS:
        if target_version > current:
            conn.executescript(sql)

    conn.commit()


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
    """Initialize the database schema and run any pending migrations."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        _run_migrations(conn)
    finally:
        conn.close()
