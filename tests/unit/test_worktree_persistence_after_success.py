"""Tests verifying that worktrees persist after successful pipeline runs.

This test suite validates that automatic worktree cleanup has been removed
from successful pipeline completions, while preserving explicit cleanup scenarios.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

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
# Tests: Worktree Persistence After Successful Runs
# ---------------------------------------------------------------------------


class TestWorktreePersistenceAfterSuccessfulRun:
    """Tests verifying worktrees persist after successful pipeline run completion."""

    def test_worktree_persists_after_completed_run(self, tmp_path):
        """Worktree directory should persist after a successful pipeline run completes."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        # Mock the pipeline execution to complete successfully
        task = TaskInput(title="Test task", description="Test description")

        with patch.object(orch, "_execute_steps") as mock_exec:
            # Create a context that will be returned from _execute_steps
            ctx = _make_context(tmp_path, status=PipelineStatus.RUNNING)
            ctx.branch_naming = "levelup/{run_id}"

            # Create the worktree
            orch._create_git_branch(tmp_path, ctx)

            # Verify worktree was created
            assert ctx.worktree_path is not None
            assert ctx.worktree_path.exists(), "Worktree should exist after creation"
            worktree_path = ctx.worktree_path

            # Set status to completed and return from mocked _execute_steps
            ctx.status = PipelineStatus.COMPLETED
            mock_exec.return_value = ctx

            # Run the pipeline (which will call _execute_steps and then cleanup logic)
            with patch.object(orch, "_persist_state"):
                result_ctx = orch.run(task)

            # CRITICAL: Worktree should still exist after successful completion
            assert worktree_path.exists(), (
                "Worktree directory should persist after successful pipeline completion"
            )
            assert result_ctx.status == PipelineStatus.COMPLETED

            # Cleanup for test
            try:
                repo.git.worktree("remove", str(worktree_path), "--force")
            except Exception:
                shutil.rmtree(worktree_path, ignore_errors=True)

    def test_worktree_persists_after_failed_run(self, tmp_path):
        """Worktree directory should persist after a failed pipeline run."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task", description="Test description")

        with patch.object(orch, "_execute_steps") as mock_exec:
            ctx = _make_context(tmp_path, status=PipelineStatus.RUNNING)
            ctx.branch_naming = "levelup/{run_id}"

            orch._create_git_branch(tmp_path, ctx)
            assert ctx.worktree_path is not None
            assert ctx.worktree_path.exists()
            worktree_path = ctx.worktree_path

            # Simulate failed run
            ctx.status = PipelineStatus.FAILED
            mock_exec.return_value = ctx

            with patch.object(orch, "_persist_state"):
                result_ctx = orch.run(task)

            # Worktree should persist after failed run
            assert worktree_path.exists(), (
                "Worktree directory should persist after failed pipeline run"
            )
            assert result_ctx.status == PipelineStatus.FAILED

            # Cleanup
            try:
                repo.git.worktree("remove", str(worktree_path), "--force")
            except Exception:
                shutil.rmtree(worktree_path, ignore_errors=True)

    def test_worktree_persists_after_aborted_run(self, tmp_path):
        """Worktree directory should persist after an aborted pipeline run."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task", description="Test description")

        with patch.object(orch, "_execute_steps") as mock_exec:
            ctx = _make_context(tmp_path, status=PipelineStatus.RUNNING)
            ctx.branch_naming = "levelup/{run_id}"

            orch._create_git_branch(tmp_path, ctx)
            assert ctx.worktree_path is not None
            assert ctx.worktree_path.exists()
            worktree_path = ctx.worktree_path

            # Simulate aborted run
            ctx.status = PipelineStatus.ABORTED
            mock_exec.return_value = ctx

            with patch.object(orch, "_persist_state"):
                result_ctx = orch.run(task)

            # Worktree should persist after aborted run
            assert worktree_path.exists(), (
                "Worktree directory should persist after aborted pipeline run"
            )
            assert result_ctx.status == PipelineStatus.ABORTED

            # Cleanup
            try:
                repo.git.worktree("remove", str(worktree_path), "--force")
            except Exception:
                shutil.rmtree(worktree_path, ignore_errors=True)

    def test_worktree_persists_after_paused_run(self, tmp_path):
        """Worktree directory should persist after a paused pipeline run."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task", description="Test description")

        with patch.object(orch, "_execute_steps") as mock_exec:
            ctx = _make_context(tmp_path, status=PipelineStatus.RUNNING)
            ctx.branch_naming = "levelup/{run_id}"

            orch._create_git_branch(tmp_path, ctx)
            assert ctx.worktree_path is not None
            assert ctx.worktree_path.exists()
            worktree_path = ctx.worktree_path

            # Simulate paused run
            ctx.status = PipelineStatus.PAUSED
            mock_exec.return_value = ctx

            with patch.object(orch, "_persist_state"):
                result_ctx = orch.run(task)

            # Worktree should persist after paused run (this was already the case)
            assert worktree_path.exists(), (
                "Worktree directory should persist after paused pipeline run"
            )
            assert result_ctx.status == PipelineStatus.PAUSED

            # Cleanup
            try:
                repo.git.worktree("remove", str(worktree_path), "--force")
            except Exception:
                shutil.rmtree(worktree_path, ignore_errors=True)


class TestWorktreePersistenceAfterSuccessfulResume:
    """Tests verifying worktrees persist after successful resume operations."""

    def test_worktree_persists_after_completed_resume(self, tmp_path):
        """Worktree directory should persist after a successful resume completes."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        # Create initial context with worktree
        ctx = _make_context(tmp_path, status=PipelineStatus.FAILED)
        ctx.branch_naming = "levelup/{run_id}"
        orch._create_git_branch(tmp_path, ctx)

        assert ctx.worktree_path is not None
        assert ctx.worktree_path.exists()
        worktree_path = ctx.worktree_path

        with patch.object(orch, "_execute_steps") as mock_exec:
            # Simulate successful resume
            ctx.status = PipelineStatus.COMPLETED
            mock_exec.return_value = ctx

            with patch.object(orch, "_persist_state"):
                result_ctx = orch.resume(ctx)

            # CRITICAL: Worktree should persist after successful resume
            assert worktree_path.exists(), (
                "Worktree directory should persist after successful resume completion"
            )
            assert result_ctx.status == PipelineStatus.COMPLETED

            # Cleanup
            try:
                repo.git.worktree("remove", str(worktree_path), "--force")
            except Exception:
                shutil.rmtree(worktree_path, ignore_errors=True)

    def test_worktree_persists_after_failed_resume(self, tmp_path):
        """Worktree directory should persist after a failed resume."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, status=PipelineStatus.FAILED)
        ctx.branch_naming = "levelup/{run_id}"
        orch._create_git_branch(tmp_path, ctx)

        assert ctx.worktree_path is not None
        worktree_path = ctx.worktree_path

        with patch.object(orch, "_execute_steps") as mock_exec:
            # Simulate failed resume
            ctx.status = PipelineStatus.FAILED
            mock_exec.return_value = ctx

            with patch.object(orch, "_persist_state"):
                result_ctx = orch.resume(ctx)

            # Worktree should persist after failed resume
            assert worktree_path.exists(), (
                "Worktree directory should persist after failed resume"
            )
            assert result_ctx.status == PipelineStatus.FAILED

            # Cleanup
            try:
                repo.git.worktree("remove", str(worktree_path), "--force")
            except Exception:
                shutil.rmtree(worktree_path, ignore_errors=True)

    def test_worktree_persists_after_aborted_resume(self, tmp_path):
        """Worktree directory should persist after an aborted resume."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, status=PipelineStatus.FAILED)
        ctx.branch_naming = "levelup/{run_id}"
        orch._create_git_branch(tmp_path, ctx)

        assert ctx.worktree_path is not None
        worktree_path = ctx.worktree_path

        with patch.object(orch, "_execute_steps") as mock_exec:
            # Simulate aborted resume
            ctx.status = PipelineStatus.ABORTED
            mock_exec.return_value = ctx

            with patch.object(orch, "_persist_state"):
                result_ctx = orch.resume(ctx)

            # Worktree should persist after aborted resume
            assert worktree_path.exists(), (
                "Worktree directory should persist after aborted resume"
            )
            assert result_ctx.status == PipelineStatus.ABORTED

            # Cleanup
            try:
                repo.git.worktree("remove", str(worktree_path), "--force")
            except Exception:
                shutil.rmtree(worktree_path, ignore_errors=True)


class TestNoCleanupErrorsAfterSuccess:
    """Tests verifying that no cleanup-related errors appear after successful runs."""

    def test_no_cleanup_warnings_after_completed_run(self, tmp_path, caplog):
        """No 'Failed to remove worktree' warnings should appear after successful completion."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task", description="Test description")

        with patch.object(orch, "_execute_steps") as mock_exec:
            ctx = _make_context(tmp_path, status=PipelineStatus.RUNNING)
            ctx.branch_naming = "levelup/{run_id}"

            orch._create_git_branch(tmp_path, ctx)
            worktree_path = ctx.worktree_path

            ctx.status = PipelineStatus.COMPLETED
            mock_exec.return_value = ctx

            with patch.object(orch, "_persist_state"):
                orch.run(task)

            # Check that no warnings about worktree removal appear in logs
            log_messages = [record.message for record in caplog.records]
            cleanup_warnings = [msg for msg in log_messages if "remove worktree" in msg.lower()]

            assert len(cleanup_warnings) == 0, (
                "No worktree cleanup warnings should appear after successful run"
            )

            # Cleanup
            try:
                repo.git.worktree("remove", str(worktree_path), "--force")
            except Exception:
                shutil.rmtree(worktree_path, ignore_errors=True)

    def test_no_cleanup_warnings_after_completed_resume(self, tmp_path, caplog):
        """No 'Failed to remove worktree' warnings should appear after successful resume."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, status=PipelineStatus.FAILED)
        ctx.branch_naming = "levelup/{run_id}"
        orch._create_git_branch(tmp_path, ctx)
        worktree_path = ctx.worktree_path

        with patch.object(orch, "_execute_steps") as mock_exec:
            ctx.status = PipelineStatus.COMPLETED
            mock_exec.return_value = ctx

            with patch.object(orch, "_persist_state"):
                orch.resume(ctx)

            log_messages = [record.message for record in caplog.records]
            cleanup_warnings = [msg for msg in log_messages if "remove worktree" in msg.lower()]

            assert len(cleanup_warnings) == 0, (
                "No worktree cleanup warnings should appear after successful resume"
            )

            # Cleanup
            try:
                repo.git.worktree("remove", str(worktree_path), "--force")
            except Exception:
                shutil.rmtree(worktree_path, ignore_errors=True)


class TestWorktreeLocationAfterSuccess:
    """Tests verifying worktrees remain in expected location after success."""

    def test_worktree_in_expected_location_after_success(self, tmp_path):
        """Worktree should remain in ~/.levelup/worktrees/<run_id>/ after successful completion."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task", description="Test description")

        with patch.object(orch, "_execute_steps") as mock_exec:
            ctx = _make_context(tmp_path, status=PipelineStatus.RUNNING)
            ctx.branch_naming = "levelup/{run_id}"

            orch._create_git_branch(tmp_path, ctx)

            # Verify expected location
            expected_path = Path.home() / ".levelup" / "worktrees" / ctx.run_id
            assert ctx.worktree_path == expected_path, (
                "Worktree should be in ~/.levelup/worktrees/<run_id>/"
            )

            ctx.status = PipelineStatus.COMPLETED
            mock_exec.return_value = ctx

            with patch.object(orch, "_persist_state"):
                orch.run(task)

            # Verify it still exists in the same location
            assert expected_path.exists(), (
                "Worktree should persist in ~/.levelup/worktrees/<run_id>/ after success"
            )

            # Cleanup
            try:
                repo.git.worktree("remove", str(expected_path), "--force")
            except Exception:
                shutil.rmtree(expected_path, ignore_errors=True)

    def test_multiple_successful_runs_create_separate_worktrees(self, tmp_path):
        """Multiple successful runs should create separate persisted worktrees."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        worktree_paths = []

        for i in range(3):
            task = TaskInput(title=f"Test task {i}", description=f"Test description {i}")

            with patch.object(orch, "_execute_steps") as mock_exec:
                ctx = _make_context(tmp_path, status=PipelineStatus.RUNNING)
                ctx.branch_naming = "levelup/{run_id}"

                orch._create_git_branch(tmp_path, ctx)
                worktree_paths.append(ctx.worktree_path)

                ctx.status = PipelineStatus.COMPLETED
                mock_exec.return_value = ctx

                with patch.object(orch, "_persist_state"):
                    orch.run(task)

        # All worktrees should exist
        for wt_path in worktree_paths:
            assert wt_path.exists(), (
                f"Worktree {wt_path} should persist after successful run"
            )

        # All should be unique locations
        assert len(set(worktree_paths)) == 3, "Each run should have unique worktree"

        # Cleanup
        for wt_path in worktree_paths:
            try:
                repo.git.worktree("remove", str(wt_path), "--force")
            except Exception:
                shutil.rmtree(wt_path, ignore_errors=True)
