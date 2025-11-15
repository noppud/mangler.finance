// Mistake detection engine combining rule-based and LLM-based analysis

import { LLMClient } from '../llm/client';
import { ContextBuilder } from '../sheets/context-builder';
import {
  SheetIssue,
  IssueDetectionResult,
  IssueDetectionConfig,
  ErrorSeverity,
  ErrorCategory,
} from '@/types/errors';
import { SheetContext, CellValue } from '@/types/sheets';
import { PROMPTS, formatSheetContext, formatSampleData } from '../llm/prompts';
import { v4 as uuidv4 } from 'uuid';

export class MistakeDetector {
  constructor(
    private contextBuilder: ContextBuilder,
    private llmClient: LLMClient
  ) {}

  /**
   * Detect issues in a sheet
   */
  async detectIssues(
    spreadsheetId: string,
    sheetTitle: string,
    config: IssueDetectionConfig
  ): Promise<IssueDetectionResult> {
    const context = await this.contextBuilder.buildContext(spreadsheetId, sheetTitle);
    const issues: SheetIssue[] = [];

    // Run rule-based checks
    if (config.enableRuleBased) {
      const ruleBasedIssues = await this.runRuleBasedChecks(context, config);
      issues.push(...ruleBasedIssues);
    }

    // Run LLM-based checks
    if (config.enableLLMBased) {
      const llmIssues = await this.runLLMBasedChecks(context, config);
      issues.push(...llmIssues);
    }

    // Filter by severity
    const filteredIssues = this.filterBySeverity(issues, config.minSeverity);

    // Limit number of issues if specified
    const finalIssues = config.maxIssues
      ? filteredIssues.slice(0, config.maxIssues)
      : filteredIssues;

    return {
      spreadsheetId,
      sheetTitle,
      issues: finalIssues,
      summary: this.generateSummary(finalIssues),
      scanTimestamp: new Date().toISOString(),
    };
  }

  /**
   * Run rule-based checks
   */
  private async runRuleBasedChecks(
    context: SheetContext,
    config: IssueDetectionConfig
  ): Promise<SheetIssue[]> {
    const issues: SheetIssue[] = [];

    // Check for formula errors
    if (config.categoriesToCheck.includes('formula_error')) {
      issues.push(...this.checkFormulaErrors(context));
    }

    // Check for inconsistent formulas
    if (config.categoriesToCheck.includes('inconsistent_formula')) {
      issues.push(...this.checkInconsistentFormulas(context));
    }

    // Check for type mismatches
    if (config.categoriesToCheck.includes('type_mismatch')) {
      issues.push(...this.checkTypeMismatches(context));
    }

    // Check for missing values in key columns
    if (config.categoriesToCheck.includes('missing_value')) {
      issues.push(...this.checkMissingValues(context));
    }

    // Check for duplicate keys
    if (config.categoriesToCheck.includes('duplicate_key')) {
      issues.push(...this.checkDuplicateKeys(context));
    }

    return issues;
  }

  /**
   * Check for formula errors
   */
  private checkFormulaErrors(context: SheetContext): SheetIssue[] {
    const issues: SheetIssue[] = [];

    if (context.summary.errorCells > 0) {
      // In a real implementation, we'd iterate through cells to find exact locations
      issues.push({
        id: uuidv4(),
        category: 'formula_error',
        severity: 'high',
        title: 'Formula errors detected',
        description: `Found ${context.summary.errorCells} cells with formula errors (e.g., #REF!, #VALUE!, #DIV/0!)`,
        location: {
          sheet: context.sheetMetadata.title,
          row: 0,
          col: 0,
          a1Notation: context.sheetMetadata.title,
        },
        affectedCells: context.summary.errorCells,
        detectedBy: 'rule',
        suggestedFix: 'Review and fix formula references and calculations',
        autoFixable: false,
      });
    }

    return issues;
  }

  /**
   * Check for inconsistent formulas in columns
   */
  private checkInconsistentFormulas(context: SheetContext): SheetIssue[] {
    const issues: SheetIssue[] = [];

    // This would require analyzing formula patterns in columns
    // For now, return empty array (implement with actual data access)

    return issues;
  }

  /**
   * Check for type mismatches in columns
   */
  private checkTypeMismatches(context: SheetContext): SheetIssue[] {
    const issues: SheetIssue[] = [];

    context.tableRegions.forEach(region => {
      region.columns.forEach(col => {
        if (col.type === 'mixed') {
          issues.push({
            id: uuidv4(),
            category: 'type_mismatch',
            severity: 'medium',
            title: `Mixed data types in column "${col.name}"`,
            description: `Column contains multiple data types. This may indicate data quality issues.`,
            location: {
              sheet: context.sheetMetadata.title,
              row: 0,
              col: col.index,
              a1Notation: `${context.sheetMetadata.title}!${this.columnToLetter(col.index + 1)}:${this.columnToLetter(col.index + 1)}`,
            },
            detectedBy: 'rule',
            suggestedFix: 'Standardize data types in this column',
            autoFixable: false,
          });
        }
      });
    });

    return issues;
  }

  /**
   * Check for missing values in non-nullable columns
   */
  private checkMissingValues(context: SheetContext): SheetIssue[] {
    const issues: SheetIssue[] = [];

    context.tableRegions.forEach(region => {
      region.columns.forEach(col => {
        if (col.nullable && col.index < 3) {
          // Assume first 3 columns should not be nullable (ID, name, etc.)
          issues.push({
            id: uuidv4(),
            category: 'missing_value',
            severity: 'low',
            title: `Missing values in key column "${col.name}"`,
            description: `Key column contains empty cells which may indicate incomplete data.`,
            location: {
              sheet: context.sheetMetadata.title,
              row: 0,
              col: col.index,
              a1Notation: `${context.sheetMetadata.title}!${this.columnToLetter(col.index + 1)}:${this.columnToLetter(col.index + 1)}`,
            },
            detectedBy: 'rule',
            suggestedFix: 'Fill in missing values or mark as N/A',
            autoFixable: false,
          });
        }
      });
    });

    return issues;
  }

  /**
   * Check for duplicate keys
   */
  private checkDuplicateKeys(context: SheetContext): SheetIssue[] {
    const issues: SheetIssue[] = [];

    // Would need to analyze actual data to detect duplicates
    // For now, return empty array

    return issues;
  }

  /**
   * Run LLM-based checks for semantic and logical issues
   */
  private async runLLMBasedChecks(
    context: SheetContext,
    config: IssueDetectionConfig
  ): Promise<SheetIssue[]> {
    try {
      const contextStr = formatSheetContext(context);
      const sampleDataStr = context.sampleData
        ? formatSampleData(context.sampleData[0]?.values || [])
        : 'No sample data';

      const userPrompt = PROMPTS.MISTAKE_DETECTION.user(contextStr, sampleDataStr);

      const response = await this.llmClient.chatJSON<any[]>(
        [
          { role: 'system', content: PROMPTS.MISTAKE_DETECTION.system },
          { role: 'user', content: userPrompt },
        ],
        { temperature: 0.3 } // Lower temperature for more consistent analysis
      );

      // Map LLM response to SheetIssue format
      const issues: SheetIssue[] = response.map((item: any) => ({
        id: uuidv4(),
        category: item.category as ErrorCategory,
        severity: item.severity as ErrorSeverity,
        title: item.title,
        description: item.description,
        location: this.parseLocation(item.location, context.sheetMetadata.title),
        detectedBy: 'llm',
        suggestedFix: item.suggestedFix,
        autoFixable: false,
        confidence: item.confidence || 0.8,
      }));

      return issues;
    } catch (error) {
      console.error('LLM-based detection failed:', error);
      return [];
    }
  }

  /**
   * Parse location string to CellLocation
   */
  private parseLocation(location: string, sheetTitle: string): any {
    // Simple A1 notation parser
    return {
      sheet: sheetTitle,
      row: 0,
      col: 0,
      a1Notation: location,
    };
  }

  /**
   * Filter issues by severity
   */
  private filterBySeverity(issues: SheetIssue[], minSeverity: ErrorSeverity): SheetIssue[] {
    const severityOrder: ErrorSeverity[] = ['critical', 'high', 'medium', 'low', 'info'];
    const minIndex = severityOrder.indexOf(minSeverity);

    return issues.filter(issue => {
      const issueIndex = severityOrder.indexOf(issue.severity);
      return issueIndex <= minIndex;
    });
  }

  /**
   * Generate summary statistics
   */
  private generateSummary(issues: SheetIssue[]) {
    const bySeverity: Record<ErrorSeverity, number> = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
      info: 0,
    };

    const byCategory: Record<ErrorCategory, number> = {
      formula_error: 0,
      inconsistent_formula: 0,
      type_mismatch: 0,
      outlier: 0,
      missing_value: 0,
      broken_reference: 0,
      duplicate_key: 0,
      constraint_violation: 0,
      semantic_anomaly: 0,
      logical_inconsistency: 0,
      suspicious_pattern: 0,
    };

    let autoFixableCount = 0;

    issues.forEach(issue => {
      bySeverity[issue.severity]++;
      byCategory[issue.category]++;
      if (issue.autoFixable) autoFixableCount++;
    });

    return {
      totalIssues: issues.length,
      bySeverity,
      byCategory,
      autoFixableCount,
    };
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
