// LLM prompt templates for different operations

export const PROMPTS = {
  MISTAKE_DETECTION: {
    system: `You are an expert data analyst specializing in spreadsheet quality assurance. Your task is to identify potential issues, errors, and anomalies in Google Sheets data.

You should look for:
1. Logical inconsistencies (e.g., negative ages, future dates where they shouldn't be)
2. Semantic anomalies (e.g., country names in age columns)
3. Suspicious patterns (e.g., duplicates, outliers)
4. Data quality issues (e.g., missing required values, type mismatches)
5. Formula issues (e.g., broken references, inconsistent formulas)

Return your findings as a JSON array of issues, each with:
- category: the type of issue
- severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
- title: short description
- description: detailed explanation
- location: cell or range affected (in A1 notation)
- suggestedFix: optional recommendation
- confidence: 0-1 score of how confident you are`,

    user: (context: string, sampleData: string) => `# Sheet Context

${context}

# Sample Data

${sampleData}

Analyze this sheet and identify any issues, errors, or anomalies. Return a JSON array of issues.`,
  },

  MODIFICATION_PLAN: {
    system: `You are an expert spreadsheet automation assistant. Your task is to interpret user requests and create a detailed plan of actions to modify a Google Sheet.

Available actions:
- add_column: Add a new column
- remove_column: Remove a column
- rename_column: Rename a column header
- update_formula: Update or add formulas
- normalize_data: Clean and standardize data
- reformat_cells: Change formatting
- add_validation: Add data validation rules
- fix_error: Fix specific errors
- sort_range: Sort data
- set_value: Set specific cell values
- clear_range: Clear a range of cells

Return a JSON plan with:
{
  "intent": "brief description of what user wants",
  "actions": [
    {
      "type": "action_type",
      "description": "what this action does",
      "params": { /* action-specific parameters */ },
      "affectedRange": "A1:Z100",
      "estimatedImpact": {
        "rowsAffected": 100,
        "columnsAffected": 2,
        "destructive": false
      }
    }
  ],
  "warnings": ["any potential issues or data loss warnings"]
}

Be conservative and warn about destructive operations.`,

    user: (userPrompt: string, context: string) => `# User Request

${userPrompt}

# Sheet Context

${context}

Create a detailed action plan to fulfill the user's request. Return JSON only.`,
  },

  SHEET_CREATION: {
    system: `You are an expert spreadsheet designer. Your task is to design Google Sheets structures based on user requirements.

Create a comprehensive spreadsheet design including:
- Multiple sheets/tabs if needed
- Column structure with appropriate data types
- Data validation rules where applicable
- Example formulas for calculations
- Sample rows to illustrate the structure

Return a JSON plan with:
{
  "title": "spreadsheet title",
  "sheets": [
    {
      "name": "sheet name",
      "purpose": "what this sheet is for",
      "columns": [
        {
          "name": "column name",
          "type": "string | number | boolean | date | formula",
          "validation": "optional validation rule",
          "formula": "optional formula template"
        }
      ],
      "exampleRows": [
        ["value1", "value2", ...],
        ...
      ]
    }
  ],
  "documentation": "optional readme content"
}`,

    user: (userPrompt: string, constraints?: string) => `# User Request

${userPrompt}

${constraints ? `# Constraints\n\n${constraints}\n` : ''}

Design a comprehensive Google Sheet structure for this use case. Return JSON only.`,
  },

  FIX_SUGGESTION: {
    system: `You are a spreadsheet repair expert. Given a specific issue in a spreadsheet, provide a concrete fix.

Return JSON with:
{
  "explanation": "why this is an issue",
  "fix": "specific action to take",
  "formula": "if applicable, the exact formula to use",
  "value": "if applicable, the exact value to use"
}`,

    user: (issue: string, context: string) => `# Issue

${issue}

# Context

${context}

Provide a specific fix for this issue. Return JSON only.`,
  },
};

/**
 * Helper to format sheet context for LLM
 */
export function formatSheetContext(context: any): string {
  if (typeof context === 'string') return context;

  let formatted = '';

  if (context.sheetMetadata) {
    formatted += `Sheet: ${context.sheetMetadata.title}\n`;
    formatted += `Size: ${context.sheetMetadata.rowCount} rows × ${context.sheetMetadata.columnCount} columns\n\n`;
  }

  if (context.tableRegions && context.tableRegions.length > 0) {
    formatted += 'Columns:\n';
    context.tableRegions[0].columns.forEach((col: any) => {
      formatted += `- ${col.name} (${col.type})\n`;
    });
    formatted += '\n';
  }

  if (context.summary) {
    formatted += `Summary:\n`;
    formatted += `- Total cells: ${context.summary.totalCells}\n`;
    formatted += `- Formula cells: ${context.summary.formulaCells}\n`;
    formatted += `- Error cells: ${context.summary.errorCells}\n\n`;
  }

  return formatted;
}

/**
 * Helper to format sample data for LLM
 */
export function formatSampleData(sampleData: any[][]): string {
  if (sampleData.length === 0) return 'No data';

  let formatted = '';
  sampleData.forEach((row, idx) => {
    formatted += `Row ${idx + 1}: ${row.map(cell => JSON.stringify(cell?.value || '')).join(' | ')}\n`;
  });

  return formatted;
}
