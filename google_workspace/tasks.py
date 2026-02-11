"""
Google Tasks tools (read-only).

Usage:
    from google_workspace.tasks import list_task_lists, list_tasks, get_all_tasks

    lists = list_task_lists()
    tasks = list_tasks(tasklist_id="MTIzNDU2Nzg5MA")
    all_tasks = get_all_tasks(show_completed=False)
"""

from __future__ import annotations

from typing import Optional

from google_workspace.auth import build_service


def _service():
    return build_service("tasks", "v1")


def list_task_lists() -> list[dict]:
    """List all task lists.

    Returns list of dicts with: id, title, updated.
    """
    results = _service().tasklists().list(maxResults=100).execute()

    return [
        {
            "id": tl["id"],
            "title": tl.get("title", ""),
            "updated": tl.get("updated", ""),
        }
        for tl in results.get("items", [])
    ]


def list_tasks(
    tasklist_id: str,
    show_completed: bool = False,
    max_results: int = 100,
) -> list[dict]:
    """List tasks from a specific task list.

    Args:
        tasklist_id: The task list ID.
        show_completed: Include completed tasks.
        max_results: Max tasks to return.

    Returns list of dicts with: id, title, notes, status, due, completed,
        updated, parent, position, list_id, list_title.
    """
    svc = _service()
    all_items = []
    page_token = None

    while True:
        result = svc.tasks().list(
            tasklist=tasklist_id,
            showCompleted=show_completed,
            showHidden=show_completed,
            maxResults=min(max_results - len(all_items), 100),
            pageToken=page_token,
        ).execute()

        all_items.extend(result.get("items", []))
        page_token = result.get("nextPageToken")

        if not page_token or len(all_items) >= max_results:
            break

    return [
        {
            "id": t["id"],
            "title": t.get("title", ""),
            "notes": t.get("notes", ""),
            "status": t.get("status", ""),
            "due": t.get("due", ""),
            "completed": t.get("completed", ""),
            "updated": t.get("updated", ""),
            "parent": t.get("parent", ""),
            "position": t.get("position", ""),
        }
        for t in all_items
    ]


def get_all_tasks(
    show_completed: bool = False,
    max_per_list: int = 100,
) -> list[dict]:
    """Get tasks from all task lists, with list name attached.

    Args:
        show_completed: Include completed tasks.
        max_per_list: Max tasks per list.

    Returns list of dicts: same as list_tasks() plus list_id, list_title.
    """
    task_lists = list_task_lists()
    all_tasks = []

    for tl in task_lists:
        tasks = list_tasks(
            tl["id"],
            show_completed=show_completed,
            max_results=max_per_list,
        )
        for t in tasks:
            t["list_id"] = tl["id"]
            t["list_title"] = tl["title"]
        all_tasks.extend(tasks)

    return all_tasks
