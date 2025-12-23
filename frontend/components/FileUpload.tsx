'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/components/Toast';
import { getApiBase } from '@/lib/config';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Upload, FileText, CheckCircle, AlertTriangle, Loader2, Link as LinkIcon, RefreshCw, File } from "lucide-react";
import { cn } from "@/lib/utils";

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
    try {
      const fileArray = files ? Array.from(files) : null;
      const data = await api.uploadFiles(fileArray, webUrls, reportWeek, asyncPdf);

      const res = data.results || [];
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
      const data = await api.loadSamples(reportWeek, asyncPdf);
      const out = data.results || [];
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
    <Card className="glass-card h-full min-h-[500px] flex flex-col">
      <CardHeader className="bg-gradient-to-r from-card to-card/50 border-b border-border/40 pb-4">
        <CardTitle className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-400 text-lg font-bold flex items-center gap-2">
           <Upload className="text-blue-400 h-5 w-5" />
           Document Ingestion
        </CardTitle>
        <CardDescription>
           Upload financial reports, statements, or paste URLs for processing.
        </CardDescription>
      </CardHeader>
      
      <CardContent className="p-6 space-y-6 flex-1 overflow-y-auto">
        {/* Upload Zone */}
        <div className="space-y-4">
           {/* Week Selector */}
           <div>
              <label className="text-xs font-semibold uppercase text-muted-foreground mb-1 block pl-1">Target Period (Optional)</label>
              <input
                type="text"
                placeholder="YYYY-W## or Custom Range"
                value={reportWeek}
                onChange={(e) => setReportWeek(e.target.value)}
                className="w-full px-4 py-2 bg-secondary/20 border border-border/50 rounded-lg text-sm focus:ring-2 focus:ring-primary/50 outline-none transition-all placeholder:text-muted-foreground/40"
              />
           </div>

           {/* File Drop Area Concept */}
           <div className="relative group">
              <input
                type="file"
                multiple
                accept=".pdf,.csv,.xlsx,.xls,.mp3,.wav,.m4a,.mp4,.mov,.png,.jpg,.jpeg"
                onChange={(e) => setFiles(e.target.files)}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
              />
              <div className="border-2 border-dashed border-primary/20 bg-primary/5 rounded-xl p-8 text-center group-hover:bg-primary/10 group-hover:border-primary/40 transition-all duration-300">
                 <div className="mx-auto w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mb-3 text-primary group-hover:scale-110 transition-transform">
                    {files && files.length > 0 ? <CheckCircle className="w-6 h-6" /> : <Upload className="w-6 h-6" />}
                 </div>
                 {files && files.length > 0 ? (
                    <div>
                       <p className="font-medium text-foreground">{files.length} files selected</p>
                       <p className="text-xs text-muted-foreground mt-1">Click to change selection</p>
                    </div>
                 ) : (
                    <div>
                        <p className="font-medium text-primary">Drag & Drop or Click to Upload</p>
                        <p className="text-xs text-muted-foreground mt-2 max-w-[200px] mx-auto">
                           Supports PDF, Excel, Media, and Images
                        </p>
                    </div>
                 ) }
              </div>
           </div>

           {/* URL Input */}
           <div>
              <div className="flex items-center gap-2 mb-1.5 pl-1">
                 <LinkIcon className="w-3 h-3 text-muted-foreground" />
                 <label className="text-xs font-semibold uppercase text-muted-foreground block">Web URLs</label>
              </div>
              <textarea
                rows={2}
                value={webUrls}
                onChange={(e) => setWebUrls(e.target.value)}
                placeholder="https://example.com/report1&#10;https://example.com/report2"
                className="w-full px-4 py-3 bg-secondary/20 border border-border/50 rounded-lg text-sm focus:ring-2 focus:ring-primary/50 outline-none transition-all placeholder:text-muted-foreground/40 resize-none font-mono text-xs"
              />
           </div>

           {/* Options */}
           <div className="flex items-center gap-2 pl-1">
              <div className="relative flex items-center">
                 <input 
                    id="asyncPdf" 
                    type="checkbox" 
                    checked={asyncPdf} 
                    onChange={(e) => setAsyncPdf(e.target.checked)} 
                    className="checkbox-accent w-4 h-4 rounded border-gray-500 text-primary focus:ring-primary bg-secondary/50"
                 />
                 <label htmlFor="asyncPdf" className="ml-2 text-sm text-muted-foreground cursor-pointer select-none">
                    Async Processing (Background Tasks)
                 </label>
              </div>
           </div>
           
           {/* Actions */}
           <div className="flex gap-3 pt-2">
               <button
                 onClick={handleUpload}
                 disabled={uploading || ((!files || files.length === 0) && !webUrls.trim())}
                 className="flex-1 bg-gradient-to-r from-primary to-purple-600 hover:from-primary/90 hover:to-purple-700 text-white font-medium py-2.5 rounded-lg shadow-lg shadow-primary/25 disabled:opacity-50 disabled:shadow-none transition-all active:scale-[0.98] flex items-center justify-center gap-2"
               >
                 {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                 {uploading ? 'Processing...' : 'Start Ingestion'}
               </button>

               <button
                 onClick={handleLoadSamples}
                 className="px-4 py-2.5 bg-secondary hover:bg-secondary/80 text-secondary-foreground font-medium rounded-lg border border-white/5 transition-colors text-sm flex items-center gap-2"
                 disabled={uploading}
                 title="Load standard sample dataset"
               >
                 <RefreshCw className={cn("w-4 h-4", uploading && "animate-spin")} />
               </button>
           </div>
        </div>

        {/* Results List */}
        {results.length > 0 && (
          <div className="space-y-3 pt-4 border-t border-border/30 animate-in slide-in-from-bottom-2">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider pl-1">Processing Status</h3>
            <div className="space-y-2 max-h-[150px] overflow-y-auto pr-1">
              {results.map((result, idx) => (
                <div
                  key={idx}
                  className={cn(
                     "p-3 rounded-lg border flex items-start gap-3 transition-colors",
                     result.status === 'success' ? "bg-emerald-500/10 border-emerald-500/20" :
                     result.status === 'queued' ? "bg-yellow-500/10 border-yellow-500/20" :
                     "bg-destructive/10 border-destructive/20"
                  )}
                >
                   <div className="mt-0.5">
                      {result.status === 'success' ? <CheckCircle className="w-4 h-4 text-emerald-500" /> :
                       result.status === 'queued' ? <Loader2 className="w-4 h-4 text-yellow-500 animate-spin" /> :
                       <AlertTriangle className="w-4 h-4 text-destructive" />
                      }
                   </div>
                   <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate text-foreground">{result.filename}</p>
                      {result.status === 'success' ? (
                        <p className="text-xs text-emerald-500/80 mt-0.5">
                          Processed {result.facts_count} facts, {result.evidence_count} items
                        </p>
                      ) : result.status === 'queued' ? (
                        <p className="text-xs text-yellow-500/80 mt-0.5">Processing in pipeline ID: {result.task_id}</p>
                      ) : (
                        <p className="text-xs text-destructive/80 mt-0.5">{result.error}</p>
                      )}
                   </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
