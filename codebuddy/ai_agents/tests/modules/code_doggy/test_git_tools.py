import pytest
import unittest.mock as mock
import subprocess

from ai_agents.tools.git import git_grep_files, is_path_in_repo, get_git_diff_content


class TestGitGrepFiles:
    """测试git_grep_files函数"""

    def test_git_grep_files_normal(self):
        """测试正常情况下找到文件"""
        mock_result = mock.Mock()
        # 根据git.py的实现，格式应该是"commit:path:content"
        mock_result.stdout = "main:file1.py:match\nmain:file2.py:another match\n"

        with mock.patch("subprocess.run", return_value=mock_result):
            result = git_grep_files("/fake/repo", "main", "search_term")

        assert result == ["file1.py", "file2.py"]
        assert isinstance(result, list)

    def test_git_grep_files_not_found(self):
        """测试未找到匹配时返回空字符串"""
        # 模拟git grep未找到匹配，返回退出码1
        mock_exception = subprocess.CalledProcessError(1, "git grep")
        mock_exception.stderr = ""

        with mock.patch("subprocess.run", side_effect=mock_exception):
            result = git_grep_files("/fake/repo", "main", "search_term")

        assert result == ""

    def test_git_grep_files_error(self):
        """测试命令执行失败抛出异常"""
        # 模拟git grep执行出错，返回退出码128
        mock_exception = subprocess.CalledProcessError(128, "git grep")
        mock_exception.stderr = "fatal: not a git repository"

        with mock.patch("subprocess.run", side_effect=mock_exception):
            with pytest.raises(RuntimeError) as excinfo:
                git_grep_files("/fake/repo", "main", "search_term")

        assert "git grep 执行失败" in str(excinfo.value)

    @pytest.mark.parametrize(
        "repo_path,commit,words",
        [
            (None, "main", "term"),
            ("", "main", "term"),
            ("/fake/repo", None, "term"),
            ("/fake/repo", "", "term"),
            ("/fake/repo", "main", None),
            ("/fake/repo", "main", ""),
        ],
    )
    def test_git_grep_files_missing_params(self, repo_path, commit, words):
        """测试缺少必要参数时抛出ValueError"""
        with pytest.raises(ValueError):
            git_grep_files(repo_path, commit, words)


class TestIsPathInRepo:
    """测试is_path_in_repo函数"""

    def test_is_path_in_repo_true(self):
        """测试文件存在于仓库中"""
        mock_result = mock.Mock()
        mock_result.stdout = "file.py\n"

        with mock.patch("subprocess.run", return_value=mock_result):
            result = is_path_in_repo("/fake/repo", "file.py", "main")

        assert result is True

    def test_is_path_in_repo_false(self):
        """测试文件不存在于仓库中"""
        mock_result = mock.Mock()
        mock_result.stdout = ""

        with mock.patch("subprocess.run", return_value=mock_result):
            result = is_path_in_repo("/fake/repo", "non_existent.py", "main")

        assert result is False

    @pytest.mark.parametrize(
        "repo_path,file_path,commit",
        [
            (None, "file.py", "main"),
            ("", "file.py", "main"),
            ("/fake/repo", None, "main"),
            ("/fake/repo", "", "main"),
            ("/fake/repo", "file.py", None),
            ("/fake/repo", "file.py", ""),
        ],
    )
    def test_is_path_in_repo_missing_params(self, repo_path, file_path, commit):
        """测试缺少必要参数时抛出ValueError"""
        with pytest.raises(ValueError):
            is_path_in_repo(repo_path, file_path, commit)

    def test_is_path_in_repo_posix_path(self):
        """测试文件路径转换为POSIX格式"""
        mock_result = mock.Mock()
        mock_result.stdout = "src/file.py\n"

        with mock.patch("subprocess.run", return_value=mock_result), mock.patch(
                "pathlib.Path.as_posix", return_value="src/file.py"):
            result = is_path_in_repo("/fake/repo", "src\\file.py", "main")

        assert result is True


class TestGetGitDiffContent:
    """测试get_git_diff_content函数"""

    def test_get_git_diff_content_normal(self):
        """测试正常获取差异内容"""
        expected_diff = """diff --git a/file.py b/file.py
index abc123..def456 100644
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 def hello():
-    print("Hello")
+    print("Hello World")
+    return True
 """
        mock_result = mock.Mock()
        mock_result.stdout = expected_diff

        with mock.patch("subprocess.run", return_value=mock_result):
            result = get_git_diff_content("/fake/repo", "HEAD~1", "HEAD")

        assert result == expected_diff

    def test_get_git_diff_content_no_diff(self):
        """测试没有差异时返回空字符串"""
        mock_result = mock.Mock()
        mock_result.stdout = ""

        with mock.patch("subprocess.run", return_value=mock_result):
            result = get_git_diff_content("/fake/repo", "HEAD~1", "HEAD")

        assert result == ""

    def test_get_git_diff_content_error(self):
        """测试命令执行失败抛出异常"""
        mock_exception = subprocess.CalledProcessError(128, "git diff")
        mock_exception.stderr = "fatal: not a git repository"

        with mock.patch("subprocess.run", side_effect=mock_exception):
            with pytest.raises(RuntimeError) as excinfo:
                get_git_diff_content("/fake/repo", "HEAD~1", "HEAD")

        assert "Git diff统计命令执行失败" in str(excinfo.value)

    def test_get_git_diff_content_with_binary_files(self):
        """测试包含二进制文件的差异"""
        diff_with_binary = """diff --git a/image.png b/image.png
index abc123..def456 100644
Binary files a/image.png and b/image.png differ
"""
        mock_result = mock.Mock()
        mock_result.stdout = diff_with_binary

        with mock.patch("subprocess.run", return_value=mock_result):
            result = get_git_diff_content("/fake/repo", "HEAD~1", "HEAD")

        assert result == diff_with_binary
