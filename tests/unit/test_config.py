"""Unit tests for src/levelup/config/ (settings and loader)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from levelup.config.settings import (
    LevelUpSettings,
    LLMSettings,
    PipelineSettings,
    ProjectSettings,
)
from levelup.config.loader import (
    CONFIG_FILENAMES,
    _deep_merge,
    find_config_file,
    load_config_file,
    load_settings,
)


# ---------------------------------------------------------------------------
# Settings defaults
# ---------------------------------------------------------------------------


class TestLLMSettings:
    """Test LLMSettings default values."""

    def test_defaults(self):
        s = LLMSettings()
        assert s.api_key == ""
        assert s.model == "claude-sonnet-4-5-20250929"
        assert s.max_tokens == 8192
        assert s.temperature == 0.0

    def test_override(self):
        s = LLMSettings(api_key="sk-test", model="gpt-4", max_tokens=4096, temperature=0.7)
        assert s.api_key == "sk-test"
        assert s.model == "gpt-4"
        assert s.max_tokens == 4096
        assert s.temperature == 0.7


class TestProjectSettings:
    """Test ProjectSettings default values."""

    def test_defaults(self):
        s = ProjectSettings()
        assert isinstance(s.path, Path)
        assert s.language is None
        assert s.framework is None
        assert s.test_command is None

    def test_override(self):
        s = ProjectSettings(
            path=Path("/my/project"), language="python", framework="django", test_command="pytest"
        )
        assert s.path == Path("/my/project")
        assert s.language == "python"
        assert s.framework == "django"
        assert s.test_command == "pytest"


class TestPipelineSettings:
    """Test PipelineSettings default values."""

    def test_defaults(self):
        s = PipelineSettings()
        assert s.max_code_iterations == 5
        assert s.require_checkpoints is True
        assert s.create_git_branch is True
        assert s.auto_commit is False

    def test_override(self):
        s = PipelineSettings(
            max_code_iterations=10,
            require_checkpoints=False,
            create_git_branch=False,
            auto_commit=True,
        )
        assert s.max_code_iterations == 10
        assert s.require_checkpoints is False
        assert s.create_git_branch is False
        assert s.auto_commit is True


class TestLevelUpSettings:
    """Test LevelUpSettings root model defaults."""

    def test_defaults(self):
        s = LevelUpSettings()
        assert isinstance(s.llm, LLMSettings)
        assert isinstance(s.project, ProjectSettings)
        assert isinstance(s.pipeline, PipelineSettings)
        assert s.ticket_source == "manual"

    def test_nested_defaults(self):
        s = LevelUpSettings()
        assert s.llm.api_key == ""
        assert s.pipeline.max_code_iterations == 5

    def test_override_ticket_source(self):
        s = LevelUpSettings(ticket_source="jira")
        assert s.ticket_source == "jira"


# ---------------------------------------------------------------------------
# find_config_file
# ---------------------------------------------------------------------------


class TestFindConfigFile:
    """Test find_config_file() behaviour."""

    def test_no_file_exists(self, tmp_path: Path):
        """When no config file is present in the tree, returns None."""
        result = find_config_file(tmp_path)
        assert result is None

    def test_finds_levelup_yaml(self, tmp_path: Path):
        config = tmp_path / "levelup.yaml"
        config.write_text("llm:\n  model: test\n")
        result = find_config_file(tmp_path)
        assert result is not None
        assert result.name == "levelup.yaml"

    def test_finds_dot_levelup_yml(self, tmp_path: Path):
        config = tmp_path / ".levelup.yml"
        config.write_text("ticket_source: jira\n")
        result = find_config_file(tmp_path)
        assert result is not None
        assert result.name == ".levelup.yml"

    def test_finds_in_parent_directory(self, tmp_path: Path):
        config = tmp_path / "levelup.yaml"
        config.write_text("llm:\n  model: parent\n")
        child = tmp_path / "sub" / "deep"
        child.mkdir(parents=True)
        result = find_config_file(child)
        assert result is not None
        assert result == config.resolve()

    def test_priority_order(self, tmp_path: Path):
        """First matching name from CONFIG_FILENAMES should win."""
        (tmp_path / "levelup.yaml").write_text("first: true\n")
        (tmp_path / "levelup.yml").write_text("second: true\n")
        result = find_config_file(tmp_path)
        assert result is not None
        assert result.name == "levelup.yaml"

    def test_defaults_to_cwd_when_none(self):
        """When start_dir is None, it uses Path.cwd()."""
        with patch("levelup.config.loader.Path.cwd", return_value=Path("/nonexistent/dir")):
            # The function should not raise even if dir is nonexistent (just returns None)
            # because .resolve() and .is_file() won't match.
            # We only care that it doesn't crash and returns None.
            result = find_config_file(None)
            # This will be None because /nonexistent/dir doesn't have config files
            assert result is None


# ---------------------------------------------------------------------------
# load_config_file
# ---------------------------------------------------------------------------


class TestLoadConfigFile:
    """Test load_config_file() YAML parsing."""

    def test_valid_yaml(self, tmp_path: Path):
        f = tmp_path / "levelup.yaml"
        f.write_text(
            yaml.dump(
                {
                    "llm": {"model": "gpt-4", "max_tokens": 2048},
                    "pipeline": {"max_code_iterations": 3},
                }
            )
        )
        data = load_config_file(f)
        assert data["llm"]["model"] == "gpt-4"
        assert data["llm"]["max_tokens"] == 2048
        assert data["pipeline"]["max_code_iterations"] == 3

    def test_empty_file_returns_empty_dict(self, tmp_path: Path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        data = load_config_file(f)
        assert data == {}

    def test_non_dict_yaml_returns_empty_dict(self, tmp_path: Path):
        """If YAML root is a list or scalar, should return {}."""
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2\n")
        data = load_config_file(f)
        assert data == {}

    def test_scalar_yaml_returns_empty_dict(self, tmp_path: Path):
        f = tmp_path / "scalar.yaml"
        f.write_text("just a string\n")
        data = load_config_file(f)
        assert data == {}


# ---------------------------------------------------------------------------
# _deep_merge
# ---------------------------------------------------------------------------


class TestDeepMerge:
    """Test _deep_merge() helper."""

    def test_simple_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 99}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 99}

    def test_adds_new_keys(self):
        base = {"a": 1}
        override = {"b": 2}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 2}

    def test_nested_merge(self):
        base: dict[str, Any] = {"llm": {"model": "default", "max_tokens": 8192}}
        override: dict[str, Any] = {"llm": {"model": "custom"}}
        result = _deep_merge(base, override)
        assert result == {"llm": {"model": "custom", "max_tokens": 8192}}

    def test_override_replaces_non_dict_with_dict(self):
        base: dict[str, Any] = {"a": "string"}
        override: dict[str, Any] = {"a": {"nested": True}}
        result = _deep_merge(base, override)
        assert result == {"a": {"nested": True}}

    def test_override_replaces_dict_with_scalar(self):
        base: dict[str, Any] = {"a": {"nested": True}}
        override: dict[str, Any] = {"a": "flat"}
        result = _deep_merge(base, override)
        assert result == {"a": "flat"}

    def test_does_not_mutate_base(self):
        base: dict[str, Any] = {"a": 1, "nested": {"x": 10}}
        override: dict[str, Any] = {"a": 2}
        _deep_merge(base, override)
        assert base["a"] == 1  # base should be unchanged

    def test_empty_override(self):
        base = {"a": 1}
        result = _deep_merge(base, {})
        assert result == {"a": 1}

    def test_empty_base(self):
        result = _deep_merge({}, {"a": 1})
        assert result == {"a": 1}

    def test_deeply_nested(self):
        base: dict[str, Any] = {"l1": {"l2": {"l3": {"val": "old"}}}}
        override: dict[str, Any] = {"l1": {"l2": {"l3": {"val": "new"}}}}
        result = _deep_merge(base, override)
        assert result["l1"]["l2"]["l3"]["val"] == "new"


# ---------------------------------------------------------------------------
# load_settings
# ---------------------------------------------------------------------------


class TestLoadSettings:
    """Test load_settings() integration of defaults, file, and overrides."""

    def test_defaults_when_no_config(self, tmp_path: Path):
        """When no config file exists, should return default settings."""
        settings = load_settings(project_path=tmp_path)
        assert isinstance(settings, LevelUpSettings)
        assert settings.llm.model == "claude-sonnet-4-5-20250929"
        assert settings.pipeline.max_code_iterations == 5
        assert settings.ticket_source == "manual"

    def test_project_path_set_when_provided(self, tmp_path: Path):
        settings = load_settings(project_path=tmp_path)
        assert settings.project.path == tmp_path

    def test_config_file_values_loaded(self, tmp_path: Path):
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "llm": {"model": "custom-model", "max_tokens": 1024},
                    "ticket_source": "linear",
                }
            )
        )
        settings = load_settings(project_path=tmp_path)
        assert settings.llm.model == "custom-model"
        assert settings.llm.max_tokens == 1024
        assert settings.ticket_source == "linear"

    def test_overrides_take_precedence_over_file(self, tmp_path: Path):
        config = tmp_path / "levelup.yaml"
        config.write_text(yaml.dump({"llm": {"model": "file-model"}}))
        settings = load_settings(
            project_path=tmp_path,
            overrides={"llm": {"model": "override-model"}},
        )
        assert settings.llm.model == "override-model"

    def test_overrides_without_config_file(self, tmp_path: Path):
        settings = load_settings(
            project_path=tmp_path,
            overrides={"pipeline": {"max_code_iterations": 99}},
        )
        assert settings.pipeline.max_code_iterations == 99

    def test_partial_overrides_preserve_defaults(self, tmp_path: Path):
        settings = load_settings(
            project_path=tmp_path,
            overrides={"llm": {"api_key": "sk-test"}},
        )
        # api_key overridden
        assert settings.llm.api_key == "sk-test"
        # other defaults preserved
        assert settings.llm.model == "claude-sonnet-4-5-20250929"
        assert settings.llm.max_tokens == 8192

    def test_project_path_not_overwritten_if_in_file(self, tmp_path: Path):
        config = tmp_path / "levelup.yaml"
        config.write_text(yaml.dump({"project": {"path": "/explicit/path"}}))
        settings = load_settings(project_path=tmp_path)
        # The file explicitly sets path, so it should use the file value
        # Normalize separators for cross-platform compatibility
        normalized = str(settings.project.path).replace("\\", "/")
        assert normalized == "/explicit/path"
