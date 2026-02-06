"""Tests for state DB schema and connection helper."""

from __future__ import annotations

import sqlite3

import pytest

from levelup.state.db import get_connection, init_db


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
