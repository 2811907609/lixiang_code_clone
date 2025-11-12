#!/usr/bin/env python3
"""
Test file for the file reader tools.

This file contains unit tests for the new file reading tools:
- read_file_content
- read_file_lines
- get_file_info
"""

import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add the ai_agents package to the path
sys.path.insert(0, str(Path(__file__).parent))

from ai_agents.tools.file_ops import read_file_content, read_file_lines, get_file_info


class TestFileReader:
    """Test cases for file reader tools."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        self.test_content = """Line 1: Hello World
Line 2: This is a test file
Line 3: With multiple lines
Line 4: For testing purposes
Line 5: End of test content"""

        self.temp_file.write(self.test_content)
        self.temp_file.close()

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_read_file_content_basic(self):
        """Test basic file content reading."""
        content = read_file_content(self.temp_file.name)
        assert content == self.test_content

    def test_read_file_content_with_strip(self):
        """Test file content reading with whitespace stripping."""
        # Create a file with leading/trailing whitespace
        temp_file_ws = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        content_with_ws = "  \n  " + self.test_content + "  \n  "
        temp_file_ws.write(content_with_ws)
        temp_file_ws.close()

        try:
            content = read_file_content(temp_file_ws.name, strip_whitespace=True)
            assert content == self.test_content
        finally:
            os.unlink(temp_file_ws.name)

    def test_read_file_content_nonexistent(self):
        """Test reading non-existent file."""
        with pytest.raises(FileNotFoundError):
            read_file_content("nonexistent_file.txt")

    def test_read_file_content_empty_path(self):
        """Test reading with empty file path."""
        with pytest.raises(ValueError):
            read_file_content("")

    def test_read_file_lines_basic(self):
        """Test basic line reading."""
        lines = read_file_lines(self.temp_file.name, start_line=1, end_line=3)
        expected = "Line 1: Hello World\nLine 2: This is a test file\nLine 3: With multiple lines"
        assert lines.strip() == expected

    def test_read_file_lines_with_line_numbers(self):
        """Test line reading with line numbers."""
        lines = read_file_lines(self.temp_file.name, start_line=2, end_line=3, include_line_numbers=True)
        assert "   2: Line 2: This is a test file" in lines
        assert "   3: Line 3: With multiple lines" in lines

    def test_read_file_lines_single_line(self):
        """Test reading a single line."""
        lines = read_file_lines(self.temp_file.name, start_line=1, end_line=1)
        assert "Line 1: Hello World" in lines

    def test_read_file_lines_from_start(self):
        """Test reading from a start line to end of file."""
        lines = read_file_lines(self.temp_file.name, start_line=4)
        assert "Line 4: For testing purposes" in lines
        assert "Line 5: End of test content" in lines

    def test_read_file_lines_invalid_range(self):
        """Test reading with invalid line range."""
        with pytest.raises(ValueError):
            read_file_lines(self.temp_file.name, start_line=5, end_line=3)

    def test_read_file_lines_beyond_file(self):
        """Test reading beyond file length."""
        result = read_file_lines(self.temp_file.name, start_line=100)
        assert "only has" in result and "lines" in result

    def test_get_file_info_basic(self):
        """Test basic file info retrieval."""
        info = get_file_info(self.temp_file.name)
        assert self.temp_file.name in info
        assert "Size:" in info
        assert "Modified:" in info
        assert "Line count:" in info

    def test_get_file_info_with_preview(self):
        """Test file info with content preview."""
        info = get_file_info(
            self.temp_file.name,
            include_content_preview=True,
            preview_lines=3
        )
        assert "Content preview" in info
        assert "Line 1: Hello World" in info
        assert "Line 2: This is a test file" in info
        assert "Line 3: With multiple lines" in info

    def test_get_file_info_no_encoding_detection(self):
        """Test file info without encoding detection."""
        info = get_file_info(
            self.temp_file.name,
            include_encoding_detection=False
        )
        assert "Detected encoding" not in info

    def test_get_file_info_nonexistent(self):
        """Test file info for non-existent file."""
        with pytest.raises(FileNotFoundError):
            get_file_info("nonexistent_file.txt")


class TestFileReaderEdgeCases:
    """Test edge cases for file reader tools."""

    def test_empty_file(self):
        """Test reading an empty file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_file.close()

        try:
            content = read_file_content(temp_file.name)
            assert content == ""

            info = get_file_info(temp_file.name)
            assert "0 bytes" in info

        finally:
            os.unlink(temp_file.name)

    def test_large_file_size_limit(self):
        """Test file size limit enforcement."""
        # Create a file that's larger than the limit
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        large_content = "x" * (1024 * 1024 + 1)  # Just over 1MB
        temp_file.write(large_content)
        temp_file.close()

        try:
            with pytest.raises(ValueError, match="too large"):
                read_file_content(temp_file.name, max_size_mb=0.001)  # Very small limit
        finally:
            os.unlink(temp_file.name)
