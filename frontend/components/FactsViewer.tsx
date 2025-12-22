'use client';

import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Loader2, TrendingUp, DollarSign, Activity, FileText } from "lucide-react";

/**
 * FactsViewer Component
 * 
 * Displays extracted intelligence from processed documents.
 * Features two main sections:
 * 1. Extracted Facts: Key-value metrics and entities found in text.
 * 2. Financial Statements: Structured tables identified as financial data (tables, balance sheets, etc.).
 * 
 * Auto-refreshes data every 3 seconds.
 */
export default function FactsViewer() {
  const [facts, setFacts] = useState<any[]>([]);
  const [financials, setFinancials] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadFacts();
    // Auto-refresh periodically
    timerRef.current = setInterval(() => loadFacts(true), 3000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const loadFacts = async (silent = false) => {
    try {
      const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
      const [factsResponse, financialsResponse] = await Promise.all([
        axios.get(`${API}/facts`),
        axios.get(`${API}/analysis/financials`),
      ]);
      setFacts(factsResponse.data.facts);
      setFinancials(financialsResponse.data.statements || []);
    } catch (error) {
      if (!silent) console.error('Failed to load facts:', error);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Loading intelligence...</span>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Extracted Facts Section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-purple-600">
            Extracted Facts
          </h2>
          <span className="text-xs font-mono px-2 py-1 rounded-full bg-primary/10 text-primary border border-primary/20">
            {facts.length} items
          </span>
        </div>

        {facts.length === 0 ? (
          <Card className="glass-card border-dashed border-2">
            <CardContent className="flex flex-col items-center justify-center p-8 text-muted-foreground">
              <Activity className="h-10 w-10 mb-2 opacity-50" />
              <p>No facts extracted yet.</p>
              <p className="text-sm">Upload a document to begin analysis.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {facts.map((fact, idx) => (
              <Card key={idx} className="glass-card hover:bg-card/80 transition-colors">
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-start">
                    <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                      {fact.entity || 'General'}
                    </CardTitle>
                    {fact.report_week && (
                      <span className="text-[10px] bg-secondary px-1.5 py-0.5 rounded text-secondary-foreground">
                        {fact.report_week}
                      </span>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {Object.entries(fact.metrics || {}).map(([key, value]: [string, any]) => (
                      <div key={key} className="flex justify-between items-center text-sm border-b border-border/50 last:border-0 pb-1 last:pb-0">
                        <span className="capitalize text-muted-foreground flex items-center gap-1">
                           {key.includes('revenue') || key.includes('spend') ? <DollarSign className="w-3 h-3" /> : <TrendingUp className="w-3 h-3" />}
                           {key}
                        </span>
                        <span className="font-semibold font-mono text-foreground">
                          {typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>
      
      {/* Financial Statements Section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-cyan-400">
            Financial Statements
          </h2>
          <span className="text-xs font-mono px-2 py-1 rounded-full bg-secondary text-secondary-foreground">
            {financials.length} detected
          </span>
        </div>

        {financials.length === 0 ? (
          <Card className="bg-card/40 border-dashed">
            <CardContent className="p-8 text-center text-muted-foreground">
              <FileText className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p>No tables detected as financial statements.</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {financials.map((statement) => {
               const summaryEntries = Object.entries(statement.summary || {}).filter(([, value]) => value !== null && value !== undefined);
               return (
                <Card key={statement.evidence_id} className="glass-card overflow-hidden">
                  <CardHeader className="bg-gradient-to-r from-card to-card/50 pb-4 border-b border-border/40">
                    <div className="flex flex-col md:flex-row justify-between gap-4">
                      <div>
                        <CardTitle className="text-lg capitalize text-primary font-bold">
                          {statement.statement_type?.replace(/_/g, ' ')}
                        </CardTitle>
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                           Source: <span className="font-mono">{statement.locator}</span>
                        </p>
                      </div>
                      <div className="flex items-center gap-4">
                         <div className="flex flex-col items-end">
                            <span className="text-[10px] uppercase text-muted-foreground">Confidence</span>
                            <div className="flex items-center gap-2">
                               <div className="w-24 h-1.5 bg-secondary rounded-full overflow-hidden">
                                  <div 
                                    className="h-full bg-gradient-to-r from-cyan-500 to-primary" 
                                    style={{ width: `${(statement.confidence || 0) * 100}%` }}
                                  />
                               </div>
                               <span className="text-xs font-bold">{Math.round((statement.confidence || 0) * 100)}%</span>
                            </div>
                         </div>
                      </div>
                    </div>
                  </CardHeader>
                  
                  <CardContent className="p-0">
                    {/* Summary Metrics */}
                    {summaryEntries.length > 0 && (
                      <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-3 bg-secondary/20">
                        {summaryEntries.map(([key, value]) => (
                          <div key={key} className="bg-background/50 p-2 rounded border border-border/50">
                            <p className="text-[10px] uppercase text-muted-foreground mb-1">{key.replace(/_/g, ' ')}</p>
                            <p className="font-mono font-medium text-sm">
                              {typeof value === 'number' ? value.toLocaleString() : String(value)}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* Data Table Preview */}
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-secondary/40 text-left text-xs uppercase tracking-wider text-muted-foreground">
                          <tr>
                            {(statement.columns || []).map((col: string) => (
                              <th key={col} className="px-4 py-3 font-medium whitespace-nowrap">{col}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/30">
                          {(statement.rows || []).slice(0, 5).map((row: any, rIdx: number) => (
                            <tr key={rIdx} className="hover:bg-secondary/10 transition-colors">
                              {statement.columns.map((col: string) => (
                                <td key={col} className="px-4 py-2.5 whitespace-nowrap text-muted-foreground font-mono text-xs">
                                  {row[col]}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {(statement.rows?.length || 0) > 5 && (
                         <div className="p-2 text-center text-xs text-muted-foreground bg-secondary/10">
                            + {statement.rows.length - 5} more rows
                         </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
