import { NextRequest, NextResponse } from 'next/server';
import { ServiceAccountSheetsClient } from '@/lib/sheets/service-account-client';
import { ContextBuilder } from '@/lib/sheets/context-builder';
import { MistakeDetector } from '@/lib/agents/mistake-detector';
import { createLLMClient } from '@/lib/llm/client';
import { IssueDetectionConfig } from '@/types/errors';
import { normalizeSpreadsheetId } from '@/lib/sheets/utils';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { spreadsheetId: rawSpreadsheetId, sheetTitle, config } = body;

    if (!rawSpreadsheetId || !sheetTitle) {
      return NextResponse.json(
        { error: 'Missing spreadsheetId or sheetTitle' },
        { status: 400 }
      );
    }

    const spreadsheetId = normalizeSpreadsheetId(rawSpreadsheetId);

    // Initialize clients with service account
    const sheetsClient = new ServiceAccountSheetsClient();
    const contextBuilder = new ContextBuilder(sheetsClient);
    const llmClient = createLLMClient();
    const detector = new MistakeDetector(contextBuilder, llmClient);

    // Default config
    const detectionConfig: IssueDetectionConfig = {
      enableRuleBased: true,
      enableLLMBased: true,
      minSeverity: 'low',
      categoriesToCheck: [
        'formula_error',
        'inconsistent_formula',
        'type_mismatch',
        'missing_value',
        'duplicate_key',
        'semantic_anomaly',
        'logical_inconsistency',
      ],
      ...config,
    };

    // Detect issues
    const result = await detector.detectIssues(spreadsheetId, sheetTitle, detectionConfig);

    return NextResponse.json(result);
  } catch (error: unknown) {
    console.error('Error detecting issues:', error);

    // Common case: spreadsheet does not exist or service account has no access
    const err = error as {
      code?: number;
      response?: { status?: number };
      message?: string;
    };

    // Spreadsheet not found or service account lacks access
    if (err.code === 404 || err.response?.status === 404) {
      return NextResponse.json(
        {
          error:
            'Spreadsheet not found. Check that the ID is correct, the sheet exists, and the service account has access.',
        },
        { status: 404 }
      );
    }

    // Specific sheet tab within the spreadsheet not found
    if (typeof err.message === 'string' && err.message.includes('not found')) {
      return NextResponse.json(
        {
          error: err.message,
        },
        { status: 404 }
      );
    }

    const message =
      typeof err.message === 'string' && err.message.length > 0
        ? err.message
        : 'Internal server error';

    return NextResponse.json({ error: message }, { status: 500 });
  }
}
