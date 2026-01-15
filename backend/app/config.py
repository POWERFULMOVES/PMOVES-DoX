"""Configuration utilities for PMOVES-DoX.

Provides helper functions for detecting deployment mode and
managing environment-based configuration.
"""

import os
from typing import Dict, Any


def is_docked_mode() -> bool:
    """Detect if DoX is running in docked mode within PMOVES.AI.

    Docked mode is indicated by:
    1. DOCKED_MODE=true environment variable (explicit)
    2. NATS_URL pointing to parent NATS (nats://nats:4222 instead of :4223)
    3. DB_BACKEND=supabase (implies production/docked deployment)

    Returns:
        True if running in docked mode, False for standalone.
    """
    # Explicit check first
    docked_env = os.getenv("DOCKED_MODE", "").lower()
    if docked_env in {"1", "true", "yes"}:
        return True
    if docked_env in {"0", "false", "no"}:
        return False

    # Check NATS URL - parent uses port 4222, standalone uses 4223
    nats_url = os.getenv("NATS_URL", "")
    if nats_url == "nats://nats:4222":
        return True
    if nats_url == "nats://nats:4223":
        return False

    # Check database backend - supabase typically indicates docked mode
    db_backend = os.getenv("DB_BACKEND", "sqlite").lower()
    if db_backend == "supabase":
        return True

    # Default to standalone if not explicitly docked
    return False


def get_deployment_info() -> Dict[str, Any]:
    """Get deployment configuration information.

    Returns:
        Dictionary containing deployment mode and service URLs.
    """
    return {
        "mode": "docked" if is_docked_mode() else "standalone",
        "nats_url": os.getenv("NATS_URL", ""),
        "tensorzero_url": os.getenv("TENSORZERO_URL", ""),
        "supabase_url": os.getenv("SUPABASE_URL", ""),
        "ollama_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    }


def env_flag(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable.

    Args:
        name: Environment variable name.
        default: Default value if not set.

    Returns:
        Boolean value of the environment variable.
    """
    val = os.getenv(name, "").lower()
    if val in {"1", "true", "yes", "on"}:
        return True
    if val in {"0", "false", "no", "off"}:
        return False
    return default
