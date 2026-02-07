"""Comprehensive tests for cost/token tracking across the pipeline."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from levelup.agents.backend import AgentResult, AnthropicSDKBackend, ClaudeCodeBackend
from levelup.agents.claude_code_client import ClaudeCodeClient
from levelup.agents.llm_client import LLMClient, ToolLoopResult
from levelup.core.context import PipelineContext, PipelineStatus, StepUsage, TaskInput
from levelup.core.journal import RunJournal
from levelup.state.db import (
    CURRENT_SCHEMA_VERSION,
    SCHEMA_SQL,
    _get_schema_version,
    get_connection,
    init_db,
)
from levelup.state.manager import StateManager
from levelup.tools.base import BaseTool, ToolRegistry


# ------------------------------------------------------------------ #
# 1. AgentResult dataclass
# ------------------------------------------------------------------ #


class TestAgentResultDefaults:
    """AgentResult should initialize all fields to zero/empty defaults."""

    def test_default_text(self):
        result = AgentResult()
        assert result.text == ""

    def test_default_cost_usd(self):
        result = AgentResult()
        assert result.cost_usd == 0.0

    def test_default_input_tokens(self):
        result = AgentResult()
        assert result.input_tokens == 0

    def test_default_output_tokens(self):
        result = AgentResult()
        assert result.output_tokens == 0

    def test_default_duration_ms(self):
        result = AgentResult()
        assert result.duration_ms == 0.0

    def test_default_num_turns(self):
        result = AgentResult()
        assert result.num_turns == 0


class TestAgentResultWithValues:
    """AgentResult should store provided values correctly."""

    def test_all_fields(self):
        result = AgentResult(
            text="hello world",
            cost_usd=0.123,
            input_tokens=500,
            output_tokens=200,
            duration_ms=2500.5,
            num_turns=4,
        )
        assert result.text == "hello world"
        assert result.cost_usd == 0.123
        assert result.input_tokens == 500
        assert result.output_tokens == 200
        assert result.duration_ms == 2500.5
        assert result.num_turns == 4

    def test_partial_fields(self):
        result = AgentResult(text="partial", cost_usd=0.01)
        assert result.text == "partial"
        assert result.cost_usd == 0.01
        assert result.input_tokens == 0
        assert result.output_tokens == 0
        assert result.duration_ms == 0.0
        assert result.num_turns == 0


# ------------------------------------------------------------------ #
# 2. ToolLoopResult dataclass
# ------------------------------------------------------------------ #


class TestToolLoopResultDefaults:
    """ToolLoopResult should initialize all fields to zero/empty defaults."""

    def test_default_text(self):
        result = ToolLoopResult()
        assert result.text == ""

    def test_default_input_tokens(self):
        result = ToolLoopResult()
        assert result.input_tokens == 0

    def test_default_output_tokens(self):
        result = ToolLoopResult()
        assert result.output_tokens == 0

    def test_default_num_turns(self):
        result = ToolLoopResult()
        assert result.num_turns == 0


class TestToolLoopResultWithValues:
    """ToolLoopResult should store provided values correctly."""

    def test_all_fields(self):
        result = ToolLoopResult(
            text="done",
            input_tokens=1000,
            output_tokens=500,
            num_turns=3,
        )
        assert result.text == "done"
        assert result.input_tokens == 1000
        assert result.output_tokens == 500
        assert result.num_turns == 3

    def test_partial_fields(self):
        result = ToolLoopResult(text="partial", num_turns=1)
        assert result.text == "partial"
        assert result.input_tokens == 0
        assert result.output_tokens == 0
        assert result.num_turns == 1


# ------------------------------------------------------------------ #
# 3. ClaudeCodeBackend returns AgentResult with cost fields
# ------------------------------------------------------------------ #


class TestClaudeCodeBackendCostFields:
    """ClaudeCodeBackend.run_agent should return AgentResult with cost fields from ClaudeCodeClient."""

    def test_returns_agent_result_with_cost_fields(self):
        mock_client = MagicMock(spec=ClaudeCodeClient)
        mock_result = MagicMock()
        mock_result.text = "hello"
        mock_result.cost_usd = 0.05
        mock_result.duration_ms = 1500.0
        mock_result.num_turns = 3
        mock_client.run.return_value = mock_result

        backend = ClaudeCodeBackend(client=mock_client)
        result = backend.run_agent(
            system_prompt="You are helpful.",
            user_prompt="Do something",
            allowed_tools=["Read"],
            working_directory="/tmp/project",
        )

        assert isinstance(result, AgentResult)
        assert result.text == "hello"
        assert result.cost_usd == 0.05
        assert result.duration_ms == 1500.0
        assert result.num_turns == 3

    def test_cost_fields_zero_by_default(self):
        mock_client = MagicMock(spec=ClaudeCodeClient)
        mock_result = MagicMock()
        mock_result.text = "result"
        mock_result.cost_usd = 0.0
        mock_result.duration_ms = 0.0
        mock_result.num_turns = 0
        mock_client.run.return_value = mock_result

        backend = ClaudeCodeBackend(client=mock_client)
        result = backend.run_agent(
            system_prompt="sys",
            user_prompt="usr",
            allowed_tools=[],
            working_directory="/tmp",
        )

        assert result.cost_usd == 0.0
        assert result.duration_ms == 0.0
        assert result.num_turns == 0

    def test_passes_arguments_to_client(self):
        mock_client = MagicMock(spec=ClaudeCodeClient)
        mock_result = MagicMock()
        mock_result.text = ""
        mock_result.cost_usd = 0.0
        mock_result.duration_ms = 0.0
        mock_result.num_turns = 0
        mock_client.run.return_value = mock_result

        backend = ClaudeCodeBackend(client=mock_client)
        backend.run_agent(
            system_prompt="system",
            user_prompt="user",
            allowed_tools=["Bash", "Read"],
            working_directory="/project",
        )

        mock_client.run.assert_called_once_with(
            prompt="user",
            system_prompt="system",
            allowed_tools=["Bash", "Read"],
            working_directory="/project",
        )


# ------------------------------------------------------------------ #
# 4. AnthropicSDKBackend returns AgentResult with token fields
# ------------------------------------------------------------------ #


class _StubTool(BaseTool):
    """Minimal tool for testing ToolRegistry interactions."""

    name = "file_read"
    description = "Read a file"

    def get_input_schema(self):
        return {"type": "object", "properties": {"path": {"type": "string"}}}

    def execute(self, **kwargs):
        return "file contents"


class TestAnthropicSDKBackendTokenFields:
    """AnthropicSDKBackend.run_agent should return AgentResult with token fields from LLMClient."""

    def test_returns_agent_result_with_token_fields(self):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="resp",
            input_tokens=500,
            output_tokens=200,
            num_turns=2,
        )

        registry = ToolRegistry()
        registry.register(_StubTool())

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)
        result = backend.run_agent(
            system_prompt="sys prompt",
            user_prompt="do work",
            allowed_tools=["Read"],
            working_directory="/tmp/proj",
        )

        assert isinstance(result, AgentResult)
        assert result.text == "resp"
        assert result.input_tokens == 500
        assert result.output_tokens == 200
        assert result.num_turns == 2

    def test_cost_usd_defaults_to_zero(self):
        """AnthropicSDKBackend does not set cost_usd (it comes from token counts)."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.run_tool_loop.return_value = ToolLoopResult(
            text="ok", input_tokens=100, output_tokens=50, num_turns=1,
        )

        registry = ToolRegistry()
        registry.register(_StubTool())

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)
        result = backend.run_agent(
            system_prompt="s",
            user_prompt="u",
            allowed_tools=["Read"],
            working_directory="/tmp",
        )

        assert result.cost_usd == 0.0

    def test_maps_tool_names_correctly(self):
        """Allowed tools should be mapped from Claude Code names to LevelUp names."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.run_tool_loop.return_value = ToolLoopResult(text="done")

        registry = ToolRegistry()
        registry.register(_StubTool())

        backend = AnthropicSDKBackend(llm_client=mock_llm, tool_registry=registry)
        backend.run_agent(
            system_prompt="s",
            user_prompt="u",
            allowed_tools=["Read"],
            working_directory="/tmp",
        )

        # The call should have been made with schemas for the mapped tool(s)
        call_kwargs = mock_llm.run_tool_loop.call_args
        tools_arg = call_kwargs.kwargs.get("tools") or call_kwargs[1].get("tools")
        # "Read" maps to "file_read", which is registered
        assert len(tools_arg) == 1
        assert tools_arg[0]["name"] == "file_read"


# ------------------------------------------------------------------ #
# 5. LLMClient.run_tool_loop accumulates tokens across iterations
# ------------------------------------------------------------------ #


class TestLLMClientTokenAccumulation:
    """LLMClient.run_tool_loop should sum input/output tokens across all API calls."""

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_accumulates_tokens_across_turns(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # First response: tool_use (triggers another iteration)
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.id = "tool_1"
        tool_use_block.name = "file_read"
        tool_use_block.input = {"path": "foo.py"}

        response1 = MagicMock()
        response1.content = [tool_use_block]
        response1.usage = MagicMock()
        response1.usage.input_tokens = 300
        response1.usage.output_tokens = 100

        # Second response: text (final response, ends the loop)
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "All done"

        response2 = MagicMock()
        response2.content = [text_block]
        response2.usage = MagicMock()
        response2.usage.input_tokens = 400
        response2.usage.output_tokens = 150

        mock_client.messages.create.side_effect = [response1, response2]

        # Set up tool registry with a stub tool
        registry = ToolRegistry()
        registry.register(_StubTool())

        # Create LLMClient (Anthropic constructor is mocked)
        llm = LLMClient(api_key="test-key")

        tools = registry.get_anthropic_schemas(["file_read"])
        messages = [{"role": "user", "content": "read foo.py"}]

        result = llm.run_tool_loop(
            system="system prompt",
            messages=messages,
            tools=tools,
            tool_registry=registry,
        )

        assert result.input_tokens == 700  # 300 + 400
        assert result.output_tokens == 250  # 100 + 150
        assert result.num_turns == 2
        assert result.text == "All done"

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_single_turn_no_tools(self, mock_anthropic_cls):
        """When no tool use occurs, should still track tokens for the single turn."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Immediate answer"

        response = MagicMock()
        response.content = [text_block]
        response.usage = MagicMock()
        response.usage.input_tokens = 200
        response.usage.output_tokens = 80

        mock_client.messages.create.return_value = response

        llm = LLMClient(api_key="test-key")
        registry = ToolRegistry()

        result = llm.run_tool_loop(
            system="sys",
            messages=[{"role": "user", "content": "hello"}],
            tools=[],
            tool_registry=registry,
        )

        assert result.input_tokens == 200
        assert result.output_tokens == 80
        assert result.num_turns == 1
        assert result.text == "Immediate answer"

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_handles_missing_usage(self, mock_anthropic_cls):
        """When response has no usage attribute, tokens should remain zero."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "No usage info"

        response = MagicMock(spec=[])  # empty spec means no attributes
        response.content = [text_block]

        mock_client.messages.create.return_value = response

        llm = LLMClient(api_key="test-key")
        registry = ToolRegistry()

        result = llm.run_tool_loop(
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            tool_registry=registry,
        )

        assert result.input_tokens == 0
        assert result.output_tokens == 0
        assert result.num_turns == 1


# ------------------------------------------------------------------ #
# 6. StepUsage model
# ------------------------------------------------------------------ #


class TestStepUsage:
    """StepUsage Pydantic model should serialize and deserialize correctly."""

    def test_default_values(self):
        usage = StepUsage()
        assert usage.cost_usd == 0.0
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.duration_ms == 0.0
        assert usage.num_turns == 0

    def test_with_values(self):
        usage = StepUsage(
            cost_usd=0.042,
            input_tokens=1500,
            output_tokens=800,
            duration_ms=3200.5,
            num_turns=5,
        )
        assert usage.cost_usd == 0.042
        assert usage.input_tokens == 1500
        assert usage.output_tokens == 800
        assert usage.duration_ms == 3200.5
        assert usage.num_turns == 5

    def test_serialization_roundtrip(self):
        original = StepUsage(
            cost_usd=0.1,
            input_tokens=999,
            output_tokens=444,
            duration_ms=5000.0,
            num_turns=3,
        )
        data = original.model_dump()
        restored = StepUsage(**data)

        assert restored.cost_usd == original.cost_usd
        assert restored.input_tokens == original.input_tokens
        assert restored.output_tokens == original.output_tokens
        assert restored.duration_ms == original.duration_ms
        assert restored.num_turns == original.num_turns

    def test_model_dump_keys(self):
        usage = StepUsage(cost_usd=0.01)
        data = usage.model_dump()
        assert set(data.keys()) == {
            "cost_usd",
            "input_tokens",
            "output_tokens",
            "duration_ms",
            "num_turns",
        }


# ------------------------------------------------------------------ #
# 7. PipelineContext with step_usage and total_cost_usd
# ------------------------------------------------------------------ #


class TestPipelineContextCostTracking:
    """PipelineContext should persist step_usage and total_cost_usd through serialization."""

    def _make_context(self, **kwargs) -> PipelineContext:
        defaults = dict(task=TaskInput(title="test task"))
        defaults.update(kwargs)
        return PipelineContext(**defaults)

    def test_default_step_usage_empty(self):
        ctx = self._make_context()
        assert ctx.step_usage == {}
        assert ctx.total_cost_usd == 0.0

    def test_step_usage_populated(self):
        ctx = self._make_context(
            step_usage={
                "requirements": StepUsage(cost_usd=0.05, input_tokens=100, output_tokens=50),
                "coding": StepUsage(cost_usd=0.10, input_tokens=500, output_tokens=300),
            },
            total_cost_usd=0.15,
        )
        assert len(ctx.step_usage) == 2
        assert ctx.step_usage["requirements"].cost_usd == 0.05
        assert ctx.step_usage["coding"].input_tokens == 500
        assert ctx.total_cost_usd == 0.15

    def test_json_serialization_roundtrip(self):
        ctx = self._make_context(
            step_usage={
                "planning": StepUsage(
                    cost_usd=0.03,
                    input_tokens=200,
                    output_tokens=100,
                    duration_ms=2000.0,
                    num_turns=2,
                ),
            },
            total_cost_usd=0.03,
        )

        json_str = ctx.model_dump_json()
        restored = PipelineContext.model_validate_json(json_str)

        assert restored.total_cost_usd == 0.03
        assert "planning" in restored.step_usage
        assert restored.step_usage["planning"].cost_usd == 0.03
        assert restored.step_usage["planning"].input_tokens == 200
        assert restored.step_usage["planning"].output_tokens == 100
        assert restored.step_usage["planning"].duration_ms == 2000.0
        assert restored.step_usage["planning"].num_turns == 2

    def test_step_usage_added_incrementally(self):
        ctx = self._make_context()
        ctx.step_usage["detect"] = StepUsage(cost_usd=0.01)
        ctx.step_usage["requirements"] = StepUsage(cost_usd=0.04, input_tokens=300)
        ctx.total_cost_usd = 0.05

        json_str = ctx.model_dump_json()
        restored = PipelineContext.model_validate_json(json_str)

        assert len(restored.step_usage) == 2
        assert restored.total_cost_usd == 0.05


# ------------------------------------------------------------------ #
# 8. DB migration v1 -> v2
# ------------------------------------------------------------------ #


class TestDBMigrationV1ToV2:
    """init_db should migrate a v1 database to v2 and add total_cost_usd column."""

    def test_migration_creates_cost_column(self, tmp_path: Path):
        db_path = tmp_path / "test_migrate.db"

        # Create a v1 database manually
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_SQL)  # base tables without migrations
        # Apply only migration v1 (schema_version table, set version=1)
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                rowid      INTEGER PRIMARY KEY CHECK (rowid = 1),
                version    INTEGER NOT NULL,
                applied_at TEXT NOT NULL
            );
            INSERT OR REPLACE INTO schema_version (rowid, version, applied_at)
            VALUES (1, 1, datetime('now'));
            """
        )
        conn.commit()

        # Verify it is at version 1
        row = conn.execute("SELECT version FROM schema_version WHERE rowid = 1").fetchone()
        assert row[0] == 1
        conn.close()

        # Run init_db which should apply migration v2
        init_db(db_path)

        # Verify schema version is now 2
        conn = get_connection(db_path)
        version = _get_schema_version(conn)
        assert version == 2
        assert version == CURRENT_SCHEMA_VERSION

        # Verify the total_cost_usd column exists on the runs table
        cursor = conn.execute("PRAGMA table_info(runs)")
        columns = {row_info["name"] for row_info in cursor.fetchall()}
        assert "total_cost_usd" in columns

        conn.close()

    def test_fresh_db_ends_at_current_version(self, tmp_path: Path):
        db_path = tmp_path / "fresh.db"
        init_db(db_path)

        conn = get_connection(db_path)
        version = _get_schema_version(conn)
        assert version == CURRENT_SCHEMA_VERSION

        # Verify total_cost_usd exists
        cursor = conn.execute("PRAGMA table_info(runs)")
        columns = {row_info["name"] for row_info in cursor.fetchall()}
        assert "total_cost_usd" in columns
        conn.close()

    def test_idempotent_init(self, tmp_path: Path):
        db_path = tmp_path / "idempotent.db"
        init_db(db_path)
        init_db(db_path)  # second call should not fail

        conn = get_connection(db_path)
        version = _get_schema_version(conn)
        assert version == CURRENT_SCHEMA_VERSION
        conn.close()


# ------------------------------------------------------------------ #
# 9. StateManager.update_run() persists cost
# ------------------------------------------------------------------ #


class TestStateManagerCostPersistence:
    """StateManager should persist total_cost_usd via update_run."""

    def test_update_run_persists_cost(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        ctx = PipelineContext(task=TaskInput(title="cost test"))
        mgr.register_run(ctx)

        ctx.total_cost_usd = 0.1234
        ctx.status = PipelineStatus.RUNNING
        mgr.update_run(ctx)

        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.total_cost_usd == pytest.approx(0.1234)

    def test_cost_defaults_to_zero(self, tmp_path: Path):
        db_path = tmp_path / "test_zero.db"
        mgr = StateManager(db_path=db_path)

        ctx = PipelineContext(task=TaskInput(title="no cost"))
        mgr.register_run(ctx)

        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.total_cost_usd == 0.0

    def test_cost_updated_multiple_times(self, tmp_path: Path):
        db_path = tmp_path / "test_multi.db"
        mgr = StateManager(db_path=db_path)

        ctx = PipelineContext(task=TaskInput(title="multi update"))
        mgr.register_run(ctx)

        ctx.total_cost_usd = 0.05
        ctx.status = PipelineStatus.RUNNING
        mgr.update_run(ctx)

        ctx.total_cost_usd = 0.12
        mgr.update_run(ctx)

        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.total_cost_usd == pytest.approx(0.12)


# ------------------------------------------------------------------ #
# 10. Journal includes cost in step and outcome logs
# ------------------------------------------------------------------ #


class TestJournalCostTracking:
    """RunJournal should include usage info in step logs and cost in outcome."""

    def test_step_log_includes_usage(self, tmp_path: Path):
        ctx = PipelineContext(
            task=TaskInput(title="journal test"),
            project_path=tmp_path,
        )
        ctx.step_usage["requirements"] = StepUsage(
            cost_usd=0.05,
            input_tokens=100,
            output_tokens=50,
            duration_ms=1500.0,
        )

        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_step("requirements", ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "Usage" in content
        assert "$0.05" in content or "$0.0500" in content
        assert "150" in content  # 100 + 50 tokens
        assert "1.5s" in content

    def test_outcome_log_includes_total_cost(self, tmp_path: Path):
        ctx = PipelineContext(
            task=TaskInput(title="outcome test"),
            project_path=tmp_path,
            status=PipelineStatus.COMPLETED,
        )
        ctx.step_usage["requirements"] = StepUsage(
            cost_usd=0.05,
            input_tokens=100,
            output_tokens=50,
            duration_ms=1500.0,
        )
        ctx.total_cost_usd = 0.05

        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_step("requirements", ctx)
        journal.log_outcome(ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "Total cost" in content
        assert "$0.05" in content or "$0.0500" in content

    def test_outcome_without_cost_omits_line(self, tmp_path: Path):
        ctx = PipelineContext(
            task=TaskInput(title="no cost outcome"),
            project_path=tmp_path,
            status=PipelineStatus.COMPLETED,
        )

        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_outcome(ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "Total cost" not in content

    def test_step_without_usage_omits_usage_line(self, tmp_path: Path):
        ctx = PipelineContext(
            task=TaskInput(title="no usage step"),
            project_path=tmp_path,
        )

        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_step("detect", ctx)

        content = journal.path.read_text(encoding="utf-8")
        # "detect" step has no usage entry, so "Usage" should not appear
        assert "Usage" not in content

    def test_full_journal_flow(self, tmp_path: Path):
        """End-to-end: header -> step with usage -> outcome with total cost."""
        ctx = PipelineContext(
            task=TaskInput(title="full flow"),
            project_path=tmp_path,
            status=PipelineStatus.COMPLETED,
        )
        ctx.step_usage["requirements"] = StepUsage(
            cost_usd=0.05,
            input_tokens=100,
            output_tokens=50,
            duration_ms=1500.0,
        )
        ctx.total_cost_usd = 0.05

        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_step("requirements", ctx)
        journal.log_outcome(ctx)

        content = journal.path.read_text(encoding="utf-8")

        # Header
        assert "Run Journal: full flow" in content
        # Step usage
        assert "Usage" in content
        assert "$0.05" in content or "$0.0500" in content
        # Outcome
        assert "Total cost" in content
        assert "completed" in content
