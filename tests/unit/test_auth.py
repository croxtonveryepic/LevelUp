"""Tests for Claude Code OAuth credential reading."""

from __future__ import annotations

import json
import time
from pathlib import Path

from levelup.config.auth import get_claude_code_api_key


def _write_credentials(tmp_path: Path, data: dict) -> None:
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / ".credentials.json").write_text(
        json.dumps(data), encoding="utf-8"
    )


class TestGetClaudeCodeApiKey:
    def test_reads_valid_credentials(self, tmp_path, monkeypatch):
        _write_credentials(tmp_path, {
            "claudeAiOauth": {
                "accessToken": "sk-ant-oat01-test-token",
                "expiresAt": int((time.time() + 3600) * 1000),
            }
        })
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert get_claude_code_api_key() == "sk-ant-oat01-test-token"

    def test_returns_empty_when_expired(self, tmp_path, monkeypatch):
        _write_credentials(tmp_path, {
            "claudeAiOauth": {
                "accessToken": "sk-ant-oat01-expired",
                "expiresAt": int((time.time() - 3600) * 1000),
            }
        })
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert get_claude_code_api_key() == ""

    def test_returns_empty_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert get_claude_code_api_key() == ""

    def test_returns_empty_when_malformed_json(self, tmp_path, monkeypatch):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / ".credentials.json").write_text(
            "not valid json{{{", encoding="utf-8"
        )
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert get_claude_code_api_key() == ""

    def test_returns_empty_when_no_oauth_section(self, tmp_path, monkeypatch):
        _write_credentials(tmp_path, {"someOtherKey": {}})
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert get_claude_code_api_key() == ""

    def test_ignores_empty_access_token(self, tmp_path, monkeypatch):
        _write_credentials(tmp_path, {
            "claudeAiOauth": {
                "accessToken": "",
                "expiresAt": int((time.time() + 3600) * 1000),
            }
        })
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert get_claude_code_api_key() == ""
