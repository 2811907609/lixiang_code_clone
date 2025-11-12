import pytest
import unittest.mock as mock

from ai_agents.tools.grep.text_grep import (
    search_keyword_in_directory,
    search_keyword_with_context,
    _check_tool_available,
    _run_search_command
)


class TestTextGrep:
    """Test text grep functionality"""

    def test_check_tool_available(self):
        """Test tool availability checking"""
        # Mock shutil.which to simulate different scenarios
        with mock.patch('shutil.which') as mock_which:
            # Test when tool is available
            mock_which.return_value = '/usr/bin/ag'
            assert _check_tool_available('ag') is True

            # Test when tool is not available
            mock_which.return_value = None
            assert _check_tool_available('nonexistent_tool') is False

    def test_run_search_command_success(self):
        """Test successful search command execution"""
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "file1.py:1:match line\nfile2.py:5:another match\n"
        mock_result.stderr = ""

        with mock.patch('subprocess.run', return_value=mock_result):
            result = _run_search_command(['ag', 'test', '/path'])
            assert "file1.py:1:match line" in result
            assert "file2.py:5:another match" in result

    def test_run_search_command_no_matches(self):
        """Test search command when no matches found"""
        mock_result = mock.Mock()
        mock_result.returncode = 1  # No matches found
        mock_result.stdout = ""
        mock_result.stderr = ""

        with mock.patch('subprocess.run', return_value=mock_result):
            result = _run_search_command(['ag', 'test', '/path'])
            assert result == ""

    def test_run_search_command_with_max_lines(self):
        """Test search command with output line limit"""
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "\n".join([f"line{i}" for i in range(10)])
        mock_result.stderr = ""

        with mock.patch('subprocess.run', return_value=mock_result):
            result = _run_search_command(['ag', 'test', '/path'], max_lines=5)
            lines = result.splitlines()
            assert len(lines) == 6  # 5 lines + truncation message
            assert "truncated" in lines[-1]

    def test_search_keyword_in_directory_with_ag(self):
        """Test search using ag tool"""
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "file1.py:1:def test_function():\n"
        mock_result.stderr = ""

        with mock.patch('shutil.which', return_value='/usr/bin/ag'), \
             mock.patch('subprocess.run', return_value=mock_result):

            result = search_keyword_in_directory('/test/dir', 'test_function')
            assert "file1.py:1:def test_function():" in result

    def test_search_keyword_in_directory_with_rg(self):
        """Test search using rg tool when ag is not available"""
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "file1.py:1:def test_function():\n"
        mock_result.stderr = ""

        def mock_which(tool):
            if tool == 'ag':
                return None
            elif tool == 'rg':
                return '/usr/bin/rg'
            return None

        with mock.patch('shutil.which', side_effect=mock_which), \
             mock.patch('subprocess.run', return_value=mock_result):

            result = search_keyword_in_directory('/test/dir', 'test_function')
            assert "file1.py:1:def test_function():" in result

    def test_search_keyword_in_directory_with_grep(self):
        """Test search using grep tool when ag and rg are not available"""
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "file1.py:1:def test_function():\n"
        mock_result.stderr = ""

        def mock_which(tool):
            if tool in ['ag', 'rg']:
                return None
            elif tool == 'grep':
                return '/usr/bin/grep'
            return None

        with mock.patch('shutil.which', side_effect=mock_which), \
             mock.patch('subprocess.run', return_value=mock_result):

            result = search_keyword_in_directory('/test/dir', 'test_function')
            assert "file1.py:1:def test_function():" in result

    def test_search_keyword_no_tools_available(self):
        """Test error when no search tools are available"""
        with mock.patch('shutil.which', return_value=None):
            with pytest.raises(RuntimeError, match="No search tool available"):
                search_keyword_in_directory('/test/dir', 'test_function')

    def test_search_keyword_with_file_extensions(self):
        """Test search with file extension filters"""
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "file1.py:1:def test_function():\n"
        mock_result.stderr = ""

        with mock.patch('shutil.which', return_value='/usr/bin/ag'), \
             mock.patch('subprocess.run', return_value=mock_result) as mock_run:

            search_keyword_in_directory(
                '/test/dir',
                'test_function',
                file_extensions=['.py', '.js']
            )

            # Check that the command includes file extension filters
            called_cmd = mock_run.call_args[0][0]
            assert '-G' in called_cmd
            assert any(r'\.py$' in arg for arg in called_cmd)

    def test_search_keyword_with_context(self):
        """Test search with context lines"""
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "file1.py-1-# before\nfile1.py:2:def test_function():\nfile1.py-3-# after\n"
        mock_result.stderr = ""

        with mock.patch('shutil.which', return_value='/usr/bin/ag'), \
             mock.patch('subprocess.run', return_value=mock_result) as mock_run:

            result = search_keyword_with_context('/test/dir', 'test_function', context_lines=1)
            assert "# before" in result
            assert "def test_function():" in result
            assert "# after" in result

            # Check that the command includes context options
            called_cmd = mock_run.call_args[0][0]
            assert '-A' in called_cmd and '-B' in called_cmd

    def test_search_keyword_case_sensitive(self):
        """Test case-sensitive search"""
        mock_result = mock.Mock()
        mock_result.returncode = 0
        mock_result.stdout = "file1.py:1:TestFunction\n"
        mock_result.stderr = ""

        with mock.patch('shutil.which', return_value='/usr/bin/ag'), \
             mock.patch('subprocess.run', return_value=mock_result) as mock_run:

            search_keyword_in_directory('/test/dir', 'TestFunction', case_sensitive=True)

            # Check that case-insensitive flag is NOT included
            called_cmd = mock_run.call_args[0][0]
            assert '-i' not in called_cmd

    @pytest.mark.parametrize(
        "directory,keyword",
        [
            (None, "test"),
            ("", "test"),
            ("/test/dir", None),
            ("/test/dir", ""),
        ],
    )
    def test_search_keyword_missing_params(self, directory, keyword):
        """Test missing required parameters"""
        with pytest.raises(ValueError):
            search_keyword_in_directory(directory, keyword)

    def test_search_keyword_with_context_negative_context(self):
        """Test context search with negative context lines"""
        with pytest.raises(ValueError, match="context_lines must be non-negative"):
            search_keyword_with_context('/test/dir', 'test', context_lines=-1)
