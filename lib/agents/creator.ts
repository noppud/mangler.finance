// Sheet creation engine using LLM to design and create new spreadsheets

import { LLMClient } from '../llm/client';
import { SheetsClient } from '../sheets/client';
import {
  SheetCreationRequest,
  SheetCreationPlan,
  SheetCreationResult,
} from '@/types/agents';
import { PROMPTS } from '../llm/prompts';

type SheetsCreatorClient = Pick<
  SheetsClient,
  'createSpreadsheet' | 'writeRange' | 'getSpreadsheetMetadata' | 'formatRange' | 'addSheet'
>;

export class SheetCreator {
  constructor(
    private sheetsClient: SheetsCreatorClient,
    private llmClient: LLMClient
  ) {}

  /**
   * Create a new spreadsheet based on natural language prompt
   */
  async create(request: SheetCreationRequest): Promise<SheetCreationResult> {
    try {
      // Generate design plan using LLM
      const plan = await this.generatePlan(request);

      // Create the spreadsheet
      const spreadsheetId = await this.createSpreadsheet(plan);

      // Populate with data and formulas
      await this.populateSpreadsheet(spreadsheetId, plan);

      return {
        success: true,
        spreadsheetId,
        spreadsheetUrl: `https://docs.google.com/spreadsheets/d/${spreadsheetId}`,
        plan,
      };
    } catch (error: any) {
      return {
        success: false,
        plan: { title: '', sheets: [] },
        errors: [error.message],
      };
    }
  }

  /**
   * Generate a creation plan using LLM
   */
  private async generatePlan(
    request: SheetCreationRequest
  ): Promise<SheetCreationPlan> {
    let constraintsStr = '';
    if (request.constraints) {
      const parts: string[] = [];
      if (request.constraints.maxSheets) {
        parts.push(`Maximum ${request.constraints.maxSheets} sheets`);
      }
      if (request.constraints.maxColumns) {
        parts.push(`Maximum ${request.constraints.maxColumns} columns per sheet`);
      }
      if (request.constraints.generateExamples !== undefined) {
        parts.push(
          request.constraints.generateExamples
            ? 'Include example data'
            : 'Do not include example data'
        );
      }
      constraintsStr = parts.join('\n');
    }

    const llmPrompt = PROMPTS.SHEET_CREATION.user(request.prompt, constraintsStr);

    const response = await this.llmClient.chatJSON<SheetCreationPlan>(
      [
        { role: 'system', content: PROMPTS.SHEET_CREATION.system },
        { role: 'user', content: llmPrompt },
      ],
      { temperature: 0.5 }
    );

    return response;
  }

  /**
   * Create the spreadsheet structure
   */
  private async createSpreadsheet(plan: SheetCreationPlan): Promise<string> {
    const sheetTitles = plan.sheets.map(sheet => sheet.name);
    const spreadsheetId = await this.sheetsClient.createSpreadsheet(
      plan.title,
      sheetTitles
    );

    return spreadsheetId;
  }

  /**
   * Populate spreadsheet with headers, data, and formulas
   */
  private async populateSpreadsheet(
    spreadsheetId: string,
    plan: SheetCreationPlan
  ): Promise<void> {
    for (const sheet of plan.sheets) {
      // Add headers
      const headers = sheet.columns.map(col => col.name);
      const headerRange = `${sheet.name}!A1:${this.columnToLetter(headers.length)}1`;
      await this.sheetsClient.writeRange(spreadsheetId, headerRange, [headers]);

      // Add example rows if provided
      if (sheet.exampleRows && sheet.exampleRows.length > 0) {
        const dataRange = `${sheet.name}!A2:${this.columnToLetter(sheet.columns.length)}${1 + sheet.exampleRows.length}`;
        await this.sheetsClient.writeRange(
          spreadsheetId,
          dataRange,
          sheet.exampleRows,
          'USER_ENTERED' // This allows formulas to be interpreted
        );
      }

      // Apply data validation if specified
      await this.applyValidation(spreadsheetId, sheet);

      // Apply formatting (freeze header row, bold headers)
      await this.applyFormatting(spreadsheetId, sheet);
    }

    // Add documentation sheet if provided
    if (plan.documentation) {
      await this.addDocumentationSheet(spreadsheetId, plan.documentation);
    }
  }

  /**
   * Apply data validation rules
   */
  private async applyValidation(
    spreadsheetId: string,
    sheet: SheetCreationPlan['sheets'][0]
  ): Promise<void> {
    // TODO: Implement data validation using batchUpdate
    // This would require detailed validation rule parsing
  }

  /**
   * Apply formatting to the sheet
   */
  private async applyFormatting(
    spreadsheetId: string,
    sheet: SheetCreationPlan['sheets'][0]
  ): Promise<void> {
    // Get sheet metadata to find sheetId
    const metadata = await this.sheetsClient.getSpreadsheetMetadata(spreadsheetId);
    const sheetMetadata = metadata.sheets.find(s => s.title === sheet.name);

    if (!sheetMetadata) return;

    // Format header row (bold, background color)
    await this.sheetsClient.formatRange(
      spreadsheetId,
      sheetMetadata.sheetId,
      0,
      1,
      0,
      sheet.columns.length,
      {
        textFormat: { bold: true },
        backgroundColor: { red: 0.9, green: 0.9, blue: 0.9 },
      }
    );
  }

  /**
   * Add a documentation/readme sheet
   */
  private async addDocumentationSheet(
    spreadsheetId: string,
    documentation: string
  ): Promise<void> {
    // Add a new sheet called "README"
    await this.sheetsClient.addSheet(spreadsheetId, 'README');

    // Write documentation as multiline text in cell A1
    const docLines = documentation.split('\n').map(line => [line]);
    await this.sheetsClient.writeRange(
      spreadsheetId,
      'README!A1',
      docLines
    );
  }

  /**
   * Convert column number to letter
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
