"""FastAPI security middleware for Defense in Depth validation.

Intercepts incoming requests and validates:
- Query parameters for command-like content
- Request bodies for dangerous commands or protected paths
- File paths in upload/download endpoints

Based on the BoTZ doctrine's "Damage Control" security layer.
"""

import json
import logging
import os
from datetime import datetime
from typing import Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .patterns import PatternsLoader, SecurityPatterns
from .validators import (
    CommandValidator,
    PathValidator,
    RequestValidator,
    ValidationResult,
    ValidationStatus,
)

logger = logging.getLogger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that enforces Defense in Depth security patterns.

    Features:
    - Validates command-like parameters against blocked patterns
    - Validates file paths against zero-access/read-only/no-delete zones
    - Logs all security validation attempts
    - Feature-flagged with SECURITY_MIDDLEWARE_ENABLED env var
    """

    # Endpoints that are exempt from security checks (health, static, etc.)
    EXEMPT_PATHS = frozenset([
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    ])

    # Endpoints that deal with file paths (need path validation)
    PATH_ENDPOINTS = frozenset([
        "/upload",
        "/artifacts",
        "/open/pdf",
        "/download",
        "/export",
    ])

    # Endpoints that may contain command-like content
    COMMAND_ENDPOINTS = frozenset([
        "/search",
        "/qa",
        "/extract",
        "/analyze",
    ])

    def __init__(
        self,
        app: ASGIApp,
        patterns: Optional[SecurityPatterns] = None,
        enabled: Optional[bool] = None,
        log_all: bool = False,
    ):
        """Initialize the security middleware.

        Args:
            app: The ASGI application.
            patterns: Security patterns to use (loads from file if None).
            enabled: Whether middleware is enabled (defaults to env var).
            log_all: Log all validations, not just failures.
        """
        super().__init__(app)

        # Check if enabled via env var
        if enabled is None:
            enabled = os.getenv("SECURITY_MIDDLEWARE_ENABLED", "true").lower() in ("1", "true", "yes", "on")

        self._enabled = enabled
        self._log_all = log_all

        # Load patterns
        if patterns is None:
            try:
                self._patterns = PatternsLoader.get_patterns()
            except Exception as e:
                logger.error(f"Failed to load security patterns: {e}")
                self._patterns = SecurityPatterns()
        else:
            self._patterns = patterns

        # Create validators
        self._cmd_validator = CommandValidator(self._patterns)
        self._path_validator = PathValidator(self._patterns)
        self._request_validator = RequestValidator(self._patterns)

        if self._enabled:
            logger.info("Security middleware initialized and enabled")
        else:
            logger.info("Security middleware initialized but DISABLED")

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process each request through security validation.

        Args:
            request: The incoming request.
            call_next: The next middleware/handler.

        Returns:
            Response from the handler or a 403 if blocked.
        """
        # Skip if disabled
        if not self._enabled:
            return await call_next(request)

        # Skip exempt paths
        path = request.url.path
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip static file requests
        if path.startswith("/static/") or path.startswith("/hyperdimensions/"):
            return await call_next(request)

        # Validate request
        validation_result = await self._validate_request(request)

        if validation_result and not validation_result.allowed:
            return self._create_security_response(request, validation_result)

        return await call_next(request)

    async def _validate_request(self, request: Request) -> Optional[ValidationResult]:
        """Validate the request against security patterns.

        Args:
            request: The incoming request.

        Returns:
            ValidationResult if validation failed, None if allowed.
        """
        path = request.url.path
        method = request.method

        # Determine operation type based on HTTP method
        operation = "read"
        if method in ("POST", "PUT", "PATCH"):
            operation = "write"
        elif method == "DELETE":
            operation = "delete"

        # Validate query parameters
        query_params = dict(request.query_params)
        if query_params:
            allowed, failures = self._request_validator.validate_params(
                query_params, operation
            )
            if not allowed and failures:
                self._log_validation(request, failures[0], "query_params")
                return failures[0]

        # Validate request body for POST/PUT/PATCH
        if method in ("POST", "PUT", "PATCH"):
            try:
                # Read body if present
                body = await self._get_body_dict(request)
                if body:
                    allowed, failures = self._request_validator.validate_body(
                        body, operation
                    )
                    if not allowed and failures:
                        self._log_validation(request, failures[0], "body")
                        return failures[0]
            except Exception as e:
                # Body parsing failed, continue with request
                logger.debug(f"Could not parse request body: {e}")

        # Check path-specific endpoints
        if any(path.startswith(ep) for ep in self.PATH_ENDPOINTS):
            # Extract path from query or path params
            file_path = query_params.get("path") or query_params.get("file")
            if file_path:
                result = self._path_validator.validate_path(file_path, operation)
                if not result.allowed:
                    self._log_validation(request, result, "file_path")
                    return result

        # Log successful validation if requested
        if self._log_all:
            self._log_validation(request, ValidationResult.allow(), "passed")

        return None

    async def _get_body_dict(self, request: Request) -> Optional[dict]:
        """Attempt to parse request body as JSON dict.

        Args:
            request: The incoming request.

        Returns:
            Dictionary if body is valid JSON, None otherwise.
        """
        content_type = request.headers.get("content-type", "")

        if "application/json" not in content_type:
            return None

        try:
            body_bytes = await request.body()
            if not body_bytes:
                return None
            return json.loads(body_bytes)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _create_security_response(
        self,
        request: Request,
        result: ValidationResult,
    ) -> JSONResponse:
        """Create a security violation response.

        Args:
            request: The blocked request.
            result: The validation result.

        Returns:
            JSONResponse with 403 status.
        """
        status_code = 403 if result.blocked else 400

        response_body = {
            "error": "Security validation failed",
            "status": result.status.value,
            "reason": result.reason or "Request blocked by security policy",
            "path": request.url.path,
            "method": request.method,
        }

        # Add ask prompt for ask_required status
        if result.ask_required:
            response_body["action_required"] = "confirmation"
            response_body["message"] = (
                f"This operation requires confirmation: {result.reason}"
            )

        return JSONResponse(
            status_code=status_code,
            content=response_body,
        )

    def _log_validation(
        self,
        request: Request,
        result: ValidationResult,
        source: str,
    ) -> None:
        """Log a security validation event.

        Args:
            request: The request being validated.
            result: The validation result.
            source: Source of the validation (query_params, body, etc.).
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path,
            "method": request.method,
            "source": source,
            "status": result.status.value,
            "reason": result.reason,
            "pattern": result.matched_pattern,
            "client_host": request.client.host if request.client else "unknown",
        }

        if result.blocked:
            logger.warning(f"SECURITY_BLOCKED: {json.dumps(log_entry)}")
        elif result.ask_required:
            logger.info(f"SECURITY_ASK: {json.dumps(log_entry)}")
        elif self._log_all:
            logger.debug(f"SECURITY_ALLOWED: {json.dumps(log_entry)}")


def create_security_middleware(
    enabled: Optional[bool] = None,
    log_all: bool = False,
) -> type:
    """Factory function to create configured security middleware.

    Args:
        enabled: Whether middleware is enabled.
        log_all: Whether to log all validations.

    Returns:
        Configured SecurityMiddleware class.
    """
    class ConfiguredSecurityMiddleware(SecurityMiddleware):
        def __init__(self, app: ASGIApp):
            super().__init__(app, enabled=enabled, log_all=log_all)

    return ConfiguredSecurityMiddleware
