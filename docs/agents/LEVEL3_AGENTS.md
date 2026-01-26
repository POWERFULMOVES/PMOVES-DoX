# Level 3 (Collective) Agents Documentation

> Multi-agent orchestration layer for PMOVES-BoTZ ecosystem

## Overview

Level 3 agents represent the **Collective** tier of the PMOVES agent hierarchy, providing:
- Unified MCP gateway routing
- Multi-agent coordination via NATS
- TensorZero LLM gateway integration
- Session persistence and forking
- Observability hooks for audit, cost tracking, and event publishing

## Architecture

```
                      +------------------+
                      |  Python Gateway  |
                      |    Port 2091     |
                      +--------+---------+
                               |
           +-------------------+-------------------+
           |                   |                   |
    +------v------+     +------v------+    +------v------+
    |  MCP Bridge |     | cipher-mem  |    |   Docling   |
    |  Port 8100  |     |  stdio      |    |  Port 3020  |
    +------+------+     +-------------+    +-------------+
           |
    +------v----------------------------------------------+
    |                  MCP Bridge Tools                   |
    | +----------+ +----------+ +----------+ +----------+ |
    | |  Hi-RAG  | | TensorZ  | |   NATS   | | Supabase | |
    | +----------+ +----------+ +----------+ +----------+ |
    +-----------------------------------------------------+
           |
    +------v----------------------------------------------+
    |                    Agent SDK                        |
    | +-----------+ +-------------+ +------------------+  |
    | | PMOVESAgt | | SessionMgr  | | Hooks (3 types) |  |
    | +-----------+ +-------------+ +------------------+  |
    |                      |                              |
    | +-----------+ +-----------+ +-----------+ +-------+ |
    | |Researcher | |CodeReview | |MediaProc  | |Knowldg| |
    | +-----------+ +-----------+ +-----------+ +-------+ |
    +-----------------------------------------------------+
```

---

## 1. Python Gateway

**Location**: `features/gateway/python-gateway/`
**Port**: 2091
**Purpose**: Unified MCP tool routing for BoTZ agents

### Configuration

**docker-compose.yml** (`features/gateway/docker-compose.yml`):
```yaml
services:
  python-gateway:
    build:
      context: ./python-gateway
      dockerfile: Dockerfile
    container_name: pmoves-python-gateway
    ports:
      - "2091:2091"
    environment:
      - PORT=2091
      - HOST=0.0.0.0
    depends_on:
      mcp-bridge:
        condition: service_healthy
```

### Upstream MCP Servers

The gateway routes to the following upstream servers:

| Server | Transport | Endpoint | Description |
|--------|-----------|----------|-------------|
| n8n-agent | stdio | docker exec | n8n Workflow Automation Agent |
| hostinger | stdio | docker exec | Hostinger VPS/DNS/Domain Management |
| cipher-memory | http | `http://cipher-memory:8081` | Persistent Memory & Reasoning |
| e2b | http | `http://e2b-runner:7071` | E2B Code Sandbox |
| vl-sentinel | http | `http://vl-sentinel:7072` | Vision-Language Guidance |
| docling | sse | `http://docling-mcp:3020/sse` | Document Processing |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with upstream server count |
| `/servers` | GET | List all configured upstream servers |
| `/tools` | GET | Get aggregated tools from all servers |
| `/tools/{server}` | GET | Get tools from specific server |
| `/call` | POST | Call a tool by name |
| `/mcp` | POST | MCP JSON-RPC endpoint |

### Tool Routing

Tools are routed using qualified names: `server:tool_name`
```json
{
  "tool": "cipher-memory:store_memory",
  "arguments": {"key": "test", "content": "Hello"}
}
```

---

## 2. MCP Bridge

**Location**: `features/mcp_bridge/`
**Port**: 8100
**Purpose**: Combined MCP server exposing all PMOVES services as tools

### Configuration

**Environment Variables**:
```yaml
TENSORZERO_URL: ${TENSORZERO_URL:-http://tensorzero:3030}
HIRAG_URL: ${HIRAG_URL:-http://hi-rag-gateway-v2:8086}
NATS_URL: ${NATS_URL:-nats://nats:4222}
SUPABASE_URL: ${SUPABASE_URL:-http://supabase:3010}
SUPABASE_ANON_KEY: ${SUPABASE_ANON_KEY:-}
```

### Authentication

**File**: `features/mcp_bridge/auth.py`

Uses JWT validation with Supabase JWT secret:
- Validates Bearer tokens from `Authorization` header
- Supports query parameter tokens (`?token=<jwt>`)
- Rejects anonymous keys (role=anon)
- Development mode allows all if no secret configured

```python
# Example validation
is_valid, payload, message = validate_jwt_token(token)
if not is_valid:
    raise HTTPException(status_code=401, detail=message)
```

### Tools Exposed

#### Hi-RAG Tools (`tools/hirag.py`)

| Tool | Description |
|------|-------------|
| `hirag_query` | Full hybrid search with vector, graph, and full-text |
| `hirag_similarity` | Vector-only similarity search |
| `hirag_graph` | Knowledge graph traversal |
| `hirag_health` | Service health check |

#### TensorZero Tools (`tools/tensorzero.py`)

| Tool | Description |
|------|-------------|
| `tensorzero_chat` | Chat completion with dynamic model selection |
| `tensorzero_embed` | Generate embeddings |
| `tensorzero_providers` | List available providers |
| `tensorzero_health` | Gateway health check |

**Dynamic Model Routing Syntax**:
```
provider::model_name
```

Examples:
- `openai::qwen3:8b` - Ollama local
- `anthropic::claude-sonnet-4-5-20250514` - Anthropic cloud
- `google_ai_studio_gemini::gemini-2.0-flash` - Gemini cloud

#### NATS Tools (`tools/nats.py`)

| Tool | Description |
|------|-------------|
| `nats_publish` | Publish event to a subject |
| `nats_request` | Request-reply pattern |
| `nats_subjects` | List common PMOVES subjects |
| `nats_health` | Connection status check |

#### Supabase Tools (`tools/supabase.py`)

| Tool | Description |
|------|-------------|
| `supabase_query` | Query table via PostgREST |
| `supabase_insert` | Insert records |
| `supabase_rpc` | Call database functions |
| `supabase_tables` | List available tables |
| `supabase_health` | Connection status |

---

## 3. Agent SDK

**Location**: `features/agent_sdk/`
**Purpose**: Production-ready agent implementation with PMOVES ecosystem integration

### PMOVESAgent (`pmoves_agent.py`)

Core agent class leveraging Claude Agent SDK with full ecosystem access.

#### Configuration

```python
agent = PMOVESAgent(
    agent_id="research-agent",
    role="researcher",  # researcher, code_reviewer, media_processor, knowledge_manager, general
    model="openai::qwen3:8b",  # TensorZero dynamic syntax
    allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
    enable_nats=True,
    enable_hooks=True,
)
```

#### Service Endpoints (Environment Variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `TENSORZERO_URL` | `http://localhost:3030` | LLM gateway |
| `HIRAG_URL` | `http://localhost:8086` | Knowledge retrieval |
| `NATS_URL` | `nats://localhost:4222` | Event coordination |
| `SUPABASE_URL` | `http://localhost:3010` | Data persistence |
| `AGENT_ZERO_URL` | `http://localhost:8080` | Orchestration |

#### MCP Server Configuration

The agent configures MCP servers for PMOVES service access:

```python
{
    "hirag": {
        "type": "http",
        "url": "http://localhost:8086",
        "description": "Hi-RAG v2 hybrid knowledge retrieval",
    },
    "tensorzero": {
        "type": "http",
        "url": "http://localhost:3030/openai/v1",
        "description": "TensorZero LLM gateway with dynamic model routing",
    },
    "nats": {
        "command": "python",
        "args": ["-m", "pmoves_botz.features.mcp_bridge.tools.nats"],
    },
    "supabase": {
        "type": "http",
        "url": "http://localhost:3010",
    },
}
```

#### Usage

```python
async with PMOVESAgent("my-agent", role="researcher") as agent:
    async for message in agent.execute("Analyze the PMOVES architecture"):
        if message.type == "assistant":
            print(message.content)
        elif message.type == "result":
            print(f"Final result: {message.result}")
```

---

### Hooks System

Hooks fire at key points for observability and coordination.

#### Audit Hook (`hooks/audit.py`)

**Purpose**: Security auditing and debugging

**Storage**:
- Local: `~/.pmoves/audit/tool_usage.jsonl`
- Supabase: `agent_audit_logs` table

**Features**:
- Logs tool invocations with timestamps
- Redacts sensitive data (passwords, tokens, API keys, JWTs)
- Tracks execution duration and success/failure

**Redaction Patterns**:
```python
SENSITIVE_PATTERNS = [
    "password", "passwd", "pwd", "secret", "token",
    "api_key", "credential", "authorization", "bearer"
]
```

#### Cost Tracker Hook (`hooks/cost_tracker.py`)

**Purpose**: Token usage and API cost monitoring

**Storage**:
- Local: `~/.pmoves/metrics/cost_tracking.jsonl`
- Supabase: `agent_cost_metrics` table
- ClickHouse: TensorZero observability

**Model Costs (per 1K tokens, USD)**:

| Model | Input | Output |
|-------|-------|--------|
| claude-sonnet-4-5 | $0.003 | $0.015 |
| claude-opus-4 | $0.015 | $0.075 |
| claude-3-haiku | $0.00025 | $0.00125 |
| gpt-4o | $0.0025 | $0.01 |
| gpt-4o-mini | $0.00015 | $0.0006 |
| gemini-2.0-flash | $0.00015 | $0.0006 |
| qwen3:8b (local) | $0 | $0 |
| llama3.1 (local) | $0 | $0 |

**Budget Alerts**:
```python
tracker = CostTrackerHook(agent_id, budget_limit=10.0)  # $10 limit
```

#### NATS Publisher Hook (`hooks/nats_publisher.py`)

**Purpose**: Multi-agent coordination via event publishing

**Events Published**:

| Subject | Description |
|---------|-------------|
| `agent.tool.pre.v1` | Before tool execution |
| `agent.tool.post.v1` | After tool execution |
| `botz.work.progress.v1` | Task progress updates |

**Event Payload Structure**:
```json
{
  "agent_id": "research-agent",
  "tool_name": "Read",
  "success": true,
  "duration_ms": 150,
  "timestamp": "2025-01-25T12:00:00Z"
}
```

---

### Session Manager (`session_manager.py`)

**Purpose**: Session persistence with resume, fork, and checkpoint capabilities

**Storage Backends**:
- `file`: Local JSON (`~/.pmoves/sessions/`)
- `supabase`: PostgreSQL `agent_sessions` table
- `surrealdb`: Open Notebook integration

**Session State**:
```python
@dataclass
class SessionState:
    session_id: str
    agent_id: str
    role: str
    created_at: str
    updated_at: str
    parent_session_id: Optional[str] = None
    fork_count: int = 0
    checkpoint_count: int = 0
    status: str = "active"  # active, completed, archived
    context: Optional[dict] = None
    metadata: Optional[dict] = None
```

**Operations**:

| Method | Description |
|--------|-------------|
| `create_session()` | Create new session |
| `resume()` | Continue from previous session |
| `fork()` | Branch for parallel exploration |
| `checkpoint()` | Save state for rollback |
| `list_sessions()` | List with filtering |
| `archive_session()` | Mark inactive |

---

### Subagents

Specialized agents for specific task types.

#### Researcher (`subagents/researcher.py`)

**Purpose**: Deep research via Hi-RAG, SupaSerch, and DeepResearch

**Services Used**:
- Hi-RAG v2: Hybrid knowledge retrieval
- SupaSerch: Multimodal holographic research
- DeepResearch: LLM research planning
- Web Search: Current information

**Methods**:
```python
async with ResearcherAgent("research-001") as agent:
    result = await agent.research(
        query="Latest quantum computing developments",
        depth="comprehensive",  # basic, detailed, comprehensive
        sources=["knowledge_base", "web", "papers"],
        max_results=20
    )
```

**NATS Events**:
- `research.deepresearch.request.v1`: Triggers DeepResearch planning

#### Code Reviewer (`subagents/code_reviewer.py`)

**Purpose**: Security-focused code analysis

**Checks**:
- OWASP Top 10 vulnerabilities
- SQL injection patterns
- Command injection patterns
- XSS vulnerabilities
- Hardcoded secrets (CWE-798)
- Code quality (line length, TODOs)

**Severity Levels**: Critical, High, Medium, Low, Info

**Methods**:
```python
async with CodeReviewerAgent("reviewer-001") as agent:
    result = await agent.review_file(
        file_path="/path/to/code.py",
        focus=["security", "quality"]
    )

    # Or review directory
    result = await agent.review_directory(
        directory="/path/to/project",
        extensions=[".py", ".js"],
        recursive=True
    )
```

#### Media Processor (`subagents/media_processor.py`)

**Purpose**: Video/audio processing workflows

**Services Used**:
- PMOVES.YT: YouTube ingestion
- FFmpeg-Whisper: Transcription
- Media-Video Analyzer: YOLOv8 object detection
- Media-Audio Analyzer: Emotion/speaker detection
- MinIO: Artifact storage

**Methods**:
```python
async with MediaProcessorAgent("media-001") as agent:
    # Full pipeline
    result = await agent.process_video(
        url="https://youtube.com/watch?v=xxx",
        transcribe=True,
        analyze_objects=True,
        analyze_audio=True
    )

    # Individual operations
    await agent.ingest_youtube(url, auto_transcribe=True)
    await agent.transcribe(file_path, language="en")
    await agent.analyze_video(file_path, frame_interval=5)
```

**NATS Events**:
- `ingest.video.started.v1`
- `media.pipeline.started.v1`

#### Knowledge Manager (`subagents/knowledge_manager.py`)

**Purpose**: Hi-RAG knowledge base management

**Services Used**:
- Qdrant: Vector embeddings
- Neo4j: Knowledge graph
- Meilisearch: Full-text search
- Extract Worker: Ingestion pipeline

**Methods**:
```python
async with KnowledgeManagerAgent("knowledge-001") as agent:
    # Query knowledge
    results = await agent.query("What is PMOVES?", top_k=10, rerank=True)

    # Ingest document
    await agent.ingest_document(doc_id, content, metadata)

    # Graph query
    results = await agent.graph_query(entity="TensorZero", depth=2)

    # Health check
    health = await agent.check_health()
```

---

## 4. Core MCP Catalog

**Location**: `core/mcp/catalog.yml`
**Purpose**: Central registry of all MCP servers

### Registered Servers

| Server | Transport | Authentication | Description |
|--------|-----------|----------------|-------------|
| skills | stdio | None | Agent skill management |
| docling | SSE | JWT (SUPABASE_JWT_SECRET) | Document processing |
| e2b | SSE | JWT (SUPABASE_JWT_SECRET) | Code sandbox |
| vl-sentinel | SSE | JWT (SUPABASE_JWT_SECRET) | Vision-language |
| cipher-memory | stdio | TENSORZERO_API_KEY | Persistent memory |
| postman | stdio | POSTMAN_API_KEY | API testing |
| n8n-agent | stdio | N8N_API_KEY | Workflow automation |
| hostinger | stdio | HOSTINGER_API_KEY | VPS/DNS management |

### Environment Variable Bindings

```yaml
# TensorZero Integration
TENSORZERO_BASE_URL: ${TENSORZERO_BASE_URL:-http://tensorzero:3000}

# n8n Integration
N8N_API_KEY: ${N8N_API_KEY}
N8N_API_URL: ${N8N_API_URL:-http://n8n:5678/api/v1}

# External API Keys
# Note: Cipher memory uses TENSORZERO_API_KEY (Venice.ai removed)
POSTMAN_API_KEY: ${POSTMAN_API_KEY}      # Postman collections
HOSTINGER_API_KEY: ${HOSTINGER_API_KEY}  # Hostinger VPS
```

---

## NATS Event Subjects Reference

### Agent Events

| Subject | Description |
|---------|-------------|
| `agent.tool.pre.v1` | Before tool execution |
| `agent.tool.post.v1` | After tool execution |
| `agent.task.start.v1` | Task started |
| `agent.handoff.request.v1` | Task delegation request |
| `agent.handoff.completed.v1` | Task delegation completed |

### BoTZ Events

| Subject | Description |
|---------|-------------|
| `botz.agent.heartbeat.v1` | Agent presence (every 30s) |
| `botz.work.available.v1` | Broadcast available work |
| `botz.work.claimed.v1` | Work item claimed |
| `botz.work.completed.v1` | Work completed with result |
| `botz.work.progress.v1` | Task progress updates |

### Research Events

| Subject | Description |
|---------|-------------|
| `research.deepresearch.request.v1` | Request LLM research planning |
| `research.deepresearch.result.v1` | Research results |
| `supaserch.request.v1` | Multimodal holographic research |
| `supaserch.result.v1` | SupaSerch results |

### Ingest Events

| Subject | Description |
|---------|-------------|
| `ingest.file.added.v1` | New file ingested |
| `ingest.transcript.ready.v1` | Transcript completed |
| `ingest.summary.ready.v1` | Summary generated |
| `ingest.chapters.ready.v1` | Chapter markers created |
| `ingest.video.started.v1` | Video ingestion started |
| `media.pipeline.started.v1` | Media pipeline started |

---

## Multi-Agent Coordination Patterns

### 1. Heartbeat Pattern

Agents publish heartbeats every 30 seconds for presence tracking:

```python
await self._publish_event("botz.agent.heartbeat.v1", {
    "agent_id": self.agent_id,
    "agent_type": "sdk",
    "role": self.role,
    "model": self.model,
    "status": "active",
    "capabilities": self.allowed_tools,
    "timestamp": "..."
})
```

### 2. Work Distribution Pattern

```
Agent A                    NATS                     Agent B
   |                         |                         |
   |-- botz.work.available -->|                        |
   |                         |<-- botz.work.claimed ---|
   |                         |                         |
   |                         |<-- botz.work.completed -|
```

### 3. Handoff Pattern

When delegating tasks to local models:

```python
await agent.delegate_to_local(
    task="Summarize this document",
    model="openai::qwen3:8b",
    timeout=300.0
)
```

Events:
1. `agent.handoff.request.v1` - Before delegation
2. `agent.handoff.completed.v1` - After completion

### 4. Session Forking Pattern

For parallel exploration:

```python
# Original session
async for msg in manager.resume(session_id, "Continue analysis"):
    ...

# Fork for alternative approach
async for msg in manager.fork(session_id, "Try different approach"):
    ...
```

---

## TensorZero Integration Status

| Component | Integration | Notes |
|-----------|-------------|-------|
| Python Gateway | - | No direct TensorZero integration |
| MCP Bridge | Active | `tensorzero_chat`, `tensorzero_embed` tools |
| Agent SDK | Active | Dynamic model routing, delegation to local |
| n8n-agent | Active | Uses `TENSORZERO_BASE_URL` |
| Subagents | Indirect | Via Agent SDK and MCP Bridge |

### TensorZero URL Usage

The Agent SDK uses TensorZero for:
1. **Chat Completions**: `/v1/chat/completions`
2. **Embeddings**: `/v1/embeddings`
3. **Health Check**: `/health`

Dynamic routing syntax enables switching between local and cloud models:
```python
# Local (Ollama)
model="openai::qwen3:8b"

# Cloud (Anthropic)
model="anthropic::claude-sonnet-4-5-20250514"

# Cloud (Gemini)
model="google_ai_studio_gemini::gemini-2.0-flash"
```

---

## Quick Reference

### Start All Level 3 Services

```bash
docker compose -f features/gateway/docker-compose.yml up -d
```

### Health Checks

```bash
# Python Gateway
curl http://localhost:2091/health

# MCP Bridge
curl http://localhost:8100/healthz

# List all tools
curl http://localhost:2091/tools
```

### Create and Use Agent

```python
from pmoves_botz.features.agent_sdk import PMOVESAgent

async with PMOVESAgent("my-agent", role="general") as agent:
    # Query knowledge base
    results = await agent.query_hirag("What is PMOVES?")

    # Delegate to local model
    response = await agent.delegate_to_local("Summarize: " + text)

    # Full task execution
    async for msg in agent.execute("Analyze architecture"):
        print(msg)
```

---

## Related Documentation

- [LEVEL1_AGENTS.md](./LEVEL1_AGENTS.md) - Individual agents (Docling, E2B, VL-Sentinel)
- [LEVEL2_AGENTS.md](./LEVEL2_AGENTS.md) - Pairwise agents (Cipher Memory, Postman)
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Overall system architecture
- [DOCKING_GUIDE.md](../DOCKING_GUIDE.md) - Integration with PMOVES.AI
