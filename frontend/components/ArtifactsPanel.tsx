'use client';

import { useEffect, useState } from 'react';

export default function ArtifactsPanel() {
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

  const load = async () => {
    const r = await fetch(`${API}/artifacts`);
    if (!r.ok) return;
    const data = await r.json();
    setArtifacts(Array.isArray(data.artifacts) ? data.artifacts : []);
  };

  useEffect(() => { load(); }, []);

  const structure = async (id: string) => {
    setBusy(id);
    try {
      await fetch(`${API}/structure/chr`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ artifact_id: id, K: 8 }) });
    } finally { setBusy(null); }
  };

  const convert = async (id: string, fmt: 'txt'|'docx') => {
    setBusy(id+fmt);
    try {
      const r = await fetch(`${API}/convert`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ artifact_id: id, format: fmt }) });
      if (!r.ok) return;
      const data = await r.json();
      if (data.rel) window.open(`${API}/download?rel=${encodeURIComponent(data.rel)}`, '_blank');
    } finally { setBusy(null); }
  };

  const chrViz = async (id: string) => {
    setBusy(id+'viz');
    try {
      const r = await fetch(`${API}/viz/datavzrd`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ artifact_id: id }) });
      if (r.ok) alert('CHR datavzrd project generated. Open http://localhost:5173');
    } finally { setBusy(null); }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Artifacts</h2>
      <div className="max-h-80 overflow-auto border rounded">
        <table className="min-w-full text-left text-xs">
          <thead>
            <tr className="bg-gray-50"><th className="px-2 py-1">id</th><th className="px-2 py-1">filename</th><th className="px-2 py-1">type</th><th className="px-2 py-1">actions</th></tr>
          </thead>
          <tbody>
            {artifacts.map((a:any)=> (
              <tr key={a.id} className="border-t">
                <td className="px-2 py-1">{a.id}</td>
                <td className="px-2 py-1">{a.filename}</td>
                <td className="px-2 py-1">{a.filetype}</td>
                <td className="px-2 py-1 space-x-2">
                  <button onClick={()=>structure(a.id)} disabled={busy===a.id} className="bg-indigo-600 text-white rounded px-2 py-0.5">CHR</button>
                  <button onClick={()=>convert(a.id,'txt')} disabled={busy===a.id+'txt'} className="bg-gray-700 text-white rounded px-2 py-0.5">TXT</button>
                  <button onClick={()=>convert(a.id,'docx')} disabled={busy===a.id+'docx'} className="bg-gray-700 text-white rounded px-2 py-0.5">DOCX</button>
                  <button onClick={()=>chrViz(a.id)} disabled={busy===a.id+'viz'} className="bg-green-600 text-white rounded px-2 py-0.5">CHR Viz</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

