"""
意图识别模块

使用大语言模型对用户输入进行意图分类。
"""

import json
import logging
from typing import List, Optional
from dataclasses import dataclass

import litellm
from ai_agents.config import config
from ai_agents.core import get_model_for_task, TaskType

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: str
    confidence: float
    reasoning: Optional[str] = None


class IntentClassifier:
    """
    意图识别器

    使用大语言模型对用户输入的文本进行意图分类。
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        confidence_threshold: float = 0.7,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_model_manager: bool = True
    ):
        """
        初始化意图识别器

        Args:
            model: 使用的模型名称，如果为None且use_model_manager=True则自动选择快速模型
            api_base: API基础URL，如果为None则使用config中的配置
            api_key: API密钥，如果为None则使用config中的配置
            confidence_threshold: 置信度阈值，低于此值返回unknown
            temperature: 模型温度参数，如果为None则使用模型管理器的默认值
            max_tokens: 最大token数，如果为None则使用模型管理器的默认值
            use_model_manager: 是否使用模型管理器自动选择模型
        """
        self.confidence_threshold = confidence_threshold
        self.use_model_manager = use_model_manager

        if use_model_manager and model is None:
            # 使用模型管理器获取快速模型配置
            self.litellm_config = get_model_for_task(TaskType.INTENT_CLASSIFICATION, "litellm")
            self.model = self.litellm_config["model"]

            # 允许覆盖部分参数
            if temperature is not None:
                self.litellm_config["temperature"] = temperature
            if max_tokens is not None:
                self.litellm_config["max_tokens"] = max_tokens

            logger.info(f"使用模型管理器自动选择模型: {self.model}")
        else:
            # 手动配置模型
            self.model = model or "gpt-4o-mini"
            self.litellm_config = {
                "model": self.model,
                "temperature": temperature or 0.1,
                "max_tokens": max_tokens or 500
            }

            # 添加API配置
            api_base = api_base or config.LLM_API_BASE
            api_key = api_key or config.LLM_API_KEY
            if api_base:
                self.litellm_config["api_base"] = api_base
            if api_key:
                self.litellm_config["api_key"] = api_key

            logger.info(f"手动配置意图识别器: model={self.model}, threshold={confidence_threshold}")

    def classify(
        self,
        user_prompt: str,
        intent_list: List[str],
        include_reasoning: bool = False
    ) -> IntentResult:
        """
        对用户输入进行意图分类

        Args:
            user_prompt: 用户输入的文本
            intent_list: 可能的意图列表
            include_reasoning: 是否包含推理过程

        Returns:
            IntentResult: 包含意图、置信度和可选推理过程的结果

        Raises:
            ValueError: 当输入参数无效时
            Exception: 当API调用失败时
        """
        if not user_prompt or not user_prompt.strip():
            raise ValueError("用户输入不能为空")

        if not intent_list:
            raise ValueError("意图列表不能为空")

        # 构建系统提示
        system_prompt = self._build_system_prompt(intent_list, include_reasoning)

        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            logger.debug(f"调用LLM进行意图识别: {user_prompt[:100]}...")

            # 准备litellm配置
            litellm_config = self.litellm_config.copy()

            # 调用litellm，使用配置字典
            response = litellm.completion(
                messages=messages,
                **litellm_config
            )

            # 解析响应
            result = self._parse_response(response.choices[0].message.content, intent_list)

            # 检查置信度阈值
            if result.confidence < self.confidence_threshold:
                logger.info(f"置信度 {result.confidence} 低于阈值 {self.confidence_threshold}，返回unknown")
                result.intent = "unknown"

            logger.info(f"意图识别结果: {result.intent} (置信度: {result.confidence})")
            return result

        except Exception as e:
            logger.error(f"意图识别失败: {str(e)}")
            raise Exception(f"意图识别API调用失败: {str(e)}") from e

    def _build_system_prompt(self, intent_list: List[str], include_reasoning: bool) -> str:
        """构建系统提示"""
        intent_descriptions = "\n".join([f"- {intent}" for intent in intent_list])

        base_prompt = f"""你是一个专业的意图识别智能体。你的任务是分析用户输入的文本，并从给定的意图列表中选择最匹配的意图。

可选意图列表：
{intent_descriptions}

请按照以下JSON格式返回结果：
{{
    "intent": "最匹配的意图名称",
    "confidence": 0.95{', "reasoning": "选择此意图的原因"' if include_reasoning else ''}
}}

要求：
1. confidence字段必须是0到1之间的数值，表示匹配的置信度
2. 如果用户输入与所有意图都不匹配，请选择最相近的意图，但confidence应该较低
3. 只返回JSON格式，不要包含其他文字"""

        return base_prompt

    def _parse_response(self, response_content: str, intent_list: List[str]) -> IntentResult:
        """解析LLM响应"""
        try:
            # 清理响应内容
            response_content = response_content.strip()

            # 移除可能的代码块标记
            if response_content.startswith("```json"):
                response_content = response_content[7:]
            if response_content.endswith("```"):
                response_content = response_content[:-3]

            # 移除<think>标签内容（某些模型会输出思考过程）
            import re
            response_content = re.sub(r'<think>.*?</think>', '', response_content, flags=re.DOTALL)

            # 查找JSON内容
            response_content = response_content.strip()

            # 如果响应中包含多行，尝试找到JSON部分
            lines = response_content.split('\n')
            json_lines = []
            in_json = False

            for line in lines:
                line = line.strip()
                if line.startswith('{') or in_json:
                    in_json = True
                    json_lines.append(line)
                    if line.endswith('}'):
                        break

            if json_lines:
                response_content = '\n'.join(json_lines)

            result_data = json.loads(response_content.strip())

            intent = result_data.get("intent", "unknown")
            confidence = float(result_data.get("confidence", 0.0))
            reasoning = result_data.get("reasoning")

            # 验证意图是否在列表中
            if intent not in intent_list and intent != "unknown":
                logger.warning(f"返回的意图 '{intent}' 不在预定义列表中，设置为unknown")
                intent = "unknown"
                confidence = 0.0

            # 验证置信度范围
            confidence = max(0.0, min(1.0, confidence))

            return IntentResult(
                intent=intent,
                confidence=confidence,
                reasoning=reasoning
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"解析LLM响应失败: {str(e)}, 响应内容: {response_content}")
            return IntentResult(
                intent="unknown",
                confidence=0.0,
                reasoning=f"解析失败: {str(e)}"
            )

    def classify_batch(
        self,
        prompts: List[str],
        intent_list: List[str],
        include_reasoning: bool = False
    ) -> List[IntentResult]:
        """
        批量进行意图分类

        Args:
            prompts: 用户输入文本列表
            intent_list: 可能的意图列表
            include_reasoning: 是否包含推理过程

        Returns:
            List[IntentResult]: 意图识别结果列表
        """
        results = []
        for prompt in prompts:
            try:
                result = self.classify(prompt, intent_list, include_reasoning)
                results.append(result)
            except Exception as e:
                logger.error(f"批量处理中单个请求失败: {str(e)}")
                results.append(IntentResult(
                    intent="unknown",
                    confidence=0.0,
                    reasoning=f"处理失败: {str(e)}"
                ))
        return results
