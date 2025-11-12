#!/usr/bin/env python3
"""
Test file for the directory browser tools.

This file contains unit tests for the directory browsing tools:
- browse_directory
- quick_browse_directory
- Helper functions
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add the ai_agents package to the path
sys.path.insert(0, str(Path(__file__).parent))

from ai_agents.tools.file_ops.directory_browser import (
    browse_directory,
    quick_browse_directory,
    should_exclude_path,
    is_important_file,
    count_items_with_timeout,
    get_file_type_prefix,
    get_file_size_category,
    collect_directory_items,
    DEFAULT_EXCLUDE_PATTERNS
)


class TestDirectoryBrowserHelpers:
    """Test cases for helper functions."""

    def test_should_exclude_path_directory_patterns(self):
        """Test directory exclusion patterns."""
        # Test directory patterns
        node_modules = Path("project/node_modules")
        assert should_exclude_path(node_modules, ["node_modules/"])

        pycache = Path("src/__pycache__")
        assert should_exclude_path(pycache, ["__pycache__/"])

        # Test non-matching
        src = Path("project/src")
        assert not should_exclude_path(src, ["node_modules/"])

    def test_should_exclude_path_file_patterns(self):
        """Test file exclusion patterns."""
        # Test wildcard patterns
        pyc_file = Path("module.pyc")
        assert should_exclude_path(pyc_file, ["*.pyc"])

        log_file = Path("app.log")
        assert should_exclude_path(log_file, ["*.log"])

        # Test exact match
        ds_store = Path(".DS_Store")
        assert should_exclude_path(ds_store, [".DS_Store"])

        # Test non-matching
        py_file = Path("module.py")
        assert not should_exclude_path(py_file, ["*.pyc"])

    def test_should_exclude_path_cross_platform(self):
        """Test cross-platform path handling."""
        # Test with different path separators
        if os.name == 'nt':  # Windows
            win_path = Path("project\\node_modules")
            assert should_exclude_path(win_path, ["node_modules/"])
        else:  # Unix-like
            unix_path = Path("project/node_modules")
            assert should_exclude_path(unix_path, ["node_modules/"])

    def test_is_important_file(self):
        """Test important file detection."""
        # Test important files
        assert is_important_file(Path("README.md"))
        assert is_important_file(Path("package.json"))
        assert is_important_file(Path("requirements.txt"))
        assert is_important_file(Path("Dockerfile"))

        # Test non-important files
        assert not is_important_file(Path("module.py"))
        assert not is_important_file(Path("data.txt"))

    def test_get_file_type_prefix(self):
        """Test file type prefix generation."""
        # Create temporary directory and file for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.txt"
            test_file.write_text("test")

            assert get_file_type_prefix(temp_path) == "[DIR]"
            assert get_file_type_prefix(test_file) == "[FILE]"

    def test_get_file_size_category(self):
        """Test file size categorization."""
        assert get_file_size_category(500) == ""  # Small files
        assert get_file_size_category(2048) == "(2K)"  # KB
        assert get_file_size_category(2 * 1024 * 1024) == "(2M)"  # MB
        assert get_file_size_category(2 * 1024 * 1024 * 1024) == "(2G)"  # GB

    def test_count_items_with_timeout(self):
        """Test item counting with timeout."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create some test files and directories
            (temp_path / "file1.txt").write_text("test")
            (temp_path / "file2.txt").write_text("test")
            (temp_path / "subdir").mkdir()

            result = count_items_with_timeout(temp_path, timeout_seconds=1.0)
            assert "2f,1d" == result  # 2 files, 1 directory


class TestDirectoryBrowserCore:
    """Test cases for core directory browsing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary directory structure for testing
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Create test structure
        # /temp_dir/
        #   ├── README.md (important file)
        #   ├── src/
        #   │   ├── main.py
        #   │   └── utils/
        #   │       └── helper.py
        #   ├── tests/
        #   │   └── test_main.py
        #   ├── node_modules/ (should be excluded)
        #   │   └── package/
        #   ├── __pycache__/ (should be excluded)
        #   │   └── cache.pyc
        #   └── data.txt

        # Important file
        (self.temp_path / "README.md").write_text("# Test Project")

        # Source directory
        src_dir = self.temp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("print('hello')")

        utils_dir = src_dir / "utils"
        utils_dir.mkdir()
        (utils_dir / "helper.py").write_text("def help(): pass")

        # Tests directory
        tests_dir = self.temp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_main.py").write_text("def test(): pass")

        # Excluded directories
        node_modules = self.temp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "package").mkdir()

        pycache = self.temp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cache.pyc").write_text("cache")

        # Regular file
        (self.temp_path / "data.txt").write_text("some data")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_collect_directory_items_basic(self):
        """Test basic directory item collection."""
        items = collect_directory_items(
            self.temp_path,
            max_depth=1,
            exclude_patterns=DEFAULT_EXCLUDE_PATTERNS,
            include_hidden=False
        )

        # Should have items at depth 0
        assert 0 in items

        # Check that excluded directories are not present
        item_names = [item[0].name for item in items[0]]
        assert "node_modules" not in item_names
        assert "__pycache__" not in item_names

        # Check that important files are included
        assert "README.md" in item_names
        assert "src" in item_names
        assert "tests" in item_names

    def test_collect_directory_items_depth(self):
        """Test directory collection with different depths."""
        # Depth 1
        items_depth1 = collect_directory_items(
            self.temp_path,
            max_depth=1,
            exclude_patterns=DEFAULT_EXCLUDE_PATTERNS
        )
        assert len(items_depth1) <= 2  # depth 0 and possibly 1

        # Depth 2
        items_depth2 = collect_directory_items(
            self.temp_path,
            max_depth=2,
            exclude_patterns=DEFAULT_EXCLUDE_PATTERNS
        )
        # Should have more items with deeper traversal
        total_items_depth2 = sum(len(items) for items in items_depth2.values())
        total_items_depth1 = sum(len(items) for items in items_depth1.values())
        assert total_items_depth2 >= total_items_depth1

    def test_quick_browse_directory_basic(self):
        """Test basic quick directory browsing."""
        result = quick_browse_directory(str(self.temp_path), max_items=20)

        # Check basic structure
        assert "Directory:" in result
        assert str(self.temp_path) in result
        assert "Summary:" in result

        # Check that important files are shown
        assert "README.md" in result
        assert "[DIR] src/" in result
        assert "[DIR] tests/" in result

        # Check that excluded items are not shown
        assert "node_modules" not in result
        assert "__pycache__" not in result

    def test_quick_browse_directory_dirs_only(self):
        """Test quick browsing with directories only."""
        result = quick_browse_directory(
            str(self.temp_path),
            show_only_dirs=True,
            max_items=10
        )

        # Should show directories but not files
        assert "[DIR] src/" in result
        assert "[DIR] tests/" in result
        assert "README.md" not in result
        assert "data.txt" not in result

    def test_browse_directory_basic(self):
        """Test basic directory browsing."""
        result = browse_directory(
            str(self.temp_path),
            max_depth=2,
            max_output_lines=100
        )

        # Check basic structure
        assert "Directory:" in result
        assert "Summary:" in result
        assert str(self.temp_path) in result

        # Check content
        assert "[DIR] src/" in result
        assert "[FILE] README.md" in result

        # Should show subdirectory contents with depth 2
        assert "main.py" in result
        assert "utils/" in result

    def test_browse_directory_with_file_counts(self):
        """Test directory browsing with file counts."""
        result = browse_directory(
            str(self.temp_path),
            max_depth=1,
            show_file_counts=True,
            count_timeout_seconds=1.0
        )

        # Should contain file count information
        assert "(" in result  # File counts are shown in parentheses

    def test_browse_directory_truncation(self):
        """Test directory browsing with output truncation."""
        result = browse_directory(
            str(self.temp_path),
            max_depth=2,
            max_output_lines=10  # Very small limit to force truncation
        )

        # Should show truncation message
        assert "Output truncated" in result or "Suggestions:" in result

    def test_browse_directory_invalid_params(self):
        """Test directory browsing with invalid parameters."""
        # Empty path
        with pytest.raises(ValueError):
            browse_directory("")

        # Invalid depth
        with pytest.raises(ValueError):
            browse_directory(str(self.temp_path), max_depth=0)

        # Invalid output lines
        with pytest.raises(ValueError):
            browse_directory(str(self.temp_path), max_output_lines=5)

        # Non-existent directory
        with pytest.raises(FileNotFoundError):
            browse_directory("/nonexistent/path")

    def test_browse_directory_custom_exclude(self):
        """Test directory browsing with custom exclude patterns."""
        result = browse_directory(
            str(self.temp_path),
            exclude_patterns=["*.txt"],  # Exclude txt files
            max_depth=1
        )

        # data.txt should be excluded
        assert "data.txt" not in result
        # But other files should be present
        assert "README.md" in result


class TestDirectoryBrowserEdgeCases:
    """Test edge cases for directory browser."""

    def test_empty_directory(self):
        """Test browsing an empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = quick_browse_directory(temp_dir)
            assert "Empty directory" in result or "0 items" in result

    def test_permission_error_handling(self):
        """Test handling of permission errors."""
        # This test might not work on all systems, so we'll skip if needed
        try:
            # Try to browse a system directory that might have restricted access
            result = browse_directory("/root", max_depth=1, max_output_lines=50)
            # If we get here, the directory was accessible
            assert "Directory:" in result
        except (PermissionError, FileNotFoundError):
            # Expected on systems where /root is not accessible
            pass

    def test_very_deep_directory(self):
        """Test browsing with very deep directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a deep directory structure
            current = temp_path
            for i in range(5):
                current = current / f"level_{i}"
                current.mkdir()
                (current / f"file_{i}.txt").write_text(f"content {i}")

            # Test with different depths
            result_shallow = browse_directory(str(temp_path), max_depth=1)
            result_deep = browse_directory(str(temp_path), max_depth=3)

            # Deeper browsing should show more content
            assert len(result_deep) >= len(result_shallow)
