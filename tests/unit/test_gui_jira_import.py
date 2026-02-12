"""Unit tests for GUI Jira import button functionality."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


def _ensure_qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


# ---------------------------------------------------------------------------
# Sidebar button tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestJiraButtonInSidebar:
    """Test Jira import button existence and visibility in the sidebar."""

    def test_jira_button_exists_with_correct_object_name(self):
        _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton
        from levelup.gui.ticket_sidebar import TicketSidebarWidget

        widget = TicketSidebarWidget()
        btn = widget.findChild(QPushButton, "jiraImportBtn")
        assert btn is not None

    def test_jira_button_hidden_by_default(self):
        _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton
        from levelup.gui.ticket_sidebar import TicketSidebarWidget

        widget = TicketSidebarWidget()
        btn = widget.findChild(QPushButton, "jiraImportBtn")
        assert btn.isVisible() is False

    def test_jira_button_text_is_j(self):
        _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton
        from levelup.gui.ticket_sidebar import TicketSidebarWidget

        widget = TicketSidebarWidget()
        btn = widget.findChild(QPushButton, "jiraImportBtn")
        assert btn.text() == "J"

    def test_set_jira_enabled_true_shows_button(self):
        _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton
        from levelup.gui.ticket_sidebar import TicketSidebarWidget

        widget = TicketSidebarWidget()
        widget.set_jira_enabled(True)
        btn = widget.findChild(QPushButton, "jiraImportBtn")
        assert btn.isVisible() is True

    def test_set_jira_enabled_false_hides_button(self):
        _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton
        from levelup.gui.ticket_sidebar import TicketSidebarWidget

        widget = TicketSidebarWidget()
        widget.set_jira_enabled(True)
        widget.set_jira_enabled(False)
        btn = widget.findChild(QPushButton, "jiraImportBtn")
        assert btn.isVisible() is False

    def test_set_jira_importing_disables_button(self):
        _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton
        from levelup.gui.ticket_sidebar import TicketSidebarWidget

        widget = TicketSidebarWidget()
        widget.set_jira_enabled(True)
        widget.set_jira_importing(True)
        btn = widget.findChild(QPushButton, "jiraImportBtn")
        assert btn.isEnabled() is False
        assert "Importing" in btn.toolTip()

    def test_set_jira_importing_false_re_enables_button(self):
        _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton
        from levelup.gui.ticket_sidebar import TicketSidebarWidget

        widget = TicketSidebarWidget()
        widget.set_jira_enabled(True)
        widget.set_jira_importing(True)
        widget.set_jira_importing(False)
        btn = widget.findChild(QPushButton, "jiraImportBtn")
        assert btn.isEnabled() is True

    def test_jira_button_emits_signal_on_click(self):
        _ensure_qapp()
        from levelup.gui.ticket_sidebar import TicketSidebarWidget

        widget = TicketSidebarWidget()
        widget.set_jira_enabled(True)

        signal_received = []
        widget.jira_import_clicked.connect(lambda: signal_received.append(True))
        widget._jira_btn.click()

        assert len(signal_received) == 1


# ---------------------------------------------------------------------------
# _JiraImportThread tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestJiraImportThread:
    """Test the background Jira import thread."""

    def test_thread_emits_finished_on_success(self):
        _ensure_qapp()
        from levelup.gui.main_window import _JiraImportThread

        thread = _JiraImportThread(
            jira_url="https://test.atlassian.net",
            jira_email="test@test.com",
            jira_token="token",
            project_path="/tmp/proj",
            db_path="/tmp/state.db",
        )

        results = []
        thread.finished.connect(lambda imported, warnings: results.append((imported, warnings)))

        mock_ticket = MagicMock()
        with patch(
            "levelup.integrations.jira.import_jira_issues_by_jql",
            return_value=([mock_ticket], ["skipped one"]),
        ), patch(
            "levelup.integrations.jira.JiraClient",
        ):
            thread.run()

        assert len(results) == 1
        assert len(results[0][0]) == 1
        assert results[0][1] == ["skipped one"]

    def test_thread_emits_error_on_auth_failure(self):
        _ensure_qapp()
        from levelup.gui.main_window import _JiraImportThread

        thread = _JiraImportThread(
            jira_url="https://test.atlassian.net",
            jira_email="test@test.com",
            jira_token="bad",
            project_path="/tmp/proj",
            db_path="/tmp/state.db",
        )

        errors = []
        thread.error.connect(lambda msg: errors.append(msg))

        from levelup.integrations.jira import JiraAuthError

        with patch(
            "levelup.integrations.jira.JiraClient",
            side_effect=JiraAuthError("bad creds"),
        ):
            thread.run()

        assert len(errors) == 1
        assert "authentication" in errors[0].lower()

    def test_thread_emits_error_on_connection_failure(self):
        _ensure_qapp()
        from levelup.gui.main_window import _JiraImportThread

        thread = _JiraImportThread(
            jira_url="https://test.atlassian.net",
            jira_email="test@test.com",
            jira_token="token",
            project_path="/tmp/proj",
            db_path="/tmp/state.db",
        )

        errors = []
        thread.error.connect(lambda msg: errors.append(msg))

        from levelup.integrations.jira import JiraConnectionError

        with patch(
            "levelup.integrations.jira.JiraClient",
            side_effect=JiraConnectionError("timeout"),
        ):
            thread.run()

        assert len(errors) == 1
        assert "connect" in errors[0].lower()


# ---------------------------------------------------------------------------
# MainWindow Jira integration tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestMainWindowJiraConfig:
    """Test _is_jira_configured and button visibility on MainWindow."""

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

    def test_jira_not_configured_when_creds_missing(self):
        _ensure_qapp()
        win, _ = self._make_window()
        assert win._is_jira_configured() is False

    def test_jira_not_configured_when_partial_creds(self):
        _ensure_qapp()
        win, settings = self._make_window(jira_url="https://x.atlassian.net")
        # Partially configured — email/token empty
        assert win._is_jira_configured() is False

    def test_jira_configured_when_all_creds_present(self):
        _ensure_qapp()
        win, _ = self._make_window(
            jira_url="https://x.atlassian.net",
            jira_email="a@b.com",
            jira_token="tok",
        )
        assert win._is_jira_configured() is True

    def test_button_hidden_when_jira_not_configured(self):
        _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton

        win, _ = self._make_window()
        btn = win._sidebar.findChild(QPushButton, "jiraImportBtn")
        assert btn.isVisible() is False

    def test_button_visible_when_jira_configured(self):
        _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton

        win, _ = self._make_window(
            jira_url="https://x.atlassian.net",
            jira_email="a@b.com",
            jira_token="tok",
        )
        btn = win._sidebar.findChild(QPushButton, "jiraImportBtn")
        assert btn.isVisible() is True

    def test_switch_project_updates_jira_visibility(self):
        _ensure_qapp()
        from pathlib import Path
        from PyQt6.QtWidgets import QPushButton

        win, settings = self._make_window(
            jira_url="https://x.atlassian.net",
            jira_email="a@b.com",
            jira_token="tok",
        )

        btn = win._sidebar.findChild(QPushButton, "jiraImportBtn")
        assert btn.isVisible() is True

        # Now switch project — settings still return configured Jira
        with patch("levelup.gui.main_window.load_settings", return_value=settings):
            win._switch_project(Path("/tmp/other"))

        assert btn.isVisible() is True
