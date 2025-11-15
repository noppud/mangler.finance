/**
 * Agent Orchestrator - Unified chat interface for all Sheet Mangler operations
 */

import { v4 as uuidv4 } from 'uuid'
import type { LLMClient } from '../llm/client'
import { PROMPTS } from '../llm/prompts'
import type {
  ChatMessage,
  SheetContext,
  AgentResponse,
  DetectIssuesArgs,
  ModifySheetArgs,
  CreateSheetArgs,
} from '../../types/chat'
import { MistakeDetector } from './mistake-detector'
import { SheetModifier } from './modifier'
import { SheetCreator } from './creator'
import { normalizeSpreadsheetId } from '../sheets/utils'
import type { ServiceAccountSheetsClient } from '../sheets/service-account-client'
import type { ContextBuilder } from '../sheets/context-builder'

/**
 * Dependencies required by the AgentOrchestrator
 */
export interface AgentOrchestorDeps {
  llmClient: LLMClient
  sheetsClient: ServiceAccountSheetsClient
  contextBuilder: ContextBuilder
}

/**
 * Main orchestrator for handling chat-based interactions
 */
export class AgentOrchestrator {
  private mistakeDetector: MistakeDetector
  private sheetModifier: SheetModifier
  private sheetCreator: SheetCreator
  private llmClient: LLMClient

  constructor(deps: AgentOrchestorDeps) {
    this.llmClient = deps.llmClient

    // Initialize the three specialized agents
    this.mistakeDetector = new MistakeDetector(deps.contextBuilder, deps.llmClient)
    this.sheetModifier = new SheetModifier(deps.sheetsClient, deps.contextBuilder, deps.llmClient)
    this.sheetCreator = new SheetCreator(deps.sheetsClient, deps.llmClient)
  }

  /**
   * Process a chat request and return new messages
   */
  async processChat(messages: ChatMessage[], sheetContext: SheetContext): Promise<ChatMessage[]> {
    try {
      // Format chat history for the LLM
      const chatHistory = this.formatChatHistory(messages)
      const contextStr = this.formatSheetContext(sheetContext)

      // Call the LLM with the AGENT prompt
      const systemPrompt = PROMPTS.AGENT.system
      const userPrompt = PROMPTS.AGENT.user(chatHistory, contextStr)

      const response = await this.llmClient.chatJSON<AgentResponse>(
        [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
        { maxTokens: 3000 }
      )

      // Validate response structure
      if (!response || typeof response !== 'object') {
        throw new Error('Invalid response from LLM: expected JSON object')
      }

      if (!response.step || !response.assistantMessage) {
        throw new Error('Invalid response structure: missing step or assistantMessage')
      }

      const newMessages: ChatMessage[] = []

      // Handle based on step type
      if (response.step === 'answer') {
        // Simple conversational response
        newMessages.push({
          id: uuidv4(),
          role: 'assistant',
          content: response.assistantMessage,
        })
      } else if (response.step === 'tool_call') {
        // Tool call required
        if (!response.tool || !response.tool.name || !response.tool.arguments) {
          throw new Error('Invalid tool call: missing tool or arguments')
        }

        // Add assistant message explaining what's about to happen
        newMessages.push({
          id: uuidv4(),
          role: 'assistant',
          content: response.assistantMessage,
        })

        // Execute the tool call
        const toolMessages = await this.executeToolCall(response.tool.name, response.tool.arguments, sheetContext)
        newMessages.push(...toolMessages)
      } else {
        throw new Error(`Unknown step type: ${response.step}`)
      }

      return newMessages
    } catch (error) {
      console.error('Error in AgentOrchestrator:', error)

      // Return error message
      return [
        {
          id: uuidv4(),
          role: 'assistant',
          content: `I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}. Please try rephrasing your request or check that your spreadsheet details are correct.`,
          metadata: {
            error: error instanceof Error ? error.message : 'Unknown error',
          },
        },
      ]
    }
  }

  /**
   * Execute a tool call and return resulting messages
   */
  private async executeToolCall(
    toolName: string,
    args: unknown,
    sheetContext: SheetContext
  ): Promise<ChatMessage[]> {
    const messages: ChatMessage[] = []

    try {
      switch (toolName) {
        case 'detect_issues': {
          const detectArgs = args as DetectIssuesArgs
          const spreadsheetId = normalizeSpreadsheetId(
            detectArgs.spreadsheetId || sheetContext.spreadsheetId || ''
          )
          const sheetTitle = detectArgs.sheetTitle || sheetContext.sheetTitle

          if (!spreadsheetId) {
            throw new Error('Missing spreadsheet ID')
          }
          if (!sheetTitle) {
            throw new Error('Missing sheet title')
          }

          // Map config properties from agent args to detector config
          const config = {
            enableRuleBased: detectArgs.config?.includeRuleBased !== false,
            enableLLMBased: detectArgs.config?.includeLLMBased !== false,
            minSeverity: 'info' as const,
            categoriesToCheck: [] as any[], // Empty array means all categories
          }

          const result = await this.mistakeDetector.detectIssues(spreadsheetId, sheetTitle, config)

          // Add tool message with results
          messages.push({
            id: uuidv4(),
            role: 'tool',
            content: `Detected ${result.issues.length} issue(s)`,
            metadata: {
              toolName: 'detect_issues',
              payload: result,
            },
          })

          // Add assistant summary
          const summary = this.summarizeDetectionResult(result)
          messages.push({
            id: uuidv4(),
            role: 'assistant',
            content: summary,
          })

          break
        }

        case 'modify_sheet': {
          const modifyArgs = args as ModifySheetArgs
          const spreadsheetId = normalizeSpreadsheetId(
            modifyArgs.spreadsheetId || sheetContext.spreadsheetId || ''
          )

          if (!spreadsheetId) {
            throw new Error('Missing spreadsheet ID')
          }
          if (!modifyArgs.prompt) {
            throw new Error('Missing modification prompt')
          }

          const result = await this.sheetModifier.modify({
            spreadsheetId,
            sheetTitle: modifyArgs.sheetTitle || sheetContext.sheetTitle,
            prompt: modifyArgs.prompt,
            constraints: modifyArgs.constraints,
          })

          // Add tool message with results
          messages.push({
            id: uuidv4(),
            role: 'tool',
            content: 'Modification completed',
            metadata: {
              toolName: 'modify_sheet',
              payload: result,
            },
          })

          // Add assistant summary
          const summary = this.summarizeModificationResult(result)
          messages.push({
            id: uuidv4(),
            role: 'assistant',
            content: summary,
          })

          break
        }

        case 'create_sheet': {
          const createArgs = args as CreateSheetArgs

          if (!createArgs.prompt) {
            throw new Error('Missing creation prompt')
          }

          const result = await this.sheetCreator.create({
            prompt: createArgs.prompt,
            constraints: createArgs.constraints,
          })

          // Add tool message with results
          messages.push({
            id: uuidv4(),
            role: 'tool',
            content: `Created new spreadsheet: ${result.plan.title}`,
            metadata: {
              toolName: 'create_sheet',
              payload: result,
            },
          })

          // Add assistant summary
          const summary = this.summarizeCreationResult(result)
          messages.push({
            id: uuidv4(),
            role: 'assistant',
            content: summary,
          })

          break
        }

        default:
          throw new Error(`Unknown tool: ${toolName}`)
      }
    } catch (error) {
      messages.push({
        id: uuidv4(),
        role: 'assistant',
        content: `Failed to execute ${toolName}: ${error instanceof Error ? error.message : 'Unknown error'}`,
        metadata: {
          error: error instanceof Error ? error.message : 'Unknown error',
        },
      })
    }

    return messages
  }

  /**
   * Format chat history for LLM consumption
   */
  private formatChatHistory(messages: ChatMessage[]): string {
    return messages
      .map((msg) => {
        const roleLabel = msg.role === 'user' ? 'User' : msg.role === 'assistant' ? 'Assistant' : 'System'
        return `${roleLabel}: ${msg.content}`
      })
      .join('\n\n')
  }

  /**
   * Format sheet context for LLM
   */
  private formatSheetContext(context: SheetContext): string | undefined {
    if (!context.spreadsheetId && !context.sheetTitle) {
      return undefined
    }

    let formatted = ''
    if (context.spreadsheetId) {
      formatted += `Spreadsheet ID: ${context.spreadsheetId}\n`
    }
    if (context.sheetTitle) {
      formatted += `Sheet Title: ${context.sheetTitle}\n`
    }
    return formatted
  }

  /**
   * Create a natural language summary of detection results
   */
  private summarizeDetectionResult(result: any): string {
    const totalIssues = result.issues.length
    if (totalIssues === 0) {
      return 'Great news! I analyzed your sheet and found no issues. The data looks clean and well-structured.'
    }

    const bySeverity = result.summary.bySeverity || {}
    const critical = bySeverity.critical || 0
    const high = bySeverity.high || 0
    const medium = bySeverity.medium || 0
    const low = bySeverity.low || 0

    let summary = `I found ${totalIssues} issue${totalIssues === 1 ? '' : 's'} in your sheet:\n\n`

    if (critical > 0) summary += `- ${critical} critical issue${critical === 1 ? '' : 's'}\n`
    if (high > 0) summary += `- ${high} high severity issue${high === 1 ? '' : 's'}\n`
    if (medium > 0) summary += `- ${medium} medium severity issue${medium === 1 ? '' : 's'}\n`
    if (low > 0) summary += `- ${low} low severity issue${low === 1 ? '' : 's'}\n`

    summary += '\nSee the detailed breakdown above for specific locations and suggested fixes.'

    return summary
  }

  /**
   * Create a natural language summary of modification results
   */
  private summarizeModificationResult(result: any): string {
    if (result.errors && result.errors.length > 0) {
      return `I attempted the modification, but encountered ${result.errors.length} error${result.errors.length === 1 ? '' : 's'}. See the details above for more information.`
    }

    const actionCount = result.executedActions?.length || 0
    if (actionCount === 0) {
      return "I created a plan but didn't execute any actions. This might mean the requested changes were already in place or couldn't be applied."
    }

    let summary = `Successfully executed ${actionCount} action${actionCount === 1 ? '' : 's'}. `

    if (result.plan?.intent) {
      summary += `Goal: ${result.plan.intent}`
    }

    if (result.summary) {
      summary += `\n\n${result.summary}`
    }

    return summary
  }

  /**
   * Create a natural language summary of creation results
   */
  private summarizeCreationResult(result: any): string {
    const spreadsheetUrl = `https://docs.google.com/spreadsheets/d/${result.spreadsheetId}`
    let summary = `I've created a new spreadsheet: **${result.plan.title}**\n\n`
    summary += `[Open in Google Sheets](${spreadsheetUrl})\n\n`

    const sheetCount = result.plan.sheets?.length || 0
    summary += `The spreadsheet includes ${sheetCount} sheet${sheetCount === 1 ? '' : 's'} with structured columns and example data. `

    if (result.plan.documentation) {
      summary += 'A documentation sheet with usage instructions has also been added.'
    }

    return summary
  }
}
