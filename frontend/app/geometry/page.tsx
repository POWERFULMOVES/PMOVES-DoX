"use client";

import { useState, useEffect } from "react";
import { HyperbolicNavigator } from "@/components/geometry/HyperbolicNavigator";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const initialData: GeometryData = {
  spec: "chit.cgp.v0.1",
  meta: { source: "initial" },
  super_nodes: [
    {
      id: "root",
      label: "Waiting for Data...",
      x: 0,
      y: 0,
      r: 20,
      constellations: []
    }
  ]
};

interface ConstellationPoint {
  id: string;
  x: number;
  y: number;
  proj: number;
  conf: number;
  text: string;
}

interface Constellation {
  id: string;
  anchor: [number, number, number];
  summary: string;
  spectrum: number[];
  radial_minmax: [number, number];
  points: ConstellationPoint[];
}

interface SuperNode {
  id: string;
  label: string;
  x: number;
  y: number;
  r: number;
  constellations: Constellation[];
}

interface GeometryData {
  spec: string;
  meta: { source: string };
  super_nodes: SuperNode[];
}

export default function GeometryPage() {
  const [geometryData, setGeometryData] = useState<GeometryData>(initialData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchGeometryData() {
      try {
        setLoading(true);
        setError(null);

        // Fetch demo geometry packet from backend
        const response = await fetch('/api/v1/cipher/geometry/demo-packet');
        if (!response.ok) {
          throw new Error(`Backend returned ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // Validate data has expected structure
        if (data.super_nodes && Array.isArray(data.super_nodes)) {
          setGeometryData(data);
        } else {
          console.warn('Invalid geometry data structure, using initial data');
        }
      } catch (err) {
        console.error('Failed to fetch geometry data:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
        // Keep initial data on error
      } finally {
        setLoading(false);
      }
    }

    fetchGeometryData();

    // Optional: Set up periodic refresh for live geometry updates
    const interval = setInterval(fetchGeometryData, 30000); // Refresh every 30s

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-white">
        <header className="p-4 border-b border-slate-800 flex justify-between items-center">
            <div>
                <h1 className="text-xl font-bold">Geometric Intelligence / Shape Discovery</h1>
                <p className="text-sm text-slate-400">
                    CHIT Protocol: Hyperbolic Knowledge Navigation
                </p>
            </div>
            <div className="flex items-center gap-4 text-sm">
                {loading && <span className="text-blue-400">Loading geometry data...</span>}
                {error && <span className="text-red-400">Error: {error}</span>}
                {!loading && !error && (
                    <span className="text-green-400">
                        {geometryData.super_nodes.length} super nodes
                    </span>
                )}
            </div>
        </header>
        <main className="flex-1 p-4 relative">
             <ErrorBoundary>
                 <HyperbolicNavigator
                    data={geometryData}
                    width={1200}
                    height={800}
                    className="w-full h-full shadow-2xl shadow-blue-900/20"
                 />
             </ErrorBoundary>
        </main>
    </div>
  );
}
