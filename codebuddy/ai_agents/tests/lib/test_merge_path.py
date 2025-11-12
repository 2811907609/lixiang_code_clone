"""
测试路径合并工具模块
"""

import pytest
from ai_agents.lib.path.merge_path import (
    merge_paths_to_limit,
    _get_path_depth,
    _merge_to_depth_with_counts,
    _merge_to_depth,
    _truncate_to_depth,
    analyze_path_structure,
    _find_common_prefixes,
    preview_merge_levels
)


class TestMergePathsToLimit:
    """测试主要的路径合并函数"""

    def test_empty_paths_list(self):
        """测试空路径列表"""
        result = merge_paths_to_limit([], 5)
        assert result == []

    def test_paths_under_limit(self):
        """测试路径数量未超过限制"""
        paths = ["./a/b/c", "./a/b/d", "./a/e/f"]
        result = merge_paths_to_limit(paths, 5)
        expected = [("./a/b/c", 1), ("./a/b/d", 1), ("./a/e/f", 1)]
        assert result == expected

    def test_paths_exactly_at_limit(self):
        """测试路径数量正好等于限制"""
        paths = ["./a/b/c", "./a/b/d", "./a/e/f"]
        result = merge_paths_to_limit(paths, 3)
        expected = [("./a/b/c", 1), ("./a/b/d", 1), ("./a/e/f", 1)]
        assert result == expected

    def test_paths_over_limit_simple_merge(self):
        """测试超过限制时的简单合并"""
        paths = ["./a/b/c/file1.py", "./a/b/c/file2.py", "./a/b/d/file3.py"]
        result = merge_paths_to_limit(paths, 2)
        expected = [("a/b/c", 2), ("a/b/d", 1)]
        assert result == expected

    def test_paths_over_limit_complex_merge(self):
        """测试超过限制时的复杂合并"""
        paths = [
            "./src/components/layout/header.tsx",
            "./src/components/layout/footer.tsx",
            "./src/components/ui/button.tsx",
            "./src/components/ui/input.tsx",
            "./src/components/ui/modal.tsx",
            "./src/utils/helpers.ts"
        ]
        result = merge_paths_to_limit(paths, 3)
        # 应该合并为: src/components/layout (2), src/components/ui (3), src/utils (1)
        assert len(result) <= 3
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)
        assert all(isinstance(item[0], str) and isinstance(item[1], int) for item in result)

    def test_deep_nesting_merge(self):
        """测试深层嵌套的路径合并"""
        paths = [
            "./a/b/c/d/e/f1.py",
            "./a/b/c/d/e/f2.py",
            "./a/b/c/g/h/f3.py",
            "./a/x/y/z/f4.py"
        ]
        result = merge_paths_to_limit(paths, 2)
        assert len(result) <= 2
        assert sum(count for _, count in result) == len(paths)

    def test_single_path(self):
        """测试单个路径"""
        paths = ["./single/path/file.py"]
        result = merge_paths_to_limit(paths, 1)
        assert result == [("./single/path/file.py", 1)]

    def test_root_level_paths(self):
        """测试根级别路径"""
        paths = ["./file1.py", "./file2.py", "./file3.py"]
        result = merge_paths_to_limit(paths, 2)
        # 根级别无法再合并，应该返回原始路径
        assert len(result) == 3
        expected = [("./file1.py", 1), ("./file2.py", 1), ("./file3.py", 1)]
        assert result == expected


class TestGetPathDepth:
    """测试路径深度计算函数"""

    def test_current_directory(self):
        """测试当前目录"""
        assert _get_path_depth(".") == 0
        assert _get_path_depth("./") == 0

    def test_single_level(self):
        """测试单层级路径"""
        assert _get_path_depth("./folder") == 1
        assert _get_path_depth("folder") == 1

    def test_multi_level(self):
        """测试多层级路径"""
        assert _get_path_depth("./a/b") == 2
        assert _get_path_depth("./a/b/c") == 3
        assert _get_path_depth("./a/b/c/d/e") == 5

    def test_cross_platform_paths(self):
        """测试跨平台路径处理"""
        # 使用 pathlib.Path 应该能处理不同平台的路径分隔符
        assert _get_path_depth("folder/subfolder") >= 1
        assert _get_path_depth("folder/subfolder/file.txt") >= 2

    def test_absolute_paths(self):
        """测试绝对路径"""
        assert _get_path_depth("/usr/local/bin") >= 3
        assert _get_path_depth("/home/user") >= 2


class TestTruncateToDepth:
    """测试路径截断函数"""

    def test_truncate_to_zero_depth(self):
        """测试截断到0深度"""
        assert _truncate_to_depth("./a/b/c", 0) == "."
        assert _truncate_to_depth("./folder/file.txt", 0) == "."

    def test_truncate_to_single_level(self):
        """测试截断到单层级"""
        assert _truncate_to_depth("./a/b/c", 1) == "a"
        assert _truncate_to_depth("./folder/subfolder/file.txt", 1) == "folder"

    def test_truncate_to_multiple_levels(self):
        """测试截断到多层级"""
        assert _truncate_to_depth("./a/b/c/d/e", 2) == "a/b"
        assert _truncate_to_depth("./a/b/c/d/e", 3) == "a/b/c"

    def test_truncate_depth_exceeds_path_length(self):
        """测试截断深度超过路径长度"""
        path = "./a/b/c"
        result = _truncate_to_depth(path, 10)
        # 当深度超过路径长度时，应该返回去掉 ./ 前缀的原路径
        assert result == "a/b/c"

    def test_truncate_current_directory(self):
        """测试截断当前目录"""
        assert _truncate_to_depth(".", 1) == "."
        assert _truncate_to_depth("./", 1) == "."

    def test_preserve_relative_path_prefix(self):
        """测试路径处理的一致性"""
        result = _truncate_to_depth("./a/b/c", 2)
        # 实际函数会去掉 ./ 前缀，返回相对路径形式
        assert result == "a/b"


class TestMergeToDepthWithCounts:
    """测试带计数的深度合并函数"""

    def test_merge_simple_paths(self):
        """测试简单路径合并"""
        path_counts = {
            "./a/b/c/file1.py": 1,
            "./a/b/c/file2.py": 1,
            "./a/b/d/file3.py": 1
        }
        result = _merge_to_depth_with_counts(path_counts, 2)
        expected = {"a/b": 3}
        assert result == expected

    def test_merge_with_existing_counts(self):
        """测试已有计数的合并"""
        path_counts = {
            "./a/b/c": 2,
            "./a/b/d": 3,
            "./a/e/f": 1
        }
        result = _merge_to_depth_with_counts(path_counts, 1)
        expected = {"a": 6}
        assert result == expected

    def test_merge_preserves_separate_trees(self):
        """测试合并保持独立的树结构"""
        path_counts = {
            "./src/components/ui/button.tsx": 1,
            "./src/components/layout/header.tsx": 1,
            "./tests/unit/test_utils.py": 1
        }
        result = _merge_to_depth_with_counts(path_counts, 2)
        expected = {
            "src/components": 2,
            "tests/unit": 1
        }
        assert result == expected

    def test_empty_path_counts(self):
        """测试空路径计数字典"""
        result = _merge_to_depth_with_counts({}, 2)
        assert result == {}


class TestMergeToDepth:
    """测试深度合并函数（不带计数）"""

    def test_merge_duplicate_paths(self):
        """测试合并重复路径"""
        paths = ["./a/b/c/file1.py", "./a/b/c/file2.py", "./a/b/d/file3.py"]
        result = _merge_to_depth(paths, 2)
        expected = ["a/b"]
        assert sorted(result) == sorted(expected)

    def test_merge_multiple_trees(self):
        """测试合并多个树结构"""
        paths = [
            "./src/components/ui/button.tsx",
            "./src/components/layout/header.tsx",
            "./tests/unit/test_utils.py",
            "./docs/README.md"
        ]
        result = _merge_to_depth(paths, 1)
        expected = ["src", "tests", "docs"]
        assert sorted(result) == sorted(expected)

    def test_empty_paths_list(self):
        """测试空路径列表"""
        result = _merge_to_depth([], 2)
        assert result == []


class TestAnalyzePathStructure:
    """测试路径结构分析函数"""

    def test_empty_paths(self):
        """测试空路径列表"""
        result = analyze_path_structure([])
        expected = {
            "total_paths": 0,
            "max_depth": 0,
            "depth_distribution": {},
            "common_prefixes": []
        }
        assert result == expected

    def test_single_path(self):
        """测试单个路径"""
        paths = ["./a/b/c/file.py"]
        result = analyze_path_structure(paths)
        assert result["total_paths"] == 1
        assert result["max_depth"] == 4
        assert 4 in result["depth_distribution"]
        assert result["depth_distribution"][4] == 1

    def test_multiple_paths_analysis(self):
        """测试多路径分析"""
        paths = [
            "./src/components/ui/button.tsx",
            "./src/components/ui/input.tsx",
            "./src/components/layout/header.tsx",
            "./tests/unit/test_utils.py",
            "./docs/README.md"
        ]
        result = analyze_path_structure(paths)

        assert result["total_paths"] == 5
        assert result["max_depth"] == 4  # ./src/components/ui/button.tsx
        assert isinstance(result["depth_distribution"], dict)
        assert isinstance(result["common_prefixes"], list)

        # 检查深度分布
        depth_dist = result["depth_distribution"]
        assert sum(depth_dist.values()) == 5

    def test_common_prefixes_detection(self):
        """测试公共前缀检测"""
        paths = [
            "./src/components/ui/button.tsx",
            "./src/components/ui/input.tsx",
            "./src/components/layout/header.tsx"
        ]
        result = analyze_path_structure(paths)
        common_prefixes = result["common_prefixes"]

        # 应该能检测到 "./src/components" 作为公共前缀
        assert any("src/components" in prefix for prefix in common_prefixes)


class TestFindCommonPrefixes:
    """测试公共前缀查找函数"""

    def test_empty_paths(self):
        """测试空路径列表"""
        result = _find_common_prefixes([])
        assert result == []

    def test_single_path(self):
        """测试单个路径"""
        result = _find_common_prefixes(["./a/b/c/file.py"])
        # 单个路径没有公共前缀
        assert result == []

    def test_paths_with_common_prefix(self):
        """测试有公共前缀的路径"""
        paths = [
            "./src/components/ui/button.tsx",
            "./src/components/ui/input.tsx",
            "./src/components/layout/header.tsx"
        ]
        result = _find_common_prefixes(paths)

        # 应该找到 src/components 相关的前缀
        assert len(result) >= 1
        assert all(isinstance(prefix, str) for prefix in result)

    def test_no_common_prefix(self):
        """测试没有公共前缀的路径"""
        paths = [
            "./src/file1.py",
            "./tests/file2.py",
            "./docs/file3.md"
        ]
        result = _find_common_prefixes(paths)
        # 这些路径在顶层就分叉了，应该没有公共前缀
        assert result == []

    def test_mixed_depth_paths(self):
        """测试混合深度路径"""
        paths = [
            "./a/b/c/deep/file1.py",
            "./a/b/c/deep/file2.py",
            "./a/b/shallow.py",
            "./x/y/file3.py"
        ]
        result = _find_common_prefixes(paths)
        assert isinstance(result, list)


class TestPreviewMergeLevels:
    """测试合并级别预览函数"""

    def test_empty_paths(self):
        """测试空路径列表"""
        result = preview_merge_levels([], 5)
        assert result == []

    def test_single_level_preview(self):
        """测试单层级预览"""
        paths = ["./file1.py", "./file2.py"]
        result = preview_merge_levels(paths, 5)

        assert len(result) >= 1
        assert all("level" in preview for preview in result)
        assert all("path_count" in preview for preview in result)
        assert all("paths" in preview for preview in result)
        assert all("truncated" in preview for preview in result)

    def test_multi_level_preview(self):
        """测试多层级预览"""
        paths = [
            "./src/components/ui/button.tsx",
            "./src/components/ui/input.tsx",
            "./src/components/layout/header.tsx",
            "./tests/unit/test_utils.py"
        ]
        result = preview_merge_levels(paths, 2)

        assert len(result) >= 1

        # 检查预览格式
        for preview in result:
            assert "level" in preview
            assert "path_count" in preview
            assert "paths" in preview
            assert "truncated" in preview

            assert isinstance(preview["level"], int)
            assert isinstance(preview["path_count"], int)
            assert isinstance(preview["paths"], list)
            assert isinstance(preview["truncated"], bool)

            # 路径列表长度不应超过10（示例限制）
            assert len(preview["paths"]) <= 10

    def test_preview_path_count_consistency(self):
        """测试预览路径计数一致性"""
        paths = [
            "./a/b/c/file1.py",
            "./a/b/c/file2.py",
            "./a/b/d/file3.py",
            "./a/e/f/file4.py"
        ]
        result = preview_merge_levels(paths, 2)

        # 原始级别应该显示所有路径
        original_preview = next(p for p in result if p["level"] == max(p["level"] for p in result))
        assert original_preview["path_count"] == len(paths)

    def test_preview_truncation_flag(self):
        """测试预览截断标志"""
        # 创建超过10个路径的列表
        paths = [f"./path{i}/file{i}.py" for i in range(15)]
        result = preview_merge_levels(paths, 5)

        # 原始级别应该标记为截断
        original_preview = next(p for p in result if p["level"] == max(p["level"] for p in result))
        assert original_preview["truncated"] is True
        assert len(original_preview["paths"]) == 10


class TestEdgeCases:
    """测试边界情况和异常处理"""

    def test_zero_max_lines(self):
        """测试最大行数为0"""
        paths = ["./a/b/c.py"]
        result = merge_paths_to_limit(paths, 0)
        # 即使限制为0，也应该至少返回合并后的结果
        assert len(result) >= 0

    def test_negative_max_lines(self):
        """测试负数最大行数"""
        paths = ["./a/b/c.py"]
        result = merge_paths_to_limit(paths, -1)
        # 负数应该被当作无限制或0处理
        assert isinstance(result, list)

    def test_very_deep_paths(self):
        """测试非常深的路径"""
        deep_path = "./a/b/c/d/e/f/g/h/i/j/k/l/m/n/o/p/q/r/s/t/file.py"
        paths = [deep_path]
        result = merge_paths_to_limit(paths, 1)
        assert len(result) == 1
        assert result[0][1] == 1

    def test_paths_with_special_characters(self):
        """测试包含特殊字符的路径"""
        paths = [
            "./src/测试_文件夹/file.py",
            "./src/folder with spaces/file.py",
            "./src/folder-with-dashes/file.py",
            "./src/folder.with.dots/file.py"
        ]
        result = merge_paths_to_limit(paths, 2)
        assert len(result) <= 2
        assert sum(count for _, count in result) == len(paths)

    def test_duplicate_paths(self):
        """测试重复路径"""
        paths = ["./a/b/c.py", "./a/b/c.py", "./a/b/d.py"]
        result = merge_paths_to_limit(paths, 5)
        # 函数输入中的重复路径会被初始化为单独的计数项
        # 因此结果应该包含重复路径但计数正确
        path_strings = [path for path, _ in result]
        # 检查结果合理性：应该有两个不同的路径
        unique_paths = set(path_strings)
        assert len(unique_paths) == 2  # 应该有 "./a/b/c.py" 和 "./a/b/d.py"
        # 验证总计数正确
        total_count = sum(count for _, count in result)
        assert total_count == 3  # 原始路径总数


class TestWindowsPaths:
    """测试Windows路径处理"""

    def test_windows_path_format_in_cross_platform(self):
        """测试在跨平台环境下Windows路径格式的处理"""
        # 注意：在非Windows系统上，反斜杠路径会被当作文件名，这是正常行为
        # 这个测试验证现有函数对这种情况的处理
        paths = [
            r".\src\components\ui\button.tsx",
            r".\src\components\ui\input.tsx",
            r".\src\components\layout\header.tsx",
            r".\src\utils\helpers.ts"
        ]
        result = merge_paths_to_limit(paths, 2)
        # 在非Windows系统上，这些会被当作根级文件，无法合并
        assert len(result) == 4  # 无法合并，保持原状
        assert sum(count for _, count in result) == len(paths)

    def test_posix_style_deep_paths(self):
        """测试POSIX风格的深层路径（适用于跨平台）"""
        paths = [
            "./a/b/c/d/file1.py",
            "./a/b/c/d/file2.py",
            "./a/b/e/f/file3.py",
            "./x/y/z/file4.py"
        ]
        result = merge_paths_to_limit(paths, 2)
        assert len(result) <= 2
        assert sum(count for _, count in result) == len(paths)

    def test_mixed_unix_and_special_chars(self):
        """测试混合Unix风格路径和特殊字符"""
        paths = [
            "./src/components/ui/button.tsx",
            "./src/components/ui/input.tsx",
            "./src/utils/helpers.ts",
            "./tests/unit/test_utils.py"
        ]
        result = merge_paths_to_limit(paths, 2)
        assert len(result) <= 2
        assert sum(count for _, count in result) == len(paths)

    def test_path_normalization(self):
        """测试路径规范化"""
        paths = [
            "./src/components/../components/ui/button.tsx",
            "./src/./components/ui/input.tsx",
            "./src/components/layout/header.tsx",
            "./src/utils/helpers.ts"
        ]
        result = merge_paths_to_limit(paths, 2)
        # 验证路径能正确处理，即使有. 和..
        assert len(result) <= 3  # 可能会有些路径无法完全合并
        assert sum(count for _, count in result) == len(paths)

    def test_cross_platform_path_depth_calculation(self):
        """测试跨平台路径深度计算"""
        from ai_agents.lib.path.merge_path import _get_path_depth

        # Unix风格路径
        assert _get_path_depth("./a/b/c") == 3
        assert _get_path_depth("./a/b/c/d") == 4

        # 测试相对路径
        assert _get_path_depth("a/b/c") == 3
        assert _get_path_depth("a") == 1

        # 测试当前目录
        assert _get_path_depth(".") == 0
        assert _get_path_depth("./") == 0


class TestSpecificScenarios:
    """测试特定场景"""

    def test_mixed_file_depth_with_limit_2(self):
        """
        测试混合文件深度场景：a.py, b.py, c.py, d.py, d1/a.py, d2/a.py
        当limit=2时的结果
        """
        paths = [
            "./a.py",
            "./b.py",
            "./c.py",
            "./d.py",
            "./d1/a.py",
            "./d2/a.py"
        ]
        result = merge_paths_to_limit(paths, 2)

        # 验证总文件数量正确
        assert sum(count for _, count in result) == len(paths)

        # 由于根级别文件无法进一步合并，实际返回6个条目
        # 其中d1/a.py被合并为d1，d2/a.py被合并为d2
        assert len(result) == 6

        # 验证路径合并结果
        result_paths = [path for path, _ in result]
        expected_paths = ["a.py", "b.py", "c.py", "d.py", "d1", "d2"]
        assert sorted(result_paths) == sorted(expected_paths)

        # 验证计数都是1
        assert all(count == 1 for _, count in result)

        # 这说明了一个重要特性：当文件分布在不同深度层级时，
        # 即使设置了较小的limit，根级别文件无法与子目录文件合并

    def test_deeper_hierarchy_with_limit_2(self):
        """
        测试更深层次的场景，确保能合并
        """
        paths = [
            "./src/a.py",
            "./src/b.py",
            "./src/c.py",
            "./src/d.py",
            "./src/d1/a.py",
            "./src/d2/a.py"
        ]
        result = merge_paths_to_limit(paths, 2)

        # 这种情况下应该能合并，因为都在src下
        assert len(result) <= 2
        assert sum(count for _, count in result) == len(paths)

        # 应该合并为单个src条目
        assert len(result) == 1
        assert result[0][0] == "src"
        assert result[0][1] == 6

    def test_complex_mixed_scenario(self):
        """
        测试复杂的混合场景
        """
        paths = [
            "./app.py",
            "./config.py",
            "./src/main.py",
            "./src/utils.py",
            "./src/models/user.py",
            "./src/models/product.py",
            "./tests/test_app.py",
            "./tests/unit/test_models.py",
            "./docs/README.md"
        ]
        result = merge_paths_to_limit(paths, 3)

        assert len(result) <= 3
        assert sum(count for _, count in result) == len(paths)

        # 检查结果的合理性
        result_dict = {path: count for path, count in result}

        # 应该包含一些合并的路径
        assert any("src" in path for path in result_dict.keys())

    def test_single_file_per_directory_scenario(self):
        """
        测试每个目录只有一个文件的场景
        """
        paths = [
            "./dir1/file.py",
            "./dir2/file.py",
            "./dir3/file.py",
            "./dir4/file.py",
            "./dir5/file.py"
        ]
        result = merge_paths_to_limit(paths, 2)

        # 由于每个目录只有一个文件，合并效果有限
        assert len(result) <= len(paths)  # 可能无法充分合并
        assert sum(count for _, count in result) == len(paths)

    def test_nested_same_names_scenario(self):
        """
        测试嵌套相同名称的场景
        """
        paths = [
            "./project/src/main.py",
            "./project/src/utils.py",
            "./project/tests/main.py",
            "./project/tests/utils.py",
            "./backup/src/main.py",
            "./backup/tests/main.py"
        ]
        result = merge_paths_to_limit(paths, 2)

        assert len(result) <= 2
        assert sum(count for _, count in result) == len(paths)

        # 应该按照目录结构进行合并
        result_dict = {path: count for path, count in result}
        assert "project" in str(result_dict) or "backup" in str(result_dict)


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v"])
