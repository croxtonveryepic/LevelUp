"""Tests for concurrent worktree behavior with new persistence model.

This test suite validates that concurrent worktree creation and management
still functions correctly with the new behavior where worktrees persist
after pipeline runs complete.
"""

from __future__ import annotations

import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
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

NUM_WORKERS = 4


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


def _make_context(tmp_path: Path, run_id: str | None = None, **kwargs) -> PipelineContext:
    """Build a minimal PipelineContext with a unique run_id."""
    rid = run_id or uuid.uuid4().hex[:12]
    return PipelineContext(
        task=TaskInput(title="Test task", description="Test description"),
        project_path=tmp_path,
        status=PipelineStatus.RUNNING,
        pre_run_sha=None,
        run_id=rid,
        **kwargs,
    )


@pytest.fixture()
def git_repo(tmp_path: Path):
    """Create a git repo and yield it. Prune any leftover worktrees on teardown."""
    repo = _init_git_repo(tmp_path)
    yield tmp_path, repo
    # Force-prune stale worktrees
    try:
        repo.git.worktree("prune")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tests: Concurrent Worktree Creation with Persistence
# ---------------------------------------------------------------------------


class TestConcurrentWorktreeCreationWithPersistence:
    """Verify that concurrent worktrees persist after runs complete."""

    def test_four_concurrent_worktrees_all_persist_after_completion(self, git_repo):
        """
        Four concurrent worktrees should all persist after their runs complete.

        This validates that the new persistence behavior works correctly with
        concurrent pipeline runs.
        """
        tmp_path, repo = git_repo
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        contexts = [_make_context(tmp_path) for _ in range(NUM_WORKERS)]
        for ctx in contexts:
            ctx.branch_naming = "levelup/{run_id}"

        with patch.object(orch, "_execute_steps") as mock_exec:
            with patch.object(orch, "_persist_state"):
                # Create worktrees concurrently
                def create_and_run(ctx: PipelineContext) -> PipelineContext:
                    orch._create_git_branch(tmp_path, ctx)
                    ctx.status = PipelineStatus.COMPLETED
                    mock_exec.return_value = ctx
                    task = TaskInput(title=f"Task {ctx.run_id}", description="Test")
                    orch.run(task)
                    return ctx

                with ThreadPoolExecutor(max_workers=NUM_WORKERS) as pool:
                    futures = [pool.submit(create_and_run, ctx) for ctx in contexts]
                    results = [f.result() for f in as_completed(futures)]

        # All worktrees should persist
        for ctx in results:
            assert ctx.worktree_path.exists(), (
                f"Worktree {ctx.worktree_path} should persist after concurrent run completion"
            )

        # All branches should exist
        head_names = [h.name for h in repo.heads]
        for ctx in results:
            branch_name = f"levelup/{ctx.run_id}"
            assert branch_name in head_names, (
                f"Branch {branch_name} should exist after concurrent run"
            )

        # Cleanup
        for ctx in results:
            try:
                repo.git.worktree("remove", str(ctx.worktree_path), "--force")
            except Exception:
                shutil.rmtree(ctx.worktree_path, ignore_errors=True)

    def test_concurrent_worktrees_in_unique_locations(self, git_repo):
        """
        Concurrent worktrees should be created in unique locations and all persist.
        """
        tmp_path, repo = git_repo
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        contexts = [_make_context(tmp_path) for _ in range(NUM_WORKERS)]
        for ctx in contexts:
            ctx.branch_naming = "levelup/{run_id}"

        # Create worktrees concurrently
        def create_wt(ctx: PipelineContext) -> PipelineContext:
            orch._create_git_branch(tmp_path, ctx)
            return ctx

        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as pool:
            futures = [pool.submit(create_wt, ctx) for ctx in contexts]
            results = [f.result() for f in as_completed(futures)]

        worktree_paths = [ctx.worktree_path for ctx in results]

        # All should exist
        for wt_path in worktree_paths:
            assert wt_path.exists(), f"Worktree {wt_path} should exist"

        # All should be unique
        assert len(set(worktree_paths)) == NUM_WORKERS, (
            "Each concurrent run should have unique worktree location"
        )

        # All should be in expected parent directory
        for wt_path in worktree_paths:
            assert wt_path.parent == Path.home() / ".levelup" / "worktrees", (
                f"Worktree {wt_path} should be in ~/.levelup/worktrees/"
            )

        # Cleanup
        for wt_path in worktree_paths:
            try:
                repo.git.worktree("remove", str(wt_path), "--force")
            except Exception:
                shutil.rmtree(wt_path, ignore_errors=True)


class TestConcurrentWorktreesWithStaleCleanup:
    """Verify stale worktree cleanup works correctly in concurrent scenarios."""

    def test_stale_worktree_cleanup_before_concurrent_runs(self, git_repo):
        """
        Stale worktree cleanup should work correctly when multiple runs start concurrently.
        """
        tmp_path, repo = git_repo
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        # Create stale worktree directories
        run_ids = [f"stale_{i}" for i in range(NUM_WORKERS)]
        for run_id in run_ids:
            stale_dir = Path.home() / ".levelup" / "worktrees" / run_id
            stale_dir.mkdir(parents=True, exist_ok=True)
            (stale_dir / "stale.txt").write_text("stale content")

        # Create new worktrees with same run_ids (simulates retries)
        contexts = [_make_context(tmp_path, run_id=rid) for rid in run_ids]
        for ctx in contexts:
            ctx.branch_naming = "levelup/{run_id}"

        def create_wt(ctx: PipelineContext) -> PipelineContext:
            orch._create_git_branch(tmp_path, ctx)
            return ctx

        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as pool:
            futures = [pool.submit(create_wt, ctx) for ctx in contexts]
            results = [f.result() for f in as_completed(futures)]

        # All new worktrees should exist without stale files
        for ctx in results:
            assert ctx.worktree_path.exists(), (
                f"New worktree {ctx.worktree_path} should exist"
            )
            # Stale files should be gone
            stale_file = ctx.worktree_path / "stale.txt"
            assert not stale_file.exists(), (
                f"Stale file {stale_file} should be removed during cleanup"
            )

        # Cleanup
        for ctx in results:
            try:
                repo.git.worktree("remove", str(ctx.worktree_path), "--force")
            except Exception:
                shutil.rmtree(ctx.worktree_path, ignore_errors=True)


class TestConcurrentWorktreeResumeScenarios:
    """Verify concurrent resume operations work with persistent worktrees."""

    def test_concurrent_resumes_preserve_worktrees(self, git_repo):
        """
        Concurrent resume operations should preserve their worktrees after completion.
        """
        tmp_path, repo = git_repo
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        # Create initial failed runs with worktrees
        contexts = [_make_context(tmp_path, status=PipelineStatus.FAILED) for _ in range(NUM_WORKERS)]
        for ctx in contexts:
            ctx.branch_naming = "levelup/{run_id}"
            orch._create_git_branch(tmp_path, ctx)

        worktree_paths = [ctx.worktree_path for ctx in contexts]

        # Verify all worktrees exist before resume
        for wt_path in worktree_paths:
            assert wt_path.exists()

        with patch.object(orch, "_execute_steps") as mock_exec:
            with patch.object(orch, "_persist_state"):
                def resume_run(ctx: PipelineContext) -> PipelineContext:
                    ctx.status = PipelineStatus.COMPLETED
                    mock_exec.return_value = ctx
                    orch.resume(ctx)
                    return ctx

                with ThreadPoolExecutor(max_workers=NUM_WORKERS) as pool:
                    futures = [pool.submit(resume_run, ctx) for ctx in contexts]
                    results = [f.result() for f in as_completed(futures)]

        # All worktrees should still persist after concurrent resumes
        for ctx in results:
            assert ctx.worktree_path.exists(), (
                f"Worktree {ctx.worktree_path} should persist after concurrent resume"
            )

        # Cleanup
        for wt_path in worktree_paths:
            try:
                repo.git.worktree("remove", str(wt_path), "--force")
            except Exception:
                shutil.rmtree(wt_path, ignore_errors=True)


class TestConcurrentMixedStatusCompletions:
    """Verify worktrees persist with mixed completion statuses in concurrent scenarios."""

    def test_mixed_status_completions_all_persist_worktrees(self, git_repo):
        """
        Concurrent runs with mixed completion statuses should all persist their worktrees.
        """
        tmp_path, repo = git_repo
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        statuses = [
            PipelineStatus.COMPLETED,
            PipelineStatus.FAILED,
            PipelineStatus.ABORTED,
            PipelineStatus.PAUSED,
        ]

        contexts = [_make_context(tmp_path) for _ in range(NUM_WORKERS)]
        for i, ctx in enumerate(contexts):
            ctx.branch_naming = "levelup/{run_id}"
            ctx.status = statuses[i]

        with patch.object(orch, "_execute_steps") as mock_exec:
            with patch.object(orch, "_persist_state"):
                def create_and_run(ctx: PipelineContext) -> PipelineContext:
                    orch._create_git_branch(tmp_path, ctx)
                    mock_exec.return_value = ctx
                    task = TaskInput(title=f"Task {ctx.run_id}", description="Test")
                    orch.run(task)
                    return ctx

                with ThreadPoolExecutor(max_workers=NUM_WORKERS) as pool:
                    futures = [pool.submit(create_and_run, ctx) for ctx in contexts]
                    results = [f.result() for f in as_completed(futures)]

        # All worktrees should persist regardless of completion status
        for ctx in results:
            assert ctx.worktree_path.exists(), (
                f"Worktree {ctx.worktree_path} with status {ctx.status} should persist"
            )

        # Cleanup
        for ctx in results:
            try:
                repo.git.worktree("remove", str(ctx.worktree_path), "--force")
            except Exception:
                shutil.rmtree(ctx.worktree_path, ignore_errors=True)
