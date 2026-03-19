# DoX Distributed Deployment Context

> Context file for Claude Code when working with DoX in distributed mode.

## Architecture Position

DoX is the **Document Intelligence** module in the PMOVES ecosystem. It hosts:

- **Agent Zero** (dual-instance): Headless (:50051) + UI (:50052) connected via MCP
- **Backend API** (:8484): Document processing, search, Q&A
- **CHIT Geometry Bus**: Real-time geometric visualization via NATS

```
┌─────────────────────────────────────┐
│              DoX                     │
│  ┌───────────────────────────────┐  │
│  │     Agent Zero (Dual)         │  │
│  │  ┌─────────┐  ┌─────────┐     │  │
│  │  │Headless │◄─►│   UI   │     │  │
│  │  │ :50051  │MCP│ :50052 │     │  │
│  │  └─────────┘  └─────────┘     │  │
│  └───────────────────────────────┘  │
│                                      │
│  Backend :8484  │  CHIT Bus :4222   │
└──────────────────────────────────────┘
```

## Service Discovery

### Environment Variables (Distributed Mode)

```bash
# This service
DOX_HOST=192.168.1.20
DOX_PORT=8484
DOX_BACKEND_URL=http://${DOX_HOST}:${DOX_PORT}

# Parent services
NATS_URL=nats://192.168.1.10:4222
TENSORZERO_URL=http://192.168.1.10:3030
SUPABASE_URL=http://192.168.1.10:54321

# Sibling submodules
BOTZ_GATEWAY_URL=http://192.168.1.30:2091
TOKENISM_URL=http://192.168.1.40:5000
```

### Configuration Files

| File | Purpose |
|------|---------|
| `env.distributed.example` | Template for cross-host configuration |
| `docker-compose.distributed.yml` | Overlay for distributed networks |
| `backend/nats-config/` | TLS certificates for secure NATS |

## NATS Subjects (Published)

DoX publishes to these NATS subjects:

| Subject | Description |
|---------|-------------|
| `geometry.event.manifold_update` | Manifold parameter changes |
| `geometry.cgp.ready.v1` | CHIT Geometry Packet ready |
| `dox.document.ingested.v1` | Document ingestion complete |
| `dox.search.query.v1` | Search query executed |
| `dox.qa.response.v1` | Q&A response generated |

## NATS Subjects (Subscribed)

DoX subscribes to:

| Subject | Source | Description |
|---------|--------|-------------|
| `tokenism.cgp.>` | Tokenism | Simulation geometry events |
| `botz.mcp.tool.executed.v1` | BoTZ | MCP tool execution results |

## Integration Health

DoX checks these services at `/system/health`:

```json
{
  "integrations": {
    "tensorzero": {"healthy": true, "url": "http://..."},
    "nats": {"healthy": true, "url": "nats://..."},
    "botz_gateway": {"healthy": true, "url": "http://..."},
    "tokenism": {"healthy": true, "url": "http://..."}
  }
}
```

## MCP Endpoint Exposure

Agent Zero exposes MCP at:
- **Headless**: `http://${DOX_HOST}:50051/mcp/t-{token}/sse`
- **UI**: `http://${DOX_HOST}:50052` (Web interface)

### MCP Token Configuration

```bash
AGENT_ZERO_MCP_TOKEN=your-secure-token
AGENT_ZERO_MCP_ENABLED=true
```

## BoTZ Integration

DoX connects to BoTZ for:

1. **MCP Tool Invocation**: Call BoTZ tools via gateway
2. **Archon Knowledge**: Query knowledge graph
3. **Cipher Memory**: Store/recall persistent memory

### A2A Discovery

DoX exposes `/.well-known/agent-card` for BoTZ discovery:

```json
{
  "name": "pmoves-dox",
  "capabilities": ["document_processing", "search", "qa", "geometry"],
  "mcp_endpoint": "http://192.168.1.20:50051/mcp"
}
```

## TLS Configuration (NATS)

For secure distributed NATS:

```bash
NATS_TLS_ENABLED=true
NATS_TLS_CA=/app/nats-certs/ca.crt
NATS_TLS_CERT=/app/nats-certs/client.crt
NATS_TLS_KEY=/app/nats-certs/client.key
```

Generate certificates:
```bash
cd backend/nats-config
./generate-certs.sh
```

## Troubleshooting

### Service Not Reachable

1. Check firewall rules (ports 8484, 50051, 50052)
2. Verify network topology in env.distributed
3. Test with `curl http://${DOX_HOST}:8484/healthz`

### NATS Connection Failed

1. Verify TLS certificates are mounted
2. Check NATS_URL resolves correctly
3. Test with `nats pub test "hello"` from container

### Agent Zero MCP Timeout

1. Verify AGENT_ZERO_MCP_ENABLED=true
2. Check token matches between services
3. Review Agent Zero logs for auth errors

## Related Documentation

- [PMOVES.AI DISTRIBUTED_SUBMODULES.md](../../pmoves/docs/DISTRIBUTED_SUBMODULES.md)
- [DoX DOCKING_GUIDE.md](../docs/DOCKING_GUIDE.md)
- [DoX ARCHITECTURE.md](../docs/ARCHITECTURE.md)
