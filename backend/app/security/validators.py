"""Security validators for commands and paths.

Provides validation logic for:
- Commands: Check against blocked/ask patterns
- Paths: Check against zero-access/read-only/no-delete zones

Based on the BoTZ "Defense in Depth" doctrine with granular permissions:
- Zero Access: Files the agent cannot see (e.g., .env, private keys)
- Read-Only: Core framework code that should not be modified
- No Delete: Valuable data that can be appended to but not removed
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from .patterns import PatternsLoader, SecurityPatterns, get_security_patterns

logger = logging.getLogger(__name__)


class ValidationStatus(str, Enum):
    """Validation result status."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    ASK_REQUIRED = "ask_required"


class PathOperation(str, Enum):
    """Types of path operations."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"


@dataclass
class ValidationResult:
    """Result of a security validation check."""

    status: ValidationStatus
    allowed: bool
    blocked: bool
    ask_required: bool
    reason: Optional[str] = None
    matched_pattern: Optional[str] = None

    @classmethod
    def allow(cls) -> "ValidationResult":
        """Create an allowed result."""
        return cls(
            status=ValidationStatus.ALLOWED,
            allowed=True,
            blocked=False,
            ask_required=False,
        )

    @classmethod
    def block(cls, reason: str, pattern: Optional[str] = None) -> "ValidationResult":
        """Create a blocked result."""
        return cls(
            status=ValidationStatus.BLOCKED,
            allowed=False,
            blocked=True,
            ask_required=False,
            reason=reason,
            matched_pattern=pattern,
        )

    @classmethod
    def ask(cls, reason: str, pattern: Optional[str] = None) -> "ValidationResult":
        """Create an ask-required result."""
        return cls(
            status=ValidationStatus.ASK_REQUIRED,
            allowed=False,
            blocked=False,
            ask_required=True,
            reason=reason,
            matched_pattern=pattern,
        )


class CommandValidator:
    """Validator for command strings against security patterns."""

    def __init__(self, patterns: Optional[SecurityPatterns] = None):
        """Initialize with security patterns.

        Args:
            patterns: SecurityPatterns to use. If None, loads from default location.
        """
        self._patterns = patterns or get_security_patterns()

    @classmethod
    def validate(cls, cmd: str, patterns: Optional[SecurityPatterns] = None) -> ValidationResult:
        """Validate a command string against security patterns.

        Args:
            cmd: The command string to validate.
            patterns: Optional patterns to use (defaults to cached patterns).

        Returns:
            ValidationResult indicating if command is allowed, blocked, or requires confirmation.
        """
        if patterns is None:
            patterns = get_security_patterns()

        if not cmd or not cmd.strip():
            return ValidationResult.allow()

        # Check blocked patterns first (more restrictive)
        for pattern in patterns.blocked_patterns:
            if pattern.compiled.search(cmd):
                logger.warning(
                    f"Command blocked: '{cmd[:100]}...' matched pattern '{pattern.pattern}' - {pattern.reason}"
                )
                return ValidationResult.block(
                    reason=pattern.reason,
                    pattern=pattern.pattern,
                )

        # Check ask patterns (require confirmation)
        for pattern in patterns.ask_patterns:
            if pattern.compiled.search(cmd):
                logger.info(
                    f"Command requires confirmation: '{cmd[:100]}...' matched pattern '{pattern.pattern}' - {pattern.reason}"
                )
                return ValidationResult.ask(
                    reason=pattern.reason,
                    pattern=pattern.pattern,
                )

        return ValidationResult.allow()

    def validate_command(self, cmd: str) -> ValidationResult:
        """Instance method for command validation."""
        return self.validate(cmd, self._patterns)


class PathValidator:
    """Validator for file paths against security zones."""

    def __init__(self, patterns: Optional[SecurityPatterns] = None):
        """Initialize with security patterns.

        Args:
            patterns: SecurityPatterns to use. If None, loads from default location.
        """
        self._patterns = patterns or get_security_patterns()

    @classmethod
    def validate(
        cls,
        path: str,
        operation: str = "read",
        patterns: Optional[SecurityPatterns] = None,
    ) -> ValidationResult:
        """Validate a path for a specific operation.

        Args:
            path: The file path to validate.
            operation: The operation type ("read", "write", "delete", "execute").
            patterns: Optional patterns to use (defaults to cached patterns).

        Returns:
            ValidationResult indicating if the operation is allowed or blocked.
        """
        if patterns is None:
            patterns = get_security_patterns()

        if not path or not path.strip():
            return ValidationResult.allow()

        # Normalize operation
        op = operation.lower().strip()

        # Check zero-access paths (blocked for ALL operations)
        for pattern in patterns.zero_access_paths:
            if pattern.matches(path):
                logger.warning(
                    f"Path blocked (zero-access): '{path}' matched '{pattern.pattern}'"
                )
                return ValidationResult.block(
                    reason=f"Zero-access path: {pattern.pattern}",
                    pattern=pattern.pattern,
                )

        # Check read-only paths (blocked for write/delete operations)
        if op in ("write", "delete", "execute"):
            for pattern in patterns.read_only_paths:
                if pattern.matches(path):
                    logger.warning(
                        f"Path blocked (read-only): '{path}' for '{op}' matched '{pattern.pattern}'"
                    )
                    return ValidationResult.block(
                        reason=f"Read-only path (cannot {op}): {pattern.pattern}",
                        pattern=pattern.pattern,
                    )

        # Check no-delete paths (blocked for delete operations only)
        if op == "delete":
            for pattern in patterns.no_delete_paths:
                if pattern.matches(path):
                    logger.warning(
                        f"Path blocked (no-delete): '{path}' matched '{pattern.pattern}'"
                    )
                    return ValidationResult.block(
                        reason=f"No-delete path: {pattern.pattern}",
                        pattern=pattern.pattern,
                    )

        return ValidationResult.allow()

    def validate_path(self, path: str, operation: str = "read") -> ValidationResult:
        """Instance method for path validation."""
        return self.validate(path, operation, self._patterns)

    @classmethod
    def validate_multiple(
        cls,
        paths: List[str],
        operation: str = "read",
        patterns: Optional[SecurityPatterns] = None,
    ) -> Tuple[List[str], List[Tuple[str, ValidationResult]]]:
        """Validate multiple paths and return allowed/blocked lists.

        Args:
            paths: List of paths to validate.
            operation: Operation type for all paths.
            patterns: Optional patterns to use.

        Returns:
            Tuple of (allowed_paths, blocked_paths_with_results).
        """
        allowed = []
        blocked = []

        for path in paths:
            result = cls.validate(path, operation, patterns)
            if result.allowed:
                allowed.append(path)
            else:
                blocked.append((path, result))

        return allowed, blocked


class RequestValidator:
    """Validator for HTTP request parameters that may contain commands or paths."""

    # Parameters that might contain command-like content
    COMMAND_PARAMS = frozenset([
        "cmd", "command", "query", "sql", "script", "exec", "shell",
        "bash", "sh", "run", "execute", "action"
    ])

    # Parameters that might contain file paths
    PATH_PARAMS = frozenset([
        "path", "file", "filepath", "filename", "dir", "directory",
        "src", "source", "dst", "destination", "target", "location"
    ])

    def __init__(self, patterns: Optional[SecurityPatterns] = None):
        """Initialize with security patterns."""
        self._patterns = patterns or get_security_patterns()
        self._cmd_validator = CommandValidator(self._patterns)
        self._path_validator = PathValidator(self._patterns)

    def validate_params(
        self,
        params: dict,
        operation: str = "read",
    ) -> Tuple[bool, List[ValidationResult]]:
        """Validate request parameters for security concerns.

        Args:
            params: Dictionary of parameter names to values.
            operation: Default operation type for path validation.

        Returns:
            Tuple of (all_allowed, list of validation results for failed checks).
        """
        failures = []

        for key, value in params.items():
            if not isinstance(value, str):
                continue

            key_lower = key.lower()

            # Check command-like parameters
            if key_lower in self.COMMAND_PARAMS:
                result = self._cmd_validator.validate_command(value)
                if not result.allowed:
                    failures.append(result)

            # Check path-like parameters
            if key_lower in self.PATH_PARAMS:
                result = self._path_validator.validate_path(value, operation)
                if not result.allowed:
                    failures.append(result)

        return len(failures) == 0, failures

    def validate_body(
        self,
        body: dict,
        operation: str = "write",
    ) -> Tuple[bool, List[ValidationResult]]:
        """Validate request body content.

        Args:
            body: Request body as dictionary.
            operation: Operation type (default "write" for POST/PUT bodies).

        Returns:
            Tuple of (all_allowed, list of validation results for failed checks).
        """
        return self.validate_params(body, operation)
