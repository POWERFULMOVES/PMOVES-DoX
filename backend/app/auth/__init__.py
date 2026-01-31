"""
Authentication module for PMOVES-DoX API.

Provides JWT authentication following PMOVES.AI patterns.
"""

from .jwt import (
    require_auth,
    get_current_user,
    optional_auth,
    validate_jwt_token,
    AuthenticationError,
    MissingTokenError,
    InvalidTokenError,
    AnonKeyRejectedError,
    get_jwt_config,
)

__all__ = [
    "require_auth",
    "get_current_user",
    "optional_auth",
    "validate_jwt_token",
    "AuthenticationError",
    "MissingTokenError",
    "InvalidTokenError",
    "AnonKeyRejectedError",
    "get_jwt_config",
]
