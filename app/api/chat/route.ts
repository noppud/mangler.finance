/**
 * Unified chat endpoint for agentic Sheet Mangler interface
 */

import { NextRequest, NextResponse } from 'next/server'
import { ServiceAccountSheetsClient } from '@/lib/sheets/service-account-client'
import { ContextBuilder } from '@/lib/sheets/context-builder'
import { createLLMClient } from '@/lib/llm/client'
import { AgentOrchestrator } from '@/lib/agents/assistant'
import type { ChatRequest, ChatResponse } from '@/types/chat'

export const maxDuration = 300

/**
 * POST /api/chat
 * Process a chat message and return agent responses
 */
export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as ChatRequest

    // Validate request
    if (!body.messages || !Array.isArray(body.messages)) {
      return NextResponse.json({ error: 'Invalid request: messages array required' }, { status: 400 })
    }

    if (!body.sheetContext) {
      body.sheetContext = {}
    }

    // Initialize dependencies
    const sheetsClient = new ServiceAccountSheetsClient()
    const contextBuilder = new ContextBuilder(sheetsClient)
    const llmClient = createLLMClient()

    // Create orchestrator
    const orchestrator = new AgentOrchestrator({
      llmClient,
      sheetsClient,
      contextBuilder,
    })

    // Process the chat
    const newMessages = await orchestrator.processChat(body.messages, body.sheetContext)

    // Build response
    const response: ChatResponse = {
      messages: newMessages,
      sessionId: body.sessionId, // Pass through for future persistence
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('Error in /api/chat:', error)

    // Return structured error
    if (error instanceof Error) {
      // Check for specific error types
      if (error.message.includes('not found') || error.message.includes('404')) {
        return NextResponse.json(
          {
            error: 'Spreadsheet or sheet not found',
            details: error.message,
          },
          { status: 404 }
        )
      }

      if (error.message.includes('permission') || error.message.includes('access')) {
        return NextResponse.json(
          {
            error: 'Permission denied',
            details: 'The service account does not have access to this spreadsheet',
          },
          { status: 403 }
        )
      }

      // Generic error
      return NextResponse.json(
        {
          error: 'Internal server error',
          details: error.message,
        },
        { status: 500 }
      )
    }

    // Unknown error type
    return NextResponse.json(
      {
        error: 'Internal server error',
        details: 'An unknown error occurred',
      },
      { status: 500 }
    )
  }
}
