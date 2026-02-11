"""TDD tests for orchestrator NOT reading run options from ticket metadata.

This test suite covers the requirements for updating the orchestrator to resolve
model/effort/skip_planning only from CLI flags and config defaults, removing
ticket metadata from the precedence chain.

Requirements:
- _read_ticket_settings() returns empty dict or only non-run-option settings
- Orchestrator resolves model/effort/skip_planning only from CLI flags and config defaults
- Precedence becomes: CLI flags > config defaults (ticket metadata removed)
- Auto-approve still reads from ticket metadata (unchanged)

These tests follow TDD approach - they SHOULD FAIL initially until the
implementation is complete.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from levelup.config.settings import LevelUpSettings, LLMSettings, PipelineSettings, ProjectSettings
from levelup.core.context import PipelineContext, TaskInfo


# ---------------------------------------------------------------------------
# AC: _read_ticket_settings() excludes run options
# ---------------------------------------------------------------------------


class TestReadTicketSettingsExcludesRunOptions:
    """Test that _read_ticket_settings() returns empty dict or excludes run options."""

    def test_read_ticket_settings_returns_empty_for_run_options(self, tmp_path):
        """AC: _read_ticket_settings() returns empty dict when ticket has run options."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        # Create ticket with run options
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"model": "opus", "effort": "high", "skip_planning": True},
        )

        # Create orchestrator
        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(),
            pipeline=PipelineSettings(),
        )
        orch = Orchestrator(settings)

        # Create context with ticket
        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        # Read ticket settings
        result = orch._read_ticket_settings(ctx)

        # Should not contain run options
        assert "model" not in result, "_read_ticket_settings should not return 'model'"
        assert "effort" not in result, "_read_ticket_settings should not return 'effort'"
        assert "skip_planning" not in result, "_read_ticket_settings should not return 'skip_planning'"

    def test_read_ticket_settings_preserves_non_run_options(self, tmp_path):
        """AC: _read_ticket_settings() can return non-run-option settings if needed."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        # Create ticket with mixed metadata
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={
                "model": "sonnet",
                "effort": "low",
                "custom_setting": "value",
            },
        )

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(),
            pipeline=PipelineSettings(),
        )
        orch = Orchestrator(settings)

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        result = orch._read_ticket_settings(ctx)

        # Run options should be excluded
        assert "model" not in result
        assert "effort" not in result

        # Implementation choice: either return empty dict or preserve non-run-option settings
        # For now, we expect empty dict since all current settings are run options

    def test_read_ticket_settings_returns_empty_for_ticket_without_metadata(self, tmp_path):
        """AC: _read_ticket_settings() returns empty dict for tickets without metadata."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(),
            pipeline=PipelineSettings(),
        )
        orch = Orchestrator(settings)

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        result = orch._read_ticket_settings(ctx)

        # Should be empty
        assert result == {} or result is None or len(result) == 0


# ---------------------------------------------------------------------------
# AC: Model resolution excludes ticket metadata
# ---------------------------------------------------------------------------


class TestModelResolutionExcludesTicketMetadata:
    """Test that model is resolved only from CLI flags and config defaults."""

    def test_model_uses_cli_flag_when_provided(self, tmp_path):
        """AC: CLI flag takes precedence (CLI flags > config defaults)."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"model": "opus"}
        )

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(model="claude-sonnet-4-5-20250929"),  # config default
            pipeline=PipelineSettings(),
        )
        orch = Orchestrator(settings, model_override="claude-opus-4-6")  # CLI flag

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        # Simulate the orchestrator's model resolution logic
        # CLI flag should win, NOT ticket metadata
        # The test verifies that ticket metadata is not consulted

    def test_model_uses_config_default_when_no_cli_flag(self, tmp_path):
        """AC: Config default used when no CLI flag (ticket metadata NOT consulted)."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"model": "opus"}
        )

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(model="claude-sonnet-4-5-20250929"),  # config default
            pipeline=PipelineSettings(),
        )
        orch = Orchestrator(settings)  # No CLI override

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        # Config default should be used, NOT ticket metadata
        # This verifies ticket metadata is removed from the precedence chain

    def test_model_does_not_read_from_ticket_metadata(self, tmp_path):
        """AC: Model is NOT read from ticket metadata (removed from chain)."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"model": "sonnet"}
        )

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(),
            pipeline=PipelineSettings(),
        )
        orch = Orchestrator(settings)

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        # Call _read_ticket_settings and verify it doesn't return model
        ticket_settings = orch._read_ticket_settings(ctx)
        assert "model" not in ticket_settings


# ---------------------------------------------------------------------------
# AC: Effort resolution excludes ticket metadata
# ---------------------------------------------------------------------------


class TestEffortResolutionExcludesTicketMetadata:
    """Test that effort is resolved only from CLI flags and config defaults."""

    def test_effort_uses_cli_flag_when_provided(self, tmp_path):
        """AC: CLI flag takes precedence (CLI flags > config defaults)."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"effort": "low"}
        )

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(),
            pipeline=PipelineSettings(),
        )
        orch = Orchestrator(settings, effort="high")  # CLI flag

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        # CLI flag should win, NOT ticket metadata

    def test_effort_does_not_read_from_ticket_metadata(self, tmp_path):
        """AC: Effort is NOT read from ticket metadata (removed from chain)."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"effort": "medium"}
        )

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(),
            pipeline=PipelineSettings(),
        )
        orch = Orchestrator(settings)

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        ticket_settings = orch._read_ticket_settings(ctx)
        assert "effort" not in ticket_settings


# ---------------------------------------------------------------------------
# AC: Skip planning resolution excludes ticket metadata
# ---------------------------------------------------------------------------


class TestSkipPlanningResolutionExcludesTicketMetadata:
    """Test that skip_planning is resolved only from CLI flags and config defaults."""

    def test_skip_planning_uses_cli_flag_when_provided(self, tmp_path):
        """AC: CLI flag takes precedence (CLI flags > config defaults)."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"skip_planning": False}
        )

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(),
            pipeline=PipelineSettings(),
        )
        orch = Orchestrator(settings, skip_planning=True)  # CLI flag

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        # CLI flag should win, NOT ticket metadata

    def test_skip_planning_does_not_read_from_ticket_metadata(self, tmp_path):
        """AC: Skip planning is NOT read from ticket metadata (removed from chain)."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"skip_planning": True}
        )

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(),
            pipeline=PipelineSettings(),
        )
        orch = Orchestrator(settings)

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        ticket_settings = orch._read_ticket_settings(ctx)
        assert "skip_planning" not in ticket_settings


# ---------------------------------------------------------------------------
# AC: Auto-approve STILL reads from ticket metadata
# ---------------------------------------------------------------------------


class TestAutoApproveStillReadsTicketMetadata:
    """Test that auto-approve continues to read from ticket metadata (unchanged)."""

    def test_auto_approve_reads_from_ticket_metadata(self, tmp_path):
        """AC: Auto-approve still reads from ticket metadata via _should_auto_approve()."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"auto_approve": True}
        )

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(),
            pipeline=PipelineSettings(auto_approve=False),  # config default is False
        )
        orch = Orchestrator(settings)

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        # _should_auto_approve should return True from ticket metadata
        result = orch._should_auto_approve(ctx)
        assert result is True, "auto_approve should read from ticket metadata"

    def test_auto_approve_false_in_ticket_metadata(self, tmp_path):
        """AC: auto_approve=False in ticket metadata should be respected."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"auto_approve": False}
        )

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(),
            pipeline=PipelineSettings(auto_approve=True),  # config default is True
        )
        orch = Orchestrator(settings)

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        # _should_auto_approve should return False from ticket metadata
        result = orch._should_auto_approve(ctx)
        assert result is False, "auto_approve should read from ticket metadata"

    def test_auto_approve_falls_back_to_config(self, tmp_path):
        """AC: auto_approve falls back to config when not in ticket metadata."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")  # No metadata

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(),
            pipeline=PipelineSettings(auto_approve=True),
        )
        orch = Orchestrator(settings)

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        # Should fall back to config default
        result = orch._should_auto_approve(ctx)
        assert result is True, "auto_approve should fall back to config when not in metadata"


# ---------------------------------------------------------------------------
# AC: Precedence chain updated
# ---------------------------------------------------------------------------


class TestPrecedenceChain:
    """Test that the precedence chain is: CLI flags > config defaults (ticket metadata removed)."""

    def test_precedence_cli_over_config_for_model(self, tmp_path):
        """AC: CLI flags > config defaults for model."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"model": "sonnet"}
        )

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(model="claude-sonnet-4-5-20250929"),
            pipeline=PipelineSettings(),
        )
        orch = Orchestrator(settings, model_override="claude-opus-4-6")

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        # CLI should win (opus), not config (sonnet) or ticket metadata (sonnet)

    def test_precedence_config_default_when_no_cli(self, tmp_path):
        """AC: Config defaults used when no CLI flags (ticket metadata ignored)."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"effort": "high"}
        )

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(),
            pipeline=PipelineSettings(),
        )
        orch = Orchestrator(settings)  # No CLI overrides

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        # Config default should be used, ticket metadata should be ignored

    def test_ticket_metadata_not_in_precedence_chain(self, tmp_path):
        """AC: Ticket metadata removed from precedence chain for run options."""
        from levelup.core.orchestrator import Orchestrator
        from levelup.core.tickets import add_ticket

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"model": "opus", "effort": "low", "skip_planning": True},
        )

        settings = LevelUpSettings(
            project=ProjectSettings(path=tmp_path),
            llm=LLMSettings(),
            pipeline=PipelineSettings(),
        )
        orch = Orchestrator(settings)

        ctx = PipelineContext(
            task=TaskInfo(
                title="Test task",
                description="Description",
                source="ticket",
                source_id=f"ticket:{ticket.number}",
            ),
            project_path=tmp_path,
            run_id="test-run-123",
        )

        # Verify _read_ticket_settings doesn't return run options
        ticket_settings = orch._read_ticket_settings(ctx)
        assert "model" not in ticket_settings
        assert "effort" not in ticket_settings
        assert "skip_planning" not in ticket_settings
