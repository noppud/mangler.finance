from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import httpx


class LLMClient:
  """
  Minimal HTTP client for OpenRouter's chat completions API, similar in spirit
  to the existing TypeScript LLMClient.
  """

  def __init__(
    self,
    api_key: str,
    model: str,
    base_url: str = "https://openrouter.ai/api/v1",
    temperature: float = 0.7,
    max_tokens: int = 4000,
    headers: Optional[Dict[str, str]] = None,
  ) -> None:
    self.api_key = api_key
    self.model = model
    self.base_url = base_url.rstrip("/")
    self.temperature = temperature
    self.max_tokens = max_tokens
    self.headers = headers or {}

  def _build_headers(self) -> Dict[str, str]:
    base = {
      "Authorization": f"Bearer {self.api_key}",
      "Content-Type": "application/json",
    }
    base.update(self.headers)
    return base

  def chat(
    self,
    messages: List[Dict[str, str]],
    overrides: Optional[Dict[str, Any]] = None,
  ) -> Dict[str, Any]:
    """
    Send a chat completion request and return the raw JSON response.
    """
    overrides = overrides or {}
    model = overrides.get("model", self.model)
    temperature = overrides.get("temperature", self.temperature)
    max_tokens = overrides.get("maxTokens", self.max_tokens)

    payload = {
      "model": model,
      "messages": messages,
      "temperature": temperature,
      "max_tokens": max_tokens,
    }

    url = f"{self.base_url}/chat/completions"

    try:
      response = httpx.post(url, headers=self._build_headers(), json=payload, timeout=60.0)
      response.raise_for_status()
    except httpx.RequestError as exc:
      raise RuntimeError(f"LLM API request failed: {exc}") from exc
    except httpx.HTTPStatusError as exc:
      raise RuntimeError(f"LLM API returned error {exc.response.status_code}: {exc.response.text}") from exc

    return response.json()

  def chat_text(
    self,
    messages: List[Dict[str, str]],
    overrides: Optional[Dict[str, Any]] = None,
  ) -> str:
    data = self.chat(messages, overrides)
    choices = data.get("choices") or []
    if not choices:
      raise RuntimeError("LLM API returned no choices")
    content = choices[0].get("message", {}).get("content", "")
    return content or ""

  def chat_json(
    self,
    messages: List[Dict[str, str]],
    overrides: Optional[Dict[str, Any]] = None,
  ) -> Any:
    """
    Send a request expecting a JSON response string. Handles the case where the
    model wraps JSON in markdown code fences.
    """
    content = self.chat_text(messages, overrides)

    json_str = content.strip()
    # Extract JSON from markdown code blocks if present
    if "```" in json_str:
      try:
        # Look for ```json ... ``` or ``` ... ```
        start = json_str.index("```")
        end = json_str.rindex("```")
        block = json_str[start + 3 : end]
        # Strip optional language tag
        if block.lstrip().startswith("json"):
          block = block.lstrip()[4:]
        json_str = block.strip()
      except ValueError:
        # Fallback to original content
        pass

    try:
      return json.loads(json_str)
    except json.JSONDecodeError as exc:
      raise RuntimeError(f"Failed to parse LLM response as JSON: {exc}\nContent was:\n{content}") from exc


def create_llm_client() -> LLMClient:
  api_key = os.getenv("OPENROUTER_API_KEY")
  if not api_key:
    raise RuntimeError("OPENROUTER_API_KEY environment variable not set")

  model = os.getenv("DEFAULT_LLM_MODEL", "anthropic/claude-haiku-4.5")

  headers: Dict[str, str] = {}
  site_url = os.getenv("OPENROUTER_SITE_URL")
  site_name = os.getenv("OPENROUTER_SITE_NAME")
  if site_url:
    headers["HTTP-Referer"] = site_url
  if site_name:
    headers["X-Title"] = site_name

  base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

  return LLMClient(
    api_key=api_key,
    model=model,
    base_url=base_url,
    temperature=0.7,
    max_tokens=4000,
    headers=headers,
  )


# --- Prompt templates (ported from TypeScript) ---


class PROMPTS:
  class MISTAKE_DETECTION:
    system: str = (
      "You are an expert data analyst specializing in spreadsheet quality assurance. "
      "Your task is to identify potential issues, errors, and anomalies in Google Sheets data.\n\n"
      "You should look for:\n"
      "1. Logical inconsistencies (e.g., negative ages, future dates where they shouldn't be)\n"
      "2. Semantic anomalies (e.g., country names in age columns)\n"
      "3. Suspicious patterns (e.g., duplicates, outliers)\n"
      "4. Data quality issues (e.g., missing required values, type mismatches)\n"
      "5. Formula issues (e.g., broken references, inconsistent formulas)\n\n"
      "Return your findings as a JSON array of issues, each with:\n"
      "- category: the type of issue (formula_error, inconsistent_formula, type_mismatch, outlier, missing_value, broken_reference, duplicate_key, constraint_violation, semantic_anomaly, logical_inconsistency, suspicious_pattern)\n"
      "- severity: 'critical' | 'high' | 'medium' | 'low' | 'info'\n"
      "- title: short description\n"
      "- description: detailed explanation\n"
      "- ranges: array of structured ranges, each with:\n"
      "  - a1Notation: cell or range in A1 notation (e.g., \"A7\", \"B2:D5\", \"3:6\" for rows, \"B:B\" for column)\n"
      "  - description: human-readable location (e.g., \"Cell A7\", \"Rows 3-6\", \"Column B\", \"Columns B, D, F, H\")\n"
      "  - cellCount: number of cells affected (optional)\n"
      "- suggestedFix: optional recommendation\n"
      "- confidence: 0-1 score of how confident you are\n\n"
      "IMPORTANT: Always provide specific cell ranges in A1 notation."
    )

    @staticmethod
    def user(context: str, sample_data: str) -> str:
      return f"# Sheet Context\n\n{context}\n\n# Sample Data\n\n{sample_data}\n\nAnalyze this sheet and identify any issues, errors, or anomalies. Return a JSON array of issues."

  class MODIFICATION_PLAN:
    system: str = (
      "You are an expert spreadsheet automation assistant. Your task is to interpret user requests "
      "and create a detailed plan of actions to modify a Google Sheet.\n\n"
      "Available actions:\n"
      "- add_column: Add a new column\n"
      "- remove_column: Remove a column\n"
      "- rename_column: Rename a column header\n"
      "- update_formula: Update or add formulas\n"
      "- normalize_data: Clean and standardize data\n"
      "- reformat_cells: Change formatting\n"
      "- add_validation: Add data validation rules\n"
      "- fix_error: Fix specific errors\n"
      "- sort_range: Sort data\n"
      "- set_value: Set specific cell values\n"
      "- clear_range: Clear a range of cells\n\n"
      "Return a JSON plan with:\n"
      "{\n"
      '  "intent": "brief description of what user wants",\n'
      '  "actions": [\n'
      "    {\n"
      '      "type": "action_type",\n'
      '      "description": "what this action does",\n'
      '      "params": { /* action-specific parameters */ },\n'
      '      "affectedRange": "A1:Z100",\n'
      '      "estimatedImpact": {\n'
      '        "rowsAffected": 100,\n'
      '        "columnsAffected": 2,\n'
      '        "destructive": false\n'
      "      }\n"
      "    }\n"
      "  ],\n"
      '  "warnings": ["any potential issues or data loss warnings"]\n'
      "}\n\n"
      "Be conservative and warn about destructive operations."
    )

    @staticmethod
    def user(user_prompt: str, context: str) -> str:
      return f"# User Request\n\n{user_prompt}\n\n# Sheet Context\n\n{context}\n\nCreate a detailed action plan to fulfill the user's request. Return JSON only."

  class SHEET_CREATION:
    system: str = (
      "You are an expert spreadsheet designer. Your task is to design Google Sheets structures based on user requirements.\n\n"
      "Create a comprehensive spreadsheet design including:\n"
      "- Multiple sheets/tabs if needed\n"
      "- Column structure with appropriate data types\n"
      "- Data validation rules where applicable\n"
      "- Example formulas for calculations\n"
      "- Sample rows to illustrate the structure\n\n"
      "Return a JSON plan with:\n"
      "{\n"
      '  "title": "spreadsheet title",\n'
      '  "sheets": [\n'
      "    {\n"
      '      "name": "sheet name",\n'
      '      "purpose": "what this sheet is for",\n'
      '      "columns": [\n'
      "        {\n"
      '          "name": "column name",\n'
      '          "type": "string | number | boolean | date | formula",\n'
      '          "validation": "optional validation rule",\n'
      '          "formula": "optional formula template"\n'
      "        }\n"
      "      ],\n"
      '      "exampleRows": [\n'
      '        ["value1", "value2", ...]\n'
      "      ]\n"
      "    }\n"
      "  ],\n"
      '  "documentation": "optional readme content"\n'
      "}"
    )

    @staticmethod
    def user(user_prompt: str, constraints: Optional[str] = None) -> str:
      constraints_part = f"\n\n# Constraints\n\n{constraints}" if constraints else ""
      return f"# User Request\n\n{user_prompt}{constraints_part}\n\nDesign the spreadsheet and return JSON only."

  class AGENT:
    system: str = (
      "You are Sheet Mangler, an AI assistant for working with Google Sheets. You help users detect issues, "
      "modify existing sheets, and create new spreadsheets through a conversational interface.\n\n"
      "You have three tools: detect_issues, modify_sheet, create_sheet. Follow the response format described "
      "in the original system prompt and ALWAYS return JSON only with either step='answer' or step='tool_call'."
    )

    @staticmethod
    def user(chat_history: str, sheet_context: Optional[str] = None) -> str:
      prompt = "# Conversation History\n\n" + chat_history
      if sheet_context:
        prompt += "\n\n# Current Sheet Context\n\n" + sheet_context
      prompt += "\n\nRespond with JSON only following the format specified in your system prompt."
      return prompt


def format_sheet_context(context: Any) -> str:
  """
  Helper to format sheet context for LLM (ported from TS).
  """
  if isinstance(context, str):
    return context

  formatted = ""

  sheet_meta = context.get("sheetMetadata")
  if sheet_meta:
    formatted += f"Sheet: {sheet_meta.get('title')}\n"
    formatted += f"Size: {sheet_meta.get('rowCount')} rows × {sheet_meta.get('columnCount')} columns\n\n"

  table_regions = context.get("tableRegions") or []
  if table_regions:
    formatted += "Columns:\n"
    for col in table_regions[0].get("columns", []):
      formatted += f"- {col.get('name')} ({col.get('type')})\n"
    formatted += "\n"

  summary = context.get("summary")
  if summary:
    formatted += "Summary:\n"
    formatted += f"- Total cells: {summary.get('totalCells')}\n"
    formatted += f"- Formula cells: {summary.get('formulaCells')}\n"
    formatted += f"- Error cells: {summary.get('errorCells')}\n\n"

  return formatted


def format_sample_data(sample_data: Any) -> str:
  """
  Helper to format sample data for LLM (ported from TS).
  """
  if not sample_data:
    return "No data"

  formatted = ""
  for idx, row in enumerate(sample_data):
    # In our context builder, each cell is a dict with a 'value'
    values = [json.dumps((cell or {}).get("value", "")) for cell in row]
    formatted += f"Row {idx + 1}: " + " | ".join(values) + "\n"

  return formatted


