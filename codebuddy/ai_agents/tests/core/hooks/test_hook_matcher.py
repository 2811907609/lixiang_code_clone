"""Tests for HookMatcher pattern matching functionality."""

import re
from ai_agents.core.hooks.hook_matcher import HookMatcher


class TestHookMatcher:
    """Test cases for HookMatcher class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = HookMatcher()

    def test_exact_string_matching(self):
        """Test exact string matching for simple tool names."""
        # Test exact matches
        assert self.matcher.matches("FileWriter", "FileWriter") is True
        assert self.matcher.matches("CodeEditor", "CodeEditor") is True
        assert self.matcher.matches("TestTool", "TestTool") is True

        # Test non-matches
        assert self.matcher.matches("FileWriter", "CodeEditor") is False
        assert self.matcher.matches("FileWriter", "FileReader") is False
        assert self.matcher.matches("TestTool", "TestTools") is False

    def test_wildcard_matching(self):
        """Test wildcard matching for '*' pattern."""
        # Wildcard should match everything
        assert self.matcher.matches("*", "FileWriter") is True
        assert self.matcher.matches("*", "CodeEditor") is True
        assert self.matcher.matches("*", "AnyTool") is True
        assert self.matcher.matches("*", "") is True
        assert self.matcher.matches("*", "Tool123") is True

    def test_regex_pattern_matching(self):
        """Test regex pattern support for complex patterns."""
        # Test OR patterns
        assert self.matcher.matches("Edit|Write", "Edit") is True
        assert self.matcher.matches("Edit|Write", "Write") is True
        assert self.matcher.matches("Edit|Write", "Read") is False

        # Test prefix patterns
        assert self.matcher.matches("File.*", "FileWriter") is True
        assert self.matcher.matches("File.*", "FileReader") is True
        assert self.matcher.matches("File.*", "FileManager") is True
        assert self.matcher.matches("File.*", "CodeEditor") is False

        # Test prefix and suffix patterns (fullmatch behavior)
        assert self.matcher.matches("File.*", "FileWriter") is True
        assert self.matcher.matches("File.*", "MyFileWriter") is False
        assert self.matcher.matches(".*Writer", "FileWriter") is True
        assert self.matcher.matches(".*Writer", "WriterTool") is False

        # Test case-sensitive matching
        assert self.matcher.matches("file.*", "FileWriter") is False
        assert self.matcher.matches("File.*", "filewriter") is False

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Empty patterns and tool names
        assert self.matcher.matches("", "Tool") is False
        assert self.matcher.matches("Tool", "") is False
        assert self.matcher.matches("", "") is False

        # None values
        assert self.matcher.matches(None, "Tool") is False
        assert self.matcher.matches("Tool", None) is False
        assert self.matcher.matches(None, None) is False

    def test_simple_tool_names_with_underscores_and_dots(self):
        """Test matching tool names with common characters like underscores and dots."""
        # Tool names with underscores and dots should be handled correctly
        assert self.matcher.matches("Tool_Name", "Tool_Name") is True
        assert self.matcher.matches("Tool.Name", "Tool.Name") is True
        assert self.matcher.matches("ToolName", "ToolName") is True

        # Different names should not match
        assert self.matcher.matches("Tool_Name", "Tool.Name") is False
        assert self.matcher.matches("ToolName", "Tool_Name") is False

    def test_invalid_regex_patterns(self):
        """Test handling of invalid regex patterns."""
        # Invalid regex patterns should fall back to exact matching
        invalid_patterns = [
            "Tool[",  # Unclosed bracket
            "Tool(",  # Unclosed parenthesis
        ]

        for pattern in invalid_patterns:
            # Should not raise exception, should fall back to exact matching
            assert self.matcher.matches(pattern, pattern) is True
            assert self.matcher.matches(pattern, "DifferentTool") is False

    def test_compile_pattern_caching(self):
        """Test pattern compilation and caching."""
        pattern = "File.*"

        # First compilation
        compiled1 = self.matcher.compile_pattern(pattern)
        assert isinstance(compiled1, re.Pattern)

        # Second compilation should return cached version
        compiled2 = self.matcher.compile_pattern(pattern)
        assert compiled1 is compiled2  # Same object reference

        # Cache should contain the pattern
        assert self.matcher.get_cache_size() >= 1

    def test_compile_pattern_types(self):
        """Test different pattern types compilation."""
        # Wildcard pattern
        wildcard = self.matcher.compile_pattern("*")
        assert wildcard.fullmatch("anything") is not None

        # Regex pattern with OR
        or_pattern = self.matcher.compile_pattern("Edit|Write")
        assert or_pattern.fullmatch("Edit") is not None
        assert or_pattern.fullmatch("Write") is not None
        assert or_pattern.fullmatch("Read") is None

        # Exact match pattern (escaped)
        exact_pattern = self.matcher.compile_pattern("Tool.Name")
        assert exact_pattern.fullmatch("Tool.Name") is not None
        assert exact_pattern.fullmatch("ToolXName") is None

    def test_cache_management(self):
        """Test cache management functionality."""
        # Add some patterns to cache
        self.matcher.compile_pattern("Pattern1")
        self.matcher.compile_pattern("Pattern2")
        self.matcher.compile_pattern("Pattern3")

        initial_size = self.matcher.get_cache_size()
        assert initial_size >= 3

        # Clear cache
        self.matcher.clear_cache()
        assert self.matcher.get_cache_size() == 0

        # Patterns should be recompiled after cache clear
        pattern = self.matcher.compile_pattern("Pattern1")
        assert isinstance(pattern, re.Pattern)
        assert self.matcher.get_cache_size() == 1

    def test_complex_matching_scenarios(self):
        """Test complex real-world matching scenarios."""
        test_cases = [
            # Pattern, Tool Name, Expected Result
            ("FileWriter|FileReader", "FileWriter", True),
            ("FileWriter|FileReader", "FileReader", True),
            ("FileWriter|FileReader", "FileManager", False),

            ("File.*", "FileWriter", True),
            ("File.*", "FileReader", True),
            ("File.*", "FileManager", True),
            ("File.*", "CodeEditor", False),

            (".*Editor", "CodeEditor", True),
            (".*Editor", "TextEditor", True),
            (".*Editor", "FileWriter", False),

            ("File.*", "FileWriter", True),
            ("File.*", "MyFileWriter", False),

            (".*Writer", "FileWriter", True),
            (".*Writer", "WriterTool", False),

            ("(File|Code).*", "FileWriter", True),
            ("(File|Code).*", "CodeEditor", True),
            ("(File|Code).*", "TextEditor", False),
        ]

        for pattern, tool_name, expected in test_cases:
            result = self.matcher.matches(pattern, tool_name)
            assert result == expected, f"Pattern '{pattern}' with tool '{tool_name}' should return {expected}, got {result}"

    def test_performance_with_repeated_matches(self):
        """Test performance with repeated pattern matching (caching benefit)."""
        pattern = "File.*"
        tool_names = ["FileWriter", "FileReader", "FileManager", "CodeEditor"]

        # First round - patterns get compiled and cached
        results1 = [self.matcher.matches(pattern, tool) for tool in tool_names]

        # Second round - should use cached patterns
        results2 = [self.matcher.matches(pattern, tool) for tool in tool_names]

        # Results should be identical
        assert results1 == results2
        assert results1 == [True, True, True, False]

        # Cache should contain the pattern
        assert self.matcher.get_cache_size() >= 1


class TestHookMatcherIntegration:
    """Integration tests for HookMatcher with realistic scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = HookMatcher()

    def test_realistic_hook_configurations(self):
        """Test with realistic hook configuration patterns."""
        # Common patterns that might be used in real configurations
        patterns_and_tools = [
            # Development tools
            ("*", ["FileWriter", "CodeEditor", "TestRunner"], [True, True, True]),
            ("File.*", ["FileWriter", "FileReader", "CodeEditor"], [True, True, False]),
            (".*Editor", ["CodeEditor", "TextEditor", "FileWriter"], [True, True, False]),

            # Specific tool groups
            ("Edit|Write|Create", ["Edit", "Write", "Create", "Read"], [True, True, True, False]),
            ("Test.*|.*Test", ["TestRunner", "UnitTest", "FileWriter"], [True, True, False]),

            # Version control tools
            ("Git.*", ["GitCommit", "GitPush", "FileCommit"], [True, True, False]),
            (".*Commit|.*Push", ["GitCommit", "GitPush", "GitPull"], [True, True, False]),
        ]

        for pattern, tools, expected_results in patterns_and_tools:
            actual_results = [self.matcher.matches(pattern, tool) for tool in tools]
            assert actual_results == expected_results, f"Pattern '{pattern}' failed for tools {tools}"

    def test_case_sensitivity(self):
        """Test case sensitivity in pattern matching."""
        # Patterns are case-sensitive by default
        assert self.matcher.matches("file.*", "FileWriter") is False
        assert self.matcher.matches("File.*", "filewriter") is False
        assert self.matcher.matches("FILE.*", "FileWriter") is False

        # Exact matches are case-sensitive
        assert self.matcher.matches("FileWriter", "filewriter") is False
        assert self.matcher.matches("filewriter", "FileWriter") is False

    def test_unicode_and_special_characters(self):
        """Test matching with unicode and special characters."""
        # Unicode tool names
        assert self.matcher.matches("Tool_测试", "Tool_测试") is True
        assert self.matcher.matches("Tool.*", "Tool_测试") is True

        # Special characters in patterns and tool names
        assert self.matcher.matches("Tool-Name", "Tool-Name") is True
        assert self.matcher.matches("Tool_Name", "Tool_Name") is True
        assert self.matcher.matches("Tool@Name", "Tool@Name") is True
