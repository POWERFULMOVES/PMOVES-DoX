'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import { getApiBase } from '@/lib/config';

type DocumentItem = {
  id: string;
  title?: string | null;
  path?: string | null;
};

type MetricHit = {
  id: string;
  type: string;
  value?: string | null;
  context?: string | null;
  page?: number | null;
};

type Props = {
  refreshKey: number;
};

export default function MetricHitsPanel({ refreshKey }: Props) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selected, setSelected] = useState<string>('');
  const [hits, setHits] = useState<MetricHit[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadDocuments = async () => {
      try {
        const API = getApiBase();
        const res = await axios.get(`${API}/documents`, { params: { type: 'pdf' } });
        const docs = (res.data?.documents || []) as DocumentItem[];
        setDocuments(docs);
        if (docs.length > 0) {
          setSelected((prev) => (prev && docs.some((d) => d.id === prev) ? prev : docs[0].id));
        } else {
          setSelected('');
        }
      } catch (err) {
        setError('Failed to load documents');
      }
    };
    loadDocuments();
  }, [refreshKey]);

  useEffect(() => {
    if (!selected) {
      setHits([]);
      setLoading(false);
      return;
    }
    let cancelled = false;
    const loadHits = async () => {
      setLoading(true);
      setError(null);
      try {
        const API = getApiBase();
        const res = await axios.get(`${API}/analysis/metrics`, { params: { document_id: selected } });
        if (!cancelled) {
          setHits((res.data?.metric_hits || []) as MetricHit[]);
        }
      } catch (err) {
        if (!cancelled) setError('Failed to load metric hits');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadHits();
    return () => {
      cancelled = true;
    };
  }, [selected, refreshKey]);

  return (
    <div className="bg-white p-6 rounded-lg shadow h-full">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-2xl font-semibold">Metric Signals</h2>
        <select
          className="border rounded px-2 py-1 text-sm"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          {documents.map((doc) => (
            <option key={doc.id} value={doc.id}>
              {doc.title || doc.path || doc.id}
            </option>
          ))}
          {documents.length === 0 && <option value="">No PDF documents</option>}
        </select>
      </div>
      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
      {loading ? (
        <p className="text-sm text-gray-500">Loading metrics…</p>
      ) : hits.length === 0 ? (
        <p className="text-sm text-gray-500">No metric patterns found.</p>
      ) : (
        <ul className="space-y-3 max-h-72 overflow-auto pr-1 text-sm text-gray-700">
          {hits.map((hit) => (
            <li key={hit.id} className="border rounded p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold uppercase text-gray-600">{hit.type}</span>
                {hit.page != null && <span className="text-xs text-gray-500">p. {hit.page}</span>}
              </div>
              {hit.value && <div className="text-lg font-semibold text-gray-900">{hit.value}</div>}
              {hit.context && (
                <div className="text-xs text-gray-500 mt-1 whitespace-pre-wrap break-words">{hit.context}</div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
