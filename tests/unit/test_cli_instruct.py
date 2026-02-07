"""Tests for the standalone `levelup instruct` CLI command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from levelup.cli.app import app
from levelup.core.instructions import read_instructions

runner = CliRunner()


class TestInstructCLI:
    def test_add_rule(self, tmp_path: Path):
        result = runner.invoke(app, ["instruct", "add", "Use type hints", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "Added rule" in result.output
        assert read_instructions(tmp_path) == ["Use type hints"]

    def test_add_without_text_fails(self, tmp_path: Path):
        result = runner.invoke(app, ["instruct", "add", "--path", str(tmp_path)])
        assert result.exit_code != 0

    def test_list_empty(self, tmp_path: Path):
        result = runner.invoke(app, ["instruct", "list", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "No project rules" in result.output

    def test_list_with_rules(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text(
            "## Project Rules\n\n- Rule A\n- Rule B\n"
        )
        result = runner.invoke(app, ["instruct", "list", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "1. Rule A" in result.output
        assert "2. Rule B" in result.output

    def test_remove_rule(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text(
            "## Project Rules\n\n- Rule A\n- Rule B\n"
        )
        result = runner.invoke(app, ["instruct", "remove", "1", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "Removed rule #1" in result.output
        assert read_instructions(tmp_path) == ["Rule B"]

    def test_remove_invalid_index(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text(
            "## Project Rules\n\n- Rule A\n"
        )
        result = runner.invoke(app, ["instruct", "remove", "5", "--path", str(tmp_path)])
        assert result.exit_code != 0

    def test_remove_non_numeric_index(self, tmp_path: Path):
        result = runner.invoke(app, ["instruct", "remove", "abc", "--path", str(tmp_path)])
        assert result.exit_code != 0

    def test_unknown_action(self, tmp_path: Path):
        result = runner.invoke(app, ["instruct", "nope", "--path", str(tmp_path)])
        assert result.exit_code != 0

    def test_default_action_is_list(self, tmp_path: Path):
        result = runner.invoke(app, ["instruct", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "No project rules" in result.output
