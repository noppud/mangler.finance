"""
# * Revert all cells in the spreadsheet to white (baseline color).
"""

import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# * Ensure the project root is importable even when run elsewhere
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.google_sheets import (
    DEFAULT_CREDENTIALS_PATH,
    DEFAULT_SPREADSHEET_URL,
    GoogleSheetsFormulaValidator,
)

load_dotenv()

WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}


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


def main() -> None:
    url_id_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", DEFAULT_SPREADSHEET_URL)
    url_gid_match = re.search(r"[?&]gid=(\d+)", DEFAULT_SPREADSHEET_URL)
    spreadsheet_id = url_id_match.group(1) if url_id_match else DEFAULT_SPREADSHEET_URL
    gid = int(url_gid_match.group(1)) if url_gid_match else None

    validator = GoogleSheetsFormulaValidator(DEFAULT_CREDENTIALS_PATH)
    spreadsheet = validator.fetch_spreadsheet(spreadsheet_id)
    sheet = _resolve_sheet(spreadsheet, gid)
    sheet_props = sheet["properties"]
    sheet_id = sheet_props["sheetId"]
    sheet_title = sheet_props["title"]

    # * ! Fallback: Reset entire sheet to white (clears all formatting)
    request = {
        "updateCells": {
            "range": {
                "sheetId": sheet_id,
            },
            "fields": "userEnteredFormat.backgroundColor",
            "rows": [],  # * Empty rows = clear formatting
        }
    }

    # TODO: Consider if we need a more granular approach (only revert specific ranges)
    validator.service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [request]},
    ).execute()

    print(f"Reverted '{sheet_title}' to white baseline.")


if __name__ == "__main__":
    main()
