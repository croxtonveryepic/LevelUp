"""Unit tests for src/levelup/agents/recon.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from levelup.agents.backend import AgentResult
from levelup.agents.recon import ReconAgent


class TestReconAgentInit:
    def test_stores_backend_and_path(self, tmp_path: Path):
        backend = MagicMock()
        agent = ReconAgent(backend, tmp_path, language="Python")
        assert agent.backend is backend
        assert agent.project_path == tmp_path

    def test_defaults_for_none_values(self, tmp_path: Path):
        agent = ReconAgent(MagicMock(), tmp_path)
        assert agent.language == "unknown"
        assert agent.framework == "none"
        assert agent.test_runner == "unknown"
        assert agent.test_command == "unknown"

    def test_explicit_values(self, tmp_path: Path):
        agent = ReconAgent(
            MagicMock(),
            tmp_path,
            language="Python",
            framework="FastAPI",
            test_runner="pytest",
            test_command="pytest -v",
        )
        assert agent.language == "Python"
        assert agent.framework == "FastAPI"
        assert agent.test_runner == "pytest"
        assert agent.test_command == "pytest -v"


class TestReconAgentRun:
    def test_calls_backend_run_agent(self, tmp_path: Path):
        backend = MagicMock()
        expected = AgentResult(text="done", cost_usd=0.01)
        backend.run_agent.return_value = expected

        agent = ReconAgent(
            backend,
            tmp_path,
            language="Python",
            framework="Django",
            test_runner="pytest",
            test_command="pytest",
        )
        result = agent.run()

        backend.run_agent.assert_called_once()
        call_kwargs = backend.run_agent.call_args
        assert "Python" in call_kwargs.kwargs["system_prompt"]
        assert "Django" in call_kwargs.kwargs["system_prompt"]
        assert call_kwargs.kwargs["working_directory"] == str(tmp_path)
        assert "Read" in call_kwargs.kwargs["allowed_tools"]
        assert "Write" in call_kwargs.kwargs["allowed_tools"]
        assert "Glob" in call_kwargs.kwargs["allowed_tools"]
        assert "Grep" in call_kwargs.kwargs["allowed_tools"]
        assert result is expected

    def test_returns_agent_result(self, tmp_path: Path):
        backend = MagicMock()
        expected = AgentResult(
            text="recon output",
            cost_usd=0.05,
            input_tokens=1000,
            output_tokens=500,
            duration_ms=3000.0,
            num_turns=5,
        )
        backend.run_agent.return_value = expected

        agent = ReconAgent(backend, tmp_path)
        result = agent.run()

        assert result.text == "recon output"
        assert result.cost_usd == 0.05
        assert result.input_tokens == 1000
        assert result.output_tokens == 500

    def test_system_prompt_includes_detection_results(self, tmp_path: Path):
        backend = MagicMock()
        backend.run_agent.return_value = AgentResult()

        agent = ReconAgent(
            backend,
            tmp_path,
            language="Go",
            framework="Gin",
            test_runner="go test",
            test_command="go test ./...",
        )
        agent.run()

        system_prompt = backend.run_agent.call_args.kwargs["system_prompt"]
        assert "Go" in system_prompt
        assert "Gin" in system_prompt
        assert "go test" in system_prompt
        assert "go test ./..." in system_prompt
