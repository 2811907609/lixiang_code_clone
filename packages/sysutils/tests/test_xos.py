import os
import tempfile
from pathlib import Path

import pytest
from sysutils.xos import change_dir


def _normalize_path(path):
    """规范化路径，解决符号链接问题"""
    return os.path.realpath(os.path.abspath(path))


def test_change_dir_basic():
    """测试基本的目录切换功能"""
    original_dir = os.getcwd()

    # 创建临时目录用于测试
    with tempfile.TemporaryDirectory() as temp_dir:
        expected_dir = _normalize_path(temp_dir)

        # 使用 change_dir 上下文管理器
        with change_dir(temp_dir):
            # 验证当前目录已经改变
            assert os.getcwd() == expected_dir

        # 验证退出上下文管理器后目录已恢复
        assert os.getcwd() == original_dir


def test_change_dir_nested():
    """测试嵌套使用 change_dir"""
    original_dir = os.getcwd()

    with tempfile.TemporaryDirectory() as temp_dir1:
        with tempfile.TemporaryDirectory() as temp_dir2:
            expected_dir1 = _normalize_path(temp_dir1)
            expected_dir2 = _normalize_path(temp_dir2)

            # 第一层嵌套
            with change_dir(temp_dir1):
                assert os.getcwd() == expected_dir1

                # 第二层嵌套
                with change_dir(temp_dir2):
                    assert os.getcwd() == expected_dir2

                # 退出第二层后，应该回到第一层
                assert os.getcwd() == expected_dir1

            # 退出第一层后，应该回到原始目录
            assert os.getcwd() == original_dir


def test_change_dir_with_exception():
    """测试在上下文管理器中发生异常时目录是否正确恢复"""
    original_dir = os.getcwd()

    with tempfile.TemporaryDirectory() as temp_dir:
        expected_dir = _normalize_path(temp_dir)

        try:
            with change_dir(temp_dir):
                assert os.getcwd() == expected_dir
                # 故意抛出异常
                raise ValueError("测试异常")
        except ValueError:
            pass  # 捕获并忽略异常

        # 验证即使发生异常，目录也能正确恢复
        assert os.getcwd() == original_dir


def test_change_dir_relative_path():
    """测试使用相对路径"""
    original_dir = os.getcwd()

    # 创建一个子目录用于测试
    test_subdir = "test_subdir"
    os.makedirs(test_subdir, exist_ok=True)

    try:
        with change_dir(test_subdir):
            # 验证当前目录已经改变到子目录
            assert os.getcwd() == os.path.join(original_dir, test_subdir)

        # 验证退出后目录已恢复
        assert os.getcwd() == original_dir
    finally:
        # 清理测试目录
        if os.path.exists(test_subdir):
            os.rmdir(test_subdir)


def test_change_dir_nonexistent_directory():
    """测试切换到不存在的目录时的行为"""
    original_dir = os.getcwd()
    nonexistent_dir = "/nonexistent/directory/path"

    # 应该抛出 FileNotFoundError 或 OSError
    with pytest.raises((FileNotFoundError, OSError)):
        with change_dir(nonexistent_dir):
            pass

    # 验证即使切换失败，当前目录没有改变
    assert os.getcwd() == original_dir


def test_change_dir_absolute_path():
    """测试使用绝对路径"""
    original_dir = os.getcwd()

    with tempfile.TemporaryDirectory() as temp_dir:
        abs_temp_dir = _normalize_path(temp_dir)

        with change_dir(abs_temp_dir):
            assert os.getcwd() == abs_temp_dir

        assert os.getcwd() == original_dir


def test_change_dir_pathlib_path():
    """测试使用 pathlib.Path 对象"""
    original_dir = os.getcwd()

    with tempfile.TemporaryDirectory() as temp_dir:
        path_obj = Path(temp_dir)
        expected_dir = str(path_obj.resolve())

        with change_dir(path_obj):
            assert os.getcwd() == expected_dir

        assert os.getcwd() == original_dir
