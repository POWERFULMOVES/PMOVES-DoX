'use client';

import { useEffect, useState } from 'react';

import { useToast } from '@/components/Toast';
import { getApiBase } from '@/lib/config';

export default function LogsPanel() {
  const [level, setLevel] = useState('');
  const [code, setCode] = useState('');
  const [q, setQ] = useState('');
  const [tsFrom, setTsFrom] = useState('');
  const [tsTo, setTsTo] = useState('');
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [building, setBuilding] = useState(false);
  const API = getApiBase();
  const { push } = useToast();

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (level) params.set('level', level);
      if (code) params.set('code', code);
      if (q) params.set('q', q);
      if (tsFrom) params.set('ts_from', tsFrom);
      if (tsTo) params.set('ts_to', tsTo);
      const r = await fetch(`${API}/logs?${params.toString()}`);
      if (!r.ok) return;
      const data = await r.json();
      setLogs(Array.isArray(data.logs) ? data.logs : []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

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

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Logs</h2>
      <div className="grid grid-cols-1 md:grid-cols-6 gap-2 mb-3">
        <input className="border rounded px-2 py-1" placeholder="level" value={level} onChange={e=>setLevel(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="code" value={code} onChange={e=>setCode(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="search text" value={q} onChange={e=>setQ(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="ts from (YYYY-MM-DD)" value={tsFrom} onChange={e=>setTsFrom(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="ts to (YYYY-MM-DD)" value={tsTo} onChange={e=>setTsTo(e.target.value)} />
        <button onClick={load} className="bg-blue-600 text-white rounded px-3">Filter</button>
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
          window.open(`${API}/logs/export?${params.toString()}`, '_blank');
        }} className="bg-gray-700 text-white rounded px-3 py-1">Export CSV</button>
      </div>
      {loading ? <div>Loading…</div> : (
        <div className="max-h-80 overflow-auto border rounded">
          <table className="min-w-full text-left text-xs">
            <thead><tr className="bg-gray-50"><th className="px-2 py-1">ts</th><th className="px-2 py-1">level</th><th className="px-2 py-1">code</th><th className="px-2 py-1">component</th><th className="px-2 py-1">message</th></tr></thead>
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
