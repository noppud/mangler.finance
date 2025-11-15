from __future__ import annotations

import datetime as _dt
import uuid
from typing import Any, Dict, List

from .context_builder import ContextBuilder
from .llm import LLMClient, PROMPTS, format_sample_data, format_sheet_context


class MistakeDetector:
  """
  Port of the TypeScript MistakeDetector. Uses rule-based checks plus an LLM
  to detect potential issues in a Google Sheet.
  """

  def __init__(self, context_builder: ContextBuilder, llm_client: LLMClient) -> None:
    self.context_builder = context_builder
    self.llm_client = llm_client

  def detect_issues(
    self,
    spreadsheet_id: str,
    sheet_title: str,
    config: Dict[str, Any],
  ) -> Dict[str, Any]:
    context = self.context_builder.build_context(spreadsheet_id, sheet_title)
    issues: List[Dict[str, Any]] = []

    if config.get("enableRuleBased"):
      issues.extend(self._run_rule_based_checks(context, config))

    if config.get("enableLLMBased"):
      issues.extend(self._run_llm_based_checks(context, config))

    filtered = self._filter_by_severity(issues, config.get("minSeverity", "info"))
    max_issues = config.get("maxIssues")
    final_issues = filtered[:max_issues] if max_issues else filtered

    return {
      "spreadsheetId": spreadsheet_id,
      "sheetTitle": sheet_title,
      "issues": final_issues,
      "summary": self._generate_summary(final_issues),
      "scanTimestamp": _dt.datetime.utcnow().isoformat() + "Z",
    }

  # --- rule-based checks ---

  def _run_rule_based_checks(self, context: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    categories: List[str] = config.get("categoriesToCheck") or []

    if "formula_error" in categories:
      issues.extend(self._check_formula_errors(context))
    if "inconsistent_formula" in categories:
      issues.extend(self._check_inconsistent_formulas(context))
    if "type_mismatch" in categories:
      issues.extend(self._check_type_mismatches(context))
    if "missing_value" in categories:
      issues.extend(self._check_missing_values(context))
    if "duplicate_key" in categories:
      issues.extend(self._check_duplicate_keys(context))

    return issues

  def _check_formula_errors(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    summary = context.get("summary") or {}
    error_cells = summary.get("errorCells", 0)
    if error_cells <= 0:
      return []

    sheet_meta = context.get("sheetMetadata") or {}
    row_count = sheet_meta.get("rowCount", 0)

    return [
      {
        "id": str(uuid.uuid4()),
        "category": "formula_error",
        "severity": "high",
        "title": "Formula errors detected",
        "description": f"Found {error_cells} cells with formula errors (e.g., #REF!, #VALUE!, #DIV/0!).",
        "ranges": [
          {
            "a1Notation": f"1:{row_count}",
            "description": f"{error_cells} cell{'s' if error_cells > 1 else ''} with errors",
            "cellCount": error_cells,
          }
        ],
        "affectedCells": error_cells,
        "detectedBy": "rule",
        "suggestedFix": "Review and fix formula references and calculations.",
        "autoFixable": False,
      }
    ]

  def _check_inconsistent_formulas(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Placeholder: requires more detailed data analysis
    return []

  def _check_type_mismatches(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    table_regions = context.get("tableRegions") or []

    for region in table_regions:
      for col in region.get("columns") or []:
        if col.get("type") == "mixed":
          col_index = col.get("index", 0)
          col_letter = self._column_to_letter(col_index + 1)
          issues.append(
            {
              "id": str(uuid.uuid4()),
              "category": "type_mismatch",
              "severity": "medium",
              "title": f'Mixed data types in column "{col.get("name")}"',
              "description": "Column contains multiple data types. This may indicate data quality issues.",
              "ranges": [
                {
                  "a1Notation": f"{col_letter}:{col_letter}",
                  "description": f"Column {col_letter} ({col.get('name')})",
                }
              ],
              "detectedBy": "rule",
              "suggestedFix": "Standardize data types in this column.",
              "autoFixable": False,
            }
          )

    return issues

  def _check_missing_values(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    table_regions = context.get("tableRegions") or []

    for region in table_regions:
      for col in region.get("columns") or []:
        # Mirror TS heuristic: first 3 columns should not be nullable
        if col.get("nullable") and col.get("index", 0) < 3:
          col_index = col.get("index", 0)
          col_letter = self._column_to_letter(col_index + 1)
          issues.append(
            {
              "id": str(uuid.uuid4()),
              "category": "missing_value",
              "severity": "low",
              "title": f'Missing values in key column "{col.get("name")}"',
              "description": "Key column contains empty cells which may indicate incomplete data.",
              "ranges": [
                {
                  "a1Notation": f"{col_letter}:{col_letter}",
                  "description": f"Column {col_letter} ({col.get('name')})",
                }
              ],
              "detectedBy": "rule",
              "suggestedFix": "Fill in missing values or mark as N/A.",
              "autoFixable": False,
            }
          )

    return issues

  def _check_duplicate_keys(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Placeholder: would need full data scan to detect duplicates
    return []

  # --- LLM-based checks ---

  def _run_llm_based_checks(self, context: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
      context_str = format_sheet_context(context)
      sample_ranges = context.get("sampleData") or []
      if sample_ranges:
        sample_data_str = format_sample_data(sample_ranges[0].get("values") or [])
      else:
        sample_data_str = "No sample data"

      user_prompt = PROMPTS.MISTAKE_DETECTION.user(context_str, sample_data_str)

      response = self.llm_client.chat_json(
        [
          {"role": "system", "content": PROMPTS.MISTAKE_DETECTION.system},
          {"role": "user", "content": user_prompt},
        ],
        overrides={"temperature": 0.3},
      )

      issues: List[Dict[str, Any]] = []
      for item in response:
        ranges = item.get("ranges")
        if not ranges and item.get("location"):
          ranges = self._parse_location_to_ranges(item["location"])

        issues.append(
          {
            "id": str(uuid.uuid4()),
            "category": item.get("category"),
            "severity": item.get("severity"),
            "title": item.get("title"),
            "description": item.get("description"),
            "ranges": ranges or [],
            "detectedBy": "llm",
            "suggestedFix": item.get("suggestedFix"),
            "autoFixable": False,
            "confidence": item.get("confidence", 0.8),
          }
        )

      return issues
    except Exception:
      # In case of LLM failure, fall back silently (log could be added)
      return []

  @staticmethod
  def _parse_location_to_ranges(location: str) -> List[Dict[str, Any]]:
    # Simple fallback for legacy location string
    return [
      {
        "a1Notation": location,
        "description": location,
      }
    ]

  # --- helpers ---

  @staticmethod
  def _filter_by_severity(issues: List[Dict[str, Any]], min_severity: str) -> List[Dict[str, Any]]:
    severity_order = ["critical", "high", "medium", "low", "info"]
    try:
      min_index = severity_order.index(min_severity)
    except ValueError:
      min_index = len(severity_order) - 1

    filtered: List[Dict[str, Any]] = []
    for issue in issues:
      sev = issue.get("severity", "info")
      try:
        issue_index = severity_order.index(sev)
      except ValueError:
        issue_index = len(severity_order) - 1
      if issue_index <= min_index:
        filtered.append(issue)
    return filtered

  @staticmethod
  def _generate_summary(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    severities = ["critical", "high", "medium", "low", "info"]
    categories = [
      "formula_error",
      "inconsistent_formula",
      "type_mismatch",
      "outlier",
      "missing_value",
      "broken_reference",
      "duplicate_key",
      "constraint_violation",
      "semantic_anomaly",
      "logical_inconsistency",
      "suspicious_pattern",
    ]

    by_severity = {s: 0 for s in severities}
    by_category = {c: 0 for c in categories}
    auto_fixable_count = 0

    for issue in issues:
      sev = issue.get("severity")
      cat = issue.get("category")
      if sev in by_severity:
        by_severity[sev] += 1
      if cat in by_category:
        by_category[cat] += 1
      if issue.get("autoFixable"):
        auto_fixable_count += 1

    return {
      "totalIssues": len(issues),
      "bySeverity": by_severity,
      "byCategory": by_category,
      "autoFixableCount": auto_fixable_count,
    }

  @staticmethod
  def _column_to_letter(column: int) -> str:
    letter = ""
    while column > 0:
      remainder = (column - 1) % 26
      letter = chr(65 + remainder) + letter
      column = (column - 1) // 26
    return letter


