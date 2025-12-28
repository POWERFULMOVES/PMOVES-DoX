"""
Knowledge Graph API Router.

Provides endpoints for Neo4j knowledge graph operations:
- Entity graph visualization
- Entity storage and retrieval
- Relationship discovery
- Graph search

Endpoints:
    GET  /graph/health          - Check Neo4j connectivity
    GET  /graph/{document_id}   - Get entity graph for document
    POST /graph/{document_id}/entities  - Store entities in graph
    GET  /graph/search          - Search for entities
    GET  /graph/{entity_id}/connections  - Find connected entities
    DELETE /graph/{document_id}  - Delete document graph
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, field_validator

from app.database_neo4j import Neo4jManager, get_neo4j, Neo4jUnavailable


LOGGER = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["graph"])


# Valid entity types (spaCy NER types)
VALID_ENTITY_TYPES = {
    "PERSON", "ORG", "LOC", "DATE", "PRODUCT", "GPE", "EVENT",
    "WORK_OF_ART", "LAW", "LANGUAGE", "NORP", "PERCENT", "MONEY",
    "QUANTITY", "ORDINAL", "CARDINAL", "TIME", "FAC", "ORG",
}


# ------------------------------------------------------------------ Request Models


class EntityRequest(BaseModel):
    """
    Entity data for storage in Neo4j knowledge graph.

    Attributes:
        id: Optional unique identifier (auto-generated if not provided)
        text: The entity text content (e.g., "Apple Inc.")
        label: Entity type (PERSON, ORG, LOC, DATE, PRODUCT, GPE, etc.)
        start_char: Starting character position in source document
        end_char: Ending character position in source document
        page: Page number where entity was found
        context: Surrounding text for additional context
        source_index: Index of the source in multi-source documents

    Raises:
        ValueError: If start_char >= end_char (invalid span)
        ValueError: If label is not a valid entity type
    """

    id: Optional[str] = None
    text: str
    label: str  # Entity type: PERSON, ORG, LOC, etc.
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    page: Optional[int] = None
    context: Optional[str] = None
    source_index: Optional[int] = None

    @field_validator("label")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Validate that the entity label is a known type."""
        if not v or v.strip() == "":
            raise ValueError("Entity label cannot be empty")
        # Normalize to uppercase for consistency
        v_upper = v.strip().upper()
        if v_upper not in VALID_ENTITY_TYPES:
            # Allow custom types but warn - log this in production
            valid_list = ", ".join(sorted(VALID_ENTITY_TYPES))
            LOGGER.warning(
                "Unknown entity type '%s' (valid types: %s). "
                "Using custom type.",
                v,
                valid_list
            )
        return v_upper

    @field_validator("start_char", "end_char")
    @classmethod
    def validate_span(cls, start_char: Optional[int], info) -> Optional[int]:
        """Validate that start_char < end_char when both are provided."""
        # Get the field name being validated
        field_name = info.field_name
        # Get all values to check the relationship
        values = info.data
        if field_name == "end_char" and start_char is not None:
            start = values.get("start_char")
            if start is not None and start >= start_char:
                raise ValueError(
                    f"end_char ({start_char}) must be greater than start_char ({start})"
                )
        return start_char

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate that entity text is not empty or just whitespace."""
        if not v or v.strip() == "":
            raise ValueError("Entity text cannot be empty or whitespace")
        return v.strip()


class EntityListRequest(BaseModel):
    """
    Request model for bulk entity storage with relationship discovery.

    Attributes:
        entities: List of entities to store in the knowledge graph
        max_distance: Maximum character distance for relationship discovery
        min_weight: Minimum relationship weight threshold
    """

    entities: List[EntityRequest]
    max_distance: int = 500  # Character distance for co-occurrence
    min_weight: float = 0.1  # Minimum relationship weight


class GraphSearchRequest(BaseModel):
    """
    Request model for searching the knowledge graph.

    Attributes:
        query: Text to search for (case-insensitive partial match)
        entity_type: Optional filter by entity type (PERSON, ORG, etc.)
        limit: Maximum number of results to return (default: 20)
    """

    query: str
    entity_type: Optional[str] = None
    limit: int = 20


class RelationshipDiscoveryRequest(BaseModel):
    """
    Request model for auto-discovering entity relationships.

    Attributes:
        max_distance: Maximum character distance for co-occurrence (default: 500)
        min_weight: Minimum relationship weight threshold (default: 0.1)
    """

    max_distance: int = 500  # Character distance for co-occurrence
    min_weight: float = 0.1  # Minimum relationship weight


# ------------------------------------------------------------------ Endpoints


@router.get("/health", response_model=Dict[str, Any])
async def graph_health() -> Dict[str, Any]:
    """
    Check Neo4j connectivity and status.

    Returns:
        {
            "enabled": bool,
            "connected": bool,
            "active": "parent" | "local" | "none",
            "doc_count": int,
            "entity_count": int
        }
    """
    try:
        neo4j = await get_neo4j()
        health = await neo4j.health_check()
        return health
    except Neo4jUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Neo4j unavailable", "message": str(exc)},
        )
    except Exception as exc:
        LOGGER.error("Graph health check failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Health check failed", "message": str(exc)},
        )


@router.get("/search", response_model=Dict[str, Any])
async def search_graph(
    query: str,
    entity_type: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Search knowledge graph for entities.

    NOTE: This route must be defined BEFORE parameterized routes like /{document_id}
    to ensure "/search" is matched literally rather than as a document_id.

    Args:
        query: Text to search for (partial match)
        entity_type: Filter by entity type (PERSON, ORG, etc.)
        limit: Maximum results

    Returns:
        List of matching entities with document IDs
    """
    if not query or len(query.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Query must be at least 2 characters"},
        )

    try:
        neo4j = await get_neo4j()
        results = await neo4j.search_entities(
            query=query.strip(),
            entity_type=entity_type,
            limit=limit,
        )

        return {
            "query": query,
            "entity_type": entity_type,
            "results": results,
            "count": len(results),
        }
    except Neo4jUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Neo4j unavailable", "message": str(exc)},
        )
    except Exception as exc:
        LOGGER.error("Failed to search graph: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Search failed", "message": str(exc)},
        )


@router.get("/{document_id}", response_model=Dict[str, Any])
async def get_entity_graph(document_id: str) -> Dict[str, Any]:
    """
    Get entity graph for document visualization.

    Returns nodes and edges in vis-network format:
    {
        "nodes": [{"id", "label", "type", "title"}, ...],
        "edges": [{"from", "to", "weight", "title"}, ...],
        "document_id": str
    }

    Args:
        document_id: Document identifier

    Returns:
        Graph data for visualization
    """
    try:
        neo4j = await get_neo4j()
        graph = await neo4j.get_entity_graph(document_id)

        if not graph.get("nodes"):
            return {
                "nodes": [],
                "edges": [],
                "document_id": document_id,
                "message": "No entities found for document",
            }

        return graph
    except Neo4jUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Neo4j unavailable", "message": str(exc)},
        )
    except Exception as exc:
        LOGGER.error("Failed to get entity graph: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to get graph", "message": str(exc)},
        )


@router.post("/{document_id}/entities", response_model=Dict[str, Any])
async def store_entity_graph(
    document_id: str, request: EntityListRequest
) -> Dict[str, Any]:
    """
    Store entities in Neo4j knowledge graph.

    Creates:
    - Document node with metadata
    - Entity nodes for each entity
    - CONTAINS relationships (document -> entities)
    - RELATED_TO relationships (between co-occurring entities)

    Args:
        document_id: Document identifier
        request: Entity list with metadata and relationship discovery parameters

    Returns:
        {
            "document_id": str,
            "node_count": int,
            "edge_count": int,
            "status": "stored"
        }
    """
    try:
        neo4j = await get_neo4j()

        # Convert pydantic models to dicts
        entities = [entity.model_dump() for entity in request.entities]

        result = await neo4j.store_entities(
            document_id,
            entities,
            max_distance=request.max_distance,
            min_weight=request.min_weight,
        )

        return {
            **result,
            "status": "stored",
        }
    except Neo4jUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Neo4j unavailable", "message": str(exc)},
        )
    except Exception as exc:
        LOGGER.error("Failed to store entities: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to store entities", "message": str(exc)},
        )


@router.post("/{document_id}/relationships", response_model=Dict[str, Any])
async def discover_relationships(
    document_id: str, request: RelationshipDiscoveryRequest
) -> Dict[str, Any]:
    """
    Auto-discover relationships between entities.

    Creates RELATED_TO edges based on:
    - Co-occurrence proximity (entities within max_distance chars)
    - Same entity type clustering

    Args:
        document_id: Document identifier
        request: Discovery parameters

    Returns:
        Number of relationships discovered
    """
    try:
        neo4j = await get_neo4j()

        # Get existing entities
        entities = await neo4j.get_document_entities(document_id)

        if not entities:
            return {
                "document_id": document_id,
                "relationships_found": 0,
                "message": "No entities found for relationship discovery",
            }

        # Re-store entities to trigger relationship discovery
        entity_dicts = [
            {
                "id": e.get("id"),
                "text": e.get("text"),
                "label": e.get("type"),
                "start_char": e.get("start_char"),
                "end_char": e.get("end_char"),
                "page": e.get("page"),
                "context": e.get("context"),
            }
            for e in entities
        ]

        result = await neo4j.store_entities(document_id, entity_dicts)

        return {
            **result,
            "document_id": document_id,
            "status": "relationships_discovered",
        }
    except Neo4jUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Neo4j unavailable", "message": str(exc)},
        )
    except Exception as exc:
        LOGGER.error("Failed to discover relationships: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to discover relationships", "message": str(exc)},
        )


@router.get("/{entity_id}/connections", response_model=Dict[str, Any])
async def get_entity_connections(
    entity_id: str, max_depth: int = 2
) -> Dict[str, Any]:
    """
    Find all connected entities up to max_depth hops.

    Useful for exploring entity relationships and context.

    Args:
        entity_id: Starting entity ID
        max_depth: Maximum hop distance (1-3, default: 2)

    Returns:
        {
            "nodes": [{"id", "label", "type"}, ...],
            "edges": [{"from", "to"}, ...]
        }
    """
    if max_depth < 1 or max_depth > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "max_depth must be between 1 and 3"},
        )

    try:
        neo4j = await get_neo4j()
        connections = await neo4j.find_entity_connections(
            entity_id=entity_id,
            max_depth=max_depth,
        )

        return {
            **connections,
            "entity_id": entity_id,
            "max_depth": max_depth,
        }
    except Neo4jUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Neo4j unavailable", "message": str(exc)},
        )
    except Exception as exc:
        LOGGER.error("Failed to get entity connections: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to get connections", "message": str(exc)},
        )


@router.get("/{document_id}/entities", response_model=List[Dict[str, Any]])
async def get_document_entities(document_id: str) -> List[Dict[str, Any]]:
    """
    Get all entities for a document.

    Returns raw entity data without graph structure.

    Args:
        document_id: Document identifier

    Returns:
        List of entity dicts
    """
    try:
        neo4j = await get_neo4j()
        entities = await neo4j.get_document_entities(document_id)
        return entities
    except Neo4jUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Neo4j unavailable", "message": str(exc)},
        )
    except Exception as exc:
        LOGGER.error("Failed to get document entities: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to get entities", "message": str(exc)},
        )


@router.delete("/{document_id}", response_model=Dict[str, Any])
async def delete_document_graph(document_id: str) -> Dict[str, Any]:
    """
    Delete all graph data for a document.

    Removes:
    - All entity nodes connected to the document
    - All relationships involving those entities
    - The document node itself

    Args:
        document_id: Document identifier

    Returns:
        Deletion status
    """
    try:
        neo4j = await get_neo4j()
        await neo4j.delete_document_graph(document_id)

        return {
            "document_id": document_id,
            "status": "deleted",
        }
    except Neo4jUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Neo4j unavailable", "message": str(exc)},
        )
    except Exception as exc:
        LOGGER.error("Failed to delete document graph: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Failed to delete graph", "message": str(exc)},
        )
