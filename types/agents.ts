// Types for agentic operations

import { SheetContext, Range } from './sheets';
import { SheetIssue } from './errors';

export type AgentActionType =
  | 'add_column'
  | 'remove_column'
  | 'rename_column'
  | 'update_formula'
  | 'normalize_data'
  | 'reformat_cells'
  | 'add_validation'
  | 'fix_error'
  | 'add_sheet'
  | 'delete_sheet'
  | 'sort_range'
  | 'filter_data'
  | 'merge_cells'
  | 'unmerge_cells'
  | 'set_value'
  | 'clear_range';

export interface AgentAction {
  type: AgentActionType;
  description: string;
  params: Record<string, any>;
  affectedRange?: string;
  estimatedImpact: {
    rowsAffected?: number;
    columnsAffected?: number;
    destructive: boolean;
  };
}

export interface AgentPlan {
  id: string;
  userPrompt: string;
  intent: string;
  actions: AgentAction[];
  overallImpact: {
    totalRowsAffected: number;
    totalColumnsAffected: number;
    hasDestructiveActions: boolean;
    estimatedDuration: string;
  };
  warnings: string[];
  requiresConfirmation: boolean;
}

export interface ModificationRequest {
  spreadsheetId: string;
  sheetTitle?: string;
  prompt: string;
  context?: SheetContext;
  constraints?: {
    maxRowsAffected?: number;
    maxColumnsAffected?: number;
    protectedRanges?: string[];
    allowDestructive?: boolean;
  };
}

export interface ModificationResult {
  success: boolean;
  plan: AgentPlan;
  executedActions: AgentAction[];
  errors?: string[];
  changedRanges: string[];
  summary: string;
}

export interface SheetCreationRequest {
  prompt: string;
  constraints?: {
    maxSheets?: number;
    maxColumns?: number;
    generateExamples?: boolean;
  };
}

export interface SheetCreationPlan {
  title: string;
  sheets: {
    name: string;
    purpose: string;
    columns: {
      name: string;
      type: string;
      validation?: string;
      formula?: string;
    }[];
    exampleRows?: any[][];
  }[];
  documentation?: string;
}

export interface SheetCreationResult {
  success: boolean;
  spreadsheetId?: string;
  spreadsheetUrl?: string;
  plan: SheetCreationPlan;
  errors?: string[];
}

export interface AgentSession {
  sessionId: string;
  startedAt: string;
  spreadsheetId?: string;
  history: {
    timestamp: string;
    type: 'detection' | 'modification' | 'creation';
    prompt?: string;
    result: any;
  }[];
  userPreferences?: Record<string, any>;
}
