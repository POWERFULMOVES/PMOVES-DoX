# PMOVES-DoX Distributed Deployment Guide

This guide explains how to deploy PMOVES-DoX on separate hardware from other PMOVES submodules while maintaining connectivity via local network, Tailscale, or VPS.

## Overview

DoX (Document Intelligence) can run independently on any host with:
- Docker and Docker Compose v2
- Network connectivity to other PMOVES services
- GPU recommended for fast PDF processing and embeddings

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/POWERFULMOVES/PMOVES-DoX.git
cd PMOVES-DoX

# Copy distributed configuration template
cp env.distributed.example .env.distributed

# Edit for your network topology
nano .env.distributed
```

### 2. Generate TLS Certificates

TLS is required for NATS in distributed deployments:

```bash
cd backend/nats-config
chmod +x generate-certs.sh
./generate-certs.sh

# Certificates are created in ./certs/
ls certs/
# ca.crt  client.crt  client.key  server.crt  server.key
```

### 3. Start DoX

```bash
# With distributed overlay
docker compose -f docker-compose.yml -f docker-compose.distributed.yml \
  --env-file .env.distributed up -d

# Check status
docker compose ps
curl http://localhost:8484/healthz
```

## Configuration

### Required Environment Variables

```bash
# Network Mode
DEPLOYMENT_MODE=distributed
DISTRIBUTED_SERVICES=true

# NATS Message Bus (TLS required)
NATS_HOST=192.168.1.10          # or Tailscale IP
NATS_PORT=4222
NATS_URL=nats://${NATS_HOST}:${NATS_PORT}
NATS_TLS_ENABLED=true

# This service (DoX)
DOX_HOST=192.168.1.20           # this host's IP
DOX_PORT=8484
```

### Optional Service Connections

```bash
# TensorZero LLM Gateway (for Q&A and summarization)
TENSORZERO_HOST=192.168.1.10
TENSORZERO_URL=http://${TENSORZERO_HOST}:3030

# BoTZ MCP Gateway (for tool orchestration)
BOTZ_HOST=192.168.1.30
BOTZ_GATEWAY_URL=http://${BOTZ_HOST}:2091

# Tokenism (for geometry visualization)
TOKENISM_HOST=192.168.1.40
TOKENISM_URL=http://${TOKENISM_HOST}:5000

# Ollama (for local embeddings)
OLLAMA_HOST=192.168.1.50
OLLAMA_BASE_URL=http://${OLLAMA_HOST}:11434
```

## Network Topologies

### Local Network (192.168.x.x)

For AI Lab setups where all machines are on the same LAN:

```bash
# .env.distributed
NATS_HOST=192.168.1.10
DOX_HOST=192.168.1.20
TENSORZERO_HOST=192.168.1.10
BOTZ_HOST=192.168.1.30
TOKENISM_HOST=192.168.1.40
```

### Tailscale Mesh (100.x.x.x)

For geographically distributed hosts connected via Tailscale:

```bash
# .env.distributed
NATS_HOST=100.64.1.10
DOX_HOST=100.64.1.20
TENSORZERO_HOST=100.64.1.10
BOTZ_HOST=100.64.1.30

# Enable Tailscale sidecar
TAILSCALE_ENABLED=true
TAILSCALE_AUTHKEY=tskey-auth-xxxxx
TAILSCALE_HOSTNAME=pmoves-dox
```

Start with Tailscale profile:

```bash
docker compose -f docker-compose.yml -f docker-compose.distributed.yml \
  --profile tailscale --env-file .env.distributed up -d
```

### VPS Deployment

For deploying DoX on a Hostinger KVM or similar VPS:

```bash
# .env.distributed
NATS_HOST=your-vps.example.com
DOX_HOST=0.0.0.0  # Listen on all interfaces
NATS_TLS_ENABLED=true

# Use WireGuard for home network connection
# (configure separately on VPS)
```

## Port Configuration

| Port | Service | Description |
|------|---------|-------------|
| 8484 | DoX Backend | FastAPI REST API |
| 3001 | DoX Frontend | Next.js UI |
| 4223 | NATS Core | Message bus (standalone) |
| 8223 | NATS HTTP | Monitoring API |
| 9223 | NATS WebSocket | Browser connections |
| 54321 | Supabase Proxy | Database API |
| 11435 | Ollama | Local LLM (optional) |
| 17474 | Neo4j HTTP | Graph database |
| 17687 | Neo4j Bolt | Graph protocol |

## TLS Configuration

### Certificate Generation

The `generate-certs.sh` script creates:

| File | Purpose |
|------|---------|
| `ca.crt` | Certificate Authority |
| `server.crt` / `server.key` | NATS server certificate |
| `client.crt` / `client.key` | Client certificate (mutual TLS) |

### Custom SANs

For Tailscale or custom hostnames, edit `generate-certs.sh`:

```bash
# In server.ext section, add your SANs:
[alt_names]
DNS.1 = nats
DNS.2 = nats.pmoves.local
DNS.3 = pmoves-dox.tailnet-name.ts.net  # Tailscale hostname
DNS.4 = localhost
IP.1 = 127.0.0.1
IP.2 = 100.64.1.20  # Tailscale IP
```

### Frontend WebSocket

When TLS is enabled, the frontend must use secure WebSocket:

```bash
# .env.distributed
NEXT_PUBLIC_NATS_WS_URL=wss://localhost:9223
```

## Health Checks

### Backend

```bash
curl http://localhost:8484/healthz
# {"status": "ok", "version": "x.x.x"}

curl http://localhost:8484/health/services
# {"nats": "connected", "database": "ok", "search_index": "ready"}
```

### NATS

```bash
curl http://localhost:8223/healthz
# ok
```

### Cross-Service Connectivity

```bash
# Test DoX → TensorZero
curl http://${TENSORZERO_HOST}:3030/health

# Test DoX → BoTZ Gateway
curl http://${BOTZ_HOST}:2091/health

# Test NATS publish (requires nats-cli)
nats pub test.ping "hello" --server=nats://${NATS_HOST}:4222
```

## GPU Configuration

### NVIDIA GPU (Default)

The distributed overlay inherits GPU settings from the base compose:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

### CPU-Only Mode

For VPS or non-GPU hosts, use the CPU compose:

```bash
docker compose -f docker-compose.cpu.yml -f docker-compose.distributed.yml \
  --env-file .env.distributed up -d
```

### Jetson Orin

For ARM64 Jetson devices:

```bash
docker compose -f docker-compose.jetson-orin.yml -f docker-compose.distributed.yml \
  --env-file .env.distributed up -d
```

## Troubleshooting

### NATS Connection Failed

```
Error: Failed to connect to NATS (standalone mode): Connection refused
```

**Solutions:**
1. Check NATS service is running: `docker compose ps nats`
2. Verify port is open: `nc -zv ${NATS_HOST} 4222`
3. Check TLS configuration if enabled

### TLS Handshake Error

```
Error: tls: failed to verify certificate
```

**Solutions:**
1. Regenerate certificates with correct SANs
2. Verify CA certificate is mounted: `docker exec pmoves-dox-backend ls /app/nats-certs/`
3. Check certificate dates: `openssl x509 -in certs/server.crt -noout -dates`

### Frontend Cannot Connect to NATS

```
WebSocket connection failed
```

**Solutions:**
1. Use `wss://` when TLS is enabled
2. Check CORS settings in NATS config
3. Verify WebSocket port (9223) is exposed

### Service Discovery Failures

```
Error: Could not resolve hostname
```

**Solutions:**
1. Use IP addresses instead of hostnames for distributed mode
2. Check DNS resolution on the host
3. Verify Tailscale is connected if using Tailscale IPs

## Integration with Other Submodules

### BoTZ Integration

DoX can be called from BoTZ via MCP:

```python
# BoTZ calling DoX
response = await mcp_client.call("dox", "search", {"query": "financial report"})
```

Configure in BoTZ:
```bash
DOX_BACKEND_URL=http://${DOX_HOST}:8484
```

### Tokenism Integration

DoX publishes geometry events to Tokenism via NATS:

```bash
# NATS subject for geometry packets
tokenism.cgp.ready.v1

# DoX listens for tokenism events
geometry.>
```

## File Reference

| File | Purpose |
|------|---------|
| `env.distributed.example` | Environment template for distributed mode |
| `docker-compose.distributed.yml` | Docker Compose overlay for distributed mode |
| `backend/nats-config/generate-certs.sh` | TLS certificate generator |
| `backend/nats-config/nats.conf` | NATS server configuration |
| `backend/nats-config/README.md` | NATS TLS documentation |

## Related Documentation

- [Parent PMOVES.AI Distributed Guide](../../pmoves/docs/DISTRIBUTED_SUBMODULES.md)
- [NATS TLS Configuration](../backend/nats-config/README.md)
- [Docking Guide](./DOCKING_GUIDE.md)
