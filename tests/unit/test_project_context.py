"""Unit tests for src/levelup/core/project_context.py."""

from __future__ import annotations

from pathlib import Path

from levelup.core.project_context import get_project_context_path, write_project_context


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
