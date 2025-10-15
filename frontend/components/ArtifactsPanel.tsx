'use client';

import { useEffect, useState } from 'react';
import { useToast } from '@/components/Toast';

export default function ArtifactsPanel() {
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [detail, setDetail] = useState<any | null>(null);
  const [opts, setOpts] = useState<Record<string, any>>({});
  const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
  const { push } = useToast();

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

  const autoTag = async (id: string) => {
    setBusy(id+'autotag');
    try {
      const o = opts[id] || {};
      const body: any = { async_run: true };
      if (o.includePoml != null) body.include_poml = !!o.includePoml;
      if (o.useHrm != null) body.use_hrm = !!o.useHrm;
      if (o.mangleExec != null) body.mangle_exec = !!o.mangleExec;
      if (o.mangleFile) body.mangle_file = String(o.mangleFile);
      if (o.mangleQuery) body.mangle_query = String(o.mangleQuery);
      if (o.pomlVariant) body.poml_variant = String(o.pomlVariant);
      const r = await fetch(`${API}/autotag/${id}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const contentType = r.headers.get('content-type') || '';
      const payload = contentType.includes('application/json') ? await r.json() : await r.text();
      if (!r.ok) {
        const detail = typeof payload === 'string' ? payload : (payload?.detail || '');
        const msg = detail ? `Auto‑Tag failed: ${detail}` : 'Auto‑Tag failed';
        push(msg, 'error');
        return;
      }
      const data = (typeof payload === 'string') ? {} : payload;
      const saved = Number(data?.tags_saved ?? 0);
      const total = Number.isFinite(Number(data?.tags_total)) ? Number(data.tags_total) : undefined;
      const extracted = Number(data?.tags_extracted ?? data?.tags?.length ?? 0);
      const parts: string[] = [`${saved} new`];
      if (typeof total === 'number' && !Number.isNaN(total)) parts.push(`${total} total`);
      else if (!Number.isNaN(extracted)) parts.push(`${extracted} extracted`);
      push(`Auto‑Tag complete (${parts.join(', ')})`, 'success');
      await load();
      if (detail?.artifact?.id === id) {
        await openDetail(id);
      }
    } catch {
      push('Auto‑Tag error', 'error');
    } finally {
      setBusy(null);
    }
  };

  const openDetail = async (id: string) => {
    const r = await fetch(`${API}/artifacts/${id}`);
    if (!r.ok) return;
    setDetail(await r.json());
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Artifacts</h2>
      <div className="max-h-80 overflow-auto border rounded">
        <table className="min-w-full text-left text-xs">
          <thead>
            <tr className="bg-gray-50"><th className="px-2 py-1">id</th><th className="px-2 py-1">filename</th><th className="px-2 py-1">type</th><th className="px-2 py-1">status</th><th className="px-2 py-1">actions</th></tr>
          </thead>
          <tbody>
            {artifacts.map((a:any)=> (
              <tr key={a.id} className="border-t">
                <td className="px-2 py-1">{a.id}</td>
                <td className="px-2 py-1">{a.filename}</td>
                <td className="px-2 py-1">{a.filetype}</td>
                <td className="px-2 py-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    {typeof a.tags_count === 'number' && (
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border ${a.tags_count>0?'bg-emerald-100 text-emerald-700 border-emerald-200':'bg-gray-100 text-gray-700 border-gray-200'}`}>
                        Auto‑Tag {a.tags_count>0?`done (${a.tags_count})`:'pending'}
                      </span>
                    )}
                    {a.chr_ready && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200">CHR ready</span>
                    )}
                    {a.status && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 border border-amber-200">{a.status}</span>
                    )}
                  </div>
                </td>
                <td className="px-2 py-1 space-x-2">
                  <button onClick={()=>structure(a.id)} disabled={busy===a.id} className="bg-indigo-600 text-white rounded px-2 py-0.5">CHR</button>
                  <button onClick={()=>convert(a.id,'txt')} disabled={busy===a.id+'txt'} className="bg-gray-700 text-white rounded px-2 py-0.5">TXT</button>
                  <button onClick={()=>convert(a.id,'docx')} disabled={busy===a.id+'docx'} className="bg-gray-700 text-white rounded px-2 py-0.5">DOCX</button>
                  <button onClick={()=>chrViz(a.id)} disabled={busy===a.id+'viz'} className="bg-green-600 text-white rounded px-2 py-0.5">CHR Viz</button>
                  <button onClick={()=>autoTag(a.id)} disabled={busy===a.id+'autotag'} className="bg-emerald-600 text-white rounded px-2 py-0.5">Auto‑Tag</button>
                  <button onClick={()=>setOpts(prev=>({ ...prev, [a.id]: { open: !prev?.[a.id]?.open, includePoml: prev?.[a.id]?.includePoml ?? true, useHrm: prev?.[a.id]?.useHrm ?? false, mangleExec: prev?.[a.id]?.mangleExec ?? false, mangleFile: prev?.[a.id]?.mangleFile ?? '', mangleQuery: prev?.[a.id]?.mangleQuery ?? 'normalized_tag(T)', pomlVariant: prev?.[a.id]?.pomlVariant ?? 'generic' } }))} className="bg-white text-gray-700 border rounded px-2 py-0.5">Options</button>
                  <button onClick={()=>openDetail(a.id)} className="bg-white text-blue-700 border border-blue-600 rounded px-2 py-0.5">Details</button>
                </td>
              </tr>
              {opts?.[a.id]?.open && (
                <tr className="bg-gray-50">
                  <td colSpan={5} className="px-2 py-2">
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                      <label className="flex items-center gap-1"><input type="checkbox" checked={!!opts[a.id].includePoml} onChange={e=>setOpts(prev=>({ ...prev, [a.id]: { ...prev[a.id], includePoml: e.target.checked } }))} /> Include POML</label>
                      <label className="flex items-center gap-1"><input type="checkbox" checked={!!opts[a.id].useHrm} onChange={e=>setOpts(prev=>({ ...prev, [a.id]: { ...prev[a.id], useHrm: e.target.checked } }))} /> Use HRM</label>
                      <select value={opts[a.id].pomlVariant} onChange={e=>setOpts(prev=>({ ...prev, [a.id]: { ...prev[a.id], pomlVariant: e.target.value } }))} className="border rounded px-2 py-0.5">
                        <option value="generic">Generic</option>
                        <option value="troubleshoot">Troubleshoot</option>
                        <option value="catalog">Catalog</option>
                      </select>
                      <label className="flex items-center gap-1"><input type="checkbox" checked={!!opts[a.id].mangleExec} onChange={e=>setOpts(prev=>({ ...prev, [a.id]: { ...prev[a.id], mangleExec: e.target.checked } }))} /> Execute Mangle</label>
                      <input value={opts[a.id].mangleFile} onChange={e=>setOpts(prev=>({ ...prev, [a.id]: { ...prev[a.id], mangleFile: e.target.value } }))} placeholder="mangle .mg file" className="border rounded px-2 py-0.5" />
                      <input value={opts[a.id].mangleQuery} onChange={e=>setOpts(prev=>({ ...prev, [a.id]: { ...prev[a.id], mangleQuery: e.target.value } }))} placeholder="mangle query" className="border rounded px-2 py-0.5" />
                      <button onClick={()=>autoTag(a.id)} className="ml-auto bg-emerald-600 text-white rounded px-2 py-0.5">Run Auto‑Tag</button>
                    </div>
                  </td>
                </tr>
              )}
            ))}
          </tbody>
        </table>
      </div>

      {detail && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center" onClick={()=>setDetail(null)}>
          <div className="bg-white rounded shadow p-4 w-[720px] max-h-[80vh] overflow-auto" onClick={e=>e.stopPropagation()}>
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-semibold">Artifact Details</h3>
              <button onClick={()=>setDetail(null)} className="text-gray-500">✕</button>
            </div>
            <div className="text-sm mb-3">
              <div><span className="font-medium">ID:</span> {detail.artifact?.id}</div>
              <div><span className="font-medium">Filename:</span> {detail.artifact?.filename}</div>
              <div><span className="font-medium">Type:</span> {detail.artifact?.filetype}</div>
              <div><span className="font-medium">Path:</span> {detail.artifact?.filepath}</div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="font-medium mb-1">Facts ({(detail.facts||[]).length})</div>
                <div className="border rounded max-h-60 overflow-auto">
                  <table className="min-w-full text-left text-xs">
                    <thead><tr className="bg-gray-50"><th className="px-2 py-1">entity</th><th className="px-2 py-1">metrics</th></tr></thead>
                    <tbody>
                      {(detail.facts||[]).slice(0,10).map((f:any,i:number)=> (
                        <tr key={i} className="border-t"><td className="px-2 py-1">{f.entity||''}</td><td className="px-2 py-1">{JSON.stringify(f.metrics)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <div>
                <div className="font-medium mb-1">Evidence ({(detail.evidence||[]).length})</div>
                <div className="border rounded max-h-60 overflow-auto">
                  <table className="min-w-full text-left text-xs">
                    <thead><tr className="bg-gray-50"><th className="px-2 py-1">locator</th><th className="px-2 py-1">type</th></tr></thead>
                    <tbody>
                      {(detail.evidence||[]).slice(0,10).map((e:any,i:number)=> (
                        <tr key={i} className="border-t"><td className="px-2 py-1">{e.locator}</td><td className="px-2 py-1">{e.content_type}</td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
