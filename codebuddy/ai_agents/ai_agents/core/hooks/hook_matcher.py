"""Hook matcher for pattern-based tool name matching."""

import re
from typing import Dict, Pattern


class HookMatcher:
    """Matches tool names against hook patterns with caching support."""

    def __init__(self):
        """Initialize the hook matcher with pattern cache."""
        self._pattern_cache: Dict[str, Pattern] = {}

    def matches(self, pattern: str, tool_name: str) -> bool:
        """
        Check if a tool name matches the given pattern.

        Args:
            pattern: The pattern to match against (exact string, regex, or wildcard)
            tool_name: The name of the tool to match

        Returns:
            True if the tool name matches the pattern, False otherwise
        """
        if not pattern:
            return False
        if tool_name is None:
            return False

        # Handle wildcard pattern
        if pattern == "*":
            return True

        # Handle exact string matching (most common case)
        if pattern == tool_name:
            return True

        # Handle regex patterns
        try:
            compiled_pattern = self.compile_pattern(pattern)
            return bool(compiled_pattern.fullmatch(tool_name))
        except re.error:
            # If regex compilation fails, fall back to exact string matching
            return pattern == tool_name

    def compile_pattern(self, pattern: str) -> Pattern:
        """
        Compile a pattern into a regex Pattern object with caching.

        Args:
            pattern: The pattern string to compile

        Returns:
            Compiled regex Pattern object

        Raises:
            re.error: If the pattern is not a valid regex
        """
        if pattern in self._pattern_cache:
            return self._pattern_cache[pattern]

        # For wildcard, create pattern that matches everything
        if pattern == "*":
            compiled = re.compile(r".*")
        elif "|" in pattern or ".*" in pattern or "^" in pattern or "$" in pattern:
            # This looks like a regex pattern - use it directly
            compiled = re.compile(pattern)
        else:
            # Treat as exact match
            compiled = re.compile(f"^{re.escape(pattern)}$")

        self._pattern_cache[pattern] = compiled
        return compiled

    def clear_cache(self) -> None:
        """Clear the pattern compilation cache."""
        self._pattern_cache.clear()

    def get_cache_size(self) -> int:
        """Get the current size of the pattern cache."""
        return len(self._pattern_cache)
