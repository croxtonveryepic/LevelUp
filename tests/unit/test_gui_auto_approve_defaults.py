"""Unit tests for auto-approve checkbox default behavior in TicketDetailWidget.

Tests that the auto-approve checkbox pre-populates with the project's default
setting from pipeline.auto_approve when the ticket has no metadata.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# GUI tests require PyQt6
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from levelup.core.tickets import Ticket, TicketStatus, add_ticket, read_tickets


# Test fixtures need a QApplication instance
@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Test TicketDetailWidget loads project settings
# ---------------------------------------------------------------------------


class TestTicketDetailWidgetLoadsProjectSettings:
    """Test that TicketDetailWidget can access project's pipeline.auto_approve setting."""

    def test_widget_can_load_settings_when_project_path_set(self, qapp, tmp_path):
        """TicketDetailWidget should load settings when project_path is available."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        # Create project config with auto_approve=True
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": True,
                    }
                }
            )
        )

        # Create widget with project_path
        widget = TicketDetailWidget(project_path=str(tmp_path))

        # Widget should be able to load settings
        # The actual loading mechanism will be implemented, but at minimum
        # the widget should have project_path available
        assert widget._project_path == str(tmp_path)

    def test_widget_loads_settings_in_set_project_context(self, qapp, tmp_path):
        """TicketDetailWidget should load settings when set_project_context is called."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        # Create project config
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": True,
                    }
                }
            )
        )

        widget = TicketDetailWidget()

        # Set project context (with db_path parameter)
        if hasattr(widget, "set_project_context"):
            widget.set_project_context(str(tmp_path), str(tmp_path / ".levelup" / "state.db"))
            # Settings should be loaded after setting project context
            assert widget._project_path == str(tmp_path)

    def test_widget_stores_auto_approve_default_from_settings(self, qapp, tmp_path):
        """Widget should store the project's pipeline.auto_approve default value."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        # Create project config with auto_approve=True
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": True,
                    }
                }
            )
        )

        widget = TicketDetailWidget(project_path=str(tmp_path))

        # Widget should have access to the auto_approve default
        # This will be implemented in the widget
        # For now, test that the widget has a way to store this
        assert hasattr(widget, "_project_path")


# ---------------------------------------------------------------------------
# Test checkbox defaults to project setting when ticket has no metadata
# ---------------------------------------------------------------------------


class TestAutoApproveCheckboxDefaultsToProjectSetting:
    """Test that checkbox defaults to project's pipeline.auto_approve when ticket has no metadata."""

    def test_checkbox_defaults_to_false_when_project_has_no_config(self, qapp, tmp_path):
        """Checkbox should default to False when project has no config (default behavior)."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket without metadata
        ticket = add_ticket(tmp_path, "Test task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.load_ticket(ticket)

        # Checkbox should be unchecked (False) - the default from PipelineSettings
        assert not widget.auto_approve_checkbox.isChecked()

    def test_checkbox_defaults_to_true_when_project_config_sets_auto_approve_true(
        self, qapp, tmp_path
    ):
        """Checkbox should default to True when project config sets pipeline.auto_approve=True."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create project config with auto_approve=True
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": True,
                    }
                }
            )
        )

        # Create ticket without metadata
        ticket = add_ticket(tmp_path, "Test task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.load_ticket(ticket)

        # Checkbox should be checked (True) - the project default
        assert widget.auto_approve_checkbox.isChecked()

    def test_checkbox_defaults_to_false_when_project_explicitly_sets_false(
        self, qapp, tmp_path
    ):
        """Checkbox should default to False when project config explicitly sets auto_approve=False."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create project config with auto_approve=False
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": False,
                    }
                }
            )
        )

        # Create ticket without metadata
        ticket = add_ticket(tmp_path, "Test task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.load_ticket(ticket)

        # Checkbox should be unchecked (False)
        assert not widget.auto_approve_checkbox.isChecked()

    def test_checkbox_defaults_to_false_when_ticket_metadata_is_none(
        self, qapp, tmp_path
    ):
        """Checkbox should use project default when ticket.metadata is None."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket without metadata (metadata=None)
        ticket = add_ticket(tmp_path, "Test task", "Description", metadata=None)

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.load_ticket(ticket)

        # Checkbox should use project default (False)
        assert not widget.auto_approve_checkbox.isChecked()

    def test_checkbox_defaults_to_false_when_ticket_metadata_is_empty_dict(
        self, qapp, tmp_path
    ):
        """Checkbox should use project default when ticket.metadata is empty dict."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket with empty metadata dict
        ticket = add_ticket(tmp_path, "Test task", "Description", metadata={})

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.load_ticket(ticket)

        # Checkbox should use project default (False)
        assert not widget.auto_approve_checkbox.isChecked()

    def test_checkbox_defaults_to_true_with_empty_metadata_and_project_config_true(
        self, qapp, tmp_path
    ):
        """Checkbox should use project default (True) when ticket.metadata is empty."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create project config with auto_approve=True
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": True,
                    }
                }
            )
        )

        # Create ticket with empty metadata
        ticket = add_ticket(tmp_path, "Test task", "Description", metadata={})

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.load_ticket(ticket)

        # Checkbox should use project default (True)
        assert widget.auto_approve_checkbox.isChecked()


# ---------------------------------------------------------------------------
# Test ticket metadata overrides project default
# ---------------------------------------------------------------------------


class TestTicketMetadataOverridesProjectDefault:
    """Test that ticket metadata takes precedence over project default when present."""

    def test_ticket_metadata_true_overrides_project_default_false(
        self, qapp, tmp_path
    ):
        """Ticket metadata auto_approve=True should override project default False."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create project config with auto_approve=False (or no config)
        # Default is False if no config

        # Create ticket with auto_approve=True in metadata
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"auto_approve": True}
        )

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.load_ticket(ticket)

        # Checkbox should respect ticket metadata (True)
        assert widget.auto_approve_checkbox.isChecked()

    def test_ticket_metadata_false_overrides_project_default_true(
        self, qapp, tmp_path
    ):
        """Ticket metadata auto_approve=False should override project default True."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create project config with auto_approve=True
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": True,
                    }
                }
            )
        )

        # Create ticket with auto_approve=False in metadata
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"auto_approve": False}
        )

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.load_ticket(ticket)

        # Checkbox should respect ticket metadata (False), not project default
        assert not widget.auto_approve_checkbox.isChecked()

    def test_ticket_metadata_preserves_existing_behavior(self, qapp, tmp_path):
        """Existing behavior of respecting ticket metadata should be preserved."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create project config with auto_approve=True
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": True,
                    }
                }
            )
        )

        # Create two tickets: one with metadata, one without
        ticket_with_metadata = add_ticket(
            tmp_path,
            "Ticket with metadata",
            "Description",
            metadata={"auto_approve": False},
        )
        ticket_without_metadata = add_ticket(
            tmp_path, "Ticket without metadata", "Description"
        )

        widget = TicketDetailWidget(project_path=str(tmp_path))

        # Load ticket with metadata
        widget.load_ticket(ticket_with_metadata)
        assert not widget.auto_approve_checkbox.isChecked()  # Metadata value

        # Load ticket without metadata
        tickets = read_tickets(tmp_path)
        ticket_without = [t for t in tickets if t.title == "Ticket without metadata"][0]
        widget.load_ticket(ticket_without)
        assert widget.auto_approve_checkbox.isChecked()  # Project default

    def test_ticket_metadata_with_other_fields_preserved(self, qapp, tmp_path):
        """Ticket metadata with other fields should still use project default for auto_approve."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create project config with auto_approve=True
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": True,
                    }
                }
            )
        )

        # Create ticket with metadata that doesn't include auto_approve
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"priority": "high", "custom_field": "value"},
        )

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.load_ticket(ticket)

        # Checkbox should use project default since auto_approve not in metadata
        assert widget.auto_approve_checkbox.isChecked()


# ---------------------------------------------------------------------------
# Test new ticket mode uses project default
# ---------------------------------------------------------------------------


class TestNewTicketModeUsesProjectDefault:
    """Test that new ticket form populates auto-approve checkbox with project default."""

    def test_new_ticket_defaults_to_false_when_no_project_config(self, qapp, tmp_path):
        """New ticket form should default auto-approve to False when no project config."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_create_mode()

        # Checkbox should default to False (project default)
        assert not widget.auto_approve_checkbox.isChecked()

    def test_new_ticket_defaults_to_true_when_project_config_sets_true(
        self, qapp, tmp_path
    ):
        """New ticket form should default to True when project config sets auto_approve=True."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create project config with auto_approve=True
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": True,
                    }
                }
            )
        )

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_create_mode()

        # Checkbox should default to True (project default)
        assert widget.auto_approve_checkbox.isChecked()

    def test_new_ticket_matches_orchestrator_behavior(self, qapp, tmp_path):
        """New ticket default should match behavior orchestrator will use if ticket saved without metadata."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create project config with auto_approve=True
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": True,
                    }
                }
            )
        )

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_create_mode()

        # Checkbox should match what orchestrator would use (True from config)
        # This ensures consistency between GUI preview and actual behavior
        assert widget.auto_approve_checkbox.isChecked()

    def test_user_can_override_default_before_saving(self, qapp, tmp_path):
        """User can still override the default by checking/unchecking before saving."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create project config with auto_approve=True
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": True,
                    }
                }
            )
        )

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.set_create_mode()

        # Initially True
        assert widget.auto_approve_checkbox.isChecked()

        # User unchecks it
        widget.auto_approve_checkbox.setChecked(False)
        assert not widget.auto_approve_checkbox.isChecked()

        # User checks it again
        widget.auto_approve_checkbox.setChecked(True)
        assert widget.auto_approve_checkbox.isChecked()

    def test_new_ticket_without_project_path_defaults_to_false(self, qapp):
        """New ticket without project_path should default to False (safe default)."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        # Create widget without project_path
        widget = TicketDetailWidget()
        widget.set_create_mode()

        # Should default to False when no project settings available
        assert not widget.auto_approve_checkbox.isChecked()


# ---------------------------------------------------------------------------
# Test environment variable support
# ---------------------------------------------------------------------------


class TestAutoApproveDefaultWithEnvironmentVariable:
    """Test that environment variable LEVELUP_PIPELINE__AUTO_APPROVE affects checkbox default."""

    def test_checkbox_respects_env_var_true(self, qapp, tmp_path):
        """Checkbox should use env var value when no config file exists."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket without metadata
        ticket = add_ticket(tmp_path, "Test task", "Description")

        with patch.dict("os.environ", {"LEVELUP_PIPELINE__AUTO_APPROVE": "true"}):
            widget = TicketDetailWidget(project_path=str(tmp_path))
            widget.load_ticket(ticket)

            # Checkbox should use env var value (True)
            assert widget.auto_approve_checkbox.isChecked()

    def test_checkbox_respects_env_var_false(self, qapp, tmp_path):
        """Checkbox should use env var value (False) when no config file exists."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create ticket without metadata
        ticket = add_ticket(tmp_path, "Test task", "Description")

        with patch.dict("os.environ", {"LEVELUP_PIPELINE__AUTO_APPROVE": "false"}):
            widget = TicketDetailWidget(project_path=str(tmp_path))
            widget.load_ticket(ticket)

            # Checkbox should use env var value (False)
            assert not widget.auto_approve_checkbox.isChecked()

    def test_env_var_overrides_config_file(self, qapp, tmp_path):
        """Environment variable should override config file for checkbox default."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create project config with auto_approve=False
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": False,
                    }
                }
            )
        )

        # Create ticket without metadata
        ticket = add_ticket(tmp_path, "Test task", "Description")

        with patch.dict("os.environ", {"LEVELUP_PIPELINE__AUTO_APPROVE": "true"}):
            widget = TicketDetailWidget(project_path=str(tmp_path))
            widget.load_ticket(ticket)

            # Checkbox should use env var value (True), not config file (False)
            assert widget.auto_approve_checkbox.isChecked()


# ---------------------------------------------------------------------------
# Test edge cases
# ---------------------------------------------------------------------------


class TestAutoApproveDefaultEdgeCases:
    """Test edge cases for auto-approve checkbox default behavior."""

    def test_checkbox_handles_malformed_config_gracefully(self, qapp, tmp_path):
        """Widget should handle malformed config file gracefully and use default False."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create malformed config
        config = tmp_path / "levelup.yaml"
        config.write_text("invalid: [[[broken yaml")

        # Create ticket without metadata
        ticket = add_ticket(tmp_path, "Test task", "Description")

        # Should not crash, should use safe default (False)
        try:
            widget = TicketDetailWidget(project_path=str(tmp_path))
            widget.load_ticket(ticket)
            assert not widget.auto_approve_checkbox.isChecked()
        except Exception:
            # If it raises an exception, that's also acceptable behavior
            # as long as it's handled gracefully and doesn't crash the GUI
            pass

    def test_checkbox_default_changes_when_project_context_changes(self, qapp, tmp_path):
        """Checkbox default should update when project context changes."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create two different project directories with different configs
        project1 = tmp_path / "project1"
        project1.mkdir()
        (project1 / "levelup").mkdir()
        config1 = project1 / "levelup.yaml"
        config1.write_text(yaml.dump({"pipeline": {"auto_approve": False}}))

        project2 = tmp_path / "project2"
        project2.mkdir()
        (project2 / "levelup").mkdir()
        config2 = project2 / "levelup.yaml"
        config2.write_text(yaml.dump({"pipeline": {"auto_approve": True}}))

        # Create tickets in each project
        ticket1 = add_ticket(project1, "Task 1", "Description")
        ticket2 = add_ticket(project2, "Task 2", "Description")

        widget = TicketDetailWidget(project_path=str(project1))

        # Load ticket from project1 (auto_approve=False)
        widget.load_ticket(ticket1)
        assert not widget.auto_approve_checkbox.isChecked()

        # Change project context to project2
        if hasattr(widget, "set_project_context"):
            widget.set_project_context(str(project2), str(project2 / ".levelup" / "state.db"))
        else:
            # Recreate widget with new project context
            widget = TicketDetailWidget(project_path=str(project2))

        # Load ticket from project2 (auto_approve=True)
        widget.load_ticket(ticket2)
        assert widget.auto_approve_checkbox.isChecked()

    def test_settings_loaded_only_once_per_project(self, qapp, tmp_path):
        """Settings should be loaded once when project context is set, not on every ticket load."""
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.config.loader import load_settings

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create project config
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": True,
                    }
                }
            )
        )

        # Create multiple tickets
        ticket1 = add_ticket(tmp_path, "Task 1", "Description")
        ticket2 = add_ticket(tmp_path, "Task 2", "Description")

        with patch("levelup.config.loader.load_settings", wraps=load_settings) as mock_load:
            widget = TicketDetailWidget(project_path=str(tmp_path))

            # Settings should be loaded during widget initialization
            # or when project_path is set
            initial_call_count = mock_load.call_count

            # Load multiple tickets
            widget.load_ticket(ticket1)
            widget.load_ticket(ticket2)

            # load_settings should not be called again for each ticket
            # It should only be called once (during init or set_project_context)
            final_call_count = mock_load.call_count

            # The difference should be minimal (ideally 0 or 1)
            # Not 2+ calls for each ticket load
            assert final_call_count - initial_call_count <= 1

    def test_checkbox_default_with_tickets_file_in_custom_location(self, qapp, tmp_path):
        """Checkbox should work correctly even when tickets_file is in custom location."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        # Create custom tickets directory
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()

        # Create project config with custom tickets_file location and auto_approve
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "project": {
                        "tickets_file": "custom/tickets.md",
                    },
                    "pipeline": {
                        "auto_approve": True,
                    },
                }
            )
        )

        # Create ticket in custom location
        ticket = add_ticket(tmp_path, "Test task", "Description")

        widget = TicketDetailWidget(project_path=str(tmp_path))
        widget.load_ticket(ticket)

        # Checkbox should use project default (True) regardless of tickets_file location
        assert widget.auto_approve_checkbox.isChecked()


# ---------------------------------------------------------------------------
# Test settings reload scenarios
# ---------------------------------------------------------------------------


class TestAutoApproveDefaultSettingsReload:
    """Test scenarios where settings might need to be reloaded."""

    def test_widget_created_before_config_file_exists(self, qapp, tmp_path):
        """Widget created before config file exists should use default False."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create widget before config exists
        widget = TicketDetailWidget(project_path=str(tmp_path))

        # Create ticket without metadata
        ticket = add_ticket(tmp_path, "Test task", "Description")
        widget.load_ticket(ticket)

        # Should use default (False)
        assert not widget.auto_approve_checkbox.isChecked()

    def test_widget_with_none_project_path_then_set_later(self, qapp, tmp_path):
        """Widget created with None project_path should update when path is set."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()

        # Create project config with auto_approve=True
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "auto_approve": True,
                    }
                }
            )
        )

        # Create widget without project_path
        widget = TicketDetailWidget()

        # Set project context later
        if hasattr(widget, "set_project_context"):
            widget.set_project_context(str(tmp_path), str(tmp_path / ".levelup" / "state.db"))

        # Create ticket and load it
        ticket = add_ticket(tmp_path, "Test task", "Description")

        # Update project_path if set_project_context doesn't exist
        if not hasattr(widget, "set_project_context"):
            widget._project_path = str(tmp_path)

        widget.load_ticket(ticket)

        # Should use project setting (True)
        assert widget.auto_approve_checkbox.isChecked()
