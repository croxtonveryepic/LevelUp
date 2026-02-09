"""Tests for levelup self-update command."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import app

runner = CliRunner()


class TestSelfUpdateCommand:
    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_successful_update_editable(self, mock_run, mock_root, mock_save, mock_load, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_load.return_value = {"method": "editable", "source_path": str(tmp_path)}

        # git pull succeeds, pip install succeeds
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0
        assert "Updated:" in result.output
        mock_save.assert_called_once()

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_successful_update_global(self, mock_run, mock_root, mock_save, mock_load, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_load.return_value = {"method": "global", "source_path": str(tmp_path)}

        # git pull succeeds, uv tool install succeeds
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0
        assert "Updated:" in result.output

        # Check that uv tool install --force was called
        calls = mock_run.call_args_list
        assert len(calls) == 2
        install_cmd = calls[1][0][0]
        assert "uv" in install_cmd
        assert "tool" in install_cmd
        assert "install" in install_cmd
        assert "--force" in install_cmd

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_successful_update_global_with_gui(self, mock_run, mock_root, mock_save, mock_load, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_load.return_value = {
            "method": "global",
            "source_path": str(tmp_path),
            "extras": ["gui"],
        }

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0

        # Check that [gui] was appended to install target
        calls = mock_run.call_args_list
        install_cmd = calls[1][0][0]
        install_target = install_cmd[-1]  # last arg is the target
        assert "[gui]" in install_target

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._get_project_root")
    def test_not_a_git_repo(self, mock_root, mock_load, tmp_path):
        mock_root.return_value = tmp_path  # no .git dir
        mock_load.return_value = None  # no metadata, falls back to _get_project_root

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 1
        assert "No git repository" in result.output

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._get_project_root")
    def test_source_path_not_found(self, mock_root, mock_load, tmp_path):
        mock_load.return_value = {
            "method": "global",
            "source_path": str(tmp_path / "nonexistent"),
        }

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 1
        assert "Source directory not found" in result.output

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_git_pull_failure(self, mock_run, mock_root, mock_save, mock_load, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_load.return_value = None

        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="fatal: not a git repo"
        )

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 1
        assert "git pull failed" in result.output

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_pip_install_failure(self, mock_run, mock_root, mock_save, mock_load, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_load.return_value = {"method": "editable", "source_path": str(tmp_path)}

        # git pull succeeds, pip install fails
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=1, stdout="", stderr="error: could not install"),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 1
        assert "pip install failed" in result.output

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_fallback_without_metadata(self, mock_run, mock_root, mock_save, mock_load, tmp_path):
        """Without install.json, falls back to _get_project_root and editable mode."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_load.return_value = None  # no metadata

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0
        assert "Updated:" in result.output

        # Should have used editable install (pip install -e .)
        calls = mock_run.call_args_list
        install_cmd = calls[1][0][0]
        assert "-e" in install_cmd

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app.subprocess.run")
    def test_source_flag_overrides_metadata(self, mock_run, mock_save, mock_load, tmp_path):
        """The --source flag overrides the saved source_path."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_load.return_value = {
            "method": "editable",
            "source_path": "/old/path",
        }

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        result = runner.invoke(app, ["self-update", "--source", str(tmp_path)])
        assert result.exit_code == 0

        # Metadata should be updated with new source_path
        saved_meta = mock_save.call_args[0][0]
        assert saved_meta["source_path"] == str(tmp_path)

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_uv_tool_install_failure(self, mock_run, mock_root, mock_save, mock_load, tmp_path):
        """Global install failure shows uv tool install error."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_load.return_value = {"method": "global", "source_path": str(tmp_path)}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=1, stdout="", stderr="error: failed to install"),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 1
        assert "uv tool install failed" in result.output

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_self_update_gui_flag_global(self, mock_run, mock_root, mock_save, mock_load, tmp_path):
        """--gui flag adds [gui] to global install target."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_load.return_value = {"method": "global", "source_path": str(tmp_path)}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        result = runner.invoke(app, ["self-update", "--gui"])
        assert result.exit_code == 0

        # Check that [gui] was appended to install target
        calls = mock_run.call_args_list
        install_cmd = calls[1][0][0]
        install_target = install_cmd[-1]
        assert "[gui]" in install_target

        # Metadata should include gui extra
        saved_meta = mock_save.call_args[0][0]
        assert "gui" in saved_meta.get("extras", [])

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_self_update_gui_flag_editable(self, mock_run, mock_root, mock_save, mock_load, tmp_path):
        """--gui flag causes .[gui] in editable install."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_load.return_value = {"method": "editable", "source_path": str(tmp_path)}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        result = runner.invoke(app, ["self-update", "--gui"])
        assert result.exit_code == 0

        # Check that .[gui] was used in pip install -e
        calls = mock_run.call_args_list
        install_cmd = calls[1][0][0]
        assert "-e" in install_cmd
        # Find the spec after -e
        e_idx = install_cmd.index("-e")
        spec = install_cmd[e_idx + 1]
        assert ".[gui]" == spec

        # Metadata should include gui extra
        saved_meta = mock_save.call_args[0][0]
        assert "gui" in saved_meta.get("extras", [])

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_self_update_editable_preserves_gui_extra(self, mock_run, mock_root, mock_save, mock_load, tmp_path):
        """Existing gui extra in metadata is preserved in editable reinstall."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_load.return_value = {
            "method": "editable",
            "source_path": str(tmp_path),
            "extras": ["gui"],
        }

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0

        # Check that .[gui] was used (not just ".")
        calls = mock_run.call_args_list
        install_cmd = calls[1][0][0]
        e_idx = install_cmd.index("-e")
        spec = install_cmd[e_idx + 1]
        assert ".[gui]" == spec
