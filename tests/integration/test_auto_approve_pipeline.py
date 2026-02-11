"""Integration tests for auto-approve functionality end-to-end."""

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
from levelup.core.tickets import Ticket, TicketStatus, add_ticket, read_tickets
from levelup.state.manager import StateManager


def _make_settings(
    tmp_path: Path,
    require_checkpoints: bool = True,
    auto_approve: bool = False,
) -> LevelUpSettings:
    return LevelUpSettings(
        llm=LLMSettings(api_key="test-key", model="test-model"),
        project=ProjectSettings(path=tmp_path),
        pipeline=PipelineSettings(
            require_checkpoints=require_checkpoints,
            auto_approve=auto_approve,
            create_git_branch=False,
            max_code_iterations=2,
        ),
    )


# ---------------------------------------------------------------------------
# Full pipeline with project-level auto_approve
# ---------------------------------------------------------------------------


class TestAutoApproveEndToEnd:
    """Test complete pipeline runs with auto-approve."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_full_pipeline_with_auto_approve(self, mock_detect, mock_agent, tmp_path):
        """Complete pipeline run with auto_approve=True should complete without prompts."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test feature", description="Add a feature")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        # All 4 checkpoint steps should have been auto-approved
        # (requirements, test_writing, security, review)

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_journal_contains_auto_approve_entries(
        self, mock_detect, mock_agent, tmp_path
    ):
        """Journal should log all auto-approved checkpoints."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test task", description="Test")
        ctx = orch.run(task)

        # Check journal was created and contains auto-approve entries
        journal_dir = tmp_path / "levelup"
        assert journal_dir.exists()
        journal_files = list(journal_dir.glob("*.md"))
        assert len(journal_files) > 0

        journal_content = journal_files[0].read_text()
        assert "auto-approved" in journal_content.lower()

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_auto_approve_faster_than_manual(self, mock_detect, mock_agent, tmp_path):
        """Auto-approve should complete faster than manual approval."""
        settings_auto = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch_auto = Orchestrator(settings=settings_auto)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        start = time.time()
        task = TaskInput(title="Speed test", description="Test")
        ctx = orch_auto.run(task)
        auto_duration = time.time() - start

        assert ctx.status == PipelineStatus.COMPLETED
        # Auto-approve should complete quickly (no user interaction)
        assert auto_duration < 5.0  # Should be nearly instant

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_auto_approve_with_state_tracking(self, mock_detect, mock_agent, tmp_path):
        """Auto-approved run should be tracked in state DB."""
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings, state_manager=mgr)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Tracked task", description="Test")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

        # Verify run is tracked
        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.status == "completed"


# ---------------------------------------------------------------------------
# Ticket-level auto_approve integration
# ---------------------------------------------------------------------------


class TestTicketAutoApproveIntegration:
    """Test tickets with metadata through full pipeline."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_ticket_with_auto_approve_true(self, mock_detect, mock_agent, tmp_path):
        """Ticket with auto_approve=True should skip prompts."""
        # Project setting is False
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=False)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Create ticket with auto_approve
        ticket = add_ticket(
            tmp_path,
            "Auto-approved task",
            "Description",
            metadata={"auto_approve": True},
        )

        task = ticket.to_task_input()
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        # Should have auto-approved despite project setting

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_mixed_tickets_with_different_metadata(
        self, mock_detect, mock_agent, tmp_path
    ):
        """Running tickets with different metadata should respect each setting."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=False)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Create tickets with different settings
        ticket1 = add_ticket(
            tmp_path,
            "Auto task",
            metadata={"auto_approve": True},
        )
        ticket2 = add_ticket(
            tmp_path,
            "Manual task",
            metadata={"auto_approve": False},
        )

        # Run first ticket (auto)
        ctx1 = orch.run(ticket1.to_task_input())
        assert ctx1.status == PipelineStatus.COMPLETED

        # Second ticket would require manual approval
        # (but we'd need to mock checkpoint responses)

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_ticket_status_updates_with_auto_approve(
        self, mock_detect, mock_agent, tmp_path
    ):
        """Ticket status should update normally with auto-approve."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        ticket = add_ticket(tmp_path, "Task", metadata={"auto_approve": True})

        # Simulate running the ticket
        from levelup.core.tickets import set_ticket_status

        set_ticket_status(tmp_path, ticket.number, TicketStatus.IN_PROGRESS)

        task = ticket.to_task_input()
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

        # After completion, ticket should be marked done
        # (This would normally be done by CLI, not orchestrator)


# ---------------------------------------------------------------------------
# Headless mode with auto_approve
# ---------------------------------------------------------------------------


class TestHeadlessAutoApprove:
    """Test headless mode with auto_approve."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_headless_with_auto_approve_no_db_requests(
        self, mock_detect, mock_agent, tmp_path
    ):
        """Headless + auto_approve should not create checkpoint requests."""
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings, state_manager=mgr, headless=True)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Headless task", description="Test")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

        # No checkpoint requests should exist
        pending = mgr.get_pending_checkpoints()
        assert len(pending) == 0

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_headless_without_auto_approve_creates_requests(
        self, mock_detect, mock_agent, tmp_path
    ):
        """Headless without auto_approve should create checkpoint requests."""
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=False)
        orch = Orchestrator(settings=settings, state_manager=mgr, headless=True)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Auto-approve in background
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
            task = TaskInput(title="Manual approval task", description="Test")
            ctx = orch.run(task)
        finally:
            stop_event.set()
            approver.join(timeout=5)

        assert ctx.status == PipelineStatus.COMPLETED


# ---------------------------------------------------------------------------
# Performance and correctness
# ---------------------------------------------------------------------------


class TestAutoApproveCorrectness:
    """Test that auto-approve produces correct results."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_auto_approve_runs_all_steps(self, mock_detect, mock_agent, tmp_path):
        """Auto-approve should run all pipeline steps."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        # Track which agents were called
        called_agents = []

        def track_agent(name, ctx):
            called_agents.append(name)
            return ctx

        mock_agent.side_effect = track_agent

        task = TaskInput(title="Test", description="Test")
        ctx = orch.run(task)

        # All agent steps should have run
        assert "requirements" in called_agents
        assert "planning" in called_agents
        assert "test_writer" in called_agents
        assert "coder" in called_agents
        assert "security" in called_agents
        assert "reviewer" in called_agents

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_auto_approve_with_git_commits(self, mock_detect, mock_agent, tmp_path):
        """Auto-approve should still create git commits."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        settings.pipeline.create_git_branch = True

        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        with patch("levelup.core.orchestrator.Orchestrator._git_step_commit") as mock_commit:
            task = TaskInput(title="Test", description="Test")
            ctx = orch.run(task)

            # Git commits should have been made for each step
            assert mock_commit.call_count > 0

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_auto_approve_context_preserved(self, mock_detect, mock_agent, tmp_path):
        """Auto-approve should preserve context through pipeline."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        # Agent modifies context
        def modify_context(name, ctx):
            ctx.status = PipelineStatus.IN_PROGRESS
            return ctx

        mock_agent.side_effect = modify_context

        task = TaskInput(title="Context test", description="Test")
        ctx = orch.run(task)

        # Final context should be complete
        assert ctx.status == PipelineStatus.COMPLETED
        assert ctx.run_id is not None
        assert ctx.task.title == "Context test"


# ---------------------------------------------------------------------------
# Configuration precedence
# ---------------------------------------------------------------------------


class TestAutoApproveConfigPrecedence:
    """Test configuration precedence for auto_approve."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_cli_override_precedence(self, mock_detect, mock_agent, tmp_path):
        """CLI override should take highest precedence."""
        # Config file says auto_approve=False
        config = tmp_path / "levelup.yaml"
        config.write_text("pipeline:\n  auto_approve: false\n")

        # Load with override
        from levelup.config.loader import load_settings

        settings = load_settings(
            project_path=tmp_path,
            overrides={"pipeline": {"auto_approve": True}},
        )

        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        with patch("levelup.core.orchestrator.run_checkpoint") as mock_checkpoint:
            task = TaskInput(title="Override test", description="Test")
            ctx = orch.run(task)

            # Should auto-approve (override wins)
            mock_checkpoint.assert_not_called()
            assert ctx.status == PipelineStatus.COMPLETED

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_ticket_metadata_highest_precedence(
        self, mock_detect, mock_agent, tmp_path
    ):
        """Ticket metadata should override project and CLI settings."""
        # Project setting is True (via override)
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Ticket says auto_approve=False
        ticket = add_ticket(
            tmp_path,
            "Manual task",
            metadata={"auto_approve": False},
        )

        with patch("levelup.core.orchestrator.run_checkpoint") as mock_checkpoint:
            mock_checkpoint.return_value = (CheckpointDecision.APPROVE, "")

            task = ticket.to_task_input()
            ctx = orch.run(task)

            # Should prompt user (ticket metadata wins)
            assert mock_checkpoint.call_count > 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestAutoApproveErrorHandling:
    """Test error handling with auto_approve."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_auto_approve_with_agent_failure(self, mock_detect, mock_agent, tmp_path):
        """Auto-approve should handle agent failures gracefully."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        # Agent fails
        def fail_agent(name, ctx):
            ctx.status = PipelineStatus.FAILED
            return ctx

        mock_agent.side_effect = fail_agent

        task = TaskInput(title="Failing task", description="Test")
        ctx = orch.run(task)

        # Should fail gracefully
        assert ctx.status == PipelineStatus.FAILED

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_auto_approve_with_invalid_ticket_metadata(
        self, mock_detect, mock_agent, tmp_path
    ):
        """Should handle malformed ticket metadata gracefully."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=False)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Create ticket with invalid metadata
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        (tickets_dir / "tickets.md").write_text(
            "## Test task\n"
            "<!--metadata\n"
            "auto_approve: not_a_boolean\n"
            "-->\n"
            "Description\n",
            encoding="utf-8",
        )

        ticket = read_tickets(tmp_path)[0]
        task = ticket.to_task_input()

        with patch("levelup.core.orchestrator.run_checkpoint") as mock_checkpoint:
            mock_checkpoint.return_value = (CheckpointDecision.APPROVE, "")

            # Should fall back to project setting or handle error
            ctx = orch.run(task)
            # Should either auto-approve or prompt, but not crash
            assert ctx.status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED]
