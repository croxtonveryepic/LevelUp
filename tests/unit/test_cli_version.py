"""Tests for levelup version command and get_version_string()."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from levelup import __version__
from levelup.cli.app import app
from levelup.cli.display import get_version_string

runner = CliRunner()


class TestGetVersionString:
    def test_includes_version_number(self):
        result = get_version_string()
        assert __version__ in result
        assert result.startswith("levelup ")

    @patch.dict("sys.modules", {"git": MagicMock()})
    def test_clean_repo(self):
        import sys

        mock_git = sys.modules["git"]
        mock_repo = MagicMock()
        mock_repo.head.commit.hexsha = "abc1234def5678"
        mock_repo.is_dirty.return_value = False
        mock_git.Repo.return_value = mock_repo

        result = get_version_string()
        assert "abc1234" in result
        assert "clean" in result

    @patch.dict("sys.modules", {"git": MagicMock()})
    def test_dirty_repo(self):
        import sys

        mock_git = sys.modules["git"]
        mock_repo = MagicMock()
        mock_repo.head.commit.hexsha = "abc1234def5678"
        mock_repo.is_dirty.return_value = True
        mock_git.Repo.return_value = mock_repo

        result = get_version_string()
        assert "abc1234" in result
        assert "dirty" in result

    def test_no_git_fallback(self):
        # Patch the import to raise ImportError
        with patch.dict("sys.modules", {"git": None}):
            result = get_version_string()
        assert result == f"levelup {__version__}"
        assert "commit" not in result


class TestVersionCommand:
    def test_version_command_exits_ok(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0

    def test_version_command_output(self):
        result = runner.invoke(app, ["version"])
        assert "levelup" in result.output
        assert __version__ in result.output
