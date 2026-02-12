"""Tests for multi-project GUI support: projects table, CRUD, filtering."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from levelup.state.db import (
    CURRENT_SCHEMA_VERSION,
    _get_schema_version,
    get_connection,
    init_db,
)
from levelup.state.manager import StateManager


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.db"
    init_db(p)
    return p


@pytest.fixture()
def mgr(db_path: Path) -> StateManager:
    return StateManager(db_path)


# -- Schema -----------------------------------------------------------------


class TestProjectsTableMigration:
    def test_schema_version_is_7(self) -> None:
        assert CURRENT_SCHEMA_VERSION == 7

    def test_migration_creates_projects_table(self, db_path: Path) -> None:
        conn = get_connection(db_path)
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
            ).fetchone()
            assert row is not None
        finally:
            conn.close()

    def test_schema_version_stored(self, db_path: Path) -> None:
        conn = get_connection(db_path)
        try:
            assert _get_schema_version(conn) == 7
        finally:
            conn.close()

    def test_projects_table_columns(self, db_path: Path) -> None:
        conn = get_connection(db_path)
        try:
            cursor = conn.execute("PRAGMA table_info(projects)")
            cols = {row[1] for row in cursor.fetchall()}
            assert cols == {"id", "project_path", "display_name", "added_at"}
        finally:
            conn.close()

    def test_project_path_unique_constraint(self, db_path: Path) -> None:
        conn = get_connection(db_path)
        try:
            conn.execute(
                "INSERT INTO projects (project_path, added_at) VALUES (?, datetime('now'))",
                ("/a",),
            )
            conn.commit()
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO projects (project_path, added_at) VALUES (?, datetime('now'))",
                    ("/a",),
                )
        finally:
            conn.close()


# -- StateManager CRUD ------------------------------------------------------


class TestAddProject:
    def test_add_project_basic(self, mgr: StateManager) -> None:
        mgr.add_project("/projects/foo")
        projects = mgr.list_known_projects()
        assert "/projects/foo" in projects

    def test_add_project_with_display_name(self, mgr: StateManager, db_path: Path) -> None:
        mgr.add_project("/projects/bar", display_name="My Bar")
        conn = get_connection(db_path)
        try:
            row = conn.execute(
                "SELECT display_name FROM projects WHERE project_path = ?",
                ("/projects/bar",),
            ).fetchone()
            assert row[0] == "My Bar"
        finally:
            conn.close()

    def test_add_project_idempotent(self, mgr: StateManager) -> None:
        mgr.add_project("/projects/foo")
        mgr.add_project("/projects/foo")  # Should not raise
        conn = get_connection(mgr._db_path)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM projects WHERE project_path = ?",
                ("/projects/foo",),
            ).fetchone()[0]
            assert count == 1
        finally:
            conn.close()


class TestRemoveProject:
    def test_remove_existing(self, mgr: StateManager) -> None:
        mgr.add_project("/projects/foo")
        mgr.remove_project("/projects/foo")
        conn = get_connection(mgr._db_path)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM projects WHERE project_path = ?",
                ("/projects/foo",),
            ).fetchone()[0]
            assert count == 0
        finally:
            conn.close()

    def test_remove_nonexistent_no_error(self, mgr: StateManager) -> None:
        mgr.remove_project("/projects/nonexistent")  # Should not raise

    def test_remove_does_not_delete_runs(self, mgr: StateManager, db_path: Path) -> None:
        """Removing a project from the projects table should not delete runs."""
        mgr.add_project("/projects/foo")
        # Manually insert a run
        conn = get_connection(db_path)
        try:
            conn.execute(
                """INSERT INTO runs (run_id, task_title, project_path, status, started_at, updated_at)
                   VALUES ('r1', 'task', '/projects/foo', 'completed', datetime('now'), datetime('now'))"""
            )
            conn.commit()
        finally:
            conn.close()

        mgr.remove_project("/projects/foo")

        conn = get_connection(db_path)
        try:
            row = conn.execute("SELECT COUNT(*) FROM runs WHERE project_path = ?", ("/projects/foo",)).fetchone()
            assert row[0] == 1  # Run still exists
        finally:
            conn.close()


class TestListKnownProjects:
    def test_empty_db(self, mgr: StateManager) -> None:
        assert mgr.list_known_projects() == []

    def test_from_projects_table(self, mgr: StateManager) -> None:
        mgr.add_project("/a")
        mgr.add_project("/b")
        projects = mgr.list_known_projects()
        assert "/a" in projects
        assert "/b" in projects

    def test_from_runs_table(self, mgr: StateManager, db_path: Path) -> None:
        conn = get_connection(db_path)
        try:
            conn.execute(
                """INSERT INTO runs (run_id, task_title, project_path, status, started_at, updated_at)
                   VALUES ('r1', 'task', '/from/runs', 'completed', datetime('now'), datetime('now'))"""
            )
            conn.commit()
        finally:
            conn.close()
        assert "/from/runs" in mgr.list_known_projects()

    def test_from_tickets_table(self, mgr: StateManager, db_path: Path) -> None:
        mgr.add_ticket("/from/tickets", "Test ticket")
        assert "/from/tickets" in mgr.list_known_projects()

    def test_deduplication(self, mgr: StateManager, db_path: Path) -> None:
        """Same project_path in multiple tables should appear only once."""
        shared_path = "/shared/project"
        mgr.add_project(shared_path)
        mgr.add_ticket(shared_path, "Test ticket")
        conn = get_connection(db_path)
        try:
            conn.execute(
                """INSERT INTO runs (run_id, task_title, project_path, status, started_at, updated_at)
                   VALUES ('r1', 'task', ?, 'completed', datetime('now'), datetime('now'))""",
                (shared_path,),
            )
            conn.commit()
        finally:
            conn.close()

        projects = mgr.list_known_projects()
        assert projects.count(shared_path) == 1

    def test_sorted_order(self, mgr: StateManager) -> None:
        mgr.add_project("/z")
        mgr.add_project("/a")
        mgr.add_project("/m")
        projects = mgr.list_known_projects()
        assert projects == sorted(projects)
