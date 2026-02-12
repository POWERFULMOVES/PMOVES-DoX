# Architecture Documentation

This directory contains comprehensive architecture and network documentation for PMOVES-DoX.

## Documents

### [Service Dependencies](service-dependencies.md)
Service dependency graph, startup order, critical dependencies, and failure scenarios.

**Key topics:**
- Startup sequence by tier
- Health check dependencies
- Failure cascade analysis
- Recovery procedures

### [Network Map](network-map.md)
Docker network configuration, service placement, port mappings, and NATS subject flows.

**Key topics:**
- Network tiers (api, app, bus, data)
- Standalone vs docked mode networking
- Port mappings (internal and external)
- Service discovery and DNS resolution

### [Data Flows](data-flows.md)
Data flow diagrams for ingestion, search, agent coordination, and knowledge retrieval.

**Key topics:**
- Document ingestion pipeline
- Search and Q&A flow
- LLM integration via TensorZero
- Agent coordination with NATS
- Knowledge graph extraction
- CHR pipeline

### [Service Catalog](service-catalog.md)
Complete catalog of all services with ports, health endpoints, and dependencies.

**Key topics:**
- Service categories (data, API, app, bus, agent, media, tool, monitoring)
- Health check endpoints
- Environment variables
- Service capabilities

### [Repository Map](repository-map.md)
Folder structure, submodule catalog, and key file purposes.

**Key topics:**
- Directory structure
- Submodule branch strategy
- Configuration files
- Documentation structure

## Quick Reference

### Essential Ports

| Port | Service | Purpose |
|------|---------|---------|
| 8484 | backend | Main API |
| 3001 | frontend | Web UI |
| 50051 | agent-zero | Agent UI |
| 3030 | tensorzero | LLM gateway |
| 4223 | nats | Message bus (standalone) |
| 9223 | nats | NATS WebSocket (standalone) |
| 17474 | neo4j | Graph browser |
| 54321 | supabase-proxy | API gateway |

### Networks

| Network | CIDR (Standalone) | Internal |
|---------|-------------------|----------|
| pmoves_dox_api | 172.31.1.0/24 | No |
| pmoves_dox_app | 172.31.2.0/24 | Yes |
| pmoves_dox_bus | 172.31.3.0/24 | Yes |
| pmoves_dox_data | 172.31.4.0/24 | Yes |

### Startup Order

1. **Infrastructure (Tier 0)**: supabase-db, nats, neo4j, clickhouse
2. **Core Services (Tier 1)**: backend, tensorzero, supabase-rest
3. **Processing Services (Tier 2)**: agent-zero, cipher-service, MCP agents
4. **Frontend (Tier 3)**: frontend
5. **Utilities (Tier 4)**: glances, datavzrd, schemavzrd

### Health Check Commands

```bash
# All services
docker compose ps

# Backend health
curl http://localhost:8484/healthz

# Agent Zero health
curl http://localhost:50051/health

# TensorZero health
curl http://localhost:3030/health

# NATS monitoring
curl http://localhost:8223
```

## Diagrams

All documentation uses Mermaid diagrams for visualization. These render natively in:
- GitHub
- GitLab
- VS Code (with Mermaid preview extension)
- Mermaid Live Editor (https://mermaid.live)

## Operational Modes

### Standalone Mode
- All services run independently
- Networks: `pmoves_dox_*`
- NATS: `nats://localhost:4223`
- WebSocket: `ws://localhost:9223`

### Docked Mode
- Connects to parent PMOVES.AI infrastructure
- Networks: `pmoves_*` (parent)
- NATS: `nats://nats:4222` (via parent)
- WebSocket: `ws://localhost:9222` (parent)

## Related Documentation

- [../ARCHITECTURE.md](../ARCHITECTURE.md) - Technical architecture details
- [../DOCKING_GUIDE.md](../DOCKING_GUIDE.md) - Parent integration guide
- [../API_REFERENCE.md](../API_REFERENCE.md) - Complete API reference
- [../DEPLOYMENT.md](../DEPLOYMENT.md) - Deployment guide

## Contributing

When updating architecture documentation:
1. Keep Mermaid diagrams compatible
2. Update quick reference tables
3. Cross-reference related documents
4. Document both standalone and docked modes
5. Include troubleshooting sections
