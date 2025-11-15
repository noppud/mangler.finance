'use client'

import { Card, CardHeader, CardBody } from '../ui/Card'
import type { SheetCreationResult } from '@/types/agents'

interface CreationResultProps {
  result: SheetCreationResult
}

export function CreationResult({ result }: CreationResultProps) {
  if (!result) {
    return null
  }

  const spreadsheetUrl = `https://docs.google.com/spreadsheets/d/${result.spreadsheetId}`

  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-semibold text-green-700 dark:text-green-300">Sheet Created Successfully!</h3>
      </CardHeader>
      <CardBody>
        <div className="space-y-4">
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg dark:bg-green-950/40 dark:border-green-900/60">
            <a
              href={spreadsheetUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline font-medium dark:text-blue-300 text-lg"
            >
              Open your new spreadsheet →
            </a>
          </div>

          {result.plan && (
            <div>
              <h4 className="font-medium text-gray-900 dark:text-slate-50 mb-2">Title: {result.plan.title}</h4>

              {result.plan.sheets && result.plan.sheets.length > 0 && (
                <>
                  <h4 className="font-medium text-gray-900 dark:text-slate-50 mb-2 mt-4">Sheets:</h4>
                  <div className="space-y-3">
                    {result.plan.sheets.map((sheet: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-4 bg-gray-50 border border-gray-200 rounded dark:bg-slate-900 dark:border-slate-700"
                      >
                        <h5 className="font-semibold text-gray-900 dark:text-slate-50 mb-1">{sheet.name}</h5>
                        <p className="text-sm text-gray-600 dark:text-slate-300 mb-3">{sheet.purpose}</p>

                        {sheet.columns && sheet.columns.length > 0 && (
                          <div className="space-y-1">
                            <p className="text-sm font-medium text-gray-700 dark:text-slate-300">Columns:</p>
                            <ul className="grid grid-cols-2 gap-2">
                              {sheet.columns.map((col: any, colIdx: number) => (
                                <li
                                  key={colIdx}
                                  className="text-sm text-gray-600 bg-white px-2 py-1 rounded border border-gray-200 dark:text-slate-200 dark:bg-slate-900 dark:border-slate-700"
                                >
                                  {col.name}{' '}
                                  <span className="text-gray-400 dark:text-slate-500">({col.type})</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}

              {result.plan.documentation && (
                <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded dark:bg-blue-950/40 dark:border-blue-900/60">
                  <h4 className="font-medium text-blue-900 dark:text-blue-200 mb-2">Documentation:</h4>
                  <p className="text-sm text-blue-800 dark:text-blue-100 whitespace-pre-wrap">
                    {result.plan.documentation}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  )
}
