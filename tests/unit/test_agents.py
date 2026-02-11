"""Unit tests for levelup agents (src/levelup/agents/)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from levelup.agents.backend import AgentResult, AnthropicSDKBackend, Backend, ClaudeCodeBackend
from levelup.agents.base import BaseAgent
from levelup.agents.claude_code_client import ClaudeCodeClient
from levelup.agents.llm_client import LLMClient, ToolLoopResult
from levelup.agents.requirements import RequirementsAgent
from levelup.agents.planning import PlanningAgent
from levelup.agents.test_writer import TestWriterAgent
from levelup.agents.coder import CodeAgent
from levelup.agents.reviewer import ReviewAgent
from levelup.core.context import (
    FileChange,
    PipelineContext,
    Plan,
    PlanStep,
    Requirement,
    Requirements,
    Severity,
    TaskInput,
    TestResult,
)
from levelup.tools.base import ToolRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def task_input() -> TaskInput:
    return TaskInput(title="Add login endpoint", description="Implement POST /login with JWT auth")


@pytest.fixture()
def basic_ctx(task_input: TaskInput, tmp_path: Path) -> PipelineContext:
    """A minimal pipeline context suitable for most agent tests."""
    return PipelineContext(
        task=task_input,
        project_path=tmp_path,
        language="python",
        framework="fastapi",
        test_runner="pytest",
        test_command="pytest tests/",
    )


@pytest.fixture()
def rich_ctx(basic_ctx: PipelineContext) -> PipelineContext:
    """Context with requirements, plan, test files, code files, and test results populated."""
    basic_ctx.requirements = Requirements(
        summary="Implement login",
        requirements=[
            Requirement(description="POST /login returns JWT token", acceptance_criteria=["returns 200"])
        ],
        assumptions=["Users table exists"],
    )
    basic_ctx.plan = Plan(
        approach="Add endpoint with JWT signing",
        steps=[PlanStep(order=1, description="Create login route", files_to_create=["routes/login.py"])],
        affected_files=["routes/login.py"],
        risks=["Token expiry handling"],
    )
    basic_ctx.test_files = [
        FileChange(path="tests/test_login.py", content="def test_login(): pass", is_new=True)
    ]
    basic_ctx.code_files = [
        FileChange(path="routes/login.py", content="def login(): ...", is_new=True)
    ]
    basic_ctx.test_results = [
        TestResult(passed=True, total=1, failures=0, output="1 passed", command="pytest")
    ]
    return basic_ctx


@pytest.fixture()
def mock_backend() -> MagicMock:
    """A MagicMock standing in for Backend."""
    backend = MagicMock(spec=Backend)
    return backend


@pytest.fixture()
def project_path(tmp_path: Path) -> Path:
    return tmp_path


# Legacy fixtures for LLMClient-specific tests
@pytest.fixture()
def mock_llm_client() -> MagicMock:
    """A MagicMock standing in for LLMClient."""
    client = MagicMock(spec=LLMClient)
    return client


@pytest.fixture()
def tool_registry() -> ToolRegistry:
    """A ToolRegistry pre-loaded with stub tools for all names agents may request."""
    reg = ToolRegistry()

    for name in ("file_read", "file_write", "file_search", "shell", "test_runner"):
        stub = MagicMock()
        stub.name = name
        stub.description = f"stub {name}"
        stub.get_input_schema.return_value = {"type": "object", "properties": {}}
        stub.to_anthropic_schema.return_value = {
            "name": name,
            "description": f"stub {name}",
            "input_schema": {"type": "object", "properties": {}},
        }
        reg.register(stub)

    return reg


# ===========================================================================
# LLMClient
# ===========================================================================


class TestLLMClient:
    """Tests for LLMClient with a mocked anthropic.Anthropic client."""

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_structured_call_returns_text(self, MockAnthropic: MagicMock):
        # Arrange
        mock_client = MockAnthropic.return_value
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Hello from the model"

        mock_response = MagicMock()
        mock_response.content = [text_block]
        mock_client.messages.create.return_value = mock_response

        llm = LLMClient(api_key="test-key", model="claude-test")

        # Act
        result = llm.structured_call(
            system="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
        )

        # Assert
        assert result == "Hello from the model"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["system"] == "You are helpful."
        assert call_kwargs["model"] == "claude-test"

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_structured_call_passes_tools_when_provided(self, MockAnthropic: MagicMock):
        mock_client = MockAnthropic.return_value
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "result"
        mock_response = MagicMock()
        mock_response.content = [text_block]
        mock_client.messages.create.return_value = mock_response

        llm = LLMClient(api_key="k")
        tools = [{"name": "t", "description": "d", "input_schema": {}}]
        llm.structured_call(system="s", messages=[{"role": "user", "content": "q"}], tools=tools)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["tools"] == tools

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_structured_call_omits_tools_when_none(self, MockAnthropic: MagicMock):
        mock_client = MockAnthropic.return_value
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "ok"
        mock_response = MagicMock()
        mock_response.content = [text_block]
        mock_client.messages.create.return_value = mock_response

        llm = LLMClient(api_key="k")
        llm.structured_call(system="s", messages=[{"role": "user", "content": "q"}])

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "tools" not in call_kwargs

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_structured_call_joins_multiple_text_blocks(self, MockAnthropic: MagicMock):
        mock_client = MockAnthropic.return_value
        block1 = MagicMock()
        block1.type = "text"
        block1.text = "part1"
        block2 = MagicMock()
        block2.type = "text"
        block2.text = "part2"
        mock_response = MagicMock()
        mock_response.content = [block1, block2]
        mock_client.messages.create.return_value = mock_response

        llm = LLMClient(api_key="k")
        result = llm.structured_call(system="s", messages=[{"role": "user", "content": "q"}])
        assert result == "part1\npart2"

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_run_tool_loop_no_tool_use(self, MockAnthropic: MagicMock):
        """When the model responds with only text (no tool_use), the loop should return immediately."""
        mock_client = MockAnthropic.return_value
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Final answer"
        mock_response = MagicMock()
        mock_response.content = [text_block]
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_response

        llm = LLMClient(api_key="k")
        reg = ToolRegistry()
        result = llm.run_tool_loop(
            system="sys",
            messages=[{"role": "user", "content": "go"}],
            tools=[],
            tool_registry=reg,
        )
        assert result.text == "Final answer"
        # Only one API call since there was no tool use
        assert mock_client.messages.create.call_count == 1

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_run_tool_loop_one_tool_call(self, MockAnthropic: MagicMock):
        """Simulate: first response uses a tool, second response is final text."""
        mock_client = MockAnthropic.return_value

        # First response: tool_use
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "call_1"
        tool_block.name = "dummy"
        tool_block.input = {"x": "1"}
        resp1 = MagicMock()
        resp1.content = [tool_block]
        resp1.usage = MagicMock()
        resp1.usage.input_tokens = 100
        resp1.usage.output_tokens = 50

        # Second response: text
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Done"
        resp2 = MagicMock()
        resp2.content = [text_block]
        resp2.usage = MagicMock()
        resp2.usage.input_tokens = 100
        resp2.usage.output_tokens = 50

        mock_client.messages.create.side_effect = [resp1, resp2]

        # Register a tool that the loop will execute
        reg = ToolRegistry()
        dummy_tool = MagicMock()
        dummy_tool.name = "dummy"
        dummy_tool.execute.return_value = "tool_result_value"
        reg.register(dummy_tool)

        llm = LLMClient(api_key="k")
        result = llm.run_tool_loop(
            system="sys",
            messages=[{"role": "user", "content": "go"}],
            tools=[{"name": "dummy"}],
            tool_registry=reg,
        )
        assert result.text == "Done"
        assert mock_client.messages.create.call_count == 2
        dummy_tool.execute.assert_called_once_with(x="1")

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_run_tool_loop_on_tool_call_callback(self, MockAnthropic: MagicMock):
        """The on_tool_call callback receives (name, input, result)."""
        mock_client = MockAnthropic.return_value

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "c1"
        tool_block.name = "my_tool"
        tool_block.input = {"key": "val"}
        resp1 = MagicMock()
        resp1.content = [tool_block]
        resp1.usage = MagicMock()
        resp1.usage.input_tokens = 100
        resp1.usage.output_tokens = 50

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "end"
        resp2 = MagicMock()
        resp2.content = [text_block]
        resp2.usage = MagicMock()
        resp2.usage.input_tokens = 100
        resp2.usage.output_tokens = 50

        mock_client.messages.create.side_effect = [resp1, resp2]

        reg = ToolRegistry()
        tool = MagicMock()
        tool.name = "my_tool"
        tool.execute.return_value = "got_it"
        reg.register(tool)

        callback = MagicMock()
        llm = LLMClient(api_key="k")
        llm.run_tool_loop(
            system="s",
            messages=[{"role": "user", "content": "q"}],
            tools=[],
            tool_registry=reg,
            on_tool_call=callback,
        )
        callback.assert_called_once_with("my_tool", {"key": "val"}, "got_it")

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_run_tool_loop_unknown_tool(self, MockAnthropic: MagicMock):
        """When the model calls a tool not in the registry, an error result is sent back."""
        mock_client = MockAnthropic.return_value

        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.id = "c1"
        tool_block.name = "nonexistent_tool"
        tool_block.input = {}
        resp1 = MagicMock()
        resp1.content = [tool_block]
        resp1.usage = MagicMock()
        resp1.usage.input_tokens = 100
        resp1.usage.output_tokens = 50

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "fallback"
        resp2 = MagicMock()
        resp2.content = [text_block]
        resp2.usage = MagicMock()
        resp2.usage.input_tokens = 100
        resp2.usage.output_tokens = 50

        mock_client.messages.create.side_effect = [resp1, resp2]

        reg = ToolRegistry()
        llm = LLMClient(api_key="k")
        result = llm.run_tool_loop(
            system="s",
            messages=[{"role": "user", "content": "q"}],
            tools=[],
            tool_registry=reg,
        )
        assert result.text == "fallback"
        # The second call's messages should include the error tool_result
        second_call_msgs = mock_client.messages.create.call_args_list[1].kwargs["messages"]
        tool_result_content = second_call_msgs[-1]["content"]
        assert any("Error" in tr["content"] for tr in tool_result_content)


# ===========================================================================
# BaseAgent (abstract)
# ===========================================================================


class TestBaseAgent:
    def test_cannot_instantiate_directly(self, mock_backend: MagicMock, project_path: Path):
        with pytest.raises(TypeError):
            BaseAgent(backend=mock_backend, project_path=project_path)

    def test_subclass_must_implement_abstract_methods(self, tmp_path: Path):
        """A subclass that doesn't implement all abstract methods cannot be instantiated."""
        class IncompleteAgent(BaseAgent):
            name = "incomplete"
            description = "missing methods"

        with pytest.raises(TypeError):
            IncompleteAgent(backend=MagicMock(), project_path=tmp_path)


# ===========================================================================
# Backend implementations
# ===========================================================================


class TestClaudeCodeBackend:
    def test_run_agent_returns_text(self):
        mock_client = MagicMock(spec=ClaudeCodeClient)
        mock_result = MagicMock()
        mock_result.text = "Hello from Claude"
        mock_client.run.return_value = mock_result

        backend = ClaudeCodeBackend(mock_client)
        result = backend.run_agent(
            system_prompt="sys",
            user_prompt="hello",
            allowed_tools=["Read"],
            working_directory="/tmp",
        )

        assert isinstance(result, AgentResult)
        assert result.text == "Hello from Claude"
        mock_client.run.assert_called_once_with(
            prompt="hello",
            system_prompt="sys",
            allowed_tools=["Read"],
            working_directory="/tmp",
            thinking_budget=None,
        )


class TestAnthropicSDKBackend:
    def test_run_agent_maps_tools_and_calls_llm(self, mock_llm_client, tool_registry):
        mock_llm_client.run_tool_loop.return_value = ToolLoopResult(text="agent response")
        backend = AnthropicSDKBackend(mock_llm_client, tool_registry)

        result = backend.run_agent(
            system_prompt="sys",
            user_prompt="hello",
            allowed_tools=["Read", "Glob"],
            working_directory="/tmp",
        )

        assert isinstance(result, AgentResult)
        assert result.text == "agent response"
        mock_llm_client.run_tool_loop.assert_called_once()

    def test_tool_name_mapping(self, mock_llm_client, tool_registry):
        backend = AnthropicSDKBackend(mock_llm_client, tool_registry)
        mapped = backend._map_tool_names(["Read", "Write", "Edit", "Glob", "Grep", "Bash"])
        assert "file_read" in mapped
        assert "file_write" in mapped
        assert "file_search" in mapped
        assert "shell" in mapped
        assert "test_runner" in mapped


# ===========================================================================
# RequirementsAgent
# ===========================================================================


class TestRequirementsAgent:
    def test_get_system_prompt_contains_context(self, mock_backend, project_path, basic_ctx):
        agent = RequirementsAgent(backend=mock_backend, project_path=project_path)
        prompt = agent.get_system_prompt(basic_ctx)
        assert isinstance(prompt, str)
        assert "project_context.md" in prompt
        assert basic_ctx.task.title in prompt
        assert basic_ctx.task.description in prompt

    def test_get_allowed_tools(self, mock_backend, project_path):
        agent = RequirementsAgent(backend=mock_backend, project_path=project_path)
        tools = agent.get_allowed_tools()
        assert "Read" in tools
        assert "Write" in tools
        assert "Glob" in tools
        assert "Grep" in tools

    def test_run_parses_json_response(self, mock_backend, project_path, basic_ctx):
        response_json = json.dumps({
            "summary": "Implement login endpoint",
            "requirements": [
                {
                    "description": "POST /login returns JWT",
                    "acceptance_criteria": ["Returns 200 with token"],
                }
            ],
            "assumptions": ["Users table exists"],
            "out_of_scope": ["Password reset"],
            "clarifications": [],
        })
        mock_backend.run_agent.return_value = AgentResult(text=response_json)

        agent = RequirementsAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(basic_ctx)

        assert ctx.requirements is not None
        assert ctx.requirements.summary == "Implement login endpoint"
        assert len(ctx.requirements.requirements) == 1
        assert ctx.requirements.requirements[0].description == "POST /login returns JWT"
        assert ctx.requirements.assumptions == ["Users table exists"]
        assert ctx.requirements.out_of_scope == ["Password reset"]

    def test_run_handles_malformed_json(self, mock_backend, project_path, basic_ctx):
        mock_backend.run_agent.return_value = AgentResult(text="This is not JSON at all")

        agent = RequirementsAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(basic_ctx)

        # Should fall back gracefully
        assert ctx.requirements is not None
        assert len(ctx.requirements.requirements) == 1


# ===========================================================================
# PlanningAgent
# ===========================================================================


class TestPlanningAgent:
    def test_get_system_prompt_contains_context(self, mock_backend, project_path, rich_ctx):
        agent = PlanningAgent(backend=mock_backend, project_path=project_path)
        prompt = agent.get_system_prompt(rich_ctx)
        assert isinstance(prompt, str)
        assert "project_context.md" in prompt
        assert "Implement login" in prompt  # from requirements summary

    def test_get_system_prompt_no_requirements(self, mock_backend, project_path, basic_ctx):
        agent = PlanningAgent(backend=mock_backend, project_path=project_path)
        prompt = agent.get_system_prompt(basic_ctx)
        assert "No structured requirements" in prompt

    def test_get_allowed_tools(self, mock_backend, project_path):
        agent = PlanningAgent(backend=mock_backend, project_path=project_path)
        assert agent.get_allowed_tools() == ["Read", "Write", "Glob", "Grep"]

    def test_run_parses_plan(self, mock_backend, project_path, rich_ctx):
        response_json = json.dumps({
            "approach": "Create login route with JWT",
            "steps": [
                {
                    "order": 1,
                    "description": "Create login handler",
                    "files_to_modify": [],
                    "files_to_create": ["routes/login.py"],
                }
            ],
            "affected_files": ["routes/login.py"],
            "risks": ["Token may expire"],
        })
        mock_backend.run_agent.return_value = AgentResult(text=response_json)

        agent = PlanningAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(rich_ctx)

        assert ctx.plan is not None
        assert ctx.plan.approach == "Create login route with JWT"
        assert len(ctx.plan.steps) == 1
        assert ctx.plan.steps[0].files_to_create == ["routes/login.py"]
        assert ctx.plan.risks == ["Token may expire"]

    def test_run_handles_malformed_json(self, mock_backend, project_path, basic_ctx):
        mock_backend.run_agent.return_value = AgentResult(text="Not valid JSON")

        agent = PlanningAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(basic_ctx)

        assert ctx.plan is not None
        assert len(ctx.plan.steps) == 1  # fallback creates one step


# ===========================================================================
# TestWriterAgent
# ===========================================================================


class TestTestWriterAgent:
    def test_get_system_prompt_contains_context(self, mock_backend, project_path, rich_ctx):
        agent = TestWriterAgent(backend=mock_backend, project_path=project_path)
        prompt = agent.get_system_prompt(rich_ctx)
        assert isinstance(prompt, str)
        assert "project_context.md" in prompt
        assert "TDD" in prompt
        assert "Implement login" in prompt  # requirements summary
        assert "Add endpoint" in prompt or "login route" in prompt.lower() or "JWT" in prompt

    def test_get_system_prompt_no_requirements_no_plan(self, mock_backend, project_path, basic_ctx):
        agent = TestWriterAgent(backend=mock_backend, project_path=project_path)
        prompt = agent.get_system_prompt(basic_ctx)
        assert "No structured requirements" in prompt
        assert "No implementation plan" in prompt

    def test_get_allowed_tools(self, mock_backend, project_path):
        agent = TestWriterAgent(backend=mock_backend, project_path=project_path)
        tools = agent.get_allowed_tools()
        assert "Read" in tools
        assert "Write" in tools
        assert "Edit" in tools
        assert "Bash" in tools

    def test_run_populates_test_files(self, mock_backend, project_path, basic_ctx):
        # Create a test file on disk for the agent to read back
        test_file = project_path / "tests" / "test_new.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def test_example(): assert True", encoding="utf-8")

        # Set the project_path on basic_ctx to match
        basic_ctx.project_path = project_path

        mock_backend.run_agent.return_value = AgentResult(text=json.dumps({
            "test_files": [{"path": "tests/test_new.py", "description": "New tests"}]
        }))

        agent = TestWriterAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(basic_ctx)

        assert len(ctx.test_files) == 1
        assert ctx.test_files[0].path == "tests/test_new.py"
        assert ctx.test_files[0].content == "def test_example(): assert True"
        assert ctx.test_files[0].is_new is True

    def test_run_skips_missing_files(self, mock_backend, project_path, basic_ctx):
        basic_ctx.project_path = project_path
        mock_backend.run_agent.return_value = AgentResult(text=json.dumps({
            "test_files": [{"path": "tests/nonexistent.py", "description": "Missing"}]
        }))

        agent = TestWriterAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(basic_ctx)

        # File that doesn't exist should NOT be added to test_files
        assert len(ctx.test_files) == 0


# ===========================================================================
# CodeAgent
# ===========================================================================


class TestCodeAgent:
    def test_get_system_prompt_contains_context(self, mock_backend, project_path, rich_ctx):
        agent = CodeAgent(backend=mock_backend, project_path=project_path)
        prompt = agent.get_system_prompt(rich_ctx)
        assert isinstance(prompt, str)
        assert "project_context.md" in prompt
        assert "TDD green phase" in prompt
        assert "tests/test_login.py" in prompt  # test file path
        assert "Implement login" in prompt  # requirements summary

    def test_get_system_prompt_no_test_files(self, mock_backend, project_path, basic_ctx):
        agent = CodeAgent(backend=mock_backend, project_path=project_path)
        prompt = agent.get_system_prompt(basic_ctx)
        assert "No test files" in prompt

    def test_get_allowed_tools(self, mock_backend, project_path):
        agent = CodeAgent(backend=mock_backend, project_path=project_path)
        tools = agent.get_allowed_tools()
        assert "Read" in tools
        assert "Write" in tools
        assert "Edit" in tools
        assert "Bash" in tools

    def test_run_populates_code_files(self, mock_backend, project_path, basic_ctx):
        # Create a code file on disk
        code_file = project_path / "src" / "login.py"
        code_file.parent.mkdir(parents=True, exist_ok=True)
        code_file.write_text("def login(): return 'token'", encoding="utf-8")

        basic_ctx.project_path = project_path
        basic_ctx.test_command = None  # skip final test run

        mock_backend.run_agent.return_value = AgentResult(text=json.dumps({
            "files_written": ["src/login.py"],
            "iterations": 1,
            "all_tests_passing": True,
        }))

        agent = CodeAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(basic_ctx)

        assert len(ctx.code_files) == 1
        assert ctx.code_files[0].path == "src/login.py"
        assert ctx.code_files[0].content == "def login(): return 'token'"

    def test_run_sets_iteration_count(self, mock_backend, project_path, basic_ctx):
        basic_ctx.project_path = project_path
        basic_ctx.test_command = None

        mock_backend.run_agent.return_value = AgentResult(text=json.dumps({
            "files_written": [],
            "iterations": 3,
            "all_tests_passing": True,
        }))

        agent = CodeAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(basic_ctx)

        assert ctx.code_iteration == 3


# ===========================================================================
# ReviewAgent
# ===========================================================================


class TestReviewAgent:
    def test_get_system_prompt_contains_context(self, mock_backend, project_path, rich_ctx):
        agent = ReviewAgent(backend=mock_backend, project_path=project_path)
        prompt = agent.get_system_prompt(rich_ctx)
        assert isinstance(prompt, str)
        assert "project_context.md" in prompt
        assert "tests/test_login.py" in prompt
        assert "routes/login.py" in prompt
        assert "PASSED" in prompt  # from test results

    def test_get_system_prompt_empty_context(self, mock_backend, project_path, basic_ctx):
        agent = ReviewAgent(backend=mock_backend, project_path=project_path)
        prompt = agent.get_system_prompt(basic_ctx)
        assert "No test files" in prompt
        assert "No code files" in prompt
        assert "No test results" in prompt

    def test_get_allowed_tools(self, mock_backend, project_path):
        agent = ReviewAgent(backend=mock_backend, project_path=project_path)
        tools = agent.get_allowed_tools()
        assert "Read" in tools
        assert "Glob" in tools
        assert "Grep" in tools
        # ReviewAgent should NOT have write/shell access
        assert "Write" not in tools
        assert "Bash" not in tools

    def test_run_parses_findings(self, mock_backend, project_path, rich_ctx):
        response_json = json.dumps({
            "findings": [
                {
                    "severity": "warning",
                    "category": "security",
                    "file": "routes/login.py",
                    "line": 10,
                    "message": "Password not hashed",
                    "suggestion": "Use bcrypt",
                },
                {
                    "severity": "info",
                    "category": "best_practices",
                    "file": "routes/login.py",
                    "line": 5,
                    "message": "Add docstring",
                    "suggestion": "Document the function",
                },
            ],
            "overall_assessment": "Needs improvement",
        })
        mock_backend.run_agent.return_value = AgentResult(text=response_json)

        agent = ReviewAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(rich_ctx)

        assert len(ctx.review_findings) == 2
        assert ctx.review_findings[0].severity == Severity.WARNING
        assert ctx.review_findings[0].category == "security"
        assert ctx.review_findings[0].message == "Password not hashed"
        assert ctx.review_findings[0].suggestion == "Use bcrypt"
        assert ctx.review_findings[1].severity == Severity.INFO

    def test_run_handles_empty_findings(self, mock_backend, project_path, rich_ctx):
        response_json = json.dumps({
            "findings": [],
            "overall_assessment": "All good",
        })
        mock_backend.run_agent.return_value = AgentResult(text=response_json)

        agent = ReviewAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(rich_ctx)

        assert ctx.review_findings == []

    def test_run_handles_malformed_json(self, mock_backend, project_path, rich_ctx):
        mock_backend.run_agent.return_value = AgentResult(text="not json")

        agent = ReviewAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(rich_ctx)

        # Should return empty findings on parse failure
        assert ctx.review_findings == []

    def test_run_handles_invalid_severity(self, mock_backend, project_path, rich_ctx):
        response_json = json.dumps({
            "findings": [
                {
                    "severity": "bogus_level",
                    "category": "general",
                    "file": "x.py",
                    "message": "Something",
                }
            ],
            "overall_assessment": "Ok",
        })
        mock_backend.run_agent.return_value = AgentResult(text=response_json)

        agent = ReviewAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(rich_ctx)

        # Should fall back to INFO for invalid severity
        assert len(ctx.review_findings) == 1
        assert ctx.review_findings[0].severity == Severity.INFO
