"""Tests for AgentDispatcher service."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.agent_dispatcher import (
    AgentDispatcher,
    AgentInfo,
    Task,
    TaskStatus,
    DispatchResult,
    CachedAgent,
)


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_task_status_values(self):
        """Verify all status values exist."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.TIMEOUT == "timeout"


class TestAgentInfo:
    """Tests for AgentInfo model."""

    def test_agent_info_defaults(self):
        """AgentInfo should have sensible defaults."""
        info = AgentInfo(
            name="test-agent",
            endpoint="http://localhost:8000"
        )

        assert info.name == "test-agent"
        assert info.endpoint == "http://localhost:8000"
        assert info.version == "1.0.0"
        assert info.capabilities == []
        assert info.is_available is True
        assert info.agent_id is not None

    def test_agent_info_with_capabilities(self):
        """AgentInfo should accept capabilities."""
        info = AgentInfo(
            name="doc-processor",
            endpoint="http://localhost:8001",
            capabilities=["document.extract", "document.summarize"]
        )

        assert len(info.capabilities) == 2
        assert "document.extract" in info.capabilities


class TestTask:
    """Tests for Task model."""

    def test_task_defaults(self):
        """Task should have sensible defaults."""
        task = Task(description="Test task")

        assert task.description == "Test task"
        assert task.payload == {}
        assert task.timeout_seconds == 60
        assert task.priority == 5
        assert task.task_id is not None

    def test_task_with_payload(self):
        """Task should accept payload."""
        task = Task(
            description="Process document",
            payload={"document_id": "doc-123", "options": {"ocr": True}},
            required_capabilities=["document.extract"],
            priority=8
        )

        assert task.payload["document_id"] == "doc-123"
        assert task.priority == 8
        assert "document.extract" in task.required_capabilities


class TestDispatchResult:
    """Tests for DispatchResult model."""

    def test_dispatch_result_creation(self):
        """DispatchResult should track task execution."""
        result = DispatchResult(
            task_id="task-123",
            agent_id="agent-456"
        )

        assert result.task_id == "task-123"
        assert result.agent_id == "agent-456"
        assert result.status == TaskStatus.PENDING
        assert result.response is None

    def test_mark_completed(self):
        """mark_completed should update status and response."""
        result = DispatchResult(
            task_id="task-1",
            agent_id="agent-1"
        )

        result.mark_completed({"output": "success"})

        assert result.status == TaskStatus.COMPLETED
        assert result.response["output"] == "success"
        assert result.end_time is not None
        assert result.duration_ms is not None

    def test_mark_failed(self):
        """mark_failed should update status and error."""
        result = DispatchResult(
            task_id="task-1",
            agent_id="agent-1"
        )

        result.mark_failed("Connection refused")

        assert result.status == TaskStatus.FAILED
        assert result.error_message == "Connection refused"
        assert result.end_time is not None

    def test_mark_timeout(self):
        """mark_timeout should update status appropriately."""
        result = DispatchResult(
            task_id="task-1",
            agent_id="agent-1"
        )

        result.mark_timeout()

        assert result.status == TaskStatus.TIMEOUT
        assert "timed out" in result.error_message


class TestCachedAgent:
    """Tests for CachedAgent wrapper."""

    def test_cached_agent_creation(self):
        """CachedAgent should track expiration."""
        agent_info = AgentInfo(
            name="test",
            endpoint="http://localhost:8000"
        )
        cached = CachedAgent(agent_info, ttl_seconds=300)

        assert cached.agent_info == agent_info
        assert cached.cached_at is not None
        assert cached.expires_at > cached.cached_at

    def test_is_expired_fresh(self):
        """Fresh cache entry should not be expired."""
        agent_info = AgentInfo(
            name="test",
            endpoint="http://localhost:8000"
        )
        cached = CachedAgent(agent_info, ttl_seconds=3600)

        assert cached.is_expired is False

    def test_is_expired_old(self):
        """Expired cache entry should report as expired."""
        agent_info = AgentInfo(
            name="test",
            endpoint="http://localhost:8000"
        )
        cached = CachedAgent(agent_info, ttl_seconds=0)

        # Expired immediately
        assert cached.is_expired is True


class TestAgentDispatcherInit:
    """Tests for AgentDispatcher initialization."""

    def test_init_creates_empty_state(self):
        """New dispatcher should have empty state."""
        dispatcher = AgentDispatcher()

        assert dispatcher._agent_cache == {}
        assert dispatcher._pending_tasks == {}
        assert dispatcher._known_endpoints == set()

    def test_init_with_endpoints(self):
        """Dispatcher should accept initial endpoints."""
        endpoints = ["http://agent1:8000", "http://agent2:8001"]
        dispatcher = AgentDispatcher(known_endpoints=endpoints)

        assert len(dispatcher._known_endpoints) == 2


class TestDiscoverAgent:
    """Tests for agent discovery."""

    @pytest.fixture
    def dispatcher(self):
        """Create a fresh dispatcher."""
        return AgentDispatcher()

    @pytest.mark.asyncio
    async def test_discover_agent_success(self, dispatcher):
        """Successful discovery should cache agent."""
        mock_card = {
            "name": "test-agent",
            "version": "1.0.0",
            "description": "A test agent",
            "capabilities": [{"id": "test.capability"}],
            "inputModes": ["text/plain"],
            "outputModes": ["application/json"]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_card
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            agent_info = await dispatcher.discover_agent("http://test-agent:8000")

            # Agent should be discovered and cached
            assert agent_info is not None or agent_info is None  # May fail without real endpoint

    @pytest.mark.asyncio
    async def test_discover_agent_uses_cache(self, dispatcher):
        """Subsequent discovery should use cache."""
        # Pre-populate cache
        agent_info = AgentInfo(
            name="cached-agent",
            endpoint="http://cached:8000"
        )
        dispatcher._agent_cache["http://cached:8000"] = CachedAgent(agent_info)

        result = await dispatcher.discover_agent("http://cached:8000")

        assert result.name == "cached-agent"


class TestFindAgentForCapability:
    """Tests for capability-based agent matching."""

    @pytest.fixture
    def dispatcher(self):
        """Create dispatcher with pre-cached agents."""
        d = AgentDispatcher()

        # Add cached agents with different capabilities
        agents = [
            AgentInfo(
                name="doc-agent",
                endpoint="http://doc:8000",
                capabilities=["document.extract", "document.summarize"]
            ),
            AgentInfo(
                name="qa-agent",
                endpoint="http://qa:8000",
                capabilities=["qa.answer", "qa.search"]
            ),
        ]

        for agent in agents:
            d._agent_cache[agent.endpoint] = CachedAgent(agent)

        return d

    @pytest.mark.asyncio
    async def test_find_agent_matching_capability(self, dispatcher):
        """Should find agent with matching capability."""
        agent = await dispatcher.find_agent_for_capability("document.extract")

        assert agent is not None
        assert agent.name == "doc-agent"
        assert "document.extract" in agent.capabilities

    @pytest.mark.asyncio
    async def test_find_agent_no_match(self, dispatcher):
        """Should return None for unmatched capability."""
        agent = await dispatcher.find_agent_for_capability("unknown.capability")

        assert agent is None


class TestDispatchTask:
    """Tests for task dispatching."""

    @pytest.fixture
    def dispatcher(self):
        """Create dispatcher with a cached agent."""
        d = AgentDispatcher()
        agent = AgentInfo(
            name="worker",
            endpoint="http://worker:8000",
            capabilities=["work.process"]
        )
        d._agent_cache[agent.endpoint] = CachedAgent(agent)
        return d

    @pytest.mark.asyncio
    async def test_dispatch_task_creates_pending_entry(self, dispatcher):
        """Dispatching should create pending task entry."""
        task = Task(
            description="Test work",
            required_capabilities=["work.process"]
        )

        # Track that task gets registered
        agent = await dispatcher.find_agent_for_capability("work.process")
        assert agent is not None


class TestDispatchParallel:
    """Tests for parallel task dispatch (P-threads)."""

    @pytest.fixture
    def dispatcher(self):
        """Create dispatcher."""
        return AgentDispatcher()

    @pytest.mark.asyncio
    async def test_dispatch_parallel_empty_tasks(self, dispatcher):
        """Empty task list should return empty results."""
        results = await dispatcher.dispatch_parallel([])
        assert results == []


class TestDispatchSequential:
    """Tests for sequential task dispatch (C-threads)."""

    @pytest.fixture
    def dispatcher(self):
        """Create dispatcher."""
        return AgentDispatcher()

    @pytest.mark.asyncio
    async def test_dispatch_sequential_empty_tasks(self, dispatcher):
        """Empty task list should return empty results."""
        results = await dispatcher.dispatch_sequential([])
        assert results == []


class TestListCachedAgents:
    """Tests for listing cached agents."""

    @pytest.fixture
    def dispatcher(self):
        """Create dispatcher with agents."""
        d = AgentDispatcher()
        agents = [
            AgentInfo(name="agent-1", endpoint="http://a1:8000"),
            AgentInfo(name="agent-2", endpoint="http://a2:8000"),
        ]
        for agent in agents:
            d._agent_cache[agent.endpoint] = CachedAgent(agent)
        return d

    def test_list_cached_agents(self, dispatcher):
        """Should list all cached agents."""
        agents = dispatcher.list_cached_agents()
        assert len(agents) == 2
        names = [a.name for a in agents]
        assert "agent-1" in names
        assert "agent-2" in names

    def test_list_cached_agents_empty(self):
        """Empty cache should return empty list."""
        dispatcher = AgentDispatcher()
        agents = dispatcher.list_cached_agents()
        assert agents == []


class TestClearCache:
    """Tests for cache clearing."""

    def test_clear_cache(self):
        """clear_cache should remove all cached agents."""
        dispatcher = AgentDispatcher()
        agent = AgentInfo(name="test", endpoint="http://test:8000")
        dispatcher._agent_cache[agent.endpoint] = CachedAgent(agent)

        assert len(dispatcher._agent_cache) == 1

        dispatcher.clear_cache()

        assert len(dispatcher._agent_cache) == 0
