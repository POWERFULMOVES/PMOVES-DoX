# Infrastructure Validation Guide

This guide describes the infrastructure validation system for PMOVES.AI deployments to Hostinger KVM and AI homelab environments.

## Overview

The validation system ensures reliable infrastructure changes before they are pushed to production. It runs automatically:

1. **Pre-commit**: Validates changes before you commit
2. **CI/CD**: Validates pull requests in GitHub Actions
3. **Manual**: Run validation on-demand via Makefile

## Quick Start

```bash
# Run full validation
make validate-changes

# Run quick validation (skip slow checks)
make validate-fast

# Run with verbose output
./scripts/validate-changes.sh --verbose

# Run in CI mode (no interactive prompts)
./scripts/validate-changes.sh --ci
```

## Installation

### Pre-commit Hook Installation

**Option 1: Using pre-commit framework (recommended)**

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

**Option 2: Using Git hooks directly**

```bash
# Create symlink
ln -s ../../scripts/pre-commit-hook .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### Bypass Pre-commit (Not Recommended)

```bash
git commit --no-verify -m "WIP: work in progress"
```

## Validation Checks

### 1. Service Health Checks

Validates that all services respond to their health endpoints:

| Service | Port | Health Endpoint | Required |
|---------|------|-----------------|----------|
| backend | 8484 | `/healthz` | Yes |
| frontend | 3001 | `/__heartbeat__` | Yes |
| tensorzero | 3030 | `/health` | Yes |
| agent-zero | 50051 | `/health` | Yes |
| nats | 4223 | - | No |
| neo4j | 17474 | - | No |
| clickhouse | 8123 | `/ping` | No |

**Exit codes:**
- `0`: Service is healthy (HTTP 2xx or 3xx)
- `1`: Service is unreachable (required services fail validation)

### 2. Environment Variable Validation

Checks for common configuration issues:

- **Empty values**: Required variables must have values
- **Placeholder patterns**: Detects `changeme`, `your_secret_here`, etc.
- **Hardcoded secrets**: Detects credentials in docker-compose files
- **Undocumented variables**: Used but not declared in env files

**Required variables:**
```bash
POSTGRES_PASSWORD=         # Required, no default
NEO4J_PASSWORD=            # Required, no default
CLICKHOUSE_PASSWORD=       # Required, no default
SUPABASE_JWT_SECRET=       # Required, no default
NATS_URL=nats://nats:4222  # Has default
DB_BACKEND=sqlite          # Has default
```

### 3. Network Connectivity Validation

Ensures proper network configuration:

- **Port conflicts**: Detects duplicate port declarations
- **Port range**: Validates ports are in 1024-65535 range
- **Service reachability**: Verifies ports are accessible
- **External networks**: Checks parent network references

**Declared ports:**
```yaml
backend:     8484  # API
frontend:    3001  # Web UI
tensorzero:  3030  # LLM Gateway
agent-zero:  50051 # Agent MCP/Web
nats:        4223  # Message bus
neo4j:       17474 # Knowledge graph HTTP
neo4j-bolt:  17687 # Knowledge graph Bolt
clickhouse:  8123  # Observability DB
```

### 4. Database Validation

Verifies database connectivity and schema:

- **Connection**: PostgreSQL container is reachable
- **Tables**: Required tables exist (artifacts, evidence, facts, summaries)
- **Migrations**: Alembic can be applied
- **Dual-write**: Supabase configuration is correct

**Required tables:**
```sql
-- Core tables
artifacts   -- Uploaded files
evidence    -- Extracted content chunks
facts       -- Structured data
summaries   -- Generated summaries
```

### 5. Configuration File Validation

Ensures docker-compose files are valid:

- **YAML syntax**: Valid YAML structure
- **Circular dependencies**: No service dependency cycles
- **Image references**: Valid Docker images, no placeholders
- **Build contexts**: Referenced directories exist

## CI/CD Integration

### GitHub Actions Workflow

The validation runs automatically on:
- Pull requests to `main` branch
- Pushes to `main` branch
- Manual trigger via `workflow_dispatch`

**Triggered by file changes:**
```yaml
paths:
  - 'docker-compose*.yml'
  - '.env.example'
  - '.env.local.example'
  - 'env.shared'
  - 'Makefile'
  - 'scripts/validate-changes.sh'
```

**Workflow jobs:**
1. `validate-configuration` - YAML and docker-compose syntax
2. `validate-environment` - Environment variable checks
3. `validate-network` - Port and network validation
4. `validate-dependencies` - Service dependency analysis
5. `validate-security` - Security checks (privileged containers, host mounts)

### Adding to Your Workflow

```yaml
- name: Validate Infrastructure Changes
  run: make validate-changes
```

## Advanced Usage

### Custom Service Checks

Edit `scripts/validate-changes.sh` to add services:

```bash
SERVICES_TO_CHECK=(
    "your-service:8080:/healthz:true"
)
```

Format: `name:port:health_path:required`

### Custom Environment Variables

Add required variables:

```bash
REQUIRED_ENV_VARS=(
    "YOUR_VAR:true:false"  # name:is_secret:default_allowed
)
```

### Custom Placeholder Patterns

Add patterns to detect:

```bash
PLACEHOLDER_PATTERNS=(
    "your_custom_pattern"
)
```

## Troubleshooting

### Validation Fails But Services Are Running

**Issue**: Health check returns 000 (unreachable)

**Solutions:**
1. Check if services are running: `docker compose ps`
2. Check port bindings: `docker compose port backend 8484`
3. Verify health endpoint path matches configuration

### Port Conflict Detected

**Issue**: Port declared multiple times

**Solutions:**
1. Use different host ports: `"8484:8484"` → `"8485:8484"`
2. Remove duplicate service declarations
3. Use `docker-compose.override.yml` for local overrides

### YAML Syntax Error

**Issue**: yamllint reports syntax error

**Solutions:**
1. Check indentation (use spaces, not tabs)
2. Validate with: `docker compose config`
3. Use YAML linter in your editor

### Environment Variable Not Declared

**Issue**: Variable used in docker-compose but not in env files

**Solutions:**
1. Add to `.env.example` with documentation
2. Add default value in docker-compose: `${VAR:-default}`
3. Add to exclusion list if it's a system variable

## Deployment Checklist

Before deploying to Hostinger KVM or AI homelab:

- [ ] Run `make validate-changes` locally
- [ ] All health checks pass
- [ ] No placeholder values in env files
- [ ] No port conflicts detected
- [ ] Database migrations applied
- [ ] Secrets loaded from vault/env
- [ ] Backup current configuration
- [ ] Test in staging environment first

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed |
| 1 | One or more checks failed |
| 2 | Invalid arguments |

## Related Documentation

- [Deployment Guide](../pmoves/docs/DEPLOYMENT_STATUS_2026-02-09.md)
- [Docker Compose Networking](../pmoves/docs/DOCKER_COMPOSE_NETWORKING_GUIDE.md)
- [Production Validation Runbook](../pmoves/docs/PRODUCTION_VALIDATION_RUNBOOK.md)
- [Hardening Checklist](../pmoves/docs/DOCKER_HARDENING_CHECKLIST.md)
