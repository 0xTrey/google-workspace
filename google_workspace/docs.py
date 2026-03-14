"""Google Docs API wrapper."""

from __future__ import annotations

from google_workspace.auth import build_service


def create_doc(title: str, folder_id: str = None) -> tuple[str, str]:
    """Create a document and optionally move it to a Drive folder."""
    docs_service = build_service("docs", "v1")
    drive_service = build_service("drive", "v3")

    created = docs_service.documents().create(body={"title": title}).execute()
    doc_id = created["documentId"]

    if folder_id:
        file_meta = drive_service.files().get(fileId=doc_id, fields="parents").execute()
        previous_parents = ",".join(file_meta.get("parents", []))
        update_kwargs = {
            "fileId": doc_id,
            "addParents": folder_id,
            "fields": "id,parents",
        }
        if previous_parents:
            update_kwargs["removeParents"] = previous_parents
        drive_service.files().update(**update_kwargs).execute()

    return doc_id, f"https://docs.google.com/document/d/{doc_id}/edit"


def read_doc(doc_id: str) -> str:
    """Read a Google Doc and return plain text."""
    docs_service = build_service("docs", "v1")
    document = docs_service.documents().get(documentId=doc_id).execute()
    body_content = document.get("body", {}).get("content", [])
    return _extract_text_from_elements(body_content)


def append_text(doc_id: str, text: str) -> None:
    """Append plain text at the end of a Google Doc."""
    if not text:
        return

    docs_service = build_service("docs", "v1")
    document = docs_service.documents().get(documentId=doc_id).execute()
    content = document.get("body", {}).get("content", [])
    end_index = content[-1].get("endIndex", 1) - 1 if content else 1

    requests = [
        {
            "insertText": {
                "location": {"index": max(1, end_index)},
                "text": text,
            }
        }
    ]
    docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()


def batch_update(doc_id: str, requests: list) -> None:
    """Execute a Docs batchUpdate request list."""
    docs_service = build_service("docs", "v1")
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()


def _extract_text_from_elements(elements: list[dict]) -> str:
    pieces: list[str] = []

    for element in elements:
        paragraph = element.get("paragraph")
        if paragraph:
            for paragraph_element in paragraph.get("elements", []):
                text_run = paragraph_element.get("textRun")
                if text_run:
                    pieces.append(text_run.get("content", ""))

        table = element.get("table")
        if table:
            for row in table.get("tableRows", []):
                for cell in row.get("tableCells", []):
                    pieces.append(_extract_text_from_elements(cell.get("content", [])))

        toc = element.get("tableOfContents")
        if toc:
            pieces.append(_extract_text_from_elements(toc.get("content", [])))

    return "".join(pieces)
