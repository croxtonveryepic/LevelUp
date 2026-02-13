"""Unit tests for Jira configure CLI command and GUI dialog integration."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
import yaml


# ---------------------------------------------------------------------------
# save_jira_settings tests
# ---------------------------------------------------------------------------


class TestSaveJiraSettings:
    """Test that save_jira_settings writes only the jira section."""

    def test_creates_new_file_with_jira_section(self, tmp_path):
        from levelup.config.loader import save_jira_settings
        from levelup.config.settings import JiraSettings

        jira = JiraSettings(url="https://x.atlassian.net", email="a@b.com", token="tok")
        save_jira_settings(jira, project_path=tmp_path)

        config_file = tmp_path / "levelup.yaml"
        assert config_file.exists()

        data = yaml.safe_load(config_file.read_text())
        assert data["jira"]["url"] == "https://x.atlassian.net"
        assert data["jira"]["email"] == "a@b.com"
        assert data["jira"]["token"] == "tok"

    def test_preserves_existing_config(self, tmp_path):
        from levelup.config.loader import save_jira_settings
        from levelup.config.settings import JiraSettings

        # Write existing config
        config_file = tmp_path / "levelup.yaml"
        config_file.write_text(yaml.dump({"llm": {"model": "claude-opus"}, "pipeline": {"auto_approve": True}}))

        jira = JiraSettings(url="https://y.atlassian.net", email="b@c.com", token="t2")
        save_jira_settings(jira, project_path=tmp_path)

        data = yaml.safe_load(config_file.read_text())
        # Jira section updated
        assert data["jira"]["url"] == "https://y.atlassian.net"
        # Other sections preserved
        assert data["llm"]["model"] == "claude-opus"
        assert data["pipeline"]["auto_approve"] is True

    def test_overwrites_existing_jira_section(self, tmp_path):
        from levelup.config.loader import save_jira_settings
        from levelup.config.settings import JiraSettings

        config_file = tmp_path / "levelup.yaml"
        config_file.write_text(yaml.dump({"jira": {"url": "old", "email": "old", "token": "old"}}))

        jira = JiraSettings(url="new-url", email="new-email", token="new-token")
        save_jira_settings(jira, project_path=tmp_path)

        data = yaml.safe_load(config_file.read_text())
        assert data["jira"]["url"] == "new-url"
        assert data["jira"]["email"] == "new-email"
        assert data["jira"]["token"] == "new-token"

    def test_uses_cwd_when_no_project_path(self, tmp_path, monkeypatch):
        from levelup.config.loader import save_jira_settings
        from levelup.config.settings import JiraSettings

        monkeypatch.chdir(tmp_path)

        jira = JiraSettings(url="https://a.atlassian.net", email="e@f.com", token="tk")
        save_jira_settings(jira)

        config_file = tmp_path / "levelup.yaml"
        assert config_file.exists()
        data = yaml.safe_load(config_file.read_text())
        assert data["jira"]["url"] == "https://a.atlassian.net"


# ---------------------------------------------------------------------------
# jira configure CLI command tests
# ---------------------------------------------------------------------------


class TestJiraConfigureCLI:
    """Test the jira configure CLI command."""

    def test_successful_configure_flow(self, tmp_path):
        """Prompts -> test connection succeeds -> saves config."""
        from typer.testing import CliRunner
        from levelup.cli.app import app

        runner = CliRunner()

        mock_client = MagicMock()
        mock_client.search_issues.return_value = []

        with patch("prompt_toolkit.prompt", side_effect=[
            "https://test.atlassian.net",  # URL
            "user@test.com",  # Email
            "mytoken",  # Token
        ]), patch("levelup.integrations.jira.JiraClient", return_value=mock_client):
            result = runner.invoke(app, ["jira", "configure", "--path", str(tmp_path)])

        assert result.exit_code == 0
        assert "saved" in result.output.lower()

        # Verify config was written
        config_file = tmp_path / "levelup.yaml"
        assert config_file.exists()
        data = yaml.safe_load(config_file.read_text())
        assert data["jira"]["url"] == "https://test.atlassian.net"
        assert data["jira"]["email"] == "user@test.com"
        assert data["jira"]["token"] == "mytoken"

    def test_failed_connection_save_anyway_yes(self, tmp_path):
        """Connection fails -> user says save anyway -> config saved."""
        from typer.testing import CliRunner
        from levelup.cli.app import app

        runner = CliRunner()

        with patch("prompt_toolkit.prompt", side_effect=[
            "https://bad.atlassian.net",  # URL
            "user@bad.com",  # Email
            "badtoken",  # Token
            "y",  # Save anyway
        ]), patch(
            "levelup.integrations.jira.JiraClient",
            side_effect=Exception("connection refused"),
        ):
            result = runner.invoke(app, ["jira", "configure", "--path", str(tmp_path)])

        assert result.exit_code == 0
        assert "saved" in result.output.lower()

        config_file = tmp_path / "levelup.yaml"
        assert config_file.exists()

    def test_failed_connection_save_anyway_no_reprompts(self, tmp_path):
        """Connection fails -> user declines save -> re-prompts -> succeeds."""
        from typer.testing import CliRunner
        from levelup.cli.app import app

        runner = CliRunner()

        mock_client = MagicMock()
        mock_client.search_issues.return_value = []

        call_count = 0

        def jira_client_factory(url, email, token):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("connection refused")
            return mock_client

        with patch("prompt_toolkit.prompt", side_effect=[
            "https://bad.atlassian.net",  # first attempt URL
            "user@bad.com",  # first attempt Email
            "badtoken",  # first attempt Token
            "n",  # Don't save
            "https://good.atlassian.net",  # second attempt URL
            "user@good.com",  # second attempt Email
            "goodtoken",  # second attempt Token
        ]), patch(
            "levelup.integrations.jira.JiraClient",
            side_effect=jira_client_factory,
        ):
            result = runner.invoke(app, ["jira", "configure", "--path", str(tmp_path)])

        assert result.exit_code == 0
        assert "saved" in result.output.lower()

    def test_loads_existing_values_as_defaults(self, tmp_path):
        """Existing config values are passed as defaults to pt_prompt."""
        config_file = tmp_path / "levelup.yaml"
        config_file.write_text(yaml.dump({
            "jira": {"url": "https://existing.atlassian.net", "email": "old@e.com", "token": "oldtok"}
        }))

        from typer.testing import CliRunner
        from levelup.cli.app import app

        runner = CliRunner()

        mock_client = MagicMock()
        mock_client.search_issues.return_value = []

        prompt_calls = []

        def mock_prompt(msg, default=""):
            prompt_calls.append(default)
            return default  # Just accept defaults

        with patch("prompt_toolkit.prompt", side_effect=mock_prompt), \
             patch("levelup.integrations.jira.JiraClient", return_value=mock_client):
            result = runner.invoke(app, ["jira", "configure", "--path", str(tmp_path)])

        assert result.exit_code == 0
        # First three defaults should be the existing values
        assert prompt_calls[0] == "https://existing.atlassian.net"
        assert prompt_calls[1] == "old@e.com"
        assert prompt_calls[2] == "oldtok"

    def test_strips_trailing_slashes_from_url(self, tmp_path):
        """Trailing slashes on URL are stripped."""
        from typer.testing import CliRunner
        from levelup.cli.app import app

        runner = CliRunner()

        mock_client = MagicMock()
        mock_client.search_issues.return_value = []

        with patch("prompt_toolkit.prompt", side_effect=[
            "https://test.atlassian.net///",  # URL with trailing slashes
            "user@test.com",
            "tok",
        ]), patch("levelup.integrations.jira.JiraClient", return_value=mock_client):
            result = runner.invoke(app, ["jira", "configure", "--path", str(tmp_path)])

        assert result.exit_code == 0
        data = yaml.safe_load((tmp_path / "levelup.yaml").read_text())
        assert data["jira"]["url"] == "https://test.atlassian.net"


# ---------------------------------------------------------------------------
# GUI tests
# ---------------------------------------------------------------------------


def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


def _ensure_qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _make_mock_terminal_cls():
    """Create a mock TerminalEmulatorWidget that is a real QWidget subclass."""
    from PyQt6.QtWidgets import QWidget
    from PyQt6.QtCore import pyqtSignal

    class FakeTerminal(QWidget):
        shell_started = pyqtSignal()
        shell_exited = pyqtSignal(int)

        def start_shell(self, cwd=None, env=None):
            pass

        def send_command(self, cmd):
            pass

        def close_shell(self):
            pass

    return FakeTerminal


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestJiraConfigureDialog:
    """Test _JiraConfigureDialog class."""

    def test_dialog_exists_and_has_correct_title(self):
        _ensure_qapp()
        from levelup.gui.main_window import _JiraConfigureDialog

        with patch("levelup.gui.terminal_emulator.TerminalEmulatorWidget", _make_mock_terminal_cls()):
            dlg = _JiraConfigureDialog(None, Path("/tmp/proj"), "/tmp/state.db")

        assert dlg.windowTitle() == "Configure Jira Connection"

    def test_dialog_has_correct_size(self):
        _ensure_qapp()
        from levelup.gui.main_window import _JiraConfigureDialog

        with patch("levelup.gui.terminal_emulator.TerminalEmulatorWidget", _make_mock_terminal_cls()):
            dlg = _JiraConfigureDialog(None, Path("/tmp/proj"), "/tmp/state.db")

        assert dlg.width() == 700
        assert dlg.height() == 500

    def test_dialog_has_terminal_widget(self):
        _ensure_qapp()
        from levelup.gui.main_window import _JiraConfigureDialog

        with patch("levelup.gui.terminal_emulator.TerminalEmulatorWidget", _make_mock_terminal_cls()):
            dlg = _JiraConfigureDialog(None, Path("/tmp/proj"), "/tmp/state.db")

        assert hasattr(dlg, "_terminal")

    def test_dialog_emits_configure_finished_false(self):
        _ensure_qapp()
        from levelup.gui.main_window import _JiraConfigureDialog

        with patch("levelup.gui.terminal_emulator.TerminalEmulatorWidget", _make_mock_terminal_cls()):
            dlg = _JiraConfigureDialog(None, Path("/tmp/proj"), "/tmp/state.db")

        results = []
        dlg.configure_finished.connect(lambda success: results.append(success))

        # Simulate shell exit with no config
        with patch("levelup.gui.main_window.load_settings") as mock_settings:
            jira = MagicMock()
            jira.url = ""
            jira.email = ""
            jira.token = ""
            mock_settings.return_value.jira = jira
            dlg._on_shell_exited(0)

        assert len(results) == 1
        assert results[0] is False

    def test_dialog_emits_configure_finished_true(self):
        _ensure_qapp()
        from levelup.gui.main_window import _JiraConfigureDialog

        with patch("levelup.gui.terminal_emulator.TerminalEmulatorWidget", _make_mock_terminal_cls()):
            dlg = _JiraConfigureDialog(None, Path("/tmp/proj"), "/tmp/state.db")

        results = []
        dlg.configure_finished.connect(lambda success: results.append(success))

        with patch("levelup.gui.main_window.load_settings") as mock_settings:
            jira = MagicMock()
            jira.url = "https://x.atlassian.net"
            jira.email = "a@b.com"
            jira.token = "tok"
            mock_settings.return_value.jira = jira
            dlg._on_shell_exited(0)

        assert len(results) == 1
        assert results[0] is True


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestMainWindowJiraConfigure:
    """Test MainWindow opens configure dialog when Jira is not configured."""

    def _make_window(self, jira_url="", jira_email="", jira_token=""):
        from levelup.gui.main_window import MainWindow

        sm = MagicMock()
        sm._db_path = "/tmp/state.db"
        sm.list_runs.return_value = []
        sm.list_known_projects.return_value = []
        sm.mark_dead_runs.return_value = None
        sm.get_pending_checkpoints.return_value = []

        jira_settings = MagicMock()
        jira_settings.url = jira_url
        jira_settings.email = jira_email
        jira_settings.token = jira_token

        settings = MagicMock()
        settings.jira = jira_settings
        settings.project.tickets_file = "tickets.md"
        settings.gui.hotkeys = MagicMock(
            next_waiting_ticket="Ctrl+N",
            back_to_runs="Escape",
            toggle_theme="Ctrl+T",
            refresh_dashboard="F5",
            open_documentation="F1",
            focus_terminal="Ctrl+`",
        )

        with patch("levelup.gui.main_window.load_settings", return_value=settings):
            win = MainWindow(sm)
        return win, settings

    def test_button_not_hidden_when_project_selected_even_if_not_configured(self):
        """Jira button is not hidden when a project is selected."""
        _ensure_qapp()
        from pathlib import Path
        from PyQt6.QtWidgets import QPushButton

        win, settings = self._make_window()

        # Switch to a project
        with patch("levelup.gui.main_window.load_settings", return_value=settings):
            win._switch_project(Path("/tmp/proj"))

        btn = win._sidebar.findChild(QPushButton, "jiraImportBtn")
        assert btn.isHidden() is False

    def test_button_hidden_when_no_project(self):
        """Jira button hidden when All Projects selected."""
        _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton

        win, settings = self._make_window()

        with patch("levelup.gui.main_window.load_settings", return_value=settings):
            win._switch_project(None)

        btn = win._sidebar.findChild(QPushButton, "jiraImportBtn")
        assert btn.isHidden() is True

    def test_on_jira_import_opens_configure_dialog_when_not_configured(self):
        """Clicking Jira import when not configured opens the configure dialog."""
        _ensure_qapp()
        from pathlib import Path

        win, settings = self._make_window()

        with patch("levelup.gui.main_window.load_settings", return_value=settings):
            win._switch_project(Path("/tmp/proj"))

        with patch("levelup.gui.main_window._JiraConfigureDialog") as MockDialog:
            mock_instance = MagicMock()
            MockDialog.return_value = mock_instance
            with patch("levelup.gui.main_window.load_settings", return_value=settings):
                win._on_jira_import()

            MockDialog.assert_called_once()
            mock_instance.exec.assert_called_once()

    def test_on_jira_import_starts_thread_when_configured(self):
        """Clicking Jira import when configured starts the import thread."""
        _ensure_qapp()
        from pathlib import Path

        win, settings = self._make_window(
            jira_url="https://x.atlassian.net",
            jira_email="a@b.com",
            jira_token="tok",
        )

        with patch("levelup.gui.main_window.load_settings", return_value=settings):
            win._switch_project(Path("/tmp/proj"))

        with patch("levelup.gui.main_window._JiraImportThread") as MockThread, \
             patch("levelup.gui.main_window.load_settings", return_value=settings):
            mock_instance = MagicMock()
            mock_instance.isRunning.return_value = False
            MockThread.return_value = mock_instance
            win._on_jira_import()

            MockThread.assert_called_once()
            mock_instance.start.assert_called_once()

    def test_on_jira_configure_finished_triggers_import(self):
        """After successful configure, auto-triggers import."""
        _ensure_qapp()
        from pathlib import Path

        win, settings = self._make_window()

        with patch("levelup.gui.main_window.load_settings", return_value=settings):
            win._switch_project(Path("/tmp/proj"))

        # Now simulate configure finished with success=True but settings still empty
        with patch.object(win, "_is_jira_configured", return_value=True), \
             patch.object(win, "_on_jira_import") as mock_import:
            win._on_jira_configure_finished(True)
            mock_import.assert_called_once()

    def test_on_jira_configure_finished_false_no_import(self):
        """Failed configure does not trigger import."""
        _ensure_qapp()
        from pathlib import Path

        win, settings = self._make_window()

        with patch("levelup.gui.main_window.load_settings", return_value=settings):
            win._switch_project(Path("/tmp/proj"))

        with patch.object(win, "_on_jira_import") as mock_import:
            win._on_jira_configure_finished(False)
            mock_import.assert_not_called()
