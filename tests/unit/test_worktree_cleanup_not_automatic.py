"""Tests verifying that worktree cleanup is NOT automatic after pipeline runs.

This test suite specifically validates that _cleanup_worktree() is NOT called
automatically at the end of run() or resume() methods, updating the behavior
from the old automatic cleanup to the new persistence model.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock, call, patch

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


def _make_context(tmp_path: Path, status: PipelineStatus = PipelineStatus.RUNNING, **kwargs) -> PipelineContext:
    """Build a minimal PipelineContext with a unique run_id."""
    rid = kwargs.pop("run_id", None) or uuid.uuid4().hex[:12]
    return PipelineContext(
        task=TaskInput(title="Test task", description="Test description"),
        project_path=tmp_path,
        status=status,
        pre_run_sha=None,
        run_id=rid,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Tests: _cleanup_worktree NOT Called Automatically After run()
# ---------------------------------------------------------------------------


class TestCleanupNotCalledAfterRun:
    """Tests verifying _cleanup_worktree is NOT called automatically after run()."""

    def test_cleanup_not_called_after_completed_run(self, tmp_path):
        """_cleanup_worktree should NOT be called after successful run completion."""
        _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task", description="Test description")

        with patch.object(orch, "_cleanup_worktree") as mock_cleanup:
            with patch.object(orch, "_execute_steps") as mock_exec:
                with patch.object(orch, "_persist_state"):
                    ctx = _make_context(tmp_path, status=PipelineStatus.COMPLETED)
                    ctx.branch_naming = "levelup/{run_id}"
                    mock_exec.return_value = ctx

                    orch.run(task)

                    # CRITICAL: _cleanup_worktree should NOT be called
                    mock_cleanup.assert_not_called()

    def test_cleanup_not_called_after_failed_run(self, tmp_path):
        """_cleanup_worktree should NOT be called after failed run."""
        _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task", description="Test description")

        with patch.object(orch, "_cleanup_worktree") as mock_cleanup:
            with patch.object(orch, "_execute_steps") as mock_exec:
                with patch.object(orch, "_persist_state"):
                    ctx = _make_context(tmp_path, status=PipelineStatus.FAILED)
                    ctx.branch_naming = "levelup/{run_id}"
                    mock_exec.return_value = ctx

                    orch.run(task)

                    mock_cleanup.assert_not_called()

    def test_cleanup_not_called_after_aborted_run(self, tmp_path):
        """_cleanup_worktree should NOT be called after aborted run."""
        _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task", description="Test description")

        with patch.object(orch, "_cleanup_worktree") as mock_cleanup:
            with patch.object(orch, "_execute_steps") as mock_exec:
                with patch.object(orch, "_persist_state"):
                    ctx = _make_context(tmp_path, status=PipelineStatus.ABORTED)
                    ctx.branch_naming = "levelup/{run_id}"
                    mock_exec.return_value = ctx

                    orch.run(task)

                    mock_cleanup.assert_not_called()

    def test_cleanup_not_called_after_paused_run(self, tmp_path):
        """_cleanup_worktree should NOT be called after paused run."""
        _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task", description="Test description")

        with patch.object(orch, "_cleanup_worktree") as mock_cleanup:
            with patch.object(orch, "_execute_steps") as mock_exec:
                with patch.object(orch, "_persist_state"):
                    ctx = _make_context(tmp_path, status=PipelineStatus.PAUSED)
                    ctx.branch_naming = "levelup/{run_id}"
                    mock_exec.return_value = ctx

                    orch.run(task)

                    mock_cleanup.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: _cleanup_worktree NOT Called Automatically After resume()
# ---------------------------------------------------------------------------


class TestCleanupNotCalledAfterResume:
    """Tests verifying _cleanup_worktree is NOT called automatically after resume()."""

    def test_cleanup_not_called_after_completed_resume(self, tmp_path):
        """_cleanup_worktree should NOT be called after successful resume completion."""
        _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, status=PipelineStatus.FAILED)
        ctx.branch_naming = "levelup/{run_id}"

        with patch.object(orch, "_cleanup_worktree") as mock_cleanup:
            with patch.object(orch, "_execute_steps") as mock_exec:
                with patch.object(orch, "_persist_state"):
                    ctx.status = PipelineStatus.COMPLETED
                    mock_exec.return_value = ctx

                    orch.resume(ctx)

                    # CRITICAL: _cleanup_worktree should NOT be called
                    mock_cleanup.assert_not_called()

    def test_cleanup_not_called_after_failed_resume(self, tmp_path):
        """_cleanup_worktree should NOT be called after failed resume."""
        _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, status=PipelineStatus.FAILED)
        ctx.branch_naming = "levelup/{run_id}"

        with patch.object(orch, "_cleanup_worktree") as mock_cleanup:
            with patch.object(orch, "_execute_steps") as mock_exec:
                with patch.object(orch, "_persist_state"):
                    ctx.status = PipelineStatus.FAILED
                    mock_exec.return_value = ctx

                    orch.resume(ctx)

                    mock_cleanup.assert_not_called()

    def test_cleanup_not_called_after_aborted_resume(self, tmp_path):
        """_cleanup_worktree should NOT be called after aborted resume."""
        _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, status=PipelineStatus.FAILED)
        ctx.branch_naming = "levelup/{run_id}"

        with patch.object(orch, "_cleanup_worktree") as mock_cleanup:
            with patch.object(orch, "_execute_steps") as mock_exec:
                with patch.object(orch, "_persist_state"):
                    ctx.status = PipelineStatus.ABORTED
                    mock_exec.return_value = ctx

                    orch.resume(ctx)

                    mock_cleanup.assert_not_called()

    def test_cleanup_not_called_after_paused_resume(self, tmp_path):
        """_cleanup_worktree should NOT be called after paused resume."""
        _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, status=PipelineStatus.FAILED)
        ctx.branch_naming = "levelup/{run_id}"

        with patch.object(orch, "_cleanup_worktree") as mock_cleanup:
            with patch.object(orch, "_execute_steps") as mock_exec:
                with patch.object(orch, "_persist_state"):
                    ctx.status = PipelineStatus.PAUSED
                    mock_exec.return_value = ctx

                    orch.resume(ctx)

                    mock_cleanup.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: Verifying Old Cleanup Calls Were Removed
# ---------------------------------------------------------------------------


class TestOldCleanupCallsRemoved:
    """Tests verifying the old automatic cleanup calls have been removed."""

    def test_run_method_does_not_contain_cleanup_call_on_line_353(self, tmp_path):
        """The run() method should not call _cleanup_worktree on line 353."""
        # This test verifies the code change by checking behavior
        _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task", description="Test description")

        # Spy on _cleanup_worktree to verify it's never called
        original_cleanup = orch._cleanup_worktree
        cleanup_calls = []

        def cleanup_spy(*args, **kwargs):
            cleanup_calls.append((args, kwargs))
            return original_cleanup(*args, **kwargs)

        with patch.object(orch, "_cleanup_worktree", side_effect=cleanup_spy):
            with patch.object(orch, "_execute_steps") as mock_exec:
                with patch.object(orch, "_persist_state"):
                    ctx = _make_context(tmp_path, status=PipelineStatus.COMPLETED)
                    ctx.branch_naming = "levelup/{run_id}"
                    mock_exec.return_value = ctx

                    orch.run(task)

                    # Verify cleanup was never called
                    assert len(cleanup_calls) == 0, (
                        "Automatic cleanup call on line 353 should be removed"
                    )

    def test_resume_method_does_not_contain_cleanup_call_on_line_466(self, tmp_path):
        """The resume() method should not call _cleanup_worktree on line 466."""
        _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, status=PipelineStatus.FAILED)
        ctx.branch_naming = "levelup/{run_id}"

        # Spy on _cleanup_worktree
        original_cleanup = orch._cleanup_worktree
        cleanup_calls = []

        def cleanup_spy(*args, **kwargs):
            cleanup_calls.append((args, kwargs))
            return original_cleanup(*args, **kwargs)

        with patch.object(orch, "_cleanup_worktree", side_effect=cleanup_spy):
            with patch.object(orch, "_execute_steps") as mock_exec:
                with patch.object(orch, "_persist_state"):
                    ctx.status = PipelineStatus.COMPLETED
                    mock_exec.return_value = ctx

                    orch.resume(ctx)

                    # Verify cleanup was never called
                    assert len(cleanup_calls) == 0, (
                        "Automatic cleanup call on line 466 should be removed"
                    )


# ---------------------------------------------------------------------------
# Tests: Branch Persistence Behavior
# ---------------------------------------------------------------------------


class TestBranchPersistenceWithoutAutomaticCleanup:
    """Tests verifying branches and worktrees both persist without automatic cleanup."""

    def test_both_branch_and_worktree_persist_after_success(self, tmp_path):
        """Both branch and worktree should persist after successful run."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task", description="Test description")

        with patch.object(orch, "_execute_steps") as mock_exec:
            with patch.object(orch, "_persist_state"):
                ctx = _make_context(tmp_path, status=PipelineStatus.RUNNING)
                ctx.branch_naming = "levelup/{run_id}"

                # Create worktree
                orch._create_git_branch(tmp_path, ctx)
                branch_name = f"levelup/{ctx.run_id}"
                worktree_path = ctx.worktree_path

                # Complete the run
                ctx.status = PipelineStatus.COMPLETED
                mock_exec.return_value = ctx
                orch.run(task)

                # Both should persist
                assert branch_name in [h.name for h in repo.heads], (
                    "Branch should persist after successful run"
                )
                assert worktree_path.exists(), (
                    "Worktree should persist after successful run"
                )

                # Cleanup
                import shutil
                try:
                    repo.git.worktree("remove", str(worktree_path), "--force")
                except Exception:
                    shutil.rmtree(worktree_path, ignore_errors=True)

    def test_both_branch_and_worktree_persist_after_resume(self, tmp_path):
        """Both branch and worktree should persist after successful resume."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, status=PipelineStatus.FAILED)
        ctx.branch_naming = "levelup/{run_id}"
        orch._create_git_branch(tmp_path, ctx)

        branch_name = f"levelup/{ctx.run_id}"
        worktree_path = ctx.worktree_path

        with patch.object(orch, "_execute_steps") as mock_exec:
            with patch.object(orch, "_persist_state"):
                ctx.status = PipelineStatus.COMPLETED
                mock_exec.return_value = ctx
                orch.resume(ctx)

                # Both should persist
                assert branch_name in [h.name for h in repo.heads], (
                    "Branch should persist after successful resume"
                )
                assert worktree_path.exists(), (
                    "Worktree should persist after successful resume"
                )

                # Cleanup
                import shutil
                try:
                    repo.git.worktree("remove", str(worktree_path), "--force")
                except Exception:
                    shutil.rmtree(worktree_path, ignore_errors=True)
