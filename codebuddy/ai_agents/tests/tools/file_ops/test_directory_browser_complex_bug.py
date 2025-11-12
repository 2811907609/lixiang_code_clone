"""
测试 directory_browser.py 中更复杂的路径归属bug
"""
import tempfile
from pathlib import Path
from ai_agents.tools.file_ops.directory_browser import collect_directory_items, format_directory_tree


class TestDirectoryBrowserComplexBug:
    """测试目录浏览器中更复杂的路径归属bug"""

    def test_complex_nested_structure_display_bug(self):
        """
        测试复杂嵌套结构的显示bug：
        检查格式化输出中是否有项目被错误归类
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # 创建复杂的目录结构
            # root/
            #   ├── projectA/
            #   │   ├── src/
            #   │   │   └── main.py
            #   │   └── tests/
            #   │       └── test_main.py
            #   └── projectB/
            #       ├── src/
            #       │   └── app.py
            #       └── docs/
            #           └── readme.md

            # 创建目录结构
            dirs_to_create = [
                "projectA/src",
                "projectA/tests",
                "projectB/src",
                "projectB/docs"
            ]

            for dir_path in dirs_to_create:
                (base_path / dir_path).mkdir(parents=True)

            # 创建文件
            files_to_create = [
                ("projectA/src/main.py", "# ProjectA main"),
                ("projectA/tests/test_main.py", "# ProjectA tests"),
                ("projectB/src/app.py", "# ProjectB app"),
                ("projectB/docs/readme.md", "# ProjectB docs"),
            ]

            for file_path, content in files_to_create:
                (base_path / file_path).write_text(content)

            # 收集目录项目，深度为3
            items = collect_directory_items(
                directory=base_path,
                max_depth=3,
                exclude_patterns=[],
                include_hidden=False
            )

            print("收集到的项目:")
            for item_path, rel_path in items:
                print(f"    {item_path.name} -> {rel_path}")

            # 格式化输出
            output_lines, truncated, stats = format_directory_tree(
                items,
                max_output_lines=100,
                show_file_counts=False,
                show_file_info=True,
                count_timeout=2.0
            )

            print("\n格式化的输出:")
            for line in output_lines:
                print(line)

            # 检查是否有项目被错误显示
            # 验证：每个文件都应该显示正确的完整路径

            # 检查特定文件是否存在且路径正确
            main_py_found = False
            app_py_found = False
            test_main_py_found = False
            readme_md_found = False

            for line in output_lines:
                if "projectA/src/main.py" in line:
                    main_py_found = True
                elif "projectB/src/app.py" in line:
                    app_py_found = True
                elif "projectA/tests/test_main.py" in line:
                    test_main_py_found = True
                elif "projectB/docs/readme.md" in line:
                    readme_md_found = True

            assert main_py_found, "没有找到 projectA/src/main.py"
            assert app_py_found, "没有找到 projectB/src/app.py"
            assert test_main_py_found, "没有找到 projectA/tests/test_main.py"
            assert readme_md_found, "没有找到 projectB/docs/readme.md"

            print("所有文件路径验证通过！")

            return output_lines


    def test_depth_inconsistency_bug(self):
        """
        测试深度不一致的bug：
        同一层级的项目应该有相同的缩进
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # 创建测试结构
            (base_path / "dir1").mkdir()
            (base_path / "dir2").mkdir()
            (base_path / "dir1" / "subfile1.txt").write_text("content1")
            (base_path / "dir2" / "subfile2.txt").write_text("content2")

            # 收集并格式化
            items = collect_directory_items(
                directory=base_path,
                max_depth=2,
                exclude_patterns=[],
                include_hidden=False
            )

            output_lines, _, _ = format_directory_tree(
                items,
                max_output_lines=100,
                show_file_counts=False,
                show_file_info=True,
                count_timeout=2.0
            )

            print("平铺显示测试输出:")
            for line in output_lines:
                print(f"'{line}'")

            # 检查文件路径是否正确显示
            subfile_lines = [line for line in output_lines if "subfile" in line]

            if len(subfile_lines) >= 2:
                # 验证两个文件都显示了正确的路径
                subfile1_line = [line for line in subfile_lines if "subfile1" in line][0]
                subfile2_line = [line for line in subfile_lines if "subfile2" in line][0]

                assert "dir1/subfile1.txt" in subfile1_line, f"subfile1路径错误: {subfile1_line}"
                assert "dir2/subfile2.txt" in subfile2_line, f"subfile2路径错误: {subfile2_line}"
                print("路径验证通过")
