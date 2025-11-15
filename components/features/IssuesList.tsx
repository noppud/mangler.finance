'use client'

import { Card, CardHeader, CardBody } from '../ui/Card'
import type { IssueDetectionResult } from '@/types/errors'

interface IssuesListProps {
  result: IssueDetectionResult
}

export function IssuesList({ result }: IssuesListProps) {
  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical:
        'text-red-700 bg-red-100 dark:text-red-200 dark:bg-red-950/60 border border-red-200/70 dark:border-red-900/70',
      high: 'text-orange-700 bg-orange-100 dark:text-orange-200 dark:bg-orange-950/60 border border-orange-200/70 dark:border-orange-900/70',
      medium:
        'text-yellow-700 bg-yellow-100 dark:text-yellow-200 dark:bg-yellow-950/60 border border-yellow-200/70 dark:border-yellow-900/70',
      low: 'text-blue-700 bg-blue-100 dark:text-blue-200 dark:bg-blue-950/60 border border-blue-200/70 dark:border-blue-900/70',
      info: 'text-gray-700 bg-gray-100 dark:text-slate-200 dark:bg-slate-900/60 border border-gray-200/70 dark:border-slate-800/70',
    }
    return (
      colors[severity] ||
      'text-gray-700 bg-gray-100 dark:text-slate-200 dark:bg-slate-900/60 border border-gray-200/70 dark:border-slate-800/70'
    )
  }

  if (!result || !result.issues) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-semibold">
          {result.issues.length === 0
            ? 'No Issues Found'
            : `Found ${result.issues.length} Issue${result.issues.length !== 1 ? 's' : ''}`}
        </h3>
      </CardHeader>
      <CardBody>
        {result.issues.length === 0 ? (
          <div className="text-center py-6">
            <div className="text-4xl mb-3">✅</div>
            <p className="text-gray-600 dark:text-slate-300">
              Great! Your sheet looks clean and well-structured.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {result.issues.map((issue) => (
              <div key={issue.id} className="border border-gray-200 rounded-lg p-4 dark:border-slate-700">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getSeverityColor(issue.severity)}`}>
                        {issue.severity.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-slate-400">{issue.category}</span>
                    </div>
                    <h4 className="font-semibold text-gray-900 dark:text-slate-50 mb-1">{issue.title}</h4>
                    <p className="text-sm text-gray-600 dark:text-slate-300 mb-2">{issue.description}</p>
                    {issue.suggestedFix && (
                      <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded dark:bg-blue-950/40 dark:border-blue-900/60">
                        <p className="text-sm font-medium text-blue-900 dark:text-blue-200 mb-1">Suggested Fix:</p>
                        <p className="text-sm text-blue-800 dark:text-blue-100">{issue.suggestedFix}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  )
}
