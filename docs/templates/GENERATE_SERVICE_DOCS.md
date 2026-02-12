# Service Documentation Generator

Guide and templates for creating standardized production documentation for PMOVES.AI services.

---

## Quick Start

### Using the Template

1. **Copy the template:**
   ```bash
   cp docs/templates/SERVICE_DOCUMENTATION_TEMPLATE.md docs/services/{service-name}.md
   ```

2. **Fill in placeholders:**
   - `{SERVICE_NAME}` - Service display name
   - `{service-name}` - Lowercase, hyphenated name for DNS/paths
   - `{VERSION}` - Current version
   - `{DATE}` - Today's date (YYYY-MM-DD)
   - `{STATUS}` - alpha/beta/stable/deprecated

3. **Remove unused sections:**
   - If the service doesn't use NATS, remove Section 7
   - If there are no webhooks, remove from Section 6.3
   - Keep empty sections with "N/A" if they may apply later

### Using the Script (Optional)

A helper script can semi-automate documentation generation:

```bash
# Generate docs from docker-compose.yml service definition
./scripts/generate-service-docs.sh {service-name}

# Or generate for all services
./scripts/generate-service-docs.sh --all
```

---

## Template Sections Guide

### Section 1: Service Overview

**Purpose:** High-level understanding of what the service does

**Required:**
- Brief description (2-3 sentences)
- 3-5 key features
- All dependencies (services, databases, external APIs)
- Technology stack table

**Tips:**
- Focus on WHAT it does, not HOW
- List external APIs (OpenAI, Anthropic, etc.)
- Include container base image

### Section 2: Network Configuration

**Purpose:** How to connect to and from the service

**Required:**
- All ports (internal container port, external host port)
- Network membership (which Docker networks)
- DNS names for service discovery
- ASCII connection diagram

**Port Types:**
- **Internal:** Port inside container (e.g., 3000)
- **External:** Port on host machine (e.g., 3030)
- **Metrics:** Prometheus scraping endpoint

**Network Names:**
- `pmoves_api` - Service-to-service APIs
- `pmoves_app` - Internal app services
- `pmoves_bus` - NATS message bus
- `pmoves_data` - Databases and storage

### Section 3: Environment Variables

**Purpose:** Configuration and secrets

**Required:**
- All required variables with descriptions
- Optional variables with defaults
- Secret sources (Docker secrets, vault, .env files)
- Environment precedence order

**Variable Naming:**
- Use `UPPER_CASE` for all env vars
- Include example values
- Note the source file (env.shared, .env.local, etc.)

### Section 4: Health & Monitoring

**Purpose:** Observability and alerting

**Required:**
- Health check endpoints (liveness, readiness)
- Prometheus metrics with example queries
- Log format and labels
- Critical alert conditions

**Health Check Pattern:**
```http
GET /healthz
```

**Response (OK):**
```json
{"status": "ok"}
```

**Metrics Naming:**
- Use snake_case: `service_request_count`
- Include labels: `service_request_count{model="gpt-4"}`
- Use standard types: counter, gauge, histogram

### Section 5: Deployment

**Purpose:** How to run the service

**Required:**
- Docker image reference
- Resource requirements (CPU, memory, GPU)
- Startup dependencies
- Docker Compose profile name
- Scaling considerations

**Resource Guidelines:**
- Be realistic with minimums
- Consider GPU requirements for ML services
- Note if service can scale horizontally

### Section 6: API Reference

**Purpose:** How to use the service

**Required:**
- All public endpoints with examples
- Request/response schemas
- Error codes and retry logic
- Internal APIs (if any)
- Webhooks (if any)

**API Documentation Pattern:**
```markdown
#### {Operation Name}

```http
POST /api/endpoint
```

**Description:** {What it does}

**Request:**
```json
{"field": "value"}
```

**Response (200 OK):**
```json
{"result": "..."}
```

**Error Responses:**
| Code | Description | Retry |
|------|-------------|-------|
| 400 | Bad request | No |
```

### Section 7: NATS Integration

**Purpose:** Event-driven communication

**Required if service uses NATS:**
- Subscribed subjects (what it listens to)
- Published subjects (what it emits)
- JetStream configuration (streams, consumers)

**Subject Naming:**
- Use version suffix: `subject.name.v1`
- Use wildcards: `subject.>` for all sub-subjects
- Document payload schema

### Section 8: Data Storage

**Purpose:** Persistence and backup

**Required:**
- Database schema or collections
- Volume mounts
- Backup/restore commands

**If service uses no database:**
- State "Stateless service - no persistent storage"
- Remove backup/restore subsections

### Section 9: Security

**Purpose:** Access control

**Required:**
- Authentication method
- Authorization levels
- Network security (TLS, IP restrictions)

**If no auth:**
- State "Relies on network isolation"
- Note which networks have access

### Section 10: Troubleshooting

**Purpose:** Common issues and recovery

**Required:**
- At least 3 common issues with resolutions
- Log patterns (healthy, warning, error)
- Recovery commands
- Escalation path

**Issue Pattern:**
```markdown
#### Issue: {Problem title}

**Symptoms:**
- {Observable symptom 1}
- {Observable symptom 2}

**Diagnosis:**
```bash
{diagnostic command}
```

**Resolution:**
1. {First step}
2. {Second step}
```

### Section 11: Development

**Purpose:** Local development

**Required:**
- Local dev commands
- Test commands and coverage targets
- Code quality tools

**For third-party services:**
- Note that code is external
- Focus on integration testing

### Section 12: Changelog

**Purpose:** Version history

**Required:**
- Current version with changes
- Use semantic categories: Added, Changed, Fixed, Deprecated

### Appendix A: Quick Reference

**Purpose:** Common commands

**Required:**
- Health check
- Log viewing
- Service restart
- Container access
- Metrics viewing

### Appendix B: Service-Specific Notes

**Purpose:** Additional context

**Content:**
- Architecture decisions
- Known limitations
- Future improvements
- Migration guides

---

## Automation Script

### Shell Script Template

Save as `scripts/generate-service-docs.sh`:

```bash
#!/usr/bin/env bash
# Generate service documentation from docker-compose.yml

set -euo pipefail

SERVICE_NAME="${1:-}"
TEMPLATE="docs/templates/SERVICE_DOCUMENTATION_TEMPLATE.md"
OUTPUT_DIR="docs/services"

if [[ -z "$SERVICE_NAME" ]]; then
  echo "Usage: $0 <service-name>"
  echo "   or: $0 --all (for all services)"
  exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Generate documentation
generate_docs() {
  local service=$1
  local output="$OUTPUT_DIR/${service}.md"

  echo "Generating documentation for $service..."

  # Extract service info from docker-compose.yml
  # This is a template - implement actual extraction

  # Copy template
  cp "$TEMPLATE" "$output"

  # Replace placeholders (implement based on your needs)
  sed -i "s/{SERVICE_NAME}/${service}/g" "$output"
  sed -i "s/{service-name}/${service}/g" "$output"
  sed -i "s/{VERSION}/latest/g" "$output"
  sed -i "s/{DATE}/$(date +%Y-%m-%d)/g" "$output"
  sed -i "s/{STATUS}/stable/g" "$output"

  echo "Created $output"
  echo "Next: Edit the file and fill in the remaining placeholders"
}

if [[ "$SERVICE_NAME" == "--all" ]]; then
  # Generate for all services in docker-compose.yml
  for service in $(docker compose config --services); do
    generate_docs "$service"
  done
else
  generate_docs "$SERVICE_NAME"
fi
```

### Usage

```bash
chmod +x scripts/generate-service-docs.sh

# Generate for specific service
./scripts/generate-service-docs.sh agent-zero

# Generate for all services
./scripts/generate-service-docs.sh --all
```

---

## Documentation Checklist

Use this checklist when creating new service documentation:

### Content Completeness

- [ ] Service overview with purpose and features
- [ ] All dependencies listed
- [ ] Network configuration (ports, networks, DNS)
- [ ] Environment variables with sources
- [ ] Health check endpoints documented
- [ ] Prometheus metrics with examples
- [ ] Log format and labels
- [ ] Critical alerts defined
- [ ] Docker image reference
- [ ] Resource requirements
- [ ] Startup dependencies
- [ ] API reference with examples
- [ ] NATS subjects (if applicable)
- [ ] Data storage and backup procedures
- [ ] Security considerations
- [ ] Troubleshooting guide with 3+ issues
- [ ] Development commands
- [ ] Changelog with current version

### Quality Checks

- [ ] All placeholders filled or removed
- [ ] Code blocks use proper syntax highlighting
- [ ] Tables are properly formatted
- [ ] Links are valid
- [ ] ASCII diagrams are readable
- [ ] Commands are tested and accurate
- [ ] Version number is correct
- [ ] Date is current

### Consistency

- [ ] Service name uses consistent capitalization
- [ ] DNS names match docker-compose.yml
- [ ] Port numbers match docker-compose.yml
- [ ] Environment variable names match actual usage
- [ ] Network names match PMOVES conventions

---

## Examples

- **TensorZero:** `docs/templates/TensorZero_DOCUMENTATION_EXAMPLE.md`
- **Agent Zero:** Coming soon
- **Hi-RAG v2:** Coming soon

---

## Contributing

When adding a new service to PMOVES.AI:

1. Create documentation using this template
2. Fill in all required sections
3. Review against checklist above
4. Submit PR with documentation

**Minimum requirement:** Service overview, network config, health checks, and troubleshooting.

---

## Support

For questions about this template or documentation generation:
- Check existing examples in `docs/templates/`
- Open an issue in the PMOVES.AI repository
- Contact the infrastructure team
