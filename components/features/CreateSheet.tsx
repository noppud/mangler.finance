'use client';

import React, { useState } from 'react';
import { Button } from '../ui/Button';
import { TextArea } from '../ui/Input';
import { Card, CardHeader, CardBody } from '../ui/Card';

export function CreateSheet() {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleCreate = async () => {
    if (!prompt) {
      setError('Please describe the sheet you want to create');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await fetch('/api/sheets/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        throw new Error('Failed to create sheet');
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <h2 className="text-xl font-semibold">Create New Sheet</h2>
          <p className="text-sm text-gray-600 mt-1">
            Describe the spreadsheet you need, and the AI will create it for you.
          </p>
        </CardHeader>
        <CardBody>
          <div className="space-y-4">
            <TextArea
              label="Describe your spreadsheet"
              placeholder="Create a project management tracker with tasks, deadlines, assignees, and status..."
              rows={6}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
            <Button onClick={handleCreate} disabled={loading} className="w-full">
              {loading ? 'Creating...' : 'Create Sheet'}
            </Button>
          </div>
        </CardBody>
      </Card>

      {error && (
        <div
          className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 shadow-sm dark:border-red-900 dark:bg-red-950/60 dark:text-red-200"
          role="alert"
        >
          <div className="mt-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-red-100 text-xs font-semibold">
            !
          </div>
          <p className="flex-1">{error}</p>
        </div>
      )}

      {result && result.success && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-green-700 dark:text-green-300">
              Sheet Created Successfully!
            </h3>
          </CardHeader>
          <CardBody>
            <div className="space-y-4">
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <a
                  href={result.spreadsheetUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline font-medium dark:text-blue-300"
                >
                  Open your new spreadsheet →
                </a>
              </div>

              {result.plan && (
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-slate-50 mb-2">
                    Title: {result.plan.title}
                  </h4>

                  <h4 className="font-medium text-gray-900 dark:text-slate-50 mb-2 mt-4">
                    Sheets:
                  </h4>
                  <div className="space-y-3">
                    {result.plan.sheets.map((sheet: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-4 bg-gray-50 border border-gray-200 rounded dark:bg-slate-900 dark:border-slate-700"
                      >
                        <h5 className="font-semibold text-gray-900 dark:text-slate-50 mb-1">
                          {sheet.name}
                        </h5>
                        <p className="text-sm text-gray-600 dark:text-slate-300 mb-3">
                          {sheet.purpose}
                        </p>

                        <div className="space-y-1">
                          <p className="text-sm font-medium text-gray-700 dark:text-slate-300">
                            Columns:
                          </p>
                          <ul className="grid grid-cols-2 gap-2">
                            {sheet.columns.map((col: any, colIdx: number) => (
                              <li
                                key={colIdx}
                                className="text-sm text-gray-600 bg-white px-2 py-1 rounded border border-gray-200 dark:text-slate-200 dark:bg-slate-900 dark:border-slate-700"
                              >
                                {col.name}{' '}
                                <span className="text-gray-400 dark:text-slate-500">
                                  ({col.type})
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    ))}
                  </div>

                  {result.plan.documentation && (
                    <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded dark:bg-blue-950/40 dark:border-blue-900/60">
                      <h4 className="font-medium text-blue-900 dark:text-blue-200 mb-2">
                        Documentation:
                      </h4>
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
      )}

      {result && !result.success && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-red-700 dark:text-red-300">
              Failed to Create Sheet
            </h3>
          </CardHeader>
          <CardBody>
            <div className="p-3 bg-red-50 border border-red-200 rounded dark:bg-red-950/40 dark:border-red-900/60">
              <ul className="list-disc list-inside text-sm text-red-800 dark:text-red-100">
                {result.errors?.map((error: string, idx: number) => (
                  <li key={idx}>{error}</li>
                ))}
              </ul>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
