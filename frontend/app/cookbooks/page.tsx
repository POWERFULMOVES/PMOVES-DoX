"use client";

import React from 'react';
import { Book, CheckCircle, Circle, Clock, ArrowRight } from 'lucide-react';
import Link from 'next/link';

interface Cookbook {
  id: string;
  title: string;
  description: string;
  status: 'ready' | 'in-progress' | 'planned';
  steps: string[];
}

const COOKBOOKS: Cookbook[] = [
  {
    id: 'financial-analysis',
    title: 'Financial Statement Analysis',
    description: 'Extract and analyze financial data from PDF reports.',
    status: 'ready',
    steps: [
      'Upload a financial PDF report',
      'System detects tables and extracts financial statements',
      'View extracted Balance Sheet and Income Statement',
      'Ask questions about the financial health'
    ]
  },
  {
    id: 'log-analysis',
    title: 'Log Analysis & Debugging',
    description: 'Ingest server logs and debug issues using AI.',
    status: 'ready',
    steps: [
      'Upload a server log file (.log or .txt)',
      'System parses log entries and timestamps',
      'Filter logs by error level or component',
      'Ask AI to identify root causes of errors'
    ]
  },
  {
    id: 'api-documentation',
    title: 'API Documentation Generator',
    description: 'Generate OpenAPI specs from code or raw text.',
    status: 'planned',
    steps: [
      'Upload code files or API descriptions',
      'System identifies endpoints and parameters',
      'Generate structured OpenAPI documentation',
      'Export as YAML/JSON'
    ]
  },
  {
    id: 'auto-tagging',
    title: 'Auto-Tagging & Classification',
    description: 'Automatically tag and classify documents using LLMs.',
    status: 'in-progress',
    steps: [
      'Upload any document',
      'Click "Auto-Tag"',
      'System generates relevant tags based on content',
      'Filter documents by generated tags'
    ]
  }
];

export default function CookbooksPage() {
  return (
    <div className="max-w-5xl mx-auto p-8 space-y-8">
      <div className="flex items-center gap-4 mb-8">
        <div className="p-3 bg-blue-100 rounded-lg">
          <Book className="w-8 h-8 text-blue-600" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Cookbooks</h1>
          <p className="text-gray-500 mt-1">Recipes for getting the most out of your documents.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {COOKBOOKS.map((cookbook) => (
          <div key={cookbook.id} className="bg-white border rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-xl font-bold text-gray-800">{cookbook.title}</h3>
              <StatusBadge status={cookbook.status} />
            </div>
            
            <p className="text-gray-600 mb-6 flex-grow">{cookbook.description}</p>
            
            <div className="space-y-3 mb-6 bg-gray-50 p-4 rounded-lg">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Workflow</p>
              {cookbook.steps.map((step, idx) => (
                <div key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-white border flex items-center justify-center text-xs text-gray-500 font-medium">
                    {idx + 1}
                  </span>
                  <span>{step}</span>
                </div>
              ))}
            </div>

            <div className="mt-auto pt-4 border-t flex justify-end">
              <Link 
                href="/"
                className="flex items-center gap-2 text-blue-600 font-medium hover:text-blue-800 transition-colors"
              >
                Try it out <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: Cookbook['status'] }) {
  const styles = {
    ready: 'bg-green-100 text-green-700 border-green-200',
    'in-progress': 'bg-yellow-100 text-yellow-700 border-yellow-200',
    planned: 'bg-gray-100 text-gray-600 border-gray-200'
  };

  const icons = {
    ready: <CheckCircle className="w-3 h-3" />,
    'in-progress': <Clock className="w-3 h-3" />,
    planned: <Circle className="w-3 h-3" />
  };

  return (
    <span className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${styles[status]}`}>
      {icons[status]}
      <span className="capitalize">{status.replace('-', ' ')}</span>
    </span>
  );
}
