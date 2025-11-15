// Core types for Google Sheets representation

export interface CellValue {
  value: string | number | boolean | null;
  formula?: string;
  type: 'string' | 'number' | 'boolean' | 'date' | 'formula' | 'error' | 'empty';
  formattedValue?: string;
}

export interface CellLocation {
  sheet: string;
  row: number;
  col: number;
  a1Notation: string;
}

export interface Cell extends CellValue {
  location: CellLocation;
}

export interface Range {
  sheet: string;
  startRow: number;
  startCol: number;
  endRow: number;
  endCol: number;
  a1Notation: string;
  values: CellValue[][];
}

export interface SheetMetadata {
  sheetId: number;
  title: string;
  index: number;
  rowCount: number;
  columnCount: number;
  gridProperties?: {
    frozenRowCount?: number;
    frozenColumnCount?: number;
  };
}

export interface SpreadsheetMetadata {
  spreadsheetId: string;
  title: string;
  url: string;
  sheets: SheetMetadata[];
  createdTime?: string;
  modifiedTime?: string;
}

export interface TableRegion {
  range: Range;
  hasHeaders: boolean;
  headerRow?: number;
  dataStartRow: number;
  columns: ColumnInfo[];
}

export interface ColumnInfo {
  index: number;
  name: string;
  type: 'string' | 'number' | 'boolean' | 'date' | 'mixed';
  nullable: boolean;
  uniqueValues?: number;
  sampleValues: any[];
}

export interface SheetContext {
  metadata: SpreadsheetMetadata;
  sheetMetadata: SheetMetadata;
  tableRegions: TableRegion[];
  summary: {
    totalCells: number;
    emptyCells: number;
    formulaCells: number;
    errorCells: number;
    dataTypes: Record<string, number>;
  };
  sampleData?: Range[];
}
