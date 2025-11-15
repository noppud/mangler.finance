from __future__ import annotations


def normalize_spreadsheet_id(raw: str) -> str:
  """
  Normalize a spreadsheet identifier that may be a bare ID or a full URL,
  mirroring the TypeScript normalizeSpreadsheetId helper.
  """
  if not raw:
    return raw

  trimmed = raw.strip()
  import re

  match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", trimmed)
  if match:
    return match.group(1)
  return trimmed


def column_to_letter(column: int) -> str:
  letter = ""
  while column > 0:
    remainder = (column - 1) % 26
    letter = chr(65 + remainder) + letter
    column = (column - 1) // 26
  return letter


