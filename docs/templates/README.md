# PMOVES.AI Service Documentation Templates

This directory contains standardized templates for creating production documentation for PMOVES.AI services.

---

## Files

| File | Purpose |
|------|---------|
| `SERVICE_DOCUMENTATION_TEMPLATE.md` | Master template with all sections |
| `TensorZero_DOCUMENTATION_EXAMPLE.md` | Filled example for reference |
| `GENERATE_SERVICE_DOCS.md` | Guide for creating documentation |

---

## Quick Start

### 1. For New Services

```bash
# Copy template
cp docs/templates/SERVICE_DOCUMENTATION_TEMPLATE.md docs/services/my-service.md

# Fill in placeholders:
# {SERVICE_NAME}    -> My Service Name
# {service-name}    -> my-service-name
# {VERSION}         -> 1.0.0
# {DATE}            -> 2025-02-10
# {STATUS}          -> alpha/beta/stable/deprecated
```

### 2. Using the Generator Script

```bash
# List available services
./scripts/generate-service-docs.sh --list

# Generate for specific service
./scripts/generate-service-docs.sh agent-zero

# Generate for all services
./scripts/generate-service-docs.sh --all

# Custom output location
./scripts/generate-service-docs.sh tensorzero --output ./my-docs
```

---

## Template Structure

Each service documentation should include:

1. **Service Overview** - Purpose, features, dependencies, tech stack
2. **Network Configuration** - Ports, networks, DNS names
3. **Environment Variables** - Required/optional vars with sources
4. **Health & Monitoring** - Health checks, metrics, logs, alerts
5. **Deployment** - Docker image, resources, scaling
6. **API Reference** - Endpoints with examples
7. **NATS Integration** - Subjects (if applicable)
8. **Data Storage** - Databases, volumes, backups
9. **Security** - Auth, authorization, network security
10. **Troubleshooting** - Common issues and recovery
11. **Development** - Local dev commands, testing
12. **Changelog** - Version history

---

## Checklist

Before submitting service documentation:

- [ ] All placeholders filled or removed
- [ ] Ports match docker-compose.yml
- [ ] Environment variables documented
- [ ] Health check endpoint tested
- [ ] At least 3 troubleshooting issues
- [ ] API examples are tested
- [ ] ASCII diagrams are readable
- [ ] Links are valid

---

## Examples

- **TensorZero:** `TensorZero_DOCUMENTATION_EXAMPLE.md` - Complete filled example
- More examples to be added as services are documented

---

## Automation

The `generate-service-docs.sh` script:

1. Parses `docker-compose.yml` for service info
2. Copies the template
3. Fills in auto-detected values (image, ports, networks)
4. Creates output file

**Note:** The script provides a starting point. Manual completion is required for:
- API documentation
- Troubleshooting scenarios
- Environment variable descriptions
- Security considerations

---

## Contributing

When adding a new service to PMOVES.AI:

1. Use the template to create documentation
2. Fill all required sections
3. Use the generator script as a starting point
4. Review against the checklist
5. Submit with your PR

**Minimum required sections:**
- Service Overview
- Network Configuration
- Health & Monitoring
- Troubleshooting

---

## Support

For questions:
- See `GENERATE_SERVICE_DOCS.md` for detailed guide
- Check existing examples in `../services/`
- Open an issue in PMOVES.AI repository
