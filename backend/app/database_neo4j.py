"""
Neo4j Knowledge Graph Storage with Hybrid Parent/Local Support.

Mirrors the dual Supabase pattern:
- Primary: Parent Neo4j on pmoves_data network (shared knowledge with Hi-RAG)
- Fallback: Local Neo4j container for resilience and DoX-specific graphs
- Write Strategy: Dual write to both for backup

Environment Variables:
    NEO4J_PARENT_URI: Bolt URI for parent Neo4j (default: bolt://pmoves-neo4j-1:7687)
    NEO4J_PARENT_USER: Username for parent Neo4j (default: neo4j)
    NEO4J_PARENT_PASSWORD: Password for parent Neo4j (required for parent connection)
    NEO4J_LOCAL_URI: Bolt URI for local Neo4j (default: bolt://neo4j:7687)
    NEO4J_LOCAL_USER: Username for local Neo4j (default: neo4j)
    NEO4J_LOCAL_PASSWORD: Password for local Neo4j (required)
    NEO4J_ENABLED: Enable Neo4j integration (default: true)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

try:  # pragma: no cover - neo4j driver optional
    from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
except Exception:  # pragma: no cover
    AsyncGraphDatabase = None  # type: ignore
    AsyncDriver = Any  # type: ignore
    AsyncSession = Any  # type: ignore


LOGGER = logging.getLogger(__name__)


class Neo4jUnavailable(RuntimeError):
    """Raised when Neo4j driver is not available or connection fails."""


class Neo4jManager:
    """
    Hybrid Neo4j manager with parent fallback.

    Connection Strategy:
        1. Try connecting to parent Neo4j on pmoves_data network
        2. Fallback to local Neo4j container
        3. Dual-write for data redundancy

    Usage:
        neo4j = Neo4jManager()
        await neo4j.connect()
        await neo4j.store_entities(document_id, entities)
        graph = await neo4j.get_entity_graph(document_id)
    """

    def __init__(
        self,
        parent_uri: Optional[str] = None,
        parent_user: Optional[str] = None,
        parent_password: Optional[str] = None,
        local_uri: Optional[str] = None,
        local_user: Optional[str] = None,
        local_password: Optional[str] = None,
    ) -> None:
        """
        Initialize Neo4j manager with parent and local connection config.

        Args:
            parent_uri: Bolt URI for parent Neo4j (from pmoves_data network)
            parent_user: Username for parent Neo4j
            parent_password: Password for parent Neo4j
            local_uri: Bolt URI for local Neo4j container
            local_user: Username for local Neo4j
            local_password: Password for local Neo4j

        Raises:
            Neo4jUnavailable: If neo4j driver is not installed

        Environment Variables (used as fallbacks):
            NEO4J_PARENT_URI, NEO4J_PARENT_USER, NEO4J_PARENT_PASSWORD
            NEO4J_LOCAL_URI, NEO4J_LOCAL_USER, NEO4J_LOCAL_PASSWORD
            NEO4J_ENABLED
        """
        if AsyncGraphDatabase is None:
            raise Neo4jUnavailable(
                "neo4j driver not available; install `neo4j>=5.0.0` and retry"
            )

        # Parent Neo4j configuration (shared with PMOVES.AI)
        self.parent_uri = parent_uri or os.getenv(
            "NEO4J_PARENT_URI", "bolt://pmoves-neo4j-1:7687"
        )
        self.parent_user = parent_user or os.getenv(
            "NEO4J_PARENT_USER", "neo4j"
        )
        self.parent_password = parent_password or os.getenv(
            "NEO4J_PARENT_PASSWORD", ""
        )

        # Local Neo4j configuration (DoX-specific)
        self.local_uri = local_uri or os.getenv(
            "NEO4J_LOCAL_URI", "bolt://neo4j:7687"
        )
        self.local_user = local_user or os.getenv(
            "NEO4J_LOCAL_USER", "neo4j"
        )
        self.local_password = local_password or os.getenv(
            "NEO4J_LOCAL_PASSWORD", ""
        )

        # Driver instances
        self.parent_driver: Optional[AsyncDriver] = None
        self.local_driver: Optional[AsyncDriver] = None

        # Connection state
        self.use_parent: bool = False
        self.connected: bool = False

        # Enabled check
        self._enabled = os.getenv("NEO4J_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def is_enabled(self) -> bool:
        """
        Check if Neo4j integration is enabled.

        Returns:
            True if NEO4J_ENABLED environment variable is set to a truthy value
        """
        return self._enabled

    async def connect(self) -> Dict[str, Any]:
        """
        Connect to parent Neo4j, fallback to local.

        Returns:
            Connection status dict with keys:
                - parent_connected: bool
                - local_connected: bool
                - active: "parent" | "local" | "none"
        """
        if not self._enabled:
            LOGGER.info("Neo4j integration disabled via NEO4J_ENABLED")
            return {
                "parent_connected": False,
                "local_connected": False,
                "active": "disabled",
            }

        status = {
            "parent_connected": False,
            "local_connected": False,
            "active": "none",
        }

        # Try parent Neo4j first
        if not self.parent_password:
            LOGGER.warning(
                "Parent Neo4j password not configured (NEO4J_PARENT_PASSWORD empty). "
                "Skipping parent connection, using local Neo4j only. "
                "Set NEO4J_PARENT_PASSWORD to enable hybrid mode."
            )

        if self.parent_password:
            try:
                self.parent_driver = AsyncGraphDatabase.driver(
                    self.parent_uri,
                    auth=(self.parent_user, self.parent_password),
                    max_connection_lifetime=3600,
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=60,
                )
                # Test connection
                async with self.parent_driver.session() as session:
                    await session.run("RETURN 1")
                self.use_parent = True
                self.connected = True
                status["parent_connected"] = True
                status["active"] = "parent"
                LOGGER.info("Connected to parent Neo4j at %s", self.parent_uri)
            except Exception as exc:
                LOGGER.warning(
                    "Parent Neo4j unavailable at %s: %s", self.parent_uri, exc
                )
                if self.parent_driver:
                    await self.parent_driver.close()
                    self.parent_driver = None

        # Fallback to local Neo4j
        if not self.connected:
            if not self.local_password:
                LOGGER.error(
                    "Local Neo4j password not configured (NEO4J_LOCAL_PASSWORD empty). "
                    "Cannot connect to any Neo4j instance. "
                    "Set NEO4J_LOCAL_PASSWORD in .env.local to enable knowledge graph."
                )
                raise Neo4jUnavailable("No Neo4j credentials configured")
            try:
                self.local_driver = AsyncGraphDatabase.driver(
                    self.local_uri,
                    auth=(self.local_user, self.local_password),
                    max_connection_lifetime=3600,
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=60,
                )
                # Test connection
                async with self.local_driver.session() as session:
                    await session.run("RETURN 1")
                self.connected = True
                status["local_connected"] = True
                status["active"] = "local"
                LOGGER.info("Connected to local Neo4j at %s", self.local_uri)
            except Exception as exc:
                LOGGER.warning(
                    "Local Neo4j unavailable at %s: %s", self.local_uri, exc
                )
                if self.local_driver:
                    await self.local_driver.close()
                    self.local_driver = None

        # If parent connected, also establish local for dual-write
        if self.use_parent and self.parent_driver:
            try:
                self.local_driver = AsyncGraphDatabase.driver(
                    self.local_uri,
                    auth=(self.local_user, self.local_password),
                    max_connection_lifetime=3600,
                    max_connection_pool_size=50,
                )
                async with self.local_driver.session() as session:
                    await session.run("RETURN 1")
                status["local_connected"] = True
                LOGGER.info("Local Neo4j also available for dual-write")
            except Exception as exc:
                LOGGER.info("Local Neo4j not available for dual-write: %s", exc)

        return status

    async def close(self) -> None:
        """
        Close all driver connections.

        Closes both parent and local Neo4j drivers if they are active.
        Sets connected flag to False.
        """
        if self.parent_driver:
            await self.parent_driver.close()
            self.parent_driver = None
        if self.local_driver:
            await self.local_driver.close()
            self.local_driver = None
        self.connected = False

    def _get_driver(self) -> AsyncDriver:
        """
        Get the active driver for operations.

        Returns:
            The parent driver if use_parent is True, otherwise the local driver

        Raises:
            Neo4jUnavailable: If not connected to any Neo4j instance
        """
        if not self.connected:
            raise Neo4jUnavailable("Not connected to Neo4j")
        if self.use_parent and self.parent_driver:
            return self.parent_driver
        if self.local_driver:
            return self.local_driver
        raise Neo4jUnavailable("No active Neo4j connection")

    async def _dual_write(
        self, query: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute query on both parent and local Neo4j (dual-write strategy).

        Executes the query on the primary driver (parent if available, else local)
        and also on the secondary driver for backup. Logs errors from secondary
        without failing the operation.

        Args:
            query: Cypher query string to execute
            params: Query parameters

        Returns:
            List of result records from the primary driver execution
        """
        primary = self.parent_driver if self.use_parent else self.local_driver
        secondary = self.local_driver if self.use_parent else None

        results = []
        # Execute on primary
        if primary:
            async with primary.session() as session:
                result = await session.run(query, params)
                results = [record async for record in result]

        # Dual-write to secondary if available
        if secondary:
            try:
                async with secondary.session() as session:
                    await session.run(query, params)
            except Exception as exc:
                # ERROR level: dual-write failure means backup not saved
                # This is critical for data durability
                backend_type = "local" if self.use_parent else "parent"
                query_preview = query[:100] + "..." if len(query) > 100 else query
                LOGGER.error(
                    "Neo4j dual-write to %s backend failed: %s. Query preview: %s",
                    backend_type,
                    exc,
                    query_preview,
                )

        return results

    # ------------------------------------------------------------------ Entity Graph

    async def store_entities(
        self,
        document_id: str,
        entities: List[Dict[str, Any]],
        max_distance: int = 500,
        min_weight: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Store document entities as graph nodes with relationships.

        Creates:
        - Document node with metadata
        - Entity nodes for each extracted entity
        - CONTAINS relationships between document and entities
        - RELATED_TO relationships between co-occurring entities

        Args:
            document_id: Document identifier
            entities: List of entity dicts with keys:
                - text: Entity text
                - label: Entity type (PERSON, ORG, LOC, etc.)
                - start_char, end_char: Position in document
                - page: Page number
                - context: Surrounding text
            max_distance: Maximum character distance for relationship discovery
                (entities within this distance are considered related)
            min_weight: Minimum relationship weight threshold (0.0-1.0)

        Returns:
            Dict with node_count, edge_count stored
        """
        if not self.connected:
            raise Neo4jUnavailable("Not connected to Neo4j")

        # Create document node
        doc_query = """
        MERGE (d:Document {id: $doc_id})
        SET d.last_updated = datetime(), d.entity_count = $count
        """
        await self._dual_write(doc_query, {"doc_id": document_id, "count": len(entities)})

        node_count = 0
        edge_count = 0

        # Batch create entity nodes and CONTAINS relationships
        for entity in entities:
            entity_id = entity.get("id") or str(uuid4())
            entity_text = entity.get("text", "")
            entity_label = entity.get("label", "UNKNOWN")
            entity_context = entity.get("context", "")
            entity_page = entity.get("page")
            start_char = entity.get("start_char")
            end_char = entity.get("end_char")

            # Create entity node
            entity_query = """
            MERGE (e:Entity {id: $id})
            SET e.text = $text, e.type = $type, e.context = $context,
                e.page = $page, e.start_char = $start_char, e.end_char = $end_char,
                e.last_seen = datetime()
            WITH e
            MATCH (d:Document {id: $doc_id})
            MERGE (d)-[:CONTAINS]->(e)
            """
            await self._dual_write(
                entity_query,
                {
                    "id": entity_id,
                    "text": entity_text,
                    "type": entity_label,
                    "context": entity_context,
                    "page": entity_page,
                    "start_char": start_char,
                    "end_char": end_char,
                    "doc_id": document_id,
                },
            )
            node_count += 1
            edge_count += 1

        # Auto-discover relationships between entities
        # Create RELATED_TO edges for entities of same type appearing near each other
        # Uses max_distance and min_weight parameters for configurable relationship discovery
        rel_query = """
        MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(e1:Entity),
              (d)-[:CONTAINS]->(e2:Entity)
        WHERE e1.type = e2.type AND e1.id < e2.id
        WITH e1, e2,
             abs(e1.start_char - e2.start_char) as distance,
             size(e1.text) + size(e2.text) as total_length
        WHERE distance < $max_distance
        WITH e1, e2, distance, (1.0 - (distance / $max_distance)) as calculated_weight
        WHERE calculated_weight >= $min_weight
        MERGE (e1)-[r:RELATED_TO]-(e2)
        SET r.proximity = distance, r.weight = calculated_weight
        """
        await self._dual_write(
            rel_query,
            {"doc_id": document_id, "max_distance": max_distance, "min_weight": min_weight}
        )

        return {
            "document_id": document_id,
            "node_count": node_count,
            "edge_count": edge_count,
        }

    async def get_entity_graph(
        self, document_id: str
    ) -> Dict[str, Any]:
        """
        Get entity graph for visualization.

        Returns nodes and edges in format suitable for vis-network:
        - nodes: List of {id, label, type, x, y}
        - edges: List of {from, to, label, weight}

        Args:
            document_id: Document identifier

        Returns:
            Dict with nodes, edges lists
        """
        if not self.connected:
            return {"nodes": [], "edges": [], "error": "Not connected to Neo4j"}

        # Get all entities in document with relationships
        query = """
        MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(e:Entity)
        OPTIONAL MATCH (e)-[r:RELATED_TO]-(other:Entity)
        RETURN e as entity, collect({to: other.id, weight: r.weight, proximity: r.proximity}) as relationships
        """
        try:
            driver = self._get_driver()
            async with driver.session() as session:
                result = await session.run(query, {"doc_id": document_id})
                records = [record async for record in result]

            nodes = []
            edges = []
            seen_edges = set()

            for record in records:
                entity = record.get("entity")
                if not entity:
                    continue

                entity_id = entity.get("id")
                nodes.append({
                    "id": entity_id,
                    "label": entity.get("text", ""),
                    "type": entity.get("type", "UNKNOWN"),
                    "title": f"{entity.get('type')}: {entity.get('text')}\nPage: {entity.get('page')}",
                })

                # Add relationships
                for rel in record.get("relationships", []):
                    to_id = rel.get("to")
                    if not to_id:
                        continue

                    # Avoid duplicate edges
                    edge_key = tuple(sorted([entity_id, to_id]))
                    if edge_key in seen_edges:
                        continue
                    seen_edges.add(edge_key)

                    edges.append({
                        "from": entity_id,
                        "to": to_id,
                        "weight": rel.get("weight", 0.5),
                        "title": f"Proximity: {rel.get('proximity', 0)}",
                    })

            return {
                "nodes": nodes,
                "edges": edges,
                "document_id": document_id,
            }
        except Exception as exc:
            LOGGER.error("Failed to get entity graph: %s", exc)
            return {"nodes": [], "edges": [], "error": str(exc)}

    async def query_graph(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute arbitrary Cypher query.

        Args:
            query: Cypher query string
            params: Query parameters

        Returns:
            List of result records as dicts
        """
        if not self.connected:
            raise Neo4jUnavailable("Not connected to Neo4j")

        driver = self._get_driver()
        async with driver.session() as session:
            result = await session.run(query, params or {})
            return [dict(record) async for record in result]

    async def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search for entities by text or type.

        Args:
            query: Text to search for (case-insensitive partial match)
            entity_type: Filter by entity type
            limit: Max results

        Returns:
            List of matching entities with documents

        Raises:
            Neo4jUnavailable: If not connected to Neo4j
        """
        if not self.connected:
            raise Neo4jUnavailable("Not connected to Neo4j")

        cypher = """
        MATCH (e:Entity)
        WHERE e.text CONTAINS $query
        """
        params = {"query": query}

        if entity_type:
            cypher += " AND e.type = $entity_type"
            params["entity_type"] = entity_type

        cypher += """
        OPTIONAL MATCH (e)<-[:CONTAINS]-(d:Document)
        RETURN e, collect(d.id) as document_ids
        LIMIT $limit
        """
        params["limit"] = limit

        return await self.query_graph(cypher, params)

    async def get_document_entities(
        self, document_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all entities for a document.

        Args:
            document_id: Document identifier

        Returns:
            List of entity dicts

        Raises:
            Neo4jUnavailable: If not connected to Neo4j
        """
        if not self.connected:
            raise Neo4jUnavailable("Not connected to Neo4j")

        query = """
        MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(e:Entity)
        RETURN e
        ORDER BY e.start_char
        """

        driver = self._get_driver()
        async with driver.session() as session:
            result = await session.run(query, {"doc_id": document_id})
            return [dict(record.get("e")) async for record in result]

    async def find_entity_connections(
        self,
        entity_id: str,
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """
        Find all connected entities up to max_depth.

        Args:
            entity_id: Starting entity ID
            max_depth: Maximum hop distance (default: 2)

        Returns:
            Dict with nodes, edges representing the connection graph
        """
        if not self.connected:
            return {"nodes": [], "edges": []}

        query = f"""
        MATCH path = (e:Entity {{id: $entity_id}})-[*1..{max_depth}]-(connected:Entity)
        WITH nodes(path) as path_nodes, relationships(path) as path_rels
        UNWIND path_nodes as node
        UNWIND path_rels as rel
        RETURN DISTINCT node, collect(DISTINCT rel) as rels
        """

        try:
            driver = self._get_driver()
            async with driver.session() as session:
                result = await session.run(query, {"entity_id": entity_id})
                records = [record async for record in result]

            nodes = []
            edges = set()

            for record in records:
                node = record.get("node")
                if node:
                    nodes.append({
                        "id": node.get("id"),
                        "label": node.get("text", ""),
                        "type": node.get("type", "UNKNOWN"),
                    })

                for rel in record.get("rels", []):
                    if hasattr(rel, "start_node") and hasattr(rel, "end_node"):
                        start = rel.start_node.get("id") if hasattr(rel.start_node, "get") else None
                        end = rel.end_node.get("id") if hasattr(rel.end_node, "get") else None
                        if start and end:
                            edges.add(tuple(sorted([start, end])))

            return {
                "nodes": nodes,
                "edges": [{"from": e[0], "to": e[1]} for e in edges],
            }
        except Exception as exc:
            LOGGER.error("Failed to find entity connections: %s", exc)
            return {"nodes": [], "edges": []}

    async def delete_document_graph(self, document_id: str) -> None:
        """
        Delete all graph data for a document.

        Args:
            document_id: Document identifier
        """
        if not self.connected:
            return

        query = """
        MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(e:Entity)
        DETACH DELETE e
        """
        await self._dual_write(query, {"doc_id": document_id})

        # Delete document node
        doc_query = """
        MATCH (d:Document {id: $doc_id})
        DELETE d
        """
        await self._dual_write(doc_query, {"doc_id": document_id})

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Neo4j connectivity and status.

        Returns:
            Dict with connection status and basic stats
        """
        status = {
            "enabled": self._enabled,
            "connected": self.connected,
            "active": "parent" if self.use_parent else "local" if self.connected else "none",
            "parent_connected": self.parent_driver is not None,
            "local_connected": self.local_driver is not None,
        }

        if self.connected:
            try:
                # Get basic stats
                stats = await self.query_graph("""
                    MATCH (d:Document) RETURN count(d) as doc_count
                """)
                doc_count = stats[0].get("doc_count", 0) if stats else 0

                entity_stats = await self.query_graph("""
                    MATCH (e:Entity) RETURN count(e) as entity_count
                """)
                entity_count = entity_stats[0].get("entity_count", 0) if entity_stats else 0

                status["doc_count"] = doc_count
                status["entity_count"] = entity_count
            except Exception as exc:
                status["error"] = str(exc)

        return status


# Singleton instance for reuse across requests
_neo4j_instance: Optional[Neo4jManager] = None


async def get_neo4j() -> Neo4jManager:
    """
    Get or create the Neo4j manager singleton.

    Returns:
        The shared Neo4jManager instance, connecting on first access

    Note:
        This function maintains a singleton instance across requests.
        Automatically reconnects if the connection was lost.
    """
    global _neo4j_instance
    if _neo4j_instance is None:
        _neo4j_instance = Neo4jManager()
        await _neo4j_instance.connect()
    elif not _neo4j_instance.connected:
        await _neo4j_instance.connect()
    return _neo4j_instance
