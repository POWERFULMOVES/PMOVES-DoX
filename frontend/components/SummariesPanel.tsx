'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useToast } from '@/components/Toast';

type SummaryStyle = 'bullet' | 'executive' | 'action_items';
type SummaryScope = 'workspace' | 'artifact';

type SummaryRecord = {
  id: string;
  style: SummaryStyle;
  provider: string;
  prompt: string;
  scope: {
    type: SummaryScope;
    key: string;
    artifact_ids: string[];
  };
  summary: string;
  citations: Array<Record<string, any>>;
  created_at: string;
};

type ArtifactRow = {
  id: string;
  filename: string;
  filetype: string;
};

const STYLE_LABELS: Record<SummaryStyle, string> = {
  bullet: 'Bullet Brief',
  executive: 'Executive Summary',
  action_items: 'Action Items',
};

export default function SummariesPanel() {
  const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
  const { push } = useToast();
  const [style, setStyle] = useState<SummaryStyle>('bullet');
  const [scope, setScope] = useState<SummaryScope>('workspace');
  const [artifacts, setArtifacts] = useState<ArtifactRow[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [summary, setSummary] = useState<SummaryRecord | null>(null);
  const [history, setHistory] = useState<SummaryRecord[]>([]);
  const [loading, setLoading] = useState(false);

  const scopeKey = useMemo(() => {
    if (scope === 'workspace') return 'workspace';
    return `artifact:${[...selected].sort().join(',')}`;
  }, [scope, selected]);

  const loadArtifacts = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/artifacts`);
      if (!resp.ok) return;
      const data = await resp.json();
      const rows = Array.isArray(data?.artifacts) ? data.artifacts : [];
      setArtifacts(rows.map((row: any) => ({ id: String(row.id), filename: row.filename, filetype: row.filetype })));
    } catch {
      // ignore fetch errors for now
    }
  }, [API]);

  const loadHistory = useCallback(async () => {
    if (scope === 'artifact' && selected.length === 0) {
      setHistory([]);
      return;
    }
    const params = new URLSearchParams();
    params.append('style', style);
    if (scope === 'artifact') {
      params.append('scope', 'artifact');
    }
    try {
      const resp = await fetch(`${API}/summaries?${params.toString()}`);
      if (!resp.ok) return;
      const data = await resp.json();
      const items: SummaryRecord[] = Array.isArray(data?.summaries) ? data.summaries : [];
      const filtered = items.filter((item) => item.scope?.key === scopeKey);
      setHistory(filtered.slice(0, 5));
      if (filtered.length > 0) {
        setSummary((current) => current ?? filtered[0]);
      }
    } catch {
      // ignore errors during history fetch
    }
  }, [API, scope, selected, scopeKey, style]);

  useEffect(() => {
    loadArtifacts();
  }, [loadArtifacts]);

  useEffect(() => {
    if (scope === 'workspace') {
      setSelected([]);
    }
  }, [scope]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const toggleArtifact = (id: string) => {
    setSelected((prev) => {
      if (prev.includes(id)) {
        return prev.filter((item) => item !== id);
      }
      return [...prev, id];
    });
  };

  const requestSummary = async (forceRefresh = false) => {
    if (scope === 'artifact' && selected.length === 0) {
      push('Select at least one artifact to summarize.', 'error');
      return;
    }
    setLoading(true);
    try {
      const body: any = {
        style,
        scope,
        force_refresh: forceRefresh,
      };
      if (scope === 'artifact') {
        body.artifact_ids = [...selected];
      }
      const resp = await fetch(`${API}/summaries/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const payload = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const detail = payload?.detail || 'Unable to generate summary.';
        push(detail, 'error');
        return;
      }
      setSummary(payload as SummaryRecord);
      push('Summary ready.', 'success');
      loadHistory();
    } catch {
      push('Summary request failed.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">Summaries</h2>
        <div className="flex gap-2">
          {(Object.keys(STYLE_LABELS) as SummaryStyle[]).map((key) => (
            <button
              key={key}
              onClick={() => { setStyle(key); setSummary(null); }}
              className={`px-3 py-1 rounded border text-sm ${style === key ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700'}`}
            >
              {STYLE_LABELS[key]}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-3 flex gap-2 text-sm">
        {(['workspace', 'artifact'] as SummaryScope[]).map((option) => (
          <button
            key={option}
            onClick={() => { setScope(option); setSummary(null); }}
            className={`px-3 py-1 rounded border ${scope === option ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-700'}`}
          >
            {option === 'workspace' ? 'Workspace' : 'Selected Artifacts'}
          </button>
        ))}
      </div>

      {scope === 'artifact' && (
        <div className="mb-4">
          <div className="text-xs text-gray-600 mb-1">Choose artifacts to summarize:</div>
          <div className="border rounded p-2 max-h-32 overflow-auto space-y-1 text-sm">
            {artifacts.length === 0 && <div className="text-gray-500">No artifacts available yet.</div>}
            {artifacts.map((art) => (
              <label key={art.id} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selected.includes(art.id)}
                  onChange={() => toggleArtifact(art.id)}
                />
                <span className="truncate" title={art.filename}>{art.filename}</span>
                <span className="text-xs text-gray-500">{art.filetype}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => requestSummary(false)}
          disabled={loading}
          className="px-4 py-1 rounded bg-blue-600 text-white text-sm disabled:opacity-50"
        >
          {loading ? 'Generating…' : 'Generate'}
        </button>
        <button
          onClick={() => requestSummary(true)}
          disabled={loading}
          className="px-4 py-1 rounded border text-sm"
        >
          Re-run
        </button>
      </div>

      <div className="flex-1 overflow-auto border rounded p-3 bg-gray-50">
        {summary ? (
          <div className="space-y-3 text-sm">
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>{STYLE_LABELS[summary.style]}</span>
              <span>•</span>
              <span>Provider: {summary.provider || 'heuristic'}</span>
              <span>•</span>
              <span>{new Date(summary.created_at).toLocaleString()}</span>
            </div>
            <pre className="whitespace-pre-wrap font-sans text-sm text-gray-800">{summary.summary}</pre>
            {summary.citations && summary.citations.length > 0 && (
              <div>
                <div className="font-semibold text-xs text-gray-600 mb-1">Citations</div>
                <ul className="list-disc list-inside text-xs text-gray-700 space-y-1">
                  {summary.citations.map((cite) => (
                    <li key={cite.id}>
                      <span className="font-medium">{cite.locator || cite.id}</span>
                      {cite.preview && <span className="ml-1 text-gray-500">— {cite.preview}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="text-sm text-gray-500">No summary generated yet. Request one to see results here.</div>
        )}
      </div>

      {history.length > 0 && (
        <div className="mt-4">
          <div className="text-xs font-semibold text-gray-600 mb-2">Recent runs</div>
          <div className="space-y-2">
            {history.map((item) => (
              <button
                key={item.id}
                onClick={() => setSummary(item)}
                className={`w-full text-left text-xs px-2 py-2 rounded border ${summary?.id === item.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white'}`}
              >
                <div className="flex items-center justify-between">
                  <span>{new Date(item.created_at).toLocaleString()}</span>
                  <span className="text-gray-500">{item.provider || 'heuristic'}</span>
                </div>
                <div className="text-gray-600 mt-1 max-h-12 overflow-hidden">{item.summary}</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
