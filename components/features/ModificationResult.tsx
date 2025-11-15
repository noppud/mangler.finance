'use client'

import { Card, CardHeader, CardBody } from '../ui/Card'
import type { ModificationResult as ModificationResultType } from '@/types/agents'

interface ModificationResultProps {
  result: ModificationResultType
}

export function ModificationResult({ result }: ModificationResultProps) {
  if (!result) {
    return null
  }

  const hasErrors = result.errors && result.errors.length > 0
  const hasWarnings = result.plan?.warnings && result.plan.warnings.length > 0

  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-semibold">{hasErrors ? 'Modification Failed' : 'Modification Complete'}</h3>
      </CardHeader>
      <CardBody>
        <div className="space-y-4">
          {result.plan && (
            <div>
              <h4 className="font-medium text-gray-900 dark:text-slate-50 mb-2">Plan:</h4>
              <p className="text-sm text-gray-600 dark:text-slate-300 mb-3">{result.plan.intent}</p>

              {result.plan.actions && result.plan.actions.length > 0 && (
                <>
                  <h4 className="font-medium text-gray-900 dark:text-slate-50 mb-2">Actions Executed:</h4>
                  <ul className="space-y-2">
                    {result.plan.actions.map((action: any, idx: number) => (
                      <li
                        key={idx}
                        className="text-sm p-3 bg-gray-50 border border-gray-200 rounded dark:bg-slate-900 dark:border-slate-700"
                      >
                        <span className="font-medium">{action.type}: </span>
                        {action.description}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}

          {hasWarnings && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded dark:bg-yellow-950/40 dark:border-yellow-900/60">
              <h4 className="font-medium text-yellow-900 dark:text-yellow-200 mb-2">Warnings:</h4>
              <ul className="list-disc list-inside text-sm text-yellow-800 dark:text-yellow-100">
                {result.plan!.warnings.map((warning: string, idx: number) => (
                  <li key={idx}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          {hasErrors && (
            <div className="p-3 bg-red-50 border border-red-200 rounded dark:bg-red-950/40 dark:border-red-900/60">
              <h4 className="font-medium text-red-900 dark:text-red-200 mb-2">Errors:</h4>
              <ul className="list-disc list-inside text-sm text-red-800 dark:text-red-100">
                {result.errors!.map((error: string, idx: number) => (
                  <li key={idx}>{error}</li>
                ))}
              </ul>
            </div>
          )}

          {result.summary && <p className="text-sm text-gray-600 dark:text-slate-300">{result.summary}</p>}
        </div>
      </CardBody>
    </Card>
  )
}
