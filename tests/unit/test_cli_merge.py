"""Unit tests for the levelup merge CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import app

runner = CliRunner()


class TestMergeCommand:
    def test_merge_registered(self):
        """The merge command is registered on the app."""
        result = runner.invoke(app, ["merge", "--help"])
        assert result.exit_code == 0
        assert "--ticket" in result.output
        assert "--branch" in result.output

    def test_merge_help_shows_options(self):
        result = runner.invoke(app, ["merge", "--help"])
        assert "--path" in result.output
        assert "--model" in result.output
        assert "--backend" in result.output

    def test_merge_requires_ticket_or_branch(self):
        """Neither --ticket nor --branch → exit 1."""
        result = runner.invoke(app, ["merge"])
        assert result.exit_code == 1
        assert "ticket" in result.output.lower() or "branch" in result.output.lower()

    def test_merge_rejects_both_ticket_and_branch(self):
        """Both --ticket and --branch → exit 1."""
        result = runner.invoke(app, ["merge", "--ticket", "1", "--branch", "feat/x"])
        assert result.exit_code == 1
        assert "only one" in result.output.lower() or "not both" in result.output.lower()

    @patch("levelup.agents.merge.MergeAgent")
    @patch("levelup.agents.claude_code_client.ClaudeCodeClient")
    @patch("levelup.agents.backend.ClaudeCodeBackend")
    def test_merge_with_ticket_runs_agent(
        self,
        mock_backend_cls,
        mock_client_cls,
        mock_agent_cls,
        tmp_path,
    ):
        from levelup.agents.backend import AgentResult

        # Create tickets.md with a ticket that has branch_name metadata
        tickets_md = tmp_path / "levelup" / "tickets.md"
        tickets_md.parent.mkdir(parents=True, exist_ok=True)
        tickets_md.write_text(
            "## [done] Test task\n"
            "<!--metadata\n"
            "branch_name: feature/test\n"
            "-->\n"
            "Some description\n"
        )

        mock_agent = MagicMock()
        mock_agent.run.return_value = AgentResult(
            text="Merge completed successfully",
            cost_usd=0.01,
            input_tokens=100,
            output_tokens=50,
            duration_ms=2000.0,
            num_turns=3,
        )
        mock_agent_cls.return_value = mock_agent

        result = runner.invoke(app, ["merge", "--ticket", "1", "--path", str(tmp_path)])

        assert result.exit_code == 0
        mock_agent_cls.assert_called_once()
        mock_agent.run.assert_called_once_with(branch_name="feature/test")

    @patch("levelup.agents.merge.MergeAgent")
    @patch("levelup.agents.claude_code_client.ClaudeCodeClient")
    @patch("levelup.agents.backend.ClaudeCodeBackend")
    def test_merge_with_branch_runs_agent(
        self,
        mock_backend_cls,
        mock_client_cls,
        mock_agent_cls,
        tmp_path,
    ):
        from levelup.agents.backend import AgentResult

        mock_agent = MagicMock()
        mock_agent.run.return_value = AgentResult(
            text="Merge completed successfully",
            cost_usd=0.02,
            input_tokens=200,
            output_tokens=100,
            duration_ms=3000.0,
            num_turns=5,
        )
        mock_agent_cls.return_value = mock_agent

        result = runner.invoke(
            app, ["merge", "--branch", "feature/direct", "--path", str(tmp_path)]
        )

        assert result.exit_code == 0
        mock_agent.run.assert_called_once_with(branch_name="feature/direct")

    @patch("levelup.agents.merge.MergeAgent")
    @patch("levelup.agents.claude_code_client.ClaudeCodeClient")
    @patch("levelup.agents.backend.ClaudeCodeBackend")
    def test_merge_shows_usage_table(
        self,
        mock_backend_cls,
        mock_client_cls,
        mock_agent_cls,
        tmp_path,
    ):
        from levelup.agents.backend import AgentResult

        mock_agent = MagicMock()
        mock_agent.run.return_value = AgentResult(
            text="success",
            cost_usd=0.03,
            input_tokens=300,
            output_tokens=150,
            duration_ms=4000.0,
            num_turns=6,
        )
        mock_agent_cls.return_value = mock_agent

        result = runner.invoke(
            app, ["merge", "--branch", "feat/x", "--path", str(tmp_path)]
        )
        assert "Merge Usage" in result.output
        assert "$0.0300" in result.output

    @patch("levelup.agents.merge.MergeAgent")
    @patch("levelup.agents.claude_code_client.ClaudeCodeClient")
    @patch("levelup.agents.backend.ClaudeCodeBackend")
    def test_merge_updates_ticket_on_success(
        self,
        mock_backend_cls,
        mock_client_cls,
        mock_agent_cls,
        tmp_path,
    ):
        from levelup.agents.backend import AgentResult

        # Create tickets.md with a ticket that has branch_name metadata
        tickets_md = tmp_path / "levelup" / "tickets.md"
        tickets_md.parent.mkdir(parents=True, exist_ok=True)
        tickets_md.write_text(
            "## [done] Test task\n"
            "<!--metadata\n"
            "branch_name: feature/test\n"
            "-->\n"
            "Some description\n"
        )

        mock_agent = MagicMock()
        mock_agent.run.return_value = AgentResult(
            text="Merge completed successfully",
            cost_usd=0.01,
            input_tokens=100,
            output_tokens=50,
            duration_ms=2000.0,
            num_turns=3,
        )
        mock_agent_cls.return_value = mock_agent

        result = runner.invoke(app, ["merge", "--ticket", "1", "--path", str(tmp_path)])

        assert result.exit_code == 0
        assert "merged" in result.output.lower()

        # Verify ticket file was updated
        content = tickets_md.read_text()
        assert "[merged]" in content

    @patch("levelup.agents.merge.MergeAgent")
    @patch("levelup.agents.claude_code_client.ClaudeCodeClient")
    @patch("levelup.agents.backend.ClaudeCodeBackend")
    def test_merge_exits_1_on_failure(
        self,
        mock_backend_cls,
        mock_client_cls,
        mock_agent_cls,
        tmp_path,
    ):
        from levelup.agents.backend import AgentResult

        mock_agent = MagicMock()
        mock_agent.run.return_value = AgentResult(
            text="error: merge failed due to conflicts",
            cost_usd=0.01,
            input_tokens=100,
            output_tokens=50,
            duration_ms=2000.0,
            num_turns=3,
        )
        mock_agent_cls.return_value = mock_agent

        result = runner.invoke(
            app, ["merge", "--branch", "feat/broken", "--path", str(tmp_path)]
        )

        assert result.exit_code == 1

    def test_merge_ticket_not_found(self, tmp_path):
        """Bad ticket number → exit 1."""
        # Create empty tickets.md
        tickets_md = tmp_path / "levelup" / "tickets.md"
        tickets_md.parent.mkdir(parents=True, exist_ok=True)
        tickets_md.write_text("")

        result = runner.invoke(app, ["merge", "--ticket", "999", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_merge_ticket_no_branch(self, tmp_path):
        """Ticket with no branch_name metadata → exit 1."""
        tickets_md = tmp_path / "levelup" / "tickets.md"
        tickets_md.parent.mkdir(parents=True, exist_ok=True)
        tickets_md.write_text(
            "## [done] Test task\n"
            "Some description\n"
        )

        result = runner.invoke(app, ["merge", "--ticket", "1", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "branch_name" in result.output.lower()
