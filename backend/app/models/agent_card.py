"""Agent Card models for A2A protocol agent discovery.

This module defines Pydantic models for the AgentCard endpoint,
enabling agent discovery per the A2A (Agent-to-Agent) protocol.

The AgentCard advertises:
- Agent identity and version
- Supported capabilities (with A2UI extension URIs)
- MCP tools available for invocation
- Input/output modalities supported

Reference: https://a2ui.org/a2a-extension/a2ui/v0.9
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class MCPTool(BaseModel):
    """Model Context Protocol tool definition.

    Represents a tool exposed via MCP manifest that can be
    invoked by agents or orchestrators.

    Attributes:
        name: Tool identifier (e.g., "search", "extract_tags")
        description: Human-readable description of tool functionality
        endpoint: API path for tool invocation
        method: HTTP method (default: POST)
        input_schema: JSON Schema for tool input parameters
    """

    name: str
    description: str
    endpoint: str
    method: str = "POST"
    input_schema: Optional[Dict[str, Any]] = Field(default=None, alias="inputSchema")

    class Config:
        populate_by_name = True


class AgentCapability(BaseModel):
    """Agent capability declaration per A2A spec.

    Capabilities are advertised in the AgentCard to inform clients
    and other agents about supported extensions and features.

    Attributes:
        uri: Unique identifier for the capability (e.g., A2UI extension URI)
        description: Human-readable description of the capability
        required: Whether this capability is required for interaction
        params: Optional parameters for the capability
    """

    uri: str
    description: str
    required: bool = False
    params: Optional[Dict[str, Any]] = None


class AgentCard(BaseModel):
    """A2A Agent Card for agent discovery.

    The AgentCard is served at /.well-known/agent-card to enable
    agent discovery per the A2A protocol. It advertises the agent's
    identity, capabilities, and available tools.

    Attributes:
        name: Human-readable agent name
        version: Semantic version of the agent
        description: Brief description of agent functionality
        capabilities: List of supported A2A capabilities/extensions
        mcp_tools: List of MCP tools available for invocation
        input_modalities: MIME types accepted as input
        output_modalities: MIME types produced as output
        homepage: Optional URL for agent documentation
        contact: Optional contact email for the agent maintainer
    """

    name: str = "PMOVES-DoX"
    version: str = "1.0.0"
    description: str = (
        "Document intelligence platform for PDF extraction, "
        "vector search, and Q&A with structured data export"
    )
    capabilities: List[AgentCapability] = Field(default_factory=list)
    mcp_tools: List[MCPTool] = Field(default_factory=list, alias="mcpTools")
    input_modalities: List[str] = Field(
        default_factory=lambda: [
            "text/plain",
            "application/json",
            "application/pdf",
            "text/csv",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/xml",
        ],
        alias="inputModalities",
    )
    output_modalities: List[str] = Field(
        default_factory=lambda: [
            "text/markdown",
            "application/json",
            "text/csv",
        ],
        alias="outputModalities",
    )
    homepage: Optional[str] = None
    contact: Optional[str] = None

    class Config:
        populate_by_name = True
