"""Pipeline orchestrator - the heart of LevelUp."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from rich.console import Console

from levelup.agents.backend import AnthropicSDKBackend, Backend, ClaudeCodeBackend
from levelup.agents.base import BaseAgent
from levelup.agents.claude_code_client import ClaudeCodeClient
from levelup.agents.coder import CodeAgent
from levelup.agents.llm_client import LLMClient
from levelup.agents.planning import PlanningAgent
from levelup.agents.requirements import RequirementsAgent
from levelup.agents.reviewer import ReviewAgent
from levelup.agents.test_writer import TestWriterAgent
from levelup.cli.display import (
    print_error,
    print_pipeline_summary,
    print_step_header,
    print_success,
)
from levelup.cli.prompts import confirm_action
from levelup.config.settings import LevelUpSettings
from levelup.core.checkpoint import build_checkpoint_display_data, run_checkpoint
from levelup.core.context import (
    CheckpointDecision,
    PipelineContext,
    PipelineStatus,
    TaskInput,
)
from levelup.core.journal import RunJournal
from levelup.core.project_context import write_project_context
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

    def _create_backend(self, project_path: Path, ctx: PipelineContext | None = None) -> Backend:
        """Create the appropriate backend based on settings."""
        if self._settings.llm.backend == "claude_code":
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
        backend = self._create_backend(project_path, ctx)
        self._register_agents(backend, project_path)

        # Optionally create git branch
        if self._settings.pipeline.create_git_branch:
            self._create_git_branch(project_path, ctx.run_id)

        try:
            for step in DEFAULT_PIPELINE:
                ctx.current_step = step.name
                self._persist_state(ctx)

                if not self._headless:
                    print_step_header(step.name, step.description)

                if step.step_type == StepType.DETECTION:
                    self._run_detection(ctx)
                    write_project_context(
                        project_path,
                        language=ctx.language,
                        framework=ctx.framework,
                        test_runner=ctx.test_runner,
                        test_command=ctx.test_command,
                    )
                    # Re-create backend/agents if SDK backend (needs updated test command)
                    if self._settings.llm.backend == "anthropic_sdk":
                        backend = self._create_backend(project_path, ctx)
                        self._register_agents(backend, project_path)

                elif step.step_type == StepType.AGENT:
                    if step.agent_name not in self._agents:
                        logger.error("Agent not found: %s", step.agent_name)
                        continue

                    ctx = self._run_agent_with_retry(step.agent_name, ctx)

                    if ctx.status == PipelineStatus.FAILED:
                        break

                journal.log_step(step.name, ctx)

                # Checkpoint
                if (
                    step.checkpoint_after
                    and self._settings.pipeline.require_checkpoints
                ):
                    if self._headless and self._state_manager is not None:
                        decision, feedback = self._wait_for_checkpoint_decision(
                            step.name, ctx
                        )
                    else:
                        decision, feedback = run_checkpoint(step.name, ctx)

                    journal.log_checkpoint(step.name, decision.value, feedback)

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
                    elif decision == CheckpointDecision.REJECT:
                        if not self._headless:
                            self._console.print("[red]Pipeline aborted by user.[/red]")
                        ctx.status = PipelineStatus.ABORTED
                        break

            # Pipeline complete
            if ctx.status == PipelineStatus.RUNNING:
                ctx.status = PipelineStatus.COMPLETED
                if not self._headless:
                    print_pipeline_summary(ctx)

                    # Offer to commit
                    if self._settings.pipeline.create_git_branch:
                        if confirm_action("Commit changes?"):
                            self._git_commit(project_path, ctx)

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

    def _run_agent_with_retry(
        self, agent_name: str, ctx: PipelineContext
    ) -> PipelineContext:
        """Run an agent with retry on failure."""
        agent = self._agents[agent_name]

        for attempt in range(MAX_AGENT_RETRIES + 1):
            try:
                if self._headless:
                    ctx = agent.run(ctx)
                else:
                    with self._console.status(f"[cyan]Running {agent_name} agent..."):
                        ctx = agent.run(ctx)
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

    def _create_git_branch(self, project_path: Path, run_id: str) -> None:
        """Create a git branch for this run."""
        try:
            import git

            repo = git.Repo(project_path)
            branch_name = f"levelup/{run_id}"
            repo.create_head(branch_name)
            repo.heads[branch_name].checkout()
            if not self._headless:
                print_success(f"Created branch: {branch_name}")
        except Exception as e:
            logger.warning("Failed to create git branch: %s", e)
            if not self._headless:
                self._console.print(f"[dim]Git branch creation skipped: {e}[/dim]")

    def _git_commit(self, project_path: Path, ctx: PipelineContext) -> None:
        """Commit all changes."""
        try:
            import git

            repo = git.Repo(project_path)
            repo.git.add(A=True)
            message = f"levelup: {ctx.task.title}\n\nRun ID: {ctx.run_id}"
            repo.index.commit(message)
            print_success("Changes committed.")
        except Exception as e:
            logger.warning("Failed to commit: %s", e)
            print_error(f"Git commit failed: {e}")
