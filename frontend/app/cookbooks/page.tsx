"use client";

import React from 'react';
import { Book } from 'lucide-react';
import { Cookbook, CookbookCard } from '@/components/CookbookCard';

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
    status: 'ready',
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
    <div className="min-h-screen bg-transparent p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header Section */}
        <div className="flex items-center gap-4 mb-8">
          <div className="p-3 bg-blue-100 rounded-xl shadow-sm">
            <Book className="w-8 h-8 text-blue-600" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">Cookbooks</h1>
            <p className="text-gray-400 mt-1 text-lg">Recipes for getting the most out of your documents.</p>
          </div>
        </div>

        {/* Grid Layout */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-8">
          {COOKBOOKS.map((cookbook) => (
            <CookbookCard key={cookbook.id} cookbook={cookbook} />
          ))}
        </div>

        {/* Empty State / Coming Soon (Optional filler) */}
        {COOKBOOKS.length === 0 && (
          <div className="text-center py-20">
            <p className="text-gray-500">No cookbooks available yet.</p>
          </div>
        )}
      </div>
    </div>
  );
}
