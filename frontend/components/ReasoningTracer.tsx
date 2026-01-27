"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { getApiBase } from '@/lib/config';
import { cn } from '@/lib/utils';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import {
  Brain,
  ChevronDown,
  ChevronRight,
  Clock,
  FileText,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Bot,
  Link2
} from "lucide-react";

// Types matching backend models
interface Evidence {
  evidence_id: string;
  source: string;
  content: string;
  relevance_score: number;
  metadata?: Record<string, unknown>;
}

interface ReasoningStep {
  step_id: string;
  step_number: number;
  thought: string;
  evidence: Evidence[];
  confidence: number;
  agent_id?: string;
  created_at: string;
}

interface ReasoningTrace {
  trace_id: string;
  question: string;
  context?: string;
  steps: ReasoningStep[];
  conclusion?: string;
  status: 'active' | 'concluded' | 'abandoned';
  final_confidence?: number;
  created_at: string;
  concluded_at?: string;
}

interface ReasoningTracerProps {
  traceId?: string;
  onStepClick?: (step: ReasoningStep) => void;
  showEvidence?: boolean;
  compact?: boolean;
  className?: string;
}

/**
 * ReasoningTracer - Visualizes step-by-step reasoning traces from the A2A reasoning engine.
 *
 * Displays reasoning steps with evidence flow, agent attribution, and confidence scores.
 * Supports expandable evidence sections and visual confidence indicators.
 */
export default function ReasoningTracer({
  traceId,
  onStepClick,
  showEvidence = true,
  compact = false,
  className
}: ReasoningTracerProps) {
  const [trace, setTrace] = useState<ReasoningTrace | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  // Fetch trace data from backend with AbortController support
  const fetchTrace = useCallback(async (id: string, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const apiBase = getApiBase();
      const response = await fetch(`${apiBase}/a2a/reasoning/trace/${id}`, { signal });
      if (!response.ok) {
        throw new Error(`Failed to fetch trace: ${response.statusText}`);
      }
      const data: ReasoningTrace = await response.json();
      setTrace(data);
    } catch (err) {
      // Ignore aborted fetches - component unmounted or traceId changed
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }
      console.error('Error fetching reasoning trace:', err);
      setError(err instanceof Error ? err.message : 'Failed to load reasoning trace');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch trace when traceId changes, with cleanup to prevent race conditions
  useEffect(() => {
    if (!traceId) {
      setTrace(null);
      return;
    }
    const controller = new AbortController();
    fetchTrace(traceId, controller.signal);
    return () => controller.abort();
  }, [traceId, fetchTrace]);

  // Toggle step expansion
  const toggleStep = useCallback((stepId: string) => {
    setExpandedSteps(prev => {
      const next = new Set(prev);
      if (next.has(stepId)) {
        next.delete(stepId);
      } else {
        next.add(stepId);
      }
      return next;
    });
  }, []);

  // Confidence color helper - returns Tailwind class
  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'text-green-500';
    if (confidence >= 0.6) return 'text-emerald-400';
    if (confidence >= 0.4) return 'text-yellow-500';
    if (confidence >= 0.2) return 'text-orange-500';
    return 'text-red-500';
  };

  // Confidence background color for bars
  const getConfidenceBarColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'bg-green-500';
    if (confidence >= 0.6) return 'bg-emerald-400';
    if (confidence >= 0.4) return 'bg-yellow-500';
    if (confidence >= 0.2) return 'bg-orange-500';
    return 'bg-red-500';
  };

  // Status icon helper
  const getStatusIcon = (status: ReasoningTrace['status']) => {
    switch (status) {
      case 'concluded':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'abandoned':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'active':
      default:
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
    }
  };

  // Status badge styling
  const getStatusBadgeClass = (status: ReasoningTrace['status']): string => {
    switch (status) {
      case 'concluded':
        return 'bg-green-500/10 text-green-400 border-green-500/20';
      case 'abandoned':
        return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'active':
      default:
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    }
  };

  // Relevance score badge color
  const getRelevanceColor = (score: number): string => {
    if (score >= 0.8) return 'bg-green-500/20 text-green-400';
    if (score >= 0.5) return 'bg-yellow-500/20 text-yellow-400';
    return 'bg-gray-500/20 text-gray-400';
  };

  // Format timestamp
  const formatTime = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return isoString;
    }
  };

  // Render evidence item
  const renderEvidence = (evidence: Evidence, index: number) => {
    return (
      <div
        key={evidence.evidence_id || index}
        className="group flex flex-col bg-secondary/20 hover:bg-secondary/30 border border-border/30 rounded-lg p-3 transition-all text-sm"
      >
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <FileText className="w-3.5 h-3.5 text-blue-400" />
            <span className="font-medium text-xs text-primary/80 font-mono truncate max-w-[200px]">
              {evidence.source}
            </span>
          </div>
          <span className={cn(
            "text-[10px] px-2 py-0.5 rounded-full font-mono",
            getRelevanceColor(evidence.relevance_score)
          )}>
            {(evidence.relevance_score * 100).toFixed(0)}% relevant
          </span>
        </div>
        <p className="text-muted-foreground text-xs line-clamp-3 leading-relaxed bg-background/20 p-2 rounded border border-white/5 font-mono opacity-80 group-hover:opacity-100">
          {evidence.content.length > 200
            ? `${evidence.content.substring(0, 200)}...`
            : evidence.content}
        </p>
        {evidence.metadata && Object.keys(evidence.metadata).length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {Object.entries(evidence.metadata).slice(0, 3).map(([key, value]) => (
              <span
                key={key}
                className="text-[9px] px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground"
              >
                {key}: {String(value).substring(0, 20)}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  };

  // Render step card
  const renderStep = (step: ReasoningStep, index: number, totalSteps: number) => {
    const isExpanded = expandedSteps.has(step.step_id);
    const hasEvidence = step.evidence && step.evidence.length > 0;
    const isLast = index === totalSteps - 1;

    return (
      <div key={step.step_id} className="relative">
        {/* Timeline connector */}
        {!isLast && (
          <div className="absolute left-5 top-12 bottom-0 w-0.5 bg-gradient-to-b from-primary/40 to-primary/10" />
        )}

        {/* Step card */}
        <div
          className={cn(
            "relative flex gap-4 pb-6",
            compact ? "pb-4" : "pb-6"
          )}
        >
          {/* Step number indicator */}
          <div className={cn(
            "flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center",
            "bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/30",
            "text-sm font-bold text-primary z-10"
          )}>
            {step.step_number}
          </div>

          {/* Step content */}
          <div className="flex-1 min-w-0">
            <div
              className={cn(
                "bg-card border border-border/50 rounded-xl p-4 shadow-md",
                "hover:border-primary/30 transition-all cursor-pointer",
                onStepClick && "hover:shadow-lg"
              )}
              onClick={() => {
                if (onStepClick) onStepClick(step);
                if (showEvidence && hasEvidence) toggleStep(step.step_id);
              }}
            >
              {/* Step header */}
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex-1">
                  {/* Agent badge */}
                  {step.agent_id && (
                    <div className="flex items-center gap-1.5 mb-2">
                      <Bot className="w-3 h-3 text-purple-400" />
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono">
                        {step.agent_id}
                      </span>
                    </div>
                  )}

                  {/* Thought content */}
                  <p className={cn(
                    "text-sm text-card-foreground leading-relaxed",
                    compact && "line-clamp-2"
                  )}>
                    {step.thought}
                  </p>
                </div>

                {/* Expand/collapse indicator for evidence */}
                {showEvidence && hasEvidence && (
                  <button
                    className="flex-shrink-0 p-1 rounded hover:bg-secondary/50 transition-colors"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleStep(step.step_id);
                    }}
                  >
                    {isExpanded
                      ? <ChevronDown className="w-4 h-4 text-muted-foreground" />
                      : <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    }
                  </button>
                )}
              </div>

              {/* Step metadata row */}
              <div className="flex items-center justify-between gap-4 mt-3 pt-3 border-t border-border/30">
                {/* Confidence bar */}
                <div className="flex-1 max-w-[200px]">
                  <div className="flex items-center justify-between text-[10px] mb-1">
                    <span className="text-muted-foreground uppercase tracking-wider">Confidence</span>
                    <span className={cn("font-mono font-bold", getConfidenceColor(step.confidence))}>
                      {(step.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-secondary/50 rounded-full overflow-hidden">
                    <div
                      className={cn("h-full rounded-full transition-all duration-500", getConfidenceBarColor(step.confidence))}
                      style={{ width: `${step.confidence * 100}%` }}
                    />
                  </div>
                </div>

                {/* Evidence count & timestamp */}
                <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                  {hasEvidence && (
                    <div className="flex items-center gap-1">
                      <Link2 className="w-3 h-3" />
                      <span>{step.evidence.length} evidence</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span>{formatTime(step.created_at)}</span>
                  </div>
                </div>
              </div>

              {/* Evidence section (expandable) */}
              {showEvidence && hasEvidence && isExpanded && (
                <div className="mt-4 pt-4 border-t border-border/30 space-y-2 animate-in slide-in-from-top-2 duration-300">
                  <h5 className="text-xs font-semibold uppercase text-muted-foreground flex items-center gap-2 mb-3">
                    <FileText className="w-3 h-3" /> Supporting Evidence
                  </h5>
                  <div className="grid grid-cols-1 gap-2">
                    {step.evidence.map((ev, idx) => renderEvidence(ev, idx))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Loading state
  if (loading) {
    return (
      <Card className={cn("glass-card overflow-hidden", className)}>
        <CardContent className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3 text-muted-foreground">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="text-sm animate-pulse">Loading reasoning trace...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card className={cn("glass-card overflow-hidden border-red-500/30", className)}>
        <CardContent className="flex items-center justify-center py-12">
          <div className="flex items-center gap-3 text-red-400">
            <AlertCircle className="w-5 h-5" />
            <span className="text-sm">{error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // No trace selected state
  if (!trace) {
    return (
      <Card className={cn("glass-card overflow-hidden", className)}>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground opacity-60">
          <Brain className="w-12 h-12 mb-4" />
          <p>No reasoning trace selected</p>
          <p className="text-xs mt-2 max-w-xs">
            Select a trace to visualize the step-by-step reasoning process.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Main render
  return (
    <Card className={cn("glass-card overflow-hidden flex flex-col", className)}>
      <CardHeader className="bg-gradient-to-r from-card to-card/50 border-b border-border/40 pb-4">
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Brain className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-purple-400">
                Reasoning Trace
              </CardTitle>
              <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                {trace.trace_id.substring(0, 8)}...
              </p>
            </div>
          </div>

          {/* Status badge */}
          <div className={cn(
            "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs border",
            getStatusBadgeClass(trace.status)
          )}>
            {getStatusIcon(trace.status)}
            <span className="capitalize">{trace.status}</span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0">
        {/* Question section */}
        <div className="p-4 bg-secondary/10 border-b border-border/30">
          <div className="flex items-start gap-3">
            <div className="p-1.5 rounded-full bg-blue-500/10 text-blue-400 flex-shrink-0 mt-0.5">
              <AlertCircle className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <span className="text-[10px] font-bold uppercase text-muted-foreground tracking-wider block mb-1">
                Question
              </span>
              <p className="text-sm text-card-foreground font-medium">
                {trace.question}
              </p>
              {trace.context && (
                <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                  Context: {trace.context}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Steps timeline */}
        <div className={cn(
          "flex-1 overflow-y-auto p-4",
          compact ? "p-3" : "p-6"
        )}>
          {trace.steps.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
              <Loader2 className="w-8 h-8 mb-3 animate-spin opacity-50" />
              <p className="text-sm">Awaiting reasoning steps...</p>
            </div>
          ) : (
            <div className="space-y-0">
              {trace.steps.map((step, idx) => renderStep(step, idx, trace.steps.length))}
            </div>
          )}
        </div>

        {/* Conclusion section (if concluded) */}
        {trace.conclusion && (
          <div className="p-4 bg-gradient-to-r from-green-500/5 to-emerald-500/5 border-t border-green-500/20">
            <div className="flex items-start gap-3">
              <div className="p-1.5 rounded-full bg-green-500/10 text-green-400 flex-shrink-0 mt-0.5">
                <CheckCircle2 className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold uppercase text-green-400/80 tracking-wider">
                    Conclusion
                  </span>
                  {trace.final_confidence !== undefined && (
                    <span className={cn(
                      "text-sm font-bold font-mono",
                      getConfidenceColor(trace.final_confidence)
                    )}>
                      {(trace.final_confidence * 100).toFixed(0)}% confidence
                    </span>
                  )}
                </div>
                <p className="text-sm text-card-foreground leading-relaxed">
                  {trace.conclusion}
                </p>
                {trace.concluded_at && (
                  <p className="text-[10px] text-muted-foreground mt-2 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Concluded at {formatTime(trace.concluded_at)}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Footer stats */}
        <div className="p-3 bg-card/60 border-t border-border/40 backdrop-blur-xl">
          <div className="flex items-center justify-between text-[10px] text-muted-foreground">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <Brain className="w-3 h-3" />
                {trace.steps.length} step{trace.steps.length !== 1 ? 's' : ''}
              </span>
              <span className="flex items-center gap-1">
                <Link2 className="w-3 h-3" />
                {trace.steps.reduce((acc, s) => acc + (s.evidence?.length || 0), 0)} evidence items
              </span>
            </div>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              Started {formatTime(trace.created_at)}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
