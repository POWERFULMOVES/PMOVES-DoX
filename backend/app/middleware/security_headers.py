"""
Security headers middleware for FastAPI.

Adds comprehensive security headers to all responses:
- Content-Security-Policy
- X-Content-Type-Options
- X-Frame-Options
- Strict-Transport-Security
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy

Usage:
    from app.middleware.security_headers import SecurityHeadersMiddleware
    from fastapi import FastAPI

    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import os


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: default-src 'self'
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: restrictive policy
    """

    # Whether to enable HSTS (only in production with HTTPS)
    ENABLE_HSTS = os.getenv("ENABLE_HSTS", "false").lower() == "true"

    # CSP configuration
    CSP_DIRECTIVES = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # unsafe-inline for development
        "style-src 'self' 'unsafe-inline'",  # unsafe-inline for Tailwind
        "img-src 'self' data: blob: https:",
        "font-src 'self' data:",
        "connect-src 'self' https:",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]

    # Permissions policy (restricts browser features)
    PERMISSIONS_POLICY = [
        "camera=()",
        "microphone=()",
        "geolocation=()",
        "payment=()",
        "usb=()",
        "magnetometer=()",
        "gyroscope=()",
        "accelerometer=()",
    ]

    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # X-Content-Type-Options: prevents MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: prevents clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection: enables browser XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy: controls referrer information sent
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy: restricts browser features
        response.headers["Permissions-Policy"] = ", ".join(self.PERMISSIONS_POLICY)

        # Content-Security-Policy: restricts resource loading
        response.headers["Content-Security-Policy"] = "; ".join(self.CSP_DIRECTIVES)

        # Strict-Transport-Security: enforce HTTPS (only if enabled)
        if self.ENABLE_HSTS:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Remove Server header if present (security by obscurity)
        if "Server" in response.headers:
            del response.headers["Server"]

        # Remove X-Powered-By header
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        return Response(
            content=response.body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )


def get_csp_directives() -> str:
    """Get current CSP directives as a string."""
    return "; ".join(SecurityHeadersMiddleware.CSP_DIRECTIVES)


def get_permissions_policy() -> str:
    """Get current permissions policy as a string."""
    return ", ".join(SecurityHeadersMiddleware.PERMISSIONS_POLICY)


__all__ = [
    "SecurityHeadersMiddleware",
    "get_csp_directives",
    "get_permissions_policy",
]
