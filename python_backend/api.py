from __future__ import annotations

import json
import os
import re
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .backend import PythonChatBackend
from .memory import ConversationStore
from .models import ChatRequest, ChatResponse
from .service import ChatService

# * Tool imports
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.google_sheets import (
    DEFAULT_CREDENTIALS_PATH,
    DEFAULT_SPREADSHEET_URL,
    GoogleSheetsFormulaValidator,
)

# * Environment
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

# * Constants
Color = Dict[str, float]
WHITE: Color = {"red": 1.0, "green": 1.0, "blue": 1.0}

# * Lazy initialization - only create when chat endpoint is called
store = None
backend = None
service = None

app = FastAPI(title="Sheet Mangler Chat API (Python Frontend)")


def _init_chat_service() -> ChatService:
    """Lazily initialize chat service on first use."""
    global store, backend, service
    if service is None:
        store = ConversationStore()
        backend = PythonChatBackend()
        service = ChatService(backend=backend, store=store)
    return service


# * ============================================================================
# * Pydantic Models for Tool APIs
# * ============================================================================

class ColorRequest(BaseModel):
    """Request to apply colors to cells based on JSON input."""
    cell_location: str
    message: str
    color: str  # hex color like #FF0000


class RestoreRequest(BaseModel):
    """Request to restore colors from Supabase snapshot."""
    snapshot_batch_id: str
    cell_locations: Optional[List[str]] = None


# * ============================================================================
# * Chat Endpoint
# * ============================================================================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
  """
  Single chat endpoint that mirrors the existing /api/chat contract.

  For now this proxies to the Next.js backend while adding conversation
  memory keyed by sessionId.
  """
  # This implementation assumes the client is sending the full message history.
  # If you prefer CLI-style incremental messages, use ChatService.simple_chat
  # directly or adapt this endpoint accordingly.
  svc = _init_chat_service()
  return svc.chat(request)


# * ============================================================================
# * Color Tool Endpoints
# * ============================================================================

def _hex_color_to_rgb(value: str) -> Color:
    """Convert hex color to RGB (0-1 range)."""
    match = re.fullmatch(r"#?([0-9A-Fa-f]{6})", value)
    if not match:
        raise ValueError(f"Invalid hex color '{value}'.")
    hex_value = match.group(1)
    red = int(hex_value[0:2], 16) / 255.0
    green = int(hex_value[2:4], 16) / 255.0
    blue = int(hex_value[4:6], 16) / 255.0
    return {"red": red, "green": green, "blue": blue}


def _column_to_index(label: str) -> int:
    """Convert column letter to index."""
    if not re.fullmatch(r"[A-Z]+", label):
        raise ValueError(f"Invalid column label '{label}'.")
    index = 0
    for char in label:
        index = index * 26 + (ord(char) - 64)
    return index - 1


def _parse_cell(cell: str) -> tuple[int, int]:
    """Parse cell reference into row and column indices."""
    match = re.fullmatch(r"([A-Z]+)(\d+)", cell)
    if not match:
        raise ValueError(f"Invalid cell reference '{cell}'.")
    column = _column_to_index(match.group(1))
    row = int(match.group(2)) - 1
    if row < 0:
        raise ValueError(f"Row index must be positive in '{cell}'.")
    return row, column


def _range_to_bounds(range_ref: str) -> tuple[int, int, int, int]:
    """Convert range reference to start/end row/col bounds."""
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
    """Get sheet from spreadsheet, optionally by gid."""
    sheets = spreadsheet.get("sheets", [])
    if not sheets:
        raise ValueError("No sheets available in spreadsheet.")
    if gid is None:
        return sheets[0]
    for sheet in sheets:
        if sheet["properties"].get("sheetId") == gid:
            return sheet
    raise ValueError(f"No sheet found with gid={gid}.")


def _build_color_request(sheet_id: int, cell_location: str, color: Color, note: str) -> Dict[str, Any]:
    """Build batch update request for cell coloring."""
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


@app.post("/tools/color")
async def apply_colors(requests: List[ColorRequest]) -> Dict[str, Any]:
    """Apply background colors to cells in spreadsheet.
    
    Automatically snapshots current colors BEFORE applying new colors,
    allowing for restoration via /tools/restore endpoint.
    """
    try:
        if not requests:
            raise ValueError("No color requests provided.")

        url_id_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", DEFAULT_SPREADSHEET_URL)
        url_gid_match = re.search(r"[?&]gid=(\d+)", DEFAULT_SPREADSHEET_URL)
        spreadsheet_id = url_id_match.group(1) if url_id_match else DEFAULT_SPREADSHEET_URL
        gid = int(url_gid_match.group(1)) if url_gid_match else None

        validator = GoogleSheetsFormulaValidator(DEFAULT_CREDENTIALS_PATH)
        spreadsheet = validator.fetch_spreadsheet(spreadsheet_id)
        sheet = _resolve_sheet(spreadsheet, gid)
        sheet_props = sheet["properties"]
        sheet_title = sheet_props["title"]

        # * STEP 1: Snapshot current colors BEFORE applying new ones
        cell_ranges = list(set(req.cell_location for req in requests))
        rows_to_insert: List[Dict[str, Any]] = []
        
        for range_ref in cell_ranges:
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
        
        if rows_to_insert:
            _post_to_supabase(rows_to_insert)

        # * Get first snapshot batch ID for response
        first_snapshot_batch_id = None
        if cell_ranges:
            first_range = cell_ranges[0]
            first_snapshot_batch_id = str(uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{spreadsheet_id}:{gid}:{first_range}",
            ))

        # * STEP 2: Apply the new colors
        batch_requests = [
            _build_color_request(sheet_props["sheetId"], req.cell_location, _hex_color_to_rgb(req.color), req.message)
            for req in requests
        ]

        validator.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": batch_requests},
        ).execute()

        return {
            "status": "success",
            "message": f"Colored {len(batch_requests)} range(s) on '{sheet_props['title']}'.",
            "count": len(batch_requests),
            "snapshot_batch_id": first_snapshot_batch_id,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# * ============================================================================
# * Helper Functions for Snapshot & Restore
# * ============================================================================

def _column_index(label: str) -> int:
    """Convert column letter to index."""
    if not re.fullmatch(r"[A-Z]+", label):
        raise ValueError(f"Invalid column label '{label}'.")
    index = 0
    for char in label:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _column_label(index: int) -> str:
    """Convert column index to letter."""
    if index < 0:
        raise ValueError(f"Column index must be non-negative: {index}")
    label = ""
    while index >= 0:
        index, remainder = divmod(index, 26)
        label = chr(65 + remainder) + label
        index -= 1
    return label


def _cell_address(row_index: int, col_index: int) -> str:
    """Build cell address from row and column indices."""
    return f"{_column_label(col_index)}{row_index + 1}"


def _range_bounds(range_ref: str) -> tuple[int, int, int, int]:
    """Get start/end row/col bounds from range reference."""
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
    """Expand range into individual cell addresses."""
    start_row, end_row, start_col, end_col = _range_bounds(range_ref)
    cells: List[str] = []
    for row in range(start_row, end_row + 1):
        for col in range(start_col, end_col + 1):
            cells.append(_cell_address(row, col))
    return cells


def _normalize_color(cell_data: Optional[Dict[str, Any]]) -> Color:
    """Extract and normalize color from cell data."""
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
    """Fetch colors for a range from Google Sheets."""
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


def _post_to_supabase(rows: List[Dict[str, Any]]) -> None:
    """Send color snapshot rows to Supabase."""
    if not rows:
        raise ValueError("No rows to persist to Supabase.")

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


# * ============================================================================
# * Restore Tool Endpoints
# * ============================================================================

def _fetch_snapshot_rows(
    snapshot_batch_id: str,
    spreadsheet_id: str,
    gid: Optional[int],
) -> List[Dict[str, Any]]:
    """Fetch color snapshot rows from Supabase."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured.")

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
    """Build batch update request for cell color restoration."""
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
                },
                "note": "",  # * Clear any existing note/comment on this cell
            },
            "fields": "userEnteredFormat.backgroundColor,note",
        }
    }


@app.post("/tools/restore")
async def restore_colors(request: RestoreRequest) -> Dict[str, Any]:
    """Restore colors from Supabase snapshot."""
    try:
        snapshot_batch_id = request.snapshot_batch_id
        expected_cells = None
        if request.cell_locations:
            expected_cells = set()
            for range_ref in request.cell_locations:
                expected_cells.update(_expand_range(range_ref))

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

        return {
            "status": "success",
            "message": f"Restored {len(requests)} cell color(s) on '{sheet_title}' from snapshot batch.",
            "count": len(requests),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

