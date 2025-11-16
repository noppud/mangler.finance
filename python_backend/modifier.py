from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .context_builder import ContextBuilder
from .llm import LLMClient, PROMPTS, format_sheet_context
from .sheets_client import ServiceAccountSheetsClient
from .utils import column_to_letter


class SheetModifier:
  """
  Port of the TypeScript SheetModifier. Uses an LLM to generate a modification
  plan, then executes supported actions via the Sheets client.
  """

  def __init__(
    self,
    sheets_client: ServiceAccountSheetsClient,
    context_builder: ContextBuilder,
    llm_client: LLMClient,
  ) -> None:
    self.sheets_client = sheets_client
    self.context_builder = context_builder
    self.llm_client = llm_client

  def modify(self, request: Dict[str, Any]) -> Dict[str, Any]:
    spreadsheet_id: str = request["spreadsheetId"]
    sheet_title: str = request.get("sheetTitle") or ""
    prompt: str = request["prompt"]
    constraints: Optional[Dict[str, Any]] = request.get("constraints")

    context = request.get("context") or self.context_builder.build_context(
      spreadsheet_id,
      sheet_title,
    )

    plan = self._generate_plan(prompt, context, constraints)
    self._validate_plan(plan, constraints)

    executed_actions: List[Dict[str, Any]] = []
    changed_ranges: List[str] = []
    errors: List[str] = []

    try:
      for action in plan["actions"]:
        try:
          self._execute_action(spreadsheet_id, sheet_title or context["sheetMetadata"]["title"], action)
          executed_actions.append(action)
          if action.get("affectedRange"):
            changed_ranges.append(action["affectedRange"])
        except Exception as exc:
          errors.append(f"Failed to execute {action.get('type')}: {exc}")

      return {
        "success": len(errors) == 0,
        "plan": plan,
        "executedActions": executed_actions,
        "errors": errors or None,
        "changedRanges": changed_ranges,
        "summary": self._generate_summary(executed_actions),
      }
    except Exception as exc:
      return {
        "success": False,
        "plan": plan,
        "executedActions": executed_actions,
        "errors": [str(exc)],
        "changedRanges": changed_ranges,
        "summary": "Modification failed",
      }

  # --- planning ---

  def _generate_plan(
    self,
    user_prompt: str,
    context: Dict[str, Any],
    constraints: Optional[Dict[str, Any]],
  ) -> Dict[str, Any]:
    context_str = format_sheet_context(context)
    llm_prompt = PROMPTS.MODIFICATION_PLAN.user(user_prompt, context_str)

    response = self.llm_client.chat_json(
      [
        {"role": "system", "content": PROMPTS.MODIFICATION_PLAN.system},
        {"role": "user", "content": llm_prompt},
      ],
      overrides={"temperature": 0.3},
    )

    actions = response.get("actions") or []

    overall_impact = {
      "totalRowsAffected": sum(a.get("estimatedImpact", {}).get("rowsAffected", 0) for a in actions),
      "totalColumnsAffected": sum(a.get("estimatedImpact", {}).get("columnsAffected", 0) for a in actions),
      "hasDestructiveActions": any(a.get("estimatedImpact", {}).get("destructive") for a in actions),
      "estimatedDuration": self._estimate_duration(len(actions)),
    }

    return {
      "id": str(uuid.uuid4()),
      "userPrompt": user_prompt,
      "intent": response.get("intent", ""),
      "actions": actions,
      "overallImpact": overall_impact,
      "warnings": response.get("warnings") or [],
      "requiresConfirmation": overall_impact["hasDestructiveActions"]
      or overall_impact["totalRowsAffected"] > 100,
    }

  def _validate_plan(self, plan: Dict[str, Any], constraints: Optional[Dict[str, Any]]) -> None:
    """
    Validate the plan against constraints and check for inefficient patterns.

    This includes:
    - Checking row/column limits
    - Preventing destructive actions if not allowed
    - Detecting inefficient action patterns (too many individual set_value actions)
    - Warning about unsupported operations
    """
    actions = plan.get("actions") or []

    # Check for inefficient patterns: too many individual set_value actions
    set_value_count = sum(1 for action in actions if action.get("type") == "set_value")
    if set_value_count > 10:
      raise ValueError(
        f"Plan contains {set_value_count} individual set_value actions. "
        f"This is inefficient - please use batch_update instead for updating multiple cells. "
        f"Batch operations are faster, more reliable, and reduce API calls."
      )

    # Check for unsupported action types that might cause issues
    unsupported_patterns = ["create_sheet", "delete_sheet", "add_sheet", "remove_sheet"]
    for action in actions:
      action_type = action.get("type", "")
      if any(pattern in action_type for pattern in unsupported_patterns):
        raise ValueError(
          f"Action type '{action_type}' is not supported. "
          f"This tool can only modify the CURRENT sheet - it cannot create or delete sheets."
        )

    # Apply user-provided constraints if present
    if not constraints:
      return

    overall = plan.get("overallImpact") or {}
    max_rows = constraints.get("maxRowsAffected")
    if max_rows is not None and overall.get("totalRowsAffected", 0) > max_rows:
      raise ValueError(
        f"Plan would affect {overall.get('totalRowsAffected')} rows, exceeding limit of {max_rows}"
      )

    max_cols = constraints.get("maxColumnsAffected")
    if max_cols is not None and overall.get("totalColumnsAffected", 0) > max_cols:
      raise ValueError(
        f"Plan would affect {overall.get('totalColumnsAffected')} columns, exceeding limit of {max_cols}"
      )

    if not constraints.get("allowDestructive") and overall.get("hasDestructiveActions"):
      raise ValueError("Plan contains destructive actions but destructive operations are not allowed")

  # --- execution ---

  def _execute_action(
    self,
    spreadsheet_id: str,
    sheet_title: str,
    action: Dict[str, Any],
  ) -> None:
    action_type = action.get("type")
    if action_type == "batch_update":
      self._execute_batch_update(spreadsheet_id, sheet_title, action)
    elif action_type == "add_column":
      self._execute_add_column(spreadsheet_id, sheet_title, action)
    elif action_type == "rename_column":
      self._execute_rename_column(spreadsheet_id, sheet_title, action)
    elif action_type == "update_formula":
      self._execute_update_formula(spreadsheet_id, sheet_title, action)
    elif action_type == "set_value":
      self._execute_set_value(spreadsheet_id, sheet_title, action)
    elif action_type == "clear_range":
      self._execute_clear_range(spreadsheet_id, sheet_title, action)
    elif action_type == "normalize_data":
      self._execute_normalize_data(spreadsheet_id, sheet_title, action)
    else:
      raise ValueError(f"Unsupported action type: {action_type}")

  def _execute_batch_update(
    self,
    spreadsheet_id: str,
    sheet_title: str,
    action: Dict[str, Any],
  ) -> None:
    """
    Execute a batch update of multiple cells at once.

    This is the preferred method for updating many cells efficiently.
    Uses Google Sheets batchUpdate API to minimize API calls.

    Params:
      updates: List of cell updates, each with:
        - cell: A1 notation (e.g., "A1", "B5")
        - value: The value to set (string, number, boolean, or formula)
        - is_formula: Optional boolean (default: False), set to True for formulas

    Example:
      {
        "type": "batch_update",
        "params": {
          "updates": [
            {"cell": "A1", "value": "Title", "is_formula": false},
            {"cell": "B2", "value": 100},
            {"cell": "C3", "value": "=A1+B2", "is_formula": true}
          ]
        }
      }
    """
    params = action.get("params") or {}
    updates = params.get("updates") or []

    if not updates:
      raise ValueError("batch_update requires params.updates list")

    # Build batch data for Google Sheets API
    batch_data: List[Dict[str, Any]] = []

    for update in updates:
      cell = update.get("cell")
      value = update.get("value")
      is_formula = update.get("is_formula", False)

      if not cell:
        raise ValueError("Each update must have a 'cell' field with A1 notation")

      # Determine value input option
      value_input_option = "USER_ENTERED" if is_formula else "RAW"

      # Prepare the cell range
      cell_range = f"{sheet_title}!{cell}"

      # Handle None/null values as empty strings
      if value is None:
        value_to_write = [[""]]
      else:
        value_to_write = [[value]]

      batch_data.append({
        "range": cell_range,
        "values": value_to_write,
      })

    # Execute batch update via Sheets client
    if batch_data:
      # Use the sheets client's service to perform batch update
      self.sheets_client.service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
          "valueInputOption": "USER_ENTERED",  # This handles both formulas and values correctly
          "data": batch_data,
        },
      ).execute()

  def _execute_add_column(
    self,
    spreadsheet_id: str,
    sheet_title: str,
    action: Dict[str, Any],
  ) -> None:
    params = action.get("params") or {}
    column_name = params.get("columnName")
    column_index = params.get("columnIndex", 0)
    default_value = params.get("defaultValue")

    # Note: This is a simplified implementation that writes into the existing
    # range; full column insertion via batchUpdate is more complex.
    range_a1 = f"{sheet_title}!A1:Z"
    data = self.sheets_client.read_range(spreadsheet_id, range_a1)

    header_cell = f"{sheet_title}!{column_to_letter(column_index + 1)}1"
    self.sheets_client.write_range(spreadsheet_id, header_cell, [[column_name]])

    if default_value is not None and data.get("values"):
      row_count = len(data["values"])
      data_range = f"{sheet_title}!{column_to_letter(column_index + 1)}2:{column_to_letter(column_index + 1)}{row_count}"
      values = [[default_value] for _ in range(row_count - 1)]
      self.sheets_client.write_range(spreadsheet_id, data_range, values)

  def _execute_rename_column(
    self,
    spreadsheet_id: str,
    sheet_title: str,
    action: Dict[str, Any],
  ) -> None:
    params = action.get("params") or {}
    column_index = params.get("columnIndex", 0)
    new_name = params.get("newName") or ""
    range_a1 = f"{sheet_title}!{column_to_letter(column_index + 1)}1"
    self.sheets_client.write_range(spreadsheet_id, range_a1, [[new_name]])

  def _execute_update_formula(
    self,
    spreadsheet_id: str,
    sheet_title: str,
    action: Dict[str, Any],
  ) -> None:
    params = action.get("params") or {}

    # Check if using the new multi-column format
    if params.get("applyToAllColumns") and params.get("rangeStart") and params.get("rangeEnd"):
      self._execute_update_formula_multi_column(spreadsheet_id, sheet_title, params)
      return

    # Legacy single-cell formula update
    local_range = params.get("range") or ""
    formula = params.get("formula") or ""

    if not local_range:
      raise ValueError("update_formula requires params.range")
    if not formula:
      raise ValueError("update_formula requires params.formula")

    full_range = f"{sheet_title}!{local_range}"
    self.sheets_client.write_range(spreadsheet_id, full_range, [[formula]], value_input_option="USER_ENTERED")

  def _execute_update_formula_multi_column(
    self,
    spreadsheet_id: str,
    sheet_title: str,
    params: Dict[str, Any],
  ) -> None:
    """
    Execute update_formula when applyToAllColumns is true.
    Generates formulas for each column in the range based on the formula pattern.

    Params:
      - rangeStart: Starting cell (e.g., "B3")
      - rangeEnd: Ending cell (e.g., "Z3")
      - formulaPattern: Pattern formula (e.g., "=B2/52")
      - referenceRow: Row to reference in formulas (optional)
    """
    range_start = params.get("rangeStart", "")
    range_end = params.get("rangeEnd", "")
    formula_pattern = params.get("formulaPattern", "")

    if not range_start or not range_end:
      raise ValueError("update_formula with applyToAllColumns requires rangeStart and rangeEnd")
    if not formula_pattern:
      raise ValueError("update_formula with applyToAllColumns requires formulaPattern")

    # Parse start and end cells to extract row and column info
    import re
    start_match = re.match(r"([A-Z]+)(\d+)", range_start)
    end_match = re.match(r"([A-Z]+)(\d+)", range_end)

    if not start_match or not end_match:
      raise ValueError(f"Invalid range format: {range_start}:{range_end}")

    start_col_letter = start_match.group(1)
    start_row = int(start_match.group(2))
    end_col_letter = end_match.group(1)
    end_row = int(end_match.group(2))

    if start_row != end_row:
      raise ValueError(f"Multi-column formula update must be on same row, got {start_row} to {end_row}")

    target_row = start_row

    # Convert column letters to numbers
    start_col_num = self._letter_to_column(start_col_letter)
    end_col_num = self._letter_to_column(end_col_letter)

    # Generate formulas for each column
    formulas = []
    for col_num in range(start_col_num, end_col_num + 1):
      col_letter = column_to_letter(col_num)

      # Replace column references in the formula pattern
      # For pattern "=B2/52", when col is C, it becomes "=C2/52"
      formula = self._adapt_formula_for_column(formula_pattern, col_letter, target_row, params)
      formulas.append(formula)

    # Write all formulas at once in a single row
    full_range = f"{sheet_title}!{range_start}:{range_end}"
    values = [formulas]  # Single row with multiple formulas

    self.sheets_client.write_range(
      spreadsheet_id,
      full_range,
      values,
      value_input_option="USER_ENTERED"
    )

  @staticmethod
  def _letter_to_column(letter: str) -> int:
    """Convert column letter to column number (A=1, B=2, ..., Z=26, AA=27, etc.)"""
    result = 0
    for char in letter:
      result = result * 26 + (ord(char) - ord('A') + 1)
    return result

  @staticmethod
  def _adapt_formula_for_column(
    formula_pattern: str,
    target_col_letter: str,
    target_row: int,
    params: Dict[str, Any],
  ) -> str:
    """
    Adapt a formula pattern for a specific column.

    For example, if pattern is "=B2/52" and target_col is "C",
    returns "=C2/52"
    """
    reference_row = params.get("referenceRow")

    # Replace column references in the formula
    # Pattern: =B2/52 -> =C2/52 for column C
    import re

    # Find all cell references like B2, C5, etc.
    def replace_column(match):
      col = match.group(1)
      row = match.group(2)

      # If this references the reference row, update the column
      if reference_row and int(row) == reference_row:
        return f"{target_col_letter}{row}"
      return match.group(0)

    # Match cell references (one or more letters followed by digits)
    adapted = re.sub(r'([A-Z]+)(\d+)', replace_column, formula_pattern)

    return adapted

  def _execute_set_value(
    self,
    spreadsheet_id: str,
    sheet_title: str,
    action: Dict[str, Any],
  ) -> None:
    params = action.get("params") or {}
    value = params.get("value")

    target_range: Optional[str] = (
      params.get("range")
      or params.get("cell")
      or params.get("a1Notation")
      or action.get("affectedRange")
    )

    if not target_range:
      row_index = params.get("rowIndex") or params.get("row") or params.get("rowNumber")
      col_index = (
        params.get("columnIndex")
        or params.get("colIndex")
        or params.get("column")
        or params.get("colNumber")
      )
      if isinstance(row_index, int) and isinstance(col_index, int):
        row_number = row_index if row_index >= 1 else row_index + 1
        col_number = col_index if col_index >= 1 else col_index + 1
        target_range = f"{column_to_letter(col_number)}{row_number}"

    if not target_range:
      raise ValueError(
        "set_value action is missing a valid target cell/range "
        "(expected params.range, params.cell, params.a1Notation, or affectedRange)"
      )

    full_range = f"{sheet_title}!{target_range}"
    self.sheets_client.write_range(spreadsheet_id, full_range, [[value]])

  def _execute_clear_range(
    self,
    spreadsheet_id: str,
    sheet_title: str,
    action: Dict[str, Any],
  ) -> None:
    params = action.get("params") or {}
    local_range = params.get("range") or ""
    full_range = f"{sheet_title}!{local_range}"

    data = self.sheets_client.read_range(spreadsheet_id, full_range)
    empty_values = [["" for _ in row] for row in data.get("values", [])]
    self.sheets_client.write_range(spreadsheet_id, full_range, empty_values)

  def _execute_normalize_data(
    self,
    spreadsheet_id: str,
    sheet_title: str,
    action: Dict[str, Any],
  ) -> None:
    params = action.get("params") or {}
    local_range = params.get("range") or ""
    normalization_type = params.get("normalizationType")
    full_range = f"{sheet_title}!{local_range}"

    data = self.sheets_client.read_range(spreadsheet_id, full_range)
    normalized_values: List[List[Any]] = []
    for row in data.get("values", []):
      new_row: List[Any] = []
      for cell in row:
        value = cell.get("value")
        if isinstance(value, str):
          if normalization_type == "trim":
            value = value.strip()
          elif normalization_type == "uppercase":
            value = value.upper()
          elif normalization_type == "lowercase":
            value = value.lower()
        new_row.append(value)
      normalized_values.append(new_row)

    self.sheets_client.write_range(spreadsheet_id, full_range, normalized_values)

  # --- misc helpers ---

  @staticmethod
  def _generate_summary(actions: List[Dict[str, Any]]) -> str:
    if not actions:
      return "No actions executed"
    types = ", ".join(a.get("type", "unknown") for a in actions)
    return f"Successfully executed {len(actions)} action(s): {types}"

  @staticmethod
  def _estimate_duration(action_count: int) -> str:
    if action_count <= 3:
      return "<10 seconds"
    if action_count <= 10:
      return "10-30 seconds"
    return "30+ seconds"


