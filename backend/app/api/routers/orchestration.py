"""Orchestration router for multi-agent task decomposition and coordination.

This router implements endpoints for orchestrating complex tasks across
multiple agents, enabling task decomposition, dispatch, status tracking,
and result aggregation.

Endpoints:
    POST /orchestrate/decompose: Break a high-level task into subtasks
    POST /orchestrate/dispatch: Send a subtask to an appropriate agent
    GET /orchestrate/status/{task_id}: Check task execution status
    POST /orchestrate/aggregate: Combine results from multiple subtasks
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# =============================================================================
# Enums and Constants
# =============================================================================


class TaskStatus(str, Enum):
    """Status values for task lifecycle tracking."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    """Available agent types for task dispatch."""

    DOCUMENT = "document"
    SEARCH = "search"
    ANALYSIS = "analysis"
    REASONING = "reasoning"
    EXTRACTION = "extraction"


# =============================================================================
# In-Memory Task Storage
# =============================================================================


# In-memory storage for tasks (stub implementation)
_task_store: Dict[str, Dict[str, Any]] = {}


def _get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a task from the in-memory store.

    Args:
        task_id: The UUID of the task to retrieve.

    Returns:
        Task dictionary if found, None otherwise.
    """
    return _task_store.get(task_id)


def _update_task(task_id: str, updates: Dict[str, Any]) -> bool:
    """Update a task in the in-memory store.

    Args:
        task_id: The UUID of the task to update.
        updates: Dictionary of fields to update.

    Returns:
        True if task was found and updated, False otherwise.
    """
    if task_id not in _task_store:
        return False
    _task_store[task_id].update(updates)
    _task_store[task_id]["updated_at"] = datetime.utcnow().isoformat()
    return True


# =============================================================================
# Request/Response Models
# =============================================================================


class DecomposeRequest(BaseModel):
    """Request model for task decomposition.

    Attributes:
        task: The high-level task description to decompose.
        context: Optional context or constraints for decomposition.
        max_subtasks: Maximum number of subtasks to generate (1-20).
        agent_hints: Optional list of preferred agent types.
    """

    task: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="High-level task description to decompose",
    )
    context: Optional[str] = Field(
        None,
        max_length=8192,
        description="Optional context or constraints for decomposition",
    )
    max_subtasks: int = Field(
        5,
        ge=1,
        le=20,
        description="Maximum number of subtasks to generate",
    )
    agent_hints: Optional[List[AgentType]] = Field(
        None,
        description="Preferred agent types for subtask assignment",
    )


class SubtaskInfo(BaseModel):
    """Information about a single subtask.

    Attributes:
        subtask_id: Unique identifier for this subtask.
        description: Description of what the subtask should accomplish.
        priority: Priority level (1=highest, 10=lowest).
        estimated_complexity: Estimated complexity (low, medium, high).
        suggested_agent: Suggested agent type for execution.
        dependencies: List of subtask IDs this depends on.
    """

    subtask_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    priority: int = Field(1, ge=1, le=10)
    estimated_complexity: str = Field("medium", pattern="^(low|medium|high)$")
    suggested_agent: AgentType = Field(AgentType.ANALYSIS)
    dependencies: List[str] = Field(default_factory=list)


class DecomposeResponse(BaseModel):
    """Response model for task decomposition.

    Attributes:
        task_id: Unique identifier for the parent task.
        original_task: The original task that was decomposed.
        subtasks: List of generated subtasks.
        created_at: Timestamp when decomposition was created.
        metadata: Additional metadata about the decomposition.
    """

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    original_task: str
    subtasks: List[SubtaskInfo] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DispatchRequest(BaseModel):
    """Request model for subtask dispatch.

    Attributes:
        subtask_id: ID of the subtask to dispatch.
        task_id: Parent task ID (optional, for tracking).
        agent_type: Target agent type for execution.
        payload: Task-specific payload for the agent.
        priority: Execution priority (1=highest).
        timeout_seconds: Maximum execution time in seconds.
    """

    subtask_id: str = Field(..., description="ID of the subtask to dispatch")
    task_id: Optional[str] = Field(None, description="Parent task ID")
    agent_type: AgentType = Field(..., description="Target agent type")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Task-specific payload for the agent",
    )
    priority: int = Field(5, ge=1, le=10, description="Execution priority")
    timeout_seconds: int = Field(
        300,
        ge=1,
        le=3600,
        description="Maximum execution time in seconds",
    )


class DispatchResponse(BaseModel):
    """Response model for subtask dispatch.

    Attributes:
        dispatch_id: Unique identifier for this dispatch operation.
        subtask_id: ID of the dispatched subtask.
        agent_type: Agent type the task was dispatched to.
        status: Current dispatch status.
        queued_at: Timestamp when task was queued.
        estimated_start: Estimated start time (if available).
    """

    dispatch_id: str = Field(default_factory=lambda: str(uuid4()))
    subtask_id: str
    agent_type: AgentType
    status: TaskStatus = Field(TaskStatus.PENDING)
    queued_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    estimated_start: Optional[str] = Field(None)


class TaskStatusResponse(BaseModel):
    """Response model for task status inquiry.

    Attributes:
        task_id: The task identifier.
        status: Current task status.
        progress_percent: Completion progress (0-100).
        created_at: When the task was created.
        updated_at: When the task was last updated.
        started_at: When execution started (if applicable).
        completed_at: When execution completed (if applicable).
        subtask_statuses: Status of each subtask (if decomposed).
        result_preview: Preview of results (if completed).
        error_message: Error message (if failed).
    """

    task_id: str
    status: TaskStatus
    progress_percent: int = Field(0, ge=0, le=100)
    created_at: str
    updated_at: str
    started_at: Optional[str] = Field(None)
    completed_at: Optional[str] = Field(None)
    subtask_statuses: Dict[str, TaskStatus] = Field(default_factory=dict)
    result_preview: Optional[str] = Field(None)
    error_message: Optional[str] = Field(None)


class AggregateRequest(BaseModel):
    """Request model for result aggregation.

    Attributes:
        task_id: Parent task ID to aggregate results for.
        subtask_ids: List of subtask IDs to include in aggregation.
        aggregation_strategy: How to combine results.
        include_metadata: Whether to include execution metadata.
    """

    task_id: str = Field(..., description="Parent task ID")
    subtask_ids: List[str] = Field(
        ...,
        min_length=1,
        description="List of subtask IDs to aggregate",
    )
    aggregation_strategy: str = Field(
        "merge",
        pattern="^(merge|concat|weighted|custom)$",
        description="Strategy for combining results",
    )
    include_metadata: bool = Field(
        True,
        description="Include execution metadata in result",
    )


class SubtaskResult(BaseModel):
    """Result from a single subtask.

    Attributes:
        subtask_id: ID of the subtask.
        status: Final status of the subtask.
        result: The subtask's output data.
        execution_time_ms: Execution time in milliseconds.
        agent_type: Agent that executed the subtask.
    """

    subtask_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = Field(None)
    execution_time_ms: Optional[int] = Field(None)
    agent_type: Optional[AgentType] = Field(None)


class AggregateResponse(BaseModel):
    """Response model for result aggregation.

    Attributes:
        task_id: Parent task ID.
        aggregated_result: Combined result from all subtasks.
        subtask_results: Individual results from each subtask.
        aggregation_strategy: Strategy used for aggregation.
        total_execution_time_ms: Total execution time in milliseconds.
        success_count: Number of successful subtasks.
        failure_count: Number of failed subtasks.
        aggregated_at: Timestamp of aggregation.
    """

    task_id: str
    aggregated_result: Dict[str, Any] = Field(default_factory=dict)
    subtask_results: List[SubtaskResult] = Field(default_factory=list)
    aggregation_strategy: str
    total_execution_time_ms: int = Field(0)
    success_count: int = Field(0)
    failure_count: int = Field(0)
    aggregated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


# =============================================================================
# Router Definition
# =============================================================================


router = APIRouter(prefix="/orchestrate", tags=["orchestration"])


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/decompose",
    response_model=DecomposeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Decompose a task into subtasks",
    responses={
        201: {"description": "Task successfully decomposed"},
        400: {"description": "Invalid request parameters"},
    },
)
async def decompose_task(request: DecomposeRequest) -> DecomposeResponse:
    """Break a high-level task into coordinated subtasks.

    This endpoint analyzes a complex task and decomposes it into smaller,
    actionable subtasks that can be dispatched to specialized agents.
    The decomposition considers task complexity, agent capabilities,
    and potential dependencies between subtasks.

    Args:
        request: DecomposeRequest containing the task and constraints.

    Returns:
        DecomposeResponse with the generated subtasks and metadata.

    Example:
        ```json
        {
            "task": "Analyze the Q3 financial report and extract key metrics",
            "context": "Focus on revenue growth and operating margins",
            "max_subtasks": 4
        }
        ```
    """
    task_id = str(uuid4())
    created_at = datetime.utcnow().isoformat()

    # Generate mock subtasks based on the request
    mock_subtasks = _generate_mock_subtasks(
        request.task,
        request.max_subtasks,
        request.agent_hints,
    )

    # Store the task in memory
    _task_store[task_id] = {
        "task_id": task_id,
        "original_task": request.task,
        "context": request.context,
        "subtasks": [st.model_dump() for st in mock_subtasks],
        "status": TaskStatus.PENDING.value,
        "created_at": created_at,
        "updated_at": created_at,
    }

    return DecomposeResponse(
        task_id=task_id,
        original_task=request.task,
        subtasks=mock_subtasks,
        created_at=created_at,
        metadata={
            "decomposition_version": "1.0.0",
            "strategy": "rule_based_mock",
            "agent_hints_applied": request.agent_hints is not None,
        },
    )


@router.post(
    "/dispatch",
    response_model=DispatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Dispatch a subtask to an agent",
    responses={
        202: {"description": "Subtask accepted for dispatch"},
        400: {"description": "Invalid dispatch request"},
        404: {"description": "Subtask not found"},
    },
)
async def dispatch_subtask(request: DispatchRequest) -> DispatchResponse:
    """Send a subtask to an appropriate agent for execution.

    This endpoint dispatches a subtask to the specified agent type.
    The dispatch is asynchronous - the endpoint returns immediately
    with a dispatch ID that can be used to track execution status.

    Args:
        request: DispatchRequest with subtask details and target agent.

    Returns:
        DispatchResponse with dispatch confirmation and tracking info.

    Note:
        This is a stub implementation that simulates dispatch.
        Full implementation requires agent registry integration.
    """
    dispatch_id = str(uuid4())
    queued_at = datetime.utcnow().isoformat()

    # Store dispatch information
    dispatch_key = f"dispatch_{dispatch_id}"
    _task_store[dispatch_key] = {
        "dispatch_id": dispatch_id,
        "subtask_id": request.subtask_id,
        "task_id": request.task_id,
        "agent_type": request.agent_type.value,
        "payload": request.payload,
        "priority": request.priority,
        "timeout_seconds": request.timeout_seconds,
        "status": TaskStatus.PENDING.value,
        "queued_at": queued_at,
        "updated_at": queued_at,
    }

    # Simulate status transition to in_progress
    _task_store[dispatch_key]["status"] = TaskStatus.IN_PROGRESS.value
    _task_store[dispatch_key]["started_at"] = datetime.utcnow().isoformat()

    return DispatchResponse(
        dispatch_id=dispatch_id,
        subtask_id=request.subtask_id,
        agent_type=request.agent_type,
        status=TaskStatus.IN_PROGRESS,
        queued_at=queued_at,
        estimated_start=None,
    )


@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task execution status",
    responses={
        200: {"description": "Task status retrieved successfully"},
        404: {"description": "Task not found"},
    },
)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Check the execution status of a task or dispatch.

    This endpoint returns the current status of a task, including
    progress percentage, timestamps, and subtask statuses if the
    task was decomposed.

    Args:
        task_id: UUID of the task or dispatch to check.

    Returns:
        TaskStatusResponse with current status and progress info.

    Raises:
        HTTPException: 404 if task_id is not found.
    """
    # Check for task in store
    task = _get_task(task_id)

    # Also check dispatch entries
    if task is None:
        task = _get_task(f"dispatch_{task_id}")

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{task_id}' not found",
        )

    # Calculate progress based on subtasks if present
    subtask_statuses = {}
    progress = 0
    if "subtasks" in task:
        subtasks = task["subtasks"]
        if subtasks:
            completed = sum(
                1 for st in subtasks
                if st.get("status") == TaskStatus.COMPLETED.value
            )
            progress = int((completed / len(subtasks)) * 100)
            subtask_statuses = {
                st["subtask_id"]: TaskStatus(
                    st.get("status", TaskStatus.PENDING.value)
                )
                for st in subtasks
            }

    current_status = TaskStatus(task.get("status", TaskStatus.PENDING.value))

    # Simulate completion for demo purposes
    if current_status == TaskStatus.IN_PROGRESS:
        progress = 50

    return TaskStatusResponse(
        task_id=task_id,
        status=current_status,
        progress_percent=progress,
        created_at=task.get("created_at", datetime.utcnow().isoformat()),
        updated_at=task.get("updated_at", datetime.utcnow().isoformat()),
        started_at=task.get("started_at"),
        completed_at=task.get("completed_at"),
        subtask_statuses=subtask_statuses,
        result_preview=task.get("result_preview"),
        error_message=task.get("error_message"),
    )


@router.post(
    "/aggregate",
    response_model=AggregateResponse,
    status_code=status.HTTP_200_OK,
    summary="Aggregate results from subtasks",
    responses={
        200: {"description": "Results aggregated successfully"},
        400: {"description": "Invalid aggregation request"},
        404: {"description": "Task or subtasks not found"},
    },
)
async def aggregate_results(request: AggregateRequest) -> AggregateResponse:
    """Combine results from multiple subtasks into a unified response.

    This endpoint aggregates the results from completed subtasks
    using the specified aggregation strategy. It supports various
    strategies including merge, concatenation, and weighted combination.

    Args:
        request: AggregateRequest specifying which subtasks to combine.

    Returns:
        AggregateResponse with combined results and execution metadata.

    Raises:
        HTTPException: 404 if task_id is not found.
    """
    # Verify parent task exists
    task = _get_task(request.task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID '{request.task_id}' not found",
        )

    # Generate mock subtask results
    subtask_results = []
    total_time = 0
    success_count = 0
    failure_count = 0

    for subtask_id in request.subtask_ids:
        # Simulate completed subtask results
        exec_time = 150 + (hash(subtask_id) % 500)  # Mock execution time
        is_success = hash(subtask_id) % 10 != 0  # 90% success rate

        result = SubtaskResult(
            subtask_id=subtask_id,
            status=TaskStatus.COMPLETED if is_success else TaskStatus.FAILED,
            result={"data": f"Result for {subtask_id[:8]}..."} if is_success else None,
            execution_time_ms=exec_time,
            agent_type=AgentType.ANALYSIS,
        )
        subtask_results.append(result)
        total_time += exec_time

        if is_success:
            success_count += 1
        else:
            failure_count += 1

    # Generate aggregated result based on strategy
    aggregated_result = _aggregate_by_strategy(
        subtask_results,
        request.aggregation_strategy,
    )

    # Update parent task status
    if failure_count == 0:
        _update_task(request.task_id, {
            "status": TaskStatus.COMPLETED.value,
            "completed_at": datetime.utcnow().isoformat(),
        })
    elif success_count == 0:
        _update_task(request.task_id, {
            "status": TaskStatus.FAILED.value,
            "error_message": "All subtasks failed",
        })

    return AggregateResponse(
        task_id=request.task_id,
        aggregated_result=aggregated_result,
        subtask_results=subtask_results,
        aggregation_strategy=request.aggregation_strategy,
        total_execution_time_ms=total_time,
        success_count=success_count,
        failure_count=failure_count,
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _generate_mock_subtasks(
    task: str,
    max_subtasks: int,
    agent_hints: Optional[List[AgentType]],
) -> List[SubtaskInfo]:
    """Generate mock subtasks for demonstration.

    This stub implementation generates realistic-looking subtasks
    based on common patterns in the input task description.

    Args:
        task: The original task description.
        max_subtasks: Maximum number of subtasks to generate.
        agent_hints: Optional preferred agent types.

    Returns:
        List of SubtaskInfo objects representing the decomposition.
    """
    # Default agent rotation if no hints provided
    default_agents = [
        AgentType.DOCUMENT,
        AgentType.SEARCH,
        AgentType.ANALYSIS,
        AgentType.EXTRACTION,
        AgentType.REASONING,
    ]
    agents = agent_hints if agent_hints else default_agents

    # Generate subtasks based on task keywords
    subtasks = []
    task_lower = task.lower()

    subtask_templates = [
        ("Parse and extract document structure", AgentType.DOCUMENT, "low"),
        ("Search for relevant context", AgentType.SEARCH, "medium"),
        ("Analyze extracted content", AgentType.ANALYSIS, "high"),
        ("Extract key entities and metrics", AgentType.EXTRACTION, "medium"),
        ("Synthesize findings and conclusions", AgentType.REASONING, "high"),
    ]

    # Adjust templates based on task content
    if "financial" in task_lower or "report" in task_lower:
        subtask_templates[2] = (
            "Analyze financial metrics and trends",
            AgentType.ANALYSIS,
            "high",
        )
        subtask_templates[3] = (
            "Extract key financial indicators",
            AgentType.EXTRACTION,
            "medium",
        )

    if "search" in task_lower or "find" in task_lower:
        subtask_templates[1] = (
            "Perform semantic search across documents",
            AgentType.SEARCH,
            "medium",
        )

    # Create subtasks up to max_subtasks
    for i, (desc, default_agent, complexity) in enumerate(subtask_templates):
        if i >= max_subtasks:
            break

        # Use hint agent if available, otherwise default
        agent = agents[i % len(agents)] if agent_hints else default_agent

        subtask = SubtaskInfo(
            description=desc,
            priority=i + 1,
            estimated_complexity=complexity,
            suggested_agent=agent,
            dependencies=[subtasks[i - 1].subtask_id] if i > 0 else [],
        )
        subtasks.append(subtask)

    return subtasks


def _aggregate_by_strategy(
    results: List[SubtaskResult],
    strategy: str,
) -> Dict[str, Any]:
    """Aggregate subtask results using the specified strategy.

    Args:
        results: List of subtask results to aggregate.
        strategy: Aggregation strategy (merge, concat, weighted, custom).

    Returns:
        Dictionary containing the aggregated result.
    """
    successful_results = [
        r for r in results if r.status == TaskStatus.COMPLETED and r.result
    ]

    if strategy == "merge":
        # Merge all result dictionaries
        merged = {}
        for r in successful_results:
            if r.result:
                merged[r.subtask_id] = r.result
        return {"merged_data": merged, "strategy": "merge"}

    elif strategy == "concat":
        # Concatenate results as a list
        return {
            "concatenated_data": [r.result for r in successful_results],
            "strategy": "concat",
        }

    elif strategy == "weighted":
        # Weight by execution time (faster = higher weight)
        weighted_data = []
        total_inverse_time = sum(
            1 / (r.execution_time_ms or 1) for r in successful_results
        )
        for r in successful_results:
            weight = (1 / (r.execution_time_ms or 1)) / total_inverse_time
            weighted_data.append({
                "subtask_id": r.subtask_id,
                "weight": round(weight, 4),
                "result": r.result,
            })
        return {"weighted_data": weighted_data, "strategy": "weighted"}

    else:  # custom
        return {
            "custom_data": [r.result for r in successful_results],
            "strategy": "custom",
            "note": "Custom aggregation requires implementation",
        }
