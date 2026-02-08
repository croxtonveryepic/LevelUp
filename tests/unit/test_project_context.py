"""Unit tests for src/levelup/core/project_context.py."""

from __future__ import annotations

from pathlib import Path

from levelup.core.project_context import (
    get_project_context_path,
    read_project_context_body,
    write_project_context,
    write_project_context_preserving,
)


class TestGetProjectContextPath:
    def test_returns_expected_path(self, tmp_path: Path):
        result = get_project_context_path(tmp_path)
        expected = tmp_path / "levelup" / "project_context.md"
        assert result == expected


class TestWriteProjectContext:
    def test_creates_file_with_all_fields(self, tmp_path: Path):
        write_project_context(
            tmp_path,
            language="Python",
            framework="FastAPI",
            test_runner="pytest",
            test_command="pytest tests/ -v",
        )

        path = get_project_context_path(tmp_path)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "# Project Context" in content
        assert "**Language:** Python" in content
        assert "**Framework:** FastAPI" in content
        assert "**Test runner:** pytest" in content
        assert "**Test command:** pytest tests/ -v" in content
        assert "## Codebase Insights" in content

    def test_creates_levelup_directory(self, tmp_path: Path):
        write_project_context(tmp_path, language="Go")
        assert (tmp_path / "levelup").is_dir()

    def test_overwrites_existing_file(self, tmp_path: Path):
        write_project_context(tmp_path, language="Python")
        write_project_context(tmp_path, language="Go")

        content = get_project_context_path(tmp_path).read_text(encoding="utf-8")
        assert "**Language:** Go" in content
        assert "Python" not in content

    def test_defaults_for_none_values(self, tmp_path: Path):
        write_project_context(tmp_path)

        content = get_project_context_path(tmp_path).read_text(encoding="utf-8")
        assert "**Language:** unknown" in content
        assert "**Framework:** none" in content
        assert "**Test runner:** unknown" in content
        assert "**Test command:** unknown" in content

    def test_handles_missing_parent_dir(self, tmp_path: Path):
        nested = tmp_path / "deep" / "nested" / "project"
        nested.mkdir(parents=True)
        write_project_context(nested, language="Rust")

        path = get_project_context_path(nested)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "**Language:** Rust" in content


class TestReadProjectContextBody:
    def test_returns_none_when_file_missing(self, tmp_path: Path):
        assert read_project_context_body(tmp_path) is None

    def test_returns_none_for_default_placeholder(self, tmp_path: Path):
        write_project_context(tmp_path, language="Python")
        assert read_project_context_body(tmp_path) is None

    def test_returns_body_after_recon(self, tmp_path: Path):
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n"
            "\n## Directory Structure\n\nSome deep analysis here.\n",
            encoding="utf-8",
        )
        body = read_project_context_body(tmp_path)
        assert body is not None
        assert "## Directory Structure" in body
        assert "Some deep analysis here." in body

    def test_returns_none_for_empty_body(self, tmp_path: Path):
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n",
            encoding="utf-8",
        )
        assert read_project_context_body(tmp_path) is None


class TestWriteProjectContextPreserving:
    def test_preserves_existing_body(self, tmp_path: Path):
        # Write recon-style content
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** Django\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n"
            "\n## Architecture\n\nLayered architecture with services.\n",
            encoding="utf-8",
        )

        # Now call preserving write with updated detection
        write_project_context_preserving(
            tmp_path,
            language="Python",
            framework="FastAPI",  # changed
            test_runner="pytest",
            test_command="pytest -v",  # changed
        )

        content = path.read_text(encoding="utf-8")
        # Header should be updated
        assert "**Framework:** FastAPI" in content
        assert "**Test command:** pytest -v" in content
        # Body should be preserved
        assert "## Architecture" in content
        assert "Layered architecture with services." in content

    def test_writes_default_when_no_existing_body(self, tmp_path: Path):
        write_project_context_preserving(tmp_path, language="Go")

        content = get_project_context_path(tmp_path).read_text(encoding="utf-8")
        assert "**Language:** Go" in content
        assert "## Codebase Insights" in content
        assert "(Agents append discoveries here)" in content

    def test_writes_default_when_only_placeholder_body(self, tmp_path: Path):
        # First write the default
        write_project_context(tmp_path, language="Python")
        # Then call preserving write
        write_project_context_preserving(tmp_path, language="Go")

        content = get_project_context_path(tmp_path).read_text(encoding="utf-8")
        assert "**Language:** Go" in content
        assert "## Codebase Insights" in content

    def test_creates_levelup_directory(self, tmp_path: Path):
        nested = tmp_path / "deep" / "project"
        nested.mkdir(parents=True)
        write_project_context_preserving(nested, language="Rust")
        assert (nested / "levelup").is_dir()
        assert get_project_context_path(nested).exists()
