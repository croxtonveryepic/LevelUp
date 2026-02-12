"""Integration tests: concurrent headless pipelines, DB coordination, and checkpoint routing."""

from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import patch

import git
import pytest

from levelup.config.settings import (
    LevelUpSettings,
    LLMSettings,
    PipelineSettings,
    ProjectSettings,
)
from levelup.core.context import (
    PipelineContext,
    PipelineStatus,
    TaskInput,
)
from levelup.core.orchestrator import Orchestrator
from levelup.state.manager import StateManager

pytestmark = pytest.mark.regression


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NUM_WORKERS = 4


def _init_git_repo(tmp_path: Path) -> git.Repo:
    """Create a git repo with an initial commit."""
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    (tmp_path / "init.txt").write_text("init")
    repo.index.add(["init.txt"])
    repo.index.commit("initial commit")
    return repo


def _make_settings(
    tmp_path: Path,
    create_git_branch: bool = False,
    require_checkpoints: bool = False,
) -> LevelUpSettings:
    return LevelUpSettings(
        llm=LLMSettings(api_key="test-key", model="test-model", backend="claude_code"),
        project=ProjectSettings(path=tmp_path),
        pipeline=PipelineSettings(
            create_git_branch=create_git_branch,
            require_checkpoints=require_checkpoints,
            max_code_iterations=2,
        ),
    )


def _make_context(tmp_path: Path, run_id: str | None = None) -> PipelineContext:
    rid = run_id or uuid.uuid4().hex[:12]
    return PipelineContext(
        task=TaskInput(title=f"Task {rid}", description="Integration test"),
        project_path=tmp_path,
        status=PipelineStatus.RUNNING,
        run_id=rid,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConcurrentHeadlessPipelines:
    """Run multiple headless pipelines concurrently, verifying DB + worktree coordination."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_four_concurrent_pipelines_all_complete(
        self, mock_detect, mock_agent, tmp_path
    ):
        """4 headless pipelines with checkpoints all complete via an approver daemon."""
        repo = _init_git_repo(tmp_path)
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        stop_event = threading.Event()

        def approve_checkpoints():
            approver_mgr = StateManager(db_path=db_path)
            while not stop_event.is_set():
                pending = approver_mgr.get_pending_checkpoints()
                for cp in pending:
                    approver_mgr.submit_checkpoint_decision(
                        cp.id, "approve", ""  # type: ignore[arg-type]
                    )
                time.sleep(0.05)

        approver = threading.Thread(target=approve_checkpoints, daemon=True)
        approver.start()

        try:
            settings = _make_settings(
                tmp_path,
                create_git_branch=True,
                require_checkpoints=True,
            )

            def run_pipeline(task_id: int) -> PipelineContext:
                orch = Orchestrator(
                    settings=settings,
                    state_manager=StateManager(db_path=db_path),
                    headless=True,
                )
                task = TaskInput(
                    title=f"Concurrent task {task_id}",
                    description="Integration test",
                )
                return orch.run(task)

            with ThreadPoolExecutor(max_workers=NUM_WORKERS) as pool:
                futures = [pool.submit(run_pipeline, i) for i in range(NUM_WORKERS)]
                results = [f.result() for f in futures]

        finally:
            stop_event.set()
            approver.join(timeout=5)
            # Cleanup worktrees
            for ctx in results:
                if ctx.worktree_path and ctx.worktree_path.exists():
                    try:
                        repo.git.worktree("remove", str(ctx.worktree_path), "--force")
                    except Exception:
                        pass
            try:
                repo.git.worktree("prune")
            except Exception:
                pass

        # All 4 pipelines completed
        assert all(ctx.status == PipelineStatus.COMPLETED for ctx in results)

        # DB has 4 records
        records = mgr.list_runs()
        assert len(records) == NUM_WORKERS
        assert all(r.status == "completed" for r in records)

        # 4 distinct branches in the main repo
        head_names = [h.name for h in repo.heads]
        run_branches = [f"levelup/{ctx.run_id}" for ctx in results]
        for bn in run_branches:
            assert bn in head_names
        assert len(set(run_branches)) == NUM_WORKERS

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_four_concurrent_pipelines_no_checkpoints(
        self, mock_detect, mock_agent, tmp_path
    ):
        """4 headless pipelines without checkpoints all complete."""
        repo = _init_git_repo(tmp_path)
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        settings = _make_settings(
            tmp_path,
            create_git_branch=True,
            require_checkpoints=False,
        )

        def run_pipeline(task_id: int) -> PipelineContext:
            orch = Orchestrator(
                settings=settings,
                state_manager=StateManager(db_path=db_path),
                headless=True,
            )
            task = TaskInput(
                title=f"NoCP task {task_id}",
                description="Integration test",
            )
            return orch.run(task)

        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as pool:
            futures = [pool.submit(run_pipeline, i) for i in range(NUM_WORKERS)]
            results = [f.result() for f in futures]

        # Cleanup worktrees
        for ctx in results:
            if ctx.worktree_path and ctx.worktree_path.exists():
                try:
                    repo.git.worktree("remove", str(ctx.worktree_path), "--force")
                except Exception:
                    pass
        try:
            repo.git.worktree("prune")
        except Exception:
            pass

        assert all(ctx.status == PipelineStatus.COMPLETED for ctx in results)

        records = mgr.list_runs()
        assert len(records) == NUM_WORKERS
        assert all(r.status == "completed" for r in records)

        head_names = [h.name for h in repo.heads]
        run_branches = [f"levelup/{ctx.run_id}" for ctx in results]
        for bn in run_branches:
            assert bn in head_names

    def test_concurrent_state_registration_and_updates(self, tmp_path):
        """Concurrent register_run + update_run calls must not corrupt the DB."""
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        contexts = [_make_context(tmp_path) for _ in range(NUM_WORKERS)]

        # Register all concurrently
        def register(ctx: PipelineContext) -> str:
            m = StateManager(db_path=db_path)
            m.register_run(ctx)
            return ctx.run_id

        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as pool:
            futures = [pool.submit(register, ctx) for ctx in contexts]
            run_ids = [f.result() for f in futures]

        assert len(run_ids) == NUM_WORKERS
        records = mgr.list_runs()
        assert len(records) == NUM_WORKERS

        # Update all concurrently with different statuses
        target_statuses = [
            PipelineStatus.COMPLETED,
            PipelineStatus.FAILED,
            PipelineStatus.ABORTED,
            PipelineStatus.COMPLETED,
        ]

        def update(ctx_status: tuple[PipelineContext, PipelineStatus]) -> str:
            ctx, status = ctx_status
            ctx.status = status
            m = StateManager(db_path=db_path)
            m.update_run(ctx)
            return ctx.run_id

        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as pool:
            futures = [
                pool.submit(update, (ctx, st))
                for ctx, st in zip(contexts, target_statuses)
            ]
            for f in futures:
                f.result()

        # Verify each run got the correct status
        for ctx, expected in zip(contexts, target_statuses):
            record = mgr.get_run(ctx.run_id)
            assert record is not None
            assert record.status == expected.value

    def test_checkpoint_routing_four_waiting_runs(self, tmp_path):
        """Checkpoint decisions are routed to the correct run+step combo."""
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        contexts = [_make_context(tmp_path) for _ in range(NUM_WORKERS)]
        steps = ["requirements", "test_writing", "security", "review"]

        # Register runs
        for ctx in contexts:
            mgr.register_run(ctx)

        # Create checkpoint requests for different steps
        request_ids = {}
        for ctx, step in zip(contexts, steps):
            req_id = mgr.create_checkpoint_request(ctx.run_id, step, f"data-{step}")
            request_ids[(ctx.run_id, step)] = req_id

        # Submit decisions for each
        decisions = ["approve", "reject", "approve", "revise"]
        feedbacks = ["ok", "bad", "good", "change this"]
        for (ctx, step), decision, feedback in zip(
            zip(contexts, steps), decisions, feedbacks
        ):
            req_id = request_ids[(ctx.run_id, step)]
            mgr.submit_checkpoint_decision(req_id, decision, feedback)

        # Verify each run gets only its own decision
        for ctx, step, expected_decision, expected_feedback in zip(
            contexts, steps, decisions, feedbacks
        ):
            result = mgr.get_checkpoint_decision(ctx.run_id, step)
            assert result is not None, f"No decision for run={ctx.run_id}, step={step}"
            actual_decision, actual_feedback = result
            assert actual_decision == expected_decision
            assert actual_feedback == expected_feedback

        # Cross-check: no run gets another run's step decision
        for i, ctx in enumerate(contexts):
            for j, step in enumerate(steps):
                if i != j:
                    result = mgr.get_checkpoint_decision(ctx.run_id, step)
                    assert result is None, (
                        f"Run {ctx.run_id} should NOT have a decision for step {step}"
                    )

    def test_mark_dead_runs_with_multiple_active(self, tmp_path):
        """mark_dead_runs correctly identifies dead PIDs among multiple active runs."""
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        contexts = [_make_context(tmp_path) for _ in range(NUM_WORKERS)]
        for ctx in contexts:
            mgr.register_run(ctx)

        # Use fake PIDs — 2 "alive" and 2 "dead"
        fake_pids = [99990001, 99990002, 99990003, 99990004]
        alive_pids = {99990001, 99990003}

        # Manually set PIDs in the DB
        from levelup.state.db import get_connection

        conn = get_connection(db_path)
        try:
            for ctx, pid in zip(contexts, fake_pids):
                conn.execute("UPDATE runs SET pid = ? WHERE run_id = ?", (pid, ctx.run_id))
            conn.commit()
        finally:
            conn.close()

        # Mock _is_pid_alive
        with patch(
            "levelup.state.manager._is_pid_alive",
            side_effect=lambda pid: pid in alive_pids,
        ):
            dead_count = mgr.mark_dead_runs()

        assert dead_count == 2

        # Verify the right runs are marked
        for ctx, pid in zip(contexts, fake_pids):
            record = mgr.get_run(ctx.run_id)
            if pid in alive_pids:
                assert record.status == "running"
            else:
                assert record.status == "failed"
                assert record.error_message == "Process died"
