'use client';

import { useEffect, useState } from 'react';

export default function APIsPanel() {
  const [tag, setTag] = useState('');
  const [method, setMethod] = useState('');
  const [pathLike, setPathLike] = useState('');
  const [apis, setApis] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (tag) params.set('tag', tag);
      if (method) params.set('method', method);
      if (pathLike) params.set('path_like', pathLike);
      const r = await fetch(`${API}/apis?${params.toString()}`);
      if (!r.ok) return;
      const data = await r.json();
      setApis(Array.isArray(data.apis) ? data.apis : []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">APIs</h2>
      <div className="grid grid-cols-1 md:grid-cols-5 gap-2 mb-3">
        <input className="border rounded px-2 py-1" placeholder="tag" value={tag} onChange={e=>setTag(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="method" value={method} onChange={e=>setMethod(e.target.value)} />
        <input className="border rounded px-2 py-1" placeholder="path contains" value={pathLike} onChange={e=>setPathLike(e.target.value)} />
        <button onClick={load} className="bg-blue-600 text-white rounded px-3">Filter</button>
      </div>
      {loading ? <div>Loading…</div> : (
        <div className="max-h-80 overflow-auto border rounded">
          <table className="min-w-full text-left text-xs">
            <thead><tr className="bg-gray-50"><th className="px-2 py-1">method</th><th className="px-2 py-1">path</th><th className="px-2 py-1">summary</th><th className="px-2 py-1">tags</th></tr></thead>
            <tbody>
              {apis.map((a,i)=> (
                <tr key={i} className="border-t"><td className="px-2 py-1">{a.method}</td><td className="px-2 py-1">{a.path}</td><td className="px-2 py-1">{a.summary}</td><td className="px-2 py-1">{(a.tags||[]).join(', ')}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

