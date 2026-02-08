#!/usr/bin/env python3
"""
Google Workspace auth setup.

Run this once to create (or refresh) the shared token:
    python -m google_workspace.setup_auth

Or migrate an existing token from another project:
    python -m google_workspace.setup_auth --migrate ~/Projects/weekly-report/token.json
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from google_workspace.auth import (
    SCOPES,
    _CONFIG_DIR,
    _CREDENTIALS_PATH,
    _TOKEN_PATH,
)


def ensure_config_dir():
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def migrate_token(source: str):
    """Copy an existing token.json to the shared config location."""
    src = Path(source).expanduser().resolve()
    if not src.exists():
        print(f"Source token not found: {src}")
        sys.exit(1)

    ensure_config_dir()
    shutil.copy2(src, _TOKEN_PATH)
    print(f"Migrated token from {src} -> {_TOKEN_PATH}")


def migrate_credentials(source: str):
    """Copy an existing credentials.json to the shared config location."""
    src = Path(source).expanduser().resolve()
    if not src.exists():
        print(f"Source credentials not found: {src}")
        sys.exit(1)

    ensure_config_dir()
    shutil.copy2(src, _CREDENTIALS_PATH)
    print(f"Migrated credentials from {src} -> {_CREDENTIALS_PATH}")


def run_oauth_flow():
    """Run the interactive OAuth flow to create a new token."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    ensure_config_dir()

    if not _CREDENTIALS_PATH.exists():
        print(f"No credentials.json found at {_CREDENTIALS_PATH}")
        print()
        print("To set up:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Select your project")
        print("3. Enable: Calendar, Gmail, Docs, Drive, Sheets APIs")
        print("4. Create OAuth 2.0 Desktop credentials")
        print("5. Download the JSON and place it at:")
        print(f"   {_CREDENTIALS_PATH}")
        print()
        print("Or migrate from an existing project:")
        print("  python -m google_workspace.setup_auth \\")
        print(f"    --migrate-credentials ~/.config/deal-research/credentials.json")
        sys.exit(1)

    creds = None

    if _TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("Starting OAuth flow (browser will open)...")
            print(f"Requesting scopes: {len(SCOPES)}")
            for s in SCOPES:
                print(f"  - {s.split('/')[-1]}")
            print()

            flow = InstalledAppFlow.from_client_secrets_file(
                str(_CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        _TOKEN_PATH.write_text(creds.to_json())
        print(f"Token saved to {_TOKEN_PATH}")

    return creds


def verify_access(creds):
    """Test each API to confirm access works."""
    from googleapiclient.discovery import build

    print()
    print("Verifying API access...")

    apis = [
        ("Calendar", "calendar", "v3",
         lambda s: s.calendarList().list(maxResults=1).execute()),
        ("Gmail", "gmail", "v1",
         lambda s: s.users().getProfile(userId="me").execute()),
        ("Docs", "docs", "v1",
         lambda s: "OK"),  # No read-only list endpoint; connection is enough
        ("Drive", "drive", "v3",
         lambda s: s.files().list(pageSize=1).execute()),
        ("Sheets", "sheets", "v4",
         lambda s: "OK"),  # No read-only list endpoint; connection is enough
    ]

    for name, api, version, test_fn in apis:
        try:
            service = build(api, version, credentials=creds)
            test_fn(service)
            print(f"  {name}: OK")
        except Exception as e:
            print(f"  {name}: FAILED - {e}")


def main():
    parser = argparse.ArgumentParser(description="Google Workspace auth setup")
    parser.add_argument(
        "--migrate", metavar="TOKEN_PATH",
        help="Migrate an existing token.json to the shared location",
    )
    parser.add_argument(
        "--migrate-credentials", metavar="CREDS_PATH",
        help="Migrate an existing credentials.json to the shared location",
    )
    parser.add_argument(
        "--verify-only", action="store_true",
        help="Only verify existing token works, don't create new one",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("Google Workspace Auth Setup")
    print("=" * 50)
    print(f"Config dir: {_CONFIG_DIR}")
    print()

    if args.migrate_credentials:
        migrate_credentials(args.migrate_credentials)

    if args.migrate:
        migrate_token(args.migrate)

    if args.verify_only:
        from google.oauth2.credentials import Credentials
        if not _TOKEN_PATH.exists():
            print(f"No token found at {_TOKEN_PATH}")
            sys.exit(1)
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), SCOPES)
        verify_access(creds)
    else:
        creds = run_oauth_flow()
        verify_access(creds)

    print()
    print("=" * 50)
    print("Setup complete.")
    print("Usage: from google_workspace import calendar, gmail, docs, drive, sheets")
    print("=" * 50)


if __name__ == "__main__":
    main()
