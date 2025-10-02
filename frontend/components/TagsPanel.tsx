'use client';

import { useEffect, useState } from 'react';

export default function TagsPanel() {
  const [docId, setDocId] = useState('');
  const [documents, setDocuments] = useState<any[]>([]);
  const [q, setQ] = useState('');
  const [tags, setTags] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (docId) params.set('document_id', docId);
      if (q) params.set('q', q);
      const r = await fetch(`${API}/tags?${params.toString()}`);
      if (!r.ok) return;
      const data = await r.json();
      setTags(Array.isArray(data.tags) ? data.tags : []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/documents`);
        if (!r.ok) return;
        const data = await r.json();
        setDocuments(Array.isArray(data.documents) ? data.documents : []);
      } catch {}
    })();
  }, []);

  const extractTags = async () => {
    if (!docId) return;
    try {
      const res = await fetch(`${API}/extract/tags`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ document_id: docId }) });
      if (res.ok) {
        load();
      } else {
        alert('Extract tags failed');
      }
    } catch {
      alert('Extract tags error');
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Application Tags</h2>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-2 mb-3">
        <select className="border rounded px-2 py-1" value={docId} onChange={e=>setDocId(e.target.value)}>
          <option value="">Select document…</option>
          {documents.map((d:any)=> (<option key={d.id} value={d.id}>{d.type} — {d.title || d.path}</option>))}
        </select>
        <input className="border rounded px-2 py-1" placeholder="search tag" value={q} onChange={e=>setQ(e.target.value)} />
        <button onClick={load} className="bg-blue-600 text-white rounded px-3">Filter</button>
        <button onClick={extractTags} disabled={!docId} className="bg-green-600 text-white rounded px-3">Extract Tags</button>
      </div>
      {loading ? <div>Loading…</div> : (
        <div className="max-h-80 overflow-auto border rounded">
          <table className="min-w-full text-left text-xs">
            <thead><tr className="bg-gray-50"><th className="px-2 py-1">tag</th><th className="px-2 py-1">score</th><th className="px-2 py-1">document</th><th className="px-2 py-1">source</th></tr></thead>
            <tbody>
              {tags.map((t,i)=> (
                <tr key={i} className="border-t"><td className="px-2 py-1">{t.tag}</td><td className="px-2 py-1">{t.score ?? ''}</td><td className="px-2 py-1">{t.document_id}</td><td className="px-2 py-1">{t.source_ptr || ''}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
