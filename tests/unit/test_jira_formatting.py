"""Tests for Jira description formatting, HTML stripping, and metadata extraction."""

from __future__ import annotations

from levelup.integrations.jira import (
    extract_jira_metadata,
    format_jira_description,
    strip_html,
)


class TestStripHtml:
    def test_plain_text_passthrough(self):
        assert strip_html("Hello world") == "Hello world"

    def test_strips_p_tags(self):
        assert strip_html("<p>Hello</p>") == "Hello"

    def test_strips_nested_tags(self):
        assert strip_html("<div><b>bold</b> text</div>") == "bold text"

    def test_empty_string(self):
        assert strip_html("") == ""

    def test_preserves_whitespace(self):
        result = strip_html("<p>line one</p>\n<p>line two</p>")
        assert "line one" in result
        assert "line two" in result

    def test_handles_br_tags(self):
        assert strip_html("a<br/>b") == "ab"

    def test_handles_entities(self):
        # HTMLParser handles &amp; etc. automatically
        assert strip_html("a &amp; b") == "a & b"


class TestFormatJiraDescription:
    def test_rendered_description(self):
        issue = {
            "renderedFields": {"description": "<p>Fix the login bug</p>"},
            "fields": {"description": "Fix the login bug (plain)"},
        }
        result = format_jira_description(issue, [])
        assert result == "Fix the login bug"

    def test_falls_back_to_plain_description(self):
        issue = {
            "renderedFields": {"description": ""},
            "fields": {"description": "Plain description"},
        }
        result = format_jira_description(issue, [])
        assert result == "Plain description"

    def test_no_description(self):
        issue = {
            "renderedFields": {},
            "fields": {},
        }
        result = format_jira_description(issue, [])
        assert result == ""

    def test_with_comments(self):
        issue = {
            "renderedFields": {"description": "<p>Main text</p>"},
            "fields": {},
        }
        comments = [
            {
                "author": {"displayName": "Jane Smith"},
                "created": "2025-01-15T10:30:00.000+0000",
                "renderedBody": "<p>Looks good</p>",
                "body": "Looks good",
            },
        ]
        result = format_jira_description(issue, comments)
        assert "Main text" in result
        assert "## Comments" in result
        assert "### Jane Smith (2025-01-15 10:30)" in result
        assert "Looks good" in result

    def test_multiple_comments(self):
        issue = {"renderedFields": {"description": "<p>Desc</p>"}, "fields": {}}
        comments = [
            {
                "author": {"displayName": "Alice"},
                "created": "2025-01-10T08:00:00.000+0000",
                "renderedBody": "",
                "body": "First comment",
            },
            {
                "author": {"displayName": "Bob"},
                "created": "2025-01-11T09:00:00.000+0000",
                "renderedBody": "<b>Second</b> comment",
                "body": "Second comment",
            },
        ]
        result = format_jira_description(issue, comments)
        assert "### Alice (2025-01-10 08:00)" in result
        assert "First comment" in result
        assert "### Bob (2025-01-11 09:00)" in result
        assert "Second comment" in result

    def test_no_comments_section_when_empty(self):
        issue = {"renderedFields": {"description": "<p>Desc</p>"}, "fields": {}}
        result = format_jira_description(issue, [])
        assert "## Comments" not in result

    def test_comment_with_missing_author(self):
        issue = {"renderedFields": {"description": "<p>Text</p>"}, "fields": {}}
        comments = [
            {
                "author": {},
                "created": "2025-01-15T10:00:00.000+0000",
                "body": "Anonymous",
            },
        ]
        result = format_jira_description(issue, comments)
        assert "### Unknown (2025-01-15 10:00)" in result

    def test_comment_fallback_to_plain_body(self):
        issue = {"renderedFields": {"description": "<p>Text</p>"}, "fields": {}}
        comments = [
            {
                "author": {"displayName": "Dev"},
                "created": "2025-01-15T10:00:00.000+0000",
                "body": "Plain body text",
            },
        ]
        result = format_jira_description(issue, comments)
        assert "Plain body text" in result


class TestExtractJiraMetadata:
    def test_full_metadata(self):
        issue = {
            "key": "PROJ-123",
            "fields": {
                "priority": {"name": "High"},
                "labels": ["backend", "urgent"],
                "status": {"name": "To Do"},
                "issuetype": {"name": "Story"},
                "assignee": {"displayName": "Jane Doe"},
                "reporter": {"displayName": "John Smith"},
            },
        }
        meta = extract_jira_metadata(issue, "https://myco.atlassian.net")
        assert meta["jira_key"] == "PROJ-123"
        assert meta["jira_url"] == "https://myco.atlassian.net/browse/PROJ-123"
        assert meta["source"] == "jira"
        assert meta["jira_priority"] == "High"
        assert meta["jira_labels"] == ["backend", "urgent"]
        assert meta["jira_status"] == "To Do"
        assert meta["jira_type"] == "Story"
        assert meta["jira_assignee"] == "Jane Doe"
        assert meta["jira_reporter"] == "John Smith"

    def test_minimal_metadata(self):
        issue = {"key": "MIN-1", "fields": {}}
        meta = extract_jira_metadata(issue, "https://x.atlassian.net")
        assert meta["jira_key"] == "MIN-1"
        assert meta["source"] == "jira"
        assert "jira_priority" not in meta
        assert "jira_assignee" not in meta

    def test_missing_fields_key(self):
        issue = {"key": "X-1"}
        meta = extract_jira_metadata(issue, "https://x.atlassian.net")
        assert meta["jira_key"] == "X-1"

    def test_trailing_slash_stripped_from_url(self):
        issue = {"key": "X-1", "fields": {}}
        meta = extract_jira_metadata(issue, "https://x.atlassian.net/")
        assert meta["jira_url"] == "https://x.atlassian.net/browse/X-1"

    def test_null_priority(self):
        issue = {"key": "X-1", "fields": {"priority": None}}
        meta = extract_jira_metadata(issue, "https://x.atlassian.net")
        assert "jira_priority" not in meta

    def test_null_assignee(self):
        issue = {"key": "X-1", "fields": {"assignee": None}}
        meta = extract_jira_metadata(issue, "https://x.atlassian.net")
        assert "jira_assignee" not in meta

    def test_empty_labels(self):
        issue = {"key": "X-1", "fields": {"labels": []}}
        meta = extract_jira_metadata(issue, "https://x.atlassian.net")
        assert "jira_labels" not in meta
