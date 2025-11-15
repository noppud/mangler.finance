'use client';

import { useState } from 'react';
import { DetectIssues } from '@/components/features/DetectIssues';
import { ModifySheet } from '@/components/features/ModifySheet';
import { CreateSheet } from '@/components/features/CreateSheet';

type Tab = 'detect' | 'modify' | 'create';

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>('detect');

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 bg-white/80 backdrop-blur border-b border-gray-200 dark:bg-slate-900/80 dark:border-slate-800">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-2xl bg-blue-600 text-white flex items-center justify-center text-sm font-semibold shadow-sm dark:bg-blue-500">
              SM
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-900 dark:text-slate-50 tracking-tight">
                Sheet Mangler
              </h1>
              <p className="text-sm text-gray-600 dark:text-slate-400">
                AI-powered Google Sheets assistant
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-10">
        {/* Tabs */}
        <div className="mb-8 flex items-center justify-between gap-4">
          <div className="inline-flex rounded-full bg-white/80 border border-gray-200 p-1 shadow-sm dark:bg-slate-900/80 dark:border-slate-700">
            <button
              onClick={() => setActiveTab('detect')}
              className={`px-5 py-2 text-sm font-medium rounded-full transition-colors ${
                activeTab === 'detect'
                  ? 'bg-blue-600 text-white shadow dark:bg-blue-500'
                  : 'text-gray-600 hover:text-gray-900 dark:text-slate-300 dark:hover:text-slate-50'
              }`}
            >
              Detect Mistakes
            </button>
            <button
              onClick={() => setActiveTab('modify')}
              className={`px-5 py-2 text-sm font-medium rounded-full transition-colors ${
                activeTab === 'modify'
                  ? 'bg-blue-600 text-white shadow dark:bg-blue-500'
                  : 'text-gray-600 hover:text-gray-900 dark:text-slate-300 dark:hover:text-slate-50'
              }`}
            >
              Modify Sheet
            </button>
            <button
              onClick={() => setActiveTab('create')}
              className={`px-5 py-2 text-sm font-medium rounded-full transition-colors ${
                activeTab === 'create'
                  ? 'bg-blue-600 text-white shadow dark:bg-blue-500'
                  : 'text-gray-600 hover:text-gray-900 dark:text-slate-300 dark:hover:text-slate-50'
              }`}
            >
              Create Sheet
            </button>
          </div>
          <p className="hidden md:block text-xs text-gray-500 dark:text-slate-400">
            Start by detecting issues, then refine or create new sheets.
          </p>
        </div>

        {/* Tab Content */}
        <div className="mb-8">
          {activeTab === 'detect' && <DetectIssues />}
          {activeTab === 'modify' && <ModifySheet />}
          {activeTab === 'create' && <CreateSheet />}
        </div>
      </main>

      <footer className="border-t border-gray-200 mt-16 bg-white/70 backdrop-blur dark:border-slate-800 dark:bg-slate-900/70">
        <div className="max-w-6xl mx-auto px-4 py-6 text-center text-sm text-gray-600 dark:text-slate-400">
          <p>
            Built with Next.js, OpenRouter, and Google Sheets API
          </p>
        </div>
      </footer>
    </div>
  );
}
