'use client';

import { useEffect, useState } from 'react';
import { useToast } from '@/components/Toast';
import { getApiBase } from '@/lib/config';

export default function APIsPanel() {
  const [tag, setTag] = useState('');
  const [method, setMethod] = useState('');
  const [pathLike, setPathLike] = useState('');
  const [apis, setApis] = useState<any[]>([]);
  const [selected, setSelected] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const API = getApiBase();
  const { push } = useToast();

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (tag) params.set('tag', tag);
      if (method) params.set('method', method);
      if (pathLike) params.set('path_like', pathLike);
      const r = await fetch(`${API}/apis?${params.toString()}`);
      if (!r.ok) { push('Failed to load API detail', 'error'); return; }
      const data = await r.json();
      setApis(Array.isArray(data.apis) ? data.apis : []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // Handle deep links to specific API id
  useEffect(() => {
    function onDeeplink(ev: any){
      const dl = ev?.detail || {};
      if (String(dl.panel||'').toLowerCase() !== 'apis') return;
      if (dl.api_id) openDetail(String(dl.api_id));
      if (dl.path_like) { setPathLike(String(dl.path_like)); setTimeout(load, 0); }
    }
    if (typeof window !== 'undefined') {
      window.addEventListener('global-deeplink' as any, onDeeplink as any);
    }
    return () => { if (typeof window !== 'undefined') window.removeEventListener('global-deeplink' as any, onDeeplink as any); };
  }, []);

  const openDetail = async (id: string) => {
    try {
      const r = await fetch(`${API}/apis/${id}`);
      if (!r.ok) return;
      const data = await r.json();
      setSelected(data);
    } catch {}
  };

  const copyCurl = async () => {
    if (!selected) return;
    const url = selected?.path || '/';
    const cmd = `curl -X ${selected.method || 'GET'} "${url}"`;
    await navigator.clipboard.writeText(cmd);
    push('cURL copied', 'success');
  };

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
            <thead><tr className="bg-gray-50 dark:bg-gray-800"><th className="px-2 py-1">method</th><th className="px-2 py-1">path</th><th className="px-2 py-1">summary</th><th className="px-2 py-1">tags</th></tr></thead>
            <tbody>
              {apis.map((a,i)=> (
                <tr key={i} className="border-t hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer" onClick={()=>openDetail(a.id)}>
                  <td className="px-2 py-1">{a.method}</td>
                  <td className="px-2 py-1">{a.path}</td>
                  <td className="px-2 py-1">{a.summary}</td>
                  <td className="px-2 py-1">{(a.tags||[]).join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-20" onClick={()=>setSelected(null)}>
          <div className="bg-white rounded shadow max-w-2xl w-full p-4" onClick={e=>e.stopPropagation()}>
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-semibold">{selected.method} {selected.path}</h3>
              <button onClick={()=>setSelected(null)} className="px-2">✕</button>
            </div>
            {selected.summary && <p className="text-sm mb-2">{selected.summary}</p>}
            <div className="mb-2">
              <div className="text-xs font-semibold">Parameters</div>
              <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-40">{JSON.stringify(selected.parameters, null, 2)}</pre>
            </div>
            <div className="mb-2">
              <div className="text-xs font-semibold">Responses</div>
              <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-40">{JSON.stringify(selected.responses, null, 2)}</pre>
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={copyCurl} className="bg-gray-800 text-white rounded px-3 py-1">Copy cURL</button>
              <button onClick={()=>setSelected(null)} className="bg-blue-600 text-white rounded px-3 py-1">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
