"""
# * Snapshot background colors for cells listed in an input JSON and store them in Supabase.
"""

import json
import os
import re
import sys
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

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

WHITE: Color = {"red": 1.0, "green": 1.0, "blue": 1.0}

# * Environment configuration (must exist; fail fast if missing)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
if not SUPABASE_URL:
    raise SystemExit("SUPABASE_URL must be defined in environment or .env file.")
if not SUPABASE_SERVICE_KEY:
    raise SystemExit("SUPABASE_SERVICE_KEY must be defined in environment or .env file.")


def _parse_args() -> Path:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python snapshot_input_colors.py /absolute/path/to/input.json")

    input_path = Path(sys.argv[1]).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"No input file found at {input_path}")
    return input_path


def _load_cell_ranges(input_path: Path) -> List[str]:
    payload = json.loads(input_path.read_text())
    potential_errors = payload.get("potential_errors")
    if not isinstance(potential_errors, list) or not potential_errors:
        raise ValueError("Input JSON must contain a non-empty 'potential_errors' list.")

    ranges: List[str] = []
    for idx, entry in enumerate(potential_errors):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry #{idx} is not an object.")
        cell_location = entry.get("cell_location")
        if not isinstance(cell_location, str) or not cell_location.strip():
            raise ValueError(f"Entry #{idx} missing 'cell_location'.")
        ranges.append(cell_location.strip().upper())
    return ranges


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


def _normalize_color(cell_data: Optional[Dict[str, Any]]) -> Color:
    if not cell_data:
        return WHITE
    fmt = cell_data.get("userEnteredFormat")
    if not isinstance(fmt, dict):
        return WHITE
    color = fmt.get("backgroundColor")
    if not isinstance(color, dict):
        return WHITE
    red = float(color.get("red", 1.0) or 0.0)
    green = float(color.get("green", 1.0) or 0.0)
    blue = float(color.get("blue", 1.0) or 0.0)
    return {"red": red, "green": green, "blue": blue}


def _fetch_colors_for_range(
    validator: GoogleSheetsFormulaValidator,
    spreadsheet_id: str,
    sheet_title: str,
    range_ref: str,
) -> Dict[str, Color]:
    sheet_range = f"'{sheet_title}'!{range_ref}"
    response = validator.service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        ranges=[sheet_range],
        includeGridData=True,
        fields="sheets(data(rowData(values(userEnteredFormat.backgroundColor)))),sheets(properties(sheetId,title))",
    ).execute()

    start_row, end_row, start_col, end_col = _range_bounds(range_ref)
    colors: Dict[str, Color] = {}

    sheets_data = response.get("sheets", [])
    if not sheets_data:
        return colors

    data_blocks = sheets_data[0].get("data", [])
    if not data_blocks:
        return colors

    row_data = data_blocks[0].get("rowData", [])
    for row_offset, row_entry in enumerate(row_data):
        values = row_entry.get("values", [])
        for col_offset, cell_entry in enumerate(values):
            row_index = start_row + row_offset
            col_index = start_col + col_offset
            cell_label = _cell_address(row_index, col_index)
            colors[cell_label] = _normalize_color(cell_entry)

    return colors


def _iter_cells(ranges: Iterable[str]) -> Iterable[str]:
    seen = set()
    for range_ref in ranges:
        for cell in _expand_range(range_ref):
            if cell not in seen:
                seen.add(cell)
                yield cell


def _post_to_supabase(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("No rows to persist to Supabase.")

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/cell_color_snapshots"
    request = urllib.request.Request(
        url,
        method="POST",
        data=json.dumps(rows).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Prefer": "resolution=merge-duplicates",
        },
    )

    try:
        with urllib.request.urlopen(request) as response:
            if response.status not in (200, 201, 204):
                raise RuntimeError(f"Unexpected Supabase status: {response.status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Supabase insert failed: {exc.status} {body}") from exc


def main() -> None:
    input_path = _parse_args()
    ranges = _load_cell_ranges(input_path)

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
    sheet_title = sheet_props["title"]

    rows_to_insert: List[Dict[str, Any]] = []
    for range_ref in ranges:
        snapshot_batch_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{spreadsheet_id}:{gid}:{range_ref}",
        )
        colors_by_cell = _fetch_colors_for_range(validator, spreadsheet_id, sheet_title, range_ref)
        for cell in _expand_range(range_ref):
            color = colors_by_cell.get(cell, WHITE)
            rows_to_insert.append(
                {
                    "snapshot_batch_id": str(snapshot_batch_id),
                    "spreadsheet_id": spreadsheet_id,
                    "gid": gid,
                    "cell": cell,
                    "red": float(color["red"]),
                    "green": float(color["green"]),
                    "blue": float(color["blue"]),
                }
            )

    _post_to_supabase(rows_to_insert)

    total_cells = len(rows_to_insert)
    total_batches = len(ranges)
    print(f"Stored {total_cells} cell color snapshot(s) across {total_batches} batch id(s).")
    
    # * Print first snapshot batch ID for test_run.py to capture
    if ranges:
        first_range = ranges[0]
        first_snapshot_batch_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{spreadsheet_id}:{gid}:{first_range}",
        )
        print(f"Snapshot batch ID: {first_snapshot_batch_id}")


if __name__ == "__main__":
    main()


