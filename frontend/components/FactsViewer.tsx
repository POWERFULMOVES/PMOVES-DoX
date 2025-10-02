'use client';

import { useEffect, useRef, useState } from 'react';
import axios from 'axios';

export default function FactsViewer() {
  const [facts, setFacts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadFacts();
    // Auto-refresh facts periodically to catch background results
    timerRef.current = setInterval(() => loadFacts(true), 3000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const loadFacts = async (silent = false) => {
    try {
      const API = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
      const response = await axios.get(`${API}/facts`);
      setFacts(response.data.facts);
    } catch (error) {
      console.error('Failed to load facts:', error);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  if (loading) return <div className="text-center py-8">Loading facts...</div>;

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Extracted Facts ({facts.length})</h2>
      
      {facts.length === 0 ? (
        <p className="text-gray-500">No facts yet. Upload some documents to get started.</p>
      ) : (
        <div className="space-y-4">
          {facts.map((fact, idx) => (
            <div key={idx} className="border rounded p-4">
              <div className="flex justify-between mb-2">
                <span className="font-medium">
                  {fact.entity || 'General'}
                </span>
                <span className="text-sm text-gray-500">
                  {fact.report_week}
                </span>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {Object.entries(fact.metrics || {}).map(([key, value]: [string, any]) => (
                  <div key={key} className="bg-gray-50 p-2 rounded">
                    <p className="text-xs text-gray-600 uppercase">{key}</p>
                    <p className="font-semibold">{typeof value === 'number' ? value.toFixed(2) : String(value)}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
