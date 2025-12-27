'use client';

import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { getApiBase } from '@/lib/config';

type DocumentItem = {
  id: string;
  title?: string | null;
  path?: string | null;
};

type EntityRow = {
  id: string;
  label: string;
  text: string;
  page?: number | null;
  context?: string | null;
};

type Props = {
  refreshKey: number;
};

export default function EntitiesPanel({ refreshKey }: Props) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selected, setSelected] = useState<string>('');
  const [entities, setEntities] = useState<EntityRow[]>([]);
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
      setEntities([]);
      setLoading(false);
      return;
    }
    let cancelled = false;
    const loadEntities = async () => {
      setLoading(true);
      setError(null);
      try {
        const API = getApiBase();
        const res = await axios.get(`${API}/analysis/entities`, { params: { document_id: selected } });
        if (!cancelled) {
          setEntities((res.data?.entities || []) as EntityRow[]);
        }
      } catch (err) {
        if (!cancelled) setError('Failed to load entities');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadEntities();
    return () => {
      cancelled = true;
    };
  }, [selected, refreshKey]);

  const grouped = useMemo(() => {
    const out: Record<string, EntityRow[]> = {};
    for (const row of entities) {
      if (!out[row.label]) out[row.label] = [];
      out[row.label].push(row);
    }
    return out;
  }, [entities]);

  return (
    <div className="bg-white p-6 rounded-lg shadow h-full">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-2xl font-semibold">Named Entities</h2>
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
        <p className="text-sm text-gray-500">Loading entities…</p>
      ) : entities.length === 0 ? (
        <p className="text-sm text-gray-500">No entities available.</p>
      ) : (
        <div className="space-y-4 max-h-72 overflow-auto pr-1">
          {Object.entries(grouped).map(([label, rows]) => (
            <div key={label} className="border rounded p-3">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-gray-800">{label}</h3>
                <span className="text-xs text-gray-500">{rows.length} hits</span>
              </div>
              <ul className="space-y-1 text-sm text-gray-700">
                {rows.slice(0, 10).map((row) => (
                  <li key={row.id} className="leading-snug">
                    <span className="font-medium">{row.text}</span>
                    {typeof row.page === 'number' && (
                      <span className="text-xs text-gray-500 ml-2">(p. {row.page})</span>
                    )}
                    {row.context && (
                      <div className="text-xs text-gray-500 mt-1 overflow-hidden text-ellipsis whitespace-nowrap">
                        {row.context}
                      </div>
                    )}
                  </li>
                ))}
                {rows.length > 10 && (
                  <li className="text-xs text-gray-500">+{rows.length - 10} more…</li>
                )}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
