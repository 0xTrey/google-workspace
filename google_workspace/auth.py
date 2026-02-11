"""
Shared Google OAuth2 authentication.

Manages a single token file at ~/.config/google-workspace/token.json
with the superset of all scopes needed across projects.

Usage:
    from google_workspace.auth import get_credentials, build_service

    creds = get_credentials()
    service = build_service("calendar", "v3")
"""

from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# All scopes needed across projects
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/tasks.readonly",
]

_CONFIG_DIR = Path(os.environ.get(
    "GOOGLE_WORKSPACE_CONFIG",
    Path.home() / ".config" / "google-workspace",
))
_TOKEN_PATH = _CONFIG_DIR / "token.json"
_CREDENTIALS_PATH = _CONFIG_DIR / "credentials.json"

# Cache to avoid re-reading disk on every call
_cached_creds: Credentials | None = None


def get_credentials() -> Credentials:
    """Load and refresh Google OAuth2 credentials.

    Reads from ~/.config/google-workspace/token.json.
    Automatically refreshes expired tokens.

    Raises FileNotFoundError if no token exists (run setup_auth.py first).
    """
    global _cached_creds

    if _cached_creds and _cached_creds.valid:
        return _cached_creds

    if not _TOKEN_PATH.exists():
        raise FileNotFoundError(
            f"No token at {_TOKEN_PATH}. "
            "Run: python -m google_workspace.setup_auth"
        )

    # Load without enforcing scopes -- the token carries its own authorized
    # scopes. Passing SCOPES here would cause refresh failures if the token
    # was created with a different scope set. New scopes require re-auth
    # via setup_auth.py.
    creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH))

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _TOKEN_PATH.write_text(creds.to_json())
        else:
            raise RuntimeError(
                f"Token at {_TOKEN_PATH} is invalid and cannot be refreshed. "
                "Run: python -m google_workspace.setup_auth"
            )

    _cached_creds = creds
    return creds


def build_service(api: str, version: str):
    """Build a Google API service client.

    Args:
        api: API name (e.g. "calendar", "gmail", "docs", "drive", "sheets")
        version: API version (e.g. "v3", "v1")

    Returns:
        googleapiclient.discovery.Resource
    """
    return build(api, version, credentials=get_credentials())


def clear_cache() -> None:
    """Clear the cached credentials. Useful for testing."""
    global _cached_creds
    _cached_creds = None
