"""Updated tests for test_cleanup_worktree_only_removes_directory_not_branch.

This test file provides the updated version of the test from test_git_completion_message.py
that reflects the new behavior where cleanup is not automatic. This test should be used
to replace or update the existing test.
"""

from __future__ import annotations

import shutil
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


# ---------------------------------------------------------------------------
# Tests: Updated Behavior for Worktree Cleanup
# ---------------------------------------------------------------------------


class TestWorktreeCleanupBehaviorUpdated:
    """Updated tests verifying that worktree cleanup behavior reflects new persistence model."""

    def test_cleanup_worktree_only_removes_directory_not_branch(self, tmp_path):
        """
        _cleanup_worktree() should only remove worktree directory, not delete the branch.

        UPDATED: This test now reflects that cleanup is NOT automatic. The _cleanup_worktree()
        method still exists and works correctly when called explicitly (e.g., during rollback),
        but it is no longer called automatically at the end of successful runs.
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        # Create a context with a worktree
        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
            status=PipelineStatus.COMPLETED,
            branch_naming="levelup/{run_id}",
        )

        # Create the git branch and worktree
        orch._create_git_branch(tmp_path, ctx)

        branch_name = f"levelup/{ctx.run_id}"
        worktree_path = ctx.worktree_path

        # Verify worktree and branch exist before cleanup
        assert worktree_path.exists(), "Worktree directory should exist before cleanup"
        assert branch_name in [h.name for h in repo.heads], "Branch should exist before cleanup"

        # EXPLICITLY call cleanup (this is no longer automatic)
        orch._cleanup_worktree(tmp_path, ctx)

        # Verify worktree directory is removed
        assert not worktree_path.exists(), "Worktree directory should be removed after cleanup"

        # CRITICAL: Branch should still exist in the repository
        assert branch_name in [h.name for h in repo.heads], (
            "Branch should persist in main repository after worktree cleanup"
        )

    def test_cleanup_worktree_method_still_works_when_called_explicitly(self, tmp_path):
        """
        The _cleanup_worktree() method should still function correctly when called explicitly.

        This verifies that the method itself works properly for explicit cleanup scenarios
        like rollback, even though it's no longer called automatically.
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test explicit cleanup"),
            project_path=tmp_path,
            status=PipelineStatus.FAILED,
            branch_naming="levelup/{run_id}",
        )

        # Create worktree
        orch._create_git_branch(tmp_path, ctx)
        worktree_path = ctx.worktree_path
        branch_name = f"levelup/{ctx.run_id}"

        assert worktree_path.exists()
        assert branch_name in [h.name for h in repo.heads]

        # Explicitly call cleanup (e.g., simulating rollback scenario)
        orch._cleanup_worktree(tmp_path, ctx)

        # Worktree removed, branch persists
        assert not worktree_path.exists(), "Explicit cleanup should remove worktree"
        assert branch_name in [h.name for h in repo.heads], "Explicit cleanup should preserve branch"

    def test_cleanup_worktree_handles_none_path_gracefully(self, tmp_path):
        """_cleanup_worktree should handle None worktree_path without errors."""
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
            status=PipelineStatus.COMPLETED,
            branch_naming="levelup/{run_id}",
        )
        # worktree_path is None

        # Should not raise any exceptions
        orch._cleanup_worktree(tmp_path, ctx)

    def test_cleanup_worktree_handles_nonexistent_path_gracefully(self, tmp_path):
        """_cleanup_worktree should handle non-existent worktree_path without errors."""
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
            status=PipelineStatus.COMPLETED,
            branch_naming="levelup/{run_id}",
        )
        ctx.worktree_path = Path.home() / ".levelup" / "worktrees" / "nonexistent"

        # Should not raise any exceptions
        orch._cleanup_worktree(tmp_path, ctx)

    def test_cleanup_is_not_automatic_after_successful_run(self, tmp_path):
        """
        Worktree cleanup should NOT happen automatically after a successful run.

        This is the key behavioral change: worktrees now persist after runs complete.
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        from unittest.mock import patch

        task = TaskInput(title="Test no auto cleanup", description="Test description")

        with patch.object(orch, "_execute_steps") as mock_exec:
            with patch.object(orch, "_persist_state"):
                ctx = PipelineContext(
                    task=task,
                    project_path=tmp_path,
                    status=PipelineStatus.RUNNING,
                    branch_naming="levelup/{run_id}",
                )

                # Create worktree
                orch._create_git_branch(tmp_path, ctx)
                worktree_path = ctx.worktree_path
                branch_name = f"levelup/{ctx.run_id}"

                # Complete the run
                ctx.status = PipelineStatus.COMPLETED
                mock_exec.return_value = ctx
                orch.run(task)

                # Worktree should still exist (NOT automatically cleaned up)
                assert worktree_path.exists(), (
                    "Worktree should persist after successful run (no automatic cleanup)"
                )
                assert branch_name in [h.name for h in repo.heads], (
                    "Branch should persist after successful run"
                )

                # Cleanup for test
                try:
                    repo.git.worktree("remove", str(worktree_path), "--force")
                except Exception:
                    shutil.rmtree(worktree_path, ignore_errors=True)
