"use client";

import React, { useState } from 'react';
import { ArrowLeft, FileText, BarChart3, TrendingUp, DollarSign } from 'lucide-react';
import Link from 'next/link';

export default function FinancialAnalysisCookbookPage() {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [financialData, setFinancialData] = useState<any>(null);

  const handleAnalyze = async (documentId: string) => {
    setSelectedDoc(documentId);
    try {
      const response = await fetch(`/api/analysis/financials?document_id=${documentId}`);
      if (response.ok) {
        const data = await response.json();
        setFinancialData(data);
      }
    } catch (error) {
      console.error('Financial analysis failed:', error);
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
          <div className="p-3 bg-green-100 rounded-xl shadow-sm">
            <BarChart3 className="w-8 h-8 text-green-600" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">
              Financial Statement Analysis
            </h1>
            <p className="text-gray-400 mt-1 text-lg">
              Extract and analyze financial data from PDF reports
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-6">

            {/* How it Works */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5 text-green-400" />
                How it Works
              </h2>
              <ol className="space-y-3">
                {[
                  'Upload a financial PDF report (10-K, 10-Q, earnings, etc.)',
                  'System detects tables and extracts financial statements',
                  'View extracted Balance Sheet, Income Statement, and Cash Flow',
                  'Ask questions about financial health, ratios, and trends'
                ].map((step, i) => (
                  <li key={i} className="flex items-start gap-3 text-gray-300">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-500/30 text-green-300 flex items-center justify-center text-sm font-medium">
                      {i + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>

            {/* Sample Documents */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">Sample Documents</h3>
              <div className="space-y-2">
                {[
                  { id: '1', name: 'annual_report_2024.pdf', type: '10-K Annual Report' },
                  { id: '2', name: 'quarterly_earnings_q3.pdf', type: '10-Q Quarterly Report' },
                  { id: '3', name: 'balance_sheet_oct.pdf', type: 'Balance Sheet' },
                ].map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between p-3 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="w-4 h-4 text-gray-400" />
                      <div>
                        <p className="text-white font-medium">{doc.name}</p>
                        <p className="text-xs text-gray-400">{doc.type}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleAnalyze(doc.id)}
                      disabled={selectedDoc === doc.id}
                      className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors"
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
                <TrendingUp className="w-5 h-5" />
                Extracted Metrics
              </h3>
              {financialData ? (
                <div className="space-y-4">
                  <div className="p-3 bg-green-500/20 border border-green-500/30 rounded-lg">
                    <p className="text-xs text-gray-400">Revenue</p>
                    <p className="text-xl font-bold text-white">$124.5M</p>
                    <p className="text-xs text-green-400">↑ 12.3% YoY</p>
                  </div>
                  <div className="p-3 bg-blue-500/20 border border-blue-500/30 rounded-lg">
                    <p className="text-xs text-gray-400">Net Income</p>
                    <p className="text-xl font-bold text-white">$18.2M</p>
                    <p className="text-xs text-green-400">↑ 8.7% YoY</p>
                  </div>
                  <div className="p-3 bg-purple-500/20 border border-purple-500/30 rounded-lg">
                    <p className="text-xs text-gray-400">Total Assets</p>
                    <p className="text-xl font-bold text-white">$456.8M</p>
                  </div>
                </div>
              ) : (
                <p className="text-gray-400 text-sm">
                  Select a document to extract financial metrics
                </p>
              )}
            </div>

            {/* API Reference */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">API Reference</h3>
              <div className="space-y-2 text-sm">
                <div className="p-3 bg-black/30 rounded-lg">
                  <p className="text-gray-400 mb-1">GET</p>
                  <code className="text-green-400 text-xs">
                    /api/analysis/financials?document_id={'{id}'}
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
