/**
 * Chat system types for the agentic SPA interface
 */

import type { IssueDetectionResult } from './errors'
import type { ModificationResult } from './agents'
import type { SheetCreationResult } from './agents'

/**
 * Message roles in the chat system
 */
export type ChatMessageRole = 'user' | 'assistant' | 'tool' | 'system'

/**
 * Tool names that can be invoked by the agent
 */
export type ToolName = 'detect_issues' | 'modify_sheet' | 'create_sheet'

/**
 * Tool-specific payload types
 */
export type ToolPayload =
  | { toolName: 'detect_issues'; result: IssueDetectionResult }
  | { toolName: 'modify_sheet'; result: ModificationResult }
  | { toolName: 'create_sheet'; result: SheetCreationResult }

/**
 * Metadata attached to chat messages
 */
export interface ChatMessageMetadata {
  toolName?: ToolName
  payload?: unknown
  plan?: string
  error?: string
  timestamp?: string
}

/**
 * A single message in the chat conversation
 */
export interface ChatMessage {
  id: string
  role: ChatMessageRole
  content: string
  metadata?: ChatMessageMetadata
}

/**
 * Sheet context for the current conversation
 */
export interface SheetContext {
  spreadsheetId?: string
  sheetTitle?: string
}

/**
 * Request body for the /api/chat endpoint
 */
export interface ChatRequest {
  messages: ChatMessage[]
  sheetContext: SheetContext
  sessionId?: string
}

/**
 * Response body from the /api/chat endpoint
 */
export interface ChatResponse {
  messages: ChatMessage[]
  sessionId?: string
}

/**
 * Agent decision types
 */
export type AgentStep = 'answer' | 'tool_call'

/**
 * Tool call arguments for each tool
 */
export interface DetectIssuesArgs {
  spreadsheetId: string
  sheetTitle?: string
  config?: {
    includeRuleBased?: boolean
    includeLLMBased?: boolean
    minConfidence?: number
  }
}

export interface ModifySheetArgs {
  spreadsheetId: string
  sheetTitle?: string
  prompt: string
  constraints?: {
    maxRowsAffected?: number
    maxColumnsAffected?: number
    allowDestructive?: boolean
  }
}

export interface CreateSheetArgs {
  prompt: string
  constraints?: {
    maxSheets?: number
    maxColumns?: number
    maxExampleRows?: number
  }
}

export type ToolArguments = DetectIssuesArgs | ModifySheetArgs | CreateSheetArgs

/**
 * Tool call structure
 */
export interface ToolCall {
  name: ToolName
  arguments: ToolArguments
}

/**
 * Agent response structure (from LLM)
 */
export interface AgentResponse {
  step: AgentStep
  assistantMessage: string
  tool?: ToolCall
}
