"""
# * Restore background colors for cells from a Supabase snapshot batch.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# * Ensure project root is importable when run from tools directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.google_sheets import (
    DEFAULT_CREDENTIALS_PATH,
    DEFAULT_SPREADSHEET_URL,
    GoogleSheetsFormulaValidator,
)

load_dotenv(PROJECT_ROOT / ".env")

Color = Dict[str, float]


# * Environment configuration (must exist; fail fast if missing)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
if not SUPABASE_URL:
    raise SystemExit("SUPABASE_URL must be defined in environment or .env file.")
if not SUPABASE_SERVICE_KEY:
    raise SystemExit("SUPABASE_SERVICE_KEY must be defined in environment or .env file.")


def _parse_args() -> Tuple[str, Optional[Path]]:
    if len(sys.argv) not in (2, 3):
        raise SystemExit(
            "Usage: python restore_input_colors.py <snapshot_batch_id> [/absolute/path/to/input.json]"
        )
    snapshot_batch_id = sys.argv[1]
    json_path = None
    if len(sys.argv) == 3:
        json_candidate = Path(sys.argv[2]).expanduser().resolve()
        if not json_candidate.exists():
            raise FileNotFoundError(f"No input file found at {json_candidate}")
        json_path = json_candidate
    return snapshot_batch_id, json_path


def _load_expected_cells(json_path: Path) -> List[str]:
    payload = json.loads(json_path.read_text())
    potential_errors = payload.get("potential_errors")
    if not isinstance(potential_errors, list) or not potential_errors:
        raise ValueError("Input JSON must contain a non-empty 'potential_errors' list.")

    cells: List[str] = []
    for idx, entry in enumerate(potential_errors):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry #{idx} is not an object.")
        cell_location = entry.get("cell_location")
        if not isinstance(cell_location, str) or not cell_location.strip():
            raise ValueError(f"Entry #{idx} missing 'cell_location'.")
        cells.extend(_expand_range(cell_location.strip().upper()))
    return cells


def _column_index(label: str) -> int:
    if not re.fullmatch(r"[A-Z]+", label):
        raise ValueError(f"Invalid column label '{label}'.")
    index = 0
    for char in label:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _parse_cell(cell: str) -> Tuple[int, int]:
    match = re.fullmatch(r"([A-Z]+)(\d+)", cell)
    if not match:
        raise ValueError(f"Invalid cell reference '{cell}'.")
    column_label, row_digits = match.groups()
    row = int(row_digits) - 1
    if row < 0:
        raise ValueError(f"Row index must be positive in '{cell}'.")
    column = _column_index(column_label)
    return row, column


def _range_bounds(range_ref: str) -> Tuple[int, int, int, int]:
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
    return start_row, end_row, start_col, end_col


def _expand_range(range_ref: str) -> List[str]:
    start_row, end_row, start_col, end_col = _range_bounds(range_ref)
    cells: List[str] = []
    for row in range(start_row, end_row + 1):
        for col in range(start_col, end_col + 1):
            cells.append(_cell_address(row, col))
    return cells


def _column_label(index: int) -> str:
    if index < 0:
        raise ValueError(f"Column index must be non-negative: {index}")
    label = ""
    while index >= 0:
        index, remainder = divmod(index, 26)
        label = chr(65 + remainder) + label
        index -= 1
    return label


def _cell_address(row_index: int, col_index: int) -> str:
    return f"{_column_label(col_index)}{row_index + 1}"


def _fetch_snapshot_rows(
    snapshot_batch_id: str,
    spreadsheet_id: str,
    gid: Optional[int],
) -> List[Dict[str, Any]]:
    params = {
        "select": "cell,red,green,blue",
        "snapshot_batch_id": f"eq.{snapshot_batch_id}",
        "spreadsheet_id": f"eq.{spreadsheet_id}",
    }
    if gid is None:
        params["gid"] = "is.null"
    else:
        params["gid"] = f"eq.{gid}"
    query = urllib.parse.urlencode(params, doseq=True)
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/cell_color_snapshots?{query}"

    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request) as response:
            if response.status != 200:
                raise RuntimeError(f"Unexpected Supabase status: {response.status}")
            payload = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Supabase fetch failed: {exc.status} {body}") from exc

    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise RuntimeError("Supabase response malformed; expected a list.")
    return rows


def _build_repeat_cell(sheet_id: int, row: int, col: int, color: Color) -> Dict[str, Any]:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row,
                "endRowIndex": row + 1,
                "startColumnIndex": col,
                "endColumnIndex": col + 1,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {
                        "red": float(color["red"]),
                        "green": float(color["green"]),
                        "blue": float(color["blue"]),
                    },
                }
            },
            "fields": "userEnteredFormat.backgroundColor",
        }
    }


def main() -> None:
    snapshot_batch_id, json_path = _parse_args()

    expected_cells = None
    if json_path:
        expected_cells = set(_load_expected_cells(json_path))

    url_id_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", DEFAULT_SPREADSHEET_URL)
    url_gid_match = re.search(r"[?&]gid=(\d+)", DEFAULT_SPREADSHEET_URL)
    spreadsheet_id = url_id_match.group(1) if url_id_match else DEFAULT_SPREADSHEET_URL
    gid = int(url_gid_match.group(1)) if url_gid_match else None

    validator = GoogleSheetsFormulaValidator(DEFAULT_CREDENTIALS_PATH)
    spreadsheet = validator.fetch_spreadsheet(spreadsheet_id)
    sheets = spreadsheet.get("sheets", [])
    if not sheets:
        raise ValueError("No sheets available in spreadsheet.")

    sheet = None
    if gid is None:
        sheet = sheets[0]
    else:
        for candidate in sheets:
            if candidate["properties"].get("sheetId") == gid:
                sheet = candidate
                break
    if sheet is None:
        raise ValueError(f"No sheet found with gid={gid}.")

    sheet_props = sheet["properties"]
    sheet_id = sheet_props["sheetId"]
    sheet_title = sheet_props["title"]

    snapshot_rows = _fetch_snapshot_rows(snapshot_batch_id, spreadsheet_id, gid)
    if not snapshot_rows:
        raise ValueError(f"No snapshot rows found for batch id '{snapshot_batch_id}'.")

    if expected_cells is not None:
        missing = expected_cells - {row["cell"] for row in snapshot_rows}
        if missing:
            raise ValueError(f"Snapshot missing {len(missing)} cell(s): {sorted(missing)}")

    requests: List[Dict[str, Any]] = []
    for row in snapshot_rows:
        cell = row.get("cell")
        if not isinstance(cell, str):
            raise ValueError("Snapshot row missing 'cell'.")
        red = row.get("red")
        green = row.get("green")
        blue = row.get("blue")
        if not all(isinstance(v, (int, float)) for v in (red, green, blue)):
            raise ValueError(f"Snapshot row for '{cell}' has invalid color values.")
        row_index, col_index = _parse_cell(cell)
        requests.append(
            _build_repeat_cell(
                sheet_id,
                row_index,
                col_index,
                {"red": float(red), "green": float(green), "blue": float(blue)},
            )
        )

    validator.service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()

    print(
        f"Restored {len(requests)} cell color(s) on '{sheet_title}' from snapshot batch '{snapshot_batch_id}'."
    )


if __name__ == "__main__":
    main()


