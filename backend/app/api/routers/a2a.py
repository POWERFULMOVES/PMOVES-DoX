"""A2A (Agent-to-Agent) protocol router for agent discovery.

This router implements the A2A protocol endpoints for agent discovery,
enabling other agents and clients to discover PMOVES-DoX capabilities.

Endpoints:
    GET /.well-known/agent-card: Return the AgentCard JSON
    GET /a2a/capabilities: Return detailed capabilities list

Reference: https://a2ui.org/a2a-extension/a2ui/v0.9
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models.agent_card import AgentCard, AgentCapability, MCPTool


router = APIRouter(tags=["a2a"])


def _load_mcp_manifest() -> Dict[str, Any]:
    """Load MCP manifest from backend/mcp/manifest.json.

    Returns:
        Parsed manifest dictionary, or empty dict if not found.
    """
    # Resolve path relative to this file's location
    manifest_path = Path(__file__).resolve().parents[3] / "mcp" / "manifest.json"

    if not manifest_path.exists():
        return {}

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _manifest_to_mcp_tools(manifest: Dict[str, Any]) -> List[MCPTool]:
    """Convert MCP manifest tools to MCPTool models.

    Args:
        manifest: Parsed MCP manifest dictionary.

    Returns:
        List of MCPTool models derived from the manifest.
    """
    tools = []
    capabilities = manifest.get("capabilities", {})
    tool_defs = capabilities.get("tools", {})

    for name, tool_def in tool_defs.items():
        endpoint_info = tool_def.get("endpoint", {})
        tools.append(
            MCPTool(
                name=name,
                description=tool_def.get("description", ""),
                endpoint=endpoint_info.get("path", f"/{name}"),
                method=endpoint_info.get("method", "POST"),
                input_schema=tool_def.get("input_schema"),
            )
        )

    return tools


def _build_default_capabilities() -> List[AgentCapability]:
    """Build default capability list for PMOVES-DoX.

    Returns:
        List of AgentCapability models representing supported extensions.
    """
    return [
        AgentCapability(
            uri="https://a2ui.org/a2a-extension/a2ui/v0.9",
            description="A2UI rendering capability for rich UI responses",
            required=False,
            params={
                "supportedCatalogIds": [
                    "https://a2ui.dev/specification/v0_9/standard_catalog.json"
                ],
                "acceptsInlineCatalogs": True,
            },
        ),
        AgentCapability(
            uri="urn:pmoves-dox:capability:document-ingestion",
            description="PDF, CSV, XLSX, and XML document ingestion with structure extraction",
            required=False,
            params={
                "supportedFormats": ["pdf", "csv", "xlsx", "xls", "xml", "json", "yaml"],
                "maxFileSizeMB": 100,
            },
        ),
        AgentCapability(
            uri="urn:pmoves-dox:capability:vector-search",
            description="Semantic vector search across ingested documents",
            required=False,
            params={
                "embeddingModel": os.getenv("SEARCH_MODEL", "all-MiniLM-L6-v2"),
                "indexType": "faiss",
            },
        ),
        AgentCapability(
            uri="urn:pmoves-dox:capability:qa-engine",
            description="Question answering with citation retrieval from documents",
            required=False,
            params=None,
        ),
        AgentCapability(
            uri="urn:pmoves-dox:capability:tag-extraction",
            description="AI-powered tag extraction using LangExtract or Ollama",
            required=False,
            params={
                "providers": ["gemini", "ollama"],
            },
        ),
        AgentCapability(
            uri="urn:pmoves-dox:capability:poml-export",
            description="Export documents as POML (Prompt Markup Language) for LLM consumption",
            required=False,
            params=None,
        ),
    ]


def _build_agent_card() -> AgentCard:
    """Build the complete AgentCard with MCP tools and capabilities.

    Returns:
        Populated AgentCard model ready for serialization.
    """
    manifest = _load_mcp_manifest()
    mcp_tools = _manifest_to_mcp_tools(manifest)
    capabilities = _build_default_capabilities()

    return AgentCard(
        name=manifest.get("name_for_human", "PMOVES-DoX"),
        version="1.0.0",
        description=manifest.get(
            "description_for_model",
            "Document intelligence platform for PDF extraction, vector search, and Q&A",
        ),
        capabilities=capabilities,
        mcp_tools=mcp_tools,
        homepage=os.getenv("DOX_HOMEPAGE", None),
        contact=os.getenv("DOX_CONTACT", None),
    )


@router.get("/.well-known/agent-card")
async def get_agent_card():
    """Return the AgentCard JSON for A2A agent discovery.

    This endpoint implements the A2A protocol's agent discovery mechanism.
    Clients and other agents can fetch this to understand the capabilities
    and tools offered by PMOVES-DoX.

    Returns:
        AgentCard JSON with capabilities, MCP tools, and modalities.
    """
    card = _build_agent_card()
    return JSONResponse(
        content=card.model_dump(by_alias=True, exclude_none=True),
        media_type="application/json",
    )


@router.get("/a2a/capabilities")
async def get_capabilities():
    """Return detailed capabilities list for the agent.

    Provides a more detailed view of supported capabilities,
    including parameters and requirements for each.

    Returns:
        List of capability dictionaries with full parameter details.
    """
    capabilities = _build_default_capabilities()
    return JSONResponse(
        content={
            "agentName": "PMOVES-DoX",
            "agentVersion": "1.0.0",
            "capabilities": [
                cap.model_dump(exclude_none=True) for cap in capabilities
            ],
        },
        media_type="application/json",
    )


@router.get("/a2a/tools")
async def get_tools():
    """Return list of MCP tools available for invocation.

    Provides the list of tools from the MCP manifest that can be
    called by agents or orchestrators.

    Returns:
        List of tool definitions with endpoints and schemas.
    """
    manifest = _load_mcp_manifest()
    tools = _manifest_to_mcp_tools(manifest)

    return JSONResponse(
        content={
            "agentName": "PMOVES-DoX",
            "tools": [tool.model_dump(by_alias=True, exclude_none=True) for tool in tools],
        },
        media_type="application/json",
    )
