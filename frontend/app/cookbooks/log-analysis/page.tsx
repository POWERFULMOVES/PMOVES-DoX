"use client";

import React, { useState } from 'react';
import { ArrowLeft, Activity, Bug, AlertTriangle, Search } from 'lucide-react';
import Link from 'next/link';

export default function LogAnalysisCookbookPage() {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [logAnalysis, setLogAnalysis] = useState<any>(null);

  const handleAnalyze = async (documentId: string) => {
    setSelectedDoc(documentId);
    try {
      // For log analysis, we'd use the search API with log filters
      const response = await fetch(`/api/search?query=error&document_id=${documentId}`);
      if (response.ok) {
        const data = await response.json();
        setLogAnalysis(data);
      }
    } catch (error) {
      console.error('Log analysis failed:', error);
    }
  };

  return (
    <div className="min-h-screen bg-transparent p-8">
      <div className="max-w-6xl mx-auto space-y-8">

        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link
            href="/cookbooks"
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </Link>
          <div className="p-3 bg-blue-100 rounded-xl shadow-sm">
            <Activity className="w-8 h-8 text-blue-600" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">
              Log Analysis & Debugging
            </h1>
            <p className="text-gray-400 mt-1 text-lg">
              Ingest server logs and debug issues using AI
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-6">

            {/* How it Works */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Bug className="w-5 h-5 text-blue-400" />
                How it Works
              </h2>
              <ol className="space-y-3">
                {[
                  'Upload a server log file (.log, .txt, or .json)',
                  'System parses log entries and extracts timestamps',
                  'Filter logs by error level (ERROR, WARN, INFO, DEBUG)',
                  'Ask AI to identify root causes and suggest fixes'
                ].map((step, i) => (
                  <li key={i} className="flex items-start gap-3 text-gray-300">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-500/30 text-blue-300 flex items-center justify-center text-sm font-medium">
                      {i + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>

            {/* Sample Logs */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">Sample Log Files</h3>
              <div className="space-y-2">
                {[
                  { id: '1', name: 'application_error.log', type: 'Application Logs', errors: 47 },
                  { id: '2', name: 'nginx_access.log', type: 'Nginx Access', errors: 0 },
                  { id: '3', name: 'system_crash.log', type: 'System Crash', errors: 156 },
                ].map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between p-3 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <Activity className="w-4 h-4 text-gray-400" />
                      <div>
                        <p className="text-white font-medium">{doc.name}</p>
                        <p className="text-xs text-gray-400">{doc.type} • {doc.errors} errors</p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleAnalyze(doc.id)}
                      disabled={selectedDoc === doc.id}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      {selectedDoc === doc.id ? 'Analyzing...' : 'Analyze'}
                    </button>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* Right Column: Results */}
          <div className="space-y-6">
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                Issues Found
              </h3>
              {logAnalysis ? (
                <div className="space-y-3">
                  <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg">
                    <p className="text-sm font-medium text-red-300">NullPointerException</p>
                    <p className="text-xs text-gray-400">Line 42 • UserService.java</p>
                  </div>
                  <div className="p-3 bg-yellow-500/20 border border-yellow-500/30 rounded-lg">
                    <p className="text-sm font-medium text-yellow-300">Database Timeout</p>
                    <p className="text-xs text-gray-400">Connection pool exhausted</p>
                  </div>
                </div>
              ) : (
                <p className="text-gray-400 text-sm">
                  Select a log file to analyze errors
                </p>
              )}
            </div>

            {/* AI Analysis */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Search className="w-5 h-5" />
                AI Insights
              </h3>
              <div className="text-sm text-gray-300 space-y-2">
                <p>Ask questions about your logs:</p>
                <div className="space-y-1">
                  {[
                    'What caused the most errors?',
                    'Show me all errors from 2:00-3:00 PM',
                    'Which endpoints are failing?'
                  ].map((q, i) => (
                    <button
                      key={i}
                      className="w-full text-left p-2 bg-white/5 hover:bg-white/10 rounded text-xs text-blue-300"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* API Reference */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">API Reference</h3>
              <div className="space-y-2 text-sm">
                <div className="p-3 bg-black/30 rounded-lg">
                  <p className="text-gray-400 mb-1">GET</p>
                  <code className="text-green-400 text-xs">
                    /api/search?query={'{term}'}
                  </code>
                </div>
                <div className="p-3 bg-black/30 rounded-lg">
                  <p className="text-gray-400 mb-1">POST</p>
                  <code className="text-green-400 text-xs">
                    /api/analysis/ask
                  </code>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
