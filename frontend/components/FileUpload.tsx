'use client';

import { useState } from 'react';
import axios from 'axios';
import { useToast } from '@/components/Toast';
import { getApiBase } from '@/lib/config';

interface FileUploadProps {
  onUploadComplete: () => void;
}

export default function FileUpload({ onUploadComplete }: FileUploadProps) {
  const [files, setFiles] = useState<FileList | null>(null);
  const [reportWeek, setReportWeek] = useState('');
  const [webUrls, setWebUrls] = useState('');
  const [asyncPdf, setAsyncPdf] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const API = getApiBase();
  const { push } = useToast();

  const pollTasks = async (taskIds: string[]) => {
    const remaining = new Set(taskIds);
    while (remaining.size > 0) {
      for (const id of Array.from(remaining)) {
        try {
          const res = await fetch(`${API}/tasks/${id}`);
          if (!res.ok) continue;
          const data = await res.json();
          if (data.status === 'completed' || data.status === 'error') {
            remaining.delete(id);
            setResults(prev => prev.map(r => r.task_id === id ? { ...r, ...data } : r));
          }
        } catch {}
      }
      if (remaining.size === 0) break;
      await new Promise(r => setTimeout(r, 1500));
    }
    onUploadComplete();
  };

  const handleUpload = async () => {
    if ((!files || files.length === 0) && !webUrls.trim()) return;

    setUploading(true);
    const formData = new FormData();

    if (files) {
      Array.from(files).forEach(file => {
        formData.append('files', file);
      });
    }

    webUrls
      .split(/\n|,/)
      .map(url => url.trim())
      .filter(url => url.length > 0)
      .forEach(url => formData.append('web_urls', url));

    try {
      const response = await axios.post(
        `${API}/upload?report_week=${encodeURIComponent(reportWeek)}&async_pdf=${asyncPdf}`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );

      const res = response.data.results || [];
      setResults(res);
      const taskIds = res.filter((r: any) => r.status === 'queued' && r.task_id).map((r: any) => r.task_id as string);
      if (taskIds.length > 0) {
        pollTasks(taskIds);
      } else {
        onUploadComplete();
      }
      setFiles(null);
      setWebUrls('');
    } catch (error) {
      console.error('Upload failed:', error);
      push('Upload failed. See console for details.', 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleLoadSamples = async () => {
    setUploading(true);
    try {
      const res = await axios.post(`${API}/load_samples?report_week=${encodeURIComponent(reportWeek)}&async_pdf=${asyncPdf}`);
      const out = res.data.results || [];
      setResults(out);
      const taskIds = out.filter((r: any) => r.status === 'queued' && r.task_id).map((r: any) => r.task_id as string);
      if (taskIds.length > 0) {
        pollTasks(taskIds);
      } else {
        onUploadComplete();
      }
    } catch (e) {
      console.error(e);
      push('Failed to load samples.', 'error');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Upload Documents</h2>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Report Week (optional)</label>
          <input
            type="text"
            placeholder="e.g., 2025-09-22..2025-09-28"
            value={reportWeek}
            onChange={(e) => setReportWeek(e.target.value)}
            className="w-full px-4 py-2 border rounded"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            Select Files (PDF, CSV, XLSX, audio/video, images)
          </label>
          <input
            type="file"
            multiple
            accept=".pdf,.csv,.xlsx,.xls,.mp3,.wav,.m4a,.mp4,.mov,.png,.jpg,.jpeg"
            onChange={(e) => setFiles(e.target.files)}
            className="w-full px-4 py-2 border rounded"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Web URLs (one per line)</label>
          <textarea
            rows={3}
            value={webUrls}
            onChange={(e) => setWebUrls(e.target.value)}
            placeholder="https://example.com/docs"
            className="w-full px-4 py-2 border rounded"
          />
          <p className="text-xs text-gray-500 mt-1">Supports http/https addresses. Pages are rendered with a headless fetch and cleaned to Markdown text.</p>
        </div>

        <div className="flex items-center gap-2">
          <input id="asyncPdf" type="checkbox" checked={asyncPdf} onChange={(e) => setAsyncPdf(e.target.checked)} />
          <label htmlFor="asyncPdf" className="text-sm">Process PDFs asynchronously (faster uploads)</label>
        </div>

        <button
          onClick={handleUpload}
          disabled={uploading || ((!files || files.length === 0) && !webUrls.trim())}
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-gray-300"
        >
          {uploading ? 'Uploading...' : 'Upload & Process'}
        </button>

        <button
          onClick={handleLoadSamples}
          className="w-full bg-purple-600 text-white py-2 rounded hover:bg-purple-700 disabled:bg-gray-300"
          disabled={uploading}
        >
          {uploading ? 'Working...' : 'Load Samples'}
        </button>
      </div>

      {results.length > 0 && (
        <div className="mt-4 space-y-2">
          <h3 className="font-semibold">Upload Results:</h3>
          {results.map((result, idx) => (
            <div
              key={idx}
              className={`p-2 rounded ${result.status === 'success' ? 'bg-green-50' : result.status === 'queued' ? 'bg-yellow-50' : 'bg-red-50'}`}
            >
              <p className="font-medium">{result.filename}</p>
              {result.status === 'success' ? (
                <p className="text-sm text-green-700">
                  ✓ {result.facts_count} facts, {result.evidence_count} evidence
                </p>
              ) : result.status === 'queued' ? (
                <p className="text-sm text-yellow-700">Queued… processing in background</p>
              ) : (
                <p className="text-sm text-red-700">⚠ {result.error}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
