"""Pipeline orchestrator - the heart of LevelUp."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from pathlib import Path

from rich.console import Console

from levelup.agents.backend import AgentResult, AnthropicSDKBackend, Backend, ClaudeCodeBackend
from levelup.agents.base import BaseAgent
from levelup.agents.claude_code_client import ClaudeCodeClient, ClaudeCodeError
from levelup.agents.coder import CodeAgent
from levelup.agents.llm_client import LLMClient
from levelup.agents.planning import PlanningAgent
from levelup.agents.requirements import RequirementsAgent
from levelup.agents.reviewer import ReviewAgent
from levelup.agents.security import SecurityAgent
from levelup.agents.test_writer import TestWriterAgent
from levelup.cli.display import (
    print_error,
    print_pipeline_summary,
    print_step_header,
    print_success,
)
from levelup.config.settings import LevelUpSettings
from levelup.core.checkpoint import build_checkpoint_display_data, run_checkpoint
from levelup.core.context import (
    CheckpointDecision,
    PipelineContext,
    PipelineStatus,
    StepUsage,
    TaskInput,
)
from levelup.core.instructions import add_instruction, build_instruct_review_prompt
from levelup.core.journal import RunJournal
from levelup.core.project_context import write_project_context_preserving
from levelup.core.pipeline import DEFAULT_PIPELINE, StepType
from levelup.detection.detector import ProjectDetector
from levelup.tools.base import ToolRegistry
from levelup.tools.file_read import FileReadTool
from levelup.tools.file_search import FileSearchTool
from levelup.tools.file_write import FileWriteTool
from levelup.tools.shell import ShellTool
from levelup.tools.test_runner import TestRunnerTool

logger = logging.getLogger(__name__)

MAX_AGENT_RETRIES = 2
CHECKPOINT_POLL_INTERVAL = 1.0  # seconds


class Orchestrator:
    """Central pipeline engine that runs the LevelUp TDD pipeline."""

    def __init__(
        self,
        settings: LevelUpSettings,
        state_manager: object | None = None,
        headless: bool = False,
        gui_mode: bool = False,
    ) -> None:
        self._settings = settings
        self._state_manager = state_manager
        self._use_db_checkpoints = headless or gui_mode
        self._quiet = headless and not gui_mode
        self._console = Console(quiet=self._quiet)
        self._agents: dict[str, BaseAgent] = {}
        self._backend: Backend | None = None

    def _create_backend(self, project_path: Path, ctx: PipelineContext | None = None) -> Backend:
        """Create the appropriate backend based on settings."""
        if self._settings.llm.backend == "claude_code":
            exe = self._settings.llm.claude_executable
            resolved = shutil.which(exe)
            if not resolved:
                raise RuntimeError(
                    f"'{exe}' executable not found on PATH.\n"
                    f"  - Install Claude Code: https://docs.anthropic.com/en/docs/claude-code\n"
                    f"  - Or set a custom path in levelup.yaml:  llm: {{ claude_executable: /path/to/claude }}\n"
                    f"  - Or use env var: LEVELUP_LLM__CLAUDE_EXECUTABLE=/path/to/claude\n"
                    f"  - Or switch backend: llm: {{ backend: anthropic_sdk }}"
                )
            # Verify the executable actually runs (catches broken shims/stubs)
            try:
                subprocess.run(
                    [resolved, "--version"],
                    capture_output=True,
                    timeout=10,
                )
            except (FileNotFoundError, subprocess.SubprocessError) as exc:
                raise RuntimeError(
                    f"'{resolved}' was found on PATH but failed to run: {exc}\n"
                    f"  - Reinstall Claude Code: https://docs.anthropic.com/en/docs/claude-code\n"
                    f"  - Or set a custom path in levelup.yaml:  llm: {{ claude_executable: /path/to/claude }}\n"
                    f"  - Or use env var: LEVELUP_LLM__CLAUDE_EXECUTABLE=/path/to/claude\n"
                    f"  - Or switch backend: llm: {{ backend: anthropic_sdk }}"
                )
            client = ClaudeCodeClient(
                model=self._settings.llm.model,
                claude_executable=resolved,
            )
            return ClaudeCodeBackend(client)
        else:
            # anthropic_sdk backend
            llm_client = LLMClient(
                api_key=self._settings.llm.api_key,
                auth_token=self._settings.llm.auth_token,
                model=self._settings.llm.model,
                max_tokens=self._settings.llm.max_tokens,
                temperature=self._settings.llm.temperature,
            )
            tool_registry = self._create_tool_registry(project_path, ctx)
            return AnthropicSDKBackend(llm_client, tool_registry)

    def _persist_state(self, ctx: PipelineContext) -> None:
        """Persist current pipeline state to the DB if a state manager is present."""
        if self._state_manager is not None:
            from levelup.state.manager import StateManager

            assert isinstance(self._state_manager, StateManager)
            self._state_manager.update_run(ctx)

    def _wait_for_checkpoint_decision(
        self, step_name: str, ctx: PipelineContext
    ) -> tuple[CheckpointDecision, str]:
        """Write checkpoint request to DB, poll until GUI provides a decision."""
        from levelup.state.manager import StateManager

        assert isinstance(self._state_manager, StateManager)

        # Build checkpoint data
        display_data = build_checkpoint_display_data(step_name, ctx)
        checkpoint_json = json.dumps(display_data)

        # Create request in DB
        self._state_manager.create_checkpoint_request(
            ctx.run_id, step_name, checkpoint_json
        )

        # Set status to waiting
        ctx.status = PipelineStatus.WAITING_FOR_INPUT
        self._persist_state(ctx)

        logger.info("Waiting for checkpoint decision: %s (run %s)", step_name, ctx.run_id)

        # Poll for decision
        while True:
            result = self._state_manager.get_checkpoint_decision(ctx.run_id, step_name)
            if result is not None:
                decision_str, feedback = result
                ctx.status = PipelineStatus.RUNNING
                self._persist_state(ctx)
                return CheckpointDecision(decision_str), feedback
            time.sleep(CHECKPOINT_POLL_INTERVAL)

    def run(self, task: TaskInput) -> PipelineContext:
        """Execute the full pipeline."""
        project_path = self._settings.project.path.resolve()

        ctx = PipelineContext(
            task=task,
            project_path=project_path,
            status=PipelineStatus.RUNNING,
        )

        # Register run in state DB
        if self._state_manager is not None:
            from levelup.state.manager import StateManager

            assert isinstance(self._state_manager, StateManager)
            self._state_manager.register_run(ctx)

        try:
            # Prompt for branch naming convention if needed (before creating branch)
            if self._settings.pipeline.create_git_branch:
                convention = self._prompt_branch_naming_if_needed(ctx, project_path)
                ctx.branch_naming = convention

            # Optionally create git worktree + branch (pre_run_sha is set inside)
            if self._settings.pipeline.create_git_branch:
                self._create_git_branch(project_path, ctx)

            # Derive the working path: worktree if created, else project_path
            working_path = ctx.worktree_path or project_path

            # Create journal in the working directory
            journal = RunJournal(ctx, base_path=working_path)
            journal.write_header(ctx)

            # Create backend and register agents against the working path
            self._backend = self._create_backend(working_path, ctx)
            self._register_agents(self._backend, working_path)

            ctx = self._execute_steps(ctx, DEFAULT_PIPELINE, journal, working_path)

            # Pipeline complete
            if ctx.status == PipelineStatus.RUNNING:
                ctx.status = PipelineStatus.COMPLETED
                if not self._quiet:
                    print_pipeline_summary(ctx)

        except KeyboardInterrupt:
            if not self._quiet:
                self._console.print("\n[yellow]Pipeline interrupted by user.[/yellow]")
            ctx.status = PipelineStatus.ABORTED
        except Exception as e:
            logger.exception("Pipeline failed: %s", e)
            ctx.status = PipelineStatus.FAILED
            ctx.error_message = str(e)
            if not self._quiet:
                print_error(str(e))

        working_path = ctx.worktree_path or project_path
        if "journal" in locals():
            journal.log_outcome(ctx)
            if ctx.status == PipelineStatus.COMPLETED:
                self._git_journal_commit(working_path, ctx, journal)
                ctx.current_step = None
                # Print branch info for the user
                if not self._quiet and ctx.branch_naming:
                    convention = ctx.branch_naming or "levelup/{run_id}"
                    branch_name = self._build_branch_name(convention, ctx)
                    self._console.print(
                        f"\n[bold]Branch '{branch_name}' is ready.[/bold]\n"
                        f"  git checkout {branch_name}\n"
                        f"  git merge {branch_name}"
                    )

        # Cleanup worktree (branch persists in main repo)
        self._cleanup_worktree(project_path, ctx)

        self._persist_state(ctx)
        return ctx

    def resume(self, ctx: PipelineContext, from_step: str | None = None) -> PipelineContext:
        """Resume a previously failed or aborted pipeline run.

        Args:
            ctx: The PipelineContext from the failed/aborted run.
            from_step: Optional step name to resume from. Defaults to ctx.current_step.

        Returns:
            Updated PipelineContext.
        """
        project_path = self._settings.project.path.resolve()

        # Determine which step to resume from
        target_step = from_step or ctx.current_step
        if not target_step:
            raise ValueError("No step to resume from: current_step is None and --from-step not specified.")

        # Validate the step exists
        step_names = [s.name for s in DEFAULT_PIPELINE]
        if target_step not in step_names:
            raise ValueError(f"Unknown step '{target_step}'. Valid steps: {', '.join(step_names)}")

        # Reset status
        ctx.status = PipelineStatus.RUNNING
        ctx.error_message = None

        try:
            # Re-create worktree if this run used one
            if ctx.worktree_path and ctx.worktree_path.exists():
                working_path = ctx.worktree_path
            elif ctx.pre_run_sha and self._settings.pipeline.create_git_branch:
                # Re-create worktree from existing branch
                try:
                    import git

                    repo = git.Repo(project_path)
                    convention = ctx.branch_naming or "levelup/{run_id}"
                    branch_name = self._build_branch_name(convention, ctx)
                    if branch_name in [h.name for h in repo.heads]:
                        worktree_dir = Path.home() / ".levelup" / "worktrees" / ctx.run_id
                        worktree_dir.parent.mkdir(parents=True, exist_ok=True)
                        # Clean up stale worktree directory if present
                        if worktree_dir.exists():
                            try:
                                repo.git.worktree("remove", str(worktree_dir), "--force")
                            except Exception:
                                import shutil as _shutil
                                _shutil.rmtree(worktree_dir, ignore_errors=True)
                        repo.git.worktree("add", str(worktree_dir), branch_name)
                        ctx.worktree_path = worktree_dir
                except Exception as e:
                    logger.warning("Could not re-create worktree for resume: %s", e)
                working_path = ctx.worktree_path or project_path
            else:
                working_path = project_path

            journal = RunJournal(ctx, base_path=working_path)
            journal._append([f"\n## Resumed from step: {target_step}", ""])

            # Create backend and register agents against the working path
            self._backend = self._create_backend(working_path, ctx)
            self._register_agents(self._backend, working_path)

            # Slice pipeline from target step onward
            start_idx = step_names.index(target_step)
            remaining_steps = DEFAULT_PIPELINE[start_idx:]

            ctx = self._execute_steps(ctx, remaining_steps, journal, working_path)

            if ctx.status == PipelineStatus.RUNNING:
                ctx.status = PipelineStatus.COMPLETED
                if not self._quiet:
                    print_pipeline_summary(ctx)

        except KeyboardInterrupt:
            if not self._quiet:
                self._console.print("\n[yellow]Pipeline interrupted by user.[/yellow]")
            ctx.status = PipelineStatus.ABORTED
        except Exception as e:
            logger.exception("Pipeline failed: %s", e)
            ctx.status = PipelineStatus.FAILED
            ctx.error_message = str(e)
            if not self._quiet:
                print_error(str(e))

        working_path = ctx.worktree_path or project_path
        if "journal" in locals():
            journal.log_outcome(ctx)
            if ctx.status == PipelineStatus.COMPLETED:
                self._git_journal_commit(working_path, ctx, journal)
                ctx.current_step = None

        # Cleanup worktree (branch persists in main repo)
        self._cleanup_worktree(project_path, ctx)

        self._persist_state(ctx)
        return ctx

    def _execute_steps(
        self,
        ctx: PipelineContext,
        steps: list,
        journal: RunJournal,
        project_path: Path,
    ) -> PipelineContext:
        """Execute a list of pipeline steps. Shared by run() and resume()."""
        for step in steps:
            ctx.current_step = step.name
            self._persist_state(ctx)

            if not self._quiet:
                print_step_header(step.name, step.description)

            if step.step_type == StepType.DETECTION:
                self._run_detection(project_path, ctx)
                # Re-create backend/agents if SDK backend (needs updated test command)
                if self._settings.llm.backend == "anthropic_sdk":
                    self._backend = self._create_backend(project_path, ctx)
                    self._register_agents(self._backend, project_path)

            elif step.step_type == StepType.AGENT:
                if step.agent_name not in self._agents:
                    logger.error("Agent not found: %s", step.agent_name)
                    continue

                ctx = self._run_agent_with_retry(step.agent_name, ctx)

                # Security loop-back for major issues
                if step.name == "security" and ctx.requires_coding_rework:
                    if not self._quiet:
                        self._console.print(
                            "[yellow]Security agent found major issues. "
                            "Re-running coding agent to fix...[/yellow]"
                        )

                    # Inject security feedback into coding task
                    original_desc = ctx.task.description
                    ctx.task.description = (
                        f"{original_desc}\n\n"
                        f"[SECURITY REVIEW FEEDBACK]\n{ctx.security_feedback}"
                    )

                    # Re-run coding agent
                    ctx = self._run_agent_with_retry("coder", ctx)
                    self._git_step_commit(project_path, ctx, "coding", revised=True)

                    # Restore original task description
                    ctx.task.description = original_desc

                    # Re-run security check on updated code
                    ctx.requires_coding_rework = False
                    ctx.security_feedback = ""
                    ctx = self._run_agent_with_retry("security", ctx)
                    self._git_step_commit(project_path, ctx, "security", revised=True)

                    # If still broken after one retry, continue to checkpoint
                    if ctx.requires_coding_rework:
                        if not self._quiet:
                            self._console.print(
                                "[red]Security issues remain after rework. "
                                "Manual review needed at checkpoint.[/red]"
                            )
                        ctx.requires_coding_rework = False  # Prevent infinite loops

                if ctx.status == PipelineStatus.FAILED:
                    break

            journal.log_step(step.name, ctx)
            self._git_step_commit(project_path, ctx, step.name)

            # Checkpoint
            if (
                step.checkpoint_after
                and self._settings.pipeline.require_checkpoints
            ):
                while True:
                    if self._use_db_checkpoints and self._state_manager is not None:
                        decision, feedback = self._wait_for_checkpoint_decision(
                            step.name, ctx
                        )
                    else:
                        decision, feedback = run_checkpoint(step.name, ctx)

                    if decision == CheckpointDecision.INSTRUCT:
                        self._run_instruct(ctx, feedback, project_path, journal)
                        continue  # re-prompt checkpoint

                    journal.log_checkpoint(step.name, decision.value, feedback)
                    break

                if decision == CheckpointDecision.APPROVE:
                    if not self._quiet:
                        print_success(f"Checkpoint '{step.name}' approved.")
                elif decision == CheckpointDecision.REVISE:
                    if not self._quiet:
                        self._console.print(
                            f"[yellow]Revising {step.name} with feedback...[/yellow]"
                        )
                    if step.agent_name:
                        ctx = self._run_agent_with_feedback(
                            step.agent_name, ctx, feedback
                        )
                        self._git_step_commit(project_path, ctx, step.name, revised=True)
                elif decision == CheckpointDecision.REJECT:
                    if not self._quiet:
                        self._console.print("[red]Pipeline aborted by user.[/red]")
                    ctx.status = PipelineStatus.ABORTED
                    break

        return ctx

    def _create_tool_registry(self, project_path: Path, ctx: PipelineContext | None = None) -> ToolRegistry:
        """Create and populate the tool registry (for SDK backend only)."""
        registry = ToolRegistry()
        registry.register(FileReadTool(project_path))
        registry.register(FileWriteTool(project_path))
        registry.register(FileSearchTool(project_path))
        registry.register(ShellTool(project_path))

        test_cmd = None
        if ctx:
            test_cmd = ctx.test_command or self._settings.project.test_command
        else:
            test_cmd = self._settings.project.test_command
        registry.register(TestRunnerTool(project_path, test_command=test_cmd))

        return registry

    def _register_agents(self, backend: Backend, project_path: Path) -> None:
        """Create and register all agents."""
        self._agents = {
            "requirements": RequirementsAgent(backend, project_path),
            "planning": PlanningAgent(backend, project_path),
            "test_writer": TestWriterAgent(backend, project_path),
            "coder": CodeAgent(
                backend,
                project_path,
                max_iterations=self._settings.pipeline.max_code_iterations,
            ),
            "security": SecurityAgent(backend, project_path),
            "reviewer": ReviewAgent(backend, project_path),
        }

    def _run_project_detection(self, project_path: Path) -> tuple[str, str, str, str]:
        """Run project detection and return detected values.

        Returns: (language, framework, test_runner, test_command)
        """
        detector = ProjectDetector()
        info = detector.detect(project_path)

        # Use detected values, but allow settings overrides
        language = self._settings.project.language or info.language
        framework = self._settings.project.framework or info.framework
        test_runner = info.test_runner
        test_command = self._settings.project.test_command or info.test_command

        return language, framework, test_runner, test_command

    def _run_detection(self, project_path: Path, ctx: PipelineContext) -> None:
        """Run project detection and update context."""
        language, framework, test_runner, test_command = self._run_project_detection(project_path)

        ctx.language = language
        ctx.framework = framework
        ctx.test_runner = test_runner
        ctx.test_command = test_command

        # Load branch naming from project_context.md (if not already set)
        if not ctx.branch_naming:
            ctx.branch_naming = self._load_branch_naming_from_context(project_path)

        # Write project context file
        write_project_context_preserving(
            project_path,
            language=ctx.language,
            framework=ctx.framework,
            test_runner=ctx.test_runner,
            test_command=ctx.test_command,
            branch_naming=ctx.branch_naming,
        )

        if not self._quiet:
            from levelup.cli.display import print_project_info
            from levelup.detection.detector import ProjectInfo

            print_project_info(ProjectInfo(
                language=ctx.language,
                framework=ctx.framework,
                test_runner=ctx.test_runner,
                test_command=ctx.test_command,
            ))

    def _capture_usage(self, ctx: PipelineContext, agent_name: str, agent_result: AgentResult) -> None:
        """Store usage metrics from an agent result into the pipeline context."""
        usage = StepUsage(
            cost_usd=agent_result.cost_usd,
            input_tokens=agent_result.input_tokens,
            output_tokens=agent_result.output_tokens,
            duration_ms=agent_result.duration_ms,
            num_turns=agent_result.num_turns,
        )
        ctx.step_usage[agent_name] = usage
        ctx.total_cost_usd += usage.cost_usd

    def _run_agent_with_retry(
        self, agent_name: str, ctx: PipelineContext
    ) -> PipelineContext:
        """Run an agent with retry on failure."""
        agent = self._agents[agent_name]

        for attempt in range(MAX_AGENT_RETRIES + 1):
            try:
                if self._quiet:
                    ctx, agent_result = agent.run(ctx)
                else:
                    with self._console.status(f"[cyan]Running {agent_name} agent..."):
                        ctx, agent_result = agent.run(ctx)
                self._capture_usage(ctx, agent_name, agent_result)
                return ctx
            except ClaudeCodeError as e:
                if "not found" in str(e).lower():
                    # Executable missing — retrying won't help
                    logger.error("Agent %s: unrecoverable error: %s", agent_name, e)
                    ctx.status = PipelineStatus.FAILED
                    ctx.error_message = f"Agent {agent_name} failed: {e}"
                    if not self._quiet:
                        print_error(ctx.error_message)
                    return ctx
                # Other ClaudeCodeError: fall through to retry logic
                if attempt < MAX_AGENT_RETRIES:
                    logger.warning(
                        "Agent %s failed (attempt %d/%d): %s",
                        agent_name,
                        attempt + 1,
                        MAX_AGENT_RETRIES + 1,
                        e,
                    )
                    if not self._quiet:
                        self._console.print(
                            f"[yellow]Agent {agent_name} failed, retrying "
                            f"({attempt + 1}/{MAX_AGENT_RETRIES})...[/yellow]"
                        )
                else:
                    logger.error("Agent %s failed after all retries: %s", agent_name, e)
                    ctx.status = PipelineStatus.FAILED
                    ctx.error_message = f"Agent {agent_name} failed: {e}"
                    if not self._quiet:
                        print_error(ctx.error_message)
            except Exception as e:
                if attempt < MAX_AGENT_RETRIES:
                    logger.warning(
                        "Agent %s failed (attempt %d/%d): %s",
                        agent_name,
                        attempt + 1,
                        MAX_AGENT_RETRIES + 1,
                        e,
                    )
                    if not self._quiet:
                        self._console.print(
                            f"[yellow]Agent {agent_name} failed, retrying "
                            f"({attempt + 1}/{MAX_AGENT_RETRIES})...[/yellow]"
                        )
                else:
                    logger.error("Agent %s failed after all retries: %s", agent_name, e)
                    ctx.status = PipelineStatus.FAILED
                    ctx.error_message = f"Agent {agent_name} failed: {e}"
                    if not self._quiet:
                        print_error(ctx.error_message)

        return ctx

    def _run_agent_with_feedback(
        self, agent_name: str, ctx: PipelineContext, feedback: str
    ) -> PipelineContext:
        """Re-run an agent with user feedback for revision."""
        # For revision, we modify the task description to include feedback
        original_desc = ctx.task.description
        ctx.task.description = (
            f"{original_desc}\n\n"
            f"USER REVISION FEEDBACK: {feedback}"
        )

        ctx = self._run_agent_with_retry(agent_name, ctx)

        # Restore original description
        ctx.task.description = original_desc
        return ctx

    def _sanitize_task_title(self, title: str) -> str:
        """Sanitize task title for use in branch names.

        - Converts to lowercase
        - Replaces spaces and special chars with hyphens
        - Removes consecutive hyphens
        - Strips leading/trailing hyphens
        - Limits to 50 characters
        """
        import re

        if not title or not title.strip():
            return "task"

        # Convert to lowercase
        sanitized = title.lower()

        # Replace special chars and spaces with hyphens
        sanitized = re.sub(r"[^a-z0-9]+", "-", sanitized)

        # Remove consecutive hyphens
        sanitized = re.sub(r"-+", "-", sanitized)

        # Strip leading/trailing hyphens
        sanitized = sanitized.strip("-")

        # Limit to 50 characters
        if len(sanitized) > 50:
            sanitized = sanitized[:50].rstrip("-")

        # Fallback to "task" if sanitization resulted in empty string
        return sanitized if sanitized else "task"

    def _build_branch_name(self, convention: str, ctx: PipelineContext) -> str:
        """Build branch name from convention pattern by substituting placeholders.

        Supports placeholders: {run_id}, {task_title}, {date}
        Falls back to 'levelup/{run_id}' if pattern is empty.
        """
        from datetime import datetime

        if not convention or not convention.strip():
            return f"levelup/{ctx.run_id}"

        # Prepare placeholder values
        task_title = self._sanitize_task_title(ctx.task.title)
        date_str = datetime.now().strftime("%Y%m%d")

        # Substitute placeholders
        branch_name = convention
        branch_name = branch_name.replace("{run_id}", ctx.run_id)
        branch_name = branch_name.replace("{task_title}", task_title)
        branch_name = branch_name.replace("{date}", date_str)

        return branch_name

    def _load_branch_naming_from_context(self, project_path: Path) -> str:
        """Load branch naming convention from project_context.md.

        Returns the stored convention, or default 'levelup/{run_id}' if not found.
        """
        from levelup.core.project_context import read_project_context_header

        header = read_project_context_header(project_path)
        if header and header.get("branch_naming"):
            return header["branch_naming"]
        return "levelup/{run_id}"

    def _prompt_branch_naming_if_needed(self, ctx: PipelineContext, project_path: Path) -> str:
        """Prompt user for branch naming convention on first run if needed.

        Returns the convention to use (either from context, from user prompt, or default).
        """
        # If already set in context, use it
        if ctx.branch_naming:
            return ctx.branch_naming

        # If create_git_branch is False, don't prompt
        if not self._settings.pipeline.create_git_branch:
            return "levelup/{run_id}"

        # If in headless/gui mode, don't prompt interactively
        if self._use_db_checkpoints:
            return "levelup/{run_id}"

        # Try to load from project_context.md
        from levelup.core.project_context import read_project_context_header

        header = read_project_context_header(project_path)
        if header and header.get("branch_naming"):
            convention = header["branch_naming"]
            ctx.branch_naming = convention
            return convention

        # First run - prompt user
        from levelup.cli.prompts import prompt_branch_naming_convention

        convention = prompt_branch_naming_convention()
        if not convention:
            convention = "levelup/{run_id}"

        ctx.branch_naming = convention
        return convention

    def _create_git_branch(self, project_path: Path, ctx: PipelineContext) -> str | None:
        """Create a git worktree with a new branch for this run.

        Returns the pre-branch HEAD SHA.  Also stores pre_run_sha and
        worktree_path in the context.
        """
        # Check if branch creation is enabled
        if not self._settings.pipeline.create_git_branch:
            return None

        try:
            import git

            repo = git.Repo(project_path)
            pre_sha = repo.head.commit.hexsha

            # Build branch name using convention
            convention = ctx.branch_naming or "levelup/{run_id}"
            branch_name = self._build_branch_name(convention, ctx)

            # Create a worktree instead of checking out a branch
            worktree_dir = Path.home() / ".levelup" / "worktrees" / ctx.run_id
            worktree_dir.parent.mkdir(parents=True, exist_ok=True)

            # Clean up stale worktree directory from a prior failed run
            if worktree_dir.exists():
                try:
                    repo.git.worktree("remove", str(worktree_dir), "--force")
                except Exception:
                    import shutil as _shutil
                    _shutil.rmtree(worktree_dir, ignore_errors=True)

            repo.git.worktree("add", str(worktree_dir), "-b", branch_name)
            ctx.worktree_path = worktree_dir

            if not self._quiet:
                print_success(f"Created branch: {branch_name} (worktree: {worktree_dir})")

            # Store pre_run_sha in context
            ctx.pre_run_sha = pre_sha
            return pre_sha
        except Exception as e:
            logger.warning("Failed to create git branch: %s", e)
            if not self._quiet:
                self._console.print(f"[dim]Git branch creation skipped: {e}[/dim]")
            return None

    def _cleanup_worktree(self, project_path: Path, ctx: PipelineContext) -> None:
        """Remove the worktree directory. The branch persists in the main repo."""
        if not ctx.worktree_path or not ctx.worktree_path.exists():
            return
        try:
            import git

            repo = git.Repo(project_path)
            repo.git.worktree("remove", str(ctx.worktree_path), "--force")
        except Exception as e:
            logger.warning("Failed to remove worktree: %s", e)

    def _run_instruct(
        self,
        ctx: PipelineContext,
        instruction_text: str,
        project_path: Path,
        journal: RunJournal,
    ) -> None:
        """Add a project rule to CLAUDE.md and review branch changes for violations."""
        add_instruction(project_path, instruction_text)
        if not self._quiet:
            self._console.print(f"[cyan]Added rule:[/cyan] {instruction_text}")

        changed_files = self._get_changed_files(ctx, project_path)
        if not changed_files:
            if not self._quiet:
                self._console.print("[dim]No changed files to review for this rule.[/dim]")
            journal.log_instruct(instruction_text)
            self._git_step_commit(project_path, ctx, "instruct")
            return

        # Run a review agent against changed files
        if self._backend is None:
            logger.warning("No backend available for instruct review.")
            journal.log_instruct(instruction_text)
            return

        review_prompt = build_instruct_review_prompt(instruction_text, changed_files)
        try:
            if self._quiet:
                agent_result = self._backend.run_agent(
                    system_prompt=review_prompt,
                    user_prompt=f"Review and fix violations of: {instruction_text}",
                    allowed_tools=["Read", "Write", "Edit", "Glob", "Grep"],
                    working_directory=str(project_path),
                )
            else:
                with self._console.status("[cyan]Reviewing changes for rule compliance..."):
                    agent_result = self._backend.run_agent(
                        system_prompt=review_prompt,
                        user_prompt=f"Review and fix violations of: {instruction_text}",
                        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep"],
                        working_directory=str(project_path),
                    )
            self._capture_usage(ctx, "instruct_review", agent_result)
            journal.log_instruct(instruction_text, agent_result)
        except Exception as e:
            logger.warning("Instruct review failed: %s", e)
            journal.log_instruct(instruction_text)

        self._git_step_commit(project_path, ctx, "instruct")

    def _get_changed_files(self, ctx: PipelineContext, project_path: Path) -> list[str]:
        """Get the list of files changed in this run."""
        # Try git diff first
        if ctx.pre_run_sha:
            try:
                import git

                repo = git.Repo(project_path)
                diff_output = repo.git.diff("--name-only", ctx.pre_run_sha, "HEAD")
                if diff_output.strip():
                    return [f for f in diff_output.strip().splitlines() if f.strip()]
            except Exception as e:
                logger.warning("Failed to get git diff for instruct review: %s", e)

        # Fallback: collect from context
        files: list[str] = []
        for f in ctx.code_files:
            if f.path not in files:
                files.append(f.path)
        for f in ctx.test_files:
            if f.path not in files:
                files.append(f.path)
        return files

    def _git_step_commit(
        self, project_path: Path, ctx: PipelineContext, step_name: str, revised: bool = False
    ) -> None:
        """Create a git commit for a pipeline step's changes."""
        if not self._settings.pipeline.create_git_branch or ctx.pre_run_sha is None:
            return
        try:
            import git

            repo = git.Repo(project_path)
            repo.git.add(A=True)
            if not repo.index.diff("HEAD"):
                return  # no changes to commit
            suffix = ", revised" if revised else ""
            message = f"levelup({step_name}{suffix}): {ctx.task.title}\n\nRun ID: {ctx.run_id}"
            commit = repo.index.commit(message)
            ctx.step_commits[step_name] = commit.hexsha
        except Exception as e:
            logger.warning("Failed to create step commit for %s: %s", step_name, e)

    def _git_journal_commit(
        self, project_path: Path, ctx: PipelineContext, journal: RunJournal
    ) -> None:
        """Commit the run journal after pipeline completion."""
        if not self._settings.pipeline.create_git_branch or ctx.pre_run_sha is None:
            return
        try:
            import git

            repo = git.Repo(project_path)
            journal_rel = journal.path.relative_to(project_path)
            repo.git.add(str(journal_rel))
            if not repo.index.diff("HEAD"):
                return
            message = f"levelup(documentation): {ctx.task.title}\n\nRun ID: {ctx.run_id}"
            repo.index.commit(message)
        except Exception as e:
            logger.warning("Failed to commit run journal: %s", e)
