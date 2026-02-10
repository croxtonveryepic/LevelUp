"""Tests for concurrent worktree creation, isolation, commits, and cleanup."""

from __future__ import annotations

import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

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
        task=TaskInput(title="Add widget feature", description="Implement widget"),
        project_path=tmp_path,
        status=PipelineStatus.RUNNING,
        pre_run_sha=None,
        run_id=rid,
        **kwargs,
    )


def _force_remove_worktree(repo: git.Repo, ctx: PipelineContext) -> None:
    """Best-effort worktree removal — falls back to shutil on Windows lock errors."""
    if not ctx.worktree_path or not ctx.worktree_path.exists():
        return
    try:
        repo.git.worktree("remove", str(ctx.worktree_path), "--force")
    except Exception:
        shutil.rmtree(ctx.worktree_path, ignore_errors=True)


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
# Tests
# ---------------------------------------------------------------------------


class TestConcurrentWorktreeCreation:
    """Verify that 4+ worktrees can be created concurrently from the same repo."""

    def test_four_worktrees_created_from_same_repo(self, git_repo):
        """Create 4 worktrees concurrently; all should be distinct valid git repos."""
        tmp_path, repo = git_repo
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        contexts = [_make_context(tmp_path) for _ in range(NUM_WORKERS)]

        def create_wt(ctx: PipelineContext) -> PipelineContext:
            orch._create_git_branch(tmp_path, ctx)
            return ctx

        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as pool:
            futures = {pool.submit(create_wt, ctx): ctx for ctx in contexts}
            results = [f.result() for f in as_completed(futures)]

        try:
            # All worktree paths exist and are distinct
            wt_paths = [ctx.worktree_path for ctx in results]
            assert all(p is not None and p.exists() for p in wt_paths)
            assert len(set(wt_paths)) == NUM_WORKERS

            # Each worktree is a valid git repo
            for p in wt_paths:
                wt_repo = git.Repo(p)
                assert not wt_repo.bare

            # All branches exist in the main repo
            head_names = [h.name for h in repo.heads]
            for ctx in results:
                branch_name = f"levelup/{ctx.run_id}"
                assert branch_name in head_names

            # Main repo is still on its original branch
            assert repo.active_branch.name in ("master", "main")
        finally:
            for ctx in results:
                _force_remove_worktree(repo, ctx)

    def test_worktree_file_isolation(self, git_repo):
        """Files written in one worktree must not appear in others or the main repo."""
        tmp_path, repo = git_repo
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        contexts = [_make_context(tmp_path) for _ in range(NUM_WORKERS)]
        for ctx in contexts:
            orch._create_git_branch(tmp_path, ctx)

        try:
            # Write a unique file in each worktree
            for i, ctx in enumerate(contexts):
                (ctx.worktree_path / f"unique_{i}.txt").write_text(f"content_{i}")

            # Verify isolation: each file exists only in its own worktree
            for i, ctx in enumerate(contexts):
                assert (ctx.worktree_path / f"unique_{i}.txt").exists()

                # Must NOT exist in other worktrees
                for j, other in enumerate(contexts):
                    if i != j:
                        assert not (other.worktree_path / f"unique_{i}.txt").exists()

                # Must NOT exist in the main repo
                assert not (tmp_path / f"unique_{i}.txt").exists()
        finally:
            for ctx in contexts:
                _force_remove_worktree(repo, ctx)

    def test_step_commits_in_separate_worktrees_are_isolated(self, git_repo):
        """Commits in each worktree stay on their own branch and don't bleed.

        Note: git worktrees from the same parent share the .git directory, so
        on Windows, concurrent ``git commit`` calls contend on COMMIT_EDITMSG.
        We commit sequentially here; the point is *isolation* (each worktree's
        branch only sees its own commit), not parallelism of ``git commit``.
        """
        tmp_path, repo = git_repo
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        contexts = [_make_context(tmp_path) for _ in range(NUM_WORKERS)]
        for ctx in contexts:
            orch._create_git_branch(tmp_path, ctx)
            ctx.pre_run_sha = repo.head.commit.hexsha

        try:
            for i, ctx in enumerate(contexts):
                wt = ctx.worktree_path
                (wt / f"code_{i}.py").write_text(f"print('hello {i}')")
                orch._git_step_commit(wt, ctx, "coding")

            # Each worktree's branch has a coding commit
            for i, ctx in enumerate(contexts):
                assert "coding" in ctx.step_commits
                wt_repo = git.Repo(ctx.worktree_path)
                last_msg = wt_repo.head.commit.message
                assert last_msg.startswith("levelup(coding):")

            # Commits don't bleed between worktrees
            for i, ctx in enumerate(contexts):
                wt_repo = git.Repo(ctx.worktree_path)
                files_in_commit = wt_repo.head.commit.stats.files
                assert f"code_{i}.py" in files_in_commit
                for j in range(NUM_WORKERS):
                    if j != i:
                        assert f"code_{j}.py" not in files_in_commit
        finally:
            for ctx in contexts:
                _force_remove_worktree(repo, ctx)

    def test_concurrent_worktree_cleanup(self, git_repo):
        """Cleanup of 4 worktrees concurrently should remove all directories."""
        tmp_path, repo = git_repo
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        contexts = [_make_context(tmp_path) for _ in range(NUM_WORKERS)]
        for ctx in contexts:
            orch._create_git_branch(tmp_path, ctx)

        # All worktree dirs exist
        for ctx in contexts:
            assert ctx.worktree_path.exists()

        # Cleanup all concurrently
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as pool:
            futures = [pool.submit(orch._cleanup_worktree, tmp_path, ctx) for ctx in contexts]
            for f in futures:
                f.result()  # raise any exceptions

        # All worktree dirs should be gone
        for ctx in contexts:
            assert not ctx.worktree_path.exists()

        # But branches should still exist in the main repo
        head_names = [h.name for h in repo.heads]
        for ctx in contexts:
            branch_name = f"levelup/{ctx.run_id}"
            assert branch_name in head_names

    def test_four_branches_have_unique_names(self, git_repo):
        """Each worktree gets a distinctly named branch."""
        tmp_path, repo = git_repo
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        contexts = [_make_context(tmp_path) for _ in range(NUM_WORKERS)]
        for ctx in contexts:
            orch._create_git_branch(tmp_path, ctx)

        try:
            branch_names = [f"levelup/{ctx.run_id}" for ctx in contexts]
            # All unique
            assert len(set(branch_names)) == NUM_WORKERS

            # All present in the repo
            head_names = [h.name for h in repo.heads]
            for bn in branch_names:
                assert bn in head_names
        finally:
            for ctx in contexts:
                _force_remove_worktree(repo, ctx)
