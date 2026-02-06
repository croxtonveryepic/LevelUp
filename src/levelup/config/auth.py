"""Read API key from Claude Code's OAuth credentials."""

from __future__ import annotations

import json
import time
from pathlib import Path


def get_claude_code_api_key() -> str:
    """Read API key from Claude Code's OAuth credentials.

    Returns the access token if found and not expired, else empty string.
    """
    creds_path = Path.home() / ".claude" / ".credentials.json"
    try:
        data = json.loads(creds_path.read_text(encoding="utf-8"))
        oauth = data.get("claudeAiOauth", {})
        token = oauth.get("accessToken", "")
        expires_at = oauth.get("expiresAt", 0)

        # expiresAt is milliseconds since epoch
        if expires_at and time.time() * 1000 > expires_at:
            return ""

        if not token:
            return ""

        return token
    except (OSError, json.JSONDecodeError, KeyError):
        return ""
