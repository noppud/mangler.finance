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
    if action_type == "add_column":
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
    local_range = params.get("range") or ""
    formula = params.get("formula") or ""
    full_range = f"{sheet_title}!{local_range}"
    self.sheets_client.write_range(spreadsheet_id, full_range, [[formula]], value_input_option="USER_ENTERED")

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


