"""Tests for Orchestrator gui_mode flag behavior."""

from __future__ import annotations

from levelup.config.settings import (
    LevelUpSettings,
    LLMSettings,
    PipelineSettings,
    ProjectSettings,
)
from levelup.core.orchestrator import Orchestrator


def _make_settings() -> LevelUpSettings:
    return LevelUpSettings(
        llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
        project=ProjectSettings(),
        pipeline=PipelineSettings(create_git_branch=False),
    )


class TestGuiModeFlags:
    def test_default_no_headless_no_gui(self):
        orch = Orchestrator(settings=_make_settings())
        assert orch._quiet is False
        assert orch._use_db_checkpoints is False

    def test_headless_sets_quiet_and_db_checkpoints(self):
        orch = Orchestrator(settings=_make_settings(), headless=True)
        assert orch._quiet is True
        assert orch._use_db_checkpoints is True

    def test_gui_mode_sets_db_checkpoints_but_not_quiet(self):
        orch = Orchestrator(settings=_make_settings(), gui_mode=True)
        assert orch._quiet is False
        assert orch._use_db_checkpoints is True

    def test_headless_and_gui_mode(self):
        # headless takes precedence for quiet
        orch = Orchestrator(settings=_make_settings(), headless=True, gui_mode=True)
        # headless=True and gui_mode=True => quiet = True and not True = False
        # Actually: quiet = headless and not gui_mode = True and False = False
        assert orch._quiet is False
        assert orch._use_db_checkpoints is True

    def test_console_quiet_matches_quiet_flag(self):
        orch_gui = Orchestrator(settings=_make_settings(), gui_mode=True)
        assert orch_gui._console.quiet is False

        orch_headless = Orchestrator(settings=_make_settings(), headless=True)
        assert orch_headless._console.quiet is True

        orch_default = Orchestrator(settings=_make_settings())
        assert orch_default._console.quiet is False
