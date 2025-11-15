import { NextRequest, NextResponse } from 'next/server';
import { ServiceAccountSheetsClient } from '@/lib/sheets/service-account-client';
import { SheetCreator } from '@/lib/agents/creator';
import { createLLMClient } from '@/lib/llm/client';
import { SheetCreationRequest } from '@/types/agents';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { prompt, constraints } = body;

    if (!prompt) {
      return NextResponse.json(
        { error: 'Missing prompt' },
        { status: 400 }
      );
    }

    // Initialize clients with service account
    const sheetsClient = new ServiceAccountSheetsClient();
    const llmClient = createLLMClient();
    const creator = new SheetCreator(sheetsClient as any, llmClient);

    // Create creation request
    const createRequest: SheetCreationRequest = {
      prompt,
      constraints: constraints || {
        maxSheets: 5,
        maxColumns: 26,
        generateExamples: true,
      },
    };

    // Execute creation
    const result = await creator.create(createRequest);

    return NextResponse.json(result);
  } catch (error: any) {
    console.error('Error creating sheet:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}
