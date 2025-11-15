// Types for error detection and reporting

import { CellLocation } from './sheets';

export type ErrorSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type ErrorCategory =
  | 'formula_error'
  | 'inconsistent_formula'
  | 'type_mismatch'
  | 'outlier'
  | 'missing_value'
  | 'broken_reference'
  | 'duplicate_key'
  | 'constraint_violation'
  | 'semantic_anomaly'
  | 'logical_inconsistency'
  | 'suspicious_pattern';

export interface SheetIssue {
  id: string;
  category: ErrorCategory;
  severity: ErrorSeverity;
  title: string;
  description: string;
  location: CellLocation | CellLocation[];
  affectedCells?: number;
  detectedBy: 'rule' | 'llm';
  suggestedFix?: string;
  autoFixable: boolean;
  confidence?: number; // 0-1 for LLM-detected issues
}

export interface IssueDetectionResult {
  spreadsheetId: string;
  sheetTitle: string;
  issues: SheetIssue[];
  summary: {
    totalIssues: number;
    bySeverity: Record<ErrorSeverity, number>;
    byCategory: Record<ErrorCategory, number>;
    autoFixableCount: number;
  };
  scanTimestamp: string;
}

export interface IssueDetectionConfig {
  enableRuleBased: boolean;
  enableLLMBased: boolean;
  minSeverity: ErrorSeverity;
  maxIssues?: number;
  categoriesToCheck: ErrorCategory[];
}
