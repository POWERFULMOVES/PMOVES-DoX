"use client";

import { useEffect, useState } from 'react';
import { useToast } from '@/components/Toast';
import { getApiBase, setApiBase, getAuthorDefault, setAuthorDefault, getVlmEnabled, setVlmEnabled, getUseOllama, setUseOllama, getOfflineHint, setOfflineHint, getHRMEnabled, setHRMEnabled, getHRMMmax, setHRMMmax, getHRMMmin, setHRMMmin } from '@/lib/config';

export default function SettingsModal({ open, onClose }:{ open:boolean; onClose:()=>void }){
  const { push } = useToast();
  const [apiBase, setApiBaseState] = useState('');
  const [author, setAuthor] = useState('');
  const [vlm, setVlm] = useState(true);
  const [useOllama, setUseOllamaState] = useState(false);
  const [offline, setOffline] = useState(false);
  const [hrmEnabled, setHrmEnabled] = useState(false);
  const [hrmMmax, setHrmMmax] = useState(6);
  const [hrmMmin, setHrmMmin] = useState(2);

  useEffect(()=>{
    if (!open) return;
    setApiBaseState(getApiBase());
    setAuthor(getAuthorDefault());
    setVlm(getVlmEnabled());
    setUseOllamaState(getUseOllama());
    setOffline(getOfflineHint());
    setHrmEnabled(getHRMEnabled());
    setHrmMmax(getHRMMmax());
    setHrmMmin(getHRMMmin());
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-40 flex items-center justify-center" onClick={onClose}>
      <div className="bg-white rounded shadow max-w-lg w-full p-4" onClick={e=>e.stopPropagation()}>
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-semibold">Settings</h3>
          <button onClick={onClose} className="px-2">✕</button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium">API Base URL</label>
            <input className="w-full border rounded px-2 py-1 mt-1" value={apiBase} onChange={e=>setApiBaseState(e.target.value)} placeholder="http://localhost:8000" />
          </div>
          <div>
            <label className="text-sm font-medium">Default Author</label>
            <input className="w-full border rounded px-2 py-1 mt-1" value={author} onChange={e=>setAuthor(e.target.value)} placeholder="Your Name" />
          </div>
          <div className="flex items-center gap-2">
            <input id="vlm" type="checkbox" checked={vlm} onChange={e=>setVlm(e.target.checked)} />
            <label htmlFor="vlm" className="text-sm">Show VLM badge (UI only)</label>
          </div>
          <div className="flex items-center gap-2">
            <input id="ollama" type="checkbox" checked={useOllama} onChange={e=>setUseOllamaState(e.target.checked)} />
            <label htmlFor="ollama" className="text-sm">Prefer Ollama for tag extraction</label>
          </div>
          <div className="flex items-center gap-2">
            <input id="offline" type="checkbox" checked={offline} onChange={e=>setOffline(e.target.checked)} />
            <label htmlFor="offline" className="text-sm">Offline mode hint (avoid external calls)</label>
          </div>
          <div className="pt-2 border-t">
            <div className="flex items-center gap-2">
              <input id="hrm" type="checkbox" checked={hrmEnabled} onChange={e=>setHrmEnabled(e.target.checked)} />
              <label htmlFor="hrm" className="text-sm">Use HRM Sidecar (experimental)</label>
            </div>
            <div className="grid grid-cols-2 gap-3 mt-2">
              <div>
                <label className="text-sm font-medium">Mmax</label>
                <input type="number" min={1} className="w-full border rounded px-2 py-1 mt-1" value={hrmMmax} onChange={e=>setHrmMmax(parseInt(e.target.value||'6',10))} />
              </div>
              <div>
                <label className="text-sm font-medium">Mmin</label>
                <input type="number" min={1} className="w-full border rounded px-2 py-1 mt-1" value={hrmMmin} onChange={e=>setHrmMmin(parseInt(e.target.value||'2',10))} />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-1">Controls refinement steps for experiments and /ask wiring.</p>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="border rounded px-3 py-1">Cancel</button>
          <button onClick={()=>{ setApiBase(apiBase); setAuthorDefault(author); setVlmEnabled(vlm); setUseOllama(useOllama); setOfflineHint(offline); setHRMEnabled(hrmEnabled); setHRMMmax(hrmMmax); setHRMMmin(hrmMmin); push('Settings saved', 'success'); onClose(); }} className="bg-blue-600 text-white rounded px-3 py-1">Save</button>
        </div>
      </div>
    </div>
  );
}
