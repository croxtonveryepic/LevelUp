"""Tests for the RunTerminalWidget."""

from __future__ import annotations

import sys

import pytest

from levelup.gui.run_terminal import build_command


def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


class TestBuildCommand:
    def test_basic_command(self):
        args = build_command(
            ticket_number=3,
            project_path="/some/project",
            db_path="/tmp/state.db",
        )
        assert args == [
            "-m", "levelup", "run",
            "--gui",
            "--ticket", "3",
            "--path", "/some/project",
            "--db-path", "/tmp/state.db",
        ]

    def test_ticket_number_is_stringified(self):
        args = build_command(
            ticket_number=42,
            project_path="/p",
            db_path="/d",
        )
        assert "--ticket" in args
        idx = args.index("--ticket")
        assert args[idx + 1] == "42"

    def test_gui_flag_present(self):
        args = build_command(ticket_number=1, project_path="/p", db_path="/d")
        assert "--gui" in args

    def test_all_required_flags_present(self):
        args = build_command(ticket_number=1, project_path="/p", db_path="/d")
        assert "--path" in args
        assert "--db-path" in args
        assert "--ticket" in args
        assert "--gui" in args


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestRunTerminalWidget:
    def test_widget_construction(self):
        from PyQt6.QtWidgets import QApplication

        # Ensure QApplication exists
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

        # Initially: run disabled (no ticket), stop disabled
        assert widget._stop_btn.isEnabled() is False

        # Simulate running state
        widget._set_running_state(True)
        assert widget._run_btn.isEnabled() is False
        assert widget._stop_btn.isEnabled() is True
        assert "Running" in widget._status_label.text()

        # Simulate stopped state
        widget._set_running_state(False)
        assert widget._run_btn.isEnabled() is True
        assert widget._stop_btn.isEnabled() is False
        assert "Ready" in widget._status_label.text()

    def test_enable_run(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
        widget.enable_run(True)
        assert widget._run_btn.isEnabled() is True

        widget.enable_run(False)
        assert widget._run_btn.isEnabled() is False
