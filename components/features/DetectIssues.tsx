'use client';

import React, { useState } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card, CardHeader, CardBody } from '../ui/Card';

interface Issue {
  id: string;
  category: string;
  severity: string;
  title: string;
  description: string;
  location: any;
  suggestedFix?: string;
}

export function DetectIssues() {
  const [spreadsheetId, setSpreadsheetId] = useState('https://docs.google.com/spreadsheets/d/1xAA7d_3SUnEI3cLsya8Z8RRl3QghWMmsYOyrQXjDP08/edit?gid=0#gid=0');
  const [sheetTitle, setSheetTitle] = useState('Taulukko1');
  const [loading, setLoading] = useState(false);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [error, setError] = useState('');

  const handleDetect = async () => {
    if (!spreadsheetId || !sheetTitle) {
      setError('Please provide both spreadsheet ID and sheet title');
      return;
    }

    setLoading(true);
    setError('');
    setIssues([]);

    try {
      const response = await fetch('/api/sheets/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spreadsheetId, sheetTitle }),
      });

      if (!response.ok) {
        let message = 'Failed to detect issues';
        try {
          const data = await response.json();
          if (typeof data?.error === 'string' && data.error.length > 0) {
            message = data.error;
          }
        } catch {
          // Ignore JSON parse errors and fall back to default message
        }
        throw new Error(message);
      }

      const result = await response.json();
      setIssues(result.issues || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical:
        'text-red-700 bg-red-100 dark:text-red-200 dark:bg-red-950/60 border border-red-200/70 dark:border-red-900/70',
      high:
        'text-orange-700 bg-orange-100 dark:text-orange-200 dark:bg-orange-950/60 border border-orange-200/70 dark:border-orange-900/70',
      medium:
        'text-yellow-700 bg-yellow-100 dark:text-yellow-200 dark:bg-yellow-950/60 border border-yellow-200/70 dark:border-yellow-900/70',
      low:
        'text-blue-700 bg-blue-100 dark:text-blue-200 dark:bg-blue-950/60 border border-blue-200/70 dark:border-blue-900/70',
      info:
        'text-gray-700 bg-gray-100 dark:text-slate-200 dark:bg-slate-900/60 border border-gray-200/70 dark:border-slate-800/70',
    };
    return (
      colors[severity] ||
      'text-gray-700 bg-gray-100 dark:text-slate-200 dark:bg-slate-900/60 border border-gray-200/70 dark:border-slate-800/70'
    );
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <h2 className="text-xl font-semibold">Detect Mistakes in Sheet</h2>
          <p className="text-sm text-gray-600 mt-1">
            Analyze your Google Sheet for errors, inconsistencies, and data quality issues.
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
              label="Sheet Title"
              placeholder="Sheet1"
              value={sheetTitle}
              onChange={(e) => setSheetTitle(e.target.value)}
            />
            <Button onClick={handleDetect} disabled={loading} className="w-full">
              {loading ? 'Analyzing...' : 'Detect Issues'}
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

      {issues.length > 0 && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold">
              Found {issues.length} Issue{issues.length !== 1 ? 's' : ''}
            </h3>
          </CardHeader>
          <CardBody>
            <div className="space-y-4">
              {issues.map((issue) => (
                <div
                  key={issue.id}
                  className="border border-gray-200 rounded-lg p-4 dark:border-slate-700"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${getSeverityColor(
                            issue.severity
                          )}`}
                        >
                          {issue.severity.toUpperCase()}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-slate-400">
                          {issue.category}
                        </span>
                      </div>
                      <h4 className="font-semibold text-gray-900 dark:text-slate-50 mb-1">
                        {issue.title}
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-slate-300 mb-2">
                        {issue.description}
                      </p>
                      {issue.suggestedFix && (
                        <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded dark:bg-blue-950/40 dark:border-blue-900/60">
                          <p className="text-sm font-medium text-blue-900 dark:text-blue-200 mb-1">
                            Suggested Fix:
                          </p>
                          <p className="text-sm text-blue-800 dark:text-blue-100">
                            {issue.suggestedFix}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
