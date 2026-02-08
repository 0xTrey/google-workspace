"""
Google Sheets tools.

Usage:
    from google_workspace.sheets import read_sheet, write_rows, append_rows

    data = read_sheet(spreadsheet_id, "Sheet1!A1:D10")
    write_rows(spreadsheet_id, "Sheet1!A1", [["Name", "Value"], ["foo", "42"]])
    append_rows(spreadsheet_id, "Sheet1", [["new row", "data"]])
"""

from __future__ import annotations

from typing import Optional

from google_workspace.auth import build_service


def _service():
    return build_service("sheets", "v4")


def read_sheet(
    spreadsheet_id: str,
    range: str,
    value_render: str = "FORMATTED_VALUE",
) -> list[list]:
    """Read values from a spreadsheet range.

    Args:
        spreadsheet_id: The spreadsheet ID from the URL.
        range: A1 notation range (e.g. "Sheet1!A1:D10").
        value_render: How to render values -- FORMATTED_VALUE, UNFORMATTED_VALUE, or FORMULA.

    Returns a 2D list of cell values (rows x cols).
    """
    result = _service().spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range,
        valueRenderOption=value_render,
    ).execute()

    return result.get("values", [])


def write_rows(
    spreadsheet_id: str,
    range: str,
    values: list[list],
    input_option: str = "USER_ENTERED",
) -> dict:
    """Write values to a spreadsheet range (overwrites existing data).

    Args:
        spreadsheet_id: The spreadsheet ID.
        range: A1 notation range (e.g. "Sheet1!A1").
        values: 2D list of values to write.
        input_option: USER_ENTERED (parsed) or RAW (literal strings).

    Returns the API response with updated cell count.
    """
    return _service().spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range,
        valueInputOption=input_option,
        body={"values": values},
    ).execute()


def append_rows(
    spreadsheet_id: str,
    range: str,
    values: list[list],
    input_option: str = "USER_ENTERED",
) -> dict:
    """Append rows to the end of a spreadsheet range.

    Args:
        spreadsheet_id: The spreadsheet ID.
        range: Sheet name or A1 range to append after (e.g. "Sheet1").
        values: 2D list of rows to append.
        input_option: USER_ENTERED or RAW.

    Returns the API response.
    """
    return _service().spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range,
        valueInputOption=input_option,
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()


def get_spreadsheet_metadata(spreadsheet_id: str) -> dict:
    """Get spreadsheet metadata (title, sheets, etc.).

    Returns dict with: id, title, sheets[{id, title, row_count, col_count}].
    """
    ss = _service().spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    return {
        "id": ss.get("spreadsheetId", ""),
        "title": ss.get("properties", {}).get("title", ""),
        "url": ss.get("spreadsheetUrl", ""),
        "sheets": [
            {
                "id": s["properties"]["sheetId"],
                "title": s["properties"]["title"],
                "row_count": s["properties"]["gridProperties"]["rowCount"],
                "col_count": s["properties"]["gridProperties"]["columnCount"],
            }
            for s in ss.get("sheets", [])
        ],
    }


def clear_range(spreadsheet_id: str, range: str) -> dict:
    """Clear all values from a range (keeps formatting)."""
    return _service().spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=range,
    ).execute()
