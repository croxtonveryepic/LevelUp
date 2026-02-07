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
