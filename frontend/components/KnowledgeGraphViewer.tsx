"use client";

import { useEffect, useState, useRef } from "react";
import * as d3 from "d3";
import { Network, Loader2, AlertCircle, RefreshCw } from "lucide-react";

/**
 * Node in the knowledge graph.
 *
 * @property id - Unique node identifier (typically UUID)
 * @property label - Display text for the node (entity text)
 * @property type - Entity type (PERSON, ORG, LOC, DATE, etc.)
 * @property title - Tooltip text showing full entity info
 */
interface GraphNode {
  id: string;
  label: string;
  type: string;
  title?: string;
}

/**
 * Edge (relationship) in the knowledge graph.
 *
 * @property from - Source node ID
 * @property to - Target node ID
 * @property weight - Relationship strength (0-1, affects line thickness)
 * @property title - Tooltip text describing the relationship
 */
interface GraphEdge {
  from: string;
  to: string;
  weight?: number;
  title?: string;
}

/**
 * Graph data response from the API.
 *
 * @property nodes - Array of entity nodes
 * @property edges - Array of relationships between entities
 * @property document_id - Associated document ID
 * @property error - Error message if the request failed
 * @property message - Optional message (e.g., "No entities found")
 */
interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  document_id?: string;
  error?: string;
  message?: string;
}

/**
 * Props for the KnowledgeGraphViewer component.
 *
 * @property documentId - Document ID to fetch entities for
 * @property width - Graph width in pixels (default: 600)
 * @property height - Graph height in pixels (default: 500)
 */
interface KnowledgeGraphViewerProps {
  documentId: string;
  width?: number;
  height?: number;
}

const ENTITY_COLORS: Record<string, string> = {
  PERSON: "#e74c3c",
  ORG: "#3498db",
  LOC: "#2ecc71",
  DATE: "#f39c12",
  PRODUCT: "#9b59b6",
  GPE: "#1abc9c",
  EVENT: "#e67e22",
  WORK_OF_ART: "#34495e",
  LAW: "#7f8c8d",
  LANGUAGE: "#16a085",
  NORP: "#8e44ad",
  PERCENT: "#27ae60",
  MONEY: "#f1c40f",
  QUANTITY: "#d35400",
  ORDINAL: "#7f8c8d",
  CARDINAL: "#95a5a6",
  UNKNOWN: "#95a5a6",
};

/**
 * Get the color for an entity type.
 *
 * @param type - Entity type (PERSON, ORG, etc.)
 * @returns Hex color string for the entity type
 */
function getNodeColor(type: string): string {
  return ENTITY_COLORS[type] || ENTITY_COLORS.UNKNOWN;
}

/**
 * Get the emoji icon for an entity type.
 *
 * @param type - Entity type (PERSON, ORG, etc.)
 * @returns Emoji character representing the entity type
 */
function getEntityIcon(type: string): string {
  // Simple icons for entity types
  const icons: Record<string, string> = {
    PERSON: "👤",
    ORG: "🏢",
    LOC: "📍",
    DATE: "📅",
    PRODUCT: "📦",
    GPE: "🌍",
    EVENT: "🎯",
  };
  return icons[type] || "•";
}

/**
 * KnowledgeGraphViewer - D3.js force-directed graph visualization.
 *
 * Displays entities extracted from a document as an interactive graph.
 * Features:
 * - Force-directed layout using D3.js
 * - Zoom and pan support
 * - Draggable nodes
 * - Color-coded entity types
 * - Hover tooltips showing entity details
 *
 * @param props - Component props (documentId, width, height)
 * @returns React component with graph visualization
 */
export default function KnowledgeGraphViewer({
  documentId,
  width = 600,
  height = 500,
}: KnowledgeGraphViewerProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphEdge> | null>(null);

  const fetchGraph = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/graph/${documentId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data: GraphData = await response.json();
      setGraphData(data);
      if (data.error) {
        setError(data.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load graph");
      setGraphData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGraph();
  }, [documentId]);

  useEffect(() => {
    if (!graphData || !graphData.nodes.length || !svgRef.current) {
      return;
    }

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const widthAttr = svgRef.current.clientWidth || width;
    const heightAttr = svgRef.current.clientHeight || height;

    // Add zoom behavior
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoom as any);

    const g = svg.append("g");

    // Create arrow markers for edges
    svg
      .append("defs")
      .append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "-0 -5 10 10")
      .attr("refX", 20)
      .attr("refY", 0)
      .attr("orient", "auto")
      .attr("markerWidth", 8)
      .attr("markerHeight", 8)
      .append("path")
      .attr("d", "M 0,-5 L 10,0 L 0,5")
      .attr("fill", "#999");

    // Create simulation
    simulationRef.current = d3
      .forceSimulation<GraphNode>(graphData.nodes)
      .force(
        "link",
        d3
          .forceLink<GraphNode, GraphEdge>(graphData.edges)
          .id((d) => d.id)
          .distance(100)
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(widthAttr / 2, heightAttr / 2))
      .force("collision", d3.forceCollide().radius(30));

    // Create edges
    const link = g
      .append("g")
      .selectAll("line")
      .data(graphData.edges)
      .join("line")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", (d) => Math.sqrt((d.weight || 0.5) * 3))
      .attr("marker-end", "url(#arrowhead)");

    // Create node groups
    const node = g
      .append("g")
      .selectAll<SVGGElement, GraphNode>("g")
      .data(graphData.nodes)
      .join("g")
      .attr("class", "node")
      .call(
        d3
          .drag<SVGSVGElement, GraphNode>()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended) as any
      );

    // Add circles for nodes
    node
      .append("circle")
      .attr("r", 20)
      .attr("fill", (d) => getNodeColor(d.type))
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .style("cursor", "pointer")
      .on("mouseover", function (_event, d) {
        d3.select(this).attr("r", 25).attr("stroke", "#ffd700");
        setHoveredNode(d);
      })
      .on("mouseout", function () {
        d3.select(this).attr("r", 20).attr("stroke", "#fff");
        setHoveredNode(null);
      });

    // Add text labels
    node
      .append("text")
      .text((d) => {
        const icon = getEntityIcon(d.type);
        return `${icon} ${d.label.length > 10 ? d.label.slice(0, 10) + "..." : d.label}`;
      })
      .attr("x", 0)
      .attr("y", 30)
      .attr("text-anchor", "middle")
      .attr("font-size", "10px")
      .attr("fill", "#e5e7eb")
      .style("pointer-events", "none");

    // Add titles (tooltips)
    node.append("title").text((d) => d.title || d.label);

    // Update positions on tick
    simulationRef.current.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as GraphNode).x!)
        .attr("y1", (d) => (d.source as GraphNode).y!)
        .attr("x2", (d) => (d.target as GraphNode).x!)
        .attr("y2", (d) => (d.target as GraphNode).y!);

      node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    });

    function dragstarted(
      event: d3.D3DragEvent<SVGGElement, GraphNode, d3.SubjectPosition>,
      d: GraphNode
    ) {
      if (!simulationRef.current) return;
      if (!event.active) simulationRef.current.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(
      event: d3.D3DragEvent<SVGGElement, GraphNode, d3.SubjectPosition>,
      d: GraphNode
    ) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(
      event: d3.D3DragEvent<SVGGElement, GraphNode, d3.SubjectPosition>,
      d: GraphNode
    ) {
      if (!simulationRef.current) return;
      if (!event.active) simulationRef.current.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    return () => {
      if (simulationRef.current) {
        simulationRef.current.stop();
      }
    };
  }, [graphData]);

  const entityTypeCounts = graphData?.nodes?.reduce((acc, node) => {
    acc[node.type] = (acc[node.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="w-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Network className="w-5 h-5 text-orange-400" />
          <h3 className="text-lg font-semibold text-white">Knowledge Graph</h3>
        </div>
        <button
          onClick={fetchGraph}
          disabled={loading}
          className="p-2 hover:bg-white/10 rounded-lg transition-colors disabled:opacity-50"
          title="Refresh graph"
        >
          <RefreshCw className={`w-4 h-4 text-gray-400 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Stats */}
      {graphData && !error && (
        <div className="flex gap-4 mb-4 text-sm">
          <div className="px-3 py-1 bg-blue-500/20 rounded-full">
            <span className="text-blue-300">{graphData.nodes.length} nodes</span>
          </div>
          <div className="px-3 py-1 bg-green-500/20 rounded-full">
            <span className="text-green-300">{graphData.edges.length} edges</span>
          </div>
        </div>
      )}

      {/* Graph Visualization */}
      <div
        className="relative bg-black/30 rounded-lg border border-white/10 overflow-hidden"
        style={{ height: `${height}px` }}
      >
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50">
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="w-8 h-8 text-orange-400 animate-spin" />
              <p className="text-gray-400">Loading knowledge graph...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/50">
            <div className="flex flex-col items-center gap-2 text-center px-4">
              <AlertCircle className="w-8 h-8 text-red-400" />
              <p className="text-red-400">{error}</p>
              <p className="text-gray-500 text-sm">
                Neo4j may not be available. Ensure the neo4j service is running.
              </p>
            </div>
          </div>
        )}

        {!loading && !error && graphData && !graphData.nodes.length && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <Network className="w-12 h-12 text-gray-600 mx-auto mb-2" />
              <p className="text-gray-500">No entities found for this document</p>
              <p className="text-gray-600 text-sm mt-1">
                Extract entities first to build the knowledge graph
              </p>
            </div>
          </div>
        )}

        <svg
          ref={svgRef}
          width="100%"
          height="100%"
          style={{ display: !loading && !error && graphData?.nodes.length ? "block" : "none" }}
        />
      </div>

      {/* Entity Type Legend */}
      {entityTypeCounts && Object.keys(entityTypeCounts).length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {Object.entries(entityTypeCounts).map(([type, count]) => (
            <div
              key={type}
              className="flex items-center gap-1 px-2 py-1 bg-white/5 rounded-full text-xs"
            >
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: getNodeColor(type) }}
              />
              <span className="text-gray-300">{type}:</span>
              <span className="text-gray-400">{count}</span>
            </div>
          ))}
        </div>
      )}

      {/* Hovered Node Info */}
      {hoveredNode && (
        <div className="mt-4 p-3 bg-white/5 rounded-lg border border-white/10">
          <p className="text-xs text-gray-400 uppercase tracking-wide">{hoveredNode.type}</p>
          <p className="text-white font-medium">{hoveredNode.label}</p>
          {hoveredNode.title && (
            <p className="text-gray-400 text-sm mt-1">{hoveredNode.title}</p>
          )}
        </div>
      )}
    </div>
  );
}
