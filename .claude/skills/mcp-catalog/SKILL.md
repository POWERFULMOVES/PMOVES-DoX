---
name: MCP Catalog Explorer
description: List, check health, and call tools from the PMOVES-BoTZ MCP server catalog. Use when user mentions "list mcp servers", "check mcp health", "call mcp tool", "mcp catalog", or "show mcp servers".
---

# MCP Catalog Explorer Skill

Discover and interact with MCP servers registered in the PMOVES-BoTZ catalog.

## Overview

This skill provides tools to:

- **List MCP Servers**: View all registered MCP servers from the catalog
- **Health Check**: Verify if an MCP server is running and responsive
- **Call Tool**: Execute a tool on a specific MCP server

## Skill Structure

```
.claude/skills/mcp-catalog/
├── SKILL.md                     # This file
├── tools/
│   ├── list_servers.py          # Parse and list catalog entries
│   ├── health_check.py          # Check server health status
│   └── call_tool.py             # Route tool calls to servers
└── cookbook/
    └── discovery.md             # Usage examples and workflows
```

## Trigger Phrases

| Phrase | Action |
|--------|--------|
| "list mcp servers" | Run `tools/list_servers.py` |
| "show mcp catalog" | Run `tools/list_servers.py` |
| "check mcp health" | Run `tools/health_check.py --server <name>` |
| "is [server] running" | Run `tools/health_check.py --server <name>` |
| "call mcp tool" | Run `tools/call_tool.py --server <name> --tool <tool>` |
| "execute [tool] on [server]" | Run `tools/call_tool.py --server <name> --tool <tool>` |

## Tools

### list_servers.py

Lists all MCP servers from the BoTZ catalog.

**Usage:**
```bash
python tools/list_servers.py
python tools/list_servers.py --format json
python tools/list_servers.py --filter sse  # Only SSE transport
python tools/list_servers.py --filter stdio  # Only stdio transport
```

**Output:**
```
MCP Server Catalog (7 servers)
================================================================================

docling
  Transport: sse
  URL:       http://localhost:3020/sse
  Description: Document processing and conversion

cipher-memory
  Transport: stdio
  Command:   docker exec -i pmz-cipher python3 memory_shim/app_cipher_memory.py
  Description: Persistent memory and reasoning

...
```

### health_check.py

Checks the health status of an MCP server.

**Usage:**
```bash
python tools/health_check.py --server docling
python tools/health_check.py --server cipher-memory
python tools/health_check.py --all  # Check all servers
```

**Output:**
```
Health Check: docling
================================================================================
Status: HEALTHY
Transport: SSE
URL: http://localhost:3020/sse
Response Time: 45ms
```

### call_tool.py

Calls a tool on a specific MCP server.

**Usage:**
```bash
python tools/call_tool.py --server docling --tool convert --args '{"file": "doc.pdf"}'
python tools/call_tool.py --server cipher-memory --tool store_memory --args '{"key": "test", "content": "value"}'
```

**Output:**
```
Tool Call: docling.convert
================================================================================
Status: SUCCESS
Result: {"output": "doc.md", "pages": 5}
```

---

## Cookbook

For detailed examples and workflows, see [cookbook/discovery.md](cookbook/discovery.md).

### Quick Examples

**List all servers:**
```bash
cd .claude/skills/mcp-catalog
python tools/list_servers.py
```

**Check if Docling is healthy:**
```bash
python tools/health_check.py --server docling
```

**Check all servers at once:**
```bash
python tools/health_check.py --all
```

---

## Catalog Location

The skill reads the MCP catalog from:
```
external/PMOVES-BoTZ/core/mcp/catalog.yml
```

This YAML file defines all registered MCP servers with their:
- Name and description
- Transport type (SSE or stdio)
- URL (for SSE) or command (for stdio)
- Required environment variables

---

## Server Types

### SSE Servers

HTTP-based servers using Server-Sent Events:
- **docling**: Document processing (Port 3020)
- **e2b**: Code execution sandbox (Port 7071)
- **vl-sentinel**: Vision-language processing (Port 7072)

Health check: HTTP GET to `/health` endpoint

### stdio Servers

Docker-based servers using standard I/O:
- **cipher-memory**: Persistent memory system
- **postman**: API testing
- **n8n-agent**: Workflow automation
- **hostinger**: VPS/DNS management

Health check: Verify container is running via `docker ps`

---

## Quick Reference

| Server | Transport | Health Endpoint |
|--------|-----------|-----------------|
| docling | sse | http://localhost:3020/health |
| e2b | sse | http://localhost:7071/health |
| vl-sentinel | sse | http://localhost:7072/health |
| cipher-memory | stdio | docker ps |
| postman | stdio | docker ps |
| n8n-agent | stdio | docker ps |
| hostinger | stdio | docker ps |

---

## Related Files

- [cookbook/discovery.md](cookbook/discovery.md) - Detailed usage examples
- [tools/list_servers.py](tools/list_servers.py) - Server listing tool
- [tools/health_check.py](tools/health_check.py) - Health check tool
- [tools/call_tool.py](tools/call_tool.py) - Tool execution
