"""Tests for the RunTerminalWidget."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from levelup.gui.run_terminal import build_run_command, build_resume_command

pytestmark = pytest.mark.regression

def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


class TestBuildRunCommand:
    def test_contains_module_invocation(self):
        cmd = build_run_command(3, "/some/project", "/tmp/state.db")
        assert "-m levelup run" in cmd

    def test_does_not_contain_gui_flag(self):
        cmd = build_run_command(1, "/p", "/d")
        assert "--gui" not in cmd

    def test_contains_ticket_number(self):
        cmd = build_run_command(42, "/p", "/d")
        assert "--ticket 42" in cmd

    def test_contains_path(self):
        cmd = build_run_command(1, "/some/project", "/d")
        assert "/some/project" in cmd

    def test_contains_db_path(self):
        cmd = build_run_command(1, "/p", "/tmp/state.db")
        assert "/tmp/state.db" in cmd

    def test_uses_sys_executable(self):
        cmd = build_run_command(1, "/p", "/d")
        exe = sys.executable.replace("\\", "/")
        assert exe in cmd


class TestBuildRunCommandAdaptive:
    def test_model_flag(self):
        cmd = build_run_command(1, "/p", "/d", model="opus")
        assert "--model opus" in cmd

    def test_effort_flag(self):
        cmd = build_run_command(1, "/p", "/d", effort="medium")
        assert "--effort medium" in cmd

    def test_skip_planning_flag(self):
        cmd = build_run_command(1, "/p", "/d", skip_planning=True)
        assert "--skip-planning" in cmd

    def test_no_flags_by_default(self):
        cmd = build_run_command(1, "/p", "/d")
        assert "--model" not in cmd
        assert "--effort" not in cmd
        assert "--skip-planning" not in cmd

    def test_all_adaptive_flags(self):
        cmd = build_run_command(1, "/p", "/d", model="sonnet", effort="high", skip_planning=True)
        assert "--model sonnet" in cmd
        assert "--effort high" in cmd
        assert "--skip-planning" in cmd


class TestBuildResumeCommand:
    def test_contains_module_invocation(self):
        cmd = build_resume_command("abc123", "/some/project", "/tmp/state.db")
        assert "-m levelup resume" in cmd

    def test_contains_run_id(self):
        cmd = build_resume_command("abc123", "/p", "/d")
        assert "abc123" in cmd

    def test_does_not_contain_gui_flag(self):
        cmd = build_resume_command("abc123", "/p", "/d")
        assert "--gui" not in cmd

    def test_contains_path(self):
        cmd = build_resume_command("abc123", "/some/project", "/d")
        assert "/some/project" in cmd

    def test_contains_db_path(self):
        cmd = build_resume_command("abc123", "/p", "/tmp/state.db")
        assert "/tmp/state.db" in cmd

    def test_uses_sys_executable(self):
        cmd = build_resume_command("abc123", "/p", "/d")
        exe = sys.executable.replace("\\", "/")
        assert exe in cmd


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestRunTerminalWidget:
    def test_widget_construction(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        assert widget.is_running is False
        assert widget.process_pid is None

    def test_set_running_state(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()

        # Initially: run disabled (no ticket), terminate/pause disabled
        assert widget._terminate_btn.isEnabled() is False
        assert widget._pause_btn.isEnabled() is False

        # Simulate running state
        widget._set_running_state(True)
        assert widget._run_btn.isEnabled() is False
        assert widget._terminate_btn.isEnabled() is True
        assert widget._pause_btn.isEnabled() is True
        assert "Running" in widget._status_label.text()

        # Simulate stopped state
        widget._set_running_state(False)
        assert widget._run_btn.isEnabled() is True
        assert widget._terminate_btn.isEnabled() is False
        assert widget._pause_btn.isEnabled() is False
        assert "Ready" in widget._status_label.text()

    def test_resume_button_disabled_without_run_id(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        assert widget._resume_btn.isEnabled() is False

    def test_forget_button_disabled_without_run_id(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        assert widget._forget_btn.isEnabled() is False

    def test_enable_run(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        widget.enable_run(True)
        assert widget._run_btn.isEnabled() is True

        widget.enable_run(False)
        assert widget._run_btn.isEnabled() is False

    def test_is_running_reflects_command_state(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        assert widget.is_running is False

        widget._command_running = True
        assert widget.is_running is True

    def test_process_pid_when_running(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        assert widget.process_pid is None

        widget._command_running = True
        assert widget.process_pid == 0

    def test_set_context(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        widget.set_context("/my/project", "/my/db.db")
        assert widget._project_path == "/my/project"
        assert widget._db_path == "/my/db.db"

    def test_set_state_manager(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        mock_sm = object()
        widget.set_state_manager(mock_sm)
        assert widget._state_manager is mock_sm

    def test_set_ticket_settings(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        widget.set_ticket_settings(model="opus", effort="high", skip_planning=True)
        assert widget._ticket_model == "opus"
        assert widget._ticket_effort == "high"
        assert widget._ticket_skip_planning is True

    def test_set_ticket_settings_defaults(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        widget.set_ticket_settings()
        assert widget._ticket_model is None
        assert widget._ticket_effort is None
        assert widget._ticket_skip_planning is False

    def test_notify_run_finished(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        received_codes: list[int] = []
        widget.run_finished.connect(lambda code: received_codes.append(code))

        # Should be no-op when not running
        widget.notify_run_finished(0)
        assert len(received_codes) == 0

        # Should emit when running
        widget._command_running = True
        widget.notify_run_finished(0)
        assert received_codes == [0]
        assert widget.is_running is False

    def test_ticket_number_attribute_exists(self):
        """ticket_detail.py directly sets _ticket_number on the widget."""
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        assert hasattr(widget, "_ticket_number")
        widget._ticket_number = 42
        assert widget._ticket_number == 42

    def test_last_run_id_initially_none(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        assert widget.last_run_id is None

    def test_has_run_paused_signal(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        # Verify the signal exists and can be connected
        received: list[bool] = []
        widget.run_paused.connect(lambda: received.append(True))

    def test_poll_detects_completion(self):
        """When DB status becomes terminal, widget transitions to finished."""
        from unittest.mock import MagicMock

        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget
        from levelup.state.manager import StateManager

        widget = RunTerminalWidget()

        # Set up mock state manager (spec so isinstance check passes)
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "completed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Simulate a running state with known run_id
        widget._command_running = True
        widget._project_path = "/some/project"
        widget._last_run_id = "test-run-123"

        # Track emitted signals
        finished_codes: list[int] = []
        widget.run_finished.connect(lambda code: finished_codes.append(code))

        # Poll should detect completion
        widget._poll_for_run_id()

        assert widget.is_running is False
        assert finished_codes == [0]
        assert "completed" in widget._status_label.text()

    def test_poll_detects_failure(self):
        """When DB status becomes failed, widget transitions with exit code 1."""
        from unittest.mock import MagicMock

        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget
        from levelup.state.manager import StateManager

        widget = RunTerminalWidget()

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._command_running = True
        widget._project_path = "/some/project"
        widget._last_run_id = "test-run-456"

        finished_codes: list[int] = []
        widget.run_finished.connect(lambda code: finished_codes.append(code))

        widget._poll_for_run_id()

        assert widget.is_running is False
        assert finished_codes == [1]

    def test_poll_detects_pause(self):
        """When DB status becomes paused, widget emits run_paused."""
        from unittest.mock import MagicMock

        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget
        from levelup.state.manager import StateManager

        widget = RunTerminalWidget()

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "paused"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._command_running = True
        widget._project_path = "/some/project"
        widget._last_run_id = "test-run-789"

        paused: list[bool] = []
        widget.run_paused.connect(lambda: paused.append(True))

        widget._poll_for_run_id()

        assert widget.is_running is False
        assert paused == [True]


# ---------------------------------------------------------------------------
# RunTerminalWidget integration tests (mocked terminal)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestRunTerminalIntegration:
    """Integration tests for RunTerminalWidget with mocked TerminalEmulatorWidget."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication

        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with the embedded terminal's PtyBackend mocked."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget

            widget = RunTerminalWidget()
        return widget

    # 2a: start_run sends command and sets focus
    def test_start_run_sends_command(self):
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command") as mock_send, \
             patch.object(widget._terminal, "setFocus") as mock_focus:

            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

            mock_send.assert_called_once()
            cmd_arg = mock_send.call_args[0][0]
            assert "-m levelup run" in cmd_arg
            assert "--ticket 1" in cmd_arg
            assert "/p" in cmd_arg
            assert "/d" in cmd_arg

            mock_focus.assert_called_once()

        assert widget._command_running is True
        assert widget._run_id_poll_timer.isActive() is True

        # Cleanup
        widget._run_id_poll_timer.stop()

    # 2b: start_run is no-op when already running
    def test_start_run_noop_when_running(self):
        widget = self._make_widget()
        widget._command_running = True

        with patch.object(widget._terminal, "send_command") as mock_send:
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            mock_send.assert_not_called()

    # 2c: _on_resume_clicked sends resume command and starts poll timer
    def test_on_resume_clicked_sends_command(self):
        widget = self._make_widget()
        widget._last_run_id = "run-abc"
        widget._project_path = "/p"
        widget._db_path = "/d"

        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command") as mock_send, \
             patch.object(widget._terminal, "setFocus") as mock_focus:

            widget._on_resume_clicked()

            mock_send.assert_called_once()
            cmd_arg = mock_send.call_args[0][0]
            assert "-m levelup resume" in cmd_arg
            assert "run-abc" in cmd_arg

            mock_focus.assert_called_once()

        assert widget._command_running is True
        assert widget._run_id_poll_timer.isActive() is True

        # Cleanup
        widget._run_id_poll_timer.stop()

    def test_on_resume_clicked_noop_when_running(self):
        widget = self._make_widget()
        widget._last_run_id = "run-abc"
        widget._project_path = "/p"
        widget._db_path = "/d"
        widget._command_running = True

        with patch.object(widget._terminal, "send_command") as mock_send:
            widget._on_resume_clicked()
            mock_send.assert_not_called()

    def test_on_resume_clicked_noop_without_run_id(self):
        widget = self._make_widget()
        widget._project_path = "/p"
        widget._db_path = "/d"
        # _last_run_id is None

        with patch.object(widget._terminal, "send_command") as mock_send:
            widget._on_resume_clicked()
            mock_send.assert_not_called()

    # 2d: _on_shell_exited stops polling and emits finished
    def test_on_shell_exited_stops_polling_and_emits(self):
        widget = self._make_widget()
        widget._command_running = True
        widget._shell_started = True
        widget._run_id_poll_timer.start(1000)

        finished_codes: list[int] = []
        widget.run_finished.connect(lambda code: finished_codes.append(code))

        widget._on_shell_exited(1)

        assert widget.is_running is False
        assert widget._run_id_poll_timer.isActive() is False
        assert finished_codes == [1]
        assert widget._shell_started is False

    def test_on_shell_exited_zero_code(self):
        widget = self._make_widget()
        widget._command_running = True
        widget._shell_started = True

        finished_codes: list[int] = []
        widget.run_finished.connect(lambda code: finished_codes.append(code))

        widget._on_shell_exited(0)

        assert widget.is_running is False
        assert finished_codes == [0]

    def test_on_shell_exited_noop_when_not_running(self):
        widget = self._make_widget()
        widget._shell_started = True
        # _command_running is False

        finished_codes: list[int] = []
        widget.run_finished.connect(lambda code: finished_codes.append(code))

        widget._on_shell_exited(0)

        # Should not emit run_finished since command wasn't running
        assert finished_codes == []
        assert widget._shell_started is False

    # 2e: _poll_for_run_id finds active run and keeps polling
    def test_poll_finds_active_run(self):
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._command_running = True

        mock_sm = MagicMock(spec=StateManager)
        mock_run = MagicMock()
        mock_run.run_id = "discovered-run"
        mock_run.project_path = "/some/project"
        mock_run.status = "running"
        mock_sm.list_runs.return_value = [mock_run]
        widget.set_state_manager(mock_sm)

        # Start the poll timer so we can verify it stays active
        widget._run_id_poll_timer.start(1000)

        widget._poll_for_run_id()

        assert widget._last_run_id == "discovered-run"
        assert widget._run_id_poll_timer.isActive() is True

        # Cleanup
        widget._run_id_poll_timer.stop()

    # 2g: _poll_for_run_id uses ticket_number when available
    def test_poll_finds_run_by_ticket_number(self):
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._ticket_number = 7
        widget._command_running = True

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.run_id = "ticket-run-abc"
        mock_record.status = "running"
        mock_sm.get_run_for_ticket.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._run_id_poll_timer.start(1000)
        widget._poll_for_run_id()

        # Should have called get_run_for_ticket instead of list_runs
        mock_sm.get_run_for_ticket.assert_called_once_with("/some/project", 7)
        mock_sm.list_runs.assert_not_called()
        assert widget._last_run_id == "ticket-run-abc"
        assert widget._run_id_poll_timer.isActive() is True

        widget._run_id_poll_timer.stop()

    def test_poll_ticket_detects_completion(self):
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._project_path = "/some/project"
        widget._ticket_number = 5
        widget._command_running = True

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.run_id = "ticket-run-done"
        mock_record.status = "completed"
        mock_sm.get_run_for_ticket.return_value = mock_record
        widget.set_state_manager(mock_sm)

        finished_codes: list[int] = []
        widget.run_finished.connect(lambda code: finished_codes.append(code))

        widget._run_id_poll_timer.start(1000)
        widget._poll_for_run_id()

        assert widget._last_run_id == "ticket-run-done"
        assert widget.is_running is False
        assert finished_codes == [0]
        assert widget._run_id_poll_timer.isActive() is False

    # 2f: _poll_for_run_id handles deleted run gracefully
    def test_poll_handles_deleted_run(self):
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._last_run_id = "deleted-run"
        widget._project_path = "/some/project"
        widget._command_running = True

        mock_sm = MagicMock(spec=StateManager)
        mock_sm.get_run.return_value = None  # Run was deleted
        widget.set_state_manager(mock_sm)

        widget._run_id_poll_timer.start(1000)

        widget._poll_for_run_id()

        # Widget should transition to not-running
        assert widget.is_running is False
        assert widget._run_id_poll_timer.isActive() is False
