'use client';

import { useEffect, useState } from 'react';
import { getApiBase } from '@/lib/config';

interface MediaEvidence {
  artifact_id?: string;
  artifact?: { id?: string; filename?: string; filetype?: string };
  locator?: string;
  preview?: string;
  content_type?: string;
  full_data?: any;
}

interface MediaSummaryResponse {
  transcripts: MediaEvidence[];
  media_metadata: MediaEvidence[];
  web_pages: MediaEvidence[];
  image_text: MediaEvidence[];
}

const initialSummary: MediaSummaryResponse = {
  transcripts: [],
  media_metadata: [],
  web_pages: [],
  image_text: [],
};

export default function MediaArtifactsPanel() {
  const [summary, setSummary] = useState<MediaSummaryResponse>(initialSummary);
  const [loading, setLoading] = useState(false);
  const API = getApiBase();

  const load = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/artifacts/media`);
      if (!res.ok) return;
      const data = await res.json();
      setSummary({
        transcripts: Array.isArray(data.transcripts) ? data.transcripts : [],
        media_metadata: Array.isArray(data.media_metadata) ? data.media_metadata : [],
        web_pages: Array.isArray(data.web_pages) ? data.web_pages : [],
        image_text: Array.isArray(data.image_text) ? data.image_text : [],
      });
    } catch (err) {
      console.error('Failed to load media artifacts', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const renderList = (items: MediaEvidence[], empty: string, max = 5) => {
    if (!items || items.length === 0) return <p className="text-xs text-gray-500">{empty}</p>;
    return (
      <ul className="space-y-2">
        {items.slice(0, max).map((item, idx) => (
          <li key={`${item.artifact_id}-${idx}`} className="text-xs border rounded p-2 bg-gray-50">
            <div className="font-semibold text-gray-700 truncate">
              {item.artifact?.filename || item.locator || 'Unknown artifact'}
            </div>
            {item.preview && (
              <div className="text-gray-600 whitespace-pre-wrap mt-1 max-h-24 overflow-hidden">
                {item.preview}
              </div>
            )}
          </li>
        ))}
      </ul>
    );
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">Media Insights</h2>
        <button
          onClick={load}
          className="text-sm px-3 py-1 border rounded text-blue-600 border-blue-300 hover:bg-blue-50"
          disabled={loading}
        >
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h3 className="font-semibold text-gray-800 mb-2">Transcripts</h3>
          <p className="text-xs text-gray-500 mb-2">Audio and video transcripts captured during ingestion.</p>
          {renderList(summary.transcripts, 'No transcripts captured yet.')}
        </div>
        <div>
          <h3 className="font-semibold text-gray-800 mb-2">Media Metadata</h3>
          <p className="text-xs text-gray-500 mb-2">Duration, codecs, and additional context extracted from media files.</p>
          {renderList(summary.media_metadata, 'No media metadata available.')}
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <div>
          <h3 className="font-semibold text-gray-800 mb-2">Web Snapshots</h3>
          <p className="text-xs text-gray-500 mb-2">Rendered and cleaned content from submitted URLs.</p>
          {renderList(summary.web_pages, 'No web pages ingested yet.')}
        </div>
        <div>
          <h3 className="font-semibold text-gray-800 mb-2">Image OCR</h3>
          <p className="text-xs text-gray-500 mb-2">Text extracted from uploaded screenshots or documents.</p>
          {renderList(summary.image_text, 'No OCR text available yet.')}
        </div>
      </div>
    </div>
  );
}
