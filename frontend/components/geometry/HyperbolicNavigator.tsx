"use client";

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';
import { useNats } from '@/lib/nats-context';
import { StringCodec } from 'nats.ws';
import { Button } from '@/components/ui/button';
import dynamic from 'next/dynamic';

// --- Types ---
interface CGPPoint {
  id: string;
  x: number;
  y: number;
  proj: number;
  conf: number;
  text?: string;
}

interface CGPConstellation {
  id: string;
  anchor: number[];
  summary: string;
  spectrum: number[];
  radial_minmax: [number, number];
  points: CGPPoint[];
}

interface CGPSuperNode {
  id: string;
  x: number;
  y: number;
  r: number;
  label: string;
  constellations: CGPConstellation[];
}

export interface ManifoldParams {
  curvature_k?: number;
  epsilon?: number;
  surfaceFn?: string;
  t?: number;
}

export interface HyperbolicNavigatorProps {
  data: {
    super_nodes: CGPSuperNode[];
  };
  className?: string;
  width?: number;
  height?: number;
  initialManifoldParams?: ManifoldParams | null;
}


// Dynamically import Manifold3D with no SSR to prevent text/canvas hydration mismatches
const Manifold3D = dynamic(() => import('./Manifold3D'), { 
    ssr: false,
    loading: () => <div className="flex items-center justify-center w-full h-full text-slate-500">Loading 3D Engine...</div>
});

// Remove local Manifold3D definition and imports
// const Manifold3D = ... (Deleted)


// --- Main Navigator Component ---
export function HyperbolicNavigator({ data, className, width = 800, height = 600, initialManifoldParams }: HyperbolicNavigatorProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const { connection } = useNats();
  const [vizData, setVizData] = useState(data);
  const [manifoldParams, setManifoldParams] = useState<ManifoldParams | null>(initialManifoldParams || null);
  const [viewMode, setViewMode] = useState<'navigator' | 'manifold'>('navigator');

  // Sync prop data
  useEffect(() => {
    setVizData(data);
  }, [data]);

  // Sync initial manifold params
  useEffect(() => {
    if (initialManifoldParams) {
      setManifoldParams(initialManifoldParams);
    }
  }, [initialManifoldParams]);

  // NATS Subscription
  useEffect(() => {
    if (!connection) return;

    const sc = StringCodec();
    const sub = connection.subscribe("geometry.event.>");
    console.log("HyperbolicNavigator: Subscribed to geometry.event.>");

    (async () => {
      for await (const m of sub) {
        try {
          const payload = JSON.parse(sc.decode(m.data));
          
           // Type Detection
           if (payload.type === 'manifold_update' || payload.parameters) {
               console.log("HyperbolicNavigator: Manifold Update", payload);
               setManifoldParams(payload.parameters);
               // Auto-switch to manifold mode if we get a pure manifold update? 
               // Maybe just let user toggle.
           } else if (payload.super_nodes || payload.type === 'constellation_update') {
               console.log("HyperbolicNavigator: Constellation Update", payload);
               setVizData(payload);
           }
        } catch (err) {
          console.error("Failed to parse NATS geometry event", err);
        }
      }
    })();

    return () => {
      sub.unsubscribe();
    };
  }, [connection]);

  // D3 Renderer (Navigator Mode)
  useEffect(() => {
    if (viewMode !== 'navigator' || !svgRef.current || !vizData?.super_nodes) return;

    const svg = d3.select(svgRef.current);
    const w = width;
    const h = height;

    svg.selectAll("*").remove();

    const g = svg.append("g").attr("class", "main-group");
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 10])
      .on("zoom", (event) => g.attr("transform", event.transform));
      
    svg.call(zoom);
    svg.call(zoom.transform, d3.zoomIdentity.translate(w/2, h/2));

    // Super Nodes
    const superNodes = g.selectAll(".super-node")
      .data(vizData.super_nodes)
      .join("g")
      .attr("class", "super-node")
      .attr("transform", d => `translate(${d.x}, ${d.y})`)
      .style("cursor", "pointer")
      .on("click", (event, d) => {
        event.stopPropagation();
        setSelectedNode(d.id);
        const transform = d3.zoomIdentity.translate(w/2, h/2).scale(2).translate(-d.x, -d.y);
        svg.transition().duration(750).call(zoom.transform, transform);
      });

    superNodes.append("circle")
      .attr("r", d => d.r)
      .attr("fill", "rgba(147, 197, 253, 0.1)")
      .attr("stroke", "#60a5fa")
      .attr("stroke-width", 1)
      .attr("stroke-dasharray", "4,4");

    superNodes.append("text")
      .attr("y", d => -d.r - 10)
      .attr("text-anchor", "middle")
      .attr("class", "fill-foreground text-xs font-mono")
      .text(d => d.label);

    // Constellations
    const constellations = superNodes.selectAll(".constellation")
      .data(d => d.constellations || [])
      .join("g")
      .attr("transform", (d, i, nodes) => {
         const parent = (nodes[i] as any).parentNode as unknown as SVGElement;
         const radius = (d3.select(parent).datum() as CGPSuperNode).r * 0.6;
         const angle = (i / nodes.length) * 2 * Math.PI;
         return `translate(${Math.cos(angle) * radius}, ${Math.sin(angle) * radius})`;
      });

    constellations.append("path")
      .attr("d", d3.symbol().type(d3.symbolStar).size(80))
      .attr("fill", "#f87171");

    // Points
    const points = constellations.selectAll(".point")
        .data(d => d.points || [])
        .join("circle")
        .attr("r", d => 2 + (d.conf * 2))
        .attr("cx", d => d.x * 0.2)
        .attr("cy", d => d.y * 0.2)
        .attr("fill", "#22d3ee")
        .attr("opacity", 0.7);

    points.append("title").text(d => `${d.text} (Conf: ${d.conf})`);

  }, [vizData, width, height, viewMode]);

  return (
    <div ref={containerRef} className={cn("relative overflow-hidden border rounded-lg bg-slate-950/50", className)}>
        {/* Toolbar */}
        <div className="absolute top-4 right-4 z-10 flex gap-2">
            <Button 
                variant={viewMode === 'navigator' ? 'default' : 'outline'} 
                size="sm" 
                onClick={() => setViewMode('navigator')}
            >
                Navigator (2D)
            </Button>
            <Button 
                variant={viewMode === 'manifold' ? 'default' : 'outline'} 
                size="sm" 
                onClick={() => setViewMode('manifold')}
            >
                Manifold (3D)
            </Button>
        </div>

        {/* Viewport */}
        {viewMode === 'navigator' ? (
             <svg 
                ref={svgRef} 
                width={width} 
                height={height} 
                className="w-full h-full"
            />
        ) : (
            <Manifold3D width={width} height={height} params={manifoldParams} />
        )}

        {/* HUD */}
        <div className="absolute top-4 left-4 pointer-events-none">
            <h3 className="text-sm font-bold text-slate-400">Hyperbolic Manifold</h3>
            <p className="text-xs text-slate-500">
                {selectedNode ? `Focused: ${selectedNode}` : "Global View"} | Mode: {viewMode}
            </p>
        </div>
    </div>
  );
}
