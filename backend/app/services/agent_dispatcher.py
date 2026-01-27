"""Agent Dispatcher service for PMOVES-DoX.

This module provides agent discovery and task dispatching capabilities
via the A2A (Agent-to-Agent) protocol. It enables discovering available
agents by fetching their agent-cards and routing tasks based on capability
matching.

Threading Models:
- P-threads (Parallel): Dispatch multiple tasks concurrently to different agents
- C-threads (Sequential): Chain tasks sequentially, passing results between steps

Caching:
- Discovered agents are cached with configurable TTL
- Set AGENT_CACHE_TTL_SECONDS to control cache duration (default: 300 seconds)
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

from app.models.agent_card import AgentCard, AgentCapability


logger = logging.getLogger(__name__)

# Configuration
DEFAULT_CACHE_TTL_SECONDS = 300  # 5 minutes
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30


class TaskStatus(str, Enum):
    """Status of a dispatched task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AgentInfo(BaseModel):
    """Information about a discovered agent.

    Represents an agent discovered via the A2A protocol, including
    its capabilities, endpoint, and metadata from the agent-card.

    Attributes:
        agent_id: Unique identifier for the agent (derived from endpoint)
        name: Human-readable agent name
        version: Semantic version of the agent
        endpoint: Base URL for the agent's API
        description: Brief description of agent functionality
        capabilities: List of capability URIs supported by the agent
        capability_details: Full capability objects with parameters
        input_modalities: MIME types accepted as input
        output_modalities: MIME types produced as output
        last_seen: Timestamp of last successful contact
        is_available: Whether the agent is currently reachable
    """

    agent_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    version: str = "1.0.0"
    endpoint: str
    description: str = ""
    capabilities: List[str] = Field(default_factory=list)
    capability_details: List[AgentCapability] = Field(default_factory=list)
    input_modalities: List[str] = Field(default_factory=list)
    output_modalities: List[str] = Field(default_factory=list)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    is_available: bool = True


class Task(BaseModel):
    """A task to be dispatched to an agent.

    Represents a unit of work that can be sent to an agent for execution.
    Tasks can be dispatched individually, in parallel (P-threads), or
    chained sequentially (C-threads).

    Attributes:
        task_id: Unique identifier for the task
        description: Human-readable description of the task
        payload: Data/parameters to send to the agent
        required_capabilities: Capability URIs the target agent must support
        timeout_seconds: Maximum time to wait for completion
        priority: Task priority (1-10, higher = more important)
        depends_on: List of task IDs this task depends on (for C-threads)
        metadata: Additional metadata for the task
    """

    task_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)
    required_capabilities: List[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=60, ge=1, le=3600)
    priority: int = Field(default=5, ge=1, le=10)
    depends_on: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DispatchResult(BaseModel):
    """Result from dispatching a task to an agent.

    Contains the outcome of task execution, including status, response
    data, and timing information.

    Attributes:
        task_id: ID of the dispatched task
        agent_id: ID of the agent that handled the task
        status: Current status of the task
        response: Response data from the agent (if completed)
        error_message: Error description (if failed)
        start_time: When execution started
        end_time: When execution completed
        duration_ms: Total execution time in milliseconds
    """

    task_id: str
    agent_id: str
    status: TaskStatus = TaskStatus.PENDING
    response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None

    def mark_completed(self, response: Dict[str, Any]) -> None:
        """Mark task as successfully completed with response data."""
        self.status = TaskStatus.COMPLETED
        self.response = response
        self.end_time = datetime.utcnow()
        self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)

    def mark_failed(self, error_message: str) -> None:
        """Mark task as failed with error message."""
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        self.end_time = datetime.utcnow()
        self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)

    def mark_timeout(self) -> None:
        """Mark task as timed out."""
        self.status = TaskStatus.TIMEOUT
        self.error_message = "Task execution timed out"
        self.end_time = datetime.utcnow()
        self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)


class CachedAgent:
    """Wrapper for cached agent information with TTL tracking."""

    def __init__(self, agent_info: AgentInfo, ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS):
        """Initialize cached agent with TTL.

        Args:
            agent_info: The agent information to cache.
            ttl_seconds: Time-to-live in seconds before cache expires.
        """
        self.agent_info = agent_info
        self.cached_at = datetime.utcnow()
        self.expires_at = self.cached_at + timedelta(seconds=ttl_seconds)

    @property
    def is_expired(self) -> bool:
        """Check if the cached entry has expired."""
        return datetime.utcnow() > self.expires_at


class AgentDispatcher:
    """Discovers and dispatches tasks to available agents.

    This service handles agent discovery via the A2A protocol and routes
    tasks to agents based on capability matching. It supports both parallel
    (P-threads) and sequential (C-threads) task execution patterns.

    The dispatcher maintains a cache of discovered agents to minimize
    network requests during task routing.

    Attributes:
        _agent_cache: Dictionary mapping endpoint URLs to cached agent info.
        _cache_ttl_seconds: TTL for cached agent entries.
        _request_timeout_seconds: Timeout for HTTP requests to agents.
        _known_endpoints: Set of agent endpoints to probe during discovery.
    """

    def __init__(self) -> None:
        """Initialize the AgentDispatcher.

        Creates a new instance with empty cache. Configure via environment
        variables:
        - AGENT_CACHE_TTL_SECONDS: Cache duration (default: 300)
        - AGENT_REQUEST_TIMEOUT_SECONDS: HTTP request timeout (default: 30)
        - AGENT_ENDPOINTS: Comma-separated list of agent base URLs to discover
        """
        self._agent_cache: Dict[str, CachedAgent] = {}
        self._cache_ttl_seconds = int(
            os.getenv("AGENT_CACHE_TTL_SECONDS", str(DEFAULT_CACHE_TTL_SECONDS))
        )
        self._request_timeout_seconds = int(
            os.getenv("AGENT_REQUEST_TIMEOUT_SECONDS", str(DEFAULT_REQUEST_TIMEOUT_SECONDS))
        )
        # Known endpoints to probe during discovery
        self._known_endpoints: List[str] = self._load_known_endpoints()

    def _load_known_endpoints(self) -> List[str]:
        """Load known agent endpoints from configuration.

        Reads AGENT_ENDPOINTS environment variable as comma-separated list.
        Falls back to default internal agents if not configured.

        Returns:
            List of agent base URLs to probe during discovery.
        """
        endpoints_env = os.getenv("AGENT_ENDPOINTS", "")
        if endpoints_env:
            return [ep.strip() for ep in endpoints_env.split(",") if ep.strip()]

        # Default: check for common internal agents
        default_endpoints = [
            "http://localhost:8000",  # Self (PMOVES-DoX)
            "http://pmoves-agent-zero:50051",  # Agent Zero if docked
            "http://ollama:11434",  # Ollama if available
        ]
        return default_endpoints

    def add_endpoint(self, endpoint: str) -> None:
        """Add an endpoint to the list of known agents to discover.

        Args:
            endpoint: Base URL of the agent to add.
        """
        if endpoint not in self._known_endpoints:
            self._known_endpoints.append(endpoint)
            logger.info(f"Added agent endpoint: {endpoint}")

    def remove_endpoint(self, endpoint: str) -> None:
        """Remove an endpoint from the list of known agents.

        Args:
            endpoint: Base URL of the agent to remove.
        """
        if endpoint in self._known_endpoints:
            self._known_endpoints.remove(endpoint)
            # Also remove from cache
            if endpoint in self._agent_cache:
                del self._agent_cache[endpoint]
            logger.info(f"Removed agent endpoint: {endpoint}")

    async def _fetch_agent_card(self, endpoint: str) -> Optional[AgentInfo]:
        """Fetch agent-card from a single endpoint.

        Attempts to retrieve the agent-card from the well-known endpoint
        and parse it into an AgentInfo model.

        Args:
            endpoint: Base URL of the agent to query.

        Returns:
            AgentInfo if successful, None if unreachable or invalid.
        """
        agent_card_url = f"{endpoint.rstrip('/')}/.well-known/agent-card"

        try:
            async with httpx.AsyncClient(timeout=self._request_timeout_seconds) as client:
                response = await client.get(agent_card_url)
                response.raise_for_status()

                data = response.json()

                # Extract capability URIs from capability details
                capability_uris = []
                capability_details = []
                for cap in data.get("capabilities", []):
                    if isinstance(cap, dict):
                        capability_uris.append(cap.get("uri", ""))
                        capability_details.append(
                            AgentCapability(
                                uri=cap.get("uri", ""),
                                description=cap.get("description", ""),
                                required=cap.get("required", False),
                                params=cap.get("params"),
                            )
                        )

                agent_info = AgentInfo(
                    agent_id=f"agent-{endpoint.replace('://', '-').replace('/', '-').replace(':', '-')}",
                    name=data.get("name", "Unknown Agent"),
                    version=data.get("version", "1.0.0"),
                    endpoint=endpoint,
                    description=data.get("description", ""),
                    capabilities=capability_uris,
                    capability_details=capability_details,
                    input_modalities=data.get("inputModalities", []),
                    output_modalities=data.get("outputModalities", []),
                    last_seen=datetime.utcnow(),
                    is_available=True,
                )

                logger.info(f"Discovered agent: {agent_info.name} at {endpoint}")
                return agent_info

        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching agent-card from {endpoint}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error fetching agent-card from {endpoint}: {e.response.status_code}")
            return None
        except httpx.RequestError as e:
            logger.debug(f"Request error fetching agent-card from {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching agent-card from {endpoint}: {e}")
            return None

    async def discover_agents(self) -> List[AgentInfo]:
        """Discover available agents via A2A protocol.

        Probes all known endpoints to fetch their agent-cards. Results are
        cached for subsequent capability matching and task dispatch.

        Returns:
            List of AgentInfo for all reachable agents.
        """
        logger.info(f"Discovering agents from {len(self._known_endpoints)} endpoints")

        # Fetch agent-cards concurrently
        tasks = [self._fetch_agent_card(endpoint) for endpoint in self._known_endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        discovered_agents: List[AgentInfo] = []

        for endpoint, result in zip(self._known_endpoints, results):
            if isinstance(result, Exception):
                logger.warning(f"Error discovering agent at {endpoint}: {result}")
                # Mark cached agent as unavailable if present
                if endpoint in self._agent_cache:
                    self._agent_cache[endpoint].agent_info.is_available = False
            elif result is not None:
                # Cache the discovered agent
                self._agent_cache[endpoint] = CachedAgent(result, self._cache_ttl_seconds)
                discovered_agents.append(result)

        logger.info(f"Discovered {len(discovered_agents)} agents")
        return discovered_agents

    def _get_cached_agents(self) -> List[AgentInfo]:
        """Get all cached agents that haven't expired.

        Returns:
            List of non-expired cached AgentInfo.
        """
        valid_agents: List[AgentInfo] = []

        for endpoint, cached in list(self._agent_cache.items()):
            if cached.is_expired:
                logger.debug(f"Cache expired for agent at {endpoint}")
                del self._agent_cache[endpoint]
            elif cached.agent_info.is_available:
                valid_agents.append(cached.agent_info)

        return valid_agents

    async def match_capabilities(
        self, task: str, required_caps: List[str]
    ) -> List[AgentInfo]:
        """Find agents with matching capabilities.

        Searches cached agents (or discovers if cache is empty) for those
        that support all required capabilities.

        Args:
            task: Description of the task (for logging/debugging).
            required_caps: List of capability URIs the agent must support.

        Returns:
            List of AgentInfo for agents matching all required capabilities.
        """
        logger.debug(f"Matching capabilities for task: {task}")
        logger.debug(f"Required capabilities: {required_caps}")

        # Get cached agents or discover if empty
        agents = self._get_cached_agents()
        if not agents:
            agents = await self.discover_agents()

        if not required_caps:
            # No specific requirements, return all available agents
            logger.debug(f"No capability requirements, returning all {len(agents)} agents")
            return agents

        matching_agents: List[AgentInfo] = []

        for agent in agents:
            agent_caps = set(agent.capabilities)
            required_set = set(required_caps)

            # Check if agent has all required capabilities
            if required_set.issubset(agent_caps):
                matching_agents.append(agent)
                logger.debug(f"Agent {agent.name} matches all required capabilities")
            else:
                missing = required_set - agent_caps
                logger.debug(f"Agent {agent.name} missing capabilities: {missing}")

        logger.info(
            f"Found {len(matching_agents)} agents matching capabilities for task: {task}"
        )
        return matching_agents

    async def dispatch_task(self, agent_id: str, task: Task) -> DispatchResult:
        """Send task to specific agent and track execution.

        Dispatches the task to the specified agent's orchestration endpoint
        and tracks the execution status.

        Args:
            agent_id: ID of the target agent.
            task: Task to dispatch.

        Returns:
            DispatchResult with execution status and response.
        """
        result = DispatchResult(task_id=task.task_id, agent_id=agent_id)
        result.status = TaskStatus.IN_PROGRESS

        # Find the agent by ID
        target_agent: Optional[AgentInfo] = None
        for cached in self._agent_cache.values():
            if cached.agent_info.agent_id == agent_id:
                target_agent = cached.agent_info
                break

        if target_agent is None:
            result.mark_failed(f"Agent not found: {agent_id}")
            logger.error(f"Cannot dispatch task: agent {agent_id} not found")
            return result

        if not target_agent.is_available:
            result.mark_failed(f"Agent unavailable: {agent_id}")
            logger.warning(f"Cannot dispatch task: agent {agent_id} is unavailable")
            return result

        # Dispatch to agent's task endpoint
        task_url = f"{target_agent.endpoint.rstrip('/')}/a2a/task/execute"

        try:
            async with httpx.AsyncClient(timeout=task.timeout_seconds) as client:
                response = await client.post(
                    task_url,
                    json={
                        "task_id": task.task_id,
                        "description": task.description,
                        "payload": task.payload,
                        "metadata": task.metadata,
                    },
                )
                response.raise_for_status()

                response_data = response.json()
                result.mark_completed(response_data)
                logger.info(
                    f"Task {task.task_id} completed on agent {agent_id} "
                    f"in {result.duration_ms}ms"
                )

        except httpx.TimeoutException:
            result.mark_timeout()
            logger.warning(f"Task {task.task_id} timed out on agent {agent_id}")
            # Mark agent as potentially unavailable
            target_agent.is_available = False

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            result.mark_failed(error_msg)
            logger.error(f"Task {task.task_id} failed on agent {agent_id}: {error_msg}")

        except httpx.RequestError as e:
            result.mark_failed(f"Request error: {str(e)}")
            logger.error(f"Task {task.task_id} request error on agent {agent_id}: {e}")
            # Mark agent as unavailable
            target_agent.is_available = False

        except Exception as e:
            result.mark_failed(f"Unexpected error: {str(e)}")
            logger.error(f"Task {task.task_id} unexpected error on agent {agent_id}: {e}")

        return result

    async def dispatch_parallel(self, tasks: List[Task]) -> List[DispatchResult]:
        """Dispatch multiple tasks in parallel (P-threads).

        Executes multiple tasks concurrently by dispatching each to a
        matching agent. Uses capability matching to select target agents.

        Args:
            tasks: List of tasks to dispatch in parallel.

        Returns:
            List of DispatchResults for all tasks.
        """
        if not tasks:
            logger.debug("No tasks to dispatch in parallel")
            return []

        logger.info(f"Dispatching {len(tasks)} tasks in parallel (P-threads)")

        # Match agents for each task
        dispatch_coroutines = []
        for task in tasks:
            matching_agents = await self.match_capabilities(
                task.description, task.required_capabilities
            )

            if matching_agents:
                # Select first matching agent (could implement load balancing)
                target_agent = matching_agents[0]
                dispatch_coroutines.append(
                    self.dispatch_task(target_agent.agent_id, task)
                )
            else:
                # No matching agent, create failed result
                result = DispatchResult(task_id=task.task_id, agent_id="none")
                result.mark_failed(
                    f"No agent found with capabilities: {task.required_capabilities}"
                )
                dispatch_coroutines.append(asyncio.coroutine(lambda r=result: r)())

        # Execute all dispatches concurrently
        results = await asyncio.gather(*dispatch_coroutines, return_exceptions=True)

        # Process results
        dispatch_results: List[DispatchResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = DispatchResult(
                    task_id=tasks[i].task_id, agent_id="error"
                )
                error_result.mark_failed(f"Dispatch error: {str(result)}")
                dispatch_results.append(error_result)
            else:
                dispatch_results.append(result)

        completed = sum(1 for r in dispatch_results if r.status == TaskStatus.COMPLETED)
        failed = sum(1 for r in dispatch_results if r.status == TaskStatus.FAILED)
        logger.info(
            f"P-threads complete: {completed} completed, {failed} failed "
            f"out of {len(tasks)} tasks"
        )

        return dispatch_results

    async def dispatch_sequential(self, tasks: List[Task]) -> DispatchResult:
        """Chain tasks sequentially (C-threads).

        Executes tasks in sequence, passing the output of each task as
        input context for the next. Stops on first failure.

        Args:
            tasks: List of tasks to execute sequentially.

        Returns:
            Final DispatchResult (from last successful task or first failure).
        """
        if not tasks:
            result = DispatchResult(task_id="empty", agent_id="none")
            result.mark_failed("No tasks provided for sequential dispatch")
            return result

        logger.info(f"Dispatching {len(tasks)} tasks sequentially (C-threads)")

        chain_id = str(uuid4())
        previous_result: Optional[DispatchResult] = None
        accumulated_context: Dict[str, Any] = {}

        for i, task in enumerate(tasks):
            logger.debug(f"C-thread step {i + 1}/{len(tasks)}: {task.description}")

            # Inject previous result into task metadata for context chaining
            if previous_result and previous_result.response:
                task.metadata["previous_step_result"] = previous_result.response
                task.metadata["chain_id"] = chain_id
                task.metadata["step_number"] = i + 1
                accumulated_context[f"step_{i}"] = previous_result.response

            # Match agent for this task
            matching_agents = await self.match_capabilities(
                task.description, task.required_capabilities
            )

            if not matching_agents:
                result = DispatchResult(task_id=task.task_id, agent_id="none")
                result.mark_failed(
                    f"C-thread failed at step {i + 1}: "
                    f"No agent found with capabilities: {task.required_capabilities}"
                )
                logger.error(f"C-thread {chain_id} failed at step {i + 1}")
                return result

            # Dispatch to first matching agent
            target_agent = matching_agents[0]
            result = await self.dispatch_task(target_agent.agent_id, task)

            if result.status != TaskStatus.COMPLETED:
                logger.error(
                    f"C-thread {chain_id} failed at step {i + 1}: {result.error_message}"
                )
                return result

            previous_result = result

        # Return final result with accumulated context
        if previous_result:
            previous_result.response = previous_result.response or {}
            previous_result.response["chain_context"] = accumulated_context
            logger.info(
                f"C-thread {chain_id} completed all {len(tasks)} steps "
                f"in {previous_result.duration_ms}ms total"
            )
            return previous_result

        # Should not reach here, but handle edge case
        fallback = DispatchResult(task_id=chain_id, agent_id="none")
        fallback.mark_failed("Sequential dispatch completed with no result")
        return fallback

    def clear_cache(self) -> int:
        """Clear all cached agent information.

        Returns:
            Number of entries cleared from cache.
        """
        count = len(self._agent_cache)
        self._agent_cache.clear()
        logger.info(f"Cleared {count} entries from agent cache")
        return count

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the agent cache.

        Returns:
            Dictionary with cache statistics.
        """
        total = len(self._agent_cache)
        expired = sum(1 for c in self._agent_cache.values() if c.is_expired)
        available = sum(
            1 for c in self._agent_cache.values()
            if not c.is_expired and c.agent_info.is_available
        )

        return {
            "total_cached": total,
            "expired": expired,
            "available": available,
            "ttl_seconds": self._cache_ttl_seconds,
            "known_endpoints": len(self._known_endpoints),
        }


# Global singleton
agent_dispatcher = AgentDispatcher()
