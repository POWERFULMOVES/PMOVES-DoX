import React from 'react';
import { BadgeCheck, Clock, Circle, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export interface Cookbook {
  id: string;
  title: string;
  description: string;
  status: 'ready' | 'in-progress' | 'planned';
  steps: string[];
}

interface CookbookCardProps {
  cookbook: Cookbook;
  className?: string;
}

export function CookbookCard({ cookbook, className }: CookbookCardProps) {
  return (
    <div className={cn("bg-white border rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col h-full", className)}>
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-xl font-bold text-gray-900 leading-tight">{cookbook.title}</h3>
        <StatusBadge status={cookbook.status} />
      </div>
      
      <p className="text-gray-600 mb-6 flex-grow text-sm leading-relaxed">
        {cookbook.description}
      </p>
      
      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">WORKFLOW</p>
        <div className="space-y-3">
          {cookbook.steps.map((step, idx) => (
            <div key={idx} className="flex items-start gap-3">
              <div className="flex-shrink-0 w-5 h-5 rounded-full bg-white border border-gray-200 flex items-center justify-center text-xs text-gray-500 font-medium shadow-sm">
                {idx + 1}
              </div>
              <span className="text-sm text-gray-700 leading-snug">{step}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-auto pt-4 border-t border-gray-100 flex justify-end">
        <Link 
          href={`/cookbooks/${cookbook.id}`}
          className="flex items-center gap-2 text-blue-600 font-semibold text-sm hover:text-blue-800 transition-colors group"
        >
          Try it out 
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </Link>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: Cookbook['status'] }) {
  const styles = {
    ready: 'bg-green-100 text-green-700 border-green-200',
    'in-progress': 'bg-yellow-100 text-yellow-700 border-yellow-200',
    planned: 'bg-gray-100 text-gray-600 border-gray-200'
  };

  const icons = {
    ready: <BadgeCheck className="w-3.5 h-3.5" />,
    'in-progress': <Clock className="w-3.5 h-3.5" />,
    planned: <Circle className="w-3.5 h-3.5" />
  };

  const labels = {
    ready: 'Ready',
    'in-progress': 'In Progress',
    planned: 'Planned'
  };

  return (
    <span className={cn("flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border shadow-sm", styles[status])}>
      {icons[status]}
      <span>{labels[status]}</span>
    </span>
  );
}
