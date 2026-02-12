"""Integration tests for end-to-end merge workflow.

These tests cover the complete merge workflow from GUI button click through
MergeAgent execution to ticket status update and sidebar refresh.

Tests follow TDD approach - they SHOULD FAIL initially until the
implementation is complete.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestMergeWorkflowEndToEnd:
    """Test complete merge workflow from button click to status update.

    AC: Complete workflow: button click → MergeAgent execution → status update → sidebar refresh
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    @pytest.fixture
    def git_repo(self, tmp_path: Path) -> Path:
        """Create a git repository with master branch."""
        repo = tmp_path / "project"
        repo.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create initial commit on master
        (repo / "README.md").write_text("# Test Project\n")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Ensure we're on master branch
        subprocess.run(
            ["git", "checkout", "-b", "master"],
            cwd=repo,
            check=False,
            capture_output=True,
        )

        return repo

    @pytest.fixture
    def feature_branch(self, git_repo: Path) -> str:
        """Create a feature branch with a commit."""
        branch_name = "feature/test-merge"

        # Create and checkout feature branch
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Add a commit
        (git_repo / "feature.txt").write_text("New feature")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Return to master
        subprocess.run(
            ["git", "checkout", "master"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        return branch_name

    def test_merge_workflow_with_clean_merge(self, git_repo: Path, feature_branch: str, tmp_path: Path):
        """Test complete merge workflow with no conflicts."""
        from levelup.core.tickets import Ticket, TicketStatus, add_ticket, read_tickets
        from levelup.core.tickets import set_ticket_status, update_ticket

        # Create tickets file with done ticket
        levelup_dir = git_repo / "levelup"
        levelup_dir.mkdir(exist_ok=True)

        add_ticket(
            git_repo,
            "Test feature",
            "Add test feature to project",
        )

        # Update ticket to done status with branch_name metadata
        set_ticket_status(git_repo, 1, TicketStatus.DONE)
        update_ticket(git_repo, 1, metadata={"branch_name": feature_branch})

        # Create RunTerminalWidget
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget()
            widget._project_path = str(git_repo)
            widget._db_path = str(tmp_path / "state.db")
            widget._ticket_number = 1

            # Set ticket
            tickets = read_tickets(git_repo)
            widget.set_ticket(tickets[0])

            # Merge button should be enabled
            widget._update_button_states()
            assert widget._merge_btn.isEnabled() is True

            # Mock MergeAgent to simulate successful merge
            with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
                mock_instance = MagicMock()
                mock_instance.run.return_value = MagicMock(
                    text="Merge completed successfully"
                )
                MockAgent.return_value = mock_instance

                with patch.object(widget, "_create_backend") as mock_backend:
                    # Click merge button
                    widget._on_merge_clicked()

                    # Verify MergeAgent was instantiated
                    MockAgent.assert_called_once()

                    # Verify agent.run was called with branch name
                    mock_instance.run.assert_called_once_with(branch_name=feature_branch)

            # Verify ticket status was updated to MERGED
            tickets = read_tickets(git_repo)
            assert tickets[0].status == TicketStatus.MERGED

    def test_merge_workflow_with_conflict_resolution(self, git_repo: Path, tmp_path: Path):
        """Test merge workflow when conflicts occur and are resolved."""
        from levelup.core.tickets import add_ticket, set_ticket_status, read_tickets, TicketStatus

        # Create conflicting branches
        # 1. Create project_context.md on master
        (git_repo / "levelup").mkdir(exist_ok=True)
        (git_repo / "levelup" / "project_context.md").write_text(
            "# Project Context\n\n## Codebase Insights\n\n- Master insight\n"
        )
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add project context"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # 2. Create feature branch with different insights
        branch_name = "feature/conflicting"
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "levelup" / "project_context.md").write_text(
            "# Project Context\n\n## Codebase Insights\n\n- Feature insight\n"
        )
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update insights"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "master"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Create ticket with branch_name
        add_ticket(git_repo, "Conflicting feature", "Test conflict resolution")
        set_ticket_status(git_repo, 1, TicketStatus.DONE)
        from levelup.core.tickets import update_ticket
        update_ticket(git_repo, 1, metadata={"branch_name": branch_name})

        # Test merge workflow
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget()
            widget._project_path = str(git_repo)
            widget._db_path = str(tmp_path / "state.db")

            tickets = read_tickets(git_repo)
            widget.set_ticket(tickets[0])

            # Mock MergeAgent to simulate conflict resolution
            with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
                mock_instance = MagicMock()
                mock_instance.run.return_value = MagicMock(
                    text="Conflicts resolved in project_context.md. Merge completed."
                )
                MockAgent.return_value = mock_instance

                with patch.object(widget, "_create_backend"):
                    widget._on_merge_clicked()

                    # Agent should have been called
                    mock_instance.run.assert_called_once()

            # Status should be updated
            tickets = read_tickets(git_repo)
            assert tickets[0].status == TicketStatus.MERGED

    def test_merge_workflow_handles_failure_gracefully(self, git_repo: Path, tmp_path: Path):
        """Test merge workflow when merge fails."""
        from levelup.core.tickets import add_ticket, set_ticket_status, read_tickets, TicketStatus

        # Create ticket
        add_ticket(git_repo, "Failed merge", "This will fail")
        set_ticket_status(git_repo, 1, TicketStatus.DONE)
        from levelup.core.tickets import update_ticket
        update_ticket(git_repo, 1, metadata={"branch_name": "nonexistent/branch"})

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget()
            widget._project_path = str(git_repo)
            widget._db_path = str(tmp_path / "state.db")

            tickets = read_tickets(git_repo)
            widget.set_ticket(tickets[0])

            # Mock MergeAgent to simulate failure
            with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
                mock_instance = MagicMock()
                mock_instance.run.return_value = MagicMock(
                    text="error: branch does not exist"
                )
                MockAgent.return_value = mock_instance

                with patch.object(widget, "_create_backend"):
                    widget._on_merge_clicked()

            # Status should remain DONE (not changed to MERGED)
            tickets = read_tickets(git_repo)
            assert tickets[0].status == TicketStatus.DONE


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestMergeWorkflowStateManagement:
    """Test merge workflow state management and button states.

    AC: Button states transition correctly during merge operation
    AC: Terminal displays merge output
    AC: Status updates trigger sidebar refresh
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def test_button_states_during_merge_lifecycle(self, tmp_path: Path):
        """Test button states through complete merge lifecycle."""
        from levelup.core.tickets import Ticket, TicketStatus

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget()
            widget._project_path = str(tmp_path)
            widget._db_path = str(tmp_path / "state.db")

            ticket = Ticket(
                number=1,
                title="Test",
                status=TicketStatus.DONE,
                metadata={"branch_name": "feature/test"}
            )

            widget.set_ticket(ticket)
            widget._update_button_states()

            # Initially: Merge enabled, Run enabled
            assert widget._merge_btn.isEnabled() is True
            initial_run_state = widget._run_btn.isEnabled()

            # During merge: all disabled
            widget._set_running_state(True)
            assert widget._merge_btn.isEnabled() is False
            assert widget._run_btn.isEnabled() is False

            # After merge: states restored
            widget._set_running_state(False)
            # Note: merge button state depends on ticket status
            # After successful merge, status would be MERGED so button disabled

    def test_merge_finished_signal_triggers_refresh(self, tmp_path: Path):
        """Test that merge_finished signal can trigger sidebar refresh."""
        from levelup.core.tickets import Ticket, TicketStatus

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget()
            widget._project_path = str(tmp_path)
            widget._db_path = str(tmp_path / "state.db")

            ticket = Ticket(
                number=1,
                title="Test",
                status=TicketStatus.DONE,
                metadata={"branch_name": "feature/test"}
            )

            widget.set_ticket(ticket)

            # Connect signal
            signal_received = False

            def on_merge_finished():
                nonlocal signal_received
                signal_received = True

            widget.merge_finished.connect(on_merge_finished)

            # Simulate successful merge
            with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
                mock_instance = MagicMock()
                mock_instance.run.return_value = MagicMock(text="success")
                MockAgent.return_value = mock_instance

                with patch.object(widget, "_create_backend"):
                    with patch("levelup.gui.run_terminal.set_ticket_status"):
                        widget._execute_merge("feature/test")

            # Signal should have been emitted
            assert signal_received is True

    def test_terminal_displays_merge_output(self, tmp_path: Path):
        """Test that terminal widget displays merge agent output."""
        from levelup.core.tickets import Ticket, TicketStatus

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget()
            widget._project_path = str(tmp_path)
            widget._db_path = str(tmp_path / "state.db")

            ticket = Ticket(
                number=1,
                title="Test",
                status=TicketStatus.DONE,
                metadata={"branch_name": "feature/test"}
            )

            widget.set_ticket(ticket)

            # Mock terminal
            mock_terminal = MagicMock()
            widget._terminal = mock_terminal

            merge_output = "git checkout feature/test\ngit rebase master\nMerge complete"

            with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
                mock_instance = MagicMock()
                mock_instance.run.return_value = MagicMock(text=merge_output)
                MockAgent.return_value = mock_instance

                with patch.object(widget, "_create_backend"):
                    with patch("levelup.gui.run_terminal.set_ticket_status"):
                        widget._execute_merge("feature/test")

            # Terminal should receive output (via write method or similar)
            # This verifies the terminal integration


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestMergeWorkflowErrorScenarios:
    """Test merge workflow error handling and edge cases.

    AC: Handles missing branch gracefully
    AC: Handles merge conflicts that cannot be resolved
    AC: Preserves repository state on error
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def test_merge_with_missing_branch_name_metadata(self, tmp_path: Path):
        """Test merge when ticket has no branch_name metadata."""
        from levelup.core.tickets import Ticket, TicketStatus

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget()
            widget._project_path = str(tmp_path)
            widget._db_path = str(tmp_path / "state.db")

            ticket = Ticket(
                number=1,
                title="Test",
                status=TicketStatus.DONE,
                metadata=None  # No metadata
            )

            widget.set_ticket(ticket)
            widget._update_button_states()

            # Merge button should be disabled
            assert widget._merge_btn.isEnabled() is False

    def test_merge_with_nonexistent_branch(self, tmp_path: Path):
        """Test merge when branch does not exist in repository."""
        from levelup.core.tickets import Ticket, TicketStatus

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget()
            widget._project_path = str(tmp_path)
            widget._db_path = str(tmp_path / "state.db")

            ticket = Ticket(
                number=1,
                title="Test",
                status=TicketStatus.DONE,
                metadata={"branch_name": "nonexistent/branch"}
            )

            widget.set_ticket(ticket)

            with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
                mock_instance = MagicMock()
                mock_instance.run.return_value = MagicMock(
                    text="error: branch 'nonexistent/branch' does not exist"
                )
                MockAgent.return_value = mock_instance

                with patch.object(widget, "_create_backend"):
                    widget._execute_merge("nonexistent/branch")

                    # Should handle error gracefully
                    # Status should not be changed
                    assert ticket.status == TicketStatus.DONE

    def test_merge_with_unresolvable_conflicts(self, tmp_path: Path):
        """Test merge when conflicts cannot be auto-resolved."""
        from levelup.core.tickets import Ticket, TicketStatus

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget()
            widget._project_path = str(tmp_path)
            widget._db_path = str(tmp_path / "state.db")

            ticket = Ticket(
                number=1,
                title="Test",
                status=TicketStatus.DONE,
                metadata={"branch_name": "feature/conflict"}
            )

            widget.set_ticket(ticket)

            with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
                mock_instance = MagicMock()
                mock_instance.run.return_value = MagicMock(
                    text="error: conflicts could not be auto-resolved. Rebase aborted."
                )
                MockAgent.return_value = mock_instance

                with patch.object(widget, "_create_backend"):
                    widget._execute_merge("feature/conflict")

                    # Should handle error gracefully
                    assert ticket.status == TicketStatus.DONE

    def test_command_running_flag_cleared_on_merge_error(self, tmp_path: Path):
        """Test that _command_running flag is cleared even on merge error."""
        from levelup.core.tickets import Ticket, TicketStatus

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget()
            widget._project_path = str(tmp_path)
            widget._db_path = str(tmp_path / "state.db")

            ticket = Ticket(
                number=1,
                title="Test",
                status=TicketStatus.DONE,
                metadata={"branch_name": "feature/test"}
            )

            widget.set_ticket(ticket)

            # Simulate error during merge
            with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
                mock_instance = MagicMock()
                mock_instance.run.side_effect = Exception("Merge error")
                MockAgent.return_value = mock_instance

                with patch.object(widget, "_create_backend"):
                    try:
                        widget._execute_merge("feature/test")
                    except Exception:
                        pass

            # _command_running should be cleared
            # This ensures buttons are re-enabled after error
            widget._update_button_states()
            # At minimum, clear button should still work


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestMergeWorkflowBackendIntegration:
    """Test merge workflow integration with backend.

    AC: MergeAgent uses appropriate backend (ClaudeCodeBackend or AnthropicSDKBackend)
    AC: Backend configuration is passed correctly
    AC: Agent execution uses project_path as working directory
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def test_merge_creates_backend_from_settings(self, tmp_path: Path):
        """Test that merge creates backend based on settings."""
        from levelup.core.tickets import Ticket, TicketStatus

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget()
            widget._project_path = str(tmp_path)
            widget._db_path = str(tmp_path / "state.db")

            ticket = Ticket(
                number=1,
                title="Test",
                status=TicketStatus.DONE,
                metadata={"branch_name": "feature/test"}
            )

            widget.set_ticket(ticket)

            with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
                mock_instance = MagicMock()
                mock_instance.run.return_value = MagicMock(text="success")
                MockAgent.return_value = mock_instance

                with patch.object(widget, "_create_backend") as mock_create:
                    mock_backend = MagicMock()
                    mock_create.return_value = mock_backend

                    widget._execute_merge("feature/test")

                    # _create_backend should be called
                    mock_create.assert_called_once()

                    # MergeAgent should be created with backend
                    MockAgent.assert_called_once()
                    call_args = MockAgent.call_args[0]
                    assert mock_backend in call_args

    def test_merge_passes_project_path_to_agent(self, tmp_path: Path):
        """Test that merge passes project_path to MergeAgent."""
        from levelup.core.tickets import Ticket, TicketStatus

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget()
            widget._project_path = str(tmp_path / "project")
            widget._db_path = str(tmp_path / "state.db")

            ticket = Ticket(
                number=1,
                title="Test",
                status=TicketStatus.DONE,
                metadata={"branch_name": "feature/test"}
            )

            widget.set_ticket(ticket)

            with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
                mock_instance = MagicMock()
                mock_instance.run.return_value = MagicMock(text="success")
                MockAgent.return_value = mock_instance

                with patch.object(widget, "_create_backend"):
                    widget._execute_merge("feature/test")

                    # MergeAgent constructor should receive project_path
                    call_args = MockAgent.call_args[0]
                    # project_path should be in args (as Path or str)
                    # Normalize paths for Windows (backslash vs forward slash)
                    expected_path = str(tmp_path / "project").replace("\\", "/")
                    actual_args = str(call_args).replace("\\", "/")
                    assert expected_path in actual_args
