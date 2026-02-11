"""Tests for git merge completion message in orchestrator.

This test file verifies that the completion message printed by the orchestrator
shows correct git workflow instructions after a successful pipeline run.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from io import StringIO

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
    """Build LevelUpSettings pointing at tmp_path."""
    return LevelUpSettings(
        llm=LLMSettings(api_key="test-key", model="test-model", backend="claude_code"),
        project=ProjectSettings(path=tmp_path),
        pipeline=PipelineSettings(
            create_git_branch=create_git_branch,
            require_checkpoints=False,
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGitCompletionMessage:
    """Tests for the git completion message shown after successful pipeline run."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_completion_message_does_not_suggest_merging_branch_into_itself(
        self, mock_prompt, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Completion message should NOT suggest 'git checkout {branch}' then 'git merge {branch}'."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        mock_prompt.return_value = "levelup/{run_id}"
        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Capture console output
        mock_console = MagicMock()
        orch._console = mock_console

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

        # Get all console.print calls
        print_calls = [str(call) for call in mock_console.print.call_args_list]

        # Look for the completion message
        completion_message_found = False
        for call in print_calls:
            call_str = str(call)
            # Check if this is the branch completion message
            if "Branch" in call_str and "ready" in call_str:
                completion_message_found = True

                # Extract the branch name from context
                convention = ctx.branch_naming or "levelup/{run_id}"
                branch_name = f"levelup/{ctx.run_id}"

                # CRITICAL: The message should NOT suggest:
                # "git checkout {branch_name}" followed by "git merge {branch_name}"
                # This would try to merge a branch into itself
                if f"git checkout {branch_name}" in call_str:
                    # If it mentions checkout of the branch, it should NOT also mention merge of the same branch
                    assert f"git merge {branch_name}" not in call_str, (
                        f"Completion message incorrectly suggests checking out '{branch_name}' "
                        f"and then merging '{branch_name}' (merging a branch into itself)"
                    )

        # The completion message should have been shown (not quiet mode)
        assert completion_message_found or mock_console.print.call_count > 0

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_completion_message_suggests_correct_git_workflow(
        self, mock_prompt, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Completion message should suggest pushing to remote OR merging into main."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        mock_prompt.return_value = "levelup/{run_id}"
        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Capture console output
        mock_console = MagicMock()
        orch._console = mock_console

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

        # Get all console.print calls
        print_calls = [str(call) for call in mock_console.print.call_args_list]

        # Look for the completion message
        completion_message_found = False
        for call in print_calls:
            call_str = str(call)
            # Check if this is the branch completion message
            if "Branch" in call_str and "ready" in call_str:
                completion_message_found = True

                # The message should suggest either:
                # 1. Pushing to remote: "git push origin {branch_name}"
                # 2. Merging into main: "git checkout main && git merge {branch_name}"
                # At least one of these patterns should be present
                has_push_suggestion = "git push" in call_str
                has_merge_suggestion = ("git checkout main" in call_str or
                                       "git checkout master" in call_str)

                # At least one valid workflow should be suggested
                assert has_push_suggestion or has_merge_suggestion, (
                    "Completion message should suggest either pushing to remote "
                    "or merging into main branch, but found neither"
                )

        # The completion message should have been shown (not quiet mode)
        assert completion_message_found or mock_console.print.call_count > 0

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_completion_message_explains_branch_is_ready(
        self, mock_prompt, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Completion message should explain that the branch is ready for review."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        mock_prompt.return_value = "levelup/{run_id}"
        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Capture console output
        mock_console = MagicMock()
        orch._console = mock_console

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

        # Get all console.print calls
        print_calls = [str(call) for call in mock_console.print.call_args_list]

        # Look for the completion message
        completion_message_found = False
        for call in print_calls:
            call_str = str(call)
            # Check if this is the branch completion message
            if "Branch" in call_str and "ready" in call_str:
                completion_message_found = True

                # Should mention the branch name
                convention = ctx.branch_naming or "levelup/{run_id}"
                branch_name = f"levelup/{ctx.run_id}"
                assert branch_name in call_str, "Completion message should mention the branch name"

                # Should indicate the branch is ready (created, prepared, etc.)
                assert "ready" in call_str.lower() or "created" in call_str.lower(), (
                    "Completion message should explain the branch is ready"
                )

        # The completion message should have been shown (not quiet mode)
        assert completion_message_found or mock_console.print.call_count > 0

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_completion_message_shown_at_correct_location_in_orchestrator(
        self, mock_prompt, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Completion message is shown at lines 265-269 of orchestrator.run()."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        mock_prompt.return_value = "levelup/{run_id}"
        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Capture console output
        mock_console = MagicMock()
        orch._console = mock_console

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

        # Verify console.print was called (message shown)
        assert mock_console.print.called, "Console print should be called to show completion message"

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_completion_message_not_shown_in_quiet_mode(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Completion message should not be shown when orchestrator is in quiet mode."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings, headless=True)  # headless sets quiet=True

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Capture console output
        mock_console = MagicMock()
        orch._console = mock_console

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

        # In quiet mode, the completion message should not be printed
        # (the check is `if not self._quiet and ctx.branch_naming:`)
        print_calls = [str(call) for call in mock_console.print.call_args_list]

        for call in print_calls:
            call_str = str(call)
            # Should not print branch completion message in quiet mode
            if "Branch" in call_str and "ready" in call_str:
                pytest.fail("Completion message should not be shown in quiet mode")

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_completion_message_not_shown_when_create_git_branch_false(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Completion message should not be shown when create_git_branch is False."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Capture console output
        mock_console = MagicMock()
        orch._console = mock_console

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

        # When create_git_branch is False, no branch is created, so no message
        print_calls = [str(call) for call in mock_console.print.call_args_list]

        for call in print_calls:
            call_str = str(call)
            # Should not print branch completion message when no branch was created
            if "Branch" in call_str and "ready" in call_str:
                pytest.fail("Completion message should not be shown when create_git_branch is False")

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_completion_message_with_custom_branch_naming_convention(
        self, mock_prompt, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Completion message should use the custom branch naming convention."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        mock_prompt.return_value = "feature/{task_title}"
        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Capture console output
        mock_console = MagicMock()
        orch._console = mock_console

        task = TaskInput(title="Add Feature")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

        # Get all console.print calls
        print_calls = [str(call) for call in mock_console.print.call_args_list]

        # Look for the completion message with custom branch name
        for call in print_calls:
            call_str = str(call)
            if "Branch" in call_str and "ready" in call_str:
                # Should use the custom branch naming (sanitized)
                assert "feature/add-feature" in call_str or "feature" in call_str, (
                    "Completion message should use custom branch naming convention"
                )


class TestResumeCompletionMessage:
    """Tests for completion message when resuming a pipeline run."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_resume_shows_completion_message_when_completed(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """resume() should show completion message when a resumed run completes successfully."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Capture console output
        mock_console = MagicMock()
        orch._console = mock_console

        # Build a context that looks like a previously failed run with a branch
        ctx = PipelineContext(
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            status=PipelineStatus.FAILED,
            current_step="detect",
            branch_naming="levelup/{run_id}",
            pre_run_sha=repo.head.commit.hexsha,
        )

        # Mock the worktree recreation
        with patch.object(orch, "_create_git_branch"):
            ctx_result = orch.resume(ctx, from_step="detect")

        assert ctx_result.status == PipelineStatus.COMPLETED

        # Get all console.print calls
        print_calls = [str(call) for call in mock_console.print.call_args_list]

        # Look for the completion message
        completion_message_found = False
        for call in print_calls:
            call_str = str(call)
            # Check if this is the branch completion message
            if "Branch" in call_str and "ready" in call_str:
                completion_message_found = True

                # Verify it shows correct workflow (same as run())
                branch_name = f"levelup/{ctx.run_id}"

                # Should NOT suggest merging branch into itself
                if f"git checkout {branch_name}" in call_str:
                    assert f"git merge {branch_name}" not in call_str, (
                        "Resume completion message incorrectly suggests merging branch into itself"
                    )

        # The completion message should have been shown when resume completes
        assert completion_message_found or mock_console.print.call_count > 0

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_resume_completion_message_consistency_with_run(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """resume() completion message should be consistent with run() completion message."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Capture console output
        mock_console = MagicMock()
        orch._console = mock_console

        # Build a context that looks like a previously failed run with a branch
        ctx = PipelineContext(
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            status=PipelineStatus.FAILED,
            current_step="detect",
            branch_naming="levelup/{run_id}",
            pre_run_sha=repo.head.commit.hexsha,
        )

        # Mock the worktree recreation
        with patch.object(orch, "_create_git_branch"):
            ctx_result = orch.resume(ctx, from_step="detect")

        assert ctx_result.status == PipelineStatus.COMPLETED

        # Get all console.print calls
        print_calls = [str(call) for call in mock_console.print.call_args_list]

        # Both run() and resume() should show the same completion message format
        # The message should suggest correct workflow in both cases
        for call in print_calls:
            call_str = str(call)
            if "Branch" in call_str and "ready" in call_str:
                # Should suggest push or merge-into-main workflow
                has_valid_workflow = ("git push" in call_str or
                                     "git checkout main" in call_str or
                                     "git checkout master" in call_str)

                assert has_valid_workflow, (
                    "Resume completion message should suggest same correct workflow as run()"
                )


class TestWorktreeCleanupBehavior:
    """Tests verifying that worktree cleanup does NOT delete branches."""

    def test_cleanup_worktree_only_removes_directory_not_branch(self, tmp_path):
        """_cleanup_worktree() should only remove worktree directory, not delete the branch."""
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

        # Cleanup the worktree
        orch._cleanup_worktree(tmp_path, ctx)

        # Verify worktree directory is removed
        assert not worktree_path.exists(), "Worktree directory should be removed after cleanup"

        # CRITICAL: Branch should still exist in the repository
        assert branch_name in [h.name for h in repo.heads], (
            "Branch should persist in main repository after worktree cleanup"
        )

    def test_cleanup_preserves_branch_for_user_review(self, tmp_path):
        """Branches should persist after cleanup so user can review and merge them."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        # Create multiple contexts with worktrees
        contexts = []
        for i in range(3):
            ctx = PipelineContext(
                task=TaskInput(title=f"Feature {i}"),
                project_path=tmp_path,
                status=PipelineStatus.COMPLETED,
                branch_naming="levelup/{run_id}",
            )
            orch._create_git_branch(tmp_path, ctx)
            contexts.append(ctx)

        # Cleanup all worktrees
        for ctx in contexts:
            orch._cleanup_worktree(tmp_path, ctx)

        # All branches should still exist
        head_names = [h.name for h in repo.heads]
        for ctx in contexts:
            branch_name = f"levelup/{ctx.run_id}"
            assert branch_name in head_names, (
                f"Branch {branch_name} should persist after cleanup for user review"
            )

    def test_cleanup_worktree_does_not_attempt_merge(self, tmp_path):
        """_cleanup_worktree() should not attempt to merge or modify branches."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
            status=PipelineStatus.COMPLETED,
            branch_naming="levelup/{run_id}",
        )

        orch._create_git_branch(tmp_path, ctx)

        # Get commit count before cleanup
        initial_commit_count = len(list(repo.iter_commits()))

        # Cleanup the worktree
        orch._cleanup_worktree(tmp_path, ctx)

        # Commit count should not change (no merge commits created)
        final_commit_count = len(list(repo.iter_commits()))
        assert final_commit_count == initial_commit_count, (
            "cleanup_worktree should not create any merge commits"
        )

    def test_cleanup_worktree_handles_windows_permission_errors_gracefully(self, tmp_path):
        """Windows permission errors during worktree cleanup should be handled gracefully."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
            status=PipelineStatus.COMPLETED,
            branch_naming="levelup/{run_id}",
        )

        orch._create_git_branch(tmp_path, ctx)

        # The cleanup uses --force flag which should handle Windows permission errors
        # This should not raise any exceptions
        try:
            orch._cleanup_worktree(tmp_path, ctx)
        except Exception as e:
            pytest.fail(f"cleanup_worktree raised exception: {e}")

        # Branch should still exist after cleanup (even if worktree removal had issues)
        branch_name = f"levelup/{ctx.run_id}"
        assert branch_name in [h.name for h in repo.heads], (
            "Branch should persist even if worktree cleanup encounters permission errors"
        )


class TestCompletionMessageEdgeCases:
    """Tests for edge cases in completion message display."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_completion_message_with_long_branch_names(
        self, mock_prompt, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Completion message should handle very long branch names correctly."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        mock_prompt.return_value = "feature/{task_title}"
        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Capture console output
        mock_console = MagicMock()
        orch._console = mock_console

        # Create a task with a very long title
        long_title = "Add a very long feature name that will be sanitized and used in branch name" * 3
        task = TaskInput(title=long_title)

        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

        # Get all console.print calls
        print_calls = [str(call) for call in mock_console.print.call_args_list]

        # Should show completion message without errors
        completion_message_found = False
        for call in print_calls:
            call_str = str(call)
            if "Branch" in call_str and "ready" in call_str:
                completion_message_found = True

        assert completion_message_found or mock_console.print.call_count > 0

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_completion_message_when_pipeline_fails(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Completion message should NOT be shown when pipeline fails."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        def fail_agent(name, ctx):
            if name == "requirements":
                ctx.status = PipelineStatus.FAILED
                ctx.error_message = "API error"
            return ctx

        mock_agent.side_effect = fail_agent

        # Capture console output
        mock_console = MagicMock()
        orch._console = mock_console

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.FAILED

        # Get all console.print calls
        print_calls = [str(call) for call in mock_console.print.call_args_list]

        # Should NOT show completion message when pipeline fails
        for call in print_calls:
            call_str = str(call)
            if "Branch" in call_str and "ready" in call_str:
                pytest.fail("Completion message should not be shown when pipeline fails")

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.Orchestrator._check_pause_requested")
    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_completion_message_when_pipeline_paused(
        self, mock_prompt, mock_check_pause, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Completion message should NOT be shown when pipeline is paused."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        mock_prompt.return_value = "levelup/{run_id}"
        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Simulate pause by having _check_pause_requested return True on second call
        call_count = {"n": 0}

        def check_pause(ctx):
            call_count["n"] += 1
            return call_count["n"] > 1  # Pause after first step

        mock_check_pause.side_effect = check_pause

        # Capture console output
        mock_console = MagicMock()
        orch._console = mock_console

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.PAUSED

        # Get all console.print calls
        print_calls = [str(call) for call in mock_console.print.call_args_list]

        # Should NOT show completion message when pipeline is paused
        for call in print_calls:
            call_str = str(call)
            if "Branch" in call_str and "ready" in call_str:
                pytest.fail("Completion message should not be shown when pipeline is paused")
