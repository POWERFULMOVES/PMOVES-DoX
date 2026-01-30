# Neo4j Integration Guide

This document describes how PMOVES-DoX integrates with Neo4j for knowledge graph storage, including local setup, parent dual-write patterns, and the CHIT/Cipher schema.

## Table of Contents

1. [Overview](#overview)
2. [Local Neo4j Setup](#local-neo4j-setup)
3. [Parent Neo4j Dual-Write Pattern](#parent-neo4j-dual-write-pattern)
4. [Knowledge Graph Schema](#knowledge-graph-schema)
5. [Connection Configuration](#connection-configuration)
6. [API Endpoints](#api-endpoints)
7. [Example Cypher Queries](#example-cypher-queries)
8. [Troubleshooting](#troubleshooting)

---

## Overview

PMOVES-DoX uses Neo4j as its primary knowledge graph database for storing document entities, relationships, and semantic connections. The architecture supports:

- **Local-only mode**: Single Neo4j instance for standalone deployments
- **Dual-write mode**: Simultaneous writes to local and parent Neo4j instances
- **Hybrid fallback**: Automatic failover from parent to local

### Port Configuration

| Service    | Local Port | Parent Port | Protocol |
| ---------- | ---------- | ----------- | -------- |
| Neo4j HTTP | 17474      | 7474        | HTTP     |
| Neo4j Bolt | 17687      | 7687        | Bolt     |

The local ports use a 10000 offset to avoid conflicts when running alongside the parent PMOVES.AI cluster.

---

## Local Neo4j Setup

### Docker Compose Configuration

The local Neo4j instance is defined in `docker-compose.yml`:

```yaml
neo4j:
  image: neo4j:5.15-community
  container_name: pmoves-dox-neo4j
  environment:
    - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-changeme}
    - NEO4J_PLUGINS=["apoc"]
    - NEO4J_dbms_security_procedures_unrestricted=apoc.*
    - NEO4J_dbms_memory_heap_initial__size=512m
    - NEO4J_dbms_memory_heap_max__size=1G
  ports:
    - "17474:7474"  # HTTP Browser
    - "17687:7687"  # Bolt Protocol
  volumes:
    - neo4j_data:/data
    - neo4j_logs:/logs
  networks:
    - data_tier
  healthcheck:
    test: ["CMD", "wget", "-qO-", "http://localhost:7474"]
    interval: 30s
    timeout: 10s
    retries: 5
```

### Starting Neo4j

```bash
# Start with Docker Compose
docker compose up -d neo4j

# Verify Neo4j is running
docker exec pmoves-dox-neo4j cypher-shell -u neo4j -p changeme "RETURN 1"

# Access Neo4j Browser
open http://localhost:17474
```

### Initial Setup

After starting Neo4j for the first time:

1. Access the browser at `http://localhost:17474`
2. Log in with credentials: `neo4j` / `changeme` (or your configured password)
3. Create required indexes:

```cypher
-- Create indexes for performance
CREATE INDEX entity_id_index IF NOT EXISTS FOR (e:Entity) ON (e.id);
CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX document_id_index IF NOT EXISTS FOR (d:Document) ON (d.id);

-- Create uniqueness constraint
CREATE CONSTRAINT entity_unique_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT document_unique_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;
```

---

## Parent Neo4j Dual-Write Pattern

### Architecture Overview

```text
                                  PMOVES.AI Parent Cluster
                                 ┌─────────────────────────┐
                                 │   pmoves-neo4j-1        │
                                 │   Bolt: 7687            │
                                 └───────────┬─────────────┘
                                             │
        ─────────────────────────────────────┼─────────────────────────
                                             │  pmoves_data network
                                             │
┌────────────────────────────────────────────┼────────────────────────────┐
│                    PMOVES-DoX              │                            │
│                                            │                            │
│  ┌─────────────────┐              ┌────────▼────────┐                  │
│  │   Backend       │──── Dual ───▶│  Parent Neo4j   │                  │
│  │   :8484         │    Write     │  :7687          │                  │
│  └────────┬────────┘              └─────────────────┘                  │
│           │                                                             │
│           │                       ┌─────────────────┐                  │
│           └────── Local Write ───▶│  Local Neo4j    │                  │
│                                   │  :17687         │                  │
│                                   └─────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Dual-Write Strategy

The `Neo4jManager` class implements the dual-write pattern:

```python
# backend/app/database_neo4j.py

class Neo4jManager:
    async def _dual_write(self, query: str, params: Dict[str, Any]) -> List[Dict]:
        """Execute query on both parent and local Neo4j."""
        primary = self.parent_driver if self.use_parent else self.local_driver
        secondary = self.local_driver if self.use_parent else None

        results = []

        # Execute on primary
        if primary:
            async with primary.session() as session:
                result = await session.run(query, params)
                results = [record async for record in result]

        # Dual-write to secondary (non-blocking)
        if secondary:
            try:
                async with secondary.session() as session:
                    await session.run(query, params)
            except Exception as exc:
                LOGGER.error("Dual-write to secondary failed: %s", exc)

        return results
```

### Connection Priority

1. **Try Parent First**: Connect to `NEO4J_PARENT_URI` if password is configured
2. **Fallback to Local**: If parent is unavailable, use `NEO4J_LOCAL_URI`
3. **Establish Both**: If parent succeeds, also connect to local for dual-write
4. **Error Handling**: Log warnings for secondary write failures (non-blocking)

---

## Knowledge Graph Schema

### Node Types

#### Document Node

Represents an ingested document in PMOVES-DoX.

```cypher
(:Document {
  id: "uuid",
  last_updated: datetime(),
  entity_count: 42
})
```

#### Entity Node

Represents named entities extracted from documents.

```cypher
(:Entity {
  id: "uuid",
  text: "Apple Inc.",
  type: "ORG",
  context: "Apple Inc. announced...",
  page: 1,
  start_char: 0,
  end_char: 10,
  last_seen: datetime()
})
```

**Supported Entity Types (spaCy NER):**

| Type      | Description           | Example          |
| --------- | --------------------- | ---------------- |
| `PERSON`  | People names          | "John Smith"     |
| `ORG`     | Organizations         | "Apple Inc."     |
| `GPE`     | Geopolitical entities | "United States"  |
| `LOC`     | Locations             | "Mount Everest"  |
| `DATE`    | Dates                 | "January 2024"   |
| `MONEY`   | Monetary values       | "$1 million"     |
| `PRODUCT` | Products              | "iPhone 15"      |
| `EVENT`   | Events                | "World Cup 2024" |

### Relationship Types

#### CONTAINS

Links documents to their extracted entities.

```cypher
(d:Document)-[:CONTAINS]->(e:Entity)
```

#### RELATED_TO

Links entities that co-occur within a document (proximity-based).

```cypher
(e1:Entity)-[:RELATED_TO {
  proximity: 150,
  weight: 0.85
}]-(e2:Entity)
```

Properties:
- `proximity`: Character distance between entities
- `weight`: Relationship strength (1.0 - proximity/max_distance)

### CHIT/Cipher Schema Extensions

For the Cymatic-Holographic Information Transfer (CHIT) protocol, the schema includes:

#### CGP Node (Geometry Packet)

Represents a CHIT Geometry Packet for geometric encoding.

```cypher
(:CGP {
  id: "uuid",
  spec: "chit.cgp.v0.1",
  source: "docx",
  units_mode: "paragraphs",
  K: 8,
  bins: 8,
  mhep: 72.3,
  backend: "sentence-transformers/all-MiniLM-L6-v2"
})
```

#### Constellation Node

Represents a semantic cluster within a CGP.

```cypher
(:Constellation {
  id: "const_0_0",
  summary: "topic keywords...",
  anchor: [0.012, -0.31, ...],  // embedding vector
  radial_minmax: [-0.45, 0.93],
  spectrum: [0.08, 0.11, ...]   // soft histogram
})
```

#### CHIT Relationships

```cypher
-- CGP contains constellations
(cgp:CGP)-[:HAS_CONSTELLATION]->(c:Constellation)

-- Constellation contains embedding points
(c:Constellation)-[:HAS_POINT {
  proj: 0.83,
  conf: 0.94
}]->(e:Entity)
```

---

## Connection Configuration

### Environment Variables

Configure Neo4j connections via environment variables in `.env.local`:

```bash
# =============================================================================
# Neo4j Knowledge Graph Configuration
# =============================================================================

# Enable/disable Neo4j integration
NEO4J_ENABLED=true

# Local Neo4j (DoX-specific)
NEO4J_LOCAL_URI=bolt://neo4j:7687
NEO4J_LOCAL_USER=neo4j
NEO4J_LOCAL_PASSWORD=changeme

# Parent Neo4j (PMOVES.AI shared - for dual-write mode)
NEO4J_PARENT_URI=bolt://pmoves-neo4j-1:7687
NEO4J_PARENT_USER=neo4j
NEO4J_PARENT_PASSWORD=  # Set for docked mode
```

### Mode Selection

| Configuration                  | Result                       |
| ------------------------------ | ---------------------------- |
| `NEO4J_PARENT_PASSWORD` empty  | Local-only mode              |
| `NEO4J_PARENT_PASSWORD` set    | Dual-write mode              |
| Parent unreachable             | Automatic fallback to local  |
| `NEO4J_ENABLED=false`          | Neo4j disabled entirely      |

### Docker Compose Environment

In `docker-compose.yml`, the backend service receives Neo4j configuration:

```yaml
backend:
  environment:
    # Neo4j Knowledge Graph - Local (DoX container)
    - NEO4J_LOCAL_URI=bolt://neo4j:7687
    - NEO4J_LOCAL_USER=neo4j
    # Neo4j Knowledge Graph - Parent (PMOVES.AI shared)
    - NEO4J_PARENT_URI=bolt://pmoves-neo4j-1:7687
    - NEO4J_PARENT_USER=neo4j
```

---

## API Endpoints

The Knowledge Graph API is available at `/graph`:

### Health Check

```http
GET /graph/health
```

Response:
```json
{
  "enabled": true,
  "connected": true,
  "active": "parent",
  "parent_connected": true,
  "local_connected": true,
  "doc_count": 15,
  "entity_count": 342
}
```

### Get Document Entity Graph

```http
GET /graph/{document_id}
```

Response (vis-network format):
```json
{
  "nodes": [
    {"id": "ent-1", "label": "Apple Inc.", "type": "ORG", "title": "ORG: Apple Inc.\nPage: 1"}
  ],
  "edges": [
    {"from": "ent-1", "to": "ent-2", "weight": 0.85, "title": "Proximity: 150"}
  ],
  "document_id": "doc-uuid"
}
```

### Store Entities

```http
POST /graph/{document_id}/entities
Content-Type: application/json

{
  "entities": [
    {
      "text": "Apple Inc.",
      "label": "ORG",
      "start_char": 0,
      "end_char": 10,
      "page": 1,
      "context": "Apple Inc. announced a new product..."
    }
  ],
  "max_distance": 500,
  "min_weight": 0.1
}
```

### Search Entities

```http
GET /graph/search?query=Apple&entity_type=ORG&limit=20
```

### Find Entity Connections

```http
GET /graph/{entity_id}/connections?max_depth=2
```

### Delete Document Graph

```http
DELETE /graph/{document_id}
```

---

## Example Cypher Queries

### Find All Entities in a Document

```cypher
MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(e:Entity)
RETURN e
ORDER BY e.start_char
```

### Find Related Organizations

```cypher
MATCH (e1:Entity {type: 'ORG'})-[r:RELATED_TO]-(e2:Entity {type: 'ORG'})
WHERE r.weight > 0.5
RETURN e1.text, e2.text, r.weight
ORDER BY r.weight DESC
LIMIT 20
```

### Find Entity Co-occurrence Network

```cypher
MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(e:Entity)
OPTIONAL MATCH (e)-[r:RELATED_TO]-(other:Entity)
RETURN e, collect({to: other.id, weight: r.weight}) as relationships
```

### Find Cross-Document Entity Mentions

```cypher
MATCH (d1:Document)-[:CONTAINS]->(e:Entity)<-[:CONTAINS]-(d2:Document)
WHERE d1.id <> d2.id AND e.text = $entity_text
RETURN d1.id, d2.id, e.text, count(*) as co_mentions
ORDER BY co_mentions DESC
```

### Get Entity Neighborhood (2-hop)

```cypher
MATCH path = (e:Entity {id: $entity_id})-[*1..2]-(connected:Entity)
WITH nodes(path) as nodes, relationships(path) as rels
UNWIND nodes as node
UNWIND rels as rel
RETURN DISTINCT node, collect(DISTINCT rel) as relationships
```

### Find High-Weight Relationship Clusters

```cypher
MATCH (e1:Entity)-[r:RELATED_TO]-(e2:Entity)
WHERE r.weight > 0.8
WITH e1, e2, r
MATCH (d:Document)-[:CONTAINS]->(e1)
RETURN d.id, e1.text, e2.text, r.weight
ORDER BY r.weight DESC
```

### Aggregate Entity Statistics by Type

```cypher
MATCH (e:Entity)
RETURN e.type as entity_type, count(*) as count
ORDER BY count DESC
```

### Find Disconnected Entities

```cypher
MATCH (e:Entity)
WHERE NOT (e)-[:RELATED_TO]-()
RETURN e.id, e.text, e.type
```

### Full-Text Search on Entity Context

```cypher
MATCH (e:Entity)
WHERE e.context CONTAINS $search_term
RETURN e.id, e.text, e.type, e.context
LIMIT 50
```

### Create Relationship from Proximity

```cypher
MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(e1:Entity),
      (d)-[:CONTAINS]->(e2:Entity)
WHERE e1.type = e2.type AND e1.id < e2.id
WITH e1, e2,
     abs(e1.start_char - e2.start_char) as distance
WHERE distance < $max_distance
WITH e1, e2, distance, (1.0 - (distance / $max_distance)) as weight
WHERE weight >= $min_weight
MERGE (e1)-[r:RELATED_TO]-(e2)
SET r.proximity = distance, r.weight = weight
```

---

## Troubleshooting

### Cannot Connect to Local Neo4j

**Symptoms:**
- "Neo4j unavailable" error in logs
- `/graph/health` returns 503

**Solutions:**

1. Check Neo4j container is running:
```bash
docker ps | grep neo4j
docker logs pmoves-dox-neo4j
```

2. Verify password configuration:
```bash
# Check environment variable
docker exec pmoves-dox-backend env | grep NEO4J_LOCAL_PASSWORD
```

3. Test connection manually:
```bash
docker exec pmoves-dox-neo4j cypher-shell -u neo4j -p changeme "RETURN 1"
```

### Dual-Write Failing to Parent

**Symptoms:**
- Logs show "Dual-write to secondary failed"
- Local data exists but parent does not sync

**Solutions:**

1. Verify parent network connectivity:
```bash
docker exec pmoves-dox-backend ping pmoves-neo4j-1
```

2. Check parent credentials:
```bash
docker exec pmoves-dox-backend env | grep NEO4J_PARENT_PASSWORD
```

3. Test parent connection:
```bash
docker exec pmoves-dox-backend python -c "
from app.database_neo4j import Neo4jManager
import asyncio

async def test():
    mgr = Neo4jManager()
    status = await mgr.connect()
    print(status)

asyncio.run(test())
"
```

### Memory Issues with Large Graphs

**Symptoms:**
- Out-of-memory errors
- Slow queries on large datasets

**Solutions:**

1. Increase Neo4j heap size in `docker-compose.yml`:
```yaml
environment:
  - NEO4J_dbms_memory_heap_max__size=2G
```

2. Add query pagination:
```cypher
MATCH (e:Entity)
RETURN e
SKIP $offset LIMIT $limit
```

3. Use indexes for frequent queries:
```cypher
CREATE INDEX entity_text_index FOR (e:Entity) ON (e.text)
```

### Entity Relationships Not Discovered

**Symptoms:**
- Entities stored but no RELATED_TO edges created
- Graph visualization shows isolated nodes

**Solutions:**

1. Check `max_distance` parameter:
```python
# Increase max_distance for sparse documents
await neo4j.store_entities(doc_id, entities, max_distance=1000)
```

2. Lower `min_weight` threshold:
```python
# Accept weaker relationships
await neo4j.store_entities(doc_id, entities, min_weight=0.05)
```

3. Verify entities have position data:
```python
# Entities need start_char/end_char for proximity calculation
entity = {
    "text": "Example",
    "label": "ORG",
    "start_char": 100,  # Required
    "end_char": 107     # Required
}
```

---

## References

- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)
- [DOCKING_GUIDE.md](./DOCKING_GUIDE.md) - Integration with parent PMOVES.AI
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview
- [PMOVESCHIT.md](./PMOVESCHIT.md) - CHIT protocol specification
- [PsyFeR Reference](../PsyFeR_reference/) - Cipher memory framework
