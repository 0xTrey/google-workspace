"""
Google Calendar tools.

Usage:
    from google_workspace.calendar import list_events, get_event

    events = list_events(days=7)
    event = get_event(event_id)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from google_workspace.auth import build_service


def _service():
    return build_service("calendar", "v3")


def list_events(
    days: int = 7,
    calendar_id: str = "primary",
    max_results: int = 250,
    query: Optional[str] = None,
) -> list[dict]:
    """Fetch calendar events for the past N days.

    Returns list of dicts with: id, summary, start, end, attendees,
    organizer, status, html_link, color_id.
    """
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=days)).isoformat()
    time_max = now.isoformat()

    kwargs = dict(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
        maxResults=max_results,
    )
    if query:
        kwargs["q"] = query

    results = _service().events().list(**kwargs).execute()
    events = results.get("items", [])

    return [
        {
            "id": e.get("id"),
            "summary": e.get("summary", "(no title)"),
            "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date")),
            "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date")),
            "attendees": [
                {
                    "email": a.get("email"),
                    "name": a.get("displayName", ""),
                    "response": a.get("responseStatus", ""),
                    "self": a.get("self", False),
                }
                for a in e.get("attendees", [])
            ],
            "organizer": e.get("organizer", {}).get("email", ""),
            "status": e.get("status", ""),
            "html_link": e.get("htmlLink", ""),
            "color_id": e.get("colorId"),
            "description": e.get("description", ""),
            "location": e.get("location", ""),
        }
        for e in events
    ]


def list_upcoming_events(
    days: int = 7,
    calendar_id: str = "primary",
    max_results: int = 250,
    query: Optional[str] = None,
) -> list[dict]:
    """Fetch calendar events for the next N days (future-looking)."""
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days)).isoformat()

    kwargs = dict(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
        maxResults=max_results,
    )
    if query:
        kwargs["q"] = query

    results = _service().events().list(**kwargs).execute()
    events = results.get("items", [])

    return [
        {
            "id": e.get("id"),
            "summary": e.get("summary", "(no title)"),
            "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date")),
            "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date")),
            "attendees": [
                {
                    "email": a.get("email"),
                    "name": a.get("displayName", ""),
                    "response": a.get("responseStatus", ""),
                    "self": a.get("self", False),
                }
                for a in e.get("attendees", [])
            ],
            "organizer": e.get("organizer", {}).get("email", ""),
            "status": e.get("status", ""),
            "html_link": e.get("htmlLink", ""),
            "color_id": e.get("colorId"),
            "description": e.get("description", ""),
            "location": e.get("location", ""),
        }
        for e in events
    ]


def get_event(event_id: str, calendar_id: str = "primary") -> dict:
    """Fetch a single calendar event by ID."""
    e = _service().events().get(calendarId=calendar_id, eventId=event_id).execute()
    return {
        "id": e.get("id"),
        "summary": e.get("summary", "(no title)"),
        "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date")),
        "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date")),
        "attendees": [
            {
                "email": a.get("email"),
                "name": a.get("displayName", ""),
                "response": a.get("responseStatus", ""),
            }
            for a in e.get("attendees", [])
        ],
        "organizer": e.get("organizer", {}).get("email", ""),
        "description": e.get("description", ""),
        "location": e.get("location", ""),
        "html_link": e.get("htmlLink", ""),
        "color_id": e.get("colorId"),
    }
