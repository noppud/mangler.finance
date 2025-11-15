import { NextRequest, NextResponse } from 'next/server';
import { ServiceAccountSheetsClient } from '@/lib/sheets/service-account-client';
import { ContextBuilder } from '@/lib/sheets/context-builder';
import { SheetModifier } from '@/lib/agents/modifier';
import { createLLMClient } from '@/lib/llm/client';
import { ModificationRequest } from '@/types/agents';
import { normalizeSpreadsheetId } from '@/lib/sheets/utils';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { spreadsheetId: rawSpreadsheetId, sheetTitle, prompt, constraints } = body;

    if (!rawSpreadsheetId || !prompt) {
      return NextResponse.json(
        { error: 'Missing spreadsheetId or prompt' },
        { status: 400 }
      );
    }

    const spreadsheetId = normalizeSpreadsheetId(rawSpreadsheetId);

    // Initialize clients with service account
    const sheetsClient = new ServiceAccountSheetsClient();
    const contextBuilder = new ContextBuilder(sheetsClient);
    const llmClient = createLLMClient();
    const modifier = new SheetModifier(sheetsClient, contextBuilder, llmClient);

    // Create modification request
    const modRequest: ModificationRequest = {
      spreadsheetId,
      sheetTitle,
      prompt,
      constraints: constraints || {
        maxRowsAffected: 1000,
        maxColumnsAffected: 50,
        allowDestructive: false,
      },
    };

    // Execute modification
    const result = await modifier.modify(modRequest);

    return NextResponse.json(result);
  } catch (error: unknown) {
    console.error('Error modifying sheet:', error);

    const err = error as { code?: number; response?: { status?: number }; message?: string };

    if (err.code === 404 || err.response?.status === 404) {
      return NextResponse.json(
        {
          error:
            'Spreadsheet not found. Check that the ID is correct, the sheet exists, and the service account has access.',
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
