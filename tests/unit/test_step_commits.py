"""Tests for step-level git commit feature (_git_step_commit and _create_git_branch)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

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


def _make_context(tmp_path: Path, pre_run_sha: str | None = "abc123", **kwargs) -> PipelineContext:
    """Build a minimal PipelineContext with controllable pre_run_sha."""
    return PipelineContext(
        task=TaskInput(title="Add widget feature", description="Implement widget"),
        project_path=tmp_path,
        status=PipelineStatus.RUNNING,
        pre_run_sha=pre_run_sha,
        **kwargs,
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
# _create_git_branch tests (now creates worktrees)
# ---------------------------------------------------------------------------


class TestCreateGitBranch:
    """Tests for Orchestrator._create_git_branch() — worktree-based."""

    def test_returns_pre_run_sha(self, tmp_path):
        """_create_git_branch returns the SHA of HEAD before branching."""
        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, pre_run_sha=None)
        returned_sha = orch._create_git_branch(tmp_path, ctx)

        assert returned_sha == initial_sha
        assert ctx.pre_run_sha == initial_sha

    def test_worktree_created_at_expected_path(self, tmp_path):
        """Worktree is created at ~/.levelup/worktrees/<run_id>/."""
        repo = _init_git_repo(tmp_path)

        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, pre_run_sha=None)
        orch._create_git_branch(tmp_path, ctx)

        expected_path = Path.home() / ".levelup" / "worktrees" / ctx.run_id
        assert ctx.worktree_path == expected_path
        assert ctx.worktree_path.exists()

        # Cleanup
        repo.git.worktree("remove", str(ctx.worktree_path), "--force")

    def test_worktree_branch_matches_convention(self, tmp_path):
        """The branch in the worktree matches the naming convention."""
        repo = _init_git_repo(tmp_path)

        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, pre_run_sha=None)
        orch._create_git_branch(tmp_path, ctx)

        # The worktree should be on the levelup/<run_id> branch
        wt_repo = git.Repo(ctx.worktree_path)
        assert wt_repo.active_branch.name == f"levelup/{ctx.run_id}"

        # Cleanup
        repo.git.worktree("remove", str(ctx.worktree_path), "--force")

    def test_original_repo_branch_unchanged(self, tmp_path):
        """After worktree creation, main repo stays on its original branch."""
        repo = _init_git_repo(tmp_path)
        original_branch = repo.active_branch.name

        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, pre_run_sha=None)
        orch._create_git_branch(tmp_path, ctx)

        # Main repo should NOT have switched branches
        assert repo.active_branch.name == original_branch

        # Cleanup
        repo.git.worktree("remove", str(ctx.worktree_path), "--force")

    def test_cleanup_removes_worktree(self, tmp_path):
        """_cleanup_worktree removes the worktree directory."""
        repo = _init_git_repo(tmp_path)

        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, pre_run_sha=None)
        orch._create_git_branch(tmp_path, ctx)

        assert ctx.worktree_path.exists()

        orch._cleanup_worktree(tmp_path, ctx)

        assert not ctx.worktree_path.exists()

    def test_cleanup_noop_when_no_worktree(self, tmp_path):
        """_cleanup_worktree does nothing when worktree_path is None."""
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, pre_run_sha=None)
        # worktree_path is None
        orch._cleanup_worktree(tmp_path, ctx)  # should not raise

    def test_noop_when_create_git_branch_false(self, tmp_path):
        """_create_git_branch returns None when create_git_branch is False."""
        _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, pre_run_sha=None)
        result = orch._create_git_branch(tmp_path, ctx)

        assert result is None
        assert ctx.worktree_path is None


# ---------------------------------------------------------------------------
# Context fields (pre_run_sha, step_commits, worktree_path)
# ---------------------------------------------------------------------------


class TestContextGitFields:
    """Tests for git-related fields on PipelineContext."""

    def test_defaults(self):
        """pre_run_sha defaults to None, step_commits defaults to empty dict."""
        ctx = PipelineContext(task=TaskInput(title="t"))
        assert ctx.pre_run_sha is None
        assert ctx.step_commits == {}
        assert ctx.worktree_path is None

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

    def test_effective_path_returns_worktree_when_set(self, tmp_path):
        """effective_path returns worktree_path when it's set."""
        wt_path = tmp_path / "worktree"
        ctx = PipelineContext(
            task=TaskInput(title="t"),
            project_path=tmp_path,
            worktree_path=wt_path,
        )
        assert ctx.effective_path == wt_path

    def test_effective_path_returns_project_path_when_no_worktree(self, tmp_path):
        """effective_path falls back to project_path when worktree_path is None."""
        ctx = PipelineContext(
            task=TaskInput(title="t"),
            project_path=tmp_path,
        )
        assert ctx.effective_path == tmp_path

    def test_worktree_path_serialization_round_trip(self, tmp_path):
        """worktree_path survives JSON serialization."""
        wt_path = tmp_path / "worktree"
        ctx = PipelineContext(
            task=TaskInput(title="t"),
            project_path=tmp_path,
            worktree_path=wt_path,
        )

        json_str = ctx.model_dump_json()
        data = json.loads(json_str)
        restored = PipelineContext(**data)

        assert restored.worktree_path == wt_path
