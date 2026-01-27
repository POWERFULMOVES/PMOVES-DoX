#!/usr/bin/env python3
"""List MCP servers from the PMOVES-BoTZ catalog.

Usage:
    python list_servers.py                  # List all servers
    python list_servers.py --format json    # Output as JSON
    python list_servers.py --filter sse     # Only SSE transport
    python list_servers.py --filter stdio   # Only stdio transport
"""

import argparse
import json
import sys
from pathlib import Path

import yaml


def find_catalog() -> Path:
    """Find the MCP catalog file.

    Searches in order:
    1. external/PMOVES-BoTZ/core/mcp/catalog.yml (DoX repo)
    2. core/mcp/catalog.yml (BoTZ repo)
    3. ../../../PMOVES-BoTZ/core/mcp/catalog.yml (sibling)

    Returns:
        Path to catalog.yml

    Raises:
        FileNotFoundError: If catalog not found
    """
    # Start from this script's location
    script_dir = Path(__file__).resolve().parent

    # Possible locations relative to different contexts
    candidates = [
        script_dir.parents[4] / "external" / "PMOVES-BoTZ" / "core" / "mcp" / "catalog.yml",
        script_dir.parents[4] / "PMOVES-BoTZ" / "core" / "mcp" / "catalog.yml",
        Path.cwd() / "external" / "PMOVES-BoTZ" / "core" / "mcp" / "catalog.yml",
        Path.cwd() / "core" / "mcp" / "catalog.yml",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "MCP catalog not found. Searched:\n" + "\n".join(f"  - {c}" for c in candidates)
    )


def load_catalog(path: Path) -> dict:
    """Load and parse the MCP catalog YAML.

    Args:
        path: Path to catalog.yml

    Returns:
        Parsed catalog dictionary
    """
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def format_server_text(name: str, config: dict) -> str:
    """Format a single server entry as human-readable text.

    Args:
        name: Server name
        config: Server configuration dict

    Returns:
        Formatted text block
    """
    lines = [name]

    if "url" in config:
        transport = config.get("transport", "sse")
        lines.append(f"  Transport: {transport}")
        lines.append(f"  URL:       {config['url']}")
    elif "command" in config:
        lines.append("  Transport: stdio")
        args = config.get("args", [])
        cmd = f"{config['command']} {' '.join(args)}"
        lines.append(f"  Command:   {cmd}")

    if "env" in config:
        env_vars = list(config["env"].keys())
        lines.append(f"  Env vars:  {', '.join(env_vars)}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="List MCP servers from catalog")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--filter",
        choices=["sse", "stdio"],
        help="Filter by transport type",
    )
    args = parser.parse_args()

    try:
        catalog_path = find_catalog()
        catalog = load_catalog(catalog_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing catalog: {e}", file=sys.stderr)
        sys.exit(1)

    servers = catalog.get("mcpServers", {})

    # Apply filter if specified
    if args.filter:
        filtered = {}
        for name, config in servers.items():
            if args.filter == "sse" and "url" in config:
                filtered[name] = config
            elif args.filter == "stdio" and "command" in config:
                filtered[name] = config
        servers = filtered

    # Output
    if args.format == "json":
        output = {
            "catalog_path": str(catalog_path),
            "server_count": len(servers),
            "servers": servers,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"MCP Server Catalog ({len(servers)} servers)")
        print(f"Source: {catalog_path}")
        print("=" * 80)
        print()
        for name, config in servers.items():
            print(format_server_text(name, config))
            print()


if __name__ == "__main__":
    main()
