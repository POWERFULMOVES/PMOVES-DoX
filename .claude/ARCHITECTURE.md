# PMOVES-DoX ↔ PMOVES-BoTZ Architecture

This document describes the integration architecture between PMOVES-DoX (Document Intelligence) and PMOVES-BoTZ (Agent Orchestration) systems.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PMOVES.AI Platform                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────┐     ┌─────────────────────────┐                │
│  │     PMOVES-DoX          │     │     PMOVES-BoTZ         │                │
│  │  Document Intelligence  │◄───►│  Agent Orchestration    │                │
│  │                         │     │                         │                │
│  │  • PDF Processing       │     │  • MCP Catalog          │                │
│  │  • Vector Search        │     │  • Cipher Memory        │                │
│  │  • Q&A Engine           │     │  • TensorZero Gateway   │                │
│  │  • Geometry Engine      │     │  • VL Sentinel          │                │
│  └───────────┬─────────────┘     └───────────┬─────────────┘                │
│              │                               │                               │
│              └───────────────┬───────────────┘                               │
│                              │                                               │
│                     ┌────────▼────────┐                                      │
│                     │   Shared Layer   │                                     │
│                     │  • NATS Bus      │                                     │
│                     │  • TensorZero    │                                     │
│                     │  • Supabase      │                                     │
│                     └──────────────────┘                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Service Port Mapping

### PMOVES-DoX Services

| Service | Port | Description |
|---------|------|-------------|
| Backend (FastAPI) | 8484 | Main API server |
| Frontend (Next.js) | 3737 | Web UI |
| NATS | 4223 | Standalone message bus |
| NATS WebSocket | 9223 | Frontend WebSocket |
| Ollama | 11434 | Local LLM |
| Neo4j | 7687 | Knowledge graph |
| Supabase REST | 3010 | Database API |
| TensorZero Gateway | 3030 | LLM orchestration |

### PMOVES-BoTZ Services

| Service | Port | Description |
|---------|------|-------------|
| Gateway | 2091 | Main BoTZ entry point |
| MCP Bridge | 8100 | MCP protocol bridge |
| Docling | 3020 | Document processing |
| E2B | 7071 | Code execution sandbox |
| VL Sentinel | 7072 | Vision-language |
| Cipher | 8081 | Memory service |
| Prometheus Push | 9091 | Metrics |

### Docked Mode Ports

When DoX runs in "docked" mode within PMOVES.AI:
- NATS: 4222 (parent)
- Backend: 8092 (proxied through gateway)
- TensorZero: 3030 (shared)

## NATS Event Subjects

### DoX Events

| Subject | Publisher | Description |
|---------|-----------|-------------|
| `geometry.event.curvature_update` | DoX Backend | Curvature analysis results |
| `geometry.event.manifold_update` | DoX Backend | Manifold parameter changes |
| `tokenism.cgp.ready.v1` | DoX Backend | CHIT Geometry Packet ready |
| `dox.document.ingested.v1` | DoX Backend | Document processing complete |
| `dox.search.query.v1` | DoX Backend | Search query executed |

### BoTZ Events

| Subject | Publisher | Description |
|---------|-----------|-------------|
| `botz.cipher.memory.stored.v1` | Cipher | Memory stored |
| `botz.cipher.memory.recalled.v1` | Cipher | Memory recalled |
| `botz.cipher.pattern.detected.v1` | Cipher | Pattern detected |
| `botz.mcp.tool.executed.v1` | MCP Bridge | Tool executed |
| `botz.vl.analysis.complete.v1` | VL Sentinel | Vision analysis done |

### Shared Events

| Subject | Publisher | Description |
|---------|-----------|-------------|
| `pmoves.health.ping.v1` | All | Health check ping |
| `pmoves.agent.status.v1` | All | Agent status update |

## Environment Variables

### Shared Variables

```bash
# TensorZero Gateway
TENSORZERO_URL=http://host.docker.internal:3030
TENSORZERO_API_KEY=<your-key>
TENSORZERO_CHAT_MODEL=orchestrator
TENSORZERO_EMBED_MODEL=qwen3_embedding_8b_local

# NATS
NATS_URL=nats://nats:4223  # standalone
NATS_URL=nats://nats:4222  # docked

# Supabase
SUPABASE_URL=http://supabase-rest:3000
SUPABASE_ANON_KEY=<your-key>
SUPABASE_SERVICE_KEY=<your-key>

# Ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### DoX-Specific Variables

```bash
# Database
DB_BACKEND=sqlite  # or supabase
DATABASE_URL=postgresql://...

# Features
WATCH_ENABLED=true
WATCH_DIR=/app/watch
PDF_FINANCIAL_ANALYSIS=true

# Geometry
CHIT_GEOMETRY_ENABLED=true
CHIT_USE_LOCAL_EMBEDDINGS=false
```

### BoTZ-Specific Variables

```bash
# Mode
DOCKED_MODE=false
PARENT_SYSTEM=PMOVES.AI

# Services
DOCLING_URL=http://localhost:3020/sse
E2B_URL=http://localhost:7071/sse
VL_SENTINEL_URL=http://localhost:7072/sse

# API Keys
VENICE_API_KEY=<your-key>
POSTMAN_API_KEY=<your-key>
N8N_API_KEY=<your-key>
E2B_API_KEY=<your-key>
```

## Integration Points

### 1. TensorZero LLM Gateway

Both systems use TensorZero for LLM orchestration:

```yaml
# TensorZero functions (tensorzero.toml)
functions:
  orchestrator:  # Chat completion
    model: qwen2.5:14b
  utility:       # Quick tasks
    model: qwen2.5:7b
  embed:         # Embeddings
    model: qwen3:8b
```

**DoX Usage:**
- Tag extraction
- Q&A generation
- Summarization

**BoTZ Usage:**
- Cipher memory reasoning
- n8n workflow suggestions
- VL Sentinel analysis

### 2. Cipher Memory Integration

DoX can query Cipher Memory for persistent context:

```python
# DoX → Cipher Memory
from app.services.cipher_service import cipher_service

# Store document context
await cipher_service.store_memory(
    key="doc-analysis",
    content=analysis_result,
    metadata={"artifact_id": doc_id}
)

# Recall related memories
results = await cipher_service.search_memory(
    query="financial analysis",
    limit=10
)
```

### 3. NATS Event Bus

Real-time communication between systems:

```python
# DoX publishing geometry event
await chit_service.publish_manifold_update({
    "curvature_k": -0.5,
    "manifold_type": "hyperbolic",
    "dimensions": 768
})

# BoTZ subscribing to DoX events
await nc.subscribe("dox.document.ingested.v1", handler)
```

### 4. A2A Protocol

Agent discovery and capability advertisement:

```bash
# DoX Agent Card
curl http://localhost:8484/.well-known/agent-card

# Capabilities advertised
{
  "capabilities": [
    "document-ingestion",
    "vector-search",
    "qa-engine",
    "agent-orchestration",  # NEW
    "memory-search",        # NEW
    "reasoning-trace",      # NEW
    "geometric-analysis"    # NEW
  ]
}
```

### 5. MCP Tool Routing

DoX can call BoTZ MCP servers via catalog:

```yaml
# BoTZ MCP Catalog (core/mcp/catalog.yml)
mcpServers:
  docling:
    url: http://localhost:3020/sse
    transport: sse

  cipher-memory:
    command: docker
    args: [exec, -i, pmz-cipher, python3, memory_shim/app_cipher_memory.py]
```

## Deployment Modes

### Standalone Mode

Both systems run independently:

```bash
# DoX
cd PMOVES-DoX
docker compose up -d

# BoTZ
cd PMOVES-BoTZ
docker compose up -d
```

### Docked Mode

DoX integrates into PMOVES.AI ecosystem:

```bash
# Set docked mode
export PMOVES_MODE=docked
export NATS_URL=nats://nats:4222  # Parent NATS

# Start DoX with docked compose
docker compose -f docker-compose.docked.yml up -d
```

### Hybrid Mode

BoTZ connects to parent PMOVES.AI services:

```bash
# BoTZ .env
DOCKED_MODE=false
TENSORZERO_URL=http://host.docker.internal:3030
NATS_URL=nats://host.docker.internal:4222
```

## Security

### JWT Authentication

MCP servers use Supabase JWT for authentication:

```bash
# Header
Authorization: Bearer <jwt_token>

# Or query param
?token=<jwt_token>
```

### Network Isolation

Services communicate via Docker network:

```yaml
networks:
  pmoves-dox-net:
    name: pmoves-dox-net

  pmoves-botz-net:
    name: pmoves-botz-net
```

### Secrets Management

Sensitive values use environment variables:

```bash
# Never commit these
SUPABASE_SERVICE_KEY
TENSORZERO_API_KEY
VENICE_API_KEY
```

## Monitoring

### Health Endpoints

| System | Endpoint | Description |
|--------|----------|-------------|
| DoX Backend | GET /health | Basic health |
| DoX Backend | GET /metrics | Prometheus metrics |
| BoTZ Gateway | GET /healthz | Gateway health |
| TensorZero | GET /healthz | LLM gateway health |

### Prometheus Metrics

```yaml
# Shared metrics endpoint
PROMETHEUS_PUSHGATEWAY=http://host.docker.internal:9091
```

## Related Documentation

- [DoX CLAUDE.md](./CLAUDE.md) - DoX developer context
- [DoX DOCKING_GUIDE.md](../docs/DOCKING_GUIDE.md) - Docking integration
- [BoTZ LEVEL1_AGENTS.md](../docs/agents/LEVEL1_AGENTS.md) - Foundational agents
- [BoTZ LEVEL2_AGENTS.md](../docs/agents/LEVEL2_AGENTS.md) - Self-evolving agents
- [BoTZ LEVEL3_AGENTS.md](../docs/agents/LEVEL3_AGENTS.md) - Collective agents
