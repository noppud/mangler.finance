"""
# * Color-code cells with formulas or hard-coded numeric values.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

# * Ensure project root modules are importable when run from tools directory
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

# * Visualization colors
FORMULA_COLOR: Color = {"red": 0.75, "green": 0.92, "blue": 0.75}  # light green
VALUE_COLOR: Color = {"red": 0.98, "green": 0.8, "blue": 0.5}      # light orange

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")


@dataclass
class SheetCell:
    cell: str
    has_formula: bool
    has_numeric_constant: bool
    color: Color


def _resolve_sheet(spreadsheet: Dict[str, Any], gid: Optional[int]) -> Dict[str, Any]:
    sheets = spreadsheet.get("sheets", [])
    if not sheets:
        raise ValueError("No sheets found in spreadsheet.")
    if gid is None:
        return sheets[0]
    for sheet in sheets:
        if sheet["properties"].get("sheetId") == gid:
            return sheet
    raise ValueError(f"No sheet found with gid={gid}.")


def _cell_to_indices(cell: str) -> Tuple[int, int]:
    match = re.fullmatch(r"([A-Z]+)(\d+)", cell.strip().upper())
    if not match:
        raise ValueError(f"Invalid cell reference '{cell}'.")
    col_letters, row_digits = match.groups()
    row_index = int(row_digits) - 1
    if row_index < 0:
        raise ValueError(f"Row index must be positive in '{cell}'.")
    col_index = 0
    for char in col_letters:
        col_index = col_index * 26 + (ord(char) - ord("A") + 1)
    col_index -= 1
    return row_index, col_index


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


def _build_request(sheet_id: int, row: int, col: int, color: Color, note: str) -> Dict[str, Any]:
    cell_payload: Dict[str, Any] = {
        "userEnteredFormat": {
            "backgroundColor": color,
        },
    }
    fields = "userEnteredFormat.backgroundColor"
    if note:
        cell_payload["note"] = note
        fields += ",note"
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row,
                "endRowIndex": row + 1,
                "startColumnIndex": col,
                "endColumnIndex": col + 1,
            },
            "cell": cell_payload,
            "fields": fields,
        }
    }


def _normalize_color(cell_data: Dict[str, Any]) -> Color:
    fmt = cell_data.get("userEnteredFormat") or cell_data.get("effectiveFormat") or {}
    color = fmt.get("backgroundColor") or {}
    red = float(color.get("red", 1.0) or 0.0)
    green = float(color.get("green", 1.0) or 0.0)
    blue = float(color.get("blue", 1.0) or 0.0)
    return {"red": red, "green": green, "blue": blue}


def _fetch_target_cells(
    validator: GoogleSheetsFormulaValidator,
    spreadsheet_id: str,
    sheet_title: str,
) -> List[SheetCell]:
    quoted_title = sheet_title.replace("'", "''")
    response = validator.service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        includeGridData=True,
        ranges=[f"'{quoted_title}'"],
        fields="sheets(data(startRow,startColumn,rowData(values(userEnteredValue,userEnteredFormat,effectiveFormat))),properties(sheetId,title))",
    ).execute()

    sheets_data = response.get("sheets", [])
    if not sheets_data:
        return []

    data_blocks = sheets_data[0].get("data", [])
    targets: List[SheetCell] = []

    for block in data_blocks:
        start_row = block.get("startRow", 0)
        start_col = block.get("startColumn", 0)
        for row_offset, row_entry in enumerate(block.get("rowData", [])):
            values = row_entry.get("values", [])
            for col_offset, cell_entry in enumerate(values):
                user_value = cell_entry.get("userEnteredValue") or {}
                has_formula = "formulaValue" in user_value
                has_numeric_constant = "numberValue" in user_value and not has_formula
                if not has_formula and not has_numeric_constant:
                    continue
                row_index = start_row + row_offset
                col_index = start_col + col_offset
                cell_label = _cell_address(row_index, col_index)
                targets.append(
                    SheetCell(
                        cell=cell_label,
                        has_formula=has_formula,
                        has_numeric_constant=has_numeric_constant,
                        color=_normalize_color(cell_entry),
                    )
                )
    return targets


def _post_snapshot_rows(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured.")

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


def visualize_formulas(sheet_url: Optional[str] = None) -> Dict[str, Any]:
    """# * Color-code formulas and hard-coded values on the target sheet."""
    target_url = (sheet_url or DEFAULT_SPREADSHEET_URL or "").strip()
    if not target_url:
        raise ValueError("Sheet URL is required.")

    url_id_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", target_url)
    url_gid_match = re.search(r"[?&]gid=(\d+)", target_url)
    spreadsheet_id = url_id_match.group(1) if url_id_match else target_url
    gid = int(url_gid_match.group(1)) if url_gid_match else None

    validator = GoogleSheetsFormulaValidator(DEFAULT_CREDENTIALS_PATH)
    spreadsheet = validator.fetch_spreadsheet(spreadsheet_id)
    sheet = _resolve_sheet(spreadsheet, gid)

    sheet_name = sheet["properties"]["title"]
    sheet_id = sheet["properties"]["sheetId"]

    targets = _fetch_target_cells(validator, spreadsheet_id, sheet_name)
    if not targets:
        return {
            "status": "no_cells",
            "message": f"No formulas or hard-coded values detected on '{sheet_name}'.",
            "count": 0,
            "snapshot_batch_id": None,
        }

    snapshot_batch_id = str(uuid.uuid4())
    rows_to_insert: List[Dict[str, Any]] = [
        {
            "snapshot_batch_id": snapshot_batch_id,
            "spreadsheet_id": spreadsheet_id,
            "gid": gid,
            "cell": cell.cell,
            "red": float(cell.color["red"]),
            "green": float(cell.color["green"]),
            "blue": float(cell.color["blue"]),
        }
        for cell in targets
    ]
    _post_snapshot_rows(rows_to_insert)

    requests: List[Dict[str, Any]] = []
    for cell in targets:
        row_idx, col_idx = _cell_to_indices(cell.cell)
        color = FORMULA_COLOR if cell.has_formula else VALUE_COLOR
        requests.append(_build_request(sheet_id, row_idx, col_idx, color, ""))

    validator.service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()

    return {
        "status": "success",
        "message": f"Colored {len(requests)} cell(s) on '{sheet_name}' "
        "(formulas → green, values → orange).",
        "count": len(requests),
        "snapshot_batch_id": snapshot_batch_id,
    }


def main() -> None:
    """# * Entry point for coloring formula issues."""
    result = visualize_formulas()
    print(result["message"])


if __name__ == "__main__":
    main()