from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build


class ServiceAccountSheetsClient:
  """
  Google Sheets API client using service account credentials, mirroring the
  behavior of the TypeScript ServiceAccountSheetsClient.
  """

  def __init__(self, credentials_path: Optional[str] = None) -> None:
    if credentials_path is None:
      # Resolve project paths relative to this file, not the CWD
      backend_root = Path(__file__).resolve().parent
      repo_root = backend_root.parent

      # Allow overriding via env var, then fall back to known locations
      env_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
      candidate_paths: List[Path] = []
      if env_path:
        candidate_paths.append(Path(env_path))

      # Preferred: dedicated key file for the Python backend
      candidate_paths.append(backend_root / "service-account.json")

      # Backwards-compatible fallbacks for existing setups
      candidate_paths.append(repo_root / "fintech-hackathon-478313-93c79ddbebac.json")
      candidate_paths.append(
        repo_root / "sheet-mangler" / "fintech-hackathon-478313-93c79ddbebac.json"
      )

      resolved_path: Optional[Path] = None
      for candidate in candidate_paths:
        if candidate and candidate.is_file():
          resolved_path = candidate
          break

      if not resolved_path:
        raise FileNotFoundError(
          "Could not find Google service account key JSON. "
          "Set GOOGLE_SERVICE_ACCOUNT_FILE to the downloaded key file path "
          "or place service-account.json in the python_backend/ directory."
        )

      credentials_path = str(resolved_path)

    scopes = [
      "https://www.googleapis.com/auth/spreadsheets",
      "https://www.googleapis.com/auth/drive.readonly",
    ]

    creds = service_account.Credentials.from_service_account_file(
      credentials_path,
      scopes=scopes,
    )

    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    self._sheets = service.spreadsheets()

  # --- Metadata ---

  def get_spreadsheet_metadata(self, spreadsheet_id: str) -> Dict[str, Any]:
    result = (
      self._sheets.get(
        spreadsheetId=spreadsheet_id,
        fields="spreadsheetId,properties,sheets",
      )
      .execute()
    )

    sheets_meta: List[Dict[str, Any]] = []
    for index, sheet in enumerate(result.get("sheets", [])):
      props = sheet.get("properties", {})
      grid_props = props.get("gridProperties", {}) or {}
      sheets_meta.append(
        {
          "sheetId": props.get("sheetId", 0),
          "title": props.get("title", ""),
          "index": index,
          "rowCount": grid_props.get("rowCount", 0),
          "columnCount": grid_props.get("columnCount", 0),
          "gridProperties": {
            "frozenRowCount": grid_props.get("frozenRowCount"),
            "frozenColumnCount": grid_props.get("frozenColumnCount"),
          },
        }
      )

    return {
      "spreadsheetId": result.get("spreadsheetId", ""),
      "title": (result.get("properties") or {}).get("title", ""),
      "url": f"https://docs.google.com/spreadsheets/d/{result.get('spreadsheetId')}",
      "sheets": sheets_meta,
    }

  # --- Range helpers ---

  @staticmethod
  def _parse_cell_value(value: Any) -> Dict[str, Any]:
    if value is None or value == "":
      return {"value": None, "type": "empty"}
    if isinstance(value, (int, float)):
      return {"value": value, "type": "number"}
    if isinstance(value, bool):
      return {"value": value, "type": "boolean"}
    # Heuristic date detection
    if isinstance(value, str):
      try:
        # Let pandas or dateutil handle more complex cases; for now just attempt parse
        import datetime as _dt

        _dt.datetime.fromisoformat(value)
        return {"value": value, "type": "date"}
      except Exception:
        return {"value": value, "type": "string"}
    return {"value": str(value), "type": "string"}

  @staticmethod
  def _extract_cell_value(effective_value: Any) -> Any:
    if not effective_value:
      return None
    if "numberValue" in effective_value:
      return effective_value["numberValue"]
    if "stringValue" in effective_value:
      return effective_value["stringValue"]
    if "boolValue" in effective_value:
      return effective_value["boolValue"]
    if "errorValue" in effective_value:
      return f"#ERROR: {effective_value['errorValue'].get('type')}"
    return None

  @staticmethod
  def _determine_cell_type(effective_value: Any, formula: Optional[str]) -> str:
    if formula:
      return "formula"
    if not effective_value:
      return "empty"
    if effective_value.get("errorValue") is not None:
      return "error"
    if "numberValue" in effective_value:
      return "number"
    if "boolValue" in effective_value:
      return "boolean"
    if "stringValue" in effective_value:
      return "string"
    return "empty"

  # --- Reading ---

  def read_range(self, spreadsheet_id: str, range_a1: str) -> Dict[str, Any]:
    result = (
      self._sheets.values()
      .get(
        spreadsheetId=spreadsheet_id,
        range=range_a1,
        valueRenderOption="UNFORMATTED_VALUE",
      )
      .execute()
    )

    values = result.get("values", []) or []
    cell_values: List[List[Dict[str, Any]]] = [
      [self._parse_cell_value(value) for value in row] for row in values
    ]

    end_row = len(values) - 1
    end_col = len(values[0]) - 1 if values and values[0] else 0

    return {
      "sheet": range_a1.split("!")[0] if "!" in range_a1 else "",
      "startRow": 0,
      "startCol": 0,
      "endRow": end_row,
      "endCol": end_col,
      "a1Notation": range_a1,
      "values": cell_values,
    }

  def read_range_with_formulas(self, spreadsheet_id: str, range_a1: str) -> Dict[str, Any]:
    result = (
      self._sheets.get(
        spreadsheetId=spreadsheet_id,
        ranges=[range_a1],
        fields="sheets(data(rowData(values(formattedValue,effectiveValue,userEnteredValue))))",
      )
      .execute()
    )

    sheet = (result.get("sheets") or [None])[0] or {}
    data = (sheet.get("data") or [None])[0] or {}
    row_data = data.get("rowData") or []

    cell_values: List[List[Dict[str, Any]]] = []
    for row in row_data:
      values = row.get("values") or []
      row_cells: List[Dict[str, Any]] = []
      for cell in values:
        user_entered = cell.get("userEnteredValue") or {}
        formula = user_entered.get("formulaValue")
        effective = cell.get("effectiveValue") or {}
        formatted = cell.get("formattedValue")

        value = self._extract_cell_value(effective)
        cell_type = self._determine_cell_type(effective, formula)
        row_cells.append(
          {
            "value": value,
            "formula": formula,
            "formattedValue": formatted,
            "type": cell_type,
          }
        )
      cell_values.append(row_cells)

    end_row = len(cell_values) - 1
    end_col = len(cell_values[0]) - 1 if cell_values and cell_values[0] else 0

    return {
      "sheet": range_a1.split("!")[0] if "!" in range_a1 else "",
      "startRow": 0,
      "startCol": 0,
      "endRow": end_row,
      "endCol": end_col,
      "a1Notation": range_a1,
      "values": cell_values,
    }

  # --- Writing / updates ---

  def write_range(
    self,
    spreadsheet_id: str,
    range_a1: str,
    values: List[List[Any]],
    value_input_option: str = "USER_ENTERED",
  ) -> None:
    (
      self._sheets.values()
      .update(
        spreadsheetId=spreadsheet_id,
        range=range_a1,
        valueInputOption=value_input_option,
        body={"values": values},
      )
      .execute()
    )

  def batch_update(
    self,
    spreadsheet_id: str,
    updates: List[Dict[str, Any]],
  ) -> None:
    (
      self._sheets.values()
      .batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
          "valueInputOption": "USER_ENTERED",
          "data": updates,
        },
      )
      .execute()
    )

  def add_sheet(self, spreadsheet_id: str, title: str) -> int:
    result = (
      self._sheets.batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
          "requests": [
            {
              "addSheet": {
                "properties": {
                  "title": title,
                }
              }
            }
          ]
        },
      )
      .execute()
    )
    replies = result.get("replies") or []
    if not replies:
      return 0
    return replies[0].get("addSheet", {}).get("properties", {}).get("sheetId", 0)

  def delete_sheet(self, spreadsheet_id: str, sheet_id: int) -> None:
    (
      self._sheets.batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
          "requests": [
            {
              "deleteSheet": {
                "sheetId": sheet_id,
              }
            }
          ]
        },
      )
      .execute()
    )

  def create_spreadsheet(self, title: str, sheet_titles: Optional[List[str]] = None) -> str:
    sheet_titles = sheet_titles or ["Sheet1"]
    result = (
      self._sheets.create(
        body={
          "properties": {"title": title},
          "sheets": [{"properties": {"title": t}} for t in sheet_titles],
        }
      )
      .execute()
    )
    return result.get("spreadsheetId", "")

  def format_range(
    self,
    spreadsheet_id: str,
    sheet_id: int,
    start_row: int,
    end_row: int,
    start_col: int,
    end_col: int,
    cell_format: Dict[str, Any],
  ) -> None:
    (
      self._sheets.batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
          "requests": [
            {
              "repeatCell": {
                "range": {
                  "sheetId": sheet_id,
                  "startRowIndex": start_row,
                  "endRowIndex": end_row,
                  "startColumnIndex": start_col,
                  "endColumnIndex": end_col,
                },
                "cell": {"userEnteredFormat": cell_format},
                "fields": "userEnteredFormat",
              }
            }
          ]
        },
      )
      .execute()
    )
