"""Tests for step-level git commit feature (_git_step_commit and _create_git_branch)."""

from __future__ import annotations

import json
from pathlib import Path

import git
import pytest

from levelup.config.settings import LevelUpSettings, LLMSettings, PipelineSettings, ProjectSettings
from levelup.core.context import PipelineContext, PipelineStatus, TaskInput
from levelup.core.orchestrator import Orchestrator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_git_repo(tmp_path: Path) -> git.Repo:
    """Create a git repo with an initial commit and return the Repo object."""
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    (tmp_path / "init.txt").write_text("init")
    repo.index.add(["init.txt"])
    repo.index.commit("initial commit")
    return repo


def _make_settings(tmp_path: Path, create_git_branch: bool = True) -> LevelUpSettings:
    """Build LevelUpSettings pointing at *tmp_path*."""
    return LevelUpSettings(
        llm=LLMSettings(api_key="test-key", model="test-model", backend="claude_code"),
        project=ProjectSettings(path=tmp_path),
        pipeline=PipelineSettings(
            create_git_branch=create_git_branch,
            require_checkpoints=False,
        ),
    )


def _make_context(tmp_path: Path, pre_run_sha: str | None = "abc123") -> PipelineContext:
    """Build a minimal PipelineContext with controllable pre_run_sha."""
    return PipelineContext(
        task=TaskInput(title="Add widget feature", description="Implement widget"),
        project_path=tmp_path,
        status=PipelineStatus.RUNNING,
        pre_run_sha=pre_run_sha,
    )


# ---------------------------------------------------------------------------
# _git_step_commit tests
# ---------------------------------------------------------------------------


class TestGitStepCommit:
    """Tests for Orchestrator._git_step_commit()."""

    def test_creates_commit_when_changes_exist(self, tmp_path):
        """A commit is created when there are staged changes."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)
        ctx = _make_context(tmp_path, pre_run_sha=repo.head.commit.hexsha)

        # Create a file change in the repo
        (tmp_path / "new_file.py").write_text("print('hello')")

        orch._git_step_commit(tmp_path, ctx, "requirements")

        # Assert the last commit message starts with the expected prefix
        last_commit = repo.head.commit
        assert last_commit.message.startswith("levelup(requirements):")
        assert "Add widget feature" in last_commit.message
        assert f"Run ID: {ctx.run_id}" in last_commit.message

        # Assert step_commits was populated
        assert "requirements" in ctx.step_commits
        assert ctx.step_commits["requirements"] == last_commit.hexsha

    def test_noop_when_no_changes(self, tmp_path):
        """No commit is created when there are no file changes."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)
        ctx = _make_context(tmp_path, pre_run_sha=repo.head.commit.hexsha)

        initial_sha = repo.head.commit.hexsha

        orch._git_step_commit(tmp_path, ctx, "requirements")

        # HEAD should not have changed
        assert repo.head.commit.hexsha == initial_sha
        assert "requirements" not in ctx.step_commits

    def test_noop_when_create_git_branch_false(self, tmp_path):
        """No commit is created when create_git_branch is False, even with changes."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)
        ctx = _make_context(tmp_path, pre_run_sha=repo.head.commit.hexsha)

        # Create a file change
        (tmp_path / "change.txt").write_text("something")

        initial_sha = repo.head.commit.hexsha

        orch._git_step_commit(tmp_path, ctx, "requirements")

        # Nothing should have been committed
        assert repo.head.commit.hexsha == initial_sha
        assert ctx.step_commits == {}

    def test_noop_when_pre_run_sha_none(self, tmp_path):
        """No commit is created when pre_run_sha is None, even with changes and branch enabled."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)
        ctx = _make_context(tmp_path, pre_run_sha=None)

        # Create a file change
        (tmp_path / "change.txt").write_text("something")

        initial_sha = repo.head.commit.hexsha

        orch._git_step_commit(tmp_path, ctx, "requirements")

        # Nothing should have been committed
        assert repo.head.commit.hexsha == initial_sha
        assert ctx.step_commits == {}

    def test_revised_commit_includes_revised_suffix(self, tmp_path):
        """When revised=True, the commit message includes ', revised'."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)
        ctx = _make_context(tmp_path, pre_run_sha=repo.head.commit.hexsha)

        # Create a file change
        (tmp_path / "revised_file.py").write_text("revised content")

        orch._git_step_commit(tmp_path, ctx, "requirements", revised=True)

        last_commit = repo.head.commit
        assert "revised" in last_commit.message
        assert last_commit.message.startswith("levelup(requirements, revised):")
        assert "Add widget feature" in last_commit.message
        assert f"Run ID: {ctx.run_id}" in last_commit.message

        # step_commits should be populated
        assert "requirements" in ctx.step_commits
        assert ctx.step_commits["requirements"] == last_commit.hexsha


# ---------------------------------------------------------------------------
# _create_git_branch tests
# ---------------------------------------------------------------------------


class TestCreateGitBranch:
    """Tests for Orchestrator._create_git_branch()."""

    def test_returns_pre_run_sha(self, tmp_path):
        """_create_git_branch returns the SHA of HEAD before branching."""
        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        run_id = "abc123def456"
        returned_sha = orch._create_git_branch(tmp_path, run_id)

        assert returned_sha == initial_sha
        # The repo should now be on the new branch
        assert repo.active_branch.name == f"levelup/{run_id}"


# ---------------------------------------------------------------------------
# Context fields (pre_run_sha, step_commits)
# ---------------------------------------------------------------------------


class TestContextGitFields:
    """Tests for git-related fields on PipelineContext."""

    def test_defaults(self):
        """pre_run_sha defaults to None, step_commits defaults to empty dict."""
        ctx = PipelineContext(task=TaskInput(title="t"))
        assert ctx.pre_run_sha is None
        assert ctx.step_commits == {}

    def test_set_and_read(self):
        """Values can be set and read back."""
        ctx = PipelineContext(task=TaskInput(title="t"))
        ctx.pre_run_sha = "deadbeef1234"
        ctx.step_commits["requirements"] = "cafebabe5678"

        assert ctx.pre_run_sha == "deadbeef1234"
        assert ctx.step_commits["requirements"] == "cafebabe5678"

    def test_serialization_round_trip(self):
        """pre_run_sha and step_commits survive JSON serialization."""
        ctx = PipelineContext(
            task=TaskInput(title="t"),
            pre_run_sha="deadbeef1234",
            step_commits={"requirements": "sha1", "planning": "sha2"},
        )

        json_str = ctx.model_dump_json()
        data = json.loads(json_str)
        restored = PipelineContext(**data)

        assert restored.pre_run_sha == "deadbeef1234"
        assert restored.step_commits == {"requirements": "sha1", "planning": "sha2"}
