"""Tests for the RunTerminalWidget."""

from __future__ import annotations

import sys

import pytest

from levelup.gui.run_terminal import build_run_command, build_resume_command


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

    def test_contains_gui_flag(self):
        cmd = build_run_command(1, "/p", "/d")
        assert "--gui" in cmd

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


class TestBuildResumeCommand:
    def test_contains_module_invocation(self):
        cmd = build_resume_command("abc123", "/some/project", "/tmp/state.db")
        assert "-m levelup resume" in cmd

    def test_contains_run_id(self):
        cmd = build_resume_command("abc123", "/p", "/d")
        assert "abc123" in cmd

    def test_contains_gui_flag(self):
        cmd = build_resume_command("abc123", "/p", "/d")
        assert "--gui" in cmd

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
