"use client";

import { useEffect, useState } from 'react';
import { useToast } from '@/components/Toast';
import { getApiBase, setApiBase, getAuthorDefault, setAuthorDefault, getVlmEnabled, setVlmEnabled, getUseOllama, setUseOllama, getOfflineHint, setOfflineHint } from '@/lib/config';

export default function SettingsModal({ open, onClose }:{ open:boolean; onClose:()=>void }){
  const { push } = useToast();
  const [apiBase, setApiBaseState] = useState('');
  const [author, setAuthor] = useState('');
  const [vlm, setVlm] = useState(true);
  const [useOllama, setUseOllamaState] = useState(false);
  const [offline, setOffline] = useState(false);

  useEffect(()=>{
    if (!open) return;
    setApiBaseState(getApiBase());
    setAuthor(getAuthorDefault());
    setVlm(getVlmEnabled());
    setUseOllamaState(getUseOllama());
    setOffline(getOfflineHint());
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
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button onClick={onClose} className="border rounded px-3 py-1">Cancel</button>
          <button onClick={()=>{ setApiBase(apiBase); setAuthorDefault(author); setVlmEnabled(vlm); setUseOllama(useOllama); setOfflineHint(offline); push('Settings saved', 'success'); onClose(); }} className="bg-blue-600 text-white rounded px-3 py-1">Save</button>
        </div>
      </div>
    </div>
  );
}
