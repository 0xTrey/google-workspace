"""Google Calendar API wrapper."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from google_workspace.auth import build_service


def list_events(days: int = 7) -> list[dict]:
    """Return events from the previous `days` days."""
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=max(0, days))).isoformat()
    time_max = now.isoformat()
    events = _list_events_window(time_min=time_min, time_max=time_max)
    return _sort_events(events)


def list_upcoming_events(days: int = 7) -> list[dict]:
    """Return events in the next `days` days."""
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=max(0, days))).isoformat()
    events = _list_events_window(time_min=time_min, time_max=time_max)
    return _sort_events(events)


def get_event(event_id: str) -> dict:
    """Return a single event by ID."""
    service = build_service("calendar", "v3")
    event = service.events().get(calendarId="primary", eventId=event_id).execute()
    return _normalize_event(event)


def _list_events_window(*, time_min: str, time_max: str) -> list[dict]:
    service = build_service("calendar", "v3")
    events: list[dict] = []
    page_token: str | None = None

    while True:
        response = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
            )
            .execute()
        )
        events.extend(_normalize_event(item) for item in response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return events


def _normalize_event(event: dict) -> dict:
    return {
        "id": event.get("id"),
        "summary": event.get("summary", ""),
        "start": _extract_event_time(event.get("start", {})),
        "end": _extract_event_time(event.get("end", {})),
        "status": event.get("status", ""),
        "htmlLink": event.get("htmlLink", ""),
        "organizer": event.get("organizer"),
        "attendees": event.get("attendees", []),
        "location": event.get("location", ""),
        "description": event.get("description", ""),
    }


def _extract_event_time(value: dict) -> str:
    return value.get("dateTime") or value.get("date") or ""


def _sort_events(events: list[dict]) -> list[dict]:
    return sorted(events, key=lambda event: _sort_key(event.get("start", "")))


def _sort_key(raw_start: str) -> datetime:
    if not raw_start:
        return datetime.max.replace(tzinfo=timezone.utc)

    if "T" in raw_start:
        return _parse_datetime(raw_start)

    try:
        day = date.fromisoformat(raw_start)
        return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    except ValueError:
        return datetime.max.replace(tzinfo=timezone.utc)


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
