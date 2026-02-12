# {SERVICE_NAME} Service Documentation

**Version:** {VERSION}
**Last Updated:** {DATE}
**Status:** {STATUS: alpha/beta/stable/deprecated}

---

## 1. Service Overview

### 1.1 Purpose

{Brief description of what the service does and its role in PMOVES.AI}

### 1.2 Key Features

- {Feature 1}
- {Feature 2}
- {Feature 3}

### 1.3 Dependencies

| Dependency | Type | Required | Purpose |
|-------------|------|----------|---------|
| {service-name} | Service | Yes/No | {Why it's needed} |
| {database-name} | Database | Yes/No | {What it stores} |
| {external-api} | External | Yes/No | {What it provides} |

### 1.4 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Runtime | {Python/Node/Go/etc} | {version} |
| Framework | {FastAPI/Express/etc} | {version} |
| Data Store | {PostgreSQL/Redis/etc} | {version} |
| Container | Docker | {base image} |

---

## 2. Network Configuration

### 2.1 Ports

| Port Type | Port Number | Protocol | Description |
|-----------|-------------|----------|-------------|
| Internal | {internal_port} | HTTP | {用途} |
| External | {external_port} | HTTP | {用途} |
| Metrics | {metrics_port} | HTTP | Prometheus metrics |

### 2.2 Network Membership

```yaml
networks:
  - {network_name_1}  # {purpose}
  - {network_name_2}  # {purpose}
```

### 2.3 DNS Names for Service Discovery

| DNS Name | Resolves To | Used By |
|----------|-------------|---------|
| {service-dns} | {container-name} | {services that use this} |

### 2.4 Connection Diagram

```
┌─────────────────┐     ┌─────────────────┐
│   Calling       │────▶│   This Service  │
│   Service       │     │   ({SERVICE_NAME})   │
└─────────────────┘     └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
            ┌───────▼────┐ ┌────▼─────┐ ┌──▼────────┐
            │ Dependency1│ │Depend. 2 │ │Dependency3│
            └────────────┘ └──────────┘ └───────────┘
```

---

## 3. Environment Variables

### 3.1 Required Variables

| Variable | Description | Example | Source |
|----------|-------------|---------|--------|
| `{VAR_NAME}` | {What it does} | `{example-value}` | {env.shared/.env.local} |

### 3.2 Optional Variables with Defaults

| Variable | Default | Description |
|----------|---------|-------------|
| `{VAR_NAME}` | `{default}` | {What it controls} |

### 3.3 Secret/Credential Sources

| Secret | Description | How to Provision |
|--------|-------------|------------------|
| `{SECRET_NAME}` | {What it's for} | {Docker secret/vault/.env} |

### 3.4 Environment Precedence

1. Docker secrets (`/run/secrets/`)
2. {source_2}
3. {source_3}

---

## 4. Health & Monitoring

### 4.1 Health Check Endpoints

#### Liveness Probe

```http
GET {health_endpoint}
```

**Response (Healthy):**
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Response (Unhealthy):**
```json
{
  "status": "error",
  "message": "..."
}
```

#### Readiness Probe

```http
GET {readiness_endpoint}
```

**Checks:**
- {Check 1: Database connection}
- {Check 2: Dependency health}
- {Check 3: Required resources}

### 4.2 Metrics Endpoints (Prometheus)

```http
GET /metrics
```

**Key Metrics:**

| Metric Name | Type | Description |
|-------------|------|-------------|
| `{metric_name}` | {gauge/histogram/counter} | {What it measures} |

**Example Queries:**

```promql
# {What this query shows}
{metric_name}{label="value"}

# {What this query shows}
rate({metric_name}[5m])
```

### 4.3 Log Location and Format

**Log Driver:** {json-driver/syslog/etc}

**Log Levels:**
- `DEBUG` - {When to use}
- `INFO` - {When to use}
- `WARNING` - {When to use}
- `ERROR` - {When to use}

**Log Labels (for Loki aggregation):**
| Label | Value |
|-------|-------|
| `service` | `{service-name}` |
| `tier` | `{tier_name}` |
| `environment` | `{production/staging/dev}` |

### 4.4 Critical Alerts

**Grafana Alerts:**

| Alert Name | Condition | Severity | Action |
|------------|-----------|----------|--------|
| `{alert_name}` | `{expr}` | {warning/critical} | {What to do} |

**Critical Conditions to Monitor:**
- {Condition 1: e.g., Service down}
- {Condition 2: e.g., High error rate}
- {Condition 3: e.g., Dependency unavailable}

---

## 5. Deployment

### 5.1 Docker Image Reference

```bash
# Pull latest
docker pull {registry}/{image}:{tag}

# Specific version
docker pull {registry}/{image}:{version}
```

### 5.2 Resource Requirements

| Resource | Minimum | Recommended | Maximum |
|----------|---------|-------------|---------|
| CPU | {cores} | {cores} | {cores} |
| Memory | {amount} | {amount} | {amount} |
| GPU | {model/count} | {model/count} | {model/count} |
| Storage | {amount} | {amount} | {amount} |

### 5.3 Startup Dependencies

```yaml
depends_on:
  {dependency_service}:
    condition: service_healthy
```

**Startup Order:**
1. {dependency_1}
2. {dependency_2}
3. {this_service}

### 5.4 Docker Compose Profile

```bash
# Start with profile
docker compose --profile {profile_name} up -d

# Stop
docker compose --profile {profile_name} down
```

### 5.5 Scaling Considerations

**Horizontal Scaling:**
- Can scale: {Yes/No}
- Max instances: {number}
- Shared state: {Redis/Database/etc}
- Load balancer: {traefik/nginx/none}

**Vertical Scaling:**
- CPU-bound: {Yes/No}
- Memory-bound: {Yes/No}
- GPU-bound: {Yes/No}

### 5.6 Deployment Commands

```bash
# Local development
make {target}

# Production deployment
make {target}

# Verify health
curl {health_endpoint}
```

---

## 6. API Reference

### 6.1 Public APIs

#### {API Operation 1}

```http
{METHOD} {endpoint}
```

**Description:** {What this endpoint does}

**Request:**
```json
{
  "field1": "value1",
  "field2": "value2"
}
```

**Response (200 OK):**
```json
{
  "result": "...",
  "metadata": {}
}
```

**Error Responses:**
| Code | Description | Retry |
|------|-------------|-------|
| 400 | {When returned} | No |
| 500 | {When returned} | Yes |

### 6.2 Internal APIs

| Endpoint | Method | Used By |
|----------|--------|---------|
| `{path}` | {GET/POST/etc} | {service} |

### 6.3 Webhooks

| Webhook | Trigger | Payload |
|---------|---------|---------|
| `{event}` | {When fired} | {schema} |

---

## 7. NATS Integration

### 7.1 Subscribed Subjects

| Subject | Handler | Description |
|---------|---------|-------------|
| `{subject_pattern}` | `{handler_function}` | {What it does} |

### 7.2 Published Subjects

| Subject | When Published | Payload Schema |
|---------|----------------|----------------|
| `{subject_pattern}` | {Trigger condition} | {JSON schema} |

### 7.3 JetStream Configuration

**Stream:** `{stream_name}`
- Consumer: `{consumer_name}`
- Ack policy: `{explicit/none}`
- Max deliver: `{number}`

---

## 8. Data Storage

### 8.1 Database Schema

**Tables/Collections:**

| Table | Purpose | Indexes |
|-------|---------|---------|
| `{table_name}` | {What it stores} | `{indexed_columns}` |

### 8.2 Volume Mounts

| Volume | Mount Path | Purpose |
|--------|------------|---------|
| `{volume_name}` | `{container_path}` | {What's stored} |

### 8.3 Backup Strategy

**What to Backup:**
- {Data source 1}
- {Data source 2}

**Backup Commands:**
```bash
# {Backup command}
```

**Restore Commands:**
```bash
# {Restore command}
```

---

## 9. Security

### 9.1 Authentication

**Method:** {JWT/API Key/OAuth/etc}

**How to Configure:**
```bash
{configuration_command}
```

### 9.2 Authorization

**Access Levels:**
- {Role 1}: {Can do X}
- {Role 2}: {Can do Y}

### 9.3 Network Security

- **Internal Only:** {Yes/No}
- **TLS Required:** {Yes/No}
- **Allowed IPs:** {CIDR ranges}

---

## 10. Troubleshooting

### 10.1 Common Issues and Resolutions

#### Issue: {Problem description}

**Symptoms:**
- {Symptom 1}
- {Symptom 2}

**Diagnosis:**
```bash
# Diagnostic command
{command}
```

**Resolution:**
1. {Step 1}
2. {Step 2}

### 10.2 Log Patterns to Watch

**Healthy Logs:**
```
{pattern indicating health}
```

**Warning Patterns:**
```
{pattern indicating warning}
```

**Error Patterns:**
```
{pattern indicating error}
```

### 10.3 Recovery Procedures

**Service Restart:**
```bash
# Graceful restart
docker compose restart {service_name}

# Hard reset
docker compose up -d --force-recreate {service_name}
```

**Data Recovery:**
```bash
# Recovery command
{command}
```

### 10.4 Escalation Path

1. **First:** Check logs `docker compose logs {service_name}`
2. **Second:** Check dependency health
3. **Third:** Check resource usage `docker stats`
4. **Finally:** Escalate to {team/person}

---

## 11. Development

### 11.1 Local Development

```bash
# Start development environment
cd {service_path}
{dev_command}

# Run tests
{test_command}

# Build
{build_command}
```

### 11.2 Testing

| Test Type | Command | Coverage Target |
|-----------|---------|-----------------|
| Unit | `{command}` | {X}% |
| Integration | `{command}` | {X}% |
| E2E | `{command}` | {X}% |

### 11.3 Code Quality

- **Linting:** `{tool}` with `{config}`
- **Formatting:** `{tool}` with `{config}`
- **Type Checking:** `{tool}`

---

## 12. Changelog

### Version {VERSION} ({DATE})

**Added:**
- {New feature 1}
- {New feature 2}

**Changed:**
- {Change 1}
- {Change 2}

**Fixed:**
- {Fix 1}
- {Fix 2}

**Deprecated:**
- {Deprecated item}

---

## 13. References

- **Source Code:** `{repository_url}`
- **Related Docs:** `{doc_links}`
- **External APIs:** `{api_documentation_links}`
- **Design Documents:** `{design_doc_links}`

---

## Appendix A: Quick Reference

```bash
# Health check
curl {health_endpoint}

# View logs
docker compose logs -f {service_name}

# Restart service
docker compose restart {service_name}

# Connect to container
docker exec -it {container_name} sh

# View metrics
curl http://localhost:{metrics_port}/metrics
```

---

## Appendix B: Service-Specific Notes

{Any additional notes specific to this service}
