'use client';

import { useEffect, useRef, useState } from 'react';
import FileUpload from '@/components/FileUpload';
import QAInterface from '@/components/QAInterface';
import FactsViewer from '@/components/FactsViewer';
import CHRPanel from '@/components/CHRPanel';
import LogsPanel from '@/components/LogsPanel';
import APIsPanel from '@/components/APIsPanel';
import TagsPanel from '@/components/TagsPanel';
import ArtifactsPanel from '@/components/ArtifactsPanel';
import { useToast } from '@/components/Toast';
import HeaderBar from '@/components/HeaderBar';
import EntitiesPanel from '@/components/EntitiesPanel';
import StructurePanel from '@/components/StructurePanel';
import MetricHitsPanel from '@/components/MetricHitsPanel';
import SummariesPanel from '@/components/SummariesPanel';

export default function Home() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [vlmRepo, setVlmRepo] = useState<string | null>(null);
  const [queuedCount, setQueuedCount] = useState<number>(0);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const [tab, setTab] = useState<'workspace'|'logs'|'apis'|'tags'|'artifacts'>('workspace');
  const { push } = useToast();

  const handleUploadComplete = () => {
    setRefreshKey(prev => prev + 1);
  };

  useEffect(() => {
    const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
    fetch(`${API}/config`).then(async (r) => {
      if (!r.ok) return;
      const cfg = await r.json();
      if (cfg?.vlm_repo) setVlmRepo(cfg.vlm_repo as string);
    }).catch(() => {});
    // Poll tasks summary for processing banner
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API}/tasks`);
        if (!r.ok) return;
        const t = await r.json();
        setQueuedCount(Number(t?.queued || 0));
      } catch {}
    }, Number(process.env.NEXT_PUBLIC_POLL_INTERVAL_MS || 3000));
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // Handle global deep links from search results
  useEffect(() => {
    function onDeeplink(e: any){
      try {
        const dl = e?.detail || {};
        const panel = String(dl.panel || '').toLowerCase();
        if (panel === 'apis') setTab('apis');
        else if (panel === 'logs') setTab('logs');
        else if (panel === 'tags') setTab('tags');
        else if (panel === 'workspace') setTab('workspace');
      } catch {}
    }
    if (typeof window !== 'undefined') {
      window.addEventListener('global-deeplink' as any, onDeeplink as any);
    }
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('global-deeplink' as any, onDeeplink as any);
      }
    };
  }, []);

  return (
    <main className="min-h-screen bg-gray-50">
      <HeaderBar />
      <div className="max-w-7xl mx-auto p-8">
        <div className="flex items-center gap-3 mb-2">
          {vlmRepo && (
            <span title={`VLM enabled: ${vlmRepo}`} className="inline-flex items-center text-xs px-2 py-1 rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200">
              VLM: Granite Docling
            </span>
          )}
        </div>
        {queuedCount > 0 && (
          <div className="mb-4 flex items-center gap-2 text-sm px-3 py-2 rounded border border-amber-200 bg-amber-50 text-amber-800">
            <span className="inline-block h-3 w-3 rounded-full bg-amber-500 animate-pulse" />
            Processing PDFs in background: {queuedCount} file(s)…
          </div>
        )}
        <h1 className="text-3xl font-semibold text-gray-900 mb-2">PMOVES-DoX</h1>
        <p className="text-gray-600 mb-3">The ultimate document structured data extraction and analysis tool.</p>
        <p className="text-gray-500 mb-6">Extract, analyze, transform, and visualize data from PDFs, XML logs, CSV/XLSX, and OpenAPI/Postman collections. Local-first with Hugging Face + Ollama; ships as standalone, Docker, and MS Teams Copilot/MCP-friendly.</p>

        <div className="mb-6 flex gap-2">
          {(['workspace','logs','apis','tags','artifacts'] as const).map(t => (
            <button key={t} onClick={()=>setTab(t)} className={`px-3 py-1 rounded border ${tab===t?'bg-blue-600 text-white border-blue-600':'bg-white text-gray-700'}`}>{t.toUpperCase()}</button>
          ))}
        </div>
        
        {tab==='workspace' && (
          <>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              <FileUpload onUploadComplete={handleUploadComplete} />
              <QAInterface />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              <FactsViewer key={refreshKey} />
              <CHRPanel />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
              <EntitiesPanel refreshKey={refreshKey} />
              <StructurePanel refreshKey={refreshKey} />
              <MetricHitsPanel refreshKey={refreshKey} />
            </div>
            <div className="grid grid-cols-1 gap-8 mb-8">
              <SummariesPanel />
            </div>
          </>
        )}
        {tab==='logs' && (
          <LogsPanel />
        )}
        {tab==='apis' && (
          <APIsPanel />
        )}
        {tab==='tags' && (
          <TagsPanel />
        )}
        {tab==='artifacts' && (
          <ArtifactsPanel />
        )}
      </div>
    </main>
  );
}
