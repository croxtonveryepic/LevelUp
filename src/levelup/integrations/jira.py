"""Jira Cloud integration: fetch issues/comments and import as LevelUp tickets."""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import requests

from levelup.core.tickets import Ticket, add_ticket, read_tickets

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class JiraAuthError(Exception):
    """Raised on 401/403 from Jira."""


class JiraNotFoundError(Exception):
    """Raised on 404 from Jira."""


class JiraConnectionError(Exception):
    """Raised on network failures."""


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------


class _HTMLStripper(HTMLParser):
    """Minimal HTML-to-text converter using stdlib."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def strip_html(html: str) -> str:
    """Strip HTML tags, returning plain text."""
    stripper = _HTMLStripper()
    stripper.feed(html)
    return stripper.get_text()


# ---------------------------------------------------------------------------
# Jira Client
# ---------------------------------------------------------------------------


class JiraClient:
    """Thin wrapper around Jira Cloud REST API v2."""

    def __init__(self, base_url: str, email: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.auth = (email, token)
        self._session.headers["Accept"] = "application/json"

    def _raise_for_status(self, resp: requests.Response) -> None:
        """Convert HTTP errors to domain exceptions."""
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            if resp.status_code in (401, 403):
                raise JiraAuthError(
                    f"Authentication failed ({resp.status_code}). "
                    "Check your email and API token."
                )
            if resp.status_code == 404:
                raise JiraNotFoundError(f"Not found: {resp.url}")
            raise

    def get_issue(self, key: str) -> dict[str, Any]:
        """Fetch a single issue with rendered fields."""
        url = f"{self.base_url}/rest/api/2/issue/{key}?expand=renderedFields"
        try:
            resp = self._session.get(url, timeout=30)
        except requests.ConnectionError as exc:
            raise JiraConnectionError(f"Cannot connect to {self.base_url}: {exc}") from exc
        self._raise_for_status(resp)
        return resp.json()

    def get_issue_comments(self, key: str) -> list[dict[str, Any]]:
        """Fetch comments for an issue."""
        url = f"{self.base_url}/rest/api/2/issue/{key}/comment"
        try:
            resp = self._session.get(url, timeout=30)
        except requests.ConnectionError as exc:
            raise JiraConnectionError(f"Cannot connect to {self.base_url}: {exc}") from exc
        self._raise_for_status(resp)
        data = resp.json()
        return data.get("comments", [])

    def search_issues(self, jql: str, max_results: int = 50) -> list[dict[str, Any]]:
        """Search issues via JQL."""
        url = f"{self.base_url}/rest/api/2/search"
        params = {
            "jql": jql,
            "maxResults": max_results,
            "expand": "renderedFields",
        }
        try:
            resp = self._session.get(url, params=params, timeout=30)
        except requests.ConnectionError as exc:
            raise JiraConnectionError(f"Cannot connect to {self.base_url}: {exc}") from exc
        self._raise_for_status(resp)
        data = resp.json()
        return data.get("issues", [])


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

_ISSUE_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")


def format_jira_description(issue: dict[str, Any], comments: list[dict[str, Any]]) -> str:
    """Build a Markdown description from Jira issue + comments.

    Uses ``renderedFields.description`` (HTML) when available,
    falls back to ``fields.description`` (plain text).
    """
    parts: list[str] = []

    # Description
    rendered = (issue.get("renderedFields") or {}).get("description", "")
    if rendered:
        parts.append(strip_html(rendered).strip())
    else:
        plain = (issue.get("fields") or {}).get("description") or ""
        parts.append(plain.strip())

    # Comments
    if comments:
        parts.append("")
        parts.append("## Comments")
        for comment in comments:
            author = (comment.get("author") or {}).get("displayName", "Unknown")
            created = comment.get("created", "")[:16].replace("T", " ")
            body_html = comment.get("renderedBody", "")
            if body_html:
                body = strip_html(body_html).strip()
            else:
                body = (comment.get("body") or "").strip()
            parts.append("")
            parts.append(f"### {author} ({created})")
            parts.append(body)

    return "\n".join(parts)


def extract_jira_metadata(issue: dict[str, Any], base_url: str) -> dict[str, Any]:
    """Extract metadata dict from a Jira issue for storage in ticket metadata."""
    fields = issue.get("fields") or {}
    key = issue.get("key", "")
    meta: dict[str, Any] = {
        "jira_key": key,
        "jira_url": f"{base_url.rstrip('/')}/browse/{key}",
        "source": "jira",
    }

    # Optional fields — gracefully handle missing
    priority = fields.get("priority")
    if priority and isinstance(priority, dict):
        meta["jira_priority"] = priority.get("name", "")

    labels = fields.get("labels")
    if labels:
        meta["jira_labels"] = labels

    status = fields.get("status")
    if status and isinstance(status, dict):
        meta["jira_status"] = status.get("name", "")

    issuetype = fields.get("issuetype")
    if issuetype and isinstance(issuetype, dict):
        meta["jira_type"] = issuetype.get("name", "")

    assignee = fields.get("assignee")
    if assignee and isinstance(assignee, dict):
        meta["jira_assignee"] = assignee.get("displayName", "")

    reporter = fields.get("reporter")
    if reporter and isinstance(reporter, dict):
        meta["jira_reporter"] = reporter.get("displayName", "")

    return meta


# ---------------------------------------------------------------------------
# Import logic
# ---------------------------------------------------------------------------


def _find_duplicate(jira_key: str, project_path: Path, db_path: Path | None) -> Ticket | None:
    """Check if a ticket with this jira_key already exists."""
    existing = read_tickets(project_path, db_path=db_path)
    for ticket in existing:
        if ticket.metadata and ticket.metadata.get("jira_key") == jira_key:
            return ticket
    return None


def import_jira_issue(
    client: JiraClient,
    key: str,
    project_path: Path,
    *,
    db_path: Path | None = None,
    dry_run: bool = False,
) -> tuple[Ticket | None, str | None]:
    """Import a single Jira issue as a LevelUp ticket.

    Returns ``(ticket, None)`` on success or ``(None, warning_message)`` on skip.
    """
    # Fetch issue + comments
    issue = client.get_issue(key)
    comments = client.get_issue_comments(key)

    jira_key = issue.get("key", key)

    # Duplicate check
    existing = _find_duplicate(jira_key, project_path, db_path)
    if existing:
        return None, f"Skipped {jira_key}: already imported as ticket #{existing.number}"

    if dry_run:
        title = (issue.get("fields") or {}).get("summary", key)
        # Return a synthetic ticket for preview
        preview = Ticket(number=0, title=f"[{jira_key}] {title}")
        return preview, None

    # Build ticket data
    fields = issue.get("fields") or {}
    title = f"[{jira_key}] {fields.get('summary', key)}"
    description = format_jira_description(issue, comments)
    metadata = extract_jira_metadata(issue, client.base_url)

    ticket = add_ticket(project_path, title, description, metadata=metadata, db_path=db_path)
    return ticket, None


def import_jira_issues_by_jql(
    client: JiraClient,
    jql: str,
    project_path: Path,
    *,
    db_path: Path | None = None,
    max_results: int = 50,
    dry_run: bool = False,
) -> tuple[list[Ticket], list[str]]:
    """Import issues matching a JQL query. Returns (imported, warnings)."""
    issues = client.search_issues(jql, max_results=max_results)
    imported: list[Ticket] = []
    warnings: list[str] = []

    for issue in issues:
        key = issue.get("key", "")
        if not key:
            continue
        try:
            ticket, warning = import_jira_issue(
                client, key, project_path, db_path=db_path, dry_run=dry_run
            )
            if warning:
                warnings.append(warning)
            elif ticket:
                imported.append(ticket)
        except (JiraAuthError, JiraNotFoundError, JiraConnectionError) as exc:
            warnings.append(f"Error importing {key}: {exc}")

    return imported, warnings
