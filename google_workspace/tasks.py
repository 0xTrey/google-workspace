"""Google Tasks API wrapper."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from google_workspace.auth import build_service


def list_tasks(days: int = 7) -> list[dict]:
    """Return recently updated or recently completed tasks across tasklists."""
    service = build_service("tasks", "v1")
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(0, days))

    tasklists = _list_tasklists(service)
    tasks: list[dict] = []

    for tasklist in tasklists:
        for task in _list_tasks(service, tasklist["id"], show_completed=True):
            updated = _parse_rfc3339(task.get("updated"))
            completed = _parse_rfc3339(task.get("completed"))
            if (updated and updated >= cutoff) or (completed and completed >= cutoff):
                tasks.append(_normalize_task(task, tasklist))

    tasks.sort(key=lambda task: task.get("updated", ""), reverse=True)
    return tasks


def get_overdue_tasks() -> list[dict]:
    """Return incomplete tasks with a due date before now across tasklists."""
    service = build_service("tasks", "v1")
    now = datetime.now(timezone.utc)

    tasklists = _list_tasklists(service)
    overdue: list[dict] = []

    for tasklist in tasklists:
        for task in _list_tasks(service, tasklist["id"], show_completed=False):
            due = _parse_rfc3339(task.get("due"))
            if due and due < now and task.get("status") != "completed":
                overdue.append(_normalize_task(task, tasklist))

    overdue.sort(key=lambda task: task.get("due", ""))
    return overdue


def _list_tasklists(service) -> list[dict]:
    tasklists: list[dict] = []
    page_token: str | None = None

    while True:
        response = service.tasklists().list(maxResults=100, pageToken=page_token).execute()
        tasklists.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return tasklists


def _list_tasks(service, tasklist_id: str, *, show_completed: bool) -> list[dict]:
    tasks: list[dict] = []
    page_token: str | None = None

    while True:
        response = (
            service.tasks()
            .list(
                tasklist=tasklist_id,
                maxResults=100,
                pageToken=page_token,
                showCompleted=show_completed,
                showHidden=False,
                showDeleted=False,
            )
            .execute()
        )
        tasks.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return tasks


def _normalize_task(task: dict, tasklist: dict) -> dict:
    return {
        "id": task.get("id"),
        "title": task.get("title", ""),
        "due": task.get("due"),
        "status": task.get("status", ""),
        "notes": task.get("notes", ""),
        "updated": task.get("updated"),
        "tasklist_id": tasklist.get("id"),
        "tasklist_title": tasklist.get("title", ""),
    }


def _parse_rfc3339(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
