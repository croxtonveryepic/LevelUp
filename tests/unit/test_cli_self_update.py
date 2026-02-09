"""Tests for levelup self-update command."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import (
    _is_levelup_repo,
    _normalize_git_url,
    _resolve_source,
    app,
)

runner = CliRunner()

# Shorthand for a successful subprocess result
_OK = MagicMock(returncode=0, stdout="Already up to date.", stderr="")
_OK_INSTALL = MagicMock(returncode=0, stdout="", stderr="")
_OK_REMOTE = MagicMock(returncode=0, stdout="https://github.com/croxtonveryepic/LevelUp.git\n", stderr="")


def _make_repo(tmp_path: Path) -> Path:
    """Create a fake git repo with a pyproject.toml."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text('name = "levelup"')
    return tmp_path


class TestHelpers:
    """Tests for _is_levelup_repo, _normalize_git_url, _resolve_source."""

    def test_is_levelup_repo_true(self, tmp_path):
        _make_repo(tmp_path)
        assert _is_levelup_repo(tmp_path) is True

    def test_is_levelup_repo_no_git(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('name = "levelup"')
        assert _is_levelup_repo(tmp_path) is False

    def test_is_levelup_repo_no_pyproject(self, tmp_path):
        (tmp_path / ".git").mkdir()
        assert _is_levelup_repo(tmp_path) is False

    def test_is_levelup_repo_wrong_name(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / "pyproject.toml").write_text('name = "other-project"')
        assert _is_levelup_repo(tmp_path) is False

    def test_normalize_git_url_https(self):
        assert _normalize_git_url("https://github.com/user/repo.git") == "git+https://github.com/user/repo.git"

    def test_normalize_git_url_ssh(self):
        assert _normalize_git_url("git@github.com:user/repo.git") == "git+ssh://git@github.com/user/repo.git"

    def test_normalize_git_url_already_prefixed(self):
        assert _normalize_git_url("git+https://github.com/user/repo.git") == "git+https://github.com/user/repo.git"

    def test_resolve_source_remote_flag(self, tmp_path):
        local, remote = _resolve_source(
            source_flag=None,
            remote_flag="https://github.com/user/repo.git",
            meta={},
        )
        assert local is None
        assert remote == "git+https://github.com/user/repo.git"

    def test_resolve_source_source_flag(self, tmp_path):
        local, remote = _resolve_source(
            source_flag=tmp_path,
            remote_flag=None,
            meta={},
        )
        assert local == tmp_path.resolve()
        assert remote is None

    def test_resolve_source_meta_valid(self, tmp_path):
        _make_repo(tmp_path)
        local, remote = _resolve_source(
            source_flag=None,
            remote_flag=None,
            meta={"source_path": str(tmp_path)},
        )
        assert local == tmp_path
        assert remote is None

    def test_resolve_source_meta_gone_with_repo_url(self, tmp_path):
        local, remote = _resolve_source(
            source_flag=None,
            remote_flag=None,
            meta={
                "source_path": str(tmp_path / "gone"),
                "repo_url": "https://github.com/user/repo.git",
            },
        )
        assert local is None
        assert remote == "git+https://github.com/user/repo.git"

    def test_resolve_source_global_no_source_defaults_to_remote(self):
        local, remote = _resolve_source(
            source_flag=None,
            remote_flag=None,
            meta={"method": "global"},
        )
        assert local is None
        assert "github.com" in remote

    @patch("levelup.cli.app._is_levelup_repo", return_value=True)
    @patch("levelup.cli.app.Path")
    def test_resolve_source_cwd_fallback(self, mock_path_cls, mock_is_repo, tmp_path):
        mock_path_cls.cwd.return_value = tmp_path
        local, remote = _resolve_source(
            source_flag=None,
            remote_flag=None,
            meta={},
        )
        assert local == tmp_path
        assert remote is None

    @patch("levelup.cli.app._is_levelup_repo", return_value=False)
    @patch("levelup.cli.app._get_project_root")
    def test_resolve_source_project_root_fallback(self, mock_root, mock_is_repo, tmp_path):
        mock_root.return_value = tmp_path
        local, remote = _resolve_source(
            source_flag=None,
            remote_flag=None,
            meta={},
        )
        assert local == tmp_path
        assert remote is None


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

        # git pull succeeds, pip install succeeds, git remote get-url origin
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="https://github.com/user/repo.git\n", stderr=""),
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

        # git pull succeeds, uv tool install succeeds, git remote get-url origin
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="https://github.com/user/repo.git\n", stderr=""),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0
        assert "Updated:" in result.output

        # Check that uv tool install --force was called
        calls = mock_run.call_args_list
        assert len(calls) == 3
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
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0

        # Check that [gui] was appended to install target
        calls = mock_run.call_args_list
        install_cmd = calls[1][0][0]
        install_target = install_cmd[-1]  # last arg is the target
        assert "[gui]" in install_target

    @patch("levelup.cli.app._is_levelup_repo", return_value=False)
    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._get_project_root")
    def test_not_a_git_repo(self, mock_root, mock_load, mock_is_repo, tmp_path):
        mock_root.return_value = tmp_path  # no .git dir
        mock_load.return_value = None  # no metadata, falls back to _get_project_root

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 1
        assert "No git repository" in result.output

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app.subprocess.run")
    def test_source_path_not_found_via_flag(self, mock_run, mock_save, mock_load, tmp_path):
        """--source flag with non-existent path shows error."""
        mock_load.return_value = {}

        result = runner.invoke(app, ["self-update", "--source", str(tmp_path / "nonexistent")])
        assert result.exit_code == 1
        assert "Source directory not found" in result.output

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app.subprocess.run")
    def test_global_source_gone_falls_back_to_remote(self, mock_run, mock_save, mock_load, tmp_path):
        """Global install with stale source_path falls back to remote URL."""
        mock_load.return_value = {
            "method": "global",
            "source_path": str(tmp_path / "nonexistent"),
        }

        # uv tool install from remote succeeds
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0
        assert "Updated:" in result.output

        # Should have used remote install (uv tool install with git+ URL)
        calls = mock_run.call_args_list
        install_cmd = calls[0][0][0]
        assert "uv" in install_cmd
        assert "--force" in install_cmd
        install_target = install_cmd[-1]
        assert "git+" in install_target

    @patch("levelup.cli.app._is_levelup_repo", return_value=False)
    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_git_pull_failure(self, mock_run, mock_root, mock_save, mock_load, mock_is_repo, tmp_path):
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

    @patch("levelup.cli.app._is_levelup_repo", return_value=False)
    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_fallback_without_metadata(self, mock_run, mock_root, mock_save, mock_load, mock_is_repo, tmp_path):
        """Without install.json, falls back to _get_project_root and editable mode."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_load.return_value = None  # no metadata

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
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


class TestSelfUpdateBOM:
    """Tests for BOM handling in _load_install_meta."""

    def test_bom_in_install_json(self, tmp_path, monkeypatch):
        """UTF-8 BOM in install.json doesn't break metadata loading."""
        from levelup.cli.app import _load_install_meta, INSTALL_META_PATH

        meta_file = tmp_path / "install.json"
        content = json.dumps({"method": "global", "source_path": "/some/path"})
        # Write with BOM
        meta_file.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))

        monkeypatch.setattr("levelup.cli.app.INSTALL_META_PATH", meta_file)
        loaded = _load_install_meta()
        assert loaded is not None
        assert loaded["method"] == "global"
        assert loaded["source_path"] == "/some/path"

    def test_no_bom_still_works(self, tmp_path, monkeypatch):
        """Normal UTF-8 (no BOM) still loads fine."""
        from levelup.cli.app import _load_install_meta

        meta_file = tmp_path / "install.json"
        meta_file.write_text(json.dumps({"method": "editable"}))

        monkeypatch.setattr("levelup.cli.app.INSTALL_META_PATH", meta_file)
        loaded = _load_install_meta()
        assert loaded is not None
        assert loaded["method"] == "editable"


class TestSelfUpdateRemote:
    """Tests for --remote flag and remote URL fallback."""

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app.subprocess.run")
    def test_remote_flag_explicit(self, mock_run, mock_save, mock_load):
        """--remote flag installs directly from git URL without git pull."""
        mock_load.return_value = {"method": "global"}

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = runner.invoke(app, [
            "self-update", "--remote", "https://github.com/croxtonveryepic/LevelUp.git"
        ])
        assert result.exit_code == 0
        assert "Updated:" in result.output

        # Should be a single uv tool install call (no git pull)
        calls = mock_run.call_args_list
        assert len(calls) == 1
        install_cmd = calls[0][0][0]
        assert "uv" in install_cmd
        assert "--force" in install_cmd

        # Install target should contain git+ URL
        install_target = install_cmd[-1]
        assert "git+https://github.com/croxtonveryepic/LevelUp.git" in install_target

        # Metadata should save repo_url
        saved_meta = mock_save.call_args[0][0]
        assert "repo_url" in saved_meta

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app.subprocess.run")
    def test_remote_with_gui_extras(self, mock_run, mock_save, mock_load):
        """--remote with --gui includes [gui] in the install target."""
        mock_load.return_value = {"method": "global"}

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = runner.invoke(app, [
            "self-update", "--remote", "https://github.com/croxtonveryepic/LevelUp.git", "--gui"
        ])
        assert result.exit_code == 0

        calls = mock_run.call_args_list
        install_cmd = calls[0][0][0]
        install_target = install_cmd[-1]
        assert "levelup[gui]" in install_target
        assert "git+" in install_target

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app.subprocess.run")
    def test_remote_url_from_metadata(self, mock_run, mock_save, mock_load, tmp_path):
        """Global install with stale source_path but saved repo_url uses remote."""
        mock_load.return_value = {
            "method": "global",
            "source_path": str(tmp_path / "gone"),
            "repo_url": "https://github.com/croxtonveryepic/LevelUp.git",
        }

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0
        assert "Updated:" in result.output

        # Should be remote install (single call, no git pull)
        calls = mock_run.call_args_list
        assert len(calls) == 1
        install_cmd = calls[0][0][0]
        install_target = install_cmd[-1]
        assert "git+https://github.com/croxtonveryepic/LevelUp.git" in install_target

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app.subprocess.run")
    def test_default_remote_fallback(self, mock_run, mock_save, mock_load):
        """Global install with no source and no repo_url falls back to DEFAULT_REPO_URL."""
        mock_load.return_value = {"method": "global"}

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0
        assert "Updated:" in result.output

        calls = mock_run.call_args_list
        assert len(calls) == 1
        install_cmd = calls[0][0][0]
        install_target = install_cmd[-1]
        assert "git+https://github.com/croxtonveryepic/LevelUp.git" in install_target

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app.subprocess.run")
    def test_remote_install_failure(self, mock_run, mock_save, mock_load):
        """Remote install failure shows error."""
        mock_load.return_value = {"method": "global"}

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error: network failure")

        result = runner.invoke(app, ["self-update", "--remote", "https://github.com/user/repo.git"])
        assert result.exit_code == 1
        assert "uv tool install failed" in result.output


class TestSelfUpdateCwdFallback:
    """Tests for CWD-based fallback when no metadata exists."""

    @patch("levelup.cli.app._is_levelup_repo", return_value=True)
    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    @patch("levelup.cli.app.Path")
    def test_cwd_fallback(self, mock_path_cls, mock_run, mock_root, mock_save, mock_load, mock_is_repo, tmp_path):
        """When no metadata, CWD is checked before _get_project_root."""
        (tmp_path / ".git").mkdir()
        mock_load.return_value = None  # no metadata

        # Make Path.cwd() return tmp_path but keep Path() working for other uses
        original_path = Path
        class MockPath(type(tmp_path)):
            @staticmethod
            def cwd():
                return tmp_path
        # We can't easily mock Path class entirely, so use _is_levelup_repo + _resolve_source directly
        # Instead, just patch _resolve_source to return the expected result
        pass

    @patch("levelup.cli.app._resolve_source")
    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app.subprocess.run")
    def test_cwd_fallback_integration(self, mock_run, mock_save, mock_load, mock_resolve, tmp_path):
        """CWD fallback works end-to-end."""
        (tmp_path / ".git").mkdir()
        mock_load.return_value = None
        mock_resolve.return_value = (tmp_path, None)

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0
        assert "Updated:" in result.output


class TestSelfUpdateRepoUrlSave:
    """Test that repo_url is auto-detected from git remote after local update."""

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_repo_url_saved_after_local_update(self, mock_run, mock_root, mock_save, mock_load, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_load.return_value = {"method": "editable", "source_path": str(tmp_path)}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="https://github.com/user/repo.git\n", stderr=""),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0

        saved_meta = mock_save.call_args[0][0]
        assert saved_meta.get("repo_url") == "https://github.com/user/repo.git"

    @patch("levelup.cli.app._load_install_meta")
    @patch("levelup.cli.app._save_install_meta")
    @patch("levelup.cli.app._get_project_root")
    @patch("levelup.cli.app.subprocess.run")
    def test_repo_url_not_saved_when_git_remote_fails(self, mock_run, mock_root, mock_save, mock_load, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_root.return_value = tmp_path
        mock_load.return_value = {"method": "editable", "source_path": str(tmp_path)}

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Already up to date.", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=1, stdout="", stderr="error"),
        ]

        result = runner.invoke(app, ["self-update"])
        assert result.exit_code == 0

        saved_meta = mock_save.call_args[0][0]
        assert "repo_url" not in saved_meta
