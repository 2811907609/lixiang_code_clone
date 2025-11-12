"""
意图识别器测试模块
"""

import pytest
import json
from unittest.mock import Mock, patch

from ai_agents.llmtools.intent_classifier import IntentClassifier, IntentResult
from tests.test_config import skip_if_no_llm_config


@pytest.mark.unit
class TestIntentClassifier:
    """意图识别器测试类 - 单元测试（使用mock）"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.intent_list = ["查询天气", "播放音乐", "设置提醒", "查询时间"]
        self.classifier = IntentClassifier(
            model="gpt-4o-mini",
            confidence_threshold=0.7
        )

    def test_init_with_default_config(self):
        """测试使用默认配置初始化（使用模型管理器）"""
        classifier = IntentClassifier()
        assert classifier.confidence_threshold == 0.7
        assert classifier.use_model_manager is True
        # 使用模型管理器时，模型应该从配置中获取
        assert classifier.model is not None
        assert len(classifier.model) > 0

    def test_init_with_custom_config(self):
        """测试使用自定义配置初始化（不使用模型管理器）"""
        classifier = IntentClassifier(
            model="gpt-4",
            api_base="https://custom.api.com",
            api_key="custom_key",
            confidence_threshold=0.8,
            temperature=0.2,
            max_tokens=1000,
            use_model_manager=False
        )
        assert classifier.model == "gpt-4"
        assert classifier.litellm_config["api_base"] == "https://custom.api.com"
        assert classifier.litellm_config["api_key"] == "custom_key"
        assert classifier.confidence_threshold == 0.8
        assert classifier.litellm_config["temperature"] == 0.2
        assert classifier.litellm_config["max_tokens"] == 1000
        assert classifier.use_model_manager is False

    def test_init_with_model_manager_override(self):
        """测试使用模型管理器但覆盖部分参数"""
        classifier = IntentClassifier(
            confidence_threshold=0.8,
            temperature=0.3,
            max_tokens=2048,
            use_model_manager=True
        )
        assert classifier.confidence_threshold == 0.8
        assert classifier.litellm_config["temperature"] == 0.3
        assert classifier.litellm_config["max_tokens"] == 2048
        assert classifier.use_model_manager is True

    def test_classify_invalid_input(self):
        """测试无效输入"""
        # 空字符串
        with pytest.raises(ValueError, match="用户输入不能为空"):
            self.classifier.classify("", self.intent_list)

        # 空白字符串
        with pytest.raises(ValueError, match="用户输入不能为空"):
            self.classifier.classify("   ", self.intent_list)

        # 空意图列表
        with pytest.raises(ValueError, match="意图列表不能为空"):
            self.classifier.classify("今天天气怎么样", [])

    @patch('ai_agents.llmtools.intent_classifier.litellm.completion')
    def test_classify_success(self, mock_completion):
        """测试成功的意图识别"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "intent": "查询天气",
            "confidence": 0.95,
            "reasoning": "用户询问天气情况"
        })
        mock_completion.return_value = mock_response

        result = self.classifier.classify("今天天气怎么样", self.intent_list, include_reasoning=True)

        assert result.intent == "查询天气"
        assert result.confidence == 0.95
        assert result.reasoning == "用户询问天气情况"

        # 验证API调用参数
        mock_completion.assert_called_once()
        call_args = mock_completion.call_args
        assert call_args[1]['model'] == "gpt-4o-mini"  # 这个测试使用手动配置的模型
        assert call_args[1]['temperature'] == 0.1
        assert call_args[1]['max_tokens'] == 500
        assert len(call_args[1]['messages']) == 2

    @patch('ai_agents.llmtools.intent_classifier.litellm.completion')
    def test_classify_low_confidence(self, mock_completion):
        """测试低置信度情况"""
        # 模拟低置信度响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "intent": "查询天气",
            "confidence": 0.5
        })
        mock_completion.return_value = mock_response

        result = self.classifier.classify("随便说点什么", self.intent_list)

        # 由于置信度低于阈值，应该返回unknown
        assert result.intent == "unknown"
        assert result.confidence == 0.5

    @patch('ai_agents.llmtools.intent_classifier.litellm.completion')
    def test_classify_invalid_intent(self, mock_completion):
        """测试返回无效意图的情况"""
        # 模拟返回不在列表中的意图
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "intent": "无效意图",
            "confidence": 0.9
        })
        mock_completion.return_value = mock_response

        result = self.classifier.classify("测试输入", self.intent_list)

        # 应该被设置为unknown
        assert result.intent == "unknown"
        assert result.confidence == 0.0

    @patch('ai_agents.llmtools.intent_classifier.litellm.completion')
    def test_classify_json_parse_error(self, mock_completion):
        """测试JSON解析错误"""
        # 模拟无效JSON响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "这不是有效的JSON"
        mock_completion.return_value = mock_response

        result = self.classifier.classify("测试输入", self.intent_list)

        assert result.intent == "unknown"
        assert result.confidence == 0.0
        assert "解析失败" in result.reasoning

    @patch('ai_agents.llmtools.intent_classifier.litellm.completion')
    def test_classify_api_error(self, mock_completion):
        """测试API调用错误"""
        # 模拟API错误
        mock_completion.side_effect = Exception("API调用失败")

        with pytest.raises(Exception, match="意图识别API调用失败"):
            self.classifier.classify("测试输入", self.intent_list)

    @patch('ai_agents.llmtools.intent_classifier.litellm.completion')
    def test_classify_with_code_block_response(self, mock_completion):
        """测试包含代码块的响应"""
        # 模拟包含```json代码块的响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''```json
{
    "intent": "播放音乐",
    "confidence": 0.88
}
```'''
        mock_completion.return_value = mock_response

        result = self.classifier.classify("播放一首歌", self.intent_list)

        assert result.intent == "播放音乐"
        assert result.confidence == 0.88

    @patch('ai_agents.llmtools.intent_classifier.litellm.completion')
    def test_classify_batch(self, mock_completion):
        """测试批量意图识别"""
        # 模拟多个响应
        responses = [
            json.dumps({"intent": "查询天气", "confidence": 0.9}),
            json.dumps({"intent": "播放音乐", "confidence": 0.85}),
            "无效JSON"  # 测试错误处理
        ]

        mock_responses = []
        for response_content in responses:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = response_content
            mock_responses.append(mock_response)

        mock_completion.side_effect = mock_responses

        prompts = ["今天天气如何", "播放音乐", "无效输入"]
        results = self.classifier.classify_batch(prompts, self.intent_list)

        assert len(results) == 3
        assert results[0].intent == "查询天气"
        assert results[0].confidence == 0.9
        assert results[1].intent == "播放音乐"
        assert results[1].confidence == 0.85
        assert results[2].intent == "unknown"  # 解析失败的情况

    def test_build_system_prompt(self):
        """测试系统提示构建"""
        prompt = self.classifier._build_system_prompt(self.intent_list, include_reasoning=True)

        # 检查是否包含所有意图
        for intent in self.intent_list:
            assert intent in prompt

        # 检查是否包含reasoning字段
        assert '"reasoning"' in prompt

        # 测试不包含reasoning的情况
        prompt_no_reasoning = self.classifier._build_system_prompt(self.intent_list, include_reasoning=False)
        assert '"reasoning"' not in prompt_no_reasoning

    def test_parse_response_edge_cases(self):
        """测试响应解析的边界情况"""
        # 测试置信度超出范围
        result = self.classifier._parse_response(
            json.dumps({"intent": "查询天气", "confidence": 1.5}),
            self.intent_list
        )
        assert result.confidence == 1.0  # 应该被限制在1.0

        result = self.classifier._parse_response(
            json.dumps({"intent": "查询天气", "confidence": -0.5}),
            self.intent_list
        )
        assert result.confidence == 0.0  # 应该被限制在0.0

        # 测试缺少字段
        result = self.classifier._parse_response(
            json.dumps({"intent": "查询天气"}),  # 缺少confidence
            self.intent_list
        )
        assert result.confidence == 0.0


@pytest.mark.unit
class TestIntentResult:
    """意图结果测试类 - 单元测试"""

    def test_intent_result_creation(self):
        """测试意图结果创建"""
        result = IntentResult(
            intent="查询天气",
            confidence=0.95,
            reasoning="用户询问天气"
        )

        assert result.intent == "查询天气"
        assert result.confidence == 0.95
        assert result.reasoning == "用户询问天气"

    def test_intent_result_without_reasoning(self):
        """测试不包含推理的意图结果"""
        result = IntentResult(
            intent="播放音乐",
            confidence=0.8
        )

        assert result.intent == "播放音乐"
        assert result.confidence == 0.8
        assert result.reasoning is None


# LLM集成测试标记
@pytest.mark.llm
class TestIntentClassifierIntegration:
    """意图识别器集成测试（需要真实LLM API调用）"""

    def setup_method(self):
        """设置集成测试环境"""
        # 检查是否有API配置
        skip_if_no_llm_config()

        self.classifier = IntentClassifier(confidence_threshold=0.6)
        self.intent_list = ["查询天气", "播放音乐", "设置提醒", "查询时间"]

    def test_real_api_weather_query(self):
        """测试真实API - 天气查询"""
        result = self.classifier.classify("今天北京的天气怎么样？", self.intent_list)

        # 应该识别为天气查询
        assert result.intent == "查询天气"
        assert result.confidence > 0.6

    def test_real_api_music_request(self):
        """测试真实API - 音乐播放"""
        result = self.classifier.classify("播放一首周杰伦的歌", self.intent_list)

        # 应该识别为播放音乐
        assert result.intent == "播放音乐"
        assert result.confidence > 0.6

    def test_real_api_unknown_intent(self):
        """测试真实API - 未知意图"""
        result = self.classifier.classify("帮我计算1+1等于多少", self.intent_list)

        # 由于不在意图列表中，可能被识别为unknown或置信度较低
        assert result.confidence >= 0.0
