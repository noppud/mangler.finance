from __future__ import annotations

import json
import os
import re
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .backend import PythonChatBackend
from .logging_config import get_logger
from .memory import ConversationStore
from .models import ChatRequest, ChatResponse
from .service import ChatService
from .sheets_client import ServiceAccountSheetsClient

# Initialize logger
logger = get_logger(__name__)

# * Tool imports
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from tools.google_sheets import (
        DEFAULT_CREDENTIALS_PATH,
        DEFAULT_SPREADSHEET_URL,
        GoogleSheetsFormulaValidator,
    )
except ImportError:  # pragma: no cover - optional tools
    DEFAULT_CREDENTIALS_PATH = None  # type: ignore[assignment]
    DEFAULT_SPREADSHEET_URL = ""  # type: ignore[assignment]
    GoogleSheetsFormulaValidator = None  # type: ignore[assignment]

# * Environment
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Allow environment variables to override tool defaults when available.
if DEFAULT_CREDENTIALS_PATH is None:
    env_credentials = os.environ.get("DEFAULT_CREDENTIALS_PATH") or os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if env_credentials:
        DEFAULT_CREDENTIALS_PATH = Path(env_credentials)
elif isinstance(DEFAULT_CREDENTIALS_PATH, str):
    DEFAULT_CREDENTIALS_PATH = Path(DEFAULT_CREDENTIALS_PATH)

env_spreadsheet = os.environ.get("DEFAULT_SPREADSHEET_URL") or os.environ.get("SPREADSHEET_URL")
if env_spreadsheet:
    DEFAULT_SPREADSHEET_URL = env_spreadsheet
else:
    DEFAULT_SPREADSHEET_URL = DEFAULT_SPREADSHEET_URL or ""

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

_sheets_service = None


class _SheetsServiceWrapper:
    """Adapter to provide the minimal interface expected by the tool endpoints."""

    def __init__(self, client: ServiceAccountSheetsClient) -> None:
        self._client = client
        self.service = client.service

    def fetch_spreadsheet(self, spreadsheet_id: str) -> Dict[str, Any]:
        return self.service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
        ).execute()


def _get_sheets_service():
    """
    Attempt to initialize a Google Sheets API helper.

    Prefers the TypeScript tool helper (if available) and falls back to the
    Python ServiceAccountSheetsClient so the /tools endpoints still function
    even if the optional tools package is missing.
    """
    global _sheets_service

    if _sheets_service is not None:
        return _sheets_service

    if GoogleSheetsFormulaValidator is not None and DEFAULT_CREDENTIALS_PATH:
        try:
            _sheets_service = GoogleSheetsFormulaValidator(DEFAULT_CREDENTIALS_PATH)
            logger.info("Using GoogleSheetsFormulaValidator for sheet tools")
            return _sheets_service
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                f"Failed to initialize GoogleSheetsFormulaValidator: {exc}",
                exc_info=True,
            )

    try:
        credentials_input = str(DEFAULT_CREDENTIALS_PATH) if DEFAULT_CREDENTIALS_PATH else None
        client = ServiceAccountSheetsClient(credentials_input)
        _sheets_service = _SheetsServiceWrapper(client)
        logger.info("Falling back to ServiceAccountSheetsClient for sheet tools")
        return _sheets_service
    except Exception as exc:
        logger.error(
            f"Unable to initialize any Google Sheets client: {exc}",
            exc_info=True,
        )
        return None


# * ============================================================================
# * Request/Response Logging Middleware
# * ============================================================================

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    Middleware to log all HTTP requests and responses.
    Adds request_id for tracing and logs timing information.
    Robust error handling to prevent middleware crashes.
    """
    # Generate unique request ID for tracing
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    # Safely extract request info
    try:
        method = str(request.method) if request.method else "UNKNOWN"
        path = str(request.url.path) if request.url and request.url.path else "/unknown"
        query_params = dict(request.query_params) if request.query_params else {}
        client_host = request.client.host if request.client else None
    except Exception:
        method = "UNKNOWN"
        path = "/unknown"
        query_params = {}
        client_host = None

    # Log incoming request (with fallback)
    try:
        logger.info(
            f"→ {method} {path}",
            extra={
                "request_id": request_id,
                "method": method,
                "endpoint": path,
                "query_params": query_params,
                "client": client_host,
            }
        )
    except Exception:
        # Fallback: simple log without extra fields
        try:
            logger.info(f"→ {method} {path}")
        except Exception:
            pass  # Give up silently to prevent middleware crash

    # Process request and handle errors
    try:
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)

        # Safely get status code
        try:
            status_code = int(response.status_code) if hasattr(response, 'status_code') else 200
        except Exception:
            status_code = 200

        # Log response (with fallback)
        try:
            log_level = logger.info if status_code < 400 else logger.error
            log_level(
                f"← {method} {path} - {status_code} ({duration_ms}ms)",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "endpoint": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                }
            )
        except Exception:
            # Fallback: simple log without extra fields
            try:
                logger.info(f"← {method} {path} - {status_code} ({duration_ms}ms)")
            except Exception:
                pass  # Give up silently

        return response

    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)

        # Log error (with fallback)
        try:
            logger.error(
                f"✗ {method} {path} - Exception ({duration_ms}ms)",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "method": method,
                    "endpoint": path,
                    "duration_ms": duration_ms,
                }
            )
        except Exception:
            # Fallback: simple error log
            try:
                logger.error(f"✗ {method} {path} - Exception", exc_info=True)
            except Exception:
                pass  # Give up silently

        # Re-raise to let FastAPI handle it
        raise


# * ============================================================================
# * Initialization Functions
# * ============================================================================

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
    url: str  # Spreadsheet URL from Apps Script


class RestoreRequest(BaseModel):
    """Request to restore colors from Supabase snapshot."""
    snapshot_batch_id: str
    cell_locations: Optional[List[str]] = None


class CellUpdate(BaseModel):
    """Single cell update request."""
    cell_location: str  # A1 notation, e.g., "A1" or "B2:C5"
    value: Any  # New value - can be string, number, boolean, formula, or null
    is_formula: bool = False  # Set to True if value is a formula (e.g., "=SUM(A1:A10)")


class UpdateCellsRequest(BaseModel):
    """Request to update cell values in a spreadsheet."""
    updates: List[CellUpdate]
    spreadsheet_id: Optional[str] = None  # Optional: defaults to env SPREADSHEET_URL
    sheet_title: str = "Sheet1"  # Sheet name, defaults to Sheet1
    create_snapshot: bool = True  # Whether to snapshot current values for undo


class UpdateCellsResponse(BaseModel):
    """Response from cell update operation."""
    status: str
    message: str
    count: int
    snapshot_batch_id: Optional[str] = None
    failed_updates: Optional[List[Dict[str, str]]] = None


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
  logger.info(
      f"Chat request: {len(request.messages)} message(s), session={request.sessionId or '(new)'}",
      extra={
          "session_id": request.sessionId,
          "message_count": len(request.messages),
          "has_sheet_context": request.sheetContext is not None,
      }
  )

  # This implementation assumes the client is sending the full message history.
  # If you prefer CLI-style incremental messages, use ChatService.simple_chat
  # directly or adapt this endpoint accordingly.
  try:
      svc = _init_chat_service()
      response = svc.chat(request)
      logger.info(
          f"Chat response: {len(response.messages)} message(s), session={response.sessionId}",
          extra={
              "session_id": response.sessionId,
              "response_message_count": len(response.messages),
          }
      )
      return response
  except Exception as e:
      logger.error(
          f"Chat request failed: {str(e)}",
          exc_info=True,
          extra={"session_id": request.sessionId}
      )
      raise


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
    """Parse cell reference into row and column indices.

    Supports:
    - Standard cells: "A1" -> (0, 0)
    - Row-only: "2" -> (1, 0)
    - Column-only: "A" -> (0, 0)
    """
    # Try standard cell format first (e.g., "A1")
    match = re.fullmatch(r"([A-Z]+)(\d+)", cell)
    if match:
        column = _column_to_index(match.group(1))
        row = int(match.group(2)) - 1
        if row < 0:
            raise ValueError(f"Row index must be positive in '{cell}'.")
        return row, column

    # Try row-only format (e.g., "2")
    if re.fullmatch(r"\d+", cell):
        row = int(cell) - 1
        if row < 0:
            raise ValueError(f"Row index must be positive in '{cell}'.")
        return row, 0  # Column 0 as placeholder

    # Try column-only format (e.g., "A")
    if re.fullmatch(r"[A-Z]+", cell):
        column = _column_to_index(cell)
        return 0, column  # Row 0 as placeholder

    raise ValueError(f"Invalid cell reference '{cell}'.")


def _range_to_bounds(range_ref: str) -> tuple[int, int, int, int]:
    """Convert range reference to start/end row/col bounds.

    Supports:
    - Standard ranges: "A1:B10" -> (0, 10, 0, 2)
    - Single cells: "A1" -> (0, 1, 0, 1)
    - Whole rows: "2" or "2:5" -> entire row(s)
    - Whole columns: "A" or "A:C" -> entire column(s)
    """
    parts = range_ref.split(":")

    # Single cell/row/column
    if len(parts) == 1:
        cell = parts[0]

        # Check if it's a whole row (just a number)
        if re.fullmatch(r"\d+", cell):
            row = int(cell) - 1
            if row < 0:
                raise ValueError(f"Row index must be positive in '{cell}'.")
            # Whole row: columns 0 to 26 (Z) - use reasonable limit
            return row, row + 1, 0, 26

        # Check if it's a whole column (just letters)
        if re.fullmatch(r"[A-Z]+", cell):
            col = _column_to_index(cell)
            # Whole column: rows 0 to 1000 - use reasonable limit
            return 0, 1000, col, col + 1

        # Standard single cell
        start_row, start_col = _parse_cell(cell)
        return start_row, start_row + 1, start_col, start_col + 1

    # Range
    elif len(parts) == 2:
        start, end = parts

        # Check if it's a row range (e.g., "2:5")
        if re.fullmatch(r"\d+", start) and re.fullmatch(r"\d+", end):
            start_row = int(start) - 1
            end_row = int(end) - 1
            if start_row < 0 or end_row < 0:
                raise ValueError(f"Row indices must be positive in '{range_ref}'.")
            if end_row < start_row:
                raise ValueError(f"Range '{range_ref}' has inverted bounds.")
            # Whole rows: columns 0 to 26 (Z)
            return start_row, end_row + 1, 0, 26

        # Check if it's a column range (e.g., "A:C")
        if re.fullmatch(r"[A-Z]+", start) and re.fullmatch(r"[A-Z]+", end):
            start_col = _column_to_index(start)
            end_col = _column_to_index(end)
            if end_col < start_col:
                raise ValueError(f"Range '{range_ref}' has inverted bounds.")
            # Whole columns: rows 0 to 1000
            return 0, 1000, start_col, end_col + 1

        # Standard cell range
        start_row, start_col = _parse_cell(start)
        end_row, end_col = _parse_cell(end)
        if end_row < start_row or end_col < start_col:
            raise ValueError(f"Range '{range_ref}' has inverted bounds.")
        # Convert to exclusive upper bounds for Sheets API
        return start_row, end_row + 1, start_col, end_col + 1

    else:
        raise ValueError(f"Invalid range '{range_ref}'.")


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
    logger.info(f"Color request: {len(requests)} cell(s) to color")

    validator = _get_sheets_service()
    if validator is None:
        logger.error(
            "503 Service Unavailable: Color tools not available",
            extra={
                "has_validator": GoogleSheetsFormulaValidator is not None,
                "credentials_path": str(DEFAULT_CREDENTIALS_PATH) if DEFAULT_CREDENTIALS_PATH else "(missing)",
            }
        )
        raise HTTPException(
            status_code=503,
            detail="Color tools are not available on this deployment.",
        )

    try:
        if not requests:
            logger.warning("No color requests provided")
            raise ValueError("No color requests provided.")

        # Use URL from the first request (all requests should be for the same spreadsheet)
        spreadsheet_url = requests[0].url
        logger.info(f"Using spreadsheet URL from request: {spreadsheet_url}")

        url_id_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", spreadsheet_url)
        url_gid_match = re.search(r"[?&]gid=(\d+)", spreadsheet_url)

        if not url_id_match:
            logger.error(f"Invalid spreadsheet URL format: {spreadsheet_url}")
            raise ValueError(f"Invalid spreadsheet URL format: {spreadsheet_url}")

        spreadsheet_id = url_id_match.group(1)
        gid = int(url_gid_match.group(1)) if url_gid_match else None

        logger.info(f"Extracted spreadsheet_id: {spreadsheet_id}, gid: {gid}")

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

        logger.info(f"Applying colors to {len(batch_requests)} range(s)")
        validator.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": batch_requests},
        ).execute()

        logger.info(
            f"Successfully colored {len(batch_requests)} range(s)",
            extra={"count": len(batch_requests), "snapshot_batch_id": first_snapshot_batch_id}
        )

        return {
            "status": "success",
            "message": f"Colored {len(batch_requests)} range(s) on '{sheet_props['title']}'.",
            "count": len(batch_requests),
            "snapshot_batch_id": first_snapshot_batch_id,
        }
    except Exception as e:
        logger.error(f"Color request failed: {str(e)}", exc_info=True)
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
    """Get start/end row/col bounds from range reference (inclusive).

    Supports:
    - Standard ranges: "A1:B10"
    - Single cells: "A1"
    - Whole rows: "2" or "2:5"
    - Whole columns: "A" or "A:C"
    """
    parts = range_ref.split(":")

    # Single cell/row/column
    if len(parts) == 1:
        cell = parts[0]

        # Check if it's a whole row (just a number)
        if re.fullmatch(r"\d+", cell):
            row = int(cell) - 1
            if row < 0:
                raise ValueError(f"Row index must be positive in '{cell}'.")
            # Whole row: columns 0 to 25 (A-Z)
            return row, row, 0, 25

        # Check if it's a whole column (just letters)
        if re.fullmatch(r"[A-Z]+", cell):
            col = _column_to_index(cell)
            # Whole column: rows 0 to 999 (reasonable limit)
            return 0, 999, col, col

        # Standard single cell
        row, col = _parse_cell(cell)
        return row, row, col, col

    # Range
    elif len(parts) == 2:
        start, end = parts

        # Check if it's a row range (e.g., "2:5")
        if re.fullmatch(r"\d+", start) and re.fullmatch(r"\d+", end):
            start_row = int(start) - 1
            end_row = int(end) - 1
            if start_row < 0 or end_row < 0:
                raise ValueError(f"Row indices must be positive in '{range_ref}'.")
            if end_row < start_row:
                raise ValueError(f"Range '{range_ref}' has inverted bounds.")
            # Whole rows: columns 0 to 25 (A-Z)
            return start_row, end_row, 0, 25

        # Check if it's a column range (e.g., "A:C")
        if re.fullmatch(r"[A-Z]+", start) and re.fullmatch(r"[A-Z]+", end):
            start_col = _column_to_index(start)
            end_col = _column_to_index(end)
            if end_col < start_col:
                raise ValueError(f"Range '{range_ref}' has inverted bounds.")
            # Whole columns: rows 0 to 999
            return 0, 999, start_col, end_col

        # Standard cell range
        start_row, start_col = _parse_cell(start)
        end_row, end_col = _parse_cell(end)
        if end_row < start_row or end_col < start_col:
            raise ValueError(f"Range '{range_ref}' has inverted bounds.")
        return start_row, end_row, start_col, end_col

    else:
        raise ValueError(f"Invalid range '{range_ref}'.")


def _expand_range(range_ref: str) -> List[str]:
    """Expand range into individual cell addresses.

    WARNING: For whole rows/columns, this can expand to many cells.
    We limit expansion to max 1000 cells to prevent memory issues.
    """
    start_row, end_row, start_col, end_col = _range_bounds(range_ref)

    # Calculate total cells
    num_rows = end_row - start_row + 1
    num_cols = end_col - start_col + 1
    total_cells = num_rows * num_cols

    # Limit expansion to prevent memory issues
    MAX_CELLS = 1000
    if total_cells > MAX_CELLS:
        logger.warning(
            f"Range '{range_ref}' expands to {total_cells} cells, limiting to {MAX_CELLS}"
        )
        # For large ranges, just return a sample of cells
        # This is mainly for logging/debugging - color API handles ranges natively
        cells: List[str] = []
        count = 0
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                if count >= MAX_CELLS:
                    break
                cells.append(_cell_address(row, col))
                count += 1
            if count >= MAX_CELLS:
                break
        return cells

    # Normal expansion
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
    validator: Any,
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
    validator = _get_sheets_service()
    if validator is None:
        raise HTTPException(
            status_code=503,
            detail="Color tools are not available on this deployment.",
        )

    try:
        snapshot_batch_id = request.snapshot_batch_id
        expected_cells = None
        if request.cell_locations:
            expected_cells = set()
            for range_ref in request.cell_locations:
                expected_cells.update(_expand_range(range_ref))

        # First, fetch snapshot rows to get spreadsheet_id and gid from the snapshot data
        logger.info(f"Fetching snapshot rows for batch_id: {snapshot_batch_id}")

        # We need to fetch without filtering by spreadsheet_id/gid first
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured.")

        params = {
            "select": "cell,red,green,blue,spreadsheet_id,gid",
            "snapshot_batch_id": f"eq.{snapshot_batch_id}",
            "limit": "1",  # Just get one row to extract spreadsheet_id and gid
        }
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/cell_color_snapshots?{query}"

        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    raise RuntimeError(f"Unexpected Supabase status: {response.status}")
                payload = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Supabase fetch failed: {exc.status} {body}") from exc

        sample_rows = json.loads(payload)
        if not isinstance(sample_rows, list) or not sample_rows:
            raise ValueError(f"No snapshot rows found for batch id '{snapshot_batch_id}'.")

        # Extract spreadsheet_id and gid from first row
        first_row = sample_rows[0]
        spreadsheet_id = first_row.get("spreadsheet_id")
        gid = first_row.get("gid")

        if not spreadsheet_id:
            raise ValueError("Snapshot is missing spreadsheet_id")

        logger.info(f"Extracted from snapshot: spreadsheet_id={spreadsheet_id}, gid={gid}")

        # Now fetch the full spreadsheet and sheet info
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

        # Now fetch all snapshot rows for this spreadsheet
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


# * ============================================================================
# * Cell Update Tool Endpoint
# * ============================================================================

def _fetch_cell_values(
    validator: Any,
    spreadsheet_id: str,
    sheet_title: str,
    cell_locations: List[str],
) -> Dict[str, Any]:
    """Fetch current values for cells to snapshot before update."""
    values_by_cell: Dict[str, Any] = {}

    for cell_loc in cell_locations:
        try:
            sheet_range = f"'{sheet_title}'!{cell_loc}"
            response = validator.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=sheet_range,
                valueRenderOption="UNFORMATTED_VALUE",
            ).execute()

            cell_values = response.get("values", [])

            # Handle single cell vs range
            if ":" in cell_loc:
                # It's a range - store the full 2D array
                values_by_cell[cell_loc] = cell_values
            else:
                # Single cell - extract the value
                if cell_values and cell_values[0]:
                    values_by_cell[cell_loc] = cell_values[0][0]
                else:
                    values_by_cell[cell_loc] = None
        except Exception:
            # Cell may be empty or out of bounds - treat as None
            values_by_cell[cell_loc] = None

    return values_by_cell


def _snapshot_cell_values(
    spreadsheet_id: str,
    gid: Optional[int],
    sheet_title: str,
    cell_locations: List[str],
    validator: Any,
) -> str:
    """Snapshot current cell values to Supabase before update."""
    snapshot_batch_id = str(uuid.uuid4())
    logger.debug(f"Fetching current values for {len(cell_locations)} cell(s)")
    values_by_cell = _fetch_cell_values(validator, spreadsheet_id, sheet_title, cell_locations)

    rows_to_insert: List[Dict[str, Any]] = []
    for cell_loc, value in values_by_cell.items():
        rows_to_insert.append({
            "snapshot_batch_id": snapshot_batch_id,
            "spreadsheet_id": spreadsheet_id,
            "gid": gid,
            "cell": cell_loc,
            "value": json.dumps(value) if value is not None else None,
            "snapshot_type": "cell_value",
        })

    if rows_to_insert:
        logger.debug(f"Posting {len(rows_to_insert)} snapshot row(s) to Supabase")
        _post_value_snapshot_to_supabase(rows_to_insert)
    else:
        logger.warning("No snapshot rows to insert")

    return snapshot_batch_id


def _post_value_snapshot_to_supabase(rows: List[Dict[str, Any]]) -> None:
    """Send cell value snapshot rows to Supabase."""
    if not rows:
        logger.error("No rows to persist to Supabase")
        raise ValueError("No rows to persist to Supabase.")

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error(
            "Supabase not configured for snapshots",
            extra={
                "has_url": bool(SUPABASE_URL),
                "has_key": bool(SUPABASE_SERVICE_KEY),
            }
        )
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured.")

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/cell_value_snapshots"
    logger.debug(f"Posting {len(rows)} row(s) to Supabase: {url}")

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
                logger.error(f"Unexpected Supabase response status: {response.status}")
                raise RuntimeError(f"Unexpected Supabase status: {response.status}")
            logger.debug(f"Successfully posted snapshot to Supabase: {response.status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        logger.error(
            f"Supabase insert failed: {exc.status}",
            exc_info=True,
            extra={"status_code": exc.status, "response_body": body}
        )
        raise RuntimeError(f"Supabase insert failed: {exc.status} {body}") from exc


@app.post("/tools/update_cells")
async def update_cells(request: UpdateCellsRequest) -> Dict[str, Any]:
    """
    Update cell values in a Google Spreadsheet with automatic snapshotting.

    Supports:
    - Batch updates (multiple cells at once)
    - Formulas and values
    - Single cells or ranges
    - Automatic snapshot for undo capability
    - Robust validation and error handling

    Example request:
    {
        "updates": [
            {"cell_location": "A1", "value": "Hello"},
            {"cell_location": "B2", "value": 42},
            {"cell_location": "C3", "value": "=SUM(A1:B2)", "is_formula": true},
            {"cell_location": "D4:E5", "value": "Batch"}
        ],
        "sheet_title": "Sheet1",
        "create_snapshot": true
    }
    """
    logger.info(
        f"Update cells request: {len(request.updates)} update(s) on sheet '{request.sheet_title}'",
        extra={
            "update_count": len(request.updates),
            "sheet_title": request.sheet_title,
            "spreadsheet_id": request.spreadsheet_id or "(default)",
            "create_snapshot": request.create_snapshot,
        }
    )

    # Check if tools are available
    validator = _get_sheets_service()
    if validator is None:
        logger.error(
            "503 Service Unavailable: Cell update tools not available",
            extra={
                "validator_available": GoogleSheetsFormulaValidator is not None,
                "credentials_available": DEFAULT_CREDENTIALS_PATH is not None,
                "credentials_path": str(DEFAULT_CREDENTIALS_PATH) if DEFAULT_CREDENTIALS_PATH else "(not set)",
            }
        )
        raise HTTPException(
            status_code=503,
            detail="Cell update tools are not available on this deployment.",
        )

    try:
        if not request.updates:
            logger.warning("No cell updates provided in request")
            raise ValueError("No cell updates provided.")

        # Parse spreadsheet ID and gid
        spreadsheet_url = request.spreadsheet_id or DEFAULT_SPREADSHEET_URL
        if not spreadsheet_url:
            logger.error("No spreadsheet URL/ID provided and no default configured")
            raise ValueError("No spreadsheet URL/ID provided and no default configured.")

        url_id_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", spreadsheet_url)
        url_gid_match = re.search(r"[?&]gid=(\d+)", spreadsheet_url)
        spreadsheet_id = url_id_match.group(1) if url_id_match else spreadsheet_url
        gid = int(url_gid_match.group(1)) if url_gid_match else None

        logger.debug(
            f"Parsed spreadsheet URL: id={spreadsheet_id}, gid={gid}",
            extra={"spreadsheet_id": spreadsheet_id, "gid": gid}
        )

        logger.debug(f"Fetching spreadsheet metadata for {spreadsheet_id}")
        spreadsheet = validator.fetch_spreadsheet(spreadsheet_id)
        logger.info(f"Successfully fetched spreadsheet: {spreadsheet_id}")

        # Resolve sheet - either by gid or by title
        sheet = None
        sheets = spreadsheet.get("sheets", [])
        if not sheets:
            logger.error("No sheets available in spreadsheet")
            raise ValueError("No sheets available in spreadsheet.")

        logger.debug(f"Resolving sheet '{request.sheet_title}' from {len(sheets)} available sheet(s)")

        # First try to find by title
        for candidate in sheets:
            if candidate["properties"]["title"] == request.sheet_title:
                sheet = candidate
                logger.debug(f"Found sheet by title: '{request.sheet_title}'")
                break

        # If not found by title and gid is provided, try gid
        if sheet is None and gid is not None:
            logger.debug(f"Sheet not found by title, trying gid={gid}")
            for candidate in sheets:
                if candidate["properties"].get("sheetId") == gid:
                    sheet = candidate
                    logger.debug(f"Found sheet by gid: {gid}")
                    break

        # If still not found, use first sheet and warn
        if sheet is None:
            sheet = sheets[0]
            actual_title = sheet["properties"]["title"]
            available_titles = [s["properties"]["title"] for s in sheets]
            if actual_title != request.sheet_title:
                logger.warning(
                    f"Sheet '{request.sheet_title}' not found, using first sheet '{actual_title}'",
                    extra={
                        "requested_sheet": request.sheet_title,
                        "used_sheet": actual_title,
                        "available_sheets": available_titles,
                    }
                )

        sheet_props = sheet["properties"]
        sheet_title = sheet_props["title"]

        logger.info(
            f"Resolved sheet: '{sheet_title}' (gid={sheet_props.get('sheetId')})",
            extra={"sheet_title": sheet_title, "sheet_id": sheet_props.get("sheetId")}
        )

        # STEP 1: Snapshot current values if requested
        snapshot_batch_id = None
        if request.create_snapshot:
            logger.info(f"Creating snapshot for {len(request.updates)} cell(s)")
            cell_locations = [update.cell_location for update in request.updates]
            snapshot_batch_id = _snapshot_cell_values(
                spreadsheet_id,
                gid,
                sheet_title,
                cell_locations,
                validator,
            )
            logger.info(f"Snapshot created: {snapshot_batch_id}")
        else:
            logger.debug("Skipping snapshot creation (create_snapshot=false)")

        # STEP 2: Apply updates using batch API
        batch_data: List[Dict[str, Any]] = []
        failed_updates: List[Dict[str, str]] = []

        logger.debug("Processing cell updates")
        for update in request.updates:
            try:
                cell_range = f"'{sheet_title}'!{update.cell_location}"

                # Determine value input option
                value_input_option = "USER_ENTERED" if update.is_formula else "RAW"

                # Handle None/null values
                if update.value is None:
                    value_to_write = [[""]]
                # Handle range updates (fill entire range with same value)
                elif ":" in update.cell_location:
                    start_row, end_row, start_col, end_col = _range_bounds(update.cell_location)
                    num_rows = end_row - start_row + 1
                    num_cols = end_col - start_col + 1
                    value_to_write = [[update.value] * num_cols for _ in range(num_rows)]
                else:
                    # Single cell
                    value_to_write = [[update.value]]

                batch_data.append({
                    "range": cell_range,
                    "values": value_to_write,
                })

            except Exception as e:
                logger.warning(
                    f"Failed to prepare update for {update.cell_location}: {str(e)}",
                    extra={"cell_location": update.cell_location, "error": str(e)}
                )
                failed_updates.append({
                    "cell_location": update.cell_location,
                    "error": str(e),
                })

        # Execute batch update if we have valid updates
        if batch_data:
            logger.info(f"Executing batch update for {len(batch_data)} cell(s)")
            validator.service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "valueInputOption": "USER_ENTERED",  # This allows formulas
                    "data": batch_data,
                },
            ).execute()
            logger.info(f"Batch update completed successfully")
        else:
            logger.warning("No valid updates to apply")

        success_count = len(batch_data)
        total_count = len(request.updates)

        if failed_updates:
            status = "partial_success" if success_count > 0 else "error"
            message = f"Updated {success_count}/{total_count} cells on '{sheet_title}'. {len(failed_updates)} failed."
            logger.warning(
                f"Cell update completed with failures: {success_count}/{total_count} succeeded",
                extra={
                    "success_count": success_count,
                    "failed_count": len(failed_updates),
                    "total_count": total_count,
                    "failed_cells": [f["cell_location"] for f in failed_updates],
                }
            )
        else:
            status = "success"
            message = f"Updated {success_count} cell(s) on '{sheet_title}'."
            logger.info(
                f"Cell update completed successfully: {success_count} cell(s) updated",
                extra={"success_count": success_count}
            )

        response_data = {
            "status": status,
            "message": message,
            "count": success_count,
        }

        if snapshot_batch_id:
            response_data["snapshot_batch_id"] = snapshot_batch_id

        if failed_updates:
            response_data["failed_updates"] = failed_updates

        return response_data

    except Exception as e:
        logger.error(
            f"Update cells failed: {str(e)}",
            exc_info=True,
            extra={
                "spreadsheet_id": request.spreadsheet_id,
                "sheet_title": request.sheet_title,
                "update_count": len(request.updates),
            }
        )
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tools/restore_cells")
async def restore_cell_values(request: RestoreRequest) -> Dict[str, Any]:
    """
    Restore cell values from a Supabase snapshot.

    This endpoint restores cells to their original values before an update_cells operation.
    Use the snapshot_batch_id returned from the update_cells endpoint.

    Example request:
    {
        "snapshot_batch_id": "550e8400-e29b-41d4-a716-446655440000",
        "cell_locations": ["A1", "B2"]  // Optional: restore only specific cells
    }
    """
    validator = _get_sheets_service()
    if validator is None:
        raise HTTPException(
            status_code=503,
            detail="Cell restore tools are not available on this deployment.",
        )

    try:
        snapshot_batch_id = request.snapshot_batch_id

        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured.")

        # Fetch snapshot rows from Supabase
        params = {
            "select": "cell,value,spreadsheet_id,gid",
            "snapshot_batch_id": f"eq.{snapshot_batch_id}",
        }
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/cell_value_snapshots?{query}"

        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Accept": "application/json",
            },
        )

        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                raise RuntimeError(f"Unexpected Supabase status: {response.status}")
            payload = response.read()

        snapshot_rows = json.loads(payload)
        if not isinstance(snapshot_rows, list) or not snapshot_rows:
            raise ValueError(f"No snapshot found for batch id '{snapshot_batch_id}'.")

        # Filter by cell_locations if provided
        if request.cell_locations:
            expected_cells = set(request.cell_locations)
            snapshot_rows = [row for row in snapshot_rows if row.get("cell") in expected_cells]
            if not snapshot_rows:
                raise ValueError("No matching cells found in snapshot.")

        # Get spreadsheet info from first row
        first_row = snapshot_rows[0]
        spreadsheet_id = first_row.get("spreadsheet_id")
        gid = first_row.get("gid")

        if not spreadsheet_id:
            raise ValueError("Snapshot missing spreadsheet_id.")

        spreadsheet = validator.fetch_spreadsheet(spreadsheet_id)
        sheets = spreadsheet.get("sheets", [])
        if not sheets:
            raise ValueError("No sheets available in spreadsheet.")

        # Find sheet by gid
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

        # Build batch update
        batch_data: List[Dict[str, Any]] = []

        for row in snapshot_rows:
            cell = row.get("cell")
            value_json = row.get("value")

            if not cell:
                continue

            # Deserialize value
            if value_json is None:
                value = None
            else:
                try:
                    value = json.loads(value_json)
                except json.JSONDecodeError:
                    value = value_json  # Fallback to string

            cell_range = f"'{sheet_title}'!{cell}"

            # Handle different value types
            if value is None:
                value_to_write = [[""]]
            elif isinstance(value, list):
                # It was a range - restore the full 2D array
                value_to_write = value
            else:
                # Single cell value
                value_to_write = [[value]]

            batch_data.append({
                "range": cell_range,
                "values": value_to_write,
            })

        # Execute batch restore
        if batch_data:
            validator.service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "valueInputOption": "USER_ENTERED",
                    "data": batch_data,
                },
            ).execute()

        return {
            "status": "success",
            "message": f"Restored {len(batch_data)} cell value(s) on '{sheet_title}' from snapshot.",
            "count": len(batch_data),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
