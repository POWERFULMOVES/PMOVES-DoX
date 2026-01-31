# PMOVES-DoX Deployment Guide

PMOVES-DoX supports **two deployment modes**:

1. **Standalone Mode** (default) - Run independently with all local services
2. **Docked Mode** - Run as submodule within PMOVES.AI, sharing parent infrastructure

---

## Quick Start

The recommended way to deploy PMOVES-DoX is via Makefile targets. These handle network setup, environment loading, and service orchestration automatically.

```bash
# Clone the repository
git clone https://github.com/POWERFULMOVES/PMOVES-DoX.git
cd PMOVES-DoX

# Bootstrap credentials from parent PMOVES.AI (if available)
make env-bootstrap

# Standalone mode (default) - all local services
make standalone

# Docked mode (within PMOVES.AI) - shares parent infrastructure
make docked
```

**Important:** Always use `make standalone` or `make docked` instead of raw `docker compose` commands. The Makefile handles:
- External network creation/verification
- Environment file loading (`.env.local`)
- Proper compose file layering for docked mode
- Service health checks

---

## Standalone Mode

Run PMOVES-DoX independently with all local services.

### Starting (Recommended)

```bash
make standalone
```

This command:
1. Creates external networks (`pmoves_api`, `pmoves_app`, `pmoves_bus`, `pmoves_data`) if they don't exist
2. Loads environment from `.env.local`
3. Starts all services with `PMOVES_MODE=standalone`

### Alternative (Manual)

If you need to run docker compose directly:

```bash
PMOVES_MODE=standalone docker compose --env-file .env.local up -d --build
```

**Note:** You must manually create networks first with `make ensure-standalone-networks`.

### Services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3001 | Next.js web UI |
| Backend API | http://localhost:8484 | FastAPI document processing |
| DoX Agent Zero | http://localhost:50051 | Document intelligence orchestrator |
| NATS WebSocket | ws://localhost:9223 | Geometry message bus |
| Neo4j | http://localhost:17474 | Knowledge graph UI |
| PostgREST | http://localhost:54321 | Supabase REST API |

### Internal BoTZ Agents

DoX Agent Zero coordinates these internal PMOVES-BoTZ agents:

| Agent | URL | Purpose |
|-------|-----|---------|
| Cipher | http://localhost:3025 | Memory operations, CHIT protocol |
| Postman | http://localhost:3026 | API testing, collection execution |
| Docling | http://localhost:3020 | Advanced PDF parsing |

### Stopping

```bash
docker compose down
# or
make clean
```

---

## Docked Mode

Run as submodule within PMOVES.AI, sharing parent services.

### Prerequisites

- PMOVES.AI repository must be checked out at `../pmoves`
- Parent PMOVES.AI services must be running
- Parent networks must exist (verified automatically)

### Verify Parent Networks

Before starting docked mode, verify parent networks are available:

```bash
make check-parent
```

This command verifies that the following parent networks exist:
- `pmoves_api` - TensorZero Gateway (:3030)
- `pmoves_bus` - Parent NATS (:4222)
- `pmoves_data` - Parent ClickHouse, Neo4j
- `pmoves_app` - Parent services

If any network is missing, you'll receive instructions to start parent PMOVES.AI first.

### Starting (Recommended)

```bash
make docked
```

This command:
1. Runs `check-parent` to verify parent networks exist
2. Loads environment from `.env.local` (which inherits from `env.shared`)
3. Starts services with both `docker-compose.yml` and `docker-compose.docked.yml`
4. Sets `PMOVES_MODE=docked`

### Alternative (Manual)

```bash
PMOVES_MODE=docked docker compose -f docker-compose.yml -f docker-compose.docked.yml --env-file .env.local up -d --build
```

**Note:** You must manually verify parent networks first with `make check-parent`.

### Services (DoX Local)

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3001 | DoX web UI |
| Backend API | http://localhost:8484 | DoX document processing |
| DoX Agent Zero | http://localhost:50051 | Document intelligence (with MCP API) |
| Neo4j | http://localhost:17474 | DoX-local knowledge graph |

### Connected Parent Services

When docked, DoX connects to these parent PMOVES.AI services:

| Parent Service | URL | Purpose |
|----------------|-----|---------|
| TensorZero Gateway | http://tensorzero-gateway:3030 | LLM orchestration |
| Parent NATS | nats://nats:4222 | Cross-service messaging |
| Parent Neo4j | bolt://pmoves-neo4j-1:7687 | Shared knowledge graph |

### Dual-Instance Agent Zero Pattern

When docked, **both Agent Zeros run**:

1. **Parent Agent Zero** (`:8080`) - General orchestration for ALL PMOVES.AI
2. **DoX Agent Zero** (`:50051`) - Document intelligence specialist
   - Exposes MCP API at `http://pmoves-agent-zero:50051/mcp/t-{token}/sse`
   - Parent can delegate document tasks to DoX Agent Zero

### Stopping

```bash
docker compose -f docker-compose.yml -f docker-compose.docked.yml down
```

---

## Environment Variables

### Environment File Inheritance

PMOVES-DoX uses a tiered environment configuration system that inherits from parent PMOVES.AI:

```
env.shared (parent PMOVES.AI)     # Base configuration for all PMOVES services
    └── env.tier-agent            # Tier-specific overrides (agent tier)
        └── .env.local            # Local/deployment-specific values
```

**env.shared** (`env.shared` in repo root):
- Contains common configuration for all PMOVES.AI tiers
- Defines service discovery URLs (NATS, TensorZero, Qdrant, Neo4j)
- Sets default timeouts, health check intervals, logging configuration
- Should NOT be modified directly - inherits from parent PMOVES.AI

**Key variables inherited from env.shared:**
| Variable | Default | Description |
|----------|---------|-------------|
| `NATS_URL` | `nats://nats:4222` | Parent NATS message bus |
| `TENSORZERO_URL` | `http://tensorzero-gateway:3030` | LLM gateway |
| `NEO4J_URL` | `http://neo4j:7474` | Knowledge graph |
| `QDRANT_URL` | `http://qdrant:6333` | Vector database |
| `AGENT_ZERO_URL` | `http://agent-zero:8080` | Parent Agent Zero |

**Bootstrap credentials from parent:**
```bash
# Windows
.\scripts\bootstrap_env.ps1

# Linux/Mac
./scripts/bootstrap_env.sh

# Or via Makefile
make env-bootstrap
```

This copies API keys (OpenRouter, Google, Anthropic, etc.) from parent PMOVES.AI `.env` files.

### Mode Selection

| Variable | Default | Description |
|----------|---------|-------------|
| `PMOVES_MODE` | `standalone` | Deployment mode (`standalone` or `docked`) |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_BACKEND` | `sqlite` | Database backend (`sqlite` or `supabase`) |
| `SUPABASE_DUAL_WRITE` | `false` | Write to both databases |
| `SUPABASE_URL` | `http://supabase-rest:3000` | Supabase REST API URL |
| `SUPABASE_ANON_KEY` | `local-dev-anon-key-for-postgrest` | Supabase anon key |
| `SUPABASE_SERVICE_KEY` | `local-dev-service-key-for-postgrest` | Supabase service key |

### Neo4j Knowledge Graph

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_LOCAL_PASSWORD` | `pmovesNeo4j!Local2025` | Local Neo4j password |
| `NEO4J_PARENT_PASSWORD` | `pmovesNeo4j!Local2025` | Parent Neo4j password (docked mode) |

### Agent Zero MCP

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_ZERO_MCP_ENABLED` | `false` | Enable MCP server (auto-enabled in docked mode) |
| `AGENT_ZERO_MCP_TOKEN` | - | MCP authentication token (required when docked) |

### TensorZero

| Variable | Default | Description |
|----------|---------|-------------|
| `TENSORZERO_BASE_URL` | `http://tensorzero-gateway:3000` | TensorZero Gateway URL |
| `TENSORZERO_EMBEDDING_MODEL` | `qwen3_embedding_8b_local` | Embedding model for search |

---

## GitHub Secrets (Production)

For production deployments, configure these GitHub repository secrets:

| Secret | Description |
|--------|-------------|
| `SUPABASE_ANON_KEY` | Production Supabase anon key |
| `SUPABASE_SERVICE_KEY` | Production Supabase service key |
| `NEO4J_PASSWORD` | Neo4j database password |
| `AGENT_ZERO_MCP_TOKEN` | MCP authentication token (generate with `openssl rand -hex 32`) |

### Setting Secrets via GitHub CLI

```bash
# Set Supabase keys
gh secret set SUPABASE_ANON_KEY --body "your-production-anon-key"
gh secret set SUPABASE_SERVICE_KEY --body "your-production-service-key"

# Set Neo4j password
gh secret set NEO4J_PASSWORD --body "your-secure-password"

# Generate and set MCP token
openssl rand -hex 32 | gh secret set AGENT_ZERO_MCP_TOKEN
```

---

## Networking

### Standalone Networks

| Network | Purpose | Subnet |
|---------|---------|--------|
| `pmoves_api` | API tier | 172.30.1.0/24 |
| `pmoves_app` | Internal apps | 172.30.2.0/24 |
| `pmoves_bus` | NATS messaging | 172.30.3.0/24 |
| `pmoves_dox_data` | Local databases | 172.31.4.0/24 |

### Docked Networks

DoX connects to parent networks when docked:

| Network | Purpose |
|---------|---------|
| `pmoves_api` | Parent API tier |
| `pmoves_app` | Parent application tier |
| `pmoves_bus` | Parent NATS message bus |
| `pmoves_data` | Parent data services |

---

## Testing

### Standalone Tests

```bash
make test-standalone
```

This validates:
- Backend health endpoint
- Frontend accessibility
- DoX Agent Zero health
- Geometry bus connectivity

### Docked Tests

```bash
make test-docked
```

This validates:
- Backend health endpoint
- DoX Agent Zero health
- Parent TensorZero Gateway connectivity
- Parent NATS connectivity

### Manual Tests

```bash
# Health checks
curl http://localhost:8484/health       # Backend
curl http://localhost:50051/health       # DoX Agent Zero
curl http://localhost:3001               # Frontend

# Geometry bus test
curl http://localhost:8484/api/v1/cipher/geometry/demo-packet | jq '.'

# MCP endpoint (docked mode only)
curl http://localhost:50051/mcp/t-{token}/sse
```

---

## Troubleshooting

### Port Conflicts

If you encounter port conflicts:

1. Check what's using the port:
   ```bash
   lsof -i :8484  # Backend
   lsof -i :3001  # Frontend
   lsof -i :50051 # DoX Agent Zero
   ```

2. Or use `make ps` to see running containers

### Service Won't Start

1. Check logs:
   ```bash
   make logs              # All services
   make backend-logs      # Backend only
   make agent-zero-logs   # DoX Agent Zero only
   ```

2. Verify environment:
   ```bash
   docker exec pmoves-dox-backend env | grep -E "PMOVES_MODE|TENSORZERO|NATS_URL"
   ```

### Geometry Bus Not Working

1. Verify NATS is running:
   ```bash
   docker exec pmoves-dox-nats nats server check
   ```

2. Check NATS configuration:
   ```bash
   docker exec pmoves-dox-backend env | grep NATS_URL
   ```

3. Test geometry endpoint:
   ```bash
   curl http://localhost:8484/api/v1/cipher/geometry/demo-packet
   ```

### Parent Services Unreachable (Docked Mode)

1. Verify parent networks exist:
   ```bash
   docker network ls | grep pmoves
   ```

2. Check connectivity:
   ```bash
   docker exec pmoves-dox-backend ping -c 2 tensorzero-gateway
   docker exec pmoves-dox-backend ping -c 2 nats
   ```

---

## Makefile Reference

```bash
# Mode selection
make standalone              # Start in standalone mode
make docked                  # Start in docked mode

# Testing
make test-standalone         # Test standalone deployment
make test-docked             # Test docked deployment

# Utilities
make build                   # Build all Docker images
make pull                    # Pull latest images
make clean                   # Stop and remove containers
make logs                    # Show all logs
make ps                      # Show running containers
make restart                 # Restart all services

# Service-specific logs
make backend-logs            # Backend service logs
make frontend-logs           # Frontend service logs
make agent-zero-logs         # DoX Agent Zero logs
make nats-logs               # NATS logs
make neo4j-logs              # Neo4j logs

# Geometry / CHIT
make geometry-test           # Test geometry bus
```

---

## Security

### Secret Management

- Never commit secrets to the repository
- Use GitHub Secrets for production values
- Development defaults are in `.env.local`

### Security Workflows

PMOVES-DoX includes GitHub Actions security workflows:

1. **env-preflight.yml** - Validates environment configuration, detects hardcoded secrets
2. **security-scan.yml** - Trivy container scans, CodeQL analysis, secret scanning

These run automatically on:
- Pull requests
- Pushes to `main` and `PMOVES.AI-Edition-Hardened` branches
- Weekly schedule (Mondays at 00:00 UTC)

### Branch Protection

Configure in repository Settings > Branches:

1. **Branch name**: `main`, `PMOVES.AI-Edition-Hardened`
2. **Require pull request reviews**: 2 approvals
3. **Require status checks**:
   - `env-preflight`
   - `security-scan`
4. **Require branches to be up to date**
5. **Require linear history**

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STANDALONE MODE                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Backend    │  │  DoX Agent   │  │    NATS      │  │    Neo4j     │    │
│  │   :8484      │  │   Zero :50051│  │   :4223      │  │  :17474/:7687│    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                 │                 │                 │            │
│         └─────────────────┼─────────────────┼─────────────────┘            │
│                           │                 │                              │
│                    ┌──────▼─────────┬──────▼──────┐                       │
│                    │    Frontend    │  Internal   │                       │
│                    │     :3001      │   BoTZ AGTs │                       │
│                    └─────────────────┴─────────────┘                       │
│                     Cipher, Postman, Docling                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              DOCKED MODE (within PMOVES.AI)                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        PMOVES.AI (Parent)                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
│  │  │TensorZero GW │  │   Parent     │  │  Parent      │             │   │
│  │  │   :3030      │  │   NATS :4222 │  │  Neo4j :7687 │             │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │   │
│  │         └─────────────────┼─────────────────┘                    │   │
│  │                          │                                      │   │
│  │                   pmoves_data network                            │   │
│  └──────────────────────────┼──────────────────────────────────────┘   │
│                             │                                           │
│          ┌──────────────────┼────────────────┐                          │
│          │                 │                │                          │
│    ┌─────▼─────┐   ┌──────▼──────┐   ┌───▼────┐                      │
│    │   DoX     │   │   Archon    │   │ Hi-RAG  │                      │
│    │  Backend  │   │   :8091     │   │ :8086  │                      │
│    │  :8484    │   └─────────────┘   └────────┘                      │
│    └───────────┘                                                      │
│         │                                                              │
│         ▼                                                              │
│    ┌────────────────────────────────────────────────────────────┐     │
│    │           PMOVES-DoX + PMOVES-BoTZ Internal Agents         │     │
│    │                                                             │     │
│    │    ┌───────────────────────────────────────────────┐       │     │
│    │    │        DoX Agent Zero (:50051)                │       │     │
│    │    │        - pmoves_custom profile               │       │     │
│    │    │        - Exposes MCP API for parent          │       │     │
│    │    └───────────────────┬───────────────────────────┘       │     │
│    │                        │                                   │     │
│    │    ┌───────────────────┼───────────────────────────┐       │     │
│    │    │                   ▼                           │       │     │
│    │    │    ┌────────────────────────────────────┐       │       │     │
│    │    │    │      Internal BoTZ MCP Agents      │       │       │     │
│    │    │    ├─────────────┬──────────────┬─────────┤       │       │     │
│    │    │    │ Cipher      │ Postman      │ Docling │       │       │     │
│    │    │    │ :3025       │ :3026        │ :3020   │       │       │     │
│    │    │    └─────────────┴──────────────┴─────────┘       │       │     │
│    │    └─────────────────────────────────────────────────────┘       │     │
│    └─────────────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Additional Documentation

- [CLAUDE.md](../CLAUDE.md) - Developer guide and architecture
- [ARCHITECTURE.md](ARCHITECTURE.md) - Technical architecture details
- [API_REFERENCE.md](API_REFERENCE.md) - Complete REST API reference
- [USER_GUIDE.md](USER_GUIDE.md) - End user documentation
- [DOCKING_GUIDE.md](DOCKING_GUIDE.md) - Integration with parent PMOVES.AI
