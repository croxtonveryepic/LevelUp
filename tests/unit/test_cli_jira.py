"""Tests for the `levelup jira import` CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import app
from levelup.core.tickets import read_tickets

runner = CliRunner()


def _make_issue(key: str = "TEST-1", summary: str = "Fix bug") -> dict:
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "description": "Plain desc",
            "priority": {"name": "Medium"},
            "status": {"name": "To Do"},
            "issuetype": {"name": "Task"},
            "labels": [],
            "assignee": None,
            "reporter": {"displayName": "Reporter"},
        },
        "renderedFields": {
            "description": "<p>Rendered desc</p>",
        },
    }


class TestJiraImportHelp:
    def test_jira_help(self):
        result = runner.invoke(app, ["jira", "--help"])
        assert result.exit_code == 0
        assert "Jira integration" in result.output

    def test_jira_import_help(self):
        result = runner.invoke(app, ["jira", "import", "--help"])
        assert result.exit_code == 0
        assert "--url" in result.output
        assert "--email" in result.output
        assert "--token" in result.output
        assert "--dry-run" in result.output
        assert "--max-results" in result.output


class TestJiraImportCredValidation:
    def test_missing_all_creds(self, tmp_path: Path):
        result = runner.invoke(app, [
            "jira", "import", "PROJ-1", "--path", str(tmp_path),
        ])
        assert result.exit_code == 1
        assert "Missing Jira credentials" in result.output
        assert "url" in result.output
        assert "email" in result.output
        assert "token" in result.output

    def test_missing_email(self, tmp_path: Path):
        result = runner.invoke(app, [
            "jira", "import", "PROJ-1",
            "--path", str(tmp_path),
            "--url", "https://x.atlassian.net",
            "--token", "tok",
        ])
        assert result.exit_code == 1
        assert "email" in result.output

    def test_missing_token(self, tmp_path: Path):
        result = runner.invoke(app, [
            "jira", "import", "PROJ-1",
            "--path", str(tmp_path),
            "--url", "https://x.atlassian.net",
            "--email", "a@b.com",
        ])
        assert result.exit_code == 1
        assert "token" in result.output

    def test_missing_url(self, tmp_path: Path):
        result = runner.invoke(app, [
            "jira", "import", "PROJ-1",
            "--path", str(tmp_path),
            "--email", "a@b.com",
            "--token", "tok",
        ])
        assert result.exit_code == 1
        assert "url" in result.output


class TestJiraImportSingleKey:
    @patch("levelup.integrations.jira.JiraClient")
    def test_import_success(self, MockClient, tmp_path: Path):
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.base_url = "https://test.atlassian.net"
        mock_client.get_issue.return_value = _make_issue("PROJ-1", "Fix login")
        mock_client.get_issue_comments.return_value = []

        result = runner.invoke(app, [
            "jira", "import", "PROJ-1",
            "--path", str(tmp_path),
            "--url", "https://test.atlassian.net",
            "--email", "a@b.com",
            "--token", "tok",
        ])

        assert result.exit_code == 0
        assert "Imported ticket" in result.output
        assert "PROJ-1" in result.output

    @patch("levelup.integrations.jira.JiraClient")
    def test_import_dry_run(self, MockClient, tmp_path: Path):
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.base_url = "https://test.atlassian.net"
        mock_client.get_issue.return_value = _make_issue("DRY-1", "Dry task")
        mock_client.get_issue_comments.return_value = []

        result = runner.invoke(app, [
            "jira", "import", "DRY-1",
            "--path", str(tmp_path),
            "--url", "https://test.atlassian.net",
            "--email", "a@b.com",
            "--token", "tok",
            "--dry-run",
        ])

        assert result.exit_code == 0
        assert "Would create" in result.output
        assert len(read_tickets(tmp_path)) == 0


class TestJiraImportJQL:
    @patch("levelup.integrations.jira.JiraClient")
    def test_jql_import(self, MockClient, tmp_path: Path):
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.base_url = "https://test.atlassian.net"
        mock_client.search_issues.return_value = [
            _make_issue("JQL-1", "First"),
            _make_issue("JQL-2", "Second"),
        ]
        mock_client.get_issue.side_effect = lambda k: _make_issue(k, f"Issue {k}")
        mock_client.get_issue_comments.return_value = []

        result = runner.invoke(app, [
            "jira", "import", "project=JQL",
            "--path", str(tmp_path),
            "--url", "https://test.atlassian.net",
            "--email", "a@b.com",
            "--token", "tok",
        ])

        assert result.exit_code == 0
        assert "2 ticket(s) imported" in result.output

    @patch("levelup.integrations.jira.JiraClient")
    def test_jql_no_results(self, MockClient, tmp_path: Path):
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.base_url = "https://test.atlassian.net"
        mock_client.search_issues.return_value = []

        result = runner.invoke(app, [
            "jira", "import", "project=EMPTY",
            "--path", str(tmp_path),
            "--url", "https://test.atlassian.net",
            "--email", "a@b.com",
            "--token", "tok",
        ])

        assert result.exit_code == 0
        assert "No issues found" in result.output


class TestJiraImportErrors:
    @patch("levelup.integrations.jira.JiraClient")
    def test_auth_error(self, MockClient, tmp_path: Path):
        from levelup.integrations.jira import JiraAuthError

        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.get_issue.side_effect = JiraAuthError("Authentication failed (401)")

        result = runner.invoke(app, [
            "jira", "import", "FAIL-1",
            "--path", str(tmp_path),
            "--url", "https://test.atlassian.net",
            "--email", "a@b.com",
            "--token", "bad",
        ])

        assert result.exit_code == 1
        assert "Authentication failed" in result.output

    @patch("levelup.integrations.jira.JiraClient")
    def test_connection_error(self, MockClient, tmp_path: Path):
        from levelup.integrations.jira import JiraConnectionError

        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.get_issue.side_effect = JiraConnectionError("Cannot connect")

        result = runner.invoke(app, [
            "jira", "import", "FAIL-1",
            "--path", str(tmp_path),
            "--url", "https://test.atlassian.net",
            "--email", "a@b.com",
            "--token", "tok",
        ])

        assert result.exit_code == 1
        assert "Cannot connect" in result.output

    @patch("levelup.integrations.jira.JiraClient")
    def test_not_found_error(self, MockClient, tmp_path: Path):
        from levelup.integrations.jira import JiraNotFoundError

        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.get_issue.side_effect = JiraNotFoundError("Not found: FAIL-1")

        result = runner.invoke(app, [
            "jira", "import", "FAIL-1",
            "--path", str(tmp_path),
            "--url", "https://test.atlassian.net",
            "--email", "a@b.com",
            "--token", "tok",
        ])

        assert result.exit_code == 1
        assert "Not found" in result.output
