"""Tests for GUI auto-install UX in the gui command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import app

runner = CliRunner()


class TestGuiInstallHint:
    @patch("levelup.cli.app._load_install_meta")
    def test_gui_error_global_install(self, mock_load):
        """Global install hint suggests self-update --gui."""
        mock_load.return_value = {"method": "global", "source_path": "/some/path"}

        # Force ImportError by patching the import
        with patch("levelup.cli.app.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = False
            mock_sys.executable = "/usr/bin/python"
            # Actually invoke the command — ImportError from gui.app
            with patch.dict("sys.modules", {"levelup.gui": None, "levelup.gui.app": None}):
                # We need to trigger the ImportError path. Simplest: call _get_gui_install_hint directly
                from levelup.cli.app import _get_gui_install_hint

                hint = _get_gui_install_hint()
                assert "self-update --gui" in hint

    @patch("levelup.cli.app._load_install_meta")
    def test_gui_error_editable_install(self, mock_load):
        """Editable install hint suggests uv pip install."""
        mock_load.return_value = {"method": "editable", "source_path": "/some/path"}

        from levelup.cli.app import _get_gui_install_hint

        hint = _get_gui_install_hint()
        assert "uv pip install" in hint
        assert ".[gui]" in hint

    @patch("levelup.cli.app._load_install_meta")
    def test_gui_error_no_metadata(self, mock_load):
        """No metadata — generic fallback hint."""
        mock_load.return_value = None

        from levelup.cli.app import _get_gui_install_hint

        hint = _get_gui_install_hint()
        assert "PyQt6" in hint


class TestGuiAutoInstall:
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app.subprocess.run")
    def test_gui_auto_install_global(self, mock_run, mock_load, mock_save):
        """Global auto-install: runs uv tool install --force with [gui], updates metadata."""
        mock_load.return_value = {
            "method": "global",
            "source_path": "/some/path",
            "extras": [],
        }
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        from levelup.cli.app import _auto_install_gui

        result = _auto_install_gui()

        # Global returns False (can't re-import)
        assert result is False

        # Check subprocess was called with correct args
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "uv" in cmd
        assert "tool" in cmd
        assert "--force" in cmd
        assert "/some/path[gui]" in cmd[-1]

        # Check metadata was updated with gui extra
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert "gui" in saved["extras"]

    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app.subprocess.run")
    def test_gui_auto_install_editable(self, mock_run, mock_load, mock_save):
        """Editable auto-install: runs uv pip install -e .[gui]."""
        mock_load.return_value = {
            "method": "editable",
            "source_path": "/some/path",
            "extras": [],
        }
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        from levelup.cli.app import _auto_install_gui

        result = _auto_install_gui()

        # Editable returns True (can re-import)
        assert result is True

        # Check subprocess was called with editable install
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "-e" in cmd
        assert ".[gui]" in cmd

        # Check metadata was updated
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert "gui" in saved["extras"]

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app.subprocess.run")
    def test_gui_auto_install_no_metadata(self, mock_run, mock_load):
        """No metadata — installs PyQt6 directly."""
        mock_load.return_value = None
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        from levelup.cli.app import _auto_install_gui

        result = _auto_install_gui()

        assert result is True
        cmd = mock_run.call_args[0][0]
        assert "PyQt6>=6.6.0" in cmd

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app.subprocess.run")
    def test_gui_auto_install_failure(self, mock_run, mock_load):
        """Install failure returns False."""
        mock_load.return_value = {"method": "editable", "source_path": "/some/path"}
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        from levelup.cli.app import _auto_install_gui

        result = _auto_install_gui()
        assert result is False

    @patch("levelup.cli.app._load_install_meta")
    def test_gui_auto_install_global_no_source(self, mock_load):
        """Global install without source_path in metadata returns False."""
        mock_load.return_value = {"method": "global"}

        from levelup.cli.app import _auto_install_gui

        result = _auto_install_gui()
        assert result is False


class TestGuiCommandIntegration:
    @patch("levelup.cli.app._get_gui_install_hint")
    @patch("levelup.cli.app.sys")
    def test_gui_not_tty_shows_hint_and_exits(self, mock_sys, mock_hint):
        """When not a TTY, show hint and exit 1 without prompting."""
        mock_sys.stdin.isatty.return_value = False
        mock_sys.executable = "/usr/bin/python"
        mock_hint.return_value = "Install hint here"

        # Simulate ImportError on gui import
        with patch("levelup.gui.app.launch_gui", side_effect=ImportError):
            result = runner.invoke(app, ["gui"])

        assert result.exit_code == 1

    @patch("levelup.cli.app._auto_install_gui")
    @patch("levelup.cli.prompts.confirm_action")
    @patch("levelup.cli.app._get_gui_install_hint")
    @patch("levelup.cli.app.sys")
    def test_gui_tty_declined(self, mock_sys, mock_hint, mock_confirm, mock_auto):
        """When TTY and user declines, exit 1."""
        mock_sys.stdin.isatty.return_value = True
        mock_sys.executable = "/usr/bin/python"
        mock_hint.return_value = "Install hint here"
        mock_confirm.return_value = False

        with patch("levelup.gui.app.launch_gui", side_effect=ImportError):
            result = runner.invoke(app, ["gui"])

        assert result.exit_code == 1
        mock_auto.assert_not_called()
