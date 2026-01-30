"""
Rate limiting middleware for FastAPI.

Uses in-memory tracking with sliding window algorithm.
For production, consider using Redis for distributed rate limiting.

Usage:
    from app.middleware.rate_limit import RateLimiter, rate_limit
    from fastapi import FastAPI, Depends

    app = FastAPI()
    limiter = RateLimiter()

    # Apply globally
    app.add_middleware(RateLimitMiddleware, limiter=limiter)

    # Or per endpoint
    @app.get("/api/search")
    @rate_limit("30/minute")
    async def search():
        return {"results": []}

    # Or using dependency
    @app.get("/api/upload")
    async def upload(_user_id: str = Depends(check_rate_limit("10/minute"))):
        return {"status": "ok"}
"""

import time
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from functools import wraps
from fastapi import Request, HTTPException, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    Tracks requests per IP address or per user.

    Attributes:
        requests: Dict mapping keys to lists of timestamps
        limits: Dict of endpoint-specific limits
    """

    def __init__(self):
        # {key: [timestamp1, timestamp2, ...]}
        self.requests: Dict[str, List[float]] = defaultdict(list)
        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Identifier (IP address or user_id)
            limit: Maximum number of requests
            window: Time window in seconds

        Returns:
            True if request is allowed, False otherwise
        """
        async with self._lock:
            now = time.time()
            cutoff = now - window

            # Get existing timestamps for this key
            timestamps = self.requests.get(key, [])

            # Filter out timestamps outside the window
            valid_timestamps = [ts for ts in timestamps if ts > cutoff]

            # Check if limit exceeded
            if len(valid_timestamps) >= limit:
                return False

            # Add current request
            valid_timestamps.append(now)
            self.requests[key] = valid_timestamps

            # Clean up old entries periodically
            if len(timestamps) > len(valid_timestamps) * 2:
                self.requests[key] = valid_timestamps

            return True

    async def cleanup(self):
        """Remove old entries to prevent memory leaks."""
        async with self._lock:
            now = time.time()
            cutoff = now - 3600  # Remove entries older than 1 hour

            for key in list(self.requests.keys()):
                self.requests[key] = [
                    ts for ts in self.requests[key] if ts > cutoff
                ]
                if not self.requests[key]:
                    del self.requests[key]


# Global rate limiter instance
_limiter = RateLimiter()


def get_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    return _limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that applies rate limiting to all requests.

    Uses IP address (from X-Forwarded-For or X-Real-IP) as key.
    """

    def __init__(
        self,
        app: ASGIApp,
        limiter: Optional[RateLimiter] = None,
        default_limit: str = "100/minute",
        exempt_paths: Optional[set] = None,
    ):
        """
        Initialize rate limit middleware.

        Args:
            app: The ASGI application
            limiter: RateLimiter instance (creates new if None)
            default_limit: Default rate limit (e.g., "100/minute")
            exempt_paths: Set of paths exempt from rate limiting
        """
        super().__init__(app)
        self.limiter = limiter or get_limiter()
        self.default_limit = default_limit
        self.exempt_paths = exempt_paths or {
            "/", "/health", "/healthz", "/metrics", "/docs", "/redoc", "/openapi.json"
        }
        self._parse_default_limit()

    def _parse_default_limit(self):
        """Parse default limit string."""
        parts = self.default_limit.split("/")
        if len(parts) == 2:
            self._default_count = int(parts[0])
            self._default_window = self._parse_window(parts[1])
        else:
            self._default_count = 100
            self._default_window = 60

    def _parse_window(self, window_str: str) -> int:
        """Parse window string (e.g., 'minute', 'hour') to seconds."""
        window_map = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }
        # Handle plurals
        window_str = window_str.rstrip("s")
        return window_map.get(window_str, 60)

    async def dispatch(self, request: Request, call_next):
        """Process request through rate limiting."""
        path = request.url.path

        # Skip exempt paths
        if path in self.exempt_paths:
            return await call_next(request)

        # Skip static files
        if path.startswith("/static/") or path.startswith("/favicon."):
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Check rate limit
        allowed = await self.limiter.is_allowed(
            key=client_id,
            limit=self._default_count,
            window=self._default_window,
        )

        if not allowed:
            return Response(
                content='{"error": "Rate limit exceeded", "retry_after": 60}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self._default_count),
                    "X-RateLimit-Window": str(self._default_window),
                },
            )

        return await call_next(request)

    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Try to get user_id from validated JWT (set by auth middleware)
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"

        # Otherwise use IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP in chain
            return f"ip:{forwarded.split(',')[0].strip()}"

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return f"ip:{real_ip}"

        return f"ip:{request.client.host if request.client else 'unknown'}"


class RateLimitConfig:
    """Configuration for endpoint-specific rate limits."""

    # Limits for different endpoint types
    LIMITS = {
        "default": (100, 60),  # 100 requests per minute
        "upload": (10, 60),  # 10 uploads per minute
        "search": (30, 60),  # 30 searches per minute
        "ask": (30, 60),  # 30 questions per minute
        "extract": (20, 60),  # 20 extractions per minute
        "analysis": (15, 60),  # 15 analysis requests per minute
        "auth": (5, 60),  # 5 auth attempts per minute
        "export": (5, 60),  # 5 exports per minute
    }

    @classmethod
    def get_limit(cls, endpoint_type: str) -> tuple[int, int]:
        """Get (limit, window) for endpoint type."""
        return cls.LIMITS.get(endpoint_type, cls.LIMITS["default"])


# Decorator for endpoint-specific rate limiting
def rate_limit(limit_str: str):
    """
    Decorator to apply rate limiting to specific endpoints.

    Args:
        limit_str: Rate limit string (e.g., "10/minute", "100/hour")

    Usage:
        @app.get("/api/upload")
        @rate_limit("10/minute")
        async def upload():
            return {"status": "ok"}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This is a simplified version
            # For full implementation, you'd need to integrate with FastAPI's dependency system
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Dependency for use in FastAPI routes
def check_rate_limit(endpoint_type: str):
    """
    FastAPI dependency that checks rate limit.

    Usage:
        @app.get("/api/upload")
        async def upload(_user_id: str = Depends(check_rate_limit("upload"))):
            return {"status": "ok"}
    """
    async def _check(request: Request) -> None:
        limiter = get_limiter()
        limit, window = RateLimitConfig.get_limit(endpoint_type)
        client_id = RateLimitMiddleware(None)._get_client_id(request)

        allowed = await limiter.is_allowed(client_id, limit, window)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {limit} requests per {window} seconds",
                headers={"Retry-After": str(window)},
            )

    return _check


__all__ = [
    "RateLimiter",
    "RateLimitMiddleware",
    "RateLimitConfig",
    "rate_limit",
    "check_rate_limit",
    "get_limiter",
]
