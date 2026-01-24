"""Security patterns loader and parser.

Loads and parses the patterns.yaml file containing security rules for:
- Blocked bash commands (bashToolPatterns)
- Zero-access paths (zeroAccessPaths)
- Read-only paths (readOnlyPaths)
- No-delete paths (noDeletePaths)

The patterns are compiled into efficient regex matchers for runtime validation.
"""

import fnmatch
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple

import yaml

logger = logging.getLogger(__name__)


@dataclass
class CommandPattern:
    """A compiled command pattern with metadata."""

    pattern: str
    compiled: Pattern[str]
    reason: str
    ask: bool = False

    @classmethod
    def from_dict(cls, data: Dict) -> "CommandPattern":
        """Create a CommandPattern from a dictionary entry."""
        pattern_str = data.get("pattern", "")
        reason = data.get("reason", "Unknown security rule")
        ask = data.get("ask", False)

        try:
            compiled = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern_str}': {e}")
            # Create a pattern that never matches
            compiled = re.compile(r"^\b$")

        return cls(
            pattern=pattern_str,
            compiled=compiled,
            reason=reason,
            ask=ask,
        )


@dataclass
class PathPattern:
    """A path pattern for access control."""

    pattern: str
    is_glob: bool
    expanded_path: Optional[str] = None

    @classmethod
    def from_string(cls, pattern: str) -> "PathPattern":
        """Create a PathPattern from a string."""
        # Expand home directory
        expanded = pattern
        if pattern.startswith("~/"):
            expanded = os.path.expanduser(pattern)
        elif pattern.startswith("~\\"):
            expanded = os.path.expanduser(pattern)

        # Check if it's a glob pattern
        is_glob = any(c in pattern for c in ["*", "?", "[", "]"])

        return cls(
            pattern=pattern,
            is_glob=is_glob,
            expanded_path=expanded if expanded != pattern else None,
        )

    def matches(self, path: str) -> bool:
        """Check if the given path matches this pattern."""
        # Normalize path separators
        normalized_path = path.replace("\\", "/")
        check_pattern = (self.expanded_path or self.pattern).replace("\\", "/")

        # Remove trailing slashes for consistent matching
        normalized_path = normalized_path.rstrip("/")
        check_pattern = check_pattern.rstrip("/")

        if self.is_glob:
            # Use fnmatch for glob patterns
            # Check both the full path and just the filename
            if fnmatch.fnmatch(normalized_path, check_pattern):
                return True
            if fnmatch.fnmatch(os.path.basename(normalized_path), check_pattern):
                return True
            # Also check if any path component matches (e.g., "*.env" in "/foo/bar/.env")
            for component in normalized_path.split("/"):
                if fnmatch.fnmatch(component, check_pattern):
                    return True
            return False
        else:
            # Exact match or prefix match for directories
            if normalized_path == check_pattern:
                return True
            # Check if path is under this directory
            if check_pattern.endswith("/"):
                return normalized_path.startswith(check_pattern)
            # Check if path starts with pattern (directory containment)
            return normalized_path.startswith(check_pattern + "/")


@dataclass
class SecurityPatterns:
    """Container for all loaded security patterns."""

    bash_patterns: List[CommandPattern] = field(default_factory=list)
    zero_access_paths: List[PathPattern] = field(default_factory=list)
    read_only_paths: List[PathPattern] = field(default_factory=list)
    no_delete_paths: List[PathPattern] = field(default_factory=list)

    # Pre-compiled lists for quick access
    blocked_patterns: List[CommandPattern] = field(default_factory=list)
    ask_patterns: List[CommandPattern] = field(default_factory=list)

    def __post_init__(self):
        """Separate patterns into blocked and ask categories."""
        self._categorize_patterns()

    def _categorize_patterns(self):
        """Categorize bash patterns into blocked and ask lists."""
        self.blocked_patterns = [p for p in self.bash_patterns if not p.ask]
        self.ask_patterns = [p for p in self.bash_patterns if p.ask]


class PatternsLoader:
    """Loader for security patterns from YAML files."""

    _instance: Optional["PatternsLoader"] = None
    _patterns: Optional[SecurityPatterns] = None
    _patterns_path: Optional[Path] = None
    _last_mtime: float = 0

    def __new__(cls):
        """Singleton pattern for efficient reuse."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_default_patterns_path(cls) -> Path:
        """Get the default patterns.yaml path."""
        # Check multiple possible locations
        candidates = [
            # Project root .claude/hooks/damage-control/patterns.yaml
            Path(__file__).resolve().parents[4] / ".claude" / "hooks" / "damage-control" / "patterns.yaml",
            # Adjacent to backend directory
            Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "damage-control" / "patterns.yaml",
            # In security module directory
            Path(__file__).parent / "patterns.yaml",
            # Environment variable override
            Path(os.getenv("SECURITY_PATTERNS_PATH", "")) if os.getenv("SECURITY_PATTERNS_PATH") else None,
        ]

        for candidate in candidates:
            if candidate and candidate.exists():
                return candidate

        # Return the first candidate as default (may not exist)
        return candidates[0]

    def load(self, path: Optional[Path] = None, force_reload: bool = False) -> SecurityPatterns:
        """Load patterns from YAML file.

        Args:
            path: Path to patterns.yaml. If None, uses default location.
            force_reload: Force reload even if cached.

        Returns:
            SecurityPatterns instance with all loaded patterns.
        """
        if path is None:
            path = self.get_default_patterns_path()

        # Check if we need to reload
        if not force_reload and self._patterns is not None and self._patterns_path == path:
            try:
                current_mtime = path.stat().st_mtime
                if current_mtime == self._last_mtime:
                    return self._patterns
            except (OSError, FileNotFoundError):
                pass

        # Load the file
        self._patterns_path = path
        self._patterns = self._load_from_file(path)

        try:
            self._last_mtime = path.stat().st_mtime
        except (OSError, FileNotFoundError):
            self._last_mtime = 0

        return self._patterns

    def _load_from_file(self, path: Path) -> SecurityPatterns:
        """Load and parse the patterns file."""
        if not path.exists():
            logger.warning(f"Security patterns file not found: {path}")
            return SecurityPatterns()

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse patterns.yaml: {e}")
            return SecurityPatterns()
        except IOError as e:
            logger.error(f"Failed to read patterns.yaml: {e}")
            return SecurityPatterns()

        if not data:
            return SecurityPatterns()

        # Parse bash patterns
        bash_patterns = []
        for pattern_data in data.get("bashToolPatterns", []):
            if isinstance(pattern_data, dict):
                bash_patterns.append(CommandPattern.from_dict(pattern_data))

        # Parse path patterns
        zero_access = [PathPattern.from_string(p) for p in data.get("zeroAccessPaths", [])]
        read_only = [PathPattern.from_string(p) for p in data.get("readOnlyPaths", [])]
        no_delete = [PathPattern.from_string(p) for p in data.get("noDeletePaths", [])]

        patterns = SecurityPatterns(
            bash_patterns=bash_patterns,
            zero_access_paths=zero_access,
            read_only_paths=read_only,
            no_delete_paths=no_delete,
        )

        logger.info(
            f"Loaded security patterns: {len(bash_patterns)} commands, "
            f"{len(zero_access)} zero-access, {len(read_only)} read-only, "
            f"{len(no_delete)} no-delete paths"
        )

        return patterns

    def reload(self) -> SecurityPatterns:
        """Force reload patterns from file."""
        return self.load(force_reload=True)

    @classmethod
    def get_patterns(cls) -> SecurityPatterns:
        """Get cached patterns or load them."""
        instance = cls()
        return instance.load()


# Module-level convenience function
def get_security_patterns() -> SecurityPatterns:
    """Get the cached security patterns."""
    return PatternsLoader.get_patterns()
