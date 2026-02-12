# Service Catalog

Complete catalog of all services in PMOVES-DoX with ports, health endpoints, dependencies, and categorization.

## Service Categories

- **Data Tier**: Storage and persistence services
- **API Tier**: External-facing API services
- **App Tier**: Internal application services
- **Bus Tier**: Message bus and event coordination
- **Agent Tier**: AI agent and orchestration services
- **Media Tier**: Media processing services
- **Tool Tier**: Utility and visualization tools
- **Monitoring Tier**: Observability and monitoring services

## Complete Service List

### Data Tier Services

| Service | Container Name | Port | Health Check | Dependencies | Purpose |
|---------|---------------|------|--------------|--------------|---------|
| **supabase-db** | supabase-db | 5432 | `pg_isready -U postgres` | None | PostgreSQL database |
| **supabase-rest** | supabase-rest | 3000 (internal) | HTTP check | supabase-db | PostgREST API |
| **supabase-proxy** | supabase-proxy | 54321 | HTTP 200 | supabase-rest | Nginx proxy for Supabase |
| **neo4j** | pmoves-dox-neo4j | 17474, 17687 | HTTP / | None | Knowledge graph database |
| **clickhouse** | pmoves-dox-clickhouse | 8123, 9000 | HTTP /ping | None | TensorZero observability backend |
| **search-index** | (backend internal) | N/A | N/A | backend | FAISS/NumPy vector index |

### API Tier Services

| Service | Container Name | Port | Health Check | Dependencies | Purpose |
|---------|---------------|------|--------------|--------------|---------|
| **backend** | pmoves-dox-backend | 8484 | `/healthz` | supabase-db, nats, neo4j | Main FastAPI backend |
| **frontend** | pmoves-dox-frontend | 3001 | HTTP 200 | backend | Next.js web UI |
| **tensorzero** | pmoves-botz-tensorzero | 3030 | `/health` | clickhouse | LLM gateway with observability |

### Bus Tier Services

| Service | Container Name | Port | Health Check | Dependencies | Purpose |
|---------|---------------|------|--------------|--------------|---------|
| **nats** | pmoves-dox-nats | 4223, 8223, 9223 | Binary check | None | Message bus with JetStream |
| **nats (docked)** | (parent) | 4222, 8222, 9222 | Binary check | None | Parent NATS for docked mode |

### App Tier Services

| Service | Container Name | Port | Health Check | Dependencies | Purpose |
|---------|---------------|------|--------------|--------------|---------|
| **cipher-service** | pmoves-dox-cipher | 3000 (internal) | TCP 3000 | nats, ollama | Cipher memory/skills service |
| **agent-zero** | pmoves-agent-zero | 50051 | `/health` | tensorzero | AI agent orchestrator |
| **ollama** | pmoves-dox-ollama-1 | 11435 (ext) / 11434 (int) | API /tags | None | Local LLM runtime |

### Agent Tier Services (MCP)

| Service | Container Name | Port | Health Check | Dependencies | Purpose |
|---------|---------------|------|--------------|--------------|---------|
| **cipher** | pmoves-botz-cipher | 3025 | `/mcp` health | backend | Cipher MCP server |
| **docling** | pmoves-botz-docling | 3020 | `/health` | backend | Docling PDF processing MCP |
| **postman-agent** | pmoves-botz-postman | 3026 | HTTP check | backend | Postman API MCP server |

### Tool Tier Services

| Service | Container Name | Port | Health Check | Dependencies | Purpose |
|---------|---------------|------|--------------|--------------|---------|
| **datavzrd** | datavzrd | 5173 | HTTP 200 | backend | Data visualization |
| **schemavzrd** | schemavzrd | 5174 | HTTP 200 | backend | Database schema visualization |
| **glances** | pmoves-dox-glancer | 61208 | HTTP 200 | None | System monitoring |

## Service Details

### Backend API (pmoves-dox-backend)

**Port**: 8484
**Health Endpoint**: `GET /healthz`
**Networks**: `pmoves_dox_api`, `pmoves_dox_app`, `pmoves_dox_bus`, `pmoves_dox_data`

**Environment Variables**:
```bash
PORT=8484
DATABASE_URL=postgresql://postgres:password@supabase-db:5432/postgres
NATS_URL=nats://nats:4222
NEO4J_LOCAL_URI=bolt://neo4j:7687
TENSORZERO_BASE_URL=http://tensorzero-gateway:3030
```

**Capabilities**:
- Document ingestion (PDF, CSV, XLSX, XML, API specs)
- Vector search with FAISS/NumPy
- Q&A with citations
- Knowledge graph queries (Neo4j)
- CHR pipeline
- Tag extraction (LangExtract)
- MCP tool provider for Agent Zero

**API Endpoints**:
- `POST /upload` - Upload documents
- `GET /search` - Semantic search
- `POST /ask` - Q&A with citations
- `GET /artifacts` - List artifacts
- `POST /chr/{id}` - Generate CHR
- `GET /graph/query` - Graph queries
- `GET /healthz` - Health check
- `GET /metrics` - Prometheus metrics

### Frontend (pmoves-dox-frontend)

**Port**: 3001
**Health Endpoint**: HTTP 200 on root
**Networks**: `pmoves_dox_api`

**Environment Variables**:
```bash
API_URL=http://backend:8484
NEXT_PUBLIC_NATS_WS_URL=ws://localhost:9223
```

**Capabilities**:
- Document upload UI
- Search and Q&A interface
- Knowledge graph visualization
- CHR panel
- API catalog management
- Real-time NATS WebSocket updates

### NATS Message Bus (pmoves-dox-nats)

**Ports**: 4223 (client), 8223 (monitoring), 9223 (WebSocket)
**Health Check**: Binary exists
**Networks**: `pmoves_dox_bus`, `pmoves_dox_api`

**Capabilities**:
- JetStream for persistence
- WebSocket support for real-time UI
- Subject-based messaging
- Geometry bus for CHIT protocol

**Key Subjects**:
- `tokenism.cgp.>` - Geometry packets
- `geometry.>` - Geometry events
- `pmoves.ingest.>` - Ingestion events
- `pmoves.agent.>` - Agent coordination

### Agent Zero (pmoves-agent-zero)

**Port**: 50051
**Health Endpoint**: `GET /health`
**Networks**: `pmoves_dox_api`, `pmoves_dox_app`, `pmoves_dox_bus`

**Environment Variables**:
```bash
MCP_SERVER_ENABLED=true
WEB_UI_PORT=50051
TENSORZERO_API_BASE=http://tensorzero-gateway:3030/v1
PROFILE=pmoves_custom
```

**Capabilities**:
- General AI agent with tool use
- MCP server for external coordination
- Web UI for direct interaction
- Integration with backend MCP tools

**MCP Tools Available**:
- `send_message` - Send chat messages
- `finish_chat` - End conversation
- Backend tools via MCP connection

### TensorZero Gateway (pmoves-botz-tensorzero)

**Port**: 3030
**Health Endpoint**: `GET /health`
**Networks**: `pmoves_dox_app`, `pmoves_dox_api`, `pmoves_dox_data`

**Environment Variables**:
```bash
TENSORZERO_CLICKHOUSE_URL=http://tensorzero-clickhouse:8123/default
```

**Capabilities**:
- OpenAI-compatible API
- Multi-provider routing (OpenRouter, Gemini, OpenAI)
- ClickHouse observability
- Request/response logging
- Token usage tracking

**API Endpoints**:
- `POST /v1/chat/completions` - Chat completions
- `POST /v1/embeddings` - Generate embeddings
- `GET /health` - Health check

### Neo4j (pmoves-dox-neo4j)

**Ports**: 17474 (HTTP), 17687 (Bolt)
**Health Endpoint**: `GET /`
**Networks**: `pmoves_dox_data`, `pmoves_data` (docked)

**Environment Variables**:
```bash
NEO4J_AUTH=neo4j/password
NEO4J_dbms_memory_heap_max__size=1G
```

**Capabilities**:
- Knowledge graph storage
- Relationship queries (Cypher)
- Entity extraction
- Graph visualization data

### ClickHouse (pmoves-dox-clickhouse)

**Ports**: 8123 (HTTP), 9000 (Native)
**Health Endpoint**: `GET /ping`
**Networks**: `pmoves_dox_data`, `pmoves_dox_app`

**Environment Variables**:
```bash
CLICKHOUSE_USER=tensorzero
CLICKHOUSE_PASSWORD=tensorzero
```

**Capabilities**:
- TensorZero observability backend
- Request/response logging
- Token usage metrics
- Performance analytics

### Cipher Service (pmoves-dox-cipher)

**Port**: 3000 (internal)
**Health Endpoint**: TCP 3000
**Networks**: `pmoves_dox_app`

**Capabilities**:
- Memory management for agents
- Skill registry
- CHIT geometry packet generation
- NATS integration

### Ollama (pmoves-dox-ollama-1)

**External Port**: 11435 (host access)
**Internal Port**: 11434 (Ollama default, used for container-to-container)
**Health Endpoint**: `GET /api/tags`
**Networks**: `pmoves_dox_api`, `pmoves_dox_app`

**Note**: Services internally use `http://ollama:11434`; host accesses `http://localhost:11435`

**Capabilities**:
- Local LLM inference
- Model management
- GPU acceleration support
- Fallback for cloud LLMs

### Supabase Stack

**Components**:
1. **supabase-db** (PostgreSQL 15.1.0)
   - Port: 5432 (internal)
   - Health: `pg_isready`

2. **supabase-rest** (PostgREST v11.1.0)
   - Port: 3000 (internal)
   - Health: HTTP check

3. **supabase-proxy** (Nginx)
   - Port: 54321 (exposed)
   - Purpose: Route /rest/v1/* to PostgREST root

**Capabilities**:
- PostgreSQL database with pgvector
- PostgREST API
- Real-time subscriptions
- Row-level security

### MCP Agents

#### Cipher (pmoves-botz-cipher)
- **Port**: 3025
- **Health**: `/mcp` HTTP check
- **Purpose**: Cipher memory MCP server

#### Docling (pmoves-botz-docling)
- **Port**: 3020
- **Health**: `/health`
- **Purpose**: PDF processing MCP server

#### Postman Agent (pmoves-botz-postman)
- **Port**: 3026
- **Health**: HTTP check
- **Purpose**: Postman API MCP server

### Tool Services

#### Glances (pmoves-dox-glancer)
- **Port**: 61208
- **Purpose**: System monitoring dashboard
- **Access**: Docker socket for container stats

#### Datavzrd (datavzrd)
- **Port**: 5173
- **Purpose**: Data visualization from artifacts
- **Profile**: `tools`

#### Schemavzrd (schemavzrd)
- **Port**: 5174
- **Purpose**: Database schema documentation
- **Profile**: `tools`

## Service Startup Profile

### CPU Profile
- All services with CPU-optimized configurations
- No GPU reservations
- Ollama disabled (or CPU-only models)

### GPU Profile
- Backend with GPU support
- Ollama with GPU access
- Docling with VLM support
- Agent Zero with GPU

### Docked Profile
- Uses parent networks
- Shares parent infrastructure
- Disables local duplicates

## Health Check Summary

| Service | Standalone | Docked | Critical |
|---------|-----------|--------|----------|
| supabase-db | Yes | No (parent) | Yes |
| nats | Yes | No (parent) | Yes |
| backend | Yes | Yes | Yes |
| frontend | Yes | Yes | Yes |
| neo4j | Yes | Yes | No |
| clickhouse | Yes | Yes | No |
| tensorzero | Yes | No (parent) | Yes |
| agent-zero | Yes | Yes | No |
| ollama | Yes | No (parent) | No |

## Environment Profiles

### env.shared
Base configuration for all services:
- NATS URL
- TensorZero URL
- Service discovery endpoints
- Data service URLs

### env.tier-api
API tier specific:
- Rate limiting
- CORS origins
- API keys

### env.tier-data
Data tier specific:
- Database credentials
- Storage endpoints
- Backup configurations

## Service Resource Limits

| Service | CPU Limit | Memory Limit | GPU |
|---------|-----------|--------------|-----|
| backend | Unspecified | Unspecified | All (GPU profile) |
| frontend | Unspecified | Unspecified | None |
| agent-zero | Unspecified | Unspecified | All (GPU profile) |
| ollama | Unspecified | Unspecified | 1 (GPU profile) |
| neo4j | 1G heap | 512M pagecache | None |
| clickhouse | Unspecified | Unspecified | None |
| supabase-db | Unspecified | Unspecified | None |

## Service Endpoints Summary

### User-Facing Endpoints

| URL | Service | Purpose |
|-----|---------|---------|
| `http://localhost:8484` | Backend | API base URL |
| `http://localhost:3001` | Frontend | Web UI |
| `http://localhost:50051` | Agent Zero | Agent UI |
| `http://localhost:17474` | Neo4j | Graph browser |
| `http://localhost:54321` | Supabase | API gateway |
| `http://localhost:61208` | Glances | System monitor |
| `http://localhost:5173` | Datavzrd | Data viz (tools) |
| `http://localhost:5174` | Schemavzrd | Schema docs (tools) |

### Internal Endpoints

| URL | Service | Purpose |
|-----|---------|---------|
| `http://backend:8484` | Backend | Internal API |
| `http://nats:4222` | NATS | Message bus (docked) |
| `http://nats:4223` | NATS | Message bus (standalone) |
| `http://tensorzero-gateway:3030` | TensorZero | LLM gateway |
| `http://neo4j:7687` | Neo4j | Bolt protocol |
| `http://ollama:11434` | Ollama | LLM API |
| `http://cipher-service:3000` | Cipher | Memory service |
| `http://supabase-db:5432` | Supabase | Database |
