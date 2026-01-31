"""
Authentication module for PMOVES-DoX API.

Provides JWT authentication following PMOVES.AI patterns.

SECURITY WARNING:
    In development mode (ENVIRONMENT=development), authentication may be bypassed
    if python-jose is not installed or SUPABASE_JWT_SECRET is not configured.
    Always verify ENVIRONMENT=production in production deployments.
"""

from .jwt import (
    require_auth,
    get_current_user,
    optional_auth,
    validate_jwt_token,
    get_jwt_config,
)

__all__ = [
    "require_auth",
    "get_current_user",
    "optional_auth",
    "validate_jwt_token",
    "get_jwt_config",
]
