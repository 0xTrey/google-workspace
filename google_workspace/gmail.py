"""Google Gmail API wrapper."""

from __future__ import annotations

import base64
import email.mime.multipart
import email.mime.text

from google_workspace.auth import build_service


def send_email(to: str, subject: str, body_html: str, body_text: str = "") -> dict:
    """
    Send an email from the authenticated Gmail account.

    Args:
        to: recipient email address
        subject: email subject line
        body_html: HTML body (primary)
        body_text: plain text fallback (optional)

    Returns the Gmail API send response (id, threadId, labelIds).
    """
    service = build_service("gmail", "v1")

    msg = email.mime.multipart.MIMEMultipart("alternative")
    msg["To"] = to
    msg["Subject"] = subject

    if body_text:
        msg.attach(email.mime.text.MIMEText(body_text, "plain"))
    msg.attach(email.mime.text.MIMEText(body_html, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()


def get_profile() -> dict:
    """Return the authenticated Gmail profile."""
    service = build_service("gmail", "v1")
    return service.users().getProfile(userId="me").execute()


def search_messages(query: str, days: int = 7) -> list[dict]:
    """Search messages with a recency filter and return normalized summaries."""
    service = build_service("gmail", "v1")
    recency = f"newer_than:{max(0, days)}d"
    full_query = f"{query} {recency}".strip()

    results: list[dict] = []
    page_token: str | None = None

    while True:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=full_query, pageToken=page_token)
            .execute()
        )

        for item in response.get("messages", []):
            message = (
                service.users()
                .messages()
                .get(userId="me", id=item["id"], format="metadata")
                .execute()
            )
            results.append(_normalize_message_summary(message))

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return results


def get_message(message_id: str) -> dict:
    """Return a parsed Gmail message."""
    service = build_service("gmail", "v1")
    message = (
        service.users().messages().get(userId="me", id=message_id, format="full").execute()
    )

    headers = _headers_map(message.get("payload", {}).get("headers", []))
    text_body, html_body = _extract_bodies(message.get("payload", {}))

    return {
        "id": message.get("id"),
        "threadId": message.get("threadId"),
        "labelIds": message.get("labelIds", []),
        "snippet": message.get("snippet", ""),
        "internalDate": message.get("internalDate"),
        "headers": headers,
        "body": text_body,
        "bodyHtml": html_body,
        "payload": {
            "mimeType": message.get("payload", {}).get("mimeType", ""),
            "filename": message.get("payload", {}).get("filename", ""),
            "partCount": len(message.get("payload", {}).get("parts", [])),
        },
    }


def get_thread(thread_id: str) -> dict:
    """Return thread metadata with normalized message summaries."""
    service = build_service("gmail", "v1")
    thread = service.users().threads().get(userId="me", id=thread_id, format="full").execute()

    messages = []
    for message in thread.get("messages", []):
        headers = _headers_map(message.get("payload", {}).get("headers", []))
        messages.append(
            {
                **_normalize_message_summary(message),
                "headers": {
                    "subject": headers.get("subject", ""),
                    "from": headers.get("from", ""),
                    "to": headers.get("to", ""),
                    "date": headers.get("date", ""),
                },
            }
        )

    return {
        "id": thread.get("id"),
        "historyId": thread.get("historyId"),
        "snippet": thread.get("snippet", ""),
        "messages": messages,
    }


def _normalize_message_summary(message: dict) -> dict:
    headers = _headers_map(message.get("payload", {}).get("headers", []))
    return {
        "id": message.get("id"),
        "threadId": message.get("threadId"),
        "snippet": message.get("snippet", ""),
        "internalDate": message.get("internalDate"),
        "labelIds": message.get("labelIds", []),
        "subject": headers.get("subject", ""),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "date": headers.get("date", ""),
    }


def _headers_map(headers: list[dict]) -> dict:
    mapped: dict[str, str] = {}
    for header in headers:
        name = str(header.get("name", "")).lower()
        if name:
            mapped[name] = header.get("value", "")
    return mapped


def _extract_bodies(payload: dict) -> tuple[str, str]:
    text_body = ""
    html_body = ""

    mime_type = payload.get("mimeType", "")
    data = payload.get("body", {}).get("data")
    if data:
        decoded = _decode_base64(data)
        if mime_type == "text/plain":
            text_body = decoded
        elif mime_type == "text/html":
            html_body = decoded

    for part in payload.get("parts", []):
        part_text, part_html = _extract_bodies(part)
        if not text_body and part_text:
            text_body = part_text
        if not html_body and part_html:
            html_body = part_html

    return text_body, html_body


def _decode_base64(data: str) -> str:
    padding = "=" * (-len(data) % 4)
    decoded = base64.urlsafe_b64decode(data + padding)
    return decoded.decode("utf-8", errors="replace")
