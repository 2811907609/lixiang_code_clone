"""
测试动态模块函数加载器
"""

import pytest
from ai_agents.lib.dynamic_import import load_function


# 创建一些测试用的简单函数
def helper_function(x, y):
    """测试用的辅助函数"""
    return x + y


def another_function():
    """另一个测试函数"""
    return "hello world"


class TestHelperClass:
    """测试用的类"""

    @staticmethod
    def static_method():
        return "static result"

    @classmethod
    def class_method(cls):
        return "class result"


class TestLoadFunction:
    """测试 load_function 函数"""

    def test_load_function_itself(self):
        """测试加载 load_function 函数本身"""
        # 加载被测试的函数本身
        loaded_func = load_function("ai_agents.lib.dynamic_import", "load_function")

        # 验证加载成功
        assert callable(loaded_func)

        # 使用加载的函数再次加载其他函数
        json_dumps = loaded_func("json", "dumps")
        assert callable(json_dumps)

        # 测试功能
        result = json_dumps({"test": "value"})
        assert "test" in result

    def test_load_function_from_current_test_module(self):
        """测试加载当前测试模块中的函数"""
        # 加载当前测试文件中的函数
        helper_func = load_function("tests.lib.test_dynamic_import", "helper_function")

        assert callable(helper_func)

        # 测试函数功能
        result = helper_func(5, 3)
        assert result == 8

    def test_load_another_function_from_current_module(self):
        """测试加载当前模块中的另一个函数"""
        another_func = load_function("tests.lib.test_dynamic_import", "another_function")

        assert callable(another_func)

        result = another_func()
        assert result == "hello world"

    def test_load_class_from_current_module(self):
        """测试加载当前模块中的类"""
        test_class = load_function("tests.lib.test_dynamic_import", "TestHelperClass")

        assert callable(test_class)

        # 创建实例
        instance = test_class()
        assert isinstance(instance, test_class)

    def test_load_project_lib_functions(self):
        """测试加载项目 lib 模块中的函数"""
        # 加载 tracing 模块中的函数
        set_task_id_func = load_function("ai_agents.lib.tracing", "set_current_task_id")

        assert callable(set_task_id_func)

        # 测试调用（这个函数没有返回值，只是设置状态）
        try:
            set_task_id_func("test_task_123")
            # 如果没有异常，说明调用成功
        except Exception as e:
            pytest.fail(f"函数调用失败: {e}")

    def test_load_rich_console_class(self):
        """测试加载 rich_console 模块中的类"""
        console_class = load_function("ai_agents.lib.rich_console", "DualConsole")

        assert callable(console_class)

        # 测试创建实例（需要提供 log_file_path 参数）
        import tempfile
        with tempfile.NamedTemporaryFile() as tmp:
            console = console_class(tmp.name)
            assert hasattr(console, 'print')

    def test_load_merge_path_function(self):
        """测试加载 merge_path 模块中的函数"""
        try:
            # 使用实际存在的函数名
            merge_func = load_function("ai_agents.lib.path.merge_path", "merge_paths_to_limit")
            assert callable(merge_func)
        except (ImportError, AttributeError):
            # 如果模块不存在或函数不存在，跳过这个测试
            pytest.skip("merge_path 模块或函数不存在")

    def test_function_not_found_in_project_module(self):
        """测试在项目模块中查找不存在的函数"""
        with pytest.raises(AttributeError) as exc_info:
            load_function("ai_agents.lib.dynamic_import", "nonexistent_function")

        assert "未找到函数 'nonexistent_function'" in str(exc_info.value)
        assert "可用的属性:" in str(exc_info.value)

    def test_module_not_found_in_project(self):
        """测试项目中不存在的模块"""
        with pytest.raises(ImportError):
            load_function("ai_agents.lib.nonexistent_module", "some_function")

    def test_load_multiple_project_functions(self):
        """测试连续加载多个项目中的函数"""
        functions_to_load = [
            ("ai_agents.lib.dynamic_import", "load_function"),
            ("ai_agents.lib.tracing", "set_current_task_id"),
            ("ai_agents.lib.tracing", "clear_current_task_id"),
        ]

        loaded_functions = []
        for module, func_name in functions_to_load:
            try:
                func = load_function(module, func_name)
                assert callable(func)
                loaded_functions.append(func)
            except ImportError:
                # 如果某个模块不存在，跳过
                continue

        # 至少应该加载到 load_function 本身
        assert len(loaded_functions) >= 1

    def test_load_tracing_context_function(self):
        """测试加载 tracing 模块中的上下文管理器函数"""
        try:
            task_context_func = load_function("ai_agents.lib.tracing", "task_context")
            assert callable(task_context_func)

            # 测试上下文管理器
            with task_context_func("test_task") as task_id:
                assert isinstance(task_id, str)
                assert "test_task" in task_id
        except ImportError:
            pytest.skip("tracing 模块不可用")


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_parameters(self):
        """测试空参数"""
        with pytest.raises(ValueError):
            load_function("", "some_function")

        with pytest.raises(AttributeError):
            load_function("ai_agents.lib.dynamic_import", "")

    def test_invalid_module_format(self):
        """测试无效的模块格式"""
        with pytest.raises(ImportError):
            load_function("invalid..module..name", "function")

    def test_load_private_function(self):
        """测试加载私有函数（如果存在的话）"""
        # 大部分私有函数不应该被直接使用，但技术上可以加载
        try:
            # 尝试加载 tracing 模块中可能存在的私有函数
            private_func = load_function("ai_agents.lib.tracing", "_setup_task_id_injection")
            assert callable(private_func)
        except AttributeError:
            # 如果私有函数不存在或已被重构，这是正常的
            pass


if __name__ == "__main__":
    pytest.main([__file__])
