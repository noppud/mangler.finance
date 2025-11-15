from __future__ import annotations

from typing import Any, Dict, List

from .sheets_client import ServiceAccountSheetsClient


class ContextBuilder:
  """
  Build contextual information about a sheet, ported from the TypeScript
  ContextBuilder. Works with the dictionary-shaped structures returned by
  ServiceAccountSheetsClient.
  """

  def __init__(self, client: ServiceAccountSheetsClient) -> None:
    self.client = client

  def build_context(self, spreadsheet_id: str, sheet_title: str) -> Dict[str, Any]:
    metadata = self.client.get_spreadsheet_metadata(spreadsheet_id)
    sheet_meta = next(
      (s for s in metadata.get("sheets", []) if s.get("title") == sheet_title),
      None,
    )
    if not sheet_meta:
      raise ValueError(f'Sheet "{sheet_title}" not found')

    col_count = sheet_meta.get("columnCount", 0)
    row_count = sheet_meta.get("rowCount", 0)
    range_a1 = f"{sheet_title}!A1:{self._column_to_letter(col_count)}{row_count}"
    data = self.client.read_range_with_formulas(spreadsheet_id, range_a1)

    table_regions = self._detect_table_regions(data)
    summary = self._generate_summary(data)
    sample_data = self._sample_data(data, top_n=10)

    return {
      "metadata": metadata,
      "sheetMetadata": sheet_meta,
      "tableRegions": table_regions,
      "summary": summary,
      "sampleData": sample_data,
    }

  def build_lightweight_context(self, spreadsheet_id: str, sheet_title: str) -> Dict[str, Any]:
    metadata = self.client.get_spreadsheet_metadata(spreadsheet_id)
    sheet_meta = next(
      (s for s in metadata.get("sheets", []) if s.get("title") == sheet_title),
      None,
    )
    if not sheet_meta:
      raise ValueError(f'Sheet "{sheet_title}" not found')

    col_count = min(sheet_meta.get("columnCount", 0), 26)
    range_a1 = f"{sheet_title}!A1:{self._column_to_letter(col_count)}100"
    data = self.client.read_range(spreadsheet_id, range_a1)

    summary = self._generate_summary(data)

    return {
      "metadata": metadata,
      "sheetMetadata": sheet_meta,
      "summary": summary,
    }

  # --- internals ---

  def _detect_table_regions(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    regions: List[Dict[str, Any]] = []
    rows: List[List[Dict[str, Any]]] = data.get("values") or []

    if not rows:
      return regions

    header_row_index = -1
    for i in range(min(10, len(rows))):
      row = rows[i]
      non_empty = len([cell for cell in row if cell.get("value") is not None])
      strings = len([cell for cell in row if cell.get("type") == "string"])
      if non_empty > 0 and strings / non_empty > 0.7:
        header_row_index = i
        break

    if header_row_index == -1:
      # No clear header; treat entire sheet as single region without headers
      columns = self._infer_columns(data, header_row_index)
      regions.append(
        {
          "range": data,
          "hasHeaders": False,
          "dataStartRow": 0,
          "columns": columns,
        }
      )
      return regions

    data_start_row = header_row_index + 1
    columns = self._infer_columns(data, header_row_index)
    regions.append(
      {
        "range": data,
        "hasHeaders": True,
        "headerRow": header_row_index,
        "dataStartRow": data_start_row,
        "columns": columns,
      }
    )
    return regions

  def _infer_columns(self, data: Dict[str, Any], header_row: int) -> List[Dict[str, Any]]:
    rows: List[List[Dict[str, Any]]] = data.get("values") or []
    if not rows:
      return []

    num_columns = len(rows[0])
    columns: List[Dict[str, Any]] = []

    for col_index in range(num_columns):
      column_cells = [
        row[col_index]
        for row in rows[header_row + 1 :]
        if len(row) > col_index and row[col_index].get("value") is not None
      ]

      # Determine dominant type
      type_counts: Dict[str, int] = {}
      for cell in column_cells:
        t = cell.get("type", "string")
        type_counts[t] = type_counts.get(t, 0) + 1

      if type_counts:
        dominant_type = max(type_counts.keys(), key=lambda k: type_counts[k])
      else:
        dominant_type = "string"

      # Map to 'mixed' when multiple types appear
      if len(type_counts) > 1:
        dominant_type = "mixed"

      unique_values = len({cell.get("value") for cell in column_cells})
      sample_values = [cell.get("value") for cell in column_cells[:5]]

      if header_row >= 0 and len(rows) > header_row and len(rows[header_row]) > col_index:
        header_cell = rows[header_row][col_index]
        name = str(header_cell.get("value")) if header_cell.get("value") is not None else self._column_to_letter(
          col_index + 1
        )
      else:
        name = self._column_to_letter(col_index + 1)

      columns.append(
        {
          "index": col_index,
          "name": name,
          "type": dominant_type,
          "nullable": len(column_cells) < len(rows) - (header_row + 1),
          "uniqueValues": unique_values,
          "sampleValues": sample_values,
        }
      )

    return columns

  def _generate_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
    all_cells: List[Dict[str, Any]] = [cell for row in data.get("values") or [] for cell in row]
    total_cells = len(all_cells)
    if total_cells == 0:
      return {
        "totalCells": 0,
        "emptyCells": 0,
        "formulaCells": 0,
        "errorCells": 0,
        "dataTypes": {},
      }

    empty_cells = sum(1 for c in all_cells if c.get("type") == "empty")
    formula_cells = sum(1 for c in all_cells if c.get("type") == "formula")
    error_cells = sum(1 for c in all_cells if c.get("type") == "error")

    data_types: Dict[str, int] = {}
    for c in all_cells:
      t = c.get("type", "empty")
      data_types[t] = data_types.get(t, 0) + 1

    return {
      "totalCells": total_cells,
      "emptyCells": empty_cells,
      "formulaCells": formula_cells,
      "errorCells": error_cells,
      "dataTypes": data_types,
    }

  def _sample_data(self, data: Dict[str, Any], top_n: int = 10) -> List[Dict[str, Any]]:
    rows: List[List[Dict[str, Any]]] = data.get("values") or []
    sampled_rows = rows[: min(top_n, len(rows))]
    return [
      {
        **data,
        "values": sampled_rows,
        "endRow": min(top_n - 1, data.get("endRow", len(rows) - 1)),
      }
    ]

  @staticmethod
  def generate_text_description(context: Dict[str, Any]) -> str:
    sheet_meta = context.get("sheetMetadata") or {}
    table_regions = context.get("tableRegions") or []
    summary = context.get("summary") or {}

    description = f"# Sheet: {sheet_meta.get('title')}\n\n"
    description += f"Dimensions: {sheet_meta.get('rowCount')} rows × {sheet_meta.get('columnCount')} columns\n\n"

    description += "## Summary\n"
    description += f"- Total cells: {summary.get('totalCells')}\n"
    description += f"- Empty cells: {summary.get('emptyCells')}\n"
    total_cells = summary.get("totalCells") or 1
    empty_cells = summary.get("emptyCells") or 0
    pct_empty = (empty_cells / total_cells) * 100 if total_cells else 0
    description += f"- Empty cells: {empty_cells} ({pct_empty:.1f}%)\n"
    description += f"- Formula cells: {summary.get('formulaCells')}\n"
    description += f"- Error cells: {summary.get('errorCells')}\n\n"

    if table_regions:
      description += "## Table Structure\n\n"
      for idx, region in enumerate(table_regions):
        description += f"### Table {idx + 1}\n"
        description += f"Has headers: {region.get('hasHeaders')}\n"
        data_start = (region.get("dataStartRow") or 0) + 1
        description += f"Data starts at row: {data_start}\n\n"

        description += "Columns:\n"
        for col in region.get("columns") or []:
          description += f"- {col.get('name')} ({col.get('type')}{', nullable' if col.get('nullable') else ''})\n"
          samples = col.get("sampleValues") or []
          if samples:
            description += f"  Sample: {', '.join(map(str, samples[:3]))}\n"
        description += "\n"

    return description

  @staticmethod
  def _column_to_letter(column: int) -> str:
    letter = ""
    while column > 0:
      remainder = (column - 1) % 26
      letter = chr(65 + remainder) + letter
      column = (column - 1) // 26
    return letter


