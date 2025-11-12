import pytest
import os
import tempfile
import shutil
from pathlib import Path

from ai_agents.tools.file_ops.file_creator import create_new_file


class TestFileCreator:
    """Test file creation functionality"""

    def setup_method(self):
        """Setup test environment before each test"""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

    def teardown_method(self):
        """Clean up after each test"""
        # Remove the temporary directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_create_simple_file(self):
        """Test creating a simple file with content"""
        file_path = self.test_path / "test.txt"
        content = "Hello, World!"

        result = create_new_file(str(file_path), content)

        # Verify file was created
        assert file_path.exists()
        assert file_path.read_text() == content
        assert "Created file" in result
        assert str(file_path) in result

    def test_create_empty_file(self):
        """Test creating an empty file"""
        file_path = self.test_path / "empty.txt"

        result = create_new_file(str(file_path))

        # Verify empty file was created
        assert file_path.exists()
        assert file_path.read_text() == ""
        assert "0 bytes" in result

    def test_create_file_with_directories(self):
        """Test creating a file with nested directories"""
        file_path = self.test_path / "nested" / "dir" / "file.txt"
        content = "Nested file content"

        create_new_file(str(file_path), content, create_directories=True)

        # Verify file and directories were created
        assert file_path.exists()
        assert file_path.read_text() == content
        assert file_path.parent.exists()

    def test_create_file_without_directories_fails(self):
        """Test that creating file without directories fails when create_directories=False"""
        file_path = self.test_path / "nonexistent" / "file.txt"

        with pytest.raises(OSError):
            create_new_file(str(file_path), "content", create_directories=False)

    def test_overwrite_existing_file(self):
        """Test overwriting an existing file"""
        file_path = self.test_path / "existing.txt"

        # Create initial file
        file_path.write_text("Original content")

        # Overwrite with new content
        new_content = "New content"
        result = create_new_file(str(file_path), new_content, overwrite=True)

        # Verify file was overwritten
        assert file_path.read_text() == new_content
        assert "Overwritten file" in result

    def test_fail_to_overwrite_without_permission(self):
        """Test that overwriting fails when overwrite=False"""
        file_path = self.test_path / "existing.txt"

        # Create initial file
        file_path.write_text("Original content")

        # Try to overwrite without permission
        with pytest.raises(FileExistsError):
            create_new_file(str(file_path), "New content", overwrite=False)

    def test_invalid_file_path(self):
        """Test error handling with invalid file paths"""
        # Empty path
        with pytest.raises(ValueError, match="file_path is required"):
            create_new_file("", "content")

        # Whitespace only path
        with pytest.raises(ValueError, match="cannot be just whitespace"):
            create_new_file("   ", "content")

    def test_create_file_with_encoding(self):
        """Test creating file with specific encoding"""
        file_path = self.test_path / "encoded.txt"
        content = "Hello, 世界! 🌍"

        result = create_new_file(str(file_path), content, encoding="utf-8")

        # Verify file was created with correct encoding
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == content
        assert "utf-8" in result
