"""Tests for CipherService team memory and workspace capabilities."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Reset module-level state before importing
import app.services.cipher_service as cipher_module

cipher_module._workspaces = {}
cipher_module._team_memories = {}
cipher_module._reasoning_steps = {}

from app.services.cipher_service import CipherService


class TestKeyValidation:
    """Tests for composite key validation."""

    def test_validate_key_component_valid(self):
        """Valid keys without colons should pass."""
        # Should not raise
        CipherService._validate_key_component("valid_key", "test")
        CipherService._validate_key_component("workspace-123", "test")
        CipherService._validate_key_component("my.key.name", "test")

    def test_validate_key_component_invalid(self):
        """Keys with colons should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CipherService._validate_key_component("invalid:key", "workspace_id")
        assert "workspace_id cannot contain ':' character" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            CipherService._validate_key_component("a:b:c", "key")
        assert "key cannot contain ':' character" in str(exc_info.value)


class TestCreateWorkspace:
    """Tests for workspace creation."""

    @pytest.fixture(autouse=True)
    def reset_storage(self):
        """Reset storage before each test."""
        cipher_module._workspaces = {}
        cipher_module._team_memories = {}
        cipher_module._reasoning_steps = {}
        yield

    @pytest.mark.asyncio
    async def test_create_workspace_success(self):
        """Creating a new workspace should succeed."""
        result = await CipherService.create_workspace(
            "test-workspace",
            metadata={"name": "Test Workspace", "description": "A test"}
        )

        assert result["id"] == "test-workspace"
        assert "created_at" in result
        assert "updated_at" in result
        assert result["metadata"]["name"] == "Test Workspace"
        assert "test-workspace" in cipher_module._workspaces

    @pytest.mark.asyncio
    async def test_create_workspace_idempotent(self):
        """Creating the same workspace twice should return existing."""
        result1 = await CipherService.create_workspace("duplicate-test")
        result2 = await CipherService.create_workspace("duplicate-test")

        assert result1["id"] == result2["id"]
        assert result1["created_at"] == result2["created_at"]

    @pytest.mark.asyncio
    async def test_create_workspace_invalid_id(self):
        """Workspace ID with colon should be rejected."""
        with pytest.raises(ValueError) as exc_info:
            await CipherService.create_workspace("invalid:workspace")
        assert "workspace_id cannot contain ':' character" in str(exc_info.value)


class TestStoreTeamMemory:
    """Tests for team memory storage."""

    @pytest.fixture(autouse=True)
    def reset_storage(self):
        """Reset storage before each test."""
        cipher_module._workspaces = {}
        cipher_module._team_memories = {}
        cipher_module._reasoning_steps = {}
        yield

    @pytest.mark.asyncio
    async def test_store_team_memory_success(self):
        """Storing team memory should succeed."""
        await CipherService.create_workspace("mem-test")

        result = await CipherService.store_team_memory(
            workspace_id="mem-test",
            key="fact-1",
            content={"text": "Important fact"},
            metadata={"author": "test-agent"}
        )

        assert result["workspace_id"] == "mem-test"
        assert result["key"] == "fact-1"
        assert "memory_id" in result
        assert "stored_at" in result

        # Verify stored in module storage
        assert "mem-test:fact-1" in cipher_module._team_memories

    @pytest.mark.asyncio
    async def test_store_team_memory_auto_creates_workspace(self):
        """Storing to non-existent workspace should auto-create it."""
        result = await CipherService.store_team_memory(
            workspace_id="auto-created",
            key="item-1",
            content="test content"
        )

        assert result["workspace_id"] == "auto-created"
        assert "auto-created" in cipher_module._workspaces

    @pytest.mark.asyncio
    async def test_store_team_memory_invalid_key(self):
        """Key with colon should be rejected."""
        await CipherService.create_workspace("valid-workspace")

        with pytest.raises(ValueError) as exc_info:
            await CipherService.store_team_memory(
                workspace_id="valid-workspace",
                key="invalid:key",
                content="test"
            )
        assert "key cannot contain ':' character" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_store_team_memory_invalid_workspace(self):
        """Workspace ID with colon should be rejected."""
        with pytest.raises(ValueError) as exc_info:
            await CipherService.store_team_memory(
                workspace_id="invalid:workspace",
                key="valid-key",
                content="test"
            )
        assert "workspace_id cannot contain ':' character" in str(exc_info.value)


class TestGetSharedContext:
    """Tests for retrieving shared context."""

    @pytest.fixture(autouse=True)
    def reset_storage(self):
        """Reset storage before each test."""
        cipher_module._workspaces = {}
        cipher_module._team_memories = {}
        cipher_module._reasoning_steps = {}
        yield

    @pytest.mark.asyncio
    async def test_get_shared_context_empty(self):
        """Getting context from empty workspace returns empty list."""
        await CipherService.create_workspace("empty-ws")
        result = await CipherService.get_shared_context("empty-ws")

        assert result["workspace_id"] == "empty-ws"
        assert result["items"] == []
        assert result["count"] == 0
        assert result["total_in_workspace"] == 0

    @pytest.mark.asyncio
    async def test_get_shared_context_with_items(self):
        """Getting context returns stored items."""
        await CipherService.create_workspace("context-test")
        await CipherService.store_team_memory("context-test", "item1", "content1")
        await CipherService.store_team_memory("context-test", "item2", "content2")

        result = await CipherService.get_shared_context("context-test")

        assert result["count"] == 2
        assert result["total_in_workspace"] == 2
        assert len(result["items"]) == 2

    @pytest.mark.asyncio
    async def test_get_shared_context_respects_limit(self):
        """Limit parameter should restrict returned items."""
        await CipherService.create_workspace("limit-test")
        for i in range(10):
            await CipherService.store_team_memory("limit-test", f"item{i}", f"content{i}")

        result = await CipherService.get_shared_context("limit-test", limit=3)

        assert result["count"] == 3
        assert result["total_in_workspace"] == 10
        assert len(result["items"]) == 3

    @pytest.mark.asyncio
    async def test_get_shared_context_sorted_by_created_at(self):
        """Items should be sorted by created_at descending (most recent first)."""
        await CipherService.create_workspace("sort-test")

        # Store items with slight delay to ensure different timestamps
        import asyncio
        await CipherService.store_team_memory("sort-test", "first", "content1")
        await asyncio.sleep(0.01)
        await CipherService.store_team_memory("sort-test", "second", "content2")
        await asyncio.sleep(0.01)
        await CipherService.store_team_memory("sort-test", "third", "content3")

        result = await CipherService.get_shared_context("sort-test")

        # Most recent should be first
        assert result["items"][0]["key"] == "third"
        assert result["items"][1]["key"] == "second"
        assert result["items"][2]["key"] == "first"


class TestStoreReasoningStep:
    """Tests for reasoning step storage."""

    @pytest.fixture(autouse=True)
    def reset_storage(self):
        """Reset storage before each test."""
        cipher_module._workspaces = {}
        cipher_module._team_memories = {}
        cipher_module._reasoning_steps = {}
        yield

    @pytest.mark.asyncio
    async def test_store_reasoning_step_success(self):
        """Storing a reasoning step should succeed."""
        step = {
            "trace_id": "trace-123",
            "step_number": 1,
            "thought": "Initial analysis",
            "evidence": [{"source": "doc1", "content": "evidence text"}],
            "confidence": 0.85
        }

        result = await CipherService.store_reasoning_step(step)

        assert result["trace_id"] == "trace-123"
        assert result["step_number"] == 1
        assert "step_id" in result
        assert "stored_at" in result

        # Verify stored
        assert "reasoning:trace-123:1" in cipher_module._reasoning_steps

    @pytest.mark.asyncio
    async def test_store_reasoning_step_missing_trace_id(self):
        """Missing trace_id should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await CipherService.store_reasoning_step({"step_number": 1})
        assert "'trace_id' and 'step_number'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_store_reasoning_step_missing_step_number(self):
        """Missing step_number should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await CipherService.store_reasoning_step({"trace_id": "test"})
        assert "'trace_id' and 'step_number'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_store_reasoning_step_prevents_overwrite(self):
        """Storing same step twice should raise ValueError."""
        step = {
            "trace_id": "trace-duplicate",
            "step_number": 1,
            "thought": "First thought"
        }

        await CipherService.store_reasoning_step(step)

        with pytest.raises(ValueError) as exc_info:
            await CipherService.store_reasoning_step(step)
        assert "already exists" in str(exc_info.value)


class TestThreadSafety:
    """Tests for thread safety of storage operations."""

    @pytest.fixture(autouse=True)
    def reset_storage(self):
        """Reset storage before each test."""
        cipher_module._workspaces = {}
        cipher_module._team_memories = {}
        cipher_module._reasoning_steps = {}
        yield

    @pytest.mark.asyncio
    async def test_concurrent_workspace_creation(self):
        """Concurrent workspace creation should be thread-safe."""
        import asyncio

        async def create_workspace(ws_id):
            return await CipherService.create_workspace(ws_id)

        # Create multiple workspaces concurrently
        results = await asyncio.gather(
            *[create_workspace(f"concurrent-ws-{i}") for i in range(10)]
        )

        # All should succeed
        assert len(results) == 10
        assert len(cipher_module._workspaces) == 10

    @pytest.mark.asyncio
    async def test_concurrent_memory_storage(self):
        """Concurrent memory storage should be thread-safe."""
        import asyncio

        await CipherService.create_workspace("concurrent-mem")

        async def store_memory(key):
            return await CipherService.store_team_memory(
                "concurrent-mem", key, f"content-{key}"
            )

        # Store multiple memories concurrently
        results = await asyncio.gather(
            *[store_memory(f"key-{i}") for i in range(20)]
        )

        # All should succeed
        assert len(results) == 20
        assert sum(1 for k in cipher_module._team_memories if k.startswith("concurrent-mem:")) == 20
