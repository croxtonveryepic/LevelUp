"""Integration test: headless pipeline with pre-populated checkpoint decisions."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from levelup.config.settings import (
    LevelUpSettings,
    LLMSettings,
    PipelineSettings,
    ProjectSettings,
)
from levelup.core.context import (
    CheckpointDecision,
    PipelineContext,
    PipelineStatus,
    TaskInput,
)
from levelup.core.orchestrator import Orchestrator
from levelup.state.manager import StateManager


def _make_settings(tmp_path: Path) -> LevelUpSettings:
    return LevelUpSettings(
        llm=LLMSettings(api_key="test-key", model="test-model"),
        project=ProjectSettings(path=tmp_path),
        pipeline=PipelineSettings(
            require_checkpoints=True,
            create_git_branch=False,
            max_code_iterations=2,
        ),
    )


class TestHeadlessPipeline:
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_headless_with_checkpoint_decisions(
        self, mock_detect, mock_agent, tmp_path
    ):
        """Simulate a full headless run where a background thread provides
        checkpoint decisions (as the GUI would)."""
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)
        settings = _make_settings(tmp_path)

        orch = Orchestrator(settings=settings, state_manager=mgr, headless=True)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Thread that polls for pending checkpoints and approves them
        stop_event = threading.Event()

        def approve_checkpoints():
            approver_mgr = StateManager(db_path=db_path)
            while not stop_event.is_set():
                pending = approver_mgr.get_pending_checkpoints()
                for cp in pending:
                    approver_mgr.submit_checkpoint_decision(
                        cp.id, "approve", ""  # type: ignore[arg-type]
                    )
                time.sleep(0.1)

        approver = threading.Thread(target=approve_checkpoints, daemon=True)
        approver.start()

        try:
            task = TaskInput(title="Headless test task", description="Integration test")
            ctx = orch.run(task)
        finally:
            stop_event.set()
            approver.join(timeout=5)

        assert ctx.status == PipelineStatus.COMPLETED

        # Verify the run is tracked in DB
        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.status == "completed"

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_headless_checkpoint_reject_aborts(
        self, mock_detect, mock_agent, tmp_path
    ):
        """Headless run where the GUI rejects at the first checkpoint."""
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings, state_manager=mgr, headless=True)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        stop_event = threading.Event()

        def reject_checkpoints():
            rejector_mgr = StateManager(db_path=db_path)
            while not stop_event.is_set():
                pending = rejector_mgr.get_pending_checkpoints()
                for cp in pending:
                    rejector_mgr.submit_checkpoint_decision(
                        cp.id, "reject", ""  # type: ignore[arg-type]
                    )
                time.sleep(0.1)

        rejector = threading.Thread(target=reject_checkpoints, daemon=True)
        rejector.start()

        try:
            task = TaskInput(title="Reject test", description="Should abort")
            ctx = orch.run(task)
        finally:
            stop_event.set()
            rejector.join(timeout=5)

        assert ctx.status == PipelineStatus.ABORTED

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_headless_waiting_for_input_status(
        self, mock_detect, mock_agent, tmp_path
    ):
        """Verify the run enters WAITING_FOR_INPUT while waiting for checkpoint."""
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings, state_manager=mgr, headless=True)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        observed_statuses = []
        stop_event = threading.Event()

        def observe_and_approve():
            observer_mgr = StateManager(db_path=db_path)
            while not stop_event.is_set():
                runs = observer_mgr.list_runs()
                for r in runs:
                    observed_statuses.append(r.status)
                pending = observer_mgr.get_pending_checkpoints()
                for cp in pending:
                    observer_mgr.submit_checkpoint_decision(
                        cp.id, "approve", ""  # type: ignore[arg-type]
                    )
                time.sleep(0.05)

        observer = threading.Thread(target=observe_and_approve, daemon=True)
        observer.start()

        try:
            task = TaskInput(title="Status test")
            ctx = orch.run(task)
        finally:
            stop_event.set()
            observer.join(timeout=5)

        assert ctx.status == PipelineStatus.COMPLETED
        # We should have observed waiting_for_input at least once
        assert "waiting_for_input" in observed_statuses
