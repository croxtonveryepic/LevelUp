"""Unit tests for branch naming convention feature."""

from __future__ import annotations

from pathlib import Path

import pytest

from levelup.core.project_context import (
    get_project_context_path,
    read_project_context_header,
    write_project_context,
    write_project_context_preserving,
)


class TestReadProjectContextHeader:
    """Tests for read_project_context_header() function."""

    def test_returns_none_when_file_missing(self, tmp_path: Path):
        """Returns None when project_context.md doesn't exist."""
        result = read_project_context_header(tmp_path)
        assert result is None

    def test_reads_all_header_fields(self, tmp_path: Path):
        """Reads language, framework, test_runner, test_command from header."""
        write_project_context(
            tmp_path,
            language="Python",
            framework="FastAPI",
            test_runner="pytest",
            test_command="pytest tests/ -v",
        )

        header = read_project_context_header(tmp_path)
        assert header is not None
        assert header["language"] == "Python"
        assert header["framework"] == "FastAPI"
        assert header["test_runner"] == "pytest"
        assert header["test_command"] == "pytest tests/ -v"

    def test_returns_none_for_branch_naming_when_missing(self, tmp_path: Path):
        """Returns None for branch_naming field when not present in file."""
        write_project_context(tmp_path, language="Python")

        header = read_project_context_header(tmp_path)
        assert header is not None
        assert header.get("branch_naming") is None

    def test_reads_branch_naming_when_present(self, tmp_path: Path):
        """Reads branch_naming field from header when present."""
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n"
            "- **Branch naming:** feature/{task_title}\n"
            "\n## Codebase Insights\n",
            encoding="utf-8",
        )

        header = read_project_context_header(tmp_path)
        assert header is not None
        assert header["branch_naming"] == "feature/{task_title}"

    def test_handles_malformed_header_gracefully(self, tmp_path: Path):
        """Returns None for malformed header content."""
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Some random content without header format", encoding="utf-8")

        # Should not crash, should return None or empty dict
        header = read_project_context_header(tmp_path)
        # Acceptable outcomes: None or dict with missing keys
        if header is not None:
            assert header.get("language") is None

    def test_handles_custom_branch_naming_patterns(self, tmp_path: Path):
        """Reads various branch naming patterns correctly."""
        test_cases = [
            "levelup/{run_id}",
            "ai/{date}-{run_id}",
            "feature/{task_title}",
            "dev/{run_id}/{task_title}",
            "custom-prefix-{run_id}",
        ]

        for pattern in test_cases:
            path = get_project_context_path(tmp_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# Project Context\n\n"
                "- **Language:** Python\n"
                "- **Framework:** none\n"
                "- **Test runner:** pytest\n"
                "- **Test command:** pytest\n"
                f"- **Branch naming:** {pattern}\n",
                encoding="utf-8",
            )

            header = read_project_context_header(tmp_path)
            assert header is not None
            assert header["branch_naming"] == pattern


class TestWriteProjectContextWithBranchNaming:
    """Tests for write_project_context() with branch_naming parameter."""

    def test_writes_branch_naming_field(self, tmp_path: Path):
        """write_project_context() accepts and writes branch_naming parameter."""
        write_project_context(
            tmp_path,
            language="Python",
            framework="none",
            test_runner="pytest",
            test_command="pytest",
            branch_naming="feature/{task_title}",
        )

        path = get_project_context_path(tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "**Branch naming:** feature/{task_title}" in content

    def test_branch_naming_appears_after_test_command(self, tmp_path: Path):
        """Branch naming field appears after test_command in header."""
        write_project_context(
            tmp_path,
            language="Python",
            test_command="pytest",
            branch_naming="levelup/{run_id}",
        )

        content = get_project_context_path(tmp_path).read_text(encoding="utf-8")
        lines = content.split("\n")

        test_cmd_idx = next(i for i, line in enumerate(lines) if "Test command" in line)
        branch_naming_idx = next(
            i for i, line in enumerate(lines) if "Branch naming" in line
        )

        assert branch_naming_idx > test_cmd_idx

    def test_defaults_to_levelup_run_id_when_none(self, tmp_path: Path):
        """Defaults to 'levelup/{run_id}' when branch_naming is None."""
        write_project_context(tmp_path, language="Python", branch_naming=None)

        content = get_project_context_path(tmp_path).read_text(encoding="utf-8")
        assert "**Branch naming:** levelup/{run_id}" in content

    def test_accepts_custom_patterns(self, tmp_path: Path):
        """Accepts and stores various custom branch naming patterns."""
        patterns = [
            "ai/{run_id}",
            "feature/{task_title}",
            "dev/{date}-{run_id}",
            "custom/{run_id}/{task_title}",
        ]

        for pattern in patterns:
            write_project_context(tmp_path, language="Python", branch_naming=pattern)
            content = get_project_context_path(tmp_path).read_text(encoding="utf-8")
            assert f"**Branch naming:** {pattern}" in content


class TestWriteProjectContextPreservingWithBranchNaming:
    """Tests for write_project_context_preserving() with branch_naming parameter."""

    def test_writes_branch_naming_field(self, tmp_path: Path):
        """write_project_context_preserving() accepts and writes branch_naming."""
        write_project_context_preserving(
            tmp_path,
            language="Python",
            test_runner="pytest",
            test_command="pytest",
            branch_naming="feature/{task_title}",
        )

        content = get_project_context_path(tmp_path).read_text(encoding="utf-8")
        assert "**Branch naming:** feature/{task_title}" in content

    def test_preserves_existing_body_with_branch_naming(self, tmp_path: Path):
        """Preserves existing body when updating header with branch_naming."""
        # Write initial content with recon data
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** Django\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n"
            "\n## Architecture\n\nLayered architecture.\n",
            encoding="utf-8",
        )

        # Update with new branch naming
        write_project_context_preserving(
            tmp_path,
            language="Python",
            framework="FastAPI",
            test_runner="pytest",
            test_command="pytest -v",
            branch_naming="ai/{run_id}",
        )

        content = path.read_text(encoding="utf-8")
        # Header should be updated
        assert "**Framework:** FastAPI" in content
        assert "**Branch naming:** ai/{run_id}" in content
        # Body should be preserved
        assert "## Architecture" in content
        assert "Layered architecture." in content

    def test_updates_branch_naming_preserving_body(self, tmp_path: Path):
        """Updates branch_naming field while preserving body content."""
        # Write initial with one convention
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n"
            "- **Branch naming:** levelup/{run_id}\n"
            "\n## Deep Analysis\n\nSome recon data.\n",
            encoding="utf-8",
        )

        # Update to different convention
        write_project_context_preserving(
            tmp_path,
            language="Python",
            framework="none",
            test_runner="pytest",
            test_command="pytest",
            branch_naming="feature/{task_title}",
        )

        content = path.read_text(encoding="utf-8")
        assert "**Branch naming:** feature/{task_title}" in content
        assert "## Deep Analysis" in content
        assert "Some recon data." in content
        # Old convention should not be present
        assert content.count("Branch naming") == 1

    def test_defaults_to_levelup_run_id_when_none(self, tmp_path: Path):
        """Defaults to 'levelup/{run_id}' when branch_naming is None."""
        write_project_context_preserving(tmp_path, language="Go", branch_naming=None)

        content = get_project_context_path(tmp_path).read_text(encoding="utf-8")
        assert "**Branch naming:** levelup/{run_id}" in content


class TestBranchNamingBackwardCompatibility:
    """Tests for backward compatibility when branch_naming field is missing."""

    def test_read_header_without_branch_naming_returns_none(self, tmp_path: Path):
        """Old project_context.md without branch_naming field returns None for that field."""
        # Simulate old format without branch_naming
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n"
            "\n## Codebase Insights\n",
            encoding="utf-8",
        )

        header = read_project_context_header(tmp_path)
        assert header is not None
        assert header["language"] == "Python"
        assert header.get("branch_naming") is None

    def test_preserving_write_adds_branch_naming_to_old_format(self, tmp_path: Path):
        """write_project_context_preserving adds branch_naming to old format files."""
        # Create old format
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n"
            "\n## Recon Data\n\nExisting content.\n",
            encoding="utf-8",
        )

        # Update with branch_naming
        write_project_context_preserving(
            tmp_path,
            language="Python",
            framework="none",
            test_runner="pytest",
            test_command="pytest",
            branch_naming="ai/{run_id}",
        )

        content = path.read_text(encoding="utf-8")
        assert "**Branch naming:** ai/{run_id}" in content
        assert "## Recon Data" in content
        assert "Existing content." in content
