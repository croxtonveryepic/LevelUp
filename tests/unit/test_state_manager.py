"""Tests for StateManager CRUD operations."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from levelup.core.context import PipelineContext, PipelineStatus, TaskInput
from levelup.state.manager import StateManager


def _make_ctx(
    run_id: str = "test123",
    title: str = "Test task",
    project_path: str | Path = "/tmp/proj",
) -> PipelineContext:
    return PipelineContext(
        run_id=run_id,
        task=TaskInput(title=title, description="A test task"),
        project_path=Path(project_path),
        status=PipelineStatus.RUNNING,
    )


class TestStateManagerRegisterRun:
    def test_register_run(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)

        record = mgr.get_run("test123")
        assert record is not None
        assert record.run_id == "test123"
        assert record.task_title == "Test task"
        assert record.status == "running"
        assert record.pid == os.getpid()

    def test_register_run_duplicate_raises(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)

        with pytest.raises(Exception):
            mgr.register_run(ctx)


class TestStateManagerUpdateRun:
    def test_update_run(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)

        ctx.status = PipelineStatus.COMPLETED
        ctx.current_step = "review"
        ctx.language = "python"
        mgr.update_run(ctx)

        record = mgr.get_run("test123")
        assert record is not None
        assert record.status == "completed"
        assert record.current_step == "review"
        assert record.language == "python"
        assert record.context_json is not None


class TestStateManagerGetRun:
    def test_get_run_not_found(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        assert mgr.get_run("nonexistent") is None


class TestStateManagerListRuns:
    def test_list_runs_empty(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        assert mgr.list_runs() == []

    def test_list_runs_multiple(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        for i in range(3):
            ctx = _make_ctx(run_id=f"run{i}", project_path=tmp_path)
            mgr.register_run(ctx)

        runs = mgr.list_runs()
        assert len(runs) == 3

    def test_list_runs_with_filter(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")

        ctx1 = _make_ctx(run_id="run1", project_path=tmp_path)
        mgr.register_run(ctx1)

        ctx2 = _make_ctx(run_id="run2", project_path=tmp_path)
        mgr.register_run(ctx2)
        ctx2.status = PipelineStatus.COMPLETED
        mgr.update_run(ctx2)

        running = mgr.list_runs(status_filter="running")
        assert len(running) == 1
        assert running[0].run_id == "run1"

    def test_list_runs_limit(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        for i in range(10):
            ctx = _make_ctx(run_id=f"run{i}", project_path=tmp_path)
            mgr.register_run(ctx)

        runs = mgr.list_runs(limit=3)
        assert len(runs) == 3


class TestStateManagerDeleteRun:
    def test_delete_run(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)

        mgr.delete_run("test123")
        assert mgr.get_run("test123") is None

    def test_delete_run_removes_checkpoints(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)
        mgr.create_checkpoint_request("test123", "requirements", '{"test": true}')

        mgr.delete_run("test123")
        assert mgr.get_pending_checkpoints() == []


class TestStateManagerCheckpoints:
    def test_create_checkpoint_request(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)

        req_id = mgr.create_checkpoint_request("test123", "requirements", '{"data": 1}')
        assert isinstance(req_id, int)

        pending = mgr.get_pending_checkpoints()
        assert len(pending) == 1
        assert pending[0].run_id == "test123"
        assert pending[0].step_name == "requirements"

    def test_submit_checkpoint_decision(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)

        req_id = mgr.create_checkpoint_request("test123", "requirements")
        mgr.submit_checkpoint_decision(req_id, "approve", "")

        # No longer pending
        assert mgr.get_pending_checkpoints() == []

        # Decision retrievable
        result = mgr.get_checkpoint_decision("test123", "requirements")
        assert result is not None
        assert result[0] == "approve"
        assert result[1] == ""

    def test_submit_checkpoint_with_feedback(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)

        req_id = mgr.create_checkpoint_request("test123", "requirements")
        mgr.submit_checkpoint_decision(req_id, "revise", "Add more tests")

        result = mgr.get_checkpoint_decision("test123", "requirements")
        assert result is not None
        assert result[0] == "revise"
        assert result[1] == "Add more tests"

    def test_get_checkpoint_decision_none_when_pending(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)
        mgr.create_checkpoint_request("test123", "requirements")

        assert mgr.get_checkpoint_decision("test123", "requirements") is None

    def test_get_checkpoint_decision_none_when_missing(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        assert mgr.get_checkpoint_decision("nonexistent", "requirements") is None


class TestStateManagerPauseRequest:
    def test_request_pause(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)

        assert mgr.is_pause_requested("test123") is False

        mgr.request_pause("test123")
        assert mgr.is_pause_requested("test123") is True

    def test_clear_pause_request(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)

        mgr.request_pause("test123")
        assert mgr.is_pause_requested("test123") is True

        mgr.clear_pause_request("test123")
        assert mgr.is_pause_requested("test123") is False

    def test_is_pause_requested_nonexistent_run(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        assert mgr.is_pause_requested("nonexistent") is False


class TestStateManagerRegisterRunTicket:
    def test_register_run_stores_ticket_number(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        ctx.task = TaskInput(
            title="Test", description="", source="ticket", source_id="ticket:5"
        )
        mgr.register_run(ctx)

        record = mgr.get_run("test123")
        assert record is not None
        assert record.ticket_number == 5

    def test_register_run_no_ticket_number_when_manual(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)

        record = mgr.get_run("test123")
        assert record is not None
        assert record.ticket_number is None


class TestStateManagerGetRunForTicket:
    def test_returns_most_recent_run(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        project = str(tmp_path)

        # Create two runs for the same ticket
        ctx1 = _make_ctx(run_id="run1", project_path=tmp_path)
        ctx1.task = TaskInput(title="T", description="", source="ticket", source_id="ticket:3")
        mgr.register_run(ctx1)

        ctx2 = _make_ctx(run_id="run2", project_path=tmp_path)
        ctx2.task = TaskInput(title="T", description="", source="ticket", source_id="ticket:3")
        mgr.register_run(ctx2)

        result = mgr.get_run_for_ticket(project, 3)
        assert result is not None
        assert result.run_id == "run2"

    def test_returns_none_when_no_match(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        assert mgr.get_run_for_ticket(str(tmp_path), 99) is None

    def test_filters_by_project_path(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")

        ctx = _make_ctx(run_id="run1", project_path=tmp_path)
        ctx.task = TaskInput(title="T", description="", source="ticket", source_id="ticket:1")
        mgr.register_run(ctx)

        # Different project path should not find the run
        assert mgr.get_run_for_ticket("/other/project", 1) is None


class TestStateManagerHasActiveRunForTicket:
    def test_returns_active_run(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        project = str(tmp_path)

        ctx = _make_ctx(project_path=tmp_path)
        ctx.task = TaskInput(title="T", description="", source="ticket", source_id="ticket:2")
        mgr.register_run(ctx)

        result = mgr.has_active_run_for_ticket(project, 2)
        assert result is not None
        assert result.run_id == "test123"

    def test_returns_none_for_completed_run(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        project = str(tmp_path)

        ctx = _make_ctx(project_path=tmp_path)
        ctx.task = TaskInput(title="T", description="", source="ticket", source_id="ticket:2")
        mgr.register_run(ctx)
        ctx.status = PipelineStatus.COMPLETED
        mgr.update_run(ctx)

        assert mgr.has_active_run_for_ticket(project, 2) is None

    def test_returns_none_for_failed_run(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        project = str(tmp_path)

        ctx = _make_ctx(project_path=tmp_path)
        ctx.task = TaskInput(title="T", description="", source="ticket", source_id="ticket:2")
        mgr.register_run(ctx)
        ctx.status = PipelineStatus.FAILED
        mgr.update_run(ctx)

        assert mgr.has_active_run_for_ticket(project, 2) is None

    def test_returns_none_when_no_runs(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        assert mgr.has_active_run_for_ticket(str(tmp_path), 1) is None


class TestStateManagerDeadRuns:
    def test_mark_dead_runs_cleans_dead_pid(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)

        # Manually set PID to a dead process
        conn = mgr._conn()
        conn.execute("UPDATE runs SET pid = 99999999 WHERE run_id = 'test123'")
        conn.commit()
        conn.close()

        with patch("levelup.state.manager._is_pid_alive", return_value=False):
            count = mgr.mark_dead_runs()

        assert count == 1
        record = mgr.get_run("test123")
        assert record is not None
        assert record.status == "failed"
        assert record.error_message == "Process died"

    def test_mark_dead_runs_ignores_alive(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = _make_ctx(project_path=tmp_path)
        mgr.register_run(ctx)

        with patch("levelup.state.manager._is_pid_alive", return_value=True):
            count = mgr.mark_dead_runs()

        assert count == 0
        record = mgr.get_run("test123")
        assert record is not None
        assert record.status == "running"
