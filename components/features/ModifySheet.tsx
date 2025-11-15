'use client';

import React, { useState } from 'react';
import { Button } from '../ui/Button';
import { Input, TextArea } from '../ui/Input';
import { Card, CardHeader, CardBody } from '../ui/Card';

export function ModifySheet() {
  const [spreadsheetId, setSpreadsheetId] = useState('https://docs.google.com/spreadsheets/d/1xAA7d_3SUnEI3cLsya8Z8RRl3QghWMmsYOyrQXjDP08/edit?gid=0#gid=0');
  const [sheetTitle, setSheetTitle] = useState('Taulukko1');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const handleModify = async () => {
    if (!spreadsheetId || !prompt) {
      setError('Please provide spreadsheet ID and a prompt');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await fetch('/api/sheets/modify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spreadsheetId, sheetTitle, prompt }),
      });

      if (!response.ok) {
        throw new Error('Failed to modify sheet');
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
          <h2 className="text-xl font-semibold">Modify Existing Sheet</h2>
          <p className="text-sm text-gray-600 mt-1">
            Describe what you want to change, and the AI will make the modifications.
          </p>
        </CardHeader>
        <CardBody>
          <div className="space-y-4">
            <Input
              label="Spreadsheet ID"
              placeholder="1ABC...XYZ"
              value={spreadsheetId}
              onChange={(e) => setSpreadsheetId(e.target.value)}
            />
            <Input
              label="Sheet Title (optional)"
              placeholder="Sheet1"
              value={sheetTitle}
              onChange={(e) => setSheetTitle(e.target.value)}
            />
            <TextArea
              label="What do you want to do?"
              placeholder="Add a new column called 'Total' that sums columns B and C..."
              rows={4}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
            <Button onClick={handleModify} disabled={loading} className="w-full">
              {loading ? 'Processing...' : 'Modify Sheet'}
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

      {result && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">
              {result.success ? 'Modification Complete' : 'Modification Failed'}
            </h3>
          </CardHeader>
          <CardBody>
            <div className="space-y-4">
              {result.plan && (
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-slate-50 mb-2">
                    Plan:
                  </h4>
                  <p className="text-sm text-gray-600 dark:text-slate-300 mb-3">
                    {result.plan.intent}
                  </p>

                  <h4 className="font-medium text-gray-900 dark:text-slate-50 mb-2">
                    Actions Executed:
                  </h4>
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
                </div>
              )}

              {result.warnings && result.warnings.length > 0 && (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded dark:bg-yellow-950/40 dark:border-yellow-900/60">
                  <h4 className="font-medium text-yellow-900 dark:text-yellow-200 mb-2">
                    Warnings:
                  </h4>
                  <ul className="list-disc list-inside text-sm text-yellow-800 dark:text-yellow-100">
                    {result.warnings.map((warning: string, idx: number) => (
                      <li key={idx}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              {result.errors && result.errors.length > 0 && (
                <div className="p-3 bg-red-50 border border-red-200 rounded dark:bg-red-950/40 dark:border-red-900/60">
                  <h4 className="font-medium text-red-900 dark:text-red-200 mb-2">
                    Errors:
                  </h4>
                  <ul className="list-disc list-inside text-sm text-red-800 dark:text-red-100">
                    {result.errors.map((error: string, idx: number) => (
                      <li key={idx}>{error}</li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="text-sm text-gray-600 dark:text-slate-300">
                {result.summary}
              </p>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
