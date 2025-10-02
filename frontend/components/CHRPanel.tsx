'use client';

import { useEffect, useState } from 'react';

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

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Structure (CHR)</h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Artifact ID</label>
          <div className="flex items-center gap-2">
            <select className="flex-1 px-3 py-2 border rounded" value={artifactId} onChange={(e) => setArtifactId(e.target.value)}>
              <option value="">Select an artifact…</option>
              {artifacts.map((a: any) => (
                <option key={a.id} value={a.id}>{a.id} — {a.filename}</option>
              ))}
            </select>
            <input
              className="flex-1 px-3 py-2 border rounded"
              value={artifactId}
              onChange={(e) => setArtifactId(e.target.value)}
              placeholder="Or paste an artifact id"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">K (constellations)</label>
          <input
            type="number"
            className="w-full px-3 py-2 border rounded"
            value={K}
            min={2}
            max={32}
            onChange={(e) => setK(Number(e.target.value))}
          />
        </div>
        <button
          onClick={runCHR}
          disabled={busy || !artifactId}
          className="w-full bg-indigo-600 text-white py-2 rounded hover:bg-indigo-700 disabled:bg-gray-300"
        >
          {busy ? 'Structuring…' : 'Run CHR'}
        </button>
      </div>

      {result && (
        <div className="mt-6 space-y-2">
          <div className="bg-indigo-50 p-3 rounded text-sm">
            <div className="font-semibold">MHEP: {result.mhep?.toFixed?.(1) ?? result.mhep}</div>
            <div>Hg: {result.Hg?.toFixed?.(4) ?? result.Hg} | Hs: {result.Hs?.toFixed?.(4) ?? result.Hs}</div>
            <div>K: {result.K}</div>
          </div>
          {result.artifacts?.rel_plot && (
            <div>
              <img src={`${API}/download?rel=${encodeURIComponent(result.artifacts.rel_plot)}`} alt="CHR PCA" className="border rounded" />
            </div>
          )}
          {Array.isArray(result.preview_rows) && result.preview_rows.length > 0 && (
            <div className="text-sm">
              <div className="font-semibold mb-1">Preview (top {result.preview_rows.length}):</div>
              <div className="max-h-64 overflow-auto border rounded">
                <table className="min-w-full text-left text-xs">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-2 py-1">Idx</th>
                      <th className="px-2 py-1">Constellation</th>
                      <th className="px-2 py-1">Radius</th>
                      <th className="px-2 py-1">Text</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.preview_rows.map((r: any, i: number) => (
                      <tr key={i} className="border-t">
                        <td className="px-2 py-1">{r.idx}</td>
                        <td className="px-2 py-1">{r.constellation}</td>
                        <td className="px-2 py-1">{typeof r.radius === 'number' ? r.radius.toFixed(3) : r.radius}</td>
                        <td className="px-2 py-1">{r.text}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          {result.artifacts && (
            <div className="text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium">CSV:</span>
                {result.artifacts.rel_csv ? (
                  <a className="text-blue-600 hover:underline" href={`${API}/download?rel=${encodeURIComponent(result.artifacts.rel_csv)}`}>Download</a>
                ) : (
                  <span>{result.artifacts.csv}</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium">JSON:</span>
                {result.artifacts.rel_json ? (
                  <a className="text-blue-600 hover:underline" href={`${API}/download?rel=${encodeURIComponent(result.artifacts.rel_json)}`}>Download</a>
                ) : (
                  <span>{result.artifacts.json}</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-8">
        <h3 className="text-lg font-semibold mb-2">Convert Artifact</h3>
        <div className="flex items-center gap-2 mb-2">
          <select value={convertFormat} onChange={(e) => setConvertFormat(e.target.value as any)} className="border rounded px-2 py-1">
            <option value="txt">TXT</option>
            <option value="docx">DOCX</option>
          </select>
          <button onClick={convert} disabled={convertBusy || !artifactId} className="bg-gray-700 text-white px-3 py-1 rounded disabled:bg-gray-300">
            {convertBusy ? 'Converting…' : 'Convert'}
          </button>
          {convertRel && (
            <a className="text-blue-600 hover:underline" href={`${API}/download?rel=${encodeURIComponent(convertRel)}`}>Download</a>
          )}
        </div>
      </div>

      <div className="mt-6">
        <h3 className="text-lg font-semibold mb-2">Build datavzrd Dashboard</h3>
        <div className="flex items-center gap-2 mb-2">
          <button onClick={buildViz} disabled={vizBusy || !artifactId} className="bg-green-600 text-white px-3 py-1 rounded disabled:bg-gray-300">
            {vizBusy ? 'Building…' : 'Generate datavzrd project'}
          </button>
          {vizRel && (
            <span className="text-xs text-gray-600">viz.yaml: {vizRel}</span>
          )}
        </div>
        <p className="text-xs text-gray-600">Use datavzrd CLI to serve: <code>datavzrd serve artifacts/datavzrd/&lt;stem&gt;/viz.yaml</code></p>
      </div>
    </div>
  );
}
