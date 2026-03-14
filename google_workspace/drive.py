"""Google Drive API wrapper."""

from __future__ import annotations

import io

from googleapiclient.http import MediaIoBaseDownload

from google_workspace.auth import build_service


def list_files(folder_id: str) -> list[dict]:
    """List files in a Drive folder."""
    query = f"'{folder_id}' in parents and trashed = false"
    return _list_files(query)


def search_files(query: str) -> list[dict]:
    """Search Drive files using Drive query syntax."""
    return _list_files(query)


def get_file_text(file_id: str) -> str:
    """Return plain text for Google Docs or plain text files."""
    service = build_service("drive", "v3")
    metadata = service.files().get(fileId=file_id, fields="id,name,mimeType").execute()
    mime_type = metadata.get("mimeType", "")

    if mime_type == "application/vnd.google-apps.document":
        exported = service.files().export(fileId=file_id, mimeType="text/plain").execute()
        if isinstance(exported, bytes):
            return exported.decode("utf-8", errors="replace")
        return str(exported)

    if mime_type.startswith("text/"):
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue().decode("utf-8", errors="replace")

    raise ValueError(f"Unsupported file type for text extraction: {mime_type}")


def move_file(file_id: str, folder_id: str) -> None:
    """Move a Drive file to a folder, preserving parent semantics."""
    service = build_service("drive", "v3")
    file_meta = service.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file_meta.get("parents", []))

    update_kwargs = {
        "fileId": file_id,
        "addParents": folder_id,
        "fields": "id,parents",
    }
    if previous_parents:
        update_kwargs["removeParents"] = previous_parents

    service.files().update(**update_kwargs).execute()


def _list_files(query: str) -> list[dict]:
    service = build_service("drive", "v3")
    files: list[dict] = []
    page_token: str | None = None

    while True:
        response = (
            service.files()
            .list(
                q=query,
                pageToken=page_token,
                pageSize=100,
                fields=(
                    "nextPageToken,files(id,name,mimeType,modifiedTime,webViewLink,parents)"
                ),
            )
            .execute()
        )

        files.extend(_normalize_file(item) for item in response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return files


def _normalize_file(file_obj: dict) -> dict:
    return {
        "id": file_obj.get("id"),
        "name": file_obj.get("name", ""),
        "mimeType": file_obj.get("mimeType", ""),
        "modifiedTime": file_obj.get("modifiedTime", ""),
        "webViewLink": file_obj.get("webViewLink", ""),
        "parents": file_obj.get("parents", []),
    }
