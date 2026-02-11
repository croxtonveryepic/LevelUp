"""Unit tests for Merge button in RunTerminalWidget (GUI).

Tests cover the Merge button functionality in the ticket detail panel,
including:
- Button presence and placement
- Enable/disable logic based on ticket status and metadata
- Button click handler that runs ``levelup merge`` in the terminal
- Merge poll timer for detecting completion
- Terminal command format via build_merge_command
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
    """Test Merge button is present in RunTerminalWidget."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_merge_button_exists(self):
        widget = self._make_widget()
        assert hasattr(widget, "_merge_btn")
        assert widget._merge_btn is not None

    def test_merge_button_has_correct_label(self):
        widget = self._make_widget()
        assert widget._merge_btn.text() == "Merge"

    def test_merge_button_has_object_name(self):
        widget = self._make_widget()
        assert widget._merge_btn.objectName() == "mergeBtn"

    def test_merge_button_initially_disabled(self):
        widget = self._make_widget()
        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_connected_to_handler(self):
        widget = self._make_widget()
        assert hasattr(widget, "_on_merge_clicked")
        assert callable(widget._on_merge_clicked)


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestMergeButtonEnableDisableLogic:
    """Test Merge button enable/disable logic based on ticket state."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_merge_button_disabled_when_no_context(self):
        widget = self._make_widget()
        widget._update_button_states()
        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_disabled_when_status_not_done(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.IN_PROGRESS,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)
        widget._update_button_states()
        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_disabled_when_no_branch_name_metadata(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(number=5, title="Test task", status=TicketStatus.DONE, metadata=None)
        widget.set_ticket(ticket)
        widget._update_button_states()
        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_disabled_when_branch_name_empty(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(number=5, title="Test task", status=TicketStatus.DONE, metadata={"branch_name": ""})
        widget.set_ticket(ticket)
        widget._update_button_states()
        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_enabled_when_done_with_branch_name(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5
        widget._command_running = False

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)
        widget._update_button_states()
        assert widget._merge_btn.isEnabled() is True

    def test_merge_button_disabled_while_command_running(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)
        widget._set_running_state(True)
        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_disabled_during_merge_operation(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)
        widget._command_running = True
        widget._update_button_states()
        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_reenabled_after_run_completes(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)

        widget._set_running_state(True)
        assert widget._merge_btn.isEnabled() is False

        widget._set_running_state(False)
        assert widget._merge_btn.isEnabled() is True


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestBuildMergeCommand:
    """Test the build_merge_command helper function."""

    def test_build_merge_command_format(self):
        from levelup.gui.run_terminal import build_merge_command

        cmd = build_merge_command(5, "/some/project")
        assert "-m levelup merge" in cmd
        assert "--ticket 5" in cmd
        assert '--path "/some/project"' in cmd

    def test_build_merge_command_uses_python_executable(self):
        import sys
        from levelup.gui.run_terminal import build_merge_command

        cmd = build_merge_command(1, "/proj")
        expected_python = sys.executable.replace("\\", "/")
        assert expected_python in cmd


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestMergeButtonClickHandler:
    """Test Merge button click handler sends command to terminal."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_on_merge_clicked_method_exists(self):
        widget = self._make_widget()
        assert hasattr(widget, "_on_merge_clicked")
        assert callable(widget._on_merge_clicked)

    def test_on_merge_clicked_sends_command_to_terminal(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/auth"},
        )
        widget.set_ticket(ticket)

        with patch.object(widget, "_ensure_shell"):
            with patch.object(widget._terminal, "send_command") as mock_send:
                with patch.object(widget._terminal, "setFocus"):
                    widget._on_merge_clicked()

                    mock_send.assert_called_once()
                    cmd = mock_send.call_args[0][0]
                    assert "--ticket 5" in cmd
                    assert "levelup merge" in cmd

    def test_on_merge_clicked_disables_buttons_during_execution(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)
        widget._update_button_states()
        assert widget._merge_btn.isEnabled() is True

        with patch.object(widget, "_ensure_shell"):
            with patch.object(widget._terminal, "send_command"):
                with patch.object(widget._terminal, "setFocus"):
                    widget._on_merge_clicked()
                    assert widget._command_running is True

    def test_on_merge_clicked_updates_status_label(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)

        with patch.object(widget, "_ensure_shell"):
            with patch.object(widget._terminal, "send_command"):
                with patch.object(widget._terminal, "setFocus"):
                    widget._on_merge_clicked()
                    status_text = widget._status_label.text()
                    assert "merg" in status_text.lower()

    def test_on_merge_clicked_starts_merge_poll_timer(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)

        with patch.object(widget, "_ensure_shell"):
            with patch.object(widget._terminal, "send_command"):
                with patch.object(widget._terminal, "setFocus"):
                    widget._on_merge_clicked()
                    assert widget._merge_poll_timer.isActive()
                    widget._merge_poll_timer.stop()  # cleanup

    def test_on_merge_clicked_noop_when_no_ticket(self):
        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._current_ticket = None

        with patch.object(widget._terminal, "send_command") as mock_send:
            widget._on_merge_clicked()
            mock_send.assert_not_called()

    def test_on_merge_clicked_noop_when_running(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._command_running = True

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)

        with patch.object(widget._terminal, "send_command") as mock_send:
            widget._on_merge_clicked()
            mock_send.assert_not_called()


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestMergePollCompletion:
    """Test merge completion polling."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_poll_detects_merged_status(self):
        """Polling should detect when ticket transitions to MERGED."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._command_running = True

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)

        # Start timer
        widget._merge_poll_count = 0
        widget._merge_poll_timer.start(2000)

        # Mock read_tickets to return MERGED status
        merged_ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.MERGED,
            metadata={"branch_name": "feature/test"},
        )

        signal_emitted = False
        def on_merge_finished():
            nonlocal signal_emitted
            signal_emitted = True
        widget.merge_finished.connect(on_merge_finished)

        with patch("levelup.core.tickets.read_tickets", return_value=[merged_ticket]):
            widget._poll_merge_completion()

        assert not widget._merge_poll_timer.isActive()
        assert widget._command_running is False
        assert signal_emitted is True

    def test_poll_timeout_restores_state(self):
        """Polling should timeout and restore state after max polls."""
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._command_running = True

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)

        widget._merge_poll_count = 30  # At timeout threshold
        widget._merge_poll_timer.start(2000)

        widget._poll_merge_completion()

        assert not widget._merge_poll_timer.isActive()
        assert widget._command_running is False

    def test_merge_finished_signal_exists(self):
        widget = self._make_widget()
        assert hasattr(widget, "merge_finished")

    def test_merge_poll_timer_exists(self):
        widget = self._make_widget()
        assert hasattr(widget, "_merge_poll_timer")


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestMergeButtonIntegrationWithExistingState:
    """Test Merge button integration with existing GUI state management."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_merge_button_requires_project_path(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = None
        widget._db_path = "/some/db"

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)
        widget._update_button_states()
        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_requires_db_path(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = None

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)
        widget._update_button_states()
        assert widget._merge_btn.isEnabled() is False

    def test_run_button_disabled_during_merge(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)
        widget._set_running_state(True)

        assert widget._run_btn.isEnabled() is False
        assert widget._merge_btn.isEnabled() is False

    def test_buttons_reenabled_after_merge_completes(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"
        widget._ticket_number = 5

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)

        widget._set_running_state(True)
        widget._set_running_state(False)

        assert widget._run_btn.isEnabled() is True or widget._resume_btn.isEnabled() is True

    def test_merge_sets_status_label(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)

        with patch.object(widget, "_ensure_shell"):
            with patch.object(widget._terminal, "send_command"):
                with patch.object(widget._terminal, "setFocus"):
                    widget._on_merge_clicked()
                    status_text = widget._status_label.text()
                    assert status_text is not None
                    assert len(status_text) > 0

    def test_shell_exit_stops_merge_poll_timer(self):
        """Shell exiting should stop the merge poll timer."""
        widget = self._make_widget()
        widget._merge_poll_timer.start(2000)
        assert widget._merge_poll_timer.isActive()

        widget._on_shell_exited(0)
        assert not widget._merge_poll_timer.isActive()


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
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_merge_button_disabled_for_merged_status(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.MERGED,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)
        widget._update_button_states()
        assert widget._merge_btn.isEnabled() is False

    def test_merge_button_disabled_for_pending_status(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.PENDING,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)
        widget._update_button_states()
        assert widget._merge_btn.isEnabled() is False

    def test_handles_ticket_with_metadata_but_no_branch_name_key(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._db_path = "/some/db"

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"model": "sonnet", "effort": "high"},
        )
        widget.set_ticket(ticket)
        widget._update_button_states()
        assert widget._merge_btn.isEnabled() is False

    def test_set_ticket_method_stores_ticket_reference(self):
        from levelup.core.tickets import Ticket, TicketStatus

        widget = self._make_widget()

        ticket = Ticket(
            number=5, title="Test task",
            status=TicketStatus.DONE,
            metadata={"branch_name": "feature/test"},
        )
        widget.set_ticket(ticket)

        assert hasattr(widget, "_current_ticket")
        assert widget._current_ticket == ticket
