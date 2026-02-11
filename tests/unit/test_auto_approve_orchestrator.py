"""Unit tests for auto-approve logic in orchestrator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call, patch

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
from levelup.core.tickets import Ticket, TicketStatus


# ---------------------------------------------------------------------------
# Helper to create test settings
# ---------------------------------------------------------------------------


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
# Project-level auto_approve
# ---------------------------------------------------------------------------


class TestProjectLevelAutoApprove:
    """Test project-level auto_approve setting in orchestrator."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.run_checkpoint")
    def test_auto_approve_skips_checkpoint_prompts(
        self, mock_checkpoint, mock_detect, mock_agent, tmp_path
    ):
        """When auto_approve=True, checkpoints should not prompt user."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test task", description="Test")
        ctx = orch.run(task)

        # run_checkpoint should never be called
        mock_checkpoint.assert_not_called()
        assert ctx.status == PipelineStatus.COMPLETED

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_auto_approve_logs_to_journal(self, mock_detect, mock_agent, tmp_path):
        """Auto-approved checkpoints should be logged to journal."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        with patch("levelup.core.orchestrator.RunJournal") as mock_journal_cls:
            mock_journal = MagicMock()
            mock_journal_cls.return_value = mock_journal

            task = TaskInput(title="Test task", description="Test")
            orch.run(task)

            # Check that checkpoints were logged with "auto-approved"
            checkpoint_calls = [
                c for c in mock_journal.log_checkpoint.call_args_list
            ]
            assert len(checkpoint_calls) > 0
            for call in checkpoint_calls:
                # Each call should be log_checkpoint(step_name, decision, feedback)
                decision = call[0][1] if len(call[0]) > 1 else call[1].get("decision")
                assert decision == "auto-approved"

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_auto_approve_creates_git_commits(self, mock_detect, mock_agent, tmp_path):
        """Auto-approved checkpoints should still create git commits."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        # Enable git commits
        settings.pipeline.create_git_branch = True

        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        with patch("levelup.core.orchestrator.Orchestrator._git_step_commit") as mock_commit:
            task = TaskInput(title="Test task", description="Test")
            orch.run(task)

            # Git commits should have been made
            assert mock_commit.call_count > 0

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_auto_approve_false_prompts_normally(
        self, mock_detect, mock_agent, tmp_path
    ):
        """When auto_approve=False, checkpoints should prompt as normal."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=False)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        with patch("levelup.core.orchestrator.run_checkpoint") as mock_checkpoint:
            # Return approve for all checkpoints
            mock_checkpoint.return_value = (CheckpointDecision.APPROVE, "")

            task = TaskInput(title="Test task", description="Test")
            orch.run(task)

            # run_checkpoint should be called
            assert mock_checkpoint.call_count > 0

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_auto_approve_with_require_checkpoints_false(
        self, mock_detect, mock_agent, tmp_path
    ):
        """When require_checkpoints=False, auto_approve is irrelevant."""
        settings = _make_settings(tmp_path, require_checkpoints=False, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        with patch("levelup.core.orchestrator.run_checkpoint") as mock_checkpoint:
            task = TaskInput(title="Test task", description="Test")
            ctx = orch.run(task)

            # Checkpoints should not run at all
            mock_checkpoint.assert_not_called()
            assert ctx.status == PipelineStatus.COMPLETED


# ---------------------------------------------------------------------------
# Ticket-level auto_approve (overrides project setting)
# ---------------------------------------------------------------------------


class TestTicketLevelAutoApprove:
    """Test per-ticket auto_approve metadata overriding project setting."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.run_checkpoint")
    def test_ticket_auto_approve_true_overrides_project_false(
        self, mock_checkpoint, mock_detect, mock_agent, tmp_path
    ):
        """Ticket with auto_approve=True should skip prompts even if project=False."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=False)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Task from ticket with auto_approve=True
        task = TaskInput(
            title="Test task",
            description="Test",
            source="ticket",
            source_id="ticket:1",
        )
        # Mock the ticket lookup
        with patch("levelup.core.tickets.read_tickets") as mock_read:
            mock_ticket = Ticket(
                number=1,
                title="Test task",
                description="Test",
                status=TicketStatus.IN_PROGRESS,
                metadata={"auto_approve": True},
            )
            mock_read.return_value = [mock_ticket]

            ctx = orch.run(task)

            # Checkpoints should be auto-approved, not prompted
            mock_checkpoint.assert_not_called()
            assert ctx.status == PipelineStatus.COMPLETED

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.run_checkpoint")
    def test_ticket_auto_approve_false_overrides_project_true(
        self, mock_checkpoint, mock_detect, mock_agent, tmp_path
    ):
        """Ticket with auto_approve=False should prompt even if project=True."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Task from ticket with auto_approve=False
        task = TaskInput(
            title="Test task",
            description="Test",
            source="ticket",
            source_id="ticket:1",
        )
        with patch("levelup.core.tickets.read_tickets") as mock_read:
            mock_ticket = Ticket(
                number=1,
                title="Test task",
                description="Test",
                status=TicketStatus.IN_PROGRESS,
                metadata={"auto_approve": False},
            )
            mock_read.return_value = [mock_ticket]

            mock_checkpoint.return_value = (CheckpointDecision.APPROVE, "")

            ctx = orch.run(task)

            # Checkpoints should prompt user
            assert mock_checkpoint.call_count > 0

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.run_checkpoint")
    def test_ticket_without_metadata_uses_project_setting(
        self, mock_checkpoint, mock_detect, mock_agent, tmp_path
    ):
        """Ticket without metadata should fall back to project setting."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(
            title="Test task",
            description="Test",
            source="ticket",
            source_id="ticket:1",
        )
        with patch("levelup.core.tickets.read_tickets") as mock_read:
            mock_ticket = Ticket(
                number=1,
                title="Test task",
                description="Test",
                status=TicketStatus.IN_PROGRESS,
                metadata=None,  # No metadata
            )
            mock_read.return_value = [mock_ticket]

            ctx = orch.run(task)

            # Should use project setting (auto_approve=True)
            mock_checkpoint.assert_not_called()
            assert ctx.status == PipelineStatus.COMPLETED

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_ticket_auto_approve_logs_correctly(
        self, mock_detect, mock_agent, tmp_path
    ):
        """Ticket-level auto-approve should log to journal."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=False)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(
            title="Test task",
            description="Test",
            source="ticket",
            source_id="ticket:1",
        )

        with patch("levelup.core.tickets.read_tickets") as mock_read:
            mock_ticket = Ticket(
                number=1,
                title="Test task",
                metadata={"auto_approve": True},
            )
            mock_read.return_value = [mock_ticket]

            with patch("levelup.core.orchestrator.RunJournal") as mock_journal_cls:
                mock_journal = MagicMock()
                mock_journal_cls.return_value = mock_journal

                orch.run(task)

                # Check journal logged auto-approved
                checkpoint_calls = mock_journal.log_checkpoint.call_args_list
                assert len(checkpoint_calls) > 0
                for call in checkpoint_calls:
                    decision = call[0][1] if len(call[0]) > 1 else call[1].get("decision")
                    assert decision == "auto-approved"


# ---------------------------------------------------------------------------
# Headless mode with auto_approve
# ---------------------------------------------------------------------------


class TestAutoApproveHeadlessMode:
    """Test auto_approve behavior in headless mode."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_headless_auto_approve_skips_db_checkpoints(
        self, mock_detect, mock_agent, tmp_path
    ):
        """In headless mode with auto_approve, should not create DB checkpoint requests."""
        from levelup.state.manager import StateManager

        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings, state_manager=mgr, headless=True)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test task", description="Test")
        ctx = orch.run(task)

        # No checkpoint requests should be created in DB
        pending = mgr.get_pending_checkpoints()
        assert len(pending) == 0
        assert ctx.status == PipelineStatus.COMPLETED

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_headless_without_auto_approve_creates_checkpoints(
        self, mock_detect, mock_agent, tmp_path
    ):
        """In headless mode without auto_approve, should create DB checkpoints."""
        from levelup.state.manager import StateManager
        import threading
        import time

        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=False)
        orch = Orchestrator(settings=settings, state_manager=mgr, headless=True)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Auto-approve checkpoints in background
        stop_event = threading.Event()

        def approve_all():
            approver_mgr = StateManager(db_path=db_path)
            while not stop_event.is_set():
                pending = approver_mgr.get_pending_checkpoints()
                for cp in pending:
                    approver_mgr.submit_checkpoint_decision(
                        cp.id, "approve", ""  # type: ignore[arg-type]
                    )
                time.sleep(0.1)

        approver = threading.Thread(target=approve_all, daemon=True)
        approver.start()

        try:
            task = TaskInput(title="Test task", description="Test")
            ctx = orch.run(task)
        finally:
            stop_event.set()
            approver.join(timeout=5)

        assert ctx.status == PipelineStatus.COMPLETED


# ---------------------------------------------------------------------------
# GUI mode with auto_approve
# ---------------------------------------------------------------------------


class TestAutoApproveGUIMode:
    """Test auto_approve behavior in GUI mode."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_gui_mode_auto_approve_skips_db_checkpoints(
        self, mock_detect, mock_agent, tmp_path
    ):
        """In GUI mode with auto_approve, should not create checkpoint requests."""
        from levelup.state.manager import StateManager

        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        # GUI mode uses state_manager but not headless flag
        orch = Orchestrator(settings=settings, state_manager=mgr, headless=False)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test task", description="Test")
        ctx = orch.run(task)

        # No checkpoint requests should be created
        pending = mgr.get_pending_checkpoints()
        assert len(pending) == 0
        assert ctx.status == PipelineStatus.COMPLETED


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestAutoApproveEdgeCases:
    """Test edge cases for auto_approve functionality."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_auto_approve_with_non_ticket_task(
        self, mock_detect, mock_agent, tmp_path
    ):
        """Auto-approve should work with tasks not from tickets."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Task without ticket source
        task = TaskInput(title="Direct task", description="Not from ticket")

        with patch("levelup.core.orchestrator.run_checkpoint") as mock_checkpoint:
            ctx = orch.run(task)

            # Should auto-approve based on project setting
            mock_checkpoint.assert_not_called()
            assert ctx.status == PipelineStatus.COMPLETED

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_ticket_not_found_uses_project_setting(
        self, mock_detect, mock_agent, tmp_path
    ):
        """If ticket lookup fails, should fall back to project setting."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(
            title="Test task",
            description="Test",
            source="ticket",
            source_id="ticket:999",  # Non-existent
        )

        with patch("levelup.core.tickets.read_tickets") as mock_read:
            mock_read.return_value = []  # Ticket not found

            with patch("levelup.core.orchestrator.run_checkpoint") as mock_checkpoint:
                ctx = orch.run(task)

                # Should use project setting
                mock_checkpoint.assert_not_called()
                assert ctx.status == PipelineStatus.COMPLETED

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_ticket_metadata_empty_dict_uses_project_setting(
        self, mock_detect, mock_agent, tmp_path
    ):
        """Ticket with metadata={} should use project setting."""
        settings = _make_settings(tmp_path, require_checkpoints=True, auto_approve=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(
            title="Test task",
            description="Test",
            source="ticket",
            source_id="ticket:1",
        )

        with patch("levelup.core.tickets.read_tickets") as mock_read:
            mock_ticket = Ticket(
                number=1,
                title="Test task",
                metadata={},  # Empty dict, no auto_approve key
            )
            mock_read.return_value = [mock_ticket]

            with patch("levelup.core.orchestrator.run_checkpoint") as mock_checkpoint:
                ctx = orch.run(task)

                # Should use project setting
                mock_checkpoint.assert_not_called()
                assert ctx.status == PipelineStatus.COMPLETED
