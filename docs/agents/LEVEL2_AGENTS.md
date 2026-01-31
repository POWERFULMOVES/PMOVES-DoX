# Level 2 Agents: Self-Evolving Agents

Level 2 agents in the PMOVES-BoTZ ecosystem are **self-evolving agents** that learn from interactions, extract patterns, and improve over time. They leverage TensorZero for unified LLM orchestration and Cipher Memory for persistent learning.

## Agent Tier Overview

| Agent | Purpose | TensorZero Integration | Memory/Learning |
|-------|---------|----------------------|-----------------|
| **Cipher Memory** | Persistent memory & reasoning | Full (orchestrator + qwen3:8b) | Pattern extraction, cross-session |
| **VL Sentinel** | Vision-language monitoring | Partial (GoG-ready) | Diagnostic patterns |
| **n8n Agent** | Workflow automation | Full (TensorZero gateway) | Workflow reasoning traces |

---

## 1. Cipher Memory Agent

**Location**: `features/cipher/memAgent/`

**Configuration File**: `cipher_pmoves.yml`

### TensorZero Migration (COMPLETED)

Cipher Memory has been migrated from Venice.ai to TensorZero-only configuration:

**Previous Configuration (Venice.ai)**:
```yaml
llm:
  provider: openai
  model: llama-3.2-3b-instruct
  apiKey: $VENICE_API_KEY
  baseURL: https://api.venice.ai/api/v1
```

**New Configuration (TensorZero)**:
```yaml
llm:
  provider: openai
  model: orchestrator
  apiKey: $TENSORZERO_API_KEY
  baseURL: ${TENSORZERO_URL:-http://host.docker.internal:3030}/openai/v1
  maxIterations: 50
  temperature: 0.7
  maxTokens: 2048

embedding:
  type: openai
  model: qwen3:8b
  apiKey: $TENSORZERO_API_KEY
  baseURL: ${TENSORZERO_URL:-http://host.docker.internal:3030}/openai/v1
  dimensions: 4096
```

### Advanced Features Enabled

#### Memory Persistence
```yaml
memory:
  persistAcrossSessions: true
  projectMemory: true
```

- **persistAcrossSessions**: Memories survive agent restarts
- **projectMemory**: Enables memory sharing across agent instances in the same project

#### Pattern Extraction & Reasoning
```yaml
reasoning:
  enabled: true
  extractPatterns: true
  patternTypes:
    - workflow_execution
    - api_call_sequence
    - error_resolution
    - optimization_opportunity
  minConfidence: 0.7
  maxPatternsPerSession: 100
```

- **extractPatterns**: Automatically identifies recurring patterns
- **patternTypes**: Categories of patterns to extract
- **minConfidence**: Threshold for pattern acceptance (0.7 = 70%)

#### NATS Event Publishing
```yaml
nats:
  enabled: true
  subjects:
    memoryStored: botz.cipher.memory.stored.v1
    memoryRecalled: botz.cipher.memory.recalled.v1
    patternDetected: botz.cipher.pattern.detected.v1
    reasoningComplete: botz.cipher.reasoning.complete.v1
```

Enables real-time event streaming for:
- Memory operations tracking
- Pattern detection notifications
- Reasoning trace completion events

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TENSORZERO_API_KEY` | TensorZero authentication key | Required |
| `TENSORZERO_URL` | TensorZero gateway URL | `http://host.docker.internal:3030` |

### MCP Tools Exposed

- `store_memory`: Store content with semantic indexing
- `recall_memory`: Retrieve memories by semantic query
- `extract_patterns`: Analyze interaction history for patterns
- `store_reasoning`: Persist decision traces for learning

---

## 2. VL Sentinel Agent

**Location**: `features/vl_sentinel/`

**Primary File**: `app_vl.py`

### Current Configuration

```python
PROVIDER = os.environ.get("VL_PROVIDER", "ollama").lower()
DEFAULT_MODELS = {
    "ollama": "qwen2.5-vl:14b",
    "openai": "gpt-4o-mini"
}
MODEL = os.environ.get("VL_MODEL") or DEFAULT_MODELS.get(PROVIDER, "qwen2.5-vl:14b")
OLLAMA = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
```

### GoG (Glance-or-Gaze) Readiness

VL Sentinel is **prepared for GoG integration** with the following capabilities:

| Capability | Status | Notes |
|------------|--------|-------|
| Multi-image input | Ready | Accepts `List[ImageInput]` |
| Base64 encoding | Ready | Handles both URL and B64 |
| Diagnostic prompting | Ready | Vision-language monitoring prompts |
| Provider switching | Ready | Ollama/OpenAI switchable |

**GoG Integration Path**:
1. Add GoG endpoint for gaze-based attention routing
2. Integrate with TensorZero for model orchestration
3. Enable pattern storage via Cipher Memory

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/vl/guide` | POST | Vision-language diagnostic guidance |
| `/health` | GET | Health check with provider/model info |

### Request Schema

```python
class GuideRequest(BaseModel):
    task: str                              # Task description
    images: Optional[List[ImageInput]]     # Screenshots/images
    logs: Optional[List[str]]              # Log entries
    metrics: Optional[Dict[str, Any]]      # Numeric metrics
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VL_PROVIDER` | Vision provider (ollama/openai) | `ollama` |
| `VL_MODEL` | Vision model name | `qwen2.5-vl:14b` (Ollama) |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://host.docker.internal:11434` |
| `OPENAI_API_KEY` | OpenAI API key (if using openai) | - |

### Future Enhancements

- [ ] TensorZero routing for vision models
- [ ] GoG attention mechanism integration
- [ ] Pattern storage via Cipher Memory
- [ ] NATS event publishing for diagnostics

---

## 3. n8n Agent

**Location**: `features/n8n/`

**Primary File**: `app_n8n_agent.py`

### TensorZero Integration

The n8n Agent uses TensorZero for intelligent workflow suggestions:

```python
class TensorZeroClient:
    def __init__(self, base_url=None, model=None):
        self.base_url = (
            base_url
            or os.environ.get("TENSORZERO_BASE_URL", "http://tensorzero-gateway:3030")
        ).rstrip("/")
        self.model = model or os.environ.get("TENSORZERO_MODEL", "orchestrator")
        self.api_key = os.environ.get("TENSORZERO_API_KEY", "")
```

### LLM-Powered Features

1. **Workflow Suggestions**: Uses TensorZero to recommend optimal workflows for tasks
2. **Skill Search**: Semantic search across stored automation patterns
3. **Reasoning Storage**: Persists decision traces for learning

### Cipher Memory Integration

```python
class CipherMemoryClient:
    async def search_skills_async(self, query: str, limit: int = 5) -> str:
        # Uses TensorZero LLM for intelligent search

    async def suggest_workflow_async(self, task_description: str, workflows: List) -> str:
        # LLM-backed workflow recommendation
```

### MCP Tools

| Tool | Description |
|------|-------------|
| `n8n_list_workflows` | List all workflows with status |
| `n8n_get_workflow` | Get workflow definition by ID |
| `n8n_execute_workflow` | Execute workflow with input data |
| `n8n_create_workflow` | Create new workflow from JSON |
| `n8n_update_workflow` | Update existing workflow |
| `n8n_delete_workflow` | Delete workflow by ID |
| `n8n_toggle_workflow` | Activate/deactivate workflow |
| `n8n_get_executions` | Get execution history |
| `n8n_store_workflow_doc` | Store workflow documentation in Cipher |
| `n8n_search_skills` | Search automation patterns |
| `n8n_suggest_workflow` | LLM-powered workflow suggestion |
| `n8n_learn_from_execution` | Store reasoning for learning |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `N8N_API_URL` | n8n REST API URL | `http://n8n:5678/api/v1` |
| `N8N_API_KEY` | n8n API key | Required |
| `TENSORZERO_BASE_URL` | TensorZero gateway URL | `http://tensorzero-gateway:3030` |
| `TENSORZERO_MODEL` | Default model for inference | `orchestrator` |
| `TENSORZERO_API_KEY` | TensorZero authentication | - |
| `CIPHER_MEMORY_PATH` | Path to Cipher installation | `/app/features/cipher/pmoves_cipher` |

### Learning Flow

```
User Task
    |
    v
n8n_suggest_workflow (TensorZero LLM)
    |
    v
Workflow Execution
    |
    v
n8n_learn_from_execution (Cipher Memory)
    |
    v
Future suggestions improved
```

---

## Cross-Agent Integration

### Memory Sharing Pattern

All Level 2 agents can share knowledge through Cipher Memory:

```
VL Sentinel                n8n Agent
     |                          |
     v                          v
 [Diagnostic]            [Workflow Pattern]
     |                          |
     +----------+---------------+
                |
                v
        Cipher Memory Store
                |
                v
        Pattern Extraction
                |
                v
        NATS Event Bus
```

### NATS Subjects

| Subject | Publisher | Description |
|---------|-----------|-------------|
| `botz.cipher.memory.stored.v1` | Cipher | Memory stored event |
| `botz.cipher.memory.recalled.v1` | Cipher | Memory recalled event |
| `botz.cipher.pattern.detected.v1` | Cipher | New pattern detected |
| `botz.mcp.tool.executed.v1` | All | MCP tool execution event |

---

## Configuration Summary

### Required Environment Variables

```bash
# TensorZero (Required for all Level 2 agents)
TENSORZERO_URL=http://host.docker.internal:3030
TENSORZERO_API_KEY=<your-api-key>

# n8n Agent
N8N_API_URL=http://n8n:5678/api/v1
N8N_API_KEY=<your-n8n-api-key>

# VL Sentinel (defaults to Ollama)
VL_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### Docker Compose Integration

Level 2 agents are orchestrated via the main `docker-compose.yml`:

```yaml
services:
  cipher-memory:
    build: ./features/cipher
    environment:
      - TENSORZERO_URL=${TENSORZERO_URL:-http://host.docker.internal:3030}
      - TENSORZERO_API_KEY=${TENSORZERO_API_KEY}
    volumes:
      - cipher-data:/app/data

  vl-sentinel:
    build: ./features/vl_sentinel
    ports:
      - "7072:7072"
    environment:
      - VL_PROVIDER=${VL_PROVIDER:-ollama}
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://host.docker.internal:11434}

  n8n-agent:
    build: ./features/n8n
    environment:
      - N8N_API_URL=${N8N_API_URL:-http://n8n:5678/api/v1}
      - N8N_API_KEY=${N8N_API_KEY}
      - TENSORZERO_BASE_URL=${TENSORZERO_URL:-http://tensorzero-gateway:3030}
```

---

## Changes Log

### 2026-01-26: Cipher Memory TensorZero Migration

**File Modified**: `features/cipher/memAgent/cipher_pmoves.yml`

**Changes**:
1. Removed Venice.ai configuration entirely
2. Added TensorZero orchestrator as primary LLM
3. Configured qwen3:8b for embeddings via TensorZero
4. Enabled `persistAcrossSessions: true`
5. Enabled `projectMemory: true`
6. Added reasoning configuration with pattern extraction
7. Added NATS event publishing subjects
8. Enhanced system prompt for Level 2 responsibilities
9. Increased vector dimensions to 4096 for qwen3:8b compatibility
10. Added entity extraction configuration

**Impact**:
- All Cipher Memory LLM calls now route through TensorZero
- Unified observability via TensorZero metrics
- Pattern extraction enabled for self-evolution
- Cross-session memory persistence enabled
