"""
Google Docs tools.

Usage:
    from google_workspace.docs import create_doc, read_doc, append_text

    doc_id, url = create_doc("My Doc", folder_id="abc123")
    content = read_doc(doc_id)
    append_text(doc_id, "New paragraph here.")
"""

from __future__ import annotations

from typing import Optional

from google_workspace.auth import build_service


def _docs():
    return build_service("docs", "v1")


def _drive():
    return build_service("drive", "v3")


def create_doc(
    title: str,
    folder_id: Optional[str] = None,
) -> tuple[str, str]:
    """Create a new Google Doc.

    Args:
        title: Document title.
        folder_id: Drive folder ID to move the doc into.

    Returns:
        (document_id, document_url)
    """
    doc = _docs().documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    if folder_id:
        drive = _drive()
        file = drive.files().get(fileId=doc_id, fields="parents").execute()
        prev_parents = ",".join(file.get("parents", []))
        drive.files().update(
            fileId=doc_id,
            addParents=folder_id,
            removeParents=prev_parents,
            fields="id, parents",
        ).execute()

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return doc_id, url


def read_doc(doc_id: str) -> str:
    """Read the full text content of a Google Doc.

    Returns the document text as a plain string.
    """
    doc = _docs().documents().get(documentId=doc_id).execute()
    content = doc.get("body", {}).get("content", [])

    text_parts = []
    for element in content:
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        for elem in paragraph.get("elements", []):
            text_run = elem.get("textRun")
            if text_run:
                text_parts.append(text_run.get("content", ""))

    return "".join(text_parts)


def append_text(doc_id: str, text: str) -> None:
    """Append text to the end of a Google Doc."""
    doc = _docs().documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"] - 1

    _docs().documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {"index": end_index},
                        "text": text,
                    }
                }
            ]
        },
    ).execute()


def batch_update(doc_id: str, requests: list[dict]) -> dict:
    """Send a raw batchUpdate to a Google Doc.

    For advanced formatting (headings, bold, links, etc.) pass
    a list of request dicts per the Docs API spec.

    Returns the batchUpdate response.
    """
    return _docs().documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()
