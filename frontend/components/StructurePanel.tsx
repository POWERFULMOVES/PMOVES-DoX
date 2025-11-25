'use client';

import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { getApiBase } from '@/lib/config';

type DocumentItem = {
  id: string;
  title?: string | null;
  path?: string | null;
};

type SectionNode = {
  level: number;
  title: string;
  content?: string[];
  subsections?: SectionNode[];
};

type StructurePayload = {
  title?: string;
  sections?: SectionNode[];
};

type Props = {
  refreshKey: number;
};

export default function StructurePanel({ refreshKey }: Props) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selected, setSelected] = useState<string>('');
  const [structure, setStructure] = useState<StructurePayload | null>(null);
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
      setStructure(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    const loadStructure = async () => {
      setLoading(true);
      setError(null);
      try {
        const API = getApiBase();
        const res = await axios.get(`${API}/analysis/structure`, { params: { document_id: selected } });
        if (!cancelled) {
          setStructure((res.data?.structure || null) as StructurePayload | null);
        }
      } catch (err) {
        if (!cancelled) setError('Failed to load structure');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadStructure();
    return () => {
      cancelled = true;
    };
  }, [selected, refreshKey]);

  const hasSections = useMemo(() => (structure?.sections || []).length > 0, [structure]);

  const renderSection = (section: SectionNode, depth = 0) => (
    <li
      key={`${section.title}-${depth}`}
      className="mb-2"
      style={{ paddingLeft: `${Math.min(depth, 4) * 12}px` }}
    >
      <div className="font-semibold text-gray-800">{section.title}</div>
      {section.content && section.content.length > 0 && (
        <ul className="text-sm text-gray-600 list-disc ml-4 mt-1">
          {section.content.slice(0, 3).map((para, idx) => (
            <li key={idx} className="truncate" title={para}>
              {para}
            </li>
          ))}
          {section.content.length > 3 && (
            <li className="text-xs text-gray-400">+{section.content.length - 3} more paragraphs</li>
          )}
        </ul>
      )}
      {section.subsections && section.subsections.length > 0 && (
        <ul className="mt-2 space-y-2 border-l border-gray-200 pl-4">
          {section.subsections.map((sub) => renderSection(sub, depth + 1))}
        </ul>
      )}
    </li>
  );

  return (
    <div className="bg-white p-6 rounded-lg shadow h-full">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-2xl font-semibold">Document Structure</h2>
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
        <p className="text-sm text-gray-500">Loading structure…</p>
      ) : !structure ? (
        <p className="text-sm text-gray-500">No structure stored for this document yet.</p>
      ) : !hasSections ? (
        <div>
          <h3 className="text-lg font-medium text-gray-800">{structure.title || 'Untitled'}</h3>
          <p className="text-sm text-gray-500 mt-1">No headings were detected.</p>
        </div>
      ) : (
        <div className="max-h-72 overflow-auto pr-1">
          <h3 className="text-lg font-medium text-gray-800 mb-2">{structure.title || 'Untitled'}</h3>
          <ul className="space-y-2">
            {(structure.sections || []).map((section) => renderSection(section, 1))}
          </ul>
        </div>
      )}
    </div>
  );
}
