"""Google Sheets API wrapper."""

from __future__ import annotations

from google_workspace.auth import build_service


def read_sheet(sheet_id: str, range: str) -> list[list]:
    """Read values from a sheet range."""
    service = build_service("sheets", "v4")
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=range)
        .execute()
    )
    return response.get("values", [])


def write_rows(sheet_id: str, range: str, values: list[list]) -> None:
    """Overwrite rows in a sheet range using RAW input."""
    service = build_service("sheets", "v4")
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=range,
        valueInputOption="RAW",
        body={"values": values},
    ).execute()


def append_rows(sheet_id: str, range: str, values: list[list]) -> None:
    """Append rows to a sheet range using RAW input."""
    service = build_service("sheets", "v4")
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=range,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()
