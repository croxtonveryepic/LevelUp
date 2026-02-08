"""Shared project context file — seeds and reads levelup/project_context.md."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_project_context_path(project_path: Path) -> Path:
    """Return the path to the shared project context file."""
    return project_path / "levelup" / "project_context.md"


def write_project_context(
    project_path: Path,
    *,
    language: str | None = None,
    framework: str | None = None,
    test_runner: str | None = None,
    test_command: str | None = None,
) -> None:
    """Write (or overwrite) the shared project context file with detection results."""
    path = get_project_context_path(project_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# Project Context",
            "",
            f"- **Language:** {language or 'unknown'}",
            f"- **Framework:** {framework or 'none'}",
            f"- **Test runner:** {test_runner or 'unknown'}",
            f"- **Test command:** {test_command or 'unknown'}",
            "",
            "## Codebase Insights",
            "",
            "(Agents append discoveries here)",
            "",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        logger.warning("Failed to write project context: %s", path)


# The detection header ends after the "- **Test command:**" line.
_DETECTION_HEADER_MARKER = "- **Test command:**"

# Default placeholder body when no recon data exists.
_DEFAULT_BODY = "\n## Codebase Insights\n\n(Agents append discoveries here)\n"


def read_project_context_body(project_path: Path) -> str | None:
    """Read everything below the detection header from project_context.md.

    Returns None if the file is missing, empty, or contains only the
    default placeholder body.
    """
    path = get_project_context_path(project_path)
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None

    # Find the end of the detection header
    marker_idx = content.find(_DETECTION_HEADER_MARKER)
    if marker_idx < 0:
        return None

    # Skip past the marker line
    newline_idx = content.find("\n", marker_idx)
    if newline_idx < 0:
        return None

    body = content[newline_idx + 1 :]

    # Treat default placeholder as "no meaningful body"
    if body.strip() == _DEFAULT_BODY.strip():
        return None
    if not body.strip():
        return None

    return body


def write_project_context_preserving(
    project_path: Path,
    *,
    language: str | None = None,
    framework: str | None = None,
    test_runner: str | None = None,
    test_command: str | None = None,
) -> None:
    """Write the detection header, preserving any existing body content.

    If the file already has meaningful content below the header (e.g. from
    a prior ``levelup recon``), that content is re-appended after the
    updated detection header.  Otherwise the default placeholder is used.
    """
    existing_body = read_project_context_body(project_path)

    path = get_project_context_path(project_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        header_lines = [
            "# Project Context",
            "",
            f"- **Language:** {language or 'unknown'}",
            f"- **Framework:** {framework or 'none'}",
            f"- **Test runner:** {test_runner or 'unknown'}",
            f"- **Test command:** {test_command or 'unknown'}",
        ]
        header = "\n".join(header_lines) + "\n"

        if existing_body is not None:
            path.write_text(header + existing_body, encoding="utf-8")
        else:
            path.write_text(header + _DEFAULT_BODY, encoding="utf-8")
    except OSError:
        logger.warning("Failed to write project context: %s", path)
