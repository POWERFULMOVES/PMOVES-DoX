"use client";

import React, { useState } from 'react';
import { ArrowLeft, Tag, Upload, Sparkles, Filter } from 'lucide-react';
import Link from 'next/link';

export default function AutoTaggingCookbookPage() {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [generatedTags, setGeneratedTags] = useState<string[]>([]);

  const mockDocuments = [
    { id: '1', name: 'financial_report_q3.pdf', type: 'PDF' },
    { id: '2', name: 'server_logs_error.log', type: 'Log' },
    { id: '3', name: 'meeting_notes.txt', type: 'Text' },
  ];

  const handleAutoTag = async (documentId: string) => {
    setSelectedDoc(documentId);
    // Call the backend autotag endpoint
    try {
      const response = await fetch(`/api/analysis/autotag/${documentId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        const data = await response.json();
        setGeneratedTags(data.tags || ['finance', 'quarterly', '2024', 'balance-sheet']);
      }
    } catch (error) {
      console.error('Auto-tag failed:', error);
      // Mock tags for demo
      setGeneratedTags(['document', 'processed', 'tagged']);
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
          <div className="p-3 bg-purple-100 rounded-xl shadow-sm">
            <Tag className="w-8 h-8 text-purple-600" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">
              Auto-Tagging & Classification
            </h1>
            <p className="text-gray-400 mt-1 text-lg">
              Automatically tag and classify documents using LLMs
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Instructions & Document List */}
          <div className="lg:col-span-2 space-y-6">

            {/* How it Works */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-yellow-400" />
                How it Works
              </h2>
              <ol className="space-y-3">
                {[
                  'Upload any document to the workspace',
                  'Select the document and click "Auto-Tag"',
                  'The AI analyzes content and generates relevant tags',
                  'Tags are automatically saved to the document metadata',
                  'Filter and search documents by generated tags'
                ].map((step, i) => (
                  <li key={i} className="flex items-start gap-3 text-gray-300">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-500/30 text-purple-300 flex items-center justify-center text-sm font-medium">
                      {i + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>

            {/* Document List */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">Your Documents</h3>
              <div className="space-y-2">
                {mockDocuments.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between p-3 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <Upload className="w-4 h-4 text-gray-400" />
                      <div>
                        <p className="text-white font-medium">{doc.name}</p>
                        <p className="text-xs text-gray-400">{doc.type}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleAutoTag(doc.id)}
                      disabled={selectedDoc === doc.id}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      {selectedDoc === doc.id ? 'Processing...' : 'Auto-Tag'}
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
                <Filter className="w-5 h-5" />
                Generated Tags
              </h3>
              {generatedTags.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {generatedTags.map((tag) => (
                    <span
                      key={tag}
                      className="px-3 py-1 bg-purple-500/30 text-purple-200 border border-purple-400/30 rounded-full text-sm"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400 text-sm">
                  Select a document and click Auto-Tag to generate tags
                </p>
              )}
            </div>

            {/* API Reference */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">API Reference</h3>
              <div className="space-y-2 text-sm">
                <div className="p-3 bg-black/30 rounded-lg">
                  <p className="text-gray-400 mb-1">POST</p>
                  <code className="text-green-400 text-xs">
                    /api/analysis/autotag/{'{document_id}'}
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
