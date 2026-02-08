"""
Google Drive tools.

Usage:
    from google_workspace.drive import list_files, get_file, search_files

    files = list_files(folder_id="abc123")
    content = get_file_text(file_id)
"""

from __future__ import annotations

from typing import Optional

from google_workspace.auth import build_service


def _service():
    return build_service("drive", "v3")


def list_files(
    folder_id: Optional[str] = None,
    mime_type: Optional[str] = None,
    max_results: int = 100,
    order_by: str = "modifiedTime desc",
) -> list[dict]:
    """List files in Drive, optionally filtered by folder or type.

    Args:
        folder_id: Restrict to this folder.
        mime_type: Filter by MIME type (e.g. "application/vnd.google-apps.document").
        max_results: Max files to return.
        order_by: Sort order.

    Returns list of dicts with: id, name, mime_type, modified_time, web_link.
    """
    query_parts = ["trashed = false"]
    if folder_id:
        query_parts.append(f"'{folder_id}' in parents")
    if mime_type:
        query_parts.append(f"mimeType = '{mime_type}'")

    q = " and ".join(query_parts)

    results = _service().files().list(
        q=q,
        pageSize=max_results,
        orderBy=order_by,
        fields="files(id, name, mimeType, modifiedTime, webViewLink, parents)",
    ).execute()

    return [
        {
            "id": f["id"],
            "name": f.get("name", ""),
            "mime_type": f.get("mimeType", ""),
            "modified_time": f.get("modifiedTime", ""),
            "web_link": f.get("webViewLink", ""),
            "parents": f.get("parents", []),
        }
        for f in results.get("files", [])
    ]


def search_files(
    query: str,
    max_results: int = 50,
) -> list[dict]:
    """Search Drive files by name.

    Args:
        query: Text to search for in file names.
        max_results: Max files to return.
    """
    q = f"name contains '{query}' and trashed = false"

    results = _service().files().list(
        q=q,
        pageSize=max_results,
        fields="files(id, name, mimeType, modifiedTime, webViewLink)",
    ).execute()

    return [
        {
            "id": f["id"],
            "name": f.get("name", ""),
            "mime_type": f.get("mimeType", ""),
            "modified_time": f.get("modifiedTime", ""),
            "web_link": f.get("webViewLink", ""),
        }
        for f in results.get("files", [])
    ]


def get_file_metadata(file_id: str) -> dict:
    """Get metadata for a single file."""
    f = _service().files().get(
        fileId=file_id,
        fields="id, name, mimeType, modifiedTime, webViewLink, parents, size",
    ).execute()

    return {
        "id": f["id"],
        "name": f.get("name", ""),
        "mime_type": f.get("mimeType", ""),
        "modified_time": f.get("modifiedTime", ""),
        "web_link": f.get("webViewLink", ""),
        "parents": f.get("parents", []),
        "size": f.get("size", ""),
    }


def get_file_text(file_id: str) -> str:
    """Download a file's content as plain text.

    Works for Google Docs (exported as text/plain) and text files.
    """
    svc = _service()

    # Check MIME type to decide export vs download
    meta = svc.files().get(fileId=file_id, fields="mimeType").execute()
    mime = meta.get("mimeType", "")

    if mime.startswith("application/vnd.google-apps."):
        # Google native format -- export as plain text
        content = svc.files().export(fileId=file_id, mimeType="text/plain").execute()
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="ignore")
        return str(content)
    else:
        # Regular file -- download
        content = svc.files().get_media(fileId=file_id).execute()
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="ignore")
        return str(content)


def move_file(file_id: str, new_folder_id: str) -> None:
    """Move a file to a different folder."""
    svc = _service()
    file = svc.files().get(fileId=file_id, fields="parents").execute()
    prev_parents = ",".join(file.get("parents", []))

    svc.files().update(
        fileId=file_id,
        addParents=new_folder_id,
        removeParents=prev_parents,
        fields="id, parents",
    ).execute()
