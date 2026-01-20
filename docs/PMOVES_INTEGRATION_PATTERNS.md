# PMOVES.AI Integration Patterns

Learnings and patterns for integrating services with the PMOVES.AI platform.

## Health Check Pattern

### Standard Implementation

```python
from pmoves_health import health_check_router, add_database_check, add_nats_check

# Include the router
app.include_router(health_check_router)

# Register checks in startup (not per-request)
@app.on_event("startup")
async def startup():
    add_database_check(lambda: db.ping())
    add_nats_check(os.getenv("NATS_URL", "nats://nats:4222"))
```

### Key Rules

1. **Always use `/healthz`** - Not `/health`. PMOVES.AI convention.
2. **Register checks once at startup** - Never in request handlers to avoid duplicates.
3. **Use lambda for database checks** - Avoids early initialization issues.
4. **Separate required vs optional** - Required checks affect healthy/unhealthy status.

### Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Duplicate health check registration | Move registration to decorator closure or startup handler |
| NATS.connect as classmethod | Instantiate first: `nc = NATS(); await nc.connect()` |
| Missing `/healthz` suffix | Always append `/healthz` to health check URLs |
| Hardcoded ports in healthcheck | Use `${SERVICE_PORT:-8080}` variable |

---

## Service Announcement Pattern

### Standard Implementation

```python
from pmoves_announcer import announce_service

@app.on_event("startup")
async def startup():
    try:
        await announce_service(
            slug="my-service",
            name="My Service Display Name",
            url=os.getenv("SERVICE_URL", "http://my-service:8080"),
            port=int(os.getenv("SERVICE_PORT", "8080")),
            tier="api",  # data, api, llm, media, agent, worker, app, ui
            metadata={
                "version": "1.0.0",
                "features": ["feature1", "feature2"],
            }
        )
    except Exception as e:
        # Log but don't fail startup
        logger.warning(f"Failed to announce service: {e}")
```

### Key Rules

1. **Non-blocking** - Service should start even if NATS unavailable.
2. **Include metadata** - Version, features help with discovery.
3. **Use correct tier** - Affects routing and resource allocation.

### Service Tiers

| Tier | Description | Example Services |
|------|-------------|------------------|
| `data` | Data storage services | Qdrant, Neo4j, Meilisearch |
| `api` | API services | DoX, HiRAG |
| `llm` | LLM gateways | TensorZero |
| `media` | Media processing | Transcription, OCR |
| `agent` | AI agents | Agent Zero, Archon |
| `worker` | Background workers | Task processors |
| `app` | Full applications | Web apps |
| `ui` | Frontend UIs | TensorZero UI |

---

## Service Registry Pattern

### Standard Implementation

```python
from pmoves_registry import get_service_url, get_service_info

# Simple URL resolution
url = await get_service_url("hirag-v2", default_port=8086)

# Full service info
info = await get_service_info("agent-zero", default_port=8080)
print(f"Health: {info.health_check_url}")
```

### Resolution Chain

1. **Environment variables** (highest priority)
   - `HIRAG_V2_URL`, `HIRAGV2_URL`, `HIRAG-V2_URL`
   - `HIRAG_V2_HEALTH_URL` (dedicated health endpoint)

2. **Docker DNS fallback** (development)
   - `http://{slug}:{default_port}`

### Key Rules

1. **Always append `/healthz`** - Health URLs must have proper endpoint.
2. **Support multiple env patterns** - `SLUG_URL`, `SLUG-URL`, `SLUGURL`.
3. **Graceful fallback** - DNS resolution for development environments.

---

## Environment File Pattern

### Dual Format Approach

Maintain two versions for different use cases:

| File | Format | Use Case |
|------|--------|----------|
| `env.tier-agent` | dotenv | Docker Compose `env_file` |
| `env.tier-agent.sh` | shell | Manual sourcing with `source` |

### Dotenv Format (Docker Compose)

```bash
# env.tier-agent
TIER=agent
MAX_CONCURRENT_AGENTS=50
MCP_ENABLED=true
```

### Shell Format (Manual)

```bash
#!/usr/bin/env bash
# env.tier-agent.sh
export TIER=agent
export MAX_CONCURRENT_AGENTS=${MAX_CONCURRENT_AGENTS:-50}
export MCP_ENABLED=${MCP_ENABLED:-true}
```

### Key Rules

1. **Add shebang to shell files** - `#!/usr/bin/env bash`
2. **No exports in dotenv** - Docker Compose doesn't support `export` keyword.
3. **Keep in sync** - Both files should have same variables.

---

## Docker Compose Pattern

### Using YAML Anchors

```yaml
services:
  my-service:
    <<: [*env-tier-agent, *pmoves-healthcheck, *pmoves-labels]
    image: my-service:latest
    environment:
      - SERVICE_NAME=my-service
      - SERVICE_PORT=8080
```

### Available Anchors

| Anchor | Purpose |
|--------|---------|
| `*env-tier-api` | API tier environment |
| `*env-tier-agent` | Agent tier environment |
| `*env-tier-worker` | Worker tier environment |
| `*env-tier-data` | Data tier environment |
| `*env-tier-llm` | LLM tier environment |
| `*env-tier-media` | Media tier environment |
| `*env-tier-ui` | UI tier environment |
| `*pmoves-healthcheck` | Standard healthcheck config |
| `*pmoves-gpu-resource` | NVIDIA GPU allocation |
| `*pmoves-labels` | Prometheus scraping labels |

### Dynamic Port in Healthcheck

```yaml
x-pmoves-healthcheck: &pmoves-healthcheck
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:$${SERVICE_PORT:-8080}/healthz || exit 1"]
```

Note: Use `$$` to escape `$` in Docker Compose.

---

## CHIT Secrets Pattern

### Manifest Structure

```yaml
api_version: "2.0"
environment: ${CHIT_ENVIRONMENT:-production}

sources:
  - type: env
    precedence: 50
  - type: chit_vault
    precedence: 100

variables:
  - SERVICE_NAME
  - SERVICE_SLUG
  - LOG_LEVEL
  - NATS_URL

groups:
  development:
    required: [SERVICE_NAME, NATS_URL]
    optional: [LOG_LEVEL]
  production:
    required: [SERVICE_NAME, SERVICE_SLUG, NATS_URL]
    optional: [LOG_LEVEL]
```

### Key Rules

1. **List all referenced variables** - Variables in groups must be in top-level list.
2. **Higher precedence overrides** - CHIT Vault (100) overrides env vars (50).
3. **Separate required/optional** - Fail on missing required, warn on optional.

---

## Integration Checklist

### Pre-Integration

- [ ] Identify service tier
- [ ] List required dependencies (NATS, Supabase, etc.)
- [ ] Review existing patterns in codebase

### Environment Setup

- [ ] Create `env.tier-{tier}` (dotenv format)
- [ ] Create `env.tier-{tier}.sh` (shell format)
- [ ] Update `chit/secrets_manifest_v2.yaml`

### Health Checks

- [ ] Add `/healthz` endpoint
- [ ] Register database check
- [ ] Register NATS check
- [ ] Register HTTP checks for dependencies

### Service Discovery

- [ ] Add service announcement on startup
- [ ] Use registry for dependent services
- [ ] Set SERVICE_NAME and SERVICE_SLUG

### Docker Compose

- [ ] Apply tier anchor
- [ ] Apply healthcheck anchor
- [ ] Set SERVICE_PORT environment variable

### Testing

- [ ] Health endpoint returns 200
- [ ] NATS announcement published
- [ ] Service discoverable via registry
- [ ] All dependency checks pass

---

## Common Issues & Solutions

### Issue: Health checks duplicating on each request

**Cause:** Registration inside wrapper function instead of decorator closure.

**Solution:**
```python
def health_check(checks=None):
    def decorator(func):
        # Register ONCE here, not in wrapper
        if checks:
            for check in list(checks):  # Defensive copy
                _health_checker.add_check(check)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Issue: NATS connection failing silently

**Cause:** Using `NATS.connect()` as classmethod.

**Solution:**
```python
nc = NATS()  # Create instance first
await nc.connect(url, connect_timeout=2)
await nc.close()
```

### Issue: Docstring shows wrong import path

**Cause:** Copy-paste from template without updating module name.

**Solution:** Always update usage examples:
```python
# Wrong: from service_announcer import ...
# Right: from pmoves_announcer import ...
```

### Issue: Docker Compose healthcheck fails on dynamic port

**Cause:** Hardcoded port in healthcheck test.

**Solution:** Use CMD-SHELL with environment variable:
```yaml
test: ["CMD-SHELL", "curl -f http://localhost:$${SERVICE_PORT:-8080}/healthz || exit 1"]
```
