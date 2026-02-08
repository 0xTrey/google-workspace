"""
Gmail tools.

Usage:
    from google_workspace.gmail import search_messages, get_thread, get_profile

    messages = search_messages("from:someone@company.com", days=7)
    thread = get_thread(thread_id)
"""

from __future__ import annotations

import base64
import re
from datetime import datetime, timedelta
from email.utils import parseaddr
from typing import Optional

from google_workspace.auth import build_service


def _service():
    return build_service("gmail", "v1")


def get_profile() -> dict:
    """Get the authenticated user's Gmail profile."""
    profile = _service().users().getProfile(userId="me").execute()
    return {
        "email": profile.get("emailAddress", ""),
        "messages_total": profile.get("messagesTotal", 0),
        "threads_total": profile.get("threadsTotal", 0),
    }


def search_messages(
    query: str,
    days: Optional[int] = None,
    max_results: int = 50,
) -> list[dict]:
    """Search Gmail messages.

    Args:
        query: Gmail search query (same syntax as the Gmail search bar).
               Examples: "from:someone@co.com", "subject:proposal", "is:unread"
        days: If set, appends "after:YYYY/MM/DD" to the query.
        max_results: Max messages to return.

    Returns list of dicts with: id, thread_id, subject, sender, date, snippet.
    """
    svc = _service()

    if days:
        after = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
        query = f"{query} after:{after}"

    results = svc.users().messages().list(
        userId="me", q=query, maxResults=max_results,
    ).execute()

    message_refs = results.get("messages", [])
    messages = []

    for ref in message_refs:
        msg = svc.users().messages().get(
            userId="me", id=ref["id"], format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        ).execute()

        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }

        messages.append({
            "id": msg["id"],
            "thread_id": msg.get("threadId", ""),
            "subject": headers.get("subject", ""),
            "sender": headers.get("from", ""),
            "date": headers.get("date", ""),
            "snippet": msg.get("snippet", ""),
            "label_ids": msg.get("labelIds", []),
        })

    return messages


def get_message(message_id: str) -> dict:
    """Fetch a single message with full body text.

    Returns dict with: id, thread_id, subject, sender, date, body, label_ids.
    """
    svc = _service()
    msg = svc.users().messages().get(
        userId="me", id=message_id, format="full",
    ).execute()

    headers = {
        h["name"].lower(): h["value"]
        for h in msg.get("payload", {}).get("headers", [])
    }

    body = _extract_body(msg.get("payload", {}))

    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId", ""),
        "subject": headers.get("subject", ""),
        "sender": headers.get("from", ""),
        "date": headers.get("date", ""),
        "body": body,
        "label_ids": msg.get("labelIds", []),
    }


def get_thread(thread_id: str) -> dict:
    """Fetch a full Gmail thread with all messages.

    Returns dict with: id, subject, messages[].
    Each message has: sender, sender_email, date, body, is_me.
    """
    svc = _service()
    user_email = get_profile()["email"]
    user_domain = user_email.split("@")[1] if "@" in user_email else ""

    thread = svc.users().threads().get(userId="me", id=thread_id).execute()
    messages_raw = thread.get("messages", [])

    subject = ""
    messages = []

    for msg in messages_raw:
        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }

        if not subject:
            subject = headers.get("subject", "")

        sender = headers.get("from", "")
        _, sender_email = parseaddr(sender)
        sender_domain = sender_email.split("@")[1] if "@" in sender_email else ""

        messages.append({
            "id": msg["id"],
            "sender": sender,
            "sender_email": sender_email,
            "date": headers.get("date", ""),
            "body": _extract_body(msg.get("payload", {})),
            "is_me": sender_domain == user_domain,
        })

    return {
        "id": thread_id,
        "subject": subject,
        "messages": messages,
    }


def _extract_body(payload: dict) -> str:
    """Extract plain text body from a message payload."""
    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})
    parts = payload.get("parts", [])

    if mime_type == "text/plain" and body.get("data"):
        text = base64.urlsafe_b64decode(body["data"]).decode("utf-8", errors="ignore")
        return re.sub(r"\n{3,}", "\n\n", text.strip())

    if parts:
        for part in parts:
            if part.get("mimeType") == "text/plain":
                part_body = part.get("body", {})
                if part_body.get("data"):
                    text = base64.urlsafe_b64decode(part_body["data"]).decode("utf-8", errors="ignore")
                    return re.sub(r"\n{3,}", "\n\n", text.strip())
            if part.get("mimeType", "").startswith("multipart/"):
                result = _extract_body(part)
                if result:
                    return result

    return ""
