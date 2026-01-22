'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { useToast } from '@/components/Toast';
import { getApiBase } from '@/lib/config';

type LogFilters = {
  level?: string;
  code?: string;
  q?: string;
  tsFrom?: string;
  tsTo?: string;
  documentId?: string;
};

export default function LogsPanel() {
  const [level, setLevel] = useState('');
  const [code, setCode] = useState('');
  const [q, setQ] = useState('');
  const [tsFrom, setTsFrom] = useState('');
  const [tsTo, setTsTo] = useState('');
  const [documentId, setDocumentId] = useState('');
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [building, setBuilding] = useState(false);
  const API = getApiBase();
  const { push } = useToast();

  const filtersRef = useRef<LogFilters>({ level, code, q, tsFrom, tsTo, documentId });

  useEffect(() => {
    filtersRef.current = { level, code, q, tsFrom, tsTo, documentId };
  }, [code, documentId, level, q, tsFrom, tsTo]);

  const fetchLogs = useCallback(async (filters: LogFilters) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.level) params.set('level', filters.level);
      if (filters.code) params.set('code', filters.code);
      if (filters.q) params.set('q', filters.q);
      if (filters.tsFrom) params.set('ts_from', filters.tsFrom);
      if (filters.tsTo) params.set('ts_to', filters.tsTo);
      if (filters.documentId) params.set('document_id', filters.documentId);
      const r = await fetch(`${API}/logs?${params.toString()}`);
      if (!r.ok) return;
      const data = await r.json();
      setLogs(Array.isArray(data.logs) ? data.logs : []);
    } finally {
      setLoading(false);
    }
  }, [API]);

  const load = useCallback(() => {
    fetchLogs({ level, code, q, tsFrom, tsTo, documentId });
  }, [code, documentId, fetchLogs, level, q, tsFrom, tsTo]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const initialLevel = params.get('level') || '';
    const initialCode = params.get('code') || '';
    const initialQuery = params.get('q') || '';
    const initialTsFrom = params.get('ts_from') || '';
    const initialTsTo = params.get('ts_to') || '';
    const initialDocumentId = params.get('document_id') || '';

    setLevel(initialLevel);
    setCode(initialCode);
    setQ(initialQuery);
    setTsFrom(initialTsFrom);
    setTsTo(initialTsTo);
    setDocumentId(initialDocumentId);
    fetchLogs({
      level: initialLevel,
      code: initialCode,
      q: initialQuery,
      tsFrom: initialTsFrom,
      tsTo: initialTsTo,
      documentId: initialDocumentId,
    });
  }, [fetchLogs]);

  // Handle deep links to logs (code/document_id pre-filters)
  useEffect(() => {
    function onDeeplink(ev: any) {
      const dl = ev?.detail || {};
      if (String(dl.panel || '').toLowerCase() !== 'logs') return;
      const nextCode = dl.code ? String(dl.code) : '';
      const nextDocumentId = dl.document_id ? String(dl.document_id) : '';

      setCode(nextCode);
      setDocumentId(nextDocumentId);
      const { level: currentLevel, q: currentQuery, tsFrom: currentTsFrom, tsTo: currentTsTo } = filtersRef.current;
      fetchLogs({
        level: currentLevel,
        code: nextCode,
        q: currentQuery,
        tsFrom: currentTsFrom,
        tsTo: currentTsTo,
        documentId: nextDocumentId,
      });
    }
    if (typeof window !== 'undefined') window.addEventListener('global-deeplink' as any, onDeeplink as any);
    return () => {
      if (typeof window !== 'undefined') window.removeEventListener('global-deeplink' as any, onDeeplink as any);
    };
  }, [fetchLogs]);

  const buildViz = async () => {
    setBuilding(true);
    try {
      const r = await fetch(`${API}/viz/datavzrd/logs`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
      if (!r.ok) throw new Error('viz failed');
      push('datavzrd logs dashboard generated (see dev server).', 'success');
    } catch {
      push('Failed to build logs viz', 'error');
    } finally {
      setBuilding(false);
    }
  };

  const resetFilters = () => {
    setLevel('');
    setCode('');
    setQ('');
    setTsFrom('');
    setTsTo('');
    setDocumentId('');
    fetchLogs({});
  };

  return (
    <div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 p-6 rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Logs</h2>
      <div className="grid grid-cols-1 md:grid-cols-7 gap-2 mb-3">
        <input className="border rounded px-2 py-1" placeholder="level" value={level} onChange={e => setLevel(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="code" value={code} onChange={e => setCode(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="search text" value={q} onChange={e => setQ(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="ts from (YYYY-MM-DD)" value={tsFrom} onChange={e => setTsFrom(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="ts to (YYYY-MM-DD)" value={tsTo} onChange={e => setTsTo(e.target.value)} />
        <input
          className="border rounded px-2 py-1"
          placeholder="document id"
          value={documentId}
          onChange={e => setDocumentId(e.target.value)}
        />
        <div className="flex gap-2">
          <button onClick={load} className="bg-blue-600 text-white rounded px-3">Filter</button>
          <button onClick={resetFilters} className="bg-gray-200 text-gray-800 rounded px-3">Reset</button>
        </div>
      </div>
      <div className="mb-3">
        <button onClick={buildViz} disabled={building} className="bg-green-600 text-white rounded px-3 py-1 mr-2">{building ? 'Building…' : 'Generate datavzrd logs dashboard'}</button>
        <button onClick={() => {
          const params = new URLSearchParams();
          if (level) params.set('level', level);
          if (code) params.set('code', code);
          if (q) params.set('q', q);
          if (tsFrom) params.set('ts_from', tsFrom);
          if (tsTo) params.set('ts_to', tsTo);
          if (documentId) params.set('document_id', documentId);
          window.open(`${API}/logs/export?${params.toString()}`, '_blank');
        }} className="bg-gray-700 text-white rounded px-3 py-1">Export CSV</button>
      </div>
      {documentId && (
        <div className="mb-3 text-sm flex flex-wrap items-center gap-2">
          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded">Filtered to document <code>{documentId}</code></span>
          <button
            onClick={() => {
              setDocumentId('');
              fetchLogs({ level, code, q, tsFrom, tsTo });
            }}
            className="text-blue-700 underline"
          >
            Clear document filter
          </button>
        </div>
      )}
      {loading ? <div>Loading…</div> : (
        <div className="max-h-80 overflow-auto border rounded">
          <table className="min-w-full text-left text-xs">
            <thead><tr className="bg-gray-50 dark:bg-gray-800"><th className="px-2 py-1">ts</th><th className="px-2 py-1">level</th><th className="px-2 py-1">code</th><th className="px-2 py-1">component</th><th className="px-2 py-1">message</th></tr></thead>
            <tbody>
              {logs.map((l,i)=> (
                <tr key={i} className="border-t"><td className="px-2 py-1">{l.ts}</td><td className="px-2 py-1">{l.level}</td><td className="px-2 py-1">{l.code}</td><td className="px-2 py-1">{l.component}</td><td className="px-2 py-1">{l.message}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
