"use client";

import React, { useState, useEffect } from 'react';
import { ArrowLeft, FileText, BarChart3, TrendingUp, DollarSign, RefreshCw, ChevronDown } from 'lucide-react';
import Link from 'next/link';

interface FinancialStatement {
  evidence_id: string;
  artifact_id: string;
  locator: string;
  statement_type: string;
  confidence: number;
  summary: Record<string, number | null>;
  columns: string[];
  rows: any[][];
  header_info: any;
}

interface ArtifactItem {
  id: string;
  filename: string;
  filetype: string;
  status?: string;
}

const STATEMENT_LABELS: Record<string, string> = {
  balance_sheet: 'Balance Sheet',
  income_statement: 'Income Statement',
  cash_flow: 'Cash Flow Statement',
};

const STATEMENT_COLORS: Record<string, { bg: string; border: string; badge: string }> = {
  balance_sheet: { bg: 'bg-purple-500/20', border: 'border-purple-500/30', badge: 'bg-purple-600' },
  income_statement: { bg: 'bg-green-500/20', border: 'border-green-500/30', badge: 'bg-green-600' },
  cash_flow: { bg: 'bg-blue-500/20', border: 'border-blue-500/30', badge: 'bg-blue-600' },
};

const VALID_TYPES = ['balance_sheet', 'income_statement', 'cash_flow'];

function formatCurrency(value: number | null | undefined): string {
  if (value == null) return '—';
  const abs = Math.abs(value);
  let formatted: string;
  if (abs >= 1_000_000_000) formatted = `$${(value / 1_000_000_000).toFixed(1)}B`;
  else if (abs >= 1_000_000) formatted = `$${(value / 1_000_000).toFixed(1)}M`;
  else if (abs >= 1_000) formatted = `$${(value / 1_000).toFixed(1)}K`;
  else formatted = `$${value.toFixed(2)}`;
  return formatted;
}

function humanizeKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export default function FinancialAnalysisCookbookPage() {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [financialData, setFinancialData] = useState<{ statements: FinancialStatement[] } | null>(null);
  const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingArtifacts, setLoadingArtifacts] = useState(true);
  const [reclassifying, setReclassifying] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('/api/artifacts');
        if (res.ok) {
          const data = await res.json();
          const list = Array.isArray(data) ? data : data.artifacts || [];
          setArtifacts(list);
        }
      } catch (e) {
        console.error('Failed to load artifacts:', e);
      } finally {
        setLoadingArtifacts(false);
      }
    })();
  }, []);

  const handleAnalyze = async (artifactId: string) => {
    setSelectedDoc(artifactId);
    setLoading(true);
    try {
      const response = await fetch(`/api/analysis/financials?artifact_id=${artifactId}`);
      if (response.ok) {
        const data = await response.json();
        setFinancialData(data);
      }
    } catch (error) {
      console.error('Financial analysis failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeAll = async () => {
    setSelectedDoc('all');
    setLoading(true);
    try {
      const response = await fetch('/api/analysis/financials');
      if (response.ok) {
        const data = await response.json();
        setFinancialData(data);
      }
    } catch (error) {
      console.error('Financial analysis failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleReclassify = async (evidenceId: string, newType: string) => {
    setReclassifying(evidenceId);
    try {
      const res = await fetch(`/api/analysis/financials/${evidenceId}/reclassify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ statement_type: newType }),
      });
      if (res.ok) {
        // Refresh data
        if (selectedDoc) {
          const url = selectedDoc === 'all'
            ? '/api/analysis/financials'
            : `/api/analysis/financials?artifact_id=${selectedDoc}`;
          const refresh = await fetch(url);
          if (refresh.ok) setFinancialData(await refresh.json());
        }
      }
    } catch (error) {
      console.error('Reclassification failed:', error);
    } finally {
      setReclassifying(null);
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
                  'Reclassify misidentified tables or ask questions about financial health'
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

            {/* Documents */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-white">Documents</h3>
                <button
                  onClick={handleAnalyzeAll}
                  disabled={loading}
                  className="px-3 py-1.5 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white text-xs font-medium rounded-lg transition-colors"
                >
                  Analyze All
                </button>
              </div>
              <div className="space-y-2">
                {loadingArtifacts ? (
                  <p className="text-gray-400 text-sm">Loading documents...</p>
                ) : artifacts.length === 0 ? (
                  <div className="text-center py-6">
                    <FileText className="w-10 h-10 text-gray-500 mx-auto mb-2" />
                    <p className="text-gray-400 text-sm">No documents uploaded yet.</p>
                    <p className="text-gray-500 text-xs mt-1">
                      Upload a financial PDF via the main upload page to get started.
                    </p>
                  </div>
                ) : (
                  artifacts.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center justify-between p-3 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="text-white font-medium truncate">{doc.filename}</p>
                          <p className="text-xs text-gray-400">{doc.filetype}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleAnalyze(doc.id)}
                        disabled={loading && selectedDoc === doc.id}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white text-sm font-medium rounded-lg transition-colors flex-shrink-0"
                      >
                        {loading && selectedDoc === doc.id ? 'Analyzing...' : 'Analyze'}
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Detected Statements */}
            {financialData && financialData.statements.length > 0 && (
              <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-green-400" />
                  Detected Statements ({financialData.statements.length})
                </h3>
                <div className="space-y-4">
                  {financialData.statements.map((stmt) => {
                    const colors = STATEMENT_COLORS[stmt.statement_type] || { bg: 'bg-gray-500/20', border: 'border-gray-500/30', badge: 'bg-gray-600' };
                    return (
                      <div key={stmt.evidence_id} className={`p-4 ${colors.bg} border ${colors.border} rounded-lg`}>
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <span className={`px-2 py-0.5 ${colors.badge} text-white text-xs font-medium rounded`}>
                              {STATEMENT_LABELS[stmt.statement_type] || stmt.statement_type}
                            </span>
                            <span className="text-xs text-gray-400">
                              {(stmt.confidence * 100).toFixed(0)}% confidence
                            </span>
                          </div>
                          {/* Reclassify dropdown */}
                          <div className="relative">
                            <select
                              value={stmt.statement_type}
                              onChange={(e) => handleReclassify(stmt.evidence_id, e.target.value)}
                              disabled={reclassifying === stmt.evidence_id}
                              className="appearance-none bg-white/10 border border-white/20 text-white text-xs rounded px-2 py-1 pr-6 cursor-pointer disabled:opacity-50"
                              aria-label={`Reclassify statement ${stmt.evidence_id}`}
                            >
                              {VALID_TYPES.map(t => (
                                <option key={t} value={t} className="bg-gray-800">
                                  {STATEMENT_LABELS[t]}
                                </option>
                              ))}
                            </select>
                            <ChevronDown className="w-3 h-3 text-gray-400 absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                          </div>
                        </div>
                        {stmt.locator && (
                          <p className="text-xs text-gray-400 mb-2">{stmt.locator}</p>
                        )}
                        {/* Summary metrics */}
                        <div className="grid grid-cols-2 gap-2">
                          {Object.entries(stmt.summary || {}).map(([key, value]) => (
                            <div key={key} className="bg-black/20 rounded p-2">
                              <p className="text-xs text-gray-400">{humanizeKey(key)}</p>
                              <p className="text-sm font-bold text-white">{formatCurrency(value)}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {financialData && financialData.statements.length === 0 && (
              <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6 text-center">
                <p className="text-gray-400">No financial statements detected in this document.</p>
                <p className="text-xs text-gray-500 mt-1">
                  The document may not contain recognizable financial tables, or tables may be classified as &quot;unknown&quot;.
                </p>
              </div>
            )}
          </div>

          {/* Right Column: Quick Metrics + API */}
          <div className="space-y-6">
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                Extracted Metrics
              </h3>
              {loading ? (
                <div className="flex items-center gap-2 text-gray-400 text-sm">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Analyzing...
                </div>
              ) : financialData && financialData.statements.length > 0 ? (
                <div className="space-y-4">
                  {financialData.statements.map((stmt) => {
                    const colors = STATEMENT_COLORS[stmt.statement_type] || { bg: 'bg-gray-500/20', border: 'border-gray-500/30', badge: 'bg-gray-600' };
                    // Pick the most interesting metric to show
                    const entries = Object.entries(stmt.summary || {}).filter(([, v]) => v != null);
                    if (entries.length === 0) return null;
                    const [topKey, topValue] = entries[0];
                    return (
                      <div key={stmt.evidence_id} className={`p-3 ${colors.bg} border ${colors.border} rounded-lg`}>
                        <p className="text-xs text-gray-400">
                          {STATEMENT_LABELS[stmt.statement_type] || stmt.statement_type} &mdash; {humanizeKey(topKey)}
                        </p>
                        <p className="text-xl font-bold text-white">{formatCurrency(topValue)}</p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {entries.length - 1} more metric{entries.length - 1 !== 1 ? 's' : ''}
                        </p>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-gray-400 text-sm">
                  {financialData ? 'No metrics found' : 'Select a document to extract financial metrics'}
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
                    /api/analysis/financials?artifact_id={'{id}'}
                  </code>
                </div>
                <div className="p-3 bg-black/30 rounded-lg">
                  <p className="text-gray-400 mb-1">POST</p>
                  <code className="text-green-400 text-xs">
                    /api/analysis/financials/{'{evidence_id}'}/reclassify
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
