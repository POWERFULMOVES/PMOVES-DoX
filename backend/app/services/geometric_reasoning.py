"""Geometric reasoning service for geometry-guided decision making.

This module uses geometric insights from the embedding space to:
- Route queries to appropriate agents based on semantic position
- Weight evidence by geodesic proximity
- Detect knowledge gaps (low-density regions)
- Identify concept hierarchies (hyperbolic structure)
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field

from app.services.geometry_engine import GeometryEngine, geometry_engine

logger = logging.getLogger(__name__)


class QueryRouteResult(BaseModel):
    """Result of geometry-guided query routing."""
    query: str
    recommended_agents: List[str]
    confidence_scores: Dict[str, float]
    semantic_region: str
    manifold_position: Optional[List[float]] = None


class EvidenceWeight(BaseModel):
    """Weighted evidence based on geometric proximity."""
    evidence_id: str
    original_score: float
    geodesic_distance: float
    geometric_weight: float
    final_score: float


class KnowledgeGap(BaseModel):
    """A detected gap in the knowledge space."""
    region_centroid: List[float]
    density: float
    suggested_topics: List[str]
    nearest_known_concepts: List[str]


class ConceptNode(BaseModel):
    """A node in the concept hierarchy."""
    label: str
    depth: int
    children: List[str] = Field(default_factory=list)
    hyperbolic_radius: float = 0.0


class GeometricReasoningService:
    """Service for geometry-guided reasoning and routing.

    Uses the geometry engine to make decisions based on
    the structure of the semantic embedding space.
    """

    def __init__(self, geometry_engine_instance: Optional[GeometryEngine] = None):
        """Initialize the geometric reasoning service.

        Args:
            geometry_engine_instance: Optional GeometryEngine to use.
                If not provided, uses the global singleton.
        """
        self._geometry_engine = geometry_engine_instance or geometry_engine
        self._agent_embeddings: Dict[str, np.ndarray] = {}
        self._agent_capabilities: Dict[str, List[str]] = {}
        self._semantic_regions: Dict[str, np.ndarray] = {}
        logger.info("GeometricReasoningService initialized")

    def register_agent(
        self,
        agent_id: str,
        capability_embedding: np.ndarray,
        capabilities: List[str]
    ) -> None:
        """Register an agent with its capability embedding.

        Args:
            agent_id: Unique agent identifier.
            capability_embedding: Vector representing agent's capabilities.
            capabilities: List of capability strings.
        """
        # Normalize the embedding for consistent distance calculations
        norm = np.linalg.norm(capability_embedding)
        if norm > 0:
            normalized = capability_embedding / norm
        else:
            normalized = capability_embedding

        self._agent_embeddings[agent_id] = normalized
        self._agent_capabilities[agent_id] = capabilities

        logger.info(
            f"Registered agent {agent_id} with {len(capabilities)} capabilities, "
            f"embedding dim={len(capability_embedding)}"
        )

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent.

        Args:
            agent_id: Agent to unregister.

        Returns:
            True if agent was removed, False if not found.
        """
        if agent_id in self._agent_embeddings:
            del self._agent_embeddings[agent_id]
            del self._agent_capabilities[agent_id]
            logger.info(f"Unregistered agent {agent_id}")
            return True
        return False

    def _compute_geodesic_distance(
        self,
        v1: np.ndarray,
        v2: np.ndarray,
        curvature: float = 0.0
    ) -> float:
        """Compute geodesic distance based on manifold curvature.

        In hyperbolic space (negative curvature), distances grow
        exponentially. In spherical space (positive curvature),
        distances are bounded. For flat space, use Euclidean.

        Args:
            v1: First vector.
            v2: Second vector.
            curvature: Manifold curvature (negative=hyperbolic, positive=spherical).

        Returns:
            Geodesic distance between vectors.
        """
        # Compute cosine similarity
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return float('inf')

        cos_sim = np.dot(v1, v2) / (norm1 * norm2)
        # Clamp to [-1, 1] to avoid numerical issues with arccos
        cos_sim = np.clip(cos_sim, -1.0, 1.0)

        if curvature < -0.1:
            # Hyperbolic distance (Poincare ball model approximation)
            # Distance grows faster for points near boundary
            euclidean_dist = np.linalg.norm(v1 - v2)
            # Scale by curvature magnitude
            k = abs(curvature)
            # Approximate hyperbolic distance
            return euclidean_dist * (1.0 + k * euclidean_dist)
        elif curvature > 0.1:
            # Spherical distance (great circle distance)
            # Bounded by pi * radius
            angle = np.arccos(cos_sim)
            return angle  # Radians on unit sphere
        else:
            # Flat/Euclidean distance
            return np.linalg.norm(v1 - v2)

    def _determine_semantic_region(
        self,
        embedding: np.ndarray,
        curvature_info: Dict[str, float]
    ) -> str:
        """Determine the semantic region of an embedding.

        Args:
            embedding: The query embedding.
            curvature_info: Curvature analysis from geometry engine.

        Returns:
            String describing the semantic region.
        """
        k = curvature_info.get("curvature_k", 0.0)
        delta = curvature_info.get("delta", 0.0)

        # Compute distance from origin (centroid of typical embeddings)
        dist_from_origin = np.linalg.norm(embedding)

        if k < -0.5:
            # Hyperbolic space - hierarchical structure
            if dist_from_origin < 0.3:
                return "hierarchical_core"
            elif dist_from_origin < 0.7:
                return "hierarchical_branch"
            else:
                return "hierarchical_leaf"
        elif k > 0.5:
            # Spherical space - clustered structure
            if dist_from_origin < 0.5:
                return "cluster_center"
            else:
                return "cluster_periphery"
        else:
            # Flat space - uniform distribution
            if delta < 0.3:
                return "dense_region"
            else:
                return "sparse_region"

    async def route_query(
        self,
        query: str,
        query_embedding: np.ndarray,
        available_agents: List[str]
    ) -> QueryRouteResult:
        """Route a query to appropriate agents based on semantic position.

        Args:
            query: The query text.
            query_embedding: Embedding vector of the query.
            available_agents: List of available agent IDs.

        Returns:
            QueryRouteResult with recommended agents and confidence.
        """
        if not available_agents:
            logger.warning("No available agents for routing")
            return QueryRouteResult(
                query=query,
                recommended_agents=[],
                confidence_scores={},
                semantic_region="unknown",
                manifold_position=query_embedding.tolist() if query_embedding is not None else None
            )

        # Filter to only registered agents that are available
        valid_agents = [
            agent_id for agent_id in available_agents
            if agent_id in self._agent_embeddings
        ]

        if not valid_agents:
            # If no registered agents available, return all available with equal scores
            logger.warning("No registered agents among available agents")
            equal_score = 1.0 / len(available_agents)
            return QueryRouteResult(
                query=query,
                recommended_agents=available_agents,
                confidence_scores={a: equal_score for a in available_agents},
                semantic_region="unknown",
                manifold_position=query_embedding.tolist() if query_embedding is not None else None
            )

        # Analyze curvature of the query region
        # Combine query embedding with agent embeddings for context
        all_embeddings = [query_embedding] + [
            self._agent_embeddings[a] for a in valid_agents
        ]
        curvature_info = self._geometry_engine.analyze_curvature(
            [e.tolist() for e in all_embeddings]
        )
        curvature = curvature_info.get("curvature_k", 0.0)

        # Determine semantic region
        semantic_region = self._determine_semantic_region(query_embedding, curvature_info)

        # Compute distances to each agent's capability embedding
        distances: Dict[str, float] = {}
        for agent_id in valid_agents:
            agent_emb = self._agent_embeddings[agent_id]
            dist = self._compute_geodesic_distance(query_embedding, agent_emb, curvature)
            distances[agent_id] = dist

        # Convert distances to confidence scores using softmax-like transformation
        # Closer agents get higher scores
        if distances:
            max_dist = max(distances.values())
            min_dist = min(distances.values())
            dist_range = max_dist - min_dist if max_dist > min_dist else 1.0

            # Invert and normalize: smaller distance = higher score
            raw_scores = {
                agent_id: np.exp(-(dist - min_dist) / (dist_range + 1e-9))
                for agent_id, dist in distances.items()
            }

            # Normalize to sum to 1
            total = sum(raw_scores.values())
            confidence_scores = {
                agent_id: score / total
                for agent_id, score in raw_scores.items()
            }
        else:
            confidence_scores = {}

        # Rank agents by confidence score
        ranked_agents = sorted(
            confidence_scores.keys(),
            key=lambda a: confidence_scores[a],
            reverse=True
        )

        logger.info(
            f"Routed query to {len(ranked_agents)} agents, "
            f"top={ranked_agents[0] if ranked_agents else 'none'}, "
            f"region={semantic_region}"
        )

        return QueryRouteResult(
            query=query,
            recommended_agents=ranked_agents,
            confidence_scores=confidence_scores,
            semantic_region=semantic_region,
            manifold_position=query_embedding.tolist()
        )

    async def weight_evidence(
        self,
        query_embedding: np.ndarray,
        evidence_items: List[Tuple[str, float, np.ndarray]]
    ) -> List[EvidenceWeight]:
        """Weight evidence items by geodesic proximity to query.

        Args:
            query_embedding: The query vector.
            evidence_items: List of (evidence_id, original_score, embedding).

        Returns:
            List of EvidenceWeight with geometric adjustments.
        """
        if not evidence_items:
            return []

        # Analyze curvature of the evidence space
        all_embeddings = [query_embedding] + [item[2] for item in evidence_items]
        curvature_info = self._geometry_engine.analyze_curvature(
            [e.tolist() for e in all_embeddings]
        )
        curvature = curvature_info.get("curvature_k", 0.0)

        results: List[EvidenceWeight] = []

        for evidence_id, original_score, embedding in evidence_items:
            # Compute geodesic distance
            geodesic_dist = self._compute_geodesic_distance(
                query_embedding, embedding, curvature
            )

            # Compute geometric weight using inverse distance weighting
            # Add small epsilon to avoid division by zero
            epsilon = 0.01
            geometric_weight = 1.0 / (geodesic_dist + epsilon)

            # Normalize weight to [0, 1] range using sigmoid-like function
            geometric_weight = 2.0 / (1.0 + np.exp(-geometric_weight)) - 1.0

            # Combine original score with geometric weight
            # Use weighted average: 60% original, 40% geometric
            alpha = 0.6
            final_score = alpha * original_score + (1 - alpha) * geometric_weight

            results.append(EvidenceWeight(
                evidence_id=evidence_id,
                original_score=original_score,
                geodesic_distance=geodesic_dist,
                geometric_weight=geometric_weight,
                final_score=final_score
            ))

        # Sort by final score descending
        results.sort(key=lambda x: x.final_score, reverse=True)

        logger.debug(
            f"Weighted {len(results)} evidence items, "
            f"curvature={curvature:.3f}"
        )

        return results

    async def detect_gaps(
        self,
        query_embedding: np.ndarray,
        knowledge_embeddings: List[np.ndarray],
        knowledge_labels: List[str]
    ) -> List[KnowledgeGap]:
        """Detect knowledge gaps relevant to a query.

        Args:
            query_embedding: The query vector.
            knowledge_embeddings: Known knowledge embeddings.
            knowledge_labels: Labels for knowledge embeddings.

        Returns:
            List of detected KnowledgeGap in query's neighborhood.
        """
        if not knowledge_embeddings or len(knowledge_embeddings) < 2:
            logger.debug("Insufficient knowledge embeddings for gap detection")
            return []

        # Stack embeddings for efficient computation
        knowledge_matrix = np.array([e for e in knowledge_embeddings])

        # Compute distances from query to all knowledge points
        distances_to_query = np.linalg.norm(
            knowledge_matrix - query_embedding, axis=1
        )

        # Find k-nearest neighbors to understand local density
        k = min(5, len(knowledge_embeddings))
        nearest_indices = np.argsort(distances_to_query)[:k]
        nearest_labels = [knowledge_labels[i] for i in nearest_indices]
        nearest_embeddings = knowledge_matrix[nearest_indices]

        # Compute local density around the query
        mean_nearest_distance = np.mean(distances_to_query[nearest_indices])

        # Compute pairwise distances among nearest neighbors
        pairwise_distances = []
        for i in range(len(nearest_embeddings)):
            for j in range(i + 1, len(nearest_embeddings)):
                pairwise_distances.append(
                    np.linalg.norm(nearest_embeddings[i] - nearest_embeddings[j])
                )

        if pairwise_distances:
            mean_pairwise = np.mean(pairwise_distances)
            std_pairwise = np.std(pairwise_distances)
        else:
            mean_pairwise = 0.0
            std_pairwise = 0.0

        gaps: List[KnowledgeGap] = []

        # Detect gap: query is far from nearest neighbors compared to their spread
        density = 1.0 / (mean_nearest_distance + 0.01)

        # Threshold for gap detection: query distance > 2x mean pairwise distance
        gap_threshold = max(mean_pairwise * 2, 0.5)

        if mean_nearest_distance > gap_threshold:
            # Found a potential gap
            # Compute centroid of the gap region (midpoint between query and nearest)
            gap_centroid = (query_embedding + nearest_embeddings[0]) / 2

            # Suggest topics based on interpolation direction
            # Direction from nearest concept toward query
            direction = query_embedding - nearest_embeddings[0]
            direction_norm = np.linalg.norm(direction)

            if direction_norm > 0:
                # Find concepts along this direction
                similarities_to_direction = []
                for i, emb in enumerate(knowledge_matrix):
                    vec_to_emb = emb - nearest_embeddings[0]
                    if np.linalg.norm(vec_to_emb) > 0:
                        cos_sim = np.dot(direction, vec_to_emb) / (
                            direction_norm * np.linalg.norm(vec_to_emb)
                        )
                        similarities_to_direction.append((i, cos_sim))

                # Sort by similarity to direction
                similarities_to_direction.sort(key=lambda x: x[1], reverse=True)

                # Suggest topics from concepts most aligned with gap direction
                suggested_indices = [idx for idx, _ in similarities_to_direction[:3]]
                suggested_topics = [
                    f"between_{nearest_labels[0]}_and_{knowledge_labels[idx]}"
                    for idx in suggested_indices
                    if idx < len(knowledge_labels)
                ]
            else:
                suggested_topics = [f"expand_{nearest_labels[0]}"]

            gaps.append(KnowledgeGap(
                region_centroid=gap_centroid.tolist(),
                density=density,
                suggested_topics=suggested_topics[:3],
                nearest_known_concepts=nearest_labels
            ))

        logger.info(
            f"Detected {len(gaps)} knowledge gaps, "
            f"local_density={density:.3f}"
        )

        return gaps

    async def analyze_concept_hierarchy(
        self,
        embeddings: List[np.ndarray],
        labels: List[str]
    ) -> Dict[str, Any]:
        """Analyze hyperbolic structure to detect concept hierarchies.

        In hyperbolic space, more general/abstract concepts tend to
        be closer to the origin, while specific concepts are at the
        periphery. This method uses that property to infer hierarchy.

        Args:
            embeddings: Concept embeddings.
            labels: Concept labels.

        Returns:
            Hierarchy dict with parent-child relationships.
        """
        if not embeddings or len(embeddings) < 2:
            return {
                "root": None,
                "nodes": {},
                "depth_map": {},
                "curvature_info": {}
            }

        # Analyze curvature to determine if hierarchical structure exists
        curvature_info = self._geometry_engine.analyze_curvature(
            [e.tolist() for e in embeddings]
        )
        curvature = curvature_info.get("curvature_k", 0.0)

        # Compute distance from origin (centroid) for each concept
        centroid = np.mean(embeddings, axis=0)
        radii = [np.linalg.norm(e - centroid) for e in embeddings]

        # Create nodes with hyperbolic radius
        nodes: Dict[str, ConceptNode] = {}
        for i, (label, radius) in enumerate(zip(labels, radii)):
            nodes[label] = ConceptNode(
                label=label,
                depth=0,  # Will be computed
                hyperbolic_radius=radius
            )

        # Sort by radius (smaller radius = more general = closer to root)
        sorted_concepts = sorted(
            range(len(labels)),
            key=lambda i: radii[i]
        )

        # Assign depths based on radius quantiles
        n = len(sorted_concepts)
        for rank, idx in enumerate(sorted_concepts):
            label = labels[idx]
            # Map rank to depth (0 = root level, higher = more specific)
            depth = int(rank * 4 / n)  # 4 depth levels
            nodes[label].depth = depth

        # Build parent-child relationships
        # For each concept, find the nearest concept with lower depth
        for i, (label, embedding) in enumerate(zip(labels, embeddings)):
            node = nodes[label]
            if node.depth == 0:
                continue  # Root level has no parent

            # Find potential parents (concepts with lower depth)
            best_parent = None
            best_distance = float('inf')

            for j, (other_label, other_embedding) in enumerate(zip(labels, embeddings)):
                if i == j:
                    continue
                other_node = nodes[other_label]
                if other_node.depth < node.depth:
                    dist = self._compute_geodesic_distance(
                        embedding, other_embedding, curvature
                    )
                    if dist < best_distance:
                        best_distance = dist
                        best_parent = other_label

            if best_parent:
                nodes[best_parent].children.append(label)

        # Find root (lowest radius concept)
        root_idx = sorted_concepts[0]
        root_label = labels[root_idx]

        # Build depth map
        depth_map: Dict[int, List[str]] = {}
        for label, node in nodes.items():
            if node.depth not in depth_map:
                depth_map[node.depth] = []
            depth_map[node.depth].append(label)

        # Convert nodes to serializable dict
        nodes_dict = {
            label: {
                "label": node.label,
                "depth": node.depth,
                "children": node.children,
                "hyperbolic_radius": node.hyperbolic_radius
            }
            for label, node in nodes.items()
        }

        logger.info(
            f"Analyzed hierarchy: {len(nodes)} concepts, "
            f"max_depth={max(depth_map.keys()) if depth_map else 0}, "
            f"root={root_label}"
        )

        return {
            "root": root_label,
            "nodes": nodes_dict,
            "depth_map": {str(k): v for k, v in depth_map.items()},
            "curvature_info": curvature_info
        }

    def define_semantic_region(
        self,
        region_name: str,
        centroid_embedding: np.ndarray
    ) -> None:
        """Define a named semantic region for routing.

        Args:
            region_name: Name of the region.
            centroid_embedding: Center of the region.
        """
        norm = np.linalg.norm(centroid_embedding)
        if norm > 0:
            self._semantic_regions[region_name] = centroid_embedding / norm
        else:
            self._semantic_regions[region_name] = centroid_embedding

        logger.debug(f"Defined semantic region: {region_name}")

    def get_nearest_region(
        self,
        embedding: np.ndarray
    ) -> Optional[Tuple[str, float]]:
        """Find the nearest defined semantic region.

        Args:
            embedding: Query embedding.

        Returns:
            Tuple of (region_name, distance) or None if no regions defined.
        """
        if not self._semantic_regions:
            return None

        best_region = None
        best_distance = float('inf')

        for region_name, centroid in self._semantic_regions.items():
            dist = np.linalg.norm(embedding - centroid)
            if dist < best_distance:
                best_distance = dist
                best_region = region_name

        return (best_region, best_distance) if best_region else None

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics.

        Returns:
            Dictionary with service statistics.
        """
        return {
            "registered_agents": len(self._agent_embeddings),
            "total_capabilities": sum(
                len(c) for c in self._agent_capabilities.values()
            ),
            "defined_regions": len(self._semantic_regions),
            "agent_ids": list(self._agent_embeddings.keys()),
        }


# Global singleton
geometric_reasoning = GeometricReasoningService()
