from __future__ import annotations

from typing import Any, Dict, List, Optional

from .llm import LLMClient, PROMPTS
from .logging_config import get_logger
from .sheets_client import ServiceAccountSheetsClient
from .utils import column_to_letter

logger = get_logger(__name__)


class SheetCreator:
  """
  Port of the TypeScript SheetCreator. Uses an LLM to design a spreadsheet,
  then creates and populates it via the Sheets API.
  """

  def __init__(self, sheets_client: ServiceAccountSheetsClient, llm_client: LLMClient) -> None:
    self.sheets_client = sheets_client
    self.llm_client = llm_client

  def create(self, request: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    spreadsheet_id: Optional[str] = None

    try:
      logger.info(f"Creating spreadsheet with prompt: {request.get('prompt', '')[:100]}...")

      plan = self._generate_plan(request)
      logger.debug(f"Generated plan with {len(plan.get('sheets', []))} sheets")

      # Validate plan structure
      validation_errors = self._validate_plan(plan)
      if validation_errors:
        logger.warning(f"Plan validation failed with {len(validation_errors)} errors")
        for error in validation_errors:
          logger.warning(f"  - {error}")
        return {
          "success": False,
          "plan": plan,
          "errors": validation_errors,
        }

      spreadsheet_id = self._create_spreadsheet(plan)
      logger.info(f"Created spreadsheet: {spreadsheet_id}")

      populate_errors = self._populate_spreadsheet(spreadsheet_id, plan)

      if populate_errors:
        logger.warning(f"Encountered {len(populate_errors)} errors while populating spreadsheet")
        for error in populate_errors:
          logger.warning(f"  - {error}")
        errors.extend(populate_errors)

      if len(errors) == 0:
        logger.info(f"Successfully created and populated spreadsheet: {spreadsheet_id}")
      else:
        logger.error(f"Spreadsheet created but with {len(errors)} errors: {spreadsheet_id}")

      return {
        "success": len(errors) == 0,
        "spreadsheetId": spreadsheet_id,
        "spreadsheetUrl": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
        "plan": plan,
        "errors": errors if errors else None,
      }
    except Exception as exc:
      error_msg = str(exc)
      logger.error(f"Failed to create spreadsheet: {error_msg}", exc_info=True)
      return {
        "success": False,
        "spreadsheetId": spreadsheet_id,
        "plan": {"title": "", "sheets": []},
        "errors": [error_msg],
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

  def _validate_plan(self, plan: Dict[str, Any]) -> List[str]:
    """
    Validate the LLM-generated plan structure.
    Returns a list of error messages (empty list if valid).
    """
    errors: List[str] = []

    if not isinstance(plan, dict):
      errors.append("Plan must be a dictionary")
      return errors

    if not plan.get("title"):
      errors.append("Plan must include a 'title' field")

    sheets = plan.get("sheets")
    if not sheets or not isinstance(sheets, list) or len(sheets) == 0:
      errors.append("Plan must include at least one sheet in 'sheets' array")
      return errors

    for idx, sheet in enumerate(sheets):
      sheet_num = idx + 1

      if not isinstance(sheet, dict):
        errors.append(f"Sheet {sheet_num} must be a dictionary")
        continue

      if not sheet.get("name"):
        errors.append(f"Sheet {sheet_num} must have a 'name' field")

      columns = sheet.get("columns")
      if not columns or not isinstance(columns, list):
        errors.append(f"Sheet {sheet_num} must have a 'columns' array")
        continue

      if len(columns) == 0:
        errors.append(f"Sheet {sheet_num} must have at least one column")

      for col_idx, col in enumerate(columns):
        col_num = col_idx + 1
        if not isinstance(col, dict):
          errors.append(f"Sheet {sheet_num}, column {col_num} must be a dictionary")
          continue

        if not col.get("name"):
          errors.append(f"Sheet {sheet_num}, column {col_num} must have a 'name' field")

      example_rows = sheet.get("exampleRows")
      if example_rows is not None:
        if not isinstance(example_rows, list):
          errors.append(f"Sheet {sheet_num} 'exampleRows' must be an array")
        else:
          # Validate each row has the correct number of columns
          for row_idx, row in enumerate(example_rows):
            row_num = row_idx + 1
            if not isinstance(row, list):
              errors.append(f"Sheet {sheet_num}, exampleRow {row_num} must be an array")
            elif len(row) != len(columns):
              errors.append(
                f"Sheet {sheet_num}, exampleRow {row_num} has {len(row)} values but {len(columns)} columns defined"
              )

    return errors

  # --- spreadsheet creation / population ---

  def _create_spreadsheet(self, plan: Dict[str, Any]) -> str:
    sheet_titles = [s.get("name") for s in plan.get("sheets", [])]
    title = plan.get("title", "Sheet Mangler Spreadsheet")
    return self.sheets_client.create_spreadsheet(title, sheet_titles)

  def _populate_spreadsheet(self, spreadsheet_id: str, plan: Dict[str, Any]) -> List[str]:
    """
    Populate the spreadsheet with data from the plan.
    Returns a list of error messages (empty if successful).
    """
    errors: List[str] = []

    for idx, sheet in enumerate(plan.get("sheets", [])):
      sheet_num = idx + 1
      sheet_name = sheet.get("name", f"Sheet{sheet_num}")

      try:
        columns = sheet.get("columns") or []
        headers = [c.get("name") for c in columns]

        if not headers:
          errors.append(f"Sheet '{sheet_name}' has no headers to write")
          continue

        header_range = f"{sheet_name}!A1:{column_to_letter(len(headers))}1"
        self.sheets_client.write_range(spreadsheet_id, header_range, [headers])

        example_rows = sheet.get("exampleRows") or []
        if example_rows:
          row_count = len(example_rows)
          data_range = f"{sheet_name}!A2:{column_to_letter(len(columns))}{1 + row_count}"

          try:
            self.sheets_client.write_range(
              spreadsheet_id,
              data_range,
              example_rows,
              value_input_option="USER_ENTERED",
            )
          except Exception as exc:
            errors.append(f"Failed to write data to sheet '{sheet_name}': {str(exc)}")

        # Apply formatting (best effort - don't fail if this errors)
        try:
          self._apply_formatting(spreadsheet_id, sheet)
        except Exception as exc:
          errors.append(f"Failed to format sheet '{sheet_name}': {str(exc)}")

      except Exception as exc:
        errors.append(f"Failed to populate sheet '{sheet_name}': {str(exc)}")

    # Add documentation sheet if present (best effort)
    documentation = plan.get("documentation")
    if documentation:
      try:
        self._add_documentation_sheet(spreadsheet_id, documentation)
      except Exception as exc:
        errors.append(f"Failed to add documentation sheet: {str(exc)}")

    return errors

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


