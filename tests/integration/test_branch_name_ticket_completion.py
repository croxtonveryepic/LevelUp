"""Integration tests for branch name recording on ticket completion.

Tests the end-to-end flow of recording branch names in ticket metadata
when a pipeline completes successfully, including real orchestrator and
ticket system interactions.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import git
import pytest
from typer.testing import CliRunner

from levelup.cli.app import app
from levelup.config.settings import LevelUpSettings, LLMSettings, PipelineSettings, ProjectSettings
from levelup.core.context import PipelineContext, PipelineStatus, TaskInput
from levelup.core.orchestrator import Orchestrator
from levelup.core.tickets import TicketStatus, add_ticket, read_tickets


runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def git_repo(tmp_path: Path) -> git.Repo:
    """Create a git repository for testing."""
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    (tmp_path / "init.txt").write_text("initial commit")
    repo.index.add(["init.txt"])
    repo.index.commit("initial commit")
    return repo


@pytest.fixture
def project_with_tickets(tmp_path: Path) -> Path:
    """Create a project with tickets directory."""
    tickets_dir = tmp_path / "levelup"
    tickets_dir.mkdir(exist_ok=True)
    return tmp_path


@pytest.fixture
def settings(tmp_path: Path) -> LevelUpSettings:
    """Create test settings."""
    return LevelUpSettings(
        llm=LLMSettings(api_key="test-key", model="test-model", backend="claude_code"),
        project=ProjectSettings(path=tmp_path),
        pipeline=PipelineSettings(
            create_git_branch=True,
            require_checkpoints=False,
        ),
    )


# ---------------------------------------------------------------------------
# End-to-end integration tests
# ---------------------------------------------------------------------------


class TestBranchNameTicketCompletionIntegration:
    """Integration tests for complete ticket flow with branch name recording."""

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_full_ticket_completion_records_branch_name(
        self, mock_sm_cls, mock_orch_cls, project_with_tickets: Path
    ):
        """Complete flow: start ticket, run pipeline, complete ticket with branch name."""
        # Create a ticket
        ticket = add_ticket(project_with_tickets, "Implement login", "Add user authentication")

        # Mock successful pipeline completion
        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "integration123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/integration123"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        # Run the pipeline
        result = runner.invoke(
            app,
            [
                "run",
                "Implement login",
                "--path",
                str(project_with_tickets),
                "--ticket",
                "1",
                "--no-checkpoints",
            ],
        )

        assert result.exit_code == 0

        # Verify ticket was marked as done with branch name
        tickets = read_tickets(project_with_tickets)
        assert len(tickets) == 1
        assert tickets[0].status == TicketStatus.DONE
        assert tickets[0].metadata is not None
        assert tickets[0].metadata["branch_name"] == "levelup/integration123"

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_ticket_next_workflow_with_branch_name(
        self, mock_sm_cls, mock_orch_cls, project_with_tickets: Path
    ):
        """Test --ticket-next workflow records branch name."""
        # Create multiple tickets
        add_ticket(project_with_tickets, "First task", "Do first")
        add_ticket(project_with_tickets, "Second task", "Do second")

        # Mock successful completion
        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "nexttask456"
        mock_ctx.branch_naming = "ai/{task_title}-{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "ai/first-task-nexttask456"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        # Run with --ticket-next
        result = runner.invoke(
            app,
            [
                "run",
                "--ticket-next",
                "--path",
                str(project_with_tickets),
                "--no-checkpoints",
            ],
        )

        assert result.exit_code == 0

        # Verify first ticket has branch name
        tickets = read_tickets(project_with_tickets)
        assert tickets[0].status == TicketStatus.DONE
        assert tickets[0].metadata["branch_name"] == "ai/first-task-nexttask456"
        # Second ticket should still be pending
        assert tickets[1].status == TicketStatus.PENDING

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_multiple_runs_different_branch_names(
        self, mock_sm_cls, mock_orch_cls, project_with_tickets: Path
    ):
        """Running multiple tickets should record different branch names."""
        add_ticket(project_with_tickets, "Task 1", "First task")
        add_ticket(project_with_tickets, "Task 2", "Second task")

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        # Run first ticket
        mock_ctx1 = MagicMock()
        mock_ctx1.status.value = "completed"
        mock_ctx1.task.source = "ticket"
        mock_ctx1.task.source_id = "ticket:1"
        mock_ctx1.run_id = "run001"
        mock_ctx1.branch_naming = "levelup/{run_id}"

        mock_orch1 = MagicMock()
        mock_orch1.run.return_value = mock_ctx1
        mock_orch1._build_branch_name.return_value = "levelup/run001"
        mock_orch_cls.return_value = mock_orch1

        result1 = runner.invoke(
            app,
            [
                "run",
                "Task 1",
                "--path",
                str(project_with_tickets),
                "--ticket",
                "1",
                "--no-checkpoints",
            ],
        )

        # Run second ticket
        mock_ctx2 = MagicMock()
        mock_ctx2.status.value = "completed"
        mock_ctx2.task.source = "ticket"
        mock_ctx2.task.source_id = "ticket:2"
        mock_ctx2.run_id = "run002"
        mock_ctx2.branch_naming = "levelup/{run_id}"

        mock_orch2 = MagicMock()
        mock_orch2.run.return_value = mock_ctx2
        mock_orch2._build_branch_name.return_value = "levelup/run002"
        mock_orch_cls.return_value = mock_orch2

        result2 = runner.invoke(
            app,
            [
                "run",
                "Task 2",
                "--path",
                str(project_with_tickets),
                "--ticket",
                "2",
                "--no-checkpoints",
            ],
        )

        # Verify both have different branch names
        tickets = read_tickets(project_with_tickets)
        assert tickets[0].metadata["branch_name"] == "levelup/run001"
        assert tickets[1].metadata["branch_name"] == "levelup/run002"

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_branch_name_persists_through_ticket_operations(
        self, mock_sm_cls, mock_orch_cls, project_with_tickets: Path
    ):
        """Branch name should persist through subsequent ticket operations."""
        add_ticket(project_with_tickets, "Task", "Description")

        # Complete with branch name
        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "persist789"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/persist789"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            [
                "run",
                "Task",
                "--path",
                str(project_with_tickets),
                "--ticket",
                "1",
                "--no-checkpoints",
            ],
        )

        # Mark as merged
        result = runner.invoke(
            app, ["tickets", "merged", "1", "--path", str(project_with_tickets)]
        )

        # Branch name should still be there
        tickets = read_tickets(project_with_tickets)
        assert tickets[0].status == TicketStatus.MERGED
        assert tickets[0].metadata["branch_name"] == "levelup/persist789"

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_failed_pipeline_does_not_mark_done_or_record_branch(
        self, mock_sm_cls, mock_orch_cls, project_with_tickets: Path
    ):
        """Failed pipeline should not mark ticket as done or record branch name."""
        add_ticket(project_with_tickets, "Failing task", "Will fail")

        # Mock failed completion
        mock_ctx = MagicMock()
        mock_ctx.status.value = "failed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "failed999"
        mock_ctx.branch_naming = "levelup/{run_id}"
        mock_ctx.error_message = "Tests failed"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        with pytest.raises(SystemExit):
            result = runner.invoke(
                app,
                [
                    "run",
                    "Failing task",
                    "--path",
                    str(project_with_tickets),
                    "--ticket",
                    "1",
                    "--no-checkpoints",
                ],
            )

        # Verify ticket is not marked done and has no branch_name
        tickets = read_tickets(project_with_tickets)
        assert tickets[0].status == TicketStatus.IN_PROGRESS
        if tickets[0].metadata:
            assert "branch_name" not in tickets[0].metadata

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_branch_name_with_custom_naming_convention(
        self, mock_sm_cls, mock_orch_cls, project_with_tickets: Path
    ):
        """Should record branch name using custom naming convention."""
        add_ticket(project_with_tickets, "Fix critical bug", "Emergency fix")

        # Mock completion with custom convention
        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "custom001"
        mock_ctx.branch_naming = "hotfix/{date}-{task_title}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "hotfix/20260210-fix-critical-bug"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            [
                "run",
                "Fix critical bug",
                "--path",
                str(project_with_tickets),
                "--ticket",
                "1",
                "--no-checkpoints",
            ],
        )

        # Verify custom branch name
        tickets = read_tickets(project_with_tickets)
        assert tickets[0].metadata["branch_name"] == "hotfix/20260210-fix-critical-bug"

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_branch_name_with_auto_approve_metadata(
        self, mock_sm_cls, mock_orch_cls, project_with_tickets: Path
    ):
        """Branch name should coexist with auto_approve metadata."""
        add_ticket(
            project_with_tickets,
            "Auto approved task",
            "Will auto approve",
            metadata={"auto_approve": True},
        )

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "auto123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/auto123"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            [
                "run",
                "Auto approved task",
                "--path",
                str(project_with_tickets),
                "--ticket",
                "1",
                "--no-checkpoints",
            ],
        )

        # Verify both metadata fields exist
        tickets = read_tickets(project_with_tickets)
        assert tickets[0].metadata["auto_approve"] is True
        assert tickets[0].metadata["branch_name"] == "levelup/auto123"


# ---------------------------------------------------------------------------
# Headless mode integration tests
# ---------------------------------------------------------------------------


class TestBranchNameHeadlessMode:
    """Test branch name recording in headless mode."""

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_headless_mode_records_branch_name(
        self, mock_sm_cls, mock_orch_cls, project_with_tickets: Path
    ):
        """Headless mode should record branch name same as interactive."""
        add_ticket(project_with_tickets, "Headless task", "Run in background")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "headless001"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/headless001"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            [
                "run",
                "Headless task",
                "--path",
                str(project_with_tickets),
                "--ticket",
                "1",
                "--headless",
                "--no-checkpoints",
            ],
        )

        tickets = read_tickets(project_with_tickets)
        assert tickets[0].metadata["branch_name"] == "levelup/headless001"


# ---------------------------------------------------------------------------
# Error handling integration tests
# ---------------------------------------------------------------------------


class TestBranchNameErrorHandlingIntegration:
    """Integration tests for error handling in branch name recording."""

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_missing_orchestrator_method_does_not_crash(
        self, mock_sm_cls, mock_orch_cls, project_with_tickets: Path
    ):
        """Should handle gracefully if orchestrator doesn't have _build_branch_name."""
        add_ticket(project_with_tickets, "Task", "Description")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "nomethod123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        # No _build_branch_name method
        delattr(mock_orch, "_build_branch_name")
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        # Should not crash
        result = runner.invoke(
            app,
            [
                "run",
                "Task",
                "--path",
                str(project_with_tickets),
                "--ticket",
                "1",
                "--no-checkpoints",
            ],
        )

        assert result.exit_code == 0

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_update_ticket_failure_does_not_prevent_completion(
        self, mock_sm_cls, mock_orch_cls, project_with_tickets: Path
    ):
        """If update_ticket fails, pipeline completion should still show success."""
        add_ticket(project_with_tickets, "Task", "Description")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "updatefail123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/updatefail123"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        # Mock update_ticket to raise an error
        with patch("levelup.core.tickets.update_ticket", side_effect=Exception("Update failed")):
            # Should still complete successfully
            result = runner.invoke(
                app,
                [
                    "run",
                    "Task",
                    "--path",
                    str(project_with_tickets),
                    "--ticket",
                    "1",
                    "--no-checkpoints",
                ],
            )

            # Pipeline should still report success even if metadata update failed
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestBranchNameBackwardCompatibility:
    """Test backward compatibility with existing tickets."""

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_tickets_without_metadata_get_branch_name(
        self, mock_sm_cls, mock_orch_cls, project_with_tickets: Path
    ):
        """Old tickets without any metadata should get branch_name added."""
        # Create ticket without metadata (old style)
        add_ticket(project_with_tickets, "Old ticket", "No metadata")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_ctx.run_id = "compat123"
        mock_ctx.branch_naming = "levelup/{run_id}"

        mock_orch = MagicMock()
        mock_orch.run.return_value = mock_ctx
        mock_orch._build_branch_name.return_value = "levelup/compat123"
        mock_orch_cls.return_value = mock_orch

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(
            app,
            [
                "run",
                "Old ticket",
                "--path",
                str(project_with_tickets),
                "--ticket",
                "1",
                "--no-checkpoints",
            ],
        )

        # Should now have metadata with branch_name
        tickets = read_tickets(project_with_tickets)
        assert tickets[0].metadata is not None
        assert tickets[0].metadata["branch_name"] == "levelup/compat123"
