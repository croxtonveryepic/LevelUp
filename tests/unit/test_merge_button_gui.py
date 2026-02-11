"""Unit tests for Merge button in RunTerminalWidget (GUI).

Tests cover the Merge button functionality in the ticket detail panel,
including:
- Button presence and placement
- Enable/disable logic based on ticket status and metadata
- Button click handler that executes MergeAgent
- Status update to 'merged' after successful merge
- Terminal output display during merge operation

These tests follow TDD approach - they SHOULD FAIL initially until the
implementation is complete.
"""

from __future__ import annotations

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
class TestMergeButtonPresence:
    """Test Merge button is present in RunTerminalWidget.

    AC: Button appears in ticket detail panel alongside existing buttons
    AC: Button follows existing GUI styling patterns and theme support
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_merge_button_exists(self):
        """Merge button should exist in the widget."""
        widget = self._make_widget()

        # Should have _merge_btn attribute
        assert hasattr(widget, "_merge_btn")
        assert widget._merge_btn is not None

    def test_merge_button_has_correct_label(self):
        """Merge button should be labeled 'Merge'."""
        widget = self._make_widget()

        assert widget._merge_btn.text() == "Merge"

    def test_merge_button_has_object_name(self):
        """Merge button should have object name for styling."""
        widget = self._make_widget()

        assert widget._merge_btn.objectName() == "mergeBtn"

    def test_merge_button_initially_disabled(self):
        """Merge button should be disabled initially."""
        widget = self._make_widget()

        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_connected_to_handler(self):
        """Merge button click should be connected to handler."""
        widget = self._make_widget()

        # Should have _on_merge_clicked method
        assert hasattr(widget, "_on_merge_clicked")
        assert callable(widget._on_merge_clicked)


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestMergeButtonEnableDisableLogic:
    """Test Merge button enable/disable logic based on ticket state.

    AC: Button is only enabled when ticket status is 'done' and ticket has branch_name metadata
    AC: Button is disabled when ticket status is not 'done' or branch_name is missing
    AC: Button is disabled while any pipeline or merge operation is running
    AC: Button respects same context requirements as Run button (project_path, db_path)
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_merge_button_disabled_when_no_context(self):
        """Merge button should be disabled when no project context set."""
        widget = self._make_widget()

        widget._update_button_states()

        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_disabled_when_status_not_done(self):
        """Merge button should be disabled when ticket status is not 'done'."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        # Create ticket with 'in progress' status and branch_name
        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.IN_PROGRESS,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)
        widget._update_button_states()

        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_disabled_when_no_branch_name_metadata(self):
        """Merge button should be disabled when ticket has no branch_name metadata."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        # Create ticket with 'done' status but no branch_name
        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata=None
        )

        widget.set_ticket(ticket)
        widget._update_button_states()

        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_disabled_when_branch_name_empty(self):
        """Merge button should be disabled when branch_name is empty string."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        # Create ticket with 'done' status but empty branch_name
        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": ""}
        )

        widget.set_ticket(ticket)
        widget._update_button_states()

        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_enabled_when_done_with_branch_name(self):
        """Merge button should be enabled when status is 'done' and branch_name exists."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5
        widget._command_running = False

        # Create ticket with 'done' status and branch_name
        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)
        widget._update_button_states()

        assert widget._merge_btn.isEnabled() is True

    def test_merge_button_disabled_while_command_running(self):
        """Merge button should be disabled while pipeline is running."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5
        widget._command_running = True

        # Create ticket with 'done' status and branch_name
        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)
        widget._set_running_state(True)

        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_disabled_during_merge_operation(self):
        """Merge button should be disabled during merge operation itself."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)
        widget._command_running = True
        widget._update_button_states()

        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_reenabled_after_run_completes(self):
        """Merge button should be re-enabled after pipeline run completes."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)

        # Start running
        widget._set_running_state(True)
        assert widget._merge_btn.isEnabled() is False

        # Complete running
        widget._set_running_state(False)
        assert widget._merge_btn.isEnabled() is True


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestMergeButtonClickHandler:
    """Test Merge button click handler execution.

    AC: Clicking Merge button instantiates MergeAgent with appropriate backend and project_path
    AC: Button click retrieves ticket metadata including branch_name
    AC: Agent runs in the project's main repository (not in a worktree)
    AC: GUI shows progress/status while merge is running
    AC: Agent output is displayed in the ticket's terminal widget
    AC: User can see git commands being executed and conflict resolution steps
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_on_merge_clicked_method_exists(self):
        """Widget should have _on_merge_clicked method."""
        widget = self._make_widget()

        assert hasattr(widget, "_on_merge_clicked")
        assert callable(widget._on_merge_clicked)

    def test_on_merge_clicked_retrieves_branch_name_from_ticket(self):
        """Merge handler should retrieve branch_name from ticket metadata."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/auth"}
        )

        widget.set_ticket(ticket)

        # Mock the merge execution
        with patch.object(widget, "_execute_merge") as mock_execute:
            widget._on_merge_clicked()

            # Should call _execute_merge with branch name
            mock_execute.assert_called_once()
            # Branch name should be passed or accessible
            assert widget._current_ticket is not None

    def test_on_merge_clicked_disables_buttons_during_execution(self):
        """Merge handler should disable buttons during merge execution."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)

        # Initially enabled
        widget._update_button_states()
        assert widget._merge_btn.isEnabled() is True

        # Mock merge to prevent actual execution
        with patch.object(widget, "_execute_merge"):
            widget._on_merge_clicked()

            # Should be disabled after click (during execution)
            # Note: This tests the _set_running_state(True) call
            assert widget._command_running is True

    def test_on_merge_clicked_updates_status_label(self):
        """Merge handler should update status label to show merge in progress."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)

        with patch.object(widget, "_execute_merge"):
            widget._on_merge_clicked()

            # Status label should indicate merge in progress
            status_text = widget._status_label.text()
            assert "merg" in status_text.lower()

    def test_execute_merge_instantiates_merge_agent(self):
        """_execute_merge should instantiate MergeAgent with backend and project_path."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/auth"}
        )

        widget.set_ticket(ticket)

        # Mock MergeAgent
        with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.run.return_value = MagicMock(text="success")
            MockAgent.return_value = mock_instance

            # Mock backend creation
            with patch.object(widget, "_create_backend") as mock_create_backend:
                mock_backend = MagicMock()
                mock_create_backend.return_value = mock_backend

                widget._execute_merge("feature/auth")

                # Should instantiate MergeAgent with backend and project_path
                MockAgent.assert_called_once()
                call_args = MockAgent.call_args
                assert mock_backend in call_args[0]  # backend is first arg
                # project_path should be in args

    def test_execute_merge_uses_main_repository_not_worktree(self):
        """_execute_merge should run agent in main repository (project_path)."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)

        with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
            mock_instance = MagicMock()
            MockAgent.return_value = mock_instance

            with patch.object(widget, "_create_backend") as mock_backend:
                widget._execute_merge("feature/test")

                # Agent should be created with project_path (not worktree)
                # project_path is passed to MergeAgent constructor
                call_args = MockAgent.call_args[0]
                # Second argument should be project_path
                assert "/some/project" in str(call_args)

    def test_execute_merge_calls_agent_run_with_branch_name(self):
        """_execute_merge should call agent.run() with branch_name parameter."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/ui"}
        )

        widget.set_ticket(ticket)

        with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.run.return_value = MagicMock(text="success")
            MockAgent.return_value = mock_instance

            with patch.object(widget, "_create_backend"):
                widget._execute_merge("feature/ui")

                # Should call agent.run with branch_name
                mock_instance.run.assert_called_once_with(branch_name="feature/ui")


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestMergeStatusUpdate:
    """Test ticket status update to 'merged' after successful merge.

    AC: After MergeAgent returns success status, GUI calls set_ticket_status() to change status to MERGED
    AC: Ticket sidebar immediately reflects updated status with merged color/icon
    AC: Ticket detail panel shows updated '[merged]' status tag
    AC: Status change persists to tickets.md file
    AC: If merge fails, ticket status remains 'done' (not changed)
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_successful_merge_calls_set_ticket_status(self, tmp_path):
        """Successful merge should call set_ticket_status with MERGED status."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = str(tmp_path)
        widget._db_path = str(tmp_path / "state.db")
        widget._ticket_number = 5

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)

        # Mock successful merge
        with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.run.return_value = MagicMock(text="Merge completed successfully")
            MockAgent.return_value = mock_instance

            with patch.object(widget, "_create_backend"):
                with patch("levelup.gui.run_terminal.set_ticket_status") as mock_set_status:
                    widget._execute_merge("feature/test")

                    # Should call set_ticket_status with MERGED
                    mock_set_status.assert_called_once()
                    call_args = mock_set_status.call_args
                    # Should pass TicketStatus.MERGED
                    assert TicketStatus.MERGED in call_args[0]

    def test_failed_merge_does_not_change_status(self, tmp_path):
        """Failed merge should NOT call set_ticket_status."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = str(tmp_path)
        widget._db_path = str(tmp_path / "state.db")
        widget._ticket_number = 5

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)

        # Mock failed merge
        with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.run.return_value = MagicMock(text="error: merge failed")
            MockAgent.return_value = mock_instance

            with patch.object(widget, "_create_backend"):
                with patch("levelup.gui.run_terminal.set_ticket_status") as mock_set_status:
                    widget._execute_merge("feature/test")

                    # Should NOT call set_ticket_status
                    mock_set_status.assert_not_called()

    def test_merge_finished_signal_emitted_on_success(self, tmp_path):
        """Successful merge should emit merge_finished signal."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = str(tmp_path)
        widget._db_path = str(tmp_path / "state.db")

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)

        # Mock signal
        signal_emitted = False

        def on_merge_finished():
            nonlocal signal_emitted
            signal_emitted = True

        widget.merge_finished.connect(on_merge_finished)

        with patch("levelup.gui.run_terminal.MergeAgent") as MockAgent:
            mock_instance = MagicMock()
            mock_instance.run.return_value = MagicMock(text="success")
            MockAgent.return_value = mock_instance

            with patch.object(widget, "_create_backend"):
                with patch("levelup.gui.run_terminal.set_ticket_status"):
                    widget._execute_merge("feature/test")

                    assert signal_emitted is True

    def test_merge_finished_signal_exists(self):
        """Widget should have merge_finished signal."""
        widget = self._make_widget()

        assert hasattr(widget, "merge_finished")


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestMergeButtonIntegrationWithExistingState:
    """Test Merge button integration with existing GUI state management.

    AC: Merge button respects same context requirements as Run button
    AC: During merge, other buttons are disabled appropriately (Run, Delete)
    AC: After merge completes (success or failure), button states are restored
    AC: Merge operation does not interfere with existing runs or worktrees
    AC: Terminal output is captured and displayed like pipeline runs
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_merge_button_requires_project_path(self):
        """Merge button should be disabled without project_path."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = None
        widget._db_path = "/some/db"

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)
        widget._update_button_states()

        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_requires_db_path(self):
        """Merge button should be disabled without db_path."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = None

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)
        widget._update_button_states()

        assert widget._merge_btn.isEnabled() is False

    def test_run_button_disabled_during_merge(self):
        """Run button should be disabled during merge operation."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)

        # Start merge (sets _command_running = True)
        widget._set_running_state(True)

        assert widget._run_btn.isEnabled() is False
        assert widget._merge_btn.isEnabled() is False

    def test_buttons_reenabled_after_merge_completes(self):
        """Buttons should be re-enabled after merge completes."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)

        # Simulate merge completion
        widget._set_running_state(True)
        widget._set_running_state(False)

        # After merge, status would be MERGED, so merge button disabled
        # But other buttons should be in correct state
        assert widget._run_btn.isEnabled() is True or widget._resume_btn.isEnabled() is True

    def test_merge_sets_status_label(self):
        """Merge operation should update status label."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)

        with patch.object(widget, "_execute_merge"):
            widget._on_merge_clicked()

            status_text = widget._status_label.text()
            assert status_text is not None
            assert len(status_text) > 0


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestMergeButtonEdgeCases:
    """Test edge cases for Merge button functionality."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_merge_button_disabled_for_merged_status(self):
        """Merge button should be disabled if ticket is already merged."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.MERGED,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)
        widget._update_button_states()

        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_disabled_for_pending_status(self):
        """Merge button should be disabled for pending tickets."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.PENDING,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)
        widget._update_button_states()

        assert widget._merge_btn.isEnabled() is False

    def test_handles_ticket_with_metadata_but_no_branch_name_key(self):
        """Should handle ticket with metadata dict but no branch_name key."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"model": "sonnet", "effort": "high"}  # no branch_name
        )

        widget.set_ticket(ticket)
        widget._update_button_states()

        assert widget._merge_btn.isEnabled() is False

    def test_set_ticket_method_stores_ticket_reference(self):
        """set_ticket should store ticket reference for later use."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()

        ticket = Ticket(
            number=5,
            title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"}
        )

        widget.set_ticket(ticket)

        # Should store ticket reference
        assert hasattr(widget, "_current_ticket")
        assert widget._current_ticket == ticket
