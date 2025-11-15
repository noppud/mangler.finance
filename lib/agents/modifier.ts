// Sheet modification engine using LLM to plan and execute changes

import { LLMClient } from '../llm/client';
import { ContextBuilder } from '../sheets/context-builder';
import { SheetsClient } from '../sheets/client';
import {
  ModificationRequest,
  ModificationResult,
  AgentPlan,
  AgentAction,
  AgentActionType,
} from '@/types/agents';
import { PROMPTS, formatSheetContext } from '../llm/prompts';
import { v4 as uuidv4 } from 'uuid';

type SheetsModifierClient = Pick<SheetsClient, 'readRange' | 'writeRange'>;

export class SheetModifier {
  constructor(
    private sheetsClient: SheetsModifierClient,
    private contextBuilder: ContextBuilder,
    private llmClient: LLMClient
  ) {}

  /**
   * Modify a sheet based on natural language prompt
   */
  async modify(request: ModificationRequest): Promise<ModificationResult> {
    // Build context if not provided
    const context = request.context || await this.contextBuilder.buildContext(
      request.spreadsheetId,
      request.sheetTitle || ''
    );

    // Generate plan using LLM
    const plan = await this.generatePlan(request.prompt, context, request.constraints);

    // Validate plan against constraints
    this.validatePlan(plan, request.constraints);

    // Execute plan (dry-run first if needed)
    const executedActions: AgentAction[] = [];
    const changedRanges: string[] = [];
    const errors: string[] = [];

    try {
      for (const action of plan.actions) {
        try {
          await this.executeAction(
            request.spreadsheetId,
            request.sheetTitle || context.sheetMetadata.title,
            action
          );
          executedActions.push(action);

          if (action.affectedRange) {
            changedRanges.push(action.affectedRange);
          }
        } catch (error: any) {
          errors.push(`Failed to execute ${action.type}: ${error.message}`);
        }
      }

      return {
        success: errors.length === 0,
        plan,
        executedActions,
        errors: errors.length > 0 ? errors : undefined,
        changedRanges,
        summary: this.generateSummary(executedActions),
      };
    } catch (error: any) {
      return {
        success: false,
        plan,
        executedActions,
        errors: [error.message],
        changedRanges,
        summary: 'Modification failed',
      };
    }
  }

  /**
   * Generate a modification plan using LLM
   */
  private async generatePlan(
    userPrompt: string,
    context: any,
    constraints?: any
  ): Promise<AgentPlan> {
    const contextStr = formatSheetContext(context);
    const llmPrompt = PROMPTS.MODIFICATION_PLAN.user(userPrompt, contextStr);

    const response = await this.llmClient.chatJSON<any>(
      [
        { role: 'system', content: PROMPTS.MODIFICATION_PLAN.system },
        { role: 'user', content: llmPrompt },
      ],
      { temperature: 0.3 }
    );

    // Calculate overall impact
    const overallImpact = {
      totalRowsAffected: response.actions.reduce(
        (sum: number, a: any) => sum + (a.estimatedImpact?.rowsAffected || 0),
        0
      ),
      totalColumnsAffected: response.actions.reduce(
        (sum: number, a: any) => sum + (a.estimatedImpact?.columnsAffected || 0),
        0
      ),
      hasDestructiveActions: response.actions.some(
        (a: any) => a.estimatedImpact?.destructive
      ),
      estimatedDuration: this.estimateDuration(response.actions.length),
    };

    return {
      id: uuidv4(),
      userPrompt,
      intent: response.intent,
      actions: response.actions,
      overallImpact,
      warnings: response.warnings || [],
      requiresConfirmation: overallImpact.hasDestructiveActions ||
        overallImpact.totalRowsAffected > 100,
    };
  }

  /**
   * Validate plan against constraints
   */
  private validatePlan(plan: AgentPlan, constraints?: any): void {
    if (!constraints) return;

    if (
      constraints.maxRowsAffected &&
      plan.overallImpact.totalRowsAffected > constraints.maxRowsAffected
    ) {
      throw new Error(
        `Plan would affect ${plan.overallImpact.totalRowsAffected} rows, exceeding limit of ${constraints.maxRowsAffected}`
      );
    }

    if (
      constraints.maxColumnsAffected &&
      plan.overallImpact.totalColumnsAffected > constraints.maxColumnsAffected
    ) {
      throw new Error(
        `Plan would affect ${plan.overallImpact.totalColumnsAffected} columns, exceeding limit of ${constraints.maxColumnsAffected}`
      );
    }

    if (
      !constraints.allowDestructive &&
      plan.overallImpact.hasDestructiveActions
    ) {
      throw new Error('Plan contains destructive actions but they are not allowed');
    }
  }

  /**
   * Execute a single action
   */
  private async executeAction(
    spreadsheetId: string,
    sheetTitle: string,
    action: AgentAction
  ): Promise<void> {
    switch (action.type) {
      case 'add_column':
        await this.executeAddColumn(spreadsheetId, sheetTitle, action);
        break;

      case 'rename_column':
        await this.executeRenameColumn(spreadsheetId, sheetTitle, action);
        break;

      case 'update_formula':
        await this.executeUpdateFormula(spreadsheetId, sheetTitle, action);
        break;

      case 'set_value':
        await this.executeSetValue(spreadsheetId, sheetTitle, action);
        break;

      case 'clear_range':
        await this.executeClearRange(spreadsheetId, sheetTitle, action);
        break;

      case 'normalize_data':
        await this.executeNormalizeData(spreadsheetId, sheetTitle, action);
        break;

      default:
        throw new Error(`Unsupported action type: ${action.type}`);
    }
  }

  /**
   * Execute add_column action
   */
  private async executeAddColumn(
    spreadsheetId: string,
    sheetTitle: string,
    action: AgentAction
  ): Promise<void> {
    const { columnName, columnIndex, defaultValue } = action.params;

    // Get current data
    const range = `${sheetTitle}!A1:Z`;
    const data = await this.sheetsClient.readRange(spreadsheetId, range);

    // Insert column header
    const headerRange = `${sheetTitle}!${this.columnToLetter(columnIndex + 1)}1`;
    await this.sheetsClient.writeRange(spreadsheetId, headerRange, [[columnName]]);

    // Optionally fill with default values
    if (defaultValue && data.values.length > 1) {
      const dataRange = `${sheetTitle}!${this.columnToLetter(columnIndex + 1)}2:${this.columnToLetter(columnIndex + 1)}${data.values.length}`;
      const values = Array(data.values.length - 1).fill([defaultValue]);
      await this.sheetsClient.writeRange(spreadsheetId, dataRange, values);
    }
  }

  /**
   * Execute rename_column action
   */
  private async executeRenameColumn(
    spreadsheetId: string,
    sheetTitle: string,
    action: AgentAction
  ): Promise<void> {
    const { columnIndex, newName } = action.params;
    const range = `${sheetTitle}!${this.columnToLetter(columnIndex + 1)}1`;
    await this.sheetsClient.writeRange(spreadsheetId, range, [[newName]]);
  }

  /**
   * Execute update_formula action
   */
  private async executeUpdateFormula(
    spreadsheetId: string,
    sheetTitle: string,
    action: AgentAction
  ): Promise<void> {
    const { range, formula } = action.params;
    const fullRange = `${sheetTitle}!${range}`;
    await this.sheetsClient.writeRange(spreadsheetId, fullRange, [[formula]], 'USER_ENTERED');
  }

  /**
   * Execute set_value action
   */
  private async executeSetValue(
    spreadsheetId: string,
    sheetTitle: string,
    action: AgentAction
  ): Promise<void> {
    const { range, value } = action.params;
    const fullRange = `${sheetTitle}!${range}`;
    await this.sheetsClient.writeRange(spreadsheetId, fullRange, [[value]]);
  }

  /**
   * Execute clear_range action
   */
  private async executeClearRange(
    spreadsheetId: string,
    sheetTitle: string,
    action: AgentAction
  ): Promise<void> {
    const { range } = action.params;
    const fullRange = `${sheetTitle}!${range}`;

    // Get dimensions of range to clear
    const data = await this.sheetsClient.readRange(spreadsheetId, fullRange);
    const emptyValues = data.values.map(row => row.map(() => ''));

    await this.sheetsClient.writeRange(spreadsheetId, fullRange, emptyValues);
  }

  /**
   * Execute normalize_data action
   */
  private async executeNormalizeData(
    spreadsheetId: string,
    sheetTitle: string,
    action: AgentAction
  ): Promise<void> {
    const { range, normalizationType } = action.params;
    const fullRange = `${sheetTitle}!${range}`;

    // Get data
    const data = await this.sheetsClient.readRange(spreadsheetId, fullRange);

    // Apply normalization based on type
    const normalizedValues = data.values.map(row =>
      row.map(cell => {
        if (normalizationType === 'trim') {
          return typeof cell.value === 'string' ? cell.value.trim() : cell.value;
        } else if (normalizationType === 'uppercase') {
          return typeof cell.value === 'string' ? cell.value.toUpperCase() : cell.value;
        } else if (normalizationType === 'lowercase') {
          return typeof cell.value === 'string' ? cell.value.toLowerCase() : cell.value;
        }
        return cell.value;
      })
    );

    await this.sheetsClient.writeRange(spreadsheetId, fullRange, normalizedValues);
  }

  /**
   * Generate summary of executed actions
   */
  private generateSummary(actions: AgentAction[]): string {
    if (actions.length === 0) return 'No actions executed';

    const actionTypes = actions.map(a => a.type).join(', ');
    return `Successfully executed ${actions.length} action(s): ${actionTypes}`;
  }

  /**
   * Estimate duration for actions
   */
  private estimateDuration(actionCount: number): string {
    if (actionCount <= 3) return '<10 seconds';
    if (actionCount <= 10) return '10-30 seconds';
    return '30+ seconds';
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
