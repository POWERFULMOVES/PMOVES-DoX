"""A2A (Agent-to-Agent) protocol router for agent discovery.

This router implements the A2A protocol endpoints for agent discovery,
enabling other agents and clients to discover PMOVES-DoX capabilities.

Endpoints:
    GET /.well-known/agent-card: Return the AgentCard JSON
    GET /a2a/capabilities: Return detailed capabilities list
    GET /a2a/tools: Return list of MCP tools
    POST /a2a/orchestrate/decompose: Multi-agent task decomposition
    POST /a2a/memory/search: Search Cipher persistent memory
    POST /a2a/reasoning/start: Start multi-step reasoning trace
    POST /a2a/geometry/analyze: Analyze semantic space geometry

Reference: https://a2ui.org/a2a-extension/a2ui/v0.9
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.models.agent_card import AgentCard, AgentCapability, MCPTool


# =============================================================================
# Request/Response Models for A2A Endpoints
# =============================================================================


class TaskDecomposeRequest(BaseModel):
    """Request model for task decomposition.

    Attributes:
        task: The high-level task to decompose into subtasks.
        context: Optional context or constraints for decomposition.
        max_subtasks: Maximum number of subtasks to generate.
    """

    task: str = Field(..., description="The task to decompose")
    context: Optional[str] = Field(None, description="Optional context or constraints")
    max_subtasks: int = Field(5, ge=1, le=20, description="Maximum number of subtasks")


class SubTask(BaseModel):
    """A single subtask in a decomposition result."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    priority: int = Field(1, ge=1, le=10)
    dependencies: List[str] = Field(default_factory=list)
    agent_hint: Optional[str] = Field(None, description="Suggested agent type for this subtask")


class TaskDecomposeResponse(BaseModel):
    """Response model for task decomposition."""

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    original_task: str
    subtasks: List[SubTask] = Field(default_factory=list)
    status: str = "not_implemented"
    message: str = "Task decomposition is not yet implemented"


class MemorySearchRequest(BaseModel):
    """Request model for memory search.

    Attributes:
        query: Search query string.
        workspace: Optional workspace to search within.
        limit: Maximum number of results to return.
        filters: Optional metadata filters.
    """

    query: str = Field(..., description="Search query")
    workspace: Optional[str] = Field(None, description="Workspace identifier")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")


class MemorySearchResult(BaseModel):
    """A single memory search result."""

    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemorySearchResponse(BaseModel):
    """Response model for memory search."""

    query: str
    results: List[MemorySearchResult] = Field(default_factory=list)
    total: int = 0
    status: str = "not_implemented"
    message: str = "Memory search is not yet implemented"


class ReasoningStartRequest(BaseModel):
    """Request model for starting a reasoning trace.

    Attributes:
        question: The question or problem to reason about.
        context: Optional supporting context.
        max_steps: Maximum reasoning steps allowed.
    """

    question: str = Field(..., description="Question to reason about")
    context: Optional[str] = Field(None, description="Supporting context")
    max_steps: int = Field(10, ge=1, le=50, description="Maximum reasoning steps")


class ReasoningStep(BaseModel):
    """A single step in a reasoning trace."""

    step_number: int
    thought: str
    evidence: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class ReasoningStartResponse(BaseModel):
    """Response model for starting a reasoning trace."""

    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    question: str
    steps: List[ReasoningStep] = Field(default_factory=list)
    status: str = "not_implemented"
    message: str = "Reasoning trace is not yet implemented"


class GeometryAnalyzeRequest(BaseModel):
    """Request model for geometry analysis.

    Attributes:
        query: Query or content to analyze.
        space_id: Optional semantic space identifier.
        analysis_type: Type of geometric analysis to perform.
    """

    query: str = Field(..., description="Query or content to analyze")
    space_id: Optional[str] = Field(None, description="Semantic space identifier")
    analysis_type: str = Field(
        "curvature", description="Analysis type: curvature, distance, or route"
    )


class ManifoldMetrics(BaseModel):
    """Geometric metrics for a manifold region."""

    curvature: float = Field(0.0, description="Local curvature value")
    manifold_type: str = Field("euclidean", description="hyperbolic, spherical, or euclidean")
    dimension: int = Field(3, ge=1, description="Manifold dimension")
    coordinates: List[float] = Field(default_factory=list, description="Position in embedding space")


class GeometryAnalyzeResponse(BaseModel):
    """Response model for geometry analysis."""

    query: str
    metrics: Optional[ManifoldMetrics] = None
    nearest_regions: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "not_implemented"
    message: str = "Geometry analysis is not yet implemented"


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
        # New A2A capabilities
        AgentCapability(
            uri="urn:pmoves-dox:capability:agent-orchestration",
            description="Multi-agent task decomposition and coordination",
            required=False,
            params={
                "tools": ["decompose_task", "dispatch_subtask", "aggregate_results"],
                "maxSubtasks": 20,
                "supportedAgentTypes": ["document", "search", "analysis", "reasoning"],
            },
        ),
        AgentCapability(
            uri="urn:pmoves-dox:capability:memory-search",
            description="Search and retrieve from Cipher persistent memory",
            required=False,
            params={
                "tools": ["search_memory", "store_memory", "get_workspace"],
                "backends": ["cipher", "faiss"],
                "maxResults": 100,
            },
        ),
        AgentCapability(
            uri="urn:pmoves-dox:capability:reasoning-trace",
            description="Multi-step reasoning with evidence tracking",
            required=False,
            params={
                "tools": ["start_reasoning", "add_step", "get_trace", "conclude"],
                "maxSteps": 50,
                "evidenceTracking": True,
            },
        ),
        AgentCapability(
            uri="urn:pmoves-dox:capability:geometric-analysis",
            description="Semantic space analysis using manifold geometry",
            required=False,
            params={
                "tools": ["analyze_curvature", "compute_distance", "route_query"],
                "manifoldTypes": ["hyperbolic", "spherical", "euclidean"],
                "dimensions": [3, 128, 768],
            },
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


# =============================================================================
# Agent Orchestration Endpoints
# =============================================================================


@router.post(
    "/a2a/orchestrate/decompose",
    response_model=TaskDecomposeResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Decompose task into subtasks",
    tags=["a2a", "orchestration"],
)
async def orchestrate_decompose(request: TaskDecomposeRequest) -> TaskDecomposeResponse:
    """Decompose a high-level task into coordinated subtasks.

    This endpoint enables multi-agent task decomposition by breaking
    a complex task into smaller, actionable subtasks that can be
    dispatched to specialized agents.

    Args:
        request: Task decomposition request with task description and constraints.

    Returns:
        TaskDecomposeResponse with decomposed subtasks or not-implemented status.

    Note:
        This endpoint is a placeholder. Full implementation requires
        integration with the agent orchestration framework.
    """
    return TaskDecomposeResponse(
        original_task=request.task,
        subtasks=[],
        status="not_implemented",
        message="Task decomposition is not yet implemented. "
        "This capability will enable multi-agent coordination.",
    )


# =============================================================================
# Memory Search Endpoints
# =============================================================================


@router.post(
    "/a2a/memory/search",
    response_model=MemorySearchResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Search Cipher persistent memory",
    tags=["a2a", "memory"],
)
async def memory_search(request: MemorySearchRequest) -> MemorySearchResponse:
    """Search and retrieve from Cipher persistent memory.

    This endpoint provides access to the Cipher memory system,
    enabling semantic search across stored knowledge, context,
    and conversation history.

    Args:
        request: Memory search request with query and optional filters.

    Returns:
        MemorySearchResponse with matching memory entries or not-implemented status.

    Note:
        This endpoint is a placeholder. Full implementation requires
        integration with the Cipher memory backend (PsyFeR).
    """
    return MemorySearchResponse(
        query=request.query,
        results=[],
        total=0,
        status="not_implemented",
        message="Memory search is not yet implemented. "
        "This capability will enable retrieval from Cipher persistent memory.",
    )


# =============================================================================
# Reasoning Trace Endpoints
# =============================================================================


@router.post(
    "/a2a/reasoning/start",
    response_model=ReasoningStartResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Start multi-step reasoning trace",
    tags=["a2a", "reasoning"],
)
async def reasoning_start(request: ReasoningStartRequest) -> ReasoningStartResponse:
    """Start a multi-step reasoning trace with evidence tracking.

    This endpoint initiates a reasoning session that tracks each
    step of the reasoning process, including supporting evidence
    and confidence scores.

    Args:
        request: Reasoning request with question and optional context.

    Returns:
        ReasoningStartResponse with trace ID or not-implemented status.

    Note:
        This endpoint is a placeholder. Full implementation requires
        integration with the HRM (Halting Reasoning Module) or similar
        iterative reasoning framework.
    """
    return ReasoningStartResponse(
        question=request.question,
        steps=[],
        status="not_implemented",
        message="Reasoning trace is not yet implemented. "
        "This capability will enable multi-step reasoning with evidence tracking.",
    )


# =============================================================================
# Geometric Analysis Endpoints
# =============================================================================


@router.post(
    "/a2a/geometry/analyze",
    response_model=GeometryAnalyzeResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Analyze semantic space geometry",
    tags=["a2a", "geometry"],
)
async def geometry_analyze(request: GeometryAnalyzeRequest) -> GeometryAnalyzeResponse:
    """Analyze semantic space using manifold geometry.

    This endpoint performs geometric analysis on the semantic
    embedding space, including curvature estimation, distance
    computation, and optimal routing through the knowledge manifold.

    Args:
        request: Geometry analysis request with query and analysis type.

    Returns:
        GeometryAnalyzeResponse with manifold metrics or not-implemented status.

    Note:
        This endpoint is a placeholder. Full implementation requires
        integration with the GeometryEngine and CHIT protocol services.
    """
    return GeometryAnalyzeResponse(
        query=request.query,
        metrics=None,
        nearest_regions=[],
        status="not_implemented",
        message=f"Geometry analysis ({request.analysis_type}) is not yet implemented. "
        "This capability will enable semantic space analysis using manifold geometry.",
    )


# =============================================================================
# Task Execution Endpoint (for Agent Dispatcher)
# =============================================================================


class TaskExecuteRequest(BaseModel):
    """Request model for task execution from agent dispatcher.

    Attributes:
        task_id: Unique identifier for this task.
        description: Human-readable task description.
        payload: Task-specific data and parameters.
        metadata: Additional metadata (chain context, step info, etc.)
    """

    task_id: str = Field(..., description="Unique task identifier")
    description: str = Field("", description="Task description")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Task metadata")


class TaskExecuteResponse(BaseModel):
    """Response model for task execution."""

    task_id: str
    status: str = Field("completed", description="Execution status")
    result: Dict[str, Any] = Field(default_factory=dict, description="Execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")


@router.post(
    "/a2a/task/execute",
    response_model=TaskExecuteResponse,
    tags=["a2a", "task"],
    summary="Execute a dispatched task",
    description="Endpoint for agent dispatcher to execute tasks on this agent.",
)
async def execute_task(request: TaskExecuteRequest) -> TaskExecuteResponse:
    """Execute a task dispatched by the agent dispatcher.

    This endpoint receives tasks from the AgentDispatcher service and executes
    them using the appropriate internal services based on the task payload.

    Args:
        request: TaskExecuteRequest with task details and payload.

    Returns:
        TaskExecuteResponse with execution status and results.

    Note:
        This is a stub implementation. Full implementation will route tasks
        to appropriate internal services (search, analysis, extraction, etc.)
        based on payload content and metadata.
    """
    import time
    start_time = time.time()

    # Stub implementation - echo back task info with mock result
    # In production, this would route to internal services based on payload
    result = {
        "task_id": request.task_id,
        "description": request.description,
        "payload_keys": list(request.payload.keys()),
        "metadata_keys": list(request.metadata.keys()),
        "message": "Task received and acknowledged. Full execution pending implementation.",
    }

    execution_time_ms = int((time.time() - start_time) * 1000)

    return TaskExecuteResponse(
        task_id=request.task_id,
        status="completed",
        result=result,
        execution_time_ms=execution_time_ms,
    )
