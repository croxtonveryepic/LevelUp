"""Tests for state DB schema and connection helper."""

from __future__ import annotations

import sqlite3

import pytest

from levelup.state.db import (
    CURRENT_SCHEMA_VERSION,
    _get_schema_version,
    _run_migrations,
    get_connection,
    init_db,
)


class TestStateDB:
    def test_init_db_creates_tables(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)

        conn = sqlite3.connect(str(db_path))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t[0] for t in tables]
        conn.close()

        assert "runs" in table_names
        assert "checkpoint_requests" in table_names

    def test_init_db_creates_parent_dirs(self, tmp_path):
        db_path = tmp_path / "sub" / "dir" / "test.db"
        init_db(db_path)
        assert db_path.exists()

    def test_init_db_idempotent(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)
        init_db(db_path)  # should not raise

    def test_get_connection_wal_mode(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"

    def test_get_connection_row_factory(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)
        assert conn.row_factory == sqlite3.Row
        conn.close()

    def test_runs_table_columns(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)
        info = conn.execute("PRAGMA table_info(runs)").fetchall()
        col_names = [row["name"] for row in info]
        conn.close()

        expected = [
            "run_id", "task_title", "task_description", "project_path",
            "status", "current_step", "language", "framework", "test_runner",
            "error_message", "context_json", "started_at", "updated_at", "pid",
        ]
        for col in expected:
            assert col in col_names, f"Missing column: {col}"

    def test_checkpoint_requests_table_columns(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)
        info = conn.execute("PRAGMA table_info(checkpoint_requests)").fetchall()
        col_names = [row["name"] for row in info]
        conn.close()

        expected = [
            "id", "run_id", "step_name", "checkpoint_data",
            "status", "decision", "feedback", "created_at", "decided_at",
        ]
        for col in expected:
            assert col in col_names, f"Missing column: {col}"

    def test_indexes_created(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = sqlite3.connect(str(db_path))
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        index_names = [i[0] for i in indexes]
        conn.close()

        assert "idx_runs_status" in index_names
        assert "idx_cp_pending" in index_names


class TestSchemaVersioning:
    def test_fresh_db_gets_current_version(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)
        version = _get_schema_version(conn)
        conn.close()
        assert version == CURRENT_SCHEMA_VERSION

    def test_schema_version_table_exists(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = sqlite3.connect(str(db_path))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        conn.close()
        assert "schema_version" in table_names

    def test_pre_migration_db_gets_upgraded(self, tmp_path):
        """A DB with full schema but no schema_version table should be migrated."""
        db_path = tmp_path / "test.db"
        # Create a DB with the full schema but no schema_version table
        # (simulating a pre-migration database)
        conn = get_connection(db_path)
        from levelup.state.db import SCHEMA_SQL

        conn.executescript(SCHEMA_SQL)
        conn.commit()
        # Verify no schema_version yet
        assert _get_schema_version(conn) == 0
        conn.close()

        # init_db should detect version 0 and run migrations
        init_db(db_path)

        conn = get_connection(db_path)
        version = _get_schema_version(conn)
        conn.close()
        assert version == CURRENT_SCHEMA_VERSION

    def test_newer_db_raises_error(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)

        # Manually set version to a future value
        conn = get_connection(db_path)
        conn.execute("UPDATE schema_version SET version = 999 WHERE rowid = 1")
        conn.commit()

        with pytest.raises(RuntimeError, match="newer than the code supports"):
            _run_migrations(conn)
        conn.close()

    def test_init_db_still_idempotent(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)
        init_db(db_path)  # should not raise or duplicate

        conn = get_connection(db_path)
        version = _get_schema_version(conn)
        conn.close()
        assert version == CURRENT_SCHEMA_VERSION

    def test_version_0_detected_for_no_table(self, tmp_path):
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        # Empty DB — no schema_version table
        version = _get_schema_version(conn)
        conn.close()
        assert version == 0


class TestMigrationV4:
    def test_current_schema_version_is_4(self):
        assert CURRENT_SCHEMA_VERSION == 5

    def test_migration_adds_ticket_number_column(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)
        info = conn.execute("PRAGMA table_info(runs)").fetchall()
        col_names = [row["name"] for row in info]
        conn.close()
        assert "ticket_number" in col_names

    def test_migration_creates_project_ticket_index(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = sqlite3.connect(str(db_path))
        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        index_names = [i[0] for i in indexes]
        conn.close()
        assert "idx_runs_project_ticket" in index_names

    def test_upgrade_from_v3_to_v4(self, tmp_path):
        """Simulate a v3 DB and verify migration to v5."""
        db_path = tmp_path / "test.db"
        # Create a DB at v3 by initializing with old schema
        from levelup.state.db import SCHEMA_SQL, MIGRATIONS

        conn = get_connection(db_path)
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        # Run only migrations up to v3
        for target_version, sql in MIGRATIONS:
            if target_version <= 3:
                conn.executescript(sql)
        conn.commit()

        version = _get_schema_version(conn)
        assert version == 3
        conn.close()

        # Now run init_db which should migrate to v5
        init_db(db_path)

        conn = get_connection(db_path)
        version = _get_schema_version(conn)
        assert version == 5
        info = conn.execute("PRAGMA table_info(runs)").fetchall()
        col_names = [row["name"] for row in info]
        conn.close()
        assert "ticket_number" in col_names
        assert "input_tokens" in col_names
        assert "output_tokens" in col_names
