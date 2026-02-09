"""Unit tests for ClaudeCodeClient subprocess wrapper."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from levelup.agents.claude_code_client import (
    ClaudeCodeClient,
    ClaudeCodeError,
    ClaudeCodeResult,
)


class TestClaudeCodeResult:
    def test_defaults(self):
        r = ClaudeCodeResult()
        assert r.text == ""
        assert r.session_id == ""
        assert r.cost_usd == 0.0
        assert r.duration_ms == 0.0
        assert r.num_turns == 0
        assert r.is_error is False
        assert r.returncode == 0
        assert r.stderr == ""


class TestClaudeCodeError:
    def test_basic(self):
        err = ClaudeCodeError("something failed", returncode=1, stderr="bad")
        assert str(err) == "something failed"
        assert err.returncode == 1
        assert err.stderr == "bad"

    def test_defaults(self):
        err = ClaudeCodeError("oops")
        assert err.returncode == -1
        assert err.stderr == ""


class TestClaudeCodeClient:
    def _make_completed_process(
        self,
        stdout: str = "",
        stderr: str = "",
        returncode: int = 0,
    ) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=["claude", "-p"],
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    def _success_json(self, **overrides) -> str:
        data = {
            "result": "Hello from Claude",
            "session_id": "sess_123",
            "cost_usd": 0.05,
            "input_tokens": 1200,
            "output_tokens": 350,
            "duration_ms": 1500.0,
            "num_turns": 3,
            "is_error": False,
        }
        data.update(overrides)
        return json.dumps(data)

    @patch("levelup.agents.claude_code_client.subprocess.run")
    def test_command_construction(self, mock_run: MagicMock):
        mock_run.return_value = self._make_completed_process(
            stdout=self._success_json()
        )

        client = ClaudeCodeClient(model="test-model", claude_executable="my-claude")
        client.run(
            prompt="hello",
            system_prompt="You are helpful",
            allowed_tools=["Read", "Write"],
            working_directory="/tmp/project",
            timeout=300,
        )

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        cmd = call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs.get("args")
        assert cmd[0] == "my-claude"
        assert "-p" in cmd
        assert "--output-format" in cmd
        assert "json" in cmd
        assert "--model" in cmd
        assert "test-model" in cmd
        assert "--system-prompt" in cmd
        assert "You are helpful" in cmd
        assert "--allowedTools" in cmd
        assert "Read,Write" in cmd
        assert call_kwargs.kwargs["cwd"] == "/tmp/project"
        assert call_kwargs.kwargs["timeout"] == 300
        assert call_kwargs.kwargs["input"] == "hello"

    @patch("levelup.agents.claude_code_client.subprocess.run")
    def test_success_response_parsing(self, mock_run: MagicMock):
        mock_run.return_value = self._make_completed_process(
            stdout=self._success_json()
        )

        client = ClaudeCodeClient()
        result = client.run(prompt="hello")

        assert result.text == "Hello from Claude"
        assert result.session_id == "sess_123"
        assert result.cost_usd == 0.05
        assert result.input_tokens == 1200
        assert result.output_tokens == 350
        assert result.duration_ms == 1500.0
        assert result.num_turns == 3
        assert result.is_error is False
        assert result.returncode == 0

    @patch("levelup.agents.claude_code_client.subprocess.run")
    def test_nonzero_exit_raises(self, mock_run: MagicMock):
        mock_run.return_value = self._make_completed_process(
            returncode=1, stderr="Auth failed"
        )

        client = ClaudeCodeClient()
        with pytest.raises(ClaudeCodeError) as exc_info:
            client.run(prompt="hello")

        assert exc_info.value.returncode == 1
        assert "Auth failed" in str(exc_info.value)

    @patch("levelup.agents.claude_code_client.subprocess.run")
    def test_empty_output_raises(self, mock_run: MagicMock):
        mock_run.return_value = self._make_completed_process(stdout="")

        client = ClaudeCodeClient()
        with pytest.raises(ClaudeCodeError, match="empty output"):
            client.run(prompt="hello")

    @patch("levelup.agents.claude_code_client.subprocess.run")
    def test_malformed_json_raises(self, mock_run: MagicMock):
        mock_run.return_value = self._make_completed_process(
            stdout="not json at all"
        )

        client = ClaudeCodeClient()
        with pytest.raises(ClaudeCodeError, match="Failed to parse"):
            client.run(prompt="hello")

    @patch("levelup.agents.claude_code_client.subprocess.run")
    def test_is_error_true_raises(self, mock_run: MagicMock):
        mock_run.return_value = self._make_completed_process(
            stdout=self._success_json(is_error=True, result="Something went wrong")
        )

        client = ClaudeCodeClient()
        with pytest.raises(ClaudeCodeError, match="reported error"):
            client.run(prompt="hello")

    @patch("levelup.agents.claude_code_client.subprocess.run")
    def test_timeout_raises(self, mock_run: MagicMock):
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["claude", "-p"], timeout=600
        )

        client = ClaudeCodeClient()
        with pytest.raises(ClaudeCodeError, match="timed out"):
            client.run(prompt="hello")

    @patch("levelup.agents.claude_code_client.subprocess.run")
    def test_claude_not_found_raises(self, mock_run: MagicMock):
        mock_run.side_effect = FileNotFoundError()

        client = ClaudeCodeClient()
        with pytest.raises(ClaudeCodeError, match="not found"):
            client.run(prompt="hello")

    @patch("levelup.agents.claude_code_client.subprocess.run")
    def test_no_system_prompt_omits_flag(self, mock_run: MagicMock):
        mock_run.return_value = self._make_completed_process(
            stdout=self._success_json()
        )

        client = ClaudeCodeClient()
        client.run(prompt="hello", system_prompt="")

        cmd = mock_run.call_args.args[0]
        assert "--system-prompt" not in cmd

    @patch("levelup.agents.claude_code_client.subprocess.run")
    def test_no_allowed_tools_omits_flag(self, mock_run: MagicMock):
        mock_run.return_value = self._make_completed_process(
            stdout=self._success_json()
        )

        client = ClaudeCodeClient()
        client.run(prompt="hello")

        cmd = mock_run.call_args.args[0]
        assert "--allowedTools" not in cmd
