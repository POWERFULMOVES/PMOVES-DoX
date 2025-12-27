'use client';

import { useEffect, useState, useRef } from 'react';

export default function CHRPanel() {
  const [artifactId, setArtifactId] = useState('');
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const [K, setK] = useState(8);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [convertBusy, setConvertBusy] = useState(false);
  const [convertFormat, setConvertFormat] = useState<'txt' | 'docx'>('txt');
  const [convertRel, setConvertRel] = useState<string | null>(null);
  const [vizBusy, setVizBusy] = useState(false);
  const [vizRel, setVizRel] = useState<string | null>(null);
  const [highlightIdx, setHighlightIdx] = useState<number | null>(null);
  const highlightRef = useRef<HTMLTableRowElement | null>(null);
  const [pageNum, setPageNum] = useState<number | null>(null);
  const [openPdfEnabled, setOpenPdfEnabled] = useState<boolean>(false);
  // HRM demo
  const [hrmDigits, setHrmDigits] = useState('93241');
  const [hrmTrace, setHrmTrace] = useState<string[] | null>(null);
  const [hrmSteps, setHrmSteps] = useState<number | null>(null);
  const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/artifacts`);
        if (!r.ok) return;
        const data = await r.json();
        setArtifacts(Array.isArray(data.artifacts) ? data.artifacts : []);
      } catch {}
    })();
    // fetch config for OPEN_PDF_ENABLED
    (async () => {
      try {
        const r = await fetch(`${API}/config`);
        if (!r.ok) return;
        const cfg = await r.json();
        setOpenPdfEnabled(!!cfg?.open_pdf_enabled);
      } catch {}
    })();
  }, []);

  const runCHR = async () => {
    if (!artifactId.trim()) return;
    setBusy(true);
    try {
      const res = await fetch(`${API}/structure/chr`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ artifact_id: artifactId.trim(), K })
      });
      if (!res.ok) throw new Error('CHR failed');
      const data = await res.json();
      setResult(data);
    } catch (e) {
      alert('CHR failed. Check backend logs.');
    } finally {
      setBusy(false);
    }
  };

  const convert = async () => {
    if (!artifactId.trim()) return;
    setConvertBusy(true);
    setConvertRel(null);
    try {
      const res = await fetch(`${API}/convert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ artifact_id: artifactId.trim(), format: convertFormat })
      });
      if (!res.ok) throw new Error('convert failed');
      const data = await res.json();
      if (data.rel) setConvertRel(String(data.rel));
    } catch (e) {
      alert('Convert failed.');
    } finally {
      setConvertBusy(false);
    }
  };

  const buildViz = async () => {
    if (!artifactId.trim()) return;
    setVizBusy(true);
    setVizRel(null);
    try {
      const res = await fetch(`${API}/viz/datavzrd`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ artifact_id: artifactId.trim(), title: `CHR – ${artifactId.trim().slice(0,8)}...` })
      });
      if (!res.ok) throw new Error('viz failed');
      const data = await res.json();
      if (data.rel_viz) setVizRel(String(data.rel_viz));
      else setVizRel(null);
      alert(`datavzrd project written to ${data.project_dir}. Run: datavzrd serve ${data.viz_yaml}`);
    } catch (e) {
      alert('Failed to generate datavzrd project.');
    } finally {
      setVizBusy(false);
    }
  };

  const runHRMDemo = async () => {
    setHrmTrace(null); setHrmSteps(null);
    try {
      const res = await fetch(`${API}/experiments/hrm/sort_digits`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ seq: hrmDigits }) });
      if (!res.ok) throw new Error('hrm demo failed');
      const data = await res.json();
      setHrmTrace(Array.isArray(data.trace) ? data.trace : []);
      setHrmSteps(typeof data.steps === 'number' ? data.steps : null);
    } catch {
      alert('HRM demo failed.');
    }
  };

  // Handle deep links to workspace/pdf chunk: { panel:'workspace', artifact_id, chunk? }
  useEffect(() => {
    function onDeeplink(ev: any){
      const dl = ev?.detail || {};
      if (String(dl.panel||'').toLowerCase() !== 'workspace') return;
      if (dl.artifact_id) {
        setArtifactId(String(dl.artifact_id));
        if (typeof dl.chunk === 'number') setHighlightIdx(Number(dl.chunk));
        if (typeof dl.page === 'number') setPageNum(Number(dl.page));
        setTimeout(runCHR, 0);
      }
    }
    if (typeof window !== 'undefined') window.addEventListener('global-deeplink' as any, onDeeplink as any);
    return () => { if (typeof window !== 'undefined') window.removeEventListener('global-deeplink' as any, onDeeplink as any); };
  }, []);

  // Scroll to highlighted row when available
  useEffect(() => {
    if (highlightRef.current) {
      try { highlightRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch {}
    }
  }, [highlightIdx, result]);

  return (
    <div className="flex flex-col h-full min-h-[500px]">
      <h2 className="text-sm font-semibold mb-4 flex items-center gap-2 text-muted-foreground uppercase tracking-wider">
         Structure Recovery (CHR)
      </h2>
      
      {artifactId && pageNum!=null && openPdfEnabled && (
        <div className="mb-4 text-xs">
          <a className="text-secondary-foreground underline flex items-center gap-1 hover:text-primary transition-colors" href={`${API}/open/pdf?artifact_id=${encodeURIComponent(artifactId)}#page=${pageNum}`} target="_blank">
             Open PDF Source <span className="opacity-50">↗</span>
          </a>
        </div>
      )}

      {/* Inputs */}
      <div className="space-y-4 mb-6">
        <div>
          <label className="block text-xs font-medium mb-1.5 text-muted-foreground ml-1">Artifact Selection</label>
          <div className="flex flex-col sm:flex-row gap-2">
            <select 
                className="flex-1 px-3 py-2 bg-secondary/30 border border-border/40 rounded-lg text-sm focus:ring-1 focus:ring-primary/50 focus:outline-none" 
                value={artifactId} 
                onChange={(e) => setArtifactId(e.target.value)}
            >
              <option value="">Select an artifact...</option>
              {artifacts.map((a: any) => (
                <option key={a.id} value={a.id}>{a.id} — {a.filename}</option>
              ))}
            </select>
            <input
              className="flex-1 px-3 py-2 bg-secondary/30 border border-border/40 rounded-lg text-sm placeholder:text-muted-foreground/50 focus:ring-1 focus:ring-primary/50 focus:outline-none"
              value={artifactId}
              onChange={(e) => setArtifactId(e.target.value)}
              placeholder="Or paste ID..."
            />
          </div>
        </div>
        
        {/* K Slider/Input */}
        <div>
           <label className="block text-xs font-medium mb-1.5 text-muted-foreground ml-1">Constellations (K): {K}</label>
           <input
             type="range"
             className="w-full accent-primary h-1 bg-secondary/50 rounded-lg appearance-none cursor-pointer"
             value={K}
             min={2}
             max={32}
             onChange={(e) => setK(Number(e.target.value))}
           />
        </div>

        <button
          onClick={runCHR}
          disabled={busy || !artifactId}
          className="w-full bg-primary/90 hover:bg-primary text-primary-foreground py-2.5 rounded-lg text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-primary/20"
        >
          {busy ? 'Analyzing Structure...' : 'Run CHR Analysis'}
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className="mt-2 space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
           {/* Stats Grid */}
           <div className="grid grid-cols-2 gap-3">
              <div className="bg-card/40 border border-border/40 p-3 rounded-xl">
                 <div className="text-xs text-muted-foreground mb-1">MHEP Score</div>
                 <div className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-green-400 to-emerald-500">
                    {result.mhep?.toFixed?.(1) ?? result.mhep}
                 </div>
              </div>
              <div className="bg-card/40 border border-border/40 p-3 rounded-xl">
                 <div className="text-xs text-muted-foreground mb-1">Entropy (Hg/Hs)</div>
                 <div className="text-sm font-mono text-foreground/80">
                    {result.Hg?.toFixed?.(2) ?? '-'} <span className="text-muted-foreground">/</span> {result.Hs?.toFixed?.(2) ?? '-'}
                 </div>
              </div>
           </div>

           {/* Plot Image */}
           {result.artifacts?.rel_plot && (
             <div className="relative group overflow-hidden rounded-xl border border-border/40 bg-black/20">
               <img src={`${API}/download?rel=${encodeURIComponent(result.artifacts.rel_plot)}`} alt="CHR PCA" className="w-full h-auto object-cover opacity-90 group-hover:opacity-100 transition-opacity" />
               <div className="absolute top-2 right-2 bg-black/60 text-white text-[10px] px-2 py-0.5 rounded backdrop-blur-md">PCA Projection</div>
             </div>
           )}

           {/* Preview Table */}
           {Array.isArray(result.preview_rows) && result.preview_rows.length > 0 && (
             <div className="bg-card/30 border border-border/40 rounded-xl overflow-hidden">
                <div className="px-3 py-2 border-b border-border/40 bg-secondary/20 text-xs font-semibold text-foreground/80">
                   Cluster Preview
                </div>
                <div className="max-h-48 overflow-y-auto">
                   <table className="w-full text-left text-xs">
                      <thead className="bg-secondary/10 text-muted-foreground sticky top-0">
                         <tr>
                            <th className="px-3 py-2 font-medium">ID</th>
                            <th className="px-3 py-2 font-medium">Cluster</th>
                            <th className="px-3 py-2 font-medium">Radius</th>
                            <th className="px-3 py-2 font-medium">Text Snippet</th>
                         </tr>
                      </thead>
                      <tbody className="divide-y divide-border/20">
                         {result.preview_rows.map((r: any, i: number) => (
                           <tr 
                              key={i}
                              ref={(el) => { if (el && highlightIdx!=null && r.idx===highlightIdx) highlightRef.current = el; }}
                              className={`transition-colors ${highlightIdx === r.idx ? 'bg-primary/20' : 'hover:bg-white/5'}`}
                           >
                              <td className="px-3 py-2 font-mono text-muted-foreground">{r.idx}</td>
                              <td className="px-3 py-2 text-primary/80">{r.constellation}</td>
                              <td className="px-3 py-2 font-mono">{typeof r.radius === 'number' ? r.radius.toFixed(2) : r.radius}</td>
                              <td className="px-3 py-2 text-foreground/70 truncate max-w-[150px]">{r.text}</td>
                           </tr>
                         ))}
                      </tbody>
                   </table>
                </div>
             </div>
           )}

           {/* Downloads */}
           {result.artifacts && (
             <div className="flex gap-2 text-xs">
                {result.artifacts.rel_csv && (
                   <a href={`${API}/download?rel=${encodeURIComponent(result.artifacts.rel_csv)}`} className="px-2 py-1 bg-secondary/40 border border-border/40 rounded hover:bg-secondary/60 transition-colors text-foreground/80">
                      Download CSV
                   </a>
                )}
                {result.artifacts.rel_json && (
                   <a href={`${API}/download?rel=${encodeURIComponent(result.artifacts.rel_json)}`} className="px-2 py-1 bg-secondary/40 border border-border/40 rounded hover:bg-secondary/60 transition-colors text-foreground/80">
                      Download JSON
                   </a>
                )}
             </div>
           )}
        </div>
      )}

      <hr className="my-6 border-border/30" />

      {/* Utilities Grid */}
      <div className="grid grid-cols-1 gap-4">
         {/* Converter */}
         <div>
            <h3 className="text-xs font-semibold mb-2 text-muted-foreground uppercase">Format Conversion</h3>
            <div className="flex items-center gap-2">
               <select 
                  value={convertFormat} 
                  onChange={(e) => setConvertFormat(e.target.value as any)} 
                  className="bg-secondary/30 border border-border/40 rounded-lg text-xs px-2 py-1.5 focus:outline-none"
               >
                  <option value="txt">TXT</option>
                  <option value="docx">DOCX</option>
               </select>
               <button 
                  onClick={convert} 
                  disabled={convertBusy || !artifactId} 
                  className="bg-secondary text-secondary-foreground hover:bg-secondary/80 px-3 py-1.5 rounded-lg text-xs transition-colors disabled:opacity-50"
               >
                  {convertBusy ? 'Converting...' : 'Convert'}
               </button>
               {convertRel && (
                 <a className="text-xs text-primary hover:underline ml-auto" href={`${API}/download?rel=${encodeURIComponent(convertRel)}`}>Download</a>
               )}
            </div>
         </div>
         
         {/* HRM Demo */}
         <div>
            <h3 className="text-xs font-semibold mb-2 text-muted-foreground uppercase flex justify-between">
               <span>HRM Trace</span>
               {hrmSteps!=null && <span className="text-purple-400">Steps: {hrmSteps}</span>}
            </h3>
            <div className="flex gap-2 mb-2">
               <input 
                  className="flex-1 bg-secondary/30 border border-border/40 rounded-lg text-xs px-2 py-1.5 focus:ring-1 focus:ring-purple-500/50 focus:outline-none" 
                  value={hrmDigits} 
                  onChange={e=>setHrmDigits(e.target.value)} 
                  placeholder="Seq..." 
               />
               <button onClick={runHRMDemo} className="bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 border border-purple-500/30 px-3 py-1.5 rounded-lg text-xs transition-colors">
                  Run
               </button>
            </div>
            {hrmTrace && (
               <div className="text-[10px] p-2 rounded-lg bg-black/40 border border-border/40 font-mono text-muted-foreground space-y-0.5 overflow-x-auto">
                 {hrmTrace.map((t,i)=> (
                   <div key={i} className="whitespace-nowrap">
                     <span className={i===0?'text-blue-400':i===hrmTrace.length-1?'text-green-400':'text-purple-400'}>
                        {i===0? 'IN ' : (i===hrmTrace.length-1? 'OUT' : `S${i} `)}
                     </span>
                     {t}
                   </div>
                 ))}
               </div>
            )}
         </div>
      </div>

    </div>
  );
}
