"use client";

import GlobalSearch from '@/components/GlobalSearch';
import { useToast } from '@/components/Toast';
import SettingsModal from '@/components/SettingsModal';
import { getApiBase, getHRMEnabled } from '@/lib/config';
import { useEffect, useState } from 'react';

export default function HeaderBar() {
  const { push } = useToast();
  const [apiBase, setApiBase] = useState<string>('');
  const [open, setOpen] = useState(false as any);
  const [health, setHealth] = useState<'unknown'|'ok'|'down'>('unknown');
  const [hrm, setHrm] = useState(false);
  const [deeplinkInfo, setDeeplinkInfo] = useState<string | null>(null);
  const [lastDeeplink, setLastDeeplink] = useState<any>(null);

  useEffect(()=>{
    setApiBase(getApiBase());
    setHrm(getHRMEnabled());
    let alive = true;
    async function poll() {
      const base = getApiBase();
      if (!alive) return;
      setApiBase(base);
      try {
        const r = await fetch(`${base.replace(/\/$/,'')}/health`, { method: 'GET' });
        setHealth(r.ok ? 'ok' : 'down');
      } catch {
        setHealth('down');
      }
    }
    poll();
    const id = setInterval(poll, 5000);
    return ()=>{ alive = false; clearInterval(id); };
  }, []);

  // Show a small deeplink breadcrumb when navigation happens
  useEffect(()=>{
    function onDeeplink(ev: any){
      const dl = ev?.detail || {};
      const panel = String(dl.panel || '').toUpperCase();
      const extra = dl.api_id ? `#${dl.api_id}` : dl.document_id ? `:${String(dl.document_id).slice(0,8)}` : (dl.code || dl.q || dl.chunk!=null ? '…' : '');
      setDeeplinkInfo(`${panel}${extra ? ' ' + extra : ''}`);
      setLastDeeplink(dl);
      // auto-hide after a few seconds
      setTimeout(()=>setDeeplinkInfo(null), 5000);
    }
    if (typeof window !== 'undefined') window.addEventListener('global-deeplink' as any, onDeeplink as any);
    return () => { if (typeof window !== 'undefined') window.removeEventListener('global-deeplink' as any, onDeeplink as any); };
  }, []);

  const rebuild = async () => {
    try {
      const base = getApiBase().replace(/\/$/, '');
      const r = await fetch(`${base}/search/rebuild`, { method: 'POST' });
      const data = await r.json().catch(()=>({}));
      if (r.ok) {
        push(`Search index rebuilt (${data.items ?? 'n/a'} items).`, 'success');
      } else {
        push('Rebuild failed', 'error');
      }
    } catch {
      push('Rebuild error', 'error');
    }
  };

  return (
    <div className="sticky top-0 z-30 bg-white/90 backdrop-blur border-b">
      <div className="max-w-7xl mx-auto flex items-center gap-3 p-3">
        <div className="font-semibold text-lg flex items-center gap-2">PMOVES_DoX {hrm && (<span title="HRM Sidecar enabled" className="text-[10px] px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 border border-purple-200">HRM</span>)}
          {deeplinkInfo && (
            <>
              <span className="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 border border-amber-200" title="Last deeplink target">{deeplinkInfo}</span>
              <button
                className="text-[10px] border rounded px-2 py-0.5 ml-1"
                title="Reopen last deeplink"
                onClick={()=>{ try { if (lastDeeplink) window.dispatchEvent(new CustomEvent('global-deeplink', { detail: lastDeeplink })); } catch {} }}
              >Reopen</button>
            </>
          )}
        </div>
        <div className="flex-1"><GlobalSearch /></div>
        <button onClick={rebuild} className="border rounded px-3 py-2 bg-white hover:bg-gray-50 text-gray-700" title="Rebuild vector index">Rebuild Index</button>
        <div
          className={`text-xs px-2 py-1 rounded border ${
            health==='down' ? 'bg-red-50 border-red-200 text-red-700' :
            (apiBase.includes('localhost')||apiBase.includes('127.0.0.1')) ? 'bg-green-50 border-green-200 text-green-700' : 'bg-amber-50 border-amber-200 text-amber-700'
          }`}
          title={`API Base URL (${health==='ok'?'healthy':'unreachable'})`}
        >
          <span className={`inline-block h-2 w-2 rounded-full mr-1 ${health==='down'?'bg-red-600':'bg-green-600'}`} />
          {apiBase || 'http://localhost:8000'}
        </div>
        <button onClick={()=>setOpen(true)} className="ml-2 border rounded px-3 py-2 bg-white hover:bg-gray-50 text-gray-700" title="Settings">Settings</button>
      </div>
      <SettingsModal open={!!open} onClose={()=>setOpen(false)} />
    </div>
  );
}
