import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from data_scrap.tools.gitcommits.perceval import run_perceval_git


class TestPerceval:

    def test_run_perceval_git_basic(self):
        """Test basic perceval git command execution"""
        mock_result = MagicMock()
        mock_result.stdout = '''[2025-06-28 11:59:39,280] - Sir Perceval is on his quest.
[2025-06-28 11:59:39,282] - gitpath /Users/test/.perceval/repositories/test-git
{"backend_name":"Git","data":{"commit":"abc123"}}
{"backend_name":"Git","data":{"commit":"def456"}}
[2025-06-28 11:59:41,043] - Fetch process completed: 2 commits fetched
'''
        mock_result.returncode = 0

        with patch('subprocess.run', return_value=mock_result) as mock_run:
            result = run_perceval_git(
                origin="git@gitlab.chehejia.com:ep/ai/claude-code-router.git",
                start_datetime="2025-06-27",
                finish_datetime="2025-06-27 18:00:00+08:00"
            )

            mock_run.assert_called_once_with([
                "perceval", "git", "--no-ssl-verify",
                "git@gitlab.chehejia.com:ep/ai/claude-code-router.git",
                "--from-date", "2025-06-27",
                "--to-date", "2025-06-27 18:00:00+08:00",
                "--max-size-bytes", "1024000",
                "--json-line"
            ], capture_output=True, text=True, check=True)

            assert len(result) == 2
            assert result[0]["backend_name"] == "Git"
            assert result[0]["data"]["commit"] == "abc123"
            assert result[1]["data"]["commit"] == "def456"

    def test_run_perceval_git_with_custom_params(self):
        """Test perceval git with custom parameters"""
        mock_result = MagicMock()
        mock_result.stdout = '{"data": {"commit": "abc123"}}\n'
        mock_result.returncode = 0

        with patch('subprocess.run', return_value=mock_result) as mock_run:
            _ = run_perceval_git(
                origin="git@gitlab.chehejia.com:ep/ai/claude-code-router.git",
                start_datetime="2025-06-27",
                finish_datetime="2025-06-27 18:00:00+08:00",
                max_size_bytes=2048000,
                no_ssl_verify=False
            )

            mock_run.assert_called_once_with([
                "perceval", "git",
                "git@gitlab.chehejia.com:ep/ai/claude-code-router.git",
                "--from-date", "2025-06-27",
                "--to-date", "2025-06-27 18:00:00+08:00",
                "--max-size-bytes", "2048000",
                "--json-line"
            ], capture_output=True, text=True, check=True)

    def test_run_perceval_git_command_failure(self):
        """Test handling of perceval command failure"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1,
                ["perceval", "git"],
                stderr="Repository not found"
            )

            with pytest.raises(subprocess.CalledProcessError):
                run_perceval_git(
                    origin="git@gitlab.chehejia.com:ep/ai/claude-code-router.git",
                    start_datetime="2025-06-27",
                    finish_datetime="2025-06-27 18:00:00+08:00"
                )

    def test_run_perceval_git_json_parse_error(self):
        """Test handling of invalid JSON output"""
        mock_result = MagicMock()
        mock_result.stdout = 'invalid json\n'
        mock_result.returncode = 0

        with patch('subprocess.run', return_value=mock_result):
            with pytest.raises(json.JSONDecodeError):
                run_perceval_git(
                    origin="git@gitlab.chehejia.com:ep/ai/claude-code-router.git",
                    start_datetime="2025-06-27",
                    finish_datetime="2025-06-27 18:00:00+08:00"
                )

    def test_run_perceval_git_empty_output(self):
        """Test handling of empty output"""
        mock_result = MagicMock()
        mock_result.stdout = '\n'
        mock_result.returncode = 0

        with patch('subprocess.run', return_value=mock_result):
            result = run_perceval_git(
                origin="git@gitlab.chehejia.com:ep/ai/claude-code-router.git",
                start_datetime="2025-06-27",
                finish_datetime="2025-06-27 18:00:00+08:00"
            )

            assert result == []
