"""Tests for JiraClient — mock requests.Session.get for all endpoints + error cases."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from levelup.integrations.jira import (
    JiraAuthError,
    JiraClient,
    JiraConnectionError,
    JiraNotFoundError,
)


def _make_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.url = "https://test.atlassian.net/rest/api/2/issue/TEST-1"
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestJiraClientGetIssue:
    def test_get_issue_success(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "tok")
        issue_data = {"key": "TEST-1", "fields": {"summary": "Fix bug"}}
        with patch.object(client._session, "get", return_value=_make_response(200, issue_data)):
            result = client.get_issue("TEST-1")
        assert result["key"] == "TEST-1"

    def test_get_issue_auth_error_401(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "bad")
        with patch.object(client._session, "get", return_value=_make_response(401)):
            with pytest.raises(JiraAuthError, match="Authentication failed"):
                client.get_issue("TEST-1")

    def test_get_issue_auth_error_403(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "bad")
        with patch.object(client._session, "get", return_value=_make_response(403)):
            with pytest.raises(JiraAuthError, match="Authentication failed"):
                client.get_issue("TEST-1")

    def test_get_issue_not_found(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "tok")
        with patch.object(client._session, "get", return_value=_make_response(404)):
            with pytest.raises(JiraNotFoundError, match="Not found"):
                client.get_issue("NOPE-999")

    def test_get_issue_connection_error(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "tok")
        with patch.object(
            client._session, "get", side_effect=requests.ConnectionError("timeout")
        ):
            with pytest.raises(JiraConnectionError, match="Cannot connect"):
                client.get_issue("TEST-1")

    def test_get_issue_strips_trailing_slash(self):
        client = JiraClient("https://test.atlassian.net/", "a@b.com", "tok")
        assert client.base_url == "https://test.atlassian.net"


class TestJiraClientGetComments:
    def test_get_comments_success(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "tok")
        data = {
            "comments": [
                {"body": "looks good", "author": {"displayName": "Alice"}},
            ]
        }
        with patch.object(client._session, "get", return_value=_make_response(200, data)):
            result = client.get_issue_comments("TEST-1")
        assert len(result) == 1
        assert result[0]["body"] == "looks good"

    def test_get_comments_empty(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "tok")
        with patch.object(client._session, "get", return_value=_make_response(200, {})):
            result = client.get_issue_comments("TEST-1")
        assert result == []

    def test_get_comments_auth_error(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "bad")
        with patch.object(client._session, "get", return_value=_make_response(401)):
            with pytest.raises(JiraAuthError):
                client.get_issue_comments("TEST-1")

    def test_get_comments_connection_error(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "tok")
        with patch.object(
            client._session, "get", side_effect=requests.ConnectionError("err")
        ):
            with pytest.raises(JiraConnectionError):
                client.get_issue_comments("TEST-1")


class TestJiraClientSearch:
    def test_search_success(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "tok")
        data = {
            "issues": [
                {"key": "TEST-1", "fields": {"summary": "One"}},
                {"key": "TEST-2", "fields": {"summary": "Two"}},
            ]
        }
        with patch.object(client._session, "get", return_value=_make_response(200, data)):
            result = client.search_issues("project=TEST", max_results=10)
        assert len(result) == 2
        assert result[0]["key"] == "TEST-1"

    def test_search_empty(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "tok")
        with patch.object(client._session, "get", return_value=_make_response(200, {"issues": []})):
            result = client.search_issues("project=NOPE")
        assert result == []

    def test_search_auth_error(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "bad")
        with patch.object(client._session, "get", return_value=_make_response(403)):
            with pytest.raises(JiraAuthError):
                client.search_issues("project=TEST")

    def test_search_connection_error(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "tok")
        with patch.object(
            client._session, "get", side_effect=requests.ConnectionError("err")
        ):
            with pytest.raises(JiraConnectionError):
                client.search_issues("project=TEST")


class TestJiraClientAuth:
    def test_basic_auth_set(self):
        client = JiraClient("https://test.atlassian.net", "user@co.com", "mytoken")
        assert client._session.auth == ("user@co.com", "mytoken")

    def test_accept_header_set(self):
        client = JiraClient("https://test.atlassian.net", "a@b.com", "tok")
        assert client._session.headers["Accept"] == "application/json"
