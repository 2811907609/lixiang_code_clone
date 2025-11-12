"""
LLM连接测试模块
用于测试所有模型管理器中的模型连接状态
"""

import pytest
import time
import logging
from typing import Tuple

import litellm

from ai_agents.lib.smolagents import CodeAgent
from ai_agents.core.model_manager import model_manager
from ai_agents.core.model_types import ModelType, TaskType
from ai_agents.core import get_model_for_task
from tests.test_config import skip_if_no_llm_config

# 配置日志
logger = logging.getLogger(__name__)


@pytest.mark.llm
class TestLLMConnection:
    """LLM连接测试类"""

    def setup_method(self):
        """设置测试环境"""
        skip_if_no_llm_config()
        self.test_message = "Hello, this is a connection test. Please respond with 'OK'."
        self.max_tokens = 50
        self.timeout = 30

    def _test_single_model_connection(self, model_type: ModelType) -> Tuple[bool, str, float]:
        """
        测试单个模型的连接

        Returns:
            Tuple[bool, str, float]: (是否成功, 错误信息或响应, 响应时间)
        """
        start_time = time.time()

        try:
            # 获取模型配置
            litellm_config = model_manager.get_litellm_config(model_type)

            # 准备测试消息
            messages = [{"role": "user", "content": self.test_message}]

            # 添加连接测试的特殊配置
            test_config = litellm_config.copy()
            test_config["max_tokens"] = self.max_tokens
            test_config["timeout"] = self.timeout

            # 调用LLM
            response = litellm.completion(
                messages=messages,
                **test_config
            )

            response_time = time.time() - start_time
            response_content = response.choices[0].message.content

            return True, response_content, response_time

        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}"
            return False, error_msg, response_time

    def test_fast_model_connection(self):
        """专门测试快速模型连接"""
        success, result, response_time = self._test_single_model_connection(ModelType.FAST)

        if not success:
            pytest.fail(f"快速模型连接失败: {result}")

        assert response_time < 60, f"快速模型响应时间过长: {response_time:.2f}s"
        assert len(result) > 0, "快速模型返回空响应"

    def test_powerful_model_connection(self):
        """专门测试强大模型连接"""
        success, result, response_time = self._test_single_model_connection(ModelType.POWERFUL)

        if not success:
            pytest.fail(f"强大模型连接失败: {result}")

        assert len(result) > 0, "强大模型返回空响应"

    def test_summary_model_connection(self):
        """专门测试摘要模型连接"""
        success, result, response_time = self._test_single_model_connection(ModelType.SUMMARY)

        if not success:
            pytest.fail(f"摘要模型连接失败: {result}")

        assert len(result) > 0, "摘要模型返回空响应"

@pytest.mark.llm
class TestLLMPerformance:
    """LLM性能测试类"""

    def setup_method(self):
        """设置测试环境"""
        skip_if_no_llm_config()

    def test_response_time_benchmark(self):
        """测试响应时间基准"""
        test_message = "Count from 1 to 5."

        # 测试快速模型的响应时间
        start_time = time.time()
        litellm_config = model_manager.get_litellm_config(ModelType.FAST)

        # 准备配置，避免参数重复
        test_config = litellm_config.copy()
        test_config["max_tokens"] = 50

        response = litellm.completion(
            messages=[{"role": "user", "content": test_message}],
            **test_config
        )

        response_time = time.time() - start_time

        print(f"\n快速模型响应时间: {response_time:.2f}s")
        print(f"响应内容: {response.choices[0].message.content}")

        # 快速模型应该在合理时间内响应
        assert response_time < 120, f"快速模型响应时间过长: {response_time:.2f}s"

    def test_concurrent_requests(self):
        """测试并发请求（简单版本）"""
        import concurrent.futures

        def make_request():
            litellm_config = model_manager.get_litellm_config(ModelType.FAST)

            # 准备配置，避免参数重复
            test_config = litellm_config.copy()
            test_config["max_tokens"] = 10

            response = litellm.completion(
                messages=[{"role": "user", "content": "Say 'test'"}],
                **test_config
            )
            return response.choices[0].message.content

        # 发送2个并发请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(make_request) for _ in range(2)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        assert len(results) == 2, "并发请求数量不正确"
        for result in results:
            assert len(result) > 0, "并发请求返回空响应"


@pytest.mark.llm
class TestSmolagentsCodeAgent:
    """Smolagents CodeAgent基本可用性测试"""

    def setup_method(self):
        """设置测试环境"""
        skip_if_no_llm_config()

    def test_codeagent_basic_functionality(self):
        """测试CodeAgent基本功能 - 最简单的case"""
        # 使用快速模型节省tokens
        model = get_model_for_task(TaskType.SIMPLE_QA, "smolagents")

        # 创建最简单的CodeAgent（无工具）
        agent = CodeAgent(
            tools=[],
            model=model,
            verbosity_level=20,
            stream_outputs=False
        )

        # 验证创建成功
        assert agent is not None
        assert agent.model is not None

        # 执行最简单的任务
        task = "Say hello"

        try:
            result = agent.run(task)

            # 验证基本响应
            assert isinstance(result, str)
            assert len(result) > 0

            print("\n✅ CodeAgent基本功能测试成功")
            print(f"任务: {task}")
            print(f"结果: {result[:50]}...")

        except Exception as e:
            pytest.fail(f"CodeAgent基本功能测试失败: {e}")
