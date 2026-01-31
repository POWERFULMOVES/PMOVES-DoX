'use client';

import { useEffect, useState, useRef } from 'react';
import { api } from '@/lib/api';
import { getHRMEnabled, getHRMMmax, getHRMMmin } from '@/lib/config';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Send, Sparkles, Bot, User, BookOpen, Layers, Image as ImageIcon, Table as TableIcon, FileText, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export default function QAInterface() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [hrmOn, setHrmOn] = useState(false);
  const [hrmMmax, setHrmMmax] = useState<number>(6);
  const [hrmMmin, setHrmMmin] = useState<number>(2);
  const inputRef = useRef<HTMLInputElement>(null);

  // initialize HRM view-only params
  useEffect(()=>{
    try { setHrmOn(getHRMEnabled()); setHrmMmax(getHRMMmax()); setHrmMmin(getHRMMmin()); } catch {}
  }, []);

  const handleAsk = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setAnswer(null); 
    try {
      const useHrm = getHRMEnabled();
      const data = await api.askQuestion(question, useHrm);
      setAnswer(data);
    } catch (error) {
      console.error('Question failed:', error);
      setAnswer({ error: "Failed to get an answer. Please check the backend connection." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="glass-card overflow-hidden flex flex-col h-full min-h-[500px]">
      <CardHeader className="bg-gradient-to-r from-card to-card/50 border-b border-border/40 pb-4">
        <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    <Sparkles className="h-5 w-5" />
                </div>
                <div>
                    <CardTitle className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-400">
                        Ask Intelligence
                    </CardTitle>
                    {hrmOn && (
                       <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                          HRM Active (Mmax:{hrmMmax}, Mmin:{hrmMmin})
                       </p>
                    )}
                </div>
            </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0">
         <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {!answer && !loading && (
               <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground opacity-60">
                  <Bot className="h-12 w-12 mb-4" />
                  <p>Ask a question to query your knowledge base.</p>
                  <p className="text-xs mt-2 max-w-xs">
                     Try "What is the revenue trend?" or "Summarize the key risks."
                  </p>
               </div>
            )}

            {/* Loading State */}
            {loading && (
               <div className="space-y-4 animate-in fade-in duration-500">
                  <div className="flex justify-end">
                     <div className="bg-primary/20 text-primary px-4 py-3 rounded-2xl rounded-tr-none max-w-[80%] backdrop-blur-sm">
                        <p className="text-sm font-medium">{question}</p>
                     </div>
                     <div className="ml-3 p-2 bg-primary/10 rounded-full h-fit">
                        <User className="h-4 w-4 text-primary" />
                     </div>
                  </div>
                  
                  <div className="flex justify-start">
                     <div className="mr-3 p-2 bg-secondary/50 rounded-full h-fit">
                        <Bot className="h-4 w-4 text-secondary-foreground" />
                     </div>
                     <div className="flex items-center gap-2 text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span className="text-sm animate-pulse">Thinking...</span>
                     </div>
                  </div>
               </div>
            )}

            {/* Answer Display */}
            {answer && !loading && (
               <div className="space-y-6 animate-in slide-in-from-bottom-2 duration-500">
                  {/* User Question Bubble */}
                  <div className="flex justify-end">
                     <div className="bg-primary/20 text-primary px-4 py-3 rounded-2xl rounded-tr-none max-w-[80%] backdrop-blur-sm shadow-sm border border-primary/5">
                        <p className="text-sm font-medium">{question}</p>
                     </div>
                     <div className="ml-3 p-2 bg-primary/10 rounded-full h-fit self-end mb-1">
                        <User className="h-4 w-4 text-primary" />
                     </div>
                  </div>

                  {/* AI Answer Bubble */}
                  <div className="flex justify-start">
                     <div className="mr-3 p-2 bg-secondary/50 rounded-full h-fit self-start mt-1">
                        <Bot className="h-4 w-4 text-secondary-foreground" />
                     </div>
                     <div className="flex-1 space-y-4">
                        <div className="bg-card border border-border/50 text-card-foreground p-5 rounded-2xl rounded-tl-none shadow-md backdrop-blur-md">
                           {answer.error ? (
                              <p className="text-red-400 text-sm">{answer.error}</p>
                           ) : (
                              <>
                                 <div className="flex items-center justify-between mb-3 border-b border-border/30 pb-2">
                                    <span className="text-xs font-bold uppercase text-muted-foreground tracking-wider flex items-center gap-1">
                                       <Sparkles className="w-3 h-3 text-yellow-500" /> Answer
                                    </span>
                                    {answer?.hrm?.enabled && (typeof answer?.hrm?.steps === 'number') && (
                                       <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono" title="HRM refinement steps">
                                          HRM Steps: {answer.hrm.steps}
                                       </span>
                                    )}
                                 </div>
                                 <div className="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed text-gray-200">
                                    <pre className="whitespace-pre-wrap font-sans">{answer.answer}</pre>
                                 </div>
                              </>
                           )}
                        </div>

                        {/* Citations / Evidence */}
                        {answer.evidence && answer.evidence.length > 0 && (
                           <div className="mt-4 space-y-3">
                              <h4 className="text-xs font-semibold uppercase text-muted-foreground flex items-center gap-2 pl-1">
                                 <BookOpen className="w-3 h-3" /> Sources Considered
                              </h4>
                              <div className="grid grid-cols-1 gap-2">
                                 {answer.evidence.map((ev: any, idx: number) => {
                                    const type = (ev.content_type || '').toString().toLowerCase();
                                    const isFigure = type === 'figure' || type === 'chart';
                                    const isTable = type === 'table' || type === 'financial_table';
                                    const page = ev?.coordinates?.page;
                                    
                                    return (
                                       <div key={idx} className="group flex flex-col bg-secondary/20 hover:bg-secondary/30 border border-border/30 rounded-lg p-3 transition-all text-sm">
                                          <div className="flex items-center justify-between mb-1.5">
                                             <div className="flex items-center gap-2">
                                                {isFigure ? <ImageIcon className="w-3.5 h-3.5 text-orange-400" /> : 
                                                 isTable ? <TableIcon className="w-3.5 h-3.5 text-emerald-400" /> : 
                                                 <FileText className="w-3.5 h-3.5 text-blue-400" />}
                                                <span className="font-medium text-xs text-primary/80 font-mono truncate max-w-[150px]">{ev.locator}</span>
                                             </div>
                                             <div className="flex gap-1.5">
                                                {ev.vlm && (
                                                   <span className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">VLM</span>
                                                )}
                                                {page !== undefined && (
                                                   <span className="text-[9px] px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground">Pg {page}</span>
                                                )}
                                             </div>
                                          </div>
                                          <p className="text-muted-foreground text-xs line-clamp-2 leading-relaxed bg-background/20 p-2 rounded border border-white/5 font-mono opacity-80 group-hover:opacity-100">
                                             {(ev.preview || '').substring(0, 150)}...
                                          </p>
                                       </div>
                                    );
                                 })}
                              </div>
                           </div>
                        )}
                     </div>
                  </div>
               </div>
            )}
         </div>

         {/* Input Area */}
         <div className="p-4 bg-card/60 border-t border-border/40 backdrop-blur-xl">
            <div className="relative flex items-center">
               <input
                  ref={inputRef}
                  type="text"
                  placeholder="Ask a question about your documents..."
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleAsk(); }}
                  className="w-full pl-4 pr-12 py-3 bg-secondary/30 border border-border/50 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm placeholder:text-muted-foreground/60 transition-all"
                  disabled={loading}
               />
               <button
                  onClick={handleAsk}
                  disabled={loading || !question.trim()}
                  className="absolute right-2 p-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
               >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
               </button>
            </div>
            <div className="text-[10px] text-muted-foreground text-center mt-2 opacity-60">
               {hrmOn ? "Powered by Hierarchical Reasoning Model" : "Standard Retrieval Augmented Generation"}
            </div>
         </div>
      </CardContent>
    </Card>
  );
}
