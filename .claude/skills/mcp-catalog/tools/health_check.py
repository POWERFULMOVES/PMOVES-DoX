#!/usr/bin/env python3
"""Health check for MCP servers.

Usage:
    python health_check.py --server docling     # Check specific server
    python health_check.py --all                # Check all servers
    python health_check.py --all --format json  # JSON output
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urlparse, urlunparse

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


def derive_health_url(sse_url: str) -> str:
    """Derive the health endpoint URL from an SSE URL using proper URL parsing."""
    parsed = urlparse(sse_url)
    # Normalize path by stripping trailing slashes to avoid double slashes
    path = parsed.path.rstrip("/")
    if path.endswith("/sse"):
        path = path[:-4]
    elif path == "/sse" or path == "":
        path = ""
    new_path = f"{path}/health" if path else "/health"
    return urlunparse(parsed._replace(path=new_path))


def check_sse_server(url: str, timeout: float = 5.0) -> Dict[str, Any]:
    """Check health of an SSE server via HTTP.

    Args:
        url: Server URL (e.g., http://localhost:3020/sse)
        timeout: Request timeout in seconds

    Returns:
        Health check result dict
    """
    if not HAS_HTTPX:
        return {
            "status": "UNKNOWN",
            "error": "httpx not installed (pip install httpx)",
        }

    # Derive health endpoint from SSE URL using proper URL parsing
    health_url = derive_health_url(url)

    start = time.time()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(health_url)
            elapsed = (time.time() - start) * 1000

            if resp.status_code == 200:
                return {
                    "status": "HEALTHY",
                    "response_time_ms": round(elapsed, 1),
                    "health_url": health_url,
                }
            else:
                return {
                    "status": "UNHEALTHY",
                    "http_status": resp.status_code,
                    "response_time_ms": round(elapsed, 1),
                    "health_url": health_url,
                }
    except httpx.ConnectError:
        return {"status": "UNREACHABLE", "error": "Connection refused", "health_url": health_url}
    except httpx.TimeoutException:
        return {"status": "TIMEOUT", "error": f"Timeout after {timeout}s", "health_url": health_url}
    except Exception as e:
        return {"status": "ERROR", "error": str(e), "health_url": health_url}


def check_stdio_server(container_name: str) -> Dict[str, Any]:
    """Check health of a stdio server via docker ps.

    Args:
        container_name: Docker container name (e.g., pmz-cipher)

    Returns:
        Health check result dict
    """
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return {"status": "ERROR", "error": result.stderr.strip() or "docker ps failed"}

        status_line = result.stdout.strip()
        if not status_line:
            return {"status": "NOT_RUNNING", "container": container_name}

        if "Up" in status_line:
            return {
                "status": "HEALTHY",
                "container": container_name,
                "docker_status": status_line,
            }
        else:
            return {
                "status": "UNHEALTHY",
                "container": container_name,
                "docker_status": status_line,
            }
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "error": "docker ps timed out"}
    except FileNotFoundError:
        return {"status": "ERROR", "error": "docker command not found"}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def extract_container_name(args: list) -> str:
    """Extract container name from docker exec args.

    Args:
        args: List of command arguments

    Returns:
        Container name or 'unknown'
    """
    # Pattern: ["exec", "-i", "container-name", ...]
    for i, arg in enumerate(args):
        if arg in ("exec", "-i", "-it", "-t"):
            continue
        if not arg.startswith("-"):
            return arg
    return "unknown"


def check_server(name: str, config: dict) -> Dict[str, Any]:
    """Check health of a single server.

    Args:
        name: Server name
        config: Server configuration

    Returns:
        Health check result with server name
    """
    result = {"server": name}

    if "url" in config:
        result["transport"] = "sse"
        result["url"] = config["url"]
        result.update(check_sse_server(config["url"]))
    elif "command" in config:
        result["transport"] = "stdio"
        args = config.get("args", [])
        container = extract_container_name(args)
        result["container"] = container
        result.update(check_stdio_server(container))
    else:
        result["status"] = "UNKNOWN"
        result["error"] = "No url or command in config"

    return result


def main():
    parser = argparse.ArgumentParser(description="Health check MCP servers")
    parser.add_argument("--server", help="Check specific server by name")
    parser.add_argument("--all", action="store_true", help="Check all servers")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    args = parser.parse_args()

    if not args.server and not args.all:
        parser.print_help()
        print("\nError: Specify --server <name> or --all")
        sys.exit(1)

    try:
        catalog = load_catalog(find_catalog())
    except Exception as e:
        print(f"Error loading catalog: {e}", file=sys.stderr)
        sys.exit(1)

    servers = catalog.get("mcpServers", {})
    results = []

    if args.server:
        if args.server not in servers:
            print(f"Error: Server '{args.server}' not found in catalog")
            sys.exit(1)
        results.append(check_server(args.server, servers[args.server]))
    else:
        for name, config in servers.items():
            results.append(check_server(name, config))

    # Output
    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"Health Check: {r['server']}")
            print("=" * 60)
            print(f"Status:    {r['status']}")
            print(f"Transport: {r.get('transport', 'unknown')}")
            if "url" in r:
                print(f"URL:       {r['url']}")
            if "container" in r:
                print(f"Container: {r['container']}")
            if "response_time_ms" in r:
                print(f"Response:  {r['response_time_ms']}ms")
            if "error" in r:
                print(f"Error:     {r['error']}")
            print()


if __name__ == "__main__":
    main()
