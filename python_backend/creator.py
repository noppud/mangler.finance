from __future__ import annotations

from typing import Any, Dict, List, Optional

from .llm import LLMClient, PROMPTS
from .sheets_client import ServiceAccountSheetsClient
from .utils import column_to_letter


class SheetCreator:
  """
  Port of the TypeScript SheetCreator. Uses an LLM to design a spreadsheet,
  then creates and populates it via the Sheets API.
  """

  def __init__(self, sheets_client: ServiceAccountSheetsClient, llm_client: LLMClient) -> None:
    self.sheets_client = sheets_client
    self.llm_client = llm_client

  def create(self, request: Dict[str, Any]) -> Dict[str, Any]:
    try:
      plan = self._generate_plan(request)
      spreadsheet_id = self._create_spreadsheet(plan)
      self._populate_spreadsheet(spreadsheet_id, plan)

      return {
        "success": True,
        "spreadsheetId": spreadsheet_id,
        "spreadsheetUrl": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
        "plan": plan,
      }
    except Exception as exc:
      return {
        "success": False,
        "plan": {"title": "", "sheets": []},
        "errors": [str(exc)],
      }

  # --- planning ---

  def _generate_plan(self, request: Dict[str, Any]) -> Dict[str, Any]:
    prompt = request["prompt"]
    constraints = request.get("constraints") or {}

    parts: List[str] = []
    if constraints.get("maxSheets"):
      parts.append(f"Maximum {constraints['maxSheets']} sheets")
    if constraints.get("maxColumns"):
      parts.append(f"Maximum {constraints['maxColumns']} columns per sheet")
    if constraints.get("maxExampleRows") is not None:
      parts.append(f"Limit example rows to {constraints['maxExampleRows']}")

    constraints_str = "\n".join(parts) if parts else None
    llm_prompt = PROMPTS.SHEET_CREATION.user(prompt, constraints_str)

    response = self.llm_client.chat_json(
      [
        {"role": "system", "content": PROMPTS.SHEET_CREATION.system},
        {"role": "user", "content": llm_prompt},
      ],
      overrides={"temperature": 0.5},
    )

    return response

  # --- spreadsheet creation / population ---

  def _create_spreadsheet(self, plan: Dict[str, Any]) -> str:
    sheet_titles = [s.get("name") for s in plan.get("sheets", [])]
    title = plan.get("title", "Sheet Mangler Spreadsheet")
    return self.sheets_client.create_spreadsheet(title, sheet_titles)

  def _populate_spreadsheet(self, spreadsheet_id: str, plan: Dict[str, Any]) -> None:
    for sheet in plan.get("sheets", []):
      columns = sheet.get("columns") or []
      headers = [c.get("name") for c in columns]
      header_range = f"{sheet['name']}!A1:{column_to_letter(len(headers))}1"
      self.sheets_client.write_range(spreadsheet_id, header_range, [headers])

      example_rows = sheet.get("exampleRows") or []
      if example_rows:
        row_count = len(example_rows)
        data_range = f"{sheet['name']}!A2:{column_to_letter(len(columns))}{1 + row_count}"
        self.sheets_client.write_range(
          spreadsheet_id,
          data_range,
          example_rows,
          value_input_option="USER_ENTERED",
        )

      # Validation is currently a no-op stub, mirroring TS "TODO"
      self._apply_formatting(spreadsheet_id, sheet)

    documentation = plan.get("documentation")
    if documentation:
      self._add_documentation_sheet(spreadsheet_id, documentation)

  def _apply_formatting(self, spreadsheet_id: str, sheet: Dict[str, Any]) -> None:
    metadata = self.sheets_client.get_spreadsheet_metadata(spreadsheet_id)
    sheet_meta = next(
      (s for s in metadata.get("sheets", []) if s.get("title") == sheet.get("name")),
      None,
    )
    if not sheet_meta:
      return

    sheet_id = sheet_meta.get("sheetId")
    columns = sheet.get("columns") or []

    self.sheets_client.format_range(
      spreadsheet_id,
      sheet_id,
      start_row=0,
      end_row=1,
      start_col=0,
      end_col=len(columns),
      cell_format={
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9},
      },
    )

  def _add_documentation_sheet(self, spreadsheet_id: str, documentation: str) -> None:
    self.sheets_client.add_sheet(spreadsheet_id, "README")
    lines = [[line] for line in documentation.split("\n")]
    self.sheets_client.write_range(spreadsheet_id, "README!A1", lines)


