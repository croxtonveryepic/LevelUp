"""Unit tests for the levelup recon CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from levelup.cli.app import app

runner = CliRunner()


class TestReconCommand:
    def test_recon_registered(self):
        """The recon command is registered on the app."""
        result = runner.invoke(app, ["recon", "--help"])
        assert result.exit_code == 0
        assert "project_context.md" in result.output

    def test_recon_help_shows_options(self):
        result = runner.invoke(app, ["recon", "--help"])
        assert "--path" in result.output
        assert "--model" in result.output
        assert "--backend" in result.output

    @patch("levelup.agents.recon.ReconAgent")
    @patch("levelup.agents.claude_code_client.ClaudeCodeClient")
    @patch("levelup.agents.backend.ClaudeCodeBackend")
    @patch("levelup.detection.detector.ProjectDetector")
    def test_recon_runs_detection_then_agent(
        self,
        mock_detector_cls,
        mock_backend_cls,
        mock_client_cls,
        mock_agent_cls,
        tmp_path,
    ):
        from levelup.agents.backend import AgentResult
        from levelup.detection.detector import ProjectInfo

        # Set up detection mock
        mock_detector = MagicMock()
        mock_detector.detect.return_value = ProjectInfo(
            language="Python", framework="Flask", test_runner="pytest", test_command="pytest"
        )
        mock_detector_cls.return_value = mock_detector

        # Set up agent mock
        mock_agent = MagicMock()
        mock_agent.run.return_value = AgentResult(
            text="done", cost_usd=0.01, input_tokens=100, output_tokens=50, duration_ms=2000.0, num_turns=3,
        )
        mock_agent_cls.return_value = mock_agent

        # Create the project_context.md to satisfy the "file was written" check
        ctx_dir = tmp_path / "levelup"
        ctx_dir.mkdir()
        (ctx_dir / "project_context.md").write_text("# Project Context\n")

        result = runner.invoke(app, ["recon", "--path", str(tmp_path)])

        # Detection should run
        mock_detector_cls.assert_called_once()
        mock_detector.detect.assert_called_once()

        # Agent should run
        mock_agent_cls.assert_called_once()
        mock_agent.run.assert_called_once()

    @patch("levelup.agents.recon.ReconAgent")
    @patch("levelup.agents.claude_code_client.ClaudeCodeClient")
    @patch("levelup.agents.backend.ClaudeCodeBackend")
    @patch("levelup.detection.detector.ProjectDetector")
    def test_recon_shows_usage_table(
        self,
        mock_detector_cls,
        mock_backend_cls,
        mock_client_cls,
        mock_agent_cls,
        tmp_path,
    ):
        from levelup.agents.backend import AgentResult
        from levelup.detection.detector import ProjectInfo

        mock_detector = MagicMock()
        mock_detector.detect.return_value = ProjectInfo(language="Python")
        mock_detector_cls.return_value = mock_detector

        mock_agent = MagicMock()
        mock_agent.run.return_value = AgentResult(
            cost_usd=0.02, input_tokens=200, output_tokens=100, duration_ms=5000.0, num_turns=4,
        )
        mock_agent_cls.return_value = mock_agent

        ctx_dir = tmp_path / "levelup"
        ctx_dir.mkdir()
        (ctx_dir / "project_context.md").write_text("# Project Context\n")

        result = runner.invoke(app, ["recon", "--path", str(tmp_path)])
        assert "Recon Usage" in result.output
        assert "$0.0200" in result.output
