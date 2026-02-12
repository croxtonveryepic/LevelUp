"""Tests for delayed terminal initialization in RunTerminalWidget.

This test module verifies that the terminal shell is NOT initialized automatically
when the widget is shown (i.e., when a ticket is selected), but ONLY when the
Run or Resume buttons are clicked.

This prevents unnecessary PTY processes from being spawned for tickets that are
just being viewed, not executed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.regression

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
class TestDelayedTerminalInitialization:
    """Test delayed terminal initialization behavior."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Setup QApplication for PyQt6 tests."""
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with the embedded terminal's PtyBackend mocked."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    # -------------------------------------------------------------------------
    # Test 1: Selecting a ticket (showEvent) should NOT start shell
    # -------------------------------------------------------------------------

    def test_show_event_does_not_start_shell(self):
        """Verify that showEvent does NOT call _ensure_shell."""
        widget = self._make_widget()

        with patch.object(widget, "_ensure_shell") as mock_ensure:
            # Trigger showEvent by simulating widget visibility
            from PyQt6.QtGui import QShowEvent
            event = QShowEvent()
            widget.showEvent(event)

            # CRITICAL: _ensure_shell should NOT be called on showEvent
            mock_ensure.assert_not_called()

    def test_show_event_does_not_initialize_pty(self):
        """Verify that showing the widget does NOT start the PTY backend."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start:
            # Trigger showEvent
            from PyQt6.QtGui import QShowEvent
            event = QShowEvent()
            widget.showEvent(event)

            # The PTY should NOT be started
            mock_start.assert_not_called()

    def test_shell_started_flag_false_after_show(self):
        """Verify that _shell_started remains False after showEvent."""
        widget = self._make_widget()

        # Initially false
        assert widget._shell_started is False

        # Show the widget
        from PyQt6.QtGui import QShowEvent
        event = QShowEvent()
        widget.showEvent(event)

        # Should still be false
        assert widget._shell_started is False

    def test_ticket_selection_does_not_spawn_process(self):
        """Integration test: selecting a ticket via TicketDetailWidget does not spawn shell."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.core.tickets import Ticket, TicketStatus

        # Ensure QApplication exists
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])

        # Create ticket detail widget
        detail = TicketDetailWidget()
        detail.set_project_context("/test/project", "/test/db.db")

        # Create a ticket
        ticket = Ticket(number=1, title="Test ticket", status=TicketStatus.PENDING)

        # Mock the terminal's start_shell to track calls
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            detail.set_ticket(ticket)
            terminal = detail._terminals[1]

            with patch.object(terminal._terminal, "start_shell") as mock_start:
                # Force the terminal widget to be shown (trigger showEvent)
                terminal.show()

                # Shell should NOT have been started
                mock_start.assert_not_called()
                assert terminal._shell_started is False

    # -------------------------------------------------------------------------
    # Test 2: Clicking Run button SHOULD start shell
    # -------------------------------------------------------------------------

    def test_start_run_calls_ensure_shell(self):
        """Verify that start_run calls _ensure_shell."""
        widget = self._make_widget()

        with patch.object(widget, "_ensure_shell") as mock_ensure, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

            # _ensure_shell MUST be called when starting a run
            mock_ensure.assert_called_once()

    def test_start_run_initializes_shell(self):
        """Verify that start_run actually starts the shell."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

            # Shell should be started
            mock_start.assert_called_once()

    def test_start_run_sets_shell_started_flag(self):
        """Verify that start_run sets _shell_started to True."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            assert widget._shell_started is False
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert widget._shell_started is True

    def test_start_run_only_initializes_once(self):
        """Verify that calling start_run multiple times only initializes shell once."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            # First run starts the shell
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert mock_start.call_count == 1

            # Mark as finished
            widget._command_running = False

            # Second run should NOT start shell again (already started)
            widget.start_run(ticket_number=2, project_path="/p", db_path="/d")
            # Still only called once
            assert mock_start.call_count == 1

    def test_run_button_click_starts_shell(self):
        """Integration test: clicking Run button starts the shell."""
        widget = self._make_widget()
        widget.set_context("/test/project", "/test/db.db")
        widget._ticket_number = 1

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            # Simulate clicking the Run button
            widget._on_run_clicked()

            # Shell should be started
            mock_start.assert_called_once()
            assert widget._shell_started is True

    # -------------------------------------------------------------------------
    # Test 3: Clicking Resume button SHOULD start shell
    # -------------------------------------------------------------------------

    def test_resume_calls_ensure_shell(self):
        """Verify that _on_resume_clicked calls _ensure_shell."""
        widget = self._make_widget()
        widget._last_run_id = "run-abc"
        widget._project_path = "/p"
        widget._db_path = "/d"

        with patch.object(widget, "_ensure_shell") as mock_ensure, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget._on_resume_clicked()

            # _ensure_shell MUST be called when resuming
            mock_ensure.assert_called_once()

    def test_resume_initializes_shell(self):
        """Verify that _on_resume_clicked actually starts the shell."""
        widget = self._make_widget()
        widget._last_run_id = "run-abc"
        widget._project_path = "/p"
        widget._db_path = "/d"

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget._on_resume_clicked()

            # Shell should be started
            mock_start.assert_called_once()

    def test_resume_sets_shell_started_flag(self):
        """Verify that _on_resume_clicked sets _shell_started to True."""
        widget = self._make_widget()
        widget._last_run_id = "run-abc"
        widget._project_path = "/p"
        widget._db_path = "/d"

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            assert widget._shell_started is False
            widget._on_resume_clicked()
            assert widget._shell_started is True

    def test_resume_only_initializes_once(self):
        """Verify that resuming multiple times only initializes shell once."""
        widget = self._make_widget()
        widget._last_run_id = "run-abc"
        widget._project_path = "/p"
        widget._db_path = "/d"

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            # First resume starts the shell
            widget._on_resume_clicked()
            assert mock_start.call_count == 1

            # Mark as finished
            widget._command_running = False

            # Second resume should NOT start shell again
            widget._on_resume_clicked()
            # Still only called once
            assert mock_start.call_count == 1

    def test_resume_button_click_starts_shell(self):
        """Integration test: clicking Resume button starts the shell."""
        widget = self._make_widget()
        widget._last_run_id = "run-abc"
        widget._project_path = "/p"
        widget._db_path = "/d"

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            # Simulate clicking the Resume button
            widget._on_resume_clicked()

            # Shell should be started
            mock_start.assert_called_once()
            assert widget._shell_started is True

    def test_resume_after_show_event_initializes_shell(self):
        """Verify that if widget is shown but shell not started, resume will start it."""
        widget = self._make_widget()
        widget._last_run_id = "run-abc"
        widget._project_path = "/p"
        widget._db_path = "/d"

        # Show the widget (should not start shell)
        from PyQt6.QtGui import QShowEvent
        event = QShowEvent()
        widget.showEvent(event)
        assert widget._shell_started is False

        # Now resume (should start shell)
        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget._on_resume_clicked()

            # Shell should be started now
            mock_start.assert_called_once()
            assert widget._shell_started is True

    # -------------------------------------------------------------------------
    # Test 4: Existing terminal functionality still works
    # -------------------------------------------------------------------------

    def test_send_command_works_after_delayed_init(self):
        """Verify send_command works after shell is initialized on run."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command") as mock_send, \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

            # send_command should have been called with the run command
            mock_send.assert_called_once()
            cmd_arg = mock_send.call_args[0][0]
            assert "-m levelup run" in cmd_arg

    def test_send_interrupt_works(self):
        """Verify send_interrupt continues to work."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

        # Now test interrupt
        with patch.object(widget._terminal, "send_interrupt") as mock_interrupt:
            widget._on_terminate_clicked()
            mock_interrupt.assert_called_once()

    def test_send_clear_works(self):
        """Verify send_clear continues to work."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "send_clear") as mock_clear:
            widget._on_clear()
            mock_clear.assert_called_once()

    def test_close_shell_works(self):
        """Verify close_shell continues to work."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert widget._shell_started is True

        # Now close the shell
        with patch.object(widget._terminal, "close_shell") as mock_close:
            widget._terminal.close_shell()
            mock_close.assert_called_once()

    def test_terminal_reuse_across_runs(self):
        """Verify terminal can be reused across multiple runs for same ticket."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command") as mock_send, \
             patch.object(widget._terminal, "setFocus"):

            # First run
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert mock_start.call_count == 1
            assert mock_send.call_count == 1

            # Finish first run
            widget._command_running = False

            # Second run (same ticket)
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

            # Shell should NOT be started again (already started)
            assert mock_start.call_count == 1
            # But command should be sent again
            assert mock_send.call_count == 2

    def test_shell_state_tracking_accurate(self):
        """Verify _shell_started flag accurately tracks shell state."""
        widget = self._make_widget()

        # Initially not started
        assert widget._shell_started is False

        # Show event should not change it
        from PyQt6.QtGui import QShowEvent
        event = QShowEvent()
        widget.showEvent(event)
        assert widget._shell_started is False

        # Start run should set it
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert widget._shell_started is True

        # Shell exit should reset it
        widget._on_shell_exited(0)
        assert widget._shell_started is False

    def test_terminal_cleanup_on_deletion(self):
        """Verify terminal cleanup still closes shell properly on widget deletion."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.core.tickets import Ticket, TicketStatus

        # Create detail widget and add terminals
        detail = TicketDetailWidget()
        detail.set_project_context("/test/project", "/test/db.db")

        ticket = Ticket(number=1, title="Test", status=TicketStatus.PENDING)

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            detail.set_ticket(ticket)
            terminal = detail._terminals[1]

            # Start the shell
            with patch.object(terminal._terminal, "start_shell"), \
                 patch.object(terminal._terminal, "send_command"), \
                 patch.object(terminal._terminal, "setFocus"):

                terminal.start_run(ticket_number=1, project_path="/p", db_path="/d")
                assert terminal._shell_started is True

            # Now clean up
            with patch.object(terminal._terminal, "close_shell") as mock_close:
                detail._remove_terminal(1)
                mock_close.assert_called_once()

    # -------------------------------------------------------------------------
    # Test 5: Edge cases and error conditions
    # -------------------------------------------------------------------------

    def test_ensure_shell_idempotent(self):
        """Verify _ensure_shell can be called multiple times safely."""
        widget = self._make_widget()
        widget._project_path = "/p"

        with patch.object(widget._terminal, "start_shell") as mock_start:
            # Call _ensure_shell multiple times
            widget._ensure_shell()
            widget._ensure_shell()
            widget._ensure_shell()

            # Should only start shell once
            assert mock_start.call_count == 1
            assert widget._shell_started is True

    def test_start_run_without_project_path(self):
        """Verify start_run handles missing project path gracefully."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            # start_run with no project_path set on widget initially
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

            # Should still work (project_path passed as parameter)
            mock_start.assert_called_once()

    def test_resume_without_shell_started(self):
        """Verify resume works even if shell was never started before."""
        widget = self._make_widget()
        widget._last_run_id = "run-abc"
        widget._project_path = "/p"
        widget._db_path = "/d"

        # Verify shell not started
        assert widget._shell_started is False

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget._on_resume_clicked()

            # Should start the shell
            mock_start.assert_called_once()
            assert widget._shell_started is True

    def test_multiple_show_events_dont_start_shell(self):
        """Verify multiple show events don't trigger shell initialization."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start:
            # Trigger multiple show events
            from PyQt6.QtGui import QShowEvent
            for _ in range(5):
                event = QShowEvent()
                widget.showEvent(event)

            # Shell should never be started
            mock_start.assert_not_called()
            assert widget._shell_started is False

    def test_shell_started_before_show_event(self):
        """Verify that if shell is already started, showEvent doesn't break anything."""
        widget = self._make_widget()

        # Start shell manually
        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert mock_start.call_count == 1

            # Now trigger show event
            from PyQt6.QtGui import QShowEvent
            event = QShowEvent()
            widget.showEvent(event)

            # Shell should not be started again
            assert mock_start.call_count == 1
            assert widget._shell_started is True

    def test_cwd_passed_to_shell_on_init(self):
        """Verify that project path is passed as cwd when starting shell."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            widget.start_run(ticket_number=1, project_path="/my/project", db_path="/d")

            # Verify start_shell was called with cwd
            mock_start.assert_called_once()
            call_kwargs = mock_start.call_args[1]
            assert call_kwargs.get("cwd") == "/my/project"

    def test_ensure_shell_with_none_project_path(self):
        """Verify _ensure_shell handles None project_path gracefully."""
        widget = self._make_widget()
        widget._project_path = None

        with patch.object(widget._terminal, "start_shell") as mock_start:
            widget._ensure_shell()

            # Should still be called (with cwd=None)
            mock_start.assert_called_once()
            call_kwargs = mock_start.call_args[1]
            assert call_kwargs.get("cwd") is None
