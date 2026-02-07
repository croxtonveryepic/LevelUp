"""Tests for the instructions module (CLAUDE.md management)."""

from __future__ import annotations

from pathlib import Path

import pytest

from levelup.core.instructions import (
    add_instruction,
    build_instruct_review_prompt,
    get_claude_md_path,
    read_instructions,
    remove_instruction,
)


class TestGetClaudeMdPath:
    def test_returns_claude_md_in_project(self, tmp_path: Path):
        assert get_claude_md_path(tmp_path) == tmp_path / "CLAUDE.md"


class TestReadInstructions:
    def test_no_file(self, tmp_path: Path):
        assert read_instructions(tmp_path) == []

    def test_file_without_section(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text("# My Project\n\nSome text.\n")
        assert read_instructions(tmp_path) == []

    def test_empty_section(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text("## Project Rules\n\n")
        assert read_instructions(tmp_path) == []

    def test_single_rule(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text(
            "## Project Rules\n\n- Use type hints\n"
        )
        assert read_instructions(tmp_path) == ["Use type hints"]

    def test_multiple_rules(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text(
            "## Project Rules\n\n"
            "- Use type hints\n"
            "- No print() for logging\n"
            "- Keep functions under 50 lines\n"
        )
        rules = read_instructions(tmp_path)
        assert rules == [
            "Use type hints",
            "No print() for logging",
            "Keep functions under 50 lines",
        ]

    def test_rules_with_other_sections(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text(
            "# My Project\n\n"
            "## Dev Environment\n\nPython 3.13\n\n"
            "## Project Rules\n\n"
            "- Rule one\n"
            "- Rule two\n\n"
            "## Gotchas\n\nSome gotcha.\n"
        )
        assert read_instructions(tmp_path) == ["Rule one", "Rule two"]


class TestAddInstruction:
    def test_creates_file_when_missing(self, tmp_path: Path):
        add_instruction(tmp_path, "Use type hints")
        content = (tmp_path / "CLAUDE.md").read_text()
        assert "## Project Rules" in content
        assert "- Use type hints" in content

    def test_creates_section_when_missing(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text("# My Project\n\nExisting content.\n")
        add_instruction(tmp_path, "Use type hints")
        content = (tmp_path / "CLAUDE.md").read_text()
        assert "# My Project" in content
        assert "Existing content." in content
        assert "## Project Rules" in content
        assert "- Use type hints" in content

    def test_appends_to_existing_section(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text(
            "## Project Rules\n\n- Existing rule\n"
        )
        add_instruction(tmp_path, "New rule")
        rules = read_instructions(tmp_path)
        assert rules == ["Existing rule", "New rule"]

    def test_preserves_other_sections(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text(
            "# Title\n\n"
            "## Project Rules\n\n- Rule one\n\n"
            "## Gotchas\n\nDon't do this.\n"
        )
        add_instruction(tmp_path, "Rule two")
        content = (tmp_path / "CLAUDE.md").read_text()
        assert "# Title" in content
        assert "## Gotchas" in content
        assert "Don't do this." in content
        rules = read_instructions(tmp_path)
        assert "Rule one" in rules
        assert "Rule two" in rules

    def test_appends_to_section_at_end_of_file(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text(
            "## Project Rules\n\n- First rule\n"
        )
        add_instruction(tmp_path, "Second rule")
        add_instruction(tmp_path, "Third rule")
        rules = read_instructions(tmp_path)
        assert rules == ["First rule", "Second rule", "Third rule"]


class TestRemoveInstruction:
    def test_remove_first(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text(
            "## Project Rules\n\n- Rule A\n- Rule B\n"
        )
        removed = remove_instruction(tmp_path, 1)
        assert removed == "Rule A"
        assert read_instructions(tmp_path) == ["Rule B"]

    def test_remove_last(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text(
            "## Project Rules\n\n- Rule A\n- Rule B\n"
        )
        removed = remove_instruction(tmp_path, 2)
        assert removed == "Rule B"
        assert read_instructions(tmp_path) == ["Rule A"]

    def test_no_file_raises(self, tmp_path: Path):
        with pytest.raises(IndexError):
            remove_instruction(tmp_path, 1)

    def test_index_zero_raises(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text(
            "## Project Rules\n\n- Rule A\n"
        )
        with pytest.raises(IndexError):
            remove_instruction(tmp_path, 0)

    def test_index_too_high_raises(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text(
            "## Project Rules\n\n- Rule A\n"
        )
        with pytest.raises(IndexError):
            remove_instruction(tmp_path, 2)


class TestBuildInstructReviewPrompt:
    def test_includes_instruction_and_files(self):
        prompt = build_instruct_review_prompt(
            "Use type hints", ["src/foo.py", "src/bar.py"]
        )
        assert "Use type hints" in prompt
        assert "src/foo.py" in prompt
        assert "src/bar.py" in prompt
        assert "review" in prompt.lower()
