"""
JWT Authentication for PMOVES-DoX API

Follows PMOVES.AI JWT pattern using Supabase JWT secret.
Compatible with PMOVES-BoTZ and PMOVES-Archon authentication.

Usage:
    from app.auth.jwt import require_auth, get_current_user
    from fastapi import Depends

    @app.get("/protected")
    def protected_endpoint(user_id: str = Depends(get_current_user)):
        return {"user_id": user_id}
"""

import os
from typing import Tuple, Dict, Any, Optional
from fastapi import Header, HTTPException, Depends
from functools import lru_cache

try:
    from jose import jwt
    HAS_JOSE = True
except ImportError:
    HAS_JOSE = False
    jwt = None

# Supabase JWT secret (shared with PMOVES.AI)
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
JWT_ALGORITHM = "HS256"

# Development mode flag
DEV_MODE = os.getenv("ENVIRONMENT", "development") == "development"


class AuthenticationError(Exception):
    """Base authentication error."""
    pass


class MissingTokenError(AuthenticationError):
    """No token provided."""
    pass


class InvalidTokenError(AuthenticationError):
    """Token validation failed."""
    pass


class AnonKeyRejectedError(AuthenticationError):
    """Anonymous key rejected."""
    pass


def validate_jwt_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Validate a JWT token using Supabase JWT secret.

    Args:
        token: JWT token string

    Returns:
        Tuple of (is_valid, payload, message)
        - is_valid: True if token is valid
        - payload: Decoded JWT payload if valid, None otherwise
        - message: Status message

    Valid tokens:
    - Must have valid signature (if JWT_SECRET is set)
    - Can be service_role or authenticated user token
    - Rejects anon keys (public keys with limited permissions)
    """
    if not token:
        return False, None, "MISSING_TOKEN"

    if not HAS_JOSE:
        # If python-jose is not installed, allow in development
        if DEV_MODE:
            return True, {"sub": "dev_user", "role": "authenticated"}, "VALIDATION_UNAVAILABLE"
        return False, None, "JOSE_NOT_INSTALLED"

    if not JWT_SECRET:
        # If no JWT secret is configured, allow in development mode only
        if DEV_MODE:
            return True, {"sub": "dev_user", "role": "authenticated"}, "NO_SECRET_CONFIGURED"
        return False, None, "NO_SECRET_CONFIGURED"

    try:
        # Decode and verify signature
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={
                "verify_signature": True,
                "verify_aud": False,
                "verify_exp": True,
            }
        )

        # Check role - reject anon keys
        role = payload.get("role", "")
        if role == "anon":
            return False, payload, "ANON_KEY_REJECTED"

        # Accept service_role and authenticated user tokens
        return True, payload, "VALID_TOKEN"

    except jwt.ExpiredSignatureError:
        return False, None, "TOKEN_EXPIRED"
    except jwt.InvalidSignatureError:
        return False, None, "INVALID_SIGNATURE"
    except jwt.JWTError as e:
        return False, None, f"JWT_ERROR: {str(e)}"
    except Exception as e:
        return False, None, f"ERROR: {str(e)}"


def require_auth(auth_header: str = Header(...)) -> Dict[str, Any]:
    """
    Validate Authorization header and extract user info.

    FastAPI dependency that validates JWT and returns user payload.

    Args:
        auth_header: Authorization header value (e.g., "Bearer <token>")

    Returns:
        Dict with JWT payload containing user info

    Raises:
        HTTPException: 401 if authentication fails
    """
    is_valid, payload, message = _extract_and_validate_token(auth_header)

    if not is_valid:
        if message == "MISSING_AUTH_HEADER":
            raise HTTPException(
                status_code=401,
                detail="Missing Authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif message == "MISSING_TOKEN":
            raise HTTPException(
                status_code=401,
                detail="No token provided",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif message == "ANON_KEY_REJECTED":
            raise HTTPException(
                status_code=401,
                detail="Anonymous keys are not allowed",
            )
        elif message == "TOKEN_EXPIRED":
            raise HTTPException(
                status_code=401,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif message == "INVALID_SIGNATURE":
            raise HTTPException(
                status_code=401,
                detail="Invalid token signature",
            )
        else:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication failed: {message}",
            )

    return payload


def get_current_user(authorization: str = Header(None)) -> str:
    """
    Extract user_id from validated JWT token.

    FastAPI dependency that returns authenticated user ID.

    Args:
        authorization: Authorization header value

    Returns:
        User ID from JWT subject claim

    Raises:
        HTTPException: 401 if authentication fails
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    is_valid, payload, message = _extract_and_validate_token(authorization)

    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {message}",
        )

    # Extract user_id from subject claim
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Token does not contain user identifier",
        )

    return user_id


def optional_auth(authorization: str = Header(None)) -> Optional[str]:
    """
    Optional authentication - returns user_id if valid, None otherwise.

    Useful for endpoints that work for both authenticated and anonymous users.

    Args:
        authorization: Authorization header value

    Returns:
        User ID if token valid, None otherwise
    """
    if not authorization:
        return None

    try:
        return get_current_user(authorization)
    except HTTPException:
        return None


def _extract_and_validate_token(auth_header: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Extract token from Authorization header and validate it.

    Args:
        auth_header: Authorization header value

    Returns:
        Tuple of (is_valid, payload, message)
    """
    if not auth_header:
        return False, None, "MISSING_AUTH_HEADER"

    # Extract token from "Bearer <token>" format
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
    elif auth_header.startswith("Bearer"):
        token = auth_header[6:]  # Handle "Bearer" without space
    else:
        token = auth_header

    return validate_jwt_token(token)


@lru_cache()
def get_jwt_config() -> Dict[str, Any]:
    """
    Get JWT configuration status.

    Returns:
        Dict with configuration status
    """
    return {
        "has_jose": HAS_JOSE,
        "has_secret": bool(JWT_SECRET),
        "dev_mode": DEV_MODE,
        "algorithm": JWT_ALGORITHM,
    }


# Public API
__all__ = [
    "require_auth",
    "get_current_user",
    "optional_auth",
    "validate_jwt_token",
    "AuthenticationError",
    "MissingTokenError",
    "InvalidTokenError",
    "AnonKeyRejectedError",
]
