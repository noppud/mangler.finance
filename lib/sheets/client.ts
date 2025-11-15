// Google Sheets API client wrapper

import { google, sheets_v4 } from 'googleapis';
import { SpreadsheetMetadata, SheetMetadata, Range as SheetRange, CellValue } from '@/types/sheets';

export class SheetsClient {
  private sheets: sheets_v4.Sheets;

  constructor(accessToken: string) {
    const auth = new google.auth.OAuth2();
    auth.setCredentials({ access_token: accessToken });
    this.sheets = google.sheets({ version: 'v4', auth });
  }

  /**
   * Get spreadsheet metadata
   */
  async getSpreadsheetMetadata(spreadsheetId: string): Promise<SpreadsheetMetadata> {
    const response = await this.sheets.spreadsheets.get({
      spreadsheetId,
      fields: 'spreadsheetId,properties,sheets',
    });

    const spreadsheet = response.data;
    const sheets: SheetMetadata[] = (spreadsheet.sheets || []).map((sheet, index) => ({
      sheetId: sheet.properties?.sheetId || 0,
      title: sheet.properties?.title || '',
      index,
      rowCount: sheet.properties?.gridProperties?.rowCount || 0,
      columnCount: sheet.properties?.gridProperties?.columnCount || 0,
      gridProperties: {
        frozenRowCount: sheet.properties?.gridProperties?.frozenRowCount,
        frozenColumnCount: sheet.properties?.gridProperties?.frozenColumnCount,
      },
    }));

    return {
      spreadsheetId: spreadsheet.spreadsheetId || '',
      title: spreadsheet.properties?.title || '',
      url: `https://docs.google.com/spreadsheets/d/${spreadsheet.spreadsheetId}`,
      sheets,
    };
  }

  /**
   * Read values from a range
   */
  async readRange(spreadsheetId: string, range: string): Promise<SheetRange> {
    const response = await this.sheets.spreadsheets.values.get({
      spreadsheetId,
      range,
      valueRenderOption: 'UNFORMATTED_VALUE',
    });

    const values = response.data.values || [];
    const cellValues: CellValue[][] = values.map(row =>
      row.map(value => this.parseCellValue(value))
    );

    return {
      sheet: range.split('!')[0] || '',
      startRow: 0, // TODO: parse from A1 notation
      startCol: 0,
      endRow: values.length - 1,
      endCol: values[0]?.length - 1 || 0,
      a1Notation: range,
      values: cellValues,
    };
  }

  /**
   * Read values with formulas
   */
  async readRangeWithFormulas(spreadsheetId: string, range: string): Promise<SheetRange> {
    const response = await this.sheets.spreadsheets.get({
      spreadsheetId,
      ranges: [range],
      fields: 'sheets(data(rowData(values(formattedValue,effectiveValue,userEnteredValue))))',
    });

    // Parse the complex response to extract values and formulas
    const sheet = response.data.sheets?.[0];
    const rowData = sheet?.data?.[0]?.rowData || [];

    const cellValues: CellValue[][] = rowData.map(row => {
      const cells = row.values || [];
      return cells.map(cell => {
        const formula = cell.userEnteredValue?.formulaValue;
        const value = cell.effectiveValue;
        const formattedValue = cell.formattedValue;

        return {
          value: this.extractCellValue(value),
          formula,
          formattedValue,
          type: this.determineCellType(value, formula),
        };
      });
    });

    return {
      sheet: range.split('!')[0] || '',
      startRow: 0,
      startCol: 0,
      endRow: cellValues.length - 1,
      endCol: cellValues[0]?.length - 1 || 0,
      a1Notation: range,
      values: cellValues,
    };
  }

  /**
   * Write values to a range
   */
  async writeRange(
    spreadsheetId: string,
    range: string,
    values: any[][],
    valueInputOption: 'RAW' | 'USER_ENTERED' = 'USER_ENTERED'
  ): Promise<void> {
    await this.sheets.spreadsheets.values.update({
      spreadsheetId,
      range,
      valueInputOption,
      requestBody: {
        values,
      },
    });
  }

  /**
   * Batch update multiple ranges
   */
  async batchUpdate(
    spreadsheetId: string,
    updates: { range: string; values: any[][] }[]
  ): Promise<void> {
    await this.sheets.spreadsheets.values.batchUpdate({
      spreadsheetId,
      requestBody: {
        valueInputOption: 'USER_ENTERED',
        data: updates,
      },
    });
  }

  /**
   * Add a new sheet
   */
  async addSheet(spreadsheetId: string, title: string): Promise<number> {
    const response = await this.sheets.spreadsheets.batchUpdate({
      spreadsheetId,
      requestBody: {
        requests: [
          {
            addSheet: {
              properties: {
                title,
              },
            },
          },
        ],
      },
    });

    const sheetId = response.data.replies?.[0]?.addSheet?.properties?.sheetId;
    return sheetId || 0;
  }

  /**
   * Delete a sheet
   */
  async deleteSheet(spreadsheetId: string, sheetId: number): Promise<void> {
    await this.sheets.spreadsheets.batchUpdate({
      spreadsheetId,
      requestBody: {
        requests: [
          {
            deleteSheet: {
              sheetId,
            },
          },
        ],
      },
    });
  }

  /**
   * Create a new spreadsheet
   */
  async createSpreadsheet(title: string, sheetTitles: string[] = ['Sheet1']): Promise<string> {
    const response = await this.sheets.spreadsheets.create({
      requestBody: {
        properties: {
          title,
        },
        sheets: sheetTitles.map(sheetTitle => ({
          properties: {
            title: sheetTitle,
          },
        })),
      },
    });

    return response.data.spreadsheetId || '';
  }

  /**
   * Apply formatting to a range
   */
  async formatRange(
    spreadsheetId: string,
    sheetId: number,
    startRow: number,
    endRow: number,
    startCol: number,
    endCol: number,
    format: any
  ): Promise<void> {
    await this.sheets.spreadsheets.batchUpdate({
      spreadsheetId,
      requestBody: {
        requests: [
          {
            repeatCell: {
              range: {
                sheetId,
                startRowIndex: startRow,
                endRowIndex: endRow,
                startColumnIndex: startCol,
                endColumnIndex: endCol,
              },
              cell: {
                userEnteredFormat: format,
              },
              fields: 'userEnteredFormat',
            },
          },
        ],
      },
    });
  }

  /**
   * List user's spreadsheets
   */
  async listSpreadsheets(): Promise<{ id: string; name: string }[]> {
    // Note: This requires Google Drive API, not Sheets API
    // For now, return empty array - implement with Drive API later
    return [];
  }

  // Helper methods

  private parseCellValue(value: any): CellValue {
    if (value === null || value === undefined || value === '') {
      return { value: null, type: 'empty' };
    }

    if (typeof value === 'number') {
      return { value, type: 'number' };
    }

    if (typeof value === 'boolean') {
      return { value, type: 'boolean' };
    }

    // Check if it's a date (heuristic)
    if (typeof value === 'string' && !isNaN(Date.parse(value))) {
      return { value, type: 'date' };
    }

    return { value: String(value), type: 'string' };
  }

  private extractCellValue(effectiveValue: any): string | number | boolean | null {
    if (!effectiveValue) return null;
    if (effectiveValue.numberValue !== undefined) return effectiveValue.numberValue;
    if (effectiveValue.stringValue !== undefined) return effectiveValue.stringValue;
    if (effectiveValue.boolValue !== undefined) return effectiveValue.boolValue;
    if (effectiveValue.errorValue !== undefined) return `#ERROR: ${effectiveValue.errorValue.type}`;
    return null;
  }

  private determineCellType(
    effectiveValue: any,
    formula?: string
  ): CellValue['type'] {
    if (formula) return 'formula';
    if (!effectiveValue) return 'empty';
    if (effectiveValue.errorValue) return 'error';
    if (effectiveValue.numberValue !== undefined) return 'number';
    if (effectiveValue.boolValue !== undefined) return 'boolean';
    if (effectiveValue.stringValue !== undefined) {
      // Could be date or string
      return 'string';
    }
    return 'empty';
  }
}
