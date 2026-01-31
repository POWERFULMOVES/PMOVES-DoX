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

SECURITY WARNING:
    In development mode (ENVIRONMENT=development), this module may return a fake
    "dev_user" payload if python-jose is not installed or SUPABASE_JWT_SECRET is not
    configured. Always verify ENVIRONMENT=production in production deployments.
"""

import logging
import os
from typing import Tuple, Dict, Any, Optional
from fastapi import Header, HTTPException
from functools import lru_cache

logger = logging.getLogger(__name__)

# HS256: HMAC-SHA256 - Supabase JWTs use HS256 with shared secret
# Other services may use RS256 (RSA) with asymmetric keys
JWT_ALGORITHM = "HS256"

try:
    from jose import jwt
    HAS_JOSE = True
except ImportError:
    HAS_JOSE = False
    jwt = None
    logger.error(
        "python-jose library not installed. JWT validation will NOT work. "
        "Install with: pip install 'python-jose[cryptography]>=3.3.0'"
    )

# Supabase JWT secret (shared with PMOVES.AI)
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# Development mode flag - defaults to production for security
# Explicitly set ENVIRONMENT=development to enable dev mode bypass
DEV_MODE = os.getenv("ENVIRONMENT", "production") == "development"

# Startup security guard
if not DEV_MODE and not HAS_JOSE:
    raise RuntimeError(
        "python-jose is required in production mode. "
        "Install with: pip install 'python-jose[cryptography]>=3.5.0'"
    )

if not DEV_MODE and not JWT_SECRET:
    raise RuntimeError(
        "SUPABASE_JWT_SECRET must be configured in production mode. "
        "Set the SUPABASE_JWT_SECRET environment variable."
    )

# Log configuration status at startup
if not JWT_SECRET:
    if DEV_MODE:
        logger.warning(
            "SUPABASE_JWT_SECRET not configured - using dev mode bypass. "
            "Configure SUPABASE_JWT_SECRET for proper authentication."
        )
else:
    logger.info("JWT authentication configured properly")


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
    - Must not be expired (exp claim verified)
    - Can be service_role or authenticated user tokens
    - Rejects Supabase anonymous tokens (role == "anon")
    """
    if not token:
        return False, None, "MISSING_TOKEN"

    if not HAS_JOSE:
        if DEV_MODE:
            logger.warning(
                "JWT library not installed; allowing requests in DEV_MODE. "
                "Install python-jose for proper authentication."
            )
            return True, {"sub": "dev_user", "role": "authenticated"}, "VALIDATION_UNAVAILABLE"
        logger.error("JWT library not installed and not in DEV_MODE - authentication will fail")
        return False, None, "JOSE_NOT_INSTALLED"

    if not JWT_SECRET:
        if DEV_MODE:
            logger.warning(
                "JWT_SECRET not configured; allowing requests in DEV_MODE. "
                "Configure SUPABASE_JWT_SECRET for proper authentication."
            )
            return True, {"sub": "dev_user", "role": "authenticated"}, "NO_SECRET_CONFIGURED"
        logger.error("JWT_SECRET not configured and not in DEV_MODE - authentication will fail")
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

        # Check role - reject Supabase anonymous tokens
        role = payload.get("role", "")
        if role == "anon":
            logger.debug("Anonymous token rejected")
            return False, payload, "ANON_KEY_REJECTED"

        # Accept service_role and authenticated user tokens
        return True, payload, "VALID_TOKEN"

    except jwt.ExpiredSignatureError:
        logger.debug("Token validation failed: expired signature")
        return False, None, "TOKEN_EXPIRED"
    except jwt.InvalidSignatureError:
        logger.debug("Token validation failed: invalid signature")
        return False, None, "INVALID_SIGNATURE"
    except jwt.JWTError as e:
        # Generic JWT errors (alg mismatch, invalid claims, etc.)
        logger.warning(f"Token validation failed: JWT error - {str(e)}")
        return False, None, "JWT_ERROR"
    except (AttributeError, TypeError, ValueError) as e:
        # These indicate programming/configuration errors, log them
        logger.error(f"Token validation configuration error: {type(e).__name__}: {str(e)}")
        return False, None, "CONFIG_ERROR"


def require_auth(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    Validate Authorization header and extract user info.

    SECURITY WARNING: In development mode (ENVIRONMENT=development), this function
    may return a fake "dev_user" payload if JWT validation is unavailable.

    FastAPI dependency that validates JWT and returns user payload.

    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")

    Returns:
        Dict with JWT payload containing user info

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
        if message == "MISSING_TOKEN":
            raise HTTPException(
                status_code=401,
                detail="No token provided",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif message == "ANON_KEY_REJECTED":
            raise HTTPException(
                status_code=401,
                detail="Anonymous tokens are not allowed",
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
        elif message == "CONFIG_ERROR":
            raise HTTPException(
                status_code=500,
                detail="Authentication configuration error",
            )
        else:
            raise HTTPException(
                status_code=401,
                detail="Authentication failed",
            )

    return payload


def get_current_user(authorization: str = Header(None)) -> str:
    """
    Extract user_id from validated JWT token.

    SECURITY WARNING: In development mode (ENVIRONMENT=development), this function
    may return a fake "dev_user" if JWT validation is unavailable.

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
        if message == "CONFIG_ERROR":
            raise HTTPException(
                status_code=500,
                detail="Authentication configuration error",
            )
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
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

    Logs authentication failures for security monitoring while allowing
    anonymous access. Useful for endpoints that work for both authenticated
    and anonymous users.

    Args:
        authorization: Authorization header value

    Returns:
        User ID if token valid, None otherwise
    """
    if not authorization:
        return None

    try:
        return get_current_user(authorization)
    except HTTPException as e:
        # Log auth failures for security monitoring (but allow anonymous access)
        logger.warning(
            f"Optional authentication failed: {e.detail}",
            extra={
                "event_type": "auth_failure_optional",
                "status_code": e.status_code,
            }
        )
        return None


def _extract_and_validate_token(auth_header: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Extract token from Authorization header and validate it.

    Args:
        auth_header: Authorization header value (case-insensitive "Bearer" handled)

    Returns:
        Tuple of (is_valid, payload, message)
    """
    if not auth_header:
        return False, None, "MISSING_AUTH_HEADER"

    # Extract token from "Bearer <token>" format (case-insensitive)
    header_lower = auth_header.lower()
    if header_lower.startswith("bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix (preserve original case)
    elif header_lower.startswith("bearer"):
        token = auth_header[6:]  # Handle "Bearer" without space
    else:
        token = auth_header

    return validate_jwt_token(token)


@lru_cache()
def get_jwt_config() -> Dict[str, Any]:
    """
    Get JWT configuration status.

    NOTE: This function is cached. If environment variables change at runtime
    (e.g., in tests), the cached value won't reflect changes.

    Returns:
        Dict with configuration status including:
        - has_jose: Whether python-jose is installed
        - has_secret: Whether JWT_SECRET is configured
        - dev_mode: Whether running in development mode
        - algorithm: JWT algorithm being used
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
    "get_jwt_config",
]
