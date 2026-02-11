"""Unit tests for auto-approve CLI flag."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import app


runner = CliRunner()


class TestAutoApproveCLIFlag:
    """Test --auto-approve flag on 'levelup run' command."""

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_auto_approve_flag_exists(self, mock_sm_cls, mock_orch_cls, tmp_path):
        """--auto-approve flag should be recognized by CLI."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_orch_cls.return_value.run.return_value = mock_ctx

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(app, [
            "run",
            "test task",
            "--path", str(tmp_path),
            "--auto-approve",
            "--no-checkpoints",
        ])

        # Should not fail due to unrecognized flag
        assert "no such option" not in result.output.lower()

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    @patch("levelup.config.loader.load_settings")
    def test_auto_approve_flag_sets_override(
        self, mock_load_settings, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """--auto-approve should set pipeline.auto_approve override."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_orch_cls.return_value.run.return_value = mock_ctx

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        from levelup.config.settings import (
            LevelUpSettings,
            LLMSettings,
            PipelineSettings,
            ProjectSettings,
        )

        mock_settings = LevelUpSettings(
            llm=LLMSettings(),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(auto_approve=True),
        )
        mock_load_settings.return_value = mock_settings

        result = runner.invoke(app, [
            "run",
            "test task",
            "--path", str(tmp_path),
            "--auto-approve",
            "--no-checkpoints",
        ])

        # Check that load_settings was called with auto_approve override
        call_args = mock_load_settings.call_args
        overrides = call_args[1].get("overrides", {})
        assert "pipeline" in overrides
        assert overrides["pipeline"].get("auto_approve") is True

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    @patch("levelup.config.loader.load_settings")
    def test_auto_approve_flag_overrides_config_file(
        self, mock_load_settings, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """--auto-approve should override config file setting."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Config file says auto_approve=False
        config = tmp_path / "levelup.yaml"
        config.write_text("pipeline:\n  auto_approve: false\n")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_orch_cls.return_value.run.return_value = mock_ctx

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        from levelup.config.settings import (
            LevelUpSettings,
            LLMSettings,
            PipelineSettings,
            ProjectSettings,
        )

        # Mock settings after override applied
        mock_settings = LevelUpSettings(
            llm=LLMSettings(),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(auto_approve=True),
        )
        mock_load_settings.return_value = mock_settings

        result = runner.invoke(app, [
            "run",
            "test task",
            "--path", str(tmp_path),
            "--auto-approve",
            "--no-checkpoints",
        ])

        # Verify override was passed
        call_args = mock_load_settings.call_args
        overrides = call_args[1].get("overrides", {})
        assert overrides["pipeline"]["auto_approve"] is True

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_without_auto_approve_flag_uses_default(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """Without --auto-approve, should use config/default value."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_orch_cls.return_value.run.return_value = mock_ctx

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        with patch("levelup.config.loader.load_settings") as mock_load:
            from levelup.config.settings import (
                LevelUpSettings,
                LLMSettings,
                PipelineSettings,
                ProjectSettings,
            )

            mock_settings = LevelUpSettings(
                llm=LLMSettings(),
                project=ProjectSettings(path=tmp_path),
                pipeline=PipelineSettings(auto_approve=False),
            )
            mock_load.return_value = mock_settings

            result = runner.invoke(app, [
                "run",
                "test task",
                "--path", str(tmp_path),
                "--no-checkpoints",
            ])

            # Check that auto_approve override was NOT set
            call_args = mock_load.call_args
            overrides = call_args[1].get("overrides", {})
            # auto_approve should not be in overrides
            assert "auto_approve" not in overrides.get("pipeline", {})

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_auto_approve_with_ticket_flag(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """--auto-approve should work with --ticket flag."""
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "test task")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_orch_cls.return_value.run.return_value = mock_ctx

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        with patch("levelup.config.loader.load_settings") as mock_load:
            from levelup.config.settings import (
                LevelUpSettings,
                LLMSettings,
                PipelineSettings,
                ProjectSettings,
            )

            mock_settings = LevelUpSettings(
                llm=LLMSettings(),
                project=ProjectSettings(path=tmp_path),
                pipeline=PipelineSettings(auto_approve=True),
            )
            mock_load.return_value = mock_settings

            result = runner.invoke(app, [
                "run",
                "--path", str(tmp_path),
                "--ticket", "1",
                "--auto-approve",
                "--no-checkpoints",
            ])

            assert result.exit_code == 0
            call_args = mock_load.call_args
            overrides = call_args[1].get("overrides", {})
            assert overrides["pipeline"]["auto_approve"] is True

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_auto_approve_with_ticket_next_flag(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """--auto-approve should work with --ticket-next flag."""
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        add_ticket(tmp_path, "pending task")

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_orch_cls.return_value.run.return_value = mock_ctx

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        with patch("levelup.config.loader.load_settings") as mock_load:
            from levelup.config.settings import (
                LevelUpSettings,
                LLMSettings,
                PipelineSettings,
                ProjectSettings,
            )

            mock_settings = LevelUpSettings(
                llm=LLMSettings(),
                project=ProjectSettings(path=tmp_path),
                pipeline=PipelineSettings(auto_approve=True),
            )
            mock_load.return_value = mock_settings

            result = runner.invoke(app, [
                "run",
                "--path", str(tmp_path),
                "--ticket-next",
                "--auto-approve",
                "--no-checkpoints",
            ])

            assert result.exit_code == 0
            call_args = mock_load.call_args
            overrides = call_args[1].get("overrides", {})
            assert overrides["pipeline"]["auto_approve"] is True

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_auto_approve_with_headless_mode(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """--auto-approve should work with --headless."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_orch_cls.return_value.run.return_value = mock_ctx

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        with patch("levelup.config.loader.load_settings") as mock_load:
            from levelup.config.settings import (
                LevelUpSettings,
                LLMSettings,
                PipelineSettings,
                ProjectSettings,
            )

            mock_settings = LevelUpSettings(
                llm=LLMSettings(),
                project=ProjectSettings(path=tmp_path),
                pipeline=PipelineSettings(auto_approve=True),
            )
            mock_load.return_value = mock_settings

            result = runner.invoke(app, [
                "run",
                "test task",
                "--path", str(tmp_path),
                "--headless",
                "--auto-approve",
                "--no-checkpoints",
            ])

            assert result.exit_code == 0

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_auto_approve_with_other_flags(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """--auto-approve should work alongside other flags."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_orch_cls.return_value.run.return_value = mock_ctx

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        with patch("levelup.config.loader.load_settings") as mock_load:
            from levelup.config.settings import (
                LevelUpSettings,
                LLMSettings,
                PipelineSettings,
                ProjectSettings,
            )

            mock_settings = LevelUpSettings(
                llm=LLMSettings(model="custom-model"),
                project=ProjectSettings(path=tmp_path),
                pipeline=PipelineSettings(
                    auto_approve=True,
                    max_code_iterations=10,
                ),
            )
            mock_load.return_value = mock_settings

            result = runner.invoke(app, [
                "run",
                "test task",
                "--path", str(tmp_path),
                "--auto-approve",
                "--model", "custom-model",
                "--max-iterations", "10",
                "--no-checkpoints",
            ])

            assert result.exit_code == 0
            call_args = mock_load.call_args
            overrides = call_args[1].get("overrides", {})
            assert overrides["pipeline"]["auto_approve"] is True
            assert overrides["llm"]["model"] == "custom-model"
            assert overrides["pipeline"]["max_code_iterations"] == 10


class TestAutoApproveInteractionWithNoCheckpoints:
    """Test interaction between --auto-approve and --no-checkpoints."""

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_both_flags_together(self, mock_sm_cls, mock_orch_cls, tmp_path):
        """Using both --auto-approve and --no-checkpoints should work."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_orch_cls.return_value.run.return_value = mock_ctx

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        result = runner.invoke(app, [
            "run",
            "test task",
            "--path", str(tmp_path),
            "--auto-approve",
            "--no-checkpoints",
        ])

        # Should not error
        assert result.exit_code == 0

    @patch("levelup.core.orchestrator.Orchestrator")
    @patch("levelup.state.manager.StateManager")
    def test_no_checkpoints_takes_precedence(
        self, mock_sm_cls, mock_orch_cls, tmp_path
    ):
        """When both flags present, --no-checkpoints disables all checkpoints."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        mock_ctx = MagicMock()
        mock_ctx.status.value = "completed"
        mock_ctx.task.source = "ticket"
        mock_ctx.task.source_id = "ticket:1"
        mock_orch_cls.return_value.run.return_value = mock_ctx

        mock_sm = MagicMock()
        mock_sm.has_active_run_for_ticket.return_value = None
        mock_sm_cls.return_value = mock_sm

        with patch("levelup.config.loader.load_settings") as mock_load:
            from levelup.config.settings import (
                LevelUpSettings,
                LLMSettings,
                PipelineSettings,
                ProjectSettings,
            )

            mock_settings = LevelUpSettings(
                llm=LLMSettings(),
                project=ProjectSettings(path=tmp_path),
                pipeline=PipelineSettings(
                    require_checkpoints=False,
                    auto_approve=True,
                ),
            )
            mock_load.return_value = mock_settings

            result = runner.invoke(app, [
                "run",
                "test task",
                "--path", str(tmp_path),
                "--auto-approve",
                "--no-checkpoints",
            ])

            assert result.exit_code == 0
            # Both overrides should be set
            call_args = mock_load.call_args
            overrides = call_args[1].get("overrides", {})
            assert overrides["pipeline"]["require_checkpoints"] is False
            assert overrides["pipeline"]["auto_approve"] is True
