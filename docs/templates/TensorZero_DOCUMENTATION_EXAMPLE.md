# TensorZero Gateway Service Documentation

**Version:** 2025.11.6
**Last Updated:** 2026-02-10
**Status:** stable

---

## 1. Service Overview

### 1.1 Purpose

TensorZero Gateway is PMOVES.AI's centralized LLM gateway providing unified access to multiple model providers (OpenAI, Anthropic, Venice, Ollama) with comprehensive observability via ClickHouse metrics collection.

### 1.2 Key Features

- Multi-provider routing (OpenAI, Anthropic, Venice, Ollama)
- Request/response logging with token tracking
- Latency metrics and error rate monitoring
- OpenAI-compatible API (`/v1/chat/completions`, `/v1/embeddings`)
- Configuration-driven model selection and fallback
- ClickHouse-backed observability

### 1.3 Dependencies

| Dependency | Type | Required | Purpose |
|-------------|------|----------|---------|
| tensorzero-clickhouse | Database | Yes | Stores metrics, logs, token usage |
| pmoves-ollama | Service | Conditional | Local model inference |
| Prometheus | Monitoring | Optional | Metrics scraping |

### 1.4 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Runtime | Rust | - |
| Container | tensorzero/gateway | latest |
| Config | TOML | - |
| Database | ClickHouse | 24.12-alpine |

---

## 2. Network Configuration

### 2.1 Ports

| Port Type | Port Number | Protocol | Description |
|-----------|-------------|----------|-------------|
| Internal | 3000 | HTTP | Gateway API (within container) |
| External | 3030 | HTTP | Gateway API (host access) |
| Metrics | 3000 | HTTP | Prometheus metrics endpoint |

### 2.2 Network Membership

```yaml
networks:
  - app_tier    # Service-to-service communication
  - api_tier    # External API access
  - data_tier   # ClickHouse database access
```

### 2.3 DNS Names for Service Discovery

| DNS Name | Resolves To | Used By |
|----------|-------------|---------|
| `tensorzero-gateway` | tensorzero-gateway container | All PMOVES services for LLM calls |
| `tensorzero-clickhouse` | clickhouse container | TensorZero gateway for metrics |

### 2.4 Connection Diagram

```
                              ┌──────────────────────────┐
                              │   PMOVES Services        │
                              │  (Agent Zero, Archon)    │
                              └─────────────┬────────────┘
                                            │
                              ┌─────────────▼────────────┐
                              │  TensorZero Gateway      │
                              │  (Port 3030)             │
                              └─────────────┬────────────┘
                                            │
          ┌─────────────────────────────────┼─────────────────────────────────┐
          │                                 │                                 │
  ┌───────▼────────┐              ┌─────────▼──────┐              ┌─────────▼──────┐
  │   OpenAI       │              │    Anthropic   │              │   Ollama       │
  │   (cloud)      │              │    (cloud)     │              │   (local)      │
  └────────────────┘              └────────────────┘              └────────────────┘
          │                                 │                                 │
          └─────────────────────────────────┼─────────────────────────────────┘
                                            │
                              ┌─────────────▼────────────┐
                              │  TensorZero ClickHouse   │
                              │  (Port 8123)             │
                              └──────────────────────────┘
```

---

## 3. Environment Variables

### 3.1 Required Variables

| Variable | Description | Example | Source |
|----------|-------------|---------|--------|
| `TENSORZERO_CLICKHOUSE_URL` | ClickHouse connection URL with auth | `http://user:pass@host:8123/db` | env.shared |
| `OPENAI_API_KEY` | OpenAI API key for GPT models | `sk-...` | .env.local |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models | `sk-ant-...` | .env.local |

### 3.2 Optional Variables with Defaults

| Variable | Default | Description |
|----------|---------|-------------|
| `TENSORZERO_API_KEY` | (empty) | Optional API key for gateway authentication |
| `GATEWAY_CONFIG_PATH` | `/app/config/tensorzero.toml` | Path to configuration file |

### 3.3 Secret/Credential Sources

| Secret | Description | How to Provision |
|--------|-------------|------------------|
| `OPENAI_API_KEY` | OpenAI access | Set in `.env.local` or Docker secret |
| `ANTHROPIC_API_KEY` | Anthropic access | Set in `.env.local` or Docker secret |
| `VENICE_API_KEY` | Venice.ai access | Set in `.env.local` or Docker secret |
| `TENSORZERO_CLICKHOUSE_PASSWORD` | ClickHouse auth | Set in `env.shared` |

### 3.4 Environment Precedence

1. Docker secrets (`/run/secrets/`)
2. Environment variables in docker-compose
3. `env.shared` file
4. `.env.local` file

---

## 4. Health & Monitoring

### 4.1 Health Check Endpoints

#### Liveness Probe

```http
GET /health
```

**Response (Healthy):**
```json
{
  "status": "ok"
}
```

**Response (Unhealthy):**
```json
{
  "status": "error",
  "message": "ClickHouse connection failed"
}
```

#### Readiness Probe

```http
GET /health
```

**Checks:**
- ClickHouse connection is established
- Configuration file is valid
- At least one model provider is configured

### 4.2 Metrics Endpoints (Prometheus)

```http
GET /metrics
```

**Key Metrics:**

| Metric Name | Type | Description |
|-------------|------|-------------|
| `tensorzero_request_duration_seconds` | histogram | Request latency by model |
| `tensorzero_request_count` | counter | Total requests by model |
| `tensorzero_token_usage` | counter | Token usage by model |
| `tensorzero_error_count` | counter | Error count by type |

**Example Queries:**

```promql
# P95 latency by model
histogram_quantile(0.95, rate(tensorzero_request_duration_seconds_bucket[5m]))

# Request rate by model
rate(tensorzero_request_count[5m])

# Error rate
rate(tensorzero_error_count[5m]) / rate(tensorzero_request_count[5m])
```

### 4.3 Log Location and Format

**Log Driver:** JSON (Docker logs)

**Log Levels:**
- `INFO` - Normal operations, request logs
- `WARN` - Configuration warnings, retries
- `ERROR` - Failed requests, provider errors

**Log Labels (for Loki aggregation):**
| Label | Value |
|-------|-------|
| `service` | `tensorzero-gateway` |
| `tier` | `app` |
| `environment` | `production` |

### 4.4 Critical Alerts

**Grafana Alerts:**

| Alert Name | Condition | Severity | Action |
|------------|-----------|----------|--------|
| TensorZeroDown | `up{job="tensorzero"} == 0` | critical | Check container, restart if needed |
| HighErrorRate | `rate(error_count[5m]) > 0.05` | warning | Check provider status |
| HighLatency | `histogram_quantile(0.95, latency) > 30s` | warning | Check ClickHouse, provider load |

**Critical Conditions to Monitor:**
- Gateway not responding to `/health`
- ClickHouse connection lost
- All providers returning errors
- P95 latency exceeding 30 seconds

---

## 5. Deployment

### 5.1 Docker Image Reference

```bash
# Pull latest
docker pull tensorzero/gateway:latest

# Specific version
docker pull tensorzero/gateway:2025.11.6
```

### 5.2 Resource Requirements

| Resource | Minimum | Recommended | Maximum |
|----------|---------|-------------|---------|
| CPU | 0.5 cores | 1 core | 4 cores |
| Memory | 256 MB | 512 MB | 2 GB |
| GPU | N/A | N/A | N/A |
| Storage | 100 MB (config only) | 100 MB | 100 MB |

### 5.3 Startup Dependencies

```yaml
depends_on:
  tensorzero-clickhouse:
    condition: service_healthy
```

**Startup Order:**
1. tensorzero-clickhouse (must be healthy)
2. tensorzero-gateway
3. tensorzero-ui

### 5.4 Docker Compose Profile

```bash
# Start with profile
docker compose --profile tensorzero up -d

# Stop
docker compose --profile tensorzero down
```

### 5.5 Scaling Considerations

**Horizontal Scaling:**
- Can scale: Yes (stateless)
- Max instances: No hard limit
- Shared state: ClickHouse (all instances write to same DB)
- Load balancer: Recommended for production

**Vertical Scaling:**
- CPU-bound: Yes (request processing)
- Memory-bound: No (minimal memory usage)
- GPU-bound: No

### 5.6 Deployment Commands

```bash
# Local development
cd pmoves && make up-tensorzero

# Production deployment
docker compose --profile tensorzero up -d

# Verify health
curl http://localhost:3030/health
curl http://localhost:8123/ping  # ClickHouse
```

---

## 6. API Reference

### 6.1 Public APIs

#### Chat Completions (OpenAI-compatible)

```http
POST /v1/chat/completions
```

**Description:** Generate chat completions via configured model providers

**Request:**
```json
{
  "model": "claude-sonnet-4-5",
  "messages": [
    {"role": "user", "content": "Hello, TensorZero!"}
  ],
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**Response (200 OK):**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "claude-sonnet-4-5",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "Hello! How can I help you today?"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21
  }
}
```

**Error Responses:**
| Code | Description | Retry |
|------|-------------|-------|
| 400 | Invalid request | No |
| 401 | Authentication failed | No |
| 429 | Rate limited | Yes |
| 500 | Provider error | Yes |
| 503 | Service unavailable | Yes |

#### Embeddings (OpenAI-compatible)

```http
POST /v1/embeddings
```

**Description:** Generate embeddings via configured embedding model

**Request:**
```json
{
  "model": "gemma_embed_local",
  "input": "Text to embed"
}
```

**Response (200 OK):**
```json
{
  "object": "list",
  "data": [{
    "object": "embedding",
    "embedding": [0.0023, -0.0052, ...],
    "index": 0
  }],
  "model": "gemma_embed_local",
  "usage": {
    "prompt_tokens": 4,
    "total_tokens": 4
  }
}
```

### 6.2 Internal APIs

| Endpoint | Method | Used By |
|----------|--------|---------|
| `/health` | GET | Health checks, orchestrators |
| `/metrics` | GET | Prometheus scraping |

### 6.3 Webhooks

None - TensorZero does not send webhooks.

---

## 7. NATS Integration

TensorZero does not use NATS directly. Services that call TensorZero may publish events to NATS about LLM usage.

---

## 8. Data Storage

### 8.1 Database Schema

**ClickHouse Tables:**

| Table | Purpose | Indexes |
|-------|---------|---------|
| `requests` | All LLM requests/responses | `timestamp`, `model` |
| `inference_params` | Request parameters | `request_id` |
| `feedback` | User feedback on responses | `request_id` |

### 8.2 Volume Mounts

| Volume | Mount Path | Purpose |
|--------|------------|---------|
| `tensorzero-clickhouse-data` | `/var/lib/clickhouse` | ClickHouse data persistence |
| `./tensorzero/config` | `/app/config` | Configuration file (read-only) |

### 8.3 Backup Strategy

**What to Backup:**
- ClickHouse data volume
- `tensorzero.toml` configuration file

**Backup Commands:**
```bash
# ClickHouse backup
docker exec tensorzero-clickhouse clickhouse-client \
  --user tensorzero --password tensorzero \
  --query "BACKUP DATABASE default TO Disk('backups', 'tensorzero_backup.zip')"
```

**Restore Commands:**
```bash
# ClickHouse restore
docker exec tensorzero-clickhouse clickhouse-client \
  --user tensorzero --password tensorzero \
  --query "RESTORE DATABASE default FROM Disk('backups', 'tensorzero_backup.zip')"
```

---

## 9. Security

### 9.1 Authentication

**Method:** Optional API key via `Authorization` header

**How to Configure:**
```bash
# Set optional gateway API key
TENSORZERO_API_KEY=your-secret-key
```

### 9.2 Authorization

No built-in authorization - relies on network isolation (private networks).

### 9.3 Network Security

- **Internal Only:** No (exposed on `pmoves_api` network)
- **TLS Required:** No (internal network)
- **Allowed IPs:** All within PMOVES networks

---

## 10. Troubleshooting

### 10.1 Common Issues and Resolutions

#### Issue: Gateway returns 500 errors

**Symptoms:**
- All requests failing with 500
- Logs show "ClickHouse connection error"

**Diagnosis:**
```bash
# Check ClickHouse health
curl http://localhost:8123/ping

# Check gateway logs
docker compose logs tensorzero-gateway | grep -i clickhouse
```

**Resolution:**
1. Verify ClickHouse is running: `docker compose ps tensorzero-clickhouse`
2. Check credentials in `TENSORZERO_CLICKHOUSE_URL`
3. Restart ClickHouse if needed

#### Issue: Observability not recording

**Symptoms:**
- Requests succeed but no data in UI
- ClickHouse tables empty

**Diagnosis:**
```bash
# Check ClickHouse tables
docker exec -it tensorzero-clickhouse clickhouse-client \
  --user tensorzero --password tensorzero \
  --query "SHOW TABLES"
```

**Resolution:**
1. Enable observability in `tensorzero.toml`: `observability.enabled = true`
2. Verify ClickHouse URL is correct
3. Restart gateway

### 10.2 Log Patterns to Watch

**Healthy Logs:**
```
observability exporter configured
successfully connected to ClickHouse
request processed: model=claude-sonnet-4-5, latency_ms=1234
```

**Warning Patterns:**
```
retrying request to provider
high latency detected
```

**Error Patterns:**
```
failed to connect to ClickHouse
provider returned error
invalid model configuration
```

### 10.3 Recovery Procedures

**Service Restart:**
```bash
# Graceful restart
docker compose restart tensorzero-gateway

# Hard reset
docker compose up -d --force-recreate tensorzero-gateway
```

**Data Recovery:**
```bash
# Restore from ClickHouse backup
docker exec tensorzero-clickhouse clickhouse-client \
  --user tensorzero --password tensorzero \
  --query "RESTORE DATABASE default FROM Disk('backups', 'backup.zip')"
```

### 10.4 Escalation Path

1. **First:** Check logs `docker compose logs tensorzero-gateway`
2. **Second:** Check ClickHouse health `curl http://localhost:8123/ping`
3. **Third:** Check configuration `cat tensorzero/config/tensorzero.toml`
4. **Finally:** Escalate to infrastructure team

---

## 11. Development

### 11.1 Local Development

```bash
# Start TensorZero stack
cd pmoves
make up-tensorzero

# View logs
docker compose logs -f tensorzero-gateway

# Test API
curl -X POST http://localhost:3030/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma:2b", "messages": [{"role": "user", "content": "Hi"}]}'
```

### 11.2 Testing

| Test Type | Command | Coverage Target |
|-----------|---------|-----------------|
| Health Check | `curl http://localhost:3030/health` | 100% |
| API Smoke | `make test-tensorzero` | Core endpoints |
| Integration | `pytest tests/integration/test_tensorzero.py` | 80% |

### 11.3 Code Quality

TensorZero is a third-party service. For PMOVES integration:
- **Config Validation:** `tensorzero-validator` tool
- **Model Testing:** Use `make test-llm` target

---

## 12. Changelog

### Version 2025.11.6 (2026-02-10)

**Added:**
- Support for new OpenAI models
- Enhanced ClickHouse observability

**Changed:**
- Updated ClickHouse connection URL format
- New configuration structure for observability

**Fixed:**
- Memory leak in long-running connections

---

## 13. References

- **Source Code:** https://github.com/tensorzero/tensorzero
- **Related Docs:** `.claude/context/tensorzero.md`
- **External APIs:** https://docs.tensorzero.com
- **Design Documents:** `pmoves/docs/services/tensorzero/`

---

## Appendix A: Quick Reference

```bash
# Health check
curl http://localhost:3030/health

# View logs
docker compose logs -f tensorzero-gateway

# Restart service
docker compose restart tensorzero-gateway

# Connect to container
docker exec -it tensorzero-gateway sh

# View metrics
curl http://localhost:3030/metrics

# Test chat completion
curl -X POST http://localhost:3030/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma:2b", "messages": [{"role": "user", "content": "Hello"}]}'

# Query ClickHouse
docker exec -it tensorzero-clickhouse clickhouse-client \
  --user tensorzero --password tensorzero

# Access UI
open http://localhost:4000
```

---

## Appendix B: Configuration Example

```toml
# tensorzero.toml
[gateway]
observability.enabled = true

# Providers
[providers.openai]
api_key = "env::OPENAI_API_KEY"

[providers.anthropic]
api_key = "env::ANTHROPIC_API_KEY"

[providers.ollama]
base_url = "http://pmoves-ollama:11434"

# Models
[models.gemma_chat]
provider = "ollama"
model = "gemma:2b"
type = "chat"

[models.claude_sonnet]
provider = "anthropic"
model = "claude-sonnet-4-5"
type = "chat"

[models.gemma_embed]
provider = "ollama"
model = "gemma:2b"
type = "embedding"
```
