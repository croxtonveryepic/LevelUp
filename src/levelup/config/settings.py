"""Pydantic Settings models for LevelUp configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator
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


class GUISettings(BaseModel):
    """GUI-related configuration."""

    theme: Literal["light", "dark", "system"] = "system"

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        """Validate theme value."""
        if v not in ("light", "dark", "system"):
            raise ValueError(f"theme must be 'light', 'dark', or 'system', got '{v}'")
        return v


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
