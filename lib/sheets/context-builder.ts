// Context builder for analyzing and summarizing sheet data

import { SheetsClient } from './client';
import {
  SheetContext,
  TableRegion,
  ColumnInfo,
  CellValue,
  Range as SheetRange,
} from '@/types/sheets';

type SheetsContextClient = Pick<
  SheetsClient,
  'getSpreadsheetMetadata' | 'readRange' | 'readRangeWithFormulas'
>;

export class ContextBuilder {
  constructor(private client: SheetsContextClient) {}

  /**
   * Build comprehensive context for a sheet
   */
  async buildContext(spreadsheetId: string, sheetTitle: string): Promise<SheetContext> {
    const metadata = await this.client.getSpreadsheetMetadata(spreadsheetId);
    const sheetMetadata = metadata.sheets.find(s => s.title === sheetTitle);

    if (!sheetMetadata) {
      throw new Error(`Sheet "${sheetTitle}" not found`);
    }

    // Read the sheet data with formulas
    const range = `${sheetTitle}!A1:${this.columnToLetter(sheetMetadata.columnCount)}${sheetMetadata.rowCount}`;
    const data = await this.client.readRangeWithFormulas(spreadsheetId, range);

    // Detect table regions
    const tableRegions = this.detectTableRegions(data);

    // Generate summary statistics
    const summary = this.generateSummary(data);

    // Sample data for LLM context (first 10 rows + random sampling)
    const sampleData = this.sampleData(data, 10);

    return {
      metadata,
      sheetMetadata,
      tableRegions,
      summary,
      sampleData,
    };
  }

  /**
   * Build lightweight context (for quick operations)
   */
  async buildLightweightContext(
    spreadsheetId: string,
    sheetTitle: string
  ): Promise<Partial<SheetContext>> {
    const metadata = await this.client.getSpreadsheetMetadata(spreadsheetId);
    const sheetMetadata = metadata.sheets.find(s => s.title === sheetTitle);

    if (!sheetMetadata) {
      throw new Error(`Sheet "${sheetTitle}" not found`);
    }

    // Only read first 100 rows for lightweight analysis
    const range = `${sheetTitle}!A1:${this.columnToLetter(Math.min(sheetMetadata.columnCount, 26))}100`;
    const data = await this.client.readRange(spreadsheetId, range);

    const summary = this.generateSummary(data);

    return {
      metadata,
      sheetMetadata,
      summary,
    };
  }

  /**
   * Detect table regions in the sheet
   */
  private detectTableRegions(data: SheetRange): TableRegion[] {
    const regions: TableRegion[] = [];
    const rows = data.values;

    if (rows.length === 0) return regions;

    // Simple heuristic: look for header rows (non-empty, string-heavy rows)
    let headerRow = -1;
    for (let i = 0; i < Math.min(10, rows.length); i++) {
      const row = rows[i];
      const nonEmpty = row.filter(cell => cell.value !== null).length;
      const strings = row.filter(cell => cell.type === 'string').length;

      if (nonEmpty > 0 && strings / nonEmpty > 0.7) {
        headerRow = i;
        break;
      }
    }

    if (headerRow === -1) {
      // No clear header, treat entire sheet as one region without headers
      return [
        {
          range: data,
          hasHeaders: false,
          dataStartRow: 0,
          columns: this.inferColumns(data, -1),
        },
      ];
    }

    // Found headers, create a table region
    const dataStartRow = headerRow + 1;
    const columns = this.inferColumns(data, headerRow);

    regions.push({
      range: data,
      hasHeaders: true,
      headerRow,
      dataStartRow,
      columns,
    });

    return regions;
  }

  /**
   * Infer column information from data
   */
  private inferColumns(data: SheetRange, headerRow: number): ColumnInfo[] {
    const rows = data.values;
    if (rows.length === 0) return [];

    const numColumns = rows[0].length;
    const columns: ColumnInfo[] = [];

    for (let col = 0; col < numColumns; col++) {
      const columnValues = rows
        .slice(headerRow + 1)
        .map(row => row[col])
        .filter(cell => cell && cell.value !== null);

      const types = columnValues.map(cell => cell.type);
      const typeCounts = types.reduce((acc, type) => {
        acc[type] = (acc[type] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

      const dominantType =
        Object.keys(typeCounts).length > 0
          ? (Object.keys(typeCounts).reduce((a, b) =>
              typeCounts[a] > typeCounts[b] ? a : b
            ) as ColumnInfo['type'])
          : 'string';

      const uniqueValues = new Set(columnValues.map(c => c.value)).size;
      const sampleValues = columnValues
        .slice(0, 5)
        .map(c => c.value);

      columns.push({
        index: col,
        name: headerRow >= 0 && rows[headerRow][col]
          ? String(rows[headerRow][col].value)
          : this.columnToLetter(col + 1),
        type: dominantType,
        nullable: columnValues.length < rows.length - (headerRow + 1),
        uniqueValues,
        sampleValues,
      });
    }

    return columns;
  }

  /**
   * Generate summary statistics
   */
  private generateSummary(data: SheetRange) {
    const allCells = data.values.flat();
    const totalCells = allCells.length;
    const emptyCells = allCells.filter(c => c.type === 'empty').length;
    const formulaCells = allCells.filter(c => c.type === 'formula').length;
    const errorCells = allCells.filter(c => c.type === 'error').length;

    const dataTypes = allCells.reduce((acc, cell) => {
      acc[cell.type] = (acc[cell.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      totalCells,
      emptyCells,
      formulaCells,
      errorCells,
      dataTypes,
    };
  }

  /**
   * Sample data from the sheet
   */
  private sampleData(data: SheetRange, topN: number = 10): SheetRange[] {
    const rows = data.values;
    const sampledRows = rows.slice(0, Math.min(topN, rows.length));

    return [
      {
        ...data,
        values: sampledRows,
        endRow: Math.min(topN - 1, data.endRow),
      },
    ];
  }

  /**
   * Generate a compact textual description for LLM
   */
  generateTextDescription(context: SheetContext): string {
    const { sheetMetadata, tableRegions, summary } = context;

    let description = `# Sheet: ${sheetMetadata.title}\n\n`;
    description += `Dimensions: ${sheetMetadata.rowCount} rows × ${sheetMetadata.columnCount} columns\n\n`;

    description += `## Summary\n`;
    description += `- Total cells: ${summary.totalCells}\n`;
    description += `- Empty cells: ${summary.emptyCells} (${((summary.emptyCells / summary.totalCells) * 100).toFixed(1)}%)\n`;
    description += `- Formula cells: ${summary.formulaCells}\n`;
    description += `- Error cells: ${summary.errorCells}\n\n`;

    if (tableRegions.length > 0) {
      description += `## Table Structure\n\n`;
      tableRegions.forEach((region, idx) => {
        description += `### Table ${idx + 1}\n`;
        description += `Has headers: ${region.hasHeaders}\n`;
        description += `Data starts at row: ${region.dataStartRow + 1}\n\n`;

        description += `Columns:\n`;
        region.columns.forEach(col => {
          description += `- ${col.name} (${col.type}${col.nullable ? ', nullable' : ''})\n`;
          if (col.sampleValues.length > 0) {
            description += `  Sample: ${col.sampleValues.slice(0, 3).join(', ')}\n`;
          }
        });
        description += `\n`;
      });
    }

    return description;
  }

  /**
   * Convert column number to letter (1 -> A, 27 -> AA)
   */
  private columnToLetter(column: number): string {
    let letter = '';
    while (column > 0) {
      const remainder = (column - 1) % 26;
      letter = String.fromCharCode(65 + remainder) + letter;
      column = Math.floor((column - 1) / 26);
    }
    return letter;
  }
}
