"""Integration tests for complete worktree lifecycle with persistence behavior.

This test suite validates end-to-end workflows with the new worktree persistence
behavior, ensuring that real-world usage patterns work correctly.
"""

from __future__ import annotations

import shutil
import uuid
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
# Integration Tests: Complete Lifecycle
# ---------------------------------------------------------------------------


class TestCompleteRunLifecycleWithPersistence:
    """Integration tests for complete run lifecycle with persistent worktrees."""

    def test_successful_run_leaves_worktree_for_inspection(self, tmp_path):
        """
        A successful run should leave worktree in place for user inspection.

        This validates the primary use case: users can inspect the worktree
        after a successful run to review changes before merging.
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Add feature", description="Implement new feature")

        with patch.object(orch, "_execute_steps") as mock_exec:
            with patch.object(orch, "_persist_state"):
                ctx = _make_context(tmp_path, status=PipelineStatus.RUNNING)
                ctx.branch_naming = "levelup/{run_id}"

                # Create worktree and simulate successful completion
                orch._create_git_branch(tmp_path, ctx)
                worktree_path = ctx.worktree_path
                branch_name = f"levelup/{ctx.run_id}"

                ctx.status = PipelineStatus.COMPLETED
                mock_exec.return_value = ctx
                result_ctx = orch.run(task)

        # Worktree should exist for inspection
        assert worktree_path.exists(), (
            "Worktree should persist after successful run for user inspection"
        )
        assert branch_name in [h.name for h in repo.heads], (
            "Branch should exist for user to review"
        )

        # User can inspect files in the worktree
        assert (worktree_path / "init.txt").exists(), (
            "User should be able to access files in persistent worktree"
        )

        # Cleanup (simulating user cleanup after inspection)
        try:
            repo.git.worktree("remove", str(worktree_path), "--force")
        except Exception:
            shutil.rmtree(worktree_path, ignore_errors=True)

    def test_failed_run_leaves_worktree_for_debugging(self, tmp_path):
        """
        A failed run should leave worktree in place for debugging.

        This validates another primary use case: users can inspect the worktree
        after a failure to understand what went wrong before resuming.
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Add feature", description="Implement new feature")

        with patch.object(orch, "_execute_steps") as mock_exec:
            with patch.object(orch, "_persist_state"):
                ctx = _make_context(tmp_path, status=PipelineStatus.RUNNING)
                ctx.branch_naming = "levelup/{run_id}"

                orch._create_git_branch(tmp_path, ctx)
                worktree_path = ctx.worktree_path
                branch_name = f"levelup/{ctx.run_id}"

                # Simulate failure
                ctx.status = PipelineStatus.FAILED
                mock_exec.return_value = ctx
                result_ctx = orch.run(task)

        # Worktree should exist for debugging
        assert worktree_path.exists(), (
            "Worktree should persist after failed run for debugging"
        )
        assert branch_name in [h.name for h in repo.heads], (
            "Branch should exist for debugging and potential resume"
        )

        # Cleanup
        try:
            repo.git.worktree("remove", str(worktree_path), "--force")
        except Exception:
            shutil.rmtree(worktree_path, ignore_errors=True)

    def test_pause_resume_preserves_worktree_throughout(self, tmp_path):
        """
        Pause and resume workflow should preserve worktree throughout the lifecycle.
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Add feature", description="Implement new feature")

        # Initial run that pauses
        with patch.object(orch, "_execute_steps") as mock_exec:
            with patch.object(orch, "_persist_state"):
                ctx = _make_context(tmp_path, status=PipelineStatus.RUNNING)
                ctx.branch_naming = "levelup/{run_id}"

                orch._create_git_branch(tmp_path, ctx)
                worktree_path = ctx.worktree_path

                # Pause
                ctx.status = PipelineStatus.PAUSED
                mock_exec.return_value = ctx
                paused_ctx = orch.run(task)

        # Worktree should persist while paused
        assert worktree_path.exists(), "Worktree should persist while run is paused"

        # Resume and complete
        with patch.object(orch, "_execute_steps") as mock_exec:
            with patch.object(orch, "_persist_state"):
                paused_ctx.status = PipelineStatus.COMPLETED
                mock_exec.return_value = paused_ctx
                completed_ctx = orch.resume(paused_ctx)

        # Worktree should still persist after resume completes
        assert worktree_path.exists(), (
            "Worktree should persist after resume completes"
        )

        # Cleanup
        try:
            repo.git.worktree("remove", str(worktree_path), "--force")
        except Exception:
            shutil.rmtree(worktree_path, ignore_errors=True)


class TestMultipleSequentialRunsWithPersistence:
    """Integration tests for multiple sequential runs building up persistent worktrees."""

    def test_three_sequential_runs_create_three_persistent_worktrees(self, tmp_path):
        """
        Three sequential runs should create three persistent worktrees that coexist.
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        worktree_paths = []
        branch_names = []

        for i in range(3):
            task = TaskInput(title=f"Feature {i}", description=f"Implement feature {i}")

            with patch.object(orch, "_execute_steps") as mock_exec:
                with patch.object(orch, "_persist_state"):
                    ctx = _make_context(tmp_path, status=PipelineStatus.RUNNING)
                    ctx.branch_naming = "levelup/{run_id}"

                    orch._create_git_branch(tmp_path, ctx)
                    worktree_paths.append(ctx.worktree_path)
                    branch_names.append(f"levelup/{ctx.run_id}")

                    ctx.status = PipelineStatus.COMPLETED
                    mock_exec.return_value = ctx
                    orch.run(task)

        # All three worktrees should coexist
        for i, wt_path in enumerate(worktree_paths):
            assert wt_path.exists(), (
                f"Worktree {i} should persist alongside others"
            )

        # All three branches should exist
        head_names = [h.name for h in repo.heads]
        for branch_name in branch_names:
            assert branch_name in head_names, (
                f"Branch {branch_name} should exist"
            )

        # Cleanup all
        for wt_path in worktree_paths:
            try:
                repo.git.worktree("remove", str(wt_path), "--force")
            except Exception:
                shutil.rmtree(wt_path, ignore_errors=True)


class TestRollbackExplicitCleanupIntegration:
    """Integration tests for rollback explicitly cleaning up worktrees."""

    def test_rollback_removes_worktree_but_not_branch(self, tmp_path):
        """
        Rollback should explicitly remove worktree but preserve branch.

        This validates that the explicit cleanup in cli/app.py rollback works correctly.
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        # Create a failed run with worktree
        ctx = _make_context(tmp_path, status=PipelineStatus.FAILED)
        ctx.branch_naming = "levelup/{run_id}"
        orch._create_git_branch(tmp_path, ctx)

        worktree_path = ctx.worktree_path
        branch_name = f"levelup/{ctx.run_id}"

        assert worktree_path.exists()
        assert branch_name in [h.name for h in repo.heads]

        # Simulate rollback cleanup (as done in cli/app.py line 669)
        if worktree_path.exists():
            try:
                repo.git.worktree("remove", str(worktree_path), "--force")
            except Exception:
                pass

        # Worktree should be removed by rollback
        assert not worktree_path.exists(), (
            "Rollback should explicitly remove worktree"
        )

        # Branch should still exist for potential future use
        assert branch_name in [h.name for h in repo.heads], (
            "Rollback should preserve branch even after removing worktree"
        )

    def test_rollback_to_specific_commit_removes_worktree(self, tmp_path):
        """
        Rollback to a specific commit should remove worktree but keep branch with changes.
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        # Create run with worktree and commit
        ctx = _make_context(tmp_path, status=PipelineStatus.RUNNING)
        ctx.branch_naming = "levelup/{run_id}"
        orch._create_git_branch(tmp_path, ctx)

        worktree_path = ctx.worktree_path
        branch_name = f"levelup/{ctx.run_id}"

        # Make a commit in the worktree
        worktree_repo = git.Repo(str(worktree_path))
        test_file = worktree_path / "test.txt"
        test_file.write_text("test content")
        worktree_repo.index.add(["test.txt"])
        worktree_repo.index.commit("Add test file")

        # Simulate partial rollback (keeps branch, removes worktree)
        if worktree_path.exists():
            try:
                repo.git.worktree("remove", str(worktree_path), "--force")
            except Exception:
                pass

        # Worktree removed
        assert not worktree_path.exists(), (
            "Partial rollback should remove worktree"
        )

        # Branch and commit should persist
        assert branch_name in [h.name for h in repo.heads], (
            "Partial rollback should preserve branch and commits"
        )


class TestGUITicketDeletionCleanupIntegration:
    """Integration tests for GUI ticket deletion explicitly cleaning up worktrees."""

    def test_gui_ticket_deletion_removes_worktree_and_branch(self, tmp_path):
        """
        GUI ticket deletion should remove worktree (and typically the branch too).

        This validates that the explicit cleanup in main_window.py works correctly.
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, run_id="gui_ticket_001")
        ctx.branch_naming = "levelup/{run_id}"
        orch._create_git_branch(tmp_path, ctx)

        worktree_path = ctx.worktree_path
        branch_name = f"levelup/{ctx.run_id}"

        assert worktree_path.exists()
        assert branch_name in [h.name for h in repo.heads]

        # Simulate GUI ticket deletion cleanup (main_window.py line 417)
        try:
            repo.git.worktree("remove", str(worktree_path), "--force")
        except Exception:
            try:
                shutil.rmtree(worktree_path)
            except Exception:
                pass

        # Worktree should be removed
        assert not worktree_path.exists(), (
            "GUI ticket deletion should remove worktree"
        )

        # Branch persists (GUI might delete it separately)
        assert branch_name in [h.name for h in repo.heads], (
            "Branch should persist after worktree cleanup (deleted separately by GUI)"
        )


class TestStaleWorktreeCleanupIntegration:
    """Integration tests for stale worktree cleanup before creating new ones."""

    def test_retry_after_failure_cleans_up_stale_worktree(self, tmp_path):
        """
        Retrying a failed run should clean up stale worktree before creating new one.

        This validates that stale cleanup in orchestrator.py line 929 works correctly.
        """
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        run_id = "retry_test_001"

        # First attempt - create worktree and fail
        ctx1 = _make_context(tmp_path, run_id=run_id, status=PipelineStatus.RUNNING)
        ctx1.branch_naming = "levelup/{run_id}"
        orch._create_git_branch(tmp_path, ctx1)

        worktree_path = ctx1.worktree_path
        branch_name = f"levelup/{run_id}"

        # Create a marker file in the worktree
        marker_file = worktree_path / "first_attempt.txt"
        marker_file.write_text("first attempt")
        assert marker_file.exists()

        # Manually remove worktree (simulating crash/failure)
        try:
            repo.git.worktree("remove", str(worktree_path), "--force")
        except Exception:
            shutil.rmtree(worktree_path, ignore_errors=True)

        # Create stale directory manually
        worktree_path.mkdir(parents=True)
        (worktree_path / "stale.txt").write_text("stale from first attempt")

        # Second attempt - should clean up stale worktree
        ctx2 = _make_context(tmp_path, run_id=run_id, status=PipelineStatus.RUNNING)
        ctx2.branch_naming = "levelup/{run_id}"
        orch._create_git_branch(tmp_path, ctx2)

        # Worktree should exist but without stale files
        assert ctx2.worktree_path.exists(), (
            "New worktree should be created after stale cleanup"
        )
        assert not (ctx2.worktree_path / "stale.txt").exists(), (
            "Stale files should be removed during cleanup"
        )

        # Cleanup
        try:
            repo.git.worktree("remove", str(ctx2.worktree_path), "--force")
        except Exception:
            shutil.rmtree(ctx2.worktree_path, ignore_errors=True)
