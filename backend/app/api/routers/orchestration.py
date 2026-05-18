"""Orchestration router for multi-agent task decomposition and coordination.

This router implements endpoints for orchestrating complex tasks across
multiple agents via Agent Zero MCP, enabling task decomposition, dispatch,
status tracking, and result aggregation.

Endpoints:
    POST /orchestrate/decompose: Break a high-level task into subtasks
    POST /orchestrate/dispatch: Send a subtask to an appropriate agent
    GET /orchestrate/status/{task_id}: Check task execution status
    POST /orchestrate/aggregate: Combine results from multiple subtasks
"""

import json
import logging
import os
from collections import OrderedDict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import get_current_user

logger = logging.getLogger(__name__)

# Agent Zero MCP configuration
AGENT_ZERO_URL = os.getenv("AGENT_ZERO_MCP_URL", "http://pmoves-agent-zero:50051")
AGENT_ZERO_TOKEN = os.getenv("AGENT_ZERO_MCP_TOKEN", "")
AGENT_ZERO_TIMEOUT = int(os.getenv("AGENT_ZERO_TIMEOUT", "30"))

# In-memory task registry with bounded size (LRU eviction)
_REGISTRY_MAX_SIZE = 1000
_task_registry: OrderedDict[str, Dict[str, Any]] = OrderedDict()


def _registry_put(key: str, value: Dict[str, Any]) -> None:
    """Insert into task registry with LRU eviction at max size."""
    _task_registry[key] = value
    _task_registry.move_to_end(key)
    while len(_task_registry) > _REGISTRY_MAX_SIZE:
        evicted_key, _ = _task_registry.popitem(last=False)
        logger.debug("Task registry evicted: %s", evicted_key)


# =============================================================================
# Enums and Constants
# =============================================================================


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    DOCUMENT = "document"
    SEARCH = "search"
    ANALYSIS = "analysis"
    REASONING = "reasoning"
    EXTRACTION = "extraction"


# =============================================================================
# Request/Response Models
# =============================================================================


class DecomposeRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=4096)
    context: Optional[str] = Field(None, max_length=8192)
    max_subtasks: int = Field(5, ge=1, le=20)
    agent_hints: Optional[List[AgentType]] = None


class SubtaskInfo(BaseModel):
    subtask_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    priority: int = Field(1, ge=1, le=10)
    estimated_complexity: str = Field("medium", pattern="^(low|medium|high)$")
    suggested_agent: AgentType = Field(AgentType.ANALYSIS)
    dependencies: List[str] = Field(default_factory=list)


class DecomposeResponse(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    original_task: str
    subtasks: List[SubtaskInfo] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DispatchRequest(BaseModel):
    subtask_id: str = Field(..., description="ID of the subtask to dispatch")
    task_id: Optional[str] = Field(None, description="Parent task ID")
    agent_type: AgentType = Field(..., description="Target agent type")
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(5, ge=1, le=10)
    timeout_seconds: int = Field(300, ge=1, le=3600)


class DispatchResponse(BaseModel):
    dispatch_id: str = Field(default_factory=lambda: str(uuid4()))
    subtask_id: str
    agent_type: AgentType
    status: TaskStatus = Field(TaskStatus.PENDING)
    queued_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    estimated_start: Optional[str] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    progress_percent: int = Field(0, ge=0, le=100)
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    subtask_statuses: Dict[str, TaskStatus] = Field(default_factory=dict)
    result_preview: Optional[str] = None
    error_message: Optional[str] = None


class AggregateRequest(BaseModel):
    task_id: str = Field(..., description="Parent task ID")
    subtask_ids: List[str] = Field(..., min_length=1)
    aggregation_strategy: str = Field("merge", pattern="^(merge|concat|weighted|custom)$")
    include_metadata: bool = Field(True)


class SubtaskResult(BaseModel):
    subtask_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    agent_type: Optional[AgentType] = None


class AggregateResponse(BaseModel):
    task_id: str
    aggregated_result: Dict[str, Any] = Field(default_factory=dict)
    subtask_results: List[SubtaskResult] = Field(default_factory=list)
    aggregation_strategy: str
    total_execution_time_ms: int = 0
    success_count: int = 0
    failure_count: int = 0
    aggregated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# =============================================================================
# Helper: Agent Zero MCP call
# =============================================================================


async def _agent_zero_request(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send a request to Agent Zero MCP API."""
    url = f"{AGENT_ZERO_URL.rstrip('/')}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if AGENT_ZERO_TOKEN:
        headers["Authorization"] = f"Bearer {AGENT_ZERO_TOKEN}"
    try:
        async with httpx.AsyncClient(timeout=AGENT_ZERO_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            try:
                return response.json()
            except (ValueError, json.JSONDecodeError) as e:
                logger.error("Agent Zero non-JSON at %s: %s (body: %s)", endpoint, e, response.text[:500])
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Agent orchestrator returned an unparseable response",
                )
    except HTTPException:
        raise
    except httpx.TimeoutException:
        logger.warning("Agent Zero timeout at %s", endpoint)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Agent orchestrator timed out",
        )
    except httpx.HTTPStatusError as e:
        logger.error("Agent Zero HTTP %d at %s", e.response.status_code, endpoint)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agent orchestrator error: {e.response.status_code}",
        )
    except httpx.RequestError as e:
        logger.warning("Agent Zero unreachable at %s: %s", endpoint, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent orchestrator is not available",
        )


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/orchestrate", tags=["orchestration"])


@router.post("/decompose", response_model=DecomposeResponse, summary="Decompose a task into subtasks via Agent Zero")
async def decompose_task(request: DecomposeRequest, _user_id: str = Depends(get_current_user)) -> DecomposeResponse:
    """Break a high-level task into coordinated subtasks via Agent Zero MCP."""
    task_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    result = await _agent_zero_request(
        "/mcp/command",
        {
            "command": "decompose",
            "params": {
                "task": request.task,
                "context": request.context or "",
                "max_subtasks": request.max_subtasks,
                "agent_hints": [h.value for h in request.agent_hints] if request.agent_hints else [],
            },
        },
    )

    subtasks = []
    for item in result.get("subtasks", result.get("steps", [])):
        agent_hint = item.get("suggested_agent", item.get("agent_type", "analysis"))
        try:
            agent_type = AgentType(agent_hint)
        except ValueError:
            agent_type = AgentType.ANALYSIS

        subtasks.append(
            SubtaskInfo(
                description=item.get("description", item.get("step", "")),
                priority=item.get("priority", 5),
                estimated_complexity=item.get("complexity", "medium"),
                suggested_agent=agent_type,
                dependencies=item.get("dependencies", []),
            )
        )

    _registry_put(task_id, {
        "task_id": task_id,
        "status": TaskStatus.COMPLETED.value,
        "original_task": request.task,
        "subtasks": {s.subtask_id: TaskStatus.PENDING.value for s in subtasks},
        "created_at": now,
        "updated_at": now,
    })

    return DecomposeResponse(
        task_id=task_id,
        original_task=request.task,
        subtasks=subtasks,
        created_at=now,
        metadata={"agent": "agent-zero", "subtask_count": len(subtasks)},
    )


@router.post("/dispatch", response_model=DispatchResponse, summary="Dispatch a subtask to an agent via Agent Zero")
async def dispatch_subtask(request: DispatchRequest, _user_id: str = Depends(get_current_user)) -> DispatchResponse:
    """Send a subtask to an appropriate agent for execution via Agent Zero MCP."""
    dispatch_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    result = await _agent_zero_request(
        "/mcp/command",
        {
            "command": "dispatch",
            "params": {
                "subtask_id": request.subtask_id,
                "task_id": request.task_id or "",
                "agent_type": request.agent_type.value,
                "payload": request.payload,
                "priority": request.priority,
                "timeout_seconds": request.timeout_seconds,
            },
        },
    )

    if request.task_id and request.task_id in _task_registry:
        task = _task_registry[request.task_id]
        task["subtasks"][request.subtask_id] = TaskStatus.IN_PROGRESS.value
        task["updated_at"] = now

    _registry_put(dispatch_id, {
        "task_id": dispatch_id,
        "parent_task_id": request.task_id,
        "subtask_id": request.subtask_id,
        "status": TaskStatus.IN_PROGRESS.value,
        "agent_type": request.agent_type.value,
        "created_at": now,
        "updated_at": now,
        "result": result,
    })

    return DispatchResponse(
        dispatch_id=dispatch_id,
        subtask_id=request.subtask_id,
        agent_type=request.agent_type,
        status=TaskStatus.IN_PROGRESS,
        queued_at=now,
    )


@router.get("/status/{task_id}", response_model=TaskStatusResponse, summary="Get task execution status")
async def get_task_status(task_id: str, _user_id: str = Depends(get_current_user)) -> TaskStatusResponse:
    """Check the execution status of a task or dispatch."""
    now = datetime.now(timezone.utc).isoformat()

    if task_id in _task_registry:
        task = _task_registry[task_id]
        task_status = TaskStatus(task.get("status", "pending"))

        subtask_statuses = {}
        for sid, s_status in task.get("subtasks", {}).items():
            subtask_statuses[sid] = TaskStatus(s_status)

        total = len(subtask_statuses)
        completed = sum(1 for s in subtask_statuses.values() if s == TaskStatus.COMPLETED)
        progress = int((completed / total * 100)) if total > 0 else 0

        return TaskStatusResponse(
            task_id=task_id,
            status=task_status,
            progress_percent=progress,
            created_at=task.get("created_at", now),
            updated_at=task.get("updated_at", now),
            subtask_statuses=subtask_statuses,
        )

    # Query Agent Zero for external task status
    try:
        result = await _agent_zero_request(
            "/mcp/command",
            {"command": "task_status", "params": {"task_id": task_id}},
        )
        return TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus(result.get("status", "pending")),
            progress_percent=result.get("progress", 0),
            created_at=result.get("created_at", now),
            updated_at=result.get("updated_at", now),
            result_preview=result.get("preview"),
        )
    except HTTPException as e:
        if e.status_code >= 500:
            raise  # Propagate infrastructure errors as-is
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )


@router.post("/aggregate", response_model=AggregateResponse, summary="Aggregate results from subtasks")
async def aggregate_results(request: AggregateRequest, _user_id: str = Depends(get_current_user)) -> AggregateResponse:
    """Combine results from multiple subtasks into a unified response."""
    subtask_results = []
    success_count = 0
    failure_count = 0
    merged_result: Dict[str, Any] = {}

    for subtask_id in request.subtask_ids:
        dispatch = None
        for entry in _task_registry.values():
            if entry.get("subtask_id") == subtask_id:
                dispatch = entry
                break

        if dispatch:
            task_status = TaskStatus(dispatch.get("status", "pending"))
            result_data = dispatch.get("result", {})

            if task_status == TaskStatus.COMPLETED:
                success_count += 1
            elif task_status == TaskStatus.FAILED:
                failure_count += 1

            subtask_results.append(
                SubtaskResult(
                    subtask_id=subtask_id,
                    status=task_status,
                    result=result_data if isinstance(result_data, dict) else {"data": result_data},
                    agent_type=AgentType(dispatch["agent_type"]) if dispatch.get("agent_type") else None,
                )
            )

            if result_data and isinstance(result_data, dict):
                if request.aggregation_strategy == "merge":
                    merged_result.update(result_data)
                elif request.aggregation_strategy == "concat":
                    merged_result[subtask_id] = result_data
        else:
            try:
                az_result = await _agent_zero_request(
                    "/mcp/command",
                    {"command": "task_result", "params": {"task_id": subtask_id}},
                )
                subtask_results.append(
                    SubtaskResult(
                        subtask_id=subtask_id,
                        status=TaskStatus(az_result.get("status", "completed")),
                        result=az_result.get("result", {}),
                    )
                )
                success_count += 1
                if request.aggregation_strategy == "merge":
                    merged_result.update(az_result.get("result", {}))
                elif request.aggregation_strategy == "concat":
                    merged_result[subtask_id] = az_result.get("result", {})
            except HTTPException as e:
                failure_count += 1
                subtask_results.append(
                    SubtaskResult(
                        subtask_id=subtask_id,
                        status=TaskStatus.FAILED,
                        result={"error": e.detail, "status_code": e.status_code},
                    )
                )

    if request.task_id in _task_registry:
        parent = _task_registry[request.task_id]
        all_done = all(
            sr.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            for sr in subtask_results
        )
        if all_done:
            parent["status"] = TaskStatus.COMPLETED.value if failure_count == 0 else TaskStatus.FAILED.value
        parent["updated_at"] = datetime.now(timezone.utc).isoformat()

    return AggregateResponse(
        task_id=request.task_id,
        aggregated_result=merged_result,
        subtask_results=subtask_results,
        aggregation_strategy=request.aggregation_strategy,
        success_count=success_count,
        failure_count=failure_count,
    )
