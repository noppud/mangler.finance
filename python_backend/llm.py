from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from .logging_config import get_logger

logger = get_logger(__name__)


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

    logger.debug(
        f"LLM API call: model={model}, messages={len(messages)}, max_tokens={max_tokens}",
        extra={"model": model, "message_count": len(messages), "max_tokens": max_tokens}
    )

    start_time = time.time()
    try:
      response = httpx.post(url, headers=self._build_headers(), json=payload, timeout=60.0)
      response.raise_for_status()
      duration_ms = int((time.time() - start_time) * 1000)

      logger.info(
          f"LLM API success: {duration_ms}ms",
          extra={"model": model, "duration_ms": duration_ms, "status_code": response.status_code}
      )
    except httpx.RequestError as exc:
      duration_ms = int((time.time() - start_time) * 1000)
      logger.error(
          f"LLM API request failed after {duration_ms}ms: {str(exc)}",
          exc_info=True,
          extra={"model": model, "duration_ms": duration_ms}
      )
      raise RuntimeError(f"LLM API request failed: {exc}") from exc
    except httpx.HTTPStatusError as exc:
      duration_ms = int((time.time() - start_time) * 1000)
      logger.error(
          f"LLM API error {exc.response.status_code} after {duration_ms}ms",
          exc_info=True,
          extra={
              "model": model,
              "status_code": exc.response.status_code,
              "duration_ms": duration_ms,
              "response_body": exc.response.text[:500]  # Truncate long responses
          }
      )
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

  def _detect_json_truncation(self, json_str: str) -> bool:
    """
    Detect if a JSON string appears to be truncated.
    Returns True if truncation is detected.
    """
    # Check for common truncation patterns
    truncation_indicators = [
      # Ends mid-key or mid-value
      json_str.endswith('"'),
      json_str.endswith(':'),
      json_str.endswith(','),
      # Unclosed brackets/braces
      json_str.count('{') > json_str.count('}'),
      json_str.count('[') > json_str.count(']'),
      # Ends with incomplete structure
      json_str.rstrip().endswith('",') and not json_str.rstrip().endswith('}'),
    ]

    return any(truncation_indicators)

  def chat_json(
    self,
    messages: List[Dict[str, str]],
    overrides: Optional[Dict[str, Any]] = None,
    max_retries: int = 1,
  ) -> Any:
    """
    Send a request expecting a JSON response string. Handles the case where the
    model wraps JSON in markdown code fences.

    Enhanced with robust error handling, truncation detection, and automatic retry.

    Args:
      messages: List of message dictionaries with 'role' and 'content'
      overrides: Optional overrides for LLM parameters
      max_retries: Number of times to retry if response is truncated (default: 1)
    """
    original_messages = messages.copy()

    for attempt in range(max_retries + 1):
      content = self.chat_text(messages, overrides)

      # Validate that we got some content
      if not content or not content.strip():
        logger.error(
          "LLM returned empty content when JSON was expected",
          extra={"messages_count": len(messages), "attempt": attempt + 1}
        )
        raise RuntimeError(
          "Failed to parse LLM response as JSON: Empty response received\n"
          "This may indicate the LLM failed to generate output or hit a token limit.\n"
          "Consider:\n"
          "1. Simplifying your request\n"
          "2. Reducing the amount of context provided\n"
          "3. Breaking the task into smaller steps"
        )

      json_str = content.strip()

      # Check for response length issues
      if len(content) > 15000:
        logger.warning(
          f"LLM response is very long ({len(content)} chars) - may hit token limits",
          extra={"content_length": len(content), "attempt": attempt + 1}
        )

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

      # Additional validation: check if response looks like JSON
      if not (json_str.startswith("{") or json_str.startswith("[")):
        logger.warning(
          "LLM response doesn't start with { or [ - may not be valid JSON",
          extra={"first_100_chars": json_str[:100]}
        )
        # Try to find the first { or [
        for char in ["{", "["]:
          if char in json_str:
            start_idx = json_str.index(char)
            logger.info(f"Found JSON start at position {start_idx}, extracting...")
            json_str = json_str[start_idx:]
            break

      # Detect truncation before attempting to parse
      if self._detect_json_truncation(json_str):
        logger.warning(
          f"Detected truncated JSON response on attempt {attempt + 1}",
          extra={
            "content_length": len(content),
            "last_50_chars": json_str[-50:],
            "attempt": attempt + 1
          }
        )

        if attempt < max_retries:
          # Retry with instructions to simplify
          logger.info("Retrying with simplified instructions...")
          messages = original_messages.copy()

          # Add simplification instruction to the last user message
          if messages and messages[-1].get("role") == "user":
            messages[-1]["content"] += (
              "\n\nIMPORTANT: Keep your response concise. "
              "Limit the number of actions and avoid repetitive formatting. "
              "Focus on the essential structure only."
            )
          continue
        else:
          raise RuntimeError(
            f"Failed to parse LLM response as JSON: Response appears truncated\n"
            f"Response length: {len(content)} chars\n"
            f"Last 100 chars: ...{json_str[-100:]}\n\n"
            f"The response is too long. Please:\n"
            f"1. Simplify your request to generate less data\n"
            f"2. Break the task into smaller steps\n"
            f"3. Reduce the number of rows/columns/actions requested"
          )

      try:
        parsed = json.loads(json_str)

        # Validate that we got a meaningful structure
        if isinstance(parsed, dict):
          # Check for common required fields based on context
          if "actions" in parsed and not isinstance(parsed["actions"], list):
            logger.warning("Parsed JSON has 'actions' field but it's not a list")

        logger.info(
          f"Successfully parsed JSON response on attempt {attempt + 1}",
          extra={"content_length": len(content)}
        )
        return parsed

      except json.JSONDecodeError as exc:
        # Enhanced error message with debugging info
        logger.error(
          f"JSON parsing failed on attempt {attempt + 1}: {exc}",
          extra={
            "error_line": exc.lineno,
            "error_col": exc.colno,
            "error_msg": exc.msg,
            "content_length": len(content),
            "json_str_length": len(json_str),
            "attempt": attempt + 1
          }
        )

        # If we have retries left and this looks like a length issue, retry
        if attempt < max_retries and len(content) > 10000:
          logger.info(f"Retrying due to large response ({len(content)} chars)...")
          messages = original_messages.copy()

          # Add simplification instruction to the last user message
          if messages and messages[-1].get("role") == "user":
            messages[-1]["content"] += (
              "\n\nIMPORTANT: Keep your response SHORT and CONCISE. "
              "Generate FEWER actions (maximum 5-10). "
              "Avoid repetitive formatting actions. "
              "Focus ONLY on the essential data structure."
            )
          continue

        # Provide detailed error message
        error_context = json_str[max(0, exc.pos - 50):min(len(json_str), exc.pos + 50)]
        raise RuntimeError(
          f"Failed to parse LLM response as JSON after {attempt + 1} attempt(s): {exc}\n"
          f"Error at line {exc.lineno}, column {exc.colno}: {exc.msg}\n"
          f"Context around error: ...{error_context}...\n\n"
          f"Response length: {len(content)} chars\n\n"
          f"Suggestions:\n"
          f"1. The LLM may have generated invalid JSON - try again\n"
          f"2. The response is too long (current: {len(content)} chars) - simplify your request\n"
          f"3. Break the task into smaller steps (e.g., create data first, format later)\n"
          f"4. Reduce the number of rows/columns/actions requested"
        ) from exc

    # If we get here, all retries failed
    raise RuntimeError(
      f"Failed to parse LLM response as JSON after {max_retries + 1} attempts\n"
      f"Please simplify your request and try again"
    )


def _load_env_from_local_files() -> None:
  """
  Load environment variables from local .env-style files if they exist.

  This lets the Python backend reuse the same config as the Next.js app
  (e.g. sheet-mangler/.env.local) without requiring manual exports, and
  also supports python_backend-local .env files.
  """
  try:
    backend_root = Path(__file__).resolve().parent
    repo_root = backend_root.parent
  except Exception:
    return

  candidates = [
    # Prefer project-local env files
    backend_root / ".env.local",
    backend_root / ".env",
    # Then repo-root env files
    repo_root / ".env.local",
    repo_root / ".env",
    # Finally, reuse the Next.js app config if present
    repo_root / "sheet-mangler" / ".env.local",
  ]

  for env_path in candidates:
    if not env_path.exists():
      continue
    try:
      for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
          continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        # Do not override values already set in the process environment
        if key and key not in os.environ:
          os.environ[key] = value
    except Exception:
      # If parsing fails for any reason, skip this file and try the next
      continue


def create_llm_client() -> LLMClient:
  # Ensure env vars are populated from local config files if present
  _load_env_from_local_files()

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
      "Your task is to identify 0-5 of potential issues, errors, and anomalies in Google Sheets data.\n\n"
      "You should focus on most impactful issues, look for:\n"
      "1. Logical inconsistencies (e.g., negative ages, future dates where they shouldn't be)\n"
      "2. Semantic anomalies (e.g., country names in age columns)\n"
      "3. Suspicious patterns (e.g., duplicates, outliers)\n"
      "4. Data quality issues (e.g., missing required values, type mismatches)\n"
      "5. Formula issues:\n"
      "   - Broken references (#REF, #ERROR, #NAME)\n"
      "   - Inconsistent formulas in rows/columns (e.g., row 5 uses SUM(A1:A4) but row 6 uses SUM(B1:B5))\n"
      "   - Formula pattern breaks (e.g., cells A2:A10 all use SUM except A7 which is hardcoded)\n"
      "   - Different formula structures for same calculation type (e.g., mixing =A1+A2 and =SUM(A1:A2))\n"
      "   - Range inconsistencies (e.g., =SUM(A1:A10) in B5 but =SUM(A1:A9) in B6)\n"
      "   - Missing formulas where pattern suggests one should exist\n\n"
      "Return your findings as a JSON array of issues, each with:\n"
      "- category: the type of issue (formula_error, inconsistent_formula, type_mismatch, outlier, missing_value, broken_reference, duplicate_key, constraint_violation, semantic_anomaly, logical_inconsistency, suspicious_pattern)\n"
      "- severity: 'critical' | 'high' | 'medium' | 'low' | 'info'\n"
      "- title: short description\n"
      "- description: detailed explanation of the issue and its context\n"
      "- ranges: array of structured ranges, each with:\n"
      "  - a1Notation: SINGLE cell or contiguous range in A1 notation (e.g., \"A7\", \"B2:D5\", \"3:6\" for rows, \"B:B\" for column)\n"
      "    IMPORTANT: If issue affects multiple non-contiguous cells, create SEPARATE range objects - do NOT use commas (e.g., WRONG: \"H26, V26, I51\", CORRECT: separate objects for H26, V26, I51)\n"
      "  - description: human-readable location (e.g., \"Cell A7\", \"Rows 3-6\", \"Column B\", \"Cells H26, V26, I51\")\n"
      "  - cellCount: number of cells affected (optional)\n"
      "- suggestedFix: DECISIVE and SPECIFIC action to take (e.g., \"Change C5 from 400000 to 4000\" not \"Verify the value\")\n"
      "- confidence: 0-1 score of how confident you are\n\n"
      "IMPORTANT GUIDELINES FOR SUGGESTED FIXES:\n"
      "- Be SPECIFIC and ACTIONABLE: Say \"Change C5 to 4000\" not \"Verify and correct C5\"\n"
      "- Make REASONABLE ASSUMPTIONS based on context:\n"
      "  * For outliers 100x-1000x different: Suggest removing extra zeros to match neighbor magnitude\n"
      "  * For broken references (#REF, #ERROR): Suggest clearing the cell or removing the formula\n"
      "  * For incomplete data: Suggest the most likely completion based on pattern\n"
      "  * For formatting issues: Suggest the standard format\n"
      "- Include the EXACT correction in your suggestedFix\n"
      "- Examples of GOOD suggestedFix:\n"
      "  ✓ \"Change C5 from 400000 to 4000 SEK to match the scale of adjacent hourly rates (900-1200 SEK)\"\n"
      "  ✓ \"Clear the broken formula in A7 (currently shows #REF error)\"\n"
      "  ✓ \"Complete phone number O2 from +358501968 to +358501968XXX (Finnish format)\"\n"
      "- Examples of BAD suggestedFix:\n"
      "  ✗ \"Verify the hourly price in C5\"\n"
      "  ✗ \"Review the formula in A7 and correct the broken reference\"\n"
      "  ✗ \"Check if the phone number is complete\"\n\n"
      "Always provide specific cell ranges in A1 notation and decisive suggested fixes."
    )

    @staticmethod
    def user(context: str, sample_data: str) -> str:
      return f"# Sheet Context\n\n{context}\n\n# Sample Data\n\n{sample_data}\n\nAnalyze this sheet and identify any issues, errors, or anomalies. Return a JSON array of issues."

  class MODIFICATION_PLAN:
    system: str = (
      "You are a spreadsheet automation assistant. Create simple, robust tables with values and formulas.\n\n"
      "🚫 CRITICAL: NO FORMATTING ACTIONS 🚫\n"
      "- ONLY insert VALUES and FORMULAS\n"
      "- NO bold, colors, fonts, number formats, or styling\n"
      "- Formatting actions will FAIL with 'Unsupported action type' error\n\n"
      "SUPPORTED ACTIONS:\n"
      "- batch_update: Set multiple cells at once (values and/or formulas)\n"
      "- set_value: Set a single cell value\n"
      "- update_formula: Update formulas in a range\n"
      "- clear_range: Clear cells\n"
      "- add_column: Add a column\n"
      "- rename_column: Rename a column header\n\n"
      "BE CAREFUL AND PRECISE:\n"
      "- Double-check cell references in formulas (e.g., =SUM(D4:D15), =F4+C5)\n"
      "- Verify formula logic matches the data structure\n"
      "- Use batch_update for efficiency when setting multiple cells\n"
      "- Keep responses concise - typically 1-2 actions total\n\n"
      "EXAMPLE - Simple hiring table:\n"
      "User asks: \"Create a hiring plan for months 1-3\"\n\n"
      "Good response:\n"
      "{\n"
      '  "intent": "Create hiring plan table with columns and formulas",\n'
      '  "actions": [{\n'
      '    "type": "batch_update",\n'
      '    "description": "Create table with headers, hires, and summary",\n'
      '    "params": {\n'
      '      "updates": [\n'
      '        {cell: "A1", value: "Month"},\n'
      '        {cell: "B1", value: "Role"},\n'
      '        {cell: "C1", value: "Salary"},\n'
      '        {cell: "A2", value: 1},\n'
      '        {cell: "B2", value: "CTO"},\n'
      '        {cell: "C2", value: 8000},\n'
      '        {cell: "A3", value: 2},\n'
      '        {cell: "B3", value: "Engineer"},\n'
      '        {cell: "C3", value: 8400},\n'
      '        {cell: "A4", value: 3},\n'
      '        {cell: "B4", value: "Engineer"},\n'
      '        {cell: "C4", value: 7500},\n'
      '        {cell: "A6", value: "Total"},\n'
      '        {cell: "B6", value: "=SUM(C2:C4)", is_formula: true}\n'
      "      ]\n"
      "    },\n"
      '    "affectedRange": "A1:C6"\n'
      "  }]\n"
      "}\n\n"
      "Return JSON with this structure:\n"
      "{\n"
      '  "intent": "brief description",\n'
      '  "actions": [{type: "...", params: {...}, description: "...", affectedRange: "..."}],\n'
      '  "warnings": []\n'
      "}\n\n"
      "Remember: Be CAREFUL with formulas. If user asks for formatting, ignore it and only add data."
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
      "modify existing sheets through a conversational interface. You can ONLY work with the CURRENT sheet - "
      "you CANNOT create new sheets or delete sheets.\n\n"
      "You have six tools: detect_issues, modify_sheet, update_cells, read_sheet, visualize_formulas.\n\n"
      "**modify_sheet** is the PREFERRED tool for creating complex layouts, tables, or simulations. "
      "It now uses efficient batch operations internally, so it can handle large setups (20+ cells) efficiently. "
      "Use this for: creating tables, setting up simulations, restructuring data, adding multiple formulas.\n\n"
      "**update_cells** is for targeted fixes - updating specific cells when you already know exactly what to change. "
      "Use this for: fixing detected issues, correcting specific values, updating individual formulas.\n\n"
      "**read_sheet** reads the current values AND formulas from a sheet range. Use this when you need to examine specific data, "
      "understand formulas, or answer questions about the sheet contents that aren't covered by the context provided.\n\n"
      "**visualize_formulas** color-codes cells on a sheet to visually distinguish formulas (green) from hard-coded numeric values (orange). "
      "Use this tool when the user wants to see which cells contain formulas vs. hardcoded values, or when debugging formula patterns. "
      "This tool creates a snapshot for undo and returns the number of cells colored.\n\n"
      "Always respond with **JSON only** (no markdown, no natural language outside JSON) using this schema:\n"
      "{\n"
      '  "step": "answer" | "tool_call",\n'
      '  "assistantMessage": "string",\n'
      '  "tool": {\n'
      '    "name"?: "detect_issues" | "modify_sheet" | "create_sheet" | "update_cells" | "read_sheet" | "visualize_formulas",\n'
      '    "arguments"?: {\n'
      '      // For detect_issues:\n'
      '      "spreadsheetId"?: "string",\n'
      '      "sheetTitle"?: "string",\n'
      '      "config"?: {\n'
      '        "includeRuleBased"?: true | false,\n'
      '        "includeLLMBased"?: true | false\n'
      '      },\n\n'
      '      // For modify_sheet:\n'
      '      "prompt"?: "string",\n'
      '      "constraints"?: { },\n\n'
      '      // For update_cells (fixing specific issues):\n'
      '      "updates"?: [\n'
      '        {\n'
      '          "cell_location": "A1 notation like A1 or B2:C5",\n'
      '          "value": "new value (string, number, boolean, or null to clear)",\n'
      '          "is_formula": false  // set to true if value is a formula like =SUM(A1:B2)\n'
      '        }\n'
      '      ],\n'
      '      "create_snapshot"?: true,  // defaults to true, allows undo\n\n'
      '      // For read_sheet (reading values and formulas):\n'
      '      "spreadsheetId"?: "string",\n'
      '      "sheetTitle"?: "string",\n'
      '      "range"?: "A1:C10"  // optional, defaults to entire sheet if omitted\n\n'
      '      // For visualize_formulas (color-code formulas vs values):\n'
      '      "spreadsheetId"?: "string"  // The spreadsheet URL or ID to visualize\n'
      "    }\n"
      "  }\n"
      "}\n\n"
      "**Tool Selection Guidelines:**\n"
      "- Use **read_sheet** when:\n"
      "  - User asks questions about their business, data, or spreadsheet content (\"Is this a good business?\", \"What is my revenue?\", etc.)\n"
      "  - User asks \"what is the spreadsheet about\" or similar questions\n"
      "  - You need to see data/formulas to answer ANY question about the sheet\n"
      "  - IMPORTANT: If you've already used read_sheet in this conversation, check the conversation history for the data - DO NOT call read_sheet again unless the user asks for updated data\n"
      "- Use **detect_issues** when user explicitly asks to find/detect/analyze issues or errors\n"
      "- Use **modify_sheet** for: \n"
      "  - Creating tables, layouts, or simulations with many cells (uses efficient batching)\n"
      "  - Setting up complex structures with headers, formulas, and data\n"
      "  - Restructuring data or adding validation rules\n"
      "  - Any task requiring 10+ cell modifications\n"
      "- Use **update_cells** for: \n"
      "  - Fixing specific detected issues (broken references, data entry errors)\n"
      "  - Targeted updates to 1-5 known cells\n"
      "  - Correcting phone numbers, fixing formulas, clearing error cells\n"
      "- Use **visualize_formulas** when user wants to see/highlight which cells are formulas vs hardcoded values, or when helping debug formula patterns\n\n"
      "**CRITICAL - ANSWERING WITH PREVIOUS DATA:**\n"
      "- When you've already called read_sheet or detect_issues earlier in the conversation, the tool results are in the conversation history\n"
      "- LOOK AT THE CONVERSATION HISTORY and use that data to answer follow-up questions\n"
      "- DO NOT say \"I've read the data\" again - actually ANALYZE and DESCRIBE what you found\n"
      "- Example: If user asks \"What is the spreadsheet about\" after you read it, explain what you saw (e.g., \"This is a financial model with revenue projections, expenses, and profit margins across 24 columns\")\n\n"
      "**CRITICAL - PROACTIVE FIXING BEHAVIOR:**\n"
      "- When the user asks you to \"fix\" an issue, take IMMEDIATE action - do NOT ask for confirmation\n"
      "- Make REASONABLE ASSUMPTIONS based on context and surrounding data\n"
      "- For outliers: If a value is 100x-1000x different from neighbors, assume it's a data entry error (extra zeros, missing decimal)\n"
      "- For broken references: Clear them immediately (set to null)\n"
      "- For formatting issues: Apply the most common/standard format\n"
      "- For missing data: Use the pattern from adjacent cells or leave empty if unclear\n"
      "- ALWAYS explain your reasoning in assistantMessage, but EXECUTE the fix immediately\n"
      "- Example: \"I'm correcting C5 from 400000 to 4000 SEK based on the adjacent hourly rates (900-1200 SEK). This appears to be a data entry error with extra zeros.\"\n\n"
      "**Decision-Making for Ambiguous Cases:**\n"
      "- Outlier 100-1000x higher: Remove extra zeros to match magnitude of neighbors\n"
      "- Outlier 10-100x higher: Divide by 10 to match scale\n"
      "- Outlier with pattern: If neighbors are 900, 1100, 1200, and outlier is 400000, the most likely correct value is 400 or 4000 (based on scale)\n"
      "- Phone numbers: Complete with standard format for the country\n"
      "- Dates: Convert Excel serial numbers to readable dates\n"
      "- Headers: Use descriptive names matching the data type\n\n"
      "- For simple conversational replies, use step=\"answer\" and ignore the tool field.\n"
      "- To call a tool, use step=\"tool_call\" and set tool.name and tool.arguments appropriately.\n"
      "- When fixing issues, ALWAYS batch multiple related fixes into a single update_cells call for efficiency.\n"
      "- Ask the user for missing spreadsheetId or sheetTitle if needed before calling tools.\n"
      "- BE DECISIVE AND PROACTIVE: The user wants fixes applied immediately, not discussions about what to fix."
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
  Includes both formulas and values when available.
  """
  if not sample_data:
    return "No data"

  formatted = ""
  for idx, row in enumerate(sample_data):
    # Format each cell: show formula if present, then value
    cell_strings = []
    for cell in row:
      cell_dict = cell or {}
      formula = cell_dict.get("formula")
      value = cell_dict.get("value", "")
      
      if formula:
        # Show formula and its result: "=SUM(A1:A5) → 100"
        cell_str = f"{formula} → {json.dumps(value)}"
      else:
        # Just show the value
        cell_str = json.dumps(value)
      
      cell_strings.append(cell_str)
    
    formatted += f"Row {idx + 1}: " + " | ".join(cell_strings) + "\n"

  return formatted
