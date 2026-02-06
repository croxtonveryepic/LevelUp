"""Config file discovery and loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from levelup.config.settings import (
    LevelUpSettings,
    LLMSettings,
    PipelineSettings,
    ProjectSettings,
)

CONFIG_FILENAMES = ["levelup.yaml", "levelup.yml", ".levelup.yaml", ".levelup.yml"]


def find_config_file(start_dir: Path | None = None) -> Path | None:
    """Search for a config file starting from start_dir, walking up to root."""
    directory = start_dir or Path.cwd()
    directory = directory.resolve()

    while True:
        for name in CONFIG_FILENAMES:
            candidate = directory / name
            if candidate.is_file():
                return candidate
        parent = directory.parent
        if parent == directory:
            break
        directory = parent

    return None


def load_config_file(path: Path) -> dict[str, Any]:
    """Load and parse a YAML config file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge override into base, returning a new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_settings(
    project_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> LevelUpSettings:
    """Load settings with full layering: defaults -> config file -> env -> overrides."""
    file_data: dict[str, Any] = {}
    config_file = find_config_file(project_path)
    if config_file:
        file_data = load_config_file(config_file)

    if overrides:
        file_data = _deep_merge(file_data, overrides)

    # Build nested settings from merged file data
    llm_data = file_data.get("llm", {})
    project_data = file_data.get("project", {})
    pipeline_data = file_data.get("pipeline", {})

    if project_path and "path" not in project_data:
        project_data["path"] = str(project_path)

    settings = LevelUpSettings(
        llm=LLMSettings(**llm_data),
        project=ProjectSettings(**project_data),
        pipeline=PipelineSettings(**pipeline_data),
        ticket_source=file_data.get("ticket_source", "manual"),
    )

    return settings
