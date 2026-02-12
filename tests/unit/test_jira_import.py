"""Tests for Jira import logic: single import, JQL batch, duplicate skip, metadata storage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from levelup.core.tickets import read_tickets
from levelup.integrations.jira import (
    JiraClient,
    JiraNotFoundError,
    import_jira_issue,
    import_jira_issues_by_jql,
)


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


def _make_comment(author: str = "Alice", body: str = "Nice work") -> dict:
    return {
        "author": {"displayName": author},
        "created": "2025-06-01T12:00:00.000+0000",
        "renderedBody": f"<p>{body}</p>",
        "body": body,
    }


class TestImportSingleIssue:
    def test_import_creates_ticket(self, tmp_path: Path):
        client = MagicMock(spec=JiraClient)
        client.base_url = "https://test.atlassian.net"
        client.get_issue.return_value = _make_issue("PROJ-42", "Login fix")
        client.get_issue_comments.return_value = []

        ticket, warning = import_jira_issue(client, "PROJ-42", tmp_path)

        assert warning is None
        assert ticket is not None
        assert ticket.title == "[PROJ-42] Login fix"
        assert ticket.number >= 1

        # Verify in DB
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
        assert tickets[0].title == "[PROJ-42] Login fix"

    def test_import_stores_metadata(self, tmp_path: Path):
        client = MagicMock(spec=JiraClient)
        client.base_url = "https://test.atlassian.net"
        client.get_issue.return_value = _make_issue("PROJ-1", "Task")
        client.get_issue_comments.return_value = []

        ticket, _ = import_jira_issue(client, "PROJ-1", tmp_path)

        assert ticket is not None
        # Metadata is stored — read back from DB
        tickets = read_tickets(tmp_path)
        meta = tickets[0].metadata
        assert meta is not None
        assert meta["jira_key"] == "PROJ-1"
        assert meta["source"] == "jira"
        assert "jira_url" in meta

    def test_import_includes_comments_in_description(self, tmp_path: Path):
        client = MagicMock(spec=JiraClient)
        client.base_url = "https://test.atlassian.net"
        client.get_issue.return_value = _make_issue("PROJ-1", "Task")
        client.get_issue_comments.return_value = [
            _make_comment("Bob", "Needs review"),
        ]

        ticket, _ = import_jira_issue(client, "PROJ-1", tmp_path)

        tickets = read_tickets(tmp_path)
        desc = tickets[0].description
        assert "## Comments" in desc
        assert "Bob" in desc
        assert "Needs review" in desc

    def test_duplicate_skip(self, tmp_path: Path):
        client = MagicMock(spec=JiraClient)
        client.base_url = "https://test.atlassian.net"
        client.get_issue.return_value = _make_issue("DUP-1", "Dup task")
        client.get_issue_comments.return_value = []

        # First import
        ticket1, warn1 = import_jira_issue(client, "DUP-1", tmp_path)
        assert ticket1 is not None
        assert warn1 is None

        # Second import — should skip
        ticket2, warn2 = import_jira_issue(client, "DUP-1", tmp_path)
        assert ticket2 is None
        assert warn2 is not None
        assert "Skipped DUP-1" in warn2
        assert f"ticket #{ticket1.number}" in warn2

        # Only one ticket in DB
        assert len(read_tickets(tmp_path)) == 1

    def test_dry_run_no_db_write(self, tmp_path: Path):
        client = MagicMock(spec=JiraClient)
        client.base_url = "https://test.atlassian.net"
        client.get_issue.return_value = _make_issue("DRY-1", "Dry task")
        client.get_issue_comments.return_value = []

        ticket, warning = import_jira_issue(client, "DRY-1", tmp_path, dry_run=True)

        assert warning is None
        assert ticket is not None
        assert ticket.number == 0  # Synthetic preview ticket
        assert "[DRY-1]" in ticket.title
        assert len(read_tickets(tmp_path)) == 0

    def test_import_with_db_path(self, tmp_path: Path):
        db_file = tmp_path / "custom.db"
        client = MagicMock(spec=JiraClient)
        client.base_url = "https://test.atlassian.net"
        client.get_issue.return_value = _make_issue("DB-1", "Custom DB")
        client.get_issue_comments.return_value = []

        ticket, _ = import_jira_issue(client, "DB-1", tmp_path, db_path=db_file)

        assert ticket is not None
        tickets = read_tickets(tmp_path, db_path=db_file)
        assert len(tickets) == 1


class TestImportJQL:
    def test_jql_import_multiple(self, tmp_path: Path):
        client = MagicMock(spec=JiraClient)
        client.base_url = "https://test.atlassian.net"
        client.search_issues.return_value = [
            _make_issue("BATCH-1", "First"),
            _make_issue("BATCH-2", "Second"),
        ]
        client.get_issue.side_effect = lambda k: _make_issue(k, f"Issue {k}")
        client.get_issue_comments.return_value = []

        imported, warnings = import_jira_issues_by_jql(
            client, "project=BATCH", tmp_path
        )

        assert len(imported) == 2
        assert len(warnings) == 0
        assert len(read_tickets(tmp_path)) == 2

    def test_jql_skips_duplicates(self, tmp_path: Path):
        client = MagicMock(spec=JiraClient)
        client.base_url = "https://test.atlassian.net"

        # Pre-import one
        client.get_issue.return_value = _make_issue("SKP-1", "Already there")
        client.get_issue_comments.return_value = []
        import_jira_issue(client, "SKP-1", tmp_path)

        # JQL returns the same + a new one
        client.search_issues.return_value = [
            _make_issue("SKP-1", "Already there"),
            _make_issue("SKP-2", "New one"),
        ]
        client.get_issue.side_effect = lambda k: _make_issue(k, f"Issue {k}")

        imported, warnings = import_jira_issues_by_jql(
            client, "project=SKP", tmp_path
        )

        assert len(imported) == 1
        assert imported[0].title.startswith("[SKP-2]")
        assert len(warnings) == 1
        assert "Skipped SKP-1" in warnings[0]

    def test_jql_empty_results(self, tmp_path: Path):
        client = MagicMock(spec=JiraClient)
        client.base_url = "https://test.atlassian.net"
        client.search_issues.return_value = []

        imported, warnings = import_jira_issues_by_jql(
            client, "project=EMPTY", tmp_path
        )

        assert imported == []
        assert warnings == []

    def test_jql_collects_errors_as_warnings(self, tmp_path: Path):
        client = MagicMock(spec=JiraClient)
        client.base_url = "https://test.atlassian.net"
        client.search_issues.return_value = [
            _make_issue("ERR-1", "Fails"),
            _make_issue("ERR-2", "Works"),
        ]

        def mock_get_issue(k):
            if k == "ERR-1":
                raise JiraNotFoundError("Not found: ERR-1")
            return _make_issue(k, "Works")

        client.get_issue.side_effect = mock_get_issue
        client.get_issue_comments.return_value = []

        imported, warnings = import_jira_issues_by_jql(
            client, "project=ERR", tmp_path
        )

        assert len(imported) == 1
        assert len(warnings) == 1
        assert "ERR-1" in warnings[0]

    def test_jql_max_results_passed(self, tmp_path: Path):
        client = MagicMock(spec=JiraClient)
        client.base_url = "https://test.atlassian.net"
        client.search_issues.return_value = []

        import_jira_issues_by_jql(client, "project=X", tmp_path, max_results=10)

        client.search_issues.assert_called_once_with("project=X", max_results=10)

    def test_jql_dry_run(self, tmp_path: Path):
        client = MagicMock(spec=JiraClient)
        client.base_url = "https://test.atlassian.net"
        client.search_issues.return_value = [
            _make_issue("DRY-1", "Preview"),
        ]
        client.get_issue.return_value = _make_issue("DRY-1", "Preview")
        client.get_issue_comments.return_value = []

        imported, warnings = import_jira_issues_by_jql(
            client, "project=DRY", tmp_path, dry_run=True
        )

        assert len(imported) == 1
        assert imported[0].number == 0  # Preview
        assert len(read_tickets(tmp_path)) == 0
