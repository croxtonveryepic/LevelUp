"""Pydantic Settings models for LevelUp configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseModel):
    """LLM-related configuration."""

    api_key: str = ""
    auth_token: str = ""
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 8192
    temperature: float = 0.0
    backend: str = "claude_code"  # "claude_code" or "anthropic_sdk"
    claude_executable: str = "claude"  # path to claude binary


class ProjectSettings(BaseModel):
    """Project-related configuration."""

    path: Path = Field(default_factory=Path.cwd)
    language: str | None = None
    framework: str | None = None
    test_command: str | None = None
    tickets_file: str = "levelup/tickets.md"


class PipelineSettings(BaseModel):
    """Pipeline behavior configuration."""

    max_code_iterations: int = 5
    require_checkpoints: bool = True
    create_git_branch: bool = True
    auto_approve: bool = False


class HotkeySettings(BaseModel):
    """Keyboard hotkey configuration for GUI navigation."""

    next_waiting_ticket: str = "Ctrl+N"
    back_to_runs: str = "Escape"
    toggle_theme: str = "Ctrl+T"
    refresh_dashboard: str = "F5"
    open_documentation: str = "F1"
    focus_terminal: str = "Ctrl+`"

    # Human-readable action descriptions
    ACTION_DESCRIPTIONS: dict[str, str] = {
        "next_waiting_ticket": "Next waiting ticket",
        "back_to_runs": "Back to runs",
        "toggle_theme": "Toggle theme",
        "refresh_dashboard": "Refresh dashboard",
        "open_documentation": "Open documentation",
        "focus_terminal": "Focus terminal",
    }

    @field_validator(
        "next_waiting_ticket",
        "back_to_runs",
        "toggle_theme",
        "refresh_dashboard",
        "open_documentation",
        "focus_terminal",
    )
    @classmethod
    def validate_keybinding(cls, v: str) -> str:
        """Validate keybinding is not empty and has valid format."""
        if not v or not v.strip():
            raise ValueError("Keybinding cannot be empty")

        # Remove extra whitespace
        v = v.strip()

        # Check for invalid patterns
        if "++" in v:
            raise ValueError(f"Invalid keybinding format: {v}")

        # Use Qt's QKeySequence to validate (import only when needed)
        try:
            from PyQt6.QtGui import QKeySequence
            from PyQt6.QtWidgets import QApplication

            # Ensure QApplication exists for QKeySequence to work
            if not QApplication.instance():
                app = QApplication([])

            seq = QKeySequence(v)
            if seq.isEmpty():
                raise ValueError(f"Invalid keybinding: {v}")

            # Check if toString() returns empty (Qt accepted but can't represent it)
            if not seq.toString():
                raise ValueError(f"Invalid keybinding: {v}")

        except ValueError:
            # Re-raise our validation errors
            raise
        except Exception:
            # If we can't import PyQt6, just do basic validation
            # Check for common invalid patterns
            if v.endswith("+") or v.startswith("+"):
                raise ValueError(f"Invalid keybinding format: {v}")

        return v

    @classmethod
    def get_action_description(cls, action: str) -> str:
        """Get human-readable description for an action."""
        return cls.ACTION_DESCRIPTIONS.get(action, action.replace("_", " ").title())


class GUISettings(BaseModel):
    """GUI-related configuration."""

    theme: Literal["light", "dark", "system"] = "system"
    hotkeys: HotkeySettings = Field(default_factory=HotkeySettings)

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        """Validate theme value."""
        if v not in ("light", "dark", "system"):
            raise ValueError(f"theme must be 'light', 'dark', or 'system', got '{v}'")
        return v


MODEL_SHORT_NAMES: dict[str, str] = {
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-6",
}

EFFORT_THINKING_BUDGETS: dict[str, int] = {
    "low": 4096,
    "medium": 16384,
    "high": 32768,
}


class LevelUpSettings(BaseSettings):
    """Root settings with layered config: defaults -> file -> env -> CLI."""

    model_config = SettingsConfigDict(
        env_prefix="LEVELUP_",
        env_nested_delimiter="__",
    )

    llm: LLMSettings = Field(default_factory=LLMSettings)
    project: ProjectSettings = Field(default_factory=ProjectSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
    gui: GUISettings = Field(default_factory=GUISettings)
