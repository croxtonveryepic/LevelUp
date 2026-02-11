"""Tests for the Orchestrator and pipeline logic."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from levelup.config.settings import (
    LevelUpSettings,
    LLMSettings,
    PipelineSettings,
    ProjectSettings,
)
from levelup.core.context import (
    CheckpointDecision,
    FileChange,
    PipelineContext,
    PipelineStatus,
    Requirements,
    TaskInput,
)
from levelup.core.orchestrator import Orchestrator
from levelup.core.pipeline import DEFAULT_PIPELINE, PipelineStep, StepType


# --- Pipeline definitions ---


class TestPipelineDefinitions:
    def test_default_pipeline_has_expected_steps(self):
        names = [s.name for s in DEFAULT_PIPELINE]
        assert "detect" in names
        assert "requirements" in names
        assert "planning" in names
        assert "test_writing" in names
        assert "coding" in names
        assert "security" in names
        assert "review" in names

    def test_pipeline_step_types(self):
        detect = next(s for s in DEFAULT_PIPELINE if s.name == "detect")
        assert detect.step_type == StepType.DETECTION

        reqs = next(s for s in DEFAULT_PIPELINE if s.name == "requirements")
        assert reqs.step_type == StepType.AGENT
        assert reqs.agent_name == "requirements"
        assert reqs.checkpoint_after is True

    def test_checkpoints_on_correct_steps(self):
        checkpoint_steps = [s.name for s in DEFAULT_PIPELINE if s.checkpoint_after]
        assert "requirements" in checkpoint_steps
        assert "test_writing" in checkpoint_steps
        assert "security" in checkpoint_steps
        assert "review" in checkpoint_steps
        assert "planning" not in checkpoint_steps
        assert "coding" not in checkpoint_steps

    def test_pipeline_step_frozen(self):
        step = PipelineStep(name="test", step_type=StepType.AGENT)
        with pytest.raises(AttributeError):
            step.name = "changed"


# --- Orchestrator ---


class TestOrchestrator:
    def _make_settings(self, tmp_path: Path, backend: str = "claude_code") -> LevelUpSettings:
        return LevelUpSettings(
            llm=LLMSettings(
                api_key="test-key",
                model="test-model",
                backend=backend,
            ),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(
                require_checkpoints=False,
                create_git_branch=False,
                max_code_iterations=2,
            ),
        )

    def test_orchestrator_creates(self, tmp_path):
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)
        assert orch is not None

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_orchestrator_runs_pipeline_no_checkpoints(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        def fake_agent(name, ctx):
            return ctx

        mock_agent.side_effect = fake_agent

        task = TaskInput(title="Test task", description="A test")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        assert mock_detect.called
        assert mock_agent.call_count == 7  # 7 agent steps (requirements, planning, test_writer, test_verifier, coder, security, reviewer)

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.run_checkpoint")
    def test_orchestrator_with_checkpoints_approve(
        self, mock_checkpoint, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        settings = self._make_settings(tmp_path)
        settings.pipeline.require_checkpoints = True
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx
        mock_checkpoint.return_value = (CheckpointDecision.APPROVE, "")

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        assert mock_checkpoint.call_count == 4  # 4 checkpoints (requirements, test_writing, security, review)

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.run_checkpoint")
    def test_orchestrator_checkpoint_reject_aborts(
        self, mock_checkpoint, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        settings = self._make_settings(tmp_path)
        settings.pipeline.require_checkpoints = True
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx
        mock_checkpoint.return_value = (CheckpointDecision.REJECT, "")

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.ABORTED

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_orchestrator_agent_failure(self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path):
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        def fail_agent(name, ctx):
            if name == "requirements":
                ctx.status = PipelineStatus.FAILED
                ctx.error_message = "API error"
            return ctx

        mock_agent.side_effect = fail_agent

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.FAILED

    def test_orchestrator_creates_with_headless(self, tmp_path):
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings, headless=True)
        assert orch._quiet is True
        assert orch._use_db_checkpoints is True

    def test_orchestrator_creates_with_state_manager(self, tmp_path):
        from levelup.state.manager import StateManager

        settings = self._make_settings(tmp_path)
        mgr = StateManager(db_path=tmp_path / "test.db")
        orch = Orchestrator(settings=settings, state_manager=mgr)
        assert orch._state_manager is mgr

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_orchestrator_with_state_manager_persists(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        from levelup.state.manager import StateManager

        settings = self._make_settings(tmp_path)
        mgr = StateManager(db_path=tmp_path / "test.db")
        orch = Orchestrator(settings=settings, state_manager=mgr)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.status == "completed"

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_headless_no_checkpoints_completes(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings, headless=True)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    def test_create_backend_claude_code(self, mock_subprocess, mock_which, tmp_path):
        """Verify claude_code backend creates ClaudeCodeBackend."""
        from levelup.agents.backend import ClaudeCodeBackend
        settings = self._make_settings(tmp_path, backend="claude_code")
        orch = Orchestrator(settings=settings)
        backend = orch._create_backend(tmp_path)
        assert isinstance(backend, ClaudeCodeBackend)

    @patch("shutil.which", return_value=None)
    def test_create_backend_claude_code_missing_executable(self, mock_which, tmp_path):
        """Raise RuntimeError when claude executable is not found on PATH."""
        settings = self._make_settings(tmp_path, backend="claude_code")
        orch = Orchestrator(settings=settings)
        with pytest.raises(RuntimeError, match="executable not found on PATH"):
            orch._create_backend(tmp_path)

    @patch("shutil.which", return_value=None)
    def test_create_backend_missing_executable_shows_workarounds(self, mock_which, tmp_path):
        """Error message includes install link, config path, env var, and alt backend."""
        settings = self._make_settings(tmp_path, backend="claude_code")
        orch = Orchestrator(settings=settings)
        with pytest.raises(RuntimeError, match="Install Claude Code") as exc_info:
            orch._create_backend(tmp_path)
        msg = str(exc_info.value)
        assert "claude_executable" in msg
        assert "LEVELUP_LLM__CLAUDE_EXECUTABLE" in msg
        assert "anthropic_sdk" in msg

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run", side_effect=FileNotFoundError("broken shim"))
    def test_create_backend_broken_shim_raises(self, mock_subprocess, mock_which, tmp_path):
        """Raise RuntimeError when executable exists on PATH but fails to run."""
        settings = self._make_settings(tmp_path, backend="claude_code")
        orch = Orchestrator(settings=settings)
        with pytest.raises(RuntimeError, match="found on PATH but failed to run") as exc_info:
            orch._create_backend(tmp_path)
        msg = str(exc_info.value)
        assert "broken shim" in msg
        assert "Reinstall Claude Code" in msg
        assert "anthropic_sdk" in msg

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    def test_retry_skipped_for_not_found_error(self, mock_subprocess, mock_which, tmp_path):
        """ClaudeCodeError with 'not found' skips retries and fails immediately."""
        from levelup.agents.claude_code_client import ClaudeCodeError

        settings = self._make_settings(tmp_path, backend="claude_code")
        orch = Orchestrator(settings=settings)
        backend = orch._create_backend(tmp_path)
        orch._register_agents(backend, tmp_path)

        # Make the agent raise a "not found" ClaudeCodeError
        mock_agent = MagicMock()
        mock_agent.run.side_effect = ClaudeCodeError("'claude' not found.", returncode=-1)
        orch._agents["coder"] = mock_agent

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
        )
        result = orch._run_agent_with_retry("coder", ctx)

        assert result.status == PipelineStatus.FAILED
        # Should only be called once (no retries)
        assert mock_agent.run.call_count == 1

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_create_backend_anthropic_sdk(self, MockAnthropic, tmp_path):
        """Verify anthropic_sdk backend creates AnthropicSDKBackend."""
        from levelup.agents.backend import AnthropicSDKBackend
        settings = self._make_settings(tmp_path, backend="anthropic_sdk")
        orch = Orchestrator(settings=settings)
        backend = orch._create_backend(tmp_path)
        assert isinstance(backend, AnthropicSDKBackend)

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.run_checkpoint")
    def test_instruct_at_checkpoint_loops_then_approves(
        self, mock_checkpoint, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """INSTRUCT decision loops back; next APPROVE proceeds normally."""
        settings = self._make_settings(tmp_path)
        settings.pipeline.require_checkpoints = True
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # First checkpoint: INSTRUCT then APPROVE; rest: APPROVE
        call_count = {"n": 0}

        def checkpoint_side_effect(step_name, ctx):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return CheckpointDecision.INSTRUCT, "Use type hints"
            return CheckpointDecision.APPROVE, ""

        mock_checkpoint.side_effect = checkpoint_side_effect

        # Patch _run_instruct to avoid real backend call
        with patch.object(orch, "_run_instruct") as mock_instruct:
            task = TaskInput(title="Test task")
            ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        # _run_instruct was called once (for the INSTRUCT at checkpoint 1)
        mock_instruct.assert_called_once()
        # Checkpoint was called 5 times: 1 INSTRUCT + 4 APPROVE (4 checkpoint steps)
        assert mock_checkpoint.call_count == 5

    def test_run_instruct_adds_rule_to_claude_md(self, tmp_path):
        """_run_instruct writes to CLAUDE.md."""
        from levelup.core.instructions import read_instructions

        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
        )
        journal = MagicMock()

        orch._run_instruct(ctx, "Use type hints", tmp_path, journal)

        rules = read_instructions(tmp_path)
        assert "Use type hints" in rules
        journal.log_instruct.assert_called_once()

    def test_run_instruct_skips_review_when_no_files(self, tmp_path):
        """_run_instruct skips review agent when there are no changed files."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
        )
        journal = MagicMock()

        # No pre_run_sha, no code_files, no test_files → no changed files
        orch._run_instruct(ctx, "Use type hints", tmp_path, journal)

        # Should still log the instruction
        journal.log_instruct.assert_called_once_with("Use type hints")

    def test_run_instruct_tracks_usage(self, tmp_path):
        """_run_instruct captures usage into ctx.step_usage."""
        from levelup.agents.backend import AgentResult

        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        # Set up a mock backend
        mock_backend = MagicMock()
        mock_backend.run_agent.return_value = AgentResult(
            text="Fixed", cost_usd=0.01, input_tokens=100, output_tokens=50,
        )
        orch._backend = mock_backend

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
            code_files=[FileChange(path="src/foo.py", content="x = 1")],
        )
        journal = MagicMock()

        orch._run_instruct(ctx, "Use type hints", tmp_path, journal)

        assert "instruct_review" in ctx.step_usage
        assert ctx.step_usage["instruct_review"].cost_usd == 0.01

    def test_get_changed_files_from_context(self, tmp_path):
        """_get_changed_files falls back to context when no git."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
            code_files=[
                FileChange(path="src/a.py", content=""),
                FileChange(path="src/b.py", content=""),
            ],
            test_files=[FileChange(path="tests/test_a.py", content="")],
        )
        files = orch._get_changed_files(ctx, tmp_path)
        assert set(files) == {"src/a.py", "src/b.py", "tests/test_a.py"}

    def test_read_ticket_settings_empty_when_no_ticket(self, tmp_path):
        """_read_ticket_settings returns {} when ctx has no ticket source."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
        )
        result = orch._read_ticket_settings(ctx)
        assert result == {}

    def test_read_ticket_settings_returns_metadata(self, tmp_path):
        """_read_ticket_settings reads model/effort/skip_planning from ticket metadata."""
        from levelup.core.tickets import add_ticket, update_ticket

        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        # Create a ticket with adaptive metadata
        ticket = add_ticket(tmp_path, "Test ticket", "desc", filename=settings.project.tickets_file)
        update_ticket(
            tmp_path, ticket.number,
            metadata={"model": "opus", "effort": "high", "skip_planning": True},
            filename=settings.project.tickets_file,
        )

        ctx = PipelineContext(
            task=TaskInput(
                title="Test ticket",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
        )
        result = orch._read_ticket_settings(ctx)
        assert result["model"] == "opus"
        assert result["effort"] == "high"
        assert result["skip_planning"] is True

    def test_cli_params_stored_on_orchestrator(self, tmp_path):
        """CLI adaptive params are stored on the orchestrator."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(
            settings=settings,
            cli_model_override=True,
            cli_effort="medium",
            cli_skip_planning=True,
        )
        assert orch._cli_model_override is True
        assert orch._cli_effort == "medium"
        assert orch._cli_skip_planning is True

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_skip_planning_removes_planning_step(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """When cli_skip_planning=True, planning step is excluded from pipeline."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings, cli_skip_planning=True)

        mock_detect.return_value = None
        agent_names_called: list[str] = []

        def track_agent(name, ctx):
            agent_names_called.append(name)
            return ctx

        mock_agent.side_effect = track_agent

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        assert "planning" not in agent_names_called

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    def test_create_backend_with_model_override(self, mock_subprocess, mock_which, tmp_path):
        """_create_backend uses model_override when provided."""
        from levelup.agents.backend import ClaudeCodeBackend
        settings = self._make_settings(tmp_path, backend="claude_code")
        orch = Orchestrator(settings=settings)
        backend = orch._create_backend(tmp_path, model_override="claude-opus-4-6")
        assert isinstance(backend, ClaudeCodeBackend)
        assert backend._client._model == "claude-opus-4-6"

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    def test_create_backend_with_thinking_budget(self, mock_subprocess, mock_which, tmp_path):
        """_create_backend passes thinking_budget to backend constructor."""
        settings = self._make_settings(tmp_path, backend="claude_code")
        orch = Orchestrator(settings=settings)
        backend = orch._create_backend(tmp_path, thinking_budget=16384)
        assert backend._thinking_budget == 16384


class TestGitJournalCommit:
    """Tests for _git_journal_commit and its integration into run()/resume()."""

    def _make_settings(self, tmp_path: Path, create_git_branch: bool = True) -> LevelUpSettings:
        return LevelUpSettings(
            llm=LLMSettings(
                api_key="test-key",
                model="test-model",
                backend="claude_code",
            ),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(
                require_checkpoints=False,
                create_git_branch=create_git_branch,
                max_code_iterations=2,
            ),
        )

    def _init_git_repo(self, tmp_path: Path):
        """Initialise a git repo with an initial commit so HEAD exists."""
        import git

        repo = git.Repo.init(tmp_path)
        (tmp_path / "README.md").write_text("init")
        repo.index.add(["README.md"])
        repo.index.commit("initial commit")
        return repo

    def test_journal_committed_on_successful_run(self, tmp_path):
        """_git_journal_commit creates a commit for the journal file."""
        import git

        repo = self._init_git_repo(tmp_path)

        settings = self._make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Add login feature"),
            project_path=tmp_path,
            status=PipelineStatus.COMPLETED,
            pre_run_sha=repo.head.commit.hexsha,
        )

        # Create a journal with a file on disk
        from levelup.core.journal import RunJournal

        journal = RunJournal(ctx)
        journal.write_header(ctx)
        assert journal.path.exists()

        orch._git_journal_commit(tmp_path, ctx, journal)

        # Verify the commit was created
        latest = repo.head.commit
        assert "levelup(documentation)" in latest.message
        assert "Add login feature" in latest.message
        assert ctx.run_id in latest.message

    def test_journal_not_committed_when_create_git_branch_false(self, tmp_path):
        """No commit when create_git_branch setting is False."""
        import git

        repo = self._init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        settings = self._make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
            status=PipelineStatus.COMPLETED,
            pre_run_sha=initial_sha,
        )

        from levelup.core.journal import RunJournal

        journal = RunJournal(ctx)
        journal.write_header(ctx)

        orch._git_journal_commit(tmp_path, ctx, journal)

        # HEAD should not have changed
        assert repo.head.commit.hexsha == initial_sha

    def test_journal_not_committed_when_no_pre_run_sha(self, tmp_path):
        """No commit when pre_run_sha is None (no branch was created)."""
        import git

        repo = self._init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        settings = self._make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
            status=PipelineStatus.COMPLETED,
            pre_run_sha=None,
        )

        from levelup.core.journal import RunJournal

        journal = RunJournal(ctx)
        journal.write_header(ctx)

        orch._git_journal_commit(tmp_path, ctx, journal)

        assert repo.head.commit.hexsha == initial_sha

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_run_calls_journal_commit_on_completion(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """run() calls _git_journal_commit when pipeline completes successfully."""
        settings = self._make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        with patch.object(orch, "_git_journal_commit") as mock_commit:
            task = TaskInput(title="Test task")
            ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        mock_commit.assert_called_once()

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_run_skips_journal_commit_on_failure(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """run() does NOT call _git_journal_commit when pipeline fails."""
        settings = self._make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        def fail_agent(name, ctx):
            if name == "requirements":
                ctx.status = PipelineStatus.FAILED
                ctx.error_message = "API error"
            return ctx

        mock_agent.side_effect = fail_agent

        with patch.object(orch, "_git_journal_commit") as mock_commit:
            task = TaskInput(title="Test task")
            ctx = orch.run(task)

        assert ctx.status == PipelineStatus.FAILED
        mock_commit.assert_not_called()

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_resume_calls_journal_commit_on_completion(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """resume() calls _git_journal_commit when pipeline completes successfully."""
        settings = self._make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Build a context that looks like a previously failed run
        ctx = PipelineContext(
            task=TaskInput(title="Test task"),
            project_path=tmp_path,
            status=PipelineStatus.FAILED,
            current_step="detect",
        )

        with patch.object(orch, "_git_journal_commit") as mock_commit:
            ctx = orch.resume(ctx, from_step="detect")

        assert ctx.status == PipelineStatus.COMPLETED
        mock_commit.assert_called_once()
