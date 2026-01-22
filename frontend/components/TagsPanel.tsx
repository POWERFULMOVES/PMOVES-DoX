'use client';

import { useEffect, useState } from 'react';
import { useToast } from '@/components/Toast';
import { getApiBase, getAuthorDefault, setAuthorDefault, getUseOllama, getHRMEnabled, getHRMMmax, getHRMMmin, setHRMMmax, setHRMMmin } from '@/lib/config';

export default function TagsPanel() {
  const [docId, setDocId] = useState('');
  const [documents, setDocuments] = useState<any[]>([]);
  const [q, setQ] = useState('');
  const [tags, setTags] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [dryRunLoading, setDryRunLoading] = useState(false);
  const [presetPrompt, setPresetPrompt] = useState('');
  const [hasPreset, setHasPreset] = useState(false);
  const [presetExamples, setPresetExamples] = useState<any[] | null>(null);
  const [author, setAuthor] = useState('');
  const [includePoml, setIncludePoml] = useState<boolean>(false);
  const [manglePath, setManglePath] = useState<string>('');
  const [mangleExec, setMangleExec] = useState<boolean>(false);
  const [mangleQuery, setMangleQuery] = useState<string>('normalized_tag(T)');
  const [showHistory, setShowHistory] = useState(false);
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const [selectedHistory, setSelectedHistory] = useState<any | null>(null);
  const [lastSavedAt, setLastSavedAt] = useState<string>('');
  const [useOllama, setUseOllamaState] = useState<boolean>(false);
  const [hrmMmax, setHrmMmax] = useState<number>(getHRMMmax());
  const [hrmMmin, setHrmMmin] = useState<number>(getHRMMmin());
  const [lastHrmSteps, setLastHrmSteps] = useState<number | null>(null);
  const API = getApiBase();
  const { push } = useToast();

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
  // Handle deep links to tags panel (document/q)
  useEffect(() => {
    function onDeeplink(ev: any){
      const dl = ev?.detail || {};
      if (String(dl.panel||'').toLowerCase() !== 'tags') return;
      if (dl.document_id) setDocId(String(dl.document_id));
      if (dl.q) setQ(String(dl.q));
      setTimeout(load, 0);
    }
    if (typeof window !== 'undefined') window.addEventListener('global-deeplink' as any, onDeeplink as any);
    return () => { if (typeof window !== 'undefined') window.removeEventListener('global-deeplink' as any, onDeeplink as any); };
  }, []);
  useEffect(() => {
    // load author from localStorage
    try {
      const a = getAuthorDefault();
      if (a) setAuthor(a);
    } catch {}
    try { setUseOllamaState(getUseOllama()); } catch {}
    (async () => {
      try {
        const r = await fetch(`${API}/documents`);
        if (!r.ok) return;
        const data = await r.json();
        setDocuments(Array.isArray(data.documents) ? data.documents : []);
      } catch {}
    })();
  }, []);

  useEffect(() => {
    try {
      const v = typeof window !== 'undefined' ? localStorage.getItem('lms_hrm_last_steps') : null;
      if (v) setLastHrmSteps(parseInt(v, 10));
    } catch {}
  }, []);

  const extractTags = async () => {
    if (!docId) return;
    try {
      const body: any = { document_id: docId, use_hrm: getHRMEnabled(), include_poml: includePoml };
      if (hasPreset && presetPrompt.trim()) body.prompt = presetPrompt;
      if (hasPreset && presetExamples) body.examples = presetExamples;
      if (useOllama) body.model_id = 'ollama:gemma3';
      try { const pv = (document.getElementById('pomlVariant') as HTMLSelectElement)?.value; if (pv) body.poml_variant = pv; } catch {}
      if (manglePath.trim()) body.mangle_file = manglePath.trim();
      if (mangleExec) body.mangle_exec = true;
      if (mangleQuery.trim()) body.mangle_query = mangleQuery.trim();
      const res = await fetch(`${API}/extract/tags`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (res.ok) { const data = await res.json(); load(); if (data?.hrm?.steps!=null) { const n=Number(data.hrm.steps); setLastHrmSteps(n); try{ localStorage.setItem('lms_hrm_last_steps', String(n)); }catch{} push(`Tags extracted (HRM steps: ${n})`, 'success'); } else { setLastHrmSteps(null); try{ localStorage.removeItem('lms_hrm_last_steps'); }catch{} push('Tags extracted', 'success'); } }
      else { push('Extract tags failed', 'error'); }
    } catch {
      alert('Extract tags error');
    }
  };

  const previewTags = async () => {
    if (!docId) return;
    setDryRunLoading(true);
    try {
      const body: any = { document_id: docId, dry_run: true, use_hrm: getHRMEnabled(), include_poml: includePoml };
      if (hasPreset && presetPrompt.trim()) body.prompt = presetPrompt;
      if (hasPreset && presetExamples) body.examples = presetExamples;
      if (useOllama) body.model_id = 'ollama:gemma3';
      try { const pv = (document.getElementById('pomlVariant') as HTMLSelectElement)?.value; if (pv) body.poml_variant = pv; } catch {}
      if (manglePath.trim()) body.mangle_file = manglePath.trim();
      if (mangleExec) body.mangle_exec = true;
      if (mangleQuery.trim()) body.mangle_query = mangleQuery.trim();
      const res = await fetch(`${API}/extract/tags`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (res.ok) { const data = await res.json(); const list = (data?.tags || []).join(', '); const base = list ? `Preview: ${list}` : 'No tags found'; const hasSteps = (data?.hrm?.steps!=null); if (hasSteps) { const n=Number(data.hrm.steps); setLastHrmSteps(n); try{ localStorage.setItem('lms_hrm_last_steps', String(n)); }catch{} } const msg = hasSteps ? `${base} (HRM steps: ${data.hrm.steps})` : base; push(msg, list ? 'info' : 'error'); } else { push('Preview failed', 'error'); }
    } catch { push('Preview error', 'error'); }
    finally {
      setDryRunLoading(false);
    }
  };

  const loadPreset = async () => {
    try {
      const r = await fetch(`${API}/tags/presets`);
      if (!r.ok) throw new Error('preset fetch failed');
      const data = await r.json();
      setPresetPrompt(String(data?.prompt || ''));
      setPresetExamples(Array.isArray(data?.examples) ? data.examples : null);
      setHasPreset(true);
    } catch { push('Failed to load preset', 'error'); }
  };

  useEffect(() => {
    // when doc changes, try to load saved prompt
    (async () => {
      if (!docId) return;
      // load draft first
      try {
        const draft = localStorage.getItem(`lms_prompt_draft_${docId}`);
        if (draft) { setPresetPrompt(draft); setHasPreset(true); setLastSavedAt('(draft)'); }
      } catch {}
      try {
        const r = await fetch(`${API}/tags/prompt/${docId}`);
        if (!r.ok) return;
        const data = await r.json();
        if (data?.prompt_text) {
          setPresetPrompt(String(data.prompt_text));
          setPresetExamples(Array.isArray(data.examples) ? data.examples : null);
          setHasPreset(true);
          setLastSavedAt(String(data.created_at || ''));
        }
      } catch {}
    })();
  }, [docId]);

  const savePreset = async () => {
    if (!docId) return;
    try {
      const r = await fetch(`${API}/tags/prompt/${docId}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt_text: presetPrompt, examples: presetExamples || [], author: author || undefined })});
      if (!r.ok) throw new Error('save failed');
      push('Prompt saved', 'success');
    } catch { push('Failed to save prompt', 'error'); }
  };

  const openHistory = async () => {
    if (!docId) return;
    try {
      const r = await fetch(`${API}/tags/prompt/${docId}/history?limit=10`);
      if (!r.ok) throw new Error('history failed');
      const data = await r.json();
      setHistoryItems(Array.isArray(data?.items) ? data.items : []);
      setShowHistory(true);
    } catch { push('Failed to load history', 'error'); }
  };

  // basic line diff between two strings
  function diffLines(a: string, b: string): { type:'same'|'add'|'del'; text:string }[] {
    const aLines = (a||'').split('\n');
    const bLines = (b||'').split('\n');
    const m = aLines.length, n = bLines.length;
    const dp: number[][] = Array.from({length:m+1}, ()=>Array(n+1).fill(0));
    for (let i=m-1;i>=0;i--) {
      for (let j=n-1;j>=0;j--) {
        dp[i][j] = aLines[i] === bLines[j] ? 1 + dp[i+1][j+1] : Math.max(dp[i+1][j], dp[i][j+1]);
      }
    }
    const out: {type:'same'|'add'|'del';text:string}[] = [];
    let i=0,j=0;
    while (i<m && j<n) {
      if (aLines[i] === bLines[j]) { out.push({type:'same', text:aLines[i]}); i++; j++; }
      else if (dp[i+1][j] >= dp[i][j+1]) { out.push({type:'del', text:aLines[i++]}); }
      else { out.push({type:'add', text:bLines[j++]}); }
    }
    while (i<m) out.push({type:'del', text:aLines[i++]});
    while (j<n) out.push({type:'add', text:bLines[j++]});
    return out;
  }

  return (
    <div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 p-6 rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Application Tags</h2>
      <div className="grid grid-cols-1 md:grid-cols-7 gap-2 mb-3">
        <select className="border rounded px-2 py-1" value={docId} onChange={e=>setDocId(e.target.value)}>
          <option value="">Select document…</option>
          {documents.map((d:any)=> (<option key={d.id} value={d.id}>{d.type} — {d.title || d.path}</option>))}
        </select>
        <input className="border rounded px-2 py-1" placeholder="search tag" value={q} onChange={e=>setQ(e.target.value)} />
        <button onClick={load} className="bg-blue-600 text-white rounded px-3">Filter</button>
        <button onClick={loadPreset} className="bg-gray-700 text-white rounded px-3">Load LMS Preset</button>
        <button onClick={previewTags} disabled={!docId || dryRunLoading} className="bg-gray-700 text-white rounded px-3">{dryRunLoading ? 'Previewing…' : 'Preview (dry run)'}</button>
        <button onClick={extractTags} disabled={!docId} className="bg-green-600 text-white rounded px-3">Extract Tags</button>
        <div className="flex items-center gap-1 text-xs text-gray-700">
          <span className="text-gray-600">HRM</span>
          <label className="text-gray-600">Mmax</label>
          <input type="number" min={1} value={hrmMmax} onChange={e=>{ const n=parseInt(e.target.value||'6',10); setHrmMmax(n); setHRMMmax(n); }} className="w-16 border rounded px-1 py-0.5" />
          <label className="text-gray-600">Mmin</label>
          <input type="number" min={1} value={hrmMmin} onChange={e=>{ const n=parseInt(e.target.value||'2',10); setHrmMmin(n); setHRMMmin(n); }} className="w-16 border rounded px-1 py-0.5" />
        </div>
        <label className="flex items-center gap-1 text-xs text-gray-700"><input type="checkbox" checked={useOllama} onChange={e=>{ setUseOllamaState(e.target.checked); try{ localStorage.setItem('lms_use_ollama', e.target.checked ? 'true' : 'false'); } catch{} }} /> Use Ollama</label>
      </div>

      {hasPreset && (
        <div className="mb-3">
          <label className="text-sm font-medium">Preset Prompt (editable) {lastSavedAt && (<span className="text-gray-500 text-xs">— last saved: {lastSavedAt}</span>)}</label>
          <textarea className="w-full border rounded px-2 py-1 mt-1" rows={3} value={presetPrompt} onChange={e=>{ setPresetPrompt(e.target.value); if (docId) localStorage.setItem(`lms_prompt_draft_${docId}`, e.target.value); }} />
          <div className="text-xs text-gray-600 mt-1">Examples loaded: {presetExamples?.length ?? 0}</div>
          <div className="mt-2 flex gap-2">
            <button onClick={async ()=>{ await savePreset(); if (docId) localStorage.removeItem(`lms_prompt_draft_${docId}`); setLastSavedAt(new Date().toISOString()); }} className="bg-gray-800 text-white rounded px-3 py-1">Save Prompt</button>
            <button onClick={openHistory} className="bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white rounded px-3 py-1">History</button>
            <select className="border rounded px-2 py-1 text-xs" id="pomlVariant">
              <option value="generic">Generic</option>
              <option value="troubleshoot">Troubleshoot</option>
              <option value="catalog">Catalog</option>
            </select>
            <button onClick={async ()=>{ if(!docId) return; try{ const variant = (document.getElementById('pomlVariant') as HTMLSelectElement)?.value || 'generic'; const r=await fetch(`${API}/export/poml`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ document_id: docId, variant })}); if(!r.ok) throw new Error('export failed'); const data=await r.json(); if (data && data.rel){ const rel = String(data.rel); const url = `${API}/download?rel=${encodeURIComponent(rel)}`; window.open(url, '_blank'); try{ localStorage.setItem('last_poml_rel', rel);}catch{} } push('POML exported', 'success'); } catch { push('POML export failed', 'error'); } }} className="bg-purple-600 text-white rounded px-3 py-1">Export POML</button>
            <label className="text-xs text-gray-700 flex items-center gap-1"><input type="checkbox" checked={includePoml} onChange={e=>setIncludePoml(e.target.checked)} /> Include POML in prompt</label>
            <input className="border rounded px-2 py-1 text-xs" placeholder="mangle file (optional)" value={manglePath} onChange={e=>setManglePath(e.target.value)} />
            <label className="text-xs text-gray-700 flex items-center gap-1"><input type="checkbox" checked={mangleExec} onChange={e=>setMangleExec(e.target.checked)} /> Execute Mangle</label>
            <input className="border rounded px-2 py-1 text-xs" placeholder="mangle query (e.g., normalized_tag(T))" value={mangleQuery} onChange={e=>setMangleQuery(e.target.value)} />
          <input className="border rounded px-2 py-1 ml-auto" placeholder="author (optional)" value={author} onChange={e=>{ setAuthor(e.target.value); setAuthorDefault(e.target.value); }} />
          </div>
        </div>
      )}

      {typeof window !== 'undefined' && localStorage.getItem('last_poml_rel') && (
        <div className="text-xs text-gray-600 -mt-2 mb-2">Last export: <a className="text-blue-700 underline" href={`${API}/download?rel=${encodeURIComponent(localStorage.getItem('last_poml_rel') || '')}`} target="_blank">download</a></div>
      )}

      {showHistory && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-20" onClick={()=>setShowHistory(false)}>
          <div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded shadow max-w-2xl w-full p-4" onClick={e=>e.stopPropagation()}>
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-semibold">Prompt History</h3>
              <button onClick={()=>setShowHistory(false)} className="px-2">✕</button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="max-h-96 overflow-auto space-y-3 border rounded p-2">
                {historyItems.length === 0 ? (
                  <div className="text-sm text-gray-500">No history found.</div>
                ) : historyItems.map((h:any)=> (
                  <div key={h.id} className={`border rounded p-2 cursor-pointer ${selectedHistory?.id===h.id?'ring-2 ring-blue-500':''}`} onClick={()=>setSelectedHistory(h)}>
                    <div className="text-xs text-gray-500 mb-1">{h.created_at} {h.author? `· ${h.author}`: ''}</div>
                    <div className="text-xs line-clamp-3 whitespace-pre-wrap">{String(h.prompt_text)}</div>
                  </div>
                ))}
              </div>
              <div>
                <div className="text-xs text-gray-600 mb-1">Diff vs current editor</div>
                <div className="text-xs bg-gray-50 dark:bg-gray-800 border rounded p-2 max-h-96 overflow-auto whitespace-pre-wrap">
                  {selectedHistory ? (
                    diffLines(selectedHistory.prompt_text || '', presetPrompt).map((d,i)=> (
                      <div key={i} className={d.type==='add'?'text-green-700':d.type==='del'?'text-red-700':'text-gray-800'}>
                        {d.type==='add'?'+ ': d.type==='del'?'- ':'  '}{d.text}
                      </div>
                    ))
                  ) : 'Select a version to preview'}
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-3">
              <button disabled={!selectedHistory} onClick={()=>{ if (!selectedHistory) return; setPresetPrompt(String(selectedHistory.prompt_text||'')); push('Restored into editor', 'success'); }} className="bg-gray-700 text-white rounded px-3 py-1 disabled:opacity-50">Restore into editor</button>
              <button disabled={!selectedHistory || !docId} onClick={async ()=>{ if (!selectedHistory) return; try { const r = await fetch(`${API}/tags/prompt/${docId}`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ prompt_text: selectedHistory.prompt_text, examples: selectedHistory.examples||[], author: author||undefined })}); if (!r.ok) throw new Error('restore save failed'); push('Restored and saved', 'success'); } catch { push('Restore failed', 'error'); } }} className="bg-green-600 text-white rounded px-3 py-1 disabled:opacity-50">Restore & Save</button>
              <button onClick={()=>setShowHistory(false)} className="bg-blue-600 text-white rounded px-3 py-1">Close</button>
            </div>
          </div>
        </div>
      )}
      {loading ? <div>Loading…</div> : (
        <div className="max-h-80 overflow-auto border rounded">
          <table className="min-w-full text-left text-xs">
            <thead><tr className="bg-gray-50 dark:bg-gray-800"><th className="px-2 py-1">tag</th><th className="px-2 py-1">score</th><th className="px-2 py-1">document</th><th className="px-2 py-1">source</th><th className="px-2 py-1">hrm</th></tr></thead>
            <tbody>
              {tags.map((t,i)=> (
                <tr key={i} className="border-t">
                  <td className="px-2 py-1">{t.tag}</td>
                  <td className="px-2 py-1">{t.score ?? ''}</td>
                  <td className="px-2 py-1">{t.document_id}</td>
                  <td className="px-2 py-1">{t.source_ptr || ''}</td>
                  <td className="px-2 py-1">{(t.hrm_steps!=null) ? (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 border border-purple-200" title="HRM refinement steps (stored)">{t.hrm_steps}</span>
                  ) : (lastHrmSteps!=null ? (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-50 text-purple-600 border border-purple-100" title="HRM refinement steps (last run)">{lastHrmSteps}</span>
                  ) : '')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
