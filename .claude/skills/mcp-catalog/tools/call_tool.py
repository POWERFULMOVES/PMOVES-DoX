#!/usr/bin/env python3
"""Call a tool on an MCP server.

Usage:
    python call_tool.py --server docling --tool list_tools
    python call_tool.py --server cipher-memory --tool store_memory --args '{"key": "test"}'
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


def find_catalog() -> Path:
    """Find the MCP catalog file."""
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir.parents[4] / "external" / "PMOVES-BoTZ" / "core" / "mcp" / "catalog.yml",
        script_dir.parents[4] / "PMOVES-BoTZ" / "core" / "mcp" / "catalog.yml",
        Path.cwd() / "external" / "PMOVES-BoTZ" / "core" / "mcp" / "catalog.yml",
        Path.cwd() / "core" / "mcp" / "catalog.yml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("MCP catalog not found")


def load_catalog(path: Path) -> dict:
    """Load catalog YAML."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def call_sse_tool(
    url: str, tool_name: str, args: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Call a tool on an SSE MCP server.

    Args:
        url: Server SSE URL
        tool_name: Name of the tool to call
        args: Tool arguments

    Returns:
        Tool result dict
    """
    if not HAS_HTTPX:
        return {
            "status": "ERROR",
            "error": "httpx not installed (pip install httpx)",
        }

    # SSE servers typically have a tools endpoint
    # Convert SSE URL to tools endpoint
    base_url = url.replace("/sse", "")
    tools_url = f"{base_url}/tools/{tool_name}"

    try:
        with httpx.Client(timeout=30.0) as client:
            if args:
                resp = client.post(tools_url, json=args)
            else:
                resp = client.post(tools_url)

            if resp.status_code == 200:
                try:
                    result = resp.json()
                except json.JSONDecodeError:
                    result = {"text": resp.text}
                return {"status": "SUCCESS", "result": result}
            else:
                return {
                    "status": "ERROR",
                    "http_status": resp.status_code,
                    "error": resp.text[:500],
                }
    except httpx.ConnectError:
        return {"status": "ERROR", "error": "Connection refused"}
    except httpx.TimeoutException:
        return {"status": "ERROR", "error": "Request timed out"}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def call_stdio_tool(
    command: str,
    args: list,
    env: dict,
    tool_name: str,
    tool_args: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Call a tool on a stdio MCP server.

    Args:
        command: Base command (e.g., 'docker')
        args: Command arguments
        env: Environment variables
        tool_name: Name of the tool to call
        tool_args: Tool arguments

    Returns:
        Tool result dict
    """
    # Build MCP JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": tool_args or {}},
    }

    # Prepare environment
    import os

    full_env = os.environ.copy()
    for k, v in env.items():
        # Expand environment variable references
        if v.startswith("${") and v.endswith("}"):
            var_name = v[2:-1].split(":-")[0]
            full_env[k] = os.environ.get(var_name, "")
        else:
            full_env[k] = v

    try:
        full_cmd = [command] + args
        result = subprocess.run(
            full_cmd,
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=30,
            env=full_env,
        )

        if result.returncode != 0:
            return {
                "status": "ERROR",
                "error": result.stderr.strip() or "Command failed",
                "exit_code": result.returncode,
            }

        try:
            response = json.loads(result.stdout)
            if "result" in response:
                return {"status": "SUCCESS", "result": response["result"]}
            elif "error" in response:
                return {"status": "ERROR", "error": response["error"]}
            else:
                return {"status": "SUCCESS", "result": response}
        except json.JSONDecodeError:
            return {"status": "SUCCESS", "result": {"text": result.stdout}}

    except subprocess.TimeoutExpired:
        return {"status": "ERROR", "error": "Command timed out"}
    except FileNotFoundError:
        return {"status": "ERROR", "error": f"Command not found: {command}"}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Call MCP server tool")
    parser.add_argument("--server", required=True, help="Server name from catalog")
    parser.add_argument("--tool", required=True, help="Tool name to call")
    parser.add_argument("--args", help="Tool arguments as JSON string")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    args = parser.parse_args()

    # Parse tool arguments
    tool_args = None
    if args.args:
        try:
            tool_args = json.loads(args.args)
        except json.JSONDecodeError as e:
            print(f"Error parsing --args JSON: {e}", file=sys.stderr)
            sys.exit(1)

    # Load catalog
    try:
        catalog = load_catalog(find_catalog())
    except Exception as e:
        print(f"Error loading catalog: {e}", file=sys.stderr)
        sys.exit(1)

    servers = catalog.get("mcpServers", {})
    if args.server not in servers:
        print(f"Error: Server '{args.server}' not found in catalog")
        sys.exit(1)

    config = servers[args.server]

    # Call the tool
    if "url" in config:
        result = call_sse_tool(config["url"], args.tool, tool_args)
    elif "command" in config:
        result = call_stdio_tool(
            config["command"],
            config.get("args", []),
            config.get("env", {}),
            args.tool,
            tool_args,
        )
    else:
        result = {"status": "ERROR", "error": "Unknown server type"}

    # Output
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"Tool Call: {args.server}.{args.tool}")
        print("=" * 60)
        print(f"Status: {result['status']}")
        if "result" in result:
            print(f"Result: {json.dumps(result['result'], indent=2)}")
        if "error" in result:
            print(f"Error:  {result['error']}")


if __name__ == "__main__":
    main()
