"""Tests for levelup self-update command."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import app

runner = CliRunner()


class TestSelfUpdateCommand:
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_successful_update(self, mock_run, mock_root, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path

        # git pull succeeds, pip install succeeds
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0
        assert "Updated:" in result.output

    @patch("levelup.cli.app._get_project_root")
    def test_not_a_git_repo(self, mock_root, tmp_path):
        mock_root.return_value = tmp_path  # no .git dir

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 1
        assert "Not a git repository" in result.output

    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_git_pull_failure(self, mock_run, mock_root, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path

        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="fatal: not a git repo"
        )

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 1
        assert "git pull failed" in result.output

    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_pip_install_failure(self, mock_run, mock_root, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path

        # git pull succeeds, pip install fails
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=1, stdout="", stderr="error: could not install"),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 1
        assert "pip install failed" in result.output
