# MCP Catalog Discovery Cookbook

This cookbook provides examples and workflows for discovering and interacting with MCP servers in the PMOVES ecosystem.

## Prerequisites

```bash
# Install dependencies
pip install pyyaml httpx
```

## Workflows

### 1. List All Available Servers

```bash
cd PMOVES-DoX/.claude/skills/mcp-catalog
python tools/list_servers.py
```

**Expected Output:**
```
MCP Server Catalog (7 servers)
Source: external/PMOVES-BoTZ/core/mcp/catalog.yml
================================================================================

docling
  Transport: sse
  URL:       http://localhost:3020/sse

e2b
  Transport: sse
  URL:       http://localhost:7071/sse

vl-sentinel
  Transport: sse
  URL:       http://localhost:7072/sse

cipher-memory
  Transport: stdio
  Command:   docker exec -i pmz-cipher python3 memory_shim/app_cipher_memory.py
  Env vars:  VENICE_API_KEY

postman
  Transport: stdio
  Command:   docker exec -i pmz-postman npx @postman/postman-mcp-server@latest --full
  Env vars:  POSTMAN_API_KEY

n8n-agent
  Transport: stdio
  Command:   docker exec -i pmz-n8n python app_n8n_agent.py
  Env vars:  N8N_API_KEY, N8N_API_URL, TENSORZERO_BASE_URL

hostinger
  Transport: stdio
  Command:   docker exec -i pmz-hostinger hostinger-api-mcp
  Env vars:  API_TOKEN
```

### 2. Check Server Health

**Single Server:**
```bash
python tools/health_check.py --server docling
```

**All Servers:**
```bash
python tools/health_check.py --all
```

**JSON Output for Scripting:**
```bash
python tools/health_check.py --all --format json | jq '.[] | select(.status == "HEALTHY")'
```

### 3. Filter by Transport Type

**SSE Servers Only (HTTP-based):**
```bash
python tools/list_servers.py --filter sse
```

**stdio Servers Only (Docker-based):**
```bash
python tools/list_servers.py --filter stdio
```

### 4. Call a Tool

**List tools on Docling server:**
```bash
python tools/call_tool.py --server docling --tool list_tools
```

**Store memory in Cipher:**
```bash
python tools/call_tool.py --server cipher-memory --tool store_memory \
  --args '{"key": "project-context", "content": "This is the main project for document analysis"}'
```

**Execute n8n workflow:**
```bash
python tools/call_tool.py --server n8n-agent --tool execute_workflow \
  --args '{"workflow_id": "abc123", "data": {"input": "test"}}'
```

## Integration Examples

### Python Integration

```python
import subprocess
import json
from pathlib import Path

def list_mcp_servers():
    """Get list of MCP servers as Python dict."""
    result = subprocess.run(
        ["python", "tools/list_servers.py", "--format", "json"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    return json.loads(result.stdout)

def check_server_health(server_name: str) -> dict:
    """Check health of a specific server."""
    result = subprocess.run(
        ["python", "tools/health_check.py", "--server", server_name, "--format", "json"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    return json.loads(result.stdout)[0]

def call_mcp_tool(server: str, tool: str, args: dict = None) -> dict:
    """Call a tool on an MCP server."""
    cmd = ["python", "tools/call_tool.py", "--server", server, "--tool", tool, "--format", "json"]
    if args:
        cmd.extend(["--args", json.dumps(args)])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    return json.loads(result.stdout)
```

### Claude Code Integration

When working with Claude Code, you can use these natural language triggers:

- "list mcp servers" → Shows all available MCP servers
- "check mcp health for docling" → Checks if Docling is running
- "call store_memory on cipher-memory" → Executes a tool call

## Troubleshooting

### Server Not Found

```
Error: MCP catalog not found
```

**Solution:** Ensure the PMOVES-BoTZ submodule is initialized:
```bash
git submodule update --init --recursive
```

### Connection Refused

```
Status: UNREACHABLE
Error: Connection refused
```

**Solution:** Start the Docker services:
```bash
docker compose up -d
```

### Permission Denied

```
Error: docker ps failed
```

**Solution:** Ensure Docker is running and you have permission:
```bash
# Linux/Mac
sudo usermod -aG docker $USER

# Or run with sudo
sudo python tools/health_check.py --all
```

### Missing Dependencies

```
Error: httpx not installed
```

**Solution:** Install the HTTP client:
```bash
pip install httpx
```

## Architecture Notes

### SSE Transport

SSE (Server-Sent Events) servers run as HTTP services:
- Port 3020: Docling (document processing)
- Port 7071: E2B (code execution)
- Port 7072: VL Sentinel (vision-language)

Health is checked via HTTP GET to `/health` endpoint.

### stdio Transport

stdio servers run inside Docker containers:
- Commands are executed via `docker exec`
- Communication uses JSON-RPC over stdin/stdout
- Health is checked via `docker ps`

### Environment Variables

Many servers require API keys:
- `VENICE_API_KEY` → Cipher Memory
- `POSTMAN_API_KEY` → Postman
- `N8N_API_KEY` → n8n
- `HOSTINGER_API_KEY` → Hostinger

Set these in your `.env` file or export them:
```bash
export VENICE_API_KEY=your-key-here
```
