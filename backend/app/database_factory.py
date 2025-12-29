"""Database factory for initializing PMOVES-DoX storage.

Supports multiple database backends with optional dual-write mode:
- SQLite: Default local storage
- Supabase: Remote PostgreSQL with enhanced features
- Dual-write: Simultaneous writes to both backends

Functions:
    init_database: Initialize the appropriate database backend
    get_db_interface: Get database interface without metadata

Classes:
    DualDatabase: Wrapper for dual-write mode to both databases
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Tuple

from app.database import ExtendedDatabase
from app.database_supabase import SupabaseDatabase, SupabaseUnavailable

LOGGER = logging.getLogger(__name__)

WRITE_METHODS = {
    "add_artifact",
    "add_fact",
    "add_evidence",
    "add_document",
    "add_section",
    "add_table",
    "add_api",
    "add_log",
    "add_tag",
    "save_tag_prompt",
    "reset",
    "reset_search_chunks",
    "store_search_chunks",
    "store_entities",
    "store_structure",
    "store_metric_hits",
    "store_summary",
    "add_memory",
    "set_user_pref",
    "register_skill",
}


class DualDatabase:
    """Delegate writes to both databases, reads from primary.

    Provides dual-write mode for migrating from SQLite to Supabase
    or for maintaining local cache with remote backup.

    Attributes:
        primary: Primary database for reads
        secondary: Secondary database for write mirroring
        backend: Combined backend identifier string
    """

    def __init__(self, primary: Any, secondary: Any) -> None:
        """Initialize dual-database wrapper.

        Args:
            primary: Primary database instance.
            secondary: Secondary database instance for write mirroring.
        """
        self.primary = primary
        self.secondary = secondary
        self.backend = f"dual:{getattr(primary, 'backend', 'primary')}+{getattr(secondary, 'backend', 'secondary')}"

    def __getattr__(self, name: str):  # pragma: no cover - thin delegation wrapper
        attr = getattr(self.primary, name)
        if callable(attr) and name in WRITE_METHODS:
            def wrapper(*args, **kwargs):
                result = attr(*args, **kwargs)
                other = getattr(self.secondary, name, None)
                if callable(other):
                    try:
                        other(*args, **kwargs)
                    except Exception as exc:
                        LOGGER.warning("Dual-write secondary failure on %s: %s", name, exc)
                return result

            return wrapper
        return attr


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse an environment variable as a boolean flag.

    Args:
        name: Environment variable name.
        default: Default value if not set.

    Returns:
        True if set to "1", "true", "yes", or "on" (case-insensitive).
    """
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def init_database() -> Tuple[Any, Dict[str, Any]]:
    """Initialize the database backend based on environment configuration.

    Reads DB_BACKEND and SUPABASE_DUAL_WRITE environment variables
    to configure the appropriate storage backend.

    Returns:
        A tuple of (database_instance, metadata_dict) where metadata contains:
        - configured: The requested backend from env var
        - active: The actual backend in use
        - dual_write: Whether dual-write mode is active
        - supabase_error: Any error message from Supabase connection

    Raises:
        SupabaseUnavailable: If DB_BACKEND=supabase and connection fails.
    """
    configured_backend = os.getenv("DB_BACKEND", "sqlite").strip().lower() or "sqlite"
    dual_write_requested = _env_flag("SUPABASE_DUAL_WRITE", False)

    sqlite_db = ExtendedDatabase()
    setattr(sqlite_db, "backend", "sqlite")

    supabase_db = None
    supabase_error = None
    if configured_backend == "supabase" or dual_write_requested:
        try:
            supabase_db = SupabaseDatabase()
            setattr(supabase_db, "backend", "supabase")
        except SupabaseUnavailable as exc:
            supabase_error = str(exc)
            if configured_backend == "supabase":
                raise
            LOGGER.warning("Supabase unavailable, continuing with SQLite only: %s", exc)

    db_instance: Any = sqlite_db
    active_backend = "sqlite"
    dual_write_active = False

    if configured_backend == "supabase" and supabase_db is not None:
        db_instance = supabase_db
        active_backend = "supabase"
    elif configured_backend not in {"sqlite", "supabase"}:
        LOGGER.warning("Unknown DB_BACKEND '%s', defaulting to SQLite", configured_backend)

    if dual_write_requested and supabase_db is not None:
        if db_instance is supabase_db:
            db_instance = DualDatabase(supabase_db, sqlite_db)
        else:
            db_instance = DualDatabase(sqlite_db, supabase_db)
        dual_write_active = True

    metadata = {
        "configured": configured_backend,
        "active": active_backend if not dual_write_active else getattr(db_instance, "backend", "dual"),
        "dual_write": dual_write_active,
        "supabase_error": supabase_error,
    }

    return db_instance, metadata


def get_db_interface() -> Any:
    """Get the database interface without metadata.

    Convenience function for code that only needs the database
    instance and not the configuration metadata.

    Returns:
        The initialized database instance.
    """
    db, _ = init_database()
    return db
