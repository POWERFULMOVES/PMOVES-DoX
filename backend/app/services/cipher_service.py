from typing import Dict, List, Optional, Any
from app.database_factory import get_db_interface
import logging
import json
import threading
from datetime import datetime, timezone
import uuid

LOGGER = logging.getLogger(__name__)

# Module-level storage for workspaces (shared across all CipherService usage)
# Protected by _storage_lock for thread-safe access in FastAPI concurrent requests
_storage_lock = threading.Lock()
_workspaces: Dict[str, Dict[str, Any]] = {}
_team_memories: Dict[str, Dict[str, Any]] = {}
_reasoning_steps: Dict[str, Dict[str, Any]] = {}


class CipherService:
    @staticmethod
    def _get_db():
        return get_db_interface()

    @staticmethod
    def add_memory(category: str, content: Dict, context: Optional[Dict] = None) -> str:
        """Stores a generic memory."""
        db = CipherService._get_db()
        if hasattr(db, "add_memory"):
            return db.add_memory(category, content, context)
        LOGGER.warning("add_memory not implemented in current DB adapter")
        return ""

    @staticmethod
    def search_memory(category: Optional[str] = None, q: Optional[str] = None) -> List[Dict]:
        """Searches memory."""
        db = CipherService._get_db()
        if hasattr(db, "search_memory"):
            return db.search_memory(category=category, q=q)
        return []

    @staticmethod
    def list_skills() -> List[Dict]:
        """Lists all enabled skills."""
        db = CipherService._get_db()
        if hasattr(db, "list_skills"):
            return db.list_skills(enabled_only=True)
        return []

    # --- Legacy/Specific Wrappers ---

    @staticmethod
    def add_fact(content: Dict, source: str = "user_input") -> str:
        return CipherService.add_memory("fact", content, {"source": source})

    @staticmethod
    def add_preference(key: str, value: Any, user_id: str) -> None:
        db = CipherService._get_db()
        if hasattr(db, "set_user_pref"):
            db.set_user_pref(user_id, key, value)
        else:
            LOGGER.warning("set_user_pref not implemented in current DB adapter")

    @staticmethod
    def get_preferences(user_id: str) -> Dict:
        db = CipherService._get_db()
        if hasattr(db, "get_user_prefs"):
            return db.get_user_prefs(user_id)
        return {}

    @staticmethod
    def learn_skill(name: str, description: str, workflow: Dict) -> str:
        db = CipherService._get_db()
        if hasattr(db, "register_skill"):
            return db.register_skill(name, description, {}, workflow)
        return ""

    # --- Team Memory Capabilities ---

    @staticmethod
    def _validate_key_component(value: str, name: str) -> None:
        """Validate that a key component does not contain the delimiter.

        Args:
            value: The value to validate.
            name: Name of the parameter for error messages.

        Raises:
            ValueError: If value contains ':' character.
        """
        if ":" in value:
            raise ValueError(f"{name} cannot contain ':' character")

    @staticmethod
    async def create_workspace(
        workspace_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new workspace for team memory collaboration.

        Args:
            workspace_id: Unique identifier for the workspace.
            metadata: Optional metadata (name, description, members, etc.)

        Returns:
            Workspace info dict with id, created_at, metadata.

        Raises:
            ValueError: If workspace_id contains ':' character.
        """
        global _workspaces, _storage_lock

        CipherService._validate_key_component(workspace_id, "workspace_id")

        with _storage_lock:
            if workspace_id in _workspaces:
                LOGGER.warning(f"Workspace '{workspace_id}' already exists, returning existing")
                return _workspaces[workspace_id]

            now = datetime.now(timezone.utc).isoformat()
            workspace_info = {
                "id": workspace_id,
                "created_at": now,
                "updated_at": now,
                "metadata": metadata or {},
            }

            _workspaces[workspace_id] = workspace_info
            LOGGER.info(f"Created workspace: {workspace_id}")

        # Optionally store in Cipher backend if available
        db = CipherService._get_db()
        if hasattr(db, "add_memory"):
            try:
                db.add_memory(
                    "workspace",
                    {"workspace_id": workspace_id, **workspace_info},
                    {"type": "workspace_creation"},
                )
            except Exception as e:
                LOGGER.warning(f"Failed to persist workspace to DB: {e}")

        return workspace_info

    @staticmethod
    async def store_team_memory(
        workspace_id: str,
        key: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Store a memory item in a team workspace.

        Args:
            workspace_id: Target workspace ID.
            key: Unique key within workspace.
            content: Content to store (will be JSON serialized).
            metadata: Optional metadata (author, timestamp, etc.)

        Returns:
            Storage confirmation with memory_id.

        Raises:
            ValueError: If workspace_id or key contains ':' character.
        """
        global _team_memories, _workspaces, _storage_lock

        # Validate key components to prevent delimiter collisions
        CipherService._validate_key_component(workspace_id, "workspace_id")
        CipherService._validate_key_component(key, "key")

        # Verify workspace exists (create_workspace has its own lock)
        with _storage_lock:
            workspace_exists = workspace_id in _workspaces
        if not workspace_exists:
            LOGGER.warning(f"Workspace '{workspace_id}' not found, creating it")
            await CipherService.create_workspace(workspace_id)

        composite_key = f"{workspace_id}:{key}"
        memory_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        memory_entry = {
            "memory_id": memory_id,
            "workspace_id": workspace_id,
            "key": key,
            "composite_key": composite_key,
            "content": content,
            "metadata": metadata or {},
            "created_at": now,
            "updated_at": now,
        }

        with _storage_lock:
            _team_memories[composite_key] = memory_entry

            # Update workspace timestamp
            if workspace_id in _workspaces:
                _workspaces[workspace_id]["updated_at"] = now

        LOGGER.info(f"Stored team memory: {composite_key} (id={memory_id})")

        # Optionally persist to Cipher backend
        db = CipherService._get_db()
        if hasattr(db, "add_memory"):
            try:
                serialized_content = (
                    json.dumps(content) if not isinstance(content, str) else content
                )
                db.add_memory(
                    "team_memory",
                    {
                        "memory_id": memory_id,
                        "workspace_id": workspace_id,
                        "key": key,
                        "content": serialized_content,
                    },
                    {"type": "team_memory", **(metadata or {})},
                )
            except Exception as e:
                LOGGER.warning(f"Failed to persist team memory to DB: {e}")

        return {
            "memory_id": memory_id,
            "workspace_id": workspace_id,
            "key": key,
            "stored_at": now,
        }

    @staticmethod
    async def get_shared_context(
        workspace_id: str, limit: int = 50
    ) -> Dict[str, Any]:
        """Retrieve all shared context from a workspace.

        Args:
            workspace_id: Workspace to query.
            limit: Maximum items to return.

        Returns:
            Dict with workspace_id, items list, and count.
        """
        global _team_memories, _workspaces, _storage_lock

        prefix = f"{workspace_id}:"
        items = []
        total_count = 0

        with _storage_lock:
            # Collect ALL matching items first (don't limit yet)
            for composite_key, memory_entry in _team_memories.items():
                if composite_key.startswith(prefix):
                    items.append(memory_entry.copy())  # Copy to avoid holding lock during sort
                    total_count += 1

            workspace_info = _workspaces.get(workspace_id, {}).copy()

        # Sort by created_at descending (most recent first), THEN apply limit
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        items = items[:limit]

        LOGGER.debug(
            f"Retrieved {len(items)} items from workspace '{workspace_id}' (limit={limit})"
        )

        return {
            "workspace_id": workspace_id,
            "workspace_metadata": workspace_info.get("metadata", {}),
            "items": items,  # Already limited after sorting
            "count": len(items),
            "total_in_workspace": total_count,
        }

    @staticmethod
    async def store_reasoning_step(step: Dict[str, Any]) -> Dict[str, Any]:
        """Store a reasoning step for trace reconstruction.

        Args:
            step: Dict with trace_id, step_number, thought, evidence, confidence.

        Returns:
            Storage confirmation with step_id.

        Raises:
            ValueError: If step is missing required fields or step already exists.
        """
        global _reasoning_steps, _storage_lock

        trace_id = step.get("trace_id")
        step_number = step.get("step_number")

        if not trace_id or step_number is None:
            raise ValueError("step must contain 'trace_id' and 'step_number'")

        composite_key = f"reasoning:{trace_id}:{step_number}"
        step_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        reasoning_entry = {
            "step_id": step_id,
            "trace_id": trace_id,
            "step_number": step_number,
            "thought": step.get("thought", ""),
            "evidence": step.get("evidence", []),
            "confidence": step.get("confidence", 0.0),
            "created_at": now,
            "raw_step": step,
        }

        with _storage_lock:
            # Prevent silent overwrites - reasoning steps should be immutable
            if composite_key in _reasoning_steps:
                raise ValueError(
                    f"Reasoning step {step_number} for trace {trace_id} already exists"
                )
            _reasoning_steps[composite_key] = reasoning_entry

        LOGGER.info(
            f"Stored reasoning step: trace={trace_id}, step={step_number} (id={step_id})"
        )

        # Optionally persist to Cipher backend
        db = CipherService._get_db()
        if hasattr(db, "add_memory"):
            try:
                db.add_memory(
                    "reasoning_step",
                    {
                        "step_id": step_id,
                        "trace_id": trace_id,
                        "step_number": step_number,
                        "thought": step.get("thought", ""),
                        "confidence": step.get("confidence", 0.0),
                    },
                    {
                        "type": "reasoning_trace",
                        "evidence": step.get("evidence", []),
                    },
                )
            except Exception as e:
                LOGGER.warning(f"Failed to persist reasoning step to DB: {e}")

        return {
            "step_id": step_id,
            "trace_id": trace_id,
            "step_number": step_number,
            "stored_at": now,
        }
