# Level 1 (Foundational) Agents Documentation

> PMOVES-BoTZ Foundational Agent Layer Review
> Generated: 2026-01-25
> Working Directory: `PMOVES-DoX/external/PMOVES-BoTZ`

## Overview

Level 1 agents are the foundational building blocks of the PMOVES-BoTZ multi-agent platform. These agents provide deterministic, infrastructure-level capabilities that higher-level agents depend on. They are designed to be reliable, self-contained, and operate independently of LLM orchestration (though some may integrate with TensorZero for enhanced features).

## Architecture Summary

```
                    Level 1 (Foundational) Agents
+----------------------------------------------------------------------------+
|                                                                            |
|  +----------------+  +----------------+  +----------------+                |
|  |  Docling MCP   |  |  E2B Runner    |  |  Postman MCP   |                |
|  |  (Port 3020)   |  |  (Port 7071)   |  |  (STDIO)       |                |
|  |  SSE Transport |  |  SSE Transport |  |  Docker Exec   |                |
|  +----------------+  +----------------+  +----------------+                |
|                                                                            |
|  +----------------+  +----------------+                                    |
|  | Hostinger MCP  |  |  Skills Server |                                    |
|  |  (STDIO)       |  |  (STDIO)       |                                    |
|  |  Docker Exec   |  |  Docker Exec   |                                    |
|  +----------------+  +----------------+                                    |
|                                                                            |
+----------------------------------------------------------------------------+
```

---

## 1. Docling MCP

### Description

Docling MCP is a document processing service that converts various document formats (PDF, DOCX, HTML, images) into structured data. It uses IBM's Docling library for advanced document understanding including table extraction, figure analysis, and layout preservation.

### Current Configuration

| Property | Value |
|----------|-------|
| **Service Name** | `docling-mcp` |
| **Container Name** | `pmoves-botz-docling` |
| **Port** | 3020 |
| **Transport** | SSE (Server-Sent Events) |
| **Profile** | `tools` |
| **Health Endpoint** | `http://localhost:3020/health` |

### Files and Locations

| File | Path | Purpose |
|------|------|---------|
| Catalog Entry | `core/mcp/catalog.yml` | MCP server registration |
| Docker Compose | `docker-compose.yml` (root) | Service definition |
| Technical Reference | `DOCLING_MCP_TECHNICAL_REFERENCE.md` | Implementation details |
| Implementation Guide | `DOCLING_MCP_IMPLEMENTATION_GUIDE.md` | Setup and usage |
| Quick Reference | `DOCLING_MCP_QUICK_REFERENCE.md` | Commands reference |

### Catalog Configuration

```yaml
docling:
  url: ${DOCLING_URL:-http://localhost:3020/sse}
  transport: sse
```

### Docker Compose Configuration

```yaml
docling-mcp:
  build:
    context: ./features/docling
    dockerfile: Dockerfile.docling-mcp
  container_name: pmoves-botz-docling
  restart: unless-stopped
  environment:
    PORT: 3020
    HOST: 0.0.0.0
    DOCLING_VLM_REPO: ${DOCLING_VLM_REPO:-}  # Optional VLM for figures
    HF_API_KEY: ${HF_API_KEY:-}               # HuggingFace token
  ports:
    - "${DOCLING_PORT:-3020}:3020"
  profiles:
    - tools
```

### TensorZero Integration

| Status | Details |
|--------|---------|
| **LLM Routing** | Not Required (deterministic document processing) |
| **VLM Support** | Optional via `DOCLING_VLM_REPO` for image/figure understanding |
| **Enhancement Opportunity** | Could route VLM calls through TensorZero if `ibm-granite/granite-docling-258m-demo` is configured |

### Key Features

- **Custom SSE Handler**: Implements MCP SDK 1.21.0+ compatibility layer
- **JSON-RPC 2.0**: Full protocol compliance with proper error codes
- **Queue-Based Streams**: Asyncio queues for bidirectional communication
- **Multi-Format Support**: PDF, DOCX, HTML, images, and more

### Current State

- **Implementation**: Exists in reference documentation
- **Features Directory**: `features/docling/` referenced in docker-compose but needs verification
- **VLM Configuration**: Supports optional VLM model via environment variable

---

## 2. E2B Runner (Sandbox Execution)

### Description

E2B Runner provides secure, sandboxed code execution for Python and JavaScript. It uses E2B's cloud-based sandbox infrastructure to isolate code execution from the host system.

### Current Configuration

| Property | Value |
|----------|-------|
| **Service Name** | `e2b-runner` |
| **Container Name** | `pmoves-botz-e2b` |
| **Port** | 7071 |
| **Transport** | SSE (Server-Sent Events) |
| **Profile** | `e2b` |
| **Health Endpoint** | `http://localhost:7071/health` |

### Files and Locations

| File | Path | Purpose |
|------|------|---------|
| Catalog Entry | `core/mcp/catalog.yml` | MCP server registration |
| Docker Compose | `docker-compose.yml` (root) | Service definition |
| Environment Template | `.env.example` | API key configuration |

### Catalog Configuration

```yaml
e2b:
  url: ${E2B_URL:-http://localhost:7071/sse}
  transport: sse
```

### Docker Compose Configuration

```yaml
e2b-runner:
  build:
    context: ./features/e2b
    dockerfile: Dockerfile
  container_name: pmoves-botz-e2b
  restart: unless-stopped
  environment:
    PORT: 7071
    HOST: 0.0.0.0
    E2B_API_KEY: ${E2B_API_KEY:-}  # Required for E2B API calls
  ports:
    - "${E2B_PORT:-7071}:7071"
  profiles:
    - e2b
```

### TensorZero Integration

| Status | Details |
|--------|---------|
| **LLM Routing** | Not Required (deterministic code execution) |
| **Authentication** | Uses `SUPABASE_JWT_SECRET` for MCP auth, `E2B_API_KEY` for E2B API |
| **Enhancement Opportunity** | None - deterministic sandbox execution |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `E2B_API_KEY` | Yes | API key for E2B sandbox service |
| `E2B_PORT` | No | Override default port 7071 |

### Current State

- **Implementation**: Referenced in docker-compose.yml
- **Features Directory**: `features/e2b/` - needs Dockerfile and implementation
- **Note**: Deterministic service, no LLM configuration needed

---

## 3. Postman MCP

### Description

Postman MCP provides API collection management and request execution capabilities. It integrates with Postman's API to manage collections, run requests, and automate API testing.

### Current Configuration

| Property | Value |
|----------|-------|
| **Service Name** | `postman` |
| **Container Name** | `pmz-postman` |
| **Transport** | STDIO (via docker exec) |
| **Tools Available** | 108 Postman API tools |

### Files and Locations

| File | Path | Purpose |
|------|------|---------|
| Catalog Entry | `core/mcp/catalog.yml` | MCP server registration |
| Fix Summary | `POSTMAN_MCP_LOCAL_FIX_SUMMARY.md` | Implementation fixes documentation |

### Catalog Configuration

```yaml
postman:
  command: docker
  args:
    - exec
    - -i
    - pmz-postman
    - npx
    - "@postman/postman-mcp-server@latest"
    - "--full"
  env:
    POSTMAN_API_KEY: ${POSTMAN_API_KEY}
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTMAN_API_KEY` | Yes | Postman API key (format: `PMAK-xxx`) |
| `POSTMAN_API_BASE_URL` | No | Default: `https://api.postman.com` |

### TensorZero Integration

| Status | Details |
|--------|---------|
| **LLM Routing** | Not Required (API operations) |
| **Authentication** | Uses `POSTMAN_API_KEY` for Postman API |
| **Enhancement Opportunity** | None - deterministic API operations |

### Key Features

- **108 Tools**: Comprehensive Postman API coverage
- **STDIO Transport**: Invoked via `docker exec`
- **Full Mode**: Uses `--full` flag for complete tool set

### Current State

- **Implementation**: Working - uses official `@postman/postman-mcp-server@latest`
- **Known Issue**: STDIO-based server exits when no client connected (expected behavior)
- **Features Directory**: Not explicitly created (uses npx runtime installation)

---

## 4. Hostinger MCP

### Description

Hostinger MCP provides VPS, DNS, and domain management capabilities for Hostinger hosting infrastructure.

### Current Configuration

| Property | Value |
|----------|-------|
| **Service Name** | `hostinger` |
| **Container Name** | `pmz-hostinger` |
| **Transport** | STDIO (via docker exec) |

### Files and Locations

| File | Path | Purpose |
|------|------|---------|
| Catalog Entry | `core/mcp/catalog.yml` | MCP server registration |

### Catalog Configuration

```yaml
hostinger:
  command: docker
  args:
    - exec
    - -i
    - pmz-hostinger
    - hostinger-api-mcp
  env:
    API_TOKEN: ${HOSTINGER_API_KEY}
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HOSTINGER_API_KEY` | Yes | Hostinger API authentication token |

### TensorZero Integration

| Status | Details |
|--------|---------|
| **LLM Routing** | Not Required (infrastructure management) |
| **Authentication** | Uses `HOSTINGER_API_KEY` (mapped to `API_TOKEN`) |
| **Enhancement Opportunity** | None - deterministic API operations |

### Current State

- **Implementation**: Defined in catalog only
- **Features Directory**: `features/hostinger/` - not explicitly created
- **Note**: Uses `hostinger-api-mcp` binary, likely installed in container

---

## 5. Skills Server

### Description

The Skills Server is an MCP server that provides agent skill management capabilities. Skills are instruction-based SKILL.md files that teach agents how to perform specialized tasks. The server aggregates skills from multiple repositories and provides search, retrieval, and management tools.

### Current Configuration

| Property | Value |
|----------|-------|
| **Service Name** | `skills` |
| **Container Name** | `pmz-skills` |
| **Transport** | STDIO (via docker exec) |
| **Entry Point** | `skill_server.py` |

### Files and Locations

| File | Path | Purpose |
|------|------|---------|
| Catalog Entry | `core/mcp/catalog.yml` | MCP server registration |
| Server Implementation | `features/skills/skill_server.py` | Main MCP server |
| Skill Loader | `features/skills/skill_loader.py` | Cipher Memory integration |
| MCP Bridge | `features/skills/mcp_skill_bridge.py` | Bridge utilities |
| Sync Utility | `features/skills/sync_skills.py` | Skill synchronization |
| Tests | `features/skills/test_skills.py` | Unit tests |
| Skill Library | `.claude/skills/` | Local skill repository |

### Catalog Configuration

```yaml
skills:
  command: docker
  args:
    - exec
    - -i
    - pmz-skills
    - python
    - skill_server.py
  description: |
    Agent skill management (list, get, search skills).
    Skills are instruction-based guides that teach agents how to perform tasks.
    Available skills: docx, xlsx, pptx, pdf, mcp-builder, skill-creator,
    webapp-testing, frontend-design, canvas-design, and more.
```

### MCP Tools Provided

| Tool | Description |
|------|-------------|
| `skill_list` | List all available agent skills with names and descriptions |
| `skill_get` | Get full skill instructions by name |
| `skill_search` | Search skills by keyword in name or description |
| `skill_file` | Get contents of a specific file from a skill |
| `skill_refresh` | Refresh the skill index to pick up newly added skills |

### Skill Sources

The Skills Server aggregates skills from multiple repositories:

| Source | Path | Structure |
|--------|------|-----------|
| library | `library/` | flat |
| anthropics | `repos/anthropics-skills/skills` | flat |
| huggingface | `repos/huggingface-skills` | nested |
| skillcreator | `repos/skillcreator-skills/skills` | flat |
| aws | `repos/aws-skills/skills` | flat |
| playwright | `repos/playwright-skill/skills` | flat |
| d3js | `repos/d3js-skill` | root |
| epub | `repos/epub-skill/markdown-to-epub` | root |
| obsidian | `repos/obsidian-plugin-skill/.claude/skills` | flat |
| marketplace-code | `repos/skills-marketplace/code-operations-plugin/skills` | flat |
| marketplace-eng | `repos/skills-marketplace/engineering-workflow-plugin/skills` | flat |
| marketplace-prod | `repos/skills-marketplace/productivity-skills-plugin/skills` | flat |
| marketplace-visual | `repos/skills-marketplace/visual-documentation-plugin/skills` | flat |

### Available Skills (Sample from .claude/skills/)

- algorithmic-art
- architecture-diagram-creator
- artifacts-builder
- ask-questions-if-underspecified
- aws-agentic-ai
- aws-cdk-development
- aws-cost-operations
- aws-serverless-eda
- backend-development
- brand-guidelines
- canvas-design
- hugging-face-evaluation-manager
- skill-creator
- And many more...

### TensorZero Integration

| Status | Details |
|--------|---------|
| **LLM Routing** | Not Required (skill indexing is deterministic) |
| **Cipher Integration** | `skill_loader.py` can store skills in Cipher Memory |
| **Enhancement Opportunity** | Could use TensorZero embeddings for semantic skill search |

### Current State

- **Implementation**: Complete and functional
- **Features Directory**: `features/skills/` - fully populated
- **Skill Library**: `.claude/skills/` contains extensive skill collection
- **Cipher Integration**: Ready via `skill_loader.py`

---

## Catalog Completeness Summary

### core/mcp/catalog.yml Status

| Agent | Registered | Status |
|-------|------------|--------|
| Skills Server | Yes | Complete |
| Docling MCP | Yes | Complete |
| E2B Runner | Yes | Complete |
| VL Sentinel | Yes | Complete (Level 2 agent) |
| Cipher Memory | Yes | Complete (Level 2 agent) |
| Postman MCP | Yes | Complete |
| n8n Agent | Yes | Complete (Level 2 agent) |
| Hostinger MCP | Yes | Complete |

### Missing from Catalog

All Level 1 agents are properly registered in `core/mcp/catalog.yml`.

---

## TensorZero Integration Summary

| Agent | Requires LLM | Current State | Recommendation |
|-------|--------------|---------------|----------------|
| Docling MCP | Optional VLM | Direct provider | Keep as-is, VLM optional |
| E2B Runner | No | N/A | No changes needed |
| Postman MCP | No | N/A | No changes needed |
| Hostinger MCP | No | N/A | No changes needed |
| Skills Server | No | N/A | Consider TensorZero embeddings for semantic search |

---

## Enhancements Made/Recommended

### 1. Docling MCP

- **Current**: Uses custom SSE handler for MCP SDK compatibility
- **Enhancement**: VLM configuration via `DOCLING_VLM_REPO` environment variable
- **Status**: No changes required

### 2. E2B Runner

- **Current**: Standard SSE transport
- **Enhancement**: None required (deterministic execution)
- **Status**: No changes required

### 3. Postman MCP

- **Current**: Uses official `@postman/postman-mcp-server@latest`
- **Enhancement**: None required (API operations)
- **Status**: Working as documented

### 4. Hostinger MCP

- **Current**: Basic STDIO configuration
- **Enhancement**: None required
- **Status**: Catalog entry complete

### 5. Skills Server

- **Current**: Complete implementation with multi-source aggregation
- **Enhancement Opportunity**: Could integrate TensorZero embeddings for semantic skill search
- **Status**: Fully functional

---

## Directory Structure Verification

### Expected Structure

```
PMOVES-BoTZ/
├── core/
│   └── mcp/
│       └── catalog.yml          # [EXISTS] MCP server catalog
├── features/
│   ├── docling/                 # [REFERENCED] Docling implementation
│   │   └── Dockerfile.docling-mcp
│   ├── e2b/                     # [REFERENCED] E2B implementation
│   │   └── Dockerfile
│   ├── postman/                 # [NPX RUNTIME] Uses npx package
│   ├── hostinger/               # [CATALOG ONLY] Binary-based
│   └── skills/                  # [EXISTS] Full implementation
│       ├── skill_server.py
│       ├── skill_loader.py
│       ├── mcp_skill_bridge.py
│       ├── sync_skills.py
│       ├── test_skills.py
│       └── library/             # Skill library
└── .claude/
    └── skills/                  # [EXISTS] Extensive skill collection
```

### Notes

1. **Docling, E2B**: Referenced in docker-compose.yml but `features/` directories need implementation files
2. **Postman**: Uses runtime npx installation, no local implementation needed
3. **Hostinger**: Uses binary installed in container, catalog-only configuration
4. **Skills**: Fully implemented with comprehensive functionality

---

## Next Steps

1. **Verify Features Directories**: Ensure `features/docling/` and `features/e2b/` contain necessary Dockerfiles and implementations
2. **TensorZero Embeddings**: Consider adding semantic search to Skills Server using TensorZero embedding model
3. **Health Endpoints**: Ensure all agents expose consistent `/health` or `/healthz` endpoints
4. **Documentation Sync**: Keep this document updated as implementations evolve
