"""Thread Manager service for PMOVES-DoX.

This module implements Thread-Based Engineering patterns from the BoTZ blueprint
for multi-agent coordination. It supports four thread types:

Thread Types:
- BASE (B): Single linear execution with one agent
- PARALLEL (P): Concurrent agent execution with asyncio.gather
- CHAINED (C): Sequential pipeline passing outputs between agents
- FUSION (F): Multi-model consensus with aggregation

Thread Lifecycle:
- created -> running -> completed/failed

The service manages thread contexts, handles timeouts, and provides
status tracking for all active execution threads.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ThreadType(str, Enum):
    """Supported thread execution patterns.

    Attributes:
        BASE: Single agent linear execution.
        PARALLEL: Concurrent execution with multiple agents.
        CHAINED: Sequential pipeline with output passing.
        FUSION: Multi-model consensus aggregation.
    """

    BASE = "base"
    PARALLEL = "parallel"
    CHAINED = "chained"
    FUSION = "fusion"


class ThreadStatus(str, Enum):
    """Thread lifecycle states.

    Attributes:
        CREATED: Thread initialized but not yet started.
        RUNNING: Thread actively executing.
        COMPLETED: Thread finished successfully.
        FAILED: Thread terminated with error.
        TIMEOUT: Thread exceeded timeout limit.
    """

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ThreadConfig(BaseModel):
    """Configuration for creating a new execution thread.

    Attributes:
        thread_type: The execution pattern to use.
        agents: List of agent identifiers to participate in the thread.
        timeout_seconds: Maximum execution time before timeout (default: 60).
        consensus_threshold: Agreement threshold for fusion threads (default: 0.7).
        metadata: Optional additional configuration data.
    """

    thread_type: ThreadType
    agents: List[str]
    timeout_seconds: int = Field(default=60, ge=1, le=3600)
    consensus_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ThreadResult(BaseModel):
    """Result from a thread execution.

    Attributes:
        thread_id: Unique identifier for the thread.
        status: Final status of the thread.
        result: Output data from the execution.
        error: Error message if thread failed.
        execution_time_ms: Time taken for execution in milliseconds.
        agent_results: Individual results from each agent (for parallel/fusion).
    """

    thread_id: str
    status: ThreadStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    agent_results: Dict[str, Any] = Field(default_factory=dict)


class ThreadContext(BaseModel):
    """Runtime context for an active thread.

    Attributes:
        thread_id: Unique identifier for the thread.
        config: Thread configuration.
        status: Current lifecycle status.
        created_at: Timestamp when thread was created.
        started_at: Timestamp when execution began.
        completed_at: Timestamp when execution finished.
        result: Final result after completion.
        error: Error message if failed.
        agent_results: Individual agent outputs.
    """

    thread_id: str
    config: ThreadConfig
    status: ThreadStatus = ThreadStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    agent_results: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic model configuration."""

        arbitrary_types_allowed = True


class ConsensusResult(BaseModel):
    """Result from consensus aggregation in fusion threads.

    Attributes:
        consensus_reached: Whether agreement threshold was met.
        consensus_value: The agreed-upon value (if reached).
        agreement_score: Proportion of agents in agreement.
        votes: Individual agent votes/responses.
        method: Consensus method used (majority, weighted, etc.).
    """

    consensus_reached: bool
    consensus_value: Optional[Any] = None
    agreement_score: float = 0.0
    votes: Dict[str, Any] = Field(default_factory=dict)
    method: str = "majority"


# Type alias for agent executor functions
AgentExecutor = Callable[[str, str], Any]


class ThreadManager:
    """Manages execution threads for multi-agent coordination.

    This service implements Thread-Based Engineering patterns supporting
    base, parallel, chained, and fusion execution modes. It handles
    thread lifecycle management, timeout enforcement, and result aggregation.

    Attributes:
        _active_threads: Dictionary of active thread contexts by ID.
        _agent_executors: Registry of agent executor functions.
    """

    def __init__(self) -> None:
        """Initialize the ThreadManager.

        Creates a new instance with empty thread and executor registries.
        """
        self._active_threads: Dict[str, ThreadContext] = {}
        self._agent_executors: Dict[str, AgentExecutor] = {}
        self._default_executor: Optional[AgentExecutor] = None

    def register_agent(self, agent_id: str, executor: AgentExecutor) -> None:
        """Register an agent executor function.

        Args:
            agent_id: Unique identifier for the agent.
            executor: Async callable that takes (agent_id, task) and returns result.
        """
        self._agent_executors[agent_id] = executor
        logger.info(f"Registered agent executor: {agent_id}")

    def set_default_executor(self, executor: AgentExecutor) -> None:
        """Set a default executor for unregistered agents.

        Args:
            executor: Async callable to use when specific agent executor not found.
        """
        self._default_executor = executor
        logger.info("Set default agent executor")

    def _get_executor(self, agent_id: str) -> Optional[AgentExecutor]:
        """Get the executor for an agent.

        Args:
            agent_id: Agent identifier to look up.

        Returns:
            The registered executor, default executor, or None.
        """
        if agent_id in self._agent_executors:
            return self._agent_executors[agent_id]
        return self._default_executor

    async def create_thread(self, config: ThreadConfig) -> str:
        """Create a new execution thread and return its ID.

        Args:
            config: Thread configuration specifying type, agents, and parameters.

        Returns:
            The unique thread ID.

        Raises:
            ValueError: If configuration is invalid (e.g., no agents specified).
        """
        if not config.agents:
            raise ValueError("Thread config must specify at least one agent")

        thread_id = str(uuid.uuid4())
        context = ThreadContext(
            thread_id=thread_id,
            config=config,
            status=ThreadStatus.CREATED,
        )

        self._active_threads[thread_id] = context
        logger.info(
            f"Created thread {thread_id[:8]}... "
            f"type={config.thread_type.value} agents={config.agents}"
        )

        return thread_id

    def get_thread_status(self, thread_id: str) -> Optional[ThreadContext]:
        """Get current thread execution status.

        Args:
            thread_id: The thread identifier.

        Returns:
            ThreadContext with current status, or None if thread not found.
        """
        return self._active_threads.get(thread_id)

    def _update_status(
        self,
        thread_id: str,
        status: ThreadStatus,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update thread status and timestamps.

        Args:
            thread_id: Thread to update.
            status: New status.
            result: Result data if completed.
            error: Error message if failed.
        """
        context = self._active_threads.get(thread_id)
        if not context:
            return

        context.status = status
        now = datetime.now(timezone.utc)

        if status == ThreadStatus.RUNNING:
            context.started_at = now
        elif status in (ThreadStatus.COMPLETED, ThreadStatus.FAILED, ThreadStatus.TIMEOUT):
            context.completed_at = now
            context.result = result
            context.error = error

    async def execute_base(self, thread_id: str, task: str) -> ThreadResult:
        """Execute single-agent base thread.

        Runs a single agent with the given task. The first agent in the
        thread config is used for execution.

        Args:
            thread_id: The thread to execute.
            task: The task description/prompt for the agent.

        Returns:
            ThreadResult with execution outcome.
        """
        context = self._active_threads.get(thread_id)
        if not context:
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error="Thread not found",
            )

        if context.config.thread_type != ThreadType.BASE:
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error=f"Thread type mismatch: expected BASE, got {context.config.thread_type}",
            )

        self._update_status(thread_id, ThreadStatus.RUNNING)
        start_time = datetime.now(timezone.utc)

        agent_id = context.config.agents[0]
        executor = self._get_executor(agent_id)

        if not executor:
            self._update_status(
                thread_id, ThreadStatus.FAILED, error=f"No executor for agent: {agent_id}"
            )
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error=f"No executor for agent: {agent_id}",
            )

        try:
            result = await asyncio.wait_for(
                self._execute_agent(executor, agent_id, task),
                timeout=context.config.timeout_seconds,
            )

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            self._update_status(thread_id, ThreadStatus.COMPLETED, result=result)

            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.COMPLETED,
                result=result,
                execution_time_ms=execution_time,
                agent_results={agent_id: result},
            )

        except asyncio.TimeoutError:
            self._update_status(thread_id, ThreadStatus.TIMEOUT, error="Execution timeout")
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.TIMEOUT,
                error=f"Timeout after {context.config.timeout_seconds}s",
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Base thread {thread_id[:8]}... failed: {error_msg}")
            self._update_status(thread_id, ThreadStatus.FAILED, error=error_msg)
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error=error_msg,
            )

    async def execute_parallel(self, thread_id: str, tasks: List[str]) -> ThreadResult:
        """Execute parallel thread with multiple agents.

        Runs all configured agents concurrently using asyncio.gather.
        Each agent receives the corresponding task from the tasks list,
        or the first task if only one is provided.

        Args:
            thread_id: The thread to execute.
            tasks: List of tasks (one per agent, or single task for all).

        Returns:
            ThreadResult with all agent results.
        """
        context = self._active_threads.get(thread_id)
        if not context:
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error="Thread not found",
            )

        if context.config.thread_type != ThreadType.PARALLEL:
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error=f"Thread type mismatch: expected PARALLEL, got {context.config.thread_type}",
            )

        # Validate tasks list is not empty
        if not tasks:
            self._update_status(
                thread_id, ThreadStatus.FAILED, error="No tasks provided"
            )
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error="No tasks provided for parallel execution",
            )

        self._update_status(thread_id, ThreadStatus.RUNNING)
        start_time = datetime.now(timezone.utc)

        # Prepare tasks for each agent
        agent_tasks = []
        for i, agent_id in enumerate(context.config.agents):
            executor = self._get_executor(agent_id)
            if not executor:
                continue

            # Use corresponding task or first task if single task provided
            task = tasks[i] if i < len(tasks) else tasks[0]
            agent_tasks.append((agent_id, executor, task))

        if not agent_tasks:
            self._update_status(
                thread_id, ThreadStatus.FAILED, error="No valid agents with executors"
            )
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error="No valid agents with executors",
            )

        try:
            # Execute all agents concurrently
            coroutines = [
                self._execute_agent(executor, agent_id, task)
                for agent_id, executor, task in agent_tasks
            ]

            results = await asyncio.wait_for(
                asyncio.gather(*coroutines, return_exceptions=True),
                timeout=context.config.timeout_seconds,
            )

            # Collect results by agent
            agent_results = {}
            successful_results = []
            for i, result in enumerate(results):
                agent_id = agent_tasks[i][0]
                if isinstance(result, Exception):
                    agent_results[agent_id] = {"error": str(result)}
                else:
                    agent_results[agent_id] = result
                    successful_results.append(result)

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            # Store in context
            context.agent_results = agent_results
            self._update_status(thread_id, ThreadStatus.COMPLETED, result=successful_results)

            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.COMPLETED,
                result=successful_results,
                execution_time_ms=execution_time,
                agent_results=agent_results,
            )

        except asyncio.TimeoutError:
            self._update_status(thread_id, ThreadStatus.TIMEOUT, error="Execution timeout")
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.TIMEOUT,
                error=f"Timeout after {context.config.timeout_seconds}s",
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Parallel thread {thread_id[:8]}... failed: {error_msg}")
            self._update_status(thread_id, ThreadStatus.FAILED, error=error_msg)
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error=error_msg,
            )

    async def execute_chained(self, thread_id: str, task: str) -> ThreadResult:
        """Execute chained thread passing output between agents.

        Runs agents sequentially in a pipeline where each agent's output
        becomes the next agent's input. The initial task is passed to
        the first agent.

        Args:
            thread_id: The thread to execute.
            task: Initial task for the first agent in the chain.

        Returns:
            ThreadResult with final pipeline output.
        """
        context = self._active_threads.get(thread_id)
        if not context:
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error="Thread not found",
            )

        if context.config.thread_type != ThreadType.CHAINED:
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error=f"Thread type mismatch: expected CHAINED, got {context.config.thread_type}",
            )

        self._update_status(thread_id, ThreadStatus.RUNNING)
        start_time = datetime.now(timezone.utc)

        agent_results = {}
        current_input = task

        try:
            for agent_id in context.config.agents:
                executor = self._get_executor(agent_id)
                if not executor:
                    raise ValueError(f"No executor for agent: {agent_id}")

                # Calculate remaining time for timeout
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                remaining = context.config.timeout_seconds - elapsed

                if remaining <= 0:
                    raise asyncio.TimeoutError()

                result = await asyncio.wait_for(
                    self._execute_agent(executor, agent_id, str(current_input)),
                    timeout=remaining,
                )

                agent_results[agent_id] = result
                current_input = result  # Pass output to next agent

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            # Store in context
            context.agent_results = agent_results
            self._update_status(thread_id, ThreadStatus.COMPLETED, result=current_input)

            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.COMPLETED,
                result=current_input,
                execution_time_ms=execution_time,
                agent_results=agent_results,
            )

        except asyncio.TimeoutError:
            self._update_status(thread_id, ThreadStatus.TIMEOUT, error="Execution timeout")
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.TIMEOUT,
                error=f"Timeout after {context.config.timeout_seconds}s",
                agent_results=agent_results,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Chained thread {thread_id[:8]}... failed: {error_msg}")
            self._update_status(thread_id, ThreadStatus.FAILED, error=error_msg)
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error=error_msg,
                agent_results=agent_results,
            )

    async def execute_fusion(self, thread_id: str, task: str) -> ThreadResult:
        """Execute fusion thread with consensus aggregation.

        Runs all agents concurrently on the same task, then aggregates
        results using a consensus mechanism. Supports majority voting
        for discrete outputs and weighted averaging for numeric outputs.

        Args:
            thread_id: The thread to execute.
            task: The task for all agents.

        Returns:
            ThreadResult with consensus result.
        """
        context = self._active_threads.get(thread_id)
        if not context:
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error="Thread not found",
            )

        if context.config.thread_type != ThreadType.FUSION:
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error=f"Thread type mismatch: expected FUSION, got {context.config.thread_type}",
            )

        self._update_status(thread_id, ThreadStatus.RUNNING)
        start_time = datetime.now(timezone.utc)

        # Collect executors
        agent_tasks = []
        for agent_id in context.config.agents:
            executor = self._get_executor(agent_id)
            if executor:
                agent_tasks.append((agent_id, executor))

        if not agent_tasks:
            self._update_status(
                thread_id, ThreadStatus.FAILED, error="No valid agents with executors"
            )
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error="No valid agents with executors",
            )

        try:
            # Execute all agents concurrently
            coroutines = [
                self._execute_agent(executor, agent_id, task)
                for agent_id, executor in agent_tasks
            ]

            results = await asyncio.wait_for(
                asyncio.gather(*coroutines, return_exceptions=True),
                timeout=context.config.timeout_seconds,
            )

            # Collect valid results
            agent_results = {}
            valid_results = []
            for i, result in enumerate(results):
                agent_id = agent_tasks[i][0]
                if isinstance(result, Exception):
                    agent_results[agent_id] = {"error": str(result)}
                else:
                    agent_results[agent_id] = result
                    valid_results.append((agent_id, result))

            # Perform consensus aggregation
            consensus = self._compute_consensus(
                valid_results, context.config.consensus_threshold
            )

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            # Store in context
            context.agent_results = agent_results
            final_result = consensus.consensus_value if consensus.consensus_reached else None
            self._update_status(thread_id, ThreadStatus.COMPLETED, result=final_result)

            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.COMPLETED,
                result={
                    "consensus": consensus.model_dump(),
                    "agent_results": agent_results,
                },
                execution_time_ms=execution_time,
                agent_results=agent_results,
            )

        except asyncio.TimeoutError:
            self._update_status(thread_id, ThreadStatus.TIMEOUT, error="Execution timeout")
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.TIMEOUT,
                error=f"Timeout after {context.config.timeout_seconds}s",
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Fusion thread {thread_id[:8]}... failed: {error_msg}")
            self._update_status(thread_id, ThreadStatus.FAILED, error=error_msg)
            return ThreadResult(
                thread_id=thread_id,
                status=ThreadStatus.FAILED,
                error=error_msg,
            )

    def _compute_consensus(
        self, results: List[tuple], threshold: float
    ) -> ConsensusResult:
        """Compute consensus from multiple agent results.

        Uses majority voting for hashable types (strings, tuples, etc.)
        and weighted averaging for numeric types.

        Args:
            results: List of (agent_id, result) tuples.
            threshold: Required agreement proportion for consensus.

        Returns:
            ConsensusResult with consensus outcome.
        """
        if not results:
            return ConsensusResult(
                consensus_reached=False,
                agreement_score=0.0,
                votes={},
                method="none",
            )

        votes = {agent_id: result for agent_id, result in results}
        total_votes = len(results)

        # Check if results are numeric for averaging
        numeric_results = []
        for _, result in results:
            if isinstance(result, (int, float)):
                numeric_results.append(result)
            elif isinstance(result, dict) and "value" in result:
                val = result["value"]
                if isinstance(val, (int, float)):
                    numeric_results.append(val)

        if len(numeric_results) == total_votes and total_votes > 0:
            # Use weighted average for numeric results
            avg_value = sum(numeric_results) / total_votes

            # Calculate variance to determine agreement
            variance = sum((v - avg_value) ** 2 for v in numeric_results) / total_votes
            std_dev = variance ** 0.5

            # Agreement based on coefficient of variation
            # Handle zero-average case: if all values are zero, that's perfect agreement
            if avg_value == 0:
                agreement_score = 1.0 if variance == 0 else 0.0
            else:
                cv = std_dev / abs(avg_value)
                agreement_score = max(0.0, 1.0 - cv)

            return ConsensusResult(
                consensus_reached=agreement_score >= threshold,
                consensus_value=avg_value,
                agreement_score=agreement_score,
                votes=votes,
                method="weighted_average",
            )

        # Use majority voting for non-numeric results
        try:
            # Attempt to hash results for counting
            vote_counts: Dict[Any, int] = {}
            for _, result in results:
                # Convert to hashable if possible
                key = self._make_hashable(result)
                vote_counts[key] = vote_counts.get(key, 0) + 1

            # Find majority
            max_count = max(vote_counts.values())
            agreement_score = max_count / total_votes

            # Find consensus value
            consensus_value = None
            for _, result in results:
                key = self._make_hashable(result)
                if vote_counts[key] == max_count:
                    consensus_value = result
                    break

            return ConsensusResult(
                consensus_reached=agreement_score >= threshold,
                consensus_value=consensus_value,
                agreement_score=agreement_score,
                votes=votes,
                method="majority_vote",
            )

        except (TypeError, ValueError):
            # Fallback: no consensus possible
            return ConsensusResult(
                consensus_reached=False,
                agreement_score=0.0,
                votes=votes,
                method="failed",
            )

    def _make_hashable(self, obj: Any) -> Any:
        """Convert an object to a hashable form for voting.

        Args:
            obj: Object to convert.

        Returns:
            Hashable representation of the object.
        """
        if isinstance(obj, dict):
            return tuple(sorted((k, self._make_hashable(v)) for k, v in obj.items()))
        if isinstance(obj, list):
            return tuple(self._make_hashable(item) for item in obj)
        if isinstance(obj, set):
            return frozenset(self._make_hashable(item) for item in obj)
        return obj

    async def _execute_agent(
        self, executor: AgentExecutor, agent_id: str, task: str
    ) -> Any:
        """Execute a single agent with error handling.

        Args:
            executor: The agent's executor function.
            agent_id: Agent identifier for logging.
            task: Task to execute.

        Returns:
            Agent execution result.
        """
        logger.debug(f"Executing agent {agent_id} with task: {task[:50]}...")

        try:
            if asyncio.iscoroutinefunction(executor):
                result = await executor(agent_id, task)
            else:
                # Run sync executor in thread pool
                result = await asyncio.get_running_loop().run_in_executor(
                    None, executor, agent_id, task
                )
            return result

        except Exception as e:
            logger.error(f"Agent {agent_id} execution failed: {e}")
            raise

    def cleanup_thread(self, thread_id: str) -> bool:
        """Remove a completed thread from active tracking.

        Args:
            thread_id: Thread to clean up.

        Returns:
            True if thread was removed, False if not found.
        """
        if thread_id in self._active_threads:
            del self._active_threads[thread_id]
            logger.debug(f"Cleaned up thread {thread_id[:8]}...")
            return True
        return False

    def list_active_threads(self) -> List[ThreadContext]:
        """List all active threads.

        Returns:
            List of ThreadContext for all tracked threads.
        """
        return list(self._active_threads.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get thread manager statistics.

        Returns:
            Dictionary with thread counts by status and type.
        """
        stats = {
            "total_active": len(self._active_threads),
            "by_status": {},
            "by_type": {},
            "registered_agents": list(self._agent_executors.keys()),
            "has_default_executor": self._default_executor is not None,
        }

        for context in self._active_threads.values():
            # Count by status
            status = context.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # Count by type
            thread_type = context.config.thread_type.value
            stats["by_type"][thread_type] = stats["by_type"].get(thread_type, 0) + 1

        return stats


# Global singleton
thread_manager = ThreadManager()
