"""PMOVES-DoX Security Module.

Implements Defense in Depth security patterns based on patterns.yaml rules.
This module provides:
- Pattern loading and parsing from YAML configuration
- Command validation against blocked/ask patterns
- Path validation for zero-access, read-only, and no-delete paths
- FastAPI middleware for request interception

Based on the BoTZ doctrine's "Damage Control" security principles:
- Deterministic Hooks: Hardcoded regex rules for blocking dangerous commands
- Granular Permissions: Zero Access, Read-Only, No-Delete path zones
- Defense in Depth: Multiple layers of validation

Usage:
    from app.security import SecurityMiddleware, CommandValidator, PathValidator

    # Add middleware to FastAPI app
    app.add_middleware(SecurityMiddleware)

    # Or validate directly
    result = CommandValidator.validate("rm -rf /")
    if result.blocked:
        raise SecurityError(result.reason)
"""

from .patterns import PatternsLoader, SecurityPatterns
from .validators import (
    CommandValidator,
    PathValidator,
    ValidationResult,
    ValidationStatus,
)
from .middleware import SecurityMiddleware

__all__ = [
    "PatternsLoader",
    "SecurityPatterns",
    "CommandValidator",
    "PathValidator",
    "ValidationResult",
    "ValidationStatus",
    "SecurityMiddleware",
]
