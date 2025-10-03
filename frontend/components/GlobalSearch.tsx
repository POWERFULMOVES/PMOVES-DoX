'use client';

import { useEffect, useRef, useState } from 'react';

type Hit = { score: number; text: string; meta: any };

import { useToast } from '@/components/Toast';
import { getApiBase } from '@/lib/config';

export default function GlobalSearch() {
  const API = getApiBase();
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<Hit[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const timer = useRef<NodeJS.Timeout | null>(null);
  const { push } = useToast();

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (!q.trim()) { setHits([]); setOpen(false); return; }
    timer.current = setTimeout(async () => {
      setLoading(true);
      try {
        const r = await fetch(`${API}/search`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q, k: 8 })});
        if (!r.ok) { setHits([]); setOpen(false); push('Search failed', 'error'); return; }
        const data = await r.json();
        setHits(Array.isArray(data.results) ? data.results : []);
        setOpen(true);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => { if (timer.current) clearTimeout(timer.current); };
  }, [q]);

  return (
    <div className="relative w-full max-w-xl">
      <input
        className="w-full border rounded px-3 py-2"
        placeholder="Search docs, APIs, logs, tags…"
        value={q}
        onChange={e=>setQ(e.target.value)}
      />
      {open && hits.length > 0 && (
        <div className="absolute left-0 right-0 mt-1 bg-white border rounded shadow max-h-80 overflow-auto z-10">
          {hits.map((h, i) => (
            <div key={i} className="px-3 py-2 border-b last:border-b-0">
              <div className="text-xs text-gray-500 flex justify-between">
                <span>{(h.meta?.type || 'text').toUpperCase()}</span>
                <span>{h.score.toFixed(3)}</span>
              </div>
              <div className="text-sm line-clamp-3 whitespace-pre-wrap">{h.text}</div>
              {h.meta?.method && h.meta?.path && (
                <div className="text-xs text-gray-600">{h.meta.method} {h.meta.path}</div>
              )}
            </div>
          ))}
        </div>
      )}
      {loading && <div className="absolute right-2 top-2 text-xs text-gray-400">…</div>}
    </div>
  );
}
