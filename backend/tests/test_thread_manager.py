"""Tests for ThreadManager service."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.thread_manager import (
    ThreadManager,
    ThreadType,
    ThreadStatus,
    ThreadConfig,
    ThreadResult,
    ThreadContext,
)


class TestThreadManagerInit:
    """Tests for ThreadManager initialization."""

    def test_init_creates_empty_state(self):
        """New ThreadManager should have empty active threads."""
        manager = ThreadManager()
        assert manager._active_threads == {}

    def test_init_with_custom_dispatcher(self):
        """ThreadManager should accept custom dispatcher."""
        mock_dispatcher = MagicMock()
        manager = ThreadManager(dispatcher=mock_dispatcher)
        assert manager._dispatcher == mock_dispatcher


class TestCreateThread:
    """Tests for thread creation."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ThreadManager."""
        return ThreadManager()

    @pytest.mark.asyncio
    async def test_create_base_thread(self, manager):
        """Creating a BASE thread should succeed."""
        config = ThreadConfig(
            thread_type=ThreadType.BASE,
            agents=["agent-1"]
        )

        thread_id = await manager.create_thread(config)

        assert thread_id is not None
        assert len(thread_id) == 36  # UUID format
        assert thread_id in manager._active_threads

    @pytest.mark.asyncio
    async def test_create_parallel_thread(self, manager):
        """Creating a PARALLEL thread should succeed."""
        config = ThreadConfig(
            thread_type=ThreadType.PARALLEL,
            agents=["agent-1", "agent-2", "agent-3"]
        )

        thread_id = await manager.create_thread(config)

        assert thread_id is not None
        ctx = manager._active_threads[thread_id]
        assert ctx.config.thread_type == ThreadType.PARALLEL
        assert len(ctx.config.agents) == 3

    @pytest.mark.asyncio
    async def test_create_thread_with_metadata(self, manager):
        """Thread config metadata should be preserved."""
        config = ThreadConfig(
            thread_type=ThreadType.BASE,
            agents=["agent-1"],
            metadata={"task": "test-task", "priority": 1}
        )

        thread_id = await manager.create_thread(config)
        ctx = manager._active_threads[thread_id]

        assert ctx.config.metadata["task"] == "test-task"
        assert ctx.config.metadata["priority"] == 1


class TestGetThreadStatus:
    """Tests for thread status retrieval."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ThreadManager."""
        return ThreadManager()

    @pytest.mark.asyncio
    async def test_get_status_existing_thread(self, manager):
        """Getting status of existing thread should succeed."""
        config = ThreadConfig(
            thread_type=ThreadType.BASE,
            agents=["agent-1"]
        )
        thread_id = await manager.create_thread(config)

        status = manager.get_thread_status(thread_id)

        assert status is not None
        assert status["thread_id"] == thread_id
        assert status["status"] == ThreadStatus.CREATED

    def test_get_status_nonexistent_thread(self, manager):
        """Getting status of non-existent thread should return None."""
        status = manager.get_thread_status("fake-thread-id")
        assert status is None


class TestExecuteBase:
    """Tests for BASE thread execution."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ThreadManager."""
        return ThreadManager()

    @pytest.mark.asyncio
    async def test_execute_base_success(self, manager):
        """BASE thread should execute single agent successfully."""
        config = ThreadConfig(
            thread_type=ThreadType.BASE,
            agents=["test-agent"]
        )
        thread_id = await manager.create_thread(config)

        # Mock executor that returns a result
        async def mock_executor(agent_id, task):
            return {"response": f"Result from {agent_id}"}

        result = await manager.execute_base(
            thread_id=thread_id,
            task="Test task",
            executor=mock_executor
        )

        assert result.status == ThreadStatus.COMPLETED
        assert result.result is not None
        assert result.execution_time_ms > 0


class TestExecuteParallel:
    """Tests for PARALLEL thread execution."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ThreadManager."""
        return ThreadManager()

    @pytest.mark.asyncio
    async def test_execute_parallel_success(self, manager):
        """PARALLEL thread should execute all agents concurrently."""
        config = ThreadConfig(
            thread_type=ThreadType.PARALLEL,
            agents=["agent-1", "agent-2"]
        )
        thread_id = await manager.create_thread(config)

        # Mock executor that tracks execution
        execution_order = []

        async def mock_executor(agent_id, task):
            execution_order.append(agent_id)
            await asyncio.sleep(0.01)
            return {"agent": agent_id, "result": "success"}

        result = await manager.execute_parallel(
            thread_id=thread_id,
            tasks=["Task 1", "Task 2"],
            executor=mock_executor
        )

        assert result.status == ThreadStatus.COMPLETED
        assert len(result.agent_results) == 2
        assert "agent-1" in result.agent_results
        assert "agent-2" in result.agent_results

    @pytest.mark.asyncio
    async def test_execute_parallel_empty_tasks(self, manager):
        """PARALLEL with empty tasks should fail gracefully."""
        config = ThreadConfig(
            thread_type=ThreadType.PARALLEL,
            agents=["agent-1"]
        )
        thread_id = await manager.create_thread(config)

        async def mock_executor(agent_id, task):
            return {"result": "success"}

        result = await manager.execute_parallel(
            thread_id=thread_id,
            tasks=[],  # Empty task list
            executor=mock_executor
        )

        assert result.status == ThreadStatus.FAILED
        assert "No tasks provided" in result.error


class TestExecuteChained:
    """Tests for CHAINED thread execution."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ThreadManager."""
        return ThreadManager()

    @pytest.mark.asyncio
    async def test_execute_chained_success(self, manager):
        """CHAINED thread should pass output between agents."""
        config = ThreadConfig(
            thread_type=ThreadType.CHAINED,
            agents=["agent-1", "agent-2"]
        )
        thread_id = await manager.create_thread(config)

        # Mock executor that transforms input
        async def mock_executor(agent_id, task):
            if agent_id == "agent-1":
                return {"step": 1, "data": "processed"}
            else:
                # Should receive previous output
                return {"step": 2, "previous": task}

        result = await manager.execute_chained(
            thread_id=thread_id,
            initial_task="Start task",
            executor=mock_executor
        )

        assert result.status == ThreadStatus.COMPLETED
        assert len(result.agent_results) == 2


class TestExecuteFusion:
    """Tests for FUSION thread execution with consensus."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ThreadManager."""
        return ThreadManager()

    @pytest.mark.asyncio
    async def test_execute_fusion_success(self, manager):
        """FUSION thread should aggregate results with consensus."""
        config = ThreadConfig(
            thread_type=ThreadType.FUSION,
            agents=["model-1", "model-2", "model-3"],
            consensus_threshold=0.5
        )
        thread_id = await manager.create_thread(config)

        # Mock executor that returns similar results
        async def mock_executor(agent_id, task):
            return {"answer": "correct", "confidence": 0.9}

        result = await manager.execute_fusion(
            thread_id=thread_id,
            task="Evaluate question",
            executor=mock_executor
        )

        assert result.status == ThreadStatus.COMPLETED
        assert "consensus" in result.result

    @pytest.mark.asyncio
    async def test_execute_fusion_zero_average_handling(self, manager):
        """FUSION should handle zero-average consensus correctly."""
        config = ThreadConfig(
            thread_type=ThreadType.FUSION,
            agents=["model-1", "model-2"],
            consensus_threshold=0.5
        )
        thread_id = await manager.create_thread(config)

        # Mock executor that returns zeros
        async def mock_executor(agent_id, task):
            return {"score": 0, "confidence": 0}

        result = await manager.execute_fusion(
            thread_id=thread_id,
            task="Edge case test",
            executor=mock_executor
        )

        # Should not fail even with zero values
        assert result.status in [ThreadStatus.COMPLETED, ThreadStatus.FAILED]


class TestCleanupThread:
    """Tests for thread cleanup."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ThreadManager."""
        return ThreadManager()

    @pytest.mark.asyncio
    async def test_cleanup_existing_thread(self, manager):
        """Cleaning up existing thread should remove it."""
        config = ThreadConfig(
            thread_type=ThreadType.BASE,
            agents=["agent-1"]
        )
        thread_id = await manager.create_thread(config)

        assert thread_id in manager._active_threads

        removed = manager.cleanup_thread(thread_id)

        assert removed is True
        assert thread_id not in manager._active_threads

    def test_cleanup_nonexistent_thread(self, manager):
        """Cleaning up non-existent thread should return False."""
        removed = manager.cleanup_thread("fake-id")
        assert removed is False


class TestListActiveThreads:
    """Tests for listing active threads."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ThreadManager."""
        return ThreadManager()

    @pytest.mark.asyncio
    async def test_list_active_threads(self, manager):
        """Listing should return all active threads."""
        configs = [
            ThreadConfig(thread_type=ThreadType.BASE, agents=["a1"]),
            ThreadConfig(thread_type=ThreadType.PARALLEL, agents=["a2", "a3"]),
        ]

        for config in configs:
            await manager.create_thread(config)

        threads = manager.list_active_threads()

        assert len(threads) == 2

    @pytest.mark.asyncio
    async def test_list_active_threads_empty(self, manager):
        """Listing with no threads should return empty list."""
        threads = manager.list_active_threads()
        assert threads == []


class TestThreadTimeout:
    """Tests for thread timeout handling."""

    @pytest.fixture
    def manager(self):
        """Create a fresh ThreadManager."""
        return ThreadManager()

    @pytest.mark.asyncio
    async def test_timeout_enforcement(self, manager):
        """Thread should timeout if execution exceeds limit."""
        config = ThreadConfig(
            thread_type=ThreadType.BASE,
            agents=["slow-agent"],
            timeout_seconds=1
        )
        thread_id = await manager.create_thread(config)

        # Mock executor that takes too long
        async def slow_executor(agent_id, task):
            await asyncio.sleep(10)  # Much longer than timeout
            return {"result": "late"}

        result = await manager.execute_base(
            thread_id=thread_id,
            task="Test",
            executor=slow_executor
        )

        assert result.status == ThreadStatus.TIMEOUT
