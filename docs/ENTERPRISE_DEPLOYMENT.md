# PMOVES-DoX Enterprise Deployment Guide

Production-grade deployment instructions for PMOVES-DoX with mutual TLS, JWT authentication, and multi-tenant isolation.

**Audience:** DevOps engineers, platform administrators, and security teams deploying PMOVES-DoX in regulated or enterprise environments.

**Prerequisites:**
- Docker and Docker Compose v2+
- OpenSSL 1.1+ (for certificate generation)
- Python 3.11+ (for backend verification)
- NATS CLI tools (optional, for TLS verification)

---

## Table of Contents

1. [TLS Certificate Generation](#1-tls-certificate-generation)
2. [TLS Verification](#2-tls-verification)
3. [JWT Authentication Setup](#3-jwt-authentication-setup)
4. [Multi-Tenant Configuration](#4-multi-tenant-configuration)

---

## 1. TLS Certificate Generation

PMOVES-DoX uses mutual TLS (mTLS) to secure all NATS message bus communication. The certificate infrastructure supports both core NATS (port 4222) and WebSocket (port 9222) connections.

### 1.1 Certificate Architecture

The TLS PKI consists of three certificate pairs:

| Certificate | Purpose | Mount Path |
|-------------|---------|------------|
| `ca.crt` / `ca.key` | Certificate Authority root | `/etc/nats/certs/ca.crt` |
| `server.crt` / `server.key` | NATS server identity | `/etc/nats/certs/server.crt`, `/etc/nats/certs/server.key` |
| `client.crt` / `client.key` | Backend client identity (mTLS) | `/app/nats-certs/client.crt`, `/app/nats-certs/client.key` |

### 1.2 Generate Certificates

The repository includes a generation script at `backend/nats-config/generate-certs.sh`.

```bash
cd backend/nats-config
chmod +x generate-certs.sh
./generate-certs.sh        # Generates into ./certs/
./generate-certs.sh /opt/pmoves/certs  # Custom output directory
```

The script performs the following operations:

1. **CA Generation** -- Creates a 4096-bit RSA CA key and self-signed CA certificate (valid 365 days) with subject `/C=US/ST=California/L=San Francisco/O=PMOVES/OU=DoX/CN=PMOVES-DoX-CA`.

2. **Server Certificate** -- Generates a 4096-bit RSA server key, creates a CSR, and signs it with the CA. The certificate includes Subject Alternative Names (SANs):
   - `DNS.1 = nats`
   - `DNS.2 = nats.pmoves.local`
   - `DNS.3 = localhost`
   - `DNS.4 = *.nats.pmoves.local`
   - `IP.1 = 127.0.0.1`
   - `IP.2 = 0.0.0.0`

3. **Client Certificate** -- Generates a client certificate with `extendedKeyUsage = clientAuth` for mutual TLS. Subject: `/C=US/ST=California/L=San Francisco/O=PMOVES/OU=DoX-Client/CN=nats-client`.

4. **Permissions** -- Sets `600` on private keys and PEM bundles, `644` on public certificates. Cleans up intermediate CSR and extension files.

### 1.3 Certificate Output

After generation, the `certs/` directory contains:

```
certs/
  ca.crt           # CA public certificate (distribute to all clients)
  ca.key           # CA private key (keep secure, offline after generation)
  server.crt       # NATS server certificate
  server.key       # NATS server private key
  server.pem       # Combined server cert + key
  client.crt       # Client certificate for backend mTLS
  client.key       # Client private key
  client.pem       # Combined client cert + key
```

### 1.4 NATS TLS Configuration

Two NATS configuration files are provided:

**`nats-config/nats.conf`** (Enterprise mode -- mutual TLS with client verification):
```
tls {
    cert_file: "/etc/nats/certs/server.crt"
    key_file: "/etc/nats/certs/server.key"
    ca_file: "/etc/nats/certs/ca.crt"
    verify: true       # Requires valid client certificate
}

websocket {
    port: 9222
    no_tls: false      # TLS enabled for WebSocket
    tls {
        cert_file: "/etc/nats/certs/server.crt"
        key_file: "/etc/nats/certs/server.key"
    }
    same_origin: false
}

jetstream {
    store_dir: "/data/jetstream"
}
```

**`nats-config/nats.tls.conf`** (Distributed mode -- server TLS without client verification):
```
tls {
    cert_file: "/etc/nats/certs/server.crt"
    key_file: "/etc/nats/certs/server.key"
    ca_file: "/etc/nats/certs/ca.crt"
    verify: false      # No client cert required
}
```

Choose the configuration based on your security posture:
- **`nats.conf`** with `verify: true`: Full mutual TLS. Every connecting client must present a valid client certificate signed by the CA. Use this for enterprise production.
- **`nats.tls.conf`** with `verify: false`: Server-side TLS only. Clients verify the server but do not present certificates. Use this for distributed deployments where client cert management is impractical.

### 1.5 Docker Volume Mounts

The `docker-compose.distributed.yml` overlay mounts certificates with read-only access and least privilege:

```yaml
nats:
  command: -c /etc/nats/nats.tls.conf
  volumes:
    - ./backend/nats-config/nats.tls.conf:/etc/nats/nats.tls.conf:ro
    - ./backend/nats-config/certs/ca.crt:/etc/nats/certs/ca.crt:ro
    - ./backend/nats-config/certs/server.crt:/etc/nats/certs/server.crt:ro
    - ./backend/nats-config/certs/server.key:/etc/nats/certs/server.key:ro
```

Only the server certificates are mounted to the NATS container. The `client.key` is never exposed to the NATS server -- it is only mounted to the backend container.

### 1.6 Production Certificate Recommendations

For production deployments, replace self-signed certificates:

| Approach | When to Use |
|----------|-------------|
| Internal CA (e.g., HashiCorp Vault PKI, step-ca) | Enterprise with existing PKI infrastructure |
| Let's Encrypt (ACME) | Public-facing NATS endpoints |
| Self-signed (generate-certs.sh) | Development, air-gapped environments, internal mesh |

To use custom certificates, replace the files in `certs/` and ensure SANs match your deployment hostnames. Update `DNS.*` entries in the server extension file if using custom domains.

**Certificate Rotation:** Regenerate certificates before the 365-day expiry. Schedule a cron job or integrate with your PKI's auto-renewal workflow. NATS requires a restart to pick up new certificates.

---

## 2. TLS Verification

### 2.1 Backend TLS Context

The backend connects to NATS using the shared TLS context factory at `backend/app/utils/nats_tls.py`. This module implements a **fail-closed** security model: if TLS is enabled but context creation fails, it raises a `RuntimeError` rather than silently degrading to plaintext.

**Environment Variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `NATS_TLS_ENABLED` | `""` (disabled) | Set to `true`, `1`, or `yes` to enable TLS |
| `NATS_TLS_CA` | `/app/nats-certs/ca.crt` | Path to CA certificate for server verification |
| `NATS_TLS_CERT` | `/app/nats-certs/client.crt` | Path to client certificate (for mTLS) |
| `NATS_TLS_KEY` | `/app/nats-certs/client.key` | Path to client private key (for mTLS) |

**Connection Flow:**

1. `create_nats_tls_context()` checks `NATS_TLS_ENABLED`.
2. If enabled, creates an `ssl.SSLContext` with `Purpose.SERVER_AUTH`.
3. Loads the CA certificate from `NATS_TLS_CA` for server verification. Falls back to system CA store if file not found.
4. If `NATS_TLS_CERT` and `NATS_TLS_KEY` both exist, loads them as client credentials for mutual TLS.
5. On any failure, raises `RuntimeError` with a diagnostic message (fail-closed).

The module also provides `sanitize_nats_url()` to strip credentials from NATS URLs before logging (e.g., `nats://user:pass@host:4222` becomes `nats://***@host:4222`).

### 2.2 Verify TLS is Working

#### Step 1: Check NATS Server TLS Status

```bash
# From the Docker host, use openssl to verify the server certificate
openssl s_client -connect localhost:4223 -CAfile backend/nats-config/certs/ca.crt

# Expected: "Verify return code: 0 (ok)"
# Check the subject and issuer match your CA
```

#### Step 2: Verify with NATS CLI

```bash
# Install NATS CLI: https://github.com/nats-io/natscli
# Server TLS only (no client cert):
nats server check connection \
  --server tls://localhost:4223 \
  --tlsca backend/nats-config/certs/ca.crt

# Mutual TLS (with client cert):
nats server check connection \
  --server tls://localhost:4223 \
  --tlsca backend/nats-config/certs/ca.crt \
  --tlscert backend/nats-config/certs/client.crt \
  --tlskey backend/nats-config/certs/client.key
```

#### Step 3: Publish/Subscribe Test over TLS

```bash
# Terminal 1 - Subscribe:
nats sub "test.>" \
  --server tls://localhost:4223 \
  --tlsca backend/nats-config/certs/ca.crt \
  --tlscert backend/nats-config/certs/client.crt \
  --tlskey backend/nats-config/certs/client.key

# Terminal 2 - Publish:
nats pub "test.tls" "Hello TLS" \
  --server tls://localhost:4223 \
  --tlsca backend/nats-config/certs/ca.crt \
  --tlscert backend/nats-config/certs/client.crt \
  --tlskey backend/nats-config/certs/client.key
```

#### Step 4: Verify Backend TLS Connection

```bash
# Check backend logs for TLS confirmation
docker compose logs backend 2>&1 | grep -i "tls\|nats\|certificate"

# Expected log lines:
#   Loaded NATS CA certificate from /app/nats-certs/ca.crt
#   Loaded NATS client certificate for mutual TLS

# If TLS fails, you will see:
#   RuntimeError: TLS context creation failed but NATS_TLS_ENABLED=true ...
```

#### Step 5: Verify WebSocket TLS

```bash
# Test WebSocket TLS endpoint (used by frontend for geometry bus)
openssl s_client -connect localhost:9223

# Or use wscat with TLS:
wscat -c wss://localhost:9223 --ca backend/nats-config/certs/ca.crt
```

### 2.3 Troubleshooting TLS Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| `RuntimeError: TLS context creation failed` | Cert files missing or unreadable | Check file paths and permissions (`chmod 600 *.key`) |
| `CERTIFICATE_VERIFY_FAILED` | CA mismatch or expired cert | Regenerate certs or verify CA chain |
| NATS connection refused on 4223 | NATS not using TLS config | Verify `command: -c /etc/nats/nats.tls.conf` in docker-compose |
| Backend connects without TLS | `NATS_TLS_ENABLED` not set | Set `NATS_TLS_ENABLED=true` in backend environment |
| `certificate unknown` error | Client cert not signed by same CA | Ensure client and server certs share the same CA |
| Frontend WebSocket fails | `no_tls: true` in nats.conf | Set `no_tls: false` in websocket block |

---

## 3. JWT Authentication Setup

PMOVES-DoX uses HS256 JWT tokens compatible with the Supabase JWT standard. The authentication module is shared across PMOVES.AI services (BoTZ, Archon, Agent Zero) for unified identity.

### 3.1 Authentication Architecture

The JWT system is implemented in `backend/app/auth/jwt.py` with three FastAPI dependency functions:

| Dependency | Usage | Behavior |
|------------|-------|----------|
| `get_current_user` | `Depends(get_current_user)` | Extracts `user_id` from JWT `sub` claim. Returns 401 if invalid. |
| `require_auth` | `Depends(require_auth)` | Returns full JWT payload dict. Returns 401 if invalid. |
| `optional_auth` | `Depends(optional_auth)` | Returns `user_id` if valid token present, `None` for anonymous. Logs failures. |

**Token Validation Rules:**
- Signature verified using `SUPABASE_JWT_SECRET` with HS256 algorithm
- Expiration (`exp` claim) is enforced
- Audience (`aud`) verification is disabled (cross-service compatibility)
- Supabase anonymous tokens (`role == "anon"`) are explicitly rejected
- Service role tokens (`role == "service_role"`) and authenticated user tokens are accepted

### 3.2 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_JWT_SECRET` | Yes (production) | `""` | HMAC-SHA256 secret for JWT signing/verification |
| `ENVIRONMENT` | No | `production` | Set to `development` to enable dev-mode bypass |

**Production Safety Guards:**

The module enforces two startup-time checks in production mode (`ENVIRONMENT != development`):

1. `python-jose` library must be installed -- raises `RuntimeError` if missing
2. `SUPABASE_JWT_SECRET` must be configured -- raises `RuntimeError` if empty

These guards prevent accidental deployment without authentication.

### 3.3 Generate JWT Tokens

#### Option A: Using Supabase (Recommended)

If deploying with Supabase, user tokens are generated automatically through the Supabase GoTrue authentication flow:

```bash
# Sign up a user
curl -X POST 'http://your-supabase-url/auth/v1/signup' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure-password"}'

# Sign in and get JWT
curl -X POST 'http://your-supabase-url/auth/v1/token?grant_type=password' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secure-password"}'

# Response includes access_token (JWT) in the body
```

#### Option B: Manual Token Generation (Service-to-Service)

For service accounts or testing, generate tokens directly using the shared secret:

```python
# Python: Generate a service JWT
from jose import jwt
from datetime import datetime, timedelta, timezone

JWT_SECRET = "your-supabase-jwt-secret"

payload = {
    "sub": "service-account-001",        # User/service identifier
    "role": "service_role",               # "service_role" or "authenticated"
    "iat": datetime.now(tz=timezone.utc),
    "exp": datetime.now(tz=timezone.utc) + timedelta(hours=24),
    "iss": "pmoves-dox",
}

token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
print(f"Bearer {token}")
```

```bash
# Curl: Use the token
curl -X GET http://localhost:8000/artifacts \
  -H "Authorization: Bearer <token>"
```

#### Option C: Development Mode Bypass

For local development only, set `ENVIRONMENT=development` to bypass JWT validation. The system returns a synthetic `dev_user` identity:

```bash
# In backend/.env
ENVIRONMENT=development
# SUPABASE_JWT_SECRET can be omitted

# All authenticated endpoints accept any or no token
# get_current_user returns "dev_user"
```

**WARNING:** Never use development mode in production. The startup guard prevents this by raising `RuntimeError` if `python-jose` or `SUPABASE_JWT_SECRET` is missing in production mode.

### 3.4 Endpoint Protection Matrix

| Endpoint | Auth Dependency | Behavior |
|----------|----------------|----------|
| `GET /artifacts` | None | Public listing |
| `GET /facts` | `optional_auth` | Anonymous sees all; authenticated sees owned |
| `GET /analysis/financials` | `optional_auth` | Scoped to user's artifacts if authenticated |
| `POST /ask` | `optional_auth` | Citations filtered to user's documents |
| `GET /evidence/{id}` | `optional_auth` | Ownership verified if authenticated |
| `DELETE /reset` | `get_current_user` | Authentication required |
| `GET /download` | `get_current_user` | Authentication required, ownership enforced |
| `POST /analysis/financials/{id}/reclassify` | `get_current_user` | Authentication required |

### 3.5 Token Error Responses

| HTTP Status | Error Detail | Cause |
|-------------|-------------|-------|
| 401 | `Missing Authorization header` | No `Authorization` header sent |
| 401 | `No token provided` | Empty or malformed Bearer token |
| 401 | `Token has expired` | JWT `exp` claim is in the past |
| 401 | `Invalid token signature` | Token signed with wrong secret |
| 401 | `Anonymous tokens are not allowed` | Supabase anon key used as bearer |
| 401 | `Token does not contain user identifier` | JWT missing `sub` claim |
| 500 | `Authentication configuration error` | Server-side JWT config issue |

---

## 4. Multi-Tenant Configuration

PMOVES-DoX supports multi-tenant isolation through user-scoped data access, configurable database backends, and network-segmented distributed deployment.

### 4.1 User-Scoped Access Control

Tenant isolation is enforced at the application layer through the `_get_user_artifact_ids()` function in `backend/app/api/routers/analysis.py`.

**Access Control Logic:**

```
Request
  |
  v
optional_auth / get_current_user
  |
  +-- No token --> user_id = None --> No scoping (anonymous access)
  |
  +-- Valid token --> user_id from JWT "sub" claim
        |
        v
      _get_user_artifact_ids(user_id)
        |
        +-- Fetches all artifacts from database
        |
        +-- Filters to artifacts where:
        |     uploaded_by == user_id  OR  user_id == user_id
        |
        +-- Returns set of owned artifact IDs
        |
        +-- If DB query fails --> Returns empty set (fail-closed)
        |
        v
      Query results filtered to owned artifact IDs only
```

**Key design decisions:**

- **Fail-closed on DB failure:** If the database query for artifacts fails, the function returns an empty set rather than `None`. This means authenticated users see no data on failure, rather than seeing all data.
- **Anonymous pass-through:** If no token is provided (`user_id` is `None`), `_get_user_artifact_ids` returns `None`, which means no scoping is applied. This is intentional for public/demo endpoints using `optional_auth`.
- **Ownership metadata:** Artifacts must have `uploaded_by` or `user_id` fields populated for tenant isolation to work. Ensure your ingestion pipeline records the uploading user's ID.

### 4.2 Download Ownership Enforcement

The `/download` endpoint in `backend/app/main.py` enforces a multi-layered security model:

1. **Path Traversal Prevention** -- Rejects paths containing `..`, leading `/` or `\`, or non-alphanumeric characters (regex: `^[a-zA-Z0-9_/.-]+$`).
2. **Directory Escape Guard** -- Resolves the target path and verifies it is within `ARTIFACTS_DIR` using `Path.relative_to()`.
3. **File Existence Check** -- Confirms the target is a file, not a directory.
4. **Artifact Lookup** -- Matches the path against known artifacts in the database.
5. **Ownership Check** -- Calls `_get_user_artifact_ids(user_id)` and returns 403 if the artifact is not in the user's allowed set.

This endpoint always requires authentication (`get_current_user`). Anonymous downloads are not permitted.

### 4.3 Database Backend Selection

PMOVES-DoX supports three database configurations via the `backend/app/database_factory.py`:

| Configuration | Environment Variables | Use Case |
|---------------|----------------------|----------|
| **SQLite** (default) | `DB_BACKEND=sqlite` | Single-tenant, local development |
| **Supabase** | `DB_BACKEND=supabase` | Multi-tenant production with PostgreSQL |
| **Dual-Write** | `DB_BACKEND=sqlite` + `SUPABASE_DUAL_WRITE=true` | Migration period: writes to both |

**SQLite Mode:**
```bash
DB_BACKEND=sqlite
DB_PATH=db.sqlite3    # Default path
```
- Single-file storage, zero configuration
- No built-in multi-user support
- Suitable for single-tenant or development deployments

**Supabase Mode:**
```bash
DB_BACKEND=supabase
SUPABASE_URL=http://supabase-kong:8000
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_KEY=<your-service-role-key>
```
- PostgreSQL-backed with Row-Level Security (RLS) support
- Native multi-tenant isolation at the database level
- Raises `SupabaseUnavailable` if connection fails (fail-closed)

**Dual-Write Mode:**
```bash
DB_BACKEND=sqlite
SUPABASE_DUAL_WRITE=true
SUPABASE_URL=http://supabase-kong:8000
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_KEY=<your-service-role-key>
```
- Writes propagate to both SQLite and Supabase
- Reads served from the primary backend (SQLite in this configuration)
- If Supabase is unavailable, secondary writes log a warning but do not block
- Use for zero-downtime migration from SQLite to Supabase

The `DualDatabase` wrapper delegates all methods in the `WRITE_METHODS` set (including `add_artifact`, `add_fact`, `add_evidence`, `reset`, and 16 others) to both backends. Read operations go to the primary only.

### 4.4 Distributed Deployment

The `docker-compose.distributed.yml` overlay configures PMOVES-DoX for deployment across multiple hosts or as a standalone satellite node.

**Usage:**
```bash
# Basic distributed deployment
docker compose \
  -f docker-compose.yml \
  -f docker-compose.distributed.yml \
  up -d

# With Tailscale VPN mesh
docker compose \
  -f docker-compose.yml \
  -f docker-compose.distributed.yml \
  --profile tailscale \
  up -d
```

**Key overlay changes:**

| Service | Change | Purpose |
|---------|--------|---------|
| `backend` | Binds to `0.0.0.0:8484` | External access from other hosts |
| `backend` | `NATS_TLS_ENABLED=true` | Enforces TLS for distributed NATS |
| `frontend` | Binds to `0.0.0.0:3001` | External access |
| `frontend` | `NEXT_PUBLIC_NATS_WS_URL=wss://localhost:9223` | Secure WebSocket |
| `nats` | Uses `nats.tls.conf` | TLS-enabled NATS |
| `nats` | Exposes `4223:4222`, `9223:9222` | External NATS + WebSocket |
| `nats` | HTTP monitoring `127.0.0.1:8223` only | Monitoring stays local |
| `ollama` | Moved to `local-ollama` profile | Uses remote Ollama by default |
| `tensorzero` | Moved to `local-tensorzero` profile | Uses remote TensorZero by default |
| All networks | `internal: false` | Allow cross-host routing |

**Environment variables for distributed service discovery:**

```bash
# Remote NATS (if not colocated)
NATS_URL=nats://remote-host:4222

# Remote TensorZero gateway
TENSORZERO_URL=http://tensorzero-host:3030

# Remote Ollama
OLLAMA_BASE_URL=http://gpu-host:11434

# Remote Neo4j
NEO4J_PARENT_URI=bolt://neo4j-host:7687

# Frontend API routing
DOX_BACKEND_URL=http://backend-host:8484
DOX_FRONTEND_ORIGIN=https://dox.pmoves.ai
```

### 4.5 Tailscale VPN Mesh (Optional)

The distributed overlay includes an optional Tailscale sidecar for encrypted mesh networking between nodes:

```bash
# Set Tailscale auth key
export TAILSCALE_AUTHKEY=tskey-auth-xxxxx

# Optionally customize hostname and advertised routes
export TAILSCALE_HOSTNAME=pmoves-dox-prod
export TAILSCALE_ADVERTISE_ROUTES=172.31.0.0/16

# Deploy with Tailscale profile
docker compose \
  -f docker-compose.yml \
  -f docker-compose.distributed.yml \
  --profile tailscale \
  up -d
```

The Tailscale container runs in `host` network mode with `NET_ADMIN` and `SYS_MODULE` capabilities, enabling it to act as a subnet router for the Docker networks.

### 4.6 Multi-Tenant Deployment Checklist

Before going live with a multi-tenant deployment, verify each item:

- [ ] **TLS Certificates Generated** -- `backend/nats-config/certs/` contains all six files
- [ ] **NATS TLS Enabled** -- `NATS_TLS_ENABLED=true` set in backend environment
- [ ] **mTLS Configuration** -- Choose `verify: true` (enterprise) or `verify: false` (distributed) in NATS config
- [ ] **JWT Secret Configured** -- `SUPABASE_JWT_SECRET` is set and matches across all PMOVES.AI services
- [ ] **Production Mode** -- `ENVIRONMENT=production` (never `development` in production)
- [ ] **python-jose Installed** -- `pip install 'python-jose[cryptography]>=3.5.0'` in backend container
- [ ] **Database Backend Selected** -- `DB_BACKEND=supabase` for multi-tenant, or `sqlite` for single-tenant
- [ ] **Artifact Ownership Tracked** -- Ingestion pipeline records `uploaded_by` field on artifacts
- [ ] **CORS Restricted** -- `FRONTEND_ORIGIN` set to specific origin (not `*`) in production
- [ ] **Certificate Rotation Scheduled** -- Certs expire in 365 days; schedule renewal
- [ ] **Health Checks Verified** -- `curl http://localhost:8484/healthz` returns 200
- [ ] **Network Segmentation** -- Internal networks are `internal: true` unless distributed mode is required
- [ ] **Monitoring Endpoints Local** -- NATS HTTP monitoring bound to `127.0.0.1` only

### 4.7 Network Tier Architecture

In distributed mode, PMOVES-DoX uses four network tiers:

```
                       Internet / VPN Mesh
                              |
                    +---------+---------+
                    |    api_tier       |  <-- Backend API (8484), Frontend (3001)
                    +---------+---------+
                              |
                    +---------+---------+
                    |    app_tier       |  <-- Internal application routing
                    +---------+---------+
                              |
                    +---------+---------+
                    |    bus_tier       |  <-- NATS (4223), WebSocket (9223)
                    +---------+---------+
                              |
                    +---------+---------+
                    |   data_tier      |  <-- Neo4j, SQLite/Supabase, Qdrant
                    +---------+---------+
```

In standalone (non-distributed) mode, all tiers except `api_tier` are set to `internal: true`, preventing external access to the message bus and data layers.

---

## Appendix: Quick Reference

### Environment Variable Summary

```bash
# TLS
NATS_TLS_ENABLED=true
NATS_TLS_CA=/app/nats-certs/ca.crt
NATS_TLS_CERT=/app/nats-certs/client.crt
NATS_TLS_KEY=/app/nats-certs/client.key

# JWT
SUPABASE_JWT_SECRET=your-jwt-secret-here
ENVIRONMENT=production

# Database
DB_BACKEND=supabase
SUPABASE_URL=http://supabase-kong:8000
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_DUAL_WRITE=false

# Distributed
NATS_URL=nats://nats:4222
TENSORZERO_URL=http://tensorzero-gateway:3030
OLLAMA_BASE_URL=http://host.docker.internal:11434
DOX_FRONTEND_ORIGIN=https://dox.yourdomain.com
```

### File Reference

| File | Description |
|------|-------------|
| `backend/nats-config/generate-certs.sh` | TLS certificate generation script |
| `backend/nats-config/nats.conf` | NATS config with mutual TLS (`verify: true`) |
| `backend/nats-config/nats.tls.conf` | NATS config with server TLS (`verify: false`) |
| `backend/app/utils/nats_tls.py` | Python TLS context factory (fail-closed) |
| `backend/app/auth/__init__.py` | Auth module public API |
| `backend/app/auth/jwt.py` | JWT validation, token parsing, FastAPI dependencies |
| `backend/app/api/routers/analysis.py` | User-scoped artifact access (`_get_user_artifact_ids`) |
| `backend/app/main.py` | Download endpoint with ownership enforcement |
| `backend/app/database_factory.py` | SQLite / Supabase / Dual-Write backend selection |
| `docker-compose.distributed.yml` | Distributed deployment overlay |
