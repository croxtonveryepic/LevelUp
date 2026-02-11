"""Unit tests for auto_approve field in PipelineSettings."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from levelup.config.settings import (
    LevelUpSettings,
    PipelineSettings,
)
from levelup.config.loader import load_settings


# ---------------------------------------------------------------------------
# PipelineSettings auto_approve field
# ---------------------------------------------------------------------------


class TestPipelineSettingsAutoApprove:
    """Test auto_approve field in PipelineSettings."""

    def test_defaults_to_false(self):
        """auto_approve should default to False."""
        s = PipelineSettings()
        assert s.auto_approve is False

    def test_can_be_set_to_true(self):
        """auto_approve can be explicitly set to True."""
        s = PipelineSettings(auto_approve=True)
        assert s.auto_approve is True

    def test_can_be_set_to_false_explicitly(self):
        """auto_approve can be explicitly set to False."""
        s = PipelineSettings(auto_approve=False)
        assert s.auto_approve is False

    def test_nested_in_level_up_settings(self):
        """auto_approve should be accessible via nested settings."""
        s = LevelUpSettings()
        assert hasattr(s.pipeline, "auto_approve")
        assert s.pipeline.auto_approve is False

    def test_set_via_nested_settings(self):
        """auto_approve can be set via LevelUpSettings initialization."""
        s = LevelUpSettings(
            pipeline=PipelineSettings(auto_approve=True)
        )
        assert s.pipeline.auto_approve is True

    def test_works_with_require_checkpoints_true(self):
        """auto_approve should work when require_checkpoints is True."""
        s = PipelineSettings(
            require_checkpoints=True,
            auto_approve=True,
        )
        assert s.require_checkpoints is True
        assert s.auto_approve is True

    def test_with_require_checkpoints_false(self):
        """auto_approve can be set even when require_checkpoints is False."""
        s = PipelineSettings(
            require_checkpoints=False,
            auto_approve=True,
        )
        assert s.require_checkpoints is False
        assert s.auto_approve is True


# ---------------------------------------------------------------------------
# Config file loading with auto_approve
# ---------------------------------------------------------------------------


class TestAutoApproveConfigFile:
    """Test loading auto_approve from levelup.yaml."""

    def test_loads_from_yaml(self, tmp_path: Path):
        """auto_approve should load from levelup.yaml."""
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
        settings = load_settings(project_path=tmp_path)
        assert settings.pipeline.auto_approve is True

    def test_false_in_yaml(self, tmp_path: Path):
        """auto_approve: false should be respected."""
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
        settings = load_settings(project_path=tmp_path)
        assert settings.pipeline.auto_approve is False

    def test_combined_with_other_pipeline_settings(self, tmp_path: Path):
        """auto_approve should work alongside other pipeline settings."""
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "require_checkpoints": True,
                        "auto_approve": True,
                        "max_code_iterations": 3,
                    }
                }
            )
        )
        settings = load_settings(project_path=tmp_path)
        assert settings.pipeline.require_checkpoints is True
        assert settings.pipeline.auto_approve is True
        assert settings.pipeline.max_code_iterations == 3

    def test_defaults_when_not_in_yaml(self, tmp_path: Path):
        """auto_approve should default to False when not in YAML."""
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "max_code_iterations": 10,
                    }
                }
            )
        )
        settings = load_settings(project_path=tmp_path)
        assert settings.pipeline.auto_approve is False
        assert settings.pipeline.max_code_iterations == 10


# ---------------------------------------------------------------------------
# Environment variable configuration
# ---------------------------------------------------------------------------


class TestAutoApproveEnvironmentVariable:
    """Test LEVELUP_PIPELINE__AUTO_APPROVE environment variable."""

    def test_env_var_true(self, tmp_path: Path):
        """LEVELUP_PIPELINE__AUTO_APPROVE=true should work."""
        with patch.dict("os.environ", {"LEVELUP_PIPELINE__AUTO_APPROVE": "true"}):
            settings = load_settings(project_path=tmp_path)
            assert settings.pipeline.auto_approve is True

    def test_env_var_false(self, tmp_path: Path):
        """LEVELUP_PIPELINE__AUTO_APPROVE=false should work."""
        with patch.dict("os.environ", {"LEVELUP_PIPELINE__AUTO_APPROVE": "false"}):
            settings = load_settings(project_path=tmp_path)
            assert settings.pipeline.auto_approve is False

    def test_env_var_1(self, tmp_path: Path):
        """LEVELUP_PIPELINE__AUTO_APPROVE=1 should be treated as True."""
        with patch.dict("os.environ", {"LEVELUP_PIPELINE__AUTO_APPROVE": "1"}):
            settings = load_settings(project_path=tmp_path)
            assert settings.pipeline.auto_approve is True

    def test_env_var_0(self, tmp_path: Path):
        """LEVELUP_PIPELINE__AUTO_APPROVE=0 should be treated as False."""
        with patch.dict("os.environ", {"LEVELUP_PIPELINE__AUTO_APPROVE": "0"}):
            settings = load_settings(project_path=tmp_path)
            assert settings.pipeline.auto_approve is False

    def test_env_var_overrides_config_file(self, tmp_path: Path):
        """Environment variable should override config file."""
        config = tmp_path / "levelup.yaml"
        config.write_text(yaml.dump({"pipeline": {"auto_approve": False}}))

        with patch.dict("os.environ", {"LEVELUP_PIPELINE__AUTO_APPROVE": "true"}):
            settings = load_settings(project_path=tmp_path)
            assert settings.pipeline.auto_approve is True

    def test_config_file_overrides_default(self, tmp_path: Path):
        """Config file should override default when env var not set."""
        config = tmp_path / "levelup.yaml"
        config.write_text(yaml.dump({"pipeline": {"auto_approve": True}}))
        settings = load_settings(project_path=tmp_path)
        assert settings.pipeline.auto_approve is True


# ---------------------------------------------------------------------------
# CLI overrides for auto_approve
# ---------------------------------------------------------------------------


class TestAutoApproveOverrides:
    """Test CLI overrides for auto_approve."""

    def test_override_true(self, tmp_path: Path):
        """Overrides should be able to set auto_approve to True."""
        settings = load_settings(
            project_path=tmp_path,
            overrides={"pipeline": {"auto_approve": True}},
        )
        assert settings.pipeline.auto_approve is True

    def test_override_false(self, tmp_path: Path):
        """Overrides should be able to set auto_approve to False."""
        settings = load_settings(
            project_path=tmp_path,
            overrides={"pipeline": {"auto_approve": False}},
        )
        assert settings.pipeline.auto_approve is False

    def test_override_precedence_over_file(self, tmp_path: Path):
        """Overrides should take precedence over config file."""
        config = tmp_path / "levelup.yaml"
        config.write_text(yaml.dump({"pipeline": {"auto_approve": False}}))

        settings = load_settings(
            project_path=tmp_path,
            overrides={"pipeline": {"auto_approve": True}},
        )
        assert settings.pipeline.auto_approve is True

    def test_override_preserves_other_settings(self, tmp_path: Path):
        """auto_approve override should not affect other settings."""
        config = tmp_path / "levelup.yaml"
        config.write_text(
            yaml.dump(
                {
                    "pipeline": {
                        "require_checkpoints": True,
                        "max_code_iterations": 7,
                    }
                }
            )
        )

        settings = load_settings(
            project_path=tmp_path,
            overrides={"pipeline": {"auto_approve": True}},
        )
        assert settings.pipeline.auto_approve is True
        assert settings.pipeline.require_checkpoints is True
        assert settings.pipeline.max_code_iterations == 7

    def test_combined_overrides(self, tmp_path: Path):
        """Multiple pipeline overrides should work together."""
        settings = load_settings(
            project_path=tmp_path,
            overrides={
                "pipeline": {
                    "auto_approve": True,
                    "require_checkpoints": False,
                    "max_code_iterations": 3,
                }
            },
        )
        assert settings.pipeline.auto_approve is True
        assert settings.pipeline.require_checkpoints is False
        assert settings.pipeline.max_code_iterations == 3
