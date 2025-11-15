"""
# * Apply background colors to spreadsheet ranges based on JSON input.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# * Ensure the project root is importable even when run elsewhere
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test import (  # type: ignore
    DEFAULT_CREDENTIALS_PATH,
    DEFAULT_SPREADSHEET_URL,
    GoogleSheetsFormulaValidator,
)

load_dotenv()

Color = Dict[str, float]


def _parse_args() -> Path:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python function_to_color_things.py /absolute/path/to/input.json")

    path = Path(sys.argv[1]).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"No input file at {path}")
    return path


def _load_payload(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text())
    potential_errors = payload.get("potential_errors")
    if not isinstance(potential_errors, list) or not potential_errors:
        raise ValueError("Input must include a non-empty 'potential_errors' list.")

    normalized: List[Dict[str, Any]] = []
    for idx, item in enumerate(potential_errors):
        if not isinstance(item, dict):
            raise ValueError(f"Entry #{idx} is not an object.")
        cell_location = item.get("cell_location")
        message = item.get("message")
        color = item.get("color")
        if not isinstance(cell_location, str) or not cell_location.strip():
            raise ValueError(f"Entry #{idx} missing 'cell_location'.")
        if not isinstance(message, str) or not message.strip():
            raise ValueError(f"Entry #{idx} missing 'message'.")
        if not isinstance(color, str) or not color.strip():
            raise ValueError(f"Entry #{idx} missing 'color'.")
        normalized.append(
            {
                "cell_location": cell_location.strip().upper(),
                "message": message.strip(),
                "color": _hex_color_to_rgb(color.strip()),
            }
        )
    return normalized


def _hex_color_to_rgb(value: str) -> Color:
    match = re.fullmatch(r"#?([0-9A-Fa-f]{6})", value)
    if not match:
        raise ValueError(f"Invalid hex color '{value}'.")
    hex_value = match.group(1)
    red = int(hex_value[0:2], 16) / 255.0
    green = int(hex_value[2:4], 16) / 255.0
    blue = int(hex_value[4:6], 16) / 255.0
    return {"red": red, "green": green, "blue": blue}


def _column_to_index(label: str) -> int:
    if not re.fullmatch(r"[A-Z]+", label):
        raise ValueError(f"Invalid column label '{label}'.")
    index = 0
    for char in label:
        index = index * 26 + (ord(char) - 64)
    return index - 1


def _parse_cell(cell: str) -> Tuple[int, int]:
    match = re.fullmatch(r"([A-Z]+)(\d+)", cell)
    if not match:
        raise ValueError(f"Invalid cell reference '{cell}'.")
    column = _column_to_index(match.group(1))
    row = int(match.group(2)) - 1
    if row < 0:
        raise ValueError(f"Row index must be positive in '{cell}'.")
    return row, column


def _range_to_bounds(range_ref: str) -> Tuple[int, int, int, int]:
    parts = range_ref.split(":")
    if len(parts) == 1:
        start = end = parts[0]
    elif len(parts) == 2:
        start, end = parts
    else:
        raise ValueError(f"Invalid range '{range_ref}'.")
    start_row, start_col = _parse_cell(start)
    end_row, end_col = _parse_cell(end)
    if end_row < start_row or end_col < start_col:
        raise ValueError(f"Range '{range_ref}' has inverted bounds.")
    # * Convert to exclusive upper bounds for Sheets API
    return start_row, end_row + 1, start_col, end_col + 1


def _resolve_sheet(spreadsheet: Dict[str, Any], gid: Optional[int]) -> Dict[str, Any]:
    sheets = spreadsheet.get("sheets", [])
    if not sheets:
        raise ValueError("No sheets available in spreadsheet.")
    if gid is None:
        return sheets[0]
    for sheet in sheets:
        if sheet["properties"].get("sheetId") == gid:
            return sheet
    raise ValueError(f"No sheet found with gid={gid}.")


def _build_request(sheet_id: int, cell_location: str, color: Color, note: str) -> Dict[str, Any]:
    start_row, end_row, start_col, end_col = _range_to_bounds(cell_location)
    cell_payload: Dict[str, Any] = {
        "userEnteredFormat": {
            "backgroundColor": color,
        }
    }
    fields = "userEnteredFormat.backgroundColor"
    if note:
        cell_payload["note"] = note
        fields += ",note"
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": start_row,
                "endRowIndex": end_row,
                "startColumnIndex": start_col,
                "endColumnIndex": end_col,
            },
            "cell": cell_payload,
            "fields": fields,
        }
    }


def main() -> None:
    input_path = _parse_args()
    entries = _load_payload(input_path)

    url_id_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", DEFAULT_SPREADSHEET_URL)
    url_gid_match = re.search(r"[?&]gid=(\d+)", DEFAULT_SPREADSHEET_URL)
    spreadsheet_id = url_id_match.group(1) if url_id_match else DEFAULT_SPREADSHEET_URL
    gid = int(url_gid_match.group(1)) if url_gid_match else None

    validator = GoogleSheetsFormulaValidator(DEFAULT_CREDENTIALS_PATH)
    spreadsheet = validator.fetch_spreadsheet(spreadsheet_id)
    sheet = _resolve_sheet(spreadsheet, gid)
    sheet_props = sheet["properties"]

    requests = [
        _build_request(sheet_props["sheetId"], entry["cell_location"], entry["color"], entry["message"])
        for entry in entries
    ]

    if not requests:
        raise ValueError("No color requests generated.")

    validator.service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()

    print(f"Colored {len(requests)} target range(s) on '{sheet_props['title']}'.")


if __name__ == "__main__":
    main()


