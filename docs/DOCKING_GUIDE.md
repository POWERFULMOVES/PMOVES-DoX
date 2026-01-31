# PMOVES-DoX Docking Pattern Guide

This guide explains how PMOVES-DoX integrates with the parent PMOVES.AI ecosystem through the **docking pattern** - a hybrid architecture where DoX can operate independently or as an integrated service.

## Overview

PMOVES-DoX supports two deployment modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Standalone** | DoX runs independently with all local services | Local development, testing, isolated deployments |
| **Docked** | DoX integrates with parent PMOVES.AI services | Production, multi-agent orchestration, shared observability |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PMOVES.AI Parent Cluster                         │
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │ PMOVES-Agent-   │  │  pmoves-neo4j-1 │  │  TensorZero     │        │
│  │  Zero (Parent)  │  │   (Parent)      │  │ ClickHouse      │        │
│  │   Port 8080     │  │   Bolt: 7687    │  │   Port 8123     │        │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘        │
│           │                    │                    │                   │
│           │ MCP calls          │ Dual-write        │ Observability    │
└───────────┼────────────────────┼────────────────────┼───────────────────┘
            │                    │                    │
            │                    │                    │
    ┌───────▼────────────────────▼────────────────────▼──────────┐
    │              pmoves_data (External Network)                  │
    │                  172.30.4.0/24                               │
    └───────┬─────────────────────────────────────────────────────┘
            │
            │ Docker network bridge
            │
┌───────────▼─────────────────────────────────────────────────────┐
│                         PMOVES-DoX                                │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    api_tier (172.30.1.0/24)               │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │   │
│  │  │  Backend    │ │  Frontend   │ │  Ollama     │        │   │
│  │  │  :8484      │ │  :3001      │ │  :11435     │        │   │
│  │  └──────┬──────┘ └─────────────┘ └─────────────┘        │   │
│  └─────────┼─────────────────────────────────────────────────┘   │
│            │                                                     │
│  ┌─────────▼─────────────────────────────────────────────────┐   │
│  │                   app_tier (internal)                      │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │   │
│  │  │Agent Zero   │ │Cipher-Svc   │ │TensorZero   │        │   │
│  │  │ :50051      │ │ (internal)  │ │  :3000      │        │   │
│  │  │ MCP Server  │ │             │ │ ClickHouse  │        │   │
│  │  └──────┬──────┘ └─────────────┘ └─────────────┘        │   │
│  └─────────┼──────────────────────────────────────────────────┘   │
│            │                                                     │
│  ┌─────────▼─────────────────────────────────────────────────┐   │
│  │                   data_tier (internal)                     │   │
│  │  ┌─────────────┐ ┌─────────────┐                         │   │
│  │  │ Neo4j Local │ │ Supabase    │                         │   │
│  │  │ :17687      │ │ PostgREST   │                         │   │
│  │  └──────┬──────┘ └─────────────┘                         │   │
│  └─────────┼──────────────────────────────────────────────────┘   │
│            │                                                     │
│  ┌─────────▼─────────────────────────────────────────────────┐   │
│  │                   bus_tier (internal)                      │   │
│  │  ┌─────────────┐                                           │   │
│  │  │    NATS     │                                           │   │
│  │  │  :4223      │                                           │   │
│  │  └─────────────┘                                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Docking Modes

### Standalone Mode (Default)

DoX operates independently with all services local:

```yaml
# docker-compose.yml defaults
AGENT_ZERO_MCP_ENABLED=false  # No MCP server
NEO4J_PARENT_URI=             # Not set
SUPABASE_DUAL_WRITE=false     # Local only
```

**Characteristics:**
- Agent Zero Web UI accessible at `http://localhost:50051`
- Neo4j writes to local instance only
- Supabase uses local PostgREST
- No dependency on parent PMOVES.AI

### Docked Mode (PMOVES.AI Integration)

DoX integrates with parent services:

```bash
# .env.local configuration
AGENT_ZERO_MCP_ENABLED=true
AGENT_ZERO_MCP_TOKEN=your-secret-token-here
NEO4J_PARENT_PASSWORD=parent-neo4j-password
SUPABASE_DUAL_WRITE=true
SUPABASE_URL=https://your-parent-supabase.com
```

**Characteristics:**
- Agent Zero exposes MCP API at `http://pmoves-agent-zero:50051/mcp/t-{token}/sse`
- Neo4j dual-writes to both local and parent instances
- Supabase dual-writes to both local and parent databases
- TensorZero observability flows to parent ClickHouse

---

## Agent Zero Docking

### MCP API Endpoints

When docked, Agent Zero provides these MCP tools:

| Tool | Description |
|------|-------------|
| `send_message` | Send chat message to Agent Zero |
| `finish_chat` | End chat session |

### Parent Integration

Parent PMOVES-Agent-Zero calls DoX Agent Zero:

```bash
# Parent makes MCP call to DoX
curl -X POST http://pmoves-agent-zero:50051/mcp/t-{token}/sse \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "send_message",
      "arguments": {"message": "Analyze this document..."}
    }
  }'
```

### Configuration

```yaml
# docker-compose.yml
agent-zero:
  environment:
    # Docking control
    - MCP_SERVER_ENABLED=${AGENT_ZERO_MCP_ENABLED:-false}
    - MCP_SERVER_TOKEN=${AGENT_ZERO_MCP_TOKEN:-}
    # Standalone Web UI
    - WEB_UI_PORT=50051
    # LLM orchestration
    - TENSORZERO_API_BASE=http://tensorzero:3000/v1
  networks:
    - app_tier
    - api_tier
    - bus_tier
```

---

## Dual-Write Architecture

### Neo4j Dual-Write

DoX maintains knowledge graphs in both local and parent Neo4j:

```python
# backend/app/database_neo4j.py
class Neo4jDualWriteManager:
    LOCAL_URI = "bolt://neo4j:7687"
    PARENT_URI = "bolt://pmoves-neo4j-1:7687"

    def _dual_write(self, query, parameters):
        # Write to parent first (if available)
        if self.parent_connection:
            self.parent_connection.run(query, parameters)
        # Always write to local
        self.local_connection.run(query, parameters)
```

**Configuration:**
```bash
NEO4J_LOCAL_URI=bolt://neo4j:7687
NEO4J_LOCAL_PASSWORD=local-password
NEO4J_PARENT_URI=bolt://pmoves-neo4j-1:7687
NEO4J_PARENT_PASSWORD=parent-password
```

### Supabase Dual-Write

DoX uses a factory pattern for dual-write:

```python
# backend/app/database_factory.py
class DualDatabase:
    def __init__(self, primary, secondary):
        self.primary = primary
        self.secondary = secondary

    def add_artifact(self, artifact):
        result = self.primary.add_artifact(artifact)
        # Non-blocking secondary write
        try:
            self.secondary.add_artifact(artifact)
        except Exception as e:
            logger.warning(f"Secondary write failed: {e}")
        return result
```

**Configuration:**
```bash
DB_BACKEND=supabase
SUPABASE_DUAL_WRITE=true
SUPABASE_URL=https://parent-supabase.com
SUPABASE_SERVICE_KEY=your-service-key
```

---

## Internal Agents

### DoX-Only Agents (Internal)

| Agent | Container | Port | Purpose |
|-------|-----------|------|---------|
| **Cipher-Service** | pmoves-dox-cipher | internal | Byterover memory framework |
| **NATS** | pmoves-dox-nats | 4223, 8223, 9223 | Message bus coordination |
| **Ollama** | pmoves-dox-ollama-1 | 11435 | Local LLM inference |

### BotZ MCP Agents

| Agent | Container | Port | MCP Endpoint |
|-------|-----------|------|--------------|
| **Cipher Agent** | pmoves-botz-cipher | 3025 | Memory operations |
| **Postman Agent** | pmoves-botz-postman | 3026 | API testing |
| **Docling Agent** | pmoves-botz-docling | 3020 | Document processing |

### Orchestrator Agents

| Agent | Container | Integration |
|-------|-----------|-------------|
| **Agent Zero** | pmoves-agent-zero | MCP dockable with parent |
| **TensorZero** | pmoves-botz-tensorzero | Observability to parent ClickHouse |

---

## Network Configuration

### DoX Namespaced Networks (Standalone)

DoX uses namespaced networks to avoid conflicts with parent PMOVES.AI:

| Network | Subnet | Internal | Purpose |
|---------|--------|----------|---------|
| `pmoves_dox_api` | 172.31.1.0/24 | No | Exposed services |
| `pmoves_dox_app` | 172.31.2.0/24 | Yes | Internal agents |
| `pmoves_dox_bus` | 172.31.3.0/24 | Yes | NATS messaging |
| `pmoves_dox_data` | 172.31.4.0/24 | Yes | Local databases |
| `pmoves_dox_monitoring` | 172.31.5.0/24 | No | Monitoring tier |

### Parent Integration Networks (Docked Mode)

| Network | Type | Subnet | Purpose |
|---------|------|--------|---------|
| `pmoves_api` | External | 172.30.1.0/24 | Parent API tier (TensorZero Gateway) |
| `pmoves_app` | External | 172.30.2.0/24 | Parent app tier |
| `pmoves_bus` | External | 172.30.3.0/24 | Parent NATS message bus |
| `pmoves_data` | External | 172.30.4.0/24 | Parent data services (Neo4j, ClickHouse) |

**Note:** DoX uses 172.31.x subnets in standalone mode to avoid conflicts with parent's 172.30.x subnets.

### Port Offset Strategy

DoX services use port offsets to avoid conflicts with parent:

| Service | Parent Port | DoX Port | Purpose |
|---------|-------------|----------|---------|
| Backend | 8000 | 8484 | API server |
| Frontend | 3000 | 3001 | Web UI |
| Agent Zero | 8080/8081 | 50051 | MCP/Web UI |
| NATS | 4222 | 4223 | Message bus |
| NATS WS | 9222 | 9223 | WebSocket |
| Neo4j HTTP | 7474 | 17474 | Graph UI |
| Neo4j Bolt | 7687 | 17687 | Graph protocol |
| Ollama | 11434 | 11435 | Local LLM |

---

## Setup Instructions

### Standalone Mode (Quick Start)

```bash
# Clone repository
git clone https://github.com/POWERFULMOVES/PMOVES-DoX.git
cd PMOVES-DoX

# Using Makefile (recommended)
make standalone

# Or manually
docker compose --env-file .env.local up -d --build

# Access Web UI
open http://localhost:3001    # Frontend
open http://localhost:8484    # Backend API
open http://localhost:50051   # DoX Agent Zero
open http://localhost:17474   # Neo4j UI
```

### Docked Mode (PMOVES.AI Integration)

**Prerequisites:** Parent PMOVES.AI cluster running with networks available.

```bash
# Verify parent networks are available
make check-parent

# Start in docked mode
make docked

# Or manually with override
docker compose -f docker-compose.yml -f docker-compose.docked.yml \
  --env-file .env.local up -d --build

# Access Web UI
open http://localhost:3001    # Frontend
open http://localhost:8484    # Backend API
open http://localhost:50051   # DoX Agent Zero (MCP enabled)
```

### Verify Deployment Mode

The `/config` endpoint reports current deployment mode:

```bash
curl http://localhost:8484/config | jq '.deployment'
```

Response:
```json
{
  "mode": "docked",           // or "standalone"
  "nats_url": "nats://nats:4222",
  "tensorzero_url": "http://tensorzero-gateway:3030"
}
```

---

## Troubleshooting

### MCP Connection Failed

**Symptom:** Parent can't reach DoX Agent Zero MCP endpoint

**Solution:**
```bash
# Check Agent Zero is running
docker exec pmoves-agent-zero curl http://localhost:50051/health

# Verify MCP is enabled
docker exec pmoves-agent-zero env | grep MCP_SERVER

# Check network connectivity
docker network inspect pmoves_data | grep pmoves-agent-zero
```

### Neo4j Dual-Write Failing

**Symptom:** Logs show "Neo4j parent connection failed"

**Solution:**
```bash
# Verify parent Neo4j is accessible
docker exec pmoves-agent-zero ping pmoves-neo4j-1

# Check password is set
docker exec pmoves-agent-zero env | grep NEO4J_PARENT_PASSWORD

# Test connection from backend
docker exec pmoves-dox-backend python -c "
from app.database_neo4j import Neo4jManager
mgr = Neo4jManager()
print(f'Parent: {mgr.parent_connection}')
print(f'Local: {mgr.local_connection}')
"
```

### Port Conflicts in Docked Mode

**Symptom:** Service fails to start with "port already in use"

**Solution:**
```bash
# Identify conflicting ports
docker ps | grep -E "(8484|50051|3001|3025|3026)"

# Use docker compose overrides
cat > docker-compose.docked.override.yml << EOF
services:
  backend:
    ports:
      - "8485:8484"  # Change host port
  agent-zero:
    ports:
      - "50052:50051"  # Change host port
EOF

docker compose -f docker-compose.yml -f docker-compose.docked.override.yml up -d
```

---

## Migration: Standalone → Docked

1. **Backup existing data:**
   ```bash
   docker exec pmoves-dox-neo4j cypher-shell -u neo4j -p $NEO4J_LOCAL_PASSWORD "CALL apoc.export.cypher.all('backup.cypher', {})"
   ```

2. **Enable docking configuration:**
   ```bash
   # Add to .env.local
   AGENT_ZERO_MCP_ENABLED=true
   AGENT_ZERO_MCP_TOKEN=$(openssl rand -hex 16)
   NEO4J_PARENT_PASSWORD=$PARENT_PASSWORD
   SUPABASE_DUAL_WRITE=true
   ```

3. **Restart services:**
   ```bash
   docker compose down
   docker compose up -d
   ```

4. **Verify integration:**
   ```bash
   # Test Agent Zero MCP
   curl http://localhost:50051/health

   # Test Neo4j dual-write
   curl http://localhost:8484/api/graph/nodes

   # Test Supabase dual-write
   curl http://localhost:8484/api/artifacts
   ```

---

## References

- **Main User Guide:** [USER_GUIDE.md](USER_GUIDE.md)
- **API Reference:** [API_REFERENCE.md](API_REFERENCE.md)
- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **CLAUDE.md:** [CLAUDE.md](../CLAUDE.md) for AI assistant context
