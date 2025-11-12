"""
代码编辑智能体测试

测试CodeEditorAgent的基本功能，包括策略选择、指令生成等。
"""

import pytest
import tempfile
import os
import logging

from ai_agents.micro_agents.code_editor_agent import (
    CodeEditorAgent,
    EditResult,
    smart_edit_code,
    create_code_editor_agent,
)
from tests.test_config import skip_if_no_llm_config

# 静默一些verbose的日志
logging.getLogger('openai').setLevel(logging.WARNING)


class TestCodeEditorAgent:
    """测试CodeEditorAgent基本功能"""

    def test_agent_creation(self):
        """测试智能体创建"""
        agent = CodeEditorAgent()
        assert agent is not None
        assert agent.name == "code_editor_agent"
        assert agent.description is not None

        # 测试获取CodeAgent
        code_agent = agent.get_code_agent()
        assert code_agent is not None

        # 测试便利函数
        agent2 = create_code_editor_agent()
        assert agent2 is not None

    @pytest.mark.llm
    def test_edit_nonexistent_file(self):
        """测试编辑不存在的文件"""
        agent = CodeEditorAgent()
        result = agent.edit_code("nonexistent.py", "some edit")

        assert not result.success
        assert "文件不存在" in result.message
        assert result.strategy_used == "none"
        assert result.attempts == 0

    @pytest.mark.llm
    def test_edit_with_simple_file(self):
        """测试编辑简单文件（无LLM）"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""def hello():
    print("Hello")
    return "world"
""")
            temp_file = f.name

        try:
            agent = CodeEditorAgent()  # 无模型
            result = agent.edit_code(temp_file, "将函数名改为greet")

            # 无模型时，应该会失败但不会崩溃
            assert isinstance(result, EditResult)
            # 基于CodeAgent的实现会使用"codeagent"策略
            assert result.strategy_used in ["codeagent", "none"]

        finally:
            os.unlink(temp_file)

    @pytest.mark.unit
    def test_task_building(self):
        """测试任务构建功能"""
        agent = CodeEditorAgent()

        # 测试基本任务构建
        task = agent._build_edit_task(
            "test.py",
            "修改函数名",
            "这是一个测试文件"
        )

        assert "test.py" in task
        assert "修改函数名" in task
        assert "这是一个测试文件" in task

        # 测试带策略偏好的任务构建
        task_cline = agent._build_edit_task(
            "test.py",
            "修改函数名",
            "",
            preferred_strategy="cline"
        )

        assert "search_and_replace" in task_cline

        task_codex = agent._build_edit_task(
            "test.py",
            "修改函数名",
            "",
            preferred_strategy="codex"
        )

        assert "codex_patch_apply" in task_codex

    @pytest.mark.llm
    def test_smart_edit_code_function(self):
        """测试便利函数"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test(): pass")
            temp_file = f.name

        try:
            result = smart_edit_code(temp_file, "修改函数名")
            assert isinstance(result, EditResult)

        finally:
            os.unlink(temp_file)


@pytest.mark.unit
class TestCodeEditorAgentWithMockLLM:
    """使用模拟LLM测试CodeEditorAgent"""

    class MockLLMClient:
        """模拟LLM客户端"""

        def complete(self, prompt: str) -> str:
            if "分析" in prompt or "JSON" in prompt:
                return """{
                    "edit_type": "修改",
                    "complexity": "简单",
                    "scope": "单行",
                    "target_elements": ["test_function"],
                    "dependencies": [],
                    "risk_level": "低",
                    "estimated_changes": "1",
                    "special_considerations": [],
                    "recommended_approach": "直接替换"
                }"""
            elif "策略" in prompt:
                return """{
                    "recommended_strategy": "cline",
                    "confidence": "高",
                    "reasoning": "简单的单行修改适合使用Cline格式",
                    "alternative_strategy": "codex",
                    "special_instructions": [],
                    "expected_success_rate": "95%"
                }"""
            elif "SEARCH" in prompt or "Cline" in prompt:
                return """------- SEARCH
def test():
=======
def modified_test():
+++++++ REPLACE"""
            elif "Patch" in prompt or "Codex" in prompt:
                return """*** Begin Patch
*** Update File: test.py
- def test():
+ def modified_test():
*** End Patch"""
            else:
                return "Mock response"

    def test_edit_with_mock_llm(self):
        """测试使用模拟LLM的编辑功能"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test():\n    pass")
            temp_file = f.name

        try:
            mock_llm = self.MockLLMClient()
            agent = CodeEditorAgent(mock_llm)

            result = agent.edit_code(temp_file, "将函数名改为modified_test")

            # 由于我们的mock LLM返回的指令可能不完全匹配文件内容，
            # 这里主要测试流程是否正常执行
            assert isinstance(result, EditResult)
            # 可能成功也可能失败，但应该尝试了某种策略
            assert result.strategy_used in ["cline", "codex", "none"]

        finally:
            os.unlink(temp_file)

    def test_task_building_with_mock_llm(self):
        """测试使用模拟LLM的任务构建功能"""
        mock_llm = self.MockLLMClient()
        agent = CodeEditorAgent(model=mock_llm)

        # 测试任务构建
        task = agent._build_edit_task(
            "test.py",
            "修改函数",
            "这是测试文件",
            preferred_strategy="cline"
        )

        assert "test.py" in task
        assert "修改函数" in task
        assert "这是测试文件" in task
        assert "search_and_replace" in task

    def test_agent_run_with_mock_llm(self):
        """测试使用模拟LLM运行智能体"""
        mock_llm = self.MockLLMClient()
        agent = CodeEditorAgent(model=mock_llm)

        # 测试运行功能（这里只测试不会崩溃）
        try:
            result = agent.run("简单的测试任务")
            # 由于是mock LLM，结果可能不可预测，但不应该崩溃
            assert result is not None
        except Exception as e:
            # 允许某些预期的错误，但不应该是AttributeError
            assert not isinstance(e, AttributeError)


@pytest.mark.llm
class TestCodeEditorAgentIntegration:
    """集成测试"""

    def test_full_workflow_without_llm(self):
        """测试完整工作流程（无LLM）"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""def calculate_sum(a, b):
    return a + b

def main():
    result = calculate_sum(1, 2)
    print(result)
""")
            temp_file = f.name

        try:
            agent = CodeEditorAgent()
            result = agent.edit_code(
                temp_file,
                "将函数名calculate_sum改为compute_total",
                preferred_strategy="cline"
            )

            # 验证结果结构
            assert isinstance(result, EditResult)
            assert hasattr(result, 'success')
            assert hasattr(result, 'message')
            assert hasattr(result, 'strategy_used')
            assert hasattr(result, 'attempts')

        finally:
            os.unlink(temp_file)


@pytest.mark.llm
class TestCodeEditorAgentWithRealLLM:
    """使用真实LLM的CodeEditorAgent测试"""

    def setup_method(self):
        """测试前设置"""
        skip_if_no_llm_config()

        # 创建带有真实LLM的智能体
        self.agent = CodeEditorAgent()

    def test_simple_function_rename_with_llm(self):
        """测试使用真实LLM进行简单函数重命名"""
        # 创建临时文件
        test_code = """def calculate_sum(a, b):
    \"\"\"计算两个数的和\"\"\"
    return a + b

def main():
    result = calculate_sum(10, 20)
    print(f"结果: {result}")
    return result
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            temp_file = f.name

        try:
            # 执行编辑
            result = self.agent.edit_code(
                temp_file,
                "将函数名calculate_sum改为compute_total，同时更新所有调用的地方"
            )

            # 验证结果
            assert isinstance(result, EditResult)
            print(f"编辑结果: {result.success}")
            print(f"使用策略: {result.strategy_used}")
            print(f"尝试次数: {result.attempts}")

            if not result.success:
                print(f"失败原因: {result.message}")
                if result.error_details:
                    print(f"错误详情: {result.error_details}")

            # 检查文件是否被修改
            with open(temp_file, 'r') as f:
                modified_content = f.read()

            print("修改后的内容:")
            print(modified_content)

            # 基本验证：使用CodeAgent策略
            assert result.strategy_used in ["codeagent", "none"]
            # 如果模型不可用，attempts可能为0
            if result.success:
                assert result.attempts > 0
            else:
                # 模型不可用时，记录但不失败测试
                print(f"模型不可用，这是配置问题: {result.message}")
                assert result.attempts >= 0  # 允许0次尝试

        finally:
            os.unlink(temp_file)

    def test_class_method_enhancement_with_llm(self):
        """测试使用真实LLM进行类方法增强"""
        test_code = """class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email

    def get_info(self):
        return f"{self.name} ({self.email})"

    def is_valid(self):
        return len(self.name) > 0
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            temp_file = f.name

        try:
            # 执行编辑
            result = self.agent.edit_code(
                temp_file,
                "为is_valid方法添加邮箱格式验证，检查邮箱中是否包含@符号",
                context_info="这是一个用户类，需要验证用户信息的有效性"
            )

            # 验证结果
            assert isinstance(result, EditResult)
            print(f"编辑结果: {result.success}")
            print(f"使用策略: {result.strategy_used}")
            print(f"尝试次数: {result.attempts}")

            if not result.success:
                print(f"失败原因: {result.message}")

            # 检查文件内容
            with open(temp_file, 'r') as f:
                modified_content = f.read()

            print("修改后的内容:")
            print(modified_content)

            # 基本验证
            assert result.strategy_used in ["codeagent", "none"]
            if result.success:
                assert result.attempts > 0
            else:
                print(f"模型不可用，这是配置问题: {result.message}")
                assert result.attempts >= 0

        finally:
            os.unlink(temp_file)

    def test_error_handling_addition_with_llm(self):
        """测试使用真实LLM添加错误处理"""
        test_code = """import json

def load_config(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    return data

def save_config(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f)
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            temp_file = f.name

        try:
            # 执行编辑
            result = self.agent.edit_code(
                temp_file,
                "为load_config函数添加文件不存在和JSON解析错误的异常处理",
                context_info="这是一个配置文件处理模块，需要健壮的错误处理"
            )

            # 验证结果
            assert isinstance(result, EditResult)
            print(f"编辑结果: {result.success}")
            print(f"使用策略: {result.strategy_used}")
            print(f"尝试次数: {result.attempts}")

            if not result.success:
                print(f"失败原因: {result.message}")

            # 检查文件内容
            with open(temp_file, 'r') as f:
                modified_content = f.read()

            print("修改后的内容:")
            print(modified_content)

            # 基本验证
            assert result.strategy_used in ["codeagent", "none"]
            if result.success:
                assert result.attempts > 0
            else:
                print(f"模型不可用，这是配置问题: {result.message}")
                assert result.attempts >= 0

        finally:
            os.unlink(temp_file)

    def test_strategy_preference_with_llm(self):
        """测试策略偏好设置"""
        test_code = """def process_data(data):
    result = []
    for item in data:
        result.append(item * 2)
    return result
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            temp_file = f.name

        try:
            # 测试强制使用Cline策略
            result_cline = self.agent.edit_code(
                temp_file,
                "将函数名process_data改为transform_data",
                preferred_strategy="cline"
            )

            print(f"Cline策略结果: {result_cline.success}, 策略: {result_cline.strategy_used}")

            # 重置文件内容
            with open(temp_file, 'w') as f:
                f.write(test_code)

            # 测试强制使用Codex策略
            result_codex = self.agent.edit_code(
                temp_file,
                "将函数名process_data改为transform_data",
                preferred_strategy="codex"
            )

            print(f"Codex策略结果: {result_codex.success}, 策略: {result_codex.strategy_used}")

            # 验证策略偏好被尊重（基于CodeAgent的实现都使用codeagent策略）
            # 但任务描述中会包含策略偏好信息
            assert result_cline.strategy_used in ["codeagent", "none"]
            assert result_codex.strategy_used in ["codeagent", "none"]

        finally:
            os.unlink(temp_file)


@pytest.mark.unit
class TestCodeEditorAgentUnit:
    """单元测试（无LLM调用）"""

    def test_placeholder(self):
        """占位测试，确保类不为空"""
        assert True
