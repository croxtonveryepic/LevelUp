"""Unit tests for MergeAgent (src/levelup/agents/merge.py).

The MergeAgent is a standalone agent (like ReconAgent) that intelligently
rebases feature branches onto master, resolves conflicts in project_context.md,
and completes the merge. It does not inherit from BaseAgent since it doesn't
participate in the main TDD pipeline.

These tests follow TDD approach - they SHOULD FAIL initially until the
implementation is complete.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from levelup.agents.backend import AgentResult


# ===========================================================================
# MergeAgent - Initialization Tests
# ===========================================================================


class TestMergeAgentInit:
    """Test MergeAgent initialization and constructor.

    AC: Agent follows the BaseAgent pattern with __init__(backend, project_path)
    AC: Agent can be instantiated and run independently (not part of main TDD pipeline)
    """

    def test_stores_backend_and_path(self, tmp_path: Path):
        """Agent should store backend and project_path on initialization."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        assert agent.backend is backend
        assert agent.project_path == tmp_path

    def test_initializes_without_ticket_metadata(self, tmp_path: Path):
        """Agent should initialize successfully without ticket metadata."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        # Should not raise
        assert agent is not None


# ===========================================================================
# MergeAgent - System Prompt Tests
# ===========================================================================


class TestMergeAgentSystemPrompt:
    """Test MergeAgent system prompt generation.

    AC: Agent has a system prompt that describes its merge/rebase/conflict resolution role
    """

    def test_get_system_prompt_contains_merge_instructions(self, tmp_path: Path):
        """System prompt should contain instructions for merge operations."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert isinstance(prompt, str)
        assert "merge" in prompt.lower() or "rebase" in prompt.lower()
        assert "conflict" in prompt.lower()

    def test_get_system_prompt_mentions_project_context(self, tmp_path: Path):
        """System prompt should mention project_context.md conflict resolution."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "project_context.md" in prompt.lower() or "project context" in prompt.lower()


# ===========================================================================
# MergeAgent - Allowed Tools Tests
# ===========================================================================


class TestMergeAgentAllowedTools:
    """Test MergeAgent allowed tools.

    AC: Allowed tools include Read, Write, Edit, Glob, Grep, Bash for git operations
    """

    def test_get_allowed_tools_includes_read_write_edit(self, tmp_path: Path):
        """Agent should have Read, Write, Edit tools for file operations."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        tools = agent.get_allowed_tools()

        assert "Read" in tools
        assert "Write" in tools
        assert "Edit" in tools

    def test_get_allowed_tools_includes_bash(self, tmp_path: Path):
        """Agent should have Bash tool for git commands."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        tools = agent.get_allowed_tools()

        assert "Bash" in tools

    def test_get_allowed_tools_includes_glob_grep(self, tmp_path: Path):
        """Agent should have Glob and Grep tools for finding files."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        tools = agent.get_allowed_tools()

        assert "Glob" in tools
        assert "Grep" in tools


# ===========================================================================
# MergeAgent - Run Method Tests
# ===========================================================================


class TestMergeAgentRun:
    """Test MergeAgent.run() method.

    AC: Returns AgentResult (not tuple[PipelineContext, AgentResult])
    AC: Agent runs in main repository (project_path), not in worktree
    """

    def test_run_returns_agent_result(self, tmp_path: Path):
        """run() should return AgentResult directly (not tuple)."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        expected = AgentResult(text="merge complete", cost_usd=0.01)
        backend.run_agent.return_value = expected

        agent = MergeAgent(backend, tmp_path)
        result = agent.run(branch_name="feature/test")

        assert isinstance(result, AgentResult)
        assert result is expected

    def test_run_calls_backend_with_project_path(self, tmp_path: Path):
        """run() should call backend.run_agent with project_path as working_directory."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        backend.run_agent.return_value = AgentResult(text="done")

        agent = MergeAgent(backend, tmp_path)
        agent.run(branch_name="feature/test")

        backend.run_agent.assert_called_once()
        call_kwargs = backend.run_agent.call_args.kwargs
        assert call_kwargs["working_directory"] == str(tmp_path)

    def test_run_calls_backend_with_system_and_user_prompts(self, tmp_path: Path):
        """run() should call backend with system_prompt and user_prompt."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        backend.run_agent.return_value = AgentResult(text="done")

        agent = MergeAgent(backend, tmp_path)
        agent.run(branch_name="feature/auth")

        call_kwargs = backend.run_agent.call_args.kwargs
        assert "system_prompt" in call_kwargs
        assert "user_prompt" in call_kwargs
        assert "feature/auth" in call_kwargs["user_prompt"]

    def test_run_includes_branch_name_in_user_prompt(self, tmp_path: Path):
        """run() user prompt should include the branch name to merge."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        backend.run_agent.return_value = AgentResult(text="done")

        agent = MergeAgent(backend, tmp_path)
        agent.run(branch_name="feature/dark-mode")

        user_prompt = backend.run_agent.call_args.kwargs["user_prompt"]
        assert "feature/dark-mode" in user_prompt


# ===========================================================================
# MergeAgent - Branch Validation Tests
# ===========================================================================


class TestMergeAgentBranchValidation:
    """Test MergeAgent branch name validation.

    AC: If branch_name not provided, returns error in AgentResult
    AC: Validates git branch exists before attempting operations
    """

    def test_run_requires_branch_name(self, tmp_path: Path):
        """run() should require branch_name parameter."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        backend.run_agent.return_value = AgentResult(text="error: no branch specified")

        agent = MergeAgent(backend, tmp_path)

        # Should include instruction to check for branch_name in system prompt
        result = agent.run(branch_name=None)

        # Agent should handle this via prompt, or method should validate
        assert result is not None

    def test_run_validates_branch_existence_via_prompt(self, tmp_path: Path):
        """User prompt should instruct agent to validate branch exists."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        backend.run_agent.return_value = AgentResult(text="done")

        agent = MergeAgent(backend, tmp_path)
        agent.run(branch_name="feature/nonexistent")

        user_prompt = backend.run_agent.call_args.kwargs["user_prompt"]
        # Prompt should instruct agent to validate branch exists
        assert "branch" in user_prompt.lower()


# ===========================================================================
# MergeAgent - Git Operations Tests
# ===========================================================================


class TestMergeAgentGitOperations:
    """Test MergeAgent git operations workflow.

    AC: Executes 'git checkout <branch>' to switch to feature branch
    AC: Executes 'git rebase master' to rebase onto latest master
    AC: After successful rebase, executes 'git checkout master'
    AC: Executes fast-forward merge 'git merge <branch>'
    AC: Optionally deletes feature branch with 'git branch -d <branch>'
    """

    def test_system_prompt_instructs_git_checkout_branch(self, tmp_path: Path):
        """System prompt should instruct agent to checkout feature branch."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "git checkout" in prompt.lower() or "checkout" in prompt.lower()

    def test_system_prompt_instructs_git_rebase(self, tmp_path: Path):
        """System prompt should instruct agent to rebase onto master."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "rebase" in prompt.lower()
        assert "master" in prompt.lower()

    def test_system_prompt_instructs_fast_forward_merge(self, tmp_path: Path):
        """System prompt should instruct agent to fast-forward merge after rebase."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "merge" in prompt.lower()

    def test_system_prompt_mentions_branch_cleanup(self, tmp_path: Path):
        """System prompt should mention optional branch deletion after merge."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "branch -d" in prompt.lower() or "delete" in prompt.lower()


# ===========================================================================
# MergeAgent - Conflict Resolution Tests
# ===========================================================================


class TestMergeAgentConflictResolution:
    """Test MergeAgent conflict resolution capabilities.

    AC: On rebase conflicts, agent detects and enters conflict resolution mode
    AC: Agent detects conflict markers in project_context.md
    AC: Uses Read tool to examine both sides of the conflict
    AC: Makes reasonable decisions to preserve information from both branches
    AC: For project_context.md conflicts, merges Codebase Insights sections intelligently
    AC: Uses Edit tool to remove conflict markers and create unified content
    AC: Executes 'git add project_context.md' after resolving
    AC: Continues rebase with 'git rebase --continue'
    AC: Handles multiple conflict rounds if necessary
    """

    def test_system_prompt_instructs_conflict_detection(self, tmp_path: Path):
        """System prompt should instruct agent to detect rebase conflicts."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "conflict" in prompt.lower()

    def test_system_prompt_instructs_conflict_marker_detection(self, tmp_path: Path):
        """System prompt should mention conflict markers (<<<<<<< ======= >>>>>>>)."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        # Should mention conflict markers or detection strategy
        assert "<<<" in prompt or "conflict marker" in prompt.lower()

    def test_system_prompt_instructs_project_context_merging(self, tmp_path: Path):
        """System prompt should specifically instruct on project_context.md merging."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "project_context.md" in prompt or "project context" in prompt.lower()
        assert "codebase insights" in prompt.lower() or "insights" in prompt.lower()

    def test_system_prompt_instructs_read_tool_usage(self, tmp_path: Path):
        """System prompt should instruct using Read tool to examine conflicts."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "read" in prompt.lower()

    def test_system_prompt_instructs_edit_tool_usage(self, tmp_path: Path):
        """System prompt should instruct using Edit tool to resolve conflicts."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "edit" in prompt.lower()

    def test_system_prompt_instructs_git_add_after_resolution(self, tmp_path: Path):
        """System prompt should instruct 'git add' after resolving conflicts."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "git add" in prompt.lower()

    def test_system_prompt_instructs_rebase_continue(self, tmp_path: Path):
        """System prompt should instruct 'git rebase --continue' after resolution."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "rebase --continue" in prompt.lower() or "continue" in prompt.lower()

    def test_system_prompt_instructs_multiple_conflict_rounds(self, tmp_path: Path):
        """System prompt should mention handling multiple conflict rounds."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        # Should mention possibility of multiple conflicts
        assert "multiple" in prompt.lower() or "rounds" in prompt.lower() or "repeat" in prompt.lower()


# ===========================================================================
# MergeAgent - Error Handling Tests
# ===========================================================================


class TestMergeAgentErrorHandling:
    """Test MergeAgent error handling.

    AC: If branch does not exist, returns error without attempting operations
    AC: If rebase fails and conflicts cannot be auto-resolved, aborts rebase and returns error
    AC: If merge fails, aborts merge and returns error
    AC: All error states preserve repository integrity (no partial merges)
    AC: Error messages are clear and actionable for the user
    """

    def test_system_prompt_instructs_error_handling(self, tmp_path: Path):
        """System prompt should instruct proper error handling."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "error" in prompt.lower()

    def test_system_prompt_instructs_rebase_abort_on_failure(self, tmp_path: Path):
        """System prompt should instruct 'git rebase --abort' on unresolvable conflicts."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "rebase --abort" in prompt.lower() or "abort" in prompt.lower()

    def test_system_prompt_instructs_merge_abort_on_failure(self, tmp_path: Path):
        """System prompt should instruct 'git merge --abort' on merge failure."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        assert "merge --abort" in prompt.lower() or "abort" in prompt.lower()

    def test_system_prompt_emphasizes_repository_integrity(self, tmp_path: Path):
        """System prompt should emphasize preserving repository integrity."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        agent = MergeAgent(backend, tmp_path)

        prompt = agent.get_system_prompt()

        # Should mention not leaving repo in partial/broken state
        assert "integrity" in prompt.lower() or "clean" in prompt.lower() or "state" in prompt.lower()

    def test_run_preserves_cost_and_token_info_on_error(self, tmp_path: Path):
        """run() should preserve cost/token info even on error."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        error_result = AgentResult(
            text="error: branch does not exist",
            cost_usd=0.02,
            input_tokens=500,
            output_tokens=100,
        )
        backend.run_agent.return_value = error_result

        agent = MergeAgent(backend, tmp_path)
        result = agent.run(branch_name="feature/missing")

        assert result.cost_usd == 0.02
        assert result.input_tokens == 500
        assert result.output_tokens == 100


# ===========================================================================
# MergeAgent - Success Scenarios Tests
# ===========================================================================


class TestMergeAgentSuccessScenarios:
    """Test MergeAgent success scenarios.

    AC: Handles rebase success case by proceeding to merge
    AC: Verifies merge succeeded by checking git status
    AC: Returns success status in AgentResult
    """

    def test_run_returns_success_on_clean_merge(self, tmp_path: Path):
        """run() should return successful AgentResult on clean merge."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        success_result = AgentResult(
            text="Merge completed successfully. Branch merged into master.",
            cost_usd=0.05,
        )
        backend.run_agent.return_value = success_result

        agent = MergeAgent(backend, tmp_path)
        result = agent.run(branch_name="feature/auth")

        assert result.text is not None
        assert "success" in result.text.lower() or "completed" in result.text.lower()

    def test_run_returns_success_after_conflict_resolution(self, tmp_path: Path):
        """run() should return successful AgentResult after resolving conflicts."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        success_result = AgentResult(
            text="Conflicts resolved in project_context.md. Merge completed.",
            cost_usd=0.08,
        )
        backend.run_agent.return_value = success_result

        agent = MergeAgent(backend, tmp_path)
        result = agent.run(branch_name="feature/ui-update")

        assert result.text is not None
        assert "conflict" in result.text.lower() and "resolved" in result.text.lower()


# ===========================================================================
# MergeAgent - Integration with Ticket Metadata Tests
# ===========================================================================


class TestMergeAgentTicketMetadata:
    """Test MergeAgent interaction with ticket metadata.

    AC: Agent retrieves branch name from ticket metadata (branch_name field)
    """

    def test_accepts_branch_name_parameter(self, tmp_path: Path):
        """run() should accept branch_name as parameter (from ticket metadata)."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        backend.run_agent.return_value = AgentResult(text="done")

        agent = MergeAgent(backend, tmp_path)

        # Should not raise
        result = agent.run(branch_name="levelup/123-add-feature")
        assert result is not None

    def test_user_prompt_includes_branch_from_metadata(self, tmp_path: Path):
        """User prompt should include the branch_name passed from ticket metadata."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        backend.run_agent.return_value = AgentResult(text="done")

        agent = MergeAgent(backend, tmp_path)
        agent.run(branch_name="levelup/456-fix-bug")

        user_prompt = backend.run_agent.call_args.kwargs["user_prompt"]
        assert "levelup/456-fix-bug" in user_prompt


# ===========================================================================
# Edge Cases and Boundary Conditions
# ===========================================================================


class TestMergeAgentEdgeCases:
    """Test edge cases and boundary conditions for MergeAgent."""

    def test_handles_branch_name_with_special_characters(self, tmp_path: Path):
        """Agent should handle branch names with slashes, dashes, underscores."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        backend.run_agent.return_value = AgentResult(text="done")

        agent = MergeAgent(backend, tmp_path)

        # Should not raise
        result = agent.run(branch_name="feature/add-user_auth-2024")
        assert result is not None

    def test_handles_empty_branch_name(self, tmp_path: Path):
        """Agent should handle empty branch name gracefully."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        backend.run_agent.return_value = AgentResult(text="error: empty branch name")

        agent = MergeAgent(backend, tmp_path)
        result = agent.run(branch_name="")

        # Should return result (agent will handle validation)
        assert result is not None

    def test_preserves_working_directory_on_error(self, tmp_path: Path):
        """Agent should not change working directory on error."""
        from levelup.agents.merge import MergeAgent

        backend = MagicMock()
        backend.run_agent.return_value = AgentResult(text="error occurred")

        agent = MergeAgent(backend, tmp_path)
        result = agent.run(branch_name="feature/test")

        # Working directory should still be project_path
        call_kwargs = backend.run_agent.call_args.kwargs
        assert call_kwargs["working_directory"] == str(tmp_path)
