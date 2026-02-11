"""Updated tests for test_cleanup_removes_worktree from test_step_commits.py.

This test file provides the updated version of the cleanup test that reflects
the new behavior where cleanup must be called explicitly, not automatically.
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


def _make_context(tmp_path: Path, pre_run_sha: str | None = None, **kwargs) -> PipelineContext:
    """Build a minimal PipelineContext."""
    return PipelineContext(
        task=TaskInput(title="Test task", description="Test description"),
        project_path=tmp_path,
        status=PipelineStatus.RUNNING,
        pre_run_sha=pre_run_sha,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Tests: Updated Cleanup Behavior
# ---------------------------------------------------------------------------


class TestCleanupRemovesWorktreeUpdated:
    """Updated test for _cleanup_worktree removing the worktree directory."""

    def test_cleanup_removes_worktree(self, tmp_path):
        """
        _cleanup_worktree removes the worktree directory when called explicitly.

        UPDATED: This test now explicitly calls _cleanup_worktree() to verify
        the method works correctly, since it is no longer called automatically
        at the end of run() or resume().
        """
        repo = _init_git_repo(tmp_path)

        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, pre_run_sha=None)
        orch._create_git_branch(tmp_path, ctx)

        assert ctx.worktree_path.exists(), "Worktree should exist after creation"

        # EXPLICITLY call cleanup (no longer automatic)
        orch._cleanup_worktree(tmp_path, ctx)

        assert not ctx.worktree_path.exists(), (
            "Worktree should be removed after explicit cleanup"
        )

    def test_cleanup_noop_when_no_worktree(self, tmp_path):
        """_cleanup_worktree does nothing when worktree_path is None."""
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, pre_run_sha=None)
        # worktree_path is None
        orch._cleanup_worktree(tmp_path, ctx)  # should not raise

    def test_worktree_persists_without_explicit_cleanup(self, tmp_path):
        """
        Worktree should persist after run completes if cleanup is not called explicitly.

        This test verifies the new behavior where worktrees are not automatically
        cleaned up at the end of successful runs.
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        from unittest.mock import patch

        task = TaskInput(title="Test persistence", description="Test description")

        with patch.object(orch, "_execute_steps") as mock_exec:
            with patch.object(orch, "_persist_state"):
                ctx = _make_context(tmp_path, pre_run_sha=None)
                ctx.branch_naming = "levelup/{run_id}"

                # Create worktree
                orch._create_git_branch(tmp_path, ctx)
                worktree_path = ctx.worktree_path

                # Complete the run
                ctx.status = PipelineStatus.COMPLETED
                mock_exec.return_value = ctx
                orch.run(task)

                # Worktree should still exist (no automatic cleanup)
                assert worktree_path.exists(), (
                    "Worktree should persist after run without explicit cleanup"
                )

                # Manual cleanup for test
                try:
                    repo.git.worktree("remove", str(worktree_path), "--force")
                except Exception:
                    shutil.rmtree(worktree_path, ignore_errors=True)

    def test_explicit_cleanup_can_be_called_anytime(self, tmp_path):
        """
        Explicit cleanup can be called at any time, not just at end of run.

        This demonstrates the new pattern where cleanup is a separate operation
        that can be invoked independently (e.g., during rollback).
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, pre_run_sha=None)
        ctx.branch_naming = "levelup/{run_id}"

        # Create worktree
        orch._create_git_branch(tmp_path, ctx)
        worktree_path = ctx.worktree_path
        assert worktree_path.exists()

        # Call cleanup explicitly (simulating rollback scenario)
        orch._cleanup_worktree(tmp_path, ctx)
        assert not worktree_path.exists()

        # Branch should still exist
        branch_name = f"levelup/{ctx.run_id}"
        assert branch_name in [h.name for h in repo.heads], (
            "Branch should persist after explicit worktree cleanup"
        )

    def test_multiple_worktrees_can_coexist_without_automatic_cleanup(self, tmp_path):
        """
        Multiple worktrees can coexist after their runs complete without automatic cleanup.

        This demonstrates the benefit of the new behavior: concurrent runs can leave
        their worktrees in place for later inspection or resumption.
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        from unittest.mock import patch
        import uuid

        worktree_paths = []

        for i in range(3):
            task = TaskInput(title=f"Test {i}", description=f"Test description {i}")

            with patch.object(orch, "_execute_steps") as mock_exec:
                with patch.object(orch, "_persist_state"):
                    ctx = _make_context(tmp_path, pre_run_sha=None)
                    ctx.run_id = uuid.uuid4().hex[:12]
                    ctx.branch_naming = "levelup/{run_id}"

                    # Create worktree
                    orch._create_git_branch(tmp_path, ctx)
                    worktree_paths.append(ctx.worktree_path)

                    # Complete the run
                    ctx.status = PipelineStatus.COMPLETED
                    mock_exec.return_value = ctx
                    orch.run(task)

        # All worktrees should coexist
        for wt_path in worktree_paths:
            assert wt_path.exists(), (
                f"Worktree {wt_path} should persist after its run completes"
            )

        # All should be unique
        assert len(set(worktree_paths)) == 3, "Each run should have unique worktree"

        # Manual cleanup
        for wt_path in worktree_paths:
            try:
                repo.git.worktree("remove", str(wt_path), "--force")
            except Exception:
                shutil.rmtree(wt_path, ignore_errors=True)
