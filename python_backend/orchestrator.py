from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .creator import SheetCreator
from .llm import LLMClient, PROMPTS
from .mistake_detector import MistakeDetector
from .modifier import SheetModifier
from .context_builder import ContextBuilder
from .sheets_client import ServiceAccountSheetsClient
from .utils import normalize_spreadsheet_id
from .models import ChatMessage, SheetContext


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
    self.mistake_detector = MistakeDetector(context_builder, llm_client)
    self.sheet_modifier = SheetModifier(sheets_client, context_builder, llm_client)
    self.sheet_creator = SheetCreator(sheets_client, llm_client)

  def process_chat(
    self,
    messages: List[ChatMessage],
    sheet_context: SheetContext,
  ) -> List[ChatMessage]:
    try:
      chat_history = self._format_chat_history(messages)
      ctx_str = self._format_sheet_context(sheet_context)

      system_prompt = PROMPTS.AGENT.system
      user_prompt = PROMPTS.AGENT.user(chat_history, ctx_str)

      response: Dict[str, Any] = self.llm_client.chat_json(
        [
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": user_prompt},
        ],
        overrides={"maxTokens": 3000},
      )

      if not isinstance(response, dict):
        raise ValueError("Invalid response from LLM: expected JSON object")
      if "step" not in response or "assistantMessage" not in response:
        raise ValueError("Invalid response structure: missing step or assistantMessage")

      new_messages: List[ChatMessage] = []

      step = response["step"]
      if step == "answer":
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
          raise ValueError("Invalid tool call: missing tool or arguments")

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
      else:
        raise ValueError(f"Unknown step type: {step}")

      return new_messages
    except Exception as exc:
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
        spreadsheet_id = normalize_spreadsheet_id(
          args.get("spreadsheetId")
          or sheet_context.spreadsheetId
          or ""
        )
        sheet_title = args.get("sheetTitle") or sheet_context.sheetTitle
        if not spreadsheet_id:
          raise ValueError("Missing spreadsheet ID")
        if not sheet_title:
          raise ValueError("Missing sheet title")

        config_dict = args.get("config") or {}
        config = {
          "enableRuleBased": config_dict.get("includeRuleBased", True),
          "enableLLMBased": config_dict.get("includeLLMBased", True),
          "minSeverity": "info",
          "categoriesToCheck": [],
        }

        result = self.mistake_detector.detect_issues(spreadsheet_id, sheet_title, config)

        messages.append(
          ChatMessage(
            id=str(uuid.uuid4()),
            role="tool",
            content=f"Detected {len(result.get('issues') or [])} issue(s)",
            metadata={
              "toolName": "detect_issues",
              "payload": result,
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
        spreadsheet_id = normalize_spreadsheet_id(
          args.get("spreadsheetId")
          or sheet_context.spreadsheetId
          or ""
        )
        if not spreadsheet_id:
          raise ValueError("Missing spreadsheet ID")
        if not args.get("prompt"):
          raise ValueError("Missing modification prompt")

        modify_request = {
          "spreadsheetId": spreadsheet_id,
          "sheetTitle": args.get("sheetTitle") or sheet_context.sheetTitle,
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
      elif role == "assistant":
        label = "Assistant"
      else:
        label = "System"
      lines.append(f"{label}: {msg.content}")
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


