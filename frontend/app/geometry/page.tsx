"use client";

import { useState, useEffect } from "react";
import { HyperbolicNavigator } from "@/components/geometry/HyperbolicNavigator";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { GeometryProvider } from "@/lib/geometry-context";

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

interface ManifoldParams {
  curvature_k: number;
  epsilon: number;
}

interface ManifoldMetadata {
  shape: string;
  curvature_k: number;
  epsilon: number;
  delta: number;
}

export default function GeometryPage() {
  const [geometryData, setGeometryData] = useState<GeometryData>(initialData);
  const [manifoldParams, setManifoldParams] = useState<ManifoldParams | null>(null);
  const [manifoldMeta, setManifoldMeta] = useState<ManifoldMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchGeometryData() {
      try {
        setLoading(true);
        setError(null);

        const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8484';

        // Fetch demo geometry packet and manifold params in parallel
        const [cgpResponse, manifoldResponse] = await Promise.all([
          fetch(`${API_BASE}/cipher/geometry/demo-packet`),
          fetch(`${API_BASE}/cipher/geometry/visualize_manifold`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ document_id: 'demo' })
          })
        ]);

        if (!cgpResponse.ok) {
          throw new Error(`CGP endpoint returned ${cgpResponse.status}: ${cgpResponse.statusText}`);
        }

        const cgpData = await cgpResponse.json();

        // Validate CGP data has expected structure
        if (cgpData.super_nodes && Array.isArray(cgpData.super_nodes)) {
          setGeometryData(cgpData);
        } else {
          console.warn('Invalid geometry data structure, using initial data');
        }

        // Parse manifold params from visualize_manifold response
        if (manifoldResponse.ok) {
          const manifoldData = await manifoldResponse.json();
          if (manifoldData.metrics) {
            setManifoldParams({
              curvature_k: manifoldData.metrics.curvature_k ?? 0,
              epsilon: manifoldData.metrics.epsilon ?? 0.1
            });
            setManifoldMeta({
              shape: manifoldData.shape || 'Unknown',
              curvature_k: manifoldData.metrics.curvature_k ?? 0,
              epsilon: manifoldData.metrics.epsilon ?? 0,
              delta: manifoldData.metrics.delta ?? 0
            });
            console.log('Manifold params loaded:', manifoldData.metrics);
          }
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

    // Note: Real-time geometry updates are handled via NATS WebSocket connection
    // in HyperbolicNavigator component. No polling needed.
  }, []);

  // Determine shape badge color
  const getShapeBadgeColor = (shape: string) => {
    if (shape.includes('Hyperbolic')) return 'bg-purple-500/20 text-purple-300 border-purple-500/50';
    if (shape.includes('Spherical')) return 'bg-orange-500/20 text-orange-300 border-orange-500/50';
    return 'bg-slate-500/20 text-slate-300 border-slate-500/50';
  };

  return (
    <GeometryProvider initialParams={manifoldParams || undefined}>
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
                      <>
                          <span className="text-green-400">
                              {geometryData.super_nodes.length} super nodes
                          </span>
                          {manifoldMeta && (
                              <span className={`px-2 py-1 rounded border text-xs font-mono ${getShapeBadgeColor(manifoldMeta.shape)}`}>
                                  {manifoldMeta.shape} (K={manifoldMeta.curvature_k.toFixed(2)})
                              </span>
                          )}
                      </>
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
                      initialManifoldParams={manifoldParams}
                   />
               </ErrorBoundary>
          </main>
      </div>
    </GeometryProvider>
  );
}
