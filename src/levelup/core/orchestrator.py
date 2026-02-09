"""Pipeline orchestrator - the heart of LevelUp."""

from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path

from rich.console import Console

from levelup.agents.backend import AgentResult, AnthropicSDKBackend, Backend, ClaudeCodeBackend
from levelup.agents.base import BaseAgent
from levelup.agents.claude_code_client import ClaudeCodeClient
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
    ) -> None:
        self._settings = settings
        self._state_manager = state_manager
        self._headless = headless
        self._console = Console(quiet=headless)
        self._agents: dict[str, BaseAgent] = {}
        self._backend: Backend | None = None

    def _create_backend(self, project_path: Path, ctx: PipelineContext | None = None) -> Backend:
        """Create the appropriate backend based on settings."""
        if self._settings.llm.backend == "claude_code":
            exe = self._settings.llm.claude_executable
            if not shutil.which(exe):
                raise RuntimeError(
                    f"'{exe}' executable not found on PATH.\n"
                    f"  - Install Claude Code: https://docs.anthropic.com/en/docs/claude-code\n"
                    f"  - Or set a custom path in levelup.yaml:  llm: {{ claude_executable: /path/to/claude }}\n"
                    f"  - Or use env var: LEVELUP_LLM__CLAUDE_EXECUTABLE=/path/to/claude\n"
                    f"  - Or switch backend: llm: {{ backend: anthropic_sdk }}"
                )
            client = ClaudeCodeClient(
                model=self._settings.llm.model,
                claude_executable=self._settings.llm.claude_executable,
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

        journal = RunJournal(ctx)
        journal.write_header(ctx)

        # Register run in state DB
        if self._state_manager is not None:
            from levelup.state.manager import StateManager

            assert isinstance(self._state_manager, StateManager)
            self._state_manager.register_run(ctx)

        # Create backend and register agents
        self._backend = self._create_backend(project_path, ctx)
        self._register_agents(self._backend, project_path)

        # Optionally create git branch
        if self._settings.pipeline.create_git_branch:
            ctx.pre_run_sha = self._create_git_branch(project_path, ctx.run_id)

        try:
            ctx = self._execute_steps(ctx, DEFAULT_PIPELINE, journal, project_path)

            # Pipeline complete
            if ctx.status == PipelineStatus.RUNNING:
                ctx.status = PipelineStatus.COMPLETED
                if not self._headless:
                    print_pipeline_summary(ctx)

        except KeyboardInterrupt:
            if not self._headless:
                self._console.print("\n[yellow]Pipeline interrupted by user.[/yellow]")
            ctx.status = PipelineStatus.ABORTED
        except Exception as e:
            logger.exception("Pipeline failed: %s", e)
            ctx.status = PipelineStatus.FAILED
            ctx.error_message = str(e)
            if not self._headless:
                print_error(str(e))

        journal.log_outcome(ctx)
        ctx.current_step = None
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

        journal = RunJournal(ctx)
        journal._append([f"\n## Resumed from step: {target_step}", ""])

        # Create backend and register agents
        self._backend = self._create_backend(project_path, ctx)
        self._register_agents(self._backend, project_path)

        # Checkout the run branch if it exists
        try:
            import git

            repo = git.Repo(project_path)
            branch_name = f"levelup/{ctx.run_id}"
            if branch_name in [h.name for h in repo.heads]:
                repo.heads[branch_name].checkout()
        except Exception as e:
            logger.warning("Could not checkout run branch: %s", e)

        # Slice pipeline from target step onward
        start_idx = step_names.index(target_step)
        remaining_steps = DEFAULT_PIPELINE[start_idx:]

        try:
            ctx = self._execute_steps(ctx, remaining_steps, journal, project_path)

            if ctx.status == PipelineStatus.RUNNING:
                ctx.status = PipelineStatus.COMPLETED
                if not self._headless:
                    print_pipeline_summary(ctx)

        except KeyboardInterrupt:
            if not self._headless:
                self._console.print("\n[yellow]Pipeline interrupted by user.[/yellow]")
            ctx.status = PipelineStatus.ABORTED
        except Exception as e:
            logger.exception("Pipeline failed: %s", e)
            ctx.status = PipelineStatus.FAILED
            ctx.error_message = str(e)
            if not self._headless:
                print_error(str(e))

        journal.log_outcome(ctx)
        ctx.current_step = None
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

            if not self._headless:
                print_step_header(step.name, step.description)

            if step.step_type == StepType.DETECTION:
                self._run_detection(ctx)
                write_project_context_preserving(
                    project_path,
                    language=ctx.language,
                    framework=ctx.framework,
                    test_runner=ctx.test_runner,
                    test_command=ctx.test_command,
                )
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
                    if not self._headless:
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
                        if not self._headless:
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
                    if self._headless and self._state_manager is not None:
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
                    if not self._headless:
                        print_success(f"Checkpoint '{step.name}' approved.")
                elif decision == CheckpointDecision.REVISE:
                    if not self._headless:
                        self._console.print(
                            f"[yellow]Revising {step.name} with feedback...[/yellow]"
                        )
                    if step.agent_name:
                        ctx = self._run_agent_with_feedback(
                            step.agent_name, ctx, feedback
                        )
                        self._git_step_commit(project_path, ctx, step.name, revised=True)
                elif decision == CheckpointDecision.REJECT:
                    if not self._headless:
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

    def _run_detection(self, ctx: PipelineContext) -> None:
        """Run project detection and update context."""
        detector = ProjectDetector()
        info = detector.detect(ctx.project_path)

        # Use detected values, but allow settings overrides
        ctx.language = self._settings.project.language or info.language
        ctx.framework = self._settings.project.framework or info.framework
        ctx.test_runner = info.test_runner
        ctx.test_command = self._settings.project.test_command or info.test_command

        if not self._headless:
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
                if self._headless:
                    ctx, agent_result = agent.run(ctx)
                else:
                    with self._console.status(f"[cyan]Running {agent_name} agent..."):
                        ctx, agent_result = agent.run(ctx)
                self._capture_usage(ctx, agent_name, agent_result)
                return ctx
            except Exception as e:
                if attempt < MAX_AGENT_RETRIES:
                    logger.warning(
                        "Agent %s failed (attempt %d/%d): %s",
                        agent_name,
                        attempt + 1,
                        MAX_AGENT_RETRIES + 1,
                        e,
                    )
                    if not self._headless:
                        self._console.print(
                            f"[yellow]Agent {agent_name} failed, retrying "
                            f"({attempt + 1}/{MAX_AGENT_RETRIES})...[/yellow]"
                        )
                else:
                    logger.error("Agent %s failed after all retries: %s", agent_name, e)
                    ctx.status = PipelineStatus.FAILED
                    ctx.error_message = f"Agent {agent_name} failed: {e}"
                    if not self._headless:
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

    def _create_git_branch(self, project_path: Path, run_id: str) -> str | None:
        """Create a git branch for this run. Returns the pre-branch HEAD SHA."""
        try:
            import git

            repo = git.Repo(project_path)
            pre_sha = repo.head.commit.hexsha
            branch_name = f"levelup/{run_id}"
            repo.create_head(branch_name)
            repo.heads[branch_name].checkout()
            if not self._headless:
                print_success(f"Created branch: {branch_name}")
            return pre_sha
        except Exception as e:
            logger.warning("Failed to create git branch: %s", e)
            if not self._headless:
                self._console.print(f"[dim]Git branch creation skipped: {e}[/dim]")
            return None

    def _run_instruct(
        self,
        ctx: PipelineContext,
        instruction_text: str,
        project_path: Path,
        journal: RunJournal,
    ) -> None:
        """Add a project rule to CLAUDE.md and review branch changes for violations."""
        add_instruction(project_path, instruction_text)
        if not self._headless:
            self._console.print(f"[cyan]Added rule:[/cyan] {instruction_text}")

        changed_files = self._get_changed_files(ctx, project_path)
        if not changed_files:
            if not self._headless:
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
            if self._headless:
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
