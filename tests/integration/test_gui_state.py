"""Integration test: GUI state read/write round-trips through DB."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from levelup.core.context import PipelineContext, PipelineStatus, TaskInput
from levelup.state.manager import StateManager


class TestGuiStateRoundTrip:
    def test_create_run_and_read_back(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = PipelineContext(
            run_id="gui_test_1",
            task=TaskInput(title="GUI test", description="Test from GUI"),
            project_path=tmp_path,
            status=PipelineStatus.RUNNING,
        )
        mgr.register_run(ctx)

        record = mgr.get_run("gui_test_1")
        assert record is not None
        assert record.task_title == "GUI test"
        assert record.task_description == "Test from GUI"

    def test_checkpoint_round_trip(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")
        ctx = PipelineContext(
            run_id="gui_test_2",
            task=TaskInput(title="Checkpoint round-trip"),
            project_path=tmp_path,
            status=PipelineStatus.RUNNING,
        )
        mgr.register_run(ctx)

        # Create checkpoint with data
        data = {"step_name": "requirements", "requirements": {"summary": "Test"}}
        req_id = mgr.create_checkpoint_request(
            "gui_test_2", "requirements", json.dumps(data)
        )

        # Read back pending
        pending = mgr.get_pending_checkpoints()
        assert len(pending) == 1
        assert pending[0].run_id == "gui_test_2"

        # Parse checkpoint data
        parsed = json.loads(pending[0].checkpoint_data)  # type: ignore[arg-type]
        assert parsed["step_name"] == "requirements"

        # Submit decision
        mgr.submit_checkpoint_decision(req_id, "approve", "")

        # Verify decision
        result = mgr.get_checkpoint_decision("gui_test_2", "requirements")
        assert result is not None
        assert result[0] == "approve"

    def test_multiple_runs_visible(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")

        for i in range(5):
            ctx = PipelineContext(
                run_id=f"multi_{i}",
                task=TaskInput(title=f"Task {i}"),
                project_path=tmp_path,
                status=PipelineStatus.RUNNING,
            )
            mgr.register_run(ctx)

        runs = mgr.list_runs()
        assert len(runs) == 5

    def test_cleanup_removes_finished_runs(self, tmp_path):
        mgr = StateManager(db_path=tmp_path / "test.db")

        # Create a completed run and a running run
        ctx1 = PipelineContext(
            run_id="done_1",
            task=TaskInput(title="Done"),
            project_path=tmp_path,
            status=PipelineStatus.RUNNING,
        )
        mgr.register_run(ctx1)
        ctx1.status = PipelineStatus.COMPLETED
        mgr.update_run(ctx1)

        ctx2 = PipelineContext(
            run_id="active_1",
            task=TaskInput(title="Active"),
            project_path=tmp_path,
            status=PipelineStatus.RUNNING,
        )
        mgr.register_run(ctx2)

        # Simulate cleanup: delete completed runs
        completed = mgr.list_runs(status_filter="completed")
        for r in completed:
            mgr.delete_run(r.run_id)

        remaining = mgr.list_runs()
        assert len(remaining) == 1
        assert remaining[0].run_id == "active_1"
