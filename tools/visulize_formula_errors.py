"""
# * Color-code cells with formula issues detected by GoogleSheetsFormulaValidator.
"""

import re
import sys
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

load_dotenv()

Color = Dict[str, float]

# * Severity colors (0-1 RGB as expected by Sheets API)
SEVERITY_COLORS: Dict[str, Color] = {
    "error": {"red": 0.95, "green": 0.45, "blue": 0.45},
    "warning": {"red": 0.98, "green": 0.8, "blue": 0.45},
    "info": {"red": 0.7, "green": 0.85, "blue": 0.98},
}


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


def main() -> None:
    """# * Entry point for coloring formula issues."""
    url_id_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", DEFAULT_SPREADSHEET_URL)
    url_gid_match = re.search(r"[?&]gid=(\d+)", DEFAULT_SPREADSHEET_URL)
    spreadsheet_id = url_id_match.group(1) if url_id_match else DEFAULT_SPREADSHEET_URL
    gid = int(url_gid_match.group(1)) if url_gid_match else None

    validator = GoogleSheetsFormulaValidator(DEFAULT_CREDENTIALS_PATH)
    spreadsheet = validator.fetch_spreadsheet(spreadsheet_id)
    sheet = _resolve_sheet(spreadsheet, gid)

    sheet_name = sheet["properties"]["title"]
    sheet_id = sheet["properties"]["sheetId"]

    formulas = validator.get_formulas(spreadsheet_id, sheet_name)
    issues = validator.analyze_formulas(formulas)
    if not issues:
        print("No issues detected; nothing to visualize.")
        return

    requests: List[Dict[str, Any]] = []
    for issue in issues:
        row_idx, col_idx = _cell_to_indices(issue.cell)
        color = SEVERITY_COLORS.get(issue.severity, SEVERITY_COLORS["info"])
        requests.append(_build_request(sheet_id, row_idx, col_idx, color, issue.message))

    validator.service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()

    print(f"Colored {len(requests)} formula issue(s) on '{sheet_name}'.")


if __name__ == "__main__":
    main()

