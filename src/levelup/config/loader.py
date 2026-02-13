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
    GUISettings,
    JiraSettings,
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
    import os

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
    gui_data = file_data.get("gui", {})
    jira_data = file_data.get("jira", {})

    if project_path and "path" not in project_data:
        project_data["path"] = str(project_path)

    # Merge environment variables for each section
    # Pydantic doesn't parse env vars when we pass explicit kwargs,
    # so we need to handle them manually
    _merge_env_vars(llm_data, "LEVELUP_LLM__")
    _merge_env_vars(pipeline_data, "LEVELUP_PIPELINE__")
    _merge_env_vars(project_data, "LEVELUP_PROJECT__")
    _merge_env_vars(gui_data, "LEVELUP_GUI__")
    _merge_env_vars(jira_data, "LEVELUP_JIRA__")

    settings = LevelUpSettings(
        llm=LLMSettings(**llm_data),
        project=ProjectSettings(**project_data),
        pipeline=PipelineSettings(**pipeline_data),
        gui=GUISettings(**gui_data),
        jira=JiraSettings(**jira_data),
    )

    return settings


def _merge_env_vars(data: dict[str, Any], prefix: str) -> None:
    """Merge environment variables with the given prefix into data dict."""
    import os

    for key, value in os.environ.items():
        if key.startswith(prefix):
            field_name = key[len(prefix):].lower()
            # Parse boolean values
            if value.lower() in ("true", "1", "yes", "on"):
                data[field_name] = True
            elif value.lower() in ("false", "0", "no", "off"):
                data[field_name] = False
            elif value.isdigit():
                data[field_name] = int(value)
            else:
                data[field_name] = value


def save_jira_settings(jira: JiraSettings, project_path: Path | None = None) -> None:
    """Save only the Jira section to the config file, preserving other settings."""
    config_file = find_config_file(project_path)
    if config_file is None:
        target_dir = project_path.resolve() if project_path else Path.cwd()
        config_file = target_dir / "levelup.yaml"

    # Load existing data or start fresh
    data: dict[str, Any] = {}
    if config_file.exists():
        data = load_config_file(config_file)

    # Update only the jira section
    data["jira"] = {"url": jira.url, "email": jira.email, "token": jira.token}

    with open(config_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def save_settings(settings: LevelUpSettings, project_path: Path | None = None) -> None:
    """Save settings to a YAML config file."""
    # Determine the config file to write to
    config_file = find_config_file(project_path)

    # If no config file exists, create levelup.yaml in project directory or cwd
    if config_file is None:
        target_dir = project_path.resolve() if project_path else Path.cwd()
        config_file = target_dir / "levelup.yaml"

    # Convert settings to dict
    data = settings.model_dump(exclude_defaults=False)

    # Convert Path objects to strings for YAML serialization
    def convert_paths(obj: Any) -> Any:
        if isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: convert_paths(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_paths(item) for item in obj]
        return obj

    data = convert_paths(data)

    # Write to file
    with open(config_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
