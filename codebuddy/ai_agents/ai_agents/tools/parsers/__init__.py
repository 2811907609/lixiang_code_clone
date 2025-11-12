"""
Code parsers package for multi-language support.

This package contains various code parsing tools and utilities:
- Tree-sitter based parsers for high accuracy
- Regex-based parsers for fallback support
- Unified parser interface for automatic selection
- Language-specific parsing utilities
"""

# Import parsers with graceful fallback (for internal use only)
try:
    from .treesitter_parser import parse_code_with_treesitter
except ImportError:
    parse_code_with_treesitter = None

try:
    from .regex_parser import parse_code_with_regex
except ImportError:
    parse_code_with_regex = None

# Always import unified parser (it handles missing dependencies)
from .unified_parser import (
    parse_code_elements,
    compare_parsers,
    analyze_file_structure,
)

__all__ = [
    # Unified interface (recommended)
    'parse_code_elements',
    'compare_parsers',

    # High-level analysis tools
    'analyze_file_structure',

    # Note: parse_code_with_treesitter and parse_code_with_regex are internal
    # Use parse_code_elements instead for automatic parser selection
]
