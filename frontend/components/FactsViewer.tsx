'use client';

import { useEffect, useRef, useState } from 'react';
import axios from 'axios';

export default function FactsViewer() {
  const [facts, setFacts] = useState<any[]>([]);
  const [financials, setFinancials] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadFacts();
    // Auto-refresh facts periodically to catch background results
    timerRef.current = setInterval(() => loadFacts(true), 3000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const loadFacts = async (silent = false) => {
    try {
      const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
      const [factsResponse, financialsResponse] = await Promise.all([
        axios.get(`${API}/facts`),
        axios.get(`${API}/analysis/financials`),
      ]);
      setFacts(factsResponse.data.facts);
      setFinancials(financialsResponse.data.statements || []);
    } catch (error) {
      console.error('Failed to load facts:', error);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  if (loading) return <div className="text-center py-8">Loading facts...</div>;

  return (
    <div className="bg-white p-6 rounded-lg shadow space-y-8">
      <div>
        <h2 className="text-2xl font-bold mb-4">Extracted Facts ({facts.length})</h2>

        {facts.length === 0 ? (
          <p className="text-gray-500">No facts yet. Upload some documents to get started.</p>
        ) : (
          <div className="space-y-4">
            {facts.map((fact, idx) => (
              <div key={idx} className="border rounded p-4">
                <div className="flex justify-between mb-2">
                  <span className="font-medium">
                    {fact.entity || 'General'}
                  </span>
                  <span className="text-sm text-gray-500">
                    {fact.report_week}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  {Object.entries(fact.metrics || {}).map(([key, value]: [string, any]) => (
                    <div key={key} className="bg-gray-50 p-2 rounded">
                      <p className="text-xs text-gray-600 uppercase">{key}</p>
                      <p className="font-semibold">{typeof value === 'number' ? value.toFixed(2) : String(value)}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold">Financial Statements ({financials.length})</h2>
          <p className="text-sm text-gray-500">Auto-detected from PDF tables</p>
        </div>

        {financials.length === 0 ? (
          <p className="text-gray-500">No financial statements detected yet.</p>
        ) : (
          <div className="space-y-4">
            {financials.map((statement) => {
              const summaryEntries = Object.entries(statement.summary || {}).filter(([, value]) => value !== null && value !== undefined);
              const rows = (statement.rows || []).slice(0, 4);
              return (
                <div key={statement.evidence_id} className="border rounded p-4">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 mb-3">
                    <div>
                      <p className="text-lg font-semibold capitalize">{statement.statement_type.replace(/_/g, ' ')}</p>
                      {statement.locator && (
                        <p className="text-xs text-gray-500">Source: {statement.locator}</p>
                      )}
                    </div>
                    <div className="md:w-48">
                      <p className="text-xs text-gray-500 uppercase tracking-wide">Confidence</p>
                      <div className="h-2 bg-gray-200 rounded">
                        <div
                          className="h-2 bg-emerald-500 rounded"
                          style={{ width: `${Math.min(100, Math.round((statement.confidence || 0) * 100))}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-600 mt-1">{Math.round((statement.confidence || 0) * 100)}%</p>
                    </div>
                  </div>

                  {summaryEntries.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 mb-4">
                      {summaryEntries.map(([key, value]) => (
                        <div key={key} className="bg-gray-50 p-3 rounded">
                          <p className="text-xs text-gray-500 uppercase">{key.replace(/_/g, ' ')}</p>
                          <p className="font-semibold">{typeof value === 'number' ? value.toLocaleString() : String(value)}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {rows.length > 0 && statement.columns?.length ? (
                    <div className="overflow-x-auto">
                      <table className="min-w-full text-sm">
                        <thead className="bg-gray-100">
                          <tr>
                            {statement.columns.map((col: string) => (
                              <th key={col} className="px-3 py-2 text-left font-medium text-gray-600">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {rows.map((row: Record<string, any>, rowIdx: number) => (
                            <tr key={rowIdx} className="odd:bg-white even:bg-gray-50">
                              {statement.columns.map((col: string) => (
                                <td key={col} className="px-3 py-2 whitespace-nowrap text-gray-700">
                                  {row[col] ?? ''}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
