"""MergeAgent - standalone agent for intelligently merging feature branches into master."""

from __future__ import annotations

import logging
from pathlib import Path

from levelup.agents.backend import AgentResult, Backend

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior software engineer managing git merges for a development team.

Your task is to rebase a feature branch onto master, intelligently resolve any conflicts, and complete the merge.

**Git workflow:**
1. First, verify the branch exists using `git branch --list <branch-name>`
2. Checkout the feature branch: `git checkout <branch-name>`
3. Rebase onto master: `git rebase master`
4. If conflicts occur:
   - Detect conflict markers (<<<<<<< ======= >>>>>>>)
   - Use Read tool to examine the conflicted file
   - For project_context.md conflicts, intelligently merge Codebase Insights sections by preserving information from both branches
   - Use Edit tool to resolve conflicts and remove markers
   - Stage the resolved file: `git add <file>`
   - Continue the rebase: `git rebase --continue`
   - Repeat for multiple conflict rounds if necessary
5. After successful rebase, checkout master: `git checkout master`
6. Merge the rebased branch (fast-forward): `git merge <branch-name>`
7. Optionally delete the feature branch: `git branch -d <branch-name>`

**Error handling:**
- If the branch does not exist, return an error message and do NOT attempt git operations
- If rebase fails and conflicts cannot be auto-resolved, abort with: `git rebase --abort`
- If merge fails, abort with: `git merge --abort`
- Always preserve repository integrity - never leave the repo in a partial/broken state
- Ensure the repository is left in a clean state after any errors

**Important:**
- Work in the main repository (not a worktree)
- Be thorough but decisive when resolving conflicts
- For project_context.md, combine insights from both branches intelligently

Return a clear success or error message when complete."""

def _format_user_prompt(branch_name: str | None) -> str:
    """Format the user prompt for the merge agent."""
    if not branch_name:
        return "Error: No branch name provided. Cannot proceed with merge."

    return f"""Merge the feature branch '{branch_name}' into master.

Follow the git workflow:
1. Verify branch '{branch_name}' exists
2. Checkout '{branch_name}'
3. Rebase onto master (resolve conflicts if needed)
4. Checkout master
5. Merge '{branch_name}' (fast-forward)
6. Optionally delete '{branch_name}'

If any step fails, abort gracefully and return an error message.
If successful, return a success message."""


class MergeAgent:
    """Standalone agent for merging feature branches into master.

    Similar to ReconAgent, this agent does not inherit from BaseAgent
    since it doesn't participate in the main TDD pipeline.
    """

    def __init__(self, backend: Backend, project_path: Path) -> None:
        self.backend = backend
        self.project_path = project_path

    def get_system_prompt(self) -> str:
        """Return the system prompt for the merge agent."""
        return SYSTEM_PROMPT

    def get_allowed_tools(self) -> list[str]:
        """Return the list of allowed tools for the merge agent."""
        return ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]

    def run(self, branch_name: str | None = None) -> AgentResult:
        """Run the merge agent and return usage metrics.

        Args:
            branch_name: The name of the feature branch to merge.

        Returns:
            AgentResult with text response and usage metrics.
        """
        system_prompt = self.get_system_prompt()
        user_prompt = _format_user_prompt(branch_name)

        result = self.backend.run_agent(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            allowed_tools=self.get_allowed_tools(),
            working_directory=str(self.project_path),
        )
        return result
