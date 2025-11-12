"""
测试 extract_coverity_compile_info 函数的测试用例

本测试文件包含对 extract_coverity_compile_info 函数的全面测试，
包括正常用例、边界情况和错误处理。
"""

import pytest
import unittest
from unittest.mock import patch
import tempfile
import os
import sys
from pathlib import Path

# 添加项目路径到 sys.path 以便导入模块
sys.path.insert(0, str(Path(__file__).parent / '../../../ai_agents'))

from ai_agents.supervisor_agents.detected_static_repair.coverity_compile_log_extractor_test import (
    extract_coverity_compile_info,
    _analyze_compile_log,
    _is_repetitive_error,
    _normalize_warning,
    _detect_file_encoding
)


class TestExtractCoverityCompileInfo(unittest.TestCase):
    """extract_coverity_compile_info 函数的测试类"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_files_dir = "/home/chehejia/programs/lixiang/agent_create_code/apr_project/files"

    def tearDown(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_extract_coverity_compile_info_with_file_path(self):
        """测试使用文件路径的情况"""
        # 创建测试文件
        test_content = """linux
build/make/base_rules.mk:67: warning: overriding recipe for target '&'
build/make/base_rules.mk:67: warning: ignoring old recipe for target '&'
compilation successful"""

        test_file = os.path.join(self.temp_dir, "test_compile.log")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)

        # 执行测试
        info_txt, bool_compile_ok = extract_coverity_compile_info(test_file)

        # 验证结果
        self.assertIsInstance(info_txt, str)
        self.assertIsInstance(bool_compile_ok, bool)
        self.assertTrue(bool_compile_ok)
        self.assertIn("COMPILATION SUCCESS", info_txt)
        self.assertIn("WARNING SUMMARY", info_txt)

    def test_extract_coverity_compile_info_with_content_string(self):
        """测试直接传入内容字符串的情况"""
        test_content = """linux
make: *** [Makefile:123] Error 1
src/main.c:45: error: undefined reference to 'main'
compilation terminated"""

        # 执行测试
        info_txt, bool_compile_ok = extract_coverity_compile_info(test_content)

        # 验证结果
        self.assertIsInstance(info_txt, str)
        self.assertIsInstance(bool_compile_ok, bool)
        self.assertFalse(bool_compile_ok)
        self.assertIn("COMPILATION FAILED", info_txt)
        self.assertIn("UNIQUE COMPILATION ERRORS", info_txt)
        self.assertIn("MAKE ERRORS", info_txt)

    def test_extract_coverity_compile_info_empty_input(self):
        """测试空输入的错误处理"""
        with self.assertRaises(ValueError) as cm:
            extract_coverity_compile_info("")

        self.assertIn("compile_info_txtpath is required and cannot be empty", str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            extract_coverity_compile_info("   ")

        self.assertIn("compile_info_txtpath is required and cannot be empty", str(cm.exception))

    def test_extract_coverity_compile_info_invalid_max_size(self):
        """测试无效文件大小限制的错误处理"""
        test_content = "test content"

        with self.assertRaises(ValueError) as cm:
            extract_coverity_compile_info(test_content, max_size_mb=0)

        self.assertIn("max_size_mb must be positive", str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            extract_coverity_compile_info(test_content, max_size_mb=-5.0)

        self.assertIn("max_size_mb must be positive", str(cm.exception))

    def test_extract_coverity_compile_info_file_not_exists(self):
        """测试文件不存在的错误处理"""
        non_existent_file = "/path/to/non/existent/file.log"

        with self.assertRaises(FileNotFoundError) as cm:
            extract_coverity_compile_info(non_existent_file)

        self.assertIn("does not exist", str(cm.exception))

    def test_extract_coverity_compile_info_file_too_large(self):
        """测试文件过大的错误处理"""
        # 创建测试文件
        test_file = os.path.join(self.temp_dir, "large_file.log")
        with open(test_file, 'w', encoding='utf-8') as f:
            # 写入足够的内容让文件超过限制
            f.write("test content\n" * 10000)

        # 设置很小的大小限制
        with self.assertRaises(ValueError) as cm:
            extract_coverity_compile_info(test_file, max_size_mb=0.001)

        self.assertIn("is too large", str(cm.exception))

    def test_extract_coverity_compile_info_directory_instead_of_file(self):
        """测试传入目录而非文件的错误处理"""
        with self.assertRaises(ValueError) as cm:
            extract_coverity_compile_info(self.temp_dir)

        self.assertIn("is not a file", str(cm.exception))

    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_extract_coverity_compile_info_permission_error(self, mock_open):
        """测试权限错误的处理"""
        test_file = os.path.join(self.temp_dir, "test.log")
        # 先创建文件以通过存在性检查
        with open(test_file, 'w') as f:
            f.write("test")

        with self.assertRaises(PermissionError) as cm:
            extract_coverity_compile_info(test_file)

        self.assertIn("Permission denied", str(cm.exception))

    def test_extract_coverity_compile_info_with_encoding(self):
        """测试指定编码的情况"""
        test_content = "编译日志内容"
        test_file = os.path.join(self.temp_dir, "test_utf8.log")

        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)

        # 测试指定编码
        info_txt, bool_compile_ok = extract_coverity_compile_info(test_file, encoding='utf-8')

        self.assertIsInstance(info_txt, str)
        self.assertIsInstance(bool_compile_ok, bool)

    def test_extract_coverity_compile_info_auto_encoding(self):
        """测试自动检测编码的情况"""
        test_content = "test content"
        test_file = os.path.join(self.temp_dir, "test_auto.log")

        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)

        # 测试自动检测编码
        info_txt, bool_compile_ok = extract_coverity_compile_info(test_file, encoding='auto')

        self.assertIsInstance(info_txt, str)
        self.assertIsInstance(bool_compile_ok, bool)

    def test_extract_coverity_compile_info_test_files(self):
        """测试所有测试数据文件"""
        test_files = [
            "agent-7941d17d.txt",
            "bv-172.txt",
            "bv-203.txt",
            "bv-649.txt",
            "bv-650.txt",
            "bv-651.txt",
            "bv.txt"
        ]

        results = {}

        for filename in test_files:
            filepath = os.path.join(self.test_files_dir, filename)
            if os.path.exists(filepath):
                try:
                    info_txt, bool_compile_ok = extract_coverity_compile_info(filepath)
                    results[filename] = {
                        "success": True,
                        "compile_ok": bool_compile_ok,
                        "info_length": len(info_txt),
                        "info_preview": info_txt[:200] + "..." if len(info_txt) > 200 else info_txt
                    }
                    print(f"\n=== {filename} ===")
                    print(f"编译状态: {'成功' if bool_compile_ok else '失败'}")
                    print(f"信息长度: {len(info_txt)} 字符")
                    print(f"处理结果预览:\n{results[filename]['info_preview']}")

                except Exception as e:
                    results[filename] = {
                        "success": False,
                        "error": str(e)
                    }
                    print(f"\n=== {filename} (处理失败) ===")
                    print(f"错误: {e}")
            else:
                results[filename] = {
                    "success": False,
                    "error": "文件不存在"
                }
                print(f"\n=== {filename} (文件不存在) ===")

        # 验证至少有一些文件被成功处理
        successful_files = [f for f, r in results.items() if r.get("success", False)]
        self.assertGreater(len(successful_files), 0, "至少应该有一个文件被成功处理")

        return results


class TestAnalyzeCompileLog(unittest.TestCase):
    """_analyze_compile_log 辅助函数的测试类"""

    def test_analyze_compile_log_success_case(self):
        """测试编译成功的情况"""
        content = """linux
make: build successful
compilation completed successfully"""

        info_txt, bool_compile_ok = _analyze_compile_log(content)

        self.assertTrue(bool_compile_ok)
        self.assertIn("COMPILATION SUCCESS", info_txt)
        self.assertIn("STATISTICS", info_txt)

    def test_analyze_compile_log_with_errors(self):
        """测试包含编译错误的情况"""
        content = """linux
src/main.c:10: error: undefined reference to 'missing_function'
src/utils.c:25: fatal error: missing header file
make: *** [target] Error 1"""

        info_txt, bool_compile_ok = _analyze_compile_log(content)

        self.assertFalse(bool_compile_ok)
        self.assertIn("COMPILATION FAILED", info_txt)
        self.assertIn("UNIQUE COMPILATION ERRORS", info_txt)
        self.assertIn("MAKE ERRORS", info_txt)

    def test_analyze_compile_log_with_warnings(self):
        """测试包含警告的情况"""
        content = """linux
src/main.c:5: warning: unused variable 'temp'
build/make/base_rules.mk:67: warning: overriding recipe for target 'all'
build/make/base_rules.mk:67: warning: ignoring old recipe for target 'all'
compilation successful"""

        info_txt, bool_compile_ok = _analyze_compile_log(content)

        self.assertTrue(bool_compile_ok)
        self.assertIn("WARNING SUMMARY", info_txt)

    def test_analyze_compile_log_empty_content(self):
        """测试空内容的情况"""
        content = ""

        info_txt, bool_compile_ok = _analyze_compile_log(content)

        self.assertTrue(bool_compile_ok)  # 空内容被视为成功
        self.assertIn("COMPILATION SUCCESS", info_txt)


class TestHelperFunctions(unittest.TestCase):
    """辅助函数的测试类"""

    def test_is_repetitive_error(self):
        """测试重复错误检测函数"""
        existing_errors = {
            "src/main.c:10: error: undefined reference to 'func1'",
            "src/utils.c:25: error: syntax error"
        }

        # 测试相似错误（只有行号不同）
        similar_error = "src/main.c:15: error: undefined reference to 'func2'"
        self.assertTrue(_is_repetitive_error(similar_error, existing_errors))

        # 测试完全不同的错误
        different_error = "src/new.c:5: error: missing semicolon"
        self.assertFalse(_is_repetitive_error(different_error, existing_errors))

    def test_normalize_warning(self):
        """测试警告标准化函数"""
        # 测试 overriding recipe 警告
        warning1 = "build/make/base_rules.mk:67: warning: overriding recipe for target 'all'"
        self.assertEqual(_normalize_warning(warning1), "overriding recipe")

        # 测试 ignoring old recipe 警告
        warning2 = "build/make/base_rules.mk:67: warning: ignoring old recipe for target 'all'"
        self.assertEqual(_normalize_warning(warning2), "ignoring old recipe")

        # 测试普通警告
        warning3 = "src/main.c:10: warning: unused variable 'temp'"
        self.assertEqual(_normalize_warning(warning3), "unused variable 'temp'")

    @patch('chardet.detect')
    def test_detect_file_encoding_with_chardet(self, mock_detect):
        """测试使用 chardet 检测编码"""
        # 创建测试文件
        test_file = os.path.join(tempfile.gettempdir(), "test_encoding.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("test content")

        # 配置 mock
        mock_detect.return_value = {'encoding': 'utf-8', 'confidence': 0.99}

        # 测试检测
        result = _detect_file_encoding(Path(test_file))

        self.assertEqual(result, 'utf-8')

        # 清理
        os.remove(test_file)

    def test_detect_file_encoding_without_chardet(self):
        """测试不使用 chardet 的编码检测"""
        # 创建测试文件
        test_file = os.path.join(tempfile.gettempdir(), "test_encoding2.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("test content")

        with patch('builtins.__import__', side_effect=ImportError):
            result = _detect_file_encoding(Path(test_file))
            self.assertEqual(result, 'utf-8')  # 应该回退到 utf-8

        # 清理
        os.remove(test_file)


class TestExtractCoverityCompileInfoIntegration:
    """集成测试类（使用 pytest 语法）"""

    @pytest.mark.parametrize("test_content,expected_success", [
        ("linux\ncompilation successful", True),
        ("linux\nsrc/main.c:10: error: undefined reference", False),
        ("linux\nmake: *** [target] Error 1", False),
        ("", True),  # 空内容视为成功
    ])
    def test_various_content_types(self, test_content, expected_success):
        """测试各种不同的内容类型"""
        info_txt, bool_compile_ok = extract_coverity_compile_info(test_content)

        assert isinstance(info_txt, str)
        assert isinstance(bool_compile_ok, bool)
        assert bool_compile_ok == expected_success

    @pytest.mark.parametrize("encoding", ["utf-8", "latin-1", "auto"])
    def test_various_encodings(self, encoding):
        """测试各种编码设置"""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as f:
            f.write("test compilation log")
            temp_file = f.name

        try:
            info_txt, bool_compile_ok = extract_coverity_compile_info(temp_file, encoding=encoding)
            assert isinstance(info_txt, str)
            assert isinstance(bool_compile_ok, bool)
        finally:
            os.unlink(temp_file)

    @pytest.mark.parametrize("max_size", [0.1, 1.0, 10.0, 100.0])
    def test_various_max_sizes(self, max_size):
        """测试各种最大文件大小设置"""
        test_content = "small test content"

        # 创建小文件进行测试
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as f:
            f.write(test_content)
            temp_file = f.name

        try:
            info_txt, bool_compile_ok = extract_coverity_compile_info(temp_file, max_size_mb=max_size)
            assert isinstance(info_txt, str)
            assert isinstance(bool_compile_ok, bool)
        finally:
            os.unlink(temp_file)


def run_all_test_files():
    """运行所有测试数据文件的处理示例"""
    print("运行所有测试数据文件的处理:")
    print("=" * 80)

    test_files_dir = "/home/chehejia/programs/lixiang/agent_create_code/apr_project/files"
    test_files = [
        "agent-7941d17d.txt",
        # "bv-172.txt",
        # "bv-203.txt",
        # "bv-649.txt",
        # "bv-650.txt",
        # "bv-651.txt",
        # "bv.txt"
    ]

    successful_count = 0
    failed_count = 0

    for filename in test_files:
        filepath = os.path.join(test_files_dir, filename)
        print(f"\n处理文件: {filename}")
        print("-" * 60)

        if not os.path.exists(filepath):
            print(f"❌ 文件不存在: {filepath}")
            failed_count += 1
            continue

        try:
            info_txt, bool_compile_ok = extract_coverity_compile_info(filepath)

            print("✅ 处理成功")
            print(f"   编译状态: {'成功' if bool_compile_ok else '失败'}")
            print(f"   输出信息长度: {len(info_txt)} 字符")

            # 显示处理结果的前几行
            lines = info_txt.split('\n')[:10]
            print("   处理结果预览:")
            for line in lines:
                print(f"     {line}")

            if len(info_txt.split('\n')) > 10:
                print(f"     ... (还有 {len(info_txt.split('\n')) - 10} 行)")

            successful_count += 1

        except Exception as e:
            print(f"❌ 处理失败: {e}")
            failed_count += 1
        break
    print("\n" + "=" * 80)
    print(f"处理完成! 成功: {successful_count}, 失败: {failed_count}")
    return successful_count, failed_count


def run_example_test():
    """运行示例测试用例"""
    print("运行 extract_coverity_compile_info 示例测试:")
    print("=" * 80)

    # 示例 1: 成功的编译日志
    print("\n1. 测试成功的编译日志:")
    print("-" * 40)
    success_content = """linux
build/make/base_rules.mk:67: warning: overriding recipe for target '&'
build/make/base_rules.mk:67: warning: ignoring old recipe for target '&'
compilation completed successfully"""

    try:
        info, success = extract_coverity_compile_info(success_content)
        print(f"✅ 编译状态: {'成功' if success else '失败'}")
        print(f"   输出信息:\n{info}")
    except Exception as e:
        print(f"❌ 处理失败: {e}")

    # 示例 2: 失败的编译日志
    print("\n2. 测试失败的编译日志:")
    print("-" * 40)
    failure_content = """linux
src/main.c:45: error: undefined reference to 'missing_function'
src/utils.c:10: fatal error: header file not found
make: *** [Makefile:123] Error 1
compilation terminated"""

    try:
        info, success = extract_coverity_compile_info(failure_content)
        print(f"✅ 编译状态: {'成功' if success else '失败'}")
        print(f"   输出信息:\n{info}")
    except Exception as e:
        print(f"❌ 处理失败: {e}")

    # 示例 3: 文件路径测试
    print("\n3. 测试文件路径处理:")
    print("-" * 40)
    temp_file = None
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("linux\nmake: Nothing to be done for 'all'.")
            temp_file = f.name

        info, success = extract_coverity_compile_info(temp_file)
        print("✅ 文件处理成功")
        print(f"   编译状态: {'成功' if success else '失败'}")
        print(f"   输出信息:\n{info}")

    except Exception as e:
        print(f"❌ 文件处理失败: {e}")
    finally:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)

    # 示例 4: 错误处理测试
    print("\n4. 测试错误处理:")
    print("-" * 40)
    try:
        extract_coverity_compile_info("")
        print("❌ 空字符串应该抛出异常")
    except ValueError as e:
        print(f"✅ 正确处理空字符串错误: {e}")

    try:
        extract_coverity_compile_info("test", max_size_mb=-1)
        print("❌ 负数大小限制应该抛出异常")
    except ValueError as e:
        print(f"✅ 正确处理负数大小限制错误: {e}")

    print("\n" + "=" * 80)
    print("示例测试完成!")


if __name__ == "__main__":
    # # 首先运行示例测试
    # run_example_test()

    print("\n\n")

    # 运行所有测试数据文件
    run_all_test_files()

    print("\n\n")

    # 运行单元测试
    print("运行完整单元测试套件:")
    print("=" * 80)
    unittest.main(argv=[''], exit=False, verbosity=2)
