from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .creator import SheetCreator
from .llm import LLMClient, PROMPTS
from .logging_config import get_logger
from .mistake_detector import MistakeDetector
from .modifier import SheetModifier
from .context_builder import ContextBuilder
from .sheets_client import ServiceAccountSheetsClient
from .utils import normalize_spreadsheet_id, parse_spreadsheet_url
from .models import ChatMessage, SheetContext

logger = get_logger(__name__)


class AgentOrchestrator:
  """
  Python port of the TypeScript AgentOrchestrator.

  It takes chat messages and sheet context, calls the LLM with the AGENT prompt,
  and either responds conversationally or calls one of the tools:
  - detect_issues
  - modify_sheet
  - create_sheet
  """

  def __init__(self, llm_client: LLMClient, sheets_client: ServiceAccountSheetsClient, context_builder: ContextBuilder):
    self.llm_client = llm_client
    self.sheets_client = sheets_client
    self.mistake_detector = MistakeDetector(context_builder, llm_client)
    self.sheet_modifier = SheetModifier(sheets_client, context_builder, llm_client)
    self.sheet_creator = SheetCreator(sheets_client, llm_client)

  def process_chat(
    self,
    messages: List[ChatMessage],
    sheet_context: SheetContext,
  ) -> List[ChatMessage]:
    try:
      logger.debug(f"Processing chat with {len(messages)} message(s)")
      chat_history = self._format_chat_history(messages)
      ctx_str = self._format_sheet_context(sheet_context)

      system_prompt = PROMPTS.AGENT.system
      user_prompt = PROMPTS.AGENT.user(chat_history, ctx_str)

      logger.debug("Calling LLM for chat processing")
      response: Dict[str, Any] = self.llm_client.chat_json(
        [
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": user_prompt},
        ],
        overrides={"maxTokens": 3000},
      )
      logger.debug(f"LLM response received: step={response.get('step')}")

      if not isinstance(response, dict):
        raise ValueError("Invalid response from LLM: expected JSON object")
      if "step" not in response or "assistantMessage" not in response:
        raise ValueError("Invalid response structure: missing step or assistantMessage")

      new_messages: List[ChatMessage] = []

      step = response["step"]
      if step == "answer":
        logger.debug("LLM chose to answer directly")
        new_messages.append(
          ChatMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            content=str(response["assistantMessage"]),
          )
        )
      elif step == "tool_call":
        tool = response.get("tool") or {}
        tool_name = tool.get("name")
        tool_args = tool.get("arguments")
        if not tool_name or tool_args is None:
          logger.error("Invalid tool call: missing tool or arguments")
          raise ValueError("Invalid tool call: missing tool or arguments")

        logger.info(f"Executing tool call: {tool_name}", extra={"tool_name": tool_name})

        # Assistant explanation
        new_messages.append(
          ChatMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            content=str(response["assistantMessage"]),
          )
        )

        tool_messages = self._execute_tool_call(tool_name, tool_args, sheet_context)
        new_messages.extend(tool_messages)
        logger.debug(f"Tool call completed: {len(tool_messages)} message(s) returned")
      else:
        logger.error(f"Unknown step type from LLM: {step}")
        raise ValueError(f"Unknown step type: {step}")

      logger.debug(f"Chat processing completed: {len(new_messages)} new message(s)")
      return new_messages
    except Exception as exc:
      logger.error(f"Chat processing failed: {str(exc)}", exc_info=True)
      return [
        ChatMessage(
          id=str(uuid.uuid4()),
          role="assistant",
          content=f"I encountered an error: {exc}. Please try rephrasing your request or check that your spreadsheet details are correct.",
          metadata={"error": str(exc)},
        )
      ]

  # --- tools ---

  def _execute_tool_call(
    self,
    tool_name: str,
    args: Dict[str, Any],
    sheet_context: SheetContext,
  ) -> List[ChatMessage]:
    messages: List[ChatMessage] = []

    try:
      if tool_name == "detect_issues":
        # Parse the spreadsheet URL to extract ID and gid
        raw_id = args.get("spreadsheetId") or sheet_context.spreadsheetId or ""
        parsed = parse_spreadsheet_url(raw_id)
        spreadsheet_id = parsed["spreadsheet_id"]
        gid = parsed["gid"]

        sheet_title = args.get("sheetTitle") or sheet_context.sheetTitle

        if not spreadsheet_id:
          raise ValueError("Missing spreadsheet ID")

        # If no sheet_title but gid is present, resolve it
        if not sheet_title and gid:
          sheet_title = self.sheets_client.get_sheet_title_by_gid(spreadsheet_id, gid)
          if not sheet_title:
            raise ValueError(f"Could not resolve sheet title from gid={gid}")

        if not sheet_title:
          raise ValueError("Missing sheet title (provide sheetTitle or a URL with gid)")

        config_dict = args.get("config") or {}
        config = {
          "enableRuleBased": config_dict.get("includeRuleBased", False),  # Disabled for debugging
          "enableLLMBased": config_dict.get("includeLLMBased", True),
          "minSeverity": "info",
          "categoriesToCheck": [],  # Disabled temporarily for debugging LLM-based detection
        }

        result = self.mistake_detector.detect_issues(spreadsheet_id, sheet_title, config)

        # The full "issues" list can be very large and is mostly redundant with
        # the flattened "potential_errors" structure. To keep responses compact,
        # omit the raw issues array from the payload returned to the client.
        payload = dict(result)
        payload.pop("issues", None)

        messages.append(
          ChatMessage(
            id=str(uuid.uuid4()),
            role="tool",
            content=f"Detected {len(result.get('issues') or [])} issue(s)",
            metadata={
              "toolName": "detect_issues",
              "payload": payload,
            },
          )
        )
        messages.append(
          ChatMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            content=self._summarize_detection_result(result),
          )
        )

      elif tool_name == "modify_sheet":
        # Parse the spreadsheet URL to extract ID and gid
        raw_id = args.get("spreadsheetId") or sheet_context.spreadsheetId or ""
        parsed = parse_spreadsheet_url(raw_id)
        spreadsheet_id = parsed["spreadsheet_id"]
        gid = parsed["gid"]

        if not spreadsheet_id:
          raise ValueError("Missing spreadsheet ID")
        if not args.get("prompt"):
          raise ValueError("Missing modification prompt")

        sheet_title = args.get("sheetTitle") or sheet_context.sheetTitle

        # If no sheet_title but gid is present, resolve it
        if not sheet_title and gid:
          sheet_title = self.sheets_client.get_sheet_title_by_gid(spreadsheet_id, gid)
          if not sheet_title:
            raise ValueError(f"Could not resolve sheet title from gid={gid}")

        modify_request = {
          "spreadsheetId": spreadsheet_id,
          "sheetTitle": sheet_title,
          "prompt": args.get("prompt"),
          "constraints": args.get("constraints"),
        }

        result = self.sheet_modifier.modify(modify_request)

        messages.append(
          ChatMessage(
            id=str(uuid.uuid4()),
            role="tool",
            content="Modification completed",
            metadata={
              "toolName": "modify_sheet",
              "payload": result,
            },
          )
        )
        messages.append(
          ChatMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            content=self._summarize_modification_result(result),
          )
        )

      elif tool_name == "create_sheet":
        if not args.get("prompt"):
          raise ValueError("Missing creation prompt")

        create_request = {
          "prompt": args.get("prompt"),
          "constraints": args.get("constraints"),
        }
        result = self.sheet_creator.create(create_request)

        messages.append(
          ChatMessage(
            id=str(uuid.uuid4()),
            role="tool",
            content=f"Created new spreadsheet: {result.get('plan', {}).get('title', '')}",
            metadata={
              "toolName": "create_sheet",
              "payload": result,
            },
          )
        )
        messages.append(
          ChatMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            content=self._summarize_creation_result(result),
          )
        )

      elif tool_name == "update_cells":
        # Import core function from api module
        from .api import _update_cells_core, UpdateCellsRequest

        # Get updates from arguments
        updates = args.get("updates")
        if not updates:
          raise ValueError("Missing updates array")

        # Parse the spreadsheet URL to extract ID and gid
        raw_id = args.get("spreadsheetId") or sheet_context.spreadsheetId or ""
        parsed = parse_spreadsheet_url(raw_id)
        spreadsheet_id = parsed["spreadsheet_id"]
        gid = parsed["gid"]

        if not spreadsheet_id:
          raise ValueError("Missing spreadsheet ID")

        sheet_title = args.get("sheetTitle") or sheet_context.sheetTitle

        # If no sheet_title but gid is present, resolve it
        if not sheet_title and gid:
          sheet_title = self.sheets_client.get_sheet_title_by_gid(spreadsheet_id, gid)

        # Fall back to Sheet1 if still no title
        if not sheet_title:
          sheet_title = "Sheet1"

        create_snapshot = args.get("create_snapshot", True)

        try:
          # Create request object and call core function
          request = UpdateCellsRequest(
            updates=updates,
            spreadsheet_id=spreadsheet_id,
            sheet_title=sheet_title,
            create_snapshot=create_snapshot,
          )
          result = _update_cells_core(request)
        except Exception as exc:
          logger.error(f"update_cells failed: {str(exc)}", exc_info=True)
          raise RuntimeError(f"Failed to execute update_cells: {exc}")

        # Create tool response messages
        messages.append(
          ChatMessage(
            id=str(uuid.uuid4()),
            role="tool",
            content=result.get("message", "Cell update completed"),
            metadata={
              "toolName": "update_cells",
              "payload": result,
            },
          )
        )
        messages.append(
          ChatMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            content=self._summarize_update_cells_result(result),
          )
        )

      elif tool_name == "read_sheet":
        # Parse the spreadsheet URL to extract ID and gid
        raw_id = args.get("spreadsheetId") or sheet_context.spreadsheetId or ""
        parsed = parse_spreadsheet_url(raw_id)
        spreadsheet_id = parsed["spreadsheet_id"]
        gid = parsed["gid"]

        if not spreadsheet_id:
          raise ValueError("Missing spreadsheet ID")

        sheet_title = args.get("sheetTitle") or sheet_context.sheetTitle

        # If no sheet_title but gid is present, resolve it
        if not sheet_title and gid:
          sheet_title = self.sheets_client.get_sheet_title_by_gid(spreadsheet_id, gid)
          if not sheet_title:
            raise ValueError(f"Could not resolve sheet title from gid={gid}")

        if not sheet_title:
          raise ValueError("Missing sheet title (provide sheetTitle or a URL with gid)")

        # Get range - default to entire sheet if not specified
        range_a1 = args.get("range")
        if range_a1:
          # If range doesn't include sheet name, prepend it
          if "!" not in range_a1:
            range_a1 = f"{sheet_title}!{range_a1}"
        else:
          # Read entire sheet (up to 1000 rows by default for safety)
          range_a1 = f"{sheet_title}!A1:ZZ1000"

        try:
          result = self.sheets_client.read_range_with_formulas(spreadsheet_id, range_a1)

          # Count cells with formulas and values
          total_cells = 0
          formula_cells = 0
          non_empty_cells = 0
          for row in result.get("values", []):
            for cell in row:
              total_cells += 1
              if cell.get("formula"):
                formula_cells += 1
              if cell.get("value") is not None:
                non_empty_cells += 1

          messages.append(
            ChatMessage(
              id=str(uuid.uuid4()),
              role="tool",
              content=f"Read {non_empty_cells} cells from {range_a1} ({formula_cells} with formulas)",
              metadata={
                "toolName": "read_sheet",
                "payload": result,
              },
            )
          )
          messages.append(
            ChatMessage(
              id=str(uuid.uuid4()),
              role="assistant",
              content=self._summarize_read_sheet_result(result, formula_cells, non_empty_cells),
            )
          )
        except Exception as exc:
          logger.error(f"read_sheet failed: {str(exc)}", exc_info=True)
          raise RuntimeError(f"Failed to read sheet: {exc}")

      elif tool_name == "visualize_formulas":
        # Import the core visualize_formulas function directly (not the async endpoint)
        try:
          from tools.visualize_formulas import visualize_formulas
        except ImportError:
          raise RuntimeError(
            "visualize_formulas tool is not available. "
            "Ensure tools.visualize_formulas module is installed."
          )

        # Parse the spreadsheet URL to extract ID and gid
        raw_id = args.get("spreadsheetId") or sheet_context.spreadsheetId or ""

        if not raw_id:
          raise ValueError("Missing spreadsheet ID for visualize_formulas")

        # Call the core function directly (synchronous)
        try:
          result = visualize_formulas(sheet_url=raw_id)
        except Exception as exc:
          logger.error(f"visualize_formulas failed: {str(exc)}", exc_info=True)
          raise RuntimeError(f"Failed to visualize formulas: {exc}")

        # Create tool response messages
        messages.append(
          ChatMessage(
            id=str(uuid.uuid4()),
            role="tool",
            content=result.get("message", "Formula visualization completed"),
            metadata={
              "toolName": "visualize_formulas",
              "payload": result,
            },
          )
        )
        messages.append(
          ChatMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            content=self._summarize_visualize_formulas_result(result),
          )
        )

      else:
        raise ValueError(f"Unknown tool: {tool_name}")
    except Exception as exc:
      messages.append(
        ChatMessage(
          id=str(uuid.uuid4()),
          role="assistant",
          content=f"Failed to execute {tool_name}: {exc}",
          metadata={"error": str(exc)},
        )
      )

    return messages

  # --- formatting helpers ---

  @staticmethod
  def _format_chat_history(messages: List[ChatMessage]) -> str:
    lines: List[str] = []
    for msg in messages:
      role = msg.role
      if role == "user":
        label = "User"
        lines.append(f"{label}: {msg.content}")
      elif role == "assistant":
        label = "Assistant"
        lines.append(f"{label}: {msg.content}")
      elif role == "tool":
        # For tool messages, include the tool result data
        label = "System"
        tool_content = f"{label}: {msg.content}"

        # Include payload data for certain tools
        if msg.metadata and msg.metadata.payload:
          tool_name = msg.metadata.toolName if msg.metadata.toolName else "unknown"
          payload = msg.metadata.payload

          if tool_name == "read_sheet":
            # Include a sample of the sheet data
            values = payload.get("values", [])
            if values:
              sample_rows = min(10, len(values))
              tool_content += f"\n  Sheet data (first {sample_rows} rows):\n"
              for i, row in enumerate(values[:sample_rows]):
                # Show each cell with its value and formula (if present)
                row_data = []
                for cell in row:
                  if isinstance(cell, dict):
                    val = cell.get("value")
                    formula = cell.get("formula")
                    if formula:
                      row_data.append(f"{val} (formula: {formula})")
                    elif val is not None:
                      row_data.append(str(val))
                    else:
                      row_data.append("")
                  else:
                    row_data.append(str(cell) if cell is not None else "")
                tool_content += f"  Row {i+1}: {' | '.join(row_data[:10])}\n"  # Show first 10 columns

          elif tool_name == "detect_issues":
            # Include summary of detected issues
            potential_errors = payload.get("potential_errors", [])
            if potential_errors:
              tool_content += f"\n  Found {len(potential_errors)} issues"

        lines.append(tool_content)
      else:
        # Other roles (system, etc.)
        lines.append(f"System: {msg.content}")
    return "\n\n".join(lines)

  @staticmethod
  def _format_sheet_context(context: SheetContext) -> Optional[str]:
    if not context.spreadsheetId and not context.sheetTitle:
      return None
    lines: List[str] = []
    if context.spreadsheetId:
      lines.append(f"Spreadsheet ID: {context.spreadsheetId}")
    if context.sheetTitle:
      lines.append(f"Sheet Title: {context.sheetTitle}")
    return "\n".join(lines)

  @staticmethod
  def _summarize_detection_result(result: Dict[str, Any]) -> str:
    issues = result.get("issues") or []
    total = len(issues)
    if total == 0:
      return (
        "Great news! I analyzed your sheet and found no issues. "
        "The data looks clean and well-structured."
      )

    summary = result.get("summary") or {}
    by_severity = summary.get("bySeverity") or {}

    parts: List[str] = [f"I found {total} issue{'s' if total != 1 else ''} in your sheet:\n"]
    for sev in ["critical", "high", "medium", "low"]:
      count = by_severity.get(sev, 0)
      if count:
        parts.append(f"- {count} {sev} issue{'s' if count != 1 else ''}")

    parts.append("\nSee the detailed breakdown above for specific locations and suggested fixes.")
    return "\n".join(parts)

  @staticmethod
  def _summarize_modification_result(result: Dict[str, Any]) -> str:
    errors = result.get("errors") or []
    if errors:
      count = len(errors)
      return (
        f"I attempted the modification, but encountered {count} error{'s' if count != 1 else ''}. "
        "See the details above for more information."
      )

    actions = result.get("executedActions") or []
    action_count = len(actions)
    if action_count == 0:
      return (
        "I created a plan but didn't execute any actions. This might mean the requested changes "
        "were already in place or couldn't be applied."
      )

    summary_parts: List[str] = [f"Successfully executed {action_count} action{'s' if action_count != 1 else ''}. "]
    plan = result.get("plan") or {}
    if plan.get("intent"):
      summary_parts.append(f"Goal: {plan['intent']}")
    if result.get("summary"):
      summary_parts.append("\n\n" + str(result["summary"]))
    return "".join(summary_parts)

  @staticmethod
  def _summarize_creation_result(result: Dict[str, Any]) -> str:
    spreadsheet_id = result.get("spreadsheetId")
    plan = result.get("plan") or {}
    title = plan.get("title", "New Spreadsheet")
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}" if spreadsheet_id else ""

    summary = f"I've created a new spreadsheet: **{title}**\n\n"
    if spreadsheet_url:
      summary += f"[Open in Google Sheets]({spreadsheet_url})\n\n"

    sheets = plan.get("sheets") or []
    summary += f"The spreadsheet includes {len(sheets)} sheet{'s' if len(sheets) != 1 else ''} with structured columns and example data. "
    if plan.get("documentation"):
      summary += "A documentation sheet with usage instructions has also been added."
    return summary

  @staticmethod
  def _summarize_update_cells_result(result: Dict[str, Any]) -> str:
    status = result.get("status")
    count = result.get("count", 0)
    failed_updates = result.get("failed_updates") or []
    snapshot_id = result.get("snapshot_batch_id")

    if status == "error" or (count == 0 and failed_updates):
      return (
        f"I encountered errors while updating cells. "
        f"{len(failed_updates)} update{'s' if len(failed_updates) != 1 else ''} failed. "
        "Please check the error details or try a different approach."
      )

    if status == "partial_success":
      summary = (
        f"I successfully updated {count} cell{'s' if count != 1 else ''}, "
        f"but {len(failed_updates)} update{'s' if len(failed_updates) != 1 else ''} failed.\n\n"
      )
      if failed_updates:
        summary += "Failed updates:\n"
        for fail in failed_updates[:3]:  # Show first 3 failures
          cell_loc = fail.get("cell_location", "unknown")
          error = fail.get("error", "unknown error")
          summary += f"- {cell_loc}: {error}\n"
        if len(failed_updates) > 3:
          summary += f"... and {len(failed_updates) - 3} more\n"
    else:
      summary = f"Successfully updated {count} cell{'s' if count != 1 else ''}."

    if snapshot_id:
      summary += f"\n\nYou can undo these changes if needed (snapshot ID: {snapshot_id[:8]}...)."

    return summary

  @staticmethod
  def _summarize_read_sheet_result(result: Dict[str, Any], formula_cells: int, non_empty_cells: int) -> str:
    range_notation = result.get("a1Notation", "")
    values = result.get("values", [])

    total_rows = len(values)
    total_cols = max(len(row) for row in values) if values else 0

    summary = f"I've read the data from {range_notation}.\n\n"
    summary += f"Sheet contains {total_rows} row{'s' if total_rows != 1 else ''} × {total_cols} column{'s' if total_cols != 1 else ''}\n"
    summary += f"- {non_empty_cells} non-empty cell{'s' if non_empty_cells != 1 else ''}\n"
    summary += f"- {formula_cells} formula{'s' if formula_cells != 1 else ''}\n\n"

    if formula_cells > 0:
      summary += "The data includes both calculated values and their underlying formulas. "

    summary += "You can now ask me questions about this data or request modifications."

    return summary

  @staticmethod
  def _summarize_visualize_formulas_result(result: Dict[str, Any]) -> str:
    status = result.get("status")
    count = result.get("count", 0)
    snapshot_id = result.get("snapshot_batch_id")

    if status == "no_cells":
      return "No formulas or hard-coded numeric values were found on this sheet."

    summary = f"I've color-coded {count} cell{'s' if count != 1 else ''} on your sheet:\n"
    summary += "- Formulas are highlighted in green\n"
    summary += "- Hard-coded numeric values are highlighted in orange\n\n"
    summary += "This visual distinction helps identify which cells contain calculations versus raw data."

    if snapshot_id:
      summary += f"\n\nYou can restore the original colors if needed (snapshot ID: {snapshot_id[:8]}...)."

    return summary

