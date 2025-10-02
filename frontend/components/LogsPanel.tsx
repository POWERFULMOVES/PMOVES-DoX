'use client';

import { useEffect, useState } from 'react';

export default function LogsPanel() {
  const [level, setLevel] = useState('');
  const [code, setCode] = useState('');
  const [q, setQ] = useState('');
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (level) params.set('level', level);
      if (code) params.set('code', code);
      if (q) params.set('q', q);
      const r = await fetch(`${API}/logs?${params.toString()}`);
      if (!r.ok) return;
      const data = await r.json();
      setLogs(Array.isArray(data.logs) ? data.logs : []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Logs</h2>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-2 mb-3">
        <input className="border rounded px-2 py-1" placeholder="level" value={level} onChange={e=>setLevel(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="code" value={code} onChange={e=>setCode(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="search text" value={q} onChange={e=>setQ(e.target.value)} />
        <button onClick={load} className="bg-blue-600 text-white rounded px-3">Filter</button>
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

