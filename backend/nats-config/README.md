# NATS Configuration for PMOVES-DoX

This directory contains NATS server configuration for the PMOVES-DoX message bus.

## TLS Configuration

For distributed deployments, NATS should use TLS to encrypt WebSocket and client connections.

### Quick Start (Development)

```bash
# Generate self-signed certificates
cd backend/nats-config
chmod +x generate-certs.sh
./generate-certs.sh

# Enable TLS in docker-compose
export NATS_TLS_ENABLED=true
docker compose up -d nats
```

### Certificate Files

After running `generate-certs.sh`, the `certs/` directory will contain:

| File | Purpose |
|------|---------|
| `ca.crt` | Certificate Authority (for client verification) |
| `server.crt` | NATS server certificate |
| `server.key` | NATS server private key |
| `client.crt` | Client certificate (for mutual TLS) |
| `client.key` | Client private key |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NATS_TLS_ENABLED` | `false` | Enable TLS connections |
| `NATS_TLS_CA` | `/app/nats-certs/ca.crt` | CA certificate path |
| `NATS_TLS_CERT` | `/app/nats-certs/client.crt` | Client certificate (mutual TLS) |
| `NATS_TLS_KEY` | `/app/nats-certs/client.key` | Client private key |

### Production Setup

For production deployments:

1. **Use proper certificates** from a trusted CA (Let's Encrypt, etc.)
2. **Update `nats.conf`** to uncomment the TLS blocks
3. **Mount certificates** in docker-compose volumes
4. **Set environment variables** for TLS paths

### Manual nats.conf Configuration

Edit `nats.conf` to enable TLS:

```hcl
# Enable WebSocket TLS
websocket {
    port: 9222
    no_tls: false  # Change from true
    tls {
        cert_file: "/etc/nats/certs/server.crt"
        key_file: "/etc/nats/certs/server.key"
    }
}

# Enable Core NATS TLS (optional)
tls {
    cert_file: "/etc/nats/certs/server.crt"
    key_file: "/etc/nats/certs/server.key"
    ca_file: "/etc/nats/certs/ca.crt"
    verify: false  # Set to true for mutual TLS
}
```

### Tailscale/WireGuard Deployments

When using Tailscale or WireGuard for VPN connectivity:

1. Certificates should use hostnames resolvable within the mesh
2. Add SANs for Tailscale IPs (100.x.x.x) in `generate-certs.sh`
3. Consider using Let's Encrypt with DNS challenge for proper certs

### Troubleshooting

**Connection refused with TLS:**
- Check that `NATS_TLS_ENABLED=true` is set
- Verify certificates exist in `certs/` directory
- Check NATS container logs: `docker logs pmoves-dox-nats`

**Certificate verification failed:**
- Ensure CA certificate is mounted and accessible
- Check certificate expiration dates
- Verify SANs include the hostname being used

**WebSocket connection fails:**
- Frontend must use `wss://` instead of `ws://` when TLS enabled
- Update `NEXT_PUBLIC_NATS_WS_URL=wss://localhost:9223`
