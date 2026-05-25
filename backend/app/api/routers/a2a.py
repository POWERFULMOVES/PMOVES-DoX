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
    POST /a2a/task/execute: Execute a dispatched task

Reference: https://a2ui.org/a2a-extension/a2ui/v0.9
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import get_current_user, optional_auth
from app.models.agent_card import AgentCard, AgentCapability, MCPTool
from app.services.cipher_service import CipherService
from app.services.reasoning_service import reasoning_service
from app.services.geometry_engine import GeometryEngine
from app.services.chit_service import chit_service

logger = logging.getLogger(__name__)

# Agent Zero MCP endpoint (internal Docker network)
AGENT_ZERO_MCP_URL = os.getenv(
    "AGENT_ZERO_MCP_URL", "http://pmoves-agent-zero:50051"
)
AGENT_ZERO_MCP_TOKEN = os.getenv("AGENT_ZERO_MCP_TOKEN", "")
AGENT_ZERO_TIMEOUT = int(os.getenv("AGENT_ZERO_TIMEOUT", "30"))

# Geometry engine singleton
geometry_engine = GeometryEngine()


# =============================================================================
# Request/Response Models for A2A Endpoints
# =============================================================================


class TaskDecomposeRequest(BaseModel):
    """Request model for task decomposition."""

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
    status: str = "completed"
    message: str = ""


class MemorySearchRequest(BaseModel):
    """Request model for memory search."""

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
    status: str = "completed"
    message: str = ""


class ReasoningStartRequest(BaseModel):
    """Request model for starting a reasoning trace."""

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
    status: str = "active"
    message: str = ""


class GeometryAnalyzeRequest(BaseModel):
    """Request model for geometry analysis."""

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
    poincare: Optional[Dict[str, Any]] = Field(
        None,
        description="Deterministic 2D Poincare disk projection for geometry consumers",
    )


class GeometryAnalyzeResponse(BaseModel):
    """Response model for geometry analysis."""

    query: str
    metrics: Optional[ManifoldMetrics] = None
    nearest_regions: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "completed"
    message: str = ""


router = APIRouter(tags=["a2a"])


# =============================================================================
# Helper: Agent Zero MCP call
# =============================================================================


async def _call_agent_zero_mcp(command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Send a command to Agent Zero via MCP API.

    Args:
        command: MCP command name.
        params: Command parameters.

    Returns:
        Response data from Agent Zero.

    Raises:
        HTTPException: If Agent Zero is unreachable or returns an error.
    """
    headers = {"Content-Type": "application/json"}
    if AGENT_ZERO_MCP_TOKEN:
        headers["Authorization"] = f"Bearer {AGENT_ZERO_MCP_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=AGENT_ZERO_TIMEOUT) as client:
            response = await client.post(
                f"{AGENT_ZERO_MCP_URL}/mcp/command",
                json={"command": command, "params": params},
                headers=headers,
            )
            response.raise_for_status()
            try:
                return response.json()
            except (ValueError, json.JSONDecodeError) as e:
                logger.error("Agent Zero non-JSON response for '%s': %s (body: %s)", command, e, response.text[:500])
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Agent orchestrator returned an unparseable response",
                )
    except HTTPException:
        raise
    except httpx.TimeoutException:
        logger.warning("Agent Zero MCP timeout for command: %s", command)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Agent orchestrator timed out",
        )
    except httpx.HTTPStatusError as e:
        logger.error("Agent Zero MCP HTTP %d: %s", e.response.status_code, e.response.text[:200])
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent orchestrator returned an error",
        )
    except httpx.RequestError as e:
        logger.warning("Agent Zero MCP unreachable: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent orchestrator is not available",
        )


# =============================================================================
# Agent Card & Discovery
# =============================================================================


def _load_mcp_manifest() -> Dict[str, Any]:
    """Load MCP manifest from backend/mcp/manifest.json."""
    manifest_path = Path(__file__).resolve().parents[3] / "mcp" / "manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("Failed to load MCP manifest from %s: %s", manifest_path, e)
        return {}


def _manifest_to_mcp_tools(manifest: Dict[str, Any]) -> List[MCPTool]:
    """Convert MCP manifest tools to MCPTool models."""
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
    """Build default capability list for PMOVES-DoX."""
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
            params={"providers": ["gemini", "ollama"]},
        ),
        AgentCapability(
            uri="urn:pmoves-dox:capability:poml-export",
            description="Export documents as POML (Prompt Markup Language) for LLM consumption",
            required=False,
            params=None,
        ),
        AgentCapability(
            uri="urn:pmoves-dox:capability:agent-orchestration",
            description="Multi-agent task decomposition and coordination via Agent Zero",
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
    """Build the complete AgentCard with MCP tools and capabilities."""
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
    """Return the AgentCard JSON for A2A agent discovery."""
    card = _build_agent_card()
    return JSONResponse(
        content=card.model_dump(by_alias=True, exclude_none=True),
        media_type="application/json",
    )


@router.get("/a2a/capabilities")
async def get_capabilities():
    """Return detailed capabilities list for the agent."""
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
    """Return list of MCP tools available for invocation."""
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
# Agent Orchestration: Decompose via Agent Zero MCP
# =============================================================================


@router.post(
    "/a2a/orchestrate/decompose",
    response_model=TaskDecomposeResponse,
    summary="Decompose task into subtasks via Agent Zero",
    tags=["a2a", "orchestration"],
)
async def orchestrate_decompose(
    request: TaskDecomposeRequest,
    _user_id: str = Depends(get_current_user),
) -> TaskDecomposeResponse:
    """Decompose a high-level task into coordinated subtasks.

    Delegates to Agent Zero MCP API for intelligent task decomposition.
    """
    result = await _call_agent_zero_mcp(
        "decompose",
        {
            "task": request.task,
            "context": request.context or "",
            "max_subtasks": request.max_subtasks,
        },
    )

    # Parse Agent Zero response into subtasks
    subtasks = []
    for item in result.get("subtasks", []):
        subtasks.append(
            SubTask(
                id=item.get("id", str(uuid4())),
                description=item.get("description", ""),
                priority=item.get("priority", 5),
                dependencies=item.get("dependencies", []),
                agent_hint=item.get("agent_hint"),
            )
        )

    return TaskDecomposeResponse(
        original_task=request.task,
        subtasks=subtasks,
        status="completed",
        message=f"Decomposed into {len(subtasks)} subtasks via Agent Zero",
    )


# =============================================================================
# Memory Search: via CipherService
# =============================================================================


@router.post(
    "/a2a/memory/search",
    response_model=MemorySearchResponse,
    summary="Search Cipher persistent memory",
    tags=["a2a", "memory"],
)
async def memory_search(
    request: MemorySearchRequest,
    user_id: str = Depends(get_current_user),
) -> MemorySearchResponse:
    """Search and retrieve from Cipher persistent memory.

    Uses CipherService to search stored knowledge, context, and history.
    Supports workspace-scoped and category-filtered searches.
    """
    # If workspace is specified, use team memory shared context
    if request.workspace:
        try:
            shared = await CipherService.get_shared_context(
                request.workspace, limit=request.limit
            )
        except Exception as e:
            logger.error("CipherService.get_shared_context failed for '%s': %s", request.workspace, e)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Memory service unavailable")
        results = []
        for item in shared.get("items", []):
            content = item.get("content", "")
            if isinstance(content, dict):
                content = json.dumps(content)
            results.append(
                MemorySearchResult(
                    id=item.get("memory_id", str(uuid4())),
                    content=str(content),
                    score=1.0,
                    metadata=item.get("metadata", {}),
                )
            )
        return MemorySearchResponse(
            query=request.query,
            results=results[:request.limit],
            total=shared.get("total_in_workspace", len(results)),
            status="completed",
            message=f"Found {len(results)} items in workspace '{request.workspace}'",
        )

    # General memory search via CipherService
    category = None
    if request.filters and "category" in request.filters:
        category = request.filters["category"]

    try:
        raw_results = CipherService.search_memory(category=category, q=request.query, user_id=user_id)
    except Exception as e:
        logger.error("CipherService.search_memory failed: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Memory service unavailable")

    results = []
    for item in raw_results[:request.limit]:
        content = item.get("content", "")
        if isinstance(content, dict):
            content = json.dumps(content)
        results.append(
            MemorySearchResult(
                id=item.get("id", str(uuid4())),
                content=str(content),
                score=item.get("relevance", 0.8),
                metadata={
                    k: v for k, v in item.items()
                    if k not in ("id", "content", "relevance")
                },
            )
        )

    return MemorySearchResponse(
        query=request.query,
        results=results,
        total=len(raw_results),
        status="completed",
        message=f"Found {len(results)} memory entries",
    )


# =============================================================================
# Reasoning Trace: via ReasoningService
# =============================================================================


@router.post(
    "/a2a/reasoning/start",
    response_model=ReasoningStartResponse,
    summary="Start multi-step reasoning trace",
    tags=["a2a", "reasoning"],
)
async def reasoning_start(
    request: ReasoningStartRequest,
    _user_id: str = Depends(get_current_user),
) -> ReasoningStartResponse:
    """Start a multi-step reasoning trace with evidence tracking.

    Uses the ReasoningService to create and manage reasoning traces.
    """
    try:
        trace = await reasoning_service.start_reasoning(
            question=request.question,
            context=request.context,
            max_steps=request.max_steps,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("ReasoningService.start_reasoning failed: %s", e)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Reasoning service unavailable")

    return ReasoningStartResponse(
        trace_id=trace.trace_id,
        question=trace.question,
        steps=[],
        status=trace.status.value,
        message=f"Reasoning trace started (max {request.max_steps} steps)",
    )


# =============================================================================
# Geometric Analysis: via GeometryEngine + ChitService
# =============================================================================


@router.post(
    "/a2a/geometry/analyze",
    response_model=GeometryAnalyzeResponse,
    summary="Analyze semantic space geometry",
    tags=["a2a", "geometry"],
)
async def geometry_analyze(
    request: GeometryAnalyzeRequest,
    _user_id: str = Depends(get_current_user),
) -> GeometryAnalyzeResponse:
    """Analyze semantic space using manifold geometry.

    Uses GeometryEngine for curvature analysis and ChitService for
    embedding generation when available.
    """
    embedding_source = "none"

    # Generate embeddings for the query using ChitService if available
    embeddings = chit_service.generate_embeddings([request.query])
    if embeddings:
        embedding_source = "chit_service"

    if not embeddings:
        # Fall back to search_index embeddings
        try:
            from app.globals import search_index
            embedding = search_index.embed_text(request.query)
            if embedding is not None:
                embeddings = [embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)]
                embedding_source = "search_index"
        except (ImportError, AttributeError, RuntimeError) as e:
            logger.warning("Search index embedding fallback failed: %s", e)

    if not embeddings or len(embeddings) < 4:
        # Need at least 4 points for curvature analysis — pad with synthetic points
        if embeddings:
            import random
            base = embeddings[0]
            while len(embeddings) < 4:
                noisy = [v + random.gauss(0, 0.01) for v in base]
                embeddings.append(noisy)
            embedding_source = f"{embedding_source}+synthetic"
        else:
            return GeometryAnalyzeResponse(
                query=request.query,
                metrics=ManifoldMetrics(
                    curvature=0.0,
                    manifold_type="euclidean",
                    dimension=3,
                    coordinates=[],
                ),
                nearest_regions=[],
                status="completed",
                message="No embeddings available for analysis; returned flat geometry default",
            )

    # Run curvature analysis
    curvature_result = geometry_engine.analyze_curvature(embeddings)

    # Determine manifold type from curvature
    k = curvature_result.get("curvature_k", 0.0)
    if k < -0.5:
        manifold_type = "hyperbolic"
    elif k > 0.5:
        manifold_type = "spherical"
    else:
        manifold_type = "euclidean"

    labels = [f"embedding_{i}" for i in range(len(embeddings))]
    if labels:
        labels[0] = "query"
    poincare = geometry_engine.project_embeddings_to_poincare(embeddings, labels=labels)

    metrics = ManifoldMetrics(
        curvature=float(k),
        manifold_type=manifold_type,
        dimension=len(embeddings[0]) if embeddings else 3,
        coordinates=embeddings[0][:10] if embeddings else [],
        poincare=poincare,
    )

    # Publish manifold update to NATS if available
    if chit_service.is_nats_available:
        await chit_service.publish_manifold_update(curvature_result)

    return GeometryAnalyzeResponse(
        query=request.query,
        metrics=metrics,
        nearest_regions=[],
        status="completed",
        message=f"Manifold analysis: {manifold_type} (K={k:.3f}, source={embedding_source})",
    )


# =============================================================================
# Task Execution: Route to internal services
# =============================================================================


class TaskExecuteRequest(BaseModel):
    """Request model for task execution from agent dispatcher."""

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
)
async def execute_task(
    request: TaskExecuteRequest,
    user_id: str = Depends(get_current_user),
) -> TaskExecuteResponse:
    """Execute a task dispatched by the agent dispatcher.

    Routes tasks to appropriate internal services based on the payload's
    'action' field: search, analyze, extract, summarize, ask.
    """
    start_time = time.time()
    action = request.payload.get("action", "").lower()

    try:
        if action == "search":
            from app.globals import search_index
            query = request.payload.get("query", request.description)
            k = request.payload.get("k", 5)
            results = search_index.search(query, k=k)
            result = {"action": "search", "query": query, "results": results}

        elif action == "ask":
            from app.globals import qa_engine
            question = request.payload.get("question", request.description)
            answer = await qa_engine.ask(question)
            result = {"action": "ask", "question": question, **answer}

        elif action == "extract_tags":
            text = request.payload.get("text", "")
            if text:
                from app.api.routers.analysis import extract_tags_text, ExtractTagsRequest
                tag_req = ExtractTagsRequest(text=text)
                tag_result = await extract_tags_text(tag_req)
                result = {"action": "extract_tags", "tags": tag_result.get("tags", [])}
            else:
                result = {"action": "extract_tags", "tags": [], "message": "No text provided"}

        elif action == "memory_search":
            query = request.payload.get("query", request.description)
            raw = CipherService.search_memory(q=query, user_id=user_id)
            result = {"action": "memory_search", "results": raw[:10]}

        else:
            result = {
                "task_id": request.task_id,
                "description": request.description,
                "payload_keys": list(request.payload.keys()),
                "message": f"Task acknowledged. Action '{action}' routed to default handler.",
            }

    except (ValueError, KeyError) as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return TaskExecuteResponse(
            task_id=request.task_id, status="failed", result={},
            error=f"Invalid input: {e}", execution_time_ms=execution_time_ms,
        )
    except Exception as e:
        logger.error("Task execution failed for %s: %s", request.task_id, e, exc_info=True)
        execution_time_ms = int((time.time() - start_time) * 1000)
        return TaskExecuteResponse(
            task_id=request.task_id, status="failed", result={},
            error="Internal service error", execution_time_ms=execution_time_ms,
        )

    execution_time_ms = int((time.time() - start_time) * 1000)
    return TaskExecuteResponse(
        task_id=request.task_id,
        status="completed",
        result=result,
        execution_time_ms=execution_time_ms,
    )
