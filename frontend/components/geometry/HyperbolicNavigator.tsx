"use client";

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';
import { useNats } from '@/lib/nats-context';
import { StringCodec } from 'nats.ws';

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

export interface HyperbolicNavigatorProps {
  data: {
    super_nodes: CGPSuperNode[];
  };
  className?: string;
  width?: number;
  height?: number;
}

export function HyperbolicNavigator({ data, className, width = 800, height = 600 }: HyperbolicNavigatorProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const { connection } = useNats();
  const [vizData, setVizData] = useState(data);

  // Sync prop data to state if it changes upstream
  useEffect(() => {
    setVizData(data);
  }, [data]);

  // NATS Subscription for Real-time Geometry Updates
  useEffect(() => {
    if (!connection) return;

    const sc = StringCodec();
    const sub = connection.subscribe("geometry.event.>");
    console.log("HyperbolicNavigator: Subscribed to geometry.event.>");

    (async () => {
      for await (const m of sub) {
        try {
          const payload = JSON.parse(sc.decode(m.data));
           // If payload looks like a CGP or has super_nodes, update viz
           if (payload.super_nodes) {
               console.log("HyperbolicNavigator: Received Geometry Update via NATS", payload);
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

  useEffect(() => {
    if (!svgRef.current || !vizData?.super_nodes) return;

    const svg = d3.select(svgRef.current);
    const w = width;
    const h = height;

    // Clear previous
    svg.selectAll("*").remove();

    // Setup group and zoom
    const g = svg.append("g").attr("class", "main-group");
    
    // Zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 10])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });
      
    svg.call(zoom);

    // Initial center transform
    svg.call(zoom.transform, d3.zoomIdentity.translate(w/2, h/2));

    // Render Super Nodes
    const superNodes = g.selectAll(".super-node")
      .data(vizData.super_nodes)
      .join("g")
      .attr("class", "super-node")
      .attr("transform", d => `translate(${d.x}, ${d.y})`)
      .style("cursor", "pointer")
      .on("click", (event, d) => {
        event.stopPropagation();
        setSelectedNode(d.id);
        
        // Zoom to node
        const scale = 2; // Fixed zoom scale for now
        const transform = d3.zoomIdentity
          .translate(w/2, h/2)
          .scale(scale)
          .translate(-d.x, -d.y);
          
        svg.transition().duration(750).call(zoom.transform, transform);
      });

    // Super Node Circle (The "Disk" of this local manifold)
    superNodes.append("circle")
      .attr("r", d => d.r)
      .attr("fill", "rgba(147, 197, 253, 0.1)") // blue-300 with low opacity
      .attr("stroke", "#60a5fa") // blue-400
      .attr("stroke-width", 1)
      .attr("stroke-dasharray", "4,4");

    // Super Node Label
    superNodes.append("text")
      .attr("y", d => -d.r - 10)
      .attr("text-anchor", "middle")
      .attr("class", "fill-foreground text-xs font-mono")
      .text(d => d.label);

    // Render Constellations (Sub-clusters)
    const constellations = superNodes.selectAll(".constellation")
      .data(d => d.constellations || [])
      .join("g")
      .attr("class", "constellation")
      // Simple radial layout for constellations within super node if encoded positions aren't absolute relative to super node
      // Assuming for now data has relative positions or we project them.
      // For v0.1 spec, points have x,y. Let's assume constellations need a visual anchor.
      .attr("transform", (d, i, nodes) => {
         // Distribute evenly if no coords (fallback)
         const parent = (nodes[i] as any).parentNode as unknown as SVGElement;
         const radius = (d3.select(parent).datum() as CGPSuperNode).r * 0.6;
         const angle = (i / nodes.length) * 2 * Math.PI;
         return `translate(${Math.cos(angle) * radius}, ${Math.sin(angle) * radius})`;
      });

    // Constellation Marker (Star)
    const starSymbol = d3.symbol().type(d3.symbolStar).size(80);
    constellations.append("path")
      .attr("d", starSymbol)
      .attr("fill", "#f87171") // red-400
      .attr("stroke", "none");

    // Ripple Rings (Cymatic Visuals based on Spectrum)
    // We use the first few bins of spectrum to define ring intensity/radius
    constellations.each(function(d) {
        const group = d3.select(this);
        const spectrum = d.spectrum || [];
        
        // Add animated rings
        spectrum.slice(0, 3).forEach((intensity, idx) => {
            group.append("circle")
                .attr("r", 10 + (idx * 5))
                .attr("fill", "none")
                .attr("stroke", `rgba(248, 113, 113, ${intensity * 0.5})`) // red-400 with spectrum alpha
                .attr("class", "animate-pulse"); // Use Tailwind animation
        });
    });

    // Constellation Points (The actual data items)
    // Note: points usually have x,y coordinates. If they are global, we need to map them.
    // Spec says points have x,y "2D layout coordinates for viz".
    // We'll render them relative to the constellation for now, or assume they are pre-projected.
    // Spec in doc says points have x,y. Let's render them relative to SuperNode? 
    // Wait, spec: "points": [{ "x": 13.4, "y": -8.2 ... }] 
    // And "constellations" are children of "super_nodes".
    // Let's assume points x,y are relative to the SuperNode center for this first pass.
    
    // Actually, creating a separate layer for points might be cleaner, but let's nest them for now
    // to keep the hierarchy visual.
    const points = constellations.selectAll(".point")
        .data(d => d.points || [])
        .join("circle")
        .attr("class", "point")
        .attr("r", d => 2 + (d.conf * 2)) // Size by confidence
        .attr("cx", d => d.x * 0.2) // Scale down if coordinates are large, simplistic for demo
        .attr("cy", d => d.y * 0.2)
        .attr("fill", "#22d3ee") // cyan-400
        .attr("opacity", 0.7)
        .on("mouseover", function(event, d) {
            d3.select(this).attr("r", 6).attr("opacity", 1);
            // Tooltip logic could go here
        })
        .on("mouseout", function(event, d) {
            d3.select(this).attr("r", 2 + (d.conf * 2)).attr("opacity", 0.7);
        });

    points.append("title")
        .text(d => `${d.text?.substring(0, 50)}... (Conf: ${d.conf})`);


  }, [vizData, width, height]);

  return (
    <div ref={containerRef} className={cn("relative overflow-hidden border rounded-lg bg-slate-950/50", className)}>
        <svg 
            ref={svgRef} 
            width={width} 
            height={height} 
            viewBox={`0 0 ${width} ${height}`}
            className="w-full h-full"
        />
        <div className="absolute top-4 left-4 pointer-events-none">
            <h3 className="text-sm font-bold text-slate-400">Hyperbolic Manifold</h3>
            <p className="text-xs text-slate-500">
                {selectedNode ? `Focused: ${selectedNode}` : "Global View"}
            </p>
        </div>
    </div>
  );
}
