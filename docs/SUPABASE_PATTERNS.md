# Supabase Integration Patterns

This document describes PMOVES-DoX integration with Supabase for PostgreSQL storage, JWT authentication, Row Level Security (RLS) policies, and the dual-write migration workflow.

## Table of Contents

1. [Overview](#overview)
2. [JWT Authentication Setup](#jwt-authentication-setup)
3. [RLS Policies](#rls-policies)
4. [Dual-Write Mode Configuration](#dual-write-mode-configuration)
5. [Migration Workflow](#migration-workflow)
6. [PostgREST Endpoints](#postgrest-endpoints)
7. [Cipher Memory Tables](#cipher-memory-tables)
8. [Troubleshooting](#troubleshooting)

---

## Overview

PMOVES-DoX supports two database backends:

- **SQLite (default)**: Local file-based storage for standalone deployments
- **Supabase**: Remote PostgreSQL with enhanced features for production/multi-tenant deployments

### Backend Selection

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Database Factory                             │
│                                                                  │
│   DB_BACKEND=sqlite ─────────▶ SQLite (ExtendedDatabase)       │
│                                 │                               │
│   DB_BACKEND=supabase ──────▶ Supabase (SupabaseDatabase)      │
│                                 │                               │
│   SUPABASE_DUAL_WRITE=true ─▶ DualDatabase (Both)              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_BACKEND` | Backend type: `sqlite` or `supabase` | `sqlite` |
| `SUPABASE_URL` | Supabase project URL | - |
| `SUPABASE_ANON_KEY` | Anonymous key (public) | - |
| `SUPABASE_SERVICE_KEY` | Service role key (admin) | - |
| `SUPABASE_JWT_SECRET` | JWT secret for PostgREST | - |
| `SUPABASE_SCHEMA` | PostgreSQL schema | `public` |
| `SUPABASE_DUAL_WRITE` | Enable dual-write mode | `false` |

---

## JWT Authentication Setup

### Generating JWT Secret

Use the included generator script:

```bash
cd tools
python gen_jwt.py --secret-length 64
```

Output:
```
Generated JWT Secret (64 chars):
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

PostgREST Configuration:
PGRST_JWT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Service Role Key (sample payload):
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Environment Configuration

Add to `.env.local`:

```bash
# =============================================================================
# Supabase / PostgREST JWT Configuration
# =============================================================================

# JWT secret for signing/verifying tokens
# CRITICAL: Keep this secret secure and never commit to version control
SUPABASE_JWT_SECRET=your-generated-secret-here

# Service role key (signed with JWT secret, role=service_role)
# This key has admin privileges, bypasses RLS
# IMPORTANT: Never commit actual keys to version control
SUPABASE_SERVICE_KEY=<your-service-role-jwt>

# Anonymous key (signed with JWT secret, role=anon)
# This key respects RLS policies
SUPABASE_ANON_KEY=<your-anon-jwt>
```

### JWT Payload Structure

#### Anonymous Key Payload

```json
{
  "role": "anon",
  "iss": "supabase",
  "iat": 1704067200,
  "exp": 1735689600
}
```

#### Service Role Key Payload

```json
{
  "role": "service_role",
  "iss": "supabase",
  "iat": 1704067200,
  "exp": 1735689600
}
```

#### Authenticated User Payload

```json
{
  "sub": "user-uuid",
  "role": "authenticated",
  "aud": "authenticated",
  "email": "user@example.com",
  "iss": "supabase",
  "iat": 1704067200,
  "exp": 1704153600
}
```

### PostgREST Configuration

In `docker-compose.yml`, the PostgREST service uses the JWT secret:

```yaml
supabase-rest:
  image: postgrest/postgrest:v11.1.0
  environment:
    PGRST_DB_URI: postgres://postgres:${POSTGRES_PASSWORD}@supabase-db:5432/postgres
    PGRST_DB_SCHEMA: public,storage,graphql_public
    PGRST_DB_ANON_ROLE: anon
    PGRST_JWT_SECRET: ${SUPABASE_JWT_SECRET}
    PGRST_OPENAPI_SERVER_PROXY_URI: http://localhost:54321/rest/v1
```

---

## RLS Policies

Row-Level Security (RLS) ensures data isolation between users and enforces access controls.

### Enable RLS on Tables

```sql
-- Enable RLS on all cipher tables
ALTER TABLE cipher_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_prefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills_registry ENABLE ROW LEVEL SECURITY;
```

### cipher_memory Policies

The `cipher_memory` table stores agent memory fragments with user-scoped access.

```sql
-- Table definition
CREATE TABLE cipher_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    category TEXT NOT NULL,
    content JSONB NOT NULL,
    context JSONB,
    embedding VECTOR(384),  -- pgvector for semantic search
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for performance
CREATE INDEX idx_cipher_memory_user ON cipher_memory(user_id);
CREATE INDEX idx_cipher_memory_category ON cipher_memory(category);
CREATE INDEX idx_cipher_memory_embedding ON cipher_memory USING ivfflat (embedding vector_cosine_ops);

-- RLS Policies
-- 1. Users can read their own memories
CREATE POLICY "Users read own memories" ON cipher_memory
    FOR SELECT
    USING (auth.uid() = user_id);

-- 2. Users can insert their own memories
CREATE POLICY "Users insert own memories" ON cipher_memory
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- 3. Users can update their own memories
CREATE POLICY "Users update own memories" ON cipher_memory
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 4. Users can delete their own memories
CREATE POLICY "Users delete own memories" ON cipher_memory
    FOR DELETE
    USING (auth.uid() = user_id);

-- 5. Service role bypasses RLS (for admin operations)
CREATE POLICY "Service role full access" ON cipher_memory
    FOR ALL
    USING (current_setting('request.jwt.claim.role', true) = 'service_role');
```

### user_prefs Policies

The `user_prefs` table stores user preference settings.

```sql
-- Table definition
CREATE TABLE user_prefs (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    preferences JSONB NOT NULL DEFAULT '{}',
    theme TEXT DEFAULT 'system',
    language TEXT DEFAULT 'en',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- RLS Policies
-- 1. Users can read their own preferences
CREATE POLICY "Users read own prefs" ON user_prefs
    FOR SELECT
    USING (auth.uid() = user_id);

-- 2. Users can insert their own preferences
CREATE POLICY "Users insert own prefs" ON user_prefs
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- 3. Users can update their own preferences
CREATE POLICY "Users update own prefs" ON user_prefs
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 4. Service role full access
CREATE POLICY "Service role prefs access" ON user_prefs
    FOR ALL
    USING (current_setting('request.jwt.claim.role', true) = 'service_role');
```

### skills_registry Policies

The `skills_registry` table stores available agent skills/capabilities.

```sql
-- Table definition
CREATE TABLE skills_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    parameters JSONB NOT NULL DEFAULT '{}',
    workflow_def JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for performance
CREATE INDEX idx_skills_name ON skills_registry(name);
CREATE INDEX idx_skills_enabled ON skills_registry(enabled);

-- RLS Policies
-- 1. All users can read enabled skills
CREATE POLICY "Users read enabled skills" ON skills_registry
    FOR SELECT
    USING (enabled = true);

-- 2. Only admins/service role can insert skills
CREATE POLICY "Admins insert skills" ON skills_registry
    FOR INSERT
    WITH CHECK (current_setting('request.jwt.claim.role', true) = 'service_role');

-- 3. Only admins/service role can update skills
CREATE POLICY "Admins update skills" ON skills_registry
    FOR UPDATE
    USING (current_setting('request.jwt.claim.role', true) = 'service_role');

-- 4. Only admins/service role can delete skills
CREATE POLICY "Admins delete skills" ON skills_registry
    FOR DELETE
    USING (current_setting('request.jwt.claim.role', true) = 'service_role');
```

### Testing RLS Policies

```sql
-- Test as anonymous user
SET request.jwt.claims = '{"role": "anon"}';
SELECT * FROM cipher_memory;  -- Should return empty (no access)

-- Test as authenticated user
SET request.jwt.claims = '{"role": "authenticated", "sub": "user-uuid"}';
SELECT * FROM cipher_memory;  -- Returns user's memories only

-- Test as service role
SET request.jwt.claims = '{"role": "service_role"}';
SELECT * FROM cipher_memory;  -- Returns all memories
```

---

## Dual-Write Mode Configuration

Dual-write mode enables simultaneous writes to both SQLite and Supabase during migration.

### Enabling Dual-Write

```bash
# .env.local
DB_BACKEND=sqlite           # Primary backend (reads come from here)
SUPABASE_DUAL_WRITE=true    # Enable dual-write to Supabase
SUPABASE_URL=http://localhost:54321
SUPABASE_SERVICE_KEY=your-service-key
```

### How Dual-Write Works

```python
# backend/app/database_factory.py

class DualDatabase:
    """Delegate writes to both databases, reads from primary."""

    def __init__(self, primary: Any, secondary: Any) -> None:
        self.primary = primary
        self.secondary = secondary

    def __getattr__(self, name: str):
        attr = getattr(self.primary, name)
        if callable(attr) and name in WRITE_METHODS:
            def wrapper(*args, **kwargs):
                # Execute on primary
                result = attr(*args, **kwargs)
                # Mirror to secondary (non-blocking on failure)
                secondary_method = getattr(self.secondary, name, None)
                if callable(secondary_method):
                    try:
                        secondary_method(*args, **kwargs)
                    except Exception as exc:
                        LOGGER.warning("Dual-write secondary failure: %s", exc)
                return result
            return wrapper
        return attr
```

### Write Methods Subject to Dual-Write

```python
WRITE_METHODS = {
    "add_artifact",
    "add_fact",
    "add_evidence",
    "add_document",
    "add_section",
    "add_table",
    "add_api",
    "add_log",
    "add_tag",
    "save_tag_prompt",
    "reset",
    "reset_search_chunks",
    "store_search_chunks",
    "store_entities",
    "store_structure",
    "store_metric_hits",
    "store_summary",
    "add_memory",        # Cipher
    "set_user_pref",     # Cipher
    "register_skill",    # Cipher
    "update_skill",      # Cipher
}
```

### Dual-Write Behavior

| Scenario | Primary | Secondary | Result |
|----------|---------|-----------|--------|
| Both succeed | SQLite writes | Supabase writes | Success |
| Primary fails | Error raised | Not attempted | Failure |
| Secondary fails | SQLite writes | Warning logged | Success |
| Secondary unavailable | SQLite writes | Warning logged | Success |

---

## Migration Workflow

### Phase 1: Preparation

1. **Enable dual-write mode** to capture new data in both systems:

```bash
# .env.local
DB_BACKEND=sqlite
SUPABASE_DUAL_WRITE=true
```

2. **Create Supabase schema** (if not using managed Supabase):

```bash
# Apply migrations
psql -h localhost -p 5432 -U postgres -d postgres -f migrations/001_initial_schema.sql
psql -h localhost -p 5432 -U postgres -d postgres -f migrations/002_cipher_tables.sql
```

### Phase 2: Data Migration

1. **Export existing SQLite data**:

```python
# scripts/export_sqlite.py
import sqlite3
import json

conn = sqlite3.connect('backend/db.sqlite3')
cursor = conn.cursor()

# Export artifacts
cursor.execute("SELECT * FROM artifact")
artifacts = [dict(row) for row in cursor.fetchall()]
with open('export/artifacts.json', 'w') as f:
    json.dump(artifacts, f)

# Repeat for other tables...
```

2. **Import to Supabase**:

```python
# scripts/import_supabase.py
from supabase import create_client
import json

client = create_client(url, service_key)

with open('export/artifacts.json') as f:
    artifacts = json.load(f)

for artifact in artifacts:
    client.table('artifacts').upsert(artifact).execute()
```

3. **Verify data consistency**:

```sql
-- Compare counts
SELECT
    (SELECT COUNT(*) FROM artifacts) as supabase_count,
    -- Compare with SQLite count
;
```

### Phase 3: Cutover

1. **Switch primary to Supabase**:

```bash
# .env.local
DB_BACKEND=supabase
SUPABASE_DUAL_WRITE=false  # Disable dual-write after migration
```

2. **Restart services**:

```bash
docker compose down
docker compose up -d
```

3. **Verify functionality**:

```bash
# Health check
curl http://localhost:8484/health

# Test operations
curl http://localhost:8484/artifacts
```

### Phase 4: Cleanup

1. **Archive SQLite database**:

```bash
mv backend/db.sqlite3 backend/db.sqlite3.backup
```

2. **Remove dual-write configuration**:

```bash
# .env.local
# SUPABASE_DUAL_WRITE=false  # Remove or comment out
```

---

## PostgREST Endpoints

PostgREST exposes your PostgreSQL tables as RESTful API endpoints.

### Base URL

```
http://localhost:54321/rest/v1
```

### Authentication

Include JWT token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer ${SUPABASE_ANON_KEY}" \
     -H "apikey: ${SUPABASE_ANON_KEY}" \
     http://localhost:54321/rest/v1/artifacts
```

### Table Endpoints

#### Artifacts

```bash
# List all artifacts
GET /rest/v1/artifacts

# Get single artifact
GET /rest/v1/artifacts?id=eq.{uuid}

# Insert artifact
POST /rest/v1/artifacts
Content-Type: application/json
{"id": "uuid", "filename": "doc.pdf", ...}

# Update artifact
PATCH /rest/v1/artifacts?id=eq.{uuid}
Content-Type: application/json
{"status": "processed"}

# Delete artifact
DELETE /rest/v1/artifacts?id=eq.{uuid}
```

#### Facts

```bash
# List facts for artifact
GET /rest/v1/facts?artifact_id=eq.{uuid}

# Search facts (full-text)
GET /rest/v1/facts?content=fts.revenue
```

#### Evidence

```bash
# Get evidence chunks
GET /rest/v1/evidence?select=id,preview,content_type

# Filter by type
GET /rest/v1/evidence?content_type=eq.table
```

#### Cipher Memory

```bash
# Get user memories
GET /rest/v1/cipher_memory?user_id=eq.{uuid}

# Search by category
GET /rest/v1/cipher_memory?category=eq.conversation

# Insert memory
POST /rest/v1/cipher_memory
Content-Type: application/json
{
  "user_id": "uuid",
  "category": "insight",
  "content": {"text": "User prefers concise responses"},
  "context": {"source": "chat"}
}
```

### Query Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equals | `?id=eq.123` |
| `neq` | Not equals | `?status=neq.deleted` |
| `gt`, `gte` | Greater than | `?count=gte.10` |
| `lt`, `lte` | Less than | `?created_at=lt.2024-01-01` |
| `like` | Pattern match | `?filename=like.*pdf` |
| `ilike` | Case-insensitive pattern | `?name=ilike.*apple*` |
| `in` | In list | `?type=in.(pdf,docx)` |
| `is` | NULL check | `?deleted_at=is.null` |
| `fts` | Full-text search | `?content=fts.revenue` |

### Pagination

```bash
# Limit results
GET /rest/v1/artifacts?limit=10

# Offset for pagination
GET /rest/v1/artifacts?limit=10&offset=20

# Order by field
GET /rest/v1/artifacts?order=created_at.desc
```

### Selecting Fields

```bash
# Select specific columns
GET /rest/v1/artifacts?select=id,filename,status

# Include related data (foreign key)
GET /rest/v1/facts?select=*,artifact:artifacts(filename)
```

---

## Cipher Memory Tables

### Schema Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       Cipher Memory Schema                       │
│                                                                  │
│  ┌────────────────┐     ┌────────────────┐                      │
│  │ cipher_memory  │     │  user_prefs    │                      │
│  │ ─────────────  │     │ ────────────── │                      │
│  │ id (PK)        │     │ user_id (PK)   │                      │
│  │ user_id (FK)   │     │ preferences    │                      │
│  │ category       │     │ theme          │                      │
│  │ content (JSONB)│     │ language       │                      │
│  │ context (JSONB)│     │ updated_at     │                      │
│  │ embedding      │     └────────────────┘                      │
│  │ created_at     │                                              │
│  └────────────────┘     ┌────────────────┐                      │
│                         │ skills_registry │                      │
│                         │ ─────────────── │                      │
│                         │ id (PK)         │                      │
│                         │ name (UNIQUE)   │                      │
│                         │ description     │                      │
│                         │ parameters      │                      │
│                         │ workflow_def    │                      │
│                         │ enabled         │                      │
│                         │ created_by (FK) │                      │
│                         └────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### Python API Usage

```python
from app.database_supabase import SupabaseDatabase

db = SupabaseDatabase()

# Add memory
memory_id = db.add_memory(
    category="insight",
    content={"text": "User prefers dark mode", "confidence": 0.95},
    context={"source": "settings_interaction", "timestamp": "2024-01-15"}
)

# Search memories
memories = db.search_memory(
    category="insight",
    limit=10,
    q="dark mode"
)

# Get user preferences
prefs = db.get_user_prefs(user_id="user-uuid")

# Set user preference
db.set_user_pref(
    user_id="user-uuid",
    key="default_model",
    value="gpt-4"
)

# Register skill
skill_id = db.register_skill(
    name="web_search",
    description="Search the web for information",
    parameters={"query": {"type": "string", "required": True}},
    workflow_def={"steps": [{"tool": "browser", "action": "search"}]},
    enabled=True
)

# List skills
skills = db.list_skills(enabled_only=True)
```

---

## Troubleshooting

### Cannot Connect to Supabase

**Symptoms:**
- "Supabase credentials not configured" error
- Connection timeouts

**Solutions:**

1. Verify environment variables:
```bash
docker exec pmoves-dox-backend env | grep SUPABASE
```

2. Test PostgREST connectivity:
```bash
curl http://localhost:54321/rest/v1/
```

3. Check PostgREST logs:
```bash
docker logs supabase-rest
```

### RLS Policy Blocking Access

**Symptoms:**
- Empty results when data exists
- 403 Forbidden errors

**Solutions:**

1. Test with service role key (bypasses RLS):
```bash
curl -H "Authorization: Bearer ${SUPABASE_SERVICE_KEY}" \
     http://localhost:54321/rest/v1/cipher_memory
```

2. Check RLS is enabled:
```sql
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public';
```

3. Debug policy evaluation:
```sql
SET request.jwt.claims = '{"role": "authenticated", "sub": "user-uuid"}';
SELECT * FROM cipher_memory;
```

### Dual-Write Failures

**Symptoms:**
- "Dual-write secondary failure" in logs
- Data inconsistency between SQLite and Supabase

**Solutions:**

1. Check Supabase connectivity:
```python
from app.database_supabase import SupabaseDatabase
db = SupabaseDatabase()
# If this fails, connection issue
```

2. Verify schema compatibility:
```sql
-- Ensure columns match between SQLite and Supabase
\d artifacts
```

3. Review error logs:
```bash
docker logs pmoves-dox-backend 2>&1 | grep "Dual-write"
```

### JWT Token Invalid

**Symptoms:**
- "Invalid JWT" errors
- 401 Unauthorized responses

**Solutions:**

1. Verify JWT secret matches:
```bash
# Check PostgREST config
docker exec supabase-rest env | grep PGRST_JWT_SECRET

# Check key generation
python tools/gen_jwt.py --verify your-token
```

2. Check token expiration:
```python
import jwt
token = "your-token"
decoded = jwt.decode(token, options={"verify_signature": False})
print(decoded["exp"])  # Expiration timestamp
```

3. Regenerate keys with correct secret:
```bash
python tools/gen_jwt.py --secret your-jwt-secret
```

---

## References

- [Supabase Documentation](https://supabase.com/docs)
- [PostgREST Documentation](https://postgrest.org/en/stable/)
- [PostgreSQL RLS Guide](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [DOCKING_GUIDE.md](./DOCKING_GUIDE.md) - Integration with parent PMOVES.AI
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview
- [database_factory.py](../backend/app/database_factory.py) - Backend selection logic
- [database_supabase.py](../backend/app/database_supabase.py) - Supabase implementation
